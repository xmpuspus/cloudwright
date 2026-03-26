"""Prompt constants, service catalogs, and configuration data."""

from __future__ import annotations

# -- Service categorization sets ---------------------------------------------------

DATA_STORE_SERVICES = {
    "rds",
    "aurora",
    "dynamodb",
    "s3",
    "elasticache",
    "redshift",
    "cloud_sql",
    "firestore",
    "spanner",
    "memorystore",
    "cloud_storage",
    "bigquery",
    "azure_sql",
    "cosmos_db",
    "azure_cache",
    "blob_storage",
    "synapse",
    "alloydb",
    "fsx",
    "efs",
    "databricks_vector_search",
    "databricks_volume",
}

DATABASE_SERVICES = {
    "rds",
    "aurora",
    "cloud_sql",
    "azure_sql",
    "cosmos_db",
    "spanner",
    "synapse",
    "redshift",
    "bigquery",
    "alloydb",
    "databricks_sql_warehouse",
}

COMPUTE_SERVICES = {
    "ec2",
    "ecs",
    "eks",
    "lambda",
    "compute_engine",
    "gke",
    "cloud_run",
    "cloud_functions",
    "app_engine",
    "virtual_machines",
    "aks",
    "azure_functions",
    "app_service",
    "container_apps",
    "fargate",
    "databricks_cluster",
    "databricks_notebook",
}

HIPAA_REQUIRED = {
    "audit_logging": {"cloudtrail", "cloud_logging", "azure_monitor", "databricks_unity_catalog"},
    "access_control": {"cognito", "firebase_auth", "azure_ad", "iam", "databricks_unity_catalog"},
}

# -- Compliance control prompt fragments -------------------------------------------

COMPLIANCE_CONTROLS: dict[str, str] = {
    "hipaa": (
        "REQUIRED: encryption_at_rest on all data stores, encryption_in_transit on all "
        "connections, audit_logging service (cloudtrail/cloud_logging/azure_monitor), "
        "access_control via auth service (cognito/firebase_auth/azure_ad), "
        "all services must be BAA-eligible"
    ),
    "pci-dss": (
        "REQUIRED: WAF/firewall on entry points, encryption on all data stores and connections, "
        "audit logging, network segmentation (separate tiers), no cardholder data in logs"
    ),
    "soc2": (
        "REQUIRED: audit logging service, encryption on data stores, access control service, "
        "monitoring/alerting (cloudwatch/cloud_monitoring/azure_monitor)"
    ),
    "gdpr": (
        "REQUIRED: encryption on all data stores, audit logging, access control service, "
        "data residency controls — do not store data outside approved regions"
    ),
    "fedramp": (
        "REQUIRED: FIPS 140-2 compliant services only, MFA/access control, audit logging, "
        "encryption at rest and in transit, US regions only"
    ),
}

# -- Service keys and model version strings ----------------------------------------

SERVICE_KEYS = """VALID SERVICE KEYS — use exactly these strings:
AWS: cloudfront, route53, api_gateway, waf, alb, nlb, ec2, ecs, eks, lambda, fargate,
     rds, aurora, dynamodb, elasticache, sqs, sns, s3, kinesis, redshift, emr, sagemaker,
     cognito, iam, step_functions, eventbridge, cloudwatch, cloudtrail, dms, migration_hub,
     direct_connect, vpn, codepipeline, codecommit, codebuild, ecr, config, guardduty,
     inspector, kms, shield, security_hub, glue, athena, fsx, efs, ebs
GCP: cloud_cdn, cloud_dns, cloud_load_balancing, cloud_armor, compute_engine, gke,
     cloud_run, cloud_functions, app_engine, cloud_sql, firestore, spanner, memorystore,
     pub_sub, cloud_storage, bigquery, dataflow, vertex_ai, firebase_auth, cloud_logging,
     cloud_build, artifact_registry, cloud_composer, dataproc, cloud_interconnect, alloydb
Azure: azure_cdn, azure_dns, app_gateway, azure_waf, azure_lb, virtual_machines, aks,
       container_apps, azure_functions, app_service, azure_sql, cosmos_db, azure_cache,
       service_bus, event_hubs, blob_storage, synapse, azure_ml, azure_ad, logic_apps,
       azure_monitor, azure_devops, azure_migrate, expressroute, azure_firewall,
       azure_sentinel, azure_policy, data_factory, api_management
Databricks: databricks_sql_warehouse, databricks_cluster, databricks_job, databricks_pipeline,
            databricks_model_serving, databricks_unity_catalog, databricks_vector_search,
            databricks_genie, databricks_notebook, databricks_secret_scope,
            databricks_dashboard, databricks_volume"""

