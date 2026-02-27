"""Tests for ConversationSession multi-turn chat — all LLM calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from cloudwright.architect import ConversationSession
from cloudwright.spec import ArchSpec, Component, Connection, Constraints


def _make_spec_json(name: str = "Test App", extra_components: list[dict] | None = None) -> str:
    """Return a minimal valid spec as JSON text (no markdown fences)."""
    components = [
        {"id": "web", "service": "ec2", "provider": "aws", "label": "Web", "tier": 2, "config": {}},
        {"id": "db", "service": "rds", "provider": "aws", "label": "DB", "tier": 3, "config": {}},
    ]
    if extra_components:
        components.extend(extra_components)
    spec = {
        "name": name,
        "provider": "aws",
        "region": "us-east-1",
        "components": components,
        "connections": [{"source": "web", "target": "db", "label": "SQL"}],
    }
    return json.dumps(spec)


def _mock_llm(responses: list[str]) -> MagicMock:
    """Return a mock LLM that yields successive responses."""
    llm = MagicMock()
    llm.generate.side_effect = [(r, {"input_tokens": 10, "output_tokens": 20}) for r in responses]
    return llm


# ---------------------------------------------------------------------------
# History tracking
# ---------------------------------------------------------------------------


class TestHistoryTracking:
    def test_history_grows_with_each_turn(self):
        llm = _mock_llm(["Hello! What kind of architecture do you need?", "Sure, let me refine it."])
        session = ConversationSession(llm=llm)

        session.send("Hi")
        assert len(session.history) == 2  # user + assistant

        session.send("Something simpler please")
        assert len(session.history) == 4  # two rounds

    def test_history_alternates_roles(self):
        llm = _mock_llm(["Great idea!", "Got it."])
        session = ConversationSession(llm=llm)

        session.send("First message")
        session.send("Second message")

        roles = [m["role"] for m in session.history]
        assert roles == ["user", "assistant", "user", "assistant"]

    def test_full_history_passed_to_llm_each_turn(self):
        llm = _mock_llm(["Response 1", "Response 2"])
        session = ConversationSession(llm=llm)

        session.send("Turn one")
        session.send("Turn two")

        # history is passed by reference, so by the time we inspect it both
        # assistant replies are already appended — verify the second call
        # received content from at least the first round (user1 + assistant1 + user2)
        second_call_messages = llm.generate.call_args_list[1][0][0]
        contents = [m["content"] for m in second_call_messages]
        assert "Turn one" in contents
        assert "Response 1" in contents
        assert "Turn two" in contents


# ---------------------------------------------------------------------------
# Spec extraction from send()
# ---------------------------------------------------------------------------


class TestSendSpecExtraction:
    def test_send_returns_spec_when_json_present(self):
        spec_json = _make_spec_json("My App")
        llm = _mock_llm([spec_json])
        session = ConversationSession(llm=llm)

        text, spec = session.send("Design a web app")
        assert spec is not None
        assert isinstance(spec, ArchSpec)
        assert spec.name == "My App"

    def test_send_returns_none_spec_for_conversational_response(self):
        llm = _mock_llm(["Sure, I can help you design that. What regions do you need?"])
        session = ConversationSession(llm=llm)

        _text, spec = session.send("I need an architecture")
        assert spec is None

    def test_send_returns_none_spec_when_json_lacks_components(self):
        # JSON present but not an arch spec
        llm = _mock_llm(['{"status": "ok"}'])
        session = ConversationSession(llm=llm)

        _text, spec = session.send("Anything")
        assert spec is None

    def test_current_spec_updated_after_send(self):
        spec_json = _make_spec_json("Initial")
        llm = _mock_llm([spec_json])
        session = ConversationSession(llm=llm)

        assert session.current_spec is None
        session.send("Design something")
        assert session.current_spec is not None
        assert session.current_spec.name == "Initial"

    def test_current_spec_tracks_latest(self):
        first = _make_spec_json("First")
        second = _make_spec_json("Second")
        llm = _mock_llm([first, second])
        session = ConversationSession(llm=llm)

        session.send("First design")
        assert session.current_spec.name == "First"

        session.send("Second design")
        assert session.current_spec.name == "Second"


# ---------------------------------------------------------------------------
# modify()
# ---------------------------------------------------------------------------


class TestModify:
    def _session_with_spec(self, llm: MagicMock) -> ConversationSession:
        """Helper: create a session that already has a current_spec."""
        session = ConversationSession(llm=llm)
        session.current_spec = ArchSpec(
            name="Base App",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
                Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={}),
            ],
            connections=[Connection(source="web", target="db", label="SQL")],
        )
        return session

    def test_modify_raises_without_current_spec(self):
        llm = _mock_llm([])
        session = ConversationSession(llm=llm)

        with pytest.raises(ValueError, match="No current architecture"):
            session.modify("Add a cache layer")

    def test_modify_returns_updated_spec(self):
        updated_json = _make_spec_json(
            "Base App",
            extra_components=[
                {"id": "cache", "service": "elasticache", "provider": "aws", "label": "Redis", "tier": 3, "config": {}}
            ],
        )
        llm = _mock_llm([updated_json])
        session = self._session_with_spec(llm)

        result = session.modify("Add ElastiCache Redis between web and db")
        assert isinstance(result, ArchSpec)
        service_ids = [c.id for c in result.components]
        assert "cache" in service_ids

    def test_modify_updates_current_spec(self):
        updated_json = _make_spec_json("Updated App")
        llm = _mock_llm([updated_json])
        session = self._session_with_spec(llm)

        session.modify("Rename the app")
        assert session.current_spec.name == "Updated App"

    def test_modify_appends_to_history(self):
        updated_json = _make_spec_json("Base App")
        llm = _mock_llm([updated_json])
        session = self._session_with_spec(llm)

        session.modify("Add a cache")
        assert len(session.history) == 2
        assert session.history[0]["role"] == "user"
        assert "Modification:" in session.history[0]["content"]
        assert session.history[1]["role"] == "assistant"

    def test_modify_passes_current_spec_in_prompt(self):
        updated_json = _make_spec_json("Base App")
        llm = _mock_llm([updated_json])
        session = self._session_with_spec(llm)

        session.modify("Add monitoring")
        prompt = llm.generate.call_args[0][0][0]["content"]
        assert "Current architecture:" in prompt
        assert "Add monitoring" in prompt

    def test_modify_preserves_cost_estimate(self):
        from cloudwright.spec import CostEstimate

        updated_json = _make_spec_json("Base App")
        llm = _mock_llm([updated_json])
        session = self._session_with_spec(llm)
        session.current_spec.cost_estimate = CostEstimate(monthly_total=500.0, components=[])

        result = session.modify("Minor tweak")
        # Cost should be carried over since LLM response had none
        assert result.cost_estimate is not None
        assert result.cost_estimate.monthly_total == 500.0


# ---------------------------------------------------------------------------
# Constraints propagation
# ---------------------------------------------------------------------------


class TestConstraints:
    def test_constraints_stored_on_session(self):
        llm = _mock_llm([])
        constraints = Constraints(budget_monthly=200.0, compliance=["hipaa"])
        session = ConversationSession(llm=llm, constraints=constraints)
        assert session.constraints == constraints

    def test_constraints_applied_to_extracted_spec(self):
        spec_json = _make_spec_json("Constrained App")
        llm = _mock_llm([spec_json])
        constraints = Constraints(budget_monthly=100.0)
        session = ConversationSession(llm=llm, constraints=constraints)

        _text, spec = session.send("Design within budget")
        assert spec is not None
        assert spec.constraints is not None
        assert spec.constraints.budget_monthly == 100.0
