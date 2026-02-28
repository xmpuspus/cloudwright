"""Icon registry for cloud service visualization.

Maps (provider, service) pairs to visual metadata: category, color, shape,
ASCII character. Used by ASCII renderer, D2/Mermaid exporters, and React Flow UI.
"""

from __future__ import annotations

from dataclasses import dataclass

# Provider brand colors
PROVIDER_COLORS = {
    "aws": "#FF9900",
    "gcp": "#4285F4",
    "azure": "#0078D4",
}

# Category accent colors (dark-theme friendly)
CATEGORY_COLORS = {
    "compute": "#10b981",
    "database": "#8b5cf6",
    "storage": "#6366f1",
    "network": "#3b82f6",
    "security": "#ef4444",
    "serverless": "#f59e0b",
    "cache": "#8b5cf6",
    "queue": "#f97316",
    "cdn": "#3b82f6",
    "monitoring": "#06b6d4",
    "ml": "#ec4899",
    "analytics": "#a855f7",
}

# Category -> D2/Mermaid node shape
CATEGORY_SHAPES = {
    "compute": "rectangle",
    "database": "cylinder",
    "storage": "rectangle",
    "network": "stadium",
    "security": "rectangle",
    "serverless": "hexagon",
    "cache": "cylinder",
    "queue": "parallelogram",
    "cdn": "stadium",
    "monitoring": "rectangle",
    "ml": "rectangle",
    "analytics": "cylinder",
}

# Category -> ASCII single-char label
CATEGORY_ASCII = {
    "compute": "S",
    "database": "D",
    "storage": "B",
    "network": "N",
    "security": "X",
    "serverless": "F",
    "cache": "H",
    "queue": "Q",
    "cdn": "C",
    "monitoring": "M",
    "ml": "A",
    "analytics": "R",
}

VALID_SHAPES = {"rectangle", "cylinder", "hexagon", "stadium", "parallelogram"}


@dataclass(frozen=True, slots=True)
class ServiceIcon:
    provider: str
    service: str
    category: str
    label: str
    color: str = ""
    shape: str = "rectangle"
    ascii_char: str = "?"

    def __post_init__(self):
        if self.shape not in VALID_SHAPES:
            raise ValueError(f"Invalid shape {self.shape!r}, must be one of {VALID_SHAPES}")


def _icon(provider: str, service: str, category: str, label: str) -> ServiceIcon:
    """Build a ServiceIcon with category-derived defaults."""
    return ServiceIcon(
        provider=provider,
        service=service,
        category=category,
        label=label,
        color=CATEGORY_COLORS.get(category, "#94a3b8"),
        shape=CATEGORY_SHAPES.get(category, "rectangle"),
        ascii_char=CATEGORY_ASCII.get(category, "?"),
    )


# --- AWS ---
_AWS_ICONS: list[ServiceIcon] = [
    _icon("aws", "ec2", "compute", "EC2"),
    _icon("aws", "ecs", "compute", "ECS"),
    _icon("aws", "eks", "compute", "EKS"),
    _icon("aws", "emr", "compute", "EMR"),
    _icon("aws", "rds", "database", "RDS"),
    _icon("aws", "aurora", "database", "Aurora"),
    _icon("aws", "dynamodb", "database", "DynamoDB"),
    _icon("aws", "redshift", "analytics", "Redshift"),
    _icon("aws", "s3", "storage", "S3"),
    _icon("aws", "ebs", "storage", "EBS"),
    _icon("aws", "ecr", "storage", "ECR"),
    _icon("aws", "alb", "network", "ALB"),
    _icon("aws", "nlb", "network", "NLB"),
    _icon("aws", "route53", "network", "Route 53"),
    _icon("aws", "cloudfront", "cdn", "CloudFront"),
    _icon("aws", "waf", "security", "WAF"),
    _icon("aws", "cognito", "security", "Cognito"),
    _icon("aws", "kms", "security", "KMS"),
    _icon("aws", "cloudtrail", "security", "CloudTrail"),
    _icon("aws", "guardduty", "security", "GuardDuty"),
    _icon("aws", "lambda", "serverless", "Lambda"),
    _icon("aws", "api_gateway", "serverless", "API Gateway"),
    _icon("aws", "step_functions", "serverless", "Step Functions"),
    _icon("aws", "glue", "serverless", "Glue"),
    _icon("aws", "elasticache", "cache", "ElastiCache"),
    _icon("aws", "sqs", "queue", "SQS"),
    _icon("aws", "sns", "queue", "SNS"),
    _icon("aws", "kinesis", "queue", "Kinesis"),
    _icon("aws", "cloudwatch", "monitoring", "CloudWatch"),
    _icon("aws", "codepipeline", "compute", "CodePipeline"),
    _icon("aws", "sagemaker", "ml", "SageMaker"),
]

