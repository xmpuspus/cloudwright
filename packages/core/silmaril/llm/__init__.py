"""LLM abstraction layer with auto-detection from environment variables."""

from __future__ import annotations

import os

from silmaril.llm.base import BaseLLM


def get_llm(provider: str | None = None) -> BaseLLM:
    """Factory: get an LLM client based on env config.

    Priority: SILMARIL_LLM_PROVIDER env var > explicit provider arg >
    auto-detect from available API keys (Anthropic first, then OpenAI).
    """
    provider = provider or os.environ.get("SILMARIL_LLM_PROVIDER", "").lower()

    if provider == "openai":
        from silmaril.llm.openai import OpenAILLM

        return OpenAILLM()

    if provider == "anthropic":
        from silmaril.llm.anthropic import AnthropicLLM

        return AnthropicLLM()

    # Auto-detect from available keys
    if os.environ.get("ANTHROPIC_API_KEY"):
        from silmaril.llm.anthropic import AnthropicLLM

        return AnthropicLLM()

    if os.environ.get("OPENAI_API_KEY"):
        from silmaril.llm.openai import OpenAILLM

        return OpenAILLM()

    raise RuntimeError(
        "No LLM provider configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
        "or set SILMARIL_LLM_PROVIDER=anthropic|openai"
    )


__all__ = ["BaseLLM", "get_llm"]
