"""Tests for the cost engine."""

import pytest
from cloudwright.spec import ArchSpec, Component, Connection


def _sample_spec() -> ArchSpec:
    return ArchSpec(
        name="Cost Test",
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
                id="db",
                service="rds",
                provider="aws",
                label="DB",
                tier=3,
                config={"instance_class": "db.t3.medium", "engine": "postgres", "storage_gb": 100},
            ),
            Component(
                id="storage",
                service="s3",
                provider="aws",
                label="Storage",
                tier=4,
                config={"storage_gb": 100},
            ),
        ],
        connections=[
            Connection(source="web", target="db"),
            Connection(source="web", target="storage"),
        ],
    )


class TestCostEngine:
    def test_estimate_returns_cost(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        estimate = engine.estimate(_sample_spec())
        assert estimate.monthly_total > 0
        assert len(estimate.breakdown) == 3
        assert estimate.currency == "USD"

    def test_each_component_has_cost(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        estimate = engine.estimate(_sample_spec())
        for item in estimate.breakdown:
            assert item.monthly >= 0
            assert item.component_id
            assert item.service

    def test_total_equals_sum(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        estimate = engine.estimate(_sample_spec())
        component_sum = sum(item.monthly for item in estimate.breakdown)
        # Total includes data transfer too
        assert estimate.monthly_total == pytest.approx(component_sum + estimate.data_transfer_monthly, abs=0.01)

    def test_empty_spec(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        spec = ArchSpec(name="Empty", provider="aws", region="us-east-1", components=[], connections=[])
        estimate = engine.estimate(spec)
        assert estimate.monthly_total == 0.0


class TestPricingTiers:
    def test_on_demand_is_default(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        estimate = engine.estimate(_sample_spec())
        assert estimate.monthly_total > 0

    def test_reserved_1yr_cheaper_than_on_demand(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        on_demand = engine.estimate(_sample_spec(), pricing_tier="on_demand")
        reserved = engine.estimate(_sample_spec(), pricing_tier="reserved_1yr")
        assert reserved.monthly_total < on_demand.monthly_total

    def test_reserved_3yr_cheaper_than_1yr(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        one_yr = engine.estimate(_sample_spec(), pricing_tier="reserved_1yr")
        three_yr = engine.estimate(_sample_spec(), pricing_tier="reserved_3yr")
        assert three_yr.monthly_total < one_yr.monthly_total

    def test_spot_cheapest(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        on_demand = engine.estimate(_sample_spec(), pricing_tier="on_demand")
        spot = engine.estimate(_sample_spec(), pricing_tier="spot")
        assert spot.monthly_total < on_demand.monthly_total

    def test_unknown_tier_falls_back_to_on_demand(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        on_demand = engine.estimate(_sample_spec(), pricing_tier="on_demand")
        unknown = engine.estimate(_sample_spec(), pricing_tier="nonexistent_tier")
        assert unknown.monthly_total == on_demand.monthly_total


class TestDataTransferCost:
    def test_no_transfer_when_no_gb_specified(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        estimate = engine.estimate(_sample_spec())
        assert estimate.data_transfer_monthly == 0.0

    def test_transfer_cost_with_estimated_gb(self):
        from cloudwright.cost import CostEngine

        spec = ArchSpec(
            name="Transfer Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0, config={}),
                Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
            ],
            connections=[
                Connection(source="cdn", target="web", estimated_monthly_gb=500.0),
            ],
        )
        engine = CostEngine()
        estimate = engine.estimate(spec)
        assert estimate.data_transfer_monthly > 0

    def test_cross_provider_transfer_costs_more(self):
        from cloudwright.cost import CostEngine

        same_provider = ArchSpec(
            name="Same",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="a", service="s3", provider="aws", label="A", tier=4, config={}),
                Component(id="b", service="ec2", provider="aws", label="B", tier=2, config={}),
            ],
            connections=[Connection(source="a", target="b", estimated_monthly_gb=100.0)],
        )
        cross_provider = ArchSpec(
            name="Cross",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="a", service="s3", provider="aws", label="A", tier=4, config={}),
                Component(id="b", service="compute_engine", provider="gcp", label="B", tier=2, config={}),
            ],
            connections=[Connection(source="a", target="b", estimated_monthly_gb=100.0)],
        )
        engine = CostEngine()
        same_est = engine.estimate(same_provider)
        cross_est = engine.estimate(cross_provider)
        assert cross_est.data_transfer_monthly > same_est.data_transfer_monthly

    def test_data_transfer_included_in_total(self):
        from cloudwright.cost import CostEngine

        spec = ArchSpec(
            name="Transfer Total",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="s", service="s3", provider="aws", label="S3", tier=4, config={}),
                Component(id="w", service="ec2", provider="aws", label="Web", tier=2, config={}),
            ],
            connections=[Connection(source="s", target="w", estimated_monthly_gb=1000.0)],
        )
        engine = CostEngine()
        estimate = engine.estimate(spec)
        component_sum = sum(c.monthly for c in estimate.breakdown)
        assert estimate.monthly_total == pytest.approx(component_sum + estimate.data_transfer_monthly, abs=0.01)
        assert estimate.data_transfer_monthly > 0

    def test_estimate_has_data_transfer_field(self):
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        estimate = engine.estimate(_sample_spec())
        assert hasattr(estimate, "data_transfer_monthly")
