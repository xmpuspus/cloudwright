"""Portable migration contract tests.

Each test names a consumer-visible break: lost fields, dangling dependency
references, unsupported dispositions, or evidence that cannot round-trip.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from cloudwright.migration import EvidenceInput, MigrationProject, TargetMapping
from pydantic import ValidationError


def _project_data() -> dict:
    return {
        "schema_version": "1.0",
        "name": "Plant ERP move",
        "industry": "manufacturing",
        "estate": {
            "name": "Current estate",
            "assets": [
                {
                    "id": "db",
                    "name": "ERP database",
                    "kind": "data",
                    "provider": "on_prem",
                    "location": "plant-a",
                    "owner": "data-team",
                    "criticality": "critical",
                    "data_classes": ["financial_records"],
                    "tags": ["erp"],
                    "current_monthly_cost": 8000,
                    "provenance": [
                        {
                            "source": "cmdb",
                            "observed_at": "2026-08-20T03:00:00Z",
                            "confidence": 0.9,
                        }
                    ],
                },
                {
                    "id": "erp",
                    "name": "ERP application",
                    "kind": "application",
                    "provider": "on_prem",
                    "criticality": "high",
                    "tags": ["erp"],
                    "current_monthly_cost": 4000,
                },
            ],
            "dependencies": [
                {
                    "source": "erp",
                    "target": "db",
                    "kind": "runtime",
                    "criticality": "critical",
                }
            ],
        },
        "target": {
            "name": "Hybrid target",
            "assets": [
                {
                    "id": "db-target",
                    "name": "Managed ERP database",
                    "kind": "data",
                    "provider": "private_cloud",
                    "location": "colo-a",
                    "criticality": "critical",
                },
                {
                    "id": "erp-target",
                    "name": "ERP containers",
                    "kind": "application",
                    "provider": "private_cloud",
                    "location": "colo-a",
                    "criticality": "high",
                },
            ],
            "mappings": [
                {
                    "source_asset_id": "db",
                    "target_asset_ids": ["db-target"],
                    "disposition": "replatform",
                    "strategy": "replicate then cut over",
                    "owner": "data-team",
                    "rollback": "resume source writes",
                    "one_time_cost": 20000,
                    "target_monthly_cost": 6000,
                    "dual_run_months": 2,
                },
                {
                    "source_asset_id": "erp",
                    "target_asset_ids": ["erp-target"],
                    "disposition": "rehost",
                    "strategy": "blue-green deployment",
                    "owner": "app-team",
                    "rollback": "restore source route",
                    "one_time_cost": 10000,
                    "target_monthly_cost": 3000,
                    "dual_run_months": 1,
                },
            ],
        },
        "metadata": {"decision_owner": "transformation-office"},
    }


def test_project_round_trip_keeps_portable_fields(tmp_path: Path):
    project = MigrationProject.model_validate(_project_data())

    assert project.schema_version == "1.0"
    assert math.isclose(project.estate.assets[0].provenance[0].confidence, 0.9)
    assert project.target.mappings[0].disposition == "replatform"

    project_file = tmp_path / "project.yaml"
    project_file.write_text(project.to_yaml())
    restored = MigrationProject.from_file(project_file)

    assert restored == project
    assert MigrationProject.from_yaml(project.to_yaml()) == project


def test_estate_rejects_dangling_dependency_reference():
    data = _project_data()
    data["estate"]["dependencies"][0]["target"] = "missing"

    with pytest.raises(ValidationError, match="missing"):
        MigrationProject.model_validate(data)


def test_mapping_rejects_unknown_disposition():
    data = _project_data()
    data["target"]["mappings"][0]["disposition"] = "teleport"

    with pytest.raises(ValidationError, match="disposition"):
        MigrationProject.model_validate(data)


def test_project_rejects_an_empty_source_estate():
    data = _project_data()
    data["estate"]["assets"] = []
    data["estate"]["dependencies"] = []
    data["target"]["mappings"] = []

    with pytest.raises(ValidationError, match="at least one asset"):
        MigrationProject.model_validate(data)


@pytest.mark.parametrize(
    "extra",
    [
        {"target_asset_ids": ["replacement"]},
        {"target_monthly_cost": 500},
        {"one_time_cost": 100},
        {"dual_run_months": 1},
        {"decommission_credit": 50},
    ],
)
def test_retain_mapping_rejects_target_changes_and_migration_costs(extra):
    with pytest.raises(ValidationError, match="retain mapping"):
        TargetMapping.model_validate(
            {
                "source_asset_id": "app",
                "disposition": "retain",
                **extra,
            }
        )


@pytest.mark.parametrize("extra", [{"target_monthly_cost": 500}, {"dual_run_months": 1}])
def test_retire_mapping_rejects_target_and_dual_run_costs(extra):
    with pytest.raises(ValidationError, match="retire mapping"):
        TargetMapping.model_validate(
            {
                "source_asset_id": "app",
                "disposition": "retire",
                **extra,
            }
        )


def test_evidence_input_round_trip_keeps_boolean_and_numeric_values(tmp_path: Path):
    evidence = EvidenceInput.model_validate(
        {
            "assessment_id": "a" * 64,
            "project_name": "Plant ERP move",
            "observations": [
                {
                    "criterion_id": "rollback-documented",
                    "value": True,
                    "source": "change-record",
                    "observed_at": "2026-08-23T09:00:00Z",
                },
                {
                    "criterion_id": "balance-delta",
                    "value": 0.005,
                    "source": "reconciliation-job",
                    "observed_at": "2026-08-23T10:00:00Z",
                },
            ],
        }
    )

    path = tmp_path / "evidence.yaml"
    path.write_text(evidence.to_yaml())
    restored = EvidenceInput.from_file(path)

    assert restored.observations[0].value is True
    assert math.isclose(restored.observations[1].value, 0.005)


def test_evidence_rejects_non_finite_numeric_values():
    with pytest.raises(ValidationError, match="finite_number"):
        EvidenceInput.from_yaml(
            """assessment_id: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
