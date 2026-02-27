"""LLM abstraction layer with auto-detection from environment variables."""

from __future__ import annotations

import os

from cloudwright.llm.base import BaseLLM


def get_llm(provider: str | None = None) -> BaseLLM:
    """Factory: get an LLM client based on env config.

    Priority: CLOUDWRIGHT_LLM_PROVIDER env var > explicit provider arg >
    auto-detect from available API keys (Anthropic first, then OpenAI).
    """
    provider = provider or os.environ.get("CLOUDWRIGHT_LLM_PROVIDER", "").lower()

    if provider == "openai":
        from cloudwright.llm.openai import OpenAILLM

        return OpenAILLM()

    if provider == "anthropic":
        from cloudwright.llm.anthropic import AnthropicLLM

        return AnthropicLLM()

    # Auto-detect from available keys
    if os.environ.get("ANTHROPIC_API_KEY"):
        from cloudwright.llm.anthropic import AnthropicLLM

        return AnthropicLLM()

    if os.environ.get("OPENAI_API_KEY"):
        from cloudwright.llm.openai import OpenAILLM

        return OpenAILLM()

    raise RuntimeError(
        "No LLM provider configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
        "or set CLOUDWRIGHT_LLM_PROVIDER=anthropic|openai"
    )


__all__ = ["BaseLLM", "get_llm"]
