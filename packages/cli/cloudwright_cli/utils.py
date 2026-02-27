from __future__ import annotations

import json

import typer
from rich.console import Console

_err_console = Console(stderr=True)


def handle_error(ctx: typer.Context, e: Exception) -> None:
    """Print a clean error message and exit 1."""
    import yaml

    verbose = ctx.obj.get("verbose", False) if ctx.obj else False
    json_mode = ctx.obj.get("json", False) if ctx.obj else False

    if isinstance(e, FileNotFoundError):
        msg = f"File not found: {e}"
    elif isinstance(e, yaml.YAMLError):
        msg = f"Invalid YAML: {e}"
    elif "validation" in type(e).__name__.lower():
        msg = f"Invalid spec: {e}"
    elif isinstance(e, ValueError):
        msg = str(e)
    else:
        msg = f"Error: {e}"

    if json_mode:
        print(json.dumps({"error": msg}))
    else:
        _err_console.print(f"[red]Error:[/red] {msg}")

    if verbose:
        _err_console.print_exception()

    raise typer.Exit(1)
