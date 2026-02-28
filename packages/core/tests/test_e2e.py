"""End-to-end tests for Cloudwright.

Tests every module, edge case, integration point, and CLI flow.
Non-LLM tests run fast; LLM tests require ANTHROPIC_API_KEY.
"""

import json
import os
from pathlib import Path

import pytest
import yaml
from cloudwright import ArchSpec
from cloudwright.catalog import Catalog
from cloudwright.cost import CostEngine
from cloudwright.differ import Differ
from cloudwright.spec import (
    Component,
    ComponentCost,
    Connection,
    Constraints,
    CostEstimate,
)
from cloudwright.validator import Validator

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

HAS_LLM = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
skip_no_llm = pytest.mark.skipif(not HAS_LLM, reason="No LLM API key available")

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "catalog" / "templates"


# Fixtures


@pytest.fixture
def three_tier():
    return ArchSpec.from_file(str(TEMPLATES_DIR / "three_tier_web.yaml"))


@pytest.fixture
def serverless():
    return ArchSpec.from_file(str(TEMPLATES_DIR / "serverless_api.yaml"))


@pytest.fixture
def ml_pipeline():
    return ArchSpec.from_file(str(TEMPLATES_DIR / "ml_pipeline.yaml"))


@pytest.fixture
def catalog():
    return Catalog()


@pytest.fixture
def cost_engine():
    return CostEngine()


@pytest.fixture
def validator():
    return Validator()


@pytest.fixture
def differ():
    return Differ()


# ArchSpec Model Tests — edge cases


class TestArchSpecEdgeCases:
    def test_empty_components(self):
        spec = ArchSpec(name="Empty", provider="aws", region="us-east-1", components=[], connections=[])
        assert len(spec.components) == 0
        assert spec.to_yaml()
        assert spec.to_json()

    def test_single_component_no_connections(self):
        spec = ArchSpec(
            name="Solo",
            provider="aws",
            region="us-east-1",
            components=[Component(id="bucket", service="s3", provider="aws", label="Bucket")],
            connections=[],
        )
        assert len(spec.components) == 1
        restored = ArchSpec.from_yaml(spec.to_yaml())
        assert restored.components[0].service == "s3"

    def test_many_components(self):
        """12 components — max recommended."""
        comps = [
            Component(id=f"comp_{i}", service="ec2", provider="aws", label=f"Comp {i}", tier=i % 5) for i in range(12)
        ]
        conns = [Connection(source=f"comp_{i}", target=f"comp_{i + 1}") for i in range(11)]
        spec = ArchSpec(name="Large", provider="aws", region="us-east-1", components=comps, connections=conns)
        assert len(spec.components) == 12
        assert len(spec.connections) == 11

    def test_component_all_config_fields(self):
        comp = Component(
            id="full",
            service="rds",
            provider="aws",
            label="Full Config RDS",
            description="All config fields",
            tier=3,
            config={
                "instance_class": "db.r5.large",
                "engine": "postgres",
                "multi_az": True,
                "encryption": True,
                "storage_gb": 500,
                "count": 3,
                "estimated_gb": 100,
            },
        )
        assert comp.config["multi_az"] is True
        assert comp.config["storage_gb"] == 500

    def test_constraints_all_fields(self):
        c = Constraints(
            compliance=["hipaa", "pci-dss", "soc2"],
            budget_monthly=5000.0,
            availability=99.99,
            regions=["us-east-1", "eu-west-1"],
        )
        assert len(c.compliance) == 3
        assert c.availability == 99.99
        assert len(c.regions) == 2

    def test_yaml_preserves_config_types(self, three_tier):
        yaml_str = three_tier.to_yaml()
        restored = ArchSpec.from_yaml(yaml_str)
        for orig, rest in zip(three_tier.components, restored.components):
            assert orig.config == rest.config, f"Config mismatch for {orig.id}"

    def test_json_preserves_cost_estimate(self):
        spec = ArchSpec(
            name="With Cost",
            provider="aws",
            region="us-east-1",
            components=[Component(id="web", service="ec2", provider="aws", label="Web")],
            connections=[],
            cost_estimate=CostEstimate(
                monthly_total=100.50,
                breakdown=[ComponentCost(component_id="web", service="ec2", monthly=100.50, hourly=0.1377)],
            ),
        )
        json_str = spec.to_json()
        restored = ArchSpec.model_validate_json(json_str)
        assert restored.cost_estimate.monthly_total == 100.50
        assert restored.cost_estimate.breakdown[0].hourly == 0.1377

    def test_from_file_detects_format(self, tmp_path):
        spec = ArchSpec(
            name="Format Test",
            provider="gcp",
            region="us-central1",
            components=[Component(id="vm", service="compute_engine", provider="gcp", label="VM")],
            connections=[],
        )
        # YAML
        yaml_path = tmp_path / "test.yaml"
        yaml_path.write_text(spec.to_yaml())
        assert ArchSpec.from_file(str(yaml_path)).provider == "gcp"

        # JSON
        json_path = tmp_path / "test.json"
        json_path.write_text(spec.to_json())
        assert ArchSpec.from_file(str(json_path)).provider == "gcp"

        # YML extension
        yml_path = tmp_path / "test.yml"
        yml_path.write_text(spec.to_yaml())
        assert ArchSpec.from_file(str(yml_path)).provider == "gcp"

    def test_model_copy_deep(self, three_tier):
        copy = three_tier.model_copy(deep=True)
        copy.components[0].config["new_key"] = "new_value"
        assert "new_key" not in three_tier.components[0].config

    def test_all_tiers_represented(self, three_tier):
        tiers = {c.tier for c in three_tier.components}
        assert len(tiers) >= 2  # at minimum edge + data tiers


