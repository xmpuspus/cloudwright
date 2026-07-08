from __future__ import annotations

import functools
from typing import Any, Callable

import typer
from rich.console import Console

from cloudwright_cli.output import emit_error

err_console = Console(stderr=True)


def cloudwright_command(json_output: bool = True, dry_run: bool = False) -> Callable:
    """Decorator that wraps command functions with standard output handling.

    Catches any exception the command function doesn't already handle and
    renders it cleanly instead of letting a raw traceback reach the user:
    a JSON envelope (via `output.emit_error`) in --json mode, a plain
    `Error: ...` on stderr otherwise, full traceback only under --verbose.

    Commands that already call `output.emit_error` themselves for specific
    known failures are unaffected — that path raises `typer.Exit`, which
    this decorator re-raises untouched.

    Args:
        json_output: Whether the command supports --json output mode.
        dry_run: Whether the command supports --dry-run interception.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            # Extract typer context from positional or keyword args
            ctx = _extract_ctx(fn, args, kwargs)

            try:
                fn(*args, **kwargs)
            except typer.Exit:
                raise
            except SystemExit:
                raise
            except Exception as e:
                if ctx is None:
                    # Commands without a ctx param (e.g. mcp_serve) can't
                    # report JSON mode or verbosity — fall back to a plain
                    # stderr message.
                    err_console.print(f"[red]Error:[/red] {e}")
                    raise typer.Exit(1) from None
                emit_error(ctx, e)

        return wrapper

    return decorator


def _extract_ctx(fn: Callable, args: tuple, kwargs: dict) -> typer.Context | None:
    import inspect

    sig = inspect.signature(fn)
    param_names = list(sig.parameters.keys())

    # Check kwargs first
    if "ctx" in kwargs:
        return kwargs["ctx"]

    # Check positional args by parameter name
    for i, name in enumerate(param_names):
        if name == "ctx" and i < len(args):
            return args[i]

    return None
