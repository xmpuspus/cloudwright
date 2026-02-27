# ArchSpec Format Specification

ArchSpec is Silmaril's core data format — a structured, machine-readable architecture specification.

## Overview

An ArchSpec describes a cloud architecture as a graph of components (nodes) connected by edges,
with cost estimates, compliance constraints, and metadata.

## YAML Format

```yaml
name: "3-Tier Web Application"
version: 1
provider: aws
region: us-east-1
constraints:
  compliance:
    - hipaa
  budget_monthly: 500.0
  availability: 99.9
components:
  - id: cdn
    service: cloudfront
    provider: aws
    label: CloudFront CDN
    description: Content delivery network for static assets
    tier: 0
    config:
      estimated_gb: 500
  - id: alb
    service: alb
    provider: aws
    label: Application Load Balancer
    description: Layer 7 load balancer
    tier: 1
  - id: web
    service: ec2
    provider: aws
    label: Web Servers
    description: Auto-scaled EC2 instances
    tier: 2
    config:
      instance_type: m5.large
      count: 2
      auto_scaling: true
  - id: db
    service: rds
    provider: aws
    label: PostgreSQL Database
    description: Multi-AZ RDS PostgreSQL
    tier: 3
    config:
      engine: postgres
      instance_class: db.r5.large
      multi_az: true
      storage_gb: 100
      encryption: true
connections:
  - source: cdn
    target: alb
    label: HTTPS
    protocol: HTTPS
    port: 443
  - source: alb
    target: web
    label: HTTP
    protocol: HTTP
    port: 80
  - source: web
    target: db
    label: PostgreSQL
    protocol: TCP
    port: 5432
cost_estimate:
  monthly_total: 487.30
  currency: USD
  as_of: "2026-02-27"
  breakdown:
    - component_id: cdn
      service: cloudfront
      monthly: 42.50
      notes: "500 GB egress"
    - component_id: alb
      service: alb
      monthly: 22.50
      notes: "Base cost"
    - component_id: web
      service: ec2
      monthly: 244.30
      notes: "2x m5.large"
    - component_id: db
      service: rds
      monthly: 178.00
      notes: "db.r5.large Multi-AZ"
```

## Fields

### ArchSpec (root)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Human-readable architecture name |
| version | int | no | Spec version, incremented on changes (default: 1) |
| provider | string | yes | Primary cloud provider (aws, gcp, azure) |
| region | string | yes | Primary deployment region |
| constraints | Constraints | no | Budget, compliance, availability constraints |
| components | Component[] | yes | List of architecture components |
| connections | Connection[] | yes | Edges between components |
| cost_estimate | CostEstimate | no | Auto-populated by cost engine |
| alternatives | Alternative[] | no | Multi-cloud alternatives |
| metadata | dict | no | Arbitrary key-value metadata |

### Component

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique identifier (snake_case) |
| service | string | yes | Catalog service key (ec2, rds, s3, etc.) |
| provider | string | yes | Cloud provider (aws, gcp, azure) |
| label | string | yes | Human-readable label |
| description | string | no | Brief description |
| tier | int | no | 0=edge, 1=ingress, 2=compute, 3=data, 4=storage |
| config | dict | no | Service-specific configuration |

### Connection

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source | string | yes | Source component ID |
| target | string | yes | Target component ID |
| label | string | no | Edge label |
| protocol | string | no | Protocol (HTTPS, TCP, gRPC, etc.) |
| port | int | no | Port number |

### Tier Assignments

- **Tier 0 — Edge**: CDN, DNS, API Gateway, WAF
- **Tier 1 — Ingress**: Load balancers, ingress controllers
- **Tier 2 — Compute**: VMs, containers, serverless functions
- **Tier 3 — Data**: Databases, caches, message queues
- **Tier 4 — Storage**: Object storage, data warehouses, ML/analytics

## Export Formats

- **Terraform** — Valid HCL with provider blocks, resources, variables, outputs
- **CloudFormation** — AWS-only YAML template
- **Mermaid** — Flowchart diagram with subgraphs by tier
- **CycloneDX SBOM** — Software Bill of Materials (JSON)
- **OWASP AIBOM** — AI Bill of Materials for AI/ML components (JSON)
