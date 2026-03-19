"""Tests for ConversationSession serialization and SessionStore."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from cloudwright.architect import ConversationSession
from cloudwright.session_store import SessionStore
from cloudwright.spec import ArchSpec, Component, Connection, Constraints


def _make_spec_json(name="Test App", extra_components=None):
    components = [
        {"id": "web", "service": "ec2", "provider": "aws", "label": "Web", "tier": 2, "config": {}},
        {"id": "db", "service": "rds", "provider": "aws", "label": "DB", "tier": 3, "config": {}},
    ]
    if extra_components:
        components.extend(extra_components)
    return json.dumps(
        {
            "name": name,
            "provider": "aws",
            "region": "us-east-1",
            "components": components,
            "connections": [{"source": "web", "target": "db", "label": "SQL"}],
        }
    )


def _mock_llm(responses):
    llm = MagicMock()
    llm.generate.side_effect = [(r, {"input_tokens": 10, "output_tokens": 20}) for r in responses]
    return llm


def _make_session_with_spec(llm=None) -> ConversationSession:
    llm = llm or MagicMock()
    session = ConversationSession(llm=llm, session_id="test-123")
    session.current_spec = ArchSpec(
        name="Saved App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={}),
        ],
        connections=[Connection(source="web", target="db", label="SQL")],
    )
    return session


def test_to_dict_includes_all_fields():
    session = _make_session_with_spec()
    session.history = [{"role": "user", "content": "hello"}]
    session.cumulative_usage = {"input_tokens": 5, "output_tokens": 10, "total_cost": 0.0001}

    data = session.to_dict()

    assert "session_id" in data
    assert "history" in data
    assert "current_spec" in data
    assert "constraints" in data
    assert "cumulative_usage" in data


def test_from_dict_restores_session():
    session = _make_session_with_spec()
    session.history = [
        {"role": "user", "content": "design an aws app"},
        {"role": "assistant", "content": "Sure!"},
    ]
    session.cumulative_usage = {"input_tokens": 50, "output_tokens": 100, "total_cost": 0.002}

    data = session.to_dict()
    restored = ConversationSession.from_dict(data, llm=MagicMock())

    assert restored.session_id == session.session_id
    assert restored.history == session.history
    assert restored.cumulative_usage == session.cumulative_usage


def test_from_dict_with_spec():
    session = _make_session_with_spec()

    data = session.to_dict()
    restored = ConversationSession.from_dict(data, llm=MagicMock())

    assert restored.current_spec is not None
    assert restored.current_spec.name == "Saved App"
    assert len(restored.current_spec.components) == 2


def test_from_dict_with_constraints():
    llm = MagicMock()
    constraints = Constraints(budget_monthly=300.0, compliance=["hipaa"])
    session = ConversationSession(llm=llm, constraints=constraints, session_id="c-session")

    data = session.to_dict()
    restored = ConversationSession.from_dict(data, llm=MagicMock())

    assert restored.constraints is not None
    assert restored.constraints.budget_monthly == 300.0
    assert "hipaa" in restored.constraints.compliance


def test_session_store_save_and_load(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = _make_session_with_spec()
    session.history = [{"role": "user", "content": "design an aws app"}]

    store.save("test-123", session)
    loaded = store.load("test-123", llm=MagicMock())

    assert loaded.session_id == "test-123"
    assert len(loaded.history) == 1
    assert loaded.current_spec is not None
    assert loaded.current_spec.name == "Saved App"


def test_session_store_list(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = _make_session_with_spec()
    session.history = [
        {"role": "user", "content": "design an aws app"},
        {"role": "assistant", "content": "Here it is."},
    ]

    store.save("test-123", session)
    sessions = store.list_sessions()

    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "test-123"
    assert sessions[0]["turn_count"] == 1
    assert sessions[0]["has_spec"] is True
    assert sessions[0]["spec_name"] == "Saved App"


def test_session_store_delete(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = _make_session_with_spec()
    store.save("to-delete", session)

    result = store.delete("to-delete")

    assert result is True
    assert not (tmp_path / "to-delete.json").exists()


def test_session_store_load_not_found(tmp_path):
    store = SessionStore(base_dir=tmp_path)

    with pytest.raises(FileNotFoundError):
        store.load("nonexistent-session")
