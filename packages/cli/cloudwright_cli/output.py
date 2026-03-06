"""Unified CLI output — structured JSON envelopes, NDJSON streaming,
stderr diagnostics, dry-run previews, and path validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

# stdout for data, stderr for diagnostics/errors
out_console = Console()
err_console = Console(stderr=True)

_BLOCKED_PREFIXES = ("/etc", "/usr", "/var", "/System", "/Library")


def emit_success(ctx: typer.Context, data: Any) -> None:
    """Emit structured JSON: {"data": ...} to stdout."""
    envelope = {"data": data}
    print(json.dumps(envelope, indent=2, default=str))


def emit_error(
    ctx: typer.Context,
    e: Exception,
    *,
    code: str | None = None,
    action: str = "",
) -> None:
    """Emit structured error and exit 1.

    JSON mode: {"error": {"code": ..., "message": ..., "action": ...}} to stdout.
    Human mode: colored error to stderr.
    """
    verbose = _get_flag(ctx, "verbose")

    if code is None:
        code = _classify_error(e)
    msg = str(e)

    if is_json_mode(ctx):
        envelope: dict[str, Any] = {
            "error": {
                "code": code,
                "message": msg,
            }
        }
        if action:
            envelope["error"]["action"] = action
        print(json.dumps(envelope, indent=2, default=str))
    else:
        err_console.print(f"[red]Error:[/red] {msg}")
        if action:
            err_console.print(f"[dim]Fix: {action}[/dim]")

    if verbose:
        err_console.print_exception()

    raise typer.Exit(1)


def emit_stream(item: dict) -> None:
    """Emit a single NDJSON line to stdout (compact, flushed)."""
    print(json.dumps(item, default=str, separators=(",", ":")), flush=True)


def emit_dry_run(ctx: typer.Context, info: dict) -> None:
    """Show what an LLM operation would do without calling the API."""
    if is_json_mode(ctx):
        emit_success(ctx, {"dry_run": info})
    else:
        err_console.print("[yellow]DRY RUN[/yellow] -- no LLM API call will be made\n")
        if info.get("model"):
            err_console.print(f"  Model: {info['model']}")
        if info.get("estimated_tokens"):
            err_console.print(f"  Estimated input tokens: ~{info['estimated_tokens']:,}")
        if info.get("max_tokens"):
            err_console.print(f"  Max output tokens: {info['max_tokens']:,}")
        if info.get("constraints"):
            err_console.print(f"  Constraints: {json.dumps(info['constraints'], default=str)}")
        if info.get("system_prompt_preview"):
            preview = info["system_prompt_preview"][:200]
            err_console.print(f"  System prompt: {preview}...")
        if info.get("user_prompt_preview"):
            preview = info["user_prompt_preview"][:300]
            err_console.print(f"  User prompt: {preview}...")
    raise typer.Exit(0)


def is_json_mode(ctx: typer.Context) -> bool:
    return bool(ctx.obj and ctx.obj.get("json"))


def should_stream(ctx: typer.Context) -> bool:
    """True if --stream flag is explicitly set."""
    return bool(ctx.obj and ctx.obj.get("stream"))


def validate_output_path(path: str | Path) -> Path:
    """Validate output path is safe. Raises ValueError on traversal."""
    p = Path(path).resolve()

    if ".." in str(path):
        raise ValueError(f"Path traversal detected in output path: {path}")

    for prefix in _BLOCKED_PREFIXES:
        if str(p).startswith(prefix):
            raise ValueError(f"Cannot write to system directory: {prefix}")

    return p


def confirm_overwrite(path: Path, *, ctx: typer.Context | None = None) -> bool:
    """Prompt for confirmation if file exists.

    In JSON mode, returns False (machine consumers should not get prompts).
    """
    if not path.exists():
        return True
    if ctx and is_json_mode(ctx):
        return False
    return typer.confirm(f"File {path} already exists. Overwrite?", default=False)


def _get_flag(ctx: typer.Context, key: str) -> bool:
    return bool(ctx.obj and ctx.obj.get(key))


def _classify_error(e: Exception) -> str:
    import yaml

    if isinstance(e, FileNotFoundError):
        return "file_not_found"
    if isinstance(e, yaml.YAMLError):
        return "invalid_yaml"
    if "validation" in type(e).__name__.lower():
        return "validation_error"
    if isinstance(e, ValueError):
        return "value_error"
    if isinstance(e, PermissionError):
        return "permission_denied"
    if isinstance(e, RuntimeError):
        return "runtime_error"
    return "internal_error"
