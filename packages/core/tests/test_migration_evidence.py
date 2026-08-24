"""Migration evidence evaluation tests."""

from __future__ import annotations

import pytest
from cloudwright.migration import (
    AcceptanceCriterion,
    AssurancePlan,
    EvidenceInput,
    MigrationAssessment,
    MigrationEconomics,
    TransitionSpec,
)
from cloudwright.migration.evidence import EvidenceEvaluator


def _assessment(*criteria: AcceptanceCriterion, complete: bool = True) -> MigrationAssessment:
    return MigrationAssessment(
        assessment_id="a" * 64,
        project_name="Test move",
        transition=TransitionSpec(
            project_name="Test move",
            complete=complete,
            waves=[],
            economics=MigrationEconomics(),
        ),
        assurance=AssurancePlan(criteria=list(criteria)),
    )


def _criterion(
    comparator: str,
    target_value,
    *,
    criterion_id: str = "gate",
    blocking: bool = True,
) -> AcceptanceCriterion:
    return AcceptanceCriterion(
        id=criterion_id,
        name="Acceptance gate",
        category="operational",
        metric="test_metric",
        comparator=comparator,
        target_value=target_value,
        blocking=blocking,
        required_evidence="test-run",
    )


def _evidence(value, *, criterion_id: str = "gate", source: str = "test-run") -> EvidenceInput:
    return EvidenceInput.model_validate(
        {
            "assessment_id": "a" * 64,
            "project_name": "Test move",
            "observations": [
                {
                    "criterion_id": criterion_id,
                    "value": value,
                    "source": source,
                    "observed_at": "2026-08-24T10:00:00Z",
                }
            ],
        }
    )


@pytest.mark.parametrize(
    ("comparator", "target", "actual"),
    [
        ("eq", "ready", "ready"),
        ("gte", 99.9, 100.0),
        ("lte", 0.01, 0.005),
        ("zero", 0, 0),
        ("true", True, True),
    ],
)
def test_supported_comparators_close_when_observation_meets_target(comparator, target, actual):
    result = EvidenceEvaluator().evaluate(_assessment(_criterion(comparator, target)), _evidence(actual))

    assert result.closed is True
    assert result.passed == 1
    assert result.blocking_failures == 0


def test_missing_blocking_evidence_blocks_closure_and_stays_visible():
    evidence = EvidenceInput(assessment_id="a" * 64, project_name="Test move", observations=[])

    result = EvidenceEvaluator().evaluate(_assessment(_criterion("true", True)), evidence)

    assert result.closed is False
    assert result.missing == 1
    assert result.failed == 0
    assert result.blocking_failures == 1
    assert result.results[0].actual is None
    assert "missing" in result.results[0].detail.lower()


def test_observed_non_blocking_failure_does_not_block_closure():
    result = EvidenceEvaluator().evaluate(
        _assessment(_criterion("lte", 1, blocking=False)),
        _evidence(2),
    )

    assert result.closed is True
    assert result.failed == 1
    assert result.blocking_failures == 0


def test_wrong_evidence_source_blocks_a_required_gate():
    result = EvidenceEvaluator().evaluate(
        _assessment(_criterion("true", True)),
        _evidence(True, source="self-attestation"),
    )

    assert result.closed is False
    assert result.results[0].passed is False
    assert "test-run" in result.results[0].detail


def test_unknown_criterion_observation_is_rejected():
    with pytest.raises(ValueError, match="unknown criterion.*other"):
        EvidenceEvaluator().evaluate(
            _assessment(_criterion("true", True)),
            _evidence(True, criterion_id="other"),
        )


def test_project_name_must_match_assessment():
    evidence = _evidence(True)
    evidence.project_name = "Different move"

    with pytest.raises(ValueError, match="Different move"):
        EvidenceEvaluator().evaluate(_assessment(_criterion("true", True)), evidence)


def test_assessment_id_must_match_exact_plan_revision():
    evidence = _evidence(True)
    evidence.assessment_id = "b" * 64

    with pytest.raises(ValueError, match="assessment id"):
        EvidenceEvaluator().evaluate(_assessment(_criterion("true", True)), evidence)


def test_incomplete_transition_cannot_close_even_when_gates_pass():
    result = EvidenceEvaluator().evaluate(
        _assessment(_criterion("true", True), complete=False),
        _evidence(True),
    )

    assert result.closed is False
    assert result.passed == 1
