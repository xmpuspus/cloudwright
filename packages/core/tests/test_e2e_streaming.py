"""E2E streaming tests — requires a real LLM API key."""

from __future__ import annotations

import pytest
from cloudwright.architect import ConversationSession
from conftest import skip_no_llm


@pytest.mark.e2e
@skip_no_llm
def test_streaming_produces_output():
    session = ConversationSession()

    chunks = list(session.send_stream("What is AWS EC2? One sentence."))

    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert len(full_text) > 10


@pytest.mark.e2e
@skip_no_llm
def test_streaming_extracts_spec():
    session = ConversationSession()

    list(session.send_stream("Design a 3-tier web app on AWS with EC2, RDS, and ALB"))

    assert session.current_spec is not None
    assert len(session.current_spec.components) >= 2
