"""Initialize a new ArchSpec from a template."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

from cloudwright_cli.utils import handle_error

console = Console()

try:
    from importlib.resources import files as _pkg_files

    _TEMPLATES_DIR = Path(str(_pkg_files("cloudwright") / "data" / "templates"))
except Exception:
    _TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "catalog" / "templates"


def init(
    ctx: typer.Context,
    template: Annotated[str | None, typer.Option("--template", "-t", help="Template name")] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")] = "spec.yaml",
    list_templates: Annotated[bool, typer.Option("--list", "-l", help="List available templates")] = False,
    provider: Annotated[str | None, typer.Option(help="Override provider (aws, gcp, azure)")] = None,
    region: Annotated[str | None, typer.Option(help="Override region")] = None,
    name: Annotated[str | None, typer.Option(help="Override architecture name")] = None,
    compliance: Annotated[
        str | None, typer.Option(help="Comma-separated compliance frameworks (hipaa, pci-dss, soc2, fedramp, gdpr)")
    ] = None,
    budget: Annotated[float | None, typer.Option(help="Monthly budget in USD")] = None,
    project: Annotated[bool, typer.Option("--project", "-p", help="Create a .cloudwright/ project directory")] = False,
) -> None:
    """Initialize a new ArchSpec from a template."""
    try:
        index_path = _TEMPLATES_DIR / "_index.yaml"
        if not index_path.exists():
            console.print("[red]Error:[/red] Template index not found.")
            raise typer.Exit(1)

        index = yaml.safe_load(index_path.read_text())
        templates = index.get("templates", {})

        if list_templates:
            table = Table(title="Available Templates")
            table.add_column("Name", style="cyan")
            table.add_column("Description")
            table.add_column("Provider")
            table.add_column("Complexity")
            table.add_column("Tags")

            for key, tmpl in templates.items():
                table.add_row(
                    key,
                    tmpl.get("description", ""),
                    tmpl.get("provider", ""),
                    tmpl.get("complexity", ""),
                    ", ".join(tmpl.get("tags", [])),
                )
            console.print(table)
            return

        if not template:
            console.print("[red]Error:[/red] Specify a template with --template <name>, or use --list to see options.")
            raise typer.Exit(1)

        if template not in templates:
            console.print(f"[red]Error:[/red] Unknown template '{template}'. Use --list to see available templates.")
            raise typer.Exit(1)

        tmpl_info = templates[template]
        tmpl_file = _TEMPLATES_DIR / tmpl_info["file"]

        if not tmpl_file.exists():
            console.print(f"[red]Error:[/red] Template file not found: {tmpl_info['file']}")
            raise typer.Exit(1)

        spec_data = yaml.safe_load(tmpl_file.read_text())

        if name:
            spec_data["name"] = name
        if provider:
            spec_data["provider"] = provider
            for comp in spec_data.get("components", []):
                comp["provider"] = provider
        if region:
            spec_data["region"] = region

        if compliance:
            if "constraints" not in spec_data:
                spec_data["constraints"] = {}
            spec_data["constraints"]["compliance"] = [c.strip() for c in compliance.split(",")]

        if budget is not None:
            if "constraints" not in spec_data:
                spec_data["constraints"] = {}
            spec_data["constraints"]["budget_monthly"] = budget

        if project:
            proj_dir = Path(".cloudwright")
            proj_dir.mkdir(exist_ok=True)
            output_path = proj_dir / "spec.yaml"
            config = {
                "version": 1,
                "default_provider": spec_data.get("provider", "aws"),
                "default_region": spec_data.get("region", "us-east-1"),
                "compliance": [c.strip() for c in compliance.split(",")] if compliance else [],
                "budget_monthly": budget,
            }
            config = {k: v for k, v in config.items() if v is not None}
            (proj_dir / "config.yaml").write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))
        else:
            output_path = Path(output)

        output_path.write_text(yaml.dump(spec_data, default_flow_style=False, sort_keys=False, allow_unicode=True))

        console.print(f"[green]Created {output_path}[/green] from template '{template}'")
        console.print(f"  Provider: {spec_data.get('provider', 'aws')}")
        console.print(f"  Components: {len(spec_data.get('components', []))}")
        if project:
            console.print(f"  Config: {proj_dir / 'config.yaml'}")
        console.print("\nNext steps:")
        console.print(f"  cloudwright cost {output_path}")
        console.print(f"  cloudwright validate {output_path}")
        console.print(f"  cloudwright export {output_path} --format terraform -o ./infra")

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)
