"""AWS Pricing API adapter.

Streams EC2 instance pricing from the AWS Bulk Pricing CSV (region-scoped)
and parses managed service pricing from the AWS JSON Pricing API for
Lambda, S3, RDS, and DynamoDB.
"""

from __future__ import annotations

import csv
import io
import json
import re
import urllib.error
import urllib.request
from typing import Any, Iterator

from cloudwright.adapters import InstancePrice, ManagedServicePrice, PricingAdapter, urlopen_safe

_PRICING_BASE = "https://pricing.us-east-1.amazonaws.com"
_TIMEOUT = 30  # seconds

# AWS region code -> location name used in the pricing API
_REGION_TO_LOCATION: dict[str, str] = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-central-1": "EU (Frankfurt)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ca-central-1": "Canada (Central)",
    "sa-east-1": "South America (Sao Paulo)",
}


def _parse_memory_gib(mem_str: str) -> float:
    """Parse '16 GiB' or '16,384 MiB' -> float GiB."""
    m = re.match(r"([\d,]+(?:\.\d+)?)\s*(GiB|MiB)", mem_str.strip())
    if not m:
        return 0.0
    value = float(m.group(1).replace(",", ""))
    return value / 1024 if m.group(2) == "MiB" else value


def _safe_int(val: str) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _safe_float(val: str | float) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _first_price(terms: dict) -> float:
    """Extract the first USD price from a terms dict."""
    for term in terms.values():
        for dim in term.get("priceDimensions", {}).values():
            p = _safe_float(dim.get("pricePerUnit", {}).get("USD", "0"))
            if p > 0:
                return p
    return 0.0


