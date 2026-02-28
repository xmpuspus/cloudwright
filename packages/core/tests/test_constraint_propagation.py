"""Tests for constraint propagation in the Architect module."""

from __future__ import annotations

import logging

from cloudwright.architect import _build_constraint_prompt, _post_validate
from cloudwright.spec import ArchSpec, Component, ComponentCost, Constraints, CostEstimate


def _make_spec(components: list[Component]) -> ArchSpec:
    return ArchSpec(name="Test", provider="aws", region="us-east-1", components=components)


class TestBuildConstraintPrompt:
    def test_budget_constraint(self):
        c = Constraints(budget_monthly=500.0)
        prompt = _build_constraint_prompt(c)
        assert "500" in prompt
        assert "HARD LIMIT" in prompt
        assert "MUST NOT exceed" in prompt

    def test_hipaa_compliance(self):
        c = Constraints(compliance=["hipaa"])
        prompt = _build_constraint_prompt(c)
        assert "HIPAA" in prompt
        assert "encryption_at_rest" in prompt
        assert "audit_logging" in prompt
        assert "BAA-eligible" in prompt

    def test_pci_compliance(self):
        c = Constraints(compliance=["pci-dss"])
        prompt = _build_constraint_prompt(c)
        assert "PCI-DSS" in prompt
        assert "WAF" in prompt

    def test_soc2_compliance(self):
        c = Constraints(compliance=["soc2"])
        prompt = _build_constraint_prompt(c)
        assert "SOC2" in prompt

    def test_region_constraint(self):
        c = Constraints(regions=["us-west-2"])
        prompt = _build_constraint_prompt(c)
        assert "us-west-2" in prompt
        assert "ALL components must be in region" in prompt

    def test_high_availability_constraint(self):
        c = Constraints(availability=0.999)
        prompt = _build_constraint_prompt(c)
        assert "multi_az" in prompt
        assert "auto_scaling" in prompt
        assert "load balancer" in prompt

    def test_availability_below_threshold_not_included(self):
        # 99% exactly should not trigger the high-availability block
        c = Constraints(availability=0.99)
        prompt = _build_constraint_prompt(c)
        assert "multi_az" not in prompt

    def test_latency_constraint(self):
        c = Constraints(latency_ms=50.0)
        prompt = _build_constraint_prompt(c)
        assert "50" in prompt
        assert "LATENCY TARGET" in prompt

    def test_data_residency_constraint(self):
        c = Constraints(data_residency=["US", "EU"])
        prompt = _build_constraint_prompt(c)
        assert "DATA RESIDENCY" in prompt
        assert "US" in prompt
        assert "EU" in prompt

    def test_throughput_constraint(self):
        c = Constraints(throughput_rps=10000)
        prompt = _build_constraint_prompt(c)
        assert "THROUGHPUT TARGET" in prompt
        assert "10,000" in prompt

    def test_empty_constraints_returns_empty(self):
        c = Constraints()
        prompt = _build_constraint_prompt(c)
        assert prompt == ""

    def test_all_constraint_types_present(self):
        c = Constraints(
            budget_monthly=1000.0,
            compliance=["hipaa", "soc2"],
            regions=["us-east-1"],
            availability=0.9999,
            latency_ms=100.0,
            data_residency=["US"],
            throughput_rps=5000,
        )
        prompt = _build_constraint_prompt(c)
        assert "HARD LIMIT" in prompt
        assert "HIPAA" in prompt
        assert "SOC2" in prompt
        assert "us-east-1" in prompt
        assert "multi_az" in prompt
        assert "LATENCY TARGET" in prompt
        assert "DATA RESIDENCY" in prompt
        assert "THROUGHPUT TARGET" in prompt


class TestPostValidate:
    def test_hipaa_adds_encryption_to_rds(self):
        comp = Component(id="db", service="rds", provider="aws", label="DB", config={})
        spec = _make_spec([comp])
        constraints = Constraints(compliance=["hipaa"])
        result = _post_validate(spec, constraints)
        db = next(c for c in result.components if c.id == "db")
        assert db.config.get("encryption") is True

    def test_hipaa_adds_encryption_to_s3(self):
        comp = Component(id="store", service="s3", provider="aws", label="Storage", config={})
        spec = _make_spec([comp])
        constraints = Constraints(compliance=["hipaa"])
        result = _post_validate(spec, constraints)
        store = next(c for c in result.components if c.id == "store")
        assert store.config.get("encryption") is True

    def test_hipaa_skips_already_encrypted(self):
        comp = Component(id="db", service="rds", provider="aws", label="DB", config={"encryption": True})
        spec = _make_spec([comp])
        constraints = Constraints(compliance=["hipaa"])
        result = _post_validate(spec, constraints)
        db = next(c for c in result.components if c.id == "db")
        assert db.config.get("encryption") is True

    def test_hipaa_does_not_touch_non_data_stores(self):
        comp = Component(id="api", service="api_gateway", provider="aws", label="API GW", config={})
        spec = _make_spec([comp])
        constraints = Constraints(compliance=["hipaa"])
        result = _post_validate(spec, constraints)
        api = next(c for c in result.components if c.id == "api")
        assert "encryption" not in api.config

    def test_no_constraints_returns_spec_unchanged(self):
        # _post_validate now always applies safe defaults regardless of constraints,
        # so data stores will always get encryption=True
        comp = Component(id="db", service="rds", provider="aws", label="DB", config={})
        spec = _make_spec([comp])
        result = _post_validate(spec, None)
        db = next(c for c in result.components if c.id == "db")
        assert db.config.get("encryption") is True

    def test_budget_warning_when_over_limit(self, caplog):
        comp = Component(id="db", service="rds", provider="aws", label="DB", config={})
        cost = CostEstimate(
            monthly_total=800.0,
            breakdown=[ComponentCost(component_id="db", service="rds", monthly=800.0)],
        )
        spec = _make_spec([comp])
        spec = spec.model_copy(update={"cost_estimate": cost})
        constraints = Constraints(budget_monthly=500.0)
        with caplog.at_level(logging.WARNING, logger="cloudwright.architect"):
            _post_validate(spec, constraints)
        assert any("800" in r.message and "500" in r.message for r in caplog.records)

    def test_no_warning_when_under_budget(self, caplog):
        comp = Component(id="db", service="rds", provider="aws", label="DB", config={})
        cost = CostEstimate(
            monthly_total=300.0,
            breakdown=[ComponentCost(component_id="db", service="rds", monthly=300.0)],
        )
        spec = _make_spec([comp])
        spec = spec.model_copy(update={"cost_estimate": cost})
        constraints = Constraints(budget_monthly=500.0)
        with caplog.at_level(logging.WARNING, logger="cloudwright.architect"):
            _post_validate(spec, constraints)
        assert not any("exceeds budget" in r.message for r in caplog.records)

    def test_multiple_data_stores_all_get_encryption(self):
        comps = [
            Component(id="rds1", service="rds", provider="aws", label="DB", config={}),
            Component(id="s3b", service="s3", provider="aws", label="Bucket", config={}),
            Component(id="cache", service="elasticache", provider="aws", label="Cache", config={}),
        ]
        spec = _make_spec(comps)
        constraints = Constraints(compliance=["hipaa"])
        result = _post_validate(spec, constraints)
        for comp in result.components:
            assert comp.config.get("encryption") is True, f"{comp.id} missing encryption"