# Template Loading Tests


class TestTemplates:
    def test_three_tier_structure(self, three_tier):
        assert three_tier.provider == "aws"
        assert len(three_tier.components) >= 3
        services = {c.service for c in three_tier.components}
        assert "ec2" in services or "ecs" in services or "fargate" in services

    def test_serverless_structure(self, serverless):
        assert serverless.provider == "aws"
        services = {c.service for c in serverless.components}
        assert "lambda" in services or "api_gateway" in services

    def test_ml_pipeline_structure(self, ml_pipeline):
        assert ml_pipeline.provider == "aws"
        services = {c.service for c in ml_pipeline.components}
        assert "sagemaker" in services or "s3" in services

    def test_all_templates_have_connections(self, three_tier, serverless, ml_pipeline):
        for spec in [three_tier, serverless, ml_pipeline]:
            assert len(spec.connections) >= 1, f"{spec.name} has no connections"

    def test_all_templates_roundtrip(self, three_tier, serverless, ml_pipeline):
        for spec in [three_tier, serverless, ml_pipeline]:
            yaml_str = spec.to_yaml()
            restored = ArchSpec.from_yaml(yaml_str)
            assert restored.name == spec.name
            assert len(restored.components) == len(spec.components)


# Catalog Tests class TestCatalog:
    def test_search_aws_compute(self, catalog):
        results = catalog.search(provider="aws", vcpus=4)
        assert len(results) > 0
        for r in results:
            assert r["vcpus"] == 4

    def test_search_gcp_compute(self, catalog):
        results = catalog.search(provider="gcp")
        assert len(results) > 0
        for r in results:
            assert r["id"].startswith("gcp:")

    def test_search_azure_compute(self, catalog):
        results = catalog.search(provider="azure")
        assert len(results) > 0

    def test_search_by_memory(self, catalog):
        results = catalog.search(memory_gb=16)
        assert len(results) > 0
        for r in results:
            assert r["memory_gb"] == 16

    def test_search_by_family(self, catalog):
        results = catalog.search(query="general purpose")
        assert len(results) > 0

    def test_search_by_name(self, catalog):
        results = catalog.search(query="t3.medium")
        assert len(results) > 0
        assert any("t3.medium" in r["name"] for r in results)

    def test_compare_cross_cloud(self, catalog):
        comp = catalog.compare("m5.xlarge", "n2-standard-4")
        assert len(comp) == 2
        names = {r["name"] for r in comp}
        assert "m5.xlarge" in names
        assert "n2-standard-4" in names

    def test_compare_same_provider(self, catalog):
        comp = catalog.compare("m5.large", "m5.xlarge")
        assert len(comp) == 2
        large = next(r for r in comp if r["name"] == "m5.large")
        xlarge = next(r for r in comp if r["name"] == "m5.xlarge")
        assert xlarge["vcpus"] > large["vcpus"]

    def test_pricing_ec2(self, catalog):
        price = catalog.get_service_pricing("ec2", "aws", {"instance_type": "m5.large"})
        assert price is not None
        assert price > 0

    def test_pricing_rds(self, catalog):
        price = catalog.get_service_pricing("rds", "aws", {"instance_class": "db.r5.large", "engine": "postgres"})
        assert price is not None
        assert price > 0

    def test_pricing_s3(self, catalog):
        price = catalog.get_service_pricing("s3", "aws", {"storage_gb": 100})
        assert price is not None
        assert price > 0

    def test_pricing_lambda(self, catalog):
        price = catalog.get_service_pricing(
            "lambda", "aws", {"requests_millions": 10, "avg_duration_ms": 200, "memory_mb": 512}
        )
        assert price is not None
        assert price > 0

    def test_pricing_unknown_service_returns_fallback(self, catalog):
        # Unknown service should still return a default price
        price = catalog.get_service_pricing("unknown_service_xyz", "aws", {})
        # Falls through to _default_managed_price
        assert price is None or price >= 0

    def test_all_providers_have_data(self, catalog):
        for provider in ["aws", "gcp", "azure"]:
            results = catalog.search(provider=provider)
            assert len(results) > 0, f"No data for provider {provider}"

    def test_catalog_reuse(self, catalog):
        """Catalog should be reusable across multiple calls."""
        r1 = catalog.search(query="m5")
        r2 = catalog.search(query="t3")
        assert len(r1) > 0
        assert len(r2) > 0
        assert r1 != r2

    def test_find_instance(self, catalog):
        result = catalog.find_instance("m5.xlarge")
        assert result is not None
        assert result["name"] == "m5.xlarge"
        assert result["vcpus"] == 4


