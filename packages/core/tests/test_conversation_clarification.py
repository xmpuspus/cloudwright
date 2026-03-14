"""Tests for clarification-first routing in ConversationSession.send()."""

from __future__ import annotations

from unittest.mock import MagicMock

from cloudwright.architect import ConversationSession
from cloudwright.spec import Constraints


def _mock_llm(responses):
    llm = MagicMock()
    llm.generate.side_effect = [(r, {"input_tokens": 10, "output_tokens": 20}) for r in responses]
    return llm


def test_short_ambiguous_message_gets_clarification():
    llm = _mock_llm([])
    session = ConversationSession(llm=llm)

    text, spec = session.send("hi")

    assert "Could you tell me more" in text
    assert spec is None
    llm.generate.assert_not_called()


def test_cloud_keyword_skips_clarification():
    llm = _mock_llm(["Sure, here is an aws app."])
    session = ConversationSession(llm=llm)

    session.send("aws app")

    llm.generate.assert_called_once()


def test_long_message_skips_clarification():
    llm = _mock_llm(["Sure, here is your big app."])
    session = ConversationSession(llm=llm)

    session.send("build me a big app")

    llm.generate.assert_called_once()


def test_clarification_skipped_with_constraints():
    llm = _mock_llm(["Here is your app."])
    constraints = Constraints(budget_monthly=100.0)
    session = ConversationSession(llm=llm, constraints=constraints)

    session.send("hi")

    llm.generate.assert_called_once()


def test_clarification_skipped_after_history():
    llm = _mock_llm(["R1", "R2", "R3", "R4"])
    session = ConversationSession(llm=llm)

    session.send("design an app on aws")
    session.send("add redis on aws")
    session.send("something on aws")

    # After 3 turns, short message should not get clarification
    call_count_before = llm.generate.call_count
    session.send("ok")
    assert llm.generate.call_count == call_count_before + 1


def test_clarification_still_adds_to_history():
    llm = _mock_llm([])
    session = ConversationSession(llm=llm)

    session.send("hi")

    assert len(session.history) == 2
    assert session.history[0]["role"] == "user"
    assert session.history[0]["content"] == "hi"
    assert session.history[1]["role"] == "assistant"
