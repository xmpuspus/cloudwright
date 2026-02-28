"""Tests for the AWS pricing adapter.

All HTTP calls are mocked — no network access required.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from cloudwright.adapters import InstancePrice, ManagedServicePrice, PricingAdapter
from cloudwright.adapters.aws import (
    AWSPricingAdapter,
    _parse_memory_gib,
    _safe_float,
    _safe_int,
)

# Fixture helpers

# Minimal EC2 pricing CSV — 5 metadata lines + header + 3 data rows
_EC2_CSV = """\
"FormatVersion","CSV/1.0"
"Disclaimer","AWS pricing list is for informational purposes only."
"Publication Date","2025-01-01"
"Version","20250101000000"
"OfferCode","AmazonEC2"
SKU,OfferTermCode,RateCode,TermType,PricePerUnit,Currency,Unit,productFamily,Location,"Instance Type",vCPU,Memory,Storage,"Network Performance","Operating System",Tenancy,CapacityStatus,"Pre Installed S/W"
ABC123,JRTCKXETXF,ABC123.JRTCKXETXF.6YS6EN2CT7,OnDemand,0.0464,USD,Hrs,Compute Instance,"US East (N. Virginia)",t3.medium,2,4 GiB,EBS Only,Up to 5 Gigabit,Linux,Shared,Used,NA
DEF456,JRTCKXETXF,DEF456.JRTCKXETXF.6YS6EN2CT7,OnDemand,0.192,USD,Hrs,Compute Instance,"US East (N. Virginia)",m5.large,2,8 GiB,EBS Only,Up to 10 Gigabit,Linux,Shared,Used,NA
WIN789,JRTCKXETXF,WIN789.JRTCKXETXF.6YS6EN2CT7,OnDemand,0.113,USD,Hrs,Compute Instance,"US East (N. Virginia)",t3.medium,2,4 GiB,EBS Only,Up to 5 Gigabit,Windows,Shared,Used,NA
SPTABC,JRTCKXETXF,SPTABC.JRTCKXETXF.6YS6EN2CT7,OnDemand,0.099,USD,Hrs,Compute Instance,"US East (N. Virginia)",t3.large,2,8 GiB,EBS Only,Up to 5 Gigabit,Linux,Dedicated,Used,NA
"""


def _make_pricing_json(
    sku: str,
    product_family: str,
    attributes: dict[str, Any],
    price_usd: str,
    unit: str = "Hrs",
    description: str = "",
) -> dict[str, Any]:
    """Build minimal AWS pricing JSON with one product and one OnDemand price."""
    term_code = "JRTCKXETXF"
    rate_code = f"{sku}.{term_code}.6YS6EN2CT7"
    return {
        "products": {
            sku: {
                "sku": sku,
                "productFamily": product_family,
                "attributes": attributes,
            }
        },
        "terms": {
            "OnDemand": {
                sku: {
                    f"{sku}.{term_code}": {
                        "offerTermCode": term_code,
                        "priceDimensions": {
                            rate_code: {
                                "unit": unit,
                                "description": description,
                                "pricePerUnit": {"USD": price_usd},
                            }
                        },
                    }
                }
            }
        },
    }


_LAMBDA_JSON = {
    "products": {
        "LAMBDA_REQ": {
            "sku": "LAMBDA_REQ",
            "productFamily": "Serverless",
            "attributes": {
                "location": "US East (N. Virginia)",
                "group": "AWS-Lambda-Requests",
            },
        },
        "LAMBDA_DUR": {
            "sku": "LAMBDA_DUR",
            "productFamily": "Serverless",
            "attributes": {
                "location": "US East (N. Virginia)",
                "group": "AWS-Lambda-Duration",
            },
        },
    },
    "terms": {
        "OnDemand": {
            "LAMBDA_REQ": {
                "LAMBDA_REQ.JRTCKXETXF": {
                    "priceDimensions": {
                        "LAMBDA_REQ.JRTCKXETXF.rate": {
                            "unit": "Requests",
                            "description": "$0.20 per 1M requests",
                            "pricePerUnit": {"USD": "0.0000002"},
                        }
                    }
                }
            },
            "LAMBDA_DUR": {
                "LAMBDA_DUR.JRTCKXETXF": {
                    "priceDimensions": {
                        "LAMBDA_DUR.JRTCKXETXF.rate": {
                            "unit": "GB-Second",
                            "description": "$0.0000166667 per GB-second",
                            "pricePerUnit": {"USD": "0.0000166667"},
                        }
                    }
                }
            },
        }
    },
}

_S3_JSON = _make_pricing_json(
    sku="S3STD",
    product_family="Storage",
    attributes={
        "location": "US East (N. Virginia)",
        "storageClass": "General Purpose",
        "volumeType": "Standard",
    },
    price_usd="0.023",
    unit="GB-Mo",
    description="$0.023 per GB-Month of storage",
)

_RDS_JSON = _make_pricing_json(
    sku="RDSPG",
    product_family="Database Instance",
    attributes={
        "location": "US East (N. Virginia)",
        "databaseEngine": "PostgreSQL",
        "deploymentOption": "Single-AZ",
        "instanceType": "db.t3.medium",
        "vcpu": "2",
        "memory": "4 GiB",
    },
    price_usd="0.068",
    unit="Hrs",
    description="PostgreSQL db.t3.medium Single-AZ",
)

_DYNAMODB_JSON = {
    "products": {
        "DDB_WR": {
            "sku": "DDB_WR",
            "productFamily": "Amazon DynamoDB PayPerRequest Throughput",
            "attributes": {
                "location": "US East (N. Virginia)",
                "group": "DDB-WriteUnits",
                "groupDescription": "Write Request Units",
            },
        },
        "DDB_RD": {
            "sku": "DDB_RD",
            "productFamily": "Amazon DynamoDB PayPerRequest Throughput",
            "attributes": {
                "location": "US East (N. Virginia)",
                "group": "DDB-ReadUnits",
                "groupDescription": "Read Request Units",
            },
        },
    },
    "terms": {
        "OnDemand": {
            "DDB_WR": {
                "DDB_WR.JRTCKXETXF": {
                    "priceDimensions": {
                        "DDB_WR.rate": {
                            "unit": "WriteRequestUnits",
                            "description": "$1.25 per million write request units",
                            "pricePerUnit": {"USD": "0.00000125"},
                        }
                    }
                }
            },
            "DDB_RD": {
                "DDB_RD.JRTCKXETXF": {
                    "priceDimensions": {
                        "DDB_RD.rate": {
                            "unit": "ReadRequestUnits",
                            "description": "$0.25 per million read request units",
                            "pricePerUnit": {"USD": "0.00000025"},
                        }
                    }
                }
            },
        }
    },
}


# Mock helper


def _mock_urlopen(response_bytes: bytes):
    """Return a context-manager mock that yields a readable response."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    cm.read = MagicMock(return_value=response_bytes)
    return cm


