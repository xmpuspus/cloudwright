from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def analyze_blast_radius(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to analyze. Builds a directed dependency graph from the "
                    "spec's connections and computes reachability per component."
                ),
            ),
        ],
        component_id: Annotated[
            str | None,
            Field(
                description=(
                    "Optional: focus analysis on a single component's blast radius "
                    "(its direct dependents + transitive dependents). When omitted, "
                    "returns blast-radius metrics for every component."
                ),
                examples=["api_gateway", "rds_primary", None],
            ),
        ] = None,
    ) -> dict:
        """Analyze blast radius and dependency structure of an architecture.

        For each component (or just one, if `component_id` is set): returns direct
        dependents, transitive dependents, blast-radius size, SPOF status, and
        tier position. Use this to reason about failure modes — 'if component X
        dies, what else breaks?'

        When to use: You have a spec and want to understand coupling and failure
        domains before production. Complementary to `score_architecture` (which
        gives a summary grade) and `lint_architecture` (which flags specific
        anti-patterns).

        Behavior: Pure graph computation — no LLM, no network. Read-only. Does
        not touch cloud resources.
        """
        from cloudwright.analyzer import Analyzer
        from cloudwright.spec import ArchSpec

        from cloudwright_mcp.serializers import analysis_result_to_dict

        spec = ArchSpec.model_validate(spec_json)
        result = Analyzer().analyze(spec, component_id=component_id)
        return analysis_result_to_dict(result)

    @mcp.tool()
    def score_architecture(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to score. Scorer evaluates across five weighted dimensions "
                    "and returns an overall 0-100 score with a letter grade (A/B/C/D/F)."
                ),
            ),
        ],
    ) -> dict:
        """Score an architecture across reliability, security, cost, compliance, and complexity.

        Returns the dimension scores, overall weighted score (0-100), letter
        grade, and per-dimension notes. Weights: Reliability 30% (load balancing,
        multi-AZ, auto-scaling, CDN, caching), Security 25% (WAF, auth,
        encryption, HTTPS, DNS), Cost Efficiency 20% (budget compliance, free-
        tier usage), Compliance 15% (framework validation), Complexity 10%
        (component count, connection density, tier separation).

        When to use: You want a quick quality summary before a design review.
        For specific findings, use `lint_architecture`, `security_scan`, or
        `validate_compliance`.

        Behavior: Pure computation — no LLM, no network. Read-only.
        """
        from cloudwright.scorer import Scorer
        from cloudwright.spec import ArchSpec

        from cloudwright_mcp.serializers import score_result_to_dict

        spec = ArchSpec.model_validate(spec_json)
        result = Scorer().score(spec)
        return score_result_to_dict(result)

    @mcp.tool()
    def diff_architectures(
        old_spec_json: Annotated[
            dict,
            Field(
                description="Previous ArchSpec (baseline). Typically the last deployed version.",
            ),
        ],
        new_spec_json: Annotated[
            dict,
            Field(
                description="Proposed ArchSpec (target). Typically the version about to be deployed.",
            ),
        ],
    ) -> dict:
        """Diff two architecture specs and return a structured change report.

        Returns a structured delta: components added / removed / modified,
        connections added / removed / modified, cost delta (USD/month),
        compliance-impact flags (e.g. WAF removal, encryption-at-rest turned off),
        and a human-readable summary.

        When to use: You have two versions of a spec (before / after a proposed
        change) and need a reviewable diff for approval or ADR writing.

        Behavior: Pure computation — no LLM, no network. Read-only. Does not
        modify either spec.
        """
        from cloudwright.differ import Differ
        from cloudwright.spec import ArchSpec

        old = ArchSpec.model_validate(old_spec_json)
        new = ArchSpec.model_validate(new_spec_json)
        result = Differ().diff(old, new)
        return result.model_dump(exclude_none=True)
