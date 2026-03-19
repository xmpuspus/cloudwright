"""Tests for token tracking and cost estimation in ConversationSession."""

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


def _mock_llm(responses):
    llm = MagicMock()
    llm.generate.side_effect = [(r, {"input_tokens": 10, "output_tokens": 20}) for r in responses]
    return llm


def test_usage_tracked_after_send():
    llm = _mock_llm(["Here is the architecture."])
    session = ConversationSession(llm=llm)

    session.send("design a web app on aws")

    assert session.last_usage["input_tokens"] == 10
    assert session.last_usage["output_tokens"] == 20
    assert "estimated_cost" in session.last_usage


def test_cumulative_usage_accumulates():
    llm = _mock_llm(["Response 1", "Response 2"])
    session = ConversationSession(llm=llm)

    session.send("design a web app on aws")
    session.send("make it serverless on aws")

    assert session.cumulative_usage["input_tokens"] == 20
    assert session.cumulative_usage["output_tokens"] == 40


def test_usage_tracked_after_modify():
    updated_json = _make_spec_json("Modified App")
    llm = _mock_llm([updated_json])
    session = ConversationSession(llm=llm)
    from cloudwright.spec import ArchSpec, Component, Connection

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

    session.modify("add a cache layer")

    assert session.last_usage["input_tokens"] == 10
    assert session.last_usage["output_tokens"] == 20
    assert session.cumulative_usage["input_tokens"] == 10


def test_get_usage_summary():
    llm = _mock_llm(["response 1", "response 2"])
    session = ConversationSession(llm=llm)

    session.send("design a web app on aws")
    session.send("add a load balancer on aws")

    summary = session.get_usage_summary()
    assert summary["input_tokens"] == 20
    assert summary["output_tokens"] == 40
    assert "total_cost" in summary
    assert summary["turn_count"] == 2


def test_initial_usage_is_zero():
    llm = _mock_llm([])
    session = ConversationSession(llm=llm)

    assert session.cumulative_usage["input_tokens"] == 0
    assert session.cumulative_usage["output_tokens"] == 0
    assert session.cumulative_usage["total_cost"] == 0.0


def test_cost_estimation_positive():
    llm = _mock_llm(["Here is your web architecture on aws."])
    session = ConversationSession(llm=llm)

    session.send("design a web app on aws")

    assert session.last_usage["estimated_cost"] > 0
