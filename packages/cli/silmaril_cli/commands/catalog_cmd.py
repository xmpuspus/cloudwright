from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from silmaril import Catalog

console = Console()

catalog_app = typer.Typer(
    name="catalog",
    help="Search and compare cloud service catalog.",
    no_args_is_help=True,
)


@catalog_app.command("search")
def catalog_search(
    query: Annotated[str, typer.Argument(help="Natural language search query")],
    provider: Annotated[str | None, typer.Option(help="Filter by provider (aws, gcp, azure)")] = None,
    vcpus: Annotated[int | None, typer.Option(help="Minimum vCPUs")] = None,
    memory: Annotated[float | None, typer.Option(help="Minimum memory in GB")] = None,
) -> None:
    """Search the cloud service catalog."""
    filters: dict = {}
    if provider:
        filters["provider"] = provider.lower()
    if vcpus is not None:
        filters["min_vcpus"] = vcpus
    if memory is not None:
        filters["min_memory_gb"] = memory

    with console.status("Searching catalog..."):
        results = Catalog().search(query, **filters)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(title=f'Catalog Search: "{query}"')
    table.add_column("Service", style="cyan")
    table.add_column("Provider")
    table.add_column("Label")
    table.add_column("vCPUs", justify="right")
    table.add_column("Memory (GB)", justify="right")
    table.add_column("$/hr", justify="right")
    table.add_column("Notes", style="dim")

    for item in results:
        table.add_row(
            item.get("service", ""),
            item.get("provider", ""),
            item.get("label", ""),
            str(item.get("vcpus", "-")),
            str(item.get("memory_gb", "-")),
            f"${item['hourly']:.4f}" if item.get("hourly") else "-",
            item.get("notes", ""),
        )

    console.print(table)


@catalog_app.command("compare")
def catalog_compare(
    instances: Annotated[list[str], typer.Argument(help="Instance names to compare (2 or more)")],
) -> None:
    """Compare two or more cloud instances side by side."""
    if len(instances) < 2:
        console.print("[red]Error:[/red] Provide at least 2 instance names to compare.")
        raise typer.Exit(1)

    with console.status("Fetching instance details..."):
        results = Catalog().compare(instances)

    if not results:
        console.print("[yellow]No data found for the given instances.[/yellow]")
        return

    # Results is expected to be a list of dicts, one per instance
    all_keys = set()
    for r in results:
        all_keys.update(r.keys())

    display_fields = ["service", "provider", "label", "vcpus", "memory_gb", "hourly", "monthly", "notes"]
    fields = [f for f in display_fields if f in all_keys]
    for k in sorted(all_keys):
        if k not in fields:
            fields.append(k)

    table = Table(title="Instance Comparison")
    table.add_column("Attribute", style="cyan")
    for instance in instances:
        table.add_column(instance, justify="right")

    inst_map = {r.get("service", r.get("id", "")): r for r in results}

    for field in fields:
        row = [field]
        for inst in instances:
            data = inst_map.get(inst, {})
            val = data.get(field, "-")
            if field in ("hourly",) and isinstance(val, float):
                row.append(f"${val:.4f}")
            elif field in ("monthly",) and isinstance(val, float):
                row.append(f"${val:,.2f}")
            else:
                row.append(str(val) if val is not None else "-")
        table.add_row(*row)

    console.print(table)
