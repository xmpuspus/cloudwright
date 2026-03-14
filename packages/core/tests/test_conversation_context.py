"""Tests for history trimming and context token estimation."""

from __future__ import annotations

from unittest.mock import MagicMock

from cloudwright.architect import ConversationSession


def _mock_llm(responses):
    llm = MagicMock()
    llm.generate.side_effect = [(r, {"input_tokens": 10, "output_tokens": 20}) for r in responses]
    llm.estimate_tokens.side_effect = lambda text: len(text) // 4
    return llm


def test_trim_does_nothing_below_limit():
    llm = _mock_llm(["R1", "R2"])
    session = ConversationSession(llm=llm, max_history_turns=10)

    session.send("design an app on aws")
    session.send("add redis on aws")

    assert len(session.history) == 4


def test_trim_reduces_history():
    # With max_history_turns=2, a no-trim session of 5 sends would have 10 messages.
    # Verify trimming keeps message count below that ceiling.
    responses = ["R1", "R2", "R3", "R4", "R5"]
    llm_notrim = _mock_llm(responses[:])
    session_notrim = ConversationSession(llm=llm_notrim, max_history_turns=50)
    for msg in ["build an aws app", "add redis on aws", "add s3 on aws", "add cloudfront on aws"]:
        session_notrim.send(msg)

    responses2 = ["R1", "R2", "R3", "R4", "R5"]
    llm = _mock_llm(responses2)
    session = ConversationSession(llm=llm, max_history_turns=2)
    for msg in ["build an aws app", "add redis on aws", "add s3 on aws", "add cloudfront on aws"]:
        session.send(msg)

    assert len(session.history) < len(session_notrim.history)


def test_trimmed_history_has_summary():
    responses = ["R1", "R2", "R3"]
    llm = _mock_llm(responses)
    session = ConversationSession(llm=llm, max_history_turns=1)

    session.send("build an aws app")
    session.send("add redis on aws")
    session.send("add s3 on aws")

    first_content = session.history[0]["content"]
    assert "Earlier conversation summary" in first_content


def test_estimate_context_tokens():
    llm = _mock_llm(["Hello, here is your aws architecture."])
    session = ConversationSession(llm=llm)

    session.send("design a web app on aws")

    tokens = session.estimate_context_tokens()
    assert isinstance(tokens, int)
    assert tokens > 0


def test_custom_max_history_turns():
    llm = _mock_llm([])
    session = ConversationSession(llm=llm, max_history_turns=5)

    assert session.max_history_turns == 5
