from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def estimate_cost(spec_json: dict, pricing_tier: str = "on_demand") -> dict:
        """Estimate monthly cost for an architecture spec."""
        from cloudwright.cost import CostEngine
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        estimate = CostEngine().estimate(spec, pricing_tier=pricing_tier)
        return estimate.model_dump(exclude_none=True)

    @mcp.tool()
    def compare_provider_costs(spec_json: dict, providers: list[str]) -> list[dict]:
        """Compare costs for an architecture across cloud providers."""
        from cloudwright.cost import CostEngine
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        comparisons = CostEngine().compare_providers(spec, providers)
        return [c.model_dump(exclude_none=True) for c in comparisons]
