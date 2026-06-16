"""Unified architecture critique — the deterministic critic layer.

Aggregates the three critics that already exist in the tree (scorer, linter,
validator) into a single severity-ranked report. This runs entirely offline (no
LLM) and is the engine behind two things:

- ``cloudwright review`` — a standalone, free, deterministic architecture review.
- The generate -> critique -> repair loop in :meth:`Architect.design`, where the
  blocking findings are fed back to the model so it self-corrects before the spec
  is ever returned. The critics were always here; v1.6 wires them into generation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from cloudwright.linter import lint
from cloudwright.scorer import Scorer
from cloudwright.validator import Validator

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_LINT_SEVERITY = {"error": "high", "warning": "medium", "info": "low"}
_BLOCKING = ("critical", "high")


def _norm_severity(value: str) -> str:
    v = (value or "").strip().lower()
    return v if v in _SEVERITY_ORDER else "medium"


@dataclass
class CritiqueFinding:
    severity: str  # critical | high | medium | low
    source: str  # scorer | linter | validator
    code: str
    message: str
    recommendation: str = ""
    component: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CritiqueReport:
    score: float
    grade: str
    findings: list[CritiqueFinding] = field(default_factory=list)

    @property
    def blocking(self) -> list[CritiqueFinding]:
        return [f for f in self.findings if f.severity in _BLOCKING]

    def summary_line(self) -> str:
        b = len(self.blocking)
        return f"score {self.score:.0f}/100 (grade {self.grade}), {len(self.findings)} findings, {b} blocking"

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "grade": self.grade,
            "findings": [f.as_dict() for f in self.findings],
            "blocking_count": len(self.blocking),
            "summary": self.summary_line(),
        }


def critique(
    spec: "ArchSpec",
    *,
    compliance: list[str] | None = None,
    well_architected: bool = False,
) -> CritiqueReport:
    """Run scorer + linter + validator and merge into one severity-ranked report."""
    result = Scorer().score(spec)
    findings: list[CritiqueFinding] = []

    for w in lint(spec):
        findings.append(
            CritiqueFinding(
                severity=_LINT_SEVERITY.get(w.severity, "medium"),
                source="linter",
                code=w.rule,
                message=w.message,
                recommendation=w.recommendation,
                component=w.component,
            )
        )

    frameworks = compliance
    if frameworks is None and spec.constraints:
        frameworks = spec.constraints.compliance
    for vr in Validator().validate(spec, compliance=frameworks or [], well_architected=well_architected):
        for ch in vr.checks:
            if not ch.passed:
                findings.append(
                    CritiqueFinding(
                        severity=_norm_severity(ch.severity),
                        source="validator",
                        code=f"{vr.framework}:{ch.name}",
                        message=ch.detail or ch.name,
                        recommendation=ch.recommendation,
                    )
                )

    for d in result.dimensions:
        if d.score < 60:
            sev = "medium" if d.score < 40 else "low"
            for rec in d.recommendations[:2]:
                findings.append(
                    CritiqueFinding(
                        severity=sev,
                        source="scorer",
                        code=f"score:{d.name.lower().replace(' ', '_')}",
                        message=f"{d.name} score {d.score:.0f}/100",
                        recommendation=rec,
                    )
                )

    findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 5))
    return CritiqueReport(score=result.overall, grade=result.grade, findings=findings)
