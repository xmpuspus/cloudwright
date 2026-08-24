"""Evaluate migration evidence against portable acceptance criteria."""

from __future__ import annotations

from datetime import UTC, datetime

from cloudwright.migration.models import (
    AcceptanceCriterion,
    CriterionResult,
    EvidenceInput,
    EvidenceObservation,
    EvidencePack,
    MigrationAssessment,
    ScalarValue,
)


class EvidenceEvaluator:
    """Apply strict evidence and threshold checks to an assessment."""

    def evaluate(self, assessment: MigrationAssessment, evidence: EvidenceInput) -> EvidencePack:
        """Return the closure decision and one result for every criterion."""
        if evidence.project_name != assessment.project_name:
            raise ValueError(
                f"evidence project {evidence.project_name!r} does not match assessment {assessment.project_name!r}"
            )
        if evidence.assessment_id != assessment.assessment_id:
            raise ValueError(
                f"evidence assessment id {evidence.assessment_id!r} does not match "
                f"current assessment id {assessment.assessment_id!r}"
            )
        evaluated_at = datetime.now(UTC)
        future_observations = [
            observation.criterion_id for observation in evidence.observations if observation.observed_at > evaluated_at
        ]
        if future_observations:
            raise ValueError("evidence contains future observation(s): " + ", ".join(sorted(future_observations)))

        criterion_ids = {criterion.id for criterion in assessment.assurance.criteria}
        observation_ids = [observation.criterion_id for observation in evidence.observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("evidence has duplicate criterion observations")
        unknown = set(observation_ids) - criterion_ids
        if unknown:
            raise ValueError(f"evidence references unknown criterion(s): {', '.join(sorted(unknown))}")

        observations = {observation.criterion_id: observation for observation in evidence.observations}
        results = [
            self._evaluate_criterion(
                criterion,
                observations.get(criterion.id),
                evidence_not_before=assessment.evidence_not_before,
            )
            for criterion in assessment.assurance.criteria
        ]
        passed = sum(result.passed for result in results)
        missing = sum(result.actual is None for result in results)
        failed = sum(not result.passed and result.actual is not None for result in results)
        blocking_failures = sum(not result.passed and result.blocking for result in results)
        return EvidencePack(
            assessment_id=assessment.assessment_id,
            project_name=assessment.project_name,
            closed=assessment.transition.complete and blocking_failures == 0,
            passed=passed,
            failed=failed,
            missing=missing,
            blocking_failures=blocking_failures,
            results=results,
        )

    def _evaluate_criterion(
        self,
        criterion: AcceptanceCriterion,
        observation: EvidenceObservation | None,
        *,
        evidence_not_before: datetime,
    ) -> CriterionResult:
        if observation is None:
            return CriterionResult(
                criterion_id=criterion.id,
                name=criterion.name,
                category=criterion.category,
                passed=False,
                blocking=criterion.blocking,
                expected=criterion.target_value,
                detail=f"Missing evidence from {criterion.required_evidence}",
            )
        if observation.observed_at < evidence_not_before:
            return self._result(
                criterion,
                observation,
                passed=False,
                detail=(
                    f"Evidence timestamp {observation.observed_at.isoformat()} is before "
                    f"the assessment boundary {evidence_not_before.isoformat()}"
                ),
            )
        if observation.source != criterion.required_evidence:
            return self._result(
                criterion,
                observation,
                passed=False,
                detail=(
                    f"Evidence source {observation.source!r} does not match required "
                    f"source {criterion.required_evidence!r}"
                ),
            )
        passed = self._compare(criterion, observation.value)
        operator = criterion.comparator
        detail = f"{criterion.metric}: actual {observation.value!r} {operator} target {criterion.target_value!r}"
        return self._result(criterion, observation, passed=passed, detail=detail)

    @staticmethod
    def _result(
        criterion: AcceptanceCriterion,
        observation: EvidenceObservation,
        *,
        passed: bool,
        detail: str,
    ) -> CriterionResult:
        return CriterionResult(
            criterion_id=criterion.id,
            name=criterion.name,
            category=criterion.category,
            passed=passed,
            blocking=criterion.blocking,
            expected=criterion.target_value,
            actual=observation.value,
            source=observation.source,
            detail=detail,
        )

    @staticmethod
    def _compare(criterion: AcceptanceCriterion, actual: ScalarValue) -> bool:
        comparator = criterion.comparator
        expected = criterion.target_value
        if comparator == "eq":
            return type(actual) is type(expected) and actual == expected
        if comparator == "true":
            return actual is True
        if comparator == "zero":
            return not isinstance(actual, bool) and isinstance(actual, int | float) and actual == 0
        if isinstance(actual, bool) or isinstance(expected, bool):
            return False
        if not isinstance(actual, int | float) or not isinstance(expected, int | float):
            return False
        if comparator == "gte":
            return actual >= expected
        if comparator == "lte":
            return actual <= expected
        return False
