"""Tests for the GCP Cloud Billing API adapter.

All HTTP calls are mocked — no network access required.
"""

from __future__ import annotations

import json
import os
import urllib.error
from unittest.mock import patch

import pytest
from cloudwright.adapters import InstancePrice, ManagedServicePrice, PricingAdapter
from cloudwright.adapters.gcp import (
    GCPPricingAdapter,
    _extract_unit_price,
    _safe_float,
)

# Fixture helpers


def _unit_price(usd: float, units_str: str = "hour") -> dict:
    """Build a GCP pricingInfo list entry."""
    full_units = int(usd)
    nanos = round((usd - full_units) * 1e9)
    return [
        {
            "pricingExpression": {
                "usageUnit": units_str,
                "tieredRates": [
                    {
                        "startUsageAmount": 0,
                        "unitPrice": {
                            "currencyCode": "USD",
                            "units": str(full_units),
                            "nanos": nanos,
                        },
                    }
                ],
            }
        }
    ]


def _sku(
    sku_id: str = "SKU-001",
    description: str = "N1 Predefined Instance Core running in Americas",
    resource_family: str = "Compute",
    resource_group: str = "CPU",
    usage_type: str = "OnDemand",
    regions: list[str] | None = None,
    price: float = 0.0475,
) -> dict:
    return {
        "skuId": sku_id,
        "description": description,
        "category": {
            "resourceFamily": resource_family,
            "resourceGroup": resource_group,
            "usageType": usage_type,
        },
        "serviceRegions": regions or ["us-east1"],
        "pricingInfo": _unit_price(price),
    }


def _gcp_skus_page(skus: list[dict], next_token: str = "") -> dict:
    page: dict = {"skus": skus}
    if next_token:
        page["nextPageToken"] = next_token
    return page


_COMPUTE_SKUS = [
    _sku("CPU-001", "N1 Predefined Instance Core running in Americas", "Compute", "CPU", price=0.0475),
    _sku("RAM-001", "N1 Predefined Instance Ram running in Americas", "Compute", "RAM", price=0.006375),
    _sku("GPU-001", "Nvidia Tesla K80 GPU running in Americas", "Compute", "GPU", price=0.45),
]

_FUNCTIONS_SKUS = [
    _sku(
        "FN-REQ",
        "Cloud Functions Invocations",
        "ApplicationServices",
        "Requests",
        regions=["us-east1"],
        price=0.0000004,
    ),
    _sku("FN-DUR", "Cloud Functions GB-Second", "ApplicationServices", "CPU", regions=["us-east1"], price=0.00001),
]

_STORAGE_SKUS = [
    _sku("GCS-STD", "Standard Storage US Multi-region", "Storage", "Storage", regions=["us"], price=0.020),
    _sku("GCS-NE", "Nearline Storage US", "Storage", "Storage", regions=["us-east1"], price=0.010),
]

_BQ_SKUS = [
    _sku("BQ-QUERY", "BigQuery Analysis", "BigQuery", "InteractiveSQL", regions=["global"], price=5.0),
    _sku("BQ-STORAGE", "BigQuery Active Storage", "BigQuery", "TableDataRead", regions=["global"], price=0.02),
]


def _make_adapter(skus: list[dict], api_key: str = "test-key") -> GCPPricingAdapter:
    adapter = GCPPricingAdapter(api_key=api_key)
    payload = json.dumps(_gcp_skus_page(skus)).encode()
    adapter._get = lambda url: payload
    return adapter


# Unit tests: helpers


class TestHelpers:
    def test_safe_float(self):
        assert _safe_float("0.5") == 0.5
        assert _safe_float(0.5) == 0.5
        assert _safe_float("") == 0.0
        assert _safe_float(None) == 0.0

    def test_extract_unit_price(self):
        pricing_info = _unit_price(0.0475)
        assert _extract_unit_price(pricing_info) == pytest.approx(0.0475, rel=1e-4)

    def test_extract_unit_price_empty(self):
        assert _extract_unit_price([]) == 0.0

    def test_extract_unit_price_zero(self):
        info = _unit_price(0.0)
        assert _extract_unit_price(info) == 0.0


# ABC conformance


class TestGCPAdapterABC:
    def test_implements_abc(self):
        assert isinstance(GCPPricingAdapter(api_key="key"), PricingAdapter)

    def test_provider_attribute(self):
        assert GCPPricingAdapter.provider == "gcp"

    def test_supported_managed_services(self):
        services = GCPPricingAdapter().supported_managed_services()
        assert set(services) == {"cloud_functions", "cloud_storage", "cloud_sql", "bigquery"}


# No API key — graceful degradation


class TestNoAPIKey:
    def test_no_key_returns_empty_instances(self):
        adapter = GCPPricingAdapter(api_key="")
        results = list(adapter.fetch_instance_pricing("us-east1"))
        assert results == []

    def test_no_key_returns_empty_managed(self):
        adapter = GCPPricingAdapter(api_key="")
        results = adapter.fetch_managed_service_pricing("cloud_functions", "us-east1")
        assert results == []

    def test_env_var_picked_up(self):
        with patch.dict(os.environ, {"GCP_API_KEY": "env-key"}):
            adapter = GCPPricingAdapter()
            assert adapter._api_key == "env-key"

    def test_403_returns_empty(self):
        adapter = GCPPricingAdapter(api_key="bad-key")

        def raise_403(url: str) -> bytes:
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)

        adapter._get = raise_403
        results = list(adapter.fetch_instance_pricing("us-east1"))
        assert results == []

    def test_401_returns_empty(self):
        adapter = GCPPricingAdapter(api_key="bad-key")

        def raise_401(url: str) -> bytes:
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

        adapter._get = raise_401
        results = adapter.fetch_managed_service_pricing("cloud_functions", "us-east1")
        assert results == []


