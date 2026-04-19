from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def estimate_cost(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to price. Pricing is resolved per-component against a "
                    "bundled SQLite catalog (no network calls), with formula dispatch "
                    "for serverless/managed services and a static fallback for rare ones."
                ),
            ),
        ],
        pricing_tier: Annotated[
            str,
            Field(
                description=(
                    "Pricing tier multiplier applied to compute and data-store components. "
                    "Values: 'on_demand' (1.0x), 'reserved_1yr' (0.6x), "
                    "'reserved_3yr' (0.4x), 'spot' (0.3x)."
                ),
                examples=["on_demand", "reserved_1yr", "reserved_3yr", "spot"],
            ),
        ] = "on_demand",
    ) -> dict:
        """Estimate the monthly cloud bill for an architecture spec.

        Returns a structured estimate with per-component breakdown, total
        monthly cost, data-transfer costs, and currency. Deterministic: same
        spec + tier yields same result.

        When to use: You need the numeric bill for one architecture on one
        provider+tier combination. For multi-provider comparison of just the
        costs, use `compare_provider_costs`. For side-by-side architecture +
        cost comparison across providers, use `compare_providers` + this tool.

        Behavior: Pure computation — no LLM, no network, no API costs. Works
        offline. Does not deploy or touch cloud resources.
        """
        from cloudwright.cost import CostEngine
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        estimate = CostEngine().estimate(spec, pricing_tier=pricing_tier)
        return estimate.model_dump(exclude_none=True)

    @mcp.tool()
    def compare_provider_costs(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to cost across providers. Services are mapped to cross-cloud "
                    "equivalents (ec2 <-> compute_engine <-> virtual_machines, etc.) before pricing."
                ),
            ),
        ],
        providers: Annotated[
            list[str],
            Field(
                description=(
                    "List of cloud providers to compare pricing across. "
                    "Values: 'aws', 'gcp', 'azure', 'databricks'."
                ),
                examples=[["aws", "gcp", "azure"], ["aws", "gcp"]],
            ),
        ],
    ) -> list[dict]:
        """Compare the monthly **cost totals** of an architecture across cloud providers.

        Returns one numeric cost summary per provider (monthly total, per-component
        breakdown, currency). Use this for cost-focused provider selection.

        When to use vs `compare_providers`: This tool returns only **cost numbers**.
        `compare_providers` returns full alternative **architectures** (components,
        connections, tiers). If you want both the re-drawn architecture and its
        bill, call `compare_providers` first, then `estimate_cost` on each returned
        spec — or call both in parallel.

        Behavior: Pure computation — no LLM, no network, no API costs. Uses the
        same offline catalog as `estimate_cost`. Does not deploy.
        """
        from cloudwright.cost import CostEngine
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        comparisons = CostEngine().compare_providers(spec, providers)
        return [c.model_dump(exclude_none=True) for c in comparisons]
