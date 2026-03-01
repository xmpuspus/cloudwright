"""OpenAI LLM provider."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

import openai

from cloudwright.llm.base import BaseLLM

GENERATE_MODEL = "gpt-5.2"
FAST_MODEL = "gpt-5-mini"
_MAX_RETRIES = 3


class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str | None = None):
        self.client = openai.OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"), timeout=180.0)

    def generate(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        full_messages = [{"role": "system", "content": system}] + messages
        return self._call(GENERATE_MODEL, full_messages, max_tokens)

    def generate_fast(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        full_messages = [{"role": "system", "content": system}] + messages
        return self._call(FAST_MODEL, full_messages, max_tokens)

    def generate_stream(self, messages: list[dict], system: str, max_tokens: int = 2000) -> Iterator[str]:
        full_messages = [{"role": "system", "content": system}] + messages
        stream = self.client.chat.completions.create(
            model=GENERATE_MODEL,
            max_tokens=max_tokens,
            messages=full_messages,
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    def _call(self, model: str, messages: list[dict], max_tokens: int) -> tuple[str, dict]:
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=messages,
                )
                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                }
                return response.choices[0].message.content, usage
            except openai.RateLimitError:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(delay)
                delay *= 2
