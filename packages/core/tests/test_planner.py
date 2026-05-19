from __future__ import annotations

import shutil
import subprocess
from unittest import mock

import pytest
from cloudwright.planner import PlanResult, plan, plan_pulumi, plan_terraform
from cloudwright.spec import ArchSpec, Component


def _spec() -> ArchSpec:
    return ArchSpec(
        name="PlanTest",
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
            Component(
                id="store",
                service="s3",
                provider="aws",
                label="Store",
                tier=4,
                config={"encryption": True, "backup": True},
            ),
        ],
    )


class TestDispatch:
    def test_unknown_target_raises(self):
        with pytest.raises(ValueError, match="Unknown plan target"):
            plan(_spec(), target="bogus")

    def test_pulumi_missing_binary_graceful(self):
        with mock.patch("cloudwright.planner.shutil.which", return_value=None):
            r = plan_pulumi(_spec(), language="python")
        assert r.available is False
        assert r.ok is False
        assert "pulumi" in r.messages[0].lower()

    def test_terraform_missing_binary_graceful(self):
        with mock.patch("cloudwright.planner.shutil.which", return_value=None):
            r = plan_terraform(_spec())
        assert r.available is False
        assert r.validated is False
        assert "terraform" in r.messages[0].lower()


class TestTerraformPlanParsing:
    def _fake_run(self, *, init_rc=0, val_rc=0, plan_rc=0, plan_out=""):
        def _runner(cmd, cwd, timeout, env=None):
            sub = cmd[1]
            if sub == "init":
                return subprocess.CompletedProcess(cmd, init_rc, "", "")
            if sub == "validate":
                return subprocess.CompletedProcess(cmd, val_rc, "Success! valid.", "")
            if sub == "plan":
                return subprocess.CompletedProcess(cmd, plan_rc, plan_out, "")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        return _runner

    def test_plan_summary_parsed(self):
        out = "Terraform will perform the following actions...\nPlan: 5 to add, 2 to change, 1 to destroy"
        with (
            mock.patch("cloudwright.planner.shutil.which", return_value="/usr/bin/terraform"),
            mock.patch("cloudwright.planner._run", side_effect=self._fake_run(plan_out=out)),
        ):
            r = plan_terraform(_spec())
        assert r.ok and r.validated and r.plan_ran
        assert r.summary == {"add": 5, "change": 2, "destroy": 1}

    def test_no_changes_parsed(self):
        with (
            mock.patch("cloudwright.planner.shutil.which", return_value="/usr/bin/terraform"),
            mock.patch(
                "cloudwright.planner._run",
                side_effect=self._fake_run(plan_out="No changes. Your infrastructure matches the configuration."),
            ),
        ):
            r = plan_terraform(_spec())
        assert r.summary == {"add": 0, "change": 0, "destroy": 0}

    def test_missing_credentials_still_deployable(self):
        err_out = "Error: No valid credential sources found for AWS Provider"
        with (
            mock.patch("cloudwright.planner.shutil.which", return_value="/usr/bin/terraform"),
            mock.patch("cloudwright.planner._run", side_effect=self._fake_run(plan_rc=1, plan_out=err_out)),
        ):
            r = plan_terraform(_spec())
        assert r.validated is True
        assert r.plan_ran is False
        assert r.ok is True  # validate proved deployability
        assert any("credential" in m.lower() for m in r.messages)

    def test_invalid_config_fails(self):
        with (
            mock.patch("cloudwright.planner.shutil.which", return_value="/usr/bin/terraform"),
            mock.patch("cloudwright.planner._run", side_effect=self._fake_run(val_rc=1)),
        ):
            r = plan_terraform(_spec())
        assert r.validated is False
        assert r.ok is False

    def test_init_invalid_config_is_classified(self):
        def _runner(cmd, cwd, timeout, env=None):
            if cmd[1] == "init":
                return subprocess.CompletedProcess(
                    cmd, 1, "", "Error: Argument definition required\n  on main.tf line 114"
                )
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with (
            mock.patch("cloudwright.planner.shutil.which", return_value="/usr/bin/terraform"),
            mock.patch("cloudwright.planner._run", side_effect=_runner),
        ):
            r = plan_terraform(_spec())
        assert r.validated is False and r.ok is False
        assert "generated configuration is invalid" in r.messages[0]
        assert "network" not in r.messages[0].lower()

    def test_init_network_failure_is_classified(self):
        def _runner(cmd, cwd, timeout, env=None):
            if cmd[1] == "init":
                return subprocess.CompletedProcess(cmd, 1, "", "Failed to install provider: dial tcp: timeout")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with (
            mock.patch("cloudwright.planner.shutil.which", return_value="/usr/bin/terraform"),
            mock.patch("cloudwright.planner._run", side_effect=_runner),
        ):
            r = plan_terraform(_spec())
        assert "network" in r.messages[0].lower()

    def test_no_plan_flag_skips_plan(self):
        with (
            mock.patch("cloudwright.planner.shutil.which", return_value="/usr/bin/terraform"),
            mock.patch("cloudwright.planner._run", side_effect=self._fake_run()),
        ):
            r = plan_terraform(_spec(), run_plan=False)
        assert r.validated is True
        assert r.plan_ran is False
        assert r.ok is True

    def test_result_serializes(self):
        r = PlanResult(tool="terraform", available=True, validated=True, plan_ran=False, ok=True)
        d = r.as_dict()
        assert d["tool"] == "terraform" and d["ok"] is True


@pytest.mark.skipif(shutil.which("terraform") is None, reason="terraform not installed")
class TestTerraformIntegration:
    def test_real_validate_passes_on_exported_spec(self):
        # Real terraform init+validate against the actual exported artifact.
        r = plan_terraform(_spec(), run_plan=False, timeout=180)
        assert r.available is True
        assert r.validated is True, r.output_tail
        assert r.ok is True