# Unit tests: helpers


class TestHelpers:
    def test_parse_memory_gib(self):
        assert _parse_memory_gib("4 GiB") == 4.0
        assert _parse_memory_gib("16 GiB") == 16.0
        assert _parse_memory_gib("1,024 MiB") == 1.0
        assert _parse_memory_gib("0.5 GiB") == 0.5
        assert _parse_memory_gib("") == 0.0
        assert _parse_memory_gib("N/A") == 0.0

    def test_safe_int(self):
        assert _safe_int("2") == 2
        assert _safe_int("0") == 0
        assert _safe_int("") == 0
        assert _safe_int("N/A") == 0

    def test_safe_float(self):
        assert _safe_float("0.0464") == pytest.approx(0.0464)
        assert _safe_float("0") == 0.0
        assert _safe_float("") == 0.0
        assert _safe_float("N/A") == 0.0


# ABC conformance


class TestPricingAdapterABC:
    def test_implements_abc(self):
        adapter = AWSPricingAdapter()
        assert isinstance(adapter, PricingAdapter)

    def test_provider_attribute(self):
        assert AWSPricingAdapter.provider == "aws"

    def test_supported_managed_services(self):
        adapter = AWSPricingAdapter()
        services = adapter.supported_managed_services()
        assert set(services) == {"lambda", "s3", "rds", "dynamodb"}