MODEL_VERSION_GUIDANCE = """
CURRENT AI/ML MODEL VERSIONS (as of March 2026):
GCP Vertex AI: gemini-3.1-pro (flagship), gemini-3-flash, gemini-2.5-pro, gemini-2.5-flash
AWS Bedrock: anthropic.claude-opus-4-6-v1, anthropic.claude-sonnet-4-6, amazon.nova-pro-v1
AWS SageMaker: meta.llama3.3-70b, mistral-large-3
Azure OpenAI: gpt-5 (GA), gpt-5-mini, gpt-5-nano, gpt-5.2 (preview)
When an architecture includes ML/AI services (vertex_ai, sagemaker, azure_ml), use these current
model versions in the config. Do NOT use outdated versions like gemini-1.5-pro or gpt-4-turbo."""

# -- Provider service validation sets ----------------------------------------------

PROVIDER_SERVICES: dict[str, set[str]] = {
    "aws": {
        "cloudfront",
        "route53",
        "api_gateway",
        "waf",
        "alb",
        "nlb",
        "ec2",
        "ecs",
        "eks",
        "lambda",
        "fargate",
        "rds",
        "aurora",
        "dynamodb",
        "elasticache",
        "sqs",
        "sns",
        "s3",
        "kinesis",
        "redshift",
        "emr",
        "sagemaker",
        "cognito",
        "iam",
        "step_functions",
        "eventbridge",
        "cloudwatch",
        "cloudtrail",
        "dms",
        "migration_hub",
        "direct_connect",
        "vpn",
        "codepipeline",
        "codecommit",
        "codebuild",
        "ecr",
        "config",
        "guardduty",
        "inspector",
        "kms",
        "shield",
        "security_hub",
        "glue",
        "athena",
        "fsx",
        "efs",
        "ebs",
    },
    "gcp": {
        "cloud_cdn",
        "cloud_dns",
        "cloud_load_balancing",
        "cloud_armor",
        "compute_engine",
        "gke",
        "cloud_run",
        "cloud_functions",
        "app_engine",
        "cloud_sql",
        "firestore",
        "spanner",
        "memorystore",
        "pub_sub",
        "cloud_storage",
        "bigquery",
        "dataflow",
        "vertex_ai",
        "firebase_auth",
        "cloud_logging",
        "cloud_build",
        "artifact_registry",
        "cloud_composer",
        "dataproc",
        "cloud_interconnect",
        "alloydb",
    },
    "azure": {
        "azure_cdn",
        "azure_dns",
        "app_gateway",
        "azure_waf",
        "azure_lb",
        "virtual_machines",
        "aks",
        "container_apps",
        "azure_functions",
        "app_service",
        "azure_sql",
        "cosmos_db",
        "azure_cache",
        "service_bus",
        "event_hubs",
        "blob_storage",
        "synapse",
        "azure_ml",
        "azure_ad",
        "logic_apps",
        "azure_monitor",
        "azure_devops",
        "azure_migrate",
        "expressroute",
        "azure_firewall",
        "azure_sentinel",
        "azure_policy",
        "data_factory",
        "api_management",
    },
    "databricks": {
        "databricks_sql_warehouse",
        "databricks_cluster",
        "databricks_job",
        "databricks_pipeline",
        "databricks_model_serving",
        "databricks_unity_catalog",
        "databricks_vector_search",
        "databricks_genie",
        "databricks_notebook",
        "databricks_secret_scope",
        "databricks_dashboard",
        "databricks_volume",
    },
}

