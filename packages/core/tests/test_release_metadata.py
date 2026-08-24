"""Release metadata must keep companion packages compatible with core."""

from __future__ import annotations

import tomllib
from pathlib import Path

import cloudwright


def test_companion_packages_require_this_core_release():
    repository_root = Path(__file__).parents[3]
    expected = f"cloudwright-ai>={cloudwright.__version__},<2"

    for package in ("cli", "web", "mcp"):
        metadata = tomllib.loads((repository_root / f"packages/{package}/pyproject.toml").read_text())
        assert expected in metadata["project"]["dependencies"]


def test_standalone_mcp_package_installs_the_cli_launcher():
    repository_root = Path(__file__).parents[3]
    metadata = tomllib.loads((repository_root / "packages/mcp/pyproject.toml").read_text())

    assert f"cloudwright-ai-cli>={cloudwright.__version__},<2" in metadata["project"]["dependencies"]


def test_mcp_inventory_documents_the_migration_group():
    repository_root = Path(__file__).parents[3]
    readme = (repository_root / "README.md").read_text()
    reference = (repository_root / "docs/mcp-reference.md").read_text()

    assert "24 tools in 10 groups" in readme
    assert "24 tools across 10 groups" in reference
    assert "### migration (2 tools)" in reference
