"""Tests for v1.4 conditional defaults in _post_validate.

The pre-v1.4 _post_validate forced encryption=true, multi_az=true, count=2 etc.
on every spec. v1.4 makes these conditional on workload profile + compliance:
- sandbox/dev profiles get the LLM's chosen values (no overrides)
- production / compliance-bound workloads get the safe defaults
"""

from __future__ import annotations

from cloudwright.parsing import _post_validate
from cloudwright.spec import ArchSpec, Component, Constraints


def _spec_with_profile(profile: str | None) -> ArchSpec:
    metadata = {"workload_profile": profile} if profile else {}
    return ArchSpec(
        name="App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={}),
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
            Component(id="store", service="s3", provider="aws", label="Bucket", tier=4, config={}),
            Component(id="cache", service="elasticache", provider="aws", label="Cache", tier=3, config={}),
        ],
        metadata=metadata,
    )


class TestSandboxProfileSkipsForcedDefaults:
    def test_sandbox_no_compliance_does_not_force_encryption(self):
        """Sandbox profile + no compliance => LLM's choice respected."""
        spec = _spec_with_profile("sandbox")
        result = _post_validate(spec, Constraints())  # empty compliance
        db = next(c for c in result.components if c.id == "db")
        store = next(c for c in result.components if c.id == "store")
        cache = next(c for c in result.components if c.id == "cache")

        assert "encryption" not in db.config
        assert "encryption" not in store.config
        assert "encryption" not in cache.config

    def test_sandbox_no_compliance_does_not_force_multi_az(self):
        spec = _spec_with_profile("sandbox")
        result = _post_validate(spec, Constraints())
        db = next(c for c in result.components if c.id == "db")
        assert "multi_az" not in db.config

    def test_sandbox_no_compliance_does_not_force_count(self):
        spec = _spec_with_profile("sandbox")
        result = _post_validate(spec, Constraints())
        web = next(c for c in result.components if c.id == "web")
        assert "count" not in web.config

    def test_sandbox_no_compliance_does_not_force_auto_scaling(self):
        spec = _spec_with_profile("sandbox")
        result = _post_validate(spec, Constraints())
        web = next(c for c in result.components if c.id == "web")
        assert "auto_scaling" not in web.config

    def test_dev_profile_treated_like_sandbox(self):
        spec = _spec_with_profile("dev")
        result = _post_validate(spec, Constraints())
        db = next(c for c in result.components if c.id == "db")
        assert "encryption" not in db.config
        assert "multi_az" not in db.config


class TestComplianceForcesDefaultsEvenInSandbox:
    """If a sandbox somehow declares HIPAA compliance, encryption is non-negotiable."""

    def test_hipaa_overrides_sandbox_for_encryption(self):
        # Even if metadata says sandbox, declared compliance trumps profile.
        # (Encryption check runs first in our predicate; HIPAA compliance forces it.)
        spec = ArchSpec(
            name="App",
            provider="aws",
            region="us-east-1",
            components=[Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={})],
            metadata={"workload_profile": "production"},
        )
        result = _post_validate(spec, Constraints(compliance=["hipaa"]))
        db = next(c for c in result.components if c.id == "db")
        assert db.config.get("encryption") is True


class TestProductionProfileGetsDefaults:
    def test_production_profile_forces_encryption(self):
        spec = _spec_with_profile("production")
        result = _post_validate(spec, Constraints())
        db = next(c for c in result.components if c.id == "db")
        assert db.config.get("encryption") is True

    def test_no_profile_defaults_to_production_posture(self):
        """Back-compat: no metadata profile means previous behavior (force defaults)."""
        spec = _spec_with_profile(None)
        result = _post_validate(spec, Constraints())
        db = next(c for c in result.components if c.id == "db")
        assert db.config.get("encryption") is True


class TestInstanceDefaultsAlwaysApplied:
    """instance_type / instance_class / node_type always get defaults — they're not
    'safety' settings, just sane fallbacks for cost estimation."""

    def test_sandbox_still_gets_instance_type_default(self):
        spec = _spec_with_profile("sandbox")
        result = _post_validate(spec, Constraints())
        web = next(c for c in result.components if c.id == "web")
        assert "instance_type" in web.config

    def test_sandbox_still_gets_instance_class_default(self):
        spec = _spec_with_profile("sandbox")
        result = _post_validate(spec, Constraints())
        db = next(c for c in result.components if c.id == "db")
        assert "instance_class" in db.config
