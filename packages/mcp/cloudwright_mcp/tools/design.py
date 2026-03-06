from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def design_architecture(
        description: str,
        provider: str = "aws",
        region: str = "us-east-1",
        budget_monthly: float | None = None,
        compliance: list[str] | None = None,
    ) -> dict:
        """Design a cloud architecture from a natural language description."""
        from cloudwright.architect import Architect
        from cloudwright.cost import CostEngine
        from cloudwright.spec import Constraints

        constraints = Constraints(regions=[region], budget_monthly=budget_monthly, compliance=compliance or [])
        spec = Architect().design(description, constraints=constraints)
        if not spec.cost_estimate:
            spec = spec.model_copy(update={"cost_estimate": CostEngine().estimate(spec)})
        return spec.model_dump(exclude_none=True)

    @mcp.tool()
    def modify_architecture(spec_json: dict, instruction: str) -> dict:
        """Modify an existing architecture with a natural language instruction."""
        from cloudwright.architect import Architect
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        modified = Architect().modify(spec, instruction)
        return modified.model_dump(exclude_none=True)

    @mcp.tool()
    def compare_providers(spec_json: dict, providers: list[str]) -> list[dict]:
        """Compare an architecture across cloud providers."""
        from cloudwright.architect import Architect
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        alternatives = Architect().compare(spec, providers)
        return [a.model_dump(exclude_none=True) for a in alternatives]
