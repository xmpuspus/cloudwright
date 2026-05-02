"""FedRAMP region allowlist tests.

The pre-v1.3 validator used ``region.startswith("us-")`` which is wrong:
a US-prefixed region like ``us-iso-east-1`` is NOT FedRAMP-authorized, and
``us-west-1`` is conspicuously NOT in the AWS commercial Moderate scope.

These tests pin the explicit allowlist behavior.
"""

from __future__ import annotations

from cloudwright.spec import ArchSpec, Component, Constraints
from cloudwright.validator import Validator


def _spec(provider: str, region: str) -> ArchSpec:
    return ArchSpec(
        name="App",
        provider=provider,
        region=region,
        constraints=Constraints(regions=[region]),
        components=[
            Component(
                id="db",
                service="rds" if provider == "aws" else "cloud_sql" if provider == "gcp" else "azure_sql",
                provider=provider,
                label="DB",
                tier=3,
                config={"encryption": True},
            ),
            Component(
                id="auth",
                service="cognito" if provider == "aws" else "firebase_auth" if provider == "gcp" else "azure_ad",
                provider=provider,
                label="Auth",
                tier=0,
            ),
            Component(
                id="trail",
                service="cloudtrail"
                if provider == "aws"
                else "cloud_logging"
                if provider == "gcp"
                else "azure_monitor",
                provider=provider,
                label="Trail",
                tier=4,
            ),
            Component(
                id="alerts",
                service="sns" if provider == "aws" else "pub_sub" if provider == "gcp" else "event_hubs",
                provider=provider,
                label="Alerts",
                tier=4,
            ),
        ],
        connections=[],
    )


def _region_check(spec: ArchSpec):
    result = Validator().validate(spec, compliance=["fedramp"])[0]
    return next(c for c in result.checks if c.name == "authorized_regions")


# --- AWS commercial Moderate -----------------------------------------------


def test_us_east_1_is_authorized_for_aws():
    check = _region_check(_spec("aws", "us-east-1"))
    assert check.passed, check.detail


def test_us_east_2_is_authorized_for_aws():
    check = _region_check(_spec("aws", "us-east-2"))
    assert check.passed


def test_us_west_2_is_authorized_for_aws():
    check = _region_check(_spec("aws", "us-west-2"))
    assert check.passed


# --- AWS GovCloud High ------------------------------------------------------


def test_us_gov_west_1_is_authorized_for_aws():
    check = _region_check(_spec("aws", "us-gov-west-1"))
    assert check.passed
    assert check.severity == "critical"


def test_us_gov_east_1_is_authorized_for_aws():
    check = _region_check(_spec("aws", "us-gov-east-1"))
    assert check.passed


# --- Out of scope -----------------------------------------------------------


def test_eu_west_1_is_not_authorized():
    check = _region_check(_spec("aws", "eu-west-1"))
    assert not check.passed
    assert "eu-west-1" in check.detail


def test_us_west_1_is_not_authorized_under_strict_allowlist():
    """us-west-1 is intentionally NOT on the AWS FedRAMP commercial list.

    The old startswith("us-") heuristic accepted this; the new allowlist
    rejects it. This test pins the corrected behavior.
    """
    check = _region_check(_spec("aws", "us-west-1"))
    assert not check.passed
    assert "us-west-1" in check.detail


def test_us_iso_east_1_is_not_authorized():
    """us-iso-* is the AWS Top Secret region, not in the FedRAMP commercial scope."""
    check = _region_check(_spec("aws", "us-iso-east-1"))
    assert not check.passed


# --- GCP --------------------------------------------------------------------


def test_us_central1_is_authorized_for_gcp():
    check = _region_check(_spec("gcp", "us-central1"))
    assert check.passed


def test_europe_west1_is_not_authorized_for_gcp():
    check = _region_check(_spec("gcp", "europe-west1"))
    assert not check.passed


# --- Azure ------------------------------------------------------------------


def test_usgovvirginia_is_authorized_for_azure():
    check = _region_check(_spec("azure", "usgovvirginia"))
    assert check.passed


def test_eastus_is_authorized_for_azure():
    check = _region_check(_spec("azure", "eastus"))
    assert check.passed


def test_northeurope_is_not_authorized_for_azure():
    check = _region_check(_spec("azure", "northeurope"))
    assert not check.passed
