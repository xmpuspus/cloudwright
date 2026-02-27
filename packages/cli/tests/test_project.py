"""Tests for project directory support."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from cloudwright_cli.project import find_project_root, load_project_config, resolve_spec_path


def test_find_project_root_exists(tmp_path: Path):
    (tmp_path / ".cloudwright").mkdir()
    result = find_project_root(tmp_path)
    assert result == tmp_path


def test_find_project_root_not_found(tmp_path: Path):
    result = find_project_root(tmp_path)
    assert result is None


def test_find_project_root_parent(tmp_path: Path):
    (tmp_path / ".cloudwright").mkdir()
    child = tmp_path / "sub" / "deep"
    child.mkdir(parents=True)
    result = find_project_root(child)
    assert result == tmp_path


def test_load_project_config(tmp_path: Path):
    proj_dir = tmp_path / ".cloudwright"
    proj_dir.mkdir()
    config = {"version": 1, "default_provider": "gcp"}
    (proj_dir / "config.yaml").write_text(yaml.dump(config))
    result = load_project_config(tmp_path)
    assert result["default_provider"] == "gcp"


def test_load_project_config_missing(tmp_path: Path):
    result = load_project_config(tmp_path)
    assert result == {}


def test_resolve_spec_path_explicit():
    path = resolve_spec_path("my_spec.yaml")
    assert path == Path("my_spec.yaml")


def test_resolve_spec_path_not_found(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        resolve_spec_path(None)


def test_resolve_spec_path_from_project(tmp_path: Path, monkeypatch):
    proj_dir = tmp_path / ".cloudwright"
    proj_dir.mkdir()
    spec = proj_dir / "spec.yaml"
    spec.write_text("name: test")
    monkeypatch.chdir(tmp_path)
    result = resolve_spec_path(None)
    assert result == spec