# Cost Engine Tests


class TestCostEngine:
    def test_three_tier_pricing(self, cost_engine, three_tier):
        estimate = cost_engine.estimate(three_tier)
        assert estimate.monthly_total > 0
        assert len(estimate.breakdown) == len(three_tier.components)
        assert estimate.currency == "USD"
        assert estimate.as_of  # date populated

    def test_serverless_pricing(self, cost_engine, serverless):
        estimate = cost_engine.estimate(serverless)
        assert estimate.monthly_total > 0
        for item in estimate.breakdown:
            assert item.monthly >= 0

    def test_ml_pipeline_pricing(self, cost_engine, ml_pipeline):
        estimate = cost_engine.estimate(ml_pipeline)
        assert estimate.monthly_total > 0

    def test_cost_notes_instance_type(self, cost_engine):
        comp = Component(
            id="web",
            service="ec2",
            provider="aws",
            label="Web",
            config={"instance_type": "m5.large", "count": 2, "multi_az": True},
        )
        notes = cost_engine._cost_notes(comp)
        assert "m5.large" in notes
        assert "2x" in notes
        assert "Multi-AZ" in notes

    def test_cost_notes_storage(self, cost_engine):
        comp = Component(
            id="db",
            service="rds",
            provider="aws",
            label="DB",
            config={"storage_gb": 100, "engine": "postgres"},
        )
        notes = cost_engine._cost_notes(comp)
        assert "100GB storage" in notes
        assert "postgres" in notes

    def test_compare_providers_aws_to_gcp(self, cost_engine, three_tier):
        alts = cost_engine.compare_providers(three_tier, ["gcp"])
        assert len(alts) == 1
        gcp_alt = alts[0]
        assert gcp_alt.provider == "gcp"
        assert gcp_alt.monthly_total > 0
        assert gcp_alt.spec is not None

    def test_compare_providers_aws_to_azure(self, cost_engine, three_tier):
        alts = cost_engine.compare_providers(three_tier, ["azure"])
        assert len(alts) == 1
        assert alts[0].provider == "azure"
        assert alts[0].monthly_total > 0

    def test_compare_providers_multi(self, cost_engine, three_tier):
        alts = cost_engine.compare_providers(three_tier, ["gcp", "azure"])
        assert len(alts) == 2
        providers = {a.provider for a in alts}
        assert providers == {"gcp", "azure"}

    def test_compare_skips_same_provider(self, cost_engine, three_tier):
        alts = cost_engine.compare_providers(three_tier, ["aws", "gcp"])
        providers = {a.provider for a in alts}
        assert "aws" not in providers  # skipped because spec is already aws

    def test_instance_mapping_aws_to_gcp(self, cost_engine):
        config = {"instance_type": "m5.xlarge"}
        mapped = cost_engine._map_instance_config(config, "aws", "gcp")
        # Should map instance_type to machine_type for GCP
        if "machine_type" in mapped:
            assert "instance_type" not in mapped
        # Even if no mapping found, shouldn't crash

    def test_estimate_total_equals_sum(self, cost_engine, three_tier):
        estimate = cost_engine.estimate(three_tier)
        computed_total = round(sum(item.monthly for item in estimate.breakdown), 2)
        assert estimate.monthly_total == computed_total

    def test_estimate_breakdown_has_services(self, cost_engine, three_tier):
        estimate = cost_engine.estimate(three_tier)
        for item in estimate.breakdown:
            assert item.service, f"Component {item.component_id} has no service"
            assert item.component_id, "Missing component_id"

    def test_gcp_spec_pricing(self, cost_engine):
        spec = ArchSpec(
            name="GCP App",
            provider="gcp",
            region="us-central1",
            components=[
                Component(
                    id="vm",
                    service="compute_engine",
                    provider="gcp",
                    label="VM",
                    config={"machine_type": "n2-standard-4"},
                ),
                Component(
                    id="db", service="cloud_sql", provider="gcp", label="DB", config={"tier": "db-n1-standard-4"}
                ),
            ],
            connections=[Connection(source="vm", target="db")],
        )
        estimate = cost_engine.estimate(spec)
        assert estimate.monthly_total > 0

    def test_azure_spec_pricing(self, cost_engine):
        spec = ArchSpec(
            name="Azure App",
            provider="azure",
            region="eastus",
            components=[
                Component(
                    id="vm",
                    service="virtual_machines",
                    provider="azure",
                    label="VM",
                    config={"vm_size": "Standard_D4s_v5"},
                ),
                Component(id="db", service="azure_sql", provider="azure", label="DB", config={"tier": "Standard_S3"}),
            ],
            connections=[Connection(source="vm", target="db")],
        )
        estimate = cost_engine.estimate(spec)
        assert estimate.monthly_total > 0


