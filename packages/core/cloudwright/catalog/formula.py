"""Named pricing formulas — no eval(), just Python functions."""

from __future__ import annotations

from typing import Any


def per_hour(config: dict[str, Any], base_rate: float = 0.0) -> float | None:
    """Hourly rate * 730 hours/month * count. Returns None when no rate available."""
    rate = base_rate or config.get("price_per_hour")
    if not rate:
        return None
    count = config.get("count", 1)
    return round(rate * 730 * count, 2)


def per_request(config: dict[str, Any], base_rate: float = 0.0) -> float:
    """Request-based pricing (Lambda, API Gateway, etc.)."""
    monthly_requests = config.get("monthly_requests", 1_000_000)
    avg_duration_ms = config.get("avg_duration_ms", 200)
    memory_mb = config.get("memory_mb", 512)
    request_cost = (monthly_requests / 1_000_000) * 0.20
    gb_seconds = (monthly_requests * avg_duration_ms / 1000) * (memory_mb / 1024)
    compute_cost = gb_seconds * 0.0000166667
    return round(request_cost + compute_cost, 2)


def per_gb(config: dict[str, Any], base_rate: float = 0.023) -> float:
    """Per-GB storage pricing."""
    storage_gb = config.get("storage_gb", config.get("estimated_gb", 50))
    rate = base_rate or 0.023
    return round(storage_gb * rate, 2)


def per_gb_hour(config: dict[str, Any], base_rate: float = 0.0) -> float:
    """Per-GB-hour pricing (cache services)."""
    memory_gb = config.get("memory_gb", 4.0)
    rate = base_rate or 0.049  # typical Redis rate
    return round(memory_gb * rate * 730, 2)


def per_zone(config: dict[str, Any], base_rate: float = 0.50) -> float:
    """DNS zone-based pricing."""
    zones = config.get("hosted_zones", 1)
    queries = config.get("monthly_queries", 1_000_000)
    zone_cost = zones * base_rate
    query_cost = (queries / 1_000_000) * 0.40
    return round(zone_cost + query_cost, 2)


def fixed_plus_request(config: dict[str, Any], base_rate: float = 5.0) -> float:
    """Fixed monthly + per-request (WAF, etc.)."""
    rules = config.get("rules", config.get("policies", 1))
    monthly_requests = config.get("monthly_requests", 10_000_000)
    fixed = rules * base_rate
    request_cost = (monthly_requests / 1_000_000) * 0.60
    return round(fixed + request_cost, 2)


def per_mau(config: dict[str, Any], base_rate: float = 0.0) -> float:
    """Monthly active user pricing (auth services). Usually free tier."""
    mau = config.get("monthly_active_users", 10_000)
    if mau <= 50_000:
        return 0.0
    excess = mau - 50_000
    return round(excess * 0.0055, 2)


def per_shard_hour(config: dict[str, Any], base_rate: float = 0.015) -> float:
    """Shard/throughput-based pricing (Kinesis, Event Hubs)."""
    shards = config.get("shards", config.get("throughput_units", 2))
    rate = base_rate or 0.015
    return round(shards * rate * 730, 2)


def per_tb_query(config: dict[str, Any], base_rate: float = 5.0) -> float:
    """Per-TB query pricing (BigQuery-style)."""
    monthly_tb = config.get("monthly_query_tb", 1.0)
    storage_gb = config.get("storage_gb", 100)
    query_cost = monthly_tb * base_rate
    storage_cost = storage_gb * 0.02  # active storage
    return round(query_cost + storage_cost, 2)


def per_node_hour(config: dict[str, Any], base_rate: float = 0.0) -> float:
    """Per-node-hour pricing (Redshift, Spanner)."""
    nodes = config.get("num_nodes", config.get("node_count", 1))
    rate = base_rate or config.get("price_per_hour", 0.25)
    storage_gb = config.get("storage_gb", 100)
    compute = round(nodes * rate * 730, 2)
    storage = round(storage_gb * 0.024, 2)
    return compute + storage


PRICING_FORMULAS = {
    "per_hour": per_hour,
    "per_request": per_request,
    "per_gb": per_gb,
    "per_gb_hour": per_gb_hour,
    "per_zone": per_zone,
    "fixed_plus_request": fixed_plus_request,
    "per_mau": per_mau,
    "per_shard_hour": per_shard_hour,
    "per_tb_query": per_tb_query,
    "per_node_hour": per_node_hour,
}

