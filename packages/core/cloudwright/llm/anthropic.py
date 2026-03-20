"""Anthropic LLM provider."""

from __future__ import annotations

import os
import random
import time
from collections.abc import Iterator

import anthropic

from cloudwright.llm.base import BaseLLM
from cloudwright.logging import get_logger

log = get_logger(__name__)

GENERATE_MODEL = "claude-sonnet-4-6"
FAST_MODEL = "claude-haiku-4-5-20251001"
_MAX_RETRIES = int(os.environ.get("CLOUDWRIGHT_LLM_MAX_RETRIES", 3))

_RETRYABLE = (
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
    anthropic.APITimeoutError,
)


class AnthropicLLM(BaseLLM):
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"), timeout=180.0)

    def generate(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> tuple[str, dict]:
        return self._call(GENERATE_MODEL, messages, system, max_tokens, timeout)

    def generate_fast(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> tuple[str, dict]:
        return self._call(FAST_MODEL, messages, system, max_tokens, timeout)

    def generate_stream(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> Iterator[str]:
        system_block = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        kwargs = dict(model=GENERATE_MODEL, max_tokens=max_tokens, system=system_block, messages=messages)
        if timeout is not None:
            kwargs["timeout"] = timeout
        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def _call(
        self, model: str, messages: list[dict], system: str, max_tokens: int, timeout: float | None = None
    ) -> tuple[str, dict]:
        # Cache the system prompt across calls — Anthropic caches for 5 minutes
        system_block = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
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
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }
                log.info(
                    "llm_call",
                    model=model,
                    duration_ms=round((time.perf_counter() - start) * 1000),
                    tokens=usage["input_tokens"] + usage["output_tokens"],
                )
                return response.content[0].text, usage
            except _RETRYABLE:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(delay * (1 + random.uniform(0, 0.5)))
                delay *= 2
