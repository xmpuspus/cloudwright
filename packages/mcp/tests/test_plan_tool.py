from __future__ import annotations

from unittest import mock

from cloudwright.spec import ArchSpec, Component


def _spec_dict() -> dict:
    spec = ArchSpec(
        name="PlanMcpTest",
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="DB",
                tier=3,
                config={"encryption": True, "backup": True, "multi_az": True},
            ),
        ],
    )
    return spec.model_dump(exclude_none=True)


class TestPlanInfrastructure:
    def test_missing_binary_returns_structured_not_available(self, register_tools):
        import cloudwright_mcp.tools.plan as mod

        fns = register_tools(mod)
        with mock.patch("cloudwright.planner.shutil.which", return_value=None):
            result = fns["plan_infrastructure"](spec_json=_spec_dict())

        assert result["available"] is False
        assert result["ok"] is False
        assert "error" not in result  # structured skip, not an exception

    def test_default_is_validate_only_never_plan(self, register_tools):
        """MCP boundary: run_plan defaults to False, unlike the CLI."""
        import cloudwright_mcp.tools.plan as mod

        fns = register_tools(mod)
        with mock.patch("cloudwright.planner.shutil.which", return_value=None):
            result = fns["plan_infrastructure"](spec_json=_spec_dict())

        assert result["plan_ran"] is False

    def test_invalid_spec_returns_error_dict_not_exception(self, register_tools):
        import cloudwright_mcp.tools.plan as mod

        fns = register_tools(mod)
        result = fns["plan_infrastructure"](spec_json={"components": [{"id": "1bad"}]})

        assert "error" in result

    def test_empty_spec_returns_error_dict_not_exception(self, register_tools):
        import cloudwright_mcp.tools.plan as mod

        fns = register_tools(mod)
        result = fns["plan_infrastructure"](spec_json={})

        assert "error" in result

    def test_unknown_target_returns_error_dict_not_exception(self, register_tools):
        import cloudwright_mcp.tools.plan as mod

        fns = register_tools(mod)
        result = fns["plan_infrastructure"](spec_json=_spec_dict(), target="bogus-target")

        assert "error" in result

    def test_works_with_no_api_key_set(self, monkeypatch, register_tools):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        import cloudwright_mcp.tools.plan as mod

        fns = register_tools(mod)
        with mock.patch("cloudwright.planner.shutil.which", return_value=None):
            result = fns["plan_infrastructure"](spec_json=_spec_dict())

        assert "error" not in result
