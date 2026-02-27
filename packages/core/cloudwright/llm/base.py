"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLM(ABC):
    @abstractmethod
    def generate(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        """Full generation using a capable model.

        Returns (response_text, usage_dict).
        """
