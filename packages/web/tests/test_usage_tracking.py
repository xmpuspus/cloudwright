from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


def _make_session(usage=None, spec=None):
    session = MagicMock()
    session.history = []
    session.current_spec = spec
    session.last_usage = usage or {"input_tokens": 42, "output_tokens": 17, "estimated_cost": 0.0005}
    session.send.return_value = ("Here is your architecture.", spec)
    return session


class TestChatResponseUsage:
    def test_chat_response_includes_usage(self, client):
        session = _make_session()

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=session):
                resp = client.post("/api/chat", json={"message": "describe my app"})

        assert resp.status_code == 200
        assert "usage" in resp.json()

    def test_chat_response_usage_can_be_none(self, client):
        session = _make_session(usage=None)
        session.last_usage = None

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=session):
                resp = client.post("/api/chat", json={"message": "describe my app"})

        assert resp.status_code == 200
        data = resp.json()
        assert "usage" in data


class TestUsageHasTokenCounts:
    def test_usage_has_input_and_output_tokens(self, client):
        usage = {"input_tokens": 100, "output_tokens": 50, "estimated_cost": 0.001}
        session = _make_session(usage=usage)

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=session):
                resp = client.post("/api/chat", json={"message": "design a web app"})

        data = resp.json()
        assert data["usage"]["input_tokens"] == 100
        assert data["usage"]["output_tokens"] == 50

    def test_usage_values_are_numeric(self, client):
        usage = {"input_tokens": 200, "output_tokens": 80, "estimated_cost": 0.002}
        session = _make_session(usage=usage)

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=session):
                resp = client.post("/api/chat", json={"message": "design a backend"})

        usage_out = resp.json()["usage"]
        assert isinstance(usage_out["input_tokens"], int)
        assert isinstance(usage_out["output_tokens"], int)