class AWSPricingAdapter(PricingAdapter):
    """Fetches AWS pricing from the bulk pricing API.

    EC2 pricing is streamed from the CSV index (large file; streamed to avoid
    loading the full ~1 GB decompressed CSV into memory at once).
    Managed service pricing uses the JSON API.
    """

    provider = "aws"

    def __init__(self, timeout: int = _TIMEOUT):
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch_instance_pricing(self, region: str = "us-east-1") -> Iterator[InstancePrice]:
        """Stream on-demand Linux EC2 instance prices for the given region."""
        url = f"{_PRICING_BASE}/offers/v1.0/aws/AmazonEC2/current/{region}/index.csv"
        data = self._get(url)
        yield from self._parse_ec2_csv(data, region)

    def fetch_managed_service_pricing(self, service: str, region: str = "us-east-1") -> list[ManagedServicePrice]:
        """Return pricing tiers for a supported managed service."""
        parsers = {
            "lambda": self._parse_lambda,
            "s3": self._parse_s3,
            "rds": self._parse_rds,
            "dynamodb": self._parse_dynamodb,
        }
        handler = parsers.get(service)
        return handler(region) if handler else []

    def supported_managed_services(self) -> list[str]:
        return ["lambda", "s3", "rds", "dynamodb"]

    # ------------------------------------------------------------------
    # EC2 CSV parsing
    # ------------------------------------------------------------------

    def _parse_ec2_csv(self, data: bytes, region: str) -> Iterator[InstancePrice]:
        """Parse EC2 pricing CSV.

        The CSV starts with several metadata lines before the actual header row
        (the one whose first field is 'SKU'). We scan for it and then parse
        the remainder as standard CSV.
        """
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()

        # Find the header row — first line where field 0 is 'SKU' (quoted or bare)
        header_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip().strip('"')
            if stripped.startswith("SKU"):
                header_idx = i
                break

        reader = csv.DictReader(io.StringIO("\n".join(lines[header_idx:])))

        for row in reader:
            if (
                row.get("TermType") == "OnDemand"
                and row.get("Operating System", "Linux") in ("Linux", "")
                and row.get("Tenancy", "Shared") == "Shared"
                and row.get("CapacityStatus", "Used") == "Used"
                and row.get("Pre Installed S/W", "NA") in ("NA", "")
                and row.get("productFamily", "Compute Instance") == "Compute Instance"
            ):
                price = _safe_float(row.get("PricePerUnit", "0"))
                if price <= 0:
                    continue
                yield InstancePrice(
                    instance_type=row.get("Instance Type", ""),
                    region=region,
                    vcpus=_safe_int(row.get("vCPU", "0")),
                    memory_gb=_parse_memory_gib(row.get("Memory", "0 GiB")),
                    price_per_hour=price,
                    price_type="on_demand",
                    os="linux",
                    storage_desc=row.get("Storage", ""),
                    network_bandwidth=row.get("Network Performance", ""),
                )

    # ------------------------------------------------------------------
    # JSON API parsing
    # ------------------------------------------------------------------

    def _fetch_json(self, offer_code: str, region: str) -> dict[str, Any]:
        url = f"{_PRICING_BASE}/offers/v1.0/aws/{offer_code}/current/{region}/index.json"
        return json.loads(self._get(url))

    def _parse_lambda(self, region: str) -> list[ManagedServicePrice]:
        data = self._fetch_json("AWSLambda", region)
        location = _REGION_TO_LOCATION.get(region, region)
        on_demand = data.get("terms", {}).get("OnDemand", {})
        prices: list[ManagedServicePrice] = []

        for sku, product in data.get("products", {}).items():
            attrs = product.get("attributes", {})
            if attrs.get("location") not in (location, region):
                continue
            sku_terms = on_demand.get(sku, {})
            for term in sku_terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    unit = dim.get("unit", "")
                    desc = dim.get("description", "")
                    price = _safe_float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if "request" in unit.lower() or "request" in desc.lower():
                        prices.append(
                            ManagedServicePrice(
                                service="lambda",
                                tier_name="per_request",
                                price_per_hour=0.0,
                                # price is per-request; store per-million
                                price_per_month=round(price * 1_000_000, 4),
                                description=desc,
                            )
                        )
                    elif "second" in unit.lower() or "gb-second" in unit.lower():
                        prices.append(
                            ManagedServicePrice(
                                service="lambda",
                                tier_name="per_gb_second",
                                price_per_hour=round(price * 3600, 6),
                                price_per_month=0.0,
                                description=desc,
                            )
                        )

        return prices

    def _parse_s3(self, region: str) -> list[ManagedServicePrice]:
        # S3 uses a global index (no region path component)
        url = f"{_PRICING_BASE}/offers/v1.0/aws/AmazonS3/current/index.json"
        data = json.loads(self._get(url))
        location = _REGION_TO_LOCATION.get(region, region)
        on_demand = data.get("terms", {}).get("OnDemand", {})
        prices: list[ManagedServicePrice] = []

        for sku, product in data.get("products", {}).items():
            attrs = product.get("attributes", {})
            if attrs.get("location") != location:
                continue
            if attrs.get("storageClass") != "General Purpose":
                continue
            if attrs.get("volumeType") != "Standard":
                continue
            sku_terms = on_demand.get(sku, {})
            for term in sku_terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    price = _safe_float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if price > 0:
                        prices.append(
                            ManagedServicePrice(
                                service="s3",
                                tier_name="standard_storage_gb",
                                price_per_hour=0.0,
                                price_per_month=price,  # per GB/month
                                description=dim.get("description", ""),
                            )
                        )

        return prices

    def _parse_rds(self, region: str) -> list[ManagedServicePrice]:
        data = self._fetch_json("AmazonRDS", region)
        location = _REGION_TO_LOCATION.get(region, region)
        on_demand = data.get("terms", {}).get("OnDemand", {})
        prices: list[ManagedServicePrice] = []

        for sku, product in data.get("products", {}).items():
            attrs = product.get("attributes", {})
            if attrs.get("location") not in (location, region):
                continue
            if attrs.get("databaseEngine") not in ("PostgreSQL", "MySQL"):
                continue
            if attrs.get("deploymentOption") != "Single-AZ":
                continue
            db_class = attrs.get("instanceType", "")
            if not db_class:
                continue

            sku_terms = on_demand.get(sku, {})
            price = _first_price(sku_terms)
            if price > 0:
                prices.append(
                    ManagedServicePrice(
                        service="rds",
                        tier_name=db_class,
                        price_per_hour=price,
                        price_per_month=round(price * 730, 2),
                        description=f"{attrs.get('databaseEngine')} {db_class} Single-AZ",
                        vcpus=_safe_int(attrs.get("vcpu", "0")),
                        memory_gb=_parse_memory_gib(attrs.get("memory", "0 GiB")),
                    )
                )

        return prices

    def _parse_dynamodb(self, region: str) -> list[ManagedServicePrice]:
        data = self._fetch_json("AmazonDynamoDB", region)
        location = _REGION_TO_LOCATION.get(region, region)
        on_demand = data.get("terms", {}).get("OnDemand", {})
        prices: list[ManagedServicePrice] = []

        for sku, product in data.get("products", {}).items():
            attrs = product.get("attributes", {})
            if attrs.get("location") not in (location, region):
                continue
            group = attrs.get("group", "")
            sku_terms = on_demand.get(sku, {})
            for term in sku_terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    price = _safe_float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    dim_desc = dim.get("description", "")
                    if not price:
                        continue
                    if "write" in group.lower() or "write" in dim_desc.lower():
                        prices.append(
                            ManagedServicePrice(
                                service="dynamodb",
                                tier_name="write_request_unit",
                                price_per_hour=0.0,
                                price_per_month=round(price * 1_000_000, 4),
                                description=dim_desc,
                            )
                        )
                    elif "read" in group.lower() or "read" in dim_desc.lower():
                        prices.append(
                            ManagedServicePrice(
                                service="dynamodb",
                                tier_name="read_request_unit",
                                price_per_hour=0.0,
                                price_per_month=round(price * 1_000_000, 4),
                                description=dim_desc,
                            )
                        )

        return prices

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _get(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers={"Accept": "*/*"})
        return urlopen_safe(req, timeout=self._timeout)
