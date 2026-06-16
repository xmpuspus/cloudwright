from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from cloudwright import ArchSpec
from cloudwright.cost import CostEngine
from rich.console import Console
from rich.table import Table

from cloudwright_cli.output import emit_success, is_json_mode

console = Console()


def cost(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Path to spec YAML file", exists=True)],
    compare: Annotated[str | None, typer.Option(help="Comma-separated providers to compare")] = None,
    pricing_tier: Annotated[
        str | None, typer.Option(help="Pricing tier (on_demand, reserved_1yr, reserved_3yr, spot)")
    ] = None,
    workload_profile: Annotated[
        str | None,
        typer.Option(
            "--workload-profile",
            "-w",
            help="Workload sizing profile (small, medium, large, enterprise). "
            "Sets realistic defaults for request volumes, storage, node counts, and data transfer.",
        ),
    ] = None,
    carbon: Annotated[
        bool,
        typer.Option("--carbon", help="Include a CO2e carbon footprint estimate."),
    ] = False,
    focus: Annotated[
        bool,
        typer.Option("--focus", help="Output cost data as FinOps FOCUS 1.0 CSV."),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Write FOCUS CSV to this file instead of stdout."),
    ] = None,
) -> None:
    """Show cost breakdown for an architecture spec."""
    if workload_profile:
        from cloudwright.cost import VALID_WORKLOAD_PROFILES

        if workload_profile not in VALID_WORKLOAD_PROFILES:
            console.print(
                f"[red]Invalid workload profile:[/red] {workload_profile!r}. "
                f"Choose from: {', '.join(sorted(VALID_WORKLOAD_PROFILES))}"
            )
            raise typer.Exit(1)

    spec = ArchSpec.from_file(spec_file)
    tier = pricing_tier or "on_demand"

    # Compute cost estimate if not present
    if not spec.cost_estimate:
        engine = CostEngine()
        spec.cost_estimate = engine.estimate(spec, pricing_tier=tier, workload_profile=workload_profile)

    # --focus: emit FOCUS CSV and exit
    if focus:
        from cloudwright.focus import to_focus_csv

        csv_text = to_focus_csv(spec.cost_estimate, pricing_tier=tier)
        if output:
            output.write_text(csv_text, encoding="utf-8")
            console.print(f"FOCUS CSV written to {output}")
        else:
            sys.stdout.write(csv_text)
        return

    if is_json_mode(ctx):
        payload: dict = {"estimate": spec.cost_estimate.model_dump(exclude_none=True)}
        if carbon:
            from cloudwright.carbon import estimate_carbon

            payload["carbon"] = estimate_carbon(spec)
        emit_success(ctx, payload)
        return

    if compare:
        providers = [p.strip() for p in compare.split(",") if p.strip()]
        _print_multi_cloud_table(spec, providers)
    else:
        _print_single_cost_table(spec)

    if carbon:
        from cloudwright.carbon import estimate_carbon

        _print_carbon_table(spec, estimate_carbon(spec))


def _print_single_cost_table(spec: ArchSpec) -> None:
    if not spec.cost_estimate:
        console.print("[yellow]No cost estimate in spec. Run 'cloudwright design' to generate one.[/yellow]")
        return

    est = spec.cost_estimate
    region_note = ""
    if est.region_multiplier != 1.0:
        region_note = f" (region multiplier: {est.region_multiplier:.2f}x vs us-east-1)"

    title = f"Cost Breakdown — {spec.name}{region_note}"
    table = Table(title=title, show_footer=True)
    table.add_column("Component", style="cyan")
    table.add_column("Service")
    table.add_column("Monthly", justify="right", footer=f"${est.monthly_total:,.2f}")
    table.add_column("Confidence", justify="center")
    table.add_column("Notes", style="dim")

    comp_map = {c.id: c for c in spec.components}
    for item in est.breakdown:
        comp = comp_map.get(item.component_id)
        svc_label = comp.service if comp else item.service
        conf_style = "green" if item.confidence == "high" else "yellow"
        table.add_row(
            item.component_id,
            svc_label,
            f"${item.monthly:,.2f}",
            f"[{conf_style}]{item.confidence}[/{conf_style}]",
            item.notes,
        )

    console.print(table)

    if est.pricing_confidence != "high":
        console.print(
            "[yellow]Pricing confidence: low[/yellow] — one or more services used formula/fallback "
            "pricing, not real catalog data. Treat totals as rough estimates."
        )


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


def _print_carbon_table(spec: ArchSpec, carbon: dict) -> None:
    table = Table(title=f"Carbon Estimate — {spec.name} ({carbon['region']})")
    table.add_column("Component", style="cyan")
    table.add_column("Service")
    table.add_column("Watts", justify="right")
    table.add_column("kWh/mo", justify="right")
    table.add_column("kgCO2e/mo", justify="right")

    for item in carbon["breakdown"]:
        table.add_row(
            item["component_id"],
            item["service"],
            f"{item['watts']:.1f}",
            f"{item['kwh_per_month']:.2f}",
            f"{item['kg_co2e_per_month']:.3f}",
        )

    console.print(table)
    console.print(
        f"[bold]Total:[/bold] {carbon['total_kg_co2e_per_month']:.3f} kgCO2e/month  "
        f"[dim](grid: {carbon['grid_intensity_g_per_kwh']} gCO2e/kWh, "
        f"PUE: {carbon['assumptions']['pue']})[/dim]"
    )
    console.print(f"[dim]{carbon['assumptions']['disclaimer']}[/dim]")
