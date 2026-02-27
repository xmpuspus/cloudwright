"""D2 diagram exporter for ArchSpec."""

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


def render(spec: "ArchSpec") -> str:
    lines: list[str] = []
    lines.append(f"# {spec.name}")
    lines.append("")

    tiers: dict[int, list] = {}
    for c in spec.components:
        tiers.setdefault(c.tier, []).append(c)

    for tier_num in sorted(tiers):
        tier_label = _TIER_LABELS.get(tier_num, f"Tier {tier_num}")
        container_id = _safe_id(f"tier_{tier_num}")
        lines.append(f"{container_id}: {tier_label} {{")
        for c in tiers[tier_num]:
            node_id = _safe_id(c.id)
            provider_badge = f" [{c.provider.upper()}]" if c.provider else ""
            lines.append(f'  {node_id}: "{c.label}{provider_badge}"')
        lines.append("}")
        lines.append("")

    for conn in spec.connections:
        src_tier = None
        tgt_tier = None
        for tier_num, comps in tiers.items():
            for c in comps:
                if c.id == conn.source:
                    src_tier = tier_num
                if c.id == conn.target:
                    tgt_tier = tier_num

        src_container = _safe_id(f"tier_{src_tier}") if src_tier is not None else ""
        tgt_container = _safe_id(f"tier_{tgt_tier}") if tgt_tier is not None else ""
        src_id = _safe_id(conn.source)
        tgt_id = _safe_id(conn.target)

        src_path = f"{src_container}.{src_id}" if src_container else src_id
        tgt_path = f"{tgt_container}.{tgt_id}" if tgt_container else tgt_id

        label = _edge_label(conn)
        if label:
            lines.append(f"{src_path} -> {tgt_path}: {label}")
        else:
            lines.append(f"{src_path} -> {tgt_path}")

    return "\n".join(lines)
