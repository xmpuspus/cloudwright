"""Tests for blast radius analyzer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cloudwright.analyzer import Analyzer
from cloudwright.spec import ArchSpec, Component, Connection


def _make_spec(name: str, components: list[tuple], connections: list[tuple]) -> ArchSpec:
    """Helper to build specs concisely. components: (id, service), connections: (src, tgt)."""
    return ArchSpec(
        name=name,
        components=[
            Component(id=cid, service=svc, provider="aws", label=cid, tier=i) for i, (cid, svc) in enumerate(components)
        ],
        connections=[Connection(source=src, target=tgt) for src, tgt in connections],
    )


class TestEmptySpec:
    def test_empty_spec_returns_empty_result(self):
        spec = ArchSpec(name="Empty")
        result = Analyzer().analyze(spec)

        assert result.total_components == 0
        assert result.max_blast_radius == 0
        assert result.spofs == []
        assert result.critical_path == []
        assert result.components == []


class TestLinearChain:
    """A -> B -> C: A affects both, B affects C, C affects nothing."""

    @pytest.fixture
    def result(self):
        spec = _make_spec("chain", [("A", "ec2"), ("B", "rds"), ("C", "s3")], [("A", "B"), ("B", "C")])
        return Analyzer().analyze(spec)

    def test_blast_radii(self, result):
        by_id = {c.component_id: c for c in result.components}
        assert by_id["A"].blast_radius == 2
        assert by_id["B"].blast_radius == 1
        assert by_id["C"].blast_radius == 0

    def test_direct_dependents(self, result):
        by_id = {c.component_id: c for c in result.components}
        assert by_id["A"].direct_dependents == ["B"]
        assert by_id["B"].direct_dependents == ["C"]
        assert by_id["C"].direct_dependents == []

    def test_transitive_dependents(self, result):
        by_id = {c.component_id: c for c in result.components}
        assert set(by_id["A"].transitive_dependents) == {"B", "C"}
        assert set(by_id["B"].transitive_dependents) == {"C"}
        assert by_id["C"].transitive_dependents == []

    def test_spofs(self, result):
        # A is only upstream for B, B is only upstream for C
        by_id = {c.component_id: c for c in result.components}
        assert by_id["A"].is_spof is True
        assert by_id["B"].is_spof is True
        assert by_id["C"].is_spof is False
        assert set(result.spofs) == {"A", "B"}

    def test_sorted_by_blast_radius(self, result):
        radii = [c.blast_radius for c in result.components]
        assert radii == sorted(radii, reverse=True)


class TestFanOut:
    """A -> B, A -> C, A -> D: A has blast_radius=3, is SPOF for all three."""

    @pytest.fixture
    def result(self):
        spec = _make_spec(
            "fanout",
            [("A", "alb"), ("B", "ec2"), ("C", "ec2"), ("D", "ec2")],
            [("A", "B"), ("A", "C"), ("A", "D")],
        )
        return Analyzer().analyze(spec)

    def test_blast_radius(self, result):
        by_id = {c.component_id: c for c in result.components}
        assert by_id["A"].blast_radius == 3
        assert by_id["B"].blast_radius == 0
        assert by_id["C"].blast_radius == 0
        assert by_id["D"].blast_radius == 0

    def test_a_is_spof_for_all_dependents(self, result):
        by_id = {c.component_id: c for c in result.components}
        assert by_id["A"].is_spof is True

    def test_leaves_not_spof(self, result):
        by_id = {c.component_id: c for c in result.components}
        for leaf in ("B", "C", "D"):
            assert by_id[leaf].is_spof is False


class TestDiamond:
    """A->B, A->C, B->D, C->D: D has 2 upstream so B and C are NOT SPOFs for D."""

    @pytest.fixture
    def result(self):
        spec = _make_spec(
            "diamond",
            [("A", "alb"), ("B", "ec2"), ("C", "ec2"), ("D", "rds")],
            [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")],
        )
        return Analyzer().analyze(spec)

    def test_blast_radii(self, result):
        by_id = {c.component_id: c for c in result.components}
        assert by_id["A"].blast_radius == 3  # B, C, D
        assert by_id["B"].blast_radius == 1  # D
        assert by_id["C"].blast_radius == 1  # D
        assert by_id["D"].blast_radius == 0

    def test_b_and_c_not_spof(self, result):
        by_id = {c.component_id: c for c in result.components}
        # D has two upstream providers (B and C), so neither is a SPOF
        assert by_id["B"].is_spof is False
        assert by_id["C"].is_spof is False

    def test_a_is_spof(self, result):
        by_id = {c.component_id: c for c in result.components}
        # A is the sole upstream for both B and C
        assert by_id["A"].is_spof is True


class TestDisconnectedComponents:
    def test_disconnected_have_zero_blast_radius(self):
        spec = _make_spec(
            "disconnected",
            [("A", "ec2"), ("B", "s3")],
            [],  # no connections
        )
        result = Analyzer().analyze(spec)
        by_id = {c.component_id: c for c in result.components}
        assert by_id["A"].blast_radius == 0
        assert by_id["B"].blast_radius == 0
        assert result.spofs == []
        assert result.max_blast_radius == 0


class TestCycleHandling:
    def test_cycle_does_not_infinite_loop(self):
        # A -> B -> A (cycle)
        spec = _make_spec("cycle", [("A", "ec2"), ("B", "ec2")], [("A", "B"), ("B", "A")])
        result = Analyzer().analyze(spec)  # must not hang

        assert result.total_components == 2
        by_id = {c.component_id: c for c in result.components}
        # Each sees the other as transitive dependent but not itself
        assert "A" not in by_id["A"].transitive_dependents
        assert "B" not in by_id["B"].transitive_dependents


class TestComponentFilter:
    def test_filter_returns_only_specified_component(self):
        spec = _make_spec("chain", [("A", "ec2"), ("B", "rds"), ("C", "s3")], [("A", "B"), ("B", "C")])
        result = Analyzer().analyze(spec, component_id="B")

        assert len(result.components) == 1
        assert result.components[0].component_id == "B"
        # Graph context is still full
        assert "A" in result.graph
        assert "C" in result.graph

    def test_total_components_reflects_full_spec(self):
        spec = _make_spec("chain", [("A", "ec2"), ("B", "rds")], [("A", "B")])
        result = Analyzer().analyze(spec, component_id="A")
        assert result.total_components == 2


class TestCriticalPath:
    def test_critical_path_is_valid_graph_path(self):
        spec = _make_spec("chain", [("A", "ec2"), ("B", "rds"), ("C", "s3")], [("A", "B"), ("B", "C")])
        result = Analyzer().analyze(spec)

        path = result.critical_path
        assert len(path) >= 1
        # Every consecutive pair must be an edge in the forward graph
        for i in range(len(path) - 1):
            assert path[i + 1] in result.graph.get(path[i], [])

    def test_critical_path_starts_from_high_impact(self):
        spec = _make_spec("chain", [("A", "ec2"), ("B", "rds"), ("C", "s3")], [("A", "B"), ("B", "C")])
        result = Analyzer().analyze(spec)
        # A has highest blast radius, so path should start there
        assert result.critical_path[0] == "A"

    def test_linear_chain_full_path(self):
        spec = _make_spec("chain", [("A", "ec2"), ("B", "rds"), ("C", "s3")], [("A", "B"), ("B", "C")])
        result = Analyzer().analyze(spec)
        assert result.critical_path == ["A", "B", "C"]


class TestToDict:
    def test_to_dict_is_json_serializable(self):
        spec = _make_spec("chain", [("A", "ec2"), ("B", "rds")], [("A", "B")])
        result = Analyzer().analyze(spec)
        d = result.to_dict()
        # Should not raise
        serialized = json.dumps(d)
        parsed = json.loads(serialized)
        assert parsed["total_components"] == 2

    def test_to_dict_shape(self):
        spec = _make_spec("chain", [("A", "ec2"), ("B", "rds")], [("A", "B")])
        result = Analyzer().analyze(spec)
        d = result.to_dict()
        assert "total_components" in d
        assert "max_blast_radius" in d
        assert "spofs" in d
        assert "critical_path" in d
        assert "components" in d
        assert "graph" in d
        comp = d["components"][0]
        for key in (
            "component_id",
            "service",
            "label",
            "tier",
            "direct_dependents",
            "transitive_dependents",
            "blast_radius",
            "is_spof",
        ):
            assert key in comp


class TestThreeTierTemplate:
    @pytest.fixture
    def result(self):
        template = Path(__file__).parents[3] / "catalog" / "templates" / "three_tier_web.yaml"
        spec = ArchSpec.from_file(template)
        return Analyzer().analyze(spec)

    def test_produces_non_empty_analysis(self, result):
        assert result.total_components == 4
        assert len(result.components) == 4

    def test_cdn_has_highest_blast_radius(self, result):
        by_id = {c.component_id: c for c in result.components}
        assert by_id["cdn"].blast_radius == 3

    def test_db_has_zero_blast_radius(self, result):
        by_id = {c.component_id: c for c in result.components}
        assert by_id["db"].blast_radius == 0

    def test_spofs_detected(self, result):
        # Linear chain — cdn, alb, web are each sole upstream for their dependent
        assert len(result.spofs) >= 1
        assert "cdn" in result.spofs

    def test_critical_path_traverses_chain(self, result):
        path = result.critical_path
        assert len(path) >= 2
        # Path must start at cdn (highest blast radius)
        assert path[0] == "cdn"
