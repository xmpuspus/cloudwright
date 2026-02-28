"""D2 diagram exporter for ArchSpec."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from cloudwright.icons import get_category_color, get_icon_or_default, get_icon_url

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_TIER_LABELS: dict[int, str] = {
    0: "Edge",
    1: "Ingress",
    2: "Compute",
    3: "Data",
    4: "Storage",
}

# Protocols that indicate async messaging — connections to/from these services get dashed edges
_ASYNC_SERVICES = {"sqs", "sns", "pub_sub", "kinesis", "service_bus", "event_hubs"}

_D2_SHAPE_MAP = {
    "cylinder": "cylinder",
    "hexagon": "hexagon",
    "stadium": "oval",
    "parallelogram": "queue",
    "rectangle": "rectangle",
}


def _safe_id(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)


def _edge_label(conn) -> str:
    parts = []
    if conn.protocol:
        parts.append(conn.protocol)
    if conn.port:
        parts.append(str(conn.port))
    if conn.label:
        label = conn.label
        if parts:
            label = f"{label} ({'/'.join(parts)})"
        return label
    return "/".join(parts) if parts else ""


def _render_node(c, indent: str, show_icons: bool) -> list[str]:
    icon = get_icon_or_default(c.provider, c.service)
    color = get_category_color(icon.category)
    d2_shape = _D2_SHAPE_MAP.get(icon.shape, "rectangle")
    node_id = _safe_id(c.id)
    provider_badge = f" [{c.provider.upper()}]" if c.provider else ""
    lines = [f'{indent}{node_id}: "{c.label}{provider_badge}" {{']
    lines.append(f"{indent}  shape: {d2_shape}")
    if show_icons:
        icon_url = get_icon_url(c.provider, c.service)
        lines.append(f"{indent}  icon: {icon_url}")
    lines.append(f'{indent}  style.fill: "#1e293b"')
    lines.append(f'{indent}  style.stroke: "{color}"')
    lines.append(f'{indent}  style.font-color: "#F8FAFC"')
    lines.append(f"{indent}}}")
    return lines


def render(spec: "ArchSpec", *, theme: str = "dark", show_boundaries: bool = True, show_icons: bool = True) -> str:
    lines: list[str] = []
    lines.append(f"# {spec.name}")
    lines.append("")
    lines.append("vars: {")
    lines.append("  d2-config: {")
    lines.append("    theme-id: 200")
    lines.append("    layout-engine: elk")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    # Track which container each component belongs to (for edge path resolution)
    comp_container: dict[str, str] = {}

    use_boundaries = show_boundaries and bool(spec.boundaries)

    if use_boundaries:
        # Map component id -> boundary id (last boundary wins if overlapping)
        comp_to_boundary: dict[str, str] = {}
        for b in spec.boundaries:
            for cid in b.component_ids:
                comp_to_boundary[cid] = b.id

        # Components not assigned to any boundary go in a top-level group
        unassigned = [c for c in spec.components if c.id not in comp_to_boundary]

        for b in spec.boundaries:
            container_id = _safe_id(b.id)
            label = b.label or b.id
            lines.append(f'{container_id}: "{label}" {{')
            for c in spec.components:
                if comp_to_boundary.get(c.id) == b.id:
                    comp_container[c.id] = container_id
                    for node_line in _render_node(c, "  ", show_icons):
                        lines.append(node_line)
            lines.append("}")
            lines.append("")

        for c in unassigned:
            comp_container[c.id] = ""
            for node_line in _render_node(c, "", show_icons):
                lines.append(node_line)
        if unassigned:
            lines.append("")
    else:
        # Tier-based grouping (fallback)
        tiers: dict[int, list] = {}
        for c in spec.components:
            tiers.setdefault(c.tier, []).append(c)

        for tier_num in sorted(tiers):
            tier_label = _TIER_LABELS.get(tier_num, f"Tier {tier_num}")
            container_id = _safe_id(f"tier_{tier_num}")
            lines.append(f"{container_id}: {tier_label} {{")
            for c in tiers[tier_num]:
                comp_container[c.id] = container_id
                for node_line in _render_node(c, "  ", show_icons):
                    lines.append(node_line)
            lines.append("}")
            lines.append("")

    # Build a service lookup for async detection
    service_by_id = {c.id: c.service for c in spec.components}

    for conn in spec.connections:
        src_container = comp_container.get(conn.source, "")
        tgt_container = comp_container.get(conn.target, "")
        src_id = _safe_id(conn.source)
        tgt_id = _safe_id(conn.target)

        src_path = f"{src_container}.{src_id}" if src_container else src_id
        tgt_path = f"{tgt_container}.{tgt_id}" if tgt_container else tgt_id

        label = _edge_label(conn)
        is_async = (
            service_by_id.get(conn.source, "") in _ASYNC_SERVICES
            or service_by_id.get(conn.target, "") in _ASYNC_SERVICES
        )

        if label:
            lines.append(f"{src_path} -> {tgt_path}: {label} {{")
        else:
            lines.append(f"{src_path} -> {tgt_path}: {{")

        if is_async:
            lines.append("  style.stroke-dash: 5")
        lines.append("}")

    # Legend
    lines.append("")
    lines.append("legend: Legend {")
    seen: set[str] = set()
    for c in spec.components:
        icon = get_icon_or_default(c.provider, c.service)
        if icon.category not in seen:
            seen.add(icon.category)
            color = get_category_color(icon.category)
            cat_id = _safe_id(icon.category)
            lines.append(f'  {cat_id}: "{icon.category}" {{')
            lines.append(f'    style.fill: "{color}"')
            lines.append('    style.font-color: "#F8FAFC"')
            lines.append("  }")
    lines.append("}")

    return "\n".join(lines)
