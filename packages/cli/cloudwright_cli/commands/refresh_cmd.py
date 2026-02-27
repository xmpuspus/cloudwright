"""Refresh live pricing data from cloud provider APIs into the catalog."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from cloudwright_cli.utils import handle_error

console = Console()


def refresh(
    ctx: typer.Context,
    provider: Annotated[
        str | None,
        typer.Option("--provider", "-p", help="Provider to refresh: aws, gcp, azure (default: all)"),
    ] = None,
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Filter to a category: compute or a service name"),
    ] = None,
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Override the default region for pricing lookups"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Fetch but don't write to catalog DB"),
    ] = False,
) -> None:
    """Refresh live pricing data from cloud provider APIs into the local catalog."""
    try:
        from cloudwright.catalog.refresh import refresh_catalog

        providers_label = provider or "aws, gcp, azure"
        with console.status(f"Fetching pricing for {providers_label}..."):
            summary = refresh_catalog(
                provider=provider,
                category=category,
                region=region,
                dry_run=dry_run,
            )

        json_mode = ctx.obj and ctx.obj.get("json")

        if json_mode:
            data = {
                "total_fetched": summary.total_fetched,
                "total_errors": summary.total_errors,
                "results": [
                    {
                        "provider": r.provider,
                        "category": r.category,
                        "instances_fetched": r.instances_fetched,
                        "managed_services_fetched": r.managed_services_fetched,
                        "errors": r.errors,
                        "dry_run": r.dry_run,
                    }
                    for r in summary.results
                ],
            }
            print(json.dumps(data, indent=2))
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("Provider")
        table.add_column("Category")
        table.add_column("Instances", justify="right")
        table.add_column("Managed", justify="right")
        table.add_column("Errors", justify="right")

        for r in summary.results:
            error_str = str(len(r.errors)) if r.errors else "[green]0[/green]"
            table.add_row(
                r.provider,
                r.category or "all",
                str(r.instances_fetched),
                str(r.managed_services_fetched),
                error_str,
            )

        console.print(table)

        suffix = " [dim](dry run)[/dim]" if dry_run else ""
        if summary.total_errors == 0:
            console.print(f"[green]Done.[/green] {summary.total_fetched} pricing records fetched{suffix}")
        else:
            console.print(
                f"[yellow]Done with errors.[/yellow] "
                f"{summary.total_fetched} fetched, {summary.total_errors} error(s){suffix}"
            )
            for r in summary.results:
                for err in r.errors:
                    console.print(f"  [red]{r.provider}:[/red] {err}")

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)
