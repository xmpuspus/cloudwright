"""Tests for the Sugiyama layout engine."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from cloudwright import ArchSpec
from cloudwright.layout import LayoutResult, compute_layout
from cloudwright.spec import Boundary, Component, Connection

TEMPLATE_DIR = Path(__file__).parents[3] / "catalog" / "templates"
TEMPLATES = [p for p in sorted(TEMPLATE_DIR.glob("*.yaml")) if p.name != "_index.yaml"]


def _make_spec(**kwargs) -> ArchSpec:
    return ArchSpec(name="Test", provider="aws", region="us-east-1", **kwargs)


def test_single_component_layout():
    spec = _make_spec(
        components=[Component(id="web", service="ec2", provider="aws", label="Web", tier=0)],
    )
    result = compute_layout(spec)
    assert len(result.positions) == 1
    pos = result.positions[0]
    assert pos.node_id == "web"
    # Single node: x_start = (layer_w - layer_w) / 2 = 0
    assert pos.x == 0.0
    assert pos.y == 0.0


def test_two_tier_layout():
    spec = _make_spec(
        components=[
            Component(id="top", service="alb", provider="aws", label="ALB", tier=0),
            Component(id="bot", service="ec2", provider="aws", label="EC2", tier=1),
        ],
        connections=[Connection(source="top", target="bot")],
    )
    result = compute_layout(spec)
    pos = {p.node_id: p for p in result.positions}
    # Tier 0 must be above tier 1 (smaller y)
    assert pos["top"].y < pos["bot"].y


def test_same_tier_horizontal():
    spec = _make_spec(
        components=[Component(id=f"svc{i}", service="ec2", provider="aws", label=f"Svc{i}", tier=2) for i in range(3)],
    )
    result = compute_layout(spec)
    assert len(result.positions) == 3
    ys = {p.y for p in result.positions}
    xs = sorted(p.x for p in result.positions)
    # All at the same vertical position
    assert len(ys) == 1
    # Each subsequent node is further right
    assert xs[0] < xs[1] < xs[2]


def test_layout_result_fields():
    spec = _make_spec(
        components=[
            Component(id="a", service="ec2", provider="aws", label="A", tier=0),
            Component(id="b", service="rds", provider="aws", label="B", tier=1),
        ],
        connections=[Connection(source="a", target="b")],
    )
    result = compute_layout(spec)
    assert isinstance(result, LayoutResult)
    assert isinstance(result.positions, list)
    assert isinstance(result.boundary_rects, list)
    assert isinstance(result.edge_waypoints, list)
    assert result.width > 0
    assert result.height > 0


def test_boundary_rect_computation():
    spec = _make_spec(
        components=[
            Component(id="a", service="ec2", provider="aws", label="A", tier=0),
            Component(id="b", service="ec2", provider="aws", label="B", tier=0),
        ],
        boundaries=[Boundary(id="vpc1", kind="vpc", label="VPC", component_ids=["a", "b"])],
    )
    result = compute_layout(spec, boundary_padding=40.0)
    assert len(result.boundary_rects) == 1
    rect = result.boundary_rects[0]
    assert rect.boundary_id == "vpc1"

    pos = {p.node_id: p for p in result.positions}
    # Rect must enclose both nodes with padding
    for nid in ("a", "b"):
        p = pos[nid]
        assert rect.x <= p.x
        assert rect.y <= p.y
        assert rect.x + rect.width >= p.x + p.width
        assert rect.y + rect.height >= p.y + p.height


def test_edge_waypoints():
    spec = _make_spec(
        components=[
            Component(id="src", service="alb", provider="aws", label="ALB", tier=0),
            Component(id="tgt", service="ec2", provider="aws", label="EC2", tier=1),
        ],
        connections=[Connection(source="src", target="tgt")],
    )
    result = compute_layout(spec, node_width=200.0, node_height=80.0)
    assert len(result.edge_waypoints) == 1
    wp = result.edge_waypoints[0]
    assert wp.source == "src"
    assert wp.target == "tgt"
    assert len(wp.points) == 2

    pos = {p.node_id: p for p in result.positions}
    src_p = pos["src"]
    tgt_p = pos["tgt"]

    # First point is source center-bottom
    assert wp.points[0] == (src_p.x + src_p.width / 2, src_p.y + src_p.height)
    # Second point is target center-top
    assert wp.points[1] == (tgt_p.x + tgt_p.width / 2, tgt_p.y)


def test_empty_spec():
    spec = _make_spec(components=[], connections=[])
    result = compute_layout(spec)
    assert result.positions == []
    assert result.boundary_rects == []
    assert result.edge_waypoints == []
    assert result.width == 0.0
    assert result.height == 0.0


def test_wide_spec_performance():
    components = [
        Component(id=f"svc{i}", service="ec2", provider="aws", label=f"Service {i}", tier=i % 4) for i in range(12)
    ]
    connections = [Connection(source=f"svc{i}", target=f"svc{i + 1}") for i in range(11)]
    spec = _make_spec(components=components, connections=connections)

    start = time.perf_counter()
    result = compute_layout(spec)
    elapsed = time.perf_counter() - start

    assert len(result.positions) == 12
    assert elapsed < 1.0


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.stem)
def test_all_templates(template):
    spec = ArchSpec.from_file(template)
    result = compute_layout(spec)
    assert len(result.positions) == len(spec.components)
