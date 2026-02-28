"""Mermaid flowchart exporter for ArchSpec."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from cloudwright.icons import get_icon_or_default

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_TIER_LABELS: dict[int, str] = {
    0: "Edge",
    1: "Ingress",
    2: "Compute",
    3: "Data",
    4: "Storage",
}

_CLASSDEFS = """\
    classDef compute fill:#1e293b,stroke:#10b981,color:#f8fafc
    classDef database fill:#1e293b,stroke:#8b5cf6,color:#f8fafc
    classDef storage fill:#1e293b,stroke:#6366f1,color:#f8fafc
    classDef network fill:#1e293b,stroke:#3b82f6,color:#f8fafc
    classDef serverless fill:#1e293b,stroke:#f59e0b,color:#f8fafc
    classDef security fill:#1e293b,stroke:#ef4444,color:#f8fafc
    classDef cache fill:#1e293b,stroke:#8b5cf6,color:#f8fafc
    classDef queue fill:#1e293b,stroke:#f97316,color:#f8fafc
    classDef cdn fill:#1e293b,stroke:#3b82f6,color:#f8fafc
    classDef monitoring fill:#1e293b,stroke:#06b6d4,color:#f8fafc
    classDef ml fill:#1e293b,stroke:#ec4899,color:#f8fafc
    classDef analytics fill:#1e293b,stroke:#a855f7,color:#f8fafc"""


def _safe_id(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)


def _edge_label(conn) -> str:
    parts = []
    if conn.protocol:
        parts.append(conn.protocol)
    if conn.port:
        parts.append(str(conn.port))
    if conn.label:
        # Use connection label when present; append port/protocol if also set
        label = conn.label
        if parts:
            label = f"{label} ({'/'.join(parts)})"
        return label
    return "/".join(parts) if parts else ""


def _node_syntax(node_id: str, label: str, shape: str) -> str:
    if shape == "cylinder":
        return f"{node_id}[({label})]"
    if shape == "hexagon":
        return f"{node_id}{{{{{label}}}}}"
    if shape == "stadium":
        return f"{node_id}([{label}])"
    if shape == "parallelogram":
        return f"{node_id}[/{label}/]"
    return f"{node_id}[{label}]"


def render(spec: "ArchSpec") -> str:
    lines: list[str] = ["flowchart TD"]
    lines.append(_CLASSDEFS)

    use_boundaries = bool(spec.boundaries)

    # category lookup for class assignment
    category_by_id: dict[str, str] = {}
    for c in spec.components:
        icon = get_icon_or_default(c.provider, c.service)
        category_by_id[c.id] = icon.category

    if use_boundaries:
        comp_to_boundary: dict[str, str] = {}
        for b in spec.boundaries:
            for cid in b.component_ids:
                comp_to_boundary[cid] = b.id

        unassigned = [c for c in spec.components if c.id not in comp_to_boundary]

        for b in spec.boundaries:
            label = b.label or b.id
            lines.append(f'    subgraph "{label}"')
            for c in spec.components:
                if comp_to_boundary.get(c.id) == b.id:
                    node_id = _safe_id(c.id)
                    icon = get_icon_or_default(c.provider, c.service)
                    lines.append(f"        {_node_syntax(node_id, c.label, icon.shape)}")
                    lines.append(f"        class {node_id} {icon.category}")
            lines.append("    end")

        for c in unassigned:
            node_id = _safe_id(c.id)
            icon = get_icon_or_default(c.provider, c.service)
            lines.append(f"    {_node_syntax(node_id, c.label, icon.shape)}")
            lines.append(f"    class {node_id} {icon.category}")
    else:
        # Tier-based grouping (fallback)
        tiers: dict[int, list] = {}
        for c in spec.components:
            tiers.setdefault(c.tier, []).append(c)

        for tier_num in sorted(tiers):
            tier_label = _TIER_LABELS.get(tier_num, f"Tier {tier_num}")
            header = f"Tier {tier_num} - {tier_label}"
            lines.append(f'    subgraph "{header}"')
            for c in tiers[tier_num]:
                node_id = _safe_id(c.id)
                icon = get_icon_or_default(c.provider, c.service)
                lines.append(f"        {_node_syntax(node_id, c.label, icon.shape)}")
                lines.append(f"        class {node_id} {icon.category}")
            lines.append("    end")

    if spec.connections:
        lines.append("")

    for conn in spec.connections:
        src = _safe_id(conn.source)
        tgt = _safe_id(conn.target)
        label = _edge_label(conn)
        if label:
            lines.append(f"    {src} -->|{label}| {tgt}")
        else:
            lines.append(f"    {src} --> {tgt}")

    # linkStyle directives for edge coloring
    if spec.connections:
        for i in range(len(spec.connections)):
            lines.append(f"    linkStyle {i} stroke:#475569,stroke-width:2px")

    return "\n".join(lines)
