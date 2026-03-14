from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


def _make_mock_session(chunks=None):
    session = MagicMock()
    session.current_spec = None
    session.last_usage = {"input_tokens": 10, "output_tokens": 20}
    session.history = []
    if chunks is not None:
        session.send_stream.return_value = iter(chunks)
    return session


class TestChatStreamEndpoint:
    def test_chat_stream_returns_sse(self, client):
        mock_session = _make_mock_session(chunks=["Hello", " world"])

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=mock_session):
                resp = client.post(
                    "/api/chat/stream",
                    json={"message": "design a simple app"},
                )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_chat_stream_yields_token_events(self, client):
        mock_session = _make_mock_session(chunks=["chunk1", "chunk2"])

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=mock_session):
                resp = client.post(
                    "/api/chat/stream",
                    json={"message": "design a simple app"},
                )

        lines = [ln for ln in resp.text.splitlines() if ln.startswith("data:")]
        events = [json.loads(ln[5:].strip()) for ln in lines]
        token_events = [e for e in events if e.get("stage") == "token"]
        assert len(token_events) >= 1

    def test_chat_stream_includes_done_event(self, client):
        mock_session = _make_mock_session(chunks=["response text"])

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=mock_session):
                resp = client.post(
                    "/api/chat/stream",
                    json={"message": "design a simple app"},
                )

        lines = [ln for ln in resp.text.splitlines() if ln.startswith("data:")]
        events = [json.loads(ln[5:].strip()) for ln in lines]
        stages = [e.get("stage") for e in events]
        assert "done" in stages

    def test_chat_stream_done_event_includes_usage(self, client):
        mock_session = _make_mock_session(chunks=["text"])

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=mock_session):
                resp = client.post(
                    "/api/chat/stream",
                    json={"message": "design something"},
                )

        lines = [ln for ln in resp.text.splitlines() if ln.startswith("data:")]
        events = [json.loads(ln[5:].strip()) for ln in lines]
        done = next(e for e in events if e.get("stage") == "done")
        assert "usage" in done

    def test_chat_stream_with_history(self, client):
        mock_session = _make_mock_session(chunks=["ok"])

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch("cloudwright.architect.ConversationSession", return_value=mock_session):
                resp = client.post(
                    "/api/chat/stream",
                    json={
                        "message": "add a cache",
                        "history": [{"role": "user", "content": "first msg"}, {"role": "assistant", "content": "got it"}],
                    },
                )

        assert resp.status_code == 200
        assert len(mock_session.history) == 2
