"""v1.6.0 generate -> critique -> repair loop."""

from cloudwright.critique import CritiqueFinding, CritiqueReport, critique
from cloudwright.designer import Architect
from cloudwright.spec import ArchSpec, Component


def _flawed_spec() -> ArchSpec:
    # A bare public-ish DB + compute with none of the safety scaffolding: this
    # trips multiple linter rules (no monitoring, no LB, no backup, ...).
    return ArchSpec(
        name="flawed",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
    )


class TestCritiqueDeterministic:
    def test_returns_score_grade_findings(self):
        report = critique(_flawed_spec())
        assert 0 <= report.score <= 100
        assert report.grade in {"A", "B", "C", "D", "F"}
        assert report.findings, "a bare 2-component spec should surface lint findings"
        # findings are severity-ranked (criticals/highs first)
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sevs = [order.get(f.severity, 4) for f in report.findings]
        assert sevs == sorted(sevs)

    def test_blocking_is_high_and_critical_only(self):
        report = critique(_flawed_spec())
        assert all(f.severity in ("critical", "high") for f in report.blocking)

    def test_compliance_findings_included(self):
        report = critique(_flawed_spec(), compliance=["hipaa"])
        assert any(f.source == "validator" for f in report.findings)

    def test_as_dict_shape(self):
        d = critique(_flawed_spec()).as_dict()
        assert {"score", "grade", "findings", "blocking_count", "summary"} <= set(d)


class _FakeLLM:
    model_name = "fake"
    pricing = {"input": 0.0, "output": 0.0}

    def __init__(self):
        self.calls = 0

    def generate_fast(self, messages, system, max_tokens=0):
        self.calls += 1
        repaired = (
            '{"name":"repaired","components":['
            '{"id":"web","service":"ec2","provider":"aws","label":"Web","tier":2},'
            '{"id":"mon","service":"cloudwatch","provider":"aws","label":"Monitoring","tier":1}'
            "]}"
        )
        return repaired, {"input_tokens": 10, "output_tokens": 20, "model": "fake"}


class TestRepairLoop:
    def test_repair_runs_when_blocking_and_keeps_better_spec(self, monkeypatch):
        import cloudwright.critique as crit

        before = CritiqueReport(
            score=40.0,
            grade="F",
            findings=[
                CritiqueFinding("high", "linter", "no_monitoring", "No monitoring"),
                CritiqueFinding("high", "linter", "no_backup", "No backup"),
            ],
        )
        after = CritiqueReport(score=80.0, grade="B", findings=[])
        reports = iter([before, after])
        monkeypatch.setattr(crit, "critique", lambda *a, **k: next(reports))

        arch = Architect(llm=_FakeLLM(), repair=True, max_repair_iters=1)
        out = arch._critique_repair(_flawed_spec(), "web app", None)

        meta = out.metadata["critique"]
        assert meta["blocking_before"] == 2
        assert meta["repair_iterations"] == 1
        assert meta["blocking_after"] == 0
        assert out.name == "repaired"  # the better spec was kept

    def test_no_repair_when_no_blocking(self, monkeypatch):
        import cloudwright.critique as crit

        clean = CritiqueReport(score=90.0, grade="A", findings=[])
        monkeypatch.setattr(crit, "critique", lambda *a, **k: clean)

        llm = _FakeLLM()
        arch = Architect(llm=llm, repair=True)
        out = arch._critique_repair(_flawed_spec(), "web app", None)

        assert llm.calls == 0  # no LLM repair call when nothing is blocking
        assert out.metadata["critique"]["repair_iterations"] == 0

    def test_repair_kept_only_if_not_worse(self, monkeypatch):
        import cloudwright.critique as crit

        before = CritiqueReport(score=40.0, grade="F", findings=[CritiqueFinding("high", "linter", "x", "X")])
        worse = CritiqueReport(
            score=20.0,
            grade="F",
            findings=[
                CritiqueFinding("high", "linter", "x", "X"),
                CritiqueFinding("critical", "linter", "y", "Y"),
            ],
        )
        reports = iter([before, worse])
        monkeypatch.setattr(crit, "critique", lambda *a, **k: next(reports))

        arch = Architect(llm=_FakeLLM(), repair=True, max_repair_iters=1)
        original = _flawed_spec()
        out = arch._critique_repair(original, "web app", None)
        assert out.name == "flawed"  # regressed repair discarded
