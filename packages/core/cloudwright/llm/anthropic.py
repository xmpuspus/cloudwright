"""Anthropic LLM provider."""

from __future__ import annotations

import asyncio
import os
import random
import time
from collections.abc import AsyncIterator, Iterator

import anthropic

from cloudwright.llm.base import BaseLLM
from cloudwright.logging import get_logger

log = get_logger(__name__)

GENERATE_MODEL = os.environ.get("CLOUDWRIGHT_MODEL") or "claude-sonnet-4-6"
FAST_MODEL = "claude-haiku-4-5-20251001"
_MAX_RETRIES = int(os.environ.get("CLOUDWRIGHT_LLM_MAX_RETRIES", 3))

# Per-1K-token pricing (USD). Sonnet rate is the safe default fallback for any
# unrecognized model — better to slightly over-bill than to silently bill 10x
# wrong (the pre-fix bug for Haiku-routed calls).
_HAIKU_PRICING = {"input": 0.0008, "output": 0.004}
_SONNET_PRICING = {"input": 0.003, "output": 0.015}

# System-prompt cache_control kicks in only above ~1024 tokens — below that
# Anthropic ignores the cache_control hint, so we still send the block but the
# overhead is irrelevant. Keep the threshold here for the session helper.
SYSTEM_CACHE_MIN_TOKENS = 1024

_RETRYABLE = (
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
    anthropic.APITimeoutError,
)


def _normalize_system(system: str | list[dict]) -> list[dict]:
    """Accept a plain string or a pre-built list-of-blocks.

    String input is wrapped in a single ephemeral cache block — this matches
    the prior behavior. Callers (e.g. ``ConversationSession``) that want to
    split the system into a stable cached prefix + a small variable suffix can
    pass a list of blocks directly; we trust those callers to set
    ``cache_control`` on the right block(s).
    """
    if isinstance(system, list):
        return system
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


class AnthropicLLM(BaseLLM):
    def __init__(self, api_key: str | None = None):
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=resolved_key, timeout=180.0)
        # Async client used by ``generate_stream_async`` — instantiated lazily
        # on first use so import-time failures (e.g. missing async deps in
        # constrained environments) don't break the sync code path.
        self._async_client: anthropic.AsyncAnthropic | None = None
        self._api_key = resolved_key

    @property
    def async_client(self) -> anthropic.AsyncAnthropic:
        if self._async_client is None:
            self._async_client = anthropic.AsyncAnthropic(api_key=self._api_key, timeout=180.0)
        return self._async_client

    @property
    def model_name(self) -> str:
        return GENERATE_MODEL

    def _pricing_table(self) -> dict[str, dict[str, float]]:
        # Match by exact model id, plus prefixes for the dated Haiku/Sonnet
        # variants Anthropic returns (e.g. claude-haiku-4-5-20251001).
        return {
            FAST_MODEL: _HAIKU_PRICING,
            "claude-haiku-4-5": _HAIKU_PRICING,
            GENERATE_MODEL: _SONNET_PRICING,
            "claude-sonnet-4-6": _SONNET_PRICING,
        }

    def _default_pricing(self) -> dict[str, float]:
        return _SONNET_PRICING

    def pricing_for(self, model: str | None = None) -> dict[str, float]:
        if model is None:
            return self._default_pricing()
        table = self._pricing_table()
        if model in table:
            return table[model]
        # Prefix match for dated model ids (claude-haiku-4-5-20251001 etc).
        for key, rate in table.items():
            if model.startswith(key):
                return rate
        return self._default_pricing()

    def generate(
        self, messages: list[dict], system: str | list[dict], max_tokens: int = 2000, timeout: float | None = None
    ) -> tuple[str, dict]:
        return self._call(GENERATE_MODEL, messages, system, max_tokens, timeout)

    def generate_fast(
        self, messages: list[dict], system: str | list[dict], max_tokens: int = 2000, timeout: float | None = None
    ) -> tuple[str, dict]:
        return self._call(FAST_MODEL, messages, system, max_tokens, timeout)

    def generate_stream(
        self,
        messages: list[dict],
        system: str | list[dict],
        max_tokens: int = 2000,
        timeout: float | None = None,
    ) -> Iterator[str]:
        system_block = _normalize_system(system)
        kwargs = dict(model=GENERATE_MODEL, max_tokens=max_tokens, system=system_block, messages=messages)
        if timeout is not None:
            kwargs["timeout"] = timeout
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                with self.client.messages.stream(**kwargs) as stream:
                    for text in stream.text_stream:
                        yield text
                return
            except _RETRYABLE:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(delay * (1 + random.uniform(0, 0.5)))
                delay *= 2

    async def generate_stream_async(
        self,
        messages: list[dict],
        system: str | list[dict],
        max_tokens: int = 2000,
        timeout: float | None = None,
    ) -> AsyncIterator[str]:
        """Async streaming via ``AsyncAnthropic``.

        Cancel-safe: if the consumer breaks (client disconnect, timeout,
        ``asyncio.CancelledError``), the ``async with`` block tears down the
        underlying httpx stream and closes the upstream connection — so we
        stop billing tokens the moment the consumer goes away.
        """
        system_block = _normalize_system(system)
        kwargs = dict(model=GENERATE_MODEL, max_tokens=max_tokens, system=system_block, messages=messages)
        if timeout is not None:
            kwargs["timeout"] = timeout
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                async with self.async_client.messages.stream(**kwargs) as stream:
                    async for text in stream.text_stream:
                        yield text
                return
            except _RETRYABLE:
                if attempt == _MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(delay * (1 + random.uniform(0, 0.5)))
                delay *= 2

    def _call(
        self,
        model: str,
        messages: list[dict],
        system: str | list[dict],
        max_tokens: int,
        timeout: float | None = None,
    ) -> tuple[str, dict]:
        system_block = _normalize_system(system)
        kwargs = dict(model=model, max_tokens=max_tokens, system=system_block, messages=messages)
        if timeout is not None:
            kwargs["timeout"] = timeout
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                start = time.perf_counter()
                response = self.client.messages.create(**kwargs)
                if not response.content:
                    raise ValueError("LLM returned empty response")
                cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
                cache_write = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
                usage = {
                    "model": model,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "cached_tokens": cache_read,
                    "cache_creation_tokens": cache_write,
                }
                log.info(
                    "llm_call",
                    model=model,
                    duration_ms=round((time.perf_counter() - start) * 1000),
                    tokens=usage["input_tokens"] + usage["output_tokens"],
                    cache_read=cache_read,
                    cache_write=cache_write,
                )
                return response.content[0].text, usage
            except _RETRYABLE:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(delay * (1 + random.uniform(0, 0.5)))
                delay *= 2
