"""No request-body / component-count caps on spec-accepting endpoints.

MEDIUM audit finding: every endpoint that parses a ``spec: dict`` (diagram,
plan, export, download, modify, modify/stream, plus compliance, validate,
and cost) accepted it unbounded, so nothing stopped a single request from
carrying thousands of components (unbounded downstream cost/render/export/
scan work) or a multi-megabyte body.

Fix: a shared ``check_component_limit`` helper (mirrors the existing
``check_rate_limit`` return-on-error pattern) rejects specs over
``MAX_SPEC_COMPONENTS`` with 422, applied right after every
``ArchSpec.model_validate(...)`` call site across the routers, and a
body-size ASGI middleware rejects oversized request bodies with 413 before
they ever reach a route handler.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


def _spec_with_components(n: int) -> dict:
    return {
        "name": "Big",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": f"c{i}",
                "service": "lambda",
                "provider": "aws",
                "label": f"L{i}",
                "tier": 2,
                "description": "",
                "config": {},
            }
            for i in range(n)
        ],
    }


class TestComponentCountCap:
    def test_diagram_rejects_over_component_limit(self, client):
        resp = client.post("/api/diagram", json={"spec": _spec_with_components(201), "format": "svg"})
        assert resp.status_code == 422

    def test_plan_rejects_over_component_limit(self, client):
        resp = client.post(
            "/api/plan", json={"spec": _spec_with_components(201), "target": "terraform", "run_plan": False}
        )
        assert resp.status_code == 422

    def test_export_rejects_over_component_limit(self, client):
        resp = client.post("/api/export", json={"spec": _spec_with_components(201), "format": "terraform"})
        assert resp.status_code == 422

    def test_download_rejects_over_component_limit(self, client):
        resp = client.post("/api/download", json={"spec": _spec_with_components(201), "format": "terraform"})
        assert resp.status_code == 422

    def test_modify_rejects_over_component_limit(self, client):
        resp = client.post("/api/modify", json={"spec": _spec_with_components(201), "instruction": "add a queue"})
        assert resp.status_code == 422

    def test_modify_stream_rejects_over_component_limit(self, client):
        resp = client.post(
            "/api/modify/stream", json={"spec": _spec_with_components(201), "instruction": "add a queue"}
        )
        assert resp.status_code == 422

    def test_compliance_rejects_over_component_limit(self, client):
        resp = client.post("/api/compliance", json={"spec": _spec_with_components(201)})
        assert resp.status_code == 422

    def test_validate_rejects_over_component_limit(self, client):
        resp = client.post("/api/validate", json={"spec": _spec_with_components(201)})
        assert resp.status_code == 422

    def test_cost_rejects_over_component_limit(self, client):
        resp = client.post("/api/cost", json={"spec": _spec_with_components(201)})
        assert resp.status_code == 422

    def test_under_limit_is_not_rejected_by_the_cap(self, client):
        """Sanity check: a normal-size spec must not trip the new guard."""
        resp = client.post("/api/export", json={"spec": _spec_with_components(2), "format": "terraform"})
        assert resp.status_code != 422


class TestBodySizeCap:
    def test_oversized_body_rejected_with_413(self, client):
        huge_spec = _spec_with_components(1)
        huge_spec["components"][0]["config"] = {"padding": "x" * 2_000_000}
        resp = client.post("/api/diagram", json={"spec": huge_spec, "format": "svg"})
        assert resp.status_code == 413

    def test_normal_body_not_rejected_by_size_cap(self, client):
        resp = client.post("/api/export", json={"spec": _spec_with_components(2), "format": "terraform"})
        assert resp.status_code != 413
