from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def design_architecture(
        description: Annotated[
            str,
            Field(
                description=(
                    "Plain-English description of the system to design. "
                    "Include workload type (e.g. 'HIPAA-compliant 3-tier healthcare API'), "
                    "traffic expectations, and any stack preferences. The LLM uses this to "
                    "select services, tiers, and connections."
                ),
                examples=[
                    "HIPAA-compliant 3-tier web app on AWS with PostgreSQL",
                    "Serverless data pipeline on GCP with Pub/Sub, Dataflow, and BigQuery",
                ],
            ),
        ],
        provider: Annotated[
            str,
            Field(
                description=(
                    "Target cloud provider for the generated architecture. "
                    "Values: 'aws', 'gcp', 'azure', 'databricks'. Default 'aws'."
                ),
                examples=["aws", "gcp", "azure", "databricks"],
            ),
        ] = "aws",
        region: Annotated[
            str,
            Field(
                description=(
                    "Cloud region for the generated architecture (e.g. 'us-east-1' for AWS, "
                    "'us-central1' for GCP, 'eastus' for Azure). Used to set region-aware "
                    "pricing and compliance constraints (e.g. FedRAMP requires US regions)."
                ),
                examples=["us-east-1", "us-central1", "eastus", "eu-west-1"],
            ),
        ] = "us-east-1",
        budget_monthly: Annotated[
            float | None,
            Field(
                description=(
                    "Optional monthly budget cap in USD. When set, the architect biases toward "
                    "instance tiers and managed services that fit under this cap."
                ),
                examples=[2000, 5000, 10000],
            ),
        ] = None,
        compliance: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional list of compliance frameworks the architecture must satisfy. "
                    "Values from: 'hipaa', 'pci-dss', 'soc2', 'fedramp', 'gdpr'. "
                    "Influences service selection (e.g. BAA-eligible services for HIPAA, "
                    "FIPS-compliant services for FedRAMP) and encryption defaults."
                ),
                examples=[["hipaa"], ["soc2", "gdpr"], ["fedramp"]],
            ),
        ] = None,
    ) -> dict:
        """Design a cloud architecture from a natural-language description.

        Primary entry point for greenfield architecture design. Returns a complete
        ArchSpec (YAML-serializable dict) with components, connections, tier
        assignments, and a cost estimate.

        When to use: You have a requirement (prose) and need a concrete architecture
        with services, wiring, and cost. Use `modify_architecture` to iterate on
        an existing spec, or `chat_create_session` + `chat_send` for multi-turn
        refinement.

        Behavior: Calls an LLM provider (Anthropic or OpenAI depending on
        configured keys) — incurs API costs per invocation. Deterministic
        post-processing layers (cost engine, catalog lookup) apply safe defaults
        like encryption-at-rest, multi-AZ on databases, and auto-scaling. Does
        not deploy or modify any cloud resources.
        """
        from cloudwright.architect import Architect
        from cloudwright.cost import CostEngine
        from cloudwright.spec import Constraints

        constraints = Constraints(regions=[region], budget_monthly=budget_monthly, compliance=compliance or [])
        spec = Architect().design(description, constraints=constraints)
        if not spec.cost_estimate:
            spec = spec.model_copy(update={"cost_estimate": CostEngine().estimate(spec)})
        return spec.model_dump(exclude_none=True)

    @mcp.tool()
    def modify_architecture(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "Existing ArchSpec as a dict (typically the output of a prior "
                    "`design_architecture`, `modify_architecture`, or `chat_send` call). "
                    "Must contain 'name', 'provider', 'components', and 'connections' keys."
                ),
            ),
        ],
        instruction: Annotated[
            str,
            Field(
                description=(
                    "Plain-English modification instruction. The LLM interprets it and "
                    "produces a new ArchSpec with components added, removed, or reconfigured."
                ),
                examples=[
                    "Add a Redis cache between the API and the database",
                    "Replace RDS PostgreSQL with Aurora Serverless v2",
                    "Move the compute tier from ECS to Lambda",
                ],
            ),
        ],
    ) -> dict:
        """Modify an existing architecture with a natural-language instruction.

        When to use: You already have an ArchSpec and want to evolve it (add a
        cache, swap a service, change a region). Returns the updated ArchSpec.
        For from-scratch design, use `design_architecture`. For iterative
        multi-turn editing with conversation memory, use `chat_create_session`.

        Behavior: Calls an LLM provider — incurs API costs. Pure function:
        returns a new spec without mutating the input. Does not deploy.
        """
        from cloudwright.architect import Architect
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        modified = Architect().modify(spec, instruction)
        return modified.model_dump(exclude_none=True)

    @mcp.tool()
    def compare_providers(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to translate across providers. Original provider's services "
                    "are mapped to equivalents on each target provider using 22 cross-cloud "
                    "equivalence pairs (e.g. ec2 <-> compute_engine <-> virtual_machines)."
                ),
            ),
        ],
        providers: Annotated[
            list[str],
            Field(
                description=(
                    "List of target provider slugs to compare against. Values: 'aws', "
                    "'gcp', 'azure', 'databricks'. Returns one result per target."
                ),
                examples=[["gcp", "azure"], ["aws", "gcp"]],
            ),
        ],
    ) -> list[dict]:
        """Compare an architecture's **service mapping** across cloud providers.

        Returns one translated ArchSpec per target provider, showing which
        services the original would become on each. Use this to understand
        architectural portability and equivalent services.

        When to use vs `compare_provider_costs`: This tool returns full
        alternative **architectures** (with components, connections, tiers).
        `compare_provider_costs` returns only numeric **cost totals** per
        provider — use that when you only care about the bill, not the shape.

        Behavior: Calls an LLM to resolve ambiguous service mappings where the
        static equivalence table is insufficient. Does not deploy.
        """
        from cloudwright.architect import Architect
        from cloudwright.spec import ArchSpec

        spec = ArchSpec.model_validate(spec_json)
        alternatives = Architect().compare(spec, providers)
        return [a.model_dump(exclude_none=True) for a in alternatives]
