"""Import live cloud infrastructure into an ArchSpec via provider APIs.

Currently supports AWS via boto3 (``cloudwright import-live --provider aws``).
GCP and Azure surface a clear ``not yet implemented`` error.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from cloudwright_cli.output import emit_success, err_console, is_json_mode, validate_output_path
from cloudwright_cli.utils import handle_error

console = Console()


def import_live(
    ctx: typer.Context,
    provider: Annotated[
        str,
        typer.Option("--provider", help="Cloud provider to scan: aws (gcp, azure not yet implemented)"),
    ] = "aws",
    region: Annotated[
        str,
        typer.Option("--region", help="Cloud region (e.g. us-east-1)"),
    ] = "us-east-1",
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="AWS named profile (~/.aws/credentials)"),
    ] = None,
    services: Annotated[
        str | None,
        typer.Option(
            "--services",
            help="Comma-separated subset of services to scan (e.g. ec2,rds,s3). Default: all.",
        ),
    ] = None,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Write ArchSpec YAML to this file instead of stdout"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Override the architecture name"),
    ] = None,
) -> None:
    """Walk live AWS APIs and produce an ArchSpec from running infrastructure."""
    try:
        provider_norm = (provider or "aws").lower()
        if provider_norm in {"gcp", "google", "azure"}:
            raise typer.BadParameter(
                f"--provider {provider!r} is not yet implemented. Only --provider aws is supported in v1.4."
            )
        if provider_norm != "aws":
            raise typer.BadParameter(f"Unknown --provider {provider!r}. Supported: aws.")

        try:
            from cloudwright.importer.live_aws import (
                SUPPORTED_SERVICES,
                LiveImportError,
                import_live_aws,
            )
        except ImportError as exc:
            # boto3 not installed at all (cloudwright.importer.live_aws import boto3 lazily,
            # but a missing core import surfaces here as a final fallback).
            err_console.print(
                "[red]boto3 is required for live AWS import.[/red] "
                "Install with: pip install 'cloudwright-ai[live-import]'"
            )
            raise typer.Exit(code=1) from exc

        services_list: list[str] | None = None
        if services:
            services_list = [s.strip().lower() for s in services.split(",") if s.strip()]
            unknown = [s for s in services_list if s not in SUPPORTED_SERVICES]
            if unknown:
                raise typer.BadParameter(
                    f"Unknown service(s): {sorted(set(unknown))}. Supported: {list(SUPPORTED_SERVICES)}"
                )

        json_mode = is_json_mode(ctx)

        def _progress(msg: str) -> None:
            if not json_mode:
                err_console.print(msg)

        try:
            spec = import_live_aws(
                region=region,
                profile=profile,
                services=services_list,
                progress=_progress,
                name=name,
            )
        except LiveImportError as exc:
            # Clean error path — credentials missing, profile not found, etc.
            err_console.print(f"[red]error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        if name:
            spec = spec.model_copy(update={"name": name})

        if json_mode:
            emit_success(ctx, {"spec": json.loads(spec.to_json())})
            return

        content = spec.to_yaml()
        n_comps = len(spec.components)
        n_bounds = len(spec.boundaries)

        if output:
            validate_output_path(output)
            Path(output).write_text(content)
            err_console.print()
            err_console.print(
                f"[green]Imported[/green] {n_comps} component(s), {n_bounds} boundary(ies) "
                f"from {region} -> [bold]{output}[/bold]"
            )
            err_console.print(f"Run [bold]cloudwright cost {output}[/bold] to estimate.")
        else:
            sys.stdout.write(content)
            err_console.print()
            err_console.print(f"[green]Imported[/green] {n_comps} component(s), {n_bounds} boundary(ies) from {region}")

    except typer.Exit:
        raise
    except typer.BadParameter:
        raise
    except Exception as e:
        handle_error(ctx, e)
