"""Cost-credibility tests (July 2026 audit).

Covers four defects verified in the audit:
1. CostEstimate.as_of stamped today's date on stale (Feb 2026) catalog pricing.
2. Cross-provider Alternative dropped the confidence signal entirely.
3. Region-aware pricing ignored real per-region catalog rows in favor of a
   static multiplier, even where the catalog has genuine regional data.
4. Aggregate pricing_confidence was binary (high/low) with no ratio detail.
"""

from __future__ import annotations

from datetime import date

import pytest
from cloudwright.catalog import Catalog
from cloudwright.cost import CostEngine
from cloudwright.spec import ArchSpec, Component


def _ec2_spec(region: str = "us-east-1", instance_type: str = "t3.medium") -> ArchSpec:
    return ArchSpec(
        name="EC2 Only",
        provider="aws",
        region=region,
        components=[
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web",
                tier=2,
                config={"instance_type": instance_type},
            ),
        ],
        connections=[],
    )


def _rds_spec(region: str = "us-east-1") -> ArchSpec:
    return ArchSpec(
        name="RDS Only",
        provider="aws",
        region=region,
        components=[
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="DB",
                tier=3,
                config={"instance_class": "db.t3.medium", "storage_gb": 50},
            ),
        ],
        connections=[],
    )


