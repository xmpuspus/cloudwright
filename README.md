# Cloudwright

[![PyPI](https://img.shields.io/pypi/v/cloudwright-ai.svg)](https://pypi.org/project/cloudwright-ai/)
[![CI](https://github.com/xmpuspus/cloudwright/actions/workflows/ci.yml/badge.svg)](https://github.com/xmpuspus/cloudwright/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/pypi/pyversions/cloudwright-ai)](https://pypi.org/project/cloudwright-ai/)

Architecture intelligence for cloud engineers.

Cloudwright bridges the gap between a whiteboard sketch and deployable infrastructure. Describe a system in natural language, and Cloudwright produces a structured architecture spec, cost estimates, compliance reports, Terraform/CloudFormation code, diagrams, and diffs — all from a single format called **ArchSpec**.

<p align="center">
  <img src="examples/cloudwright-demo.gif" alt="Cloudwright CLI Demo" width="800">
</p>

<p align="center"><em>HIPAA-compliant healthcare API on AWS — 12 components with VPC boundaries, cost breakdown ($2,263/mo), compliance validation (HIPAA 60%), and eight export formats including Terraform, CloudFormation, and ASCII architecture diagrams.</em></p>

| Architecture Diagram | Cost Breakdown |
|:---:|:---:|
| ![E-Commerce Platform](docs/screenshots/cloudwright-light-1-ecommerce.png) | ![Analytics Pipeline](docs/screenshots/cloudwright-light-2-analytics.png) |
| ![Cost Breakdown](docs/screenshots/cloudwright-light-3-cost.png) | ![Compliance Validation](docs/screenshots/cloudwright-light-4-validate.png) |

<p align="center"><em>Web UI — interactive React Flow diagrams with tier-based layout, service-category color coding, boundary grouping, per-component cost overlay, and compliance validation.</em></p>

## Installation

```bash
pip install 'cloudwright-ai[cli]'          # CLI
pip install 'cloudwright-ai[web]'          # CLI + Web UI
pip install cloudwright-ai-mcp             # MCP server for AI agents
```

Set an LLM provider key (required for `design`, `modify`, `chat`, `adr`; all other commands work offline):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

```bash
# Design from natural language
cloudwright design "3-tier web app on AWS with Redis and PostgreSQL"

# Estimate cost with production-realistic workload profiles
cloudwright cost spec.yaml --workload-profile medium
cloudwright cost spec.yaml -w enterprise --pricing-tier reserved_1yr

# Validate compliance
cloudwright validate spec.yaml --compliance hipaa,soc2

# Export Terraform
cloudwright export spec.yaml --format terraform -o ./infra

# Compare cost across clouds
cloudwright cost spec.yaml --compare gcp,azure

# Security scan
cloudwright security spec.yaml

# Import existing infrastructure
cloudwright import terraform.tfstate -o spec.yaml

# Interactive multi-turn design
cloudwright chat           # terminal
cloudwright chat --web     # browser UI
```

---

## What's New

### v0.3.5 — Conversational UX and Observability (2026-03-14)

<p align="center">
  <img src="examples/cloudwright-v035-demo.gif" alt="Cloudwright v0.3.5 Web UI Demo" width="720">
</p>

<p align="center"><em>Web UI — natural language design with streaming SSE, suggestion buttons, cost estimation, architecture diagram with tier boundaries, and multi-turn modification via suggestions.</em></p>

Major upgrade to the conversational experience across CLI, Web, and MCP. Token-level streaming, session persistence, usage tracking, and structured error handling.

**Streaming.** Token-level streaming in CLI (Rich Live display) and Web (SSE `/api/chat/stream`). Responses render incrementally instead of blocking until complete.

**Session persistence.** Save and resume conversations across sessions. CLI: `/save-session`, `/load-session`, `/sessions`, `--resume SESSION_ID`. SDK: `SessionStore` class with `save()`, `load()`, `list_sessions()`, `delete()`.

**Usage tracking.** Per-turn and cumulative token counts with cost estimation. Displayed after every response in CLI, included in API responses and SSE done events.

```bash
cloudwright chat                    # streaming by default
cloudwright chat --resume my-sess   # resume saved session
cloudwright chat --debug            # show prompts, timing, token counts
```

**Also added:**
- Context window management — automatic history trimming at 50 turns
- Spec diff display after modifications (added/removed/changed components)
- Clarification routing for ambiguous single-word inputs
- Rate limiting (30 req/min per IP) and structured error responses in Web API
- Thread-safe singletons for web server concurrency
- Suggestion buttons and confirmation dialogs in React frontend
- MCP session TTL (1hr), max 100 sessions, auto-cleanup
- Expanded LLM retry logic with jitter (rate limit, connection, 5xx, timeout)
- Per-call timeout parameter on all LLM methods
- Few-shot examples in system prompts to reduce JSON parsing failures
- 44 Playwright browser tests covering every README feature (design, cost, validate, export, spec, modify, suggestions, multi-turn, streaming, confirmation dialogs, API endpoints)
- 1,144 tests total (1,084 unit/integration + 28 e2e/behavioral + 44 browser, all with real LLM)

### v0.3.3 — Cost Accuracy and Import Reliability (2026-03-09)

**Workload profiles** fix cost estimates that were 10-100x too low for production workloads. Profiles inject realistic sizing defaults (Lambda invocations, DB storage, cache memory, CDN egress) before pricing formulas run — without overwriting explicit config.

```bash
cloudwright cost spec.yaml -w medium       # 1M Lambda requests, 100GB DB, 6GB cache
cloudwright cost spec.yaml -w enterprise   # 100M requests, 2TB DB, 26GB cache
```

| Profile | Lambda Requests | DB Storage | Cache Memory | CDN Egress | EKS Nodes |
|---|---|---|---|---|---|
| `small` | 100K/mo | 20 GB | 1 GB | 10 GB | 2 |
| `medium` | 1M/mo | 100 GB | 6 GB | 100 GB | 3 |
| `large` | 10M/mo | 500 GB | 13 GB | 500 GB | 5 |
| `enterprise` | 100M/mo | 2 TB | 26 GB | 2 TB | 10 |

**Import pipeline** failure rate dropped from ~20% to near-zero with 70+ new resource type mappings:
- 20 new CloudFormation types: IAM, VPC, CloudWatch, Kinesis, StepFunctions, SecretsManager, KMS, ECR, MSK, EventBridge
- 50 hardcoded Terraform type fallbacks across AWS, GCP, and Azure
- Post-import encryption defaults automatically applied to databases and storage

**MCP package** now included in CI/CD build and publish workflow.

### v0.3.1 — MCP Server and ASCII Export (2026-03-05)

<p align="center">
  <img src="examples/cloudwright-mcp-showcase.gif" alt="Claude Code using Cloudwright MCP" width="720">
</p>

<p align="center"><em>Claude Code designing, costing, and exporting a multi-tier architecture via Cloudwright MCP tools.</em></p>

MCP (Model Context Protocol) server exposes 18 Cloudwright tools across 6 groups for AI agent integration. Works with Claude Code, Claude Desktop, and any MCP-compatible client.

```bash
cloudwright mcp                              # start MCP server (stdio)
cloudwright mcp --tools design,cost          # selective tool groups
```

Also added: ASCII diagram exporter (`--format ascii`), NDJSON streaming (`--stream`), and a skills system for CLI extensibility.

<p align="center">
  <img src="examples/cloudwright-dryrun-demo.gif" alt="Dry-Run and Streaming Demo" width="720">
</p>

<p align="center"><em>Structured JSON output and dry-run mode — preview LLM operations without API calls.</em></p>

### v0.3.0 — Security Scanner and ADR Generator (2026-03-04)

<p align="center">
  <img src="examples/cloudwright-security-demo.gif" alt="Security Scanning Demo" width="720">
</p>

<p align="center"><em>Security scanner checking an architecture for missing encryption, open ingress, IAM wildcards, and more.</em></p>

Security scanner with 6 checks: missing encryption, open ingress, no HTTPS, IAM wildcards, missing backups, no monitoring. Also scans exported Terraform HCL.

```bash
cloudwright security spec.yaml --fail-on high
cloudwright security spec.yaml --json        # CI-friendly
```

ADR generator produces MADR-format Architecture Decision Records with LLM-powered analysis and deterministic fallback.

```bash
cloudwright adr spec.yaml --output docs/ADR-001.md
```

Databricks cost governance template added (job clusters, SQL Warehouse auto-stop, Secret Scope).

### v0.2.27 — Public Release (2026-03-04)

First public release on PyPI. Added CI/CD, badges, contribution guidelines, issue templates, and changelog backfill for all versions.

### v0.2.0 — CLI Overhaul (2026-03-01)

Major CLI redesign with `--json` machine-readable output on all commands, `--verbose` for stack traces, D2 diagram export, policy-as-code engine, and global error handling. 112 service keys across AWS, GCP, Azure, and Databricks.

### v0.1.0 — Initial Release (2026-02-27)

Natural language architecture design, ArchSpec data model, cost engine with catalog-backed pricing, cross-cloud comparison, compliance validation (HIPAA, PCI-DSS, SOC 2), Terraform/CloudFormation/Mermaid export, CycloneDX SBOM, architecture diffing, SQLite service catalog, CLI with Rich formatting, and FastAPI web backend.

Full changelog: [CHANGELOG.md](CHANGELOG.md)

---

## How It Works

```mermaid
flowchart LR
    subgraph Input
        nl(["Natural language"])
        tpl(["17 templates"])
        imp(["Import TF / CFN (70+ types)"])
    end

    spec["ArchSpec (YAML)"]

    subgraph Analyze
        cost["Cost estimation"]
        lint["Lint 10 rules"]
        score["Score 5 dimensions"]
        blast["Blast radius / SPOF"]
    end

    subgraph Validate
        comply["6 compliance frameworks"]
        policy["Policy engine"]
        drift["Drift detection"]
    end

    subgraph Export
        iac["Terraform / CloudFormation"]
        diagram["Mermaid / D2"]
        sbom["SBOM / AIBOM"]
        diff["Arch diff"]
    end

    nl -- design / chat --> spec
    tpl -- init --> spec
    imp -- import --> spec

    spec --> cost & lint & score & blast
    spec --> comply & policy & drift
    spec --> iac & diagram & sbom & diff

    style spec fill:#1a3a5c,stroke:#1a3a5c,color:#fff
```

## Why Cloudwright

Most cloud tooling assumes you already know what to build (IaC) or already have it deployed (cost dashboards, security scanners). Cloudwright operates in the design phase — the gap where architects currently rely on tribal knowledge, ad-hoc spreadsheets, and copy-pasting last quarter's Terraform.

**One spec, many outputs.** ArchSpec is the universal interchange format. Every module — design, cost, compliance, export, diff, lint, score — reads and writes it. No glue code, no format conversion.

### How it compares

| Capability | Cloudwright | Terraform | Pulumi Neo | Brainboard | Infracost | Checkov |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| NL to architecture | Y | - | Y | Y | - | - |
| IaC generation | TF + CFN | HCL | Code | TF | - | - |
| Cost estimation | Y (workload profiles) | - | - | Basic | Y (code-time) | - |
| Compliance validation | 6 frameworks | - | OPA policies | - | - | 2500+ rules |
| Architecture diffing | Y | Plan diff | Preview diff | Drift | Cost diff | - |
| Diagram export | Mermaid + D2 | - | - | Y | - | - |
| SBOM / AIBOM | Y | - | - | - | - | - |
| Multi-cloud | AWS/GCP/Azure/Databricks | All | All | AWS/GCP/Azure/OCI | AWS/GCP/Azure | All |
| Open source | Y | BSL / OpenTofu | Engine only | - | CLI only | Y |
| Runs locally | Y | Y | Y | - | Y | Y |

Terraform and Infracost are deployment/cost tools that sit *downstream* — Cloudwright generates the Terraform code and estimates costs before any code exists. Checkov and Prowler scan *after* code is written; Cloudwright validates at design time. Brainboard is the closest direct competitor (NL-to-arch + TF), but it's SaaS-only and doesn't do compliance or cost estimation.

Full competitor analysis covering 30 tools across IaC, cost, compliance, and diagramming: [competitor-landscape.md](docs/competitor-landscape.md)

## Real-World Examples

### 1. Microservices Platform — Design to Diagram in 30 Seconds

Start from a template, generate a Mermaid architecture diagram, and get a cost breakdown:

```bash
$ cloudwright init --template microservices -o platform.yaml

Created platform.yaml from template 'microservices'
  Provider: aws
  Components: 8

$ cloudwright export platform.yaml --format mermaid
```

```mermaid
flowchart TD
    subgraph "Tier 0 - Edge"
        cloudfront([CloudFront CDN])
    end
    subgraph "Tier 1 - Ingress"
        alb([Application Load Balancer])
    end
    subgraph "Tier 2 - Compute"
        ecs_api[API Service]
        ecs_user[User Service]
        ecs_order[Order Service]
        sqs[/SQS Event Queue/]
    end
    subgraph "Tier 3 - Data"
        elasticache[(ElastiCache Redis)]
        rds[(RDS PostgreSQL)]
    end

    cloudfront -->|HTTPS| alb
    alb -->|/api/*| ecs_api
    alb -->|/users/*| ecs_user
    alb -->|/orders/*| ecs_order
    ecs_api --> rds
    ecs_user --> rds
    ecs_order --> rds
    ecs_api --> elasticache
    ecs_order -->|Publish events| sqs
    ecs_api -->|Consume events| sqs
```

```bash
$ cloudwright cost platform.yaml

                       Cost Breakdown — ECS Microservices
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component   ┃ Service     ┃   Monthly ┃ Notes                                ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ cloudfront  │ cloudfront  │    $42.50 │ 500GB egress                         │
│ alb         │ alb         │    $16.43 │                                      │
│ ecs_api     │ ecs         │   $300.00 │                                      │
│ ecs_user    │ ecs         │   $300.00 │                                      │
│ ecs_order   │ ecs         │   $300.00 │                                      │
│ elasticache │ elasticache │   $360.00 │ cache.t3.medium, redis               │
│ rds         │ rds         │   $388.00 │ db.r5.large, Multi-AZ, 200GB, pg     │
│ sqs         │ sqs         │     $4.00 │                                      │
├─────────────┼─────────────┼───────────┼──────────────────────────────────────┤
│             │             │ $1,710.93 │                                      │
└─────────────┴─────────────┴───────────┴──────────────────────────────────────┘
```

### 2. Blast Radius and SPOF Detection

Find single points of failure and understand which components take everything down:

```bash
$ cloudwright analyze platform.yaml

╭─────────── Blast Radius Analysis: ECS Microservices ────────────╮
│ Components: 8  |  Max Blast Radius: 7  |  SPOFs: 3             │
╰─────────────────────────────────────────────────────────────────╯

Single Points of Failure: cloudfront, alb, ecs_api

Critical Path: cloudfront -> alb -> ecs_api -> rds

                            Component Impact
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━┓
┃ Component   ┃ Service     ┃ Tier ┃ Direct Deps ┃ Blast Radius ┃ SPOF ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━┩
│ cloudfront  │ cloudfront  │    0 │           1 │            7 │ YES  │
│ alb         │ alb         │    1 │           3 │            6 │ YES  │
│ ecs_api     │ ecs         │    2 │           3 │            3 │ YES  │
│ ecs_order   │ ecs         │    2 │           2 │            2 │      │
│ ecs_user    │ ecs         │    2 │           1 │            1 │      │
│ elasticache │ elasticache │    3 │           0 │            0 │      │
│ rds         │ rds         │    3 │           0 │            0 │      │
│ sqs         │ sqs         │    2 │           0 │            0 │      │
└─────────────┴─────────────┴──────┴─────────────┴──────────────┴──────┘

Dependency Graph
└── cloudfront
    └── alb
        ├── ecs_api
        │   ├── rds
        │   ├── elasticache
        │   └── sqs
        ├── ecs_user
        │   └── rds
        └── ecs_order
            ├── rds
            └── sqs
```

### 3. Data Lake — Compliance Audit and Linting

Generate a data lake, then check it against SOC 2 and GDPR before your auditor does:

```bash
$ cloudwright init --template data_lake -o pipeline.yaml
$ cloudwright validate pipeline.yaml --compliance soc2,gdpr

──────────────────────────── SOC 2 Review ─────────────────────────
[FAIL] logging — No logging service found
[FAIL] access_controls — No auth service found
[FAIL] encryption_at_rest — Missing encryption on: s3_raw, s3_processed, redshift
[FAIL] availability — No multi-AZ or load balancer found
[FAIL] change_management — No CI/CD service detected
Score: 0/5 (0%)

──────────────────────────── GDPR Review ──────────────────────────
[FAIL] data_residency — Non-EU regions detected: us-east-1
[FAIL] encryption_at_rest — Unencrypted data stores: s3_raw, s3_processed, redshift
[PASS] encryption_in_transit — All connections use encrypted protocols
[FAIL] access_controls — No authentication service found
[FAIL] audit_trail — No logging or monitoring service found
[FAIL] data_deletion_capability — No TTL, lifecycle, or retention policy found
Score: 1/6 (16%)

$ cloudwright lint pipeline.yaml

                         Lint Results: Data Lake
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Severity  ┃ Rule          ┃ Component    ┃ Message                         ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ error     │ no_encryption │ s3_raw       │ No encryption configured        │
│ error     │ no_encryption │ s3_processed │ No encryption configured        │
│ error     │ no_encryption │ redshift     │ No encryption configured        │
│ error     │ single_az     │ redshift     │ Not configured for multi-AZ     │
│ warning   │ no_waf        │ —            │ API gateway present but no WAF  │
│ warning   │ no_monitoring │ —            │ 7 components but no monitoring  │
│ warning   │ no_backup     │ redshift     │ No backup configured            │
│ warning   │ no_auth       │ —            │ No authentication service       │
└───────────┴───────────────┴──────────────┴─────────────────────────────────┘

8 finding(s): 4 error(s), 4 warning(s)
```

### 4. Cross-Cloud Instance Comparison

Compare equivalent instances across AWS, GCP, and Azure — pricing, specs, and storage in one table:

```bash
$ cloudwright catalog compare m5.xlarge n2-standard-4 Standard_D4s_v5

                              Instance Comparison
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Attribute         ┃        m5.xlarge ┃     n2-standard-4 ┃   Standard_D4s_v5 ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ vcpus             │                4 │                 4 │                 4 │
│ memory_gb         │             16.0 │              16.0 │              16.0 │
│ arch              │           x86_64 │            x86_64 │            x86_64 │
│ network_bandwidth │ Up to 10 Gigabit │     Up to 10 Gbps │   Up to 12.5 Gbps │
│ price_per_hour    │          $0.1920 │           $0.1942 │           $0.1920 │
│ price_per_month   │          $140.16 │           $141.77 │           $140.16 │
│ storage_desc      │         EBS only │   Persistent Disk │    Remote Storage │
└───────────────────┴──────────────────┴───────────────────┴───────────────────┘

$ cloudwright catalog search "4 vcpu 16gb"

                         Catalog Search: "4 vcpu 16gb"
┏━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Service     ┃ Provider ┃ Label           ┃ vCPUs ┃ Memory (GB) ┃    $/hr ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━┩
│ e2-standard │ gcp      │ General Purpose │     4 │        16.0 │ $0.1340 │
│ t4g.xlarge  │ aws      │                 │     4 │        16.0 │ $0.1344 │
│ t3a.xlarge  │ aws      │                 │     4 │        16.0 │ $0.1504 │
│ m6g.xlarge  │ aws      │                 │     4 │        16.0 │ $0.1540 │
│ Standard_D4 │ azure    │ General Purpose │     4 │        16.0 │ $0.1720 │
│ m5a.xlarge  │ aws      │                 │     4 │        16.0 │ $0.1720 │
│ ...         │          │                 │       │             │         │
└─────────────┴──────────┴─────────────────┴───────┴─────────────┴─────────┘
```

### 5. Serverless API — From Zero to Terraform

Generate a serverless API spec and export production-ready Terraform in one pipeline:

```bash
$ cloudwright init --template serverless_api -o api.yaml
$ cloudwright cost api.yaml -w medium

                    Cost Breakdown — Serverless REST API
┏━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component ┃ Service     ┃  Monthly ┃ Notes                                 ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ api_gw    │ api_gateway │   $17.50 │ 1M requests/mo                        │
│ auth      │ cognito     │    $0.00 │                                       │
│ handler   │ lambda      │   $20.87 │ 1M invocations, 256MB                 │
│ db        │ dynamodb    │   $25.00 │                                       │
│ storage   │ s3          │    $1.15 │ 50GB storage                          │
├───────────┼─────────────┼──────────┼───────────────────────────────────────┤
│           │             │   $64.52 │ Workload profile: medium              │
└───────────┴─────────────┴──────────┴───────────────────────────────────────┘

$ cloudwright export api.yaml --format terraform -o ./infra

Written to ./infra/main.tf
```

The generated Terraform includes provider config, VPC data sources, IAM role variables, and properly tagged resources:

```hcl
resource "aws_api_gateway_rest_api" "api_gw" {
  name = "API Gateway"
  tags = { Name = "API Gateway" }
}

resource "aws_lambda_function" "handler" {
  function_name = "handler"
  role          = var.lambda_role_arn
  handler       = "index.handler"
  runtime       = "python3.12"
  filename      = "lambda.zip"
  tags = { Name = "Lambda Handlers" }
}

resource "aws_dynamodb_table" "db" {
  name         = "db"
  billing_mode = "on_demand"
  hash_key     = "id"
  attribute { name = "id"; type = "S" }
  tags = { Name = "DynamoDB Table" }
}
```

### 6. Architecture Quality Scorecard

Get a letter grade across reliability, security, cost, compliance, and complexity:

```bash
$ cloudwright score platform.yaml --with-cost

╭──────────── Architecture Quality: ECS Microservices ─────────────╮
│ Overall Score: 70/100  Grade: D                                  │
╰──────────────────────────────────────────────────────────────────╯

                              Dimension Breakdown
┏━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Dimension       ┃ Score ┃ Weight ┃ Weighted ┃ Details                      ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Reliability     │   100 │    30% │     30.0 │ LB + Multi-AZ enabled        │
│ Security        │    32 │    25% │      8.0 │ 1/10 connections use HTTPS   │
│ Cost Efficiency │    60 │    20% │     12.0 │ $1,710.93/mo (avg $214/comp) │
│ Compliance      │    70 │    15% │     10.5 │ No frameworks specified      │
│ Complexity      │    90 │    10% │      9.0 │ 8 components, 10 connections │
└─────────────────┴───────┴────────┴──────────┴──────────────────────────────┘

Top Recommendations:
  1. Add a WAF for web application protection
  2. Add an authentication service
```

### 7. Databricks Lakehouse — Design to Deploy

<p align="center">
  <img src="examples/cloudwright-databricks-demo.gif" alt="Databricks Lakehouse Demo" width="800">
</p>

Design a Databricks lakehouse architecture with cost estimates and Terraform export:

```bash
$ cloudwright init --template databricks_lakehouse -o lakehouse.yaml

Created lakehouse.yaml from template 'databricks_lakehouse'
  Provider: databricks
  Components: 6

$ cloudwright cost lakehouse.yaml

                  Cost Breakdown — Databricks Lakehouse
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component      ┃ Service                  ┃  Monthly ┃ Notes                   ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ unity_catalog │ databricks_unity_catalog │     $0.00 │                      │
│ sql_warehouse │ databricks_sql_warehouse │ $1,606.00 │ Small, 100GB storage │
│ dlt_pipeline  │ databricks_pipeline      │   $438.00 │                      │
│ volume        │ databricks_volume        │    $23.00 │ 1000GB storage       │
│ model_serving │ databricks_model_serving │   $511.00 │                      │
│ dashboard     │ databricks_dashboard     │     $0.00 │                      │
├───────────────┼──────────────────────────┼───────────┼──────────────────────┤
│               │                          │ $2,578.00 │                      │
└────────────────┴──────────────────────────┴──────────┴─────────────────────────┘

$ cloudwright export lakehouse.yaml --format terraform -o ./infra

Written to ./infra/main.tf
```

The generated Terraform uses the `databricks/databricks` provider and maps each service to native Databricks resources:

```hcl
terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.65"
    }
  }
}

resource "databricks_sql_endpoint" "sql_warehouse" {
  name             = "SQL Analytics Warehouse"
  cluster_size     = "Small"
  max_num_clusters = 1
  tags { custom_tags { key = "managed-by"; value = "cloudwright" } }
}

resource "databricks_pipeline" "etl_pipeline" {
  name    = "ETL Pipeline"
  edition = "ADVANCED"
  channel = "CURRENT"
}
```

Cross-cloud equivalences map Databricks services to AWS/GCP/Azure alternatives — `cloudwright compare lakehouse.yaml --providers aws` shows what the same architecture would cost on pure AWS (Redshift + Glue + SageMaker).

All examples above use real output from `cloudwright-ai` on PyPI — no LLM key required.

## Features

### Architecture Design

LLM-powered architecture generation from plain English. Supports multi-turn conversation, constraint-aware design, and natural language modification of existing specs.

```bash
cloudwright design "Serverless data pipeline on GCP with Pub/Sub, Dataflow, and BigQuery" \
  --provider gcp --budget 2000 --compliance gdpr

cloudwright modify spec.yaml "Add a Redis cache between the API and database"

cloudwright chat  # interactive mode with /save, /cost, /export commands
```

112 service keys across four clouds:
- **AWS** (47): EC2, ECS, EKS, Lambda, RDS, Aurora, DynamoDB, S3, SQS, SNS, Kinesis, Redshift, SageMaker, KMS, GuardDuty, CloudTrail, and more
- **GCP** (25): Compute Engine, GKE, Cloud Run, Cloud SQL, Spanner, BigQuery, Pub/Sub, Vertex AI, Cloud Build, and more
- **Azure** (28): Virtual Machines, AKS, Azure Functions, Azure SQL, Cosmos DB, Synapse, Azure ML, Azure Sentinel, and more
- **Databricks** (12): SQL Warehouse, Clusters, Jobs, DLT Pipelines, Model Serving, Unity Catalog, Vector Search, Genie, Notebooks, Volumes, and more

The architect applies safe defaults automatically: encryption on data stores, backups on databases, multi-AZ on production workloads, auto-scaling on compute.

### Cost Estimation

Per-component monthly pricing from a built-in SQLite catalog. No external API calls, no rate limits. Supports four pricing tiers and four workload profiles.

```bash
cloudwright cost spec.yaml                              # on-demand pricing
cloudwright cost spec.yaml --pricing-tier reserved_1yr  # 1-year reserved
cloudwright cost spec.yaml --compare gcp,azure          # multi-cloud comparison
cloudwright cost spec.yaml --workload-profile medium    # production-realistic sizing
cloudwright cost spec.yaml -w enterprise                # enterprise-grade defaults
```

The cost engine resolves prices through three tiers: catalog database (instance-level pricing), registry formula dispatch (11 named formulas for serverless/managed services), and static fallback table (100+ service defaults). Data transfer costs are calculated separately with per-provider egress rates and are also scaled by workload profile.

Pricing tiers: `on_demand` (1.0x), `reserved_1yr` (0.6x), `reserved_3yr` (0.4x), `spot` (0.3x).

### Compliance Validation

Six compliance frameworks with 35 individual checks:

| Framework | Checks | Key Validations |
|---|---|---|
| HIPAA | 5 | Encryption at rest/transit, audit logging, access control, BAA eligibility |
| PCI-DSS | 5 | WAF, network segmentation, encryption, TLS 1.2+, audit trail |
| SOC 2 | 5 | Logging, access controls, encryption, availability, change management |
| FedRAMP Moderate | 7 | FIPS 140-2, US regions, MFA, audit logging, continuous monitoring |
| GDPR | 6 | EU data residency, encryption, access controls, audit trail, data deletion |
| Well-Architected | 7 | Multi-AZ, auto-scaling, backup, monitoring, SPOF detection, cost optimization |

```bash
cloudwright validate spec.yaml --compliance hipaa,pci-dss,soc2
cloudwright validate spec.yaml --well-architected
cloudwright validate spec.yaml --compliance fedramp --report audit-report.md
```

Exit code 1 on failures, making it CI-friendly.

### Infrastructure Export

Eight export formats from a single ArchSpec:

| Format | Flag | Description |
|---|---|---|
| Terraform HCL | `terraform` | Provider-native resources for AWS (24 types), GCP (11), Azure (10), Databricks (12) |
| CloudFormation | `cloudformation` | YAML template with Parameters and Outputs |
| Mermaid | `mermaid` | Tier-grouped flowchart for docs and GitHub |
| D2 | `d2` | D2 diagram language with provider badges |
| ASCII Diagram | `ascii` | Terminal-friendly architecture diagram with tier grouping |
| CycloneDX SBOM | `sbom` | CycloneDX 1.5 service bill of materials |
| OWASP AIBOM | `aibom` | AI bill of materials documenting LLM usage and risks |
| Compliance Report | `compliance` | Audit-ready markdown with check details and evidence |

```bash
cloudwright export spec.yaml --format terraform -o ./infra
cloudwright export spec.yaml --format mermaid
cloudwright export spec.yaml --format ascii       # terminal architecture diagram
cloudwright export spec.yaml --format sbom -o sbom.json
```

Terraform output uses variables for sensitive values (no hardcoded passwords or ARNs), includes provider blocks with region configuration, and generates data sources for VPC/subnet discovery.

### Infrastructure Import

Import existing infrastructure into ArchSpec format:

```bash
cloudwright import terraform.tfstate -o spec.yaml
cloudwright import cloudformation-template.yaml -o spec.yaml
```

Auto-detects format from file extension and content. Recognizes 70+ resource types across Terraform (AWS, GCP, Azure) and CloudFormation (including IAM, VPC, CloudWatch, Kinesis, StepFunctions, SecretsManager, KMS, ECR, MSK, and EventBridge). Imported databases and storage services automatically get `encryption: true` set as a post-import security default.

Plugin support for custom importers via the `cloudwright.importers` entry point.

### Security Scanning

Scans an ArchSpec for security anti-patterns — missing encryption, open ingress, no HTTPS, IAM wildcards, unmonitored production architectures, and more.

```bash
cloudwright security spec.yaml              # scan with default fail-on=high
cloudwright security spec.yaml --fail-on critical
cloudwright security spec.yaml --json       # JSON output for CI pipelines
```

Also scans exported Terraform HCL for `0.0.0.0/0` security groups, `"*"` IAM actions, and `publicly_accessible = true` databases:

```python
from cloudwright.security import SecurityScanner, scan_terraform

# Scan ArchSpec
report = SecurityScanner().scan(spec)
for f in report.findings:
    print(f"[{f.severity.upper()}] {f.message}")

# Scan Terraform HCL output
hcl = spec.export("terraform")
report = scan_terraform(hcl)
print(f"Passed: {report.passed}")
```

### Schema Introspection

<p align="center">
  <img src="examples/cloudwright-schema-demo.gif" alt="Schema Introspection Demo" width="720">
</p>

Explore available cloud services, their configuration fields, cross-cloud equivalents, and compliance framework checks — all without an API key.

```bash
cloudwright schema aws.ec2        # service config fields, pricing, cross-cloud equivalents
cloudwright schema hipaa           # compliance checks, categories, severities
cloudwright schema gcp.cloud_sql   # GCP Cloud SQL configuration
```

Service mode shows default config, pricing formula, cross-cloud equivalences, and feature parity gaps across providers. Compliance mode shows all checks organized by category with severity levels.

### MCP Server

Expose cloudwright functions as [Model Context Protocol](https://modelcontextprotocol.io/) tools for external AI agents. 18 tools across 6 groups: design, cost, validate, analyze, export, and session.

```bash
pip install cloudwright-ai-mcp
cloudwright mcp                              # start MCP server (all tools, stdio)
cloudwright mcp --tools design,cost          # only design and cost tools
cloudwright mcp --transport sse              # SSE transport for HTTP clients
```

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cloudwright": {
      "command": "cloudwright",
      "args": ["mcp"]
    }
  }
}
```

### Architecture Diffing

Structured comparison between two ArchSpec versions with component-level changes, cost delta, and compliance impact assessment.

```bash
cloudwright diff v1.yaml v2.yaml
```

Detects: added/removed components, changed configurations, connection changes (added/removed/modified), cost impact, and security implications (removal of WAF, encryption changes, auth service changes).

### Multi-Cloud Comparison

Maps equivalent services across providers using 22 cross-cloud equivalence pairs:

```
ec2 <-> compute_engine <-> virtual_machines
rds <-> cloud_sql <-> azure_sql
s3  <-> cloud_storage <-> blob_storage
eks <-> gke <-> aks
...
```

```bash
cloudwright compare spec.yaml --providers gcp,azure
```

Shows side-by-side service mapping with monthly cost totals per provider.

### Architecture Linter

10 anti-pattern checks:

```bash
cloudwright lint spec.yaml
cloudwright lint spec.yaml --strict  # fail on warnings too
```

Errors: unencrypted data stores, single-AZ databases, missing load balancer, public databases, single point of failure.
Warnings: oversized instances (16xlarge+), missing WAF, missing monitoring, missing backups, missing auth.

### Architecture Scorer

Five-dimension quality scoring (0-100, letter grade):

```bash
cloudwright score spec.yaml --with-cost
```

- **Reliability** (30%): load balancing, multi-AZ, auto-scaling, CDN, caching
- **Security** (25%): WAF, auth, encryption, HTTPS, DNS management
- **Cost Efficiency** (20%): budget compliance, per-component ratio, free tier usage
- **Compliance** (15%): framework validation score
- **Complexity** (10%): component count, connection density, tier separation

Grades: A (90+), B (80+), C (70+), D (60+), F (<60).

### Blast Radius Analysis

Dependency graph analysis with SPOF detection and critical path identification.

```bash
cloudwright analyze spec.yaml
cloudwright analyze spec.yaml --component api_gateway  # focus on one component
```

For each component: direct dependents, transitive dependents, blast radius, SPOF status, and tier position.

### Drift Detection

Compares architecture spec against deployed infrastructure.

```bash
cloudwright drift spec.yaml terraform.tfstate
cloudwright drift spec.yaml cloudformation-template.yaml
```

Produces a drift score (0.0-1.0) with lists of drifted, extra, and missing components.

### Policy Engine

Policy-as-code via YAML rules. Nine built-in checks: max_components, all_encrypted, require_multi_az, budget_monthly, no_banned_services, required_tags, min_redundancy, allowed_providers, allowed_regions.

```yaml
# policy.yaml
rules:
  - name: enforce-encryption
    check: all_encrypted
    severity: deny
  - name: budget-cap
    check: budget_monthly
    value: 10000
    severity: deny
  - name: no-azure
    check: allowed_providers
    value: [aws, gcp]
    severity: warn
```

```bash
cloudwright policy spec.yaml --rules policy.yaml
```

Severity levels: `deny` (exit code 1), `warn`, `info`.

### Architecture Decision Records

Generate an ADR (Architecture Decision Record) from any ArchSpec. Uses the MADR format with context, decision, consequences, and cost estimate.

```bash
cloudwright adr spec.yaml                          # print to stdout
cloudwright adr spec.yaml --output docs/ADR-001.md
cloudwright adr spec.yaml --title "Platform Choice" --decision "Adopt Databricks over AWS EMR"
```

### Templates

17 starter architectures across four providers:

```bash
cloudwright init --list                              # show available templates
cloudwright init --template serverless_api           # AWS API Gateway + Lambda + DynamoDB
cloudwright init --template gcp_microservices -o .   # GKE + service mesh
cloudwright init --template databricks_lakehouse     # Unity Catalog + SQL Warehouse + DLT
cloudwright init --project                           # create .cloudwright/ project directory
```

**AWS** (8): three_tier_web, serverless_api, ml_pipeline, data_lake, event_driven, static_site, microservices, batch_processing.
**GCP** (3): three_tier_web, serverless_api, microservices.
**Azure** (3): three_tier_web, serverless_api, microservices.
**Databricks** (2): databricks_lakehouse, databricks_ml_platform.

### Web UI

FastAPI backend + React frontend for browser-based architecture design.

```bash
pip install 'cloudwright-ai[web]'
cloudwright chat --web
```

10 API endpoints: design, modify, cost, validate, export, diff, catalog search, catalog compare, chat, health.

### Structured Output and Streaming

All commands support machine-readable output with consistent JSON envelopes:

```bash
cloudwright --json cost spec.yaml          # {"data": {"estimate": {...}}}
cloudwright --json security spec.yaml      # {"data": {"passed": false, "findings": [...]}}
```

Errors use a separate envelope: `{"error": {"code": "...", "message": "...", "action": "..."}}`. Data goes to stdout, diagnostics to stderr.

NDJSON streaming emits one JSON object per line for incremental consumption:

```bash
cloudwright --stream --json validate spec.yaml --compliance hipaa
# {"framework":"HIPAA","check":"encryption_at_rest","passed":false,...}
# {"framework":"HIPAA","check":"encryption_in_transit","passed":true,...}
```

### Dry-Run Mode

Preview LLM operations without burning API credits:

```bash
cloudwright --dry-run design "3-tier web app on AWS"
# Shows model name, estimated tokens, prompt preview — no API call
```

Supported on all LLM-powered commands: `design`, `modify`, `adr`.

### Plugin System

Four extension points via Python entry points:

- `cloudwright.exporters` — custom export formats
- `cloudwright.validators` — custom compliance frameworks
- `cloudwright.policies` — custom policy checks
- `cloudwright.importers` — custom infrastructure importers

```bash
cloudwright --list-plugins  # discover installed plugins
```

## ArchSpec Format

ArchSpec is plain YAML, human-editable, and version-controllable alongside code.

```yaml
name: healthcare-portal
version: 1
provider: aws
region: us-east-1

constraints:
  compliance: [hipaa]
  budget_monthly: 5000
  availability: 99.9

components:
  - id: alb
    service: alb
    provider: aws
    label: Application Load Balancer
    tier: 1

  - id: api
    service: ecs
    provider: aws
    label: API Service
    tier: 2
    config:
      launch_type: FARGATE
      cpu: 512
      memory: 1024
      desired_count: 2

  - id: db
    service: rds
    provider: aws
    label: PostgreSQL
    tier: 3
    config:
      engine: postgresql
      instance_class: db.r5.large
      multi_az: true
      encryption: true
      storage_gb: 100

connections:
  - source: alb
    target: api
    protocol: https
    port: 443
  - source: api
    target: db
    protocol: tcp
    port: 5432
```

Components use a 5-tier system for vertical positioning: Edge (0), Ingress (1), Compute (2), Data (3), Storage/Analytics (4).

## CLI Reference

| Command | Description |
|---|---|
| `design <prompt>` | Generate ArchSpec from natural language |
| `modify <spec> <instruction>` | Modify existing spec with natural language |
| `cost <spec>` | Monthly cost breakdown with `--compare`, `--pricing-tier`, `--workload-profile` / `-w` |
| `compare <spec>` | Multi-cloud service mapping and cost comparison |
| `validate <spec>` | Compliance checks with `--compliance`, `--well-architected`, `--report` |
| `export <spec>` | Export to IaC/diagram/SBOM with `--format`, `--output` |
| `diff <spec_a> <spec_b>` | Structured diff with cost delta and compliance impact |
| `import <source>` | Import from Terraform state or CloudFormation (70+ types) |
| `chat` | Interactive multi-turn design session (`--web` for browser UI) |
| `init` | Initialize from template with `--template`, `--project` |
| `lint <spec>` | Anti-pattern detection (`--strict` fails on warnings) |
| `score <spec>` | Quality scoring across 5 dimensions (`--with-cost`) |
| `analyze <spec>` | Blast radius and SPOF detection (`--component` for focus) |
| `drift <spec> <infra>` | Compare design vs deployed infrastructure |
| `policy <spec>` | Evaluate policy rules from YAML (`--rules`) |
| `refresh` | Update catalog pricing data (`--provider`, `--dry-run`) |
| `catalog search <query>` | Search instance catalog by specs |
| `catalog compare <a> <b>` | Side-by-side instance comparison |
| `security <spec>` | Scan for security anti-patterns (`--fail-on critical/high/medium`) |
| `adr <spec>` | Generate Architecture Decision Record (`--output`, `--title`, `--decision`) |
| `schema <query>` | Introspect service configs (`aws.ec2`) or compliance frameworks (`hipaa`) |
| `mcp` | Start MCP server for AI agent integration (`--tools`, `--transport`) |
| `databricks-validate <spec>` | Validate Databricks components against workspace (`--host`, `--token`) |

Global flags: `--json`, `--verbose / -v`, `--version / -V`, `--dry-run`, `--stream`.

## Python API

```python
from pathlib import Path
from cloudwright import ArchSpec
from cloudwright.cost import CostEngine
from cloudwright.validator import Validator
from cloudwright.exporter import export_spec
from cloudwright.differ import diff_specs
from cloudwright.linter import lint
from cloudwright.scorer import Scorer

spec = ArchSpec.from_file("spec.yaml")

# Cost (with workload profile for production-realistic estimates)
engine = CostEngine()
priced = engine.estimate(spec, workload_profile="medium")
for item in priced.cost_estimate.breakdown:
    print(f"{item.component_id}: ${item.monthly:,.2f}/mo")

# Compliance
validator = Validator()
results = validator.validate(spec, compliance=["hipaa", "pci-dss"])

# Export
hcl = export_spec(spec, "terraform", output_dir="./infra")
diagram = export_spec(spec, "mermaid")

# Diff
old = ArchSpec.from_file("v1.yaml")
new = ArchSpec.from_file("v2.yaml")
diff = diff_specs(old, new)

# Lint
findings = lint(spec)

# Score
scorer = Scorer()
report = scorer.score(spec)
print(f"Grade: {report.grade} ({report.overall:.0f}/100)")
```

## Service Catalog

Ships as a SQLite database bundled with the package. No network calls required.

- Compute, database, networking, and storage pricing for AWS, GCP, Azure, and Databricks
- 4 pricing tiers (on-demand, reserved 1yr/3yr, spot)
- Cross-cloud instance equivalences with confidence scores
- 22 service-level equivalence pairs for multi-cloud mapping (including Databricks)
- 11 named pricing formulas for managed/serverless services (including DBU-based)
- 100+ static fallback prices for less common services

```bash
cloudwright catalog search "8 vcpu 32gb memory"
cloudwright catalog compare m5.xlarge n2-standard-4 Standard_D4s_v5
```

## Benchmarks

Evaluated against raw Claude (Sonnet 4.6) across 54 use cases spanning greenfield, compliance, cost optimization, import, microservices, data pipelines, industry-specific, migration, edge computing, and cross-cloud comparison scenarios.

| Metric | Cloudwright | Claude (raw) | Delta |
|---|---|---|---|
| Structural Validity | 79.6% | 37.0% | +42.6 |
| Compliance Completeness | 62.9% | 38.5% | +24.3 |
| Export Quality (IaC) | 55.7% | 0.3% | +55.5 |
| Diff Capability | 100.0% | 0.0% | +100.0 |
| Reproducibility | 77.9% | 35.0% | +42.9 |
| Time to IaC | 82.5% | 0.0% | +82.5 |
| **Overall** | **68.1%** | **28.0%** | **+40.1** |

Cloudwright wins 6 of 8 metrics. Cost accuracy improved significantly in v0.3.3 with workload profiles, and import/migration reliability improved with 70+ resource type mappings.

Full results: [benchmark/results/benchmark_report.md](benchmark/results/benchmark_report.md)

## Repository Structure

```
cloudwright/
  packages/
    core/       pip install cloudwright-ai             Models, architect, catalog, cost, validators, exporters
    cli/        pip install 'cloudwright-ai[cli]'      Typer CLI with Rich formatting
    web/        pip install 'cloudwright-ai[web]'      FastAPI + React web UI
    mcp/        pip install cloudwright-ai-mcp          MCP server (18 tools for AI agents)
  skills/                                         Agent skill files (23 files, 5 layers)
  catalog/                                        Service catalog JSON (compute, database, storage, networking)
  benchmark/                                      54 use cases + evaluation framework
```

## Development

```bash
git clone https://github.com/xmpuspus/cloudwright
pip install -e packages/core -e packages/cli -e packages/web -e packages/mcp
```

```bash
pytest packages/core/tests/           # 1000+ tests
ruff check packages/ && ruff format packages/
```

LLM-dependent tests (architect, chat) require an API key and are skipped by default:

```bash
ANTHROPIC_API_KEY=sk-ant-... pytest packages/core/tests/test_architect.py -v
```

## License

MIT
