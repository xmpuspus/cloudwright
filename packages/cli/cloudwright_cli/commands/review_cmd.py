"""Review an architecture with the deterministic critics (offline)."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cloudwright_cli.output import emit_success, is_json_mode
from cloudwright_cli.utils import handle_error

console = Console()

_SEV_COLOR = {"critical": "red", "high": "red", "medium": "yellow", "low": "cyan"}


def review(
    ctx: typer.Context,
    spec_file: Annotated[str, typer.Argument(help="Path to ArchSpec YAML/JSON file")],
    compliance: Annotated[str, typer.Option("--compliance", help="Comma-separated frameworks, e.g. hipaa,soc2")] = "",
    well_architected: Annotated[
        bool, typer.Option("--well-architected", help="Include Well-Architected checks")
    ] = False,
) -> None:
    """Review an architecture: unified scorer + linter + validator findings (no LLM, free)."""
    try:
        from cloudwright import ArchSpec
        from cloudwright.critique import critique

        spec = ArchSpec.from_file(spec_file)
        frameworks = [f.strip() for f in compliance.split(",") if f.strip()] or None
        report = critique(spec, compliance=frameworks, well_architected=well_architected)

        if is_json_mode(ctx):
            emit_success(ctx, {"review": report.as_dict()})
            return

        border = "green" if not report.blocking else "red"
        console.print(
            Panel(
                f"[bold]{report.summary_line()}[/bold]",
                title=f"Architecture Review: {spec.name}",
                border_style=border,
            )
        )

        if not report.findings:
            console.print("[green]No findings. This architecture passes every critic.[/green]")
            return

        table = Table(title="Findings (severity-ranked)")
        table.add_column("Severity")
        table.add_column("Source", style="dim")
        table.add_column("Finding")
        table.add_column("Fix")
        for f in report.findings:
            color = _SEV_COLOR.get(f.severity, "white")
            table.add_row(
                f"[{color}]{f.severity}[/{color}]",
                f.source,
                f.message,
                (f.recommendation or "")[:80],
            )
        console.print(table)

        if report.blocking:
            console.print(
                f"\n[red]{len(report.blocking)} blocking finding(s).[/red] "
                "Run `cloudwright design` (repair is on by default) or fix these before deploy."
            )

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)
