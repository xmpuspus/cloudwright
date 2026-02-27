"""Tests for the architecture quality scorer."""

from __future__ import annotations

import json
from pathlib import Path

from cloudwright.spec import ArchSpec, Component, ComponentCost, Connection, Constraints, CostEstimate

TEMPLATES = Path(__file__).parent.parent.parent.parent / "catalog" / "templates"


def _minimal_spec() -> ArchSpec:
    """Single EC2 — intentionally weak on most dimensions."""
    return ArchSpec(
        name="Minimal",
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
            )
        ],
    )


def _secured_spec() -> ArchSpec:
    """Fully hardened spec expected to score well."""
    return ArchSpec(
        name="Hardened",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0, config={}),
            Component(id="lb", service="alb", provider="aws", label="ALB", tier=1, config={}),
            Component(id="waf", service="waf", provider="aws", label="WAF", tier=1, config={}),
            Component(id="auth", service="cognito", provider="aws", label="Auth", tier=1, config={}),
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web",
                tier=2,
                config={"instance_type": "m5.large", "count": 3, "auto_scaling": True},
            ),
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="DB",
                tier=3,
                config={"engine": "postgres", "multi_az": True, "encryption": True},
            ),
            Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=3, config={}),
        ],
        connections=[
            Connection(source="cdn", target="lb", protocol="HTTPS", port=443),
            Connection(source="lb", target="web", protocol="HTTPS", port=443),
            Connection(source="web", target="db", protocol="HTTPS"),
            Connection(source="web", target="cache", protocol="HTTPS"),
        ],
    )


class TestScorerBasics:
    def test_empty_spec_scores_without_error(self):
        from cloudwright.scorer import Scorer

        spec = ArchSpec(name="Empty", provider="aws", region="us-east-1")
        result = Scorer().score(spec)
        assert 0 <= result.overall <= 100
        assert result.grade in ("A", "B", "C", "D", "F")

    def test_dimensions_count_and_weights_sum_to_one(self):
        from cloudwright.scorer import Scorer

        result = Scorer().score(_minimal_spec())
        assert len(result.dimensions) == 5
        total_weight = sum(d.weight for d in result.dimensions)
        assert abs(total_weight - 1.0) < 1e-9

    def test_dimension_names(self):
        from cloudwright.scorer import Scorer

        result = Scorer().score(_minimal_spec())
        names = [d.name for d in result.dimensions]
        assert "Reliability" in names
        assert "Security" in names
        assert "Cost Efficiency" in names
        assert "Compliance" in names
        assert "Complexity" in names

    def test_grade_mapping(self):
        from cloudwright.scorer import Scorer

        scorer = Scorer()
        assert scorer._grade(95) == "A"
        assert scorer._grade(85) == "B"
        assert scorer._grade(75) == "C"
        assert scorer._grade(65) == "D"
        assert scorer._grade(55) == "F"
        assert scorer._grade(90) == "A"
        assert scorer._grade(80) == "B"
        assert scorer._grade(70) == "C"
        assert scorer._grade(60) == "D"

    def test_to_dict_is_json_serializable(self):
        from cloudwright.scorer import Scorer

        result = Scorer().score(_secured_spec())
        d = result.to_dict()
        # Must not raise
        serialized = json.dumps(d)
        parsed = json.loads(serialized)
        assert "overall" in parsed
        assert "grade" in parsed
        assert "dimensions" in parsed
        assert "recommendations" in parsed

    def test_to_dict_structure(self):
        from cloudwright.scorer import Scorer

        result = Scorer().score(_minimal_spec())
        d = result.to_dict()
        assert isinstance(d["overall"], float)
        assert isinstance(d["grade"], str)
        assert len(d["dimensions"]) == 5
        for dim in d["dimensions"]:
            assert "name" in dim
            assert "score" in dim
            assert "weight" in dim
            assert "details" in dim
            assert "recommendations" in dim


