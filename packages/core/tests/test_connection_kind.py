"""Tests for v1.4 Connection.kind enum (sync_request/async_event/stream/replication/batch)."""

from __future__ import annotations

import pytest
from cloudwright.parsing import _parse_arch_spec
from cloudwright.spec import ArchSpec, Component, Connection
from pydantic import ValidationError


class TestConnectionKindEnum:
    @pytest.mark.parametrize(
        "kind",
        ["sync_request", "async_event", "stream", "replication", "batch"],
    )
    def test_valid_kind_accepted(self, kind: str):
        conn = Connection(source="a", target="b", kind=kind)  # type: ignore[arg-type]
        assert conn.kind == kind

    def test_kind_defaults_to_none(self):
        conn = Connection(source="a", target="b")
        assert conn.kind is None

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValidationError):
            Connection(source="a", target="b", kind="rpc")  # type: ignore[arg-type]


class TestConnectionKindRoundTrip:
    def test_kind_round_trips_through_yaml(self):
        spec = ArchSpec(
            name="App",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="api", service="api_gateway", provider="aws", label="API", tier=0, config={}),
                Component(id="fn", service="lambda", provider="aws", label="Fn", tier=2, config={}),
                Component(id="q", service="sqs", provider="aws", label="Q", tier=3, config={}),
                Component(id="db", service="dynamodb", provider="aws", label="DB", tier=3, config={}),
            ],
            connections=[
                Connection(source="api", target="fn", label="invoke", kind="sync_request"),
                Connection(source="fn", target="q", label="enqueue", kind="async_event"),
                Connection(source="fn", target="db", label="query", kind="sync_request"),
            ],
        )
        yaml_text = spec.to_yaml()
        assert "sync_request" in yaml_text
        assert "async_event" in yaml_text

        restored = ArchSpec.from_yaml(yaml_text)
        kinds = {(c.source, c.target): c.kind for c in restored.connections}
        assert kinds[("api", "fn")] == "sync_request"
        assert kinds[("fn", "q")] == "async_event"

    def test_kind_omitted_when_none(self):
        """to_yaml() with exclude_none should not emit kind: null."""
        spec = ArchSpec(
            name="App",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="a", service="ec2", provider="aws", label="A", tier=2, config={}),
                Component(id="b", service="rds", provider="aws", label="B", tier=3, config={}),
            ],
            connections=[Connection(source="a", target="b", kind=None)],
        )
        yaml_text = spec.to_yaml()
        assert "kind" not in yaml_text

    def test_parse_arch_spec_normalizes_kind_variants(self):
        """LLM-emitted variants like 'sync', 'async', 'http' get coerced to canonical kinds."""
        data = {
            "name": "App",
            "provider": "aws",
            "region": "us-east-1",
            "components": [
                {"id": "a", "service": "ec2", "provider": "aws", "label": "A", "tier": 2, "config": {}},
                {"id": "b", "service": "rds", "provider": "aws", "label": "B", "tier": 3, "config": {}},
            ],
            "connections": [
                {"source": "a", "target": "b", "kind": "Sync-Request"},  # case + dash
                {"source": "a", "target": "b", "kind": "async"},  # short alias
                {"source": "a", "target": "b", "kind": "http"},  # protocol-named alias
                {"source": "a", "target": "b", "kind": "junk_value"},  # invalid -> None
            ],
        }
        spec = _parse_arch_spec(data, None)
        kinds = [c.kind for c in spec.connections]
        assert kinds[0] == "sync_request"
        assert kinds[1] == "async_event"
        assert kinds[2] == "sync_request"
        assert kinds[3] is None  # invalid silently dropped

    def test_parse_arch_spec_handles_missing_kind(self):
        """Connections without `kind` field get kind=None (back-compat)."""
        data = {
            "name": "App",
            "provider": "aws",
            "region": "us-east-1",
            "components": [
                {"id": "a", "service": "ec2", "provider": "aws", "label": "A", "tier": 2, "config": {}},
                {"id": "b", "service": "rds", "provider": "aws", "label": "B", "tier": 3, "config": {}},
            ],
            "connections": [{"source": "a", "target": "b", "label": "SQL"}],
        }
        spec = _parse_arch_spec(data, None)
        assert spec.connections[0].kind is None
