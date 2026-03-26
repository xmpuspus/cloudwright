from __future__ import annotations

from cloudwright import ConversationSession
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

console = Console()


def stream_response(session: ConversationSession, text: str) -> list[str]:
    """Stream LLM response with Live rendering. Returns collected chunks.

    Falls back to session.send() if streaming fails due to a non-rate-limit,
    non-timeout error.

    Returns an empty list if the error was handled (rate limit / timeout / no provider).
    Returns None on fallback send() error.
    """
    chunks: list[str] = []
    try:
        with Live(Markdown(""), console=console, refresh_per_second=12) as live:
            for chunk in session.send_stream(text):
                chunks.append(chunk)
                live.update(Markdown("".join(chunks)))
        return chunks
    except Exception as stream_err:
        raise stream_err


def is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "rate limit" in msg or "rate_limit" in msg or "429" in msg


def is_timeout(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "timeout" in msg or "timed out" in msg


def format_error(exc: Exception) -> str:
    msg = str(exc)
    if isinstance(exc, RuntimeError) and "No LLM provider" in msg:
        return "[red]No LLM provider configured.[/red] Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
    if is_rate_limit(exc):
        return "[yellow]Rate limited, try again in a moment.[/yellow]"
    if is_timeout(exc):
        return "[yellow]Request timed out, try a simpler request.[/yellow]"
    if isinstance(exc, ValueError):
        return "[red]Failed to parse architecture, try rephrasing.[/red]"
    return f"[red]Error:[/red] {exc}"
