"""Simplified Sugiyama layered graph layout for ArchSpec diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec


@dataclass
class NodePosition:
    node_id: str
    x: float
    y: float
    width: float = 200.0
    height: float = 80.0


@dataclass
class BoundaryRect:
    boundary_id: str
    x: float
    y: float
    width: float
    height: float


@dataclass
class EdgeWaypoint:
    source: str
    target: str
    points: list[tuple[float, float]]


@dataclass
class LayoutResult:
    positions: list[NodePosition]
    boundary_rects: list[BoundaryRect]
    edge_waypoints: list[EdgeWaypoint]
    width: float
    height: float


def compute_layout(
    spec: "ArchSpec",
    *,
    node_width: float = 200.0,
    node_height: float = 80.0,
    h_gap: float = 40.0,
    v_gap: float = 120.0,
    boundary_padding: float = 40.0,
) -> LayoutResult:
    if not spec.components:
        return LayoutResult(positions=[], boundary_rects=[], edge_waypoints=[], width=0.0, height=0.0)

    # Layer assignment from component.tier (default 2 if not set)
    layers: dict[int, list[str]] = {}
    for comp in spec.components:
        tier = comp.tier if comp.tier is not None else 2
        layers.setdefault(tier, []).append(comp.id)

    sorted_tiers = sorted(layers.keys())
    ordered_layers: list[list[str]] = [layers[t] for t in sorted_tiers]

    # Build adjacency for barycenter sweeps
    node_set = {c.id for c in spec.components}
    neighbors_down: dict[str, list[str]] = {c.id: [] for c in spec.components}
    neighbors_up: dict[str, list[str]] = {c.id: [] for c in spec.components}
    for conn in spec.connections:
        if conn.source in node_set and conn.target in node_set:
            neighbors_down[conn.source].append(conn.target)
            neighbors_up[conn.target].append(conn.source)

    def _sort_by_barycenter(layer: list[str], ref: dict[str, float]) -> list[str]:
        def bc(node_id: str) -> float:
            nbrs = [ref[n] for n in neighbors_down.get(node_id, []) + neighbors_up.get(node_id, []) if n in ref]
            return sum(nbrs) / len(nbrs) if nbrs else 0.0

        return sorted(layer, key=bc)

    def _layer_positions(layer: list[str]) -> dict[str, float]:
        return {nid: float(i) for i, nid in enumerate(layer)}

    # 12 top-down + 12 bottom-up barycenter sweeps
    for _ in range(12):
        ref: dict[str, float] = {}
        for i, layer in enumerate(ordered_layers):
            if i > 0:
                ordered_layers[i] = _sort_by_barycenter(layer, ref)
            ref.update(_layer_positions(ordered_layers[i]))

    for _ in range(12):
        ref = {}
        for i in range(len(ordered_layers) - 1, -1, -1):
            layer = ordered_layers[i]
            if i < len(ordered_layers) - 1:
                ordered_layers[i] = _sort_by_barycenter(layer, ref)
            ref.update(_layer_positions(ordered_layers[i]))

    # Coordinate assignment — center each layer relative to the widest
    max_layer_px = max(len(layer) * (node_width + h_gap) - h_gap for layer in ordered_layers)

    pos_map: dict[str, NodePosition] = {}
    for row, layer in enumerate(ordered_layers):
        layer_px = len(layer) * (node_width + h_gap) - h_gap
        x_offset = (max_layer_px - layer_px) / 2.0
        y = row * (node_height + v_gap)
        for col, node_id in enumerate(layer):
            x = x_offset + col * (node_width + h_gap)
            pos_map[node_id] = NodePosition(node_id=node_id, x=x, y=y, width=node_width, height=node_height)

    # Boundary rects: bounding box of contained components + padding
    boundary_rects: list[BoundaryRect] = []
    for boundary in spec.boundaries:
        members = [pos_map[cid] for cid in boundary.component_ids if cid in pos_map]
        if not members:
            continue
        min_x = min(p.x for p in members) - boundary_padding
        min_y = min(p.y for p in members) - boundary_padding
        max_x = max(p.x + p.width for p in members) + boundary_padding
        max_y = max(p.y + p.height for p in members) + boundary_padding
        boundary_rects.append(
            BoundaryRect(
                boundary_id=boundary.id,
                x=min_x,
                y=min_y,
                width=max_x - min_x,
                height=max_y - min_y,
            )
        )

    # Edge waypoints: straight line from source center-bottom to target center-top
    edge_waypoints: list[EdgeWaypoint] = []
    for conn in spec.connections:
        src = pos_map.get(conn.source)
        tgt = pos_map.get(conn.target)
        if src is None or tgt is None:
            continue
        edge_waypoints.append(
            EdgeWaypoint(
                source=conn.source,
                target=conn.target,
                points=[
                    (src.x + src.width / 2, src.y + src.height),
                    (tgt.x + tgt.width / 2, tgt.y),
                ],
            )
        )

    all_pos = list(pos_map.values())
    canvas_w = max(p.x + p.width for p in all_pos)
    canvas_h = max(p.y + p.height for p in all_pos)

    return LayoutResult(
        positions=all_pos,
        boundary_rects=boundary_rects,
        edge_waypoints=edge_waypoints,
        width=canvas_w,
        height=canvas_h,
    )
