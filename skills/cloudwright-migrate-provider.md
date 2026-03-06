---
name: cloudwright-migrate-provider
version: 0.3.0
description: Migrate an architecture from one cloud provider to another
layer: 2
mcp_tools: [compare_providers, modify_architecture, validate_compliance, estimate_cost]
tags: [migration, cross-cloud, provider, aws, gcp, azure, chain]
---

# Cloudwright Migrate Provider

Map an architecture to a target cloud provider, validate compliance on the new platform, and estimate the new cost.

## When to Use

- User wants to move from AWS to GCP (or any other cross-cloud migration)
- Evaluating multi-cloud costs before committing to a migration
- Generating a target-state architecture for migration planning

## Chain

```
compare_providers  →  modify_architecture (target provider)  →  validate_compliance  →  estimate_cost
```

1. **Compare** — show service-level mapping and cost delta across providers
2. **Modify** — rewrite the architecture for the target provider using equivalent services
3. **Validate** — confirm compliance frameworks still pass on the new platform
4. **Estimate** — compute the new monthly cost

## CLI Usage

```bash
# Step 1: compare providers
cloudwright compare arch.yaml --providers aws,gcp,azure

# Step 2: migrate to GCP
cloudwright modify arch.yaml "migrate to GCP, map all services to GCP equivalents"

# Step 3: validate compliance
cloudwright validate arch.yaml --compliance hipaa

# Step 4: estimate new cost
cloudwright cost arch.yaml
```

## MCP Tool Usage

```json
// Step 1 — compare
{
  "tool": "compare_providers",
  "arguments": {
    "spec_json": <current_spec>,
    "providers": ["aws", "gcp", "azure"]
  }
}

// Step 2 — migrate
{
  "tool": "modify_architecture",
  "arguments": {
    "spec_json": <current_spec>,
    "instruction": "Migrate this architecture from AWS to GCP. Map services: RDS -> Cloud SQL, S3 -> Cloud Storage, Lambda -> Cloud Functions, EKS -> GKE, SQS -> Cloud Pub/Sub."
  }
}

// Step 3 — validate compliance
{
  "tool": "validate_compliance",
  "arguments": {
    "spec_json": <migrated_spec>,
    "frameworks": ["hipaa", "soc2"]
  }
}

// Step 4 — cost
{
  "tool": "estimate_cost",
  "arguments": {"spec_json": <migrated_spec>}
}
```

## Service Mapping Reference

| AWS | GCP | Azure |
|-----|-----|-------|
| EC2 | Compute Engine | Azure VM |
| ECS / EKS | GKE | AKS |
| Lambda | Cloud Functions | Azure Functions |
| RDS | Cloud SQL | Azure SQL |
| S3 | Cloud Storage | Blob Storage |
| DynamoDB | Firestore | Cosmos DB |
| ElastiCache | Memorystore | Azure Cache for Redis |
| Redshift | BigQuery | Synapse Analytics |
| SQS | Cloud Pub/Sub | Service Bus |
| CloudFront | Cloud CDN | Azure CDN |
| Route 53 | Cloud DNS | Azure DNS |
| ALB | Cloud Load Balancing | Azure Load Balancer |
| API Gateway | Apigee / Cloud Endpoints | Azure API Management |

## Example Output

```
Migration: AWS → GCP

Service Mapping:
  rds         → cloud_sql      (equivalent)
  s3          → cloud_storage  (equivalent)
  lambda      → cloud_functions (equivalent)
  eks         → gke            (equivalent)

Compliance: HIPAA — PASS (Cloud SQL, Cloud Storage support HIPAA BAA)

Cost Comparison:
  AWS (current):  $1,240/month
  GCP (migrated): $1,080/month  (-$160, -13%)
```

## Follow-Up Actions

After migration:
- `cloudwright export arch.yaml --format terraform` — generate GCP Terraform
- `cloudwright lint arch.yaml` — check for GCP-specific anti-patterns
- `cloudwright security arch.yaml` — verify security rules on the new provider

## Notes

- Some services have no direct equivalent (e.g., AWS Step Functions → GCP Workflows). The LLM will pick the closest equivalent and note the gap.
- FedRAMP compliance requires US-based GCP or Azure regions. The migration will update `region` accordingly.
