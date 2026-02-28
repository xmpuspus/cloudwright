"""Tests for the ASCII/Unicode diagram renderer."""

from cloudwright.ascii_diagram import render_ascii, render_next_steps, render_summary
from cloudwright.spec import ArchSpec, Component, ComponentCost, Connection, CostEstimate


def _sample_spec() -> ArchSpec:
    return ArchSpec(
        name="Test Web App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0),
            Component(id="alb", service="alb", provider="aws", label="Load Balancer", tier=1),
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web Servers",
                tier=2,
                config={"instance_type": "m5.large", "count": 2},
            ),
            Component(
                id="db", service="rds", provider="aws", label="PostgreSQL", tier=3, config={"engine": "postgres"}
            ),
        ],
        connections=[
            Connection(source="cdn", target="alb", label="HTTPS", protocol="HTTPS", port=443),
            Connection(source="alb", target="web", label="HTTP", protocol="HTTP", port=80),
            Connection(source="web", target="db", label="SQL", protocol="TCP", port=5432),
        ],
    )


def test_render_ascii_basic():
    spec = _sample_spec()
    out = render_ascii(spec)
    # Box-drawing characters present
    assert "┌" in out
    assert "└" in out
    assert "│" in out
    # All component labels appear
    assert "CDN" in out
    assert "Load Balancer" in out
    assert "Web Servers" in out
    assert "PostgreSQL" in out


def test_render_ascii_includes_connections():
    spec = _sample_spec()
    out = render_ascii(spec)
    # Vertical arrows between tiers
    assert "▼" in out


def test_render_ascii_multicomponent_tier():
    spec = ArchSpec(
        name="Multi Tier",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="web1", service="ec2", provider="aws", label="Web A", tier=2),
            Component(id="web2", service="ec2", provider="aws", label="Web B", tier=2),
        ],
    )
    out = render_ascii(spec)
    assert "Web A" in out
    assert "Web B" in out


def test_render_summary():
    spec = _sample_spec()
    out = render_summary(spec)
    assert "Components: 4" in out
    assert "AWS" in out
    assert "us-east-1" in out


def test_render_summary_with_cost():
    spec = _sample_spec()
    spec = spec.model_copy(
        update={
            "cost_estimate": CostEstimate(
                monthly_total=487.0,
                breakdown=[ComponentCost(component_id="web", service="ec2", monthly=487.0)],
            )
        }
    )
    out = render_summary(spec)
    assert "$" in out
    assert "487" in out


def test_render_summary_no_cost():
    spec = ArchSpec(
        name="No Cost",
        provider="gcp",
        region="us-central1",
        components=[Component(id="vm", service="compute_engine", provider="gcp", label="VM", tier=2)],
    )
    out = render_summary(spec)
    assert "$" not in out
    assert "Components: 1" in out


def test_render_next_steps():
    out = render_next_steps()
    assert "cloudwright cost" in out
    assert "cloudwright validate" in out
    assert "cloudwright export tf" in out
    assert "cloudwright chat" in out


def test_render_ascii_no_color():
    spec = _sample_spec()
    out = render_ascii(spec, color=False)
    # No ANSI escape sequences
    assert "\033[" not in out
    # Still has box characters and labels
    assert "┌" in out
    assert "CDN" in out


def test_render_ascii_empty_spec():
    spec = ArchSpec(name="Empty", provider="aws", region="us-east-1", components=[])
    # Should not raise
    out = render_ascii(spec)
    assert "Empty" in out


# --- Category C edge case tests ---


def test_single_component():
    spec = ArchSpec(
        name="Solo",
        components=[Component(id="db", service="rds", provider="aws", label="Database")],
        connections=[],
    )
    out = render_ascii(spec)
    assert "Database" in out
    assert "┌" in out


def test_no_connections():
    spec = ArchSpec(
        name="Disconnected",
        components=[
            Component(id="a", service="ec2", provider="aws", label="Server A"),
            Component(id="b", service="s3", provider="aws", label="Bucket B"),
            Component(id="c", service="rds", provider="aws", label="DB C"),
        ],
        connections=[],
    )
    out = render_ascii(spec)
    assert "Server A" in out
    assert "Bucket B" in out
    assert "DB C" in out


def test_all_same_tier():
    spec = ArchSpec(
        name="Same Tier",
        components=[Component(id=f"w{i}", service="ec2", provider="aws", label=f"Web {i}", tier=2) for i in range(5)],
        connections=[],
    )
    out = render_ascii(spec)
    assert "Web 0" in out
    assert "Web 4" in out


def test_deep_tier_chain():
    spec = ArchSpec(
        name="Deep Chain",
        components=[
            Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0),
            Component(id="lb", service="alb", provider="aws", label="LB", tier=1),
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
            Component(id="backup", service="s3", provider="aws", label="Backup", tier=4),
        ],
        connections=[
            Connection(source="cdn", target="lb", protocol="HTTPS", port=443),
            Connection(source="lb", target="web", protocol="HTTP", port=80),
            Connection(source="web", target="db", protocol="TCP", port=5432),
            Connection(source="db", target="backup"),
        ],
    )
    out = render_ascii(spec)
    assert "CDN" in out
    assert "Backup" in out
    assert "▼" in out


def test_cross_provider():
    spec = ArchSpec(
        name="Multi-Cloud",
        components=[
            Component(id="aws_web", service="ec2", provider="aws", label="AWS Web"),
            Component(id="gcp_db", service="cloud_sql", provider="gcp", label="GCP Database"),
            Component(id="azure_cache", service="azure_cache", provider="azure", label="Azure Cache"),
        ],
        connections=[
            Connection(source="aws_web", target="gcp_db"),
            Connection(source="aws_web", target="azure_cache"),
        ],
    )
    out = render_ascii(spec)
    assert "AWS Web" in out
    assert "GCP Database" in out
    assert "Azure Cache" in out


def test_wide_arch_wraps():
    """6+ components in a tier should wrap across rows."""
    spec = ArchSpec(
        name="Wide",
        components=[
            Component(id=f"svc{i}", service="ec2", provider="aws", label=f"Service {i}", tier=2) for i in range(8)
        ],
        connections=[],
    )
    out = render_ascii(spec, width=80)
    assert "Service 0" in out
    assert "Service 7" in out
