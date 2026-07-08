from __future__ import annotations

from cloudwright.spec import ArchSpec, Component


def _flawed_spec_dict() -> dict:
    # Bare compute + DB, no monitoring/backup/LB scaffolding: trips linter rules
    # deterministically so the review always returns findings.
    spec = ArchSpec(
        name="flawed",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
    )
    return spec.model_dump(exclude_none=True)


class TestReviewArchitecture:
    def test_valid_spec_returns_expected_shape(self, register_tools):
        import cloudwright_mcp.tools.review as mod

        fns = register_tools(mod)
        result = fns["review_architecture"](spec_json=_flawed_spec_dict())

        assert {"score", "grade", "findings", "blocking_count", "summary"} <= set(result)
        assert result["findings"], "a bare 2-component spec should surface findings"

    def test_compliance_frameworks_fold_in_validator_findings(self, register_tools):
        import cloudwright_mcp.tools.review as mod

        fns = register_tools(mod)
        result = fns["review_architecture"](spec_json=_flawed_spec_dict(), compliance=["hipaa"])

        assert any(f["source"] == "validator" for f in result["findings"])

    def test_invalid_spec_returns_error_dict_not_exception(self, register_tools):
        import cloudwright_mcp.tools.review as mod

        fns = register_tools(mod)
        result = fns["review_architecture"](spec_json={"components": [{"id": "1bad"}]})

        assert "error" in result

    def test_empty_spec_returns_error_dict_not_exception(self, register_tools):
        import cloudwright_mcp.tools.review as mod

        fns = register_tools(mod)
        result = fns["review_architecture"](spec_json={})

        assert "error" in result

    def test_works_with_no_api_key_set(self, monkeypatch, register_tools):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        import cloudwright_mcp.tools.review as mod

        fns = register_tools(mod)
        result = fns["review_architecture"](spec_json=_flawed_spec_dict())

        assert "error" not in result
        assert "score" in result
