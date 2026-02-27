"""Architecture evolution timeline — track spec changes over time."""

from __future__ import annotations

import datetime
import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec


def create_version(spec: "ArchSpec", description: str = "", author: str = "") -> str:
    """Stamp the current spec with a version, return version_id."""
    from cloudwright.spec import ArchVersion

    content = spec.to_json()
    version_id = hashlib.sha256(content.encode()).hexdigest()[:12]

    parent = spec.history[-1].version_id if spec.history else ""

    version = ArchVersion(
        version_id=version_id,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        author=author,
        description=description,
        parent_version=parent,
    )
    spec.history.append(version)
    return version_id


def get_timeline(spec: "ArchSpec") -> list[dict]:
    """Return the full evolution timeline."""
    return [
        {
            "version": v.version_id,
            "timestamp": v.timestamp,
            "author": v.author,
            "description": v.description,
            "parent": v.parent_version,
        }
        for v in spec.history
    ]


def diff_versions(spec_v1: "ArchSpec", spec_v2: "ArchSpec") -> dict:
    """Diff two versioned specs, returning structured changes."""
    from cloudwright.differ import Differ

    diff = Differ().diff(spec_v1, spec_v2)
    v1_id = spec_v1.history[-1].version_id if spec_v1.history else "unknown"
    v2_id = spec_v2.history[-1].version_id if spec_v2.history else "unknown"
    return {
        "from_version": v1_id,
        "to_version": v2_id,
        "added": len(diff.added),
        "removed": len(diff.removed),
        "changed": len(diff.changed),
        "connection_changes": len(diff.connection_changes),
        "cost_delta": diff.cost_delta,
        "summary": diff.summary,
    }
