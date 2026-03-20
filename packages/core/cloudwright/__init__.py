"""Cloudwright — Architecture intelligence for cloud engineers."""

from cloudwright.spec import (
    Alternative,
    ArchSpec,
    ArchVersion,
    Boundary,
    Component,
    ComponentChange,
    ComponentCost,
    Connection,
    ConnectionChange,
    Constraints,
    CostEstimate,
    DiffResult,
    ValidationCheck,
    ValidationResult,
)

__version__ = "0.4.0"

__all__ = [
    "Alternative",
    "ArchSpec",
    "ArchVersion",
    "Architect",
    "Boundary",
    "Catalog",
    "ConversationSession",
    "Component",
    "ComponentChange",
    "ComponentCost",
    "Connection",
    "ConnectionChange",
    "Constraints",
    "CostEstimate",
    "create_version",
    "detect_drift",
    "diff_versions",
    "Differ",
    "DiffResult",
    "DriftReport",
    "get_timeline",
    "import_spec",
    "LintWarning",
    "lint",
    "SecurityFinding",
    "SecurityReport",
    "SecurityScanner",
    "SessionStore",
    "ValidationCheck",
    "ValidationResult",
    "Validator",
]


def __getattr__(name: str):
    # Lazy imports for heavy modules that need LLM/DB
    if name == "Architect":
        from cloudwright.architect import Architect

        return Architect
    if name == "ConversationSession":
        from cloudwright.architect import ConversationSession

        return ConversationSession
    if name == "Catalog":
        from cloudwright.catalog import Catalog

        return Catalog
    if name == "Differ":
        from cloudwright.differ import Differ

        return Differ
    if name == "Validator":
        from cloudwright.validator import Validator

        return Validator
    if name == "lint":
        from cloudwright.linter import lint

        return lint
    if name == "LintWarning":
        from cloudwright.linter import LintWarning

        return LintWarning
    if name == "detect_drift":
        from cloudwright.drift import detect_drift

        return detect_drift
    if name == "DriftReport":
        from cloudwright.drift import DriftReport

        return DriftReport
    if name == "create_version":
        from cloudwright.evolution import create_version

        return create_version
    if name == "get_timeline":
        from cloudwright.evolution import get_timeline

        return get_timeline
    if name == "diff_versions":
        from cloudwright.evolution import diff_versions

        return diff_versions
    if name == "import_spec":
        from cloudwright.importer import import_spec

        return import_spec
    if name == "SessionStore":
        from cloudwright.session_store import SessionStore

        return SessionStore
    if name == "SecurityScanner":
        from cloudwright.security import SecurityScanner

        return SecurityScanner
    if name == "SecurityFinding":
        from cloudwright.security import SecurityFinding

        return SecurityFinding
    if name == "SecurityReport":
        from cloudwright.security import SecurityReport

        return SecurityReport
    raise AttributeError(f"module 'cloudwright' has no attribute {name!r}")
