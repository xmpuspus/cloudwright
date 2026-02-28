"""Tests for FedRAMP Moderate and GDPR compliance validators."""

from __future__ import annotations

from cloudwright.spec import ArchSpec, Component, Connection, Constraints
from cloudwright.validator import Validator

# Fixtures


def _fedramp_compliant_spec() -> ArchSpec:
    return ArchSpec(
        name="FedRAMP App",
        provider="aws",
        region="us-east-1",
        constraints=Constraints(
            compliance=["fedramp"],
            regions=["us-east-1"],
        ),
        components=[
            Component(id="alb", service="alb", provider="aws", label="ALB", tier=1),
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web",
                tier=2,
            ),
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="RDS",
                tier=3,
                config={"encryption": True, "multi_az": True, "region": "us-east-1"},
            ),
            Component(id="logs", service="cloudtrail", provider="aws", label="CloudTrail", tier=4),
            Component(id="monitor", service="cloudwatch", provider="aws", label="CloudWatch", tier=4),
            Component(id="auth", service="cognito", provider="aws", label="Cognito", tier=0),
            Component(id="alerts", service="sns", provider="aws", label="SNS", tier=4),
        ],
        connections=[
            Connection(source="alb", target="web", protocol="HTTPS", port=443),
            Connection(source="web", target="db", protocol="TLS", port=5432),
        ],
    )


def _fedramp_failing_spec() -> ArchSpec:
    """Spec with non-US region, unencrypted store, no auth, no logging, no alerting."""
    return ArchSpec(
        name="FedRAMP Failing",
        provider="aws",
        region="eu-west-1",
        constraints=Constraints(regions=["eu-west-1"]),
        components=[
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="RDS",
                tier=3,
                # no encryption
            ),
        ],
        connections=[],
    )


def _gdpr_compliant_spec() -> ArchSpec:
    return ArchSpec(
        name="GDPR App",
        provider="aws",
        region="eu-west-1",
        constraints=Constraints(
            compliance=["gdpr"],
            regions=["eu-west-1"],
        ),
        components=[
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="RDS",
                tier=3,
                config={"encryption": True, "ttl": 90, "region": "eu-west-1"},
            ),
            Component(id="logs", service="cloudwatch", provider="aws", label="CloudWatch", tier=4),
            Component(id="auth", service="cognito", provider="aws", label="Cognito", tier=0),
        ],
        connections=[
            Connection(source="auth", target="db", protocol="HTTPS", port=443),
        ],
    )


def _gdpr_failing_spec() -> ArchSpec:
    """Spec in US region, unencrypted store, plain HTTP, no auth, no logging, no TTL."""
    return ArchSpec(
        name="GDPR Failing",
        provider="aws",
        region="us-east-1",
        constraints=Constraints(regions=["us-east-1"]),
        components=[
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="RDS",
                tier=3,
                # no encryption, no lifecycle/ttl
            ),
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
        ],
        connections=[
            Connection(source="web", target="db", protocol="HTTP", port=80),
        ],
    )


# FedRAMP tests


