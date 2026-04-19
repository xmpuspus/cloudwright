from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def export_architecture(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to export. Components are translated to provider-native "
                    "resources; connections become security-group / firewall / IAM rules."
                ),
            ),
        ],
        format: Annotated[
            str,
            Field(
                description=(
                    "Target output format. "
                    "Values: 'terraform' (HCL with provider blocks, 24 AWS / 11 GCP / 10 "
                    "Azure resource types), 'cloudformation' (YAML template with "
                    "Parameters/Outputs), 'mermaid' (tier-grouped flowchart), "
                    "'d2' (D2 diagram), 'sbom' (CycloneDX 1.5 service bill of materials), "
                    "'aibom' (OWASP AI bill of materials), 'compliance' (audit-ready "
                    "markdown report)."
                ),
                examples=["terraform", "cloudformation", "mermaid", "d2", "sbom"],
            ),
        ] = "terraform",
    ) -> dict:
        """Export an architecture spec to Terraform, CloudFormation, Mermaid, D2, or other formats.

        Returns `{'format': str, 'content': str}` where `content` is the
        ready-to-write payload. Terraform/CFN outputs use variables for sensitive
        values (no hardcoded credentials), include provider blocks with region
        configuration, and generate data sources for VPC/subnet discovery.

        When to use: You have a finalized ArchSpec and need IaC code, a diagram,
        or an audit artifact. For multi-format export, call once per `format`.

        Behavior: Pure computation — no LLM, no network. Does not write files or
        deploy; the caller is responsible for persisting or applying the returned
        content.
        """
        from cloudwright.exporter import export_spec
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        content = export_spec(spec, fmt=format)
        return {"format": format, "content": content}

    @mcp.tool()
    def list_services(
        provider: Annotated[
            str,
            Field(
                description=(
                    "Cloud provider slug. Values: 'aws' (47 services), 'gcp' (25), "
                    "'azure' (28), 'databricks'."
                ),
                examples=["aws", "gcp", "azure", "databricks"],
            ),
        ] = "aws",
    ) -> list[dict]:
        """List all cloud services supported for a given provider.

        Returns one entry per service with its slug, human-readable name, category
        (compute / database / storage / networking / etc.), and supported tiers.
        Use this to discover valid `service:` keys when hand-authoring ArchSpecs
        or mapping requirements to services.

        Behavior: Pure lookup from the bundled service registry — no LLM, no
        network, no cloud access.
        """
        from cloudwright.registry import ServiceRegistry

        services = ServiceRegistry().list_services(provider)
        return [s.to_dict() for s in services]

    @mcp.tool()
    def catalog_search(
        provider: Annotated[
            str,
            Field(
                description="Cloud provider slug to search within. Default 'aws'.",
                examples=["aws", "gcp", "azure"],
            ),
        ] = "aws",
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Optional free-text query matching instance family, generation, or purpose "
                    "(e.g. 'memory-optimized', 'graviton', 'gpu')."
                ),
                examples=["memory-optimized", "graviton", "gpu"],
            ),
        ] = None,
        vcpus: Annotated[
            int | None,
            Field(
                description="Optional exact vCPU count filter. Returns instances matching this vCPU count.",
                examples=[4, 8, 16, 32],
            ),
        ] = None,
        memory_gb: Annotated[
            float | None,
            Field(
                description="Optional exact memory-in-GB filter. Returns instances matching this memory size.",
                examples=[8, 16, 32, 64],
            ),
        ] = None,
        max_price_per_hour: Annotated[
            float | None,
            Field(
                description=(
                    "Optional maximum hourly on-demand price (USD). Returns only instances "
                    "at or below this price. Useful for budget-constrained sizing."
                ),
                examples=[0.10, 0.50, 2.00],
            ),
        ] = None,
    ) -> list[dict]:
        """Search the cloud instance catalog by provider, specs, or text query.

        Returns matching instance types with instance family, vCPU / memory /
        storage, hourly on-demand price, region availability, and architecture
        (x86 / arm). All filters combine with AND semantics.

        When to use: Right-sizing workloads, finding the cheapest instance that
        meets a hardware bar, or discovering equivalents across families.

        Behavior: Pure lookup from the bundled SQLite catalog — no LLM, no
        network. Prices reflect catalog snapshot date (see `refresh` CLI command
        to update).
        """
        from cloudwright.catalog import Catalog

        return Catalog().search(
            query=query,
            provider=provider,
            vcpus=vcpus,
            memory_gb=memory_gb,
            max_price_per_hour=max_price_per_hour,
        )
