"""Tests for the drift CLI command."""

from __future__ import annotations

from pathlib import Path

from cloudwright_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_drift_missing_spec(tmp_path: Path):
    result = runner.invoke(app, ["drift", str(tmp_path / "nonexistent.yaml"), str(tmp_path / "state.tfstate")])
    assert result.exit_code != 0


def test_drift_missing_infra(tmp_path: Path):
    spec = tmp_path / "spec.yaml"
    spec.write_text("name: test\n")
    result = runner.invoke(app, ["drift", str(spec), str(tmp_path / "nonexistent.tfstate")])
    assert result.exit_code != 0


def test_drift_help():
    result = runner.invoke(app, ["drift", "--help"])
    assert result.exit_code == 0
    assert "drift" in result.output.lower() or "infrastructure" in result.output.lower()
