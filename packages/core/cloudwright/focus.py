"""FinOps FOCUS 1.0 CSV exporter for CostEstimate line items.

FOCUS (FinOps Open Cost and Usage Specification) defines a standard schema for
cloud billing data. Spec: https://focus.finops.org/

Column mapping:
    BilledCost          — actual monthly charge for this line item
    EffectiveCost       — same as BilledCost (no amortisation applied here)
    ServiceName         — cloud service name (e.g. "ec2", "rds")
    ServiceCategory     — FOCUS category inferred from service name
    ResourceId          — component_id from the ArchSpec
    RegionId            — region from the estimate
    ChargePeriodStart   — first day of current month (ISO 8601)
    ChargePeriodEnd     — last day of current month (ISO 8601)
    BillingCurrency     — always "USD"
    PricingUnit         — "Month"
    PricingQuantity     — 1.0
    ChargeType          — "Usage"
    PricingCategory     — "Standard" (on_demand) or "Committed" (reserved)
    PricingConfidence   — per-line confidence from the cost engine ("high"/"low")
"""

from __future__ import annotations

import csv
import io
from calendar import monthrange
from datetime import date

from cloudwright.spec import CostEstimate

# FOCUS 1.0 required + recommended columns we emit
_FOCUS_COLUMNS = [
    "BilledCost",
    "EffectiveCost",
    "ServiceName",
    "ServiceCategory",
    "ResourceId",
    "RegionId",
    "ChargePeriodStart",
    "ChargePeriodEnd",
    "BillingCurrency",
    "PricingUnit",
    "PricingQuantity",
    "ChargeType",
    "PricingCategory",
    "PricingConfidence",
]

# Rough FOCUS ServiceCategory mapping by service keyword
_SERVICE_CATEGORY: dict[str, str] = {
    "ec2": "Compute",
    "compute_engine": "Compute",
    "virtual_machines": "Compute",
    "ecs": "Compute",
    "eks": "Compute",
    "gke": "Compute",
    "aks": "Compute",
    "fargate": "Compute",
    "cloud_run": "Compute",
    "container_apps": "Compute",
    "app_engine": "Compute",
    "app_service": "Compute",
    "lambda": "Compute",
    "cloud_functions": "Compute",
    "azure_functions": "Compute",
    "rds": "Databases",
    "aurora": "Databases",
    "cloud_sql": "Databases",
    "azure_sql": "Databases",
    "dynamodb": "Databases",
    "cosmos_db": "Databases",
    "firestore": "Databases",
    "spanner": "Databases",
    "elasticache": "Databases",
    "memorystore": "Databases",
    "azure_cache": "Databases",
    "s3": "Storage",
    "cloud_storage": "Storage",
    "blob_storage": "Storage",
    "ebs": "Storage",
    "cloudfront": "Networking",
    "cloud_cdn": "Networking",
    "azure_cdn": "Networking",
    "alb": "Networking",
    "nlb": "Networking",
    "app_gateway": "Networking",
    "azure_lb": "Networking",
    "cloud_load_balancing": "Networking",
    "api_gateway": "Networking",
    "api_management": "Networking",
    "nat_gateway": "Networking",
    "cloud_nat": "Networking",
    "route53": "Networking",
    "cloud_dns": "Networking",
    "azure_dns": "Networking",
    "sqs": "Integration",
    "pub_sub": "Integration",
    "service_bus": "Integration",
    "sns": "Integration",
    "event_hubs": "Integration",
    "kinesis": "Integration",
    "eventbridge": "Integration",
    "event_grid": "Integration",
    "redshift": "Analytics",
    "bigquery": "Analytics",
    "synapse": "Analytics",
    "dataflow": "Analytics",
    "sagemaker": "AI and Machine Learning",
    "vertex_ai": "AI and Machine Learning",
    "azure_ml": "AI and Machine Learning",
    "databricks_cluster": "Analytics",
    "databricks_sql_warehouse": "Analytics",
    "databricks_job": "Analytics",
    "databricks_pipeline": "Analytics",
    "databricks_model_serving": "AI and Machine Learning",
    "kms": "Security",
    "cloud_kms": "Security",
    "key_vault": "Security",
    "secrets_manager": "Security",
    "secret_manager": "Security",
    "waf": "Security",
    "cloud_armor": "Security",
    "azure_waf": "Security",
    "guardduty": "Security",
    "security_hub": "Security",
    "cloudwatch": "Management and Governance",
    "cloud_logging": "Management and Governance",
    "cloud_monitoring": "Management and Governance",
    "azure_monitor": "Management and Governance",
    "cloudtrail": "Management and Governance",
    "config": "Management and Governance",
}


def _service_category(service: str) -> str:
    return _SERVICE_CATEGORY.get(service, "Other")


def _charge_period() -> tuple[str, str]:
    """Return (ChargePeriodStart, ChargePeriodEnd) for the current month."""
    today = date.today()
    start = today.replace(day=1)
    last_day = monthrange(today.year, today.month)[1]
    end = today.replace(day=last_day)
    return start.isoformat(), end.isoformat()


def to_focus_csv(estimate: CostEstimate, pricing_tier: str = "on_demand") -> str:
    """Serialise a CostEstimate to a FOCUS 1.0 compliant CSV string.

    Each line item in estimate.breakdown becomes one row. The data-transfer
    sub-total is added as a synthetic "DataTransfer" service row when non-zero.

    Args:
        estimate: A CostEstimate produced by CostEngine.estimate().
        pricing_tier: The pricing tier used to produce the estimate. Controls
            PricingCategory ("Standard" for on_demand, "Committed" for reserved).

    Returns:
        A UTF-8 CSV string with FOCUS 1.0 column headers.
    """
    period_start, period_end = _charge_period()
    region = estimate.region or "us-east-1"
    currency = estimate.currency or "USD"
    pricing_category = "Standard" if pricing_tier == "on_demand" else "Committed"

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_FOCUS_COLUMNS, lineterminator="\n")
    writer.writeheader()

    for item in estimate.breakdown:
        writer.writerow(
            {
                "BilledCost": round(item.monthly, 4),
                "EffectiveCost": round(item.monthly, 4),
                "ServiceName": item.service,
                "ServiceCategory": _service_category(item.service),
                "ResourceId": item.component_id,
                "RegionId": region,
                "ChargePeriodStart": period_start,
                "ChargePeriodEnd": period_end,
                "BillingCurrency": currency,
                "PricingUnit": "Month",
                "PricingQuantity": 1.0,
                "ChargeType": "Usage",
                "PricingCategory": pricing_category,
                "PricingConfidence": item.confidence,
            }
        )

    # Add data-transfer line if non-zero
    if estimate.data_transfer_monthly > 0:
        writer.writerow(
            {
                "BilledCost": round(estimate.data_transfer_monthly, 4),
                "EffectiveCost": round(estimate.data_transfer_monthly, 4),
                "ServiceName": "DataTransfer",
                "ServiceCategory": "Networking",
                "ResourceId": "data-transfer",
                "RegionId": region,
                "ChargePeriodStart": period_start,
                "ChargePeriodEnd": period_end,
                "BillingCurrency": currency,
                "PricingUnit": "Month",
                "PricingQuantity": 1.0,
                "ChargeType": "Usage",
                "PricingCategory": pricing_category,
                "PricingConfidence": "low",  # always estimated from connection metadata
            }
        )

    return buf.getvalue()
