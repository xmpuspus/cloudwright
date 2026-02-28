"""C4 model exporter for ArchSpec.

Supports L1 (System Context), L2 (Container), L3 (Component) diagrams
in both D2 and Mermaid output formats.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component

# Services whose icon category implies a database shape in Mermaid C4
_DB_SERVICES = {
    "rds",
    "dynamodb",
    "cloud_sql",
    "azure_sql",
    "cosmos_db",
    "redshift",
    "bigquery",
    "elasticache",
    "memorystore",
    "azure_cache",
}

# Services whose config may carry sub-resources worth expanding at L3
_EXPANDABLE_SERVICES = {"ecs", "eks", "lambda", "cloud_run", "azure_functions"}

# C4 blue palette
_C4_BLUE = "#1168bd"
_C4_LIGHT = "#438dd5"
_C4_EXTERNAL = "#999999"
_C4_DB = "#23648c"


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
    return ":".join(parts) if parts else ""


def _tech_label(c: Component) -> str:
    """Short technology string for C4 diagrams (e.g. 'CloudFront', 'RDS PostgreSQL')."""
    svc = c.service.replace("_", " ").title()
    engine = c.config.get("engine", "")
    if engine:
        return f"{svc} {engine.title()}"
    return svc


def _description(c: Component) -> str:
    if c.description:
        return c.description
    return c.label


# ---------------------------------------------------------------------------
# D2 renderers
# ---------------------------------------------------------------------------


def _d2_l1(spec: ArchSpec) -> str:
    """L1 System Context in D2."""
    lines: list[str] = [
        f"# C4 Level 1 - System Context: {spec.name}",
        "",
        f'title: "{spec.name} - System Context"',
        "",
    ]

    # Tier-0 components are external actors; everything else is the system
    external = [c for c in spec.components if c.tier == 0]
    internal_ids = {c.id for c in spec.components if c.tier != 0}

    # External actors
    for c in external:
        node_id = _safe_id(c.id)
        lines.append(f'{node_id}: "{c.label}\\n[{_tech_label(c)}]" {{')
        lines.append(f'  style.fill: "{_C4_EXTERNAL}"')
        lines.append('  style.font-color: "#ffffff"')
        lines.append("}")

    if external:
        lines.append("")

    # System boundary
    sys_id = _safe_id(spec.name)
    lines.append(f'{sys_id}: "{spec.name}" {{')
    lines.append(f'  style.fill: "{_C4_BLUE}"')
    lines.append('  style.font-color: "#ffffff"')
    lines.append("}")
    lines.append("")

    # Connections involving external actors
    for conn in spec.connections:
        src_external = conn.source not in internal_ids
        tgt_external = conn.target not in internal_ids

        src_id = _safe_id(conn.source) if src_external else sys_id
        tgt_id = _safe_id(conn.target) if tgt_external else sys_id

        if src_id == tgt_id:
            continue

        label = _edge_label(conn)
        if label:
            lines.append(f"{src_id} -> {tgt_id}: {label}")
        else:
            lines.append(f"{src_id} -> {tgt_id}")

    return "\n".join(lines)


def _d2_l2(spec: ArchSpec) -> str:
    """L2 Container Diagram in D2."""
    lines: list[str] = [
        f"# C4 Level 2 - Container Diagram: {spec.name}",
        "",
        f'title: "{spec.name} - Container Diagram"',
        "",
    ]

    sys_id = _safe_id(spec.name)
    lines.append(f'{sys_id}: "{spec.name}" {{')
    lines.append(f'  style.fill: "{_C4_BLUE}"')
    lines.append('  style.font-color: "#ffffff"')
    lines.append("")

    for c in spec.components:
        node_id = _safe_id(c.id)
        tech = _tech_label(c)
        fill = _C4_DB if c.service in _DB_SERVICES else _C4_LIGHT
        lines.append(f'  {node_id}: "{c.label}\\n[{tech}]" {{')
        lines.append(f'    style.fill: "{fill}"')
        lines.append('    style.font-color: "#ffffff"')
        lines.append("  }")

    lines.append("}")
    lines.append("")

    for conn in spec.connections:
        src = f"{sys_id}.{_safe_id(conn.source)}"
        tgt = f"{sys_id}.{_safe_id(conn.target)}"
        label = _edge_label(conn)
        if label:
            lines.append(f"{src} -> {tgt}: {label}")
        else:
            lines.append(f"{src} -> {tgt}")

    return "\n".join(lines)


def _d2_l3(spec: ArchSpec) -> str:
    """L3 Component Diagram in D2.

    Expands ECS/Lambda/etc. containers into their config sub-resources.
    Falls back to L2 layout if nothing is expandable.
    """
    expandable = [c for c in spec.components if c.service in _EXPANDABLE_SERVICES and _l3_subcomponents(c)]

    if not expandable:
        return _d2_l2(spec)

    lines: list[str] = [
        f"# C4 Level 3 - Component Diagram: {spec.name}",
        "",
        f'title: "{spec.name} - Component Diagram"',
        "",
    ]

    expandable_ids = {c.id for c in expandable}
    sys_id = _safe_id(spec.name)
    lines.append(f'{sys_id}: "{spec.name}" {{')
    lines.append(f'  style.fill: "{_C4_BLUE}"')
    lines.append('  style.font-color: "#ffffff"')
    lines.append("")

    for c in spec.components:
        node_id = _safe_id(c.id)
        if c.id in expandable_ids:
            tech = _tech_label(c)
            lines.append(f'  {node_id}: "{c.label}\\n[{tech}]" {{')
            lines.append(f'    style.fill: "{_C4_LIGHT}"')
            lines.append('    style.font-color: "#ffffff"')
            lines.append("")
            for sub_id, sub_label in _l3_subcomponents(c):
                safe_sub = _safe_id(sub_id)
                lines.append(f'    {safe_sub}: "{sub_label}" {{')
                lines.append(f'      style.fill: "{_C4_LIGHT}"')
                lines.append('      style.font-color: "#ffffff"')
                lines.append("    }")
            lines.append("  }")
        else:
            fill = _C4_DB if c.service in _DB_SERVICES else _C4_LIGHT
            lines.append(f'  {node_id}: "{c.label}\\n[{_tech_label(c)}]" {{')
            lines.append(f'    style.fill: "{fill}"')
            lines.append('    style.font-color: "#ffffff"')
            lines.append("  }")

    lines.append("}")
    lines.append("")

    for conn in spec.connections:
        src = f"{sys_id}.{_safe_id(conn.source)}"
        tgt = f"{sys_id}.{_safe_id(conn.target)}"
        label = _edge_label(conn)
        if label:
            lines.append(f"{src} -> {tgt}: {label}")
        else:
            lines.append(f"{src} -> {tgt}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mermaid renderers
# ---------------------------------------------------------------------------


def _mermaid_l1(spec: ArchSpec) -> str:
    """L1 System Context in Mermaid C4Context."""
    lines: list[str] = [
        "C4Context",
        f"  title {spec.name} - System Context",
        "",
    ]

    external = [c for c in spec.components if c.tier == 0]
    internal_ids = {c.id for c in spec.components if c.tier != 0}
    sys_id = _safe_id(spec.name)

    for c in external:
        node_id = _safe_id(c.id)
        tech = _tech_label(c)
        lines.append(f'  System_Ext({node_id}, "{c.label}", "{tech}")')

    lines.append(f'  System({sys_id}, "{spec.name}", "Cloud architecture system")')
    lines.append("")

    seen_pairs: set[tuple[str, str]] = set()
    for conn in spec.connections:
        src_external = conn.source not in internal_ids
        tgt_external = conn.target not in internal_ids

        src_id = _safe_id(conn.source) if src_external else sys_id
        tgt_id = _safe_id(conn.target) if tgt_external else sys_id

        if src_id == tgt_id:
            continue
        pair = (src_id, tgt_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        label = _edge_label(conn)
        lines.append(f'  Rel({src_id}, {tgt_id}, "{label}")')

    return "\n".join(lines)


def _mermaid_l2(spec: ArchSpec) -> str:
    """L2 Container Diagram in Mermaid C4Container."""
    lines: list[str] = [
        "C4Container",
        f"  title {spec.name} - Container Diagram",
        "",
        f'  Container_Boundary(system, "{spec.name}") {{',
    ]

    for c in spec.components:
        node_id = _safe_id(c.id)
        tech = _tech_label(c)
        desc = _description(c)
        if c.service in _DB_SERVICES:
            lines.append(f'    ContainerDb({node_id}, "{c.label}", "{tech}", "{desc}")')
        else:
            lines.append(f'    Container({node_id}, "{c.label}", "{tech}", "{desc}")')

    lines.append("  }")
    lines.append("")

    for conn in spec.connections:
        src = _safe_id(conn.source)
        tgt = _safe_id(conn.target)
        label = _edge_label(conn)
        lines.append(f'  Rel({src}, {tgt}, "{label}")')

    return "\n".join(lines)


def _mermaid_l3(spec: ArchSpec) -> str:
    """L3 Component Diagram in Mermaid C4Component.

    Expands ECS/Lambda/etc. into sub-components from config.
    Falls back to L2 layout if nothing to expand.
    """
    expandable = [c for c in spec.components if c.service in _EXPANDABLE_SERVICES and _l3_subcomponents(c)]

    if not expandable:
        return _mermaid_l2(spec)

    expandable_ids = {c.id for c in expandable}
    lines: list[str] = [
        "C4Component",
        f"  title {spec.name} - Component Diagram",
        "",
        f'  Container_Boundary(system, "{spec.name}") {{',
    ]

    for c in spec.components:
        node_id = _safe_id(c.id)
        tech = _tech_label(c)
        desc = _description(c)
        if c.id in expandable_ids:
            lines.append(f'    Container_Boundary({node_id}_b, "{c.label}") {{')
            for sub_id, sub_label in _l3_subcomponents(c):
                safe_sub = _safe_id(sub_id)
                lines.append(f'      Component({safe_sub}, "{sub_label}", "{tech}", "")')
            lines.append("    }")
        elif c.service in _DB_SERVICES:
            lines.append(f'    ContainerDb({node_id}, "{c.label}", "{tech}", "{desc}")')
        else:
            lines.append(f'    Container({node_id}, "{c.label}", "{tech}", "{desc}")')

    lines.append("  }")
    lines.append("")

    for conn in spec.connections:
        src = _safe_id(conn.source)
        tgt = _safe_id(conn.target)
        label = _edge_label(conn)
        lines.append(f'  Rel({src}, {tgt}, "{label}")')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# L3 sub-component expansion
# ---------------------------------------------------------------------------


def _l3_subcomponents(c: Component) -> list[tuple[str, str]]:
    """Return (id, label) pairs for sub-resources in a component's config.

    Handles:
    - containers: list of str/dict
    - functions: list of str/dict
    - count: int (generates numbered replicas)
    """
    cfg = c.config
    results: list[tuple[str, str]] = []

    # Named containers or functions
    for key in ("containers", "functions", "tasks"):
        items = cfg.get(key)
        if not items:
            continue
        if isinstance(items, list):
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    name = item.get("name", f"{c.id}_{key}_{i}")
                    label = item.get("label", name)
                elif isinstance(item, str):
                    name = item
                    label = item
                else:
                    continue
                results.append((_safe_id(f"{c.id}_{name}"), label))
        return results

    # count-based replicas (only expand if > 1 and <= 8 — avoid noise for large clusters)
    count = cfg.get("count") or cfg.get("desired_count")
    if isinstance(count, int) and 1 < count <= 8:
        for i in range(1, count + 1):
            results.append((_safe_id(f"{c.id}_{i}"), f"{c.label} {i}"))

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(spec: ArchSpec, *, level: int = 2, output_format: str = "d2") -> str:
    """Render an ArchSpec as a C4 model diagram.

    Args:
        spec: The architecture specification.
        level: C4 level (1=System Context, 2=Container, 3=Component).
        output_format: ``"d2"`` or ``"mermaid"``.

    Returns:
        Diagram source as a string.
    """
    fmt = output_format.lower().strip()

    if fmt == "d2":
        if level == 1:
            return _d2_l1(spec)
        if level == 3:
            return _d2_l3(spec)
        return _d2_l2(spec)

    if fmt == "mermaid":
        if level == 1:
            return _mermaid_l1(spec)
        if level == 3:
            return _mermaid_l3(spec)
        return _mermaid_l2(spec)

    raise ValueError(f"Unknown C4 output format: {fmt!r}. Supported: d2, mermaid")
