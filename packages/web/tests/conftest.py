"""Shared fixtures for web API tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear rate limiter state between tests so requests don't bleed across."""
    from cloudwright_web.middleware import _rate_limiter

    _rate_limiter._buckets.clear()
