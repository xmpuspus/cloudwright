from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


class TestRateLimiterDirect:
    def test_allows_under_limit(self):
        from cloudwright_web.app import _RateLimiter

        limiter = _RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            allowed, retry = limiter.is_allowed("1.2.3.4")
            assert allowed is True
            assert retry == 0

    def test_blocks_over_limit(self):
        from cloudwright_web.app import _RateLimiter

        limiter = _RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("1.2.3.4")

        allowed, retry = limiter.is_allowed("1.2.3.4")
        assert allowed is False
        assert retry > 0

    def test_different_ips_independent(self):
        from cloudwright_web.app import _RateLimiter

        limiter = _RateLimiter(max_requests=1, window_seconds=60)
        limiter.is_allowed("1.1.1.1")
        allowed_a, _ = limiter.is_allowed("1.1.1.1")
        allowed_b, _ = limiter.is_allowed("2.2.2.2")
        assert allowed_a is False
        assert allowed_b is True

    def test_resets_after_window(self):
        from cloudwright_web.app import _RateLimiter

        limiter = _RateLimiter(max_requests=2, window_seconds=1)
        limiter.is_allowed("1.2.3.4")
        limiter.is_allowed("1.2.3.4")
        blocked, _ = limiter.is_allowed("1.2.3.4")
        assert blocked is False

        # Manually expire the bucket by backdating timestamps
        import collections

        limiter._buckets["1.2.3.4"] = collections.deque([time.time() - 2, time.time() - 2])
        allowed, _ = limiter.is_allowed("1.2.3.4")
        assert allowed is True


class TestRateLimitingViaAPI:
    def test_rate_limiter_blocks_over_limit(self, client):
        from cloudwright_web.app import _RateLimiter

        tight = _RateLimiter(max_requests=1, window_seconds=60)

        with patch("cloudwright_web.app._rate_limiter", tight):
            # First request uses the one allowed slot
            client.post("/api/design", json={"description": "simple app"})
            # Second should be blocked
            resp = client.post("/api/design", json={"description": "simple app"})

        assert resp.status_code == 429
        data = resp.json()
        assert data["code"] == "rate_limited"
        assert "suggestion" in data
