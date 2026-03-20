"""Render an ArchSpec as an ASCII architecture diagram for terminal display."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_TIER_LABELS = {
    0: "Edge",
    1: "Ingress",
    2: "Compute",
    3: "Data",
    4: "Storage",
}

_WIDTH = 72
_TIER_INNER = _WIDTH - 8  # content area inside tier boxes
_MAX_CELL = 20  # max width per component cell


def render(spec: "ArchSpec") -> str:
    """Render an ArchSpec as a boxed ASCII architecture diagram."""
    tiers: dict[int, list[tuple[str, str]]] = {}
    for c in spec.components:
        tiers.setdefault(c.tier, []).append((c.service, c.label))

    lines: list[str] = []
    inner = _WIDTH - 4  # inside the outer box

    # Header
    lines.append("+" + "=" * (_WIDTH - 2) + "+")
    lines.append(_pad(f"  {spec.name}", inner))
    region = spec.region or ""
    provider = (spec.provider or "").upper()
    meta = f"  {provider} / {region}  --  {len(spec.components)} services  --  {len(spec.connections)} connections"
    lines.append(_pad(meta, inner))
    lines.append("+" + "=" * (_WIDTH - 2) + "+")

    # Tiers
    sorted_tiers = sorted(tiers.keys())
    for i, tier_num in enumerate(sorted_tiers):
        components = tiers[tier_num]
        tier_label = _TIER_LABELS.get(tier_num, f"Tier {tier_num}")

        lines.append(_pad("", inner))

        # Tier box top with label
        box_w = inner - 4  # tier box width
        label_part = f"-- {tier_label} "
        dash_rest = "-" * (box_w - len(label_part) - 1)
        lines.append(_pad(f"  +{label_part}{dash_rest}+", inner))

        # Component rows (fit within tier box)
        for row_start in range(0, len(components), 3):
            row = components[row_start : row_start + 3]
            cells = []
            for service, _label in row:
                cells.append(f"[{service}]")
            row_text = "  |  " + "  ".join(cells)
            # Pad to tier box width
            pad_needed = box_w - len(row_text) + 2
            if pad_needed > 0:
                row_text += " " * pad_needed + "|"
            else:
                row_text = row_text[: box_w + 2] + "|"
            lines.append(_pad(row_text, inner))

        # Tier box bottom
        lines.append(_pad("  +" + "-" * box_w + "+", inner))

        # Arrow between tiers
        if i < len(sorted_tiers) - 1:
            mid = inner // 2
            lines.append(_pad(" " * mid + "|", inner))
            lines.append(_pad(" " * mid + "v", inner))

    lines.append(_pad("", inner))

    # Connection summary
    if spec.connections:
        lines.append(_pad("  Connections:", inner))
        shown = min(6, len(spec.connections))
        for conn in spec.connections[:shown]:
            arrow = f"    {conn.source} --> {conn.target}"
            if conn.label:
                max_label = inner - len(arrow) - 5
                lbl = conn.label if len(conn.label) <= max_label else conn.label[: max_label - 2] + ".."
                arrow += f"  ({lbl})"
            if len(arrow) > inner:
                arrow = arrow[: inner - 3] + "..."
            lines.append(_pad(arrow, inner))
        if len(spec.connections) > shown:
            lines.append(_pad(f"    ... +{len(spec.connections) - shown} more", inner))

    lines.append(_pad("", inner))
    lines.append("+" + "=" * (_WIDTH - 2) + "+")
    lines.append("Designed with Cloudwright")

    return "\n".join(lines)


def _pad(text: str, inner: int) -> str:
    """Wrap text in outer box borders, padded to fixed width."""
    if len(text) > inner:
        text = text[:inner]
    return "| " + text + " " * (inner - len(text)) + " |"
