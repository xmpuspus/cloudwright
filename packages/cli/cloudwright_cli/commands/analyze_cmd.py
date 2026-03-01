"""Analyze architecture blast radius and dependencies."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from cloudwright_cli.utils import handle_error

console = Console()


def analyze(
    ctx: typer.Context,
    spec_file: Annotated[str, typer.Argument(help="Path to ArchSpec YAML/JSON file")],
    component: Annotated[str | None, typer.Option("--component", "-c", help="Analyze specific component")] = None,
) -> None:
    """Analyze blast radius, SPOFs, and dependency structure."""
    try:
        from cloudwright import ArchSpec
        from cloudwright.analyzer import Analyzer

        spec = ArchSpec.from_file(spec_file)

        if component:
            valid_ids = {c.id for c in spec.components}
            if component not in valid_ids:
                console.print(f"[red]Error:[/red] Component '{component}' not found in spec.")
                console.print(f"[dim]Available components: {', '.join(sorted(valid_ids))}[/dim]")
                raise typer.Exit(1)

        analyzer = Analyzer()
        result = analyzer.analyze(spec, component_id=component)

        if ctx.obj and ctx.obj.get("json"):
            print(json.dumps(result.to_dict(), indent=2))
            return

        spof_text = ", ".join(result.spofs) if result.spofs else "None"
        console.print(
            Panel(
                f"Components: {result.total_components}  |  "
                f"Max Blast Radius: {result.max_blast_radius}  |  "
                f"SPOFs: {len(result.spofs)}",
                title=f"Blast Radius Analysis: {spec.name}",
                border_style="red" if result.spofs else "green",
            )
        )

        if result.spofs:
            console.print(f"\n[bold red]Single Points of Failure:[/bold red] {spof_text}")

        if result.critical_path:
            console.print(f"\n[bold]Critical Path:[/bold] {' -> '.join(result.critical_path)}")

        table = Table(title="\nComponent Impact")
        table.add_column("Component", style="cyan")
        table.add_column("Service")
        table.add_column("Tier", justify="right")
        table.add_column("Direct Deps", justify="right")
        table.add_column("Blast Radius", justify="right")
        table.add_column("SPOF")

        for impact in result.components:
            spof_marker = "[red]YES[/red]" if impact.is_spof else ""
            if impact.blast_radius > result.total_components * 0.5:
                blast_color = "red"
            elif impact.blast_radius > 0:
                blast_color = "yellow"
            else:
                blast_color = "green"
            table.add_row(
                impact.component_id,
                impact.service,
                str(impact.tier),
                str(len(impact.direct_dependents)),
                f"[{blast_color}]{impact.blast_radius}[/{blast_color}]",
                spof_marker,
            )

        console.print(table)

        if not component:
            all_targets: set[str] = set()
            for deps in result.graph.values():
                all_targets.update(deps)
            roots = [c.component_id for c in result.components if c.component_id not in all_targets]
            if not roots and result.components:
                roots = [result.components[0].component_id]

            tree = Tree("[bold]Dependency Graph[/bold]")
            visited_tree: set[str] = set()
            for root in roots:
                _build_tree(tree, root, result.graph, visited_tree)

            console.print(tree)

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)


def _build_tree(
    parent: Tree,
    node_id: str,
    graph: dict[str, list[str]],
    visited: set[str],
    depth: int = 0,
) -> None:
    if depth > 10:
        return
    label = f"[cyan]{node_id}[/cyan]" if node_id not in visited else f"[dim]{node_id} (cycle)[/dim]"
    branch = parent.add(label)
    if node_id in visited:
        return
    visited.add(node_id)
    for dep in graph.get(node_id, []):
        _build_tree(branch, dep, graph, visited, depth + 1)
