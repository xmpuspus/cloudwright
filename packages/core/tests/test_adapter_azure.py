"""Tests for the Azure pricing adapter.

All HTTP calls are mocked — no network access required.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from cloudwright.adapters import InstancePrice, PricingAdapter
from cloudwright.adapters.azure import AzurePricingAdapter, _safe_float

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _azure_item(
    arm_sku: str,
    sku_name: str,
    product_name: str,
    service_name: str,
    meter_name: str,
    price: float,
    region: str = "eastus",
) -> dict[str, Any]:
    return {
        "armSkuName": arm_sku,
        "skuName": sku_name,
        "productName": product_name,
        "serviceName": service_name,
        "meterName": meter_name,
        "retailPrice": price,
        "armRegionName": region,
        "priceType": "Consumption",
    }


_VM_ITEMS = [
    _azure_item("Standard_D2s_v5", "D2s v5", "Virtual Machines DSv5 Series Linux", "Virtual Machines", "D2s v5", 0.096),
    _azure_item("Standard_D4s_v5", "D4s v5", "Virtual Machines DSv5 Series Linux", "Virtual Machines", "D4s v5", 0.192),
    _azure_item(
        "Standard_D2s_v5",
        "D2s v5 Spot",
        "Virtual Machines DSv5 Series Windows",
        "Virtual Machines",
        "D2s v5 Spot",
        0.020,
    ),
]

_FUNCTIONS_ITEMS = [
    _azure_item("", "Execution Time", "Azure Functions", "Azure Functions", "Execution", 0.0000002, "eastus"),
    _azure_item("", "First 400,000 GB/s", "Azure Functions", "Azure Functions", "GB Second", 0.0000166667, "eastus"),
]

_BLOB_ITEMS = [
    _azure_item("LRS", "LRS", "Blob Storage LRS", "Storage", "LRS Data Stored", 0.018, "eastus"),
]

_SQL_ITEMS = [
    _azure_item(
        "", "General Purpose", "Azure SQL Database General Purpose", "Azure SQL Database", "vCore", 0.1688, "eastus"
    ),
]

_COSMOS_ITEMS = [
    _azure_item(
        "", "100 RU/s", "Azure Cosmos DB Request Units", "Azure Cosmos DB", "100 Request Units", 0.00012, "eastus"
    ),
    _azure_item("", "Storage", "Azure Cosmos DB Storage", "Azure Cosmos DB", "Data Storage", 0.25, "eastus"),
]


def _mock_adapter(items: list[dict]) -> AzurePricingAdapter:
    """Return adapter with _get mocked to return the given items."""
    adapter = AzurePricingAdapter()
    payload = json.dumps({"Items": items, "NextPageLink": None}).encode()
    adapter._get = lambda url: payload
    return adapter


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_safe_float_normal(self):
        assert _safe_float(0.096) == pytest.approx(0.096)

    def test_safe_float_string(self):
        assert _safe_float("0.192") == pytest.approx(0.192)

    def test_safe_float_invalid(self):
        assert _safe_float("N/A") == 0.0

    def test_safe_float_none(self):
        assert _safe_float(None) == 0.0


# ---------------------------------------------------------------------------
# ABC conformance
# ---------------------------------------------------------------------------


class TestPricingAdapterABC:
    def test_implements_abc(self):
        adapter = AzurePricingAdapter()
        assert isinstance(adapter, PricingAdapter)

    def test_provider_attribute(self):
        assert AzurePricingAdapter.provider == "azure"

    def test_supported_managed_services(self):
        adapter = AzurePricingAdapter()
        svcs = adapter.supported_managed_services()
        assert set(svcs) == {"azure_functions", "blob_storage", "azure_sql", "cosmos_db"}


# ---------------------------------------------------------------------------
# VM instance pricing
# ---------------------------------------------------------------------------


class TestVMParsing:
    def test_yields_instance_prices(self):
        adapter = _mock_adapter(_VM_ITEMS)
        results = list(adapter.fetch_instance_pricing("eastus"))
        assert len(results) > 0
        assert all(isinstance(r, InstancePrice) for r in results)

    def test_filters_spot_items(self):
        adapter = _mock_adapter(_VM_ITEMS)
        results = list(adapter.fetch_instance_pricing("eastus"))
        assert all("Spot" not in r.instance_type for r in results)

    def test_correct_prices(self):
        adapter = _mock_adapter(_VM_ITEMS)
        results = list(adapter.fetch_instance_pricing("eastus"))
        prices = {r.instance_type: r.price_per_hour for r in results}
        assert prices.get("Standard_D2s_v5") == pytest.approx(0.096)
        assert prices.get("Standard_D4s_v5") == pytest.approx(0.192)

    def test_region_stored_on_price(self):
        adapter = _mock_adapter(_VM_ITEMS)
        results = list(adapter.fetch_instance_pricing("eastus"))
        assert all(r.region == "eastus" for r in results)

    def test_price_type_is_on_demand(self):
        adapter = _mock_adapter(_VM_ITEMS)
        results = list(adapter.fetch_instance_pricing("eastus"))
        assert all(r.price_type == "on_demand" for r in results)

    def test_skips_zero_price(self):
        zero_items = [_azure_item("Standard_A0", "A0", "VMs", "Virtual Machines", "A0", 0.0)]
        adapter = _mock_adapter(zero_items)
        results = list(adapter.fetch_instance_pricing("eastus"))
        assert results == []


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    def test_follows_next_page_link(self):
        page1 = {"Items": [_VM_ITEMS[0]], "NextPageLink": "https://page2.example.com"}
        page2 = {"Items": [_VM_ITEMS[1]], "NextPageLink": None}
        pages = [json.dumps(page1).encode(), json.dumps(page2).encode()]
        call_count = 0

        adapter = AzurePricingAdapter()

        def get(url):
            nonlocal call_count
            result = pages[call_count]
            call_count += 1
            return result

        adapter._get = get
        results = list(adapter.fetch_instance_pricing("eastus"))
        assert call_count == 2
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Azure Functions
# ---------------------------------------------------------------------------


class TestFunctionsParsing:
    def test_returns_execution_and_duration_tiers(self):
        adapter = _mock_adapter(_FUNCTIONS_ITEMS)
        results = adapter.fetch_managed_service_pricing("azure_functions", "eastus")
        tiers = {r.tier_name for r in results}
        assert "per_execution" in tiers
        assert "per_gb_second" in tiers

    def test_service_field(self):
        adapter = _mock_adapter(_FUNCTIONS_ITEMS)
        results = adapter.fetch_managed_service_pricing("azure_functions", "eastus")
        assert all(r.service == "azure_functions" for r in results)


# ---------------------------------------------------------------------------
# Blob Storage
# ---------------------------------------------------------------------------


class TestBlobParsing:
    def test_returns_storage_price(self):
        adapter = _mock_adapter(_BLOB_ITEMS)
        results = adapter.fetch_managed_service_pricing("blob_storage", "eastus")
        assert len(results) > 0

    def test_storage_tier_name(self):
        adapter = _mock_adapter(_BLOB_ITEMS)
        results = adapter.fetch_managed_service_pricing("blob_storage", "eastus")
        lrs = next(r for r in results if r.tier_name == "lrs_gb")
        assert lrs.price_per_month == pytest.approx(0.018)
        assert lrs.service == "blob_storage"


# ---------------------------------------------------------------------------
# Azure SQL
# ---------------------------------------------------------------------------


class TestSQLParsing:
    def test_returns_sql_price(self):
        adapter = _mock_adapter(_SQL_ITEMS)
        results = adapter.fetch_managed_service_pricing("azure_sql", "eastus")
        assert len(results) > 0

    def test_monthly_from_hourly(self):
        adapter = _mock_adapter(_SQL_ITEMS)
        results = adapter.fetch_managed_service_pricing("azure_sql", "eastus")
        for r in results:
            if r.price_per_hour > 0:
                assert r.price_per_month == pytest.approx(r.price_per_hour * 730, rel=1e-3)


# ---------------------------------------------------------------------------
# Cosmos DB
# ---------------------------------------------------------------------------


class TestCosmosParsing:
    def test_returns_ru_and_storage_tiers(self):
        adapter = _mock_adapter(_COSMOS_ITEMS)
        results = adapter.fetch_managed_service_pricing("cosmos_db", "eastus")
        tiers = {r.tier_name for r in results}
        assert "request_unit" in tiers
        assert "storage_gb" in tiers

    def test_service_field(self):
        adapter = _mock_adapter(_COSMOS_ITEMS)
        results = adapter.fetch_managed_service_pricing("cosmos_db", "eastus")
        assert all(r.service == "cosmos_db" for r in results)


# ---------------------------------------------------------------------------
# Unsupported service
# ---------------------------------------------------------------------------


class TestUnsupportedService:
    def test_unknown_service_returns_empty(self):
        adapter = _mock_adapter([])
        result = adapter.fetch_managed_service_pricing("unknown_service", "eastus")
        assert result == []
