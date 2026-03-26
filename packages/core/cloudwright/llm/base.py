"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class BaseLLM(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Primary model identifier (e.g. 'claude-sonnet-4-6')."""

    @property
    @abstractmethod
    def pricing(self) -> dict[str, float]:
        """Per-1K-token pricing: {"input": ..., "output": ...}."""

    @abstractmethod
    def generate(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> tuple[str, dict]:
        """Full generation. Returns (response_text, usage_dict)."""

    @abstractmethod
    def generate_fast(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> tuple[str, dict]:
        """Fast generation using a lighter model. Returns (response_text, usage_dict)."""

    @abstractmethod
    def generate_stream(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> Iterator[str]:
        """Stream generation. Yields text chunks."""

    def estimate_tokens(self, text: str) -> int:
        """Rough token count (~4 chars per token for English)."""
        return len(text) // 4
