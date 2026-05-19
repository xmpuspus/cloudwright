"""Import live cloud infrastructure into an ArchSpec via provider APIs.

Supports AWS (boto3), GCP (google-cloud SDKs), and Azure (azure-mgmt SDKs):

    cloudwright import-live --provider aws   --region us-east-1
    cloudwright import-live --provider gcp   --project my-project
    cloudwright import-live --provider azure --subscription <SUB_ID>
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
        typer.Option("--provider", help="Cloud provider to scan: aws | gcp | azure"),
    ] = "aws",
    region: Annotated[
        str,
        typer.Option("--region", help="Cloud region (e.g. us-east-1). Recorded in metadata for gcp/azure."),
    ] = "us-east-1",
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="AWS named profile (~/.aws/credentials)"),
    ] = None,
    project: Annotated[
        str | None,
        typer.Option("--project", help="GCP project ID (or set GOOGLE_CLOUD_PROJECT)"),
    ] = None,
    subscription: Annotated[
        str | None,
        typer.Option("--subscription", help="Azure subscription ID (or set AZURE_SUBSCRIPTION_ID)"),
    ] = None,
    services: Annotated[
        str | None,
        typer.Option(
            "--services",
            help="Comma-separated subset of services to scan. Default: all for the provider.",
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
    """Walk live cloud APIs and produce an ArchSpec from running infrastructure."""
    try:
        provider_norm = (provider or "aws").lower()
        if provider_norm == "google":
            provider_norm = "gcp"
        if provider_norm not in {"aws", "gcp", "azure"}:
            raise typer.BadParameter(f"Unknown --provider {provider!r}. Supported: aws, gcp, azure.")

        try:
            from cloudwright.importer.live_aws import LiveImportError
        except ImportError as exc:
            err_console.print(
                "[red]Live import core is unavailable.[/red] Install with: pip install 'cloudwright-ai[live-import]'"
            )
            raise typer.Exit(code=1) from exc

        json_mode = is_json_mode(ctx)

        def _progress(msg: str) -> None:
            if not json_mode:
                err_console.print(msg)

        services_list: list[str] | None = None
        if services:
            services_list = [s.strip().lower() for s in services.split(",") if s.strip()]

        scope_label = region
        try:
            if provider_norm == "aws":
                from cloudwright.importer.live_aws import SUPPORTED_SERVICES, import_live_aws

                _check_services(services_list, SUPPORTED_SERVICES)
                spec = import_live_aws(
                    region=region,
                    profile=profile,
                    services=services_list,
                    progress=_progress,
                    name=name,
                )
                scope_label = region
            elif provider_norm == "gcp":
                from cloudwright.importer.live_gcp import SUPPORTED_SERVICES, import_live_gcp

                _check_services(services_list, SUPPORTED_SERVICES)
                spec = import_live_gcp(
                    project=project,
                    region=region,
                    services=services_list,
                    progress=_progress,
                    name=name,
                )
                scope_label = project or "project"
            else:  # azure
                from cloudwright.importer.live_azure import SUPPORTED_SERVICES, import_live_azure

                _check_services(services_list, SUPPORTED_SERVICES)
                spec = import_live_azure(
                    subscription=subscription,
                    region=region,
                    services=services_list,
                    progress=_progress,
                    name=name,
                )
                scope_label = subscription or "subscription"
        except LiveImportError as exc:
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
                f"from {scope_label} -> [bold]{output}[/bold]"
            )
            err_console.print(f"Run [bold]cloudwright cost {output}[/bold] to estimate.")
        else:
            sys.stdout.write(content)
            err_console.print()
            err_console.print(
                f"[green]Imported[/green] {n_comps} component(s), {n_bounds} boundary(ies) from {scope_label}"
            )

    except typer.Exit:
        raise
    except typer.BadParameter:
        raise
    except Exception as e:
        handle_error(ctx, e)


def _check_services(services_list: list[str] | None, supported: tuple[str, ...]) -> None:
    if not services_list:
        return
    unknown = [s for s in services_list if s not in supported]
    if unknown:
        raise typer.BadParameter(f"Unknown service(s): {sorted(set(unknown))}. Supported: {list(supported)}")
