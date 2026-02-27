from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.syntax import Syntax
from silmaril import ArchSpec
from silmaril.exporter import FORMATS

console = Console()

_SYNTAX_MAP = {
    "terraform": "hcl",
    "cloudformation": "yaml",
    "mermaid": "text",
    "sbom": "json",
    "aibom": "json",
}


def export(
    spec_file: Annotated[Path, typer.Argument(help="Path to spec YAML file", exists=True)],
    format: Annotated[str, typer.Option("--format", "-f", help=f"Export format: {', '.join(FORMATS)}")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file or directory")] = None,
) -> None:
    """Export an architecture spec to Terraform, CloudFormation, Mermaid, SBOM, or AIBOM."""
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

    with console.status(f"Exporting as {fmt}..."):
        content = spec.export(fmt, output=output_str, output_dir=output_dir_str)

    if output:
        if output_dir_str:
            console.print(f"[green]Written to {output_dir_str}/main.tf[/green]")
        else:
            console.print(f"[green]Written to {output}[/green]")
    else:
        lang = _SYNTAX_MAP.get(fmt, "text")
        console.print(Syntax(content, lang, theme="monokai", word_wrap=True))
