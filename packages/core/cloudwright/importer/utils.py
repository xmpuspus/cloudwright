"""Shared utilities for infrastructure importers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec


def align_ids(imported: "ArchSpec", design: "ArchSpec") -> "ArchSpec":
    """Remap imported component IDs to match design spec IDs by (service, provider).

    Used during drift detection to align infrastructure state IDs with the
    original design spec's naming conventions.
    """
    from cloudwright.spec import Component

    design_by_svc: dict[tuple[str, str], list[Component]] = {}
    for c in design.components:
        key = (c.service, c.provider)
        design_by_svc.setdefault(key, []).append(c)

    id_map: dict[str, str] = {}
    used_design_ids: set[str] = set()

    for c in imported.components:
        key = (c.service, c.provider)
        for dc in design_by_svc.get(key, []):
            if dc.id not in used_design_ids:
                id_map[c.id] = dc.id
                used_design_ids.add(dc.id)
                break

    if not id_map:
        return imported

    new_components = [c.model_copy(update={"id": id_map.get(c.id, c.id)}) for c in imported.components]
    new_connections = [
        conn.model_copy(
            update={"source": id_map.get(conn.source, conn.source), "target": id_map.get(conn.target, conn.target)}
        )
        for conn in imported.connections
    ]
    return imported.model_copy(update={"components": new_components, "connections": new_connections})
