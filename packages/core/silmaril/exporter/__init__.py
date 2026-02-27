"""Export ArchSpec to various formats."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from silmaril.spec import ArchSpec

FORMATS = ("terraform", "cloudformation", "mermaid", "sbom", "aibom")


def export_spec(spec: ArchSpec, fmt: str, output: str | None = None, output_dir: str | None = None) -> str:
    """Export an ArchSpec to the given format. Returns the rendered string."""
    fmt = fmt.lower().strip()

    if fmt == "terraform":
        from silmaril.exporter.terraform import render

        content = render(spec)
        if output_dir:
            _write_dir(output_dir, {"main.tf": content})
        elif output:
            Path(output).write_text(content)
        return content

    if fmt in ("cloudformation", "cfn"):
        from silmaril.exporter.cloudformation import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt == "mermaid":
        from silmaril.exporter.mermaid import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt == "sbom":
        from silmaril.exporter.sbom import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    if fmt == "aibom":
        from silmaril.exporter.aibom import render

        content = render(spec)
        if output:
            Path(output).write_text(content)
        return content

    raise ValueError(f"Unknown export format: {fmt!r}. Supported: {', '.join(FORMATS)}")


def _write_dir(dir_path: str, files: dict[str, str]) -> None:
    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (d / name).write_text(content)
