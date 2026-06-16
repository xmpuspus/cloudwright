"""OSCAL 1.1.2 component-definition export for Cloudwright compliance results.

Converts a ComplianceReport + ArchSpec into a machine-readable OSCAL
component-definition document. FedRAMP's 20x/OSCAL direction makes this
the interoperability surface competitors don't have.

Control IDs from compliance_controls.yaml are already NIST-shaped for
FedRAMP/NIST-800-53 (e.g. "SC-28", "AC-3"). For HIPAA/SOC2/PCI-DSS/GDPR/ISO27001
the control IDs are kept verbatim and annotated with a source-framework prop
so validators know they're not NIST identifiers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cloudwright.compliance import ComplianceReport
    from cloudwright.spec import ArchSpec

_OSCAL_VERSION = "1.1.2"
_CW_VERSION = "1.6.0"

# Frameworks whose control IDs are already NIST SP 800-53 style.
_NIST_SHAPED = {"FedRAMP", "NIST-800-53"}


def _det_uuid(spec_name: str, frameworks: list[str]) -> str:
    """Deterministic uuid5 from spec name + sorted framework list.

    Stable across calls with the same inputs — required for reproducible tests
    and idempotent CI artifact generation.
    """
    seed = f"{spec_name}|{','.join(sorted(frameworks))}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def _component_uuid(spec_name: str, component_id: str) -> str:
    seed = f"{spec_name}::{component_id}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def _req_uuid(spec_name: str, component_id: str, control_id: str, framework: str) -> str:
    seed = f"{spec_name}::{component_id}::{framework}::{control_id}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def _normalize_control_id(control_id: str, framework: str) -> str:
    """Return a lowercase NIST-style control ID when the framework uses NIST IDs.

    Non-NIST IDs (HIPAA CFR citations, SOC2 criteria, etc.) are kept verbatim
    because forcibly lowercasing them would make them unrecognizable.
    """
    if framework in _NIST_SHAPED:
        return control_id.lower()
    return control_id


def to_oscal(spec: ArchSpec, scan_result: ComplianceReport, frameworks: list[str]) -> dict[str, Any]:
    """Return a valid OSCAL 1.1.2 component-definition document as a dict.

    Args:
        spec: The architecture specification being assessed.
        scan_result: The ComplianceReport produced by ComplianceScanner.scan().
        frameworks: The list of canonical framework names used during the scan
                    (e.g. ["HIPAA", "FedRAMP"]).

    Returns:
        A dict that serialises to valid OSCAL 1.1.2 component-definition JSON.
    """
    doc_uuid = _det_uuid(spec.name, frameworks)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build a fast lookup: (component_id, framework, control_id) -> worst severity
    # A control is "not-satisfied" when any finding references it.
    failing: dict[tuple[str | None, str, str], str] = {}
    for finding in scan_result.findings:
        for ctrl in finding.controls:
            key = (finding.component_id, ctrl.framework, ctrl.control_id)
            prev = failing.get(key)
            if prev is None:
                failing[key] = finding.severity
            else:
                _rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                if _rank.get(finding.severity, 4) < _rank.get(prev, 4):
                    failing[key] = finding.severity

    components = []
    for comp in spec.components:
        ctrl_impls = _control_implementations_for(spec.name, comp, frameworks, scan_result, failing)
        components.append(
            {
                "uuid": _component_uuid(spec.name, comp.id),
                "type": "service",
                "title": comp.label or comp.id,
                "description": comp.description or f"{comp.service} ({comp.provider})",
                "props": [
                    {"name": "provider", "value": comp.provider},
                    {"name": "service", "value": comp.service},
                ],
                "control-implementations": ctrl_impls,
            }
        )

    return {
        "component-definition": {
            "uuid": doc_uuid,
            "metadata": {
                "title": f"Cloudwright Compliance — {spec.name}",
                "last-modified": now,
                "version": _CW_VERSION,
                "oscal-version": _OSCAL_VERSION,
                "props": [
                    {"name": "generator", "value": "cloudwright-ai"},
                    {"name": "frameworks", "value": ", ".join(frameworks)},
                ],
            },
            "components": components,
        }
    }


def _control_implementations_for(
    spec_name: str,
    comp: Any,
    frameworks: list[str],
    scan_result: ComplianceReport,
    failing: dict[tuple[str | None, str, str], str],
) -> list[dict]:
    """Build the control-implementations array for one architecture component."""
    # Gather all (framework, control_id) pairs relevant to this component:
    # - controls from findings scoped to this component
    # - controls from findings with no component scope (architecture-wide)
    seen: dict[tuple[str, str], str] = {}  # (framework, ctrl) -> worst severity

    for finding in scan_result.findings:
        if finding.component_id not in (comp.id, None):
            continue
        for ctrl in finding.controls:
            if ctrl.framework not in frameworks:
                continue
            key = (ctrl.framework, ctrl.control_id)
            sev_key = (finding.component_id, ctrl.framework, ctrl.control_id)
            sev = failing.get(sev_key, finding.severity)
            prev = seen.get(key)
            if prev is None:
                seen[key] = sev
            else:
                _rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                if _rank.get(sev, 4) < _rank.get(prev, 4):
                    seen[key] = sev

    if not seen:
        return []

    # Group by framework
    by_fw: dict[str, list[tuple[str, str]]] = {}
    for (fw, ctrl), sev in seen.items():
        by_fw.setdefault(fw, []).append((ctrl, sev))

    impls = []
    for fw in frameworks:
        reqs = by_fw.get(fw)
        if not reqs:
            continue

        implemented_reqs = []
        for ctrl_id, sev in reqs:
            normalized = _normalize_control_id(ctrl_id, fw)
            props = [
                {"name": "framework", "value": fw},
                {"name": "severity", "value": sev},
            ]
            if fw not in _NIST_SHAPED:
                # Non-NIST control IDs need source annotation for validators
                props.append({"name": "control-id-source", "value": fw})

            implemented_reqs.append(
                {
                    "uuid": _req_uuid(spec_name, comp.id, ctrl_id, fw),
                    "control-id": normalized,
                    "description": f"Cloudwright finding for control {ctrl_id} ({fw})",
                    "props": props,
                    "implementation-status": {"state": "not-satisfied"},
                }
            )

        impls.append(
            {
                "uuid": _req_uuid(spec_name, comp.id, fw, "impl"),
                "source": f"https://cloudwright.ai/frameworks/{fw.lower()}",
                "description": f"{fw} control implementation for {comp.id}",
                "implemented-requirements": implemented_reqs,
            }
        )

    return impls
