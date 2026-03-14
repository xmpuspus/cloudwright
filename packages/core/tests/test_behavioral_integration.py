"""Behavioral integration tests — multi-turn flows with a real LLM.

Each test class targets a specific behavioral contract. All tests that hit the
LLM are marked @pytest.mark.e2e and guarded by skip_no_llm so they are skipped
in CI without API keys.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from cloudwright.architect import ConversationSession
from cloudwright.session_store import SessionStore
from conftest import skip_no_llm

# ---------------------------------------------------------------------------
# TestMultiTurnConversation
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_no_llm
def test_multi_turn_spec_evolves():
    """Design -> modify -> modify again: spec grows and history accumulates."""
    session = ConversationSession()

    _text, spec1 = session.send("Design a 3-tier web app on AWS with EC2, RDS, and an ALB")
    assert spec1 is not None, "first turn should produce a spec"
    initial_count = len(spec1.components)

    spec2 = session.modify("Add an ElastiCache Redis cluster for session caching")
    services_after_redis = [c.service for c in spec2.components]
    assert any("elasticache" in s or "redis" in s.lower() for s in services_after_redis), (
        "cache component expected after modify"
    )
    assert len(spec2.components) >= initial_count, "components should not shrink"

    spec3 = session.modify("Add an S3 bucket for static asset storage")
    services_after_s3 = [c.service for c in spec3.components]
    assert any("s3" in s for s in services_after_s3), "S3 expected after second modify"

    # history should reflect all three turns
    user_turns = [m for m in session.history if m["role"] == "user"]
    assert len(user_turns) >= 3, "three user turns expected in history"


# ---------------------------------------------------------------------------
# TestUsageTrackingAccumulates
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_no_llm
def test_cumulative_usage_grows_and_cost_is_positive():
    """Usage totals increase monotonically across turns and cost stays positive."""
    session = ConversationSession()

    session.send("Design a serverless API on AWS with Lambda, API Gateway, and DynamoDB")
    after_first = session.get_usage_summary()
    assert after_first["input_tokens"] > 0, "tokens should be recorded after first turn"
    assert after_first["total_cost"] > 0, "cost must be positive"

    session.modify("Add an SNS topic for event notifications")
    after_second = session.get_usage_summary()
    assert after_second["input_tokens"] > after_first["input_tokens"], (
        "input tokens must grow after second LLM call"
    )
    assert after_second["total_cost"] > after_first["total_cost"], (
        "total cost must grow after second LLM call"
    )

    assert after_second["turn_count"] >= 2, "turn_count should reflect both user messages"


# ---------------------------------------------------------------------------
# TestStreamingMultiTurn
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_no_llm
def test_streaming_then_follow_up_preserves_spec():
    """Stream a design, then send a follow-up with send(); spec stays consistent."""
    session = ConversationSession()

    chunks = list(session.send_stream(
        "Design a microservices platform on GCP with Cloud Run and Cloud SQL"
    ))
    assert len(chunks) > 0, "streaming should yield chunks"
    streamed_spec = session.current_spec
    assert streamed_spec is not None, "streaming should produce a spec"

    _text, follow_spec = session.send("What are the main cost drivers in this architecture?")
    # The spec should not disappear after a follow-up question
    assert session.current_spec is not None, "spec must survive a follow-up turn"
    assert session.current_spec.provider == streamed_spec.provider, (
        "provider must remain consistent"
    )


# ---------------------------------------------------------------------------
# TestSessionPersistenceRoundTrip
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_no_llm
def test_session_save_load_then_continue(tmp_path):
    """Design, save, reload, verify fidelity, then continue modifying."""
    store = SessionStore(base_dir=tmp_path)
    session = ConversationSession(session_id="behavioral-roundtrip")

    _text, spec = session.send(
        "Design a data pipeline on AWS with S3, Glue, and Redshift"
    )
    assert spec is not None

    store.save("behavioral-roundtrip", session)

    loaded = store.load("behavioral-roundtrip")
    assert loaded.current_spec is not None, "spec must survive round-trip"
    assert loaded.current_spec.name == spec.name, "spec name must be preserved"
    assert loaded.cumulative_usage["input_tokens"] == session.cumulative_usage["input_tokens"], (
        "usage must be preserved"
    )

    # Continue from the loaded session — it must have enough context to modify
    spec_continued = loaded.modify("Add a Lambda function to trigger the Glue job on S3 events")
    assert spec_continued is not None, "modify should succeed from loaded session"
    assert len(spec_continued.components) >= len(spec.components), (
        "components should not regress after modification"
    )


# ---------------------------------------------------------------------------
# TestContextWindowEstimation
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_no_llm
def test_context_tokens_grow_with_turns():
    """estimate_context_tokens() increases as conversation history grows."""
    session = ConversationSession()

    session.send("Design an ECS cluster on AWS with ALB and RDS")
    tokens_after_1 = session.estimate_context_tokens()
    assert tokens_after_1 > 0, "context tokens should be nonzero after first turn"

    session.modify("Add CloudWatch dashboards for monitoring")
    tokens_after_2 = session.estimate_context_tokens()
    assert tokens_after_2 > tokens_after_1, (
        "context token count must grow as history expands"
    )

    session.send("What compliance controls should I add for SOC 2?")
    tokens_after_3 = session.estimate_context_tokens()
    assert tokens_after_3 > tokens_after_2, (
        "context token count must grow with each additional turn"
    )


# ---------------------------------------------------------------------------
# TestModifyProducesDiff
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_no_llm
def test_modify_produces_meaningful_diff():
    """modify() sets last_diff with non-empty added/changed/summary after adding a component."""
    session = ConversationSession()

    _text, spec = session.send("Design a simple two-tier app on AWS with EC2 and RDS")
    assert spec is not None

    session.modify("Add an ElastiCache Redis cluster and a CloudFront CDN")

    diff = session.last_diff
    assert diff is not None, "last_diff must be set after modify()"

    has_changes = len(diff.added) > 0 or len(diff.changed) > 0
    assert has_changes, "diff should reflect added components (added or changed must be non-empty)"
    assert isinstance(diff.summary, str) and len(diff.summary) > 0, (
        "diff.summary should be a non-empty string"
    )


# ---------------------------------------------------------------------------
# TestClarificationBehavior
# ---------------------------------------------------------------------------
# These tests use a mock LLM — no API key required.


def test_single_word_hi_returns_clarification_without_llm_call():
    """'hi' is too short and has no cloud keyword — must get clarification, no LLM hit."""
    llm = MagicMock()
    session = ConversationSession(llm=llm)

    text, spec = session.send("hi")

    assert "Could you tell me more" in text, "clarification prompt expected"
    assert spec is None, "no spec should be returned for ambiguous input"
    llm.generate.assert_not_called()


def test_design_aws_app_bypasses_clarification():
    """Multi-word messages with a cloud keyword bypass clarification and call the LLM."""
    llm = MagicMock()
    llm.generate.return_value = (
        "Sure, here is an AWS app design.",
        {"input_tokens": 10, "output_tokens": 20},
    )
    session = ConversationSession(llm=llm)

    text, _spec = session.send("Design AWS app")

    llm.generate.assert_called_once()
    assert isinstance(text, str)
