"""Shared fixtures for core tests."""

from __future__ import annotations

import os

import pytest
from cloudwright.spec import ArchSpec, Component, Connection

HAS_LLM = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
skip_no_llm = pytest.mark.skipif(not HAS_LLM, reason="No LLM API key available")


@pytest.fixture
def sample_spec() -> ArchSpec:
    """A minimal two-component AWS spec for tests."""
    return ArchSpec(
        name="Test App",
        version=1,
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web Server",
                tier=2,
                config={"instance_type": "m5.large"},
            ),
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="Database",
                tier=3,
                config={"engine": "postgres", "instance_class": "db.r5.large"},
            ),
        ],
        connections=[
            Connection(source="web", target="db", label="SQL", protocol="TCP", port=5432),
        ],
    )


@pytest.fixture
def serverless_spec() -> ArchSpec:
    """A serverless AWS spec for tests."""
    return ArchSpec(
        name="Serverless API",
        version=1,
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="api", service="api_gateway", provider="aws", label="API GW", tier=0, config={}),
            Component(id="fn", service="lambda", provider="aws", label="Handler", tier=2, config={"memory_mb": 512}),
            Component(id="table", service="dynamodb", provider="aws", label="DynamoDB", tier=3, config={}),
        ],
        connections=[
            Connection(source="api", target="fn"),
            Connection(source="fn", target="table"),
        ],
    )
