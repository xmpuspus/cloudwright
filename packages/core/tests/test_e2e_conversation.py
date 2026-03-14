"""E2E tests for ConversationSession — requires a real LLM API key."""

from __future__ import annotations

import pytest
from cloudwright.architect import ConversationSession
from cloudwright.session_store import SessionStore
from conftest import skip_no_llm


@pytest.mark.e2e
@skip_no_llm
def test_full_conversation_flow():
    session = ConversationSession()

    text, spec = session.send("Design a 3-tier web app on AWS with EC2, RDS, and a load balancer")

    assert isinstance(text, str)
    assert len(text) > 0
    assert spec is not None
    assert len(spec.components) >= 2

    modified = session.modify("Add an S3 bucket for static asset storage")

    assert modified is not None
    services = [c.service for c in modified.components]
    assert any("s3" in s.lower() for s in services)

    summary = session.get_usage_summary()
    assert summary["input_tokens"] > 0
    assert summary["output_tokens"] > 0
    assert summary["turn_count"] >= 1


@pytest.mark.e2e
@skip_no_llm
def test_session_save_load_roundtrip(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = ConversationSession(session_id="e2e-roundtrip")

    _text, spec = session.send("Design a serverless API on AWS with Lambda and DynamoDB")
    assert spec is not None

    store.save("e2e-roundtrip", session)
    loaded = store.load("e2e-roundtrip")

    assert loaded.current_spec is not None
    assert loaded.current_spec.name == spec.name
    component_ids = {c.id for c in loaded.current_spec.components}
    original_ids = {c.id for c in spec.components}
    assert component_ids == original_ids
