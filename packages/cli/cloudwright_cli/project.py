"""Project directory support — finds and loads .cloudwright/ configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_USER_CONFIG_PATH = Path.home() / ".cloudwright" / "config.yaml"

_DEFAULTS: dict[str, Any] = {
    "llm_provider": None,
    "default_provider": "aws",
    "default_region": "us-east-1",
    "compliance": [],
    "model_overrides": {},
}


def load_merged_config() -> dict[str, Any]:
    """Load config with precedence: project > user > defaults."""
    config = dict(_DEFAULTS)

    # Layer 1: user config (~/.cloudwright/config.yaml)
    if _USER_CONFIG_PATH.exists():
        user_cfg = yaml.safe_load(_USER_CONFIG_PATH.read_text()) or {}
        config.update({k: v for k, v in user_cfg.items() if v is not None})

    # Layer 2: project config (.cloudwright/config.yaml overrides user)
    root = find_project_root()
    if root:
        project_cfg = load_project_config(root)
        config.update({k: v for k, v in project_cfg.items() if v is not None})

    return config


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default: cwd) looking for .cloudwright/ directory."""
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".cloudwright").is_dir():
            return parent
    return None


def load_project_config(project_root: Path) -> dict[str, Any]:
    """Load .cloudwright/config.yaml if it exists."""
    config_path = project_root / ".cloudwright" / "config.yaml"
    if config_path.exists():
        return yaml.safe_load(config_path.read_text()) or {}
    return {}


def get_project_spec_path(project_root: Path) -> Path | None:
    """Return the path to .cloudwright/spec.yaml if it exists."""
    spec_path = project_root / ".cloudwright" / "spec.yaml"
    if spec_path.exists():
        return spec_path
    return None


def resolve_spec_path(spec_file: str | None) -> Path:
    """Resolve a spec file path — if None, try project directory."""
    if spec_file:
        return Path(spec_file)

    root = find_project_root()
    if root:
        spec_path = get_project_spec_path(root)
        if spec_path:
            return spec_path

    raise FileNotFoundError(
        "No spec file specified and no .cloudwright/spec.yaml found. "
        "Pass a spec file or run 'cloudwright init --project' to create a project."
    )
