from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from cloudwright_cli.output import emit_success, is_json_mode
from cloudwright_cli.utils import handle_error

console = Console()


def plan(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Path to ArchSpec YAML file", exists=True)],
    target: Annotated[
        str,
        typer.Option("--target", "-t", help="terraform | pulumi-python | pulumi-ts"),
    ] = "terraform",
    no_plan: Annotated[
        bool,
        typer.Option("--no-plan", help="Validate only; skip the credential-requiring plan/preview step"),
    ] = False,
    timeout: Annotated[int, typer.Option("--timeout", help="Seconds before the plan step is aborted")] = 180,
) -> None:
    """Prove the exported infrastructure is deployable.

    Runs `terraform validate`/`plan` or `pulumi preview` against the generated
    artifact. Read-only — nothing is applied. `validate` needs no credentials
    and is the offline proof of deployability; `plan` adds a real resource
    diff when cloud credentials are available.
    """
    try:
        from cloudwright import ArchSpec
        from cloudwright.planner import plan as run_plan

        spec = ArchSpec.from_file(spec_file)
        result = run_plan(spec, target=target, run_plan=not no_plan, timeout=timeout)

        if is_json_mode(ctx):
            emit_success(ctx, result.as_dict())
            if not result.ok:
                raise typer.Exit(1)
            return

        console.print(f"\nPlan ({result.tool}): {spec_file.name}\n")
        if not result.available:
            console.print(f"[yellow][SKIP][/yellow] {result.messages[0]}")
            raise typer.Exit(1)

        for msg in result.messages:
            console.print(f"  {msg}")
        if result.summary is not None:
            s = result.summary
            console.print(
                f"\n  Resource diff: [green]+{s['add']}[/green] "
                f"[yellow]~{s['change']}[/yellow] [red]-{s['destroy']}[/red]"
            )
        if result.output_tail:
            console.print("\n[dim]--- tool output (tail) ---[/dim]")
            console.print(f"[dim]{result.output_tail}[/dim]")

        verdict = "DEPLOYABLE" if result.ok else "NOT DEPLOYABLE"
        style = "green" if result.ok else "red"
        plan_note = "" if result.plan_ran else " (validate only — no credentials for full plan)"
        console.print(f"\nVerdict: [{style}]{verdict}[/{style}]{plan_note}")
        if not result.ok:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)
