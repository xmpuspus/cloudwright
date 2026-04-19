from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def validate_compliance(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to validate. Checks are run against the declared components, "
                    "connections, and provider settings — no cloud API access required."
                ),
            ),
        ],
        frameworks: Annotated[
            list[str],
            Field(
                description=(
                    "List of compliance framework slugs to validate against. "
                    "Each framework runs 5-7 checks (encryption, logging, access control, etc.). "
                    "Values: 'hipaa', 'pci-dss', 'soc2', 'fedramp', 'gdpr'."
                ),
                examples=[["hipaa"], ["soc2", "pci-dss"], ["fedramp", "gdpr"]],
            ),
        ],
        well_architected: Annotated[
            bool,
            Field(
                description=(
                    "When True, additionally runs the AWS Well-Architected Framework pillar "
                    "checks (multi-AZ, auto-scaling, backup, monitoring, SPOF detection, "
                    "cost optimization). Independent of the `frameworks` list."
                ),
            ),
        ] = False,
    ) -> list[dict]:
        """Validate an architecture against compliance frameworks.

        Returns one result object per framework with pass/fail status per check,
        evidence (which components triggered the rule), and remediation hints.

        When to use: You have a proposed architecture and need to know whether
        it satisfies HIPAA / PCI-DSS / SOC 2 / FedRAMP / GDPR before proceeding.
        Use `security_scan` for anti-pattern detection (weak auth, public
        buckets, etc.) which is framework-agnostic.

        Behavior: Pure computation — no LLM, no network. Evaluates the spec
        statically against 30+ rules. Does not access or modify any cloud
        resources.
        """
        from cloudwright.spec import ArchSpec
        from cloudwright.validator import Validator

        spec = ArchSpec.model_validate(spec_json)
        results = Validator().validate(spec, compliance=frameworks, well_architected=well_architected)
        return [r.model_dump(exclude_none=True) for r in results]

    @mcp.tool()
    def security_scan(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to scan. The scanner inspects component configs, connection "
                    "protocols, encryption flags, exposure boundaries, and auth presence."
                ),
            ),
        ],
    ) -> dict:
        """Scan an architecture for security anti-patterns and misconfigurations.

        Returns a structured report with severity-graded findings (critical / high
        / medium / low / info), each tied to specific component IDs. Framework-
        agnostic — use `validate_compliance` for specific regulatory frameworks.

        Checks include: unencrypted data stores, public-facing databases, missing
        WAF on public HTTP endpoints, weak auth on APIs, SPOFs, overly permissive
        connection protocols.

        Behavior: Pure computation — no LLM, no network. Does not touch cloud.
        """
        from cloudwright.security import SecurityScanner
        from cloudwright.spec import ArchSpec

        from cloudwright_mcp.serializers import security_report_to_dict

        spec = ArchSpec.model_validate(spec_json)
        report = SecurityScanner().scan(spec)
        return security_report_to_dict(report)

    @mcp.tool()
    def scan_terraform(
        hcl_content: Annotated[
            str,
            Field(
                description=(
                    "Raw Terraform HCL source code to scan. Typically the contents of a "
                    "`main.tf` file or a concatenated module. The scanner parses resource "
                    "blocks directly; no terraform binary is invoked."
                ),
            ),
        ],
    ) -> dict:
        """Scan Terraform HCL source for security misconfigurations.

        Returns findings (severity-graded) tied to specific resource blocks — e.g.
        aws_s3_bucket with `acl = public-read`, aws_security_group with
        `cidr_blocks = 0.0.0.0/0` on sensitive ports, aws_rds_instance with
        `storage_encrypted = false`.

        When to use: You have existing Terraform code (not an ArchSpec) and want
        an immediate security audit. For ArchSpec-level audit, use `security_scan`.

        Behavior: Pure computation — no LLM, no network. Does not run Terraform
        or touch cloud. Safe for scanning untrusted HCL.
        """
        from cloudwright.security import scan_terraform as _scan_terraform

        from cloudwright_mcp.serializers import security_report_to_dict

        report = _scan_terraform(hcl_content)
        return security_report_to_dict(report)

    @mcp.tool()
    def lint_architecture(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to lint. Runs 10 anti-pattern checks covering encryption, "
                    "redundancy, load balancing, auth presence, and resource sizing."
                ),
            ),
        ],
    ) -> list[dict]:
        """Lint an architecture for anti-patterns and best-practice violations.

        Returns a list of warnings with rule name, severity (error / warning),
        component IDs involved, and a human-readable message.

        Errors (production-blocking): unencrypted data stores, single-AZ
        databases, missing load balancer on public compute, public databases,
        single point of failure.
        Warnings (review-worthy): oversized instances (16xlarge+), missing WAF,
        missing monitoring, missing backups, missing auth.

        When to use vs `security_scan`: lint is about **architectural hygiene**
        (is this a sane shape?). security_scan is about **threat exposure**
        (can an attacker reach X?). Use both for comprehensive review.

        Behavior: Pure computation — no LLM, no network. Does not touch cloud.
        """
        from cloudwright.linter import lint
        from cloudwright.spec import ArchSpec

        from cloudwright_mcp.serializers import lint_warnings_to_dict

        spec = ArchSpec.model_validate(spec_json)
        warnings = lint(spec)
        return lint_warnings_to_dict(warnings)
