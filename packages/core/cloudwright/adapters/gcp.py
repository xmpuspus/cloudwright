"""GCP Cloud Billing API adapter.

Fetches compute and managed service pricing from the GCP Cloud Catalog API:
  https://cloudbilling.googleapis.com/v1/services/{service_id}/skus

Requires a GCP_API_KEY environment variable. Gracefully degrades to empty
results when the key is absent or the request returns 403/401.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator

from cloudwright.adapters import InstancePrice, ManagedServicePrice, PricingAdapter, urlopen_safe

_BASE_URL = "https://cloudbilling.googleapis.com/v1"
_TIMEOUT = 30  # seconds
_PAGE_SIZE = 500

# GCP service IDs for the Cloud Billing API
_SERVICE_IDS: dict[str, str] = {
    "compute": "6F81-5844-456A",  # Compute Engine
    "cloud_functions": "9B50-17A3-3F3D",  # Cloud Functions
    "cloud_storage": "95FF-2EF5-5EA1",  # Cloud Storage
    "cloud_sql": "9662-B51E-5089",  # Cloud SQL
    "bigquery": "95FF-2EF5-5EA1",  # BigQuery (shares billing with Storage)
}

# GCP regions are just ARM region names (e.g. "us-east1", "europe-west1")
_REGION_TO_GCP: dict[str, str] = {
    "us-east1": "us-east1",
    "us-central1": "us-central1",
    "us-west1": "us-west1",
    "us-west2": "us-west2",
    "europe-west1": "europe-west1",
    "europe-west2": "europe-west2",
    "asia-east1": "asia-east1",
    "asia-southeast1": "asia-southeast1",
    "asia-northeast1": "asia-northeast1",
    "australia-southeast1": "australia-southeast1",
    "southamerica-east1": "southamerica-east1",
}


def _safe_float(val: Any) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _extract_unit_price(pricing_info: list[dict]) -> float:
    """Extract USD nanos unit price from a GCP SKU's pricingInfo list."""
    for pi in pricing_info:
        expr = pi.get("pricingExpression", {})
        tiers = expr.get("tieredRates", [])
        for tier in tiers:
            unit_price = tier.get("unitPrice", {})
            nanos = int(unit_price.get("nanos", 0))
            units = int(unit_price.get("units", 0))
            price = units + nanos / 1e9
            if price > 0:
                return price
    return 0.0


def _region_matches(gcp_region: str, service_regions: list[str]) -> bool:
    """Check if gcp_region matches any entry in service_regions.

    Handles parent regions (e.g. "us" matches "us-east1") and "global".
    """
    for sr in service_regions:
        if sr == "global" or sr == gcp_region or gcp_region.startswith(sr + "-"):
            return True
    return False