ALL_VALID_SERVICES: set[str] = set().union(*PROVIDER_SERVICES.values())

# -- Default instance types when LLM omits them -----------------------------------

DEFAULT_INSTANCE_TYPES: dict[str, dict[str, str]] = {
    "aws": {"compute": "m5.large", "database": "db.r5.large", "cache": "cache.r5.large"},
    "gcp": {"compute": "n2-standard-4", "database": "db-n1-standard-4", "cache": "M1"},
    "azure": {"compute": "Standard_D4s_v3", "database": "GP_Gen5_4", "cache": "C3"},
    "databricks": {"compute": "i3.xlarge", "database": "Small", "cache": "Small"},
}

DEFAULT_CONNECTION_PROTOCOLS: list[tuple[tuple[int, int], str, int]] = [
    ((0, 1), "HTTPS", 443),
    ((1, 2), "HTTPS", 443),
    ((2, 3), "TCP", 5432),
]

# -- Service normalization for LLM output drift ------------------------------------

SERVICE_NORMALIZATION: dict[str, str] = {
    "aws_rds": "rds",
    "aws_lambda": "lambda",
    "aws_ec2": "ec2",
    "aws_ecs": "ecs",
    "aws_eks": "eks",
    "aws_s3": "s3",
    "lambda_function": "lambda",
    "s3_bucket": "s3",
    "gcp_gke": "gke",
    "gcp_cloud_run": "cloud_run",
    "azure_aks": "aks",
    "azure_vm": "virtual_machines",
    "rds_postgres": "rds",
    "rds_mysql": "rds",
    "aurora_postgres": "aurora",
    "aurora_mysql": "aurora",
    "gcp_alloydb": "alloydb",
    "gcp_cloud_armor": "cloud_armor",
    "gcp_vertex_ai": "vertex_ai",
    "gcp_firestore": "firestore",
    "gcp_spanner": "spanner",
    "gcp_dataflow": "dataflow",
    "gcp_dataproc": "dataproc",
    "gcp_cloud_composer": "cloud_composer",
    "aws_eventbridge": "eventbridge",
    "aws_athena": "athena",
    "aws_glue": "glue",
    "aws_fargate": "fargate",
    "aws_shield": "shield",
    "azure_api_management": "api_management",
    "azure_data_factory": "data_factory",
    "azure_logic_apps": "logic_apps",
    "azure_cosmos_db": "cosmos_db",
    "azure_sentinel": "azure_sentinel",
    "memorystore_redis": "memorystore",
    "gcp_memorystore": "memorystore",
    "cloud_memorystore": "memorystore",
    "redis_memorystore": "memorystore",
    "cloud_function": "cloud_functions",
    "pubsub": "pub_sub",
    "pub/sub": "pub_sub",
    "cloud_run_service": "cloud_run",
    "gcs": "cloud_storage",
    "bq": "bigquery",
    "big_query": "bigquery",
    "cloud_sql_instance": "cloud_sql",
    "aws_sqs": "sqs",
    "aws_sns": "sns",
    "aws_cloudwatch": "cloudwatch",
    "aws_cloudtrail": "cloudtrail",
    "aws_kinesis": "kinesis",
    "azure_blob": "blob_storage",
    "azure_cosmosdb": "cosmos_db",
    "azure_redis": "azure_cache",
    "redis": "elasticache",
    "postgres": "rds",
    "mysql": "rds",
    "mongodb": "cosmos_db",
    "kubernetes": "eks",
    "docker": "ecs",
    "sql_warehouse": "databricks_sql_warehouse",
    "dlt": "databricks_pipeline",
    "delta_live_tables": "databricks_pipeline",
    "dbx_cluster": "databricks_cluster",
    "dbx_job": "databricks_job",
    "mlflow_serving": "databricks_model_serving",
    "databricks_dlt": "databricks_pipeline",
    "unity_catalog": "databricks_unity_catalog",
    "secret_scope": "databricks_secret_scope",
}

