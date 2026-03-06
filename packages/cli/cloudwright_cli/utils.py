from __future__ import annotations

import re
from pathlib import Path

import typer

from cloudwright_cli.output import emit_error


def handle_error(ctx: typer.Context, e: Exception) -> None:
    """Print a clean error message and exit 1.

    Delegates to output.emit_error for consistent structured output.
    """
    emit_error(ctx, e)


def auto_save_spec(spec, explicit_output: Path | None = None) -> Path:
    if explicit_output:
        explicit_output.write_text(spec.to_yaml())
        return explicit_output
    slug = re.sub(r"[^a-z0-9]+", "-", spec.name.lower()).strip("-")
    path = Path(f"{slug}.yaml")
    path.write_text(spec.to_yaml())
    return path
