"""Anthropic LLM provider."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

import anthropic

from cloudwright.llm.base import BaseLLM

GENERATE_MODEL = "claude-sonnet-4-6"
FAST_MODEL = "claude-haiku-4-5-20251001"
_MAX_RETRIES = 3


class AnthropicLLM(BaseLLM):
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"), timeout=180.0)

    def generate(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        return self._call(GENERATE_MODEL, messages, system, max_tokens)

    def generate_fast(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        return self._call(FAST_MODEL, messages, system, max_tokens)

    def generate_stream(self, messages: list[dict], system: str, max_tokens: int = 2000) -> Iterator[str]:
        system_block = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        with self.client.messages.stream(
            model=GENERATE_MODEL,
            max_tokens=max_tokens,
            system=system_block,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text

    def _call(self, model: str, messages: list[dict], system: str, max_tokens: int) -> tuple[str, dict]:
        # Cache the system prompt across calls — Anthropic caches for 5 minutes
        system_block = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_block,
                    messages=messages,
                )
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }
                return response.content[0].text, usage
            except anthropic.RateLimitError:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(delay)
                delay *= 2
