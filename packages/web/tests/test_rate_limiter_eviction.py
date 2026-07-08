"""``_RateLimiter`` must evict empty IP buckets, not just pop expired entries.

MEDIUM audit finding: the limiter only ever popped expired timestamps off a
per-IP deque; it never removed the (now-empty) deque from ``_buckets``. Under
IP churn (many one-off or rotating source IPs, e.g. behind a CDN or scanner
traffic) every distinct IP that is seen even once leaves a permanent dict
entry, since pruning for a given IP only happens when that same IP calls
``is_allowed`` again. The dict grows without bound over the life of the
process.

Fix must not change the limiting semantics for any individual IP (same
window, same max_requests, same retry_after math) — only add eviction.
"""

from __future__ import annotations

import collections
import time

from cloudwright_web.middleware import _RateLimiter


class TestBucketEviction:
    def test_stale_bucket_is_evicted_from_the_dict(self):
        limiter = _RateLimiter(max_requests=5, window_seconds=1)
        limiter.is_allowed("1.1.1.1")
        assert "1.1.1.1" in limiter._buckets

        # Backdate every entry in 1.1.1.1's bucket past the window so the
        # next sweep prunes it to empty.
        limiter._buckets["1.1.1.1"] = collections.deque([time.time() - 5])

        # A completely different IP triggers the sweep; 1.1.1.1 never calls
        # back, which is exactly the churn scenario the finding describes.
        limiter.is_allowed("2.2.2.2")

        assert "1.1.1.1" not in limiter._buckets

    def test_many_one_off_ips_do_not_grow_the_dict_unbounded(self):
        limiter = _RateLimiter(max_requests=5, window_seconds=1)
        for i in range(50):
            limiter.is_allowed(f"10.0.0.{i}")
            # Immediately expire this IP's own entry so it looks like a
            # one-off caller that never returns.
            limiter._buckets[f"10.0.0.{i}"] = collections.deque([time.time() - 5])

        # One more call should sweep and evict all the stale one-off buckets.
        limiter.is_allowed("9.9.9.9")

        stale_remaining = [k for k in limiter._buckets if k.startswith("10.0.0.")]
        assert stale_remaining == []


class TestLimitSemanticsUnchanged:
    """Pin the pre-existing behavior so the eviction fix can't drift it."""

    def test_allows_under_limit(self):
        limiter = _RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            allowed, retry = limiter.is_allowed("1.2.3.4")
            assert allowed is True
            assert retry == 0

    def test_blocks_over_limit(self):
        limiter = _RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("1.2.3.4")

        allowed, retry = limiter.is_allowed("1.2.3.4")
        assert allowed is False
        assert retry > 0

    def test_different_ips_independent(self):
        limiter = _RateLimiter(max_requests=1, window_seconds=60)
        limiter.is_allowed("1.1.1.1")
        allowed_a, _ = limiter.is_allowed("1.1.1.1")
        allowed_b, _ = limiter.is_allowed("2.2.2.2")
        assert allowed_a is False
        assert allowed_b is True

    def test_resets_after_window(self):
        limiter = _RateLimiter(max_requests=2, window_seconds=1)
        limiter.is_allowed("1.2.3.4")
        limiter.is_allowed("1.2.3.4")
        blocked, _ = limiter.is_allowed("1.2.3.4")
        assert blocked is False

        limiter._buckets["1.2.3.4"] = collections.deque([time.time() - 2, time.time() - 2])
        allowed, _ = limiter.is_allowed("1.2.3.4")
        assert allowed is True