# Compute Engine pricing


class TestGCPInstancePricing:
    def test_yields_instance_prices(self):
        adapter = _make_adapter(_COMPUTE_SKUS)
        results = list(adapter.fetch_instance_pricing("us-east1"))
        assert len(results) > 0
        assert all(isinstance(r, InstancePrice) for r in results)

    def test_price_set_from_sku(self):
        adapter = _make_adapter([_COMPUTE_SKUS[0]])
        results = list(adapter.fetch_instance_pricing("us-east1"))
        assert results[0].price_per_hour == pytest.approx(0.0475, rel=1e-4)

    def test_skips_zero_price_skus(self):
        zero_sku = _sku("ZERO", price=0.0)
        adapter = _make_adapter([zero_sku, _COMPUTE_SKUS[0]])
        results = list(adapter.fetch_instance_pricing("us-east1"))
        assert all(r.price_per_hour > 0 for r in results)

    def test_filters_by_region(self):
        other_region_sku = _sku("OTHER-REGION", regions=["europe-west1"], price=0.05)
        adapter = _make_adapter([_COMPUTE_SKUS[0], other_region_sku])
        results = list(adapter.fetch_instance_pricing("us-east1"))
        ids = {r.instance_type for r in results}
        assert "OTHER-REGION" not in ids

    def test_region_stored_on_price(self):
        adapter = _make_adapter(_COMPUTE_SKUS)
        results = list(adapter.fetch_instance_pricing("us-east1"))
        assert all(r.region == "us-east1" for r in results)

    def test_price_type_on_demand(self):
        adapter = _make_adapter(_COMPUTE_SKUS)
        results = list(adapter.fetch_instance_pricing("us-east1"))
        assert all(r.price_type == "on_demand" for r in results)


# Pagination


class TestGCPPagination:
    def test_follows_next_page_token(self):
        page1 = _gcp_skus_page([_COMPUTE_SKUS[0]], next_token="token-abc")
        page2 = _gcp_skus_page([_COMPUTE_SKUS[1]])
        pages = [json.dumps(page1).encode(), json.dumps(page2).encode()]
        call_count = 0

        adapter = GCPPricingAdapter(api_key="test")

        def get(url: str) -> bytes:
            nonlocal call_count
            result = pages[call_count]
            call_count += 1
            return result

        adapter._get = get
        skus = adapter._list_skus("service-id")
        assert call_count == 2
        assert len(skus) == 2


# Cloud Functions


class TestCloudFunctionsPricing:
    def test_returns_managed_prices(self):
        adapter = _make_adapter(_FUNCTIONS_SKUS)
        results = adapter.fetch_managed_service_pricing("cloud_functions", "us-east1")
        assert len(results) > 0
        assert all(isinstance(r, ManagedServicePrice) for r in results)

    def test_service_field(self):
        adapter = _make_adapter(_FUNCTIONS_SKUS)
        results = adapter.fetch_managed_service_pricing("cloud_functions", "us-east1")
        assert all(r.service == "cloud_functions" for r in results)


# Cloud Storage


class TestCloudStoragePricing:
    def test_returns_standard_storage(self):
        adapter = _make_adapter(_STORAGE_SKUS)
        results = adapter.fetch_managed_service_pricing("cloud_storage", "us-east1")
        std = [r for r in results if r.tier_name == "standard_storage_gb"]
        assert len(std) > 0

    def test_service_field(self):
        adapter = _make_adapter(_STORAGE_SKUS)
        results = adapter.fetch_managed_service_pricing("cloud_storage", "us-east1")
        assert all(r.service == "cloud_storage" for r in results)


# BigQuery


class TestBigQueryPricing:
    def test_returns_query_and_storage_tiers(self):
        adapter = _make_adapter(_BQ_SKUS)
        results = adapter.fetch_managed_service_pricing("bigquery", "us-east1")
        tiers = {r.tier_name for r in results}
        assert "per_tb_queried" in tiers
        assert "active_storage_gb" in tiers

    def test_service_field(self):
        adapter = _make_adapter(_BQ_SKUS)
        results = adapter.fetch_managed_service_pricing("bigquery", "us-east1")
        assert all(r.service == "bigquery" for r in results)


# Unsupported service


class TestUnsupportedService:
    def test_unknown_returns_empty(self):
        adapter = _make_adapter([])
        result = adapter.fetch_managed_service_pricing("eks", "us-east1")
        assert result == []


# Non-auth HTTP errors propagate


class TestGCPHTTPErrors:
    def test_non_auth_error_propagates(self):
        adapter = GCPPricingAdapter(api_key="key")

        def raise_500(url: str) -> bytes:
            raise urllib.error.HTTPError(url, 500, "Server Error", {}, None)

        adapter._get = raise_500
        with pytest.raises(urllib.error.HTTPError):
            list(adapter.fetch_instance_pricing("us-east1"))