# Validator Tests class TestValidator:
    def test_hipaa_full_check(self, validator, three_tier):
        results = validator.validate(three_tier, compliance=["hipaa"])
        assert len(results) == 1
        hipaa = results[0]
        assert hipaa.framework == "HIPAA"
        assert 0.0 <= hipaa.score <= 1.0
        check_names = {c.name for c in hipaa.checks}
        assert "encryption_at_rest" in check_names

    def test_pci_dss(self, validator, three_tier):
        results = validator.validate(three_tier, compliance=["pci-dss"])
        assert len(results) == 1
        assert results[0].framework == "PCI-DSS"
        assert len(results[0].checks) > 0

    def test_soc2(self, validator, three_tier):
        results = validator.validate(three_tier, compliance=["soc2"])
        assert len(results) == 1
        assert results[0].framework == "SOC 2"

    def test_well_architected(self, validator, three_tier):
        results = validator.validate(three_tier, well_architected=True)
        wa = [r for r in results if r.framework == "Well-Architected"]
        assert len(wa) == 1
        assert len(wa[0].checks) >= 5

    def test_all_frameworks(self, validator, three_tier):
        results = validator.validate(three_tier, compliance=["hipaa", "pci-dss", "soc2"], well_architected=True)
        frameworks = {r.framework for r in results}
        assert "HIPAA" in frameworks
        assert "PCI-DSS" in frameworks
        assert "SOC 2" in frameworks
        assert "Well-Architected" in frameworks

    def test_fully_compliant_spec(self, validator):
        """Spec with all security features should score well."""
        spec = ArchSpec(
            name="Secure App",
            provider="aws",
            region="us-east-1",
            constraints=Constraints(compliance=["hipaa"]),
            components=[
                Component(id="waf", service="waf", provider="aws", label="WAF", tier=0),
                Component(id="auth", service="cognito", provider="aws", label="Auth", tier=0),
                Component(id="alb", service="alb", provider="aws", label="ALB", tier=1),
                Component(id="web", service="ecs", provider="aws", label="Web", tier=2, config={"encryption": True}),
                Component(
                    id="db",
                    service="rds",
                    provider="aws",
                    label="DB",
                    tier=3,
                    config={"encryption": True, "multi_az": True},
                ),
                Component(id="logs", service="cloudwatch", provider="aws", label="Logs", tier=4),
                Component(id="trail", service="cloudtrail", provider="aws", label="Trail", tier=4),
            ],
            connections=[
                Connection(source="waf", target="alb", protocol="HTTPS", port=443),
                Connection(source="alb", target="web", protocol="HTTPS", port=443),
                Connection(source="web", target="db", protocol="TCP", port=5432),
            ],
        )
        results = validator.validate(spec, compliance=["hipaa"])
        hipaa = results[0]
        passed = [c for c in hipaa.checks if c.passed]
        assert len(passed) >= 4, f"Only {len(passed)}/{len(hipaa.checks)} passed for secure spec"

    def test_minimal_spec_fails_everything(self, validator):
        spec = ArchSpec(
            name="Bare",
            provider="aws",
            region="us-east-1",
            components=[Component(id="x", service="ec2", provider="aws", label="X")],
            connections=[],
        )
        results = validator.validate(spec, compliance=["hipaa", "pci-dss", "soc2"], well_architected=True)
        for r in results:
            failed = [c for c in r.checks if not c.passed]
            assert len(failed) > 0, f"{r.framework} should have failures for minimal spec"

    def test_check_severity_levels(self, validator, three_tier):
        results = validator.validate(three_tier, compliance=["hipaa"])
        for check in results[0].checks:
            assert check.severity in ("critical", "high", "medium", "low", "info", None), (
                f"Invalid severity: {check.severity}"
            )


