"""Cloud provider service definitions and mappings."""

from silmaril.providers.aws import AWS_SERVICES
from silmaril.providers.azure import AZURE_SERVICES
from silmaril.providers.gcp import GCP_SERVICES

PROVIDERS = {
    "aws": AWS_SERVICES,
    "gcp": GCP_SERVICES,
    "azure": AZURE_SERVICES,
}

# Cross-cloud service equivalence map: aws_key -> {gcp: key, azure: key}
EQUIVALENCES = {
    "ec2": {"gcp": "compute_engine", "azure": "virtual_machines"},
    "lambda": {"gcp": "cloud_functions", "azure": "azure_functions"},
    "ecs": {"gcp": "cloud_run", "azure": "container_apps"},
    "eks": {"gcp": "gke", "azure": "aks"},
    "rds": {"gcp": "cloud_sql", "azure": "azure_sql"},
    "aurora": {"gcp": "cloud_sql", "azure": "azure_sql"},
    "dynamodb": {"gcp": "firestore", "azure": "cosmos_db"},
    "elasticache": {"gcp": "memorystore", "azure": "azure_cache"},
    "s3": {"gcp": "cloud_storage", "azure": "blob_storage"},
    "sqs": {"gcp": "pub_sub", "azure": "service_bus"},
    "sns": {"gcp": "pub_sub", "azure": "event_hubs"},
    "cloudfront": {"gcp": "cloud_cdn", "azure": "azure_cdn"},
    "alb": {"gcp": "cloud_load_balancing", "azure": "app_gateway"},
    "nlb": {"gcp": "cloud_load_balancing", "azure": "azure_lb"},
    "route53": {"gcp": "cloud_dns", "azure": "azure_dns"},
    "waf": {"gcp": "cloud_armor", "azure": "azure_waf"},
    "kinesis": {"gcp": "dataflow", "azure": "event_hubs"},
    "redshift": {"gcp": "bigquery", "azure": "synapse"},
    "sagemaker": {"gcp": "vertex_ai", "azure": "azure_ml"},
    "cognito": {"gcp": "firebase_auth", "azure": "azure_ad"},
    "step_functions": {"gcp": "workflows", "azure": "logic_apps"},
    "api_gateway": {"gcp": "api_gateway", "azure": "api_management"},
}


def get_equivalent(service: str, from_provider: str, to_provider: str) -> str | None:
    """Get the equivalent service key in another cloud provider."""
    if from_provider == to_provider:
        return service

    if from_provider == "aws":
        mapping = EQUIVALENCES.get(service, {})
        return mapping.get(to_provider)

    # Reverse lookup: find the AWS key for this service, then map to target
    for aws_key, mappings in EQUIVALENCES.items():
        if mappings.get(from_provider) == service:
            if to_provider == "aws":
                return aws_key
            return mappings.get(to_provider)

    return None


__all__ = ["AWS_SERVICES", "GCP_SERVICES", "AZURE_SERVICES", "PROVIDERS", "EQUIVALENCES", "get_equivalent"]
