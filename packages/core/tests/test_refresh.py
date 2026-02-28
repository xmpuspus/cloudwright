"""Tests for the catalog refresh pipeline.

All adapter calls are mocked — no network access required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from cloudwright.adapters import InstancePrice, ManagedServicePrice
from cloudwright.catalog.refresh import (
    RefreshResult,
    RefreshSummary,
    _load_adapter,
    refresh_catalog,
)

# Fixture helpers


def _fake_instances(provider: str, count: int = 3) -> list[InstancePrice]:
    return [
        InstancePrice(
            instance_type=f"{provider}-inst-{i}",
            region="us-east-1",
            vcpus=2 * (i + 1),
            memory_gb=4.0 * (i + 1),
            price_per_hour=0.05 * (i + 1),
            price_type="on_demand",
            os="linux",
        )
        for i in range(count)
    ]


def _fake_managed(service: str, count: int = 2) -> list[ManagedServicePrice]:
    return [
        ManagedServicePrice(
            service=service,
            tier_name=f"tier-{i}",
            price_per_hour=0.01 * (i + 1),
            price_per_month=round(0.01 * (i + 1) * 730, 2),
            description=f"{service} tier {i}",
        )
        for i in range(count)
    ]


def _mock_adapter(provider: str, instance_count: int = 3, service_count: int = 2):
    """Build a mock PricingAdapter for the given provider."""
    adapter = MagicMock()
    adapter.provider = provider
    adapter.fetch_instance_pricing.return_value = iter(_fake_instances(provider, instance_count))
    adapter.supported_managed_services.return_value = ["svc_a", "svc_b"]
    adapter.fetch_managed_service_pricing.side_effect = lambda svc, region: _fake_managed(svc, service_count)
    return adapter


# RefreshResult / RefreshSummary unit tests


class TestRefreshDataclasses:
    def test_result_defaults(self):
        r = RefreshResult(provider="aws")
        assert r.instances_fetched == 0
        assert r.managed_services_fetched == 0
        assert r.errors == []
        assert r.dry_run is False

    def test_summary_total_fetched(self):
        s = RefreshSummary(
            results=[
                RefreshResult(provider="aws", instances_fetched=10, managed_services_fetched=5),
                RefreshResult(provider="gcp", instances_fetched=8, managed_services_fetched=3),
            ]
        )
        assert s.total_fetched == 26

    def test_summary_total_errors(self):
        s = RefreshSummary(
            results=[
                RefreshResult(provider="aws", errors=["e1", "e2"]),
                RefreshResult(provider="gcp", errors=["e3"]),
            ]
        )
        assert s.total_errors == 3

    def test_summary_empty(self):
        s = RefreshSummary()
        assert s.total_fetched == 0
        assert s.total_errors == 0


# _load_adapter


class TestLoadAdapter:
    def test_load_aws(self):
        from cloudwright.adapters.aws import AWSPricingAdapter

        adapter = _load_adapter("aws")
        assert isinstance(adapter, AWSPricingAdapter)

    def test_load_gcp(self):
        from cloudwright.adapters.gcp import GCPPricingAdapter

        adapter = _load_adapter("gcp")
        assert isinstance(adapter, GCPPricingAdapter)

    def test_load_azure(self):
        from cloudwright.adapters.azure import AzurePricingAdapter

        adapter = _load_adapter("azure")
        assert isinstance(adapter, AzurePricingAdapter)

    def test_load_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            _load_adapter("alibaba")


# refresh_catalog — dry run (no DB writes)


class TestRefreshDryRun:
    def _run_dry(self, provider=None, category=None):
        mock_aws = _mock_adapter("aws")
        mock_gcp = _mock_adapter("gcp")
        mock_azure = _mock_adapter("azure")

        def fake_load(p):
            return {"aws": mock_aws, "gcp": mock_gcp, "azure": mock_azure}[p]

        with patch("cloudwright.catalog.refresh._load_adapter", side_effect=fake_load):
            return refresh_catalog(provider=provider, category=category, dry_run=True)

    def test_all_providers_returns_three_results(self):
        summary = self._run_dry()
        assert len(summary.results) == 3
        providers = {r.provider for r in summary.results}
        assert providers == {"aws", "gcp", "azure"}

    def test_single_provider(self):
        summary = self._run_dry(provider="aws")
        assert len(summary.results) == 1
        assert summary.results[0].provider == "aws"

    def test_instances_fetched(self):
        summary = self._run_dry(provider="aws")
        assert summary.results[0].instances_fetched == 3

    def test_managed_fetched(self):
        summary = self._run_dry(provider="aws")
        # 2 services * 2 tiers each = 4
        assert summary.results[0].managed_services_fetched == 4

    def test_no_errors_on_success(self):
        summary = self._run_dry()
        assert summary.total_errors == 0

    def test_total_fetched_across_providers(self):
        summary = self._run_dry()
        # 3 providers * (3 instances + 4 managed) = 21
        assert summary.total_fetched == 21

    def test_dry_run_flag_propagated(self):
        summary = self._run_dry()
        assert all(r.dry_run for r in summary.results)

    def test_category_compute_skips_managed(self):
        summary = self._run_dry(provider="aws", category="compute")
        r = summary.results[0]
        assert r.instances_fetched == 3
        assert r.managed_services_fetched == 0


# refresh_catalog — error handling


class TestRefreshErrorHandling:
    def test_adapter_load_failure(self):
        with patch("cloudwright.catalog.refresh._load_adapter", side_effect=RuntimeError("boom")):
            summary = refresh_catalog(provider="aws", dry_run=True)
        assert len(summary.results) == 1
        assert summary.total_errors == 1
        assert "boom" in summary.results[0].errors[0]

    def test_instance_fetch_error_captured(self):
        adapter = _mock_adapter("aws")
        adapter.fetch_instance_pricing.side_effect = ConnectionError("timeout")

        with patch("cloudwright.catalog.refresh._load_adapter", return_value=adapter):
            summary = refresh_catalog(provider="aws", dry_run=True)

        r = summary.results[0]
        assert r.instances_fetched == 0
        assert any("timeout" in e for e in r.errors)
        # Managed services should still work
        assert r.managed_services_fetched == 4

    def test_managed_service_partial_error(self):
        adapter = _mock_adapter("aws")
        call_count = 0

        def flaky_fetch(svc, region):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("flaky")
            return _fake_managed(svc, 2)

        adapter.fetch_managed_service_pricing.side_effect = flaky_fetch

        with patch("cloudwright.catalog.refresh._load_adapter", return_value=adapter):
            summary = refresh_catalog(provider="aws", dry_run=True)

        r = summary.results[0]
        # One service failed, one succeeded (2 tiers)
        assert r.managed_services_fetched == 2
        assert len(r.errors) == 1
        assert "flaky" in r.errors[0]

    def test_all_providers_one_fails(self):
        mock_aws = _mock_adapter("aws")
        mock_gcp = _mock_adapter("gcp")

        def fake_load(p):
            if p == "azure":
                raise RuntimeError("no azure SDK")
            return {"aws": mock_aws, "gcp": mock_gcp}[p]

        with patch("cloudwright.catalog.refresh._load_adapter", side_effect=fake_load):
            summary = refresh_catalog(dry_run=True)

        assert len(summary.results) == 3
        azure_result = next(r for r in summary.results if r.provider == "azure")
        assert len(azure_result.errors) == 1
        aws_result = next(r for r in summary.results if r.provider == "aws")
        assert aws_result.instances_fetched == 3


# refresh_catalog — DB writes (non-dry-run with temp DB)


class TestRefreshWritesToDB:
    def test_upserts_instances_to_catalog(self, tmp_path):
        from cloudwright.catalog.store import Catalog

        db_path = tmp_path / "test_catalog.db"
        adapter = _mock_adapter("aws", instance_count=2, service_count=0)
        adapter.supported_managed_services.return_value = []

        # Baseline: count before refresh to handle pre-seeded DBs
        catalog = Catalog(db_path)
        with catalog._connect() as conn:
            before = conn.execute("SELECT COUNT(*) FROM instance_types WHERE id LIKE 'aws:aws-inst-%'").fetchone()[0]

        def fake_load(p):
            return adapter

        with patch("cloudwright.catalog.refresh._load_adapter", side_effect=fake_load):
            summary = refresh_catalog(provider="aws", dry_run=False, _db_path=db_path)

        assert summary.results[0].instances_fetched == 2

        with catalog._connect() as conn:
            after = conn.execute("SELECT COUNT(*) FROM instance_types WHERE id LIKE 'aws:aws-inst-%'").fetchone()[0]
            assert after - before == 2
            price_count = conn.execute(
                "SELECT COUNT(*) FROM pricing WHERE instance_type_id LIKE 'aws:aws-inst-%'"
            ).fetchone()[0]
            assert price_count >= 2

    def test_upserts_managed_to_catalog(self, tmp_path):
        from cloudwright.catalog.store import Catalog

        db_path = tmp_path / "test_catalog.db"
        adapter = _mock_adapter("aws", instance_count=0, service_count=2)
        adapter.fetch_instance_pricing.return_value = iter([])

        # Baseline: count before refresh
        catalog = Catalog(db_path)
        with catalog._connect() as conn:
            before = conn.execute("SELECT COUNT(*) FROM managed_services WHERE id LIKE 'aws:svc_%'").fetchone()[0]

        def fake_load(p):
            return adapter

        with patch("cloudwright.catalog.refresh._load_adapter", side_effect=fake_load):
            summary = refresh_catalog(provider="aws", dry_run=False, _db_path=db_path)

        assert summary.results[0].managed_services_fetched == 4

        with catalog._connect() as conn:
            after = conn.execute("SELECT COUNT(*) FROM managed_services WHERE id LIKE 'aws:svc_%'").fetchone()[0]
            assert after - before == 4