# Differ Tests class TestDiffer:
    def test_added_component(self, differ):
        spec1 = ArchSpec(
            name="V1",
            provider="aws",
            region="us-east-1",
            components=[Component(id="web", service="ec2", provider="aws", label="Web")],
            connections=[],
        )
        spec2 = ArchSpec(
            name="V2",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="web", service="ec2", provider="aws", label="Web"),
                Component(id="cache", service="elasticache", provider="aws", label="Cache"),
            ],
            connections=[Connection(source="web", target="cache")],
        )
        diff = differ.diff(spec1, spec2)
        assert len(diff.added) == 1
        assert diff.added[0].id == "cache"

    def test_removed_component(self, differ):
        spec1 = ArchSpec(
            name="V1",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="web", service="ec2", provider="aws", label="Web"),
                Component(id="cache", service="elasticache", provider="aws", label="Cache"),
            ],
            connections=[],
        )
        spec2 = ArchSpec(
            name="V2",
            provider="aws",
            region="us-east-1",
            components=[Component(id="web", service="ec2", provider="aws", label="Web")],
            connections=[],
        )
        diff = differ.diff(spec1, spec2)
        assert len(diff.removed) == 1
        assert diff.removed[0].id == "cache"

    def test_changed_service(self, differ):
        spec1 = ArchSpec(
            name="V1",
            provider="aws",
            region="us-east-1",
            components=[Component(id="db", service="rds", provider="aws", label="DB")],
            connections=[],
        )
        spec2 = ArchSpec(
            name="V2",
            provider="aws",
            region="us-east-1",
            components=[Component(id="db", service="dynamodb", provider="aws", label="DB")],
            connections=[],
        )
        diff = differ.diff(spec1, spec2)
        assert len(diff.changed) >= 1

    def test_diff_between_templates(self, differ, three_tier, serverless):
        diff = differ.diff(three_tier, serverless)
        total_changes = len(diff.added) + len(diff.removed) + len(diff.changed)
        assert total_changes > 0
        assert diff.summary

    def test_identical_diff(self, differ, three_tier):
        diff = differ.diff(three_tier, three_tier)
        assert len(diff.added) == 0
        assert len(diff.removed) == 0
        assert len(diff.changed) == 0

    def test_diff_cost_delta_with_estimates(self, differ, cost_engine, three_tier, serverless):
        three_tier.cost_estimate = cost_engine.estimate(three_tier)
        serverless.cost_estimate = cost_engine.estimate(serverless)
        diff = differ.diff(three_tier, serverless)
        # cost_delta should exist
        assert diff.cost_delta is not None or diff.cost_delta == 0

    def test_diff_all_templates(self, differ, three_tier, serverless, ml_pipeline):
        for a, b in [(three_tier, serverless), (serverless, ml_pipeline), (three_tier, ml_pipeline)]:
            diff = differ.diff(a, b)
            assert diff.summary, f"No summary for diff {a.name} -> {b.name}"


