"""End-to-end proof projects for the portable migration kernel."""

from __future__ import annotations

from pathlib import Path

from cloudwright.migration import EvidenceEvaluator, EvidenceInput, MigrationPlanner, MigrationProject

ROOT = Path(__file__).parents[3]
EXAMPLES = ROOT / "examples" / "migrations"


def test_ph_telco_project_plans_and_closes_with_pack_evidence():
    project = MigrationProject.from_file(EXAMPLES / "ph-telco-project.yaml")
    evidence = EvidenceInput.from_file(EXAMPLES / "ph-telco-evidence.yaml")

    assessment = MigrationPlanner().plan(project)
    result = EvidenceEvaluator().evaluate(assessment, evidence)

    assert assessment.domain_pack == "ph_telco"
    assert assessment.transition.complete is True
    assert [wave.order for wave in assessment.transition.waves] == [1, 2, 3, 4, 5]
    assert len(assessment.assurance.criteria) == 22
    assert assessment.transition.economics.current_monthly_cost > assessment.transition.economics.target_monthly_cost
    assert result.closed is True
    assert result.passed == 22
    assert result.failed == 0
    assert result.missing == 0


def test_missing_ph_telco_blocking_observation_stops_closure():
    project = MigrationProject.from_file(EXAMPLES / "ph-telco-project.yaml")
    evidence = EvidenceInput.from_file(EXAMPLES / "ph-telco-evidence.yaml")
    evidence.observations = [item for item in evidence.observations if item.criterion_id != "subscriber-record-parity"]

    result = EvidenceEvaluator().evaluate(MigrationPlanner().plan(project), evidence)

    assert result.closed is False
    assert result.missing == 1
    assert result.blocking_failures == 1


def test_manufacturing_project_uses_same_kernel_without_telco_pack():
    project = MigrationProject.from_file(EXAMPLES / "manufacturing-erp-project.yaml")
    evidence = EvidenceInput.from_file(EXAMPLES / "manufacturing-erp-evidence.yaml")

    assessment = MigrationPlanner().plan(project)
    result = EvidenceEvaluator().evaluate(assessment, evidence)

    assert assessment.domain_pack is None
    assert [criterion.id for criterion in assessment.assurance.criteria] == [
        "wave-1-rollback-ready",
        "wave-2-rollback-ready",
        "wave-3-rollback-ready",
    ]
    assert result.closed is True
    assert all("subscriber" not in criterion.id for criterion in assessment.assurance.criteria)
