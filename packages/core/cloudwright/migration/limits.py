"""Shared request-size checks for migration service surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

MAX_MIGRATION_ITEMS = 200
MAX_MIGRATION_NESTED_ITEMS = 10_000
MAX_MIGRATION_TEXT_CHARACTERS = 1_000_000
MAX_MIGRATION_PACK_NAME_CHARACTERS = 128
MAX_MIGRATION_FILE_BYTES = 2_000_000


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
    text_characters = 0
    while stack:
        value = stack.pop()
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        if isinstance(value, str):
            text_characters += len(value)
            if text_characters > MAX_MIGRATION_TEXT_CHARACTERS:
                raise ValueError(
                    f"Migration has more than {MAX_MIGRATION_TEXT_CHARACTERS} text characters; "
                    "reduce descriptions, metadata, or evidence details"
                )
            continue
        if isinstance(value, Mapping):
            item_count = len(value)
        elif isinstance(value, (list, tuple, set, frozenset)):
            item_count = len(value)
        else:
            continue

        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        total += item_count
        if total > MAX_MIGRATION_NESTED_ITEMS:
            raise ValueError(
                f"Migration has more than {MAX_MIGRATION_NESTED_ITEMS} nested items; "
                "reduce nested metadata, tags, classifications, or evidence details"
            )
        if isinstance(value, Mapping):
            stack.extend(value.keys())
            stack.extend(value.values())
        else:
            stack.extend(value)


def validate_migration_size(project: Any, evidence: Any = None, pack: Any = None) -> None:
    """Reject oversized project and evidence collections before deeper work."""
    if isinstance(pack, str) and len(pack) > MAX_MIGRATION_PACK_NAME_CHARACTERS:
        raise ValueError(f"Migration pack name has more than {MAX_MIGRATION_PACK_NAME_CHARACTERS} text characters")
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
    _validate_nested_item_budget(project, evidence, pack)
