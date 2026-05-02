"""OpenAI LLM provider."""

from __future__ import annotations

import asyncio
import os
import random
import time
from collections.abc import AsyncIterator, Iterator

import openai

from cloudwright.llm.base import BaseLLM
from cloudwright.logging import get_logger

log = get_logger(__name__)

GENERATE_MODEL = os.environ.get("CLOUDWRIGHT_MODEL") or "gpt-5.2"
FAST_MODEL = "gpt-5-mini"
_MAX_RETRIES = int(os.environ.get("CLOUDWRIGHT_LLM_MAX_RETRIES", 3))

# Per-1K-token pricing (USD). Conservative starting rates pending an audit
# pass against the live OpenAI pricing page; fall back to GPT-5 rates for any
# unrecognized id.
_GPT5_PRICING = {"input": 0.0025, "output": 0.01}
_GPT5_MINI_PRICING = {"input": 0.0005, "output": 0.002}

_RETRYABLE = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.InternalServerError,
    openai.APITimeoutError,
)


class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str | None = None):
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = openai.OpenAI(api_key=resolved_key, timeout=180.0)
        self._async_client: openai.AsyncOpenAI | None = None
        self._api_key = resolved_key

    @property
    def async_client(self) -> openai.AsyncOpenAI:
        if self._async_client is None:
            self._async_client = openai.AsyncOpenAI(api_key=self._api_key, timeout=180.0)
        return self._async_client

    @property
    def model_name(self) -> str:
        return GENERATE_MODEL

    def _pricing_table(self) -> dict[str, dict[str, float]]:
        return {
            FAST_MODEL: _GPT5_MINI_PRICING,
            "gpt-5-mini": _GPT5_MINI_PRICING,
            GENERATE_MODEL: _GPT5_PRICING,
            "gpt-5.2": _GPT5_PRICING,
            "gpt-5": _GPT5_PRICING,
        }

    def _default_pricing(self) -> dict[str, float]:
        return _GPT5_PRICING

    def pricing_for(self, model: str | None = None) -> dict[str, float]:
        if model is None:
            return self._default_pricing()
        table = self._pricing_table()
        if model in table:
            return table[model]
        # Prefix match (e.g. gpt-5-2024-..., gpt-5-mini-2024-...). Order matters
        # — check the more-specific "mini" prefix before the generic "gpt-5".
        if model.startswith("gpt-5-mini"):
            return _GPT5_MINI_PRICING
        if model.startswith("gpt-5"):
            return _GPT5_PRICING
        return self._default_pricing()

    def generate(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> tuple[str, dict]:
        full_messages = [{"role": "system", "content": system}] + messages
        return self._call(GENERATE_MODEL, full_messages, max_tokens, timeout)

    def generate_fast(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> tuple[str, dict]:
        full_messages = [{"role": "system", "content": system}] + messages
        return self._call(FAST_MODEL, full_messages, max_tokens, timeout)

    def generate_stream(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> Iterator[str]:
        full_messages = [{"role": "system", "content": system}] + messages
        kwargs = dict(
            model=GENERATE_MODEL,
            max_completion_tokens=max_tokens,
            messages=full_messages,
            stream=True,
            # Surface usage on the final chunk; without this the streaming
            # response carries no token counts and we can't bill or cache-track.
            stream_options={"include_usage": True},
        )
        if timeout is not None:
            kwargs["timeout"] = timeout
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            stream = None
            try:
                stream = self.client.chat.completions.create(**kwargs)
                try:
                    for chunk in stream:
                        if not chunk.choices:
                            continue
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                finally:
                    # Always release the connection — the OpenAI SDK Stream
                    # holds an HTTP response, and dropping it without close()
                    # leaks connections from the pool when the consumer breaks
                    # early (e.g. client disconnect mid-stream).
                    close = getattr(stream, "close", None)
                    if callable(close):
                        try:
                            close()
                        except Exception:
                            pass
                return
            except _RETRYABLE:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(delay * (1 + random.uniform(0, 0.5)))
                delay *= 2

    async def generate_stream_async(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> AsyncIterator[str]:
        """Async streaming via ``AsyncOpenAI``.

        Cancel-safe: ``async with`` on the stream guarantees the underlying
        httpx response is released the moment the consumer goes away (client
        disconnect, ``asyncio.CancelledError``, exception in the consumer).
        Without this, the orphaned coroutine would keep consuming tokens
        until the LLM returned its final chunk.
        """
        full_messages = [{"role": "system", "content": system}] + messages
        kwargs = dict(
            model=GENERATE_MODEL,
            max_completion_tokens=max_tokens,
            messages=full_messages,
            stream=True,
            # Surface usage on the final chunk; without this the streaming
            # response carries no token counts and we can't bill or
            # cache-track.
            stream_options={"include_usage": True},
        )
        if timeout is not None:
            kwargs["timeout"] = timeout
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                stream = await self.async_client.chat.completions.create(**kwargs)
                try:
                    async for chunk in stream:
                        if not chunk.choices:
                            continue
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                finally:
                    # AsyncStream supports either ``aclose`` or ``close`` on a
                    # given SDK version — call whichever exists. Swallow
                    # close-time errors because we may already be unwinding
                    # from a cancellation.
                    aclose = getattr(stream, "aclose", None)
                    if callable(aclose):
                        try:
                            await aclose()
                        except Exception:
                            pass
                    else:
                        close = getattr(stream, "close", None)
                        if callable(close):
                            try:
                                close()
                            except Exception:
                                pass
                return
            except _RETRYABLE:
                if attempt == _MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(delay * (1 + random.uniform(0, 0.5)))
                delay *= 2

    def _call(
        self, model: str, messages: list[dict], max_tokens: int, timeout: float | None = None
    ) -> tuple[str, dict]:
        kwargs = dict(model=model, max_completion_tokens=max_tokens, messages=messages)
        if timeout is not None:
            kwargs["timeout"] = timeout
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                start = time.perf_counter()
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("LLM returned empty response")
                cached = 0
                details = getattr(response.usage, "prompt_tokens_details", None)
                if details is not None:
                    cached = getattr(details, "cached_tokens", 0) or 0
                usage = {
                    "model": model,
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                    "cached_tokens": cached,
                }
                log.info(
                    "llm_call",
                    model=model,
                    duration_ms=round((time.perf_counter() - start) * 1000),
                    tokens=usage["input_tokens"] + usage["output_tokens"],
                    cached=cached,
                )
                return content, usage
            except _RETRYABLE:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(delay * (1 + random.uniform(0, 0.5)))
                delay *= 2
