from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from silmaril import ArchSpec, Differ

console = Console()


def diff(
    spec_a: Annotated[Path, typer.Argument(help="First spec file (baseline)", exists=True)],
    spec_b: Annotated[Path, typer.Argument(help="Second spec file (new)", exists=True)],
) -> None:
    """Show the diff between two architecture specs."""
    a = ArchSpec.from_file(spec_a)
    b = ArchSpec.from_file(spec_b)

    with console.status("Computing diff..."):
        result = Differ().diff(a, b)

    console.print(Rule(f"[bold]Diff: {spec_a.name} → {spec_b.name}[/bold]"))

    if result.summary:
        console.print(f"[dim]{result.summary}[/dim]\n")

    if not result.added and not result.removed and not result.changed:
        console.print("[green]No changes detected.[/green]")
        return

    if result.added:
        console.print("[bold green]Added Components[/bold green]")
        for comp in result.added:
            console.print(f"  [green]+[/green] {comp.id} ({comp.service}) — {comp.label}")
        console.print()

    if result.removed:
        console.print("[bold red]Removed Components[/bold red]")
        for comp in result.removed:
            console.print(f"  [red]-[/red] {comp.id} ({comp.service}) — {comp.label}")
        console.print()

    if result.changed:
        table = Table(title="Changed Components")
        table.add_column("Component", style="cyan")
        table.add_column("Field")
        table.add_column("Before", style="red")
        table.add_column("After", style="green")
        table.add_column("Cost Delta", justify="right")

        for change in result.changed:
            delta_str = _fmt_delta(change.cost_delta)
            table.add_row(
                change.component_id,
                change.field,
                change.old_value,
                change.new_value,
                delta_str,
            )
        console.print(table)

    if result.cost_delta != 0.0:
        delta_str = _fmt_delta(result.cost_delta)
        console.print(f"\nTotal cost delta: {delta_str}/month")

    if result.compliance_impact:
        console.print("\n[bold yellow]Compliance Impact[/bold yellow]")
        for item in result.compliance_impact:
            console.print(f"  [yellow]![/yellow] {item}")


def _fmt_delta(delta: float) -> str:
    if delta > 0:
        return f"[red]+${delta:,.2f}[/red]"
    if delta < 0:
        return f"[green]-${abs(delta):,.2f}[/green]"
    return "[dim]$0.00[/dim]"