SERVICE_ENGINE_SUFFIXES: dict[str, str] = {
    "rds_postgres": "postgres",
    "rds_mysql": "mysql",
    "aurora_postgres": "postgres",
    "aurora_mysql": "mysql",
}

# -- Ambiguity detection keywords -------------------------------------------------

CLOUD_KEYWORDS = {
    "aws",
    "gcp",
    "azure",
    "cloud",
    "kubernetes",
    "k8s",
    "docker",
    "serverless",
    "lambda",
    "ec2",
    "s3",
    "rds",
    "vpc",
    "api",
    "web",
    "app",
    "database",
    "server",
    "microservice",
    "container",
    "terraform",
    "deploy",
    "databricks",
    "ecs",
    "eks",
    "gke",
    "fargate",
    "cloudfront",
    "alb",
    "cdn",
    "redis",
    "postgres",
    "mysql",
    "dynamodb",
    "sqs",
    "sns",
    "kafka",
    "tier",
    "architecture",
    "infra",
}

# -- System prompts ----------------------------------------------------------------

DESIGN_SYSTEM = f"""You generate cloud architectures as structured JSON.

Given a natural language description, produce a JSON object with this exact structure:
{{
  "name": "Short descriptive name for the architecture",
  "provider": "aws|gcp|azure|databricks",
  "region": "primary region (e.g. us-east-1, us-central1, eastus)",
  "components": [
    {{
      "id": "unique_snake_case_id",
      "service": "<service_key>",
      "provider": "aws|gcp|azure|databricks",
      "label": "Human-readable label",
      "description": "Brief purpose note (instance type, config)",
      "tier": <integer 0-4>,
      "config": {{
        "instance_type": "optional",
        "multi_az": true,
        "encryption": true,
        "auto_scaling": true
      }}
    }}
  ],
  "connections": [
    {{
      "source": "component_id",
      "target": "component_id",
      "label": "HTTPS/443",
      "protocol": "HTTPS",
      "port": 443
    }}
  ],
  "rationale": [
    {{"decision": "Short description of a key design decision", "reason": "Why this choice was made"}}
  ],
  "suggestions": ["add a Redis cache for session management", "swap RDS for Aurora Serverless", "add CloudWatch monitoring"]
}}

TIER RULES (vertical positioning, top to bottom):
- Tier 0: Internet-facing entry points (CDN, DNS, API gateway, WAF, users)
- Tier 1: Load balancing and ingress
- Tier 2: Compute (VMs, containers, serverless functions)
- Tier 3: Data layer (databases, caches, message queues)
- Tier 4: Storage, backup, analytics, ML, monitoring

{SERVICE_KEYS}

RULES:
- Use 4-12 components to keep architectures clear and practical
- Every component must connect to at least one other component
- Connections flow logically from entry points down to data layer
- Include meaningful labels on connections (protocols, ports, or data type)
- For production workloads, enable multi_az and encryption in config by default
- Match the provider to the user's description; default to aws if unspecified
- Respond with ONLY the JSON object — no markdown, no explanation text
- Include 2-4 "rationale" entries explaining key design decisions
- Include 3 "suggestions" for modifications the user might want to make next
- When the user mentions a specific service by name (e.g. "use RDS", "with Lambda"), INCLUDE that exact service in components. Do not substitute alternatives unless explicitly asked.
- Use EXACT service keys listed above. Do not invent compound keys like 'rds_postgres' — use 'rds' with `engine: postgres` in config.

For ALL architectures, ensure component configs include:
- encryption: true on all data stores and caches
- multi_az: true on all databases (for production workloads)
- backup: true on all databases
- auto_scaling: true on all compute services
- security_groups: true on all VPC-connected resources
- ALWAYS include instance_type in config for EC2/compute_engine/virtual_machines (e.g. m5.large, n2-standard-4, Standard_D4s_v3)
- ALWAYS include instance_class in config for RDS/Aurora/Cloud SQL/Azure SQL (e.g. db.r5.large, db-n1-standard-4)
- ALWAYS include node_type in config for ElastiCache/Memorystore (e.g. cache.r5.large)
- Include storage_gb on all database and storage components
- Include count on compute components when multiple instances needed
{MODEL_VERSION_GUIDANCE}

EXAMPLES:

User: "Simple web app on AWS"
Response:
{{"name": "Simple Web App", "provider": "aws", "region": "us-east-1", "components": [{{"id": "alb", "service": "alb", "provider": "aws", "label": "Load Balancer", "tier": 1, "config": {{}}}}, {{"id": "web", "service": "ec2", "provider": "aws", "label": "Web Server", "tier": 2, "config": {{"instance_type": "t3.medium", "auto_scaling": true}}}}, {{"id": "db", "service": "rds", "provider": "aws", "label": "PostgreSQL", "tier": 3, "config": {{"engine": "postgres", "instance_class": "db.t3.medium", "multi_az": true, "encryption": true}}}}], "connections": [{{"source": "alb", "target": "web", "label": "HTTP/80"}}, {{"source": "web", "target": "db", "label": "TCP/5432"}}], "rationale": [{{"decision": "ALB for load balancing", "reason": "Handles HTTP routing and health checks"}}], "suggestions": ["Add ElastiCache for session caching", "Add CloudFront CDN", "Add S3 for static assets"]}}

User: "Serverless API"
Response:
{{"name": "Serverless API", "provider": "aws", "region": "us-east-1", "components": [{{"id": "apigw", "service": "api_gateway", "provider": "aws", "label": "API Gateway", "tier": 0, "config": {{}}}}, {{"id": "fn", "service": "lambda", "provider": "aws", "label": "API Handler", "tier": 2, "config": {{"memory_mb": 512, "runtime": "python3.12"}}}}, {{"id": "table", "service": "dynamodb", "provider": "aws", "label": "Data Store", "tier": 3, "config": {{"encryption": true}}}}], "connections": [{{"source": "apigw", "target": "fn", "label": "invoke"}}, {{"source": "fn", "target": "table", "label": "read/write"}}], "rationale": [{{"decision": "Serverless stack", "reason": "Zero idle cost, auto-scaling"}}], "suggestions": ["Add Cognito for auth", "Add SQS for async processing", "Add S3 for file uploads"]}}"""

