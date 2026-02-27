"""Tests for the modify CLI command."""

from __future__ import annotations

from pathlib import Path

from cloudwright_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_modify_missing_spec(tmp_path: Path):
    result = runner.invoke(app, ["modify", str(tmp_path / "nonexistent.yaml"), "add cache"])
    assert result.exit_code != 0


def test_modify_help():
    result = runner.invoke(app, ["modify", "--help"])
    assert result.exit_code == 0
    assert "modify" in result.output.lower() or "instruction" in result.output.lower()