class GCPPricingAdapter(PricingAdapter):
    """Fetches GCP pricing from the Cloud Billing Catalog API.

    Requires a GCP_API_KEY in the environment. When the key is absent or
    the API returns 401/403, all methods return empty results rather than
    raising exceptions — enabling graceful degradation in CI and offline use.
    """

    provider = "gcp"

    def __init__(self, api_key: str | None = None, timeout: int = _TIMEOUT):
        self._api_key = api_key or os.environ.get("GCP_API_KEY", "")
        self._timeout = timeout

    # Public interface

    def fetch_instance_pricing(self, region: str = "us-east1") -> Iterator[InstancePrice]:
        """Yield on-demand Compute Engine VM prices for the given region."""
        service_id = _SERVICE_IDS["compute"]
        skus = self._list_skus(service_id)
        gcp_region = _REGION_TO_GCP.get(region, region)

        for sku in skus:
            category = sku.get("category", {})
            if category.get("resourceFamily") != "Compute":
                continue
            if category.get("usageType") not in ("OnDemand", ""):
                continue
            if category.get("resourceGroup") not in ("CPU", "N1Standard"):
                continue
            # Check region is applicable
            regions = sku.get("serviceRegions", [])
            if regions and gcp_region not in regions and "global" not in regions:
                continue

            desc = sku.get("description", "")
            price = _extract_unit_price(sku.get("pricingInfo", []))
            if price <= 0:
                continue

            # GCP SKU descriptions like "N1 Predefined Instance Core running in Americas"
            # We can't reliably extract instance type from SKU so use description as type
            yield InstancePrice(
                instance_type=sku.get("skuId", desc[:40]),
                region=region,
                vcpus=0,  # Not available from billing SKU; use machine type catalog
                memory_gb=0.0,
                price_per_hour=price,
                price_type="on_demand",
                os="linux",
                storage_desc="",
                network_bandwidth="",
            )

    def fetch_managed_service_pricing(self, service: str, region: str = "us-east1") -> list[ManagedServicePrice]:
        """Return pricing tiers for a GCP managed service."""
        parsers = {
            "cloud_functions": self._parse_cloud_functions,
            "cloud_storage": self._parse_cloud_storage,
            "cloud_sql": self._parse_cloud_sql,
            "bigquery": self._parse_bigquery,
        }
        handler = parsers.get(service)
        return handler(region) if handler else []

    def supported_managed_services(self) -> list[str]:
        return ["cloud_functions", "cloud_storage", "cloud_sql", "bigquery"]

    # Managed service parsers

    def _parse_cloud_functions(self, region: str) -> list[ManagedServicePrice]:
        skus = self._list_skus(_SERVICE_IDS.get("cloud_functions", "9B50-17A3-3F3D"))
        gcp_region = _REGION_TO_GCP.get(region, region)
        prices: list[ManagedServicePrice] = []
        for sku in skus:
            regions = sku.get("serviceRegions", [])
            if regions and gcp_region not in regions and "global" not in regions:
                continue
            desc = sku.get("description", "").lower()
            price = _extract_unit_price(sku.get("pricingInfo", []))
            if price <= 0:
                continue
            if "invocation" in desc or "request" in desc:
                prices.append(
                    ManagedServicePrice(
                        service="cloud_functions",
                        tier_name="per_invocation",
                        price_per_hour=0.0,
                        price_per_month=round(price * 1_000_000, 4),
                        description=sku.get("description", ""),
                    )
                )
            elif "compute time" in desc or "gb-second" in desc:
                prices.append(
                    ManagedServicePrice(
                        service="cloud_functions",
                        tier_name="per_gb_second",
                        price_per_hour=round(price * 3600, 6),
                        price_per_month=0.0,
                        description=sku.get("description", ""),
                    )
                )
        return prices

    def _parse_cloud_storage(self, region: str) -> list[ManagedServicePrice]:
        skus = self._list_skus(_SERVICE_IDS.get("cloud_storage", "95FF-2EF5-5EA1"))
        gcp_region = _REGION_TO_GCP.get(region, region)
        prices: list[ManagedServicePrice] = []
        for sku in skus:
            regions = sku.get("serviceRegions", [])
            if regions and not _region_matches(gcp_region, regions):
                continue
            desc = sku.get("description", "")
            if "Standard Storage" not in desc:
                continue
            price = _extract_unit_price(sku.get("pricingInfo", []))
            if price > 0:
                prices.append(
                    ManagedServicePrice(
                        service="cloud_storage",
                        tier_name="standard_storage_gb",
                        price_per_hour=0.0,
                        price_per_month=price,
                        description=desc,
                    )
                )
        return prices

    def _parse_cloud_sql(self, region: str) -> list[ManagedServicePrice]:
        skus = self._list_skus(_SERVICE_IDS.get("cloud_sql", "9662-B51E-5089"))
        gcp_region = _REGION_TO_GCP.get(region, region)
        prices: list[ManagedServicePrice] = []
        for sku in skus:
            regions = sku.get("serviceRegions", [])
            if regions and gcp_region not in regions and "global" not in regions:
                continue
            category = sku.get("category", {})
            if category.get("usageType") not in ("OnDemand", ""):
                continue
            desc = sku.get("description", "")
            price = _extract_unit_price(sku.get("pricingInfo", []))
            if price > 0 and "db-" in desc.lower():
                prices.append(
                    ManagedServicePrice(
                        service="cloud_sql",
                        tier_name=sku.get("skuId", desc[:40]),
                        price_per_hour=price,
                        price_per_month=round(price * 730, 2),
                        description=desc,
                    )
                )
        return prices

    def _parse_bigquery(self, region: str) -> list[ManagedServicePrice]:
        # BigQuery uses a different service ID
        bq_service_id = "24E6-581D-38E5"
        skus = self._list_skus(bq_service_id)
        prices: list[ManagedServicePrice] = []
        for sku in skus:
            desc = sku.get("description", "")
            price = _extract_unit_price(sku.get("pricingInfo", []))
            if price <= 0:
                continue
            desc_lower = desc.lower()
            if "active storage" in desc_lower:
                prices.append(
                    ManagedServicePrice(
                        service="bigquery",
                        tier_name="active_storage_gb",
                        price_per_hour=0.0,
                        price_per_month=price,
                        description=desc,
                    )
                )
            elif "analysis" in desc_lower or "interactive" in desc_lower:
                prices.append(
                    ManagedServicePrice(
                        service="bigquery",
                        tier_name="per_tb_queried",
                        price_per_hour=0.0,
                        price_per_month=price,
                        description=desc,
                    )
                )
        return prices

    # API helpers

    def _list_skus(self, service_id: str) -> list[dict]:
        """Fetch all SKUs for a GCP service, following pagination."""
        if not self._api_key:
            return []

        skus: list[dict] = []
        page_token = ""
        while True:
            params: dict[str, Any] = {
                "key": self._api_key,
                "pageSize": _PAGE_SIZE,
            }
            if page_token:
                params["pageToken"] = page_token

            url = f"{_BASE_URL}/services/{service_id}/skus?" + urllib.parse.urlencode(params)
            try:
                data = json.loads(self._get(url))
            except (urllib.error.HTTPError, urllib.error.URLError) as exc:
                # Graceful degradation: missing/invalid key → empty results
                code = getattr(exc, "code", None)
                if code in (401, 403):
                    return []
                raise

            skus.extend(data.get("skus", []))
            page_token = data.get("nextPageToken", "")
            if not page_token:
                break

        return skus

    def _get(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        return urlopen_safe(req, timeout=self._timeout)
