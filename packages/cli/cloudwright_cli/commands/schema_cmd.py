"""Schema introspection — explore service configs, pricing, and compliance."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cloudwright_cli.output import emit_error, emit_success, is_json_mode

console = Console()


def schema(
    ctx: typer.Context,
    query: Annotated[
        str,
        typer.Argument(help="Service (aws.ec2, gcp.cloud_sql) or compliance framework (hipaa, soc2)"),
    ],
) -> None:
    """Show service config fields, pricing, regions, or compliance checks."""
    try:
        if "." in query:
            _show_service(ctx, query)
        else:
            _show_compliance(ctx, query)
    except typer.Exit:
        raise
    except Exception as e:
        emit_error(ctx, e, code="schema_lookup_failed")


def _show_service(ctx: typer.Context, query: str) -> None:
    from cloudwright.registry import get_registry

    parts = query.split(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Expected provider.service format, got: {query}")

    provider, service_key = parts
    registry = get_registry()
    svc_def = registry.get(provider, service_key)

    if not svc_def:
        available = [s.service_key for s in registry.list_services(provider)[:15]]
        raise ValueError(
            f"Service '{service_key}' not found for provider '{provider}'. "
            f"Available: {', '.join(available)}"
        )

    equivalents = {}
    for target_provider in ("aws", "gcp", "azure", "databricks"):
        if target_provider != provider:
            eq = registry.get_equivalent(service_key, provider, target_provider)
            if eq:
                equivalents[target_provider] = eq

    parity = registry.get_feature_parity(service_key)

    data = {
        "service_key": svc_def.service_key,
        "provider": svc_def.provider,
        "name": svc_def.name,
        "category": svc_def.category,
        "description": svc_def.description,
        "pricing_formula": svc_def.pricing_formula,
        "default_config": svc_def.default_config,
        "equivalents": equivalents,
        "feature_parity": parity,
    }

    if is_json_mode(ctx):
        emit_success(ctx, data)
        return

    console.print(
        Panel(
            f"[bold]{svc_def.name}[/bold] ({provider}.{service_key})\n"
            f"Category: {svc_def.category}  |  Pricing: {svc_def.pricing_formula}\n"
            f"{svc_def.description}" if svc_def.description else "",
            title="Service Schema",
        )
    )

    if svc_def.default_config:
        table = Table(title="Default Configuration")
        table.add_column("Field", style="cyan")
        table.add_column("Default Value")
        for k, v in svc_def.default_config.items():
            table.add_row(k, str(v))
        console.print(table)

    if equivalents:
        console.print("\n[bold]Cross-Cloud Equivalents[/bold]")
        for p, eq in equivalents.items():
            console.print(f"  {p}: {eq}")

    if parity:
        ft = Table(title="Feature Parity")
        ft.add_column("Feature", style="cyan")
        for p in ("aws", "gcp", "azure"):
            ft.add_column(p.upper(), justify="center")
        for feature, support in parity.items():
            row = [feature]
            for p in ("aws", "gcp", "azure"):
                val = support.get(p)
                if val is True:
                    row.append("[green]yes[/green]")
                elif val is False:
                    row.append("[red]no[/red]")
                elif val is not None:
                    row.append(str(val))
                else:
                    row.append("-")
            ft.add_row(*row)
        console.print(ft)

    gaps = registry.feature_gaps(service_key, provider)
    if gaps:
        console.print(f"\n[yellow]Feature gaps for {provider}:[/yellow] {', '.join(gaps)}")


def _show_compliance(ctx: typer.Context, framework: str) -> None:
    from cloudwright.spec import ArchSpec, Component
    from cloudwright.validator import Validator

    known = {"hipaa", "pci-dss", "soc2", "fedramp", "gdpr", "well-architected"}
    if framework.lower() not in known:
        raise ValueError(f"Unknown framework: {framework}. Available: {', '.join(sorted(known))}")

    dummy = ArchSpec(
        name="schema_introspection",
        components=[Component(id="dummy", service="ec2", provider="aws", label="Dummy")],
    )

    wa = framework.lower() == "well-architected"
    compliance_list = [] if wa else [framework]
    results = Validator().validate(dummy, compliance_list, well_architected=wa)

    if not results:
        raise ValueError(f"No checks available for framework: {framework}")

    result = results[0]
    data = {
        "framework": result.framework,
        "total_checks": len(result.checks),
        "checks": [
            {"name": c.name, "category": c.category, "severity": c.severity}
            for c in result.checks
        ],
    }

    if is_json_mode(ctx):
        emit_success(ctx, data)
        return

    console.print(
        Panel(
            f"[bold]{framework.upper()}[/bold] -- {len(result.checks)} checks",
            title="Compliance Framework",
        )
    )

    by_category: dict[str, list] = {}
    for c in result.checks:
        by_category.setdefault(c.category, []).append(c)

    for category, checks in sorted(by_category.items()):
        table = Table(title=category)
        table.add_column("Check", style="cyan")
        table.add_column("Severity")
        for c in checks:
            sev_style = {"critical": "bold red", "high": "red", "medium": "yellow"}.get(c.severity, "dim")
            table.add_row(c.name, f"[{sev_style}]{c.severity}[/{sev_style}]")
        console.print(table)