class TestFedRAMPValidator:
    def test_compliant_spec_returns_fedramp_result(self):
        results = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])
        assert len(results) == 1
        assert results[0].framework == "FedRAMP Moderate"

    def test_compliant_spec_has_seven_checks(self):
        results = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])
        assert len(results[0].checks) == 7

    def test_compliant_spec_passes_all_critical(self):
        result = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0]
        critical_failures = [c for c in result.checks if c.severity == "critical" and not c.passed]
        assert critical_failures == [], f"Critical failures: {[c.name for c in critical_failures]}"

    def test_fips_encryption_passes_with_encrypted_stores(self):
        result = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "fips_encryption")
        assert check.passed

    def test_fips_encryption_fails_without_encryption(self):
        result = Validator().validate(_fedramp_failing_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "fips_encryption")
        assert not check.passed
        assert check.severity == "critical"

    def test_authorized_regions_passes_with_us_region(self):
        result = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "authorized_regions")
        assert check.passed

    def test_authorized_regions_fails_with_eu_region(self):
        result = Validator().validate(_fedramp_failing_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "authorized_regions")
        assert not check.passed
        assert check.severity == "critical"
        assert "eu-west-1" in check.detail

    def test_authorized_regions_accepts_govcloud(self):
        spec = ArchSpec(
            name="GovCloud App",
            provider="aws",
            region="us-gov-east-1",
            constraints=Constraints(regions=["us-gov-east-1"]),
            components=[
                Component(
                    id="db",
                    service="rds",
                    provider="aws",
                    label="RDS",
                    tier=3,
                    config={"encryption": True},
                ),
                Component(id="auth", service="cognito", provider="aws", label="Cognito", tier=0),
                Component(id="trail", service="cloudtrail", provider="aws", label="Trail", tier=4),
                Component(id="alerts", service="sns", provider="aws", label="SNS", tier=4),
            ],
            connections=[],
        )
        result = Validator().validate(spec, compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "authorized_regions")
        assert check.passed

    def test_multi_factor_auth_passes_with_cognito(self):
        result = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "multi_factor_auth")
        assert check.passed

    def test_multi_factor_auth_fails_without_auth_service(self):
        result = Validator().validate(_fedramp_failing_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "multi_factor_auth")
        assert not check.passed
        assert check.severity == "critical"

    def test_audit_logging_passes_with_cloudtrail(self):
        result = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "audit_logging")
        assert check.passed

    def test_audit_logging_fails_without_logging_service(self):
        result = Validator().validate(_fedramp_failing_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "audit_logging")
        assert not check.passed
        assert check.severity == "critical"

    def test_access_control_passes_with_iam(self):
        result = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "access_control")
        assert check.passed
        assert check.severity == "high"

    def test_continuous_monitoring_passes_with_cloudwatch(self):
        result = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "continuous_monitoring")
        assert check.passed
        assert check.severity == "high"

    def test_continuous_monitoring_fails_without_monitoring_service(self):
        result = Validator().validate(_fedramp_failing_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "continuous_monitoring")
        assert not check.passed

    def test_incident_response_passes_with_sns(self):
        result = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "incident_response")
        assert check.passed
        assert check.severity == "medium"

    def test_incident_response_fails_without_alerting(self):
        result = Validator().validate(_fedramp_failing_spec(), compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "incident_response")
        assert not check.passed

    def test_failing_spec_overall_not_passed(self):
        result = Validator().validate(_fedramp_failing_spec(), compliance=["fedramp"])[0]
        assert not result.passed

    def test_score_is_fraction(self):
        result = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0]
        assert 0.0 <= result.score <= 1.0

    def test_score_is_lower_for_failing_spec(self):
        passing = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp"])[0].score
        failing = Validator().validate(_fedramp_failing_spec(), compliance=["fedramp"])[0].score
        assert failing < passing

    def test_fedramp_combined_with_hipaa(self):
        results = Validator().validate(_fedramp_compliant_spec(), compliance=["fedramp", "hipaa"])
        frameworks = {r.framework for r in results}
        assert "FedRAMP Moderate" in frameworks
        assert "HIPAA" in frameworks

    def test_spec_region_fallback_when_no_constraints(self):
        """When no constraints.regions set, spec.region is used for region check."""
        spec = ArchSpec(
            name="No Constraints",
            provider="aws",
            region="us-west-2",
            components=[
                Component(
                    id="db",
                    service="rds",
                    provider="aws",
                    label="RDS",
                    tier=3,
                    config={"encryption": True},
                ),
                Component(id="auth", service="cognito", provider="aws", label="Auth", tier=0),
                Component(id="trail", service="cloudtrail", provider="aws", label="Trail", tier=4),
                Component(id="alerts", service="sns", provider="aws", label="SNS", tier=4),
            ],
            connections=[],
        )
        result = Validator().validate(spec, compliance=["fedramp"])[0]
        check = next(c for c in result.checks if c.name == "authorized_regions")
        assert check.passed


# GDPR tests


