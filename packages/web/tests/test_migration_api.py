"""HTTP contract tests for read-only migration planning and evidence checks."""

from __future__ import annotations

import pytest
from cloudwright.migration.demo import load_demo
from cloudwright_web.app import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


def test_migration_packs_lists_installed_pack(client: TestClient):
    response = client.get("/api/migration/packs")

    assert response.status_code == 200
    pack = response.json()["packs"][0]
    assert pack["name"] == "ph_telco"
    assert pack["jurisdiction"] == "PH"


def test_migration_plan_uses_portable_project_body(client: TestClient):
    project, _ = load_demo()

    response = client.post("/api/migration/plan", json={"project": project.as_dict()})

    assert response.status_code == 200
    assessment = response.json()["assessment"]
    assert assessment["transition"]["complete"] is True
    assert [wave["order"] for wave in assessment["transition"]["waves"]] == [1, 2, 3, 4, 5]
    assert len(assessment["assurance"]["criteria"]) == 22


def test_migration_verify_closes_with_complete_evidence(client: TestClient):
    project, evidence = load_demo()
    assessment = client.post("/api/migration/plan", json={"project": project.as_dict()}).json()["assessment"]

    response = client.post(
        "/api/migration/verify",
        json={"assessment": assessment, "evidence": evidence.as_dict()},
    )

    assert response.status_code == 200
    evidence_pack = response.json()["evidence_pack"]
    assert evidence_pack["closed"] is True
    assert evidence_pack["passed"] == 22


def test_migration_verify_returns_visible_blocked_result(client: TestClient):
    project, evidence = load_demo()
    assessment = client.post("/api/migration/plan", json={"project": project.as_dict()}).json()["assessment"]
    evidence.observations = [item for item in evidence.observations if item.criterion_id != "subscriber-record-parity"]

    response = client.post(
        "/api/migration/verify",
        json={"assessment": assessment, "evidence": evidence.as_dict()},
    )

    assert response.status_code == 200
    evidence_pack = response.json()["evidence_pack"]
    assert evidence_pack["closed"] is False
    assert evidence_pack["missing"] == 1
    assert evidence_pack["blocking_failures"] == 1


def test_migration_demo_returns_checked_core_outputs(client: TestClient):
    response = client.get("/api/migration/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["domain_pack"] == "ph_telco"
    assert payload["assessment"]["transition"]["complete"] is True
    assert payload["evidence_pack"]["closed"] is True


def test_migration_plan_rejects_invalid_project_shape(client: TestClient):
    response = client.post(
        "/api/migration/plan",
        json={"project": {"name": "Broken", "estate": {"assets": []}}},
    )

    assert response.status_code == 422
