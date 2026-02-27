"""Tests for plugin discovery system."""

import pytest
from cloudwright.plugins import (
    ALL_GROUPS,
    EXPORTER_GROUP,
    IMPORTER_GROUP,
    POLICY_GROUP,
    VALIDATOR_GROUP,
    discover_exporters,
    discover_importers,
    discover_plugins,
    discover_policies,
    discover_validators,
    list_plugins,
)


class TestPluginDiscovery:
    def test_discover_all_groups(self):
        """discover_plugins returns all groups even if empty."""
        result = discover_plugins()
        assert len(result) == 4
        for group in ALL_GROUPS:
            assert group in result
            assert isinstance(result[group], dict)

    def test_discover_single_group(self):
        result = discover_plugins(EXPORTER_GROUP)
        assert EXPORTER_GROUP in result
        assert len(result) == 1

    def test_discover_exporters(self):
        result = discover_exporters()
        assert isinstance(result, dict)

    def test_discover_validators(self):
        result = discover_validators()
        assert isinstance(result, dict)

    def test_discover_policies(self):
        result = discover_policies()
        assert isinstance(result, dict)

    def test_discover_importers(self):
        result = discover_importers()
        assert isinstance(result, dict)

    def test_list_plugins(self):
        result = list_plugins()
        assert isinstance(result, dict)
        for group in ALL_GROUPS:
            assert group in result
            assert isinstance(result[group], list)

    def test_group_names_correct(self):
        assert EXPORTER_GROUP == "cloudwright.exporters"
        assert VALIDATOR_GROUP == "cloudwright.validators"
        assert POLICY_GROUP == "cloudwright.policies"
        assert IMPORTER_GROUP == "cloudwright.importers"


class TestExporterPluginIntegration:
    def test_export_spec_includes_builtins(self):
        """Built-in formats still work with plugin system."""
        from cloudwright.exporter import FORMATS

        assert "terraform" in FORMATS
        assert "cloudformation" in FORMATS
        assert "mermaid" in FORMATS

    def test_get_all_formats_includes_builtins(self):
        from cloudwright.exporter import _get_all_formats

        all_formats = _get_all_formats()
        assert "terraform" in all_formats
        assert "cloudformation" in all_formats


class TestExporterPluginABC:
    def test_abc_cannot_instantiate(self):
        from cloudwright.exporter import ExporterPlugin

        with pytest.raises(TypeError):
            ExporterPlugin()

    def test_abc_subclass_works(self):
        from cloudwright.exporter import ExporterPlugin

        class DummyExporter(ExporterPlugin):
            def render(self, spec) -> str:
                return "dummy output"

            @property
            def format_name(self) -> str:
                return "dummy"

        exporter = DummyExporter()
        assert exporter.format_name == "dummy"
        assert exporter.render(None) == "dummy output"