class TestScorerScores:
    def test_three_tier_template_scores_in_range(self):
        from cloudwright.scorer import Scorer

        spec = ArchSpec.from_file(TEMPLATES / "three_tier_web.yaml")
        result = Scorer().score(spec)
        assert 30 <= result.overall <= 90

    def test_secured_spec_scores_high(self):
        from cloudwright.scorer import Scorer

        result = Scorer().score(_secured_spec())
        assert result.overall >= 70

    def test_minimal_spec_scores_low(self):
        from cloudwright.scorer import Scorer

        result = Scorer().score(_minimal_spec())
        assert result.overall < 60

    def test_recommendations_populated_for_weak_spec(self):
        from cloudwright.scorer import Scorer

        result = Scorer().score(_minimal_spec())
        assert len(result.recommendations) > 0

    def test_overall_equals_weighted_sum(self):
        from cloudwright.scorer import Scorer

        result = Scorer().score(_secured_spec())
        expected = sum(d.score * d.weight for d in result.dimensions)
        assert abs(result.overall - expected) < 1e-9


class TestCostEfficiency:
    def test_cost_estimate_affects_score(self):
        from cloudwright.scorer import Scorer

        spec_no_cost = _minimal_spec()
        spec_with_cost = _minimal_spec()
        spec_with_cost = spec_with_cost.model_copy(
            update={
                "cost_estimate": CostEstimate(
                    monthly_total=50.0,
                    breakdown=[ComponentCost(component_id="web", service="ec2", monthly=50.0)],
                )
            }
        )

        scorer = Scorer()
        dim_no_cost = scorer._score_cost_efficiency(spec_no_cost)
        dim_with_cost = scorer._score_cost_efficiency(spec_with_cost)

        # With actual cost data we get different scoring path
        assert dim_no_cost.score != dim_with_cost.score or dim_no_cost.details != dim_with_cost.details

    def test_under_budget_boosts_score(self):
        from cloudwright.scorer import Scorer

        spec = _minimal_spec()
        spec = spec.model_copy(
            update={
                "constraints": Constraints(budget_monthly=500.0),
                "cost_estimate": CostEstimate(
                    monthly_total=100.0,
                    breakdown=[ComponentCost(component_id="web", service="ec2", monthly=100.0)],
                ),
            }
        )
        dim = Scorer()._score_cost_efficiency(spec)
        assert dim.score > 60  # base 60 + budget bonus

    def test_over_budget_penalizes_score(self):
        from cloudwright.scorer import Scorer

        spec = _minimal_spec()
        spec = spec.model_copy(
            update={
                "constraints": Constraints(budget_monthly=50.0),
                "cost_estimate": CostEstimate(
                    monthly_total=500.0,
                    breakdown=[ComponentCost(component_id="web", service="ec2", monthly=500.0)],
                ),
            }
        )
        dim = Scorer()._score_cost_efficiency(spec)
        # base 60 - 20 budget penalty - 10 dominance penalty = 30
        assert dim.score < 60


class TestDimensionDetails:
    def test_reliability_multi_az_detected(self):
        from cloudwright.scorer import Scorer

        spec = ArchSpec(
            name="HA",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="db", service="rds", provider="aws", label="DB", config={"multi_az": True}),
                Component(id="lb", service="alb", provider="aws", label="LB", config={}),
            ],
        )
        dim = Scorer()._score_reliability(spec)
        assert any("Multi-AZ" in d for d in dim.details)

    def test_security_waf_detected(self):
        from cloudwright.scorer import Scorer

        spec = ArchSpec(
            name="Waf",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="waf", service="waf", provider="aws", label="WAF", config={}),
            ],
        )
        dim = Scorer()._score_security(spec)
        assert any("WAF" in d for d in dim.details)

    def test_complexity_penalizes_too_many_components(self):
        from cloudwright.scorer import Scorer

        comps = [Component(id=f"svc{i}", service="ec2", provider="aws", label=f"S{i}", config={}) for i in range(20)]
        spec = ArchSpec(name="Bloated", provider="aws", region="us-east-1", components=comps)
        dim = Scorer()._score_complexity(spec)
        assert dim.score < 80
