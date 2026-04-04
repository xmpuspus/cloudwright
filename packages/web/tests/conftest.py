"""Shared fixtures for web API tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _mock_llm_key(monkeypatch):
    """Ensure an LLM API key is present for health checks in CI."""
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-for-ci")


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear rate limiter state between tests so requests don't bleed across."""
    from cloudwright_web.middleware import _rate_limiter

    _rate_limiter._buckets.clear()
