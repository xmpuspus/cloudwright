from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def export_architecture(spec_json: dict, format: str = "terraform") -> dict:
        """Export an architecture spec to Terraform, CloudFormation, Mermaid, D2, or other formats."""
        from cloudwright.exporter import export_spec
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        content = export_spec(spec, fmt=format)
        return {"format": format, "content": content}

    @mcp.tool()
    def list_services(provider: str = "aws") -> list[dict]:
        """List all cloud services for a provider from the service registry."""
        from cloudwright.registry import ServiceRegistry

        services = ServiceRegistry().list_services(provider)
        return [s.to_dict() for s in services]

    @mcp.tool()
    def catalog_search(
        provider: str = "aws",
        query: str | None = None,
        vcpus: int | None = None,
        memory_gb: float | None = None,
        max_price_per_hour: float | None = None,
    ) -> list[dict]:
        """Search the cloud instance catalog by provider, specs, or text query."""
        from cloudwright.catalog import Catalog

        return Catalog().search(
            query=query,
            provider=provider,
            vcpus=vcpus,
            memory_gb=memory_gb,
            max_price_per_hour=max_price_per_hour,
        )
