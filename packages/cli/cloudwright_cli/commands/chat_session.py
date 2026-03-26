from __future__ import annotations

from datetime import datetime

from cloudwright import ConversationSession
from cloudwright.session_store import SessionStore
from rich.console import Console
from rich.prompt import Prompt

console = Console()


def make_session(resume: str | None, store: SessionStore) -> ConversationSession:
    session = ConversationSession()
    if resume:
        try:
            session = store.load(resume)
            console.print(f"[cyan]Resumed session: {resume}[/cyan]")
            if session.current_spec:
                console.print(f"[dim]Current architecture: {session.current_spec.name}[/dim]")
        except FileNotFoundError:
            console.print(f"[yellow]Session {resume!r} not found. Starting fresh.[/yellow]")
    return session


def default_session_id() -> str:
    return datetime.now().strftime("session-%Y%m%d-%H%M%S")


def maybe_save_on_quit(session: ConversationSession, store: SessionStore) -> None:
    turn_count = sum(1 for m in session.history if m.get("role") == "user")
    if turn_count == 0:
        return
    try:
        answer = Prompt.ask("Save session? (y/N)", default="N")
    except (KeyboardInterrupt, EOFError):
        return
    if answer.strip().lower() == "y":
        name = default_session_id()
        store.save(name, session)
        console.print(f"[green]Session saved as: {name}[/green]")
