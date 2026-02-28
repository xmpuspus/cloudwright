"""Importers — convert existing infrastructure state into ArchSpec."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec


class ImporterPlugin(ABC):
    """ABC for importer plugins. Implement can_import() and do_import()."""

    @abstractmethod
    def can_import(self, path: str) -> bool:
        """Return True if this importer can handle the given file."""
        ...

    @abstractmethod
    def do_import(self, path: str) -> ArchSpec:
        """Parse the file and return an ArchSpec."""
        ...

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Short format name (e.g., 'terraform', 'cloudformation')."""
        ...


def import_spec(path: str, fmt: str = "auto", design_spec: "ArchSpec | None" = None) -> ArchSpec:
    """Import an ArchSpec from an infrastructure state file.

    Args:
        path: Path to the state file (.tfstate, etc.).
        fmt: Format hint — 'terraform' or 'auto' (default) to detect by extension.
        design_spec: Optional design ArchSpec for ID alignment during drift detection.
    """
    p = Path(path)

    if fmt == "auto":
        fmt = _detect_format(p)

    if fmt == "terraform":
        from cloudwright.importer.terraform_state import TerraformStateImporter

        return TerraformStateImporter().do_import(path, design_spec=design_spec)

    if fmt in ("cloudformation", "cfn"):
        from cloudwright.importer.cloudformation import CloudFormationImporter

        return CloudFormationImporter().do_import(path, design_spec=design_spec)

    raise ValueError(f"Unknown import format: {fmt!r}. Supported: terraform, cloudformation")


def _detect_format(path: Path) -> str:
    if path.suffix == ".tfstate" or (path.suffix == ".json" and "tfstate" in path.name):
        return "terraform"

    if path.suffix in (".yaml", ".yml", ".json"):
        try:
            import json

            import yaml as _yaml

            text = path.read_text()
            data = json.loads(text) if path.suffix == ".json" else _yaml.safe_load(text)
            if isinstance(data, dict) and "Resources" in data and "AWSTemplateFormatVersion" in data:
                return "cloudformation"
        except Exception:
            pass

    raise ValueError(
        f"Cannot detect import format for {path.name!r}. Pass fmt='terraform' or fmt='cloudformation' explicitly."
    )
