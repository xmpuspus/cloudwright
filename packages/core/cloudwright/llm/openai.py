"""OpenAI LLM provider."""

from __future__ import annotations

import os
import random
import time
from collections.abc import Iterator

import openai

from cloudwright.llm.base import BaseLLM

GENERATE_MODEL = "gpt-5.2"
FAST_MODEL = "gpt-5-mini"
_MAX_RETRIES = int(os.environ.get("CLOUDWRIGHT_LLM_MAX_RETRIES", 3))

_RETRYABLE = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.InternalServerError,
    openai.APITimeoutError,
)


class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str | None = None):
        self.client = openai.OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"), timeout=180.0)

    def generate(self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None) -> tuple[str, dict]:
        full_messages = [{"role": "system", "content": system}] + messages
        return self._call(GENERATE_MODEL, full_messages, max_tokens, timeout)

    def generate_fast(self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None) -> tuple[str, dict]:
        full_messages = [{"role": "system", "content": system}] + messages
        return self._call(FAST_MODEL, full_messages, max_tokens, timeout)

    def generate_stream(self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None) -> Iterator[str]:
        full_messages = [{"role": "system", "content": system}] + messages
        kwargs = dict(model=GENERATE_MODEL, max_tokens=max_tokens, messages=full_messages, stream=True)
        if timeout is not None:
            kwargs["timeout"] = timeout
        stream = self.client.chat.completions.create(**kwargs)
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    def _call(self, model: str, messages: list[dict], max_tokens: int, timeout: float | None = None) -> tuple[str, dict]:
        kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
        if timeout is not None:
            kwargs["timeout"] = timeout
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(**kwargs)
                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                }
                return response.choices[0].message.content, usage
            except _RETRYABLE:
                if attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(delay * (1 + random.uniform(0, 0.5)))
                delay *= 2
