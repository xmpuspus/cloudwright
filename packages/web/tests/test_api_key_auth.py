"""Tests for the constant-time API key check.

The pre-v1.3 ``check_api_key`` used ``provided != _API_KEY`` which leaks the
key length and (under some interpreters) prefix-match timing. v1.3 switches
to ``hmac.compare_digest`` on bytes, plus an explicit empty-input short-circuit.

Tests patch the module-level ``_API_KEY`` directly via monkeypatch and restore
it on teardown — we avoid ``importlib.reload`` because reloading the
middleware module wipes the singleton ``_rate_limiter`` and breaks
unrelated tests that rely on the same instance.
"""

from __future__ import annotations

import cloudwright_web.middleware as middleware
import pytest
from fastapi import HTTPException


class _StubRequest:
    """Just enough of starlette.Request to drive ``check_api_key``."""

    def __init__(self, header_value: str | None):
        self.headers = {"x-api-key": header_value} if header_value is not None else {}


@pytest.fixture
def with_key(monkeypatch):
    """Set the configured API key for the duration of one test."""

    def _set(value: str | None):
        monkeypatch.setattr(middleware, "_API_KEY", value)

    return _set


def test_returns_none_when_no_api_key_configured(with_key):
    with_key(None)
    # Even an explicitly garbage header is allowed when no key is set.
    assert middleware.check_api_key(_StubRequest("anything")) is None


def test_correct_key_passes(with_key):
    with_key("secret-token-abc123")
    assert middleware.check_api_key(_StubRequest("secret-token-abc123")) is None


def test_wrong_key_same_length_raises_401(with_key):
    """Two equal-length keys must compare via hmac.compare_digest."""
    with_key("secret-token-abc123")
    with pytest.raises(HTTPException) as exc:
        middleware.check_api_key(_StubRequest("secret-token-XYZ999"))
    assert exc.value.status_code == 401


def test_wrong_key_different_length_raises_401(with_key):
    with_key("secret-token-abc123")
    with pytest.raises(HTTPException) as exc:
        middleware.check_api_key(_StubRequest("short"))
    assert exc.value.status_code == 401


def test_missing_header_raises_401(with_key):
    with_key("secret-token-abc123")
    with pytest.raises(HTTPException) as exc:
        middleware.check_api_key(_StubRequest(None))
    assert exc.value.status_code == 401


def test_empty_header_raises_401(with_key):
    with_key("secret-token-abc123")
    with pytest.raises(HTTPException) as exc:
        middleware.check_api_key(_StubRequest(""))
    assert exc.value.status_code == 401


def test_uses_hmac_compare_digest(with_key, monkeypatch):
    """Sanity check: the implementation actually calls hmac.compare_digest.

    We monkeypatch ``hmac.compare_digest`` and assert it is invoked with the
    UTF-8 encoded bytes of both sides — this pins the constant-time semantic.
    """
    with_key("abc")
    calls: list[tuple[bytes, bytes]] = []
    real = middleware.hmac.compare_digest

    def spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(middleware.hmac, "compare_digest", spy)
    with pytest.raises(HTTPException):
        middleware.check_api_key(_StubRequest("xyz"))
    assert calls, "hmac.compare_digest should have been called"
    a, b = calls[0]
    assert isinstance(a, bytes) and isinstance(b, bytes)
    assert a == b"xyz"
    assert b == b"abc"