# EC2 CSV parsing


class TestEC2Parsing:
    def _adapter_with_csv(self, csv_data: str = _EC2_CSV) -> AWSPricingAdapter:
        adapter = AWSPricingAdapter()
        adapter._get = lambda url: csv_data.encode("utf-8")
        return adapter

    def test_yields_instance_prices(self):
        adapter = self._adapter_with_csv()
        results = list(adapter.fetch_instance_pricing("us-east-1"))
        assert len(results) > 0
        assert all(isinstance(r, InstancePrice) for r in results)

    def test_filters_windows(self):
        adapter = self._adapter_with_csv()
        results = list(adapter.fetch_instance_pricing("us-east-1"))
        assert all(r.os == "linux" for r in results)

    def test_filters_dedicated_tenancy(self):
        adapter = self._adapter_with_csv()
        results = list(adapter.fetch_instance_pricing("us-east-1"))
        # t3.large with Dedicated tenancy should be excluded
        assert not any(r.instance_type == "t3.large" for r in results)

    def test_t3_medium_parsed_correctly(self):
        adapter = self._adapter_with_csv()
        results = list(adapter.fetch_instance_pricing("us-east-1"))
        t3 = next(r for r in results if r.instance_type == "t3.medium")
        assert t3.vcpus == 2
        assert t3.memory_gb == 4.0
        assert t3.price_per_hour == pytest.approx(0.0464)
        assert t3.region == "us-east-1"
        assert t3.price_type == "on_demand"

    def test_m5_large_parsed_correctly(self):
        adapter = self._adapter_with_csv()
        results = list(adapter.fetch_instance_pricing("us-east-1"))
        m5 = next(r for r in results if r.instance_type == "m5.large")
        assert m5.memory_gb == 8.0
        assert m5.price_per_hour == pytest.approx(0.192)

    def test_skips_zero_price_rows(self):
        csv_with_zero = _EC2_CSV + (
            "ZERO1,JRTCKXETXF,ZERO1.rate,OnDemand,0.0000,USD,Hrs,"
            'Compute Instance,"US East (N. Virginia)",t4g.nano,2,0.5 GiB,'
            "EBS Only,Up to 5 Gigabit,Linux,Shared,Used,NA\n"
        )
        adapter = self._adapter_with_csv(csv_with_zero)
        results = list(adapter.fetch_instance_pricing("us-east-1"))
        assert not any(r.instance_type == "t4g.nano" for r in results)

    def test_region_stored_on_price(self):
        adapter = self._adapter_with_csv()
        results = list(adapter.fetch_instance_pricing("eu-west-1"))
        assert all(r.region == "eu-west-1" for r in results)


# Lambda JSON parsing


class TestLambdaParsing:
    def _adapter(self) -> AWSPricingAdapter:
        adapter = AWSPricingAdapter()
        adapter._get = lambda url: json.dumps(_LAMBDA_JSON).encode()
        return adapter

    def test_returns_list_of_managed_prices(self):
        results = self._adapter().fetch_managed_service_pricing("lambda", "us-east-1")
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, ManagedServicePrice) for r in results)

    def test_has_per_request_tier(self):
        results = self._adapter().fetch_managed_service_pricing("lambda", "us-east-1")
        tiers = {r.tier_name for r in results}
        assert "per_request" in tiers

    def test_has_per_gb_second_tier(self):
        results = self._adapter().fetch_managed_service_pricing("lambda", "us-east-1")
        tiers = {r.tier_name for r in results}
        assert "per_gb_second" in tiers

    def test_service_field_is_lambda(self):
        results = self._adapter().fetch_managed_service_pricing("lambda", "us-east-1")
        assert all(r.service == "lambda" for r in results)


