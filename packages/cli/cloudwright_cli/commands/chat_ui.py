from __future__ import annotations

from cloudwright import ArchSpec
from rich.console import Console
from rich.table import Table

console = Console()

_HELP = """\
Commands:
  /save <file>              Save last architecture to YAML file
  /save-session [name]      Save this conversation session
  /load-session <name>      Load a saved session
  /sessions                 List saved sessions
  /diagram                  Show ASCII diagram for last architecture
  /yaml                     Show YAML for last architecture
  /cost                     Show cost estimate for last architecture
  /validate [fw]            Run compliance check (hipaa, pci-dss, soc2, fedramp, gdpr)
  /export <fmt>             Export last architecture (terraform, pulumi-ts, pulumi-python, mermaid, d2, cloudformation, sbom, aibom)
  /terraform                Export last architecture as Terraform
  /new                      Start a new architecture from scratch
  /help, /?                 Show this help
  /quit                     Exit

Follow-up messages modify the current architecture. Use /new to start over.
"""


def print_diff(diff) -> None:
    if diff.added:
        console.print(f"[green]+ Added: {', '.join(c.id for c in diff.added)}[/green]")
    if diff.removed:
        console.print(f"[red]- Removed: {', '.join(c.id for c in diff.removed)}[/red]")
    if diff.changed:
        console.print(f"[yellow]~ Changed: {', '.join(c.id for c in diff.changed)}[/yellow]")
    if diff.cost_delta is not None and diff.cost_delta != 0:
        sign = "+" if diff.cost_delta > 0 else ""
        console.print(f"[dim]Cost delta: {sign}${diff.cost_delta:,.2f}/mo[/dim]")


def run_validate(spec: ArchSpec, framework: str | None) -> None:
    from cloudwright.validator import Validator

    if framework:
        results = Validator().validate(spec, compliance=[framework])
    else:
        results = Validator().validate(spec, well_architected=True)

    if not results:
        console.print("[yellow]No validation results.[/yellow]")
        return

    for result in results:
        passed = sum(1 for c in result.checks if c.passed)
        total = len(result.checks)
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        console.print(f"{result.framework}: {status}  ({passed}/{total} checks passed)")
        for check in result.checks:
            icon = "[green]+[/green]" if check.passed else "[red]-[/red]"
            console.print(f"  {icon} {check.name}")
            if not check.passed and check.recommendation:
                console.print(f"    [dim]{check.recommendation}[/dim]")


def print_cost_summary(spec: ArchSpec) -> None:
    table = Table(title="Cost Estimate", show_footer=True)
    table.add_column("Component", style="cyan")
    table.add_column("Monthly", justify="right", footer=f"${spec.cost_estimate.monthly_total:,.2f}")
    table.add_column("Notes", style="dim")

    for item in spec.cost_estimate.breakdown:
        table.add_row(item.component_id, f"${item.monthly:,.2f}", item.notes)

    console.print(table)
