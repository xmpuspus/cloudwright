"""/api/design and /api/modify must surface LLM usage in the response.

Pre-fix: only /api/chat returned usage; design and modify dropped it. UI
clients had no way to surface tokens or cost for those endpoints.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


def _make_spec():
    from cloudwright.spec import ArchSpec, Component, Connection

    return ArchSpec(
        name="Test App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={}),
        ],
        connections=[Connection(source="web", target="db", label="SQL")],
    )


class TestDesignReturnsUsage:
    def test_design_response_includes_usage_field(self, client):
        spec = _make_spec()
        architect = MagicMock()
        architect.design.return_value = spec
        architect.last_usage = {
            "model": "claude-sonnet-4-6",
            "input_tokens": 500,
            "output_tokens": 200,
            "cached_tokens": 0,
            "cost_usd": 0.0045,
            "latency_ms": 1234,
        }

        with patch("cloudwright_web.singletons.get_architect", return_value=architect):
            resp = client.post(
                "/api/design",
                json={"description": "3-tier web app on AWS", "provider": "aws", "region": "us-east-1"},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "usage" in data
        usage = data["usage"]
        assert usage["model"] == "claude-sonnet-4-6"
        assert usage["input_tokens"] == 500
        assert usage["output_tokens"] == 200
        assert usage["cost_usd"] == 0.0045

    def test_modify_response_includes_usage_field(self, client):
        original = _make_spec()
        modified = original
        architect = MagicMock()
        architect.modify.return_value = modified
        architect.last_usage = {
            "model": "claude-haiku-4-5-20251001",
            "input_tokens": 100,
            "output_tokens": 50,
            "cached_tokens": 80,
            "cost_usd": 0.00028,
            "latency_ms": 400,
        }

        with patch("cloudwright_web.singletons.get_architect", return_value=architect):
            resp = client.post(
                "/api/modify",
                json={"spec": original.model_dump(exclude_none=True), "instruction": "add a cache layer"},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "usage" in data
        # Haiku model surfaces — and the cost is the cheap rate, not Sonnet's.
        assert data["usage"]["model"].startswith("claude-haiku")
        assert data["usage"]["cost_usd"] == 0.00028

    def test_design_usage_empty_when_unavailable(self, client):
        """Backwards-compat: if architect.last_usage is empty (e.g. template
        match path), the response still includes the field but as {}."""
        spec = _make_spec()
        architect = MagicMock()
        architect.design.return_value = spec
        architect.last_usage = {}

        with patch("cloudwright_web.singletons.get_architect", return_value=architect):
            resp = client.post(
                "/api/design",
                json={"description": "3-tier web app on AWS", "provider": "aws", "region": "us-east-1"},
            )

        assert resp.status_code == 200
        assert resp.json()["usage"] == {}
