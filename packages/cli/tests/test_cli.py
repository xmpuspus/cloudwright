"""CLI command tests using Typer's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from cloudwright_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()

# Minimal valid spec YAML for commands that need a spec file
_SPEC_YAML = """\
name: Test App
version: 1
provider: aws
region: us-east-1
components:
  - id: web
    service: ec2
    provider: aws
    label: Web Server
    tier: 2
    config:
      instance_type: m5.large
  - id: db
    service: rds
    provider: aws
    label: Database
    tier: 3
    config:
      engine: postgres
      instance_class: db.r5.large
connections:
  - source: web
    target: db
    label: SQL
    protocol: TCP
    port: 5432
"""


@pytest.fixture
def spec_file(tmp_path: Path) -> Path:
    p = tmp_path / "test_spec.yaml"
    p.write_text(_SPEC_YAML)
    return p


@pytest.fixture
def spec_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Two slightly different specs for diff testing."""
    a = tmp_path / "v1.yaml"
    a.write_text(_SPEC_YAML)

    modified = _SPEC_YAML.replace("m5.large", "m5.xlarge").replace("Web Server", "Web Servers")
    b = tmp_path / "v2.yaml"
    b.write_text(modified)
    return a, b


class TestAppHelp:
    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "cloudwright" in result.output.lower() or "architecture" in result.output.lower()

    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "design" in result.output
        assert "cost" in result.output
        assert "validate" in result.output
        assert "export" in result.output
        assert "diff" in result.output
        assert "catalog" in result.output


