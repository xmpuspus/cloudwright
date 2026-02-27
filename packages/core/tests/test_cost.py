"""Tests for the cost engine."""

import pytest
from silmaril.spec import ArchSpec, Component, Connection


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
        from silmaril.cost import CostEngine

        engine = CostEngine()
        estimate = engine.estimate(_sample_spec())
        assert estimate.monthly_total > 0
        assert len(estimate.breakdown) == 3
        assert estimate.currency == "USD"

    def test_each_component_has_cost(self):
        from silmaril.cost import CostEngine

        engine = CostEngine()
        estimate = engine.estimate(_sample_spec())
        for item in estimate.breakdown:
            assert item.monthly >= 0
            assert item.component_id
            assert item.service

    def test_total_equals_sum(self):
        from silmaril.cost import CostEngine

        engine = CostEngine()
        estimate = engine.estimate(_sample_spec())
        component_sum = sum(item.monthly for item in estimate.breakdown)
        assert estimate.monthly_total == pytest.approx(component_sum, abs=0.01)

    def test_empty_spec(self):
        from silmaril.cost import CostEngine

        engine = CostEngine()
        spec = ArchSpec(name="Empty", provider="aws", region="us-east-1", components=[], connections=[])
        estimate = engine.estimate(spec)
        assert estimate.monthly_total == 0.0