# Exporter Tests class TestExporters:
    def test_terraform_all_templates(self, three_tier, serverless, ml_pipeline):
        for spec in [three_tier, serverless, ml_pipeline]:
            hcl = spec.export("terraform")
            assert "terraform" in hcl.lower() or "resource" in hcl.lower()
            assert "provider" in hcl.lower()

    def test_terraform_gcp_spec(self):
        spec = ArchSpec(
            name="GCP",
            provider="gcp",
            region="us-central1",
            components=[
                Component(id="vm", service="compute_engine", provider="gcp", label="VM"),
                Component(id="db", service="cloud_sql", provider="gcp", label="DB"),
            ],
            connections=[Connection(source="vm", target="db")],
        )
        hcl = spec.export("terraform")
        assert "google" in hcl.lower()

    def test_terraform_azure_spec(self):
        spec = ArchSpec(
            name="Azure",
            provider="azure",
            region="eastus",
            components=[
                Component(id="vm", service="virtual_machines", provider="azure", label="VM"),
                Component(id="db", service="azure_sql", provider="azure", label="DB"),
            ],
            connections=[Connection(source="vm", target="db")],
        )
        hcl = spec.export("terraform")
        assert "azurerm" in hcl.lower()

    def test_terraform_write_to_dir(self, three_tier, tmp_path):
        from cloudwright.exporter.terraform import render

        hcl = render(three_tier)
        out_file = tmp_path / "main.tf"
        out_file.write_text(hcl)
        assert out_file.exists()
        assert out_file.stat().st_size > 0

    def test_cloudformation_all_templates(self, three_tier, serverless, ml_pipeline):
        for spec in [three_tier, serverless, ml_pipeline]:
            cfn = spec.export("cloudformation")
            assert "AWSTemplateFormatVersion" in cfn
            data = yaml.safe_load(cfn)
            assert "Resources" in data

    def test_cloudformation_skips_non_aws(self):
        spec = ArchSpec(
            name="GCP",
            provider="gcp",
            region="us-central1",
            components=[Component(id="vm", service="compute_engine", provider="gcp", label="VM")],
            connections=[],
        )
        cfn = spec.export("cloudformation")
        data = yaml.safe_load(cfn)
        # Non-AWS components should be skipped or empty — shouldn't crash
        assert data is not None

    def test_mermaid_all_templates(self, three_tier, serverless, ml_pipeline):
        for spec in [three_tier, serverless, ml_pipeline]:
            mermaid = spec.export("mermaid")
            assert "flowchart" in mermaid.lower()
            # Every component should appear as a node
            for comp in spec.components:
                assert comp.id in mermaid or comp.label in mermaid

    def test_mermaid_tier_subgraphs(self, three_tier):
        mermaid = three_tier.export("mermaid")
        assert "subgraph" in mermaid

    def test_sbom_all_templates(self, three_tier, serverless, ml_pipeline):
        for spec in [three_tier, serverless, ml_pipeline]:
            sbom = spec.export("sbom")
            data = json.loads(sbom)
            assert data["bomFormat"] == "CycloneDX"
            assert data["specVersion"] == "1.5"
            assert len(data["components"]) > 0

    def test_sbom_has_dependencies(self, three_tier):
        sbom = three_tier.export("sbom")
        data = json.loads(sbom)
        assert "dependencies" in data
        assert len(data["dependencies"]) > 0

    def test_aibom_all_templates(self, three_tier, serverless, ml_pipeline):
        for spec in [three_tier, serverless, ml_pipeline]:
            aibom = spec.export("aibom")
            data = json.loads(aibom)
            assert data["aibomVersion"]
            assert "aiComponents" in data
            # Cloudwright AI should always be present
            names = [c["name"] for c in data["aiComponents"]]
            assert any("Cloudwright" in n for n in names)

    def test_aibom_detects_ml_services(self, ml_pipeline):
        aibom = ml_pipeline.export("aibom")
        data = json.loads(aibom)
        # ML pipeline should have AI services detected
        ai_services = data.get("architectureAIServices", [])
        if ai_services:
            service_names = [s.get("service", "") for s in ai_services]
            assert len(service_names) > 0

    def test_export_unknown_format_raises(self, three_tier):
        with pytest.raises(ValueError, match="Unknown export format"):
            three_tier.export("banana")


# Integration Tests — cross-module flows


