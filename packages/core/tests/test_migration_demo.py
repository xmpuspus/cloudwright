"""Packaged migration proof-project tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cloudwright.migration.demo import load_demo, run_demo


def test_ph_telco_demo_loads_from_package_resources():
    project, evidence = load_demo("ph_telco")

    assert project.name == "PH telco hybrid service migration"
    assert project.domain_pack == "ph_telco"
    assert evidence.project_name == project.name


def test_packaged_demo_runs_offline_to_a_closed_evidence_pack():
    result = run_demo("ph_telco")

    assert result.assessment.transition.complete is True
    assert result.evidence_pack.closed is True
    assert len(result.assessment.transition.waves) == 5
    assert result.evidence_pack.passed == 22


def test_packaged_demo_evidence_is_not_future_dated_on_release_day(monkeypatch):
    class ReleaseMorning(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 8, 24, 8, 39, tzinfo=UTC)

    monkeypatch.setattr("cloudwright.migration.evidence.datetime", ReleaseMorning)

    assert run_demo("ph_telco").evidence_pack.closed is True


def test_cli_demo_tape_creates_its_temporary_parent_directory():
    repository_root = Path(__file__).parents[3]
    tape = (repository_root / "examples/tapes/cloudwright-migration.tape").read_text()

    mkdir_position = tape.index("Type 'mkdir -p \"$PWD/tmp\"' Enter")
    mktemp_position = tape.index("Type 'migration_demo_dir=$(mktemp -d \"$PWD/tmp/migration-gif.XXXXXX\")' Enter")

    assert mkdir_position < mktemp_position
