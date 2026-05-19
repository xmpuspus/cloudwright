from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from cloudwright_cli.output import emit_stream, emit_success, is_json_mode, should_stream
from cloudwright_cli.utils import handle_error

console = Console()

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}


def compliance_scan(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Path to ArchSpec YAML file", exists=True)],
    frameworks: Annotated[
        str | None,
        typer.Option("--frameworks", "-f", help="Comma list: hipaa,soc2,pci-dss,fedramp,gdpr,iso27001,nist"),
    ] = None,
    checkov: Annotated[
        bool | None,
        typer.Option("--checkov/--no-checkov", help="Force or skip the Checkov deep scan (auto-detected by default)"),
    ] = None,
    fail_on: Annotated[str, typer.Option("--fail-on", help="Fail on: critical, high, medium, none")] = "high",
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write a markdown control report")] = None,
) -> None:
    """Scan an ArchSpec and map every finding to framework control IDs.

    Maps design-stage findings to HIPAA / SOC 2 / PCI-DSS / FedRAMP / GDPR /
    ISO 27001 / NIST 800-53 controls before any infrastructure exists. Folds in
    a Checkov deep scan against the exported Terraform when Checkov is on PATH.
    """
    try:
        from cloudwright import ArchSpec
        from cloudwright.compliance import ComplianceScanner, render_markdown

        spec = ArchSpec.from_file(spec_file)
        fw_list = [f for f in (frameworks.split(",") if frameworks else []) if f.strip()]
        report = ComplianceScanner().scan(spec, frameworks=fw_list or None, run_checkov=checkov)

        if output:
            Path(output).write_text(render_markdown(spec, report))

        if is_json_mode(ctx):
            if should_stream(ctx):
                for f in report.findings:
                    emit_stream(f.as_dict())
            else:
                emit_success(ctx, report.as_dict())
            _maybe_exit(report, fail_on)
            return

        console.print(f"\nCompliance Scan: {spec_file.name}  (scanner: {report.scanner})\n")

        posture = Table("Framework", "Satisfied", "Violated controls", "Findings", "Status")
        for s in report.frameworks:
            sat = f"{s.controls_total - len(s.controls_violated)}/{s.controls_total}"
            viol = ", ".join(s.controls_violated) if s.controls_violated else "-"
            style = "green" if s.status == "pass" else "red"
            posture.add_row(s.framework, sat, viol, str(s.findings), f"[{style}]{s.status.upper()}[/{style}]")
        console.print(posture)
        console.print()

        if not report.findings:
            console.print("[green][PASS][/green] No control violations detected.")
        else:
            for f in report.findings:
                sev = f.severity.upper()
                color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow"}.get(sev, "dim")
                console.print(f"  [{color}][{sev}][/{color}] {f.message}  [dim]({f.source})[/dim]")
                if f.controls:
                    ctrl = ", ".join(f"{c.framework} {c.control_id}" for c in f.controls)
                    console.print(f"           Controls: {ctrl}", style="cyan")
                console.print(f"           Remediation: {f.remediation}", style="dim")
                console.print()

        crit = report.critical_count
        high = report.high_count
        console.print(f"{len(report.findings)} finding(s) ({crit} critical, {high} high)")
        threshold = _SEVERITY_ORDER.get(fail_on, 1)
        worst = min((_SEVERITY_ORDER.get(f.severity, 4) for f in report.findings), default=4)
        status = "PASSED" if worst > threshold else "FAILED"
        console.print(f"Status: [{'green' if status == 'PASSED' else 'red'}]{status}[/] (fail-on={fail_on})")
        if output:
            console.print(f"\nReport written to {output}", style="dim")

        _maybe_exit(report, fail_on)

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)


def _maybe_exit(report, fail_on: str) -> None:
    threshold = _SEVERITY_ORDER.get(fail_on, 1)
    for f in report.findings:
        if _SEVERITY_ORDER.get(f.severity, 4) <= threshold:
            raise typer.Exit(1)
