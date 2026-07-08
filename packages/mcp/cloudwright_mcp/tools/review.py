from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def review_architecture(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to review. The critic runs the scorer, linter, and validator "
                    "against the declared components, connections, and constraints. No "
                    "cloud API access required."
                ),
            ),
        ],
        compliance: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional compliance frameworks to fold validator findings from. When "
                    "omitted, uses `spec.constraints.compliance` if set, otherwise runs no "
                    "framework checks. Values: 'hipaa', 'pci-dss', 'soc2', 'fedramp', 'gdpr'."
                ),
                examples=[["hipaa"], ["soc2", "gdpr"], None],
            ),
        ] = None,
        well_architected: Annotated[
            bool,
            Field(
                description=(
                    "When True, additionally runs the AWS Well-Architected Framework pillar "
                    "checks (multi-AZ, auto-scaling, backup, monitoring, SPOF, cost)."
                ),
            ),
        ] = False,
    ) -> dict:
        """Run the deterministic offline critic (scorer + linter + validator) on an architecture.

        This is the same generate -> critique -> repair engine `Architect.design()` uses
        internally to self-correct a spec before returning it, exposed standalone so an
        agent can review any spec (hand-authored, imported, or previously designed) for
        free, with no LLM call.

        Returns `{'score': float, 'grade': str, 'findings': [...], 'blocking_count': int,
        'summary': str}`. Findings are severity-ranked (critical/high first) and each
        carries `source` ('scorer' | 'linter' | 'validator'), `code`, `message`,
        `recommendation`, and an optional `component` id. `blocking_count` counts
        critical + high findings; a non-zero count means the architecture should not
        ship as-is.

        When to use: A quick, free, structured review of any spec, before deploying,
        after a `modify_architecture` edit, or auditing an imported/hand-written spec.
        For a numeric-only quality score use `score_architecture`; for anti-pattern
        detail alone use `lint_architecture` or `security_scan`. This tool merges all
        three plus compliance checks into one severity-ranked report.

        Behavior: Pure computation, no LLM, no network, no API key required. Read-only.
        Invalid or empty `spec_json` returns `{'error': str}` instead of raising.
        """
        from cloudwright.critique import critique
        from cloudwright.spec import ArchSpec

        try:
            spec = ArchSpec.model_validate(spec_json)
        except Exception as exc:
            return {"error": f"Invalid spec: {exc}"}

        report = critique(spec, compliance=compliance, well_architected=well_architected)
        return report.as_dict()
