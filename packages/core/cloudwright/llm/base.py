"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator


class BaseLLM(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Primary model identifier (e.g. 'claude-sonnet-4-6')."""

    def pricing_for(self, model: str | None = None) -> dict[str, float]:
        """Per-1K-token pricing for the given model.

        Override in subclasses to map model -> {"input": ..., "output": ...}.
        Falling back to the default model's rate when ``model`` is unknown or
        ``None`` keeps callers safe even if the LLM returns an unexpected name.
        """
        return self._pricing_table().get(model or self.model_name, self._default_pricing())

    @property
    def pricing(self) -> dict[str, float]:
        """Backwards-compatible default-model pricing.

        Older callers (and tests) read ``llm.pricing`` directly. Returning the
        default model's rate keeps them working while new code can call
        ``pricing_for(model)`` to bill the actual model used per call.
        """
        return self._default_pricing()

    def _pricing_table(self) -> dict[str, dict[str, float]]:
        """Subclasses override with their per-model pricing table."""
        return {}

    def _default_pricing(self) -> dict[str, float]:
        """Subclasses override with the default model's per-1K-token rate."""
        return {"input": 0.003, "output": 0.015}

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

    async def generate_stream_async(
        self, messages: list[dict], system: str, max_tokens: int = 2000, timeout: float | None = None
    ) -> AsyncIterator[str]:
        """Async streaming. Yields text chunks via ``async for``.

        Default implementation falls back to bridging the sync ``generate_stream``
        through ``asyncio.to_thread``. Concrete providers should override with a
        native async path (``AsyncAnthropic``, ``AsyncOpenAI``) so that
        cancellation propagates into the underlying httpx connection — without
        the override, cancelling the consumer leaves the worker thread (and
        upstream LLM call) running to completion.
        """
        import asyncio

        chunks: list[str] = []

        def _collect() -> list[str]:
            for c in self.generate_stream(messages, system, max_tokens, timeout):
                chunks.append(c)
            return chunks

        # Fallback path: drain the sync stream off-thread, then yield.
        # Not cancel-safe, but provides a working default for any third-party
        # provider that hasn't yet implemented the async path.
        for c in await asyncio.to_thread(_collect):
            yield c

    def estimate_tokens(self, text: str) -> int:
        """Rough token count (~4 chars per token for English)."""
        return len(text) // 4
