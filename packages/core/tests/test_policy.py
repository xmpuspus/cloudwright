import pytest
import yaml
from cloudwright.policy import PolicyEngine, PolicyRule
from cloudwright.spec import ArchSpec, Component, CostEstimate


@pytest.fixture
def sample_spec():
    return ArchSpec(
        name="Test App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web Server",
                tier=2,
                config={"instance_type": "t3.medium"},
            ),
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="Database",
                tier=3,
                config={"engine": "postgres", "storage_encrypted": True},
            ),
            Component(id="cache", service="s3", provider="aws", label="Storage", tier=4),
        ],
    )


@pytest.fixture
def engine():
    return PolicyEngine()


class TestPolicyEngine:
    def test_max_components_pass(self, engine, sample_spec):
        rules = [PolicyRule(name="max-comp", check="max_components", value=10, severity="deny")]
        result = engine.evaluate(sample_spec, rules)
        assert result.passed

    def test_max_components_fail(self, engine, sample_spec):
        rules = [PolicyRule(name="max-comp", check="max_components", value=2, severity="deny")]
        result = engine.evaluate(sample_spec, rules)
        assert not result.passed
        assert result.deny_count == 1

    def test_allowed_providers_pass(self, engine, sample_spec):
        rules = [PolicyRule(name="providers", check="allowed_providers", value=["aws", "gcp"], severity="deny")]
        result = engine.evaluate(sample_spec, rules)
        assert result.passed

    def test_allowed_providers_fail(self, engine, sample_spec):
        rules = [PolicyRule(name="providers", check="allowed_providers", value=["gcp"], severity="deny")]
        result = engine.evaluate(sample_spec, rules)
        assert not result.passed

    def test_allowed_regions_pass(self, engine, sample_spec):
        rules = [PolicyRule(name="regions", check="allowed_regions", value=["us-east-1", "us-west-2"], severity="deny")]
        result = engine.evaluate(sample_spec, rules)
        assert result.passed

    def test_allowed_regions_fail(self, engine, sample_spec):
        rules = [PolicyRule(name="regions", check="allowed_regions", value=["eu-west-1"], severity="deny")]
        result = engine.evaluate(sample_spec, rules)
        assert not result.passed

    def test_no_banned_services_pass(self, engine, sample_spec):
        rules = [PolicyRule(name="banned", check="no_banned_services", value=["dynamodb"], severity="deny")]
        result = engine.evaluate(sample_spec, rules)
        assert result.passed

    def test_no_banned_services_fail(self, engine, sample_spec):
        rules = [PolicyRule(name="banned", check="no_banned_services", value=["ec2"], severity="deny")]
        result = engine.evaluate(sample_spec, rules)
        assert not result.passed

    def test_budget_monthly_pass(self, engine, sample_spec):
        cost = CostEstimate(monthly_total=100.0)
        rules = [PolicyRule(name="budget", check="budget_monthly", value=500, severity="warn")]
        result = engine.evaluate(sample_spec, rules, cost_estimate=cost)
        assert result.passed

    def test_budget_monthly_fail(self, engine, sample_spec):
        cost = CostEstimate(monthly_total=6000.0)
        rules = [PolicyRule(name="budget", check="budget_monthly", value=5000, severity="warn")]
        result = engine.evaluate(sample_spec, rules, cost_estimate=cost)
        assert result.warn_count == 1
        # warn doesn't fail overall
        assert result.passed

    def test_severity_deny_fails_overall(self, engine, sample_spec):
        cost = CostEstimate(monthly_total=6000.0)
        rules = [PolicyRule(name="budget", check="budget_monthly", value=5000, severity="deny")]
        result = engine.evaluate(sample_spec, rules, cost_estimate=cost)
        assert not result.passed
        assert result.deny_count == 1

    def test_unknown_check(self, engine, sample_spec):
        rules = [PolicyRule(name="unknown", check="nonexistent_check", severity="warn")]
        result = engine.evaluate(sample_spec, rules)
        assert not result.results[0].passed
        assert "Unknown check" in result.results[0].message

    def test_load_rules_from_file(self, tmp_path, engine, sample_spec):
        rules_yaml = {
            "rules": [
                {"name": "test-rule", "check": "max_components", "value": 50, "severity": "deny"},
            ]
        }
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(yaml.dump(rules_yaml))

        result = engine.evaluate_from_file(sample_spec, rules_file)
        assert result.passed

    def test_multiple_rules(self, engine, sample_spec):
        rules = [
            PolicyRule(name="max-comp", check="max_components", value=50, severity="deny"),
            PolicyRule(name="providers", check="allowed_providers", value=["aws"], severity="deny"),
            PolicyRule(name="regions", check="allowed_regions", value=["us-east-1"], severity="warn"),
        ]
        result = engine.evaluate(sample_spec, rules)
        assert result.passed
        assert len(result.results) == 3
        assert all(r.passed for r in result.results)

    def test_budget_fails_when_no_cost_estimate(self, engine, sample_spec):
        rules = [PolicyRule(name="budget", check="budget_monthly", value=5000, severity="deny")]
        result = engine.evaluate(sample_spec, rules, cost_estimate=None)
        assert not result.passed
        assert result.deny_count == 1
        failing = [r for r in result.results if not r.passed]
        assert "No cost estimate" in failing[0].message
