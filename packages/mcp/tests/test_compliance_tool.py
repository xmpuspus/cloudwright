from __future__ import annotations

from cloudwright.spec import ArchSpec, Component, Constraints


def _hipaa_spec_dict() -> dict:
    # Unencrypted RDS trips missing_encryption, which the control catalog maps
    # to HIPAA 164.312(a)(2)(iv) and FedRAMP SC-28 deterministically.
    spec = ArchSpec(
        name="ComplianceTest",
        provider="aws",
        region="us-east-1",
        constraints=Constraints(compliance=["hipaa"]),
        components=[
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="DB",
                tier=3,
                config={"backup": True, "multi_az": True},
            ),
        ],
    )
    return spec.model_dump(exclude_none=True)


class TestScanComplianceControls:
    def test_valid_spec_maps_findings_to_controls(self, register_tools):
        import cloudwright_mcp.tools.compliance as mod

        fns = register_tools(mod)
        result = fns["scan_compliance_controls"](spec_json=_hipaa_spec_dict(), frameworks=["hipaa"], checkov=False)

        assert {"passed", "scanner", "checkov_used", "findings", "frameworks"} <= set(result)
        assert result["findings"], "unencrypted RDS should trip a HIPAA-mapped finding"
        assert any(c["framework"] == "HIPAA" for f in result["findings"] for c in f["controls"])

    def test_oscal_returns_component_definition_not_raw_report(self, register_tools):
        import cloudwright_mcp.tools.compliance as mod

        fns = register_tools(mod)
        result = fns["scan_compliance_controls"](
            spec_json=_hipaa_spec_dict(), frameworks=["hipaa"], checkov=False, oscal=True
        )

        assert "component-definition" in result
        assert result["component-definition"]["metadata"]["oscal-version"] == "1.1.2"
        assert "findings" not in result

    def test_traceability_included_when_requested(self, register_tools):
        import cloudwright_mcp.tools.compliance as mod

        fns = register_tools(mod)
        result = fns["scan_compliance_controls"](
            spec_json=_hipaa_spec_dict(), frameworks=["hipaa"], checkov=False, traceability=True
        )

        assert "traceability" in result

    def test_traceability_absent_by_default(self, register_tools):
        import cloudwright_mcp.tools.compliance as mod

        fns = register_tools(mod)
        result = fns["scan_compliance_controls"](spec_json=_hipaa_spec_dict(), frameworks=["hipaa"], checkov=False)

        assert "traceability" not in result

    def test_invalid_spec_returns_error_dict_not_exception(self, register_tools):
        import cloudwright_mcp.tools.compliance as mod

        fns = register_tools(mod)
        result = fns["scan_compliance_controls"](spec_json={"components": [{"id": "1bad"}]}, frameworks=["hipaa"])

        assert "error" in result

    def test_empty_spec_returns_error_dict_not_exception(self, register_tools):
        import cloudwright_mcp.tools.compliance as mod

        fns = register_tools(mod)
        result = fns["scan_compliance_controls"](spec_json={}, frameworks=None)

        assert "error" in result

    def test_works_with_no_api_key_set(self, monkeypatch, register_tools):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        import cloudwright_mcp.tools.compliance as mod

        fns = register_tools(mod)
        result = fns["scan_compliance_controls"](spec_json=_hipaa_spec_dict(), checkov=False)

        assert "error" not in result
