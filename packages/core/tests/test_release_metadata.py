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
