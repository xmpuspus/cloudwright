"""Tests for the C4 model exporter."""

from __future__ import annotations

import glob

import pytest
from cloudwright.exporter.c4 import render
from cloudwright.spec import ArchSpec, Component, Connection


def _sample_spec() -> ArchSpec:
    return ArchSpec(
        name="Test App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0),
            Component(id="alb", service="alb", provider="aws", label="Load Balancer", tier=1),
            Component(id="web", service="ec2", provider="aws", label="Web Server", tier=2),
            Component(id="db", service="rds", provider="aws", label="Database", tier=3),
        ],
        connections=[
            Connection(source="cdn", target="alb", protocol="HTTPS", port=443),
            Connection(source="alb", target="web", protocol="HTTP", port=80),
            Connection(source="web", target="db", protocol="TCP", port=5432),
        ],
    )


def _ecs_spec() -> ArchSpec:
    return ArchSpec(
        name="ECS App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="cluster",
                service="ecs",
                provider="aws",
                label="API Cluster",
                tier=2,
                config={"desired_count": 3},
            ),
            Component(id="db", service="rds", provider="aws", label="Database", tier=3),
        ],
        connections=[
            Connection(source="cluster", target="db", protocol="TCP", port=5432),
        ],
    )


def test_level1_system_context():
    out = render(_sample_spec(), level=1)
    assert "Test App" in out


def test_level1_external_actor_separate():
    out = render(_sample_spec(), level=1, output_format="d2")
    # CDN is tier=0 so it should be an external node, not inside the system block
    assert "cdn" in out
    # System block should appear
    assert "Test_App" in out or "Test App" in out


def test_level2_container():
    out = render(_sample_spec(), level=2)
    assert "CDN" in out
    assert "Database" in out
    assert "Web Server" in out


def test_level3_component():
    out = render(_sample_spec(), level=3)
    # L3 with no expandable config falls back to L2 layout — still has all components
    assert "CDN" in out
    assert "Database" in out


def test_level3_expands_ecs_count():
    out = render(_ecs_spec(), level=3)
    # desired_count=3 should produce 3 numbered sub-components
    assert "API Cluster 1" in out
    assert "API Cluster 2" in out
    assert "API Cluster 3" in out


def test_c4_d2_format():
    out = render(_sample_spec(), output_format="d2")
    assert "style.fill" in out or "->" in out


def test_c4_mermaid_format():
    out = render(_sample_spec(), output_format="mermaid")
    assert "C4" in out or "Container" in out


def test_c4_mermaid_l1():
    out = render(_sample_spec(), level=1, output_format="mermaid")
    assert "C4Context" in out
    assert "Test App" in out


def test_c4_mermaid_l2():
    out = render(_sample_spec(), level=2, output_format="mermaid")
    assert "C4Container" in out
    assert "ContainerDb" in out  # rds should use ContainerDb


def test_c4_mermaid_l3_fallback():
    out = render(_sample_spec(), level=3, output_format="mermaid")
    # No expandable components → falls back to L2 mermaid
    assert "C4Container" in out or "C4Component" in out


def test_c4_mermaid_l3_expands():
    out = render(_ecs_spec(), level=3, output_format="mermaid")
    assert "C4Component" in out
    assert "API Cluster 1" in out


def test_c4_unknown_format_raises():
    with pytest.raises(ValueError, match="Unknown C4 output format"):
        render(_sample_spec(), output_format="graphviz")


def test_c4_dispatch_via_export_spec():
    from cloudwright.exporter import export_spec

    content = export_spec(_sample_spec(), "c4")
    assert len(content) > 0
    assert "Test App" in content


def test_c4_edge_labels():
    out = render(_sample_spec(), level=2, output_format="d2")
    assert "HTTPS" in out or "443" in out
    assert "TCP" in out or "5432" in out


def test_c4_all_templates():
    templates = sorted(glob.glob("/Users/xavier/Desktop/cloudwright/catalog/templates/*.yaml"))
    for t in templates:
        if "_index" in t:
            continue
        spec = ArchSpec.from_file(t)
        for level in (1, 2, 3):
            out = render(spec, level=level)
            assert len(out) > 0, f"Empty C4 L{level} for {t}"
