"""Export ArchSpec to various formats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

FORMATS = ("terraform", "cloudformation", "mermaid", "sbom", "aibom", "compliance")


class ExporterPlugin(ABC):
    """Base class for exporter plugins discovered via entry points."""

    @abstractmethod
    def render(self, spec: "ArchSpec") -> str: ...

    @property
    @abstractmethod
    def format_name(self) -> str: ...


def _get_all_formats() -> dict[str, object]:
    """Return all known formats (built-in + plugins)."""
    formats = {f: None for f in FORMATS}
    try:
        from cloudwright.plugins import discover_exporters

        for name, plugin_cls in discover_exporters().items():
            formats[name] = plugin_cls
    except ImportError:
        pass
    return formats


def export_spec(spec: ArchSpec, fmt: str, output: str | None = None, output_dir: str | None = None) -> str:
    """Export an ArchSpec to the given format. Returns the rendered string."""
    fmt = fmt.lower().strip()

    if fmt == "terraform":
        from cloudwright.exporter.terraform import render

        content = render(spec)
        if output_dir:
            _write_dir(output_dir, {"main.tf": content})
        elif output:
            Path(output).write_text(content)
        return content

    if fmt in ("cloudformation", "cfn"):
        from cloudwright.exporter.cloudformation import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt == "mermaid":
        from cloudwright.exporter.mermaid import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt == "sbom":
        from cloudwright.exporter.sbom import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt == "aibom":
        from cloudwright.exporter.aibom import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt == "compliance":
        raise ValueError(
            "compliance format requires a ValidationResult — use compliance_report.render(spec, validation) directly"
        )

    raise ValueError(f"Unknown export format: {fmt!r}. Supported: {', '.join(FORMATS)}")


def _write_dir(dir_path: str, files: dict[str, str]) -> None:
    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (d / name).write_text(content)
