"""Packaged offline migration proof projects."""

from __future__ import annotations

from importlib.resources import files

from cloudwright.migration.evidence import EvidenceEvaluator
from cloudwright.migration.models import EvidenceInput, EvidencePack, MigrationAssessment, MigrationProject, YamlModel
from cloudwright.migration.planner import MigrationPlanner


class MigrationDemoResult(YamlModel):
    """Inputs and checked outputs for one packaged proof project."""

    project: MigrationProject
    evidence: EvidenceInput
    assessment: MigrationAssessment
    evidence_pack: EvidencePack


def load_demo(name: str = "ph_telco") -> tuple[MigrationProject, EvidenceInput]:
    """Load a migration proof project from installed package resources."""
    demo_dir = files("cloudwright").joinpath("data", "migration_demos", name)
    project_resource = demo_dir.joinpath("project.yaml")
    evidence_resource = demo_dir.joinpath("evidence.yaml")
    if not project_resource.is_file() or not evidence_resource.is_file():
        raise ValueError(f"unknown migration demo {name!r}; available demos: ph_telco")
    project = MigrationProject.from_yaml(project_resource.read_text(encoding="utf-8"))
    evidence = EvidenceInput.from_yaml(evidence_resource.read_text(encoding="utf-8"))
    return project, evidence


def run_demo(name: str = "ph_telco") -> MigrationDemoResult:
    """Plan and check one packaged proof project without network access."""
    project, evidence = load_demo(name)
    assessment = MigrationPlanner().plan(project)
    evidence_pack = EvidenceEvaluator().evaluate(assessment, evidence)
    return MigrationDemoResult(
        project=project,
        evidence=evidence,
        assessment=assessment,
        evidence_pack=evidence_pack,
    )
