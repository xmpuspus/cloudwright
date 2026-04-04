"""Export ArchSpec to various formats."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

FORMATS = (
    "terraform",
    "cloudformation",
    "mermaid",
    "d2",
    "ascii",
    "svg",
    "png",
    "c4",
    "sbom",
    "aibom",
    "compliance",
    "html",
)


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


_DANGEROUS_PATTERNS = re.compile(r"[;|&`]|\$\(|\$\{|%\{")


def validate_export_config(config: dict, path: str = "") -> None:
    """Validate component config values are safe for IaC export.

    Raises ValueError on dangerous content (shell metacharacters, HCL injection).
    """
    for key, value in config.items():
        field_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            validate_export_config(value, field_path)
        elif isinstance(value, str):
            if _DANGEROUS_PATTERNS.search(value):
                raise ValueError(
                    f"Config field {field_path!r} contains dangerous characters: {value!r}. "
                    "Values must not contain shell metacharacters (;|&`$()${})."
                )
        elif isinstance(value, bool):
            pass  # booleans are safe
        elif isinstance(value, (int, float)):
            pass  # numbers are safe
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    validate_export_config(item, f"{field_path}[{i}]")
                elif isinstance(item, str) and _DANGEROUS_PATTERNS.search(item):
                    raise ValueError(f"Config field {field_path}[{i}] contains dangerous characters: {item!r}.")
                elif isinstance(item, list):
                    validate_export_config({"_": item}, f"{field_path}[{i}]")
                elif not isinstance(item, (bool, int, float, str, type(None))):
                    raise ValueError(f"Config field {field_path}[{i}] has unsupported type: {type(item).__name__}.")


def export_spec(spec: ArchSpec, fmt: str, output: str | None = None, output_dir: str | None = None) -> str:
    """Export an ArchSpec to the given format. Returns the rendered string."""
    fmt = fmt.lower().strip()

    # Validate all component configs before exporting (prevents injection in any format)
    for comp in spec.components:
        validate_export_config(comp.config, path=f"component[{comp.id}].config")

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

    if fmt == "d2":
        from cloudwright.exporter.d2 import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt in ("ascii", "text"):
        from cloudwright.exporter.ascii import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt == "c4":
        from cloudwright.exporter.c4 import render

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

    if fmt == "svg":
        from cloudwright.exporter.renderer import DiagramRenderer

        content = DiagramRenderer().render_svg(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt == "png":
        from cloudwright.exporter.renderer import DiagramRenderer

        data = DiagramRenderer().render_png(spec)
        if output:
            Path(output).write_bytes(data)
        return f"<PNG binary: {len(data)} bytes>"

    if fmt == "html":
        from cloudwright.exporter.html_report import render

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
