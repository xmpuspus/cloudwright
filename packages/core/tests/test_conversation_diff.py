"""Tests for diff integration in ConversationSession.modify()."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from cloudwright.architect import ConversationSession
from cloudwright.spec import ArchSpec, Component, Connection


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


def _session_with_spec(llm):
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


def test_last_diff_none_before_modify():
    llm = _mock_llm([])
    session = ConversationSession(llm=llm)

    assert session.last_diff is None


def test_last_diff_set_after_modify():
    updated_json = _make_spec_json("Base App")
    llm = _mock_llm([updated_json])
    session = _session_with_spec(llm)

    session.modify("rename the app")

    assert session.last_diff is not None


def test_last_diff_shows_added_components():
    updated_json = _make_spec_json(
        "Base App",
        extra_components=[
            {"id": "cache", "service": "elasticache", "provider": "aws", "label": "Redis", "tier": 3, "config": {}}
        ],
    )
    llm = _mock_llm([updated_json])
    session = _session_with_spec(llm)

    session.modify("add ElastiCache for caching")

    added_ids = [c.id for c in session.last_diff.added]
    assert "cache" in added_ids


def test_diff_summary_present():
    updated_json = _make_spec_json(
        "Base App",
        extra_components=[
            {"id": "cdn", "service": "cloudfront", "provider": "aws", "label": "CDN", "tier": 1, "config": {}}
        ],
    )
    llm = _mock_llm([updated_json])
    session = _session_with_spec(llm)

    session.modify("add CloudFront CDN")

    assert isinstance(session.last_diff.summary, str)
    assert len(session.last_diff.summary) > 0