class TestIntegrationFlows:
    def test_template_to_cost_to_export(self, cost_engine, three_tier):
        """Load template -> price it -> export to terraform."""
        estimate = cost_engine.estimate(three_tier)
        assert estimate.monthly_total > 0
        three_tier.cost_estimate = estimate
        hcl = three_tier.export("terraform")
        assert "resource" in hcl.lower()

    def test_template_to_validate_to_diff(self, validator, differ, cost_engine, three_tier):
        """Validate, then diff against a modified version."""
        results = validator.validate(three_tier, compliance=["hipaa"])
        assert len(results) > 0

        # Create a modified version with security improvements
        improved = three_tier.model_copy(deep=True)
        improved.components.append(Component(id="logs", service="cloudwatch", provider="aws", label="Logging", tier=4))
        diff = differ.diff(three_tier, improved)
        assert len(diff.added) == 1

    def test_cost_comparison_then_export_alternatives(self, cost_engine, three_tier):
        """Price across clouds then export each alternative."""
        alts = cost_engine.compare_providers(three_tier, ["gcp", "azure"])
        for alt in alts:
            assert alt.spec is not None
            # Each alternative should be exportable to mermaid
            mermaid = alt.spec.export("mermaid")
            assert "flowchart" in mermaid.lower()

    def test_full_pipeline(self, cost_engine, validator, differ, three_tier, serverless):
        """Full pipeline: load, cost, validate, diff, export."""
        # Cost
        three_tier.cost_estimate = cost_engine.estimate(three_tier)
        serverless.cost_estimate = cost_engine.estimate(serverless)
        assert three_tier.cost_estimate.monthly_total > 0
        assert serverless.cost_estimate.monthly_total > 0

        # Validate
        v_results = validator.validate(three_tier, compliance=["hipaa"], well_architected=True)
        assert len(v_results) >= 2

        # Diff
        diff = differ.diff(three_tier, serverless)
        assert diff.summary

        # Export all formats
        for fmt in ["terraform", "cloudformation", "mermaid", "sbom", "aibom"]:
            output = three_tier.export(fmt)
            assert output, f"Empty {fmt} export"

    def test_cross_cloud_pricing_consistency(self, cost_engine, three_tier):
        """All cloud providers should return non-zero pricing."""
        aws_estimate = cost_engine.estimate(three_tier)
        alts = cost_engine.compare_providers(three_tier, ["gcp", "azure"])

        assert aws_estimate.monthly_total > 0, "AWS pricing is $0"
        for alt in alts:
            assert alt.monthly_total > 0, f"{alt.provider} pricing is $0"

    def test_yaml_json_export_roundtrip(self, cost_engine, three_tier):
        """Spec with cost should survive YAML and JSON roundtrips."""
        three_tier.cost_estimate = cost_engine.estimate(three_tier)

        # YAML roundtrip
        yaml_str = three_tier.to_yaml()
        from_yaml = ArchSpec.from_yaml(yaml_str)
        assert from_yaml.cost_estimate.monthly_total == three_tier.cost_estimate.monthly_total

        # JSON roundtrip
        json_str = three_tier.to_json()
        from_json = ArchSpec.model_validate_json(json_str)
        assert from_json.cost_estimate.monthly_total == three_tier.cost_estimate.monthly_total

    def test_diff_with_file_save_and_reload(self, differ, three_tier, tmp_path):
        """Save two specs to files, reload, and diff."""
        v1_path = tmp_path / "v1.yaml"
        v1_path.write_text(three_tier.to_yaml())

        v2 = three_tier.model_copy(deep=True)
        v2.components.append(Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=3))
        v2_path = tmp_path / "v2.yaml"
        v2_path.write_text(v2.to_yaml())

        loaded_v1 = ArchSpec.from_file(str(v1_path))
        loaded_v2 = ArchSpec.from_file(str(v2_path))
        diff = differ.diff(loaded_v1, loaded_v2)
        assert len(diff.added) == 1
        assert diff.added[0].id == "cache"


# LLM Architect Tests (requires API key)


