from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from cloudwright import ArchSpec
from cloudwright.exporter import FORMATS
from rich.console import Console
from rich.syntax import Syntax

from cloudwright_cli.output import emit_error, emit_success, is_json_mode, validate_output_path

console = Console()

_SYNTAX_MAP = {
    "terraform": "hcl",
    "pulumi-ts": "typescript",
    "pulumi-typescript": "typescript",
    "pulumi-python": "python",
    "pulumi-py": "python",
    "cloudformation": "yaml",
    "mermaid": "text",
    "d2": "text",
    "svg": "xml",
    "png": "text",
    "c4": "text",
    "sbom": "json",
    "aibom": "json",
}

# Formats that produce a multi-file project layout when --output points at a
# directory (or any extensionless path). Keep in sync with the dispatch in
# cloudwright.exporter.export_spec.
_DIRECTORY_FORMATS = {
    "terraform",
    "pulumi-ts",
    "pulumi-typescript",
    "pulumi-python",
    "pulumi-py",
}

# Primary entry filename per directory-format, used only for status messages.
_DIRECTORY_ENTRY = {
    "terraform": "main.tf",
    "pulumi-ts": "index.ts",
    "pulumi-typescript": "index.ts",
    "pulumi-python": "__main__.py",
    "pulumi-py": "__main__.py",
}


def export(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Path to spec YAML file", exists=True)],
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help=f"Export format: {', '.join(FORMATS)}. svg/png require the D2 binary (https://d2lang.com).",
        ),
    ],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file or directory")] = None,
) -> None:
    """Export an architecture spec to Terraform, Pulumi (TS/Python), CloudFormation, Mermaid, SVG, PNG, SBOM, or AIBOM."""
    fmt = format.lower().strip()
    _aliases = {"cfn", "pulumi-typescript", "pulumi-py"}
    if fmt not in FORMATS and fmt not in _aliases:
        emit_error(ctx, ValueError(f"Unknown format {fmt!r}"), action=f"Use one of: {', '.join(FORMATS)}")

    if output:
        try:
            validate_output_path(output)
        except ValueError as e:
            emit_error(ctx, e)

    spec = ArchSpec.from_file(spec_file)

    output_str = str(output) if output else None
    output_dir_str = None

    # Terraform / Pulumi with a directory target writes a project layout in the dir
    if fmt in _DIRECTORY_FORMATS and output and output.is_dir():
        output_dir_str = output_str
        output_str = None
    elif fmt in _DIRECTORY_FORMATS and output and not output.suffix:
        # Treat extensionless output as a directory path
        output_dir_str = output_str
        output_str = None

    # PNG is binary — handle separately before the text-oriented path
    if fmt == "png":
        from cloudwright.exporter.renderer import DiagramRenderer

        if not DiagramRenderer.is_available():
            emit_error(
                ctx,
                RuntimeError("D2 binary not found"),
                action="Install: curl -fsSL https://d2lang.com/install.sh | sh",
            )

        with console.status("Rendering PNG via D2..."):
            data = DiagramRenderer().render_png(spec)

        if output:
            output.write_bytes(data)
            console.print(f"[green]Written to {output}[/green]")
        else:
            console.print(f"[green]PNG rendered: {len(data)} bytes (use --output to save)[/green]")
        return

    # Warn when svg/c4 requested but D2 not installed — render still proceeds with fallback
    if fmt in ("svg", "c4"):
        from cloudwright.exporter.renderer import DiagramRenderer

        if not DiagramRenderer.is_available():
            console.print(
                "[yellow]Warning:[/yellow] D2 binary not found — returning D2 source text. "
                "Install: curl -fsSL https://d2lang.com/install.sh | sh"
            )

    with console.status(f"Exporting as {fmt}..."):
        content = spec.export(fmt, output=output_str, output_dir=output_dir_str)

    if is_json_mode(ctx):
        emit_success(ctx, {"format": fmt, "content": content})
        return

    if output:
        if output_dir_str:
            entry = _DIRECTORY_ENTRY.get(fmt, "main.tf")
            console.print(f"[green]Written to {output_dir_str}/{entry}[/green]")
        else:
            console.print(f"[green]Written to {output}[/green]")
    else:
        lang = _SYNTAX_MAP.get(fmt, "text")
        console.print(Syntax(content, lang, theme="monokai", word_wrap=True))
