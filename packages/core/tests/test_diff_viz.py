"""Tests for diff visualization."""

from __future__ import annotations

from cloudwright.differ import Differ
from cloudwright.exporter.diff_diagram import diff_to_react_flow_props, render_diff_d2
from cloudwright.spec import ArchSpec, Component, Connection, CostEstimate


def _base_spec() -> ArchSpec:
    return ArchSpec(
        name="Base",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
        connections=[Connection(source="web", target="db")],
    )


def test_added_component_green():
    old = _base_spec()
    new = ArchSpec(
        name="Base",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
            Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=2),
        ],
        connections=[Connection(source="web", target="db")],
    )
    diff = Differ().diff(old, new)
    output = render_diff_d2(old, new, diff)
    assert "[ADDED]" in output
    assert "#059669" in output
    assert "#064e3b" in output


def test_removed_component_red():
    old = _base_spec()
    new = ArchSpec(
        name="Base",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
        ],
        connections=[],
    )
    diff = Differ().diff(old, new)
    output = render_diff_d2(old, new, diff)
    assert "[REMOVED]" in output
    assert "#dc2626" in output
    assert "#450a0a" in output


def test_changed_component_yellow():
    old = _base_spec()
    new = ArchSpec(
        name="Base",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web Updated", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
        connections=[Connection(source="web", target="db")],
    )
    diff = Differ().diff(old, new)
    output = render_diff_d2(old, new, diff)
    assert "#d97706" in output
    assert "#451a03" in output


def test_new_connection_dashed_green():
    old = _base_spec()
    new = ArchSpec(
        name="Base",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
            Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=2),
        ],
        connections=[
            Connection(source="web", target="db"),
            Connection(source="web", target="cache"),
        ],
    )
    diff = Differ().diff(old, new)
    output = render_diff_d2(old, new, diff)
    # New connection should have green stroke and dash
    assert "#059669" in output
    assert "stroke-dash" in output


def test_removed_connection_red():
    old = _base_spec()
    new = ArchSpec(
        name="Base",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
        connections=[],
    )
    diff = Differ().diff(old, new)
    output = render_diff_d2(old, new, diff)
    assert "#dc2626" in output
    assert "stroke-dash" in output


def test_no_changes_all_unchanged():
    spec = _base_spec()
    diff = Differ().diff(spec, spec)
    output = render_diff_d2(spec, spec, diff)
    # No added/removed badges
    assert "[ADDED]" not in output
    assert "[REMOVED]" not in output
    # Unchanged color present
    assert "#475569" in output


def test_diff_legend_present():
    spec = _base_spec()
    diff = Differ().diff(spec, spec)
    output = render_diff_d2(spec, spec, diff)
    assert "Diff Legend" in output
    assert "Added" in output
    assert "Removed" in output
    assert "Changed" in output


def test_cost_delta_annotation():
    old = ArchSpec(
        name="Base",
        components=[Component(id="web", service="ec2", provider="aws", label="Web", tier=2)],
        connections=[],
        cost_estimate=CostEstimate(monthly_total=100.0),
    )
    new = ArchSpec(
        name="Base",
        components=[Component(id="web", service="ec2", provider="aws", label="Web", tier=2)],
        connections=[],
        cost_estimate=CostEstimate(monthly_total=150.0),
    )
    diff = Differ().diff(old, new)
    output = render_diff_d2(old, new, diff)
    assert "cost_delta" in output
    assert "+$50.00/mo" in output


def test_react_flow_props_structure():
    spec = _base_spec()
    diff = Differ().diff(spec, spec)
    props = diff_to_react_flow_props(spec, spec, diff)
    assert "node_styles" in props
    assert "edge_styles" in props
    assert "annotations" in props
    assert isinstance(props["node_styles"], dict)
    assert isinstance(props["edge_styles"], dict)
    assert isinstance(props["annotations"], list)


def test_react_flow_added_node_badge():
    old = _base_spec()
    new = ArchSpec(
        name="Base",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
            Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=2),
        ],
        connections=[Connection(source="web", target="db")],
    )
    diff = Differ().diff(old, new)
    props = diff_to_react_flow_props(old, new, diff)
    cache_style = props["node_styles"].get("cache")
    assert cache_style is not None
    assert cache_style["badge"] == "ADDED"
    assert cache_style["borderColor"] == "#059669"
