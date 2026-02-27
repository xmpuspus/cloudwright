from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from silmaril import Architect, ArchSpec

console = Console()


def compare(
    spec_file: Annotated[Path, typer.Argument(help="Path to spec YAML file", exists=True)],
    providers: Annotated[str, typer.Option(help="Comma-separated target providers")],
) -> None:
    """Compare an architecture across multiple cloud providers."""
    target_providers = [p.strip() for p in providers.split(",") if p.strip()]
    if not target_providers:
        console.print("[red]Error:[/red] --providers requires at least one provider")
        raise typer.Exit(1)

    spec = ArchSpec.from_file(spec_file)

    with console.status("Generating alternatives..."):
        alts = Architect().compare(spec, target_providers)

    all_providers = [spec.provider] + [a.provider for a in alts]
    alt_map = {spec.provider: spec}
    for alt in alts:
        if alt.spec:
            alt_map[alt.provider] = alt.spec

    # Side-by-side service comparison
    table = Table(title=f"Provider Comparison — {spec.name}")
    table.add_column("Component", style="cyan")
    table.add_column("Original Label")
    for p in all_providers:
        table.add_column(p.upper())

    for comp in spec.components:
        row = [comp.id, comp.label]
        for p in all_providers:
            s = alt_map.get(p)
            if s:
                mapped = next((c for c in s.components if c.id == comp.id), None)
                row.append(mapped.service if mapped else "-")
            else:
                row.append("-")
        table.add_row(*row)

    console.print(table)

    # Monthly totals
    totals_table = Table(title="Monthly Cost Totals", show_header=True)
    totals_table.add_column("Provider")
    totals_table.add_column("Monthly Total", justify="right")
    totals_table.add_column("Key Differences", style="dim")

    origin_total = spec.cost_estimate.monthly_total if spec.cost_estimate else 0.0
    totals_table.add_row(
        spec.provider.upper(),
        f"${origin_total:,.2f}" if origin_total else "-",
        "(baseline)",
    )
    for alt in alts:
        diffs = ", ".join(alt.key_differences[:3]) if alt.key_differences else ""
        totals_table.add_row(
            alt.provider.upper(),
            f"${alt.monthly_total:,.2f}" if alt.monthly_total else "-",
            diffs,
        )

    console.print(totals_table)
