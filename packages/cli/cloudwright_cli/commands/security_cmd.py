from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from cloudwright_cli.utils import handle_error

console = Console()

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}


def security_scan(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Path to ArchSpec YAML file", exists=True)],
    fail_on: Annotated[str, typer.Option("--fail-on", help="Fail on: critical, high, medium, none")] = "high",
    output: Annotated[str | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Scan an ArchSpec for security anti-patterns and misconfigurations."""
    try:
        from cloudwright import ArchSpec
        from cloudwright.security import SecurityScanner

        spec = ArchSpec.from_file(spec_file)
        report = SecurityScanner().scan(spec)

        if ctx.obj and ctx.obj.get("json"):
            result = {
                "passed": report.passed,
                "findings": [
                    {
                        "severity": f.severity,
                        "rule": f.rule,
                        "component_id": f.component_id,
                        "message": f.message,
                        "remediation": f.remediation,
                    }
                    for f in report.findings
                ],
            }
            print(json.dumps(result, indent=2))
            _maybe_exit(report, fail_on)
            return

        console.print(f"\nSecurity Scan: {spec_file.name}\n")

        if not report.findings:
            console.print("[green][PASS][/green] No security findings detected.")
        else:
            for f in report.findings:
                sev_upper = f.severity.upper()
                if f.severity == "critical":
                    sev_text = Text(f"[{sev_upper}]", style="bold red")
                elif f.severity == "high":
                    sev_text = Text(f"[{sev_upper}]", style="red")
                elif f.severity == "medium":
                    sev_text = Text(f"[{sev_upper}]", style="yellow")
                else:
                    sev_text = Text(f"[{sev_upper}]", style="dim")

                line = Text("  ")
                line.append_text(sev_text)
                line.append(f" {f.message}")
                console.print(line)
                console.print(f"           Remediation: {f.remediation}", style="dim")
                console.print()

        total = len(report.findings)
        crit = report.critical_count
        high = report.high_count
        med = sum(1 for f in report.findings if f.severity == "medium")

        console.print(f"{total} finding(s) ({crit} critical, {high} high, {med} medium)")

        threshold = _SEVERITY_ORDER.get(fail_on, 1)
        worst = min((_SEVERITY_ORDER.get(f.severity, 4) for f in report.findings), default=4)
        status = "PASSED" if worst > threshold else "FAILED"
        style = "green" if status == "PASSED" else "red"
        console.print(f"Status: [{style}]{status}[/{style}] (fail-on={fail_on})")

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
