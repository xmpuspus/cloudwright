from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from cloudwright import ArchSpec
from cloudwright.exporter import FORMATS
from rich.console import Console
from rich.syntax import Syntax

console = Console()

_SYNTAX_MAP = {
    "terraform": "hcl",
    "cloudformation": "yaml",
    "mermaid": "text",
    "d2": "text",
    "svg": "xml",
    "png": "text",
    "c4": "text",
    "sbom": "json",
    "aibom": "json",
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
    """Export an architecture spec to Terraform, CloudFormation, Mermaid, SVG, PNG, SBOM, or AIBOM."""
    fmt = format.lower().strip()
    if fmt not in FORMATS and fmt != "cfn":
        console.print(f"[red]Error:[/red] Unknown format {fmt!r}. Supported: {', '.join(FORMATS)}")
        raise typer.Exit(1)

    spec = ArchSpec.from_file(spec_file)

    output_str = str(output) if output else None
    output_dir_str = None

    # Terraform with a directory target writes main.tf inside the dir
    if fmt == "terraform" and output and output.is_dir():
        output_dir_str = output_str
        output_str = None
    elif fmt == "terraform" and output and not output.suffix:
        # Treat extensionless output as a directory path
        output_dir_str = output_str
        output_str = None

    # PNG is binary — handle separately before the text-oriented path
    if fmt == "png":
        from cloudwright.exporter.renderer import DiagramRenderer

        if not DiagramRenderer.is_available():
            console.print(
                "[red]Error:[/red] D2 binary not found. Install: curl -fsSL https://d2lang.com/install.sh | sh"
            )
            raise typer.Exit(1)

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

    if ctx.obj and ctx.obj.get("json"):
        import json

        print(json.dumps({"format": fmt, "content": content}, default=str))
        return

    if output:
        if output_dir_str:
            console.print(f"[green]Written to {output_dir_str}/main.tf[/green]")
        else:
            console.print(f"[green]Written to {output}[/green]")
    else:
        lang = _SYNTAX_MAP.get(fmt, "text")
        console.print(Syntax(content, lang, theme="monokai", word_wrap=True))
