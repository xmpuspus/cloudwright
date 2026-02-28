"""Tests for pricing formula functions."""

from cloudwright.catalog.formula import (
    PRICING_FORMULAS,
    default_managed_price,
    fixed_plus_request,
    per_gb,
    per_gb_hour,
    per_hour,
    per_mau,
    per_node_hour,
    per_request,
    per_shard_hour,
    per_tb_query,
    per_zone,
)


class TestPricingFormulas:
    def test_per_hour_basic(self):
        result = per_hour({"price_per_hour": 0.10, "count": 1})
        assert result == 73.0  # 0.10 * 730

    def test_per_hour_with_count(self):
        result = per_hour({"price_per_hour": 0.10, "count": 3})
        assert result == 219.0

    def test_per_request_lambda(self):
        result = per_request({"monthly_requests": 1_000_000, "avg_duration_ms": 200, "memory_mb": 512})
        assert result > 0

    def test_per_gb_s3(self):
        result = per_gb({"storage_gb": 100}, base_rate=0.023)
        assert result == 2.3

    def test_per_gb_hour_cache(self):
        result = per_gb_hour({"memory_gb": 4.0}, base_rate=0.049)
        assert result > 0

    def test_per_zone_dns(self):
        result = per_zone({"hosted_zones": 1, "monthly_queries": 1_000_000})
        assert result > 0

    def test_fixed_plus_request_waf(self):
        result = fixed_plus_request({"rules": 5, "monthly_requests": 10_000_000})
        assert result > 0

    def test_per_mau_free_tier(self):
        result = per_mau({"monthly_active_users": 10_000})
        assert result == 0.0

    def test_per_mau_above_free(self):
        result = per_mau({"monthly_active_users": 100_000})
        assert result > 0

    def test_per_shard_hour(self):
        result = per_shard_hour({"shards": 2})
        assert result > 0

    def test_per_tb_query(self):
        result = per_tb_query({"monthly_query_tb": 1.0, "storage_gb": 100})
        assert result > 0

    def test_per_node_hour(self):
        result = per_node_hour({"num_nodes": 2, "price_per_hour": 0.25, "storage_gb": 100})
        assert result > 0

    def test_all_formulas_registered(self):
        assert len(PRICING_FORMULAS) == 10
        for name, fn in PRICING_FORMULAS.items():
            assert callable(fn)

    def test_default_managed_price_known(self):
        assert default_managed_price("rds", {}) == 200.0
        assert default_managed_price("lambda", {}) == 15.0

    def test_default_managed_price_unknown(self):
        assert default_managed_price("nonexistent", {}) == 10.0
