"""Tests for ArchSpec models — serialization, validation, round-tripping."""

import json

import pytest
from cloudwright.spec import (
    Alternative,
    ArchSpec,
    Boundary,
    Component,
    ComponentCost,
    Connection,
    Constraints,
    CostEstimate,
    DiffResult,
    ValidationCheck,
    ValidationResult,
)


def _sample_spec() -> ArchSpec:
    return ArchSpec(
        name="Test Architecture",
        version=1,
        provider="aws",
        region="us-east-1",
        constraints=Constraints(compliance=["hipaa"], budget_monthly=500.0),
        components=[
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web Server",
                description="Application server",
                tier=2,
                config={"instance_type": "t3.medium"},
            ),
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="Database",
                description="PostgreSQL",
                tier=3,
                config={"engine": "postgres", "instance_class": "db.t3.medium"},
            ),
        ],
        connections=[
            Connection(source="web", target="db", label="SQL", protocol="TCP", port=5432),
        ],
        cost_estimate=CostEstimate(
            monthly_total=108.00,
            breakdown=[
                ComponentCost(component_id="web", service="ec2", monthly=30.37),
                ComponentCost(component_id="db", service="rds", monthly=77.63),
            ],
        ),
    )


def test_create_spec():
    spec = _sample_spec()
    assert spec.name == "Test Architecture"
    assert len(spec.components) == 2
    assert len(spec.connections) == 1
    assert spec.cost_estimate.monthly_total == 108.00


def test_yaml_roundtrip():
    spec = _sample_spec()
    yaml_str = spec.to_yaml()
    assert "Test Architecture" in yaml_str
    assert "ec2" in yaml_str

    restored = ArchSpec.from_yaml(yaml_str)
    assert restored.name == spec.name
    assert len(restored.components) == len(spec.components)
    assert restored.components[0].id == "web"
    assert restored.components[0].config["instance_type"] == "t3.medium"
    assert restored.connections[0].port == 5432


def test_json_roundtrip():
    spec = _sample_spec()
    json_str = spec.to_json()
    data = json.loads(json_str)
    assert data["name"] == "Test Architecture"

    restored = ArchSpec.model_validate_json(json_str)
    assert restored.name == spec.name
    assert len(restored.components) == 2


def test_json_schema():
    schema = ArchSpec.json_schema()
    # Pydantic v2 uses $defs/$ref format
    assert "$defs" in schema
    assert "ArchSpec" in schema["$defs"]
    assert "components" in schema["$defs"]["ArchSpec"]["properties"]


def test_component_defaults():
    comp = Component(id="test", service="s3", provider="aws", label="Bucket")
    assert comp.tier == 2
    assert comp.config == {}
    assert comp.description == ""


def test_connection_optional_fields():
    conn = Connection(source="a", target="b")
    assert conn.label == ""
    assert conn.protocol is None
    assert conn.port is None


def test_constraints():
    c = Constraints(compliance=["hipaa", "pci-dss"], budget_monthly=1000.0, availability=99.99)
    assert len(c.compliance) == 2
    assert c.budget_monthly == 1000.0


def test_cost_estimate_as_of():
    ce = CostEstimate(monthly_total=100.0)
    assert ce.as_of  # auto-populated with today's date
    assert ce.currency == "USD"


def test_alternative():
    alt = Alternative(provider="gcp", monthly_total=450.0, key_differences=["Cloud SQL instead of RDS"])
    assert alt.provider == "gcp"
    assert len(alt.key_differences) == 1


def test_diff_result():
    diff = DiffResult(
        added=[Component(id="cache", service="elasticache", provider="aws", label="Cache")],
        cost_delta=48.60,
        summary="Added cache",
    )
    assert len(diff.added) == 1
    assert diff.cost_delta == 48.60


def test_validation_result():
    result = ValidationResult(
        framework="hipaa",
        passed=False,
        score=0.6,
        checks=[
            ValidationCheck(
                name="Encryption at Rest",
                category="security",
                passed=True,
                severity="critical",
                detail="All data stores encrypted",
            ),
            ValidationCheck(
                name="Audit Logging",
                category="compliance",
                passed=False,
                severity="critical",
                detail="No logging component",
                recommendation="Add CloudTrail",
            ),
        ],
    )
    assert not result.passed
    assert result.score == 0.6
    assert result.checks[0].passed
    assert not result.checks[1].passed


def test_from_file_yaml(tmp_path):
    spec = _sample_spec()
    path = tmp_path / "test.yaml"
    path.write_text(spec.to_yaml())
    restored = ArchSpec.from_file(str(path))
    assert restored.name == spec.name


def test_from_file_json(tmp_path):
    spec = _sample_spec()
    path = tmp_path / "test.json"
    path.write_text(spec.to_json())
    restored = ArchSpec.from_file(str(path))
    assert restored.name == spec.name


def test_export_delegates():
    """Test that export() calls the exporter module (mermaid as simplest case)."""
    spec = _sample_spec()
    # This will fail if exporter/mermaid.py isn't implemented yet
    try:
        mermaid = spec.export("mermaid")
        assert "flowchart" in mermaid.lower() or "graph" in mermaid.lower()
    except ImportError:
        pytest.skip("Mermaid exporter not yet available")


def test_export_unknown_format():
    spec = _sample_spec()
    with pytest.raises(ValueError, match="Unknown export format"):
        spec.export("unknown_format")


def test_boundary_model():
    b = Boundary(id="vpc_main", kind="vpc", label="Main VPC", component_ids=["web", "db"])
    assert b.id == "vpc_main"
    assert b.kind == "vpc"
    assert len(b.component_ids) == 2
    assert b.parent is None
    assert b.config == {}


def test_boundary_id_validation():
    with pytest.raises(ValueError, match="not IaC-safe"):
        Boundary(id="bad id!", kind="vpc")


def test_spec_with_boundaries_yaml_roundtrip():
    spec = ArchSpec(
        name="Bounded App",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
        connections=[Connection(source="web", target="db")],
        boundaries=[
            Boundary(id="vpc_main", kind="vpc", label="Main VPC", component_ids=["web", "db"]),
            Boundary(id="subnet_pub", kind="subnet", label="Public Subnet", parent="vpc_main", component_ids=["web"]),
        ],
    )
    yaml_str = spec.to_yaml()
    assert "boundaries" in yaml_str
    assert "vpc_main" in yaml_str

    restored = ArchSpec.from_yaml(yaml_str)
    assert len(restored.boundaries) == 2
    assert restored.boundaries[0].id == "vpc_main"
    assert restored.boundaries[1].parent == "vpc_main"


def test_spec_without_boundaries_backward_compat():
    yaml_str = """\
name: Old Spec
provider: aws
region: us-east-1
components:
  - id: web
    service: ec2
    provider: aws
    label: Web
    tier: 2
connections: []
"""
    spec = ArchSpec.from_yaml(yaml_str)
    assert spec.boundaries == []
    # Re-serialize and confirm boundaries is not emitted (clean_empty strips it)
    output = spec.to_yaml()
    assert "boundaries" not in output
