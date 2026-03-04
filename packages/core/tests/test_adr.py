from __future__ import annotations

from cloudwright.spec import ArchSpec, Component, Connection
from cloudwright_cli.commands.adr import _deterministic_adr


def _make_spec(name: str = "My Architecture", **kwargs) -> ArchSpec:
    components = kwargs.pop(
        "components",
        [
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
    )
    return ArchSpec(
        name=name,
        provider="aws",
        region="us-east-1",
        components=components,
        connections=kwargs.pop("connections", [Connection(source="web", target="db")]),
        **kwargs,
    )


def test_adr_generates_string():
    spec = _make_spec()
    result = _deterministic_adr(spec)
    assert isinstance(result, str)
    assert len(result) > 0


def test_adr_contains_spec_name():
    spec = _make_spec(name="My Production Stack")
    result = _deterministic_adr(spec)
    assert "My Production Stack" in result


def test_adr_contains_components():
    spec = _make_spec()
    result = _deterministic_adr(spec)
    assert "web" in result
    assert "db" in result


def test_adr_deterministic():
    spec = _make_spec()
    first = _deterministic_adr(spec)
    second = _deterministic_adr(spec)
    assert first == second


def test_adr_with_rationale():
    spec = _make_spec(
        metadata={
            "rationale": [
                {"decision": "Use RDS over DynamoDB", "reason": "Relational data model suits the workload"},
                {"decision": "ALB for load balancing", "reason": "HTTP/HTTPS routing built in"},
            ]
        }
    )
    result = _deterministic_adr(spec)
    assert "Use RDS over DynamoDB" in result
    assert "Relational data model" in result


def test_adr_custom_title():
    spec = _make_spec()
    result = _deterministic_adr(spec, title="Custom ADR Title")
    assert "Custom ADR Title" in result


def test_adr_custom_decision():
    spec = _make_spec()
    result = _deterministic_adr(spec, decision="Choose PostgreSQL over MySQL")
    assert "Choose PostgreSQL over MySQL" in result


def test_adr_contains_status():
    spec = _make_spec()
    result = _deterministic_adr(spec)
    assert "## Status" in result
    assert "Proposed" in result


def test_adr_contains_components_table():
    spec = _make_spec()
    result = _deterministic_adr(spec)
    assert "## Components" in result
    assert "| ID |" in result


def test_adr_contains_consequences():
    spec = _make_spec()
    result = _deterministic_adr(spec)
    assert "## Consequences" in result
    assert "### Positive" in result
    assert "### Negative" in result


def test_adr_with_cost_estimate():
    from cloudwright.spec import ComponentCost, CostEstimate

    spec = _make_spec(
        cost_estimate=CostEstimate(
            monthly_total=450.00,
            breakdown=[ComponentCost(component_id="db", service="rds", monthly=450.00)],
        )
    )
    result = _deterministic_adr(spec)
    assert "450" in result
    assert "## Cost Estimate" in result