# S3 JSON parsing


class TestS3Parsing:
    def _adapter(self) -> AWSPricingAdapter:
        adapter = AWSPricingAdapter()
        adapter._get = lambda url: json.dumps(_S3_JSON).encode()
        return adapter

    def test_returns_storage_price(self):
        results = self._adapter().fetch_managed_service_pricing("s3", "us-east-1")
        assert len(results) > 0

    def test_storage_gb_price(self):
        results = self._adapter().fetch_managed_service_pricing("s3", "us-east-1")
        std = next(r for r in results if r.tier_name == "standard_storage_gb")
        assert std.price_per_month == pytest.approx(0.023)
        assert std.service == "s3"

    def test_filters_other_storage_classes(self):
        # Only Standard General Purpose should be returned
        results = self._adapter().fetch_managed_service_pricing("s3", "us-east-1")
        assert all(r.tier_name == "standard_storage_gb" for r in results)


# RDS JSON parsing


class TestRDSParsing:
    def _adapter(self) -> AWSPricingAdapter:
        adapter = AWSPricingAdapter()
        adapter._get = lambda url: json.dumps(_RDS_JSON).encode()
        return adapter

    def test_returns_db_instance_price(self):
        results = self._adapter().fetch_managed_service_pricing("rds", "us-east-1")
        assert len(results) > 0

    def test_db_t3_medium_price(self):
        results = self._adapter().fetch_managed_service_pricing("rds", "us-east-1")
        tier = next(r for r in results if r.tier_name == "db.t3.medium")
        assert tier.price_per_hour == pytest.approx(0.068)
        assert tier.price_per_month == pytest.approx(0.068 * 730, rel=1e-3)
        assert tier.vcpus == 2
        assert tier.memory_gb == 4.0
        assert tier.service == "rds"

    def test_monthly_is_hourly_times_730(self):
        results = self._adapter().fetch_managed_service_pricing("rds", "us-east-1")
        for r in results:
            if r.price_per_hour > 0:
                assert r.price_per_month == pytest.approx(r.price_per_hour * 730, rel=1e-3)


# DynamoDB JSON parsing


class TestDynamoDBParsing:
    def _adapter(self) -> AWSPricingAdapter:
        adapter = AWSPricingAdapter()
        adapter._get = lambda url: json.dumps(_DYNAMODB_JSON).encode()
        return adapter

    def test_returns_read_and_write_tiers(self):
        results = self._adapter().fetch_managed_service_pricing("dynamodb", "us-east-1")
        tiers = {r.tier_name for r in results}
        assert "write_request_unit" in tiers
        assert "read_request_unit" in tiers

    def test_service_field_is_dynamodb(self):
        results = self._adapter().fetch_managed_service_pricing("dynamodb", "us-east-1")
        assert all(r.service == "dynamodb" for r in results)

    def test_write_unit_price(self):
        results = self._adapter().fetch_managed_service_pricing("dynamodb", "us-east-1")
        write = next(r for r in results if r.tier_name == "write_request_unit")
        # 0.00000125 * 1_000_000 = 1.25
        assert write.price_per_month == pytest.approx(1.25, rel=1e-3)


# Unsupported service


class TestUnsupportedService:
    def test_unknown_service_returns_empty(self):
        adapter = AWSPricingAdapter()
        adapter._get = lambda url: b"{}"
        result = adapter.fetch_managed_service_pricing("unknown_service", "us-east-1")
        assert result == []


# HTTP error propagation


class TestHTTPErrors:
    def test_http_error_propagates(self):
        import urllib.error

        adapter = AWSPricingAdapter()

        def raise_error(url):
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)

        adapter._get = raise_error
        with pytest.raises(urllib.error.HTTPError):
            list(adapter.fetch_instance_pricing("us-east-1"))