MODIFY_SYSTEM = f"""You modify an existing cloud architecture based on user instructions.

You will receive the current architecture JSON and a modification instruction.
Return the COMPLETE updated architecture JSON in the same format — never return partial updates.
Preserve all existing component IDs unless explicitly removing or renaming them.
Apply the requested change precisely without unnecessary restructuring.
Respond with ONLY the JSON object — no markdown, no explanation.
{MODEL_VERSION_GUIDANCE}

EXAMPLE:
Current architecture has components: alb, web, db.
Modification: "Add a Redis cache between web and db"
Response:
{{"name": "Web App with Cache", "provider": "aws", "region": "us-east-1", "components": [{{"id": "alb", "service": "alb", "provider": "aws", "label": "Load Balancer", "tier": 1, "config": {{}}}}, {{"id": "web", "service": "ec2", "provider": "aws", "label": "Web Server", "tier": 2, "config": {{"instance_type": "t3.medium"}}}}, {{"id": "cache", "service": "elasticache", "provider": "aws", "label": "Redis Cache", "tier": 3, "config": {{"engine": "redis", "node_type": "cache.t3.medium"}}}}, {{"id": "db", "service": "rds", "provider": "aws", "label": "PostgreSQL", "tier": 3, "config": {{"engine": "postgres", "instance_class": "db.t3.medium"}}}}], "connections": [{{"source": "alb", "target": "web", "label": "HTTP/80"}}, {{"source": "web", "target": "cache", "label": "TCP/6379"}}, {{"source": "web", "target": "db", "label": "TCP/5432"}}]}}"""

