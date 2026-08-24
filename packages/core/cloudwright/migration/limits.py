"""Shared request-size checks for migration service surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

MAX_MIGRATION_ITEMS = 200


def _field(value: Any, name: str, default: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _count(value: Any) -> int:
    try:
        return len(value)
    except TypeError:
        return 0


def validate_migration_size(project: Any, evidence: Any = None) -> None:
    """Reject oversized project and evidence collections before deeper work."""
    estate = _field(project, "estate", {})
    target = _field(project, "target", {})
    collections = (
        ("source assets", _field(estate, "assets", [])),
        ("dependencies", _field(estate, "dependencies", [])),
        ("target assets", _field(target, "assets", [])),
        ("target mappings", _field(target, "mappings", [])),
        ("evidence observations", _field(evidence, "observations", []) if evidence is not None else []),
    )
    for label, items in collections:
        count = _count(items)
        if count > MAX_MIGRATION_ITEMS:
            raise ValueError(f"Migration has {count} {label}; max allowed is {MAX_MIGRATION_ITEMS}")
