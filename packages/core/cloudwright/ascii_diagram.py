"""ASCII/Unicode box-drawing diagram renderer for ArchSpec."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.icons import get_icon_or_default

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component

_TIER_LABELS: dict[int, str] = {
    0: "Edge",
    1: "Ingress",
    2: "Compute",
    3: "Data",
    4: "Storage",
}

# ANSI category colors — approximate terminal codes for dark-theme output
_ANSI_CATEGORY: dict[str, str] = {
    "compute": "\033[92m",
    "database": "\033[95m",
    "storage": "\033[94m",
    "network": "\033[94m",
    "security": "\033[91m",
    "serverless": "\033[93m",
    "cache": "\033[95m",
    "queue": "\033[33m",
    "cdn": "\033[94m",
    "monitoring": "\033[96m",
    "ml": "\033[35m",
    "analytics": "\033[35m",
}
_ANSI_RESET = "\033[0m"
_MIN_BOX_INNER = 10  # minimum inner width


def _ansi(category: str, text: str) -> str:
    code = _ANSI_CATEGORY.get(category, "")
    if not code:
        return text
    return f"{code}{text}{_ANSI_RESET}"


def _edge_label(conn) -> str:
    if conn.protocol and conn.port:
        return f"{conn.protocol}:{conn.port}"
    if conn.protocol:
        return conn.protocol
    if conn.port:
        return str(conn.port)
    return conn.label or ""


def _content_lines(comp: "Component") -> tuple[str, str]:
    """Return the two raw (uncolored) content strings for a component box."""
    icon = get_icon_or_default(comp.provider, comp.service)
    char = icon.ascii_char
    count = comp.config.get("count", 1) if comp.config else 1
    line1 = f"[{char}] {comp.label}"
    if count and int(count) > 1:
        line2 = f"{comp.service} (x{count})"
    else:
        line2 = comp.service
    return line1, line2


def _render_box(comp: "Component", color: bool, inner: int) -> list[str]:
    """Return lines for a single box sized to `inner` width."""
    icon = get_icon_or_default(comp.provider, comp.service)
    category = icon.category
    line1_raw, line2_raw = _content_lines(comp)

    line1 = line1_raw.center(inner)
    line2 = line2_raw.center(inner)

    if color:
        line1 = _ansi(category, line1)
        line2 = _ansi(category, line2)

    top = f"┌{'─' * inner}┐"
    bot = f"└{'─' * inner}┘"
    return [top, f"│{line1}│", f"│{line2}│", bot]


def _box_inner_width(comp: "Component") -> int:
    """Compute the minimum inner width needed to fit a component's content."""
    line1, line2 = _content_lines(comp)
    return max(_MIN_BOX_INNER, len(line1), len(line2))


def _connection_arrow(label: str, box_total_w: int) -> list[str]:
    """Vertical arrow lines centered under the first box."""
    # Center position is middle of first box
    center = box_total_w // 2
    pad = " " * center
    lines = [f"{pad}│"]
    if label:
        lines.append(f"{pad} {label}")
    lines.append(f"{pad}▼")
    return lines


def _merge_boxes_with_arrows(boxes: list[list[str]]) -> list[str]:
    """Merge boxes side-by-side, inserting ──▶ between them at the content row."""
    max_h = max(len(b) for b in boxes)
    # All boxes have the same height (4 lines), but pad just in case
    widths = [len(b[0]) for b in boxes]  # visual width from top border
    arrow = "──▶"
    arrow_row = 2  # second content line (0=top, 1=line1, 2=line2, 3=bot)

    result = []
    for row in range(max_h):
        parts = []
        for i, box in enumerate(boxes):
            if row < len(box):
                parts.append(box[row])
            else:
                parts.append(" " * widths[i])
            if i < len(boxes) - 1:
                parts.append(arrow if row == arrow_row else " " * len(arrow))
        result.append("".join(parts))
    return result


def render_ascii(spec: "ArchSpec", *, color: bool = True, width: int = 80) -> str:
    """Render an ArchSpec as a Unicode box-drawing diagram.

    Groups components by tier, draws them side-by-side within a tier,
    and connects tiers with vertical arrows.
    """
    lines: list[str] = []

    title = f"{spec.name} ({spec.provider.upper()} / {spec.region})"
    lines.append(title.center(width))
    lines.append("")

    if not spec.components:
        lines.append("  (no components)")
        return "\n".join(lines)

    conn_by_source: dict[str, list] = {}
    for conn in spec.connections:
        conn_by_source.setdefault(conn.source, []).append(conn)

    tiers: dict[int, list] = {}
    for c in spec.components:
        tiers.setdefault(c.tier, []).append(c)

    sorted_tiers = sorted(tiers.keys())
    indent = "  "

    # Compute per-tier inner box width (all boxes in a tier share the same width)
    tier_inner: dict[int, int] = {}
    for tier_num, comps in tiers.items():
        tier_inner[tier_num] = max(_box_inner_width(c) for c in comps)

    # Decide how many boxes fit per row given the terminal width
    def cols_for_tier(tier_num: int) -> int:
        inner = tier_inner[tier_num]
        box_w = inner + 2  # +2 for the │ borders
        arrow_w = 3  # ──▶
        usable = width - len(indent)
        if usable < box_w:
            return 1
        n = 1
        while (n + 1) * box_w + n * arrow_w <= usable:
            n += 1
        return n

    for tier_idx, tier_num in enumerate(sorted_tiers):
        components = tiers[tier_num]
        inner = tier_inner[tier_num]
        cols = cols_for_tier(tier_num)

        for row_start in range(0, len(components), cols):
            row_comps = components[row_start : row_start + cols]
            boxes = [_render_box(c, color, inner) for c in row_comps]

            if len(boxes) == 1:
                for bline in boxes[0]:
                    lines.append(f"{indent}{bline}")
            else:
                for bline in _merge_boxes_with_arrows(boxes):
                    lines.append(f"{indent}{bline}")

        # Vertical arrow to next tier
        if tier_idx < len(sorted_tiers) - 1:
            next_tier = sorted_tiers[tier_idx + 1]
            next_ids = {c.id for c in tiers[next_tier]}

            arrow_label = ""
            for c in tiers[tier_num]:
                for conn in conn_by_source.get(c.id, []):
                    if conn.target in next_ids:
                        arrow_label = _edge_label(conn)
                        break
                if arrow_label:
                    break

            box_total_w = inner + 2 + len(indent)
            for al in _connection_arrow(arrow_label, box_total_w):
                lines.append(al)

    lines.append("")
    return "\n".join(lines)


def render_summary(spec: "ArchSpec") -> str:
    """One-line summary: component count, provider, optional cost, region."""
    n = len(spec.components)
    parts = [f"Components: {n}  |  {spec.provider.upper()}"]
    if spec.cost_estimate is not None:
        total = spec.cost_estimate.monthly_total
        parts.append(f"Est. ${total:,.0f}/mo")
    parts.append(f"Region: {spec.region}")
    return "  " + "  |  ".join(parts)


def render_next_steps() -> str:
    return (
        "Next steps:\n"
        "  cloudwright cost          Cost breakdown\n"
        "  cloudwright validate      Compliance check\n"
        "  cloudwright export tf     Generate Terraform\n"
        "  cloudwright export d2     D2 diagram\n"
        "  cloudwright chat          Interactive refinement"
    )
