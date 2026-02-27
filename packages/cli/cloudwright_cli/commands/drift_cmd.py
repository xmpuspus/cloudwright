"""Drift detection — compare design spec against deployed infrastructure."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from cloudwright_cli.utils import handle_error

console = Console()


def drift(
    ctx: typer.Context,
    spec_file: Annotated[str, typer.Argument(help="Path to the design ArchSpec YAML")],
    infra_file: Annotated[str, typer.Argument(help="Path to Terraform .tfstate or CloudFormation template")],
    fmt: Annotated[
        str, typer.Option("--format", "-f", help="Infrastructure format: auto, terraform, cloudformation")
    ] = "auto",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Compare design spec against deployed infrastructure to detect drift."""
    try:
        from cloudwright.drift import detect_drift

        if not Path(spec_file).exists():
            console.print(f"[red]Error:[/red] Design spec not found: {spec_file}")
            raise typer.Exit(1)
        if not Path(infra_file).exists():
            console.print(f"[red]Error:[/red] Infrastructure file not found: {infra_file}")
            raise typer.Exit(1)

        with console.status("Detecting drift..."):
            report = detect_drift(spec_file, infra_file, infra_format=fmt)

        if json_output:
            import json

            result = {
                "drift_score": report.drift_score,
                "drifted_components": report.drifted_components,
                "extra_components": report.extra_components,
                "missing_components": report.missing_components,
                "diff": report.diff.model_dump(),
                "summary": report.summary,
            }
            console.print_json(json.dumps(result, default=str))
            return

        score_color = "green" if report.drift_score == 0 else "yellow" if report.drift_score < 0.3 else "red"

        console.print(Rule("[bold]Cloudwright Drift Detection[/bold]"))
        console.print(
            Panel(
                f"[{score_color}]Drift Score: {report.drift_score:.0%}[/{score_color}]\n[dim]{report.summary}[/dim]",
                title=f"[dim]{Path(spec_file).name}[/dim] vs [dim]{Path(infra_file).name}[/dim]",
            )
        )

        if report.drift_score == 0:
            return

        if report.missing_components:
            console.print(f"\n[bold red]Missing from deployment ({len(report.missing_components)})[/bold red]")
            for cid in report.missing_components:
                console.print(f"  [red]-[/red] {cid}")

        if report.extra_components:
            console.print(f"\n[bold yellow]Extra in deployment ({len(report.extra_components)})[/bold yellow]")
            for cid in report.extra_components:
                console.print(f"  [yellow]+[/yellow] {cid}")

        if report.drifted_components:
            table = Table(title=f"Configuration Drift ({len(report.drifted_components)} components)")
            table.add_column("Component", style="cyan")
            table.add_column("Field")
            table.add_column("Design", style="green")
            table.add_column("Deployed", style="red")
            for change in report.diff.changed:
                table.add_row(change.component_id, change.field, change.old_value, change.new_value)
            console.print()
            console.print(table)

        if report.diff.compliance_impact:
            console.print("\n[bold red]Compliance Impact[/bold red]")
            for impact in report.diff.compliance_impact:
                console.print(f"  [red]![/red] {impact}")

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)
