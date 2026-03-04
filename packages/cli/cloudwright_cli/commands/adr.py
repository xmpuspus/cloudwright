from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from cloudwright_cli.utils import handle_error

console = Console()

_ADR_SYSTEM = """You generate Architecture Decision Records (ADRs) in MADR format.

Given an architecture spec as JSON, produce a markdown ADR with this exact structure:

# ADR: {name} — {key decision}

## Status
Proposed

## Context
{problem and why a decision is needed}

## Decision
{the chosen architecture and key choices}

## Components
| ID | Service | Provider | Purpose |
|---|---|---|---|
{component rows}

## Consequences
### Positive
- {benefits}

### Negative
- {trade-offs and risks}

## Alternatives Considered
{alternatives if any, otherwise note none documented}

## Cost Estimate
{monthly cost if available, otherwise omit}

Be concise. Focus on the WHY, not just what the architecture contains.
Respond with ONLY the markdown — no explanation, no code fences."""


def adr(
    ctx: typer.Context,
    spec_file: Annotated[Path, typer.Argument(help="Path to ArchSpec YAML file", exists=True)],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write ADR to this file")] = None,
    title: Annotated[str | None, typer.Option("--title", help="ADR title (default: auto-generated)")] = None,
    decision: Annotated[str | None, typer.Option("--decision", help="Specific decision to document")] = None,
) -> None:
    """Generate an Architecture Decision Record from an ArchSpec."""
    try:
        from cloudwright import ArchSpec

        spec = ArchSpec.from_file(spec_file)
        text = _generate_adr(spec, title=title, decision=decision)

        if output:
            Path(output).write_text(text)
            console.print(f"[green]ADR written to {output}[/green]")
        else:
            print(text)

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)


def _generate_adr(spec, *, title: str | None = None, decision: str | None = None) -> str:
    try:
        return _llm_adr(spec, title=title, decision=decision)
    except Exception:
        return _deterministic_adr(spec, title=title, decision=decision)


def _llm_adr(spec, *, title: str | None, decision: str | None) -> str:
    from cloudwright.architect import Architect

    arch = Architect()
    spec_summary = spec.model_dump_json(indent=2, exclude_none=True)

    decision_hint = f"\nDocument this specific decision: {decision}" if decision else ""
    title_hint = f"\nUse this ADR title: {title}" if title else ""
    prompt = f"Generate an ADR for this architecture:{title_hint}{decision_hint}\n\n{spec_summary}"

    text, _ = arch.llm.generate([{"role": "user", "content": prompt}], _ADR_SYSTEM, max_tokens=2000)
    if not text.strip().startswith("#"):
        raise ValueError("LLM did not return markdown ADR")
    return text.strip()


def _deterministic_adr(spec, *, title: str | None = None, decision: str | None = None) -> str:
    adr_title = title or spec.name
    key_decision = decision or _infer_key_decision(spec)

    lines = [
        f"# ADR: {adr_title} — {key_decision}",
        "",
        "## Status",
        "Proposed",
        "",
        "## Context",
        _build_context(spec),
        "",
        "## Decision",
        _build_decision(spec),
        "",
        "## Components",
        "| ID | Service | Provider | Purpose |",
        "|---|---|---|---|",
    ]

    for c in spec.components:
        purpose = c.description or c.label
        lines.append(f"| {c.id} | {c.service} | {c.provider} | {purpose} |")

    lines += ["", "## Consequences"]
    lines += _build_consequences(spec)

    rationale = spec.metadata.get("rationale") or []
    if rationale:
        lines += ["", "## Alternatives Considered"]
        for r in rationale:
            if isinstance(r, dict):
                lines.append(f"- **{r.get('decision', '')}**: {r.get('reason', '')}")

    if spec.cost_estimate:
        lines += [
            "",
            "## Cost Estimate",
            f"Estimated monthly cost: ${spec.cost_estimate.monthly_total:,.2f} USD",
        ]

    return "\n".join(lines)


def _infer_key_decision(spec) -> str:
    rationale = spec.metadata.get("rationale") or []
    if rationale and isinstance(rationale[0], dict):
        return rationale[0].get("decision", f"{spec.provider.upper()} architecture")
    return f"{spec.provider.upper()} architecture"


def _build_context(spec) -> str:
    parts = [f"This architecture, {spec.name!r}, targets the {spec.provider.upper()} platform in region {spec.region}."]
    if spec.constraints:
        if spec.constraints.compliance:
            parts.append(f"Compliance requirements: {', '.join(spec.constraints.compliance)}.")
        if spec.constraints.budget_monthly:
            parts.append(f"Monthly budget constraint: ${spec.constraints.budget_monthly:,.0f}.")
    parts.append(f"It consists of {len(spec.components)} components across {len(spec.connections)} connections.")
    return " ".join(parts)


def _build_decision(spec) -> str:
    rationale = spec.metadata.get("rationale") or []
    if rationale:
        items = []
        for r in rationale:
            if isinstance(r, dict):
                items.append(f"- **{r.get('decision', '')}**: {r.get('reason', '')}")
        if items:
            return "\n".join(items)

    services = ", ".join(c.service for c in spec.components[:5])
    suffix = ", ..." if len(spec.components) > 5 else ""
    return f"Selected architecture using: {services}{suffix}."


def _build_consequences(spec) -> list[str]:
    lines = ["### Positive"]
    suggestions = spec.metadata.get("suggestions") or []

    positives = [
        f"Established {spec.provider.upper()} native services reduce operational overhead.",
        f"{len(spec.components)} components provide clear separation of concerns.",
    ]
    lines += [f"- {p}" for p in positives]

    lines += ["", "### Negative"]
    negatives = ["Vendor lock-in to selected provider and service tier."]
    if suggestions:
        negatives.append("Additional configuration required: " + suggestions[0].lower() + ".")
    lines += [f"- {n}" for n in negatives]

    return lines
