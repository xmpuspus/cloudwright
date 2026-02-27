"""Lint an architecture spec for anti-patterns."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from cloudwright_cli.utils import handle_error

console = Console()


def lint(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Architecture spec YAML file", exists=True)],
    output: Annotated[str, typer.Option(help="Output format: text, json")] = "text",
    strict: Annotated[bool, typer.Option(help="Fail on warnings too")] = False,
) -> None:
    """Detect architecture anti-patterns in a spec file."""
    try:
        from cloudwright import ArchSpec
        from cloudwright.linter import lint as run_lint

        spec = ArchSpec.from_file(spec_file)
        warnings = run_lint(spec)

        if output == "json":
            result = [
                {
                    "rule": w.rule,
                    "severity": w.severity,
                    "component": w.component,
                    "message": w.message,
                    "recommendation": w.recommendation,
                }
                for w in warnings
            ]
            print(json.dumps(result, indent=2))
        else:
            if not warnings:
                console.print(f"[green][PASS][/green] No anti-patterns detected in {spec.name}")
            else:
                table = Table(title=f"Lint Results: {spec.name}", show_lines=True)
                table.add_column("Severity", width=9)
                table.add_column("Rule", style="cyan")
                table.add_column("Component")
                table.add_column("Message")
                table.add_column("Recommendation")

                for w in warnings:
                    if w.severity == "error":
                        sev = Text("error", style="bold red")
                    elif w.severity == "warning":
                        sev = Text("warning", style="yellow")
                    else:
                        sev = Text("info", style="blue")

                    table.add_row(
                        sev,
                        w.rule,
                        w.component or "—",
                        w.message,
                        w.recommendation,
                    )

                console.print(table)

                errors = [w for w in warnings if w.severity == "error"]
                warns = [w for w in warnings if w.severity == "warning"]
                console.print(
                    f"\n[bold]{len(warnings)} finding(s)[/bold]: "
                    f"[red]{len(errors)} error(s)[/red], "
                    f"[yellow]{len(warns)} warning(s)[/yellow]"
                )

        has_errors = any(w.severity == "error" for w in warnings)
        has_warnings = any(w.severity == "warning" for w in warnings)

        if has_errors or (strict and has_warnings):
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)
