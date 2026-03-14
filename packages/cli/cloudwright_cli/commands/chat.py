from __future__ import annotations

import logging
import sys
import time
from typing import Annotated

import typer
from cloudwright import ArchSpec, ConversationSession
from cloudwright.ascii_diagram import render_ascii
from cloudwright.session_store import SessionStore
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.syntax import Syntax

console = Console()

_HELP = """\
Commands:
  /save <file>              Save last architecture to YAML file
  /save-session [name]      Save this conversation session
  /load-session <name>      Load a saved session
  /sessions                 List saved sessions
  /diagram                  Show ASCII diagram for last architecture
  /yaml                     Show YAML for last architecture
  /cost                     Show cost estimate for last architecture
  /validate [fw]            Run compliance check (hipaa, pci-dss, soc2, fedramp, gdpr)
  /export <fmt>             Export last architecture (terraform, mermaid, d2, cloudformation, sbom, aibom)
  /terraform                Export last architecture as Terraform
  /new                      Start a new architecture from scratch
  /help, /?                 Show this help
  /quit                     Exit

Follow-up messages modify the current architecture. Use /new to start over.
"""


def chat(
    web: Annotated[bool, typer.Option("--web", help="Launch web UI instead of terminal chat")] = False,
    resume: Annotated[str | None, typer.Option("--resume", help="Resume a saved session by ID")] = None,
    debug: Annotated[bool, typer.Option("--debug", help="Log LLM requests/responses to stderr")] = False,
) -> None:
    """Interactive architecture design chat."""
    if web:
        _launch_web()
        return

    _run_terminal_chat(resume=resume, debug=debug)


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
    import webbrowser

    url = f"http://127.0.0.1:{port}"
    console.print(f"[cyan]Launching Cloudwright web UI on {url}[/cyan]")

    def _open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(cloudwright_web.app, host="127.0.0.1", port=port)


