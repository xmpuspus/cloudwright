"""Tests for cloudwright.remediation — no real LLM, cloud, or terraform calls.

The plan step shells out to terraform/tofu (slow + network), so these tests use
skip_plan=True or monkeypatch the planner; one fast path exercises the
binary-absent branch directly.
"""

from __future__ import annotations

from cloudwright.remediation import remediate
from cloudwright.spec import ArchSpec, Component, Connection


def _small_spec() -> ArchSpec:
    return ArchSpec(
        name="Small",
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="web", service="ec2", provider="aws", label="Web", tier=2, config={"instance_type": "t3.micro"}
            ),
        ],
    )


def _large_spec() -> ArchSpec:
    return ArchSpec(
        name="Large",
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web",
                tier=2,
                config={"instance_type": "m5.large", "count": 3},
            ),
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="DB",
                tier=3,
                config={
                    "engine": "postgres",
                    "instance_class": "db.r5.large",
                    "multi_az": True,
                    "allocated_storage": 500,
                },
            ),
            Component(
                id="cache",
                service="elasticache",
                provider="aws",
                label="Cache",
                tier=3,
                config={"node_type": "cache.r5.large", "engine": "redis"},
            ),
        ],
        connections=[
            Connection(source="web", target="db", label="SQL", protocol="TCP", port=5432),
            Connection(source="web", target="cache", label="Redis", protocol="TCP", port=6379),
        ],
    )


def test_remediate_returns_required_keys():
    result = remediate(_small_spec(), _large_spec(), skip_plan=True)
    assert {"drift", "cost_delta", "quality_delta", "plan", "summary"} <= set(result)


def test_remediate_drift_reflects_differences():
    result = remediate(_small_spec(), _large_spec(), skip_plan=True)
    assert "add" in {item["change"] for item in result["drift"]}


def test_remediate_cost_delta_positive_for_larger_desired():
    cd = remediate(_small_spec(), _large_spec(), skip_plan=True)["cost_delta"]
    assert cd["desired"] > cd["current"]
    assert cd["delta"] > 0
    assert cd["currency"] == "USD"


def test_remediate_quality_delta_keys():
    qd = remediate(_small_spec(), _large_spec(), skip_plan=True)["quality_delta"]
    assert {"current", "desired", "delta", "current_grade", "desired_grade"} <= set(qd)


def test_remediate_plan_keys_with_mocked_planner(monkeypatch):
    from cloudwright import planner
    from cloudwright.planner import PlanResult

    stub = PlanResult(tool="terraform", available=True, validated=True, plan_ran=False, ok=True, messages=["stub"])
    monkeypatch.setattr(planner, "plan_terraform", lambda spec, **k: stub)
    plan = remediate(_small_spec(), _large_spec())["plan"]
    assert {"tool", "available", "validated", "ok", "messages"} <= set(plan)
    assert plan["validated"] is True


def test_remediate_no_raise_when_terraform_absent(monkeypatch):
    # binary-absent branch is fast (no subprocess); plan reflects unavailability.
    import shutil

    original = shutil.which

    def patched_which(name, *a, **k):
        if name in ("terraform", "tofu"):
            return None
        return original(name, *a, **k)

    monkeypatch.setattr(shutil, "which", patched_which)
    result = remediate(_small_spec(), _large_spec())
    assert result["plan"]["available"] is False
    assert result["summary"]


def test_remediate_identical_specs_no_drift():
    spec = _small_spec()
    result = remediate(spec, spec, skip_plan=True)
    assert result["drift"] == []
    assert result["cost_delta"]["delta"] == 0.0


def test_remediate_summary_is_string():
    result = remediate(_small_spec(), _large_spec(), skip_plan=True)
    assert isinstance(result["summary"], str) and result["summary"]