CHAT_SYSTEM = f"""You are a cloud architecture assistant. You help design and refine architectures through conversation.

When the user asks you to generate or modify an architecture, respond with a JSON object using this schema:
- Top level: name, provider, region, components (array), connections (array)
- Each component: id (string), service (string — use one of the service keys below), provider, label, description, tier (int), config (object)
- Each connection: source (component id), target (component id), label, protocol, port

When generating architecture JSON, also include:
- "rationale": key design decisions with reasons
- "suggestions": 3 concrete modifications the user could request next

When the user asks questions or wants to discuss trade-offs, respond conversationally — no JSON needed.

{SERVICE_KEYS}
{MODEL_VERSION_GUIDANCE}"""

IMPORT_SYSTEM = f"""You parse infrastructure descriptions or state into structured JSON architecture specs.

Given a description of existing infrastructure, produce a JSON object using the same schema as a design prompt
(name, provider, region, components, connections).
Focus on mapping existing resources to the correct service keys, preserving the actual topology,
and including real configuration values (instance types, storage sizes, etc.).

Respond with ONLY the JSON object — no markdown, no explanation.

{SERVICE_KEYS}

TERRAFORM RESOURCE TYPE MAPPING (use these when parsing Terraform state/config):
- aws_instance, aws_autoscaling_group -> ec2
- aws_lb, aws_alb -> alb
- aws_rds_instance, aws_rds_cluster -> rds (aurora for clusters)
- aws_lambda_function -> lambda
- aws_ecs_service, aws_ecs_cluster -> ecs
- aws_eks_cluster -> eks
- aws_s3_bucket -> s3
- aws_dynamodb_table -> dynamodb
- aws_elasticache_cluster -> elasticache
- aws_cloudfront_distribution -> cloudfront
- aws_sqs_queue -> sqs
- google_compute_instance -> compute_engine
- google_container_cluster -> gke
- google_sql_database_instance -> cloud_sql
- google_cloud_run_service -> cloud_run
- google_storage_bucket -> cloud_storage
- azurerm_virtual_machine -> virtual_machines
- azurerm_kubernetes_cluster -> aks
- azurerm_mssql_server -> azure_sql
- azurerm_cosmosdb_account -> cosmos_db
- azurerm_storage_account -> blob_storage
- databricks_sql_endpoint -> databricks_sql_warehouse
- databricks_cluster -> databricks_cluster
- databricks_job -> databricks_job
- databricks_pipeline -> databricks_pipeline
- databricks_serving_endpoint -> databricks_model_serving
- databricks_catalog -> databricks_unity_catalog
- databricks_vector_search_endpoint -> databricks_vector_search
- databricks_notebook -> databricks_notebook
- databricks_secret_scope -> databricks_secret_scope
- databricks_volume -> databricks_volume
- databricks_sql_dashboard -> databricks_dashboard

RULES:
- Map every resource to its closest service key
- Preserve actual instance types and configurations
- Include all connections between resources
- Respond with ONLY the JSON object"""

MIGRATION_SYSTEM = f"""You design target cloud architectures for migration scenarios.

Given a source architecture and migration requirements, produce a JSON object representing the target architecture.
Focus on service equivalence across cloud providers, preserving functionality while modernizing where appropriate,
and including realistic instance types for the target provider.

Respond with ONLY the JSON object — no markdown, no explanation.

{SERVICE_KEYS}

RULES:
- Map each source service to its target provider equivalent
- Preserve capacity (instance sizes, storage, redundancy)
- Include instance_type/instance_class in all compute/database configs
- Respond with ONLY the JSON object"""

COMPARISON_SYSTEM = f"""You generate a representative cloud architecture that can be compared across providers.

Given a workload description, produce a JSON object representing a single canonical architecture.
This architecture will be re-priced across multiple cloud providers for comparison.

Respond with ONLY the JSON object — no markdown, no explanation.

{SERVICE_KEYS}

RULES:
- Design a single provider-agnostic architecture using the primary provider's service keys
- Include realistic instance types and configurations for accurate pricing
- Respond with ONLY the JSON object"""
