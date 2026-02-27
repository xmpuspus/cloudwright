"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLM(ABC):
    @abstractmethod
    def classify(self, text: str, system: str) -> tuple[str, dict]:
        """Fast classification using a cheap model.

        Returns (response_text, usage_dict) where usage_dict has
        'input_tokens' and 'output_tokens' keys.
        """

    @abstractmethod
    def generate(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        """Full generation using a capable model.

        Returns (response_text, usage_dict).
        """
