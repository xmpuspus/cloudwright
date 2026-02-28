"""Tests for the icon registry — coverage, shapes, colors, lookups."""

import pytest
from cloudwright.icons import (
    ICON_REGISTRY,
    VALID_SHAPES,
    ServiceIcon,
    get_category_color,
    get_icon,
    get_icon_or_default,
    get_icon_url,
)


def test_known_services_have_icons():
    """All services in the terraform.py resource maps should have registry entries."""
    from cloudwright.exporter.terraform import _AWS_RESOURCES, _AZURE_RESOURCES, _GCP_RESOURCES

    missing = []
    for svc in _AWS_RESOURCES:
        if ("aws", svc) not in ICON_REGISTRY:
            missing.append(f"aws/{svc}")
    for svc in _GCP_RESOURCES:
        if ("gcp", svc) not in ICON_REGISTRY:
            missing.append(f"gcp/{svc}")
    for svc in _AZURE_RESOURCES:
        if ("azure", svc) not in ICON_REGISTRY:
            missing.append(f"azure/{svc}")
    assert not missing, f"Missing icon registry entries: {missing}"


def test_get_icon_returns_none_for_unknown():
    assert get_icon("aws", "nonexistent_service_xyz") is None
    assert get_icon("unknown_provider", "ec2") is None


def test_get_icon_or_default_returns_fallback():
    icon = get_icon_or_default("aws", "nonexistent_service_xyz")
    assert icon is not None
    assert icon.shape in VALID_SHAPES


def test_get_icon_or_default_known():
    icon = get_icon_or_default("aws", "ec2")
    assert icon.service == "ec2"
    assert icon.provider == "aws"
    assert icon.category == "compute"


def test_all_icons_have_valid_shape():
    for key, icon in ICON_REGISTRY.items():
        assert icon.shape in VALID_SHAPES, f"Invalid shape for {key}: {icon.shape}"


def test_category_color_mapping():
    for cat in ("compute", "database", "storage", "network", "security", "serverless", "cache", "queue"):
        color = get_category_color(cat)
        assert color.startswith("#"), f"Category {cat} color should be hex: {color}"


def test_category_color_unknown_returns_default():
    color = get_category_color("nonexistent_category")
    assert color == "#94a3b8"


def test_icon_url_format():
    url = get_icon_url("aws", "ec2")
    assert url.startswith("https://")
    assert "ec2" in url
    assert "aws" in url


def test_registry_has_all_providers():
    providers = {icon.provider for icon in ICON_REGISTRY.values()}
    assert "aws" in providers
    assert "gcp" in providers
    assert "azure" in providers
    assert "generic" in providers


def test_database_services_have_cylinder_shape():
    db_services = [
        ("aws", "rds"),
        ("aws", "dynamodb"),
        ("gcp", "cloud_sql"),
        ("azure", "azure_sql"),
        ("azure", "cosmos_db"),
    ]
    for provider, svc in db_services:
        icon = get_icon(provider, svc)
        assert icon is not None, f"Missing icon for {provider}/{svc}"
        assert icon.shape == "cylinder", f"{provider}/{svc} should be cylinder, got {icon.shape}"


def test_serverless_services_have_hexagon_shape():
    serverless_services = [
        ("aws", "lambda"),
        ("aws", "api_gateway"),
        ("gcp", "cloud_functions"),
        ("gcp", "cloud_run"),
        ("azure", "azure_functions"),
    ]
    for provider, svc in serverless_services:
        icon = get_icon(provider, svc)
        assert icon is not None, f"Missing icon for {provider}/{svc}"
        assert icon.shape == "hexagon", f"{provider}/{svc} should be hexagon, got {icon.shape}"


def test_network_services_have_stadium_shape():
    network_services = [
        ("aws", "alb"),
        ("aws", "nlb"),
        ("gcp", "cloud_load_balancing"),
        ("azure", "app_gateway"),
    ]
    for provider, svc in network_services:
        icon = get_icon(provider, svc)
        assert icon is not None, f"Missing icon for {provider}/{svc}"
        assert icon.shape == "stadium", f"{provider}/{svc} should be stadium, got {icon.shape}"


def test_service_icon_rejects_invalid_shape():
    with pytest.raises(ValueError, match="Invalid shape"):
        ServiceIcon(
            provider="aws",
            service="test",
            category="compute",
            label="Test",
            shape="triangle",
        )
