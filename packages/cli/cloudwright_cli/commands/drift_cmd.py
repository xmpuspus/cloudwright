"""Drift detection — compare design spec against deployed infrastructure."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from cloudwright_cli.output import emit_success, err_console, is_json_mode
from cloudwright_cli.utils import handle_error

console = Console()


def drift(
    ctx: typer.Context,
    spec_file: Annotated[str, typer.Argument(help="Path to the design ArchSpec YAML")],
    infra_file: Annotated[str, typer.Argument(help="Path to Terraform .tfstate or CloudFormation template")],
    fmt: Annotated[
        str, typer.Option("--format", "-f", help="Infrastructure format: auto, terraform, cloudformation")
    ] = "auto",
    remediate: Annotated[
        bool,
        typer.Option(
            "--remediate",
            help="Show cost/quality delta and terraform plan preview to close drift (read-only).",
        ),
    ] = False,
    run_plan: Annotated[
        bool,
        typer.Option("--run-plan", help="With --remediate: attempt a real terraform plan (needs credentials)."),
    ] = False,
) -> None:
    """Compare design spec against deployed infrastructure to detect drift."""
    try:
        from cloudwright.drift import detect_drift

        if not Path(spec_file).exists():
            err_console.print(f"[red]Error:[/red] Design spec not found: {spec_file}")
            raise typer.Exit(1)
        if not Path(infra_file).exists():
            err_console.print(f"[red]Error:[/red] Infrastructure file not found: {infra_file}")
            raise typer.Exit(1)

        with console.status("Detecting drift..."):
            report = detect_drift(spec_file, infra_file, infra_format=fmt)

        if remediate:
            _run_remediate(ctx, report, run_plan=run_plan)
            return

        if is_json_mode(ctx):
            result = {
                "drift_score": report.drift_score,
                "drifted_components": report.drifted_components,
                "extra_components": report.extra_components,
                "missing_components": report.missing_components,
                "diff": report.diff.model_dump(),
                "summary": report.summary,
            }
            emit_success(ctx, {"drift": result})
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


def _run_remediate(ctx: typer.Context, report: Any, *, run_plan: bool) -> None:
    from cloudwright.remediation import remediate as compute_remediation

    with console.status("Computing remediation plan..."):
        result = compute_remediation(report.deployed_spec, report.design_spec, run_plan=run_plan)

    if is_json_mode(ctx):
        emit_success(ctx, {"remediation": result})
        return

    console.print(Rule("[bold]Cloudwright Remediation Preview[/bold]"))
    console.print(Panel(result["summary"], title="Summary"))

    drift_items = result["drift"]
    if drift_items:
        table = Table(title=f"Changes to close drift ({len(drift_items)})")
        table.add_column("Action", style="cyan")
        table.add_column("Component")
        table.add_column("Detail")
        for item in drift_items:
            action = item["change"]
            cid = item.get("id", "")
            detail = ""
            if action == "modify":
                detail = f"{item.get('field')}: {item.get('from')} -> {item.get('to')}"
            elif action == "add":
                detail = item.get("service", "")
            elif action == "remove":
                detail = item.get("service", "")
            color = {"add": "green", "remove": "red", "modify": "yellow"}.get(action, "white")
            table.add_row(f"[{color}]{action}[/{color}]", cid, detail)
        console.print()
        console.print(table)
    else:
        console.print("[green]No drift changes required.[/green]")

    cd = result["cost_delta"]
    sign = "+" if cd["delta"] >= 0 else ""
    console.print(
        f"\n[bold]Cost delta:[/bold] {sign}${cd['delta']:,.2f}/mo (${cd['current']:,.2f} -> ${cd['desired']:,.2f})"
    )

    qd = result["quality_delta"]
    q_sign = "+" if qd["delta"] >= 0 else ""
    q_color = "green" if qd["delta"] >= 0 else "red"
    console.print(
        f"[bold]Quality delta:[/bold] [{q_color}]{q_sign}{qd['delta']:.1f} pts[/{q_color}] "
        f"(grade {qd['current_grade']} -> {qd['desired_grade']})"
    )

    plan = result["plan"]
    plan_color = "green" if plan.get("ok") else "red"
    plan_label = "valid" if plan.get("validated") else "not validated"
    console.print(f"[bold]Plan ([/bold]{plan['tool']}[bold]):[/bold] [{plan_color}]{plan_label}[/{plan_color}]")
    for msg in plan.get("messages", []):
        console.print(f"  [dim]{msg}[/dim]")
