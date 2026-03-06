---
name: cloudwright-catalog
version: 0.3.0
description: Search the cloud service catalog and compare service specs across providers
layer: 1
mcp_tools: [catalog_search, list_services]
tags: [catalog, services, instances, cross-cloud, comparison]
---

# Cloudwright Catalog

Search for cloud services and instances, compare specs, and find cross-cloud equivalents.

## When to Use

- User asks "what's the equivalent of AWS RDS on GCP?"
- User wants to find all instances with 8+ vCPUs under $0.20/hour
- User needs to compare EC2 instance types before right-sizing
- Building cost models that need accurate instance specs

## CLI Usage

```bash
# Natural language search
cloudwright catalog search "8 vCPU memory-optimized instance on AWS"

# Filter by provider
cloudwright catalog search "compute instance" --provider gcp

# Filter by specs
cloudwright catalog search "database service" --vcpus 4 --memory 16

# List all services for a provider
cloudwright catalog list aws

# List with filter
cloudwright catalog list gcp --category storage
```

## MCP Tool Usage

### Search the catalog

```json
{
  "tool": "catalog_search",
  "arguments": {
    "query": "managed PostgreSQL with high availability",
    "provider": "aws",
    "vcpus": 4,
    "memory": 16
  }
}
```

### List services

```json
{
  "tool": "list_services",
  "arguments": {
    "provider": "aws",
    "category": "database"
  }
}
```

## Output Structure (search)

```json
{
  "results": [
    {
      "service": "rds",
      "provider": "aws",
      "label": "Amazon RDS",
      "category": "database",
      "instance_type": "db.r6g.xlarge",
      "vcpus": 4,
      "memory_gb": 32,
      "price_per_hour": 0.48,
      "cross_cloud_equivalents": {
        "gcp": "cloud_sql",
        "azure": "azure_sql"
      }
    }
  ]
}
```

## Cross-Cloud Service Equivalents

| AWS | GCP | Azure | Databricks |
|-----|-----|-------|------------|
| `ec2` | `compute_engine` | `azure_vm` | — |
| `rds` | `cloud_sql` | `azure_sql` | — |
| `s3` | `cloud_storage` | `blob_storage` | `databricks_volume` |
| `lambda` | `cloud_functions` | `azure_functions` | — |
| `eks` | `gke` | `aks` | — |
| `redshift` | `bigquery` | `synapse` | `databricks_sql_warehouse` |
| `elasticache` | `memorystore` | `azure_cache` | — |
| `sqs` | `cloud_pubsub` | `service_bus` | — |

## Follow-Up Actions

After searching the catalog:
- Found the right instance? Use it in a design: `cloudwright design "... using db.r6g.xlarge for the database"`
- Comparing instance costs across providers: `cloudwright compare arch.yaml --providers aws,gcp,azure`
- Right-sizing: `cloudwright modify arch.yaml "use db.t3.medium for the RDS instance"`

## Notes

- The catalog is pre-computed from provider price lists. It does not make live API calls.
- `memory` filter is in GB. `vcpus` filter is a minimum (returns instances with >= N vCPUs).
- Natural language queries support shorthand: "8 vcpu", "16gb memory", "under $0.50/hr".
