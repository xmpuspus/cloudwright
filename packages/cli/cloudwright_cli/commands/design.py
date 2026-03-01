from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from cloudwright import Architect, Constraints
from cloudwright.ascii_diagram import render_ascii, render_next_steps
from cloudwright.cost import CostEngine
from cloudwright.validator import Validator
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


def design(
    ctx: typer.Context,
    description: Annotated[str, typer.Argument(help="Natural language architecture description")],
    provider: Annotated[str, typer.Option(help="Cloud provider")] = "aws",
    region: Annotated[str, typer.Option(help="Primary region")] = "us-east-1",
    budget: Annotated[float | None, typer.Option(help="Monthly budget in USD")] = None,
    compliance: Annotated[
        list[str] | None, typer.Option(help="Compliance frameworks (hipaa, pci-dss, soc2, fedramp, gdpr)")
    ] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write YAML to file")] = None,
    yaml_output: Annotated[bool, typer.Option("--yaml")] = False,
) -> None:
    """Design a cloud architecture from a natural language description."""
    constraints = Constraints(
        regions=[region] if region else [],
        budget_monthly=budget,
        compliance=compliance or [],
    )

    try:
        architect = Architect()
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    with console.status("Designing architecture..."):
        spec = architect.design(description, constraints=constraints)
        # Set provider/region from CLI args if not overridden by LLM
        if spec.provider == "aws" and provider != "aws":
            spec = spec.model_copy(update={"provider": provider})
        if spec.region == "us-east-1" and region != "us-east-1":
            spec = spec.model_copy(update={"region": region})

    if ctx.obj and ctx.obj.get("json"):
        import json

        print(json.dumps(spec.model_dump(), default=str))
        return

    yaml_str = spec.to_yaml()

    if yaml_output:
        console.print(
            Panel(
                Syntax(yaml_str, "yaml", theme="monokai", word_wrap=True),
                title=f"[bold cyan]{spec.name}[/bold cyan]",
                subtitle=f"{spec.provider.upper()} / {spec.region}",
            )
        )
        if spec.cost_estimate:
            _print_cost_table(spec)
        if output:
            output.write_text(yaml_str)
            console.print(f"[green]Saved to {output}[/green]")
        return

    # Default: ASCII diagram + auto-save + next steps
    console.print(render_ascii(spec))

    if not spec.cost_estimate:
        spec = spec.model_copy(update={"cost_estimate": CostEngine().estimate(spec)})
    _print_cost_table(spec)

    _print_compliance_flags(spec)

    from cloudwright_cli.utils import auto_save_spec

    save_path = auto_save_spec(spec, output)
    console.print(f"[dim]Saved: {save_path}[/dim]")
    console.print(f"[dim]{render_next_steps()}[/dim]")


def _print_compliance_flags(spec) -> None:
    results = Validator().validate(spec, well_architected=True)
    if not results:
        return
    wa = results[0]
    total = len(wa.checks)
    passed = sum(1 for c in wa.checks if c.passed)
    console.print(
        f"[dim]Well-Architected: {passed}/{total} checks passed  |  "
        "Run 'cloudwright validate --compliance hipaa' for full report[/dim]"
    )


def _print_cost_table(spec) -> None:
    table = Table(title="Cost Estimate", show_footer=True)
    table.add_column("Component", style="cyan")
    table.add_column("Service")
    table.add_column("Monthly", justify="right", footer=f"${spec.cost_estimate.monthly_total:,.2f}")
    table.add_column("Notes", style="dim")

    comp_map = {c.id: c for c in spec.components}
    for item in spec.cost_estimate.breakdown:
        service = comp_map.get(item.component_id, None)
        svc_label = service.service if service else item.service
        table.add_row(
            item.component_id,
            svc_label,
            f"${item.monthly:,.2f}",
            item.notes,
        )

    console.print(table)
