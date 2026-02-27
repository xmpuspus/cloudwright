"""Tests for the compliance validator."""

from silmaril.spec import ArchSpec, Component, Connection, Constraints


def _hipaa_compliant_spec() -> ArchSpec:
    return ArchSpec(
        name="HIPAA App",
        provider="aws",
        region="us-east-1",
        constraints=Constraints(compliance=["hipaa"]),
        components=[
            Component(id="alb", service="alb", provider="aws", label="ALB", tier=1),
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web",
                tier=2,
                config={"encryption": True},
            ),
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="RDS",
                tier=3,
                config={"encryption": True, "multi_az": True, "engine": "postgres"},
            ),
            Component(id="logs", service="cloudwatch", provider="aws", label="CloudWatch", tier=4),
            Component(id="auth", service="cognito", provider="aws", label="Auth", tier=0),
        ],
        connections=[
            Connection(source="alb", target="web", protocol="HTTPS", port=443),
            Connection(source="web", target="db", protocol="TCP", port=5432),
        ],
    )


def _minimal_spec() -> ArchSpec:
    return ArchSpec(
        name="Minimal",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
        ],
        connections=[],
    )


class TestHIPAAValidation:
    def test_compliant_spec_passes(self):
        from silmaril.validator import Validator

        v = Validator()
        results = v.validate(_hipaa_compliant_spec(), compliance=["hipaa"])
        assert len(results) == 1
        hipaa = results[0]
        assert hipaa.framework == "HIPAA"
        # Should have checks
        assert len(hipaa.checks) > 0

    def test_minimal_spec_has_failures(self):
        from silmaril.validator import Validator

        v = Validator()
        results = v.validate(_minimal_spec(), compliance=["hipaa"])
        hipaa = results[0]
        failed = [c for c in hipaa.checks if not c.passed]
        assert len(failed) > 0  # minimal spec can't be HIPAA compliant


class TestWellArchitected:
    def test_well_architected_review(self):
        from silmaril.validator import Validator

        v = Validator()
        results = v.validate(_hipaa_compliant_spec(), well_architected=True)
        wa = [r for r in results if r.framework == "Well-Architected"]
        assert len(wa) == 1
        assert len(wa[0].checks) > 0

    def test_minimal_has_recommendations(self):
        from silmaril.validator import Validator

        v = Validator()
        results = v.validate(_minimal_spec(), well_architected=True)
        wa = [r for r in results if r.framework == "Well-Architected"][0]
        failed = [c for c in wa.checks if not c.passed]
        assert len(failed) > 0


class TestMultipleFrameworks:
    def test_multiple_compliance_frameworks(self):
        from silmaril.validator import Validator

        v = Validator()
        results = v.validate(_hipaa_compliant_spec(), compliance=["hipaa", "soc2"])
        assert len(results) == 2
        frameworks = {r.framework for r in results}
        assert "HIPAA" in frameworks
        assert "SOC 2" in frameworks
