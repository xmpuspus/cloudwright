from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from cloudwright import ArchSpec
from cloudwright.cost import CostEngine
from cloudwright.policy import PolicyEngine
from rich.console import Console
from rich.table import Table

console = Console()


def policy(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Path to spec YAML file", exists=True)],
    rules: Annotated[Path, typer.Option("--rules", "-r", help="Path to policy rules YAML file", exists=True)],
) -> None:
    """Evaluate an architecture spec against policy rules."""
    try:
        spec = ArchSpec.from_file(spec_file)
        engine = PolicyEngine()

        cost_estimate = spec.cost_estimate
        if not cost_estimate:
            cost_engine = CostEngine()
            cost_estimate = cost_engine.estimate(spec)

        result = engine.evaluate_from_file(spec, rules, cost_estimate=cost_estimate)

        json_mode = ctx.obj.get("json", False) if ctx.obj else False
        if json_mode:
            print(json.dumps(result.model_dump(), default=str))
            if not result.passed:
                raise typer.Exit(1)
            return

        table = Table(title="Policy Evaluation")
        table.add_column("Status", width=6)
        table.add_column("Rule", style="cyan")
        table.add_column("Severity")
        table.add_column("Message", style="dim")

        for check in result.results:
            if check.passed:
                status = "[green]PASS[/green]"
            elif check.severity == "deny":
                status = "[red]DENY[/red]"
            elif check.severity == "warn":
                status = "[yellow]WARN[/yellow]"
            else:
                status = "[blue]INFO[/blue]"

            sev_colors = {"deny": "red", "warn": "yellow", "info": "blue"}
            color = sev_colors.get(check.severity, "")
            severity_display = f"[{color}]{check.severity.upper()}[/{color}]" if color else check.severity.upper()

            table.add_row(status, check.rule, severity_display, check.message)

        console.print(table)
        console.print()

        if result.passed:
            console.print("[green]All policies passed.[/green]")
        else:
            parts = []
            if result.deny_count:
                parts.append(f"[red]{result.deny_count} denied[/red]")
            if result.warn_count:
                parts.append(f"[yellow]{result.warn_count} warnings[/yellow]")
            console.print(f"Policy evaluation: {', '.join(parts)}")
            if result.deny_count > 0:
                raise typer.Exit(1)

    except typer.Exit:
        raise
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] File not found: {e}")
        raise typer.Exit(1)
    except Exception as e:
        verbose = ctx.obj.get("verbose", False) if ctx.obj else False
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
