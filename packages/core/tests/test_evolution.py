"""Tests for architecture evolution timeline."""

from __future__ import annotations

from cloudwright.evolution import create_version, diff_versions, get_timeline
from cloudwright.spec import ArchSpec, ArchVersion, Component, Connection


def _base_spec() -> ArchSpec:
    return ArchSpec(
        name="Test App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={}),
        ],
        connections=[Connection(source="web", target="db", label="SQL")],
    )


class TestCreateVersion:
    def test_returns_version_id_string(self):
        spec = _base_spec()
        vid = create_version(spec)
        assert isinstance(vid, str)
        assert len(vid) == 12

    def test_version_appended_to_history(self):
        spec = _base_spec()
        assert len(spec.history) == 0
        create_version(spec, description="initial", author="alice")
        assert len(spec.history) == 1

    def test_version_fields_populated(self):
        spec = _base_spec()
        vid = create_version(spec, description="initial deploy", author="alice")
        v = spec.history[0]
        assert v.version_id == vid
        assert v.description == "initial deploy"
        assert v.author == "alice"
        assert v.timestamp != ""
        assert v.parent_version == ""  # first version has no parent

    def test_second_version_has_parent(self):
        spec = _base_spec()
        v1 = create_version(spec, description="v1")
        create_version(spec, description="v2")
        assert spec.history[1].parent_version == v1

    def test_version_id_is_content_hash(self):
        spec1 = _base_spec()
        spec2 = _base_spec()
        # Same content → same hash
        v1 = create_version(spec1)
        v2 = create_version(spec2)
        assert v1 == v2

    def test_different_content_different_id(self):
        spec1 = _base_spec()
        spec2 = _base_spec()
        spec2 = spec2.model_copy(update={"name": "Different App"})
        v1 = create_version(spec1)
        v2 = create_version(spec2)
        assert v1 != v2

    def test_sequential_versions_accumulate(self):
        spec = _base_spec()
        for i in range(3):
            create_version(spec, description=f"version {i}")
        assert len(spec.history) == 3


class TestGetTimeline:
    def test_empty_history_returns_empty_list(self):
        spec = _base_spec()
        assert get_timeline(spec) == []

    def test_timeline_entry_structure(self):
        spec = _base_spec()
        create_version(spec, description="initial", author="bob")
        timeline = get_timeline(spec)
        assert len(timeline) == 1
        entry = timeline[0]
        assert set(entry.keys()) == {"version", "timestamp", "author", "description", "parent"}
        assert entry["author"] == "bob"
        assert entry["description"] == "initial"
        assert entry["parent"] == ""

    def test_timeline_preserves_order(self):
        spec = _base_spec()
        create_version(spec, description="v1")
        create_version(spec, description="v2")
        create_version(spec, description="v3")
        timeline = get_timeline(spec)
        assert [e["description"] for e in timeline] == ["v1", "v2", "v3"]

    def test_timeline_parent_chain(self):
        spec = _base_spec()
        v1 = create_version(spec, description="v1")
        create_version(spec, description="v2")
        timeline = get_timeline(spec)
        assert timeline[1]["parent"] == v1


class TestDiffVersions:
    def test_returns_expected_keys(self):
        spec_v1 = _base_spec()
        create_version(spec_v1, description="v1")
        spec_v2 = _base_spec()
        spec_v2 = spec_v2.model_copy(
            update={
                "components": spec_v2.components
                + [Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=3, config={})]
            }
        )
        create_version(spec_v2, description="v2")
        result = diff_versions(spec_v1, spec_v2)
        assert set(result.keys()) == {
            "from_version",
            "to_version",
            "added",
            "removed",
            "changed",
            "connection_changes",
            "cost_delta",
            "summary",
        }

    def test_added_component_counted(self):
        spec_v1 = _base_spec()
        create_version(spec_v1, description="v1")
        spec_v2 = _base_spec()
        spec_v2 = spec_v2.model_copy(
            update={
                "components": spec_v2.components
                + [Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=3, config={})]
            }
        )
        create_version(spec_v2, description="v2")
        result = diff_versions(spec_v1, spec_v2)
        assert result["added"] == 1
        assert result["removed"] == 0

    def test_removed_component_counted(self):
        spec_v1 = _base_spec()
        create_version(spec_v1, description="v1")
        spec_v2 = _base_spec()
        spec_v2 = spec_v2.model_copy(update={"components": spec_v2.components[:1]})
        create_version(spec_v2, description="v2")
        result = diff_versions(spec_v1, spec_v2)
        assert result["removed"] == 1

    def test_version_ids_in_result(self):
        spec_v1 = _base_spec()
        v1 = create_version(spec_v1, description="v1")
        spec_v2 = _base_spec()
        spec_v2 = spec_v2.model_copy(update={"name": "Updated App"})
        v2 = create_version(spec_v2, description="v2")
        result = diff_versions(spec_v1, spec_v2)
        assert result["from_version"] == v1
        assert result["to_version"] == v2

    def test_no_history_uses_unknown(self):
        spec_v1 = _base_spec()
        spec_v2 = _base_spec()
        result = diff_versions(spec_v1, spec_v2)
        assert result["from_version"] == "unknown"
        assert result["to_version"] == "unknown"

    def test_identical_specs_zero_changes(self):
        spec_v1 = _base_spec()
        create_version(spec_v1)
        spec_v2 = _base_spec()
        create_version(spec_v2)
        result = diff_versions(spec_v1, spec_v2)
        assert result["added"] == 0
        assert result["removed"] == 0
        assert result["changed"] == 0


class TestArchVersion:
    def test_arch_version_defaults(self):
        v = ArchVersion()
        assert v.version_id == ""
        assert v.timestamp == ""
        assert v.author == ""
        assert v.description == ""
        assert v.parent_version == ""

    def test_arch_spec_has_history_field(self):
        spec = _base_spec()
        assert hasattr(spec, "history")
        assert isinstance(spec.history, list)

    def test_history_serializes_to_yaml(self):
        spec = _base_spec()
        create_version(spec, description="initial")
        yaml_str = spec.to_yaml()
        assert "history" in yaml_str
        assert "version_id" in yaml_str
