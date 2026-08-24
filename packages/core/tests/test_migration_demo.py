"""Packaged migration proof-project tests."""

from __future__ import annotations

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
