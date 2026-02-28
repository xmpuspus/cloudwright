"""Azure Retail Prices API adapter.

Fetches compute and managed service pricing from the Azure Retail Prices API:
  https://prices.azure.com/api/retail/prices

No API key required. Supports OData-style query filters and pagination via
nextPageLink.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator

from cloudwright.adapters import InstancePrice, ManagedServicePrice, PricingAdapter, urlopen_safe

_BASE_URL = "https://prices.azure.com/api/retail/prices"
_API_VERSION = "2023-01-01-preview"
_TIMEOUT = 30  # seconds

# Azure region display names -> region codes (used in the API response)
# The API uses ARM location names, not display names.
_REGION_TO_ARM: dict[str, str] = {
    "eastus": "eastus",
    "eastus2": "eastus2",
    "westus": "westus",
    "westus2": "westus2",
    "centralus": "centralus",
    "northeurope": "northeurope",
    "westeurope": "westeurope",
    "uksouth": "uksouth",
    "southeastasia": "southeastasia",
    "eastasia": "eastasia",
    "japaneast": "japaneast",
    "australiaeast": "australiaeast",
    "brazilsouth": "brazilsouth",
    "canadacentral": "canadacentral",
}

# Azure ARM location -> cloudwright region code
_ARM_TO_REGION: dict[str, str] = {v: k for k, v in _REGION_TO_ARM.items()}

# Managed service -> Azure service name in pricing API
_SERVICE_TO_AZURE: dict[str, str] = {
    "azure_functions": "Azure Functions",
    "blob_storage": "Storage",
    "azure_sql": "Azure SQL Database",
    "cosmos_db": "Azure Cosmos DB",
}


def _safe_float(val: Any) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


class AzurePricingAdapter(PricingAdapter):
    """Fetches Azure pricing from the Retail Prices API (no auth required).

    Uses OData filter expressions and follows nextPageLink for pagination.
    """

    provider = "azure"

    def __init__(self, timeout: int = _TIMEOUT):
        self._timeout = timeout

    # Public interface

    def fetch_instance_pricing(self, region: str = "eastus") -> Iterator[InstancePrice]:
        """Yield on-demand Linux VM prices for the given Azure region."""
        arm_region = _REGION_TO_ARM.get(region, region)
        # contains() on productName causes 400 errors on some API versions;
        # use only equality/service filters and handle exclusions client-side
        odata = f"armRegionName eq '{arm_region}' and serviceName eq 'Virtual Machines' and priceType eq 'Consumption'"
        yield from self._paginate_instances(odata, region)

    def fetch_managed_service_pricing(self, service: str, region: str = "eastus") -> list[ManagedServicePrice]:
        """Return pricing tiers for a supported Azure managed service."""
        parsers = {
            "azure_functions": self._parse_functions,
            "blob_storage": self._parse_blob,
            "azure_sql": self._parse_sql,
            "cosmos_db": self._parse_cosmos,
        }
        handler = parsers.get(service)
        return handler(region) if handler else []

    def supported_managed_services(self) -> list[str]:
        return ["azure_functions", "blob_storage", "azure_sql", "cosmos_db"]

    # Instance pricing (VM)

    def _paginate_instances(self, odata_filter: str, region: str) -> Iterator[InstancePrice]:
        """Follow nextPageLink pagination for the Azure retail prices API."""
        url = self._build_url(odata_filter)
        while url:
            data = json.loads(self._get(url))
            for item in data.get("Items", []):
                price = _safe_float(item.get("retailPrice", 0))
                if price <= 0:
                    continue
                sku_name = item.get("skuName", "")
                product_name = item.get("productName", "")
                # Skip Windows, Spot, Low Priority, Dedicated Host, and Reserved items
                if any(kw in sku_name for kw in ("Spot", "Low Priority")):
                    continue
                if any(kw in product_name for kw in ("Windows", "Spot", "Low Priority", "Dedicated Host", "Reserved")):
                    continue
                # Extract instance type from skuName (e.g. "D2s v3" from "D2s v3")
                instance_type = item.get("armSkuName", sku_name).strip()
                if not instance_type:
                    continue
                yield InstancePrice(
                    instance_type=instance_type,
                    region=region,
                    vcpus=0,  # Azure API doesn't return vCPU in pricing; use catalog for specs
                    memory_gb=0.0,
                    price_per_hour=price,
                    price_type="on_demand",
                    os="linux",
                    storage_desc="",
                    network_bandwidth="",
                )
            url = data.get("NextPageLink") or ""

    # Managed service parsers

    def _parse_functions(self, region: str) -> list[ManagedServicePrice]:
        arm_region = _REGION_TO_ARM.get(region, region)
        odata = f"armRegionName eq '{arm_region}' and serviceName eq 'Azure Functions' and priceType eq 'Consumption'"
        items = self._fetch_all(odata)
        prices: list[ManagedServicePrice] = []
        for item in items:
            price = _safe_float(item.get("retailPrice", 0))
            desc = item.get("skuName", "")
            meter = item.get("meterName", "").lower()
            if price <= 0:
                continue
            if "execution" in meter or "request" in meter:
                prices.append(
                    ManagedServicePrice(
                        service="azure_functions",
                        tier_name="per_execution",
                        price_per_hour=0.0,
                        price_per_month=round(price * 1_000_000, 4),
                        description=item.get("productName", desc),
                    )
                )
            elif "gb second" in meter or "duration" in meter:
                prices.append(
                    ManagedServicePrice(
                        service="azure_functions",
                        tier_name="per_gb_second",
                        price_per_hour=round(price * 3600, 6),
                        price_per_month=0.0,
                        description=item.get("productName", desc),
                    )
                )
        return prices

    def _parse_blob(self, region: str) -> list[ManagedServicePrice]:
        arm_region = _REGION_TO_ARM.get(region, region)
        odata = (
            f"armRegionName eq '{arm_region}'"
            " and serviceName eq 'Storage'"
            " and skuName eq 'LRS'"
            " and meterName eq 'LRS Data Stored'"
        )
        items = self._fetch_all(odata)
        prices: list[ManagedServicePrice] = []
        for item in items:
            price = _safe_float(item.get("retailPrice", 0))
            if price > 0:
                prices.append(
                    ManagedServicePrice(
                        service="blob_storage",
                        tier_name="lrs_gb",
                        price_per_hour=0.0,
                        price_per_month=price,  # per GB/month
                        description=item.get("productName", "Blob Storage LRS"),
                    )
                )
        return prices

    def _parse_sql(self, region: str) -> list[ManagedServicePrice]:
        arm_region = _REGION_TO_ARM.get(region, region)
        odata = (
            f"armRegionName eq '{arm_region}'"
            " and serviceName eq 'Azure SQL Database'"
            " and priceType eq 'Consumption'"
            " and skuName eq 'General Purpose'"
        )
        items = self._fetch_all(odata)
        prices: list[ManagedServicePrice] = []
        for item in items:
            price = _safe_float(item.get("retailPrice", 0))
            sku = item.get("skuName", "")
            meter = item.get("meterName", "").lower()
            if price <= 0 or "vcore" not in meter:
                continue
            prices.append(
                ManagedServicePrice(
                    service="azure_sql",
                    tier_name=sku or "general_purpose",
                    price_per_hour=price,
                    price_per_month=round(price * 730, 2),
                    description=item.get("productName", sku),
                )
            )
        return prices

    def _parse_cosmos(self, region: str) -> list[ManagedServicePrice]:
        arm_region = _REGION_TO_ARM.get(region, region)
        odata = f"armRegionName eq '{arm_region}' and serviceName eq 'Azure Cosmos DB' and priceType eq 'Consumption'"
        items = self._fetch_all(odata)
        prices: list[ManagedServicePrice] = []
        for item in items:
            price = _safe_float(item.get("retailPrice", 0))
            meter = item.get("meterName", "").lower()
            sku = item.get("skuName", "")
            if price <= 0:
                continue
            if "request unit" in meter or "ru" in meter:
                prices.append(
                    ManagedServicePrice(
                        service="cosmos_db",
                        tier_name="request_unit",
                        price_per_hour=0.0,
                        price_per_month=round(price * 1_000_000, 4),
                        description=item.get("productName", sku),
                    )
                )
            elif "storage" in meter:
                prices.append(
                    ManagedServicePrice(
                        service="cosmos_db",
                        tier_name="storage_gb",
                        price_per_hour=0.0,
                        price_per_month=price,
                        description=item.get("productName", sku),
                    )
                )
        return prices

    # HTTP + pagination helpers

    def _build_url(self, odata_filter: str) -> str:
        params = urllib.parse.urlencode(
            {
                "api-version": _API_VERSION,
                "$filter": odata_filter,
            }
        )
        return f"{_BASE_URL}?{params}"

    def _fetch_all(self, odata_filter: str) -> list[dict]:
        """Collect all pages for an OData filter and return items."""
        items: list[dict] = []
        url = self._build_url(odata_filter)
        while url:
            data = json.loads(self._get(url))
            items.extend(data.get("Items", []))
            url = data.get("NextPageLink") or ""
        return items

    def _get(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        return urlopen_safe(req, timeout=self._timeout)
