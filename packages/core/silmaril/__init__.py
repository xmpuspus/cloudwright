"""Silmaril — Architecture intelligence for cloud engineers."""

from silmaril.spec import (
    Alternative,
    ArchSpec,
    Component,
    ComponentChange,
    ComponentCost,
    Connection,
    Constraints,
    CostEstimate,
    DiffResult,
    ValidationCheck,
    ValidationResult,
)

__version__ = "0.1.0"

__all__ = [
    "Alternative",
    "ArchSpec",
    "Architect",
    "Catalog",
    "Component",
    "ComponentChange",
    "ComponentCost",
    "Connection",
    "Constraints",
    "CostEstimate",
    "Differ",
    "DiffResult",
    "ValidationCheck",
    "ValidationResult",
    "Validator",
]


def __getattr__(name: str):
    # Lazy imports for heavy modules that need LLM/DB
    if name == "Architect":
        from silmaril.architect import Architect

        return Architect
    if name == "Catalog":
        from silmaril.catalog import Catalog

        return Catalog
    if name == "Differ":
        from silmaril.differ import Differ

        return Differ
    if name == "Validator":
        from silmaril.validator import Validator

        return Validator
    raise AttributeError(f"module 'silmaril' has no attribute {name!r}")
