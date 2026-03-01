"""Pre-computed architecture templates for common patterns."""

from __future__ import annotations

TEMPLATES: dict[str, dict] = {
    "3-tier-web-aws": {
        "name": "3-Tier Web Application (AWS)",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "cdn",
                "service": "cloudfront",
                "provider": "aws",
                "label": "CloudFront CDN",
                "tier": 0,
                "config": {"https": True},
            },
            {
                "id": "alb",
                "service": "alb",
                "provider": "aws",
                "label": "Application Load Balancer",
                "tier": 1,
                "config": {"https": True, "health_check": True},
            },
            {
                "id": "web",
                "service": "ec2",
                "provider": "aws",
                "label": "Web / App Servers",
                "tier": 2,
                "config": {"instance_type": "m5.large", "count": 2, "auto_scaling": True, "security_groups": True},
            },
            {
                "id": "db",
                "service": "rds",
                "provider": "aws",
                "label": "RDS PostgreSQL",
                "tier": 3,
                "config": {
                    "instance_class": "db.r5.large",
                    "engine": "postgres",
                    "multi_az": True,
                    "encryption": True,
                    "backup": True,
                    "storage_gb": 100,
                },
            },
        ],
        "connections": [
            {"source": "cdn", "target": "alb", "label": "HTTPS/443", "protocol": "HTTPS", "port": 443},
            {"source": "alb", "target": "web", "label": "HTTP/80", "protocol": "HTTP", "port": 80},
            {"source": "web", "target": "db", "label": "TCP/5432", "protocol": "TCP", "port": 5432},
        ],
        "rationale": [
            {"decision": "CloudFront for static asset caching", "reason": "Reduces latency and origin load"},
            {"decision": "ALB for HTTP traffic distribution", "reason": "Layer-7 routing and health checks"},
            {"decision": "RDS Multi-AZ", "reason": "Automatic failover for production durability"},
        ],
        "suggestions": [
            "Add ElastiCache for session caching",
            "Add S3 for static asset storage",
            "Add CloudWatch for monitoring and alerting",
        ],
        "keywords": ["3-tier", "three-tier", "web app", "web application", "alb", "rds", "postgres", "mysql"],
    },
    "serverless-api-aws": {
        "name": "Serverless API (AWS)",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "apigw",
                "service": "api_gateway",
                "provider": "aws",
                "label": "API Gateway",
                "tier": 0,
                "config": {"https": True, "throttling": True},
            },
            {
                "id": "fn",
                "service": "lambda",
                "provider": "aws",
                "label": "Lambda Functions",
                "tier": 2,
                "config": {"runtime": "python3.12", "auto_scaling": True, "memory_mb": 512},
            },
            {
                "id": "db",
                "service": "dynamodb",
                "provider": "aws",
                "label": "DynamoDB",
                "tier": 3,
                "config": {"encryption": True, "backup": True, "on_demand": True},
            },
        ],
        "connections": [
            {"source": "apigw", "target": "fn", "label": "Invoke", "protocol": "HTTPS", "port": 443},
            {"source": "fn", "target": "db", "label": "SDK", "protocol": "HTTPS", "port": 443},
        ],
        "rationale": [
            {"decision": "Lambda for compute", "reason": "Zero server management, scales to zero"},
            {"decision": "DynamoDB for storage", "reason": "Serverless, single-digit ms latency at any scale"},
        ],
        "suggestions": [
            "Add Cognito for user authentication",
            "Add SQS for async job processing",
            "Add CloudFront in front of API Gateway for global distribution",
        ],
        "keywords": ["serverless", "lambda", "api gateway", "dynamodb", "api", "rest api", "function"],
    },
    "3-tier-web-gcp": {
        "name": "3-Tier Web Application (GCP)",
        "provider": "gcp",
        "region": "us-central1",
        "components": [
            {
                "id": "cdn",
                "service": "cloud_cdn",
                "provider": "gcp",
                "label": "Cloud CDN",
                "tier": 0,
                "config": {"https": True},
            },
            {
                "id": "lb",
                "service": "cloud_load_balancing",
                "provider": "gcp",
                "label": "Cloud Load Balancing",
                "tier": 1,
                "config": {"https": True, "health_check": True},
            },
            {
                "id": "app",
                "service": "cloud_run",
                "provider": "gcp",
                "label": "Cloud Run",
                "tier": 2,
                "config": {
                    "auto_scaling": True,
                    "min_instances": 1,
                    "max_instances": 10,
                    "cpu": "1",
                    "memory": "512Mi",
                },
            },
            {
                "id": "db",
                "service": "cloud_sql",
                "provider": "gcp",
                "label": "Cloud SQL PostgreSQL",
                "tier": 3,
                "config": {
                    "instance_class": "db-n1-standard-4",
                    "engine": "postgres",
                    "high_availability": True,
                    "encryption": True,
                    "backup": True,
                    "storage_gb": 100,
                },
            },
        ],
        "connections": [
            {"source": "cdn", "target": "lb", "label": "HTTPS/443", "protocol": "HTTPS", "port": 443},
            {"source": "lb", "target": "app", "label": "HTTP/8080", "protocol": "HTTP", "port": 8080},
            {"source": "app", "target": "db", "label": "TCP/5432", "protocol": "TCP", "port": 5432},
        ],
        "rationale": [
            {"decision": "Cloud Run for stateless compute", "reason": "Managed containers with autoscaling"},
            {"decision": "Cloud SQL HA", "reason": "Regional failover for production durability"},
        ],
        "suggestions": [
            "Add Memorystore for Redis caching",
            "Add Cloud Storage for static assets",
            "Add Cloud Armor for WAF protection",
        ],
        "keywords": ["3-tier", "three-tier", "web app", "gcp", "google", "cloud run", "cloud sql"],
    },
    "microservices-aws": {
        "name": "Microservices Platform (AWS)",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "alb",
                "service": "alb",
                "provider": "aws",
                "label": "Application Load Balancer",
                "tier": 1,
                "config": {"https": True, "health_check": True},
            },
            {
                "id": "ecs",
                "service": "ecs",
                "provider": "aws",
                "label": "ECS Fargate Services",
                "tier": 2,
                "config": {"launch_type": "FARGATE", "auto_scaling": True, "count": 2, "security_groups": True},
            },
            {
                "id": "db",
                "service": "rds",
                "provider": "aws",
                "label": "RDS PostgreSQL",
                "tier": 3,
                "config": {
                    "instance_class": "db.r5.large",
                    "engine": "postgres",
                    "multi_az": True,
                    "encryption": True,
                    "backup": True,
                    "storage_gb": 100,
                },
            },
            {
                "id": "cache",
                "service": "elasticache",
                "provider": "aws",
                "label": "ElastiCache Redis",
                "tier": 3,
                "config": {"node_type": "cache.r5.large", "engine": "redis", "encryption": True, "backup": True},
            },
            {
                "id": "queue",
                "service": "sqs",
                "provider": "aws",
                "label": "SQS Message Queue",
                "tier": 3,
                "config": {"encryption": True},
            },
        ],
        "connections": [
            {"source": "alb", "target": "ecs", "label": "HTTP/8080", "protocol": "HTTP", "port": 8080},
            {"source": "ecs", "target": "db", "label": "TCP/5432", "protocol": "TCP", "port": 5432},
            {"source": "ecs", "target": "cache", "label": "TCP/6379", "protocol": "TCP", "port": 6379},
            {"source": "ecs", "target": "queue", "label": "HTTPS/443", "protocol": "HTTPS", "port": 443},
        ],
        "rationale": [
            {"decision": "ECS Fargate for containers", "reason": "No EC2 management, per-task billing"},
            {"decision": "ElastiCache for session/caching", "reason": "Sub-ms latency for hot data"},
            {"decision": "SQS for async decoupling", "reason": "At-least-once delivery between services"},
        ],
        "suggestions": [
            "Add ECR for container image registry",
            "Add CloudWatch for centralized logging",
            "Add X-Ray for distributed tracing",
        ],
        "keywords": ["microservices", "containers", "ecs", "fargate", "docker", "sqs", "elasticache"],
    },
    "ml-pipeline-gcp": {
        "name": "ML Pipeline (GCP)",
        "provider": "gcp",
        "region": "us-central1",
        "components": [
            {
                "id": "storage",
                "service": "cloud_storage",
                "provider": "gcp",
                "label": "Cloud Storage",
                "tier": 4,
                "config": {"encryption": True, "backup": True},
            },
            {"id": "pubsub", "service": "pub_sub", "provider": "gcp", "label": "Pub/Sub", "tier": 3, "config": {}},
            {
                "id": "dataflow",
                "service": "dataflow",
                "provider": "gcp",
                "label": "Dataflow",
                "tier": 3,
                "config": {"auto_scaling": True},
            },
            {
                "id": "bq",
                "service": "bigquery",
                "provider": "gcp",
                "label": "BigQuery",
                "tier": 4,
                "config": {"encryption": True, "backup": True},
            },
            {
                "id": "vertex",
                "service": "vertex_ai",
                "provider": "gcp",
                "label": "Vertex AI",
                "tier": 4,
                "config": {"model": "gemini-3.1-pro"},
            },
        ],
        "connections": [
            {"source": "storage", "target": "pubsub", "label": "notifications", "protocol": "HTTPS", "port": 443},
            {"source": "pubsub", "target": "dataflow", "label": "stream", "protocol": "HTTPS", "port": 443},
            {"source": "dataflow", "target": "bq", "label": "write", "protocol": "HTTPS", "port": 443},
            {"source": "bq", "target": "vertex", "label": "training data", "protocol": "HTTPS", "port": 443},
        ],
        "rationale": [
            {"decision": "Pub/Sub for event ingestion", "reason": "Decouples data producers from pipeline"},
            {"decision": "Dataflow for stream processing", "reason": "Managed Apache Beam, auto-scales"},
            {"decision": "BigQuery as data warehouse", "reason": "Petabyte-scale analytics, serverless"},
        ],
        "suggestions": [
            "Add Cloud Composer for workflow orchestration",
            "Add Artifact Registry for model versioning",
            "Add Cloud Monitoring for pipeline observability",
        ],
        "keywords": ["ml", "machine learning", "pipeline", "gcp", "vertex", "bigquery", "dataflow", "pubsub"],
    },
    "data-warehouse-aws": {
        "name": "Data Warehouse (AWS)",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "kinesis",
                "service": "kinesis",
                "provider": "aws",
                "label": "Kinesis Data Streams",
                "tier": 3,
                "config": {"encryption": True},
            },
            {"id": "glue", "service": "glue", "provider": "aws", "label": "AWS Glue ETL", "tier": 3, "config": {}},
            {
                "id": "s3",
                "service": "s3",
                "provider": "aws",
                "label": "S3 Data Lake",
                "tier": 4,
                "config": {"encryption": True, "backup": True},
            },
            {
                "id": "redshift",
                "service": "redshift",
                "provider": "aws",
                "label": "Redshift",
                "tier": 4,
                "config": {
                    "instance_type": "ra3.xlplus",
                    "encryption": True,
                    "backup": True,
                    "multi_az": True,
                    "storage_gb": 1000,
                },
            },
            {
                "id": "athena",
                "service": "athena",
                "provider": "aws",
                "label": "Athena",
                "tier": 4,
                "config": {"encryption": True},
            },
        ],
        "connections": [
            {"source": "kinesis", "target": "glue", "label": "stream", "protocol": "HTTPS", "port": 443},
            {"source": "glue", "target": "s3", "label": "write", "protocol": "HTTPS", "port": 443},
            {"source": "s3", "target": "redshift", "label": "COPY", "protocol": "HTTPS", "port": 443},
            {"source": "s3", "target": "athena", "label": "query", "protocol": "HTTPS", "port": 443},
        ],
        "rationale": [
            {"decision": "Kinesis for real-time ingestion", "reason": "Durable streaming at scale"},
            {"decision": "S3 as data lake foundation", "reason": "Cost-effective, queryable by Athena"},
            {"decision": "Redshift for analytics queries", "reason": "Columnar storage, petabyte-scale"},
        ],
        "suggestions": [
            "Add EMR for Spark-based transformations",
            "Add QuickSight for BI dashboards",
            "Add Lake Formation for fine-grained access control",
        ],
        "keywords": ["data warehouse", "analytics", "etl", "redshift", "glue", "kinesis", "athena", "data lake"],
    },
    "web-app-azure": {
        "name": "Web Application (Azure)",
        "provider": "azure",
        "region": "eastus",
        "components": [
            {
                "id": "cdn",
                "service": "azure_cdn",
                "provider": "azure",
                "label": "Azure CDN",
                "tier": 0,
                "config": {"https": True},
            },
            {
                "id": "agw",
                "service": "app_gateway",
                "provider": "azure",
                "label": "Application Gateway",
                "tier": 1,
                "config": {"https": True, "waf": True},
            },
            {
                "id": "app",
                "service": "app_service",
                "provider": "azure",
                "label": "App Service",
                "tier": 2,
                "config": {"sku": "P2v3", "auto_scaling": True, "count": 2},
            },
            {
                "id": "db",
                "service": "azure_sql",
                "provider": "azure",
                "label": "Azure SQL Database",
                "tier": 3,
                "config": {
                    "instance_class": "GP_Gen5_4",
                    "multi_az": True,
                    "encryption": True,
                    "backup": True,
                    "storage_gb": 100,
                },
            },
        ],
        "connections": [
            {"source": "cdn", "target": "agw", "label": "HTTPS/443", "protocol": "HTTPS", "port": 443},
            {"source": "agw", "target": "app", "label": "HTTP/80", "protocol": "HTTP", "port": 80},
            {"source": "app", "target": "db", "label": "TCP/1433", "protocol": "TCP", "port": 1433},
        ],
        "rationale": [
            {"decision": "App Gateway with WAF", "reason": "Layer-7 LB with built-in DDoS protection"},
            {"decision": "App Service for PaaS compute", "reason": "Managed runtime, auto-scaling, easy deploys"},
        ],
        "suggestions": [
            "Add Azure Cache for Redis",
            "Add Service Bus for async messaging",
            "Add Azure Monitor for observability",
        ],
        "keywords": ["azure", "web app", "app service", "azure sql", "3-tier", "three-tier"],
    },
    "event-driven-aws": {
        "name": "Event-Driven Architecture (AWS)",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "apigw",
                "service": "api_gateway",
                "provider": "aws",
                "label": "API Gateway",
                "tier": 0,
                "config": {"https": True},
            },
            {
                "id": "fn_ingest",
                "service": "lambda",
                "provider": "aws",
                "label": "Ingest Lambda",
                "tier": 2,
                "config": {"runtime": "python3.12", "auto_scaling": True},
            },
            {
                "id": "eventbus",
                "service": "eventbridge",
                "provider": "aws",
                "label": "EventBridge",
                "tier": 3,
                "config": {"encryption": True},
            },
            {
                "id": "fn_process",
                "service": "lambda",
                "provider": "aws",
                "label": "Processing Lambda",
                "tier": 2,
                "config": {"runtime": "python3.12", "auto_scaling": True},
            },
            {
                "id": "db",
                "service": "dynamodb",
                "provider": "aws",
                "label": "DynamoDB",
                "tier": 3,
                "config": {"encryption": True, "backup": True, "on_demand": True},
            },
        ],
        "connections": [
            {"source": "apigw", "target": "fn_ingest", "label": "Invoke", "protocol": "HTTPS", "port": 443},
            {"source": "fn_ingest", "target": "eventbus", "label": "PutEvents", "protocol": "HTTPS", "port": 443},
            {"source": "eventbus", "target": "fn_process", "label": "Trigger", "protocol": "HTTPS", "port": 443},
            {"source": "fn_process", "target": "db", "label": "SDK", "protocol": "HTTPS", "port": 443},
        ],
        "rationale": [
            {"decision": "EventBridge for event routing", "reason": "Decouples producers and consumers"},
            {"decision": "Lambda for processing", "reason": "Pay-per-invocation, scales to demand"},
        ],
        "suggestions": [
            "Add SQS DLQ for failed event handling",
            "Add Step Functions for multi-step workflows",
            "Add CloudWatch for event monitoring",
        ],
        "keywords": ["event-driven", "events", "eventbridge", "lambda", "serverless", "async"],
    },
    "kubernetes-aws": {
        "name": "Kubernetes Platform (AWS EKS)",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "alb",
                "service": "alb",
                "provider": "aws",
                "label": "Application Load Balancer",
                "tier": 1,
                "config": {"https": True, "health_check": True},
            },
            {
                "id": "eks",
                "service": "eks",
                "provider": "aws",
                "label": "EKS Cluster",
                "tier": 2,
                "config": {"instance_type": "m5.xlarge", "count": 3, "auto_scaling": True, "security_groups": True},
            },
            {
                "id": "ecr",
                "service": "ecr",
                "provider": "aws",
                "label": "ECR Container Registry",
                "tier": 4,
                "config": {"encryption": True, "scan_on_push": True},
            },
            {
                "id": "db",
                "service": "rds",
                "provider": "aws",
                "label": "RDS PostgreSQL",
                "tier": 3,
                "config": {
                    "instance_class": "db.r5.large",
                    "engine": "postgres",
                    "multi_az": True,
                    "encryption": True,
                    "backup": True,
                    "storage_gb": 100,
                },
            },
            {
                "id": "cache",
                "service": "elasticache",
                "provider": "aws",
                "label": "ElastiCache Redis",
                "tier": 3,
                "config": {"node_type": "cache.r5.large", "engine": "redis", "encryption": True},
            },
        ],
        "connections": [
            {"source": "alb", "target": "eks", "label": "HTTP/8080", "protocol": "HTTP", "port": 8080},
            {"source": "ecr", "target": "eks", "label": "pull", "protocol": "HTTPS", "port": 443},
            {"source": "eks", "target": "db", "label": "TCP/5432", "protocol": "TCP", "port": 5432},
            {"source": "eks", "target": "cache", "label": "TCP/6379", "protocol": "TCP", "port": 6379},
        ],
        "rationale": [
            {"decision": "EKS for orchestration", "reason": "Managed Kubernetes, integrates with AWS IAM/VPC"},
            {"decision": "ECR for image storage", "reason": "Private registry, integrates natively with EKS"},
        ],
        "suggestions": [
            "Add AWS Load Balancer Controller for ingress",
            "Add CloudWatch Container Insights for monitoring",
            "Add Karpenter for intelligent node autoscaling",
        ],
        "keywords": ["kubernetes", "k8s", "eks", "containers", "docker", "helm", "pods"],
    },
    "static-site-aws": {
        "name": "Static Website (AWS)",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "cdn",
                "service": "cloudfront",
                "provider": "aws",
                "label": "CloudFront",
                "tier": 0,
                "config": {"https": True},
            },
            {
                "id": "storage",
                "service": "s3",
                "provider": "aws",
                "label": "S3 Static Assets",
                "tier": 4,
                "config": {"encryption": True, "backup": True, "static_website": True},
            },
            {
                "id": "apigw",
                "service": "api_gateway",
                "provider": "aws",
                "label": "API Gateway",
                "tier": 0,
                "config": {"https": True},
            },
            {
                "id": "fn",
                "service": "lambda",
                "provider": "aws",
                "label": "Lambda Backend",
                "tier": 2,
                "config": {"runtime": "python3.12", "auto_scaling": True},
            },
        ],
        "connections": [
            {"source": "cdn", "target": "storage", "label": "origin", "protocol": "HTTPS", "port": 443},
            {"source": "cdn", "target": "apigw", "label": "API", "protocol": "HTTPS", "port": 443},
            {"source": "apigw", "target": "fn", "label": "Invoke", "protocol": "HTTPS", "port": 443},
        ],
        "rationale": [
            {"decision": "S3 + CloudFront for static hosting", "reason": "Globally distributed, near-zero cost"},
            {"decision": "Lambda for backend APIs", "reason": "No server management, scales to zero"},
        ],
        "suggestions": [
            "Add DynamoDB for data persistence",
            "Add Cognito for user authentication",
            "Add Route53 for custom domain",
        ],
        "keywords": ["static", "static site", "spa", "single page", "s3", "cloudfront", "jamstack"],
    },
}

# Keywords that indicate specific providers to help template selection
_PROVIDER_KEYWORDS = {
    "aws": {"aws", "amazon", "ec2", "s3", "lambda", "rds", "dynamodb", "eks", "ecs"},
    "gcp": {"gcp", "google", "google cloud", "gke", "cloud run", "bigquery", "vertex"},
    "azure": {"azure", "microsoft", "azure sql", "aks", "app service", "cosmos"},
}


def match_template(description: str, provider: str | None = None) -> dict | None:
    """Return the best-matching template if confidence > 0.7, else None."""
    desc = description.lower()

    # Detect provider from description if not specified
    if not provider:
        for p, kws in _PROVIDER_KEYWORDS.items():
            if any(kw in desc for kw in kws):
                provider = p
                break

    best_key: str | None = None
    best_score = 0.0

    for key, template in TEMPLATES.items():
        # Skip templates that don't match the detected provider
        if provider and template["provider"] != provider:
            continue

        keywords: list[str] = template.get("keywords", [])
        if not keywords:
            continue

        hits = sum(1 for kw in keywords if kw in desc)
        score = hits / len(keywords)

        if score > best_score:
            best_score = score
            best_key = key

    if best_score >= 0.7 and best_key:
        return TEMPLATES[best_key]
    return None
