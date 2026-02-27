"""OpenAI LLM provider."""

from __future__ import annotations

import os
import time

import openai

from silmaril.llm.base import BaseLLM

_CLASSIFY_MODEL = "gpt-5-mini"
_GENERATE_MODEL = "gpt-5.2"
_MAX_RETRIES = 3


class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str | None = None):
        self.client = openai.OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def classify(self, text: str, system: str) -> tuple[str, dict]:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ]
        return self._call(_CLASSIFY_MODEL, messages, 500)

    def generate(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        full_messages = [{"role": "system", "content": system}] + messages
        return self._call(_GENERATE_MODEL, full_messages, max_tokens)

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
