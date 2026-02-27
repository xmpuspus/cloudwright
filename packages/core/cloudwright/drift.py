"""Drift detection — compare design intent against deployed infrastructure."""

from __future__ import annotations

from dataclasses import dataclass

from cloudwright.differ import Differ
from cloudwright.importer import import_spec
from cloudwright.spec import ArchSpec, DiffResult


@dataclass
class DriftReport:
    """Result of comparing a design spec against deployed infrastructure."""

    design_spec: ArchSpec
    deployed_spec: ArchSpec
    diff: DiffResult
    drift_score: float  # 0.0 = identical, 1.0 = completely different
    drifted_components: list[str]  # component IDs with config drift
    extra_components: list[str]  # deployed but not in design
    missing_components: list[str]  # in design but not deployed
    summary: str


def detect_drift(design_path: str, infra_path: str, infra_format: str = "auto") -> DriftReport:
    """Compare a design spec against deployed infrastructure.

    Args:
        design_path: Path to the ArchSpec YAML (the intended design).
        infra_path: Path to Terraform .tfstate or CloudFormation template.
        infra_format: 'terraform', 'cloudformation', or 'auto'.

    Returns:
        DriftReport with full drift analysis.
    """
    design = ArchSpec.from_file(design_path)
    deployed = import_spec(infra_path, fmt=infra_format)

    # diff(old=design, new=deployed) means:
    #   added   = in deployed but not in design (extra infra)
    #   removed = in design but not in deployed (missing infra)
    #   changed = same ID but different config (drifted)
    differ = Differ()
    diff = differ.diff(design, deployed)

    extra = [c.id for c in diff.added]
    missing = [c.id for c in diff.removed]
    drifted = list({ch.component_id for ch in diff.changed})

    total_design = len(design.components)
    total_issues = len(extra) + len(missing) + len(drifted)
    drift_score = round(min(1.0, total_issues / max(total_design, 1)), 3)

    summary = _build_drift_summary(extra, missing, drifted, diff, drift_score)

    return DriftReport(
        design_spec=design,
        deployed_spec=deployed,
        diff=diff,
        drift_score=drift_score,
        drifted_components=drifted,
        extra_components=extra,
        missing_components=missing,
        summary=summary,
    )


def _build_drift_summary(
    extra: list[str],
    missing: list[str],
    drifted: list[str],
    diff: DiffResult,
    score: float,
) -> str:
    if not extra and not missing and not drifted:
        return "No drift detected. Deployed infrastructure matches design."

    parts = [f"Drift score: {score:.0%}"]

    if missing:
        parts.append(f"{len(missing)} component(s) in design but not deployed: {', '.join(missing)}")
    if extra:
        parts.append(f"{len(extra)} component(s) deployed but not in design: {', '.join(extra)}")
    if drifted:
        parts.append(f"{len(drifted)} component(s) with configuration drift: {', '.join(drifted)}")
        for ch in diff.changed:
            parts.append(f"  {ch.component_id}.{ch.field}: {ch.old_value} -> {ch.new_value}")

    return "\n".join(parts)
