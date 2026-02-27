from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.rule import Rule
from rich.text import Text
from silmaril import ArchSpec, Validator

console = Console()


def validate(
    spec_file: Annotated[Path, typer.Argument(help="Path to spec YAML file", exists=True)],
    compliance: Annotated[
        str | None, typer.Option(help="Comma-separated compliance frameworks (hipaa, pci-dss, soc2)")
    ] = None,
    well_architected: Annotated[bool, typer.Option("--well-architected", help="Run well-architected review")] = False,
) -> None:
    """Validate an architecture spec against compliance frameworks or well-architected principles."""
    if not compliance and not well_architected:
        console.print("[yellow]Specify --compliance and/or --well-architected.[/yellow]")
        raise typer.Exit(1)

    spec = ArchSpec.from_file(spec_file)
    frameworks: list[str] = []

    if compliance:
        frameworks.extend(f.strip() for f in compliance.split(",") if f.strip())
    if well_architected:
        frameworks.append("well-architected")

    with console.status("Running validation..."):
        results = Validator().validate(spec, frameworks)

    any_failed = False
    for result in results:
        title = _framework_title(result.framework)
        console.print(Rule(f"[bold]{title}[/bold]"))

        passed_count = sum(1 for c in result.checks if c.passed)
        total = len(result.checks)

        for check in result.checks:
            status = Text("[PASS]", style="green") if check.passed else Text("[FAIL]", style="red")
            line = Text()
            line.append_text(status)
            line.append(f" {check.name}")
            if check.detail:
                line.append(f" — {check.detail}", style="dim")
            console.print(line)

            if not check.passed and check.recommendation:
                console.print(f"       [dim]Recommendation: {check.recommendation}[/dim]")
                any_failed = True

        pct = int(result.score * 100) if result.score <= 1 else int(result.score)
        console.print(f"Score: {passed_count}/{total} ({pct}%)\n")

    if any_failed:
        raise typer.Exit(1)


def _framework_title(framework: str) -> str:
    titles = {
        "hipaa": "HIPAA Compliance Review",
        "pci-dss": "PCI-DSS Compliance Review",
        "soc2": "SOC 2 Compliance Review",
        "well-architected": "Well-Architected Review",
    }
    return titles.get(framework.lower(), f"{framework.upper()} Review")
