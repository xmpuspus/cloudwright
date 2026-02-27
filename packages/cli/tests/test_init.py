"""Tests for the init command."""

from __future__ import annotations

from pathlib import Path

import yaml
from cloudwright_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


class TestInitGcpTemplate:
    def test_init_gcp_template(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(app, ["init", "--template", "gcp_three_tier_web", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = yaml.safe_load(out.read_text())
        assert data["provider"] == "gcp"
        assert data["region"] == "us-central1"
        assert len(data["components"]) > 0
        # All components should carry gcp provider
        for comp in data["components"]:
            assert comp["provider"] == "gcp"

    def test_init_gcp_serverless(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(app, ["init", "--template", "gcp_serverless_api", "--output", str(out)])
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert data["provider"] == "gcp"
        assert any(c["service"] == "cloud_functions" for c in data["components"])

    def test_init_gcp_microservices(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(app, ["init", "--template", "gcp_microservices", "--output", str(out)])
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert data["provider"] == "gcp"
        assert any(c["service"] == "gke" for c in data["components"])


class TestInitAzureTemplate:
    def test_init_azure_template(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(app, ["init", "--template", "azure_three_tier_web", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = yaml.safe_load(out.read_text())
        assert data["provider"] == "azure"
        assert data["region"] == "eastus"
        assert len(data["components"]) > 0
        for comp in data["components"]:
            assert comp["provider"] == "azure"

    def test_init_azure_serverless(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(app, ["init", "--template", "azure_serverless_api", "--output", str(out)])
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert data["provider"] == "azure"
        assert any(c["service"] == "azure_functions" for c in data["components"])

    def test_init_azure_microservices(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(app, ["init", "--template", "azure_microservices", "--output", str(out)])
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert data["provider"] == "azure"
        assert any(c["service"] == "aks" for c in data["components"])


class TestInitWithCompliance:
    def test_init_with_compliance_single(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(
            app,
            ["init", "--template", "gcp_three_tier_web", "--output", str(out), "--compliance", "hipaa"],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert "constraints" in data
        assert data["constraints"]["compliance"] == ["hipaa"]

    def test_init_with_compliance_multiple(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(
            app,
            ["init", "--template", "azure_three_tier_web", "--output", str(out), "--compliance", "hipaa,pci-dss,soc2"],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert data["constraints"]["compliance"] == ["hipaa", "pci-dss", "soc2"]

    def test_init_compliance_preserves_existing_constraints(self, tmp_path: Path):
        # gcp_three_tier_web has availability: 99.9 constraint
        out = tmp_path / "spec.yaml"
        result = runner.invoke(
            app,
            ["init", "--template", "gcp_three_tier_web", "--output", str(out), "--compliance", "gdpr"],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert data["constraints"]["availability"] == 99.9
        assert data["constraints"]["compliance"] == ["gdpr"]


class TestInitWithBudget:
    def test_init_with_budget(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(
            app,
            ["init", "--template", "gcp_serverless_api", "--output", str(out), "--budget", "500"],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert "constraints" in data
        assert data["constraints"]["budget_monthly"] == 500.0

    def test_init_with_budget_and_compliance(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(
            app,
            [
                "init",
                "--template",
                "azure_serverless_api",
                "--output",
                str(out),
                "--budget",
                "1000",
                "--compliance",
                "fedramp",
            ],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert data["constraints"]["budget_monthly"] == 1000.0
        assert data["constraints"]["compliance"] == ["fedramp"]


class TestInitProjectDir:
    def test_init_project_dir_creates_cloudwright_dir(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init", "--template", "gcp_three_tier_web", "--project"])
        assert result.exit_code == 0, result.output
        proj_dir = tmp_path / ".cloudwright"
        assert proj_dir.exists()
        assert (proj_dir / "spec.yaml").exists()
        assert (proj_dir / "config.yaml").exists()

    def test_init_project_dir_config_contents(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init", "--template", "azure_three_tier_web", "--project"])
        assert result.exit_code == 0, result.output
        config = yaml.safe_load((tmp_path / ".cloudwright" / "config.yaml").read_text())
        assert config["version"] == 1
        assert config["default_provider"] == "azure"
        assert config["default_region"] == "eastus"

    def test_init_project_dir_with_compliance_and_budget(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["init", "--template", "gcp_microservices", "--project", "--compliance", "hipaa", "--budget", "2000"],
        )
        assert result.exit_code == 0, result.output
        config = yaml.safe_load((tmp_path / ".cloudwright" / "config.yaml").read_text())
        assert config["compliance"] == ["hipaa"]
        assert config["budget_monthly"] == 2000.0
        spec = yaml.safe_load((tmp_path / ".cloudwright" / "spec.yaml").read_text())
        assert spec["constraints"]["compliance"] == ["hipaa"]
        assert spec["constraints"]["budget_monthly"] == 2000.0

    def test_init_project_dir_idempotent(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Running twice should not fail
        runner.invoke(app, ["init", "--template", "gcp_three_tier_web", "--project"])
        result = runner.invoke(app, ["init", "--template", "azure_three_tier_web", "--project"])
        assert result.exit_code == 0, result.output


class TestListTemplatesShowsAllProviders:
    def test_list_templates_shows_all_providers(self):
        result = runner.invoke(app, ["init", "--list"])
        assert result.exit_code == 0, result.output
        assert "aws" in result.output
        assert "gcp" in result.output
        assert "azure" in result.output

    def test_list_templates_shows_gcp_entries(self):
        result = runner.invoke(app, ["init", "--list"])
        assert result.exit_code == 0
        # Rich may truncate long keys with ellipsis, so check stable prefixes
        assert "gcp_three_tier" in result.output
        assert "gcp_serverless" in result.output
        assert "gcp_microservi" in result.output

    def test_list_templates_shows_azure_entries(self):
        result = runner.invoke(app, ["init", "--list"])
        assert result.exit_code == 0
        # Rich may truncate long keys with ellipsis, so check stable prefixes
        assert "azure_three_ti" in result.output
        assert "azure_serverle" in result.output
        assert "azure_microser" in result.output

    def test_list_templates_shows_complexity(self):
        result = runner.invoke(app, ["init", "--list"])
        assert result.exit_code == 0
        assert "medium" in result.output
        assert "low" in result.output
        assert "high" in result.output


class TestInitErrorCases:
    def test_init_unknown_template(self):
        result = runner.invoke(app, ["init", "--template", "nonexistent_template"])
        assert result.exit_code != 0
        assert "nonexistent_template" in result.output or "Unknown" in result.output

    def test_init_no_template_no_list(self):
        result = runner.invoke(app, ["init"])
        assert result.exit_code != 0

    def test_init_aws_template_still_works(self, tmp_path: Path):
        out = tmp_path / "spec.yaml"
        result = runner.invoke(app, ["init", "--template", "three_tier_web", "--output", str(out)])
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        assert data["provider"] == "aws"
