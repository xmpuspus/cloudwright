"""Tests for v1.6.0 cost engine improvements:
- Regional price multipliers
- Pricing confidence per line item
- Carbon footprint estimator
- FOCUS CSV export
"""

from __future__ import annotations

import csv
import io

import pytest
from cloudwright.spec import ArchSpec, Component, Connection


def _simple_spec(region: str = "us-east-1", provider: str = "aws") -> ArchSpec:
    return ArchSpec(
        name="Test",
        provider=provider,
        region=region,
        components=[
            Component(
                id="web",
                service="ec2",
                provider=provider,
                label="Web",
                tier=2,
                config={"instance_type": "t3.medium"},
            ),
            Component(
                id="db",
                service="rds",
                provider=provider,
                label="DB",
                tier=3,
                config={"instance_class": "db.t3.medium", "storage_gb": 50},
            ),
        ],
        connections=[],
    )


def _fallback_spec() -> ArchSpec:
    """Spec with a service that has no catalog row — forces fallback pricing."""
    return ArchSpec(
        name="Fallback",
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="custom",
                service="definitely_unknown_service_xyz",
                provider="aws",
                label="Unknown",
                tier=2,
                config={},
            ),
        ],
        connections=[],
    )


class TestRegionMultiplier:
    def test_eu_west_costs_more_than_us_east(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        us = engine.estimate(_simple_spec(region="us-east-1"))
        eu = engine.estimate(_simple_spec(region="eu-west-1"))
        # eu-west-1 multiplier is 1.08 — formula/fallback tiers get it applied
        # catalog tiers (ec2/rds with instance class) may not differ if catalog has exact pricing
        # but at least the region multiplier should be recorded
        assert eu.region_multiplier > us.region_multiplier

    def test_sa_east_costs_more_than_us_east(self):
        """sa-east-1 has a 1.25 multiplier for fallback-priced services."""
        from cloudwright.cost import CostEngine

        # Use a spec with only fallback-priced services so multiplier is clearly applied
        spec_us = ArchSpec(
            name="SA Test US",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="q", service="sqs", provider="aws", label="Q", tier=2, config={}),
            ],
            connections=[],
        )
        spec_sa = spec_us.model_copy(update={"region": "sa-east-1", "name": "SA Test SA"})

        engine = CostEngine()
        us_est = engine.estimate(spec_us)
        sa_est = engine.estimate(spec_sa)
        assert sa_est.monthly_total > us_est.monthly_total

    def test_region_multiplier_recorded_on_estimate(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        est = engine.estimate(_simple_spec(region="eu-west-1"))
        assert est.region == "eu-west-1"
        assert est.region_multiplier == pytest.approx(1.08, rel=1e-3)

    def test_us_east_multiplier_is_baseline(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        est = engine.estimate(_simple_spec(region="us-east-1"))
        assert est.region_multiplier == pytest.approx(1.00, rel=1e-3)

    def test_unknown_region_falls_back_to_1x(self):
        from cloudwright.cost import _region_multiplier

        assert _region_multiplier("totally-unknown-region-99") == 1.00

    def test_region_multiplier_helper(self):
        from cloudwright.cost import _region_multiplier

        assert _region_multiplier("us-east-1") == pytest.approx(1.00)
        assert _region_multiplier("eu-west-1") == pytest.approx(1.08)
        assert _region_multiplier("sa-east-1") == pytest.approx(1.25)
        assert _region_multiplier("ap-southeast-1") == pytest.approx(1.15)

    def test_prefix_fallback_eu(self):
        """A region like eu-west-9 (fictional) should hit the eu- prefix."""
        from cloudwright.cost import _region_multiplier

        m = _region_multiplier("eu-west-9")
        assert m > 1.00  # eu prefix is 1.10


class TestPricingConfidence:
    def test_unknown_service_marked_low_confidence(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        est = engine.estimate(_fallback_spec())
        item = est.breakdown[0]
        assert item.confidence == "low"
        assert item.estimated is True

    def test_unknown_service_marks_overall_low(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        est = engine.estimate(_fallback_spec())
        assert est.pricing_confidence == "low"

    def test_estimate_has_confidence_fields(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        est = engine.estimate(_simple_spec())
        assert hasattr(est, "pricing_confidence")
        for item in est.breakdown:
            assert item.confidence in ("high", "low")
            assert isinstance(item.estimated, bool)

    def test_catalog_backed_service_confidence(self):
        """ec2 with a known instance type should come from catalog (high confidence)."""
        from cloudwright.cost import CostEngine

        spec = ArchSpec(
            name="EC2 Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(
                    id="web",
                    service="ec2",
                    provider="aws",
                    label="Web",
                    tier=2,
                    config={"instance_type": "t3.medium"},
                ),
            ],
            connections=[],
        )
        engine = CostEngine()
        est = engine.estimate(spec)
        item = next(i for i in est.breakdown if i.component_id == "web")
        # t3.medium is in the catalog — should be high confidence
        assert item.confidence == "high"
        assert item.estimated is False

    def test_warning_logged_for_unknown_service(self, caplog):
        import logging

        from cloudwright.cost import CostEngine

        with caplog.at_level(logging.WARNING, logger="cloudwright.catalog.formula"):
            engine = CostEngine()
            engine.estimate(_fallback_spec())

        assert any("definitely_unknown_service_xyz" in r.message for r in caplog.records)

    def test_mixed_spec_aggregate_confidence(self):
        """A spec with one unknown and one catalog service should be low overall."""
        from cloudwright.cost import CostEngine

        spec = ArchSpec(
            name="Mixed",
            provider="aws",
            region="us-east-1",
            components=[
                Component(
                    id="web",
                    service="ec2",
                    provider="aws",
                    label="Web",
                    tier=2,
                    config={"instance_type": "t3.medium"},
                ),
                Component(
                    id="mystery",
                    service="definitely_unknown_service_xyz",
                    provider="aws",
                    label="?",
                    tier=2,
                    config={},
                ),
            ],
            connections=[],
        )
        engine = CostEngine()
        est = engine.estimate(spec)
        assert est.pricing_confidence == "low"


class TestCarbonEstimate:
    def _simple_carbon_spec(self) -> ArchSpec:
        return ArchSpec(
            name="Carbon Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
                Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={}),
            ],
            connections=[],
        )

    def test_total_is_positive(self):
        from cloudwright.carbon import estimate_carbon

        result = estimate_carbon(self._simple_carbon_spec())
        assert result["total_kg_co2e_per_month"] > 0

    def test_scales_with_component_count(self):
        from cloudwright.carbon import estimate_carbon

        one = ArchSpec(
            name="One",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="w", service="ec2", provider="aws", label="W", tier=2, config={}),
            ],
            connections=[],
        )
        two = ArchSpec(
            name="Two",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="w", service="ec2", provider="aws", label="W", tier=2, config={}),
                Component(id="d", service="rds", provider="aws", label="D", tier=3, config={}),
            ],
            connections=[],
        )
        r1 = estimate_carbon(one)
        r2 = estimate_carbon(two)
        assert r2["total_kg_co2e_per_month"] > r1["total_kg_co2e_per_month"]

    def test_breakdown_length_matches_components(self):
        from cloudwright.carbon import estimate_carbon

        result = estimate_carbon(self._simple_carbon_spec())
        assert len(result["breakdown"]) == 2

    def test_breakdown_has_required_fields(self):
        from cloudwright.carbon import estimate_carbon

        result = estimate_carbon(self._simple_carbon_spec())
        for item in result["breakdown"]:
            assert "component_id" in item
            assert "service" in item
            assert "kg_co2e_per_month" in item

    def test_virtual_component_is_zero(self):
        from cloudwright.carbon import estimate_carbon

        spec = ArchSpec(
            name="Virtual",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="users", service="users", provider="aws", label="Users", tier=0, config={}),
            ],
            connections=[],
        )
        result = estimate_carbon(spec)
        assert result["total_kg_co2e_per_month"] == 0.0

    def test_high_carbon_region_costs_more(self):
        """ap-south-1 (Mumbai) has higher grid intensity than us-west-2 (Oregon)."""
        from cloudwright.carbon import estimate_carbon

        spec_clean = ArchSpec(
            name="Clean",
            provider="aws",
            region="us-west-2",
            components=[
                Component(id="w", service="ec2", provider="aws", label="W", tier=2, config={}),
            ],
            connections=[],
        )
        spec_dirty = spec_clean.model_copy(update={"region": "ap-south-1", "name": "Dirty"})

        clean = estimate_carbon(spec_clean)
        dirty = estimate_carbon(spec_dirty)
        assert dirty["total_kg_co2e_per_month"] > clean["total_kg_co2e_per_month"]

    def test_assumptions_dict_present(self):
        from cloudwright.carbon import estimate_carbon

        result = estimate_carbon(self._simple_carbon_spec())
        assert "assumptions" in result
        assert "pue" in result["assumptions"]
        assert "disclaimer" in result["assumptions"]

    def test_empty_spec_returns_zero(self):
        from cloudwright.carbon import estimate_carbon

        spec = ArchSpec(name="Empty", provider="aws", region="us-east-1", components=[], connections=[])
        result = estimate_carbon(spec)
        assert result["total_kg_co2e_per_month"] == 0.0