_FALLBACK_PRICES: dict[str, float] = {
    "rds": 50.0,
    "aurora": 75.0,
    "cloud_sql": 45.0,
    "azure_sql": 55.0,
    "elasticache": 47.0,
    "memorystore": 44.0,
    "azure_cache": 50.0,
    "alb": 22.50,
    "nlb": 22.50,
    "app_gateway": 25.0,
    "azure_lb": 20.0,
    "cloud_load_balancing": 18.26,
    "cloudfront": 42.50,
    "cloud_cdn": 40.0,
    "azure_cdn": 40.0,
    "s3": 2.30,
    "cloud_storage": 2.30,
    "blob_storage": 2.30,
    "sqs": 4.0,
    "pub_sub": 6.0,
    "service_bus": 10.0,
    "sns": 2.50,
    "event_hubs": 11.0,
    "dynamodb": 25.0,
    "firestore": 18.0,
    "cosmos_db": 30.0,
    "lambda": 5.0,
    "cloud_functions": 5.0,
    "azure_functions": 5.0,
    "waf": 5.0,
    "cloud_armor": 5.0,
    "azure_waf": 5.0,
    "route53": 1.0,
    "cloud_dns": 1.0,
    "azure_dns": 1.0,
    "api_gateway": 3.50,
    "api_management": 5.0,
    "cognito": 0.0,
    "firebase_auth": 0.0,
    "azure_ad": 0.0,
    "kinesis": 15.0,
    "dataflow": 20.0,
    "event_grid": 10.0,
    "redshift": 180.0,
    "bigquery": 7.0,
    "synapse": 200.0,
    "sagemaker": 50.0,
    "vertex_ai": 50.0,
    "azure_ml": 50.0,
    "step_functions": 2.50,
    "workflows": 2.0,
    "logic_apps": 5.0,
    "eventbridge": 1.0,
    "ecs": 73.0,
    "eks": 73.0,
    "gke": 73.0,
    "aks": 73.0,
    "fargate": 35.0,
    "cloud_run": 15.0,
    "container_apps": 15.0,
    "app_engine": 25.0,
    "app_service": 13.0,
    "spanner": 65.70,
    # Virtual/meta components (no billing)
    "users": 0.0,
    "internet": 0.0,
    "external": 0.0,
    "client": 0.0,
    "browser": 0.0,
    "mobile": 0.0,
    # Common services the LLM might name
    "cloudwatch": 3.0,
    "cloud_logging": 0.50,
    "cloud_monitoring": 3.0,
    "azure_monitor": 2.30,
    "kms": 1.0,
    "cloud_kms": 1.0,
    "key_vault": 1.0,
    "secrets_manager": 0.40,
    "secret_manager": 0.06,
    "ecr": 1.0,
    "gcr": 0.0,
    "acr": 5.0,
    "artifact_registry": 0.0,
    "codecommit": 0.0,
    "codebuild": 1.0,
    "codepipeline": 1.0,
    "cloud_build": 0.0,
    "nat_gateway": 32.40,
    "cloud_nat": 32.40,
    "vpc": 0.0,
    "vnet": 0.0,
    "iam": 0.0,
    "shield": 0.0,
    "guardduty": 3.0,
    "security_hub": 0.0,
    "config": 2.0,
    "cloudtrail": 2.0,
    "audit_log": 0.0,
    "msk": 70.0,
    "confluent_kafka": 70.0,
    "elasticbeanstalk": 0.0,
    "elastic_beanstalk": 0.0,
    "amplify": 0.0,
    "ses": 1.0,
    "sendgrid": 0.0,
    "terraform_cloud": 0.0,
}


def default_managed_price(service: str, config: dict) -> float:
    """Fallback pricing when catalog doesn't have specific data."""
    base = _FALLBACK_PRICES.get(service, 10.0)
    # Multiplier from various count-like config keys
    count = config.get("count", config.get("instance_count", config.get("desired_count",
            config.get("min_tasks", config.get("min_instances", 1)))))
    if isinstance(count, str):
        try:
            count = int(count)
        except ValueError:
            count = 1
    if count > 1:
        base = base * count
    storage_gb = config.get("storage_gb", 0)
    if storage_gb > 0:
        base += storage_gb * 0.10
    node_count = config.get("node_count", config.get("num_nodes", 0))
    if node_count > 1:
        base = base * node_count
    return round(base, 2)
