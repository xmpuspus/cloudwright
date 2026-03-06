---
name: cloudwright-design
version: 0.3.0
description: Design a cloud architecture from a natural language description
layer: 1
mcp_tools: [design_architecture, estimate_cost]
tags: [design, architect, llm]
---

# Cloudwright Design

Generate a full cloud architecture spec from a plain-English description.

## When to Use

- User describes a system ("web app with React, Python API, PostgreSQL on AWS")
- User wants a starting architecture for a new service
- User needs to explore what components a workload requires

## CLI Usage

```bash
# Basic design
cloudwright design "Web app with React, Python API, PostgreSQL on AWS"

# With constraints
cloudwright design "Streaming analytics pipeline" \
  --provider gcp \
  --region us-central1 \
  --budget 2000 \
  --compliance hipaa

# Save to file for further processing
cloudwright design "Microservices e-commerce platform" \
  --provider aws \
  --output arch.yaml

# Machine-readable output
cloudwright --json design "ML training pipeline on Azure"
```

## MCP Tool Usage

```json
{
  "tool": "design_architecture",
  "arguments": {
    "description": "Real-time fraud detection service with ML inference",
    "provider": "aws",
    "region": "us-east-1",
    "budget_monthly": 5000,
    "compliance": ["pci-dss"]
  }
}
```

Response is an `ArchSpec` dict with `components`, `connections`, `cost_estimate`, `provider`, `region`.

To get a cost estimate alongside the design:

```json
{
  "tool": "estimate_cost",
  "arguments": {
    "spec_json": <output from design_architecture>
  }
}
```

## Key Inputs

| Parameter | Description | Example |
|-----------|-------------|---------|
| `description` | Natural language workload description | "SaaS app with auth, REST API, and Postgres" |
| `provider` | Cloud provider | `aws`, `gcp`, `azure`, `databricks` |
| `region` | Primary region | `us-east-1`, `us-central1`, `eastus` |
| `budget_monthly` | Monthly budget cap in USD | `1500` |
| `compliance` | Compliance frameworks | `["hipaa", "pci-dss", "soc2", "fedramp", "gdpr"]` |

## Output Structure

```yaml
name: fraud-detection-service
provider: aws
region: us-east-1
components:
  - id: api
    service: api_gateway
    label: API Gateway
    tier: presentation
  - id: inference
    service: lambda
    label: ML Inference
    tier: application
connections:
  - source: api
    target: inference
cost_estimate:
  total_monthly: 847.20
  breakdown: [...]
```

## Follow-Up Actions

After designing:
- `cloudwright validate arch.yaml --compliance <framework>` — check compliance
- `cloudwright score arch.yaml` — score quality
- `cloudwright export arch.yaml --format terraform` — generate IaC
- `cloudwright lint arch.yaml` — check for anti-patterns

## Notes

- The LLM selects appropriate services based on the provider. It will not mix AWS and GCP services in one spec.
- If budget is set, components are right-sized to stay within the limit.
- Compliance flags add required components (e.g., `hipaa` adds audit logging, encryption at rest).
