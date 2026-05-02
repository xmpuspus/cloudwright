from __future__ import annotations

import logging
import os
import time
from typing import Annotated

import typer
from cloudwright import ArchSpec, ConversationSession
from cloudwright.ascii_diagram import render_ascii
from cloudwright.logging import configure_logging
from cloudwright.session_store import SessionStore
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.syntax import Syntax

from .chat_session import default_session_id, maybe_save_on_quit
from .chat_streaming import format_error, is_rate_limit, is_timeout
from .chat_ui import _HELP, print_cost_summary, print_diff, run_validate

console = Console()

DEFAULT_WEB_PORT = 8765


def chat(
    web: Annotated[bool, typer.Option("--web", help="Launch web UI instead of terminal chat")] = False,
    resume: Annotated[str | None, typer.Option("--resume", help="Resume a saved session by ID")] = None,
    debug: Annotated[bool, typer.Option("--debug", help="Log LLM requests/responses to stderr")] = False,
    port: Annotated[
        int,
        typer.Option("--port", help=f"Port for --web (default: {DEFAULT_WEB_PORT})"),
    ] = DEFAULT_WEB_PORT,
) -> None:
    """Interactive architecture design chat."""
    if web:
        _launch_web(port=port)
        return

    _run_terminal_chat(resume=resume, debug=debug)


def _launch_web(port: int = DEFAULT_WEB_PORT) -> None:
    try:
        import cloudwright_web  # type: ignore
        import uvicorn
    except ImportError:
        console.print(
            "[red]Error:[/red] cloudwright-web is not installed.\nInstall it with: pip install 'cloudwright-ai[web]'"
        )
        raise typer.Exit(1)

    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            console.print(
                f"[red]Error:[/red] port {port} is already in use. "
                f"Pass --port to choose another (e.g. --port {port + 1})."
            )
            raise typer.Exit(1)

    import threading
    import webbrowser

    url = f"http://127.0.0.1:{port}"
    console.print(f"\n[bold cyan]Cloudwright web UI:[/bold cyan] {url}\n")

    def _open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(cloudwright_web.app, host="127.0.0.1", port=port)


def _run_terminal_chat(resume: str | None = None, debug: bool = False) -> None:
    configure_logging()
    env_level = os.environ.get("CLOUDWRIGHT_LOG_LEVEL", "").upper()
    if debug or env_level == "DEBUG":
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("cloudwright").setLevel(logging.DEBUG)
    elif env_level in {"INFO", "WARNING", "ERROR", "CRITICAL"}:
        logging.getLogger().setLevel(getattr(logging, env_level))
        logging.getLogger("cloudwright").setLevel(getattr(logging, env_level))

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
            maybe_save_on_quit(session, store)
            break

        text = user_input.strip()
        if not text:
            continue

        if text.lower() in ("/quit", "/exit", "/q"):
            maybe_save_on_quit(session, store)
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
            name = parts[1].strip() if len(parts) > 1 else default_session_id()
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
                print_cost_summary(session.current_spec)
            continue

        if text.startswith("/validate"):
            if not session.current_spec:
                console.print("[yellow]No architecture yet.[/yellow]")
            else:
                parts = text.split(None, 1)
                framework = parts[1].strip() if len(parts) > 1 else None
                run_validate(session.current_spec, framework)
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
            if is_rate_limit(stream_err):
                console.print("[yellow]Rate limited, try again in a moment.[/yellow]")
                continue
            if is_timeout(stream_err):
                console.print("[yellow]Request timed out, try a simpler request.[/yellow]")
                continue
            if isinstance(stream_err, RuntimeError) and "No LLM provider" in str(stream_err):
                console.print("[red]No LLM provider configured.[/red] Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")
                continue
            try:
                _, _ = session.send(text)
            except Exception as e:
                console.print(format_error(e))
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
            print_cost_summary(spec)

        # Show spec diff when modifying
        if had_spec and session.last_diff:
            print_diff(session.last_diff)

        suggestions = spec.metadata.get("suggestions", [])
        if suggestions:
            console.print(f"[dim]Try: {' | '.join(repr(s) for s in suggestions[:3])}[/dim]")


def _default_session_id() -> str:
    return default_session_id()


def _maybe_save_on_quit(session: ConversationSession, store: SessionStore) -> None:
    maybe_save_on_quit(session, store)


def _is_rate_limit(exc: Exception) -> bool:
    return is_rate_limit(exc)


def _is_timeout(exc: Exception) -> bool:
    return is_timeout(exc)


def _format_error(exc: Exception) -> str:
    return format_error(exc)


def _print_diff(diff) -> None:
    print_diff(diff)


def _run_validate(spec: ArchSpec, framework: str | None) -> None:
    run_validate(spec, framework)


def _print_cost_summary(spec: ArchSpec) -> None:
    print_cost_summary(spec)
