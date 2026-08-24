"""Dependency-aware migration planning and economics tests."""

from __future__ import annotations

import math
import sys

import pytest
from cloudwright.migration import AssetDependency, EstateAsset, MigrationProject, TargetMapping
from cloudwright.migration.planner import MigrationPlanner


def _project() -> MigrationProject:
    return MigrationProject.model_validate(
        {
            "name": "ERP move",
            "industry": "manufacturing",
            "estate": {
                "name": "Current",
                "assets": [
                    {
                        "id": "db",
                        "name": "Database",
                        "kind": "data",
                        "provider": "on_prem",
                        "current_monthly_cost": 8000,
                    },
                    {
                        "id": "app",
                        "name": "Application",
                        "kind": "application",
                        "provider": "on_prem",
                        "current_monthly_cost": 4000,
                    },
                ],
                "dependencies": [{"source": "app", "target": "db"}],
            },
            "target": {
                "name": "Target",
                "assets": [
                    {"id": "db-new", "name": "New database", "kind": "data"},
                    {"id": "app-new", "name": "New application", "kind": "application"},
                ],
                "mappings": [
                    {
                        "source_asset_id": "db",
                        "target_asset_ids": ["db-new"],
                        "disposition": "replatform",
                        "strategy": "replicate",
                        "rollback": "resume source writes",
                        "one_time_cost": 20000,
                        "target_monthly_cost": 6000,
                        "dual_run_months": 2,
                    },
                    {
                        "source_asset_id": "app",
                        "target_asset_ids": ["app-new"],
                        "disposition": "rehost",
                        "strategy": "blue-green",
                        "rollback": "restore source route",
                        "one_time_cost": 10000,
                        "target_monthly_cost": 3000,
                        "dual_run_months": 1,
                    },
                ],
            },
        }
    )


def test_planner_schedules_dependencies_before_consumers():
    assessment = MigrationPlanner().plan(_project())

    assert [[action.source_asset_id for action in wave.actions] for wave in assessment.transition.waves] == [
        ["db"],
        ["app"],
    ]
    assert assessment.transition.complete is True
    assert assessment.transition.waves[1].prerequisites == ["db"]


def test_planner_groups_independent_assets_in_one_wave():
    project = _project()
    project.estate.dependencies = []

    assessment = MigrationPlanner().plan(project)

    assert len(assessment.transition.waves) == 1
    assert {action.source_asset_id for action in assessment.transition.waves[0].actions} == {"db", "app"}


def test_wave_hint_can_postpone_an_action_and_dependents_follow_it():
    project = _project()
    project.target.mappings[0].wave_hint = 3

    assessment = MigrationPlanner().plan(project)

    assert [wave.order for wave in assessment.transition.waves] == [3, 4]
    assert assessment.transition.waves[1].actions[0].source_asset_id == "app"


def test_explicit_wave_hint_cannot_run_before_dependency():
    project = _project()
    project.target.mappings[0].wave_hint = 3
    project.target.mappings[1].wave_hint = 2

    with pytest.raises(ValueError, match="wave hint.*app.*db"):
        MigrationPlanner().plan(project)


def test_dependency_cycle_stops_planning_and_names_assets():
    project = _project()
    project.estate.dependencies.append(AssetDependency(source="db", target="app"))

    with pytest.raises(ValueError, match="cycle.*app.*db|cycle.*db.*app"):
        MigrationPlanner().plan(project)