project_name: Plant ERP move
observations:
  - criterion_id: record-parity
    value: .inf
    source: reconciliation-job
    observed_at: "2026-08-23T10:00:00Z"
"""
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("one_time_cost", 1e308),
        ("target_monthly_cost", 1e308),
        ("decommission_credit", 1e308),
        ("dual_run_months", 1e308),
    ],
)
def test_mapping_rejects_cost_values_that_can_overflow_aggregate_economics(field, value):
    with pytest.raises(ValidationError, match="less_than_equal"):
        TargetMapping.model_validate(
            {
                "source_asset_id": "app",
                "target_asset_ids": ["app-target"],
                "disposition": "rehost",
                "rollback": "restore source route",
                field: value,
            }
        )


def test_asset_rejects_monthly_cost_that_can_overflow_aggregate_economics():
    data = _project_data()
    data["estate"]["assets"][0]["current_monthly_cost"] = 1e308

    with pytest.raises(ValidationError, match="less_than_equal"):
        MigrationProject.model_validate(data)


@pytest.mark.parametrize("observed_at", ["", "not-a-timestamp", "2026-08-24"])
def test_evidence_rejects_missing_or_unzoned_timestamps(observed_at):
    with pytest.raises(ValidationError, match="observed_at"):
        EvidenceInput.model_validate(
            {
                "assessment_id": "a" * 64,
                "project_name": "Plant ERP move",
                "observations": [
                    {
                        "criterion_id": "record-parity",
                        "value": True,
                        "source": "reconciliation-job",
                        "observed_at": observed_at,
                    }
                ],
            }
        )


def test_file_loader_rejects_non_mapping_yaml(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("- not\n- a\n- project\n")

    with pytest.raises(ValueError, match="mapping"):
        MigrationProject.from_file(path)
