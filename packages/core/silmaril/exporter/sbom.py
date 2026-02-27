"""CycloneDX 1.5 SBOM exporter for ArchSpec."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from silmaril.spec import ArchSpec

_PROVIDER_DISPLAY: dict[str, str] = {
    "aws": "Amazon Web Services",
    "gcp": "Google Cloud Platform",
    "azure": "Microsoft Azure",
}


def render(spec: "ArchSpec") -> str:
    now = datetime.now(timezone.utc).isoformat()

    components: list[dict[str, Any]] = []
    for c in spec.components:
        provider_display = _PROVIDER_DISPLAY.get(c.provider.lower(), c.provider)
        comp: dict[str, Any] = {
            "type": "service",
            "bom-ref": c.id,
            "name": c.service,
            "version": "latest",
            "supplier": {"name": provider_display},
            "properties": [
                {"name": "silmaril:provider", "value": c.provider},
                {"name": "silmaril:tier", "value": str(c.tier)},
                {"name": "silmaril:region", "value": spec.region},
                {"name": "silmaril:label", "value": c.label},
            ],
        }
        if c.description:
            comp["description"] = c.description
        components.append(comp)

    # Build dependency map from connections
    dep_map: dict[str, list[str]] = {c.id: [] for c in spec.components}
    for conn in spec.connections:
        if conn.source in dep_map:
            dep_map[conn.source].append(conn.target)

    dependencies = [{"ref": comp_id, "dependsOn": targets} for comp_id, targets in dep_map.items()]

    bom: dict[str, Any] = {
        "$schema": "http://cyclonedx.org/schema/bom-1.5.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "component": {
                "type": "application",
                "name": spec.name,
                "version": "1.0.0",
            },
            "tools": [{"name": "Silmaril", "version": "0.1.0"}],
        },
        "components": components,
        "dependencies": dependencies,
    }

    return json.dumps(bom, indent=2)
