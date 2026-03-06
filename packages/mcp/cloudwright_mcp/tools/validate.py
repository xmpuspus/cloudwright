from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def validate_compliance(
        spec_json: dict,
        frameworks: list[str],
        well_architected: bool = False,
    ) -> list[dict]:
        """Validate an architecture against compliance frameworks."""
        from cloudwright.spec import ArchSpec
        from cloudwright.validator import Validator

        spec = ArchSpec.model_validate(spec_json)
        results = Validator().validate(spec, compliance=frameworks, well_architected=well_architected)
        return [r.model_dump(exclude_none=True) for r in results]

    @mcp.tool()
    def security_scan(spec_json: dict) -> dict:
        """Scan an architecture for security anti-patterns and misconfigurations."""
        from cloudwright.security import SecurityScanner
        from cloudwright.spec import ArchSpec

        from cloudwright_mcp.serializers import security_report_to_dict

        spec = ArchSpec.model_validate(spec_json)
        report = SecurityScanner().scan(spec)
        return security_report_to_dict(report)

    @mcp.tool()
    def scan_terraform(hcl_content: str) -> dict:
        """Scan Terraform HCL for security misconfigurations."""
        from cloudwright.security import scan_terraform as _scan_terraform

        from cloudwright_mcp.serializers import security_report_to_dict

        report = _scan_terraform(hcl_content)
        return security_report_to_dict(report)

    @mcp.tool()
    def lint_architecture(spec_json: dict) -> list[dict]:
        """Lint an architecture for anti-patterns and best-practice violations."""
        from cloudwright.linter import lint
        from cloudwright.spec import ArchSpec

        from cloudwright_mcp.serializers import lint_warnings_to_dict

        spec = ArchSpec.model_validate(spec_json)
        warnings = lint(spec)
        return lint_warnings_to_dict(warnings)
