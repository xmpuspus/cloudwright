"""Structured modify — modify a spec with natural language and show the diff."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table

from cloudwright_cli.utils import handle_error

console = Console()


def modify(
    ctx: typer.Context,
    spec_file: Annotated[str, typer.Argument(help="Path to the ArchSpec YAML to modify")],
    instruction: Annotated[str, typer.Argument(help="Natural language modification instruction")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file (default: overwrite input)")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show changes without writing")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Modify an ArchSpec with natural language and show the diff."""
    try:
        from cloudwright import ArchSpec, Differ
        from cloudwright.architect import Architect
        from cloudwright.cost import CostEngine

        spec_path = Path(spec_file)
        if not spec_path.exists():
            console.print(f"[red]Error:[/red] Spec file not found: {spec_file}")
            raise typer.Exit(1)

        original = ArchSpec.from_file(spec_path)

        console.print(f"Modifying [cyan]{spec_file}[/cyan]: [yellow]{instruction}[/yellow]\n")

        try:
            architect = Architect()
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

        with console.status("Applying modification..."):
            modified = architect.modify(original, instruction)

        # Price both versions; ignore errors (catalog may not have all services)
        cost_engine = CostEngine()
        try:
            original_costed = cost_engine.price(original)
            modified_costed = cost_engine.price(modified)
        except Exception:
            original_costed = original
            modified_costed = modified

        diff_result = Differ().diff(original_costed, modified_costed)

        if json_output:
            import json

            result = {
                "original": original.model_dump(),
                "modified": modified.model_dump(),
                "diff": diff_result.model_dump(),
            }
            console.print_json(json.dumps(result, default=str))
            return

        console.print(Rule("[bold]Changes[/bold]"))

        if not diff_result.added and not diff_result.removed and not diff_result.changed:
            console.print("[dim]No structural changes detected.[/dim]")
        else:
            if diff_result.added:
                console.print(f"[bold green]Added ({len(diff_result.added)})[/bold green]")
                for comp in diff_result.added:
                    console.print(f"  [green]+[/green] {comp.id} ({comp.service}) — {comp.label}")
                console.print()

            if diff_result.removed:
                console.print(f"[bold red]Removed ({len(diff_result.removed)})[/bold red]")
                for comp in diff_result.removed:
                    console.print(f"  [red]-[/red] {comp.id} ({comp.service}) — {comp.label}")
                console.print()

            if diff_result.changed:
                table = Table(title="Changed")
                table.add_column("Component", style="cyan")
                table.add_column("Field")
                table.add_column("Before", style="red")
                table.add_column("After", style="green")
                for change in diff_result.changed:
                    table.add_row(change.component_id, change.field, change.old_value, change.new_value)
                console.print(table)
                console.print()

        if diff_result.cost_delta != 0.0:
            sign = "+" if diff_result.cost_delta > 0 else ""
            color = "red" if diff_result.cost_delta > 0 else "green"
            console.print(f"Cost delta: [{color}]{sign}${diff_result.cost_delta:,.2f}/mo[/{color}]")

        if diff_result.compliance_impact:
            console.print("\n[bold red]Compliance Impact[/bold red]")
            for impact in diff_result.compliance_impact:
                console.print(f"  [red]![/red] {impact}")

        console.print()
        console.print(
            Panel(
                Syntax(modified.to_yaml(), "yaml", theme="monokai", word_wrap=True),
                title="[bold cyan]Modified Spec[/bold cyan]",
            )
        )

        if not dry_run:
            out_path = Path(output) if output else spec_path
            out_path.write_text(modified.to_yaml())
            console.print(f"\n[green]Written to {out_path}[/green]")
        else:
            console.print("\n[dim]Dry run — no files written.[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)