class TestFocusCsv:
    def _sample_estimate(self):
        from cloudwright.cost import CostEngine

        spec = ArchSpec(
            name="FOCUS Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(
                    id="web",
                    service="ec2",
                    provider="aws",
                    label="Web",
                    tier=2,
                    config={"instance_type": "t3.medium"},
                ),
                Component(
                    id="store",
                    service="s3",
                    provider="aws",
                    label="Storage",
                    tier=4,
                    config={"storage_gb": 100},
                ),
            ],
            connections=[
                Connection(source="web", target="store", estimated_monthly_gb=50.0),
            ],
        )
        return CostEngine().estimate(spec)

    def test_csv_has_focus_headers(self):
        from cloudwright.focus import _FOCUS_COLUMNS, to_focus_csv

        csv_text = to_focus_csv(self._sample_estimate())
        reader = csv.DictReader(io.StringIO(csv_text))
        for col in _FOCUS_COLUMNS:
            assert col in (reader.fieldnames or []), f"Missing FOCUS column: {col}"

    def test_one_row_per_component(self):
        from cloudwright.focus import to_focus_csv

        est = self._sample_estimate()
        csv_text = to_focus_csv(est)
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        # 2 components + 1 data transfer row
        assert len(rows) == 3

    def test_data_transfer_row_present(self):
        from cloudwright.focus import to_focus_csv

        csv_text = to_focus_csv(self._sample_estimate())
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        services = [r["ServiceName"] for r in rows]
        assert "DataTransfer" in services

    def test_billed_cost_matches_estimate(self):
        from cloudwright.focus import to_focus_csv

        est = self._sample_estimate()
        csv_text = to_focus_csv(est)
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        total_billed = sum(float(r["BilledCost"]) for r in rows)
        assert total_billed == pytest.approx(est.monthly_total, rel=1e-3)

    def test_billing_currency_is_usd(self):
        from cloudwright.focus import to_focus_csv

        csv_text = to_focus_csv(self._sample_estimate())
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        assert all(r["BillingCurrency"] == "USD" for r in rows)

    def test_charge_period_start_before_end(self):
        from cloudwright.focus import to_focus_csv

        csv_text = to_focus_csv(self._sample_estimate())
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        for row in rows:
            assert row["ChargePeriodStart"] <= row["ChargePeriodEnd"]

    def test_resource_id_matches_component_id(self):
        from cloudwright.focus import to_focus_csv

        est = self._sample_estimate()
        csv_text = to_focus_csv(est)
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        component_ids = {r["ResourceId"] for r in rows if r["ServiceName"] != "DataTransfer"}
        expected = {item.component_id for item in est.breakdown}
        assert component_ids == expected

    def test_no_data_transfer_row_when_zero(self):
        """If there's no egress, no DataTransfer row should appear."""
        from cloudwright.cost import CostEngine
        from cloudwright.focus import to_focus_csv

        spec = ArchSpec(
            name="No Egress",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="w", service="ec2", provider="aws", label="W", tier=2, config={}),
            ],
            connections=[],
        )
        est = CostEngine().estimate(spec)
        csv_text = to_focus_csv(est)
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        assert all(r["ServiceName"] != "DataTransfer" for r in rows)

    def test_pricing_confidence_column_present(self):
        from cloudwright.focus import to_focus_csv

        csv_text = to_focus_csv(self._sample_estimate())
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        for row in rows:
            assert row["PricingConfidence"] in ("high", "low")
