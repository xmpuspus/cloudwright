"""Read-only migration planning and evidence commands."""

from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path
from typing import Annotated

import typer
import yaml
from cloudwright.migration import (
    EvidenceEvaluator,
    EvidenceInput,
    MigrationAssessment,
    MigrationPlanner,
    MigrationProject,
    validate_migration_size,
)
from cloudwright.migration.demo import run_demo
from cloudwright.migration.limits import MAX_MIGRATION_FILE_BYTES
from cloudwright.migration.packs import list_packs
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cloudwright_cli.output import (
    emit_stream,
    emit_success,
    is_json_mode,
    should_stream,
    validate_output_path,
)
from cloudwright_cli.utils import handle_error

migrate_app = typer.Typer(
    help="Plan migrations and check cutover evidence without changing systems.",
    no_args_is_help=True,
)
console = Console()


def _emit_machine(ctx: typer.Context, data: dict) -> None:
    if should_stream(ctx):
        emit_stream({"data": data})
    else:
        emit_success(ctx, data)


def _read_bounded_regular_file(path: Path, label: str) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"{label} must be a readable regular file: {exc.strerror}") from exc

    try:
        file_info = os.fstat(descriptor)
        if not stat.S_ISREG(file_info.st_mode):
            raise ValueError(f"{label} must be a regular file")
        if file_info.st_size > MAX_MIGRATION_FILE_BYTES:
            raise ValueError(f"{label} file has {file_info.st_size} bytes; max allowed is {MAX_MIGRATION_FILE_BYTES}")

        chunks: list[bytes] = []
        remaining = MAX_MIGRATION_FILE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    finally:
        os.close(descriptor)

    raw = b"".join(chunks)
    if len(raw) > MAX_MIGRATION_FILE_BYTES:
        raise ValueError(f"{label} file exceeds the {MAX_MIGRATION_FILE_BYTES}-byte limit")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} file must be UTF-8 text") from exc


def _read_mapping(path: Path, label: str) -> dict:
    data = yaml.safe_load(_read_bounded_regular_file(path, label))
    if not isinstance(data, dict):
        raise ValueError(f"{label} file must contain a mapping")
    return data


def _load_project(project_file: Path, *, pack: str | None = None) -> MigrationProject:
    project_data = _read_mapping(project_file, "migration project")
    validate_migration_size(project_data, pack=pack)
    return MigrationProject.model_validate(project_data)


def _load_verification_inputs(
    project_file: Path,
    evidence_file: Path,
    *,
    pack: str | None = None,
) -> tuple[MigrationProject, EvidenceInput]:
    project_data = _read_mapping(project_file, "migration project")
    evidence_data = _read_mapping(evidence_file, "migration evidence")
    validate_migration_size(project_data, evidence_data, pack=pack)
    return MigrationProject.model_validate(project_data), EvidenceInput.model_validate(evidence_data)


def _confirm_output_overwrite(path: Path, directory_descriptor: int, ctx: typer.Context) -> bool:
    try:
        os.stat(path.name, dir_fd=directory_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return True
    if is_json_mode(ctx):
        return False
    return typer.confirm(f"File {path} already exists. Overwrite?", default=False)


def _write_yaml(ctx: typer.Context, model, output: Path | None) -> None:
    if output is None:
        return
    path = validate_output_path(output)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_descriptor = os.open(path.parent, directory_flags)
    except OSError as exc:
        raise ValueError(f"output directory cannot be opened safely: {exc.strerror}") from exc

    temporary_name: str | None = None
    temporary_descriptor: int | None = None
    try:
        if not stat.S_ISDIR(os.fstat(directory_descriptor).st_mode):
            raise ValueError("output parent must be a directory")
        if not _confirm_output_overwrite(path, directory_descriptor, ctx):
            raise ValueError(f"output file already exists: {path}")

        create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        for _ in range(10):
            candidate = f".{path.name}.{secrets.token_hex(8)}.tmp"
            try:
                temporary_descriptor = os.open(candidate, create_flags, 0o600, dir_fd=directory_descriptor)
                temporary_name = candidate
                break
            except FileExistsError:
                continue
        if temporary_descriptor is None or temporary_name is None:
            raise ValueError("could not allocate a temporary output file")

        temporary_file = os.fdopen(temporary_descriptor, "w", encoding="utf-8")
        temporary_descriptor = None
        with temporary_file:
            temporary_file.write(model.to_yaml())
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=directory_descriptor,
            dst_dir_fd=directory_descriptor,
        )
        temporary_name = None
    finally:
        if temporary_descriptor is not None:
            os.close(temporary_descriptor)
        if temporary_name is not None:
            try:
                os.unlink(temporary_name, dir_fd=directory_descriptor)
            except FileNotFoundError:
                pass
        try:
            os.close(directory_descriptor)
        except OSError:
            pass


def _render_assessment(assessment: MigrationAssessment) -> None:
    transition = assessment.transition
    state = "Complete" if transition.complete else "Incomplete"
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
            _emit_machine(ctx, {"packs": [summary.as_dict() for summary in summaries]})
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
        project = _load_project(project_file, pack=pack)
        assessment = MigrationPlanner().plan(project, pack_name=pack)
        _write_yaml(ctx, assessment, output)
        if is_json_mode(ctx):
            _emit_machine(ctx, {"assessment": assessment.as_dict()})
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
        project, evidence = _load_verification_inputs(project_file, evidence_file, pack=pack)
        assessment = MigrationPlanner().plan(project, pack_name=pack)
        evidence_pack = EvidenceEvaluator().evaluate(assessment, evidence)
        _write_yaml(ctx, evidence_pack, output)
        if is_json_mode(ctx):
            _emit_machine(ctx, {"evidence_pack": evidence_pack.as_dict()})
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
            _emit_machine(
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
