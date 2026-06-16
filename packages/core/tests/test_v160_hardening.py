"""v1.6.0 Tier-0 credibility hardening regressions.

Covers: Terraform exporter injection hardening (numeric coercion + validator),
the WAF multi-line fix, the compliance-overrides-workload-profile invariant, and
the `cloudwright plan` subprocess secret scoping.
"""

import pytest
from cloudwright.exporter import export_spec, validate_export_config
from cloudwright.exporter.terraform.common import _hcl_num
from cloudwright.parsing import _profile_requires_encryption, _profile_requires_ha
from cloudwright.spec import ArchSpec, Component, Constraints


def _spec(component: Component, **meta) -> ArchSpec:
    return ArchSpec(name="t", components=[component], metadata=meta)


class TestNumericCoercion:
    def test_int_string_coerced(self):
        assert _hcl_num("20", 20) == "20"

    def test_real_int_passthrough(self):
        assert _hcl_num(50, 20) == "50"

    def test_uncoercible_falls_back_to_default(self):
        assert _hcl_num("100abc", 20) == "20"
        assert _hcl_num(None, 7) == "7"
        assert _hcl_num({"x": 1}, 3) == "3"

    def test_float_truncated_when_int_required(self):
        assert _hcl_num("20.9", 20) == "20"


class TestExportValidator:
    def test_rejects_newline_brace_injection(self):
        payload = '20\n  provisioner "local-exec" {\n    command = "id"\n  }'
        with pytest.raises(ValueError):
            validate_export_config({"allocated_storage": payload})

    def test_rejects_bare_braces(self):
        with pytest.raises(ValueError):
            validate_export_config({"x": "a{b}"})

    def test_allows_clean_scalar(self):
        validate_export_config({"engine": "postgres", "instance_class": "db.t3.medium"})


class TestExporterInjectionProof:
    def test_string_numeric_field_is_coerced_not_injected(self):
        # A string value that survives the validator (no metachars) must still be
        # emitted as a number, never as raw HCL.
        spec = _spec(
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="DB",
                tier=3,
                config={"engine": "postgres", "allocated_storage": "9999"},
            )
        )
        tf = export_spec(spec, "terraform")
        assert "allocated_storage       = 9999" in tf
        assert "provisioner" not in tf
        assert "local-exec" not in tf

    def test_waf_default_action_is_multiline(self):
        spec = _spec(Component(id="acl", service="waf", provider="aws", label="ACL", tier=1))
        tf = export_spec(spec, "terraform")
        # single-line nested block is what Terraform rejects
        assert "default_action { allow {} }" not in tf
        assert "default_action {\n    allow {}" in tf


class TestComplianceOverridesProfile:
    def test_sandbox_plus_hipaa_forces_encryption_and_ha(self):
        spec = _spec(
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
            workload_profile="sandbox",
        )
        c = Constraints(compliance=["hipaa"])
        assert _profile_requires_encryption(spec, c) is True
        assert _profile_requires_ha(spec, c) is True

    def test_plain_sandbox_does_not_force(self):
        spec = _spec(
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
            workload_profile="sandbox",
        )
        c = Constraints(compliance=[])
        assert _profile_requires_encryption(spec, c) is False
        assert _profile_requires_ha(spec, c) is False


class TestOpenTofuParity:
    def test_opentofu_format_matches_terraform(self):
        spec = _spec(Component(id="web", service="ec2", provider="aws", label="Web", tier=2))
        assert export_spec(spec, "opentofu") == export_spec(spec, "terraform")
        assert export_spec(spec, "tofu") == export_spec(spec, "terraform")

    def test_binary_resolution_prefers_override(self, monkeypatch, tmp_path):
        from cloudwright import planner

        fake = tmp_path / "tofu"
        fake.write_text("#!/bin/sh\n")
        fake.chmod(0o755)
        monkeypatch.setenv("CLOUDWRIGHT_TF_BINARY", str(fake))
        path, label = planner._terraform_binary()
        assert label == "opentofu"
        assert path == str(fake)


class TestPlanSecretScoping:
    def test_subprocess_env_strips_llm_key(self, monkeypatch):
        from cloudwright import planner

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value-1234")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAEXAMPLE")
        env = planner._subprocess_env()
        assert "ANTHROPIC_API_KEY" not in env
        assert env.get("AWS_ACCESS_KEY_ID") == "AKIAEXAMPLE"

    def test_scrub_redacts_secret_values(self, monkeypatch):
        from cloudwright import planner

        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "verylongsecretvalue0987654321")
        out = planner._scrub("error using verylongsecretvalue0987654321 to auth")
        assert "verylongsecretvalue0987654321" not in out
        assert "REDACTED" in out