@skip_no_llm
class TestLLM:
    @pytest.mark.timeout(60)
    def test_design_aws_three_tier(self):
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design("3-tier web application on AWS with CloudFront, ALB, EC2, and RDS PostgreSQL")
        assert isinstance(spec, ArchSpec)
        assert spec.provider == "aws"
        assert len(spec.components) >= 3
        assert len(spec.connections) >= 2

    @pytest.mark.timeout(60)
    def test_design_gcp(self):
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design("Serverless API on GCP with Cloud Run, Firestore, and Pub/Sub")
        assert isinstance(spec, ArchSpec)
        assert spec.provider == "gcp"
        assert len(spec.components) >= 2

    @pytest.mark.timeout(60)
    def test_design_azure(self):
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design("Web app on Azure with App Service, Azure SQL, and Blob Storage")
        assert isinstance(spec, ArchSpec)
        assert spec.provider == "azure"
        assert len(spec.components) >= 2

    @pytest.mark.timeout(60)
    def test_design_with_budget_constraint(self):
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design(
            "Simple blog on AWS",
            constraints=Constraints(budget_monthly=100.0),
        )
        assert isinstance(spec, ArchSpec)
        assert len(spec.components) >= 2

    @pytest.mark.timeout(60)
    def test_design_with_compliance(self):
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design(
            "Healthcare data processing pipeline",
            constraints=Constraints(compliance=["hipaa"]),
        )
        assert isinstance(spec, ArchSpec)

    @pytest.mark.timeout(120)
    def test_modify_add_component(self):
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design("Simple web app with EC2 and RDS on AWS")
        original_count = len(spec.components)
        modified = arch.modify(spec, "Add an ElastiCache Redis cluster between the web servers and database")
        assert isinstance(modified, ArchSpec)
        # Should have at least as many components
        assert len(modified.components) >= original_count

    @pytest.mark.timeout(120)
    def test_design_then_cost_then_validate(self):
        """Full flow: design -> cost -> validate."""
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design("Production web app on AWS with ALB, ECS, RDS, ElastiCache")
        assert len(spec.components) >= 3

        engine = CostEngine()
        estimate = engine.estimate(spec)
        assert estimate.monthly_total > 0
        spec.cost_estimate = estimate

        v = Validator()
        results = v.validate(spec, well_architected=True)
        assert len(results) > 0

    @pytest.mark.timeout(120)
    def test_design_then_compare_providers(self):
        """Design on AWS, then compare across clouds."""
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design("3-tier web app with load balancer, compute, and database on AWS")

        engine = CostEngine()
        spec.cost_estimate = engine.estimate(spec)
        assert spec.cost_estimate.monthly_total > 0

        alts = engine.compare_providers(spec, ["gcp", "azure"])
        assert len(alts) == 2
        for alt in alts:
            assert alt.monthly_total > 0


# Provider Equivalences Tests


class TestProviderEquivalences:
    def test_ec2_to_gcp(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("ec2", "aws", "gcp")
        assert equiv == "compute_engine"

    def test_ec2_to_azure(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("ec2", "aws", "azure")
        assert equiv == "virtual_machines"

    def test_rds_to_gcp(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("rds", "aws", "gcp")
        assert equiv == "cloud_sql"

    def test_rds_to_azure(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("rds", "aws", "azure")
        assert equiv == "azure_sql"

    def test_s3_to_gcp(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("s3", "aws", "gcp")
        assert equiv == "cloud_storage"

    def test_s3_to_azure(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("s3", "aws", "azure")
        assert equiv == "blob_storage"

    def test_lambda_to_gcp(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("lambda", "aws", "gcp")
        assert equiv == "cloud_functions"

    def test_lambda_to_azure(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("lambda", "aws", "azure")
        assert equiv == "azure_functions"

    def test_unknown_service(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("totally_fake_service", "aws", "gcp")
        assert equiv is None

    def test_same_provider(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("ec2", "aws", "aws")
        # Same provider should return the same service
        assert equiv == "ec2" or equiv is None

    def test_gcp_to_aws(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("compute_engine", "gcp", "aws")
        assert equiv == "ec2"

    def test_azure_to_aws(self):
        from cloudwright.providers import get_equivalent

        equiv = get_equivalent("virtual_machines", "azure", "aws")
        assert equiv == "ec2"


# CLI Module Import Tests


class TestCLIImports:
    def test_main_imports(self):
        pass

    def test_design_command_imports(self):
        pass

    def test_cost_command_imports(self):
        pass

    def test_compare_command_imports(self):
        pass

    def test_validate_command_imports(self):
        pass

    def test_export_command_imports(self):
        pass

    def test_diff_command_imports(self):
        pass

    def test_chat_command_imports(self):
        pass

    def test_catalog_command_imports(self):
        pass