def test_long_dependency_chain_plans_without_recursion_failure():
    asset_count = 600
    project = MigrationProject.model_validate(
        {
            "name": "Long move",
            "estate": {
                "name": "Current",
                "assets": [
                    {"id": f"asset-{index}", "name": f"Asset {index}", "kind": "application"}
                    for index in range(asset_count)
                ],
                "dependencies": [
                    {"source": f"asset-{index}", "target": f"asset-{index - 1}"} for index in range(1, asset_count)
                ],
            },
            "target": {
                "name": "Target",
                "assets": [
                    {"id": f"target-{index}", "name": f"Target {index}", "kind": "application"}
                    for index in range(asset_count)
                ],
                "mappings": [
                    {
                        "source_asset_id": f"asset-{index}",
                        "target_asset_ids": [f"target-{index}"],
                        "disposition": "rehost",
                        "rollback": "restore source route",
                    }
                    for index in range(asset_count)
                ],
            },
        }
    )

    previous_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(500)
        assessment = MigrationPlanner().plan(project)
    finally:
        sys.setrecursionlimit(previous_limit)

    assert assessment.transition.waves[-1].order == asset_count


def test_retained_asset_cannot_depend_on_retired_asset():
    project = _project()
    project.target.mappings[0] = TargetMapping(source_asset_id="db", disposition="retire")
    project.target.mappings[1] = TargetMapping(source_asset_id="app", disposition="retain")
    project = MigrationProject.model_validate(project.model_dump())

    with pytest.raises(ValueError, match="retained asset app depends on retired asset db"):
        MigrationPlanner().plan(project)


def test_unmapped_asset_blocks_complete_plan():
    project = _project()
    project.estate.assets.append(EstateAsset(id="files", name="File store", kind="data", current_monthly_cost=500))

    assessment = MigrationPlanner().plan(MigrationProject.model_validate(project.model_dump()))

    assert assessment.transition.complete is False
    assert assessment.transition.unresolved_assets == ["files"]
    assert any("files" in warning for warning in assessment.transition.warnings)
    assert assessment.transition.economics.target_monthly_cost == 9500
    assert assessment.transition.economics.monthly_delta == -3000


def test_retirement_runs_after_moving_assets():
    project = _project()
    project.estate.assets.append(
        EstateAsset(
            id="legacy-report",
            name="Legacy report",
            kind="application",
            current_monthly_cost=500,
        )
    )
    project.target.mappings.append(
        TargetMapping(
            source_asset_id="legacy-report",
            disposition="retire",
            strategy="archive then remove",
            rollback="restore archived service",
            decommission_credit=2500,
        )
    )
    project = MigrationProject.model_validate(project.model_dump())

    assessment = MigrationPlanner().plan(project)

    last_wave = assessment.transition.waves[-1]
    assert last_wave.actions[0].source_asset_id == "legacy-report"
    assert last_wave.actions[0].disposition == "retire"


def test_retirement_waits_for_assets_that_depend_on_it():
    project = _project()
    project.target.mappings[0] = TargetMapping(source_asset_id="db", disposition="retire")
    project = MigrationProject.model_validate(project.model_dump())

    assessment = MigrationPlanner().plan(project)

    assert [[action.source_asset_id for action in wave.actions] for wave in assessment.transition.waves] == [
        ["app"],
        ["db"],
    ]
    assert [wave.order for wave in assessment.transition.waves] == [1, 2]
    assert assessment.transition.waves[1].prerequisites == ["app"]


def test_economics_use_explicit_source_target_and_dual_run_values():
    economics = MigrationPlanner().plan(_project()).transition.economics

    assert math.isclose(economics.current_monthly_cost, 12000)
    assert math.isclose(economics.target_monthly_cost, 9000)
    assert math.isclose(economics.monthly_delta, -3000)
    assert math.isclose(economics.one_time_cost, 30000)
    assert math.isclose(economics.dual_run_cost, 35000)
    assert math.isclose(economics.net_migration_cost, 65000)
    assert economics.payback_months is not None
    assert math.isclose(economics.payback_months, 21.67, abs_tol=0.01)


def test_each_wave_has_generic_rollback_gate():
    assurance = MigrationPlanner().plan(_project()).assurance

    assert [criterion.id for criterion in assurance.criteria] == [
        "wave-1-rollback-ready",
        "wave-2-rollback-ready",
    ]
    assert all(criterion.comparator == "true" for criterion in assurance.criteria)
