"""Migration CLI contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
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
