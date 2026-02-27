"""Mermaid flowchart exporter for ArchSpec."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_TIER_LABELS: dict[int, str] = {
    0: "Edge",
    1: "Ingress",
    2: "Compute",
    3: "Data",
    4: "Storage",
}


def _safe_id(raw: str) -> str:
    """Strip anything Mermaid can't handle in node IDs."""
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


def render(spec: "ArchSpec") -> str:
    lines: list[str] = ["flowchart TD"]

    # Group by tier
    tiers: dict[int, list] = {}
    for c in spec.components:
        tiers.setdefault(c.tier, []).append(c)

    for tier_num in sorted(tiers):
        tier_label = _TIER_LABELS.get(tier_num, f"Tier {tier_num}")
        header = f"Tier {tier_num} - {tier_label}"
        lines.append(f'    subgraph "{header}"')
        for c in tiers[tier_num]:
            node_id = _safe_id(c.id)
            lines.append(f"        {node_id}[{c.label}]")
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

    return "\n".join(lines)
