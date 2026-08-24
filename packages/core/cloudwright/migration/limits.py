"""Shared request-size checks for migration service surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

MAX_MIGRATION_ITEMS = 200
MAX_MIGRATION_NESTED_ITEMS = 10_000


def _field(value: Any, name: str, default: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _count(value: Any) -> int:
    try:
        return len(value)
    except TypeError:
        return 0


def _validate_nested_item_budget(*values: Any) -> None:
    """Bound aggregate work across nested project and evidence collections."""
    stack = list(values)
    seen: set[int] = set()
    total = 0
    while stack:
        value = stack.pop()
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        if isinstance(value, Mapping):
            children = list(value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            children = list(value)
        else:
            continue

        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        total += len(children)
        if total > MAX_MIGRATION_NESTED_ITEMS:
            raise ValueError(
                f"Migration has more than {MAX_MIGRATION_NESTED_ITEMS} nested items; "
                "reduce nested metadata, tags, classifications, or evidence details"
            )
        stack.extend(children)


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
    _validate_nested_item_budget(project, evidence)