# --- GCP ---
_GCP_ICONS: list[ServiceIcon] = [
    _icon("gcp", "compute_engine", "compute", "Compute Engine"),
    _icon("gcp", "gke", "compute", "GKE"),
    _icon("gcp", "cloud_sql", "database", "Cloud SQL"),
    _icon("gcp", "bigquery", "analytics", "BigQuery"),
    _icon("gcp", "cloud_storage", "storage", "Cloud Storage"),
    _icon("gcp", "cloud_load_balancing", "network", "Cloud LB"),
    _icon("gcp", "cloud_cdn", "cdn", "Cloud CDN"),
    _icon("gcp", "cloud_functions", "serverless", "Cloud Functions"),
    _icon("gcp", "cloud_run", "serverless", "Cloud Run"),
    _icon("gcp", "memorystore", "cache", "Memorystore"),
    _icon("gcp", "pub_sub", "queue", "Pub/Sub"),
]

# --- Azure ---
_AZURE_ICONS: list[ServiceIcon] = [
    _icon("azure", "virtual_machines", "compute", "Virtual Machines"),
    _icon("azure", "aks", "compute", "AKS"),
    _icon("azure", "azure_sql", "database", "Azure SQL"),
    _icon("azure", "cosmos_db", "database", "Cosmos DB"),
    _icon("azure", "blob_storage", "storage", "Blob Storage"),
    _icon("azure", "app_gateway", "network", "App Gateway"),
    _icon("azure", "azure_functions", "serverless", "Azure Functions"),
    _icon("azure", "azure_cache", "cache", "Azure Cache"),
    _icon("azure", "service_bus", "queue", "Service Bus"),
]

# --- Generic fallbacks ---
_GENERIC_ICONS: list[ServiceIcon] = [
    _icon("generic", "user", "network", "User"),
    _icon("generic", "internet", "network", "Internet"),
    _icon("generic", "firewall", "security", "Firewall"),
    _icon("generic", "load_balancer", "network", "Load Balancer"),
    _icon("generic", "database", "database", "Database"),
    _icon("generic", "cache", "cache", "Cache"),
    _icon("generic", "queue", "queue", "Queue"),
    _icon("generic", "storage", "storage", "Storage"),
    _icon("generic", "compute", "compute", "Compute"),
    _icon("generic", "cdn", "cdn", "CDN"),
]

# Build the lookup registry: (provider, service) -> ServiceIcon
ICON_REGISTRY: dict[tuple[str, str], ServiceIcon] = {}
for _icon_list in (_AWS_ICONS, _GCP_ICONS, _AZURE_ICONS, _GENERIC_ICONS):
    for _si in _icon_list:
        ICON_REGISTRY[(_si.provider, _si.service)] = _si

# Default fallback icon
_DEFAULT_ICON = ServiceIcon(
    provider="generic",
    service="unknown",
    category="compute",
    label="Service",
    color="#94a3b8",
    shape="rectangle",
    ascii_char="?",
)

_D2_ICON_BASE = "https://icons.terrastruct.com"
_D2_PROVIDER_PATHS = {
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
}


def get_icon(provider: str, service: str) -> ServiceIcon | None:
    """Look up icon metadata for a (provider, service) pair. Returns None if unknown."""
    return ICON_REGISTRY.get((provider.lower(), service.lower()))


def get_icon_or_default(provider: str, service: str) -> ServiceIcon:
    """Look up icon metadata, returning a generic fallback if unknown."""
    icon = get_icon(provider, service)
    if icon is not None:
        return icon
    # Try generic fallback by guessing category from service name
    for generic_key in ("compute", "database", "cache", "queue", "storage", "cdn"):
        if generic_key in service.lower():
            generic = ICON_REGISTRY.get(("generic", generic_key))
            if generic:
                return generic
    return _DEFAULT_ICON


def get_category_color(category: str) -> str:
    """Get the accent color for a service category."""
    return CATEGORY_COLORS.get(category, "#94a3b8")


def get_icon_url(provider: str, service: str) -> str:
    """Get a terrastruct CDN icon URL for D2 remote rendering."""
    provider_path = _D2_PROVIDER_PATHS.get(provider.lower(), "aws")
    return f"{_D2_ICON_BASE}/{provider_path}/{service}.svg"