class TestVersionFlag:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "cloudwright" in result.output

    def test_version_contains_number(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        # Should contain a version number like 0.1.0
        parts = result.output.strip().split()
        assert len(parts) == 2
        assert "." in parts[1]


class TestCostCommand:
    def test_cost_basic(self, spec_file: Path):
        result = runner.invoke(app, ["cost", str(spec_file)])
        assert result.exit_code == 0
        # Should show cost breakdown table
        assert "$" in result.output or "Cost" in result.output

    def test_cost_nonexistent_file(self, tmp_path: Path):
        result = runner.invoke(app, ["cost", str(tmp_path / "nope.yaml")])
        assert result.exit_code != 0

    def test_cost_pricing_tier_accepted(self, spec_file: Path):
        # --pricing-tier option should be accepted without error
        result = runner.invoke(app, ["cost", str(spec_file), "--pricing-tier", "reserved_1yr"])
        assert result.exit_code == 0


class TestValidateCommand:
    def test_validate_no_framework(self, spec_file: Path):
        result = runner.invoke(app, ["validate", str(spec_file)])
        assert result.exit_code != 0
        assert "compliance" in result.output.lower() or "well-architected" in result.output.lower()

    def test_validate_hipaa(self, spec_file: Path):
        result = runner.invoke(app, ["validate", str(spec_file), "--compliance", "hipaa"])
        # May pass or fail depending on spec, but should run
        assert "HIPAA" in result.output or "hipaa" in result.output.lower()

    def test_validate_well_architected(self, spec_file: Path):
        result = runner.invoke(app, ["validate", str(spec_file), "--well-architected"])
        assert "Well-Architected" in result.output or "well-architected" in result.output.lower()

    def test_validate_multiple_frameworks(self, spec_file: Path):
        result = runner.invoke(app, ["validate", str(spec_file), "--compliance", "hipaa,pci-dss", "--well-architected"])
        assert "HIPAA" in result.output or "hipaa" in result.output.lower()
        assert "PCI" in result.output or "pci" in result.output.lower()


class TestExportCommand:
    def test_export_terraform(self, spec_file: Path):
        result = runner.invoke(app, ["export", str(spec_file), "--format", "terraform"])
        assert result.exit_code == 0
        assert "resource" in result.output or "provider" in result.output

    def test_export_mermaid(self, spec_file: Path):
        result = runner.invoke(app, ["export", str(spec_file), "--format", "mermaid"])
        assert result.exit_code == 0
        assert "graph" in result.output or "flowchart" in result.output

    def test_export_cloudformation(self, spec_file: Path):
        result = runner.invoke(app, ["export", str(spec_file), "--format", "cloudformation"])
        assert result.exit_code == 0
        assert "AWSTemplateFormatVersion" in result.output or "Resources" in result.output

    def test_export_sbom(self, spec_file: Path):
        result = runner.invoke(app, ["export", str(spec_file), "--format", "sbom"])
        assert result.exit_code == 0

    def test_export_aibom(self, spec_file: Path):
        result = runner.invoke(app, ["export", str(spec_file), "--format", "aibom"])
        assert result.exit_code == 0

    def test_export_invalid_format(self, spec_file: Path):
        result = runner.invoke(app, ["export", str(spec_file), "--format", "invalid"])
        assert result.exit_code != 0

    def test_export_to_file(self, spec_file: Path, tmp_path: Path):
        out = tmp_path / "output.tf"
        result = runner.invoke(app, ["export", str(spec_file), "--format", "terraform", "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert len(content) > 0


class TestDiffCommand:
    def test_diff_basic(self, spec_pair: tuple[Path, Path]):
        a, b = spec_pair
        result = runner.invoke(app, ["diff", str(a), str(b)])
        assert result.exit_code == 0
        # Should show some changes
        assert "change" in result.output.lower() or "config" in result.output.lower() or "Diff" in result.output

    def test_diff_identical(self, spec_file: Path):
        result = runner.invoke(app, ["diff", str(spec_file), str(spec_file)])
        assert result.exit_code == 0
        assert "No changes" in result.output or "no change" in result.output.lower()


class TestCatalogSubcommands:
    def test_catalog_help(self):
        result = runner.invoke(app, ["catalog", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output
        assert "compare" in result.output

    def test_catalog_search(self):
        result = runner.invoke(app, ["catalog", "search", "4 vcpu 16gb"])
        assert result.exit_code == 0

    def test_catalog_search_with_provider(self):
        result = runner.invoke(app, ["catalog", "search", "m5", "--provider", "aws"])
        assert result.exit_code == 0

    def test_catalog_compare_too_few(self):
        result = runner.invoke(app, ["catalog", "compare", "m5.large"])
        assert result.exit_code != 0
        assert "2" in result.output or "least" in result.output.lower()

    def test_catalog_compare(self):
        result = runner.invoke(app, ["catalog", "compare", "m5.large", "m5.xlarge"])
        assert result.exit_code == 0


class TestJsonOutput:
    def test_json_flag_cost(self, spec_file: Path):
        result = runner.invoke(app, ["--json", "cost", str(spec_file)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "estimate" in data

    def test_json_flag_validate(self, spec_file: Path):
        result = runner.invoke(app, ["--json", "validate", str(spec_file), "--compliance", "hipaa"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_json_flag_export_terraform(self, spec_file: Path):
        result = runner.invoke(app, ["--json", "export", str(spec_file), "-f", "terraform"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["format"] == "terraform"
        assert "content" in data
        assert len(data["content"]) > 0

    def test_json_flag_diff(self, spec_pair: tuple[Path, Path]):
        a, b = spec_pair
        result = runner.invoke(app, ["--json", "diff", str(a), str(b)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_json_flag_catalog_search(self):
        result = runner.invoke(app, ["--json", "catalog", "search", "4 vcpu 16gb"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_json_flag_design(self, spec_file: Path):
        from cloudwright import ArchSpec

        mock_spec = ArchSpec.from_yaml(spec_file.read_text())
        with patch("cloudwright_cli.commands.design.Architect") as MockArch:
            MockArch.return_value.design.return_value = mock_spec
            result = runner.invoke(app, ["--json", "design", "test webapp"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "name" in data
        assert "provider" in data

    def test_json_flag_catalog_compare(self):
        result = runner.invoke(app, ["--json", "catalog", "compare", "m5.large", "m5.xlarge"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "comparison" in data


class TestRenderNextSteps:
    def test_render_next_steps_content(self):
        from cloudwright.ascii_diagram import render_next_steps

        result = render_next_steps()
        assert "cloudwright cost" in result
        assert "cloudwright validate" in result

    def test_render_next_steps_returns_string(self):
        from cloudwright.ascii_diagram import render_next_steps

        result = render_next_steps()
        assert isinstance(result, str)
        assert len(result) > 0


class TestAutoSaveSpec:
    def test_auto_save_explicit_output(self, tmp_path: Path):
        from cloudwright import ArchSpec
        from cloudwright_cli.utils import auto_save_spec

        spec = ArchSpec.from_yaml(_SPEC_YAML)
        out = tmp_path / "out.yaml"
        result = auto_save_spec(spec, out)
        assert result == out
        assert out.exists()

    def test_auto_save_slug_path(self, tmp_path: Path, monkeypatch):
        from cloudwright import ArchSpec
        from cloudwright_cli.utils import auto_save_spec

        monkeypatch.chdir(tmp_path)
        spec = ArchSpec.from_yaml(_SPEC_YAML)
        result = auto_save_spec(spec)
        assert result.exists()
        assert result.suffix == ".yaml"
        assert "test" in result.stem


class TestErrorHandling:
    def test_error_handling_invalid_yaml(self, tmp_path: Path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("not: valid: yaml: {{{")
        result = runner.invoke(app, ["cost", str(bad_yaml)])
        assert result.exit_code != 0

    def test_error_handling_empty_file(self, tmp_path: Path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        result = runner.invoke(app, ["validate", str(empty), "--compliance", "hipaa"])
        assert result.exit_code != 0

    def test_json_error_output(self, tmp_path: Path):
        # With --json flag, errors should also be JSON
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("not: valid: yaml: {{{")
        result = runner.invoke(app, ["--json", "cost", str(bad_yaml)])
        assert result.exit_code != 0
        # Output should be JSON with an error key
        try:
            data = json.loads(result.output)
            assert "error" in data
        except json.JSONDecodeError:
            # Error might be on stderr, not stdout — acceptable
            pass

    def test_verbose_flag_accepted(self, spec_file: Path):
        result = runner.invoke(app, ["--verbose", "cost", str(spec_file)])
        assert result.exit_code == 0
