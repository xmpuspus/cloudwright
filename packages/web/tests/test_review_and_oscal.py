"""Web surface for the v1.6.0 differentiating features: offline review and OSCAL.

Prior to this, ``cloudwright review`` (deterministic critique) and
``cloudwright compliance --oscal`` (OSCAL 1.1.2 component-definition export)
were CLI-only. These tests cover the new ``POST /api/review`` route and the
``oscal`` flag on ``POST /api/compliance``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


def _sample_spec() -> dict:
    return {
        "name": "Sample",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "web",
                "service": "ec2",
                "provider": "aws",
                "label": "Web Server",
                "tier": 2,
                "description": "",
                "config": {},
            },
            {
                "id": "db",
                "service": "rds",
                "provider": "aws",
                "label": "Database",
                "tier": 3,
                "description": "",
                "config": {},
            },
        ],
    }


class TestReviewEndpoint:
    def test_review_returns_expected_keys_for_valid_spec(self, client):
        resp = client.post("/api/review", json={"spec": _sample_spec()})

        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "grade" in data
        assert "findings" in data
        assert "blocking_count" in data
        assert "summary" in data
        assert isinstance(data["findings"], list)

    def test_review_accepts_compliance_and_well_architected(self, client):
        resp = client.post(
            "/api/review",
            json={"spec": _sample_spec(), "compliance": ["hipaa"], "well_architected": True},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "findings" in data

    def test_review_bad_body_returns_structured_4xx(self, client):
        resp = client.post("/api/review", json={"spec": {"provider": "aws"}})

        assert 400 <= resp.status_code < 500
        assert resp.json()

    def test_review_missing_spec_field_returns_422(self, client):
        resp = client.post("/api/review", json={})

        assert resp.status_code == 422

    def test_review_rejects_over_component_limit(self, client):
        spec = _sample_spec()
        spec["components"] = [
            {
                "id": f"c{i}",
                "service": "lambda",
                "provider": "aws",
                "label": f"L{i}",
                "tier": 2,
                "description": "",
                "config": {},
            }
            for i in range(201)
        ]
        resp = client.post("/api/review", json={"spec": spec})

        assert resp.status_code == 422

    def test_review_works_with_no_api_key(self, client):
        """CLOUDWRIGHT_API_KEY is unset in the test env; auth must no-op."""
        resp = client.post("/api/review", json={"spec": _sample_spec()})

        assert resp.status_code != 401


class TestComplianceOscalExport:
    def test_compliance_without_oscal_flag_has_no_oscal_key(self, client):
        resp = client.post("/api/compliance", json={"spec": _sample_spec()})

        assert resp.status_code == 200
        assert "oscal" not in resp.json()

    def test_compliance_oscal_flag_returns_component_definition_shape(self, client):
        resp = client.post(
            "/api/compliance",
            json={"spec": _sample_spec(), "frameworks": ["hipaa"], "oscal": True},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "oscal" in data
        oscal_doc = data["oscal"]
        assert "component-definition" in oscal_doc
        component_def = oscal_doc["component-definition"]
        assert "uuid" in component_def
        assert "metadata" in component_def
        assert "components" in component_def

    def test_compliance_oscal_bad_body_returns_structured_4xx(self, client):
        resp = client.post(
            "/api/compliance",
            json={"spec": {"provider": "aws"}, "oscal": True},
        )

        assert 400 <= resp.status_code < 500

    def test_compliance_oscal_works_with_no_api_key(self, client):
        resp = client.post(
            "/api/compliance",
            json={"spec": _sample_spec(), "oscal": True},
        )

        assert resp.status_code != 401
