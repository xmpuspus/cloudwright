"""End-to-end proof projects for the portable migration kernel."""

from __future__ import annotations

from pathlib import Path

import pytest
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


def test_missing_rollback_procedure_stops_closure_even_with_ready_evidence():
    project = MigrationProject.from_file(EXAMPLES / "manufacturing-erp-project.yaml")
    evidence = EvidenceInput.from_file(EXAMPLES / "manufacturing-erp-evidence.yaml")
    project.target.mappings[0].rollback = ""

    assessment = MigrationPlanner().plan(project)
    evidence.assessment_id = assessment.assessment_id
    result = EvidenceEvaluator().evaluate(assessment, evidence)

    assert assessment.transition.complete is False
    assert any("no rollback procedure" in warning for warning in assessment.transition.warnings)
    assert result.closed is False


def test_whitespace_only_rollback_procedure_stops_closure():
    project = MigrationProject.from_file(EXAMPLES / "manufacturing-erp-project.yaml")
    evidence = EvidenceInput.from_file(EXAMPLES / "manufacturing-erp-evidence.yaml")
    project.target.mappings[0].rollback = " \t "

    assessment = MigrationPlanner().plan(project)
    evidence.assessment_id = assessment.assessment_id
    result = EvidenceEvaluator().evaluate(assessment, evidence)

    assert assessment.transition.complete is False
    assert assessment.transition.waves[0].rollback_procedures == []
    assert result.closed is False


def test_evidence_from_an_older_target_plan_cannot_close_a_revision():
    project = MigrationProject.from_file(EXAMPLES / "manufacturing-erp-project.yaml")
    evidence = EvidenceInput.from_file(EXAMPLES / "manufacturing-erp-evidence.yaml")
    original_assessment = MigrationPlanner().plan(project)
    assert evidence.assessment_id == original_assessment.assessment_id

    project.target.mappings[0].target_monthly_cost += 100
    revised_assessment = MigrationPlanner().plan(project)

    with pytest.raises(ValueError, match="assessment id"):
        EvidenceEvaluator().evaluate(revised_assessment, evidence)


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