def _mixed_spec() -> ArchSpec:
    """One catalog-backed component, one formula/fallback component."""
    return ArchSpec(
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


class TestPricesAsOfReflectsCatalogRefresh:
    def test_as_of_matches_catalog_refresh_not_today(self):
        engine = CostEngine()
        refresh_date = engine.catalog.get_catalog_refresh_date()
        assert refresh_date, "bundled catalog.db must carry catalog_metadata rows"

        est = engine.estimate(_ec2_spec())
        assert est.as_of == refresh_date
        # The bundled catalog was refreshed in Feb 2026; today (test run date) is later.
        assert est.as_of != date.today().isoformat()

    def test_prices_as_of_field_present_and_matches_as_of(self):
        engine = CostEngine()
        est = engine.estimate(_ec2_spec())
        assert est.prices_as_of == est.as_of

    def test_estimated_on_is_todays_date(self):
        engine = CostEngine()
        est = engine.estimate(_ec2_spec())
        assert est.estimated_on == date.today().isoformat()

    def test_catalog_refresh_date_none_when_metadata_empty(self, tmp_path):
        """A fresh catalog with no refresh history reports no fabricated freshness."""
        empty_db = tmp_path / "empty_catalog.db"
        catalog = Catalog(db_path=empty_db)
        assert catalog.get_catalog_refresh_date() is None

    def test_as_of_falls_back_to_today_when_catalog_has_no_metadata(self, tmp_path):
        """Without any catalog_metadata, as_of should still be populated (fallback to today)
        rather than left blank — it just can't claim a real refresh date it doesn't have.
        """
        empty_db = tmp_path / "empty_catalog2.db"
        catalog = Catalog(db_path=empty_db)
        engine = CostEngine(catalog=catalog)
        est = engine.estimate(_ec2_spec())
        assert est.as_of == date.today().isoformat()
        assert est.prices_as_of is None


class TestAlternativeCarriesConfidence:
    def test_compare_providers_alternative_has_confidence(self):
        engine = CostEngine()
        spec = _ec2_spec()
        alts = engine.compare_providers(spec, ["gcp"])
        assert len(alts) == 1
        alt = alts[0]
        assert alt.pricing_confidence in ("high", "medium", "low")
        assert "/" in alt.pricing_confidence_detail

    def test_alternative_model_has_confidence_fields_with_defaults(self):
        from cloudwright.spec import Alternative

        alt = Alternative(provider="gcp", monthly_total=100.0)
        assert hasattr(alt, "pricing_confidence")
        assert hasattr(alt, "pricing_confidence_detail")

    def test_alternative_confidence_matches_its_own_estimate(self):
        """The Alternative's confidence should reflect the alt spec's own cost
        estimate, not just copy the origin spec's confidence.
        """
        engine = CostEngine()
        spec = _mixed_spec()
        alts = engine.compare_providers(spec, ["gcp"])
        alt = alts[0]
        alt_estimate = engine.estimate(alt.spec)
        assert alt.pricing_confidence == alt_estimate.pricing_confidence
        assert alt.pricing_confidence_detail == alt_estimate.pricing_confidence_detail


class TestRegionAwarePricing:
    def test_real_regional_row_used_when_available(self):
        """t3.medium has a genuine aws:eu-west-1 pricing row in the catalog —
        the estimate should use it directly rather than the static multiplier.
        """
        catalog = Catalog()
        real_hourly = catalog.get_instance_price_for_region("t3.medium", "aws", "eu-west-1")
        assert real_hourly is not None, "expected a real eu-west-1 catalog row for t3.medium"

        engine = CostEngine(catalog=catalog)
        est = engine.estimate(_ec2_spec(region="eu-west-1"))
        item = est.breakdown[0]

        expected_monthly = round(real_hourly * 730, 2)
        assert item.monthly == pytest.approx(expected_monthly)
        assert item.confidence == "high"

        # Sanity: the real regional price must differ from a naive baseline*multiplier
        # guess, proving the test actually exercises the regional-row path.
        baseline_hourly = catalog.get_instance_price_for_region("t3.medium", "aws", "us-east-1")
        naive_guess = round(baseline_hourly * 730 * 1.08, 2)
        assert expected_monthly != naive_guess

    def test_multiplier_downgrades_confidence_when_no_regional_row(self):
        """RDS pricing has no per-region rows in the catalog schema at all, so any
        non-baseline region must fall back to the static multiplier — and that
        fallback must not be reported as high confidence.
        """
        engine = CostEngine()
        est = engine.estimate(_rds_spec(region="eu-west-1"))
        item = est.breakdown[0]
        assert item.confidence == "medium"
        assert item.estimated is False  # still catalog-derived, just region-rescaled
        # A medium-confidence, region-rescaled line item is not a formula/fallback
        # guess, so it must not flip the legacy binary aggregate to "low".
        assert est.pricing_confidence == "high"

    def test_baseline_region_stays_high_confidence(self):
        engine = CostEngine()
        est = engine.estimate(_rds_spec(region="us-east-1"))
        item = est.breakdown[0]
        assert item.confidence == "high"

    def test_compute_instance_without_regional_row_falls_back_to_multiplier(self):
        """A region with no seeded pricing rows at all (e.g. sa-east-1) must fall
        back to the baseline * multiplier estimate and be marked medium confidence.
        """
        catalog = Catalog()
        assert catalog.get_instance_price_for_region("t3.medium", "aws", "sa-east-1") is None

        engine = CostEngine(catalog=catalog)
        est = engine.estimate(_ec2_spec(region="sa-east-1"))
        item = est.breakdown[0]
        assert item.confidence == "medium"


class TestPricingConfidenceDetailRatio:
    def test_ratio_detail_present_for_mixed_spec(self):
        engine = CostEngine()
        est = engine.estimate(_mixed_spec())
        assert est.pricing_confidence_detail == "1/2 line items catalog-backed"

    def test_ratio_detail_all_catalog_backed(self):
        engine = CostEngine()
        est = engine.estimate(_ec2_spec())
        assert est.pricing_confidence_detail == "1/1 line items catalog-backed"

    def test_ratio_detail_none_catalog_backed(self):
        engine = CostEngine()
        spec = ArchSpec(
            name="All Unknown",
            provider="aws",
            region="us-east-1",
            components=[
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
        est = engine.estimate(spec)
        assert est.pricing_confidence_detail == "0/1 line items catalog-backed"

    def test_legacy_pricing_confidence_field_still_binary(self):
        """Back-compat: the old aggregate field stays high/low even though
        per-line confidence now has a medium tier.
        """
        engine = CostEngine()
        est = engine.estimate(_mixed_spec())
        assert est.pricing_confidence in ("high", "low")
        assert est.pricing_confidence == "low"

        est_clean = engine.estimate(_ec2_spec(region="eu-west-1"))
        # eu-west-1 with a real catalog row is still fully catalog-backed —
        # a medium-confidence *region* estimate is not a formula/fallback estimate,
        # so the legacy aggregate should remain "high".
        assert est_clean.pricing_confidence == "high"
