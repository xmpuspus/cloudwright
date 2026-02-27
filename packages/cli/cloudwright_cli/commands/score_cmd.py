"""Score an architecture's quality."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cloudwright_cli.utils import handle_error

console = Console()


def score(
    ctx: typer.Context,
    spec_file: Annotated[str, typer.Argument(help="Path to ArchSpec YAML/JSON file")],
    with_cost: Annotated[bool, typer.Option("--with-cost", help="Run cost analysis before scoring")] = False,
) -> None:
    """Score an architecture's quality on 5 dimensions (0-100)."""
    try:
        from cloudwright import ArchSpec
        from cloudwright.scorer import Scorer

        spec = ArchSpec.from_file(spec_file)

        if with_cost:
            from cloudwright.cost import CostEngine

            engine = CostEngine()
            spec = engine.price(spec)

        scorer = Scorer()
        result = scorer.score(spec)

        if ctx.obj and ctx.obj.get("json"):
            print(json.dumps(result.to_dict(), indent=2))
            return

        border = "green" if result.overall >= 70 else "yellow" if result.overall >= 50 else "red"
        console.print(
            Panel(
                f"[bold]Overall Score: {result.overall:.0f}/100[/bold]  Grade: [bold]{result.grade}[/bold]",
                title=f"Architecture Quality: {spec.name}",
                border_style=border,
            )
        )

        table = Table(title="Dimension Breakdown")
        table.add_column("Dimension", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Weight", justify="right")
        table.add_column("Weighted", justify="right")
        table.add_column("Details")

        for d in result.dimensions:
            weighted = d.score * d.weight
            color = "green" if d.score >= 70 else "yellow" if d.score >= 50 else "red"
            table.add_row(
                d.name,
                f"[{color}]{d.score:.0f}[/{color}]",
                f"{d.weight:.0%}",
                f"{weighted:.1f}",
                "; ".join(d.details[:2]) if d.details else "",
            )

        console.print(table)

        if result.recommendations:
            console.print("\n[bold]Top Recommendations:[/bold]")
            for i, rec in enumerate(result.recommendations, 1):
                console.print(f"  {i}. {rec}")

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)
