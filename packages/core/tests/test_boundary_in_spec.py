"""Tests for v1.4 Boundary first-class support (VPC/subnet/SG round-trip)."""

from __future__ import annotations

from cloudwright.parsing import _parse_arch_spec
from cloudwright.spec import ArchSpec, Boundary, Component


def _spec_with_boundaries() -> ArchSpec:
    return ArchSpec(
        name="VPC App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="alb", service="alb", provider="aws", label="ALB", tier=1, config={}),
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={}),
        ],
        boundaries=[
            Boundary(id="main_vpc", kind="vpc", label="Main VPC", component_ids=["alb", "web", "db"]),
            Boundary(
                id="public_subnet",
                kind="subnet",
                label="Public",
                parent="main_vpc",
                component_ids=["alb"],
            ),
            Boundary(
                id="private_subnet",
                kind="subnet",
                label="Private",
                parent="main_vpc",
                component_ids=["web"],
            ),
            Boundary(
                id="db_subnet",
                kind="subnet",
                label="DB Isolated",
                parent="main_vpc",
                component_ids=["db"],
            ),
            Boundary(
                id="web_sg",
                kind="security_group",
                label="Web SG",
                parent="main_vpc",
                component_ids=["web"],
            ),
        ],
    )


class TestBoundaryRoundTrip:
    def test_yaml_round_trip_preserves_boundaries(self):
        spec = _spec_with_boundaries()
        yaml_text = spec.to_yaml()
        assert "boundaries" in yaml_text
        assert "main_vpc" in yaml_text
        assert "public_subnet" in yaml_text

        restored = ArchSpec.from_yaml(yaml_text)
        assert len(restored.boundaries) == 5
        assert {b.id for b in restored.boundaries} == {
            "main_vpc",
            "public_subnet",
            "private_subnet",
            "db_subnet",
            "web_sg",
        }
        assert restored.boundaries[0].kind == "vpc"
        # Parent linkage preserved.
        subnet = next(b for b in restored.boundaries if b.id == "public_subnet")
        assert subnet.parent == "main_vpc"

    def test_json_round_trip_preserves_boundaries(self):
        spec = _spec_with_boundaries()
        json_text = spec.to_json()
        restored = ArchSpec.model_validate_json(json_text)
        assert len(restored.boundaries) == 5
        sg = next(b for b in restored.boundaries if b.id == "web_sg")
        assert sg.kind == "security_group"

    def test_parse_arch_spec_pulls_boundaries_from_llm_output(self):
        """LLM output containing a boundaries array gets parsed into Boundary objects."""
        data = {
            "name": "VPC App",
            "provider": "aws",
            "region": "us-east-1",
            "components": [
                {"id": "web", "service": "ec2", "provider": "aws", "label": "Web", "tier": 2, "config": {}},
                {"id": "db", "service": "rds", "provider": "aws", "label": "DB", "tier": 3, "config": {}},
            ],
            "connections": [{"source": "web", "target": "db", "label": "SQL"}],
            "boundaries": [
                {"id": "vpc1", "kind": "vpc", "label": "Main", "component_ids": ["web", "db"]},
                {"id": "sub_priv", "kind": "subnet", "parent": "vpc1", "component_ids": ["web"]},
            ],
        }
        spec = _parse_arch_spec(data, None)
        assert len(spec.boundaries) == 2
        assert spec.boundaries[0].id == "vpc1"
        assert spec.boundaries[1].parent == "vpc1"

    def test_invalid_boundary_id_skipped_gracefully(self):
        """A boundary with an invalid id is dropped, not crashed-on."""
        data = {
            "name": "App",
            "provider": "aws",
            "region": "us-east-1",
            "components": [
                {"id": "web", "service": "ec2", "provider": "aws", "label": "Web", "tier": 2, "config": {}},
            ],
            "connections": [],
            "boundaries": [
                {"id": "good_vpc", "kind": "vpc", "component_ids": ["web"]},
                {"id": "123-bad-id", "kind": "vpc", "component_ids": ["web"]},  # invalid id
                {"id": "missing_kind"},  # missing required field
            ],
        }
        spec = _parse_arch_spec(data, None)
        # Only the valid boundary survives.
        assert len(spec.boundaries) == 1
        assert spec.boundaries[0].id == "good_vpc"

    def test_boundary_filters_unknown_component_ids(self):
        """Component ids in a boundary that don't exist in components are dropped."""
        data = {
            "name": "App",
            "provider": "aws",
            "region": "us-east-1",
            "components": [
                {"id": "web", "service": "ec2", "provider": "aws", "label": "Web", "tier": 2, "config": {}},
            ],
            "connections": [],
            "boundaries": [
                {"id": "v", "kind": "vpc", "component_ids": ["web", "ghost", "phantom"]},
            ],
        }
        spec = _parse_arch_spec(data, None)
        assert spec.boundaries[0].component_ids == ["web"]
