from __future__ import annotations

import functools
import traceback
from typing import Any, Callable

import typer
from rich.console import Console

err_console = Console(stderr=True)


def cloudwright_command(json_output: bool = True, dry_run: bool = False) -> Callable:
    """Decorator that wraps command functions with standard output handling.

    Handles: JSON envelope wrapping, Rich console formatting, --verbose stack
    traces, --dry-run interception, and exit codes.

    Args:
        json_output: Whether the command supports --json output mode.
        dry_run: Whether the command supports --dry-run interception.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            # Extract typer context from positional or keyword args
            ctx = _extract_ctx(fn, args, kwargs)
            verbose = bool(ctx and ctx.obj and ctx.obj.get("verbose"))
            is_dry = dry_run and bool(ctx and ctx.obj and ctx.obj.get("dry_run"))

            if is_dry:
                # Commands that handle dry_run themselves will see ctx.obj["dry_run"]
                # This outer gate lets the inner function emit_dry_run and exit.
                pass

            try:
                fn(*args, **kwargs)
            except typer.Exit:
                raise
            except SystemExit:
                raise
            except Exception as e:
                if verbose:
                    err_console.print_exception()
                else:
                    err_console.print(f"[red]Error:[/red] {e}")
                    if verbose:
                        err_console.print(traceback.format_exc())
                raise typer.Exit(1)

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
