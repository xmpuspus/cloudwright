"""Import existing infrastructure (Terraform state, CloudFormation) into an ArchSpec."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from cloudwright_cli.utils import handle_error

console = Console()


def import_infra(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Path to .tfstate or CloudFormation template")],
    fmt: Annotated[
        str | None,
        typer.Option("--format", "-f", help="Import format: terraform, cloudformation (default: auto-detect)"),
    ] = None,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Write ArchSpec YAML to this file instead of stdout"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Override the architecture name"),
    ] = None,
) -> None:
    """Import infrastructure state or templates into an ArchSpec YAML file."""
    try:
        from cloudwright.importer import import_spec

        kwargs: dict = {}
        if fmt:
            kwargs["fmt"] = fmt

        with console.status(f"Importing {Path(source).name}..."):
            spec = import_spec(source, **kwargs)

        if name:
            spec = spec.model_copy(update={"name": name})

        json_mode = ctx.obj and ctx.obj.get("json")

        if json_mode:
            print(json.dumps(json.loads(spec.to_json()), indent=2))
            return

        content = spec.to_yaml()

        if output:
            Path(output).write_text(content)
            n_comps = len(spec.components)
            n_conns = len(spec.connections)
            console.print(
                f"[green]Imported[/green] {n_comps} component(s), {n_conns} connection(s) → [bold]{output}[/bold]"
            )
        else:
            sys.stdout.write(content)

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)
