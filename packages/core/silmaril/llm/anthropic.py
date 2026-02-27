"""Anthropic LLM provider."""

from __future__ import annotations

import os
import time

import anthropic

from silmaril.llm.base import BaseLLM

_CLASSIFY_MODEL = "claude-haiku-4-5-20251001"
_GENERATE_MODEL = "claude-sonnet-4-20250514"
_MAX_RETRIES = 3


class AnthropicLLM(BaseLLM):
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def classify(self, text: str, system: str) -> tuple[str, dict]:
        return self._call(_CLASSIFY_MODEL, [{"role": "user", "content": text}], system, 500)

    def generate(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        return self._call(_GENERATE_MODEL, messages, system, max_tokens)

    def _call(self, model: str, messages: list[dict], system: str, max_tokens: int) -> tuple[str, dict]:
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
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
