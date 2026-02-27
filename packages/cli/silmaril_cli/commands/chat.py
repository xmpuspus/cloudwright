from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.syntax import Syntax
from silmaril import Architect, ArchSpec

console = Console()

_HELP = """\
Commands:
  /save <file>     Save last architecture to YAML file
  /cost            Show cost estimate for last architecture
  /export <fmt>    Export last architecture (terraform, mermaid, sbom, aibom)
  /quit            Exit
"""


def chat(
    web: Annotated[bool, typer.Option("--web", help="Launch web UI instead of terminal chat")] = False,
) -> None:
    """Interactive architecture design chat."""
    if web:
        _launch_web()
        return

    _run_terminal_chat()


def _launch_web() -> None:
    try:
        import silmaril_web  # type: ignore
        import uvicorn

        console.print("[cyan]Launching Silmaril web UI...[/cyan]")
        uvicorn.run(silmaril_web.app, host="127.0.0.1", port=8000)
    except ImportError:
        console.print("[red]Error:[/red] silmaril-web is not installed.\nInstall it with: pip install silmaril-web")
        raise typer.Exit(1)


def _run_terminal_chat() -> None:
    console.print(
        Panel(
            "[bold cyan]Silmaril Architecture Chat[/bold cyan]\nDescribe any cloud architecture.",
            subtitle="Type /quit to exit",
        )
    )
    console.print(f"[dim]{_HELP}[/dim]")

    architect = Architect()
    history: list[dict] = []
    last_spec: ArchSpec | None = None

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]>[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting.[/dim]")
            break

        text = user_input.strip()
        if not text:
            continue

        if text.lower() in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if text.startswith("/save "):
            path = text[6:].strip()
            if not last_spec:
                console.print("[yellow]No architecture to save yet.[/yellow]")
            else:
                from pathlib import Path

                Path(path).write_text(last_spec.to_yaml())
                console.print(f"[green]Saved to {path}[/green]")
            continue

        if text == "/cost":
            if not last_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            elif not last_spec.cost_estimate:
                console.print("[yellow]No cost estimate available.[/yellow]")
            else:
                _print_cost_summary(last_spec)
            continue

        if text.startswith("/export "):
            fmt = text[8:].strip()
            if not last_spec:
                console.print("[yellow]No architecture to export yet.[/yellow]")
            else:
                try:
                    content = last_spec.export(fmt)
                    lang = {"terraform": "hcl", "mermaid": "text"}.get(fmt, "json")
                    console.print(Syntax(content, lang, theme="monokai", word_wrap=True))
                except ValueError as e:
                    console.print(f"[red]Error:[/red] {e}")
            continue

        # Treat as architecture request
        history.append({"role": "user", "content": text})

        with console.status("Thinking..."):
            try:
                if last_spec and _looks_like_modification(text):
                    spec = architect.modify(last_spec, text)
                else:
                    spec = architect.design(text)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                history.pop()
                continue

        last_spec = spec
        history.append({"role": "assistant", "content": f"Designed: {spec.name}"})

        yaml_str = spec.to_yaml()
        console.print(Rule(f"[bold cyan]{spec.name}[/bold cyan]"))
        console.print(Syntax(yaml_str, "yaml", theme="monokai", word_wrap=True))

        if spec.cost_estimate:
            _print_cost_summary(spec)


def _looks_like_modification(text: str) -> bool:
    mod_verbs = (
        "add",
        "remove",
        "change",
        "update",
        "replace",
        "increase",
        "decrease",
        "modify",
        "swap",
        "upgrade",
        "downgrade",
    )
    lower = text.lower()
    return any(lower.startswith(v) or f" {v} " in lower for v in mod_verbs)


def _print_cost_summary(spec: ArchSpec) -> None:
    from rich.table import Table

    table = Table(title="Cost Estimate", show_footer=True)
    table.add_column("Component", style="cyan")
    table.add_column("Monthly", justify="right", footer=f"${spec.cost_estimate.monthly_total:,.2f}")
    table.add_column("Notes", style="dim")

    for item in spec.cost_estimate.breakdown:
        table.add_row(item.component_id, f"${item.monthly:,.2f}", item.notes)

    console.print(table)
