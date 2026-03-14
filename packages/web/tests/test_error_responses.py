from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


class TestMissingApiKeyError:
    def test_design_returns_missing_api_key_error(self, client):
        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.design.side_effect = RuntimeError("No LLM provider configured")
            resp = client.post("/api/design", json={"description": "simple web app on AWS"})

        assert resp.status_code == 503
        data = resp.json()
        assert data["code"] == "missing_api_key"

    def test_chat_returns_missing_api_key_error(self, client):
        mock_session = MagicMock()
        mock_session.history = []
        mock_session.send.side_effect = RuntimeError("No LLM provider configured")

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=mock_session):
                resp = client.post("/api/chat", json={"message": "design something"})

        assert resp.status_code == 503
        data = resp.json()
        assert data["code"] == "missing_api_key"


class TestErrorHasSuggestionField:
    def test_missing_api_key_has_suggestion(self, client):
        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.design.side_effect = RuntimeError("No LLM provider configured")
            resp = client.post("/api/design", json={"description": "simple web app on AWS"})

        assert "suggestion" in resp.json()

    def test_rate_limit_error_has_suggestion(self, client):
        from cloudwright_web.app import _RateLimiter

        tight = _RateLimiter(max_requests=0, window_seconds=60)
        with patch("cloudwright_web.app._rate_limiter", tight):
            resp = client.post("/api/design", json={"description": "simple web app on AWS"})

        assert resp.status_code == 429
        assert "suggestion" in resp.json()

    def test_timeout_error_has_suggestion(self, client):
        import asyncio

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.design.side_effect = asyncio.TimeoutError()
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                resp = client.post("/api/design", json={"description": "simple web app on AWS"})

        assert "suggestion" in resp.json()

    def test_internal_error_has_suggestion(self, client):
        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.design.side_effect = Exception("unexpected boom")
            resp = client.post("/api/design", json={"description": "simple web app on AWS"})

        data = resp.json()
        assert "suggestion" in data
        assert data["code"] == "internal_error"
