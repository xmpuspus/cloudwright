"""``/api/diagram`` hardening.

Audit findings fixed here:
1. HIGH — the D2 subprocess render (up to 300s for PNG) ran synchronously on
   the event loop, blocking every other request. Must go through
   ``asyncio.to_thread`` the same way ``routers/plan.py`` already does.
2. HIGH/MEDIUM — the handler read ``data["spec"]`` off a raw ``request.json()``
   with no request model, so a missing ``spec`` key or malformed spec content
   raised an unhandled exception -> 500 instead of a 4xx.
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


def _spec(n_components: int = 2) -> dict:
    return {
        "name": "Test",
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
            for i in range(n_components)
        ],
    }


class TestDiagramRendersOffTheEventLoop:
    def test_diagram_router_uses_asyncio_to_thread(self):
        from cloudwright_web.routers import diagram as diagram_router

        src = inspect.getsource(diagram_router)
        assert "asyncio.to_thread" in src, (
            "diagram render must run via asyncio.to_thread, matching routers/plan.py, "
            "so the D2 subprocess (up to 300s) doesn't block the event loop"
        )

    def test_render_svg_success(self, client):
        with patch("cloudwright.exporter.renderer.DiagramRenderer.render_svg", return_value="<svg>ok</svg>"):
            resp = client.post("/api/diagram", json={"spec": _spec(), "format": "svg"})
        assert resp.status_code == 200
        assert "svg" in resp.headers.get("content-type", "")

    def test_render_png_success(self, client):
        with patch("cloudwright.exporter.renderer.DiagramRenderer.render_png", return_value=b"\x89PNG"):
            resp = client.post("/api/diagram", json={"spec": _spec(), "format": "png"})
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "image/png"


class TestDiagramBadBodyIsNotA500:
    def test_missing_spec_key_is_4xx_not_500(self, client):
        resp = client.post("/api/diagram", json={})
        assert resp.status_code != 500
        assert 400 <= resp.status_code < 500

    def test_non_dict_spec_is_4xx_not_500(self, client):
        resp = client.post("/api/diagram", json={"spec": "not-a-dict"})
        assert resp.status_code != 500
        assert 400 <= resp.status_code < 500

    def test_structurally_invalid_spec_is_4xx_not_500(self, client):
        resp = client.post("/api/diagram", json={"spec": {"components": "not-a-list"}})
        assert resp.status_code != 500
        assert 400 <= resp.status_code < 500

    def test_render_failure_is_a_structured_response_not_a_bare_crash(self, client):
        """A renderer-side RuntimeError (e.g. D2 missing) is a real server-side
        failure (legitimately 5xx), but it must be a structured JSON error
        response from our own except-block, not an unhandled traceback."""
        with patch(
            "cloudwright.exporter.renderer.DiagramRenderer.render_png",
            side_effect=RuntimeError("D2 binary not installed"),
        ):
            resp = client.post("/api/diagram", json={"spec": _spec(), "format": "png"})
        assert resp.status_code == 500
        data = resp.json()
        assert "message" in data
        assert "suggestion" in data
