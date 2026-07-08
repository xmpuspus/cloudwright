from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def scan_compliance_controls(
        spec_json: Annotated[
            dict,
            Field(
                description=(
                    "ArchSpec to scan. Runs the built-in component scanner plus a Terraform "
                    "HCL scan of the exported infrastructure, and folds in a Checkov deep "
                    "scan when the checkov binary is on PATH."
                ),
            ),
        ],
        frameworks: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Compliance framework slugs to map findings against. Values: 'hipaa', "
                    "'soc2', 'pci-dss', 'fedramp', 'gdpr', 'iso27001', 'nist'. When omitted, "
                    "uses `spec.constraints.compliance` if set, otherwise maps against all "
                    "7 supported frameworks."
                ),
                examples=[["hipaa"], ["soc2", "fedramp"], None],
            ),
        ] = None,
        checkov: Annotated[
            bool | None,
            Field(
                description=(
                    "Force (True) or skip (False) the optional Checkov deep scan against the "
                    "exported Terraform. None (default) auto-detects whether the checkov "
                    "binary is on PATH and runs it only if present."
                ),
            ),
        ] = None,
        oscal: Annotated[
            bool,
            Field(
                description=(
                    "When True, return an OSCAL 1.1.2 component-definition document (dict) "
                    "instead of the raw scan report, using the same builder `cloudwright "
                    "compliance --oscal` uses. `traceability` is ignored in this mode."
                ),
            ),
        ] = False,
        traceability: Annotated[
            bool,
            Field(
                description=(
                    "When True and `oscal` is False, include a `traceability` key: the "
                    "design-intent -> component -> IaC resource -> control -> status chain "
                    "for every finding."
                ),
            ),
        ] = False,
    ) -> dict:
        """Scan an architecture and map every finding to compliance framework control IDs.

        Unlike `validate_compliance` (5-7 static pass/fail checks per framework), this
        maps EVERY finding, from the built-in scanner, a Terraform HCL scan, and an
        optional Checkov deep scan, to the specific control IDs it violates (e.g. HIPAA
        164.312(a)(2)(iv), SOC2 CC6.1, FedRAMP SC-28), before any infrastructure exists.

        Returns `{'passed': bool, 'scanner': str, 'checkov_used': bool, 'findings': [...],
        'frameworks': [...]}`. Each finding carries `severity`, `rule`, `component_id`,
        `message`, `remediation`, `source` ('builtin' | 'terraform' | 'checkov'), and
        `controls` (list of `{framework, control_id, title}`). Each framework summary
        carries `controls_total`, `controls_violated`, `controls_satisfied`, `findings`,
        and `status` ('pass' | 'fail').

        Set `oscal=True` to instead receive a machine-readable OSCAL 1.1.2
        component-definition document mapping every architecture component to its
        control-implementation status: the interoperability surface for FedRAMP 20x /
        OSCAL-consuming tooling. Set `traceability=True` (non-OSCAL mode) for the
        component -> resource -> control chain used in audit reports.

        When to use: Pre-deployment compliance posture with control-level detail, or
        generating an OSCAL artifact for a FedRAMP/NIST-800-53 pipeline. For a quick
        pass/fail per framework without control mapping, use `validate_compliance`.

        Behavior: Pure computation plus an optional local Checkov subprocess (never a
        network call; auto-skipped when the checkov binary is absent). Never writes
        files; the caller persists the returned content if needed. Invalid or empty
        `spec_json` returns `{'error': str}` instead of raising.
        """
        from cloudwright.compliance import ComplianceScanner, build_traceability
        from cloudwright.spec import ArchSpec

        try:
            spec = ArchSpec.model_validate(spec_json)
        except Exception as exc:
            return {"error": f"Invalid spec: {exc}"}

        scanner = ComplianceScanner()
        report = scanner.scan(spec, frameworks=frameworks, run_checkov=checkov)

        if oscal:
            from cloudwright.oscal import to_oscal

            resolved = scanner.resolve_frameworks(spec, frameworks)
            return to_oscal(spec, report, resolved)

        payload = report.as_dict()
        if traceability:
            payload["traceability"] = build_traceability(spec, report)
        return payload
