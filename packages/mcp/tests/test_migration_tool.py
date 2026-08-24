from __future__ import annotations

from cloudwright.migration.demo import load_demo


class TestMigrationTools:
    def test_plan_migration_returns_the_core_assessment(self, register_tools):
        import cloudwright_mcp.tools.migration as mod

        project, _ = load_demo()
        tools = register_tools(mod)

        result = tools["plan_migration"](project_json=project.as_dict())

        assert result["transition"]["complete"] is True
        assert len(result["transition"]["waves"]) == 5
        assert len(result["assurance"]["criteria"]) == 22

    def test_verify_migration_rebuilds_gates_and_closes_with_complete_evidence(self, register_tools):
        import cloudwright_mcp.tools.migration as mod

        project, evidence = load_demo()
        tools = register_tools(mod)

        result = tools["verify_migration"](
            project_json=project.as_dict(),
            evidence_json=evidence.as_dict(),
        )

        assert result["closed"] is True
        assert result["passed"] == 22

    def test_verify_migration_keeps_missing_blocking_evidence_visible(self, register_tools):
        import cloudwright_mcp.tools.migration as mod

        project, evidence = load_demo()
        evidence.observations = [
            item for item in evidence.observations if item.criterion_id != "subscriber-record-parity"
        ]
        tools = register_tools(mod)

        result = tools["verify_migration"](
            project_json=project.as_dict(),
            evidence_json=evidence.as_dict(),
        )

        assert result["closed"] is False
        assert result["blocking_failures"] == 1

    def test_invalid_project_returns_error_instead_of_raising(self, register_tools):
        import cloudwright_mcp.tools.migration as mod

        tools = register_tools(mod)

        result = tools["plan_migration"](project_json={})

        assert "error" in result


def test_migration_group_is_registered_by_the_server():
    from cloudwright_mcp.server import _GROUPS

    assert "migration" in _GROUPS