class TestGDPRValidator:
    def test_compliant_spec_returns_gdpr_result(self):
        results = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])
        assert len(results) == 1
        assert results[0].framework == "GDPR"

    def test_compliant_spec_has_six_checks(self):
        results = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])
        assert len(results[0].checks) == 6

    def test_compliant_spec_passes_all_critical(self):
        result = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])[0]
        critical_failures = [c for c in result.checks if c.severity == "critical" and not c.passed]
        assert critical_failures == [], f"Critical failures: {[c.name for c in critical_failures]}"

    def test_data_residency_passes_with_eu_region(self):
        result = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "data_residency")
        assert check.passed

    def test_data_residency_fails_with_us_region(self):
        result = Validator().validate(_gdpr_failing_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "data_residency")
        assert not check.passed
        assert check.severity == "critical"
        assert "us-east-1" in check.detail

    def test_data_residency_accepts_multiple_eu_regions(self):
        spec = ArchSpec(
            name="Multi EU",
            provider="aws",
            region="eu-central-1",
            constraints=Constraints(regions=["eu-central-1", "eu-west-2"]),
            components=[
                Component(
                    id="db",
                    service="rds",
                    provider="aws",
                    label="RDS",
                    tier=3,
                    config={"encryption": True, "ttl": 30},
                ),
                Component(id="auth", service="cognito", provider="aws", label="Auth", tier=0),
                Component(id="logs", service="cloudwatch", provider="aws", label="CW", tier=4),
            ],
            connections=[],
        )
        result = Validator().validate(spec, compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "data_residency")
        assert check.passed

    def test_encryption_at_rest_passes_with_encrypted_store(self):
        result = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "encryption_at_rest")
        assert check.passed

    def test_encryption_at_rest_fails_without_encryption(self):
        result = Validator().validate(_gdpr_failing_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "encryption_at_rest")
        assert not check.passed
        assert check.severity == "critical"

    def test_encryption_in_transit_passes_with_https(self):
        result = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "encryption_in_transit")
        assert check.passed

    def test_encryption_in_transit_fails_with_plain_http(self):
        result = Validator().validate(_gdpr_failing_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "encryption_in_transit")
        assert not check.passed
        assert check.severity == "critical"

    def test_encryption_in_transit_passes_with_no_connections(self):
        spec = ArchSpec(
            name="No Connections",
            provider="aws",
            region="eu-west-1",
            constraints=Constraints(regions=["eu-west-1"]),
            components=[
                Component(
                    id="db",
                    service="rds",
                    provider="aws",
                    label="RDS",
                    tier=3,
                    config={"encryption": True, "ttl": 30},
                ),
                Component(id="auth", service="cognito", provider="aws", label="Auth", tier=0),
                Component(id="logs", service="cloudwatch", provider="aws", label="CW", tier=4),
            ],
            connections=[],
        )
        result = Validator().validate(spec, compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "encryption_in_transit")
        assert check.passed

    def test_access_controls_passes_with_cognito(self):
        result = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "access_controls")
        assert check.passed
        assert check.severity == "high"

    def test_access_controls_fails_without_auth_service(self):
        result = Validator().validate(_gdpr_failing_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "access_controls")
        assert not check.passed

    def test_audit_trail_passes_with_cloudwatch(self):
        result = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "audit_trail")
        assert check.passed
        assert check.severity == "high"

    def test_audit_trail_fails_without_logging_service(self):
        result = Validator().validate(_gdpr_failing_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "audit_trail")
        assert not check.passed

    def test_data_deletion_passes_with_ttl_in_config(self):
        result = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "data_deletion_capability")
        assert check.passed
        assert check.severity == "medium"

    def test_data_deletion_passes_with_lifecycle_config(self):
        spec = ArchSpec(
            name="Lifecycle App",
            provider="aws",
            region="eu-west-1",
            constraints=Constraints(regions=["eu-west-1"]),
            components=[
                Component(
                    id="bucket",
                    service="s3",
                    provider="aws",
                    label="S3",
                    tier=3,
                    config={"encryption": True, "lifecycle": {"expiration_days": 365}},
                ),
                Component(id="auth", service="cognito", provider="aws", label="Auth", tier=0),
                Component(id="logs", service="cloudwatch", provider="aws", label="CW", tier=4),
            ],
            connections=[],
        )
        result = Validator().validate(spec, compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "data_deletion_capability")
        assert check.passed

    def test_data_deletion_passes_with_retention_days(self):
        spec = ArchSpec(
            name="Retention App",
            provider="aws",
            region="eu-west-1",
            constraints=Constraints(regions=["eu-west-1"]),
            components=[
                Component(
                    id="db",
                    service="rds",
                    provider="aws",
                    label="RDS",
                    tier=3,
                    config={"encryption": True, "retention_days": 30},
                ),
                Component(id="auth", service="cognito", provider="aws", label="Auth", tier=0),
                Component(id="logs", service="cloudwatch", provider="aws", label="CW", tier=4),
            ],
            connections=[],
        )
        result = Validator().validate(spec, compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "data_deletion_capability")
        assert check.passed

    def test_data_deletion_fails_without_lifecycle_or_ttl(self):
        result = Validator().validate(_gdpr_failing_spec(), compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "data_deletion_capability")
        assert not check.passed

    def test_failing_spec_overall_not_passed(self):
        result = Validator().validate(_gdpr_failing_spec(), compliance=["gdpr"])[0]
        assert not result.passed

    def test_score_is_fraction(self):
        result = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])[0]
        assert 0.0 <= result.score <= 1.0

    def test_score_is_lower_for_failing_spec(self):
        passing = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr"])[0].score
        failing = Validator().validate(_gdpr_failing_spec(), compliance=["gdpr"])[0].score
        assert failing < passing

    def test_gdpr_combined_with_soc2(self):
        results = Validator().validate(_gdpr_compliant_spec(), compliance=["gdpr", "soc2"])
        frameworks = {r.framework for r in results}
        assert "GDPR" in frameworks
        assert "SOC 2" in frameworks

    def test_gdpr_case_insensitive(self):
        results = Validator().validate(_gdpr_compliant_spec(), compliance=["GDPR"])
        assert results[0].framework == "GDPR"

    def test_fedramp_case_insensitive(self):
        results = Validator().validate(_fedramp_compliant_spec(), compliance=["FEDRAMP"])
        assert results[0].framework == "FedRAMP Moderate"

    def test_spec_region_fallback_when_no_constraints(self):
        """When no constraints.regions set, spec.region is used for data residency."""
        spec = ArchSpec(
            name="No Constraints EU",
            provider="aws",
            region="eu-north-1",
            components=[
                Component(
                    id="db",
                    service="rds",
                    provider="aws",
                    label="RDS",
                    tier=3,
                    config={"encryption": True, "ttl": 30},
                ),
                Component(id="auth", service="cognito", provider="aws", label="Auth", tier=0),
                Component(id="logs", service="cloudwatch", provider="aws", label="CW", tier=4),
            ],
            connections=[],
        )
        result = Validator().validate(spec, compliance=["gdpr"])[0]
        check = next(c for c in result.checks if c.name == "data_residency")
        assert check.passed
