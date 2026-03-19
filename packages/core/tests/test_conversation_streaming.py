"""Tests for ConversationSession.send_stream()."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from cloudwright.architect import ConversationSession


def _make_spec_json(name="Test App"):
    components = [
        {"id": "web", "service": "ec2", "provider": "aws", "label": "Web", "tier": 2, "config": {}},
        {"id": "db", "service": "rds", "provider": "aws", "label": "DB", "tier": 3, "config": {}},
    ]
    return json.dumps(
        {
            "name": name,
            "provider": "aws",
            "region": "us-east-1",
            "components": components,
            "connections": [{"source": "web", "target": "db", "label": "SQL"}],
        }
    )


def _mock_llm_stream(chunks):
    llm = MagicMock()
    llm.generate_stream.return_value = iter(chunks)
    return llm


def test_send_stream_yields_chunks():
    llm = _mock_llm_stream(["Here ", "is ", "your ", "architecture."])
    session = ConversationSession(llm=llm)

    chunks = list(session.send_stream("design a web app on aws"))

    assert chunks == ["Here ", "is ", "your ", "architecture."]


def test_send_stream_updates_history():
    llm = _mock_llm_stream(["Here is your aws architecture."])
    session = ConversationSession(llm=llm)

    list(session.send_stream("design a web app on aws"))

    assert len(session.history) == 2
    assert session.history[0]["role"] == "user"
    assert session.history[0]["content"] == "design a web app on aws"
    assert session.history[1]["role"] == "assistant"
    assert session.history[1]["content"] == "Here is your aws architecture."


def test_send_stream_extracts_spec():
    spec_json = _make_spec_json("Streamed App")
    llm = _mock_llm_stream([spec_json])
    session = ConversationSession(llm=llm)

    list(session.send_stream("design a web app on aws"))

    assert session.current_spec is not None
    assert session.current_spec.name == "Streamed App"


def test_send_stream_no_spec_for_text():
    llm = _mock_llm_stream(["Sure, I can help you design an aws architecture. What services do you need?"])
    session = ConversationSession(llm=llm)

    list(session.send_stream("design something on aws"))

    assert session.current_spec is None
