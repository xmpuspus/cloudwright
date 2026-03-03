"""Tests for Databricks adapter (mock-only, no live workspace)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_import_guard():
    """DatabricksWorkspaceAdapter raises ImportError without SDK."""
    with patch.dict("sys.modules", {"databricks": None, "databricks.sdk": None}):
        from importlib import reload

        import cloudwright.adapters.databricks as mod

        reload(mod)
        with pytest.raises(ImportError, match="databricks-sdk"):
            mod.DatabricksWorkspaceAdapter(host="https://test.cloud.databricks.com")


def test_pricing_adapter_dbx_rates():
    from cloudwright.adapters.databricks import DatabricksPricingAdapter

    adapter = DatabricksPricingAdapter()
    rates = adapter.fetch_managed_service_pricing("databricks_cluster", "us-east-1")
    assert len(rates) > 0
    all_purpose = [r for r in rates if r.tier_name == "all_purpose"]
    assert len(all_purpose) == 1
    assert all_purpose[0].price_per_hour == 0.40


def test_pricing_adapter_supported_services():
    from cloudwright.adapters.databricks import DatabricksPricingAdapter

    adapter = DatabricksPricingAdapter()
    services = adapter.supported_managed_services()
    assert "databricks_sql_warehouse" in services
    assert "databricks_cluster" in services


def test_pricing_adapter_no_instance_pricing():
    from cloudwright.adapters.databricks import DatabricksPricingAdapter

    adapter = DatabricksPricingAdapter()
    instances = list(adapter.fetch_instance_pricing("us-east-1"))
    assert instances == []


def test_validate_spec_mocked():
    """Mock WorkspaceClient and verify validate_spec logic."""
    mock_client = MagicMock()
    mock_client.warehouses.list.return_value = []
    mock_client.catalogs.list.return_value = []

    with patch("cloudwright.adapters.databricks.DatabricksWorkspaceAdapter.__init__", return_value=None):
        from cloudwright.adapters.databricks import DatabricksWorkspaceAdapter
        from cloudwright.spec import ArchSpec, Component

        adapter = DatabricksWorkspaceAdapter.__new__(DatabricksWorkspaceAdapter)
        adapter._client = mock_client

        spec = ArchSpec(
            name="test",
            provider="databricks",
            components=[
                Component(id="wh", service="databricks_sql_warehouse", provider="databricks", label="WH"),
                Component(id="uc", service="databricks_unity_catalog", provider="databricks", label="UC"),
            ],
        )

        issues = adapter.validate_spec(spec)
        assert len(issues) == 2
        severities = {i["severity"] for i in issues}
        assert "info" in severities or "warning" in severities
