"""Diff visualization overlay for ArchSpec changes.

Produces D2 diagram source with color-coded overlays:
- Green: added components/connections
- Red: removed components/connections
- Yellow: changed components
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, DiffResult

_ADDED_COLOR = "#059669"
_REMOVED_COLOR = "#dc2626"
_CHANGED_COLOR = "#d97706"
_UNCHANGED_COLOR = "#475569"

_ADDED_BG = "#064e3b"
_REMOVED_BG = "#450a0a"
_CHANGED_BG = "#451a03"
_UNCHANGED_BG = "#1e293b"


def _safe_id(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)


def _changed_summary(component_id: str, changed_list) -> str:
    parts = [f"{c.field}: {c.old_value!r} -> {c.new_value!r}" for c in changed_list if c.component_id == component_id]
    return "; ".join(parts)


def render_diff_d2(old_spec: "ArchSpec", new_spec: "ArchSpec", diff: "DiffResult") -> str:
    """Render a D2 diagram showing diff between two ArchSpecs.

    Components and connections are color-coded by change status.
    """
    added_ids = {c.id for c in diff.added}
    removed_ids = {c.id for c in diff.removed}
    changed_ids = {c.component_id for c in diff.changed}

    lines: list[str] = []
    lines.append(f"# Diff: {old_spec.name} -> {new_spec.name}")
    lines.append("")
    lines.append("vars: {")
    lines.append("  d2-config: {")
    lines.append("    theme-id: 200")
    lines.append("    layout-engine: elk")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    # Render all components — removed from old_spec, everything else from new_spec
    all_components = {c.id: c for c in new_spec.components}
    for c in old_spec.components:
        if c.id in removed_ids:
            all_components[c.id] = c

    for comp in all_components.values():
        node_id = _safe_id(comp.id)

        if comp.id in added_ids:
            fill = _ADDED_BG
            stroke = _ADDED_COLOR
            label = f"[ADDED] {comp.label}"
        elif comp.id in removed_ids:
            fill = _REMOVED_BG
            stroke = _REMOVED_COLOR
            label = f"[REMOVED] {comp.label}"
        elif comp.id in changed_ids:
            fill = _CHANGED_BG
            stroke = _CHANGED_COLOR
            label = comp.label
        else:
            fill = _UNCHANGED_BG
            stroke = _UNCHANGED_COLOR
            label = comp.label

        provider_badge = f" [{comp.provider.upper()}]" if comp.provider else ""
        lines.append(f'{node_id}: "{label}{provider_badge}" {{')
        lines.append("  shape: rectangle")
        lines.append(f'  style.fill: "{fill}"')
        lines.append(f'  style.stroke: "{stroke}"')
        lines.append('  style.font-color: "#F8FAFC"')

        if comp.id in removed_ids:
            lines.append("  style.stroke-dash: 5")

        if comp.id in changed_ids:
            summary = _changed_summary(comp.id, diff.changed)
            if summary:
                # D2 tooltip for change details
                lines.append(f'  tooltip: "{summary}"')

        lines.append("}")

    lines.append("")

    # Build connection change lookup
    conn_added = {(c.source, c.target) for c in diff.connection_changes if c.change_type == "added"}
    conn_removed = {(c.source, c.target) for c in diff.connection_changes if c.change_type == "removed"}
    conn_changed = {(c.source, c.target) for c in diff.connection_changes if c.change_type == "changed"}

    # Render connections from new_spec plus removed ones from old_spec
    rendered_edges: set[tuple[str, str]] = set()

    for conn in new_spec.connections:
        key = (conn.source, conn.target)
        rendered_edges.add(key)
        src = _safe_id(conn.source)
        tgt = _safe_id(conn.target)

        if key in conn_added:
            stroke = _ADDED_COLOR
            dash = True
        elif key in conn_changed:
            stroke = _CHANGED_COLOR
            dash = False
        else:
            stroke = _UNCHANGED_COLOR
            dash = False

        lines.append(f"{src} -> {tgt}: {{")
        lines.append(f'  style.stroke: "{stroke}"')
        if dash:
            lines.append("  style.stroke-dash: 5")
        lines.append("}")

    # Removed connections (exist in old but not new)
    for conn in old_spec.connections:
        key = (conn.source, conn.target)
        if key in conn_removed and key not in rendered_edges:
            src = _safe_id(conn.source)
            tgt = _safe_id(conn.target)
            lines.append(f"{src} -> {tgt}: {{")
            lines.append(f'  style.stroke: "{_REMOVED_COLOR}"')
            lines.append("  style.stroke-dash: 5")
            lines.append("}")

    lines.append("")

    # Diff legend
    lines.append("legend: Diff Legend {")
    lines.append('  added: "Added" {')
    lines.append(f'    style.fill: "{_ADDED_BG}"')
    lines.append(f'    style.stroke: "{_ADDED_COLOR}"')
    lines.append('    style.font-color: "#F8FAFC"')
    lines.append("  }")
    lines.append('  removed: "Removed" {')
    lines.append(f'    style.fill: "{_REMOVED_BG}"')
    lines.append(f'    style.stroke: "{_REMOVED_COLOR}"')
    lines.append('    style.font-color: "#F8FAFC"')
    lines.append("  }")
    lines.append('  changed: "Changed" {')
    lines.append(f'    style.fill: "{_CHANGED_BG}"')
    lines.append(f'    style.stroke: "{_CHANGED_COLOR}"')
    lines.append('    style.font-color: "#F8FAFC"')
    lines.append("  }")
    lines.append("}")

    # Cost delta annotation
    if diff.cost_delta != 0.0:
        sign = "+" if diff.cost_delta >= 0 else ""
        lines.append("")
        lines.append(f'cost_delta: "Cost delta: {sign}${diff.cost_delta:,.2f}/mo" {{')
        lines.append("  shape: text")
        color = _ADDED_COLOR if diff.cost_delta > 0 else _REMOVED_COLOR
        lines.append(f'  style.font-color: "{color}"')
        lines.append("}")

    # Summary annotation
    if diff.summary:
        safe_summary = diff.summary.replace('"', "'")
        lines.append("")
        lines.append(f'diff_summary: "{safe_summary}" {{')
        lines.append("  shape: text")
        lines.append('  style.font-color: "#94a3b8"')
        lines.append("}")

    return "\n".join(lines)


def diff_to_react_flow_props(old_spec: "ArchSpec", new_spec: "ArchSpec", diff: "DiffResult") -> dict:
    """Convert a diff into React Flow node/edge styling overrides.

    Returns dict with:
    - node_styles: {component_id: {borderColor, backgroundColor, badge}}
    - edge_styles: {edge_key: {stroke, strokeDasharray, animated}}
    - annotations: list of text annotations
    """
    added_ids = {c.id for c in diff.added}
    removed_ids = {c.id for c in diff.removed}
    changed_ids = {c.component_id for c in diff.changed}

    node_styles: dict[str, dict] = {}

    all_ids = {c.id for c in new_spec.components} | {c.id for c in old_spec.components}

    for cid in all_ids:
        if cid in added_ids:
            node_styles[cid] = {
                "borderColor": _ADDED_COLOR,
                "backgroundColor": _ADDED_BG,
                "badge": "ADDED",
                "badgeColor": _ADDED_COLOR,
            }
        elif cid in removed_ids:
            node_styles[cid] = {
                "borderColor": _REMOVED_COLOR,
                "backgroundColor": _REMOVED_BG,
                "badge": "REMOVED",
                "badgeColor": _REMOVED_COLOR,
                "opacity": 0.7,
            }
        elif cid in changed_ids:
            changes = [c for c in diff.changed if c.component_id == cid]
            node_styles[cid] = {
                "borderColor": _CHANGED_COLOR,
                "backgroundColor": _CHANGED_BG,
                "badge": "CHANGED",
                "badgeColor": _CHANGED_COLOR,
                "changes": [{"field": c.field, "oldValue": c.old_value, "newValue": c.new_value} for c in changes],
            }
        else:
            node_styles[cid] = {
                "borderColor": _UNCHANGED_COLOR,
                "backgroundColor": _UNCHANGED_BG,
            }

    conn_added = {(c.source, c.target) for c in diff.connection_changes if c.change_type == "added"}
    conn_removed = {(c.source, c.target) for c in diff.connection_changes if c.change_type == "removed"}
    conn_changed = {(c.source, c.target) for c in diff.connection_changes if c.change_type == "changed"}

    edge_styles: dict[str, dict] = {}

    all_connections = {(c.source, c.target) for c in new_spec.connections} | {
        (c.source, c.target) for c in old_spec.connections
    }

    for src, tgt in all_connections:
        key = f"{src}->{tgt}"
        if (src, tgt) in conn_added:
            edge_styles[key] = {
                "stroke": _ADDED_COLOR,
                "strokeDasharray": "5,5",
                "animated": True,
            }
        elif (src, tgt) in conn_removed:
            edge_styles[key] = {
                "stroke": _REMOVED_COLOR,
                "strokeDasharray": "5,5",
                "animated": False,
                "opacity": 0.6,
            }
        elif (src, tgt) in conn_changed:
            edge_styles[key] = {
                "stroke": _CHANGED_COLOR,
                "strokeDasharray": None,
                "animated": True,
            }
        else:
            edge_styles[key] = {
                "stroke": _UNCHANGED_COLOR,
                "animated": False,
            }

    annotations: list[str] = []
    if diff.summary:
        annotations.append(diff.summary)
    if diff.cost_delta != 0.0:
        sign = "+" if diff.cost_delta >= 0 else ""
        annotations.append(f"Cost delta: {sign}${diff.cost_delta:,.2f}/mo")

    return {
        "node_styles": node_styles,
        "edge_styles": edge_styles,
        "annotations": annotations,
    }
