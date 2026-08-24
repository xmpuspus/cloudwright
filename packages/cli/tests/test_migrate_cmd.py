"""Migration CLI contract tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
from cloudwright_cli.commands import migrate_cmd
from cloudwright_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()
ROOT = Path(__file__).parents[3]
EXAMPLES = ROOT / "examples" / "migrations"


def test_migrate_help_lists_offline_commands():
    result = runner.invoke(app, ["migrate", "--help"])

    assert result.exit_code == 0
    assert "packs" in result.output
    assert "plan" in result.output
    assert "verify" in result.output
    assert "demo" in result.output


def test_migrate_packs_supports_human_and_json_output():
    human = runner.invoke(app, ["migrate", "packs"])
    machine = runner.invoke(app, ["--json", "migrate", "packs"])

    assert human.exit_code == 0
    assert "Philippine telecommunications" in human.output
    assert machine.exit_code == 0
    payload = json.loads(machine.output)["data"]
    assert payload["packs"][0]["name"] == "ph_telco"


def test_migrate_plan_renders_waves_and_writes_assessment(tmp_path: Path):
    output = tmp_path / "assessment.yaml"
    result = runner.invoke(
        app,
        ["migrate", "plan", str(EXAMPLES / "ph-telco-project.yaml"), "-o", str(output)],
    )

    assert result.exit_code == 0
    assert "PH telco hybrid service migration" in result.output
    assert "Wave 5" in result.output
    assert "Monthly savings" in result.output
    assert output.exists()
    assessment = yaml.safe_load(output.read_text())
    assert assessment["transition"]["complete"] is True
    assert len(assessment["assurance"]["criteria"]) == 22


def test_migrate_plan_has_stable_json_envelope():
    result = runner.invoke(
        app,
        ["--json", "migrate", "plan", str(EXAMPLES / "manufacturing-erp-project.yaml")],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)["data"]
    assert payload["assessment"]["project_name"] == "Manufacturing ERP and plant data migration"
    assert payload["assessment"]["domain_pack"] is None
    assert len(payload["assessment"]["transition"]["waves"]) == 3


def test_migrate_verify_closes_and_writes_evidence_pack(tmp_path: Path):
    evidence_pack = tmp_path / "evidence-pack.yaml"

    result = runner.invoke(
        app,
        [
            "migrate",
            "verify",
            str(EXAMPLES / "ph-telco-project.yaml"),
            str(EXAMPLES / "ph-telco-evidence.yaml"),
            "-o",
            str(evidence_pack),
        ],
    )

    assert result.exit_code == 0
    assert "Ready to close" in result.output
    assert evidence_pack.exists()
    assert yaml.safe_load(evidence_pack.read_text())["closed"] is True


def test_migrate_verify_returns_nonzero_for_missing_blocking_evidence(tmp_path: Path):
    blocked_evidence = tmp_path / "blocked-evidence.yaml"
    evidence = yaml.safe_load((EXAMPLES / "ph-telco-evidence.yaml").read_text())
    evidence["observations"] = [
        item for item in evidence["observations"] if item["criterion_id"] != "subscriber-record-parity"
    ]
    blocked_evidence.write_text(yaml.safe_dump(evidence, sort_keys=False))

    result = runner.invoke(
        app,
        ["--json", "migrate", "verify", str(EXAMPLES / "ph-telco-project.yaml"), str(blocked_evidence)],
    )

    assert result.exit_code == 2
    payload = json.loads(result.output)["data"]
    assert payload["evidence_pack"]["closed"] is False
    assert payload["evidence_pack"]["blocking_failures"] == 1


def test_migrate_verify_rejects_a_client_supplied_assessment(tmp_path: Path):
    forged_assessment = tmp_path / "forged-assessment.yaml"
    forged_assessment.write_text(
        yaml.safe_dump(
            {
                "project_name": "prod-cutover",
                "transition": {
                    "project_name": "prod-cutover",
                    "complete": True,
                    "waves": [],
                    "economics": {},
                },
                "assurance": {"criteria": []},
            }
        )
    )
    evidence = tmp_path / "evidence.yaml"
    evidence.write_text(yaml.safe_dump({"project_name": "prod-cutover", "observations": []}))

    result = runner.invoke(app, ["migrate", "verify", str(forged_assessment), str(evidence)])

    assert result.exit_code != 0
    assert "Ready to close" not in result.output


def test_migrate_demo_runs_packaged_project_in_human_and_json_modes():
    human = runner.invoke(app, ["migrate", "demo"])
    machine = runner.invoke(app, ["--json", "migrate", "demo"])

    assert human.exit_code == 0
    assert "Ready to close" in human.output
    assert "5 waves" in human.output
    assert machine.exit_code == 0
    payload = json.loads(machine.output)["data"]
    assert payload["assessment"]["domain_pack"] == "ph_telco"
    assert payload["evidence_pack"]["closed"] is True


def test_migrate_demo_streams_one_compact_ndjson_record():
    result = runner.invoke(app, ["--json", "--stream", "migrate", "demo"])

    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert len(lines) == 1
    assert lines[0] == lines[0].strip()
    decoded = json.loads(lines[0])
    assert json.dumps(decoded, separators=(",", ":")) == lines[0]
    payload = decoded["data"]
    assert payload["evidence_pack"]["closed"] is True


def test_migrate_plan_rejects_more_than_200_source_assets(tmp_path: Path):
    project_file = tmp_path / "oversized.yaml"
    project_file.write_text(
        yaml.safe_dump(
            {
                "name": "Oversized move",
                "evidence_not_before": "2026-08-24T00:00:00Z",
                "estate": {
                    "name": "Current",
                    "assets": [
                        {"id": f"asset-{index}", "name": f"Asset {index}", "kind": "application"}
                        for index in range(201)
                    ],
                },
                "target": {
                    "name": "Target",
                    "mappings": [
                        {"source_asset_id": f"asset-{index}", "disposition": "retain"} for index in range(201)
                    ],
                },
            }
        )
    )

    result = runner.invoke(app, ["migrate", "plan", str(project_file)])

    assert result.exit_code == 1
    assert "201 source assets" in result.output


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="named pipes are not available")
def test_migrate_plan_rejects_named_pipe_input(tmp_path: Path):
    project_file = tmp_path / "project.yaml"
    os.mkfifo(project_file)

    result = runner.invoke(app, ["migrate", "plan", str(project_file)])

    assert result.exit_code == 1
    assert "regular file" in result.output


def test_migrate_output_write_does_not_follow_swapped_symlink(tmp_path: Path, monkeypatch):
    output = tmp_path / "assessment.yaml"
    output.write_text("old assessment")
    protected = tmp_path / "protected.txt"
    protected.write_text("keep me")

    def swap_output_for_symlink(path: Path, directory_descriptor: int, ctx) -> bool:
        path.unlink()
        path.symlink_to(protected)
        return True

    monkeypatch.setattr(migrate_cmd, "_confirm_output_overwrite", swap_output_for_symlink)

    result = runner.invoke(
        app,
        ["migrate", "plan", str(EXAMPLES / "manufacturing-erp-project.yaml"), "-o", str(output)],
    )

    assert result.exit_code == 0
    assert protected.read_text() == "keep me"
    assert output.is_symlink() is False
    assert yaml.safe_load(output.read_text())["project_name"] == "Manufacturing ERP and plant data migration"


def test_migrate_output_write_stays_bound_to_validated_directory(tmp_path: Path, monkeypatch):
    output_directory = tmp_path / "output"
    output_directory.mkdir()
    output = output_directory / "assessment.yaml"
    output.write_text("old assessment")
    moved_directory = tmp_path / "validated-output"
    redirected_directory = tmp_path / "redirected-output"
    redirected_directory.mkdir()
    redirected_output = redirected_directory / "assessment.yaml"
    redirected_output.write_text("keep me")

    def replace_parent_with_symlink(path: Path, directory_descriptor: int, ctx) -> bool:
        output_directory.rename(moved_directory)
        output_directory.symlink_to(redirected_directory, target_is_directory=True)
        return True

    monkeypatch.setattr(migrate_cmd, "_confirm_output_overwrite", replace_parent_with_symlink)

    result = runner.invoke(
        app,
        ["migrate", "plan", str(EXAMPLES / "manufacturing-erp-project.yaml"), "-o", str(output)],
    )

    assert result.exit_code == 0
    assert redirected_output.read_text() == "keep me"
    assert yaml.safe_load((moved_directory / "assessment.yaml").read_text())["project_name"] == (
        "Manufacturing ERP and plant data migration"
    )
