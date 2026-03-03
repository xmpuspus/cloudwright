from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

console = Console()


def databricks_validate(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Path to architecture spec YAML file", exists=True)],
    host: Annotated[
        str | None, typer.Option("--host", envvar="DATABRICKS_HOST", help="Databricks workspace URL")
    ] = None,
    token: Annotated[
        str | None, typer.Option("--token", envvar="DATABRICKS_TOKEN", help="Databricks access token")
    ] = None,
) -> None:
    """Validate Databricks components against a live workspace."""
    from cloudwright import ArchSpec

    spec = ArchSpec.from_file(spec_file)

    dbx_components = [c for c in spec.components if c.provider == "databricks"]
    if not dbx_components:
        console.print("No Databricks components found in spec.")
        raise typer.Exit(0)

    try:
        from cloudwright.adapters.databricks import DatabricksWorkspaceAdapter

        adapter = DatabricksWorkspaceAdapter(host=host, token=token)
    except ImportError:
        console.print(
            "[red]Error:[/red] databricks-sdk not installed. Run: pip install cloudwright-ai[databricks]",
            err=True,
        )
        raise typer.Exit(1)

    with console.status(f"Validating {len(dbx_components)} Databricks component(s)..."):
        issues = adapter.validate_spec(spec)

    if not issues:
        console.print("[green]All Databricks components validated successfully.[/green]")
    else:
        severity_style = {"error": "red", "warning": "yellow", "info": "cyan"}
        for issue in issues:
            sev = issue["severity"]
            style = severity_style.get(sev, "white")
            console.print(f"  [{style}][{sev.upper()}][/{style}] {issue['component']}: {issue['message']}")

    has_errors = any(i["severity"] == "error" for i in issues)
    raise typer.Exit(1 if has_errors else 0)
