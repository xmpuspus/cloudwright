"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class BaseLLM(ABC):
    @abstractmethod
    def generate(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        """Full generation using a capable model.

        Returns (response_text, usage_dict).
        """

    @abstractmethod
    def generate_fast(self, messages: list[dict], system: str, max_tokens: int = 2000) -> tuple[str, dict]:
        """Fast generation using a lighter model for simple tasks.

        Returns (response_text, usage_dict).
        """

    @abstractmethod
    def generate_stream(self, messages: list[dict], system: str, max_tokens: int = 2000) -> Iterator[str]:
        """Stream generation using the capable model. Yields text chunks."""
