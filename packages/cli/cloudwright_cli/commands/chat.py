from __future__ import annotations

from typing import Annotated

import typer
from cloudwright import Architect, ArchSpec
from cloudwright.ascii_diagram import render_ascii
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.syntax import Syntax

console = Console()

_HELP = """\
Commands:
  /save <file>         Save last architecture to YAML file
  /diagram             Show ASCII diagram for last architecture
  /yaml                Show YAML for last architecture
  /cost                Show cost estimate for last architecture
  /validate [fw]       Run compliance check (hipaa, pci-dss, soc2, fedramp, gdpr)
  /export <fmt>        Export last architecture (terraform, mermaid, d2, cloudformation, sbom, aibom)
  /terraform           Export last architecture as Terraform
  /new                 Start a new architecture from scratch
  /quit                Exit

Follow-up messages modify the current architecture. Use /new to start over.
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
        import cloudwright_web  # type: ignore
        import uvicorn
    except ImportError:
        console.print(
            "[red]Error:[/red] cloudwright-web is not installed.\nInstall it with: pip install 'cloudwright-ai[web]'"
        )
        raise typer.Exit(1)

    import socket

    port = 8000
    for candidate in range(8000, 8100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", candidate)) != 0:
                port = candidate
                break

    import threading
    import time
    import webbrowser

    url = f"http://127.0.0.1:{port}"
    console.print(f"[cyan]Launching Cloudwright web UI on {url}[/cyan]")

    def _open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(cloudwright_web.app, host="127.0.0.1", port=port)


def _run_terminal_chat() -> None:
    console.print(
        Panel(
            "[bold cyan]Cloudwright Architecture Chat[/bold cyan]\nDescribe any cloud architecture.",
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

        if text.lower() == "/new":
            last_spec = None
            history.clear()
            console.print("[cyan]Starting fresh. Describe a new architecture.[/cyan]")
            continue

        if text.startswith("/save "):
            path = text[6:].strip()
            if not last_spec:
                console.print("[yellow]No architecture to save yet.[/yellow]")
            else:
                from pathlib import Path

                Path(path).write_text(last_spec.to_yaml())
                console.print(f"[green]Saved to {path}[/green]")
            continue

        if text == "/diagram":
            if not last_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            else:
                console.print(Rule(f"[bold cyan]{last_spec.name}[/bold cyan]"))
                console.print(render_ascii(last_spec))
            continue

        if text == "/yaml":
            if not last_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            else:
                console.print(Rule(f"[bold cyan]{last_spec.name}[/bold cyan]"))
                console.print(Syntax(last_spec.to_yaml(), "yaml", theme="monokai", word_wrap=True))
            continue

        if text == "/cost":
            if not last_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            elif not last_spec.cost_estimate:
                console.print("[yellow]No cost estimate available.[/yellow]")
            else:
                _print_cost_summary(last_spec)
            continue

        if text.startswith("/validate"):
            if not last_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            else:
                parts = text.split(None, 1)
                framework = parts[1].strip() if len(parts) > 1 else None
                _run_validate(last_spec, framework)
            continue

        if text == "/terraform":
            if not last_spec:
                console.print("[yellow]No architecture to export yet.[/yellow]")
            else:
                try:
                    content = last_spec.export("terraform")
                    console.print(Syntax(content, "hcl", theme="monokai", word_wrap=True))
                except ValueError as e:
                    console.print(f"[red]Error:[/red] {e}")
            continue

        if text.startswith("/export "):
            fmt = text[8:].strip()
            if not last_spec:
                console.print("[yellow]No architecture to export yet.[/yellow]")
            else:
                try:
                    content = last_spec.export(fmt)
                    lang = {"terraform": "hcl", "mermaid": "text", "d2": "text", "cloudformation": "yaml"}.get(
                        fmt, "json"
                    )
                    console.print(Syntax(content, lang, theme="monokai", word_wrap=True))
                except ValueError as e:
                    console.print(f"[red]Error:[/red] {e}")
            continue

        # Treat as architecture request — modify existing or design new
        history.append({"role": "user", "content": text})

        with console.status("Thinking..."):
            try:
                if last_spec is not None:
                    spec = architect.modify(last_spec, text)
                else:
                    spec = architect.design(text)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                history.pop()
                continue

        # Auto-reprice after each design/modify
        if not spec.cost_estimate:
            try:
                from cloudwright.cost import CostEngine

                estimate = CostEngine().estimate(spec)
                spec = spec.model_copy(update={"cost_estimate": estimate})
            except Exception:
                pass  # cost is best-effort

        verb = "Modified" if last_spec is not None else "Designed"
        last_spec = spec
        history.append({"role": "assistant", "content": f"{verb}: {spec.name}"})

        console.print(Rule(f"[bold cyan]{spec.name}[/bold cyan]"))
        console.print(render_ascii(spec))

        if spec.cost_estimate:
            _print_cost_summary(spec)

        from cloudwright_cli.utils import auto_save_spec

        save_path = auto_save_spec(spec)
        console.print(f"[dim]Saved: {save_path}[/dim]")

        suggestions = spec.metadata.get("suggestions", [])
        if suggestions:
            console.print(f"[dim]Try: {' | '.join(repr(s) for s in suggestions[:3])}[/dim]")


def _run_validate(spec: ArchSpec, framework: str | None) -> None:
    from cloudwright.validator import Validator

    if framework:
        results = Validator().validate(spec, compliance=[framework])
    else:
        results = Validator().validate(spec, well_architected=True)

    if not results:
        console.print("[yellow]No validation results.[/yellow]")
        return

    for result in results:
        passed = sum(1 for c in result.checks if c.passed)
        total = len(result.checks)
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        console.print(f"{result.framework}: {status}  ({passed}/{total} checks passed)")
        for check in result.checks:
            icon = "[green]+[/green]" if check.passed else "[red]-[/red]"
            console.print(f"  {icon} {check.name}")
            if not check.passed and check.recommendation:
                console.print(f"    [dim]{check.recommendation}[/dim]")



def _print_cost_summary(spec: ArchSpec) -> None:
    from rich.table import Table

    table = Table(title="Cost Estimate", show_footer=True)
    table.add_column("Component", style="cyan")
    table.add_column("Monthly", justify="right", footer=f"${spec.cost_estimate.monthly_total:,.2f}")
    table.add_column("Notes", style="dim")

    for item in spec.cost_estimate.breakdown:
        table.add_row(item.component_id, f"${item.monthly:,.2f}", item.notes)

    console.print(table)
