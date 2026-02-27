from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from cloudwright import ArchSpec
from cloudwright.cost import CostEngine
from rich.console import Console
from rich.table import Table

console = Console()


def cost(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Path to spec YAML file", exists=True)],
    compare: Annotated[str | None, typer.Option(help="Comma-separated providers to compare")] = None,
    pricing_tier: Annotated[
        str | None, typer.Option(help="Pricing tier (on_demand, reserved_1yr, reserved_3yr, spot)")
    ] = None,
) -> None:
    """Show cost breakdown for an architecture spec."""
    spec = ArchSpec.from_file(spec_file)

    # Compute cost estimate if not present
    if not spec.cost_estimate:
        engine = CostEngine()
        spec.cost_estimate = engine.estimate(spec)

    if ctx.obj and ctx.obj.get("json"):
        import json

        print(json.dumps({"estimate": spec.cost_estimate.model_dump()}, default=str))
        return

    if compare:
        providers = [p.strip() for p in compare.split(",") if p.strip()]
        _print_multi_cloud_table(spec, providers)
    else:
        _print_single_cost_table(spec)


def _print_single_cost_table(spec: ArchSpec) -> None:
    if not spec.cost_estimate:
        console.print("[yellow]No cost estimate in spec. Run 'cloudwright design' to generate one.[/yellow]")
        return

    table = Table(title=f"Cost Breakdown — {spec.name}", show_footer=True)
    table.add_column("Component", style="cyan")
    table.add_column("Service")
    table.add_column("Monthly", justify="right", footer=f"${spec.cost_estimate.monthly_total:,.2f}")
    table.add_column("Notes", style="dim")

    comp_map = {c.id: c for c in spec.components}
    for item in spec.cost_estimate.breakdown:
        comp = comp_map.get(item.component_id)
        svc_label = comp.service if comp else item.service
        table.add_row(
            item.component_id,
            svc_label,
            f"${item.monthly:,.2f}",
            item.notes,
        )

    console.print(table)


def _print_multi_cloud_table(spec: ArchSpec, providers: list[str]) -> None:
    all_providers = [spec.provider] + [p for p in providers if p != spec.provider]
    alternatives_map: dict = {spec.provider: spec}

    engine = CostEngine()
    if not spec.cost_estimate:
        spec.cost_estimate = engine.estimate(spec)
    with console.status("Computing alternatives..."):
        alts = engine.compare_providers(spec, providers)
        for alt in alts:
            if alt.spec:
                alt.spec.cost_estimate = engine.estimate(alt.spec)
                alternatives_map[alt.provider] = alt.spec

    table = Table(title=f"Multi-Cloud Comparison — {spec.name}")
    table.add_column("Component", style="cyan")

    for p in all_providers:
        table.add_column(p.upper(), justify="right")

    comp_ids = [c.id for c in spec.components]
    for cid in comp_ids:
        row = [cid]
        for p in all_providers:
            s = alternatives_map.get(p)
            if s and s.cost_estimate:
                item = next((i for i in s.cost_estimate.breakdown if i.component_id == cid), None)
                row.append(f"${item.monthly:,.2f}" if item else "-")
            else:
                row.append("-")
        table.add_row(*row)

    # Totals row
    totals = []
    for p in all_providers:
        s = alternatives_map.get(p)
        if s and s.cost_estimate:
            totals.append(f"${s.cost_estimate.monthly_total:,.2f}")
        else:
            totals.append("-")
    table.add_section()
    table.add_row("[bold]TOTAL[/bold]", *totals)

    console.print(table)
