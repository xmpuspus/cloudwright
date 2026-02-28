"""Tests for the presentation/deck exporter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from cloudwright.exporter.presentation import render_html, render_pdf
from cloudwright.spec import ArchSpec, Component, ComponentCost, Connection, CostEstimate

TEMPLATE_DIR = Path(__file__).parents[3] / "catalog" / "templates"
TEMPLATES = [p for p in sorted(TEMPLATE_DIR.glob("*.yaml")) if p.name != "_index.yaml"]


def _sample_spec() -> ArchSpec:
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
                config={"instance_type": "m5.large", "count": 2},
            ),
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="PostgreSQL",
                tier=3,
                config={"engine": "postgres", "multi_az": True},
            ),
        ],
        connections=[
            Connection(source="web", target="db", protocol="TCP", port=5432, label="SQL"),
        ],
    )


def _spec_with_cost() -> ArchSpec:
    spec = _sample_spec()
    spec.cost_estimate = CostEstimate(
        monthly_total=312.50,
        breakdown=[
            ComponentCost(component_id="web", service="ec2", monthly=200.00),
            ComponentCost(component_id="db", service="rds", monthly=112.50),
        ],
        data_transfer_monthly=15.00,
        currency="USD",
    )
    return spec


# --- basic structure ---


def test_render_html_basic():
    html = render_html(_sample_spec())
    assert "<html" in html
    assert "<head" in html
    assert "<body" in html
    assert "</html>" in html


def test_render_html_contains_title():
    html = render_html(_sample_spec())
    assert "Test App" in html


def test_render_html_contains_components():
    html = render_html(_sample_spec())
    assert "Web Server" in html
    assert "PostgreSQL" in html


def test_render_html_contains_connections():
    html = render_html(_sample_spec())
    # Source and target labels should appear
    assert "Web Server" in html
    assert "PostgreSQL" in html
    # Protocol appears in network topology table
    assert "TCP" in html


# --- cost ---


def test_render_html_with_cost():
    html = render_html(_spec_with_cost())
    assert "312" in html  # total appears somewhere
    assert "200" in html
    assert "112" in html


def test_render_html_no_cost():
    html = render_html(_sample_spec())
    # Cost section heading should not appear
    assert "Cost Breakdown" not in html


# --- optional SVG ---


def test_render_html_with_svg():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
    html = render_html(_sample_spec(), include_diagram_svg=svg)
    assert "<svg" in html
    assert "circle" in html


def test_render_html_no_svg_placeholder():
    html = render_html(_sample_spec(), include_diagram_svg=None)
    assert "No diagram provided" in html


# --- config details ---


def test_render_html_config_details():
    html = render_html(_sample_spec())
    assert "m5.large" in html
    assert "instance_type" in html
    assert "postgres" in html


# --- PDF import guard ---


def test_render_pdf_requires_weasyprint():
    import builtins

    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "weasyprint":
            raise ImportError("No module named 'weasyprint'")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        with pytest.raises(ImportError, match="weasyprint"):
            render_pdf(_sample_spec())


# --- edge cases ---


def test_empty_spec_html():
    spec = ArchSpec(name="Empty", provider="aws", region="us-east-1")
    html = render_html(spec)
    assert "<html" in html
    assert "Empty" in html


def test_gcp_provider_badge():
    spec = ArchSpec(
        name="GCP App",
        provider="gcp",
        region="us-central1",
        components=[
            Component(id="vm", service="compute_engine", provider="gcp", label="VM", tier=2),
        ],
        connections=[],
    )
    html = render_html(spec)
    assert "GCP" in html
    assert "badge-gcp" in html


def test_no_connections_skips_topology_page():
    spec = ArchSpec(
        name="No Conn",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
        ],
        connections=[],
    )
    html = render_html(spec)
    assert "Network Topology" not in html


# --- template parametrize ---


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.stem)
def test_all_templates_html(template):
    spec = ArchSpec.from_file(template)
    html = render_html(spec)
    assert "<html" in html
    assert spec.name in html