def _run_terminal_chat(resume: str | None = None, debug: bool = False) -> None:
    if debug:
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    console.print(
        Panel(
            "[bold cyan]Cloudwright Architecture Chat[/bold cyan]\nDescribe any cloud architecture.",
            subtitle="Type /quit to exit",
        )
    )
    console.print(f"[dim]{_HELP}[/dim]")

    store = SessionStore()
    session = ConversationSession()

    if resume:
        try:
            session = store.load(resume)
            console.print(f"[cyan]Resumed session: {resume}[/cyan]")
            if session.current_spec:
                console.print(f"[dim]Current architecture: {session.current_spec.name}[/dim]")
        except FileNotFoundError:
            console.print(f"[yellow]Session {resume!r} not found. Starting fresh.[/yellow]")

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]>[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting.[/dim]")
            _maybe_save_on_quit(session, store)
            break

        text = user_input.strip()
        if not text:
            continue

        if text.lower() in ("/quit", "/exit", "/q"):
            _maybe_save_on_quit(session, store)
            console.print("[dim]Goodbye.[/dim]")
            break

        if text.lower() in ("/help", "/?"):
            console.print(f"[dim]{_HELP}[/dim]")
            continue

        if text.lower() == "/new":
            session = ConversationSession()
            console.print("[cyan]Starting fresh. Describe a new architecture.[/cyan]")
            continue

        if text.startswith("/save ") and not text.startswith("/save-session"):
            path = text[6:].strip()
            if not session.current_spec:
                console.print("[yellow]No architecture to save yet.[/yellow]")
            else:
                from pathlib import Path

                Path(path).write_text(session.current_spec.to_yaml())
                console.print(f"[green]Saved to {path}[/green]")
            continue

        if text.startswith("/save-session"):
            parts = text.split(None, 1)
            name = parts[1].strip() if len(parts) > 1 else _default_session_id()
            saved_path = store.save(name, session)
            console.print(f"[green]Session saved: {name} ({saved_path})[/green]")
            continue

        if text.startswith("/load-session"):
            parts = text.split(None, 1)
            if len(parts) < 2:
                console.print("[yellow]Usage: /load-session <name>[/yellow]")
                continue
            name = parts[1].strip()
            try:
                session = store.load(name)
                console.print(f"[cyan]Loaded session: {name}[/cyan]")
                if session.current_spec:
                    console.print(Rule(f"[bold cyan]{session.current_spec.name}[/bold cyan]"))
                    console.print(render_ascii(session.current_spec))
            except FileNotFoundError:
                console.print(f"[yellow]Session {name!r} not found.[/yellow]")
            continue

        if text == "/sessions":
            sessions = store.list_sessions()
            if not sessions:
                console.print("[dim]No saved sessions.[/dim]")
            else:
                for s in sessions:
                    spec_note = f"  [{s['spec_name']}]" if s.get("spec_name") else ""
                    console.print(f"  [cyan]{s['session_id']}[/cyan]  {s['turn_count']} turns{spec_note}")
            continue

        if text == "/diagram":
            if not session.current_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            else:
                console.print(Rule(f"[bold cyan]{session.current_spec.name}[/bold cyan]"))
                console.print(render_ascii(session.current_spec))
            continue

        if text == "/yaml":
            if not session.current_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            else:
                console.print(Rule(f"[bold cyan]{session.current_spec.name}[/bold cyan]"))
                console.print(Syntax(session.current_spec.to_yaml(), "yaml", theme="monokai", word_wrap=True))
            continue

        if text == "/cost":
            if not session.current_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            elif not session.current_spec.cost_estimate:
                console.print("[yellow]No cost estimate available.[/yellow]")
            else:
                _print_cost_summary(session.current_spec)
            continue

        if text.startswith("/validate"):
            if not session.current_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            else:
                parts = text.split(None, 1)
                framework = parts[1].strip() if len(parts) > 1 else None
                _run_validate(session.current_spec, framework)
            continue

        if text == "/terraform":
            if not session.current_spec:
                console.print("[yellow]No architecture to export yet.[/yellow]")
            else:
                try:
                    content = session.current_spec.export("terraform")
                    console.print(Syntax(content, "hcl", theme="monokai", word_wrap=True))
                except ValueError as e:
                    console.print(f"[red]Error:[/red] {e}")
            continue

        if text.startswith("/export "):
            fmt = text[8:].strip()
            if not session.current_spec:
                console.print("[yellow]No architecture to export yet.[/yellow]")
            else:
                try:
                    content = session.current_spec.export(fmt)
                    lang = {"terraform": "hcl", "mermaid": "text", "d2": "text", "cloudformation": "yaml"}.get(
                        fmt, "json"
                    )
                    console.print(Syntax(content, lang, theme="monokai", word_wrap=True))
                except ValueError as e:
                    console.print(f"[red]Error:[/red] {e}")
            continue

        had_spec = session.current_spec is not None

        # Stream the LLM response with live rendering
        chunks: list[str] = []
        try:
            with Live(Markdown(""), console=console, refresh_per_second=12) as live:
                for chunk in session.send_stream(text):
                    chunks.append(chunk)
                    live.update(Markdown("".join(chunks)))
        except Exception as stream_err:
            # Fallback to non-streaming if streaming fails
            if _is_rate_limit(stream_err):
                console.print("[yellow]Rate limited, try again in a moment.[/yellow]")
                continue
            if _is_timeout(stream_err):
                console.print("[yellow]Request timed out, try a simpler request.[/yellow]")
                continue
            if isinstance(stream_err, RuntimeError) and "No LLM provider" in str(stream_err):
                console.print(
                    "[red]No LLM provider configured.[/red] Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
                )
                continue
            try:
                _, _ = session.send(text)
            except Exception as e:
                console.print(_format_error(e))
                continue

        # Token usage (show regardless of spec)
        if session.last_usage:
            inp = session.last_usage.get("input_tokens", 0)
            out = session.last_usage.get("output_tokens", 0)
            cost = session.last_usage.get("estimated_cost", 0.0)
            console.print(f"[dim]Tokens: {inp} in / {out} out (~${cost:.4f})[/dim]")

        spec = session.current_spec

        if spec is None:
            continue

        # Auto-reprice after each response
        if not spec.cost_estimate:
            try:
                from cloudwright.cost import CostEngine

                estimate = CostEngine().estimate(spec)
                spec = spec.model_copy(update={"cost_estimate": estimate})
                session.current_spec = spec
            except Exception:
                pass

        console.print(Rule(f"[bold cyan]{spec.name}[/bold cyan]"))
        console.print(render_ascii(spec))

        if spec.cost_estimate:
            _print_cost_summary(spec)

        # Show spec diff when modifying
        if had_spec and session.last_diff:
            _print_diff(session.last_diff)

        suggestions = spec.metadata.get("suggestions", [])
        if suggestions:
            console.print(f"[dim]Try: {' | '.join(repr(s) for s in suggestions[:3])}[/dim]")


def _default_session_id() -> str:
    from datetime import datetime

    return datetime.now().strftime("session-%Y%m%d-%H%M%S")


def _maybe_save_on_quit(session: ConversationSession, store: SessionStore) -> None:
    turn_count = sum(1 for m in session.history if m.get("role") == "user")
    if turn_count == 0:
        return
    try:
        answer = Prompt.ask("Save session? (y/N)", default="N")
    except (KeyboardInterrupt, EOFError):
        return
    if answer.strip().lower() == "y":
        name = _default_session_id()
        store.save(name, session)
        console.print(f"[green]Session saved as: {name}[/green]")


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "rate limit" in msg or "rate_limit" in msg or "429" in msg


def _is_timeout(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "timeout" in msg or "timed out" in msg


def _format_error(exc: Exception) -> str:
    msg = str(exc)
    if isinstance(exc, RuntimeError) and "No LLM provider" in msg:
        return "[red]No LLM provider configured.[/red] Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
    if _is_rate_limit(exc):
        return "[yellow]Rate limited, try again in a moment.[/yellow]"
    if _is_timeout(exc):
        return "[yellow]Request timed out, try a simpler request.[/yellow]"
    if isinstance(exc, ValueError):
        return "[red]Failed to parse architecture, try rephrasing.[/red]"
    return f"[red]Error:[/red] {exc}"


def _print_diff(diff) -> None:
    if diff.added:
        console.print(f"[green]+ Added: {', '.join(c.id for c in diff.added)}[/green]")
    if diff.removed:
        console.print(f"[red]- Removed: {', '.join(c.id for c in diff.removed)}[/red]")
    if diff.changed:
        console.print(f"[yellow]~ Changed: {', '.join(c.id for c in diff.changed)}[/yellow]")
    if diff.cost_delta is not None and diff.cost_delta != 0:
        sign = "+" if diff.cost_delta > 0 else ""
        console.print(f"[dim]Cost delta: {sign}${diff.cost_delta:,.2f}/mo[/dim]")


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
