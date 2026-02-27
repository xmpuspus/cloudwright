"""Tests for the architecture diff engine."""

import pytest
from cloudwright.spec import ArchSpec, Component, ComponentCost, Connection, CostEstimate


def _spec_v1() -> ArchSpec:
    return ArchSpec(
        name="App v1",
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="web", service="ec2", provider="aws", label="Web", tier=2, config={"instance_type": "t3.medium"}
            ),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
        connections=[
            Connection(source="web", target="db", label="SQL"),
        ],
        cost_estimate=CostEstimate(
            monthly_total=100.0,
            breakdown=[
                ComponentCost(component_id="web", service="ec2", monthly=30.0),
                ComponentCost(component_id="db", service="rds", monthly=70.0),
            ],
        ),
    )


def _spec_v2() -> ArchSpec:
    return ArchSpec(
        name="App v2",
        version=2,
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="web", service="ec2", provider="aws", label="Web", tier=2, config={"instance_type": "m5.large"}
            ),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
            Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=3),
        ],
        connections=[
            Connection(source="web", target="cache", label="Cache"),
            Connection(source="web", target="db", label="SQL"),
            Connection(source="cache", target="db", label="Read-through"),
        ],
        cost_estimate=CostEstimate(
            monthly_total=148.60,
            breakdown=[
                ComponentCost(component_id="web", service="ec2", monthly=62.0),
                ComponentCost(component_id="db", service="rds", monthly=70.0),
                ComponentCost(component_id="cache", service="elasticache", monthly=16.60),
            ],
        ),
    )


class TestDiffer:
    def test_detects_added(self):
        from cloudwright.differ import Differ

        diff = Differ().diff(_spec_v1(), _spec_v2())
        added_ids = [c.id for c in diff.added]
        assert "cache" in added_ids

    def test_detects_removed(self):
        from cloudwright.differ import Differ

        diff = Differ().diff(_spec_v2(), _spec_v1())
        removed_ids = [c.id for c in diff.removed]
        assert "cache" in removed_ids

    def test_detects_changed(self):
        from cloudwright.differ import Differ

        diff = Differ().diff(_spec_v1(), _spec_v2())
        changed_ids = [c.component_id for c in diff.changed]
        assert "web" in changed_ids

    def test_cost_delta(self):
        from cloudwright.differ import Differ

        diff = Differ().diff(_spec_v1(), _spec_v2())
        assert diff.cost_delta == pytest.approx(48.60, abs=0.01)

    def test_summary_generated(self):
        from cloudwright.differ import Differ

        diff = Differ().diff(_spec_v1(), _spec_v2())
        assert diff.summary  # non-empty

    def test_no_diff_identical(self):
        from cloudwright.differ import Differ

        diff = Differ().diff(_spec_v1(), _spec_v1())
        assert len(diff.added) == 0
        assert len(diff.removed) == 0
        assert len(diff.changed) == 0
        assert diff.cost_delta == 0.0


def _base_spec(connections: list[Connection]) -> ArchSpec:
    return ArchSpec(
        name="Test",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
            Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=3),
        ],
        connections=connections,
    )


class TestConnectionDiff:
    def test_connection_added(self):
        from cloudwright.differ import Differ

        old = _base_spec([Connection(source="web", target="db", label="SQL")])
        new = _base_spec(
            [
                Connection(source="web", target="db", label="SQL"),
                Connection(source="web", target="cache", label="Cache"),
            ]
        )
        diff = Differ().diff(old, new)
        added = [(c.source, c.target) for c in diff.connection_changes if c.change_type == "added"]
        assert ("web", "cache") in added

    def test_connection_removed(self):
        from cloudwright.differ import Differ

        old = _base_spec(
            [
                Connection(source="web", target="db", label="SQL"),
                Connection(source="web", target="cache", label="Cache"),
            ]
        )
        new = _base_spec([Connection(source="web", target="db", label="SQL")])
        diff = Differ().diff(old, new)
        removed = [(c.source, c.target) for c in diff.connection_changes if c.change_type == "removed"]
        assert ("web", "cache") in removed

    def test_connection_changed(self):
        from cloudwright.differ import Differ

        old = _base_spec([Connection(source="web", target="db", label="SQL", protocol="tcp", port=5432)])
        new = _base_spec([Connection(source="web", target="db", label="Postgres", protocol="tcp", port=5433)])
        diff = Differ().diff(old, new)
        changes = {c.field: c for c in diff.connection_changes if c.change_type == "changed"}
        assert "label" in changes
        assert changes["label"].old_value == "SQL"
        assert changes["label"].new_value == "Postgres"
        assert "port" in changes
        assert changes["port"].old_value == "5432"
        assert changes["port"].new_value == "5433"

    def test_connection_no_changes(self):
        from cloudwright.differ import Differ

        spec = _base_spec([Connection(source="web", target="db", label="SQL", port=5432)])
        diff = Differ().diff(spec, spec)
        assert diff.connection_changes == []

    def test_connection_changes_in_summary(self):
        from cloudwright.differ import Differ

        old = _base_spec([Connection(source="web", target="db", label="SQL")])
        new = _base_spec(
            [
                Connection(source="web", target="db", label="SQL"),
                Connection(source="web", target="cache", label="Cache"),
            ]
        )
        diff = Differ().diff(old, new)
        assert "connection" in diff.summary.lower()
