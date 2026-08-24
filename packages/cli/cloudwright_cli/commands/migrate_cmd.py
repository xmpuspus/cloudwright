"""Read-only migration planning and evidence commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from cloudwright.migration import (
    EvidenceEvaluator,
    EvidenceInput,
    MigrationAssessment,
    MigrationPlanner,
    MigrationProject,
)
from cloudwright.migration.demo import run_demo
from cloudwright.migration.packs import list_packs
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cloudwright_cli.output import confirm_overwrite, emit_success, is_json_mode, validate_output_path
from cloudwright_cli.utils import handle_error

migrate_app = typer.Typer(
    help="Plan migrations and check cutover evidence without changing systems.",
    no_args_is_help=True,
)
console = Console()


def _write_yaml(ctx: typer.Context, model, output: Path | None) -> None:
    if output is None:
        return
    path = validate_output_path(output)
    if not confirm_overwrite(path, ctx=ctx):
        raise ValueError(f"output file already exists: {path}")
    path.write_text(model.to_yaml())


def _render_assessment(assessment: MigrationAssessment) -> None:
    transition = assessment.transition
    state = "Complete" if transition.complete else "Needs mappings"
    console.print(
        Panel(
            f"{len(transition.waves)} waves | {len(assessment.assurance.criteria)} gates | {state}",
            title=assessment.project_name,
            border_style="green" if transition.complete else "yellow",
        )
    )
    waves = Table(title="Migration waves")
    waves.add_column("Wave")
    waves.add_column("Actions")
    waves.add_column("Prerequisites")
    waves.add_column("Gates")
    for wave in transition.waves:
        waves.add_row(
            wave.name,
            ", ".join(action.source_name for action in wave.actions),
            ", ".join(wave.prerequisites) or "None",
            str(len(wave.gate_ids)),
        )
    console.print(waves)

    economics = transition.economics
    savings = max(0.0, -economics.monthly_delta)
    costs = Table(title="Migration economics")
    costs.add_column("Measure")
    costs.add_column("Amount", justify="right")
    for label, value in (
        ("Current monthly cost", economics.current_monthly_cost),
        ("Target monthly cost", economics.target_monthly_cost),
        ("Monthly savings", savings),
        ("Net migration cost", economics.net_migration_cost),
    ):
        costs.add_row(label, f"{economics.currency} {value:,.2f}")
    if economics.payback_months is not None:
        costs.add_row("Payback", f"{economics.payback_months:,.2f} months")
    console.print(costs)


def _render_evidence(evidence_pack) -> None:
    title = "Ready to close" if evidence_pack.closed else "Blocked"
    color = "green" if evidence_pack.closed else "red"
    console.print(
        Panel(
            (
                f"{evidence_pack.passed} passed | {evidence_pack.failed} failed | "
                f"{evidence_pack.missing} missing | {evidence_pack.blocking_failures} blocking"
            ),
            title=title,
            border_style=color,
        )
    )
    exceptions = [result for result in evidence_pack.results if not result.passed]
    if exceptions:
        table = Table(title="Evidence exceptions")
        table.add_column("Gate")
        table.add_column("Status")
        table.add_column("Detail")
        for result in exceptions:
            table.add_row(result.criterion_id, "Blocking" if result.blocking else "Advisory", result.detail)
        console.print(table)


@migrate_app.command("packs")
def packs(ctx: typer.Context) -> None:
    """List installed migration domain packs."""
    try:
        summaries = list_packs()
        if is_json_mode(ctx):
            emit_success(ctx, {"packs": [summary.as_dict() for summary in summaries]})
            return
        table = Table(title="Migration domain packs")
        table.add_column("Name")
        table.add_column("Title")
        table.add_column("Version")
        table.add_column("Jurisdiction")
        for summary in summaries:
            table.add_row(summary.name, summary.title, summary.version, summary.jurisdiction or "General")
        console.print(table)
    except typer.Exit:
        raise
    except Exception as exc:
        handle_error(ctx, exc)


@migrate_app.command("plan")
def plan_migration(
    ctx: typer.Context,
    project_file: Annotated[Path, typer.Argument(help="Migration project YAML or JSON file")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write assessment YAML")] = None,
    pack: Annotated[str | None, typer.Option("--pack", help="Override the project's domain pack")] = None,
) -> None:
    """Build dependency-ordered waves, economics, and acceptance gates."""
    try:
        project = MigrationProject.from_file(project_file)
        assessment = MigrationPlanner().plan(project, pack_name=pack)
        _write_yaml(ctx, assessment, output)
        if is_json_mode(ctx):
            emit_success(ctx, {"assessment": assessment.as_dict()})
            return
        _render_assessment(assessment)
        if output:
            console.print(f"Assessment written to {output}")
    except typer.Exit:
        raise
    except Exception as exc:
        handle_error(ctx, exc)


@migrate_app.command("verify")
def verify_migration(
    ctx: typer.Context,
    project_file: Annotated[Path, typer.Argument(help="Migration project YAML or JSON file")],
    evidence_file: Annotated[Path, typer.Argument(help="Evidence YAML or JSON file")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write evidence-pack YAML")] = None,
    pack: Annotated[str | None, typer.Option("--pack", help="Override the project's domain pack")] = None,
) -> None:
    """Check recorded evidence and block closure when required gates fail."""
    try:
        project = MigrationProject.from_file(project_file)
        assessment = MigrationPlanner().plan(project, pack_name=pack)
        evidence = EvidenceInput.from_file(evidence_file)
        evidence_pack = EvidenceEvaluator().evaluate(assessment, evidence)
        _write_yaml(ctx, evidence_pack, output)
        if is_json_mode(ctx):
            emit_success(ctx, {"evidence_pack": evidence_pack.as_dict()})
        else:
            _render_evidence(evidence_pack)
            if output:
                console.print(f"Evidence pack written to {output}")
        if not evidence_pack.closed:
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except Exception as exc:
        handle_error(ctx, exc)


@migrate_app.command("demo")
def migration_demo(ctx: typer.Context) -> None:
    """Run the packaged PH telco proof project entirely offline."""
    try:
        result = run_demo("ph_telco")
        if is_json_mode(ctx):
            emit_success(
                ctx,
                {
                    "assessment": result.assessment.as_dict(),
                    "evidence_pack": result.evidence_pack.as_dict(),
                },
            )
            return
        console.print(
            f"[bold]Packaged proof project:[/bold] {result.project.name} "
            f"({len(result.assessment.transition.waves)} waves)"
        )
        _render_assessment(result.assessment)
        _render_evidence(result.evidence_pack)
    except typer.Exit:
        raise
    except Exception as exc:
        handle_error(ctx, exc)
