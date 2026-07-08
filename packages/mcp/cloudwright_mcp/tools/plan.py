from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def plan_infrastructure(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to prove deployable. Exported to Terraform/Pulumi in a "
                    "throwaway temp directory that is deleted when the call returns, "
                    "never a persistent workspace."
                ),
            ),
        ],
        target: Annotated[
            str,
            Field(
                description=(
                    "IaC target. Values: 'terraform' (or 'tf'; prefers OpenTofu when it's "
                    "on PATH), 'pulumi-python', 'pulumi-ts'."
                ),
                examples=["terraform", "pulumi-python", "pulumi-ts"],
            ),
        ] = "terraform",
        run_plan: Annotated[
            bool,
            Field(
                description=(
                    "When False (default), only exports and runs `terraform validate` (or "
                    "the Pulumi login/compile step): no cloud credentials needed, fast. "
                    "When True, additionally runs `terraform plan` / `pulumi preview` for a "
                    "real resource diff, which needs cloud credentials and can take longer. "
                    "Neither mode ever applies; there is no apply path in this tool."
                ),
            ),
        ] = False,
        timeout: Annotated[
            int,
            Field(
                description="Seconds before the validate/plan subprocess is aborted.",
                examples=[60, 180],
            ),
        ] = 60,
    ) -> dict:
        """Prove an architecture's exported infrastructure is deployable. Read-only.

        Exports the spec to a throwaway temp directory and runs `terraform init
        -backend=false` + `validate` (no cloud credentials required) as the offline
        proof of deployability, or the Pulumi equivalent. This is the same read-only
        planner behind `cloudwright plan`.

        Returns `{'tool': str, 'available': bool, 'validated': bool, 'plan_ran': bool,
        'ok': bool, 'summary': {'add','change','destroy'}|None, 'messages': [str],
        'output_tail': str}`. `available=False` means the terraform/tofu/pulumi binary
        isn't installed: a structured skip, not an error. `ok` is the overall
        deployability verdict; `plan_ran` is True only when a full plan/preview
        executed (needs credentials).

        MCP-context boundary: the default here is validate-only (`run_plan=False`) to
        keep the call fast and credential-free, unlike the CLI which defaults to
        attempting a full plan. Pass `run_plan=True` for a real resource diff when
        credentials are available in the server's environment. Under no argument
        combination does this tool run `terraform apply` / `pulumi up`; the
        underlying planner has no apply code path at all.

        When to use: After `export_architecture` (format='terraform'), to confirm the
        generated IaC is syntactically and semantically valid before handing it to a
        deploy pipeline. Complementary to `security_scan` / `scan_compliance_controls`,
        which check the *design*, not whether the emitted HCL/Pulumi program compiles.

        Behavior: Runs a local subprocess (terraform/tofu/pulumi) against a temp
        directory deleted when the call returns. No cloud resources are read, created,
        or modified. Degrades to a structured `{'available': False, ...}` result when
        the binary is missing, and to `{'error': str}` for an invalid spec or unknown
        `target`. Neither case raises.
        """
        from cloudwright.planner import plan as run_plan_fn
        from cloudwright.spec import ArchSpec

        try:
            spec = ArchSpec.model_validate(spec_json)
        except Exception as exc:
            return {"error": f"Invalid spec: {exc}"}

        try:
            result = run_plan_fn(spec, target=target, run_plan=run_plan, timeout=timeout)
        except ValueError as exc:
            return {"error": str(exc)}

        return result.as_dict()
