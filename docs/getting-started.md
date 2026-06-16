# Getting Started

This guide gets you from zero to a deployable architecture spec in about five minutes.

Related: [CLI Reference](cli-reference.md) | [Troubleshooting](troubleshooting.md) | [MCP Reference](mcp-reference.md) | [README](../README.md)

---

## Install

Cloudwright is published as four packages. The `[cli]` extra is the starting point for most users.

```bash
pip install 'cloudwright-ai[cli]'
```

Other extras:

| Extra | What it adds |
|---|---|
| `[cli]` | The `cloudwright` command |
| `[web]` | FastAPI backend + React canvas (`cloudwright chat --web`) |
| `[mcp]` | MCP server for Claude Desktop / Cursor / Cline |
| `[all]` | All of the above |
| `[pdf]` | PDF compliance report export |
| `[live-import]` | `import-live` for AWS, GCP, and Azure |
| `[live-import-aws]` | AWS-only live import (boto3) |
| `[live-import-gcp]` | GCP-only live import |
| `[live-import-azure]` | Azure-only live import |
| `[compliance]` | Checkov deep scan in `cloudwright compliance` |
| `[databricks]` | `databricks-validate` adapter |

All extras together:

```bash
pip install 'cloudwright-ai[all]'
```

Requires Python 3.12 or later.

---

## Set your API key

`cloudwright design`, `cloudwright modify`, `cloudwright compare`, `cloudwright chat`, and `cloudwright adr` call an LLM. All other commands run offline.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

OpenAI also works:

```bash
export OPENAI_API_KEY=sk-...
```

Cloudwright picks up whichever key is present. Anthropic (Claude Sonnet for design, Haiku for projection) is preferred when both are set.

---

## Design your first architecture

```bash
cloudwright design "3-tier web app on AWS with PostgreSQL and Redis"
```

This runs the LLM, prints an ASCII diagram and cost table, and auto-saves a `spec.yaml` in the current directory. v1.6 adds a generate->critique->repair loop: blocking findings (missing encryption, single points of failure) are fed back to the model before the spec is returned.

Common options:

```bash
# Target a different provider or region
cloudwright design "serverless API" --provider gcp --region us-central1

# Add compliance constraints
cloudwright design "healthcare API with Postgres" --compliance hipaa --compliance soc2

# Set a monthly budget cap
cloudwright design "data pipeline" --budget 2000

# Save spec to a specific file
cloudwright design "..." -o my-arch.yaml

# Print YAML panel instead of ASCII diagram
cloudwright design "..." --yaml
```

The global `--dry-run` flag shows what the LLM call would look like without making it:

```bash
cloudwright --dry-run design "3-tier web app on AWS"
```

---

## Estimate cost

`cost` runs offline against a bundled SQLite pricing catalog. No API key needed.

```bash
cloudwright cost spec.yaml
cloudwright cost spec.yaml --workload-profile medium
```

Workload profiles (`small`, `medium`, `large`, `enterprise`) set realistic defaults for request volumes, storage, node counts, and data transfer.

---

## Validate against a compliance framework

```bash
cloudwright validate spec.yaml --compliance hipaa
cloudwright validate spec.yaml --compliance hipaa,soc2
cloudwright validate spec.yaml --well-architected
cloudwright validate spec.yaml --compliance pci-dss --report report.md
```

Available frameworks: `hipaa`, `pci-dss`, `soc2`, `fedramp`, `gdpr`, plus `well-architected`. Exit code is non-zero when any check fails.

For a deeper scan that maps each finding to its specific control ID (HIPAA `164.312`, SOC 2 `CC6.1`, FedRAMP `SC-28`, PCI-DSS, GDPR, ISO 27001, NIST 800-53) and optionally folds in Checkov against the generated Terraform:

```bash
cloudwright compliance spec.yaml --frameworks hipaa,soc2
```

---

## Export to Terraform (or Pulumi / CloudFormation)

```bash
# Print HCL to stdout
cloudwright export spec.yaml --format terraform

# Write a Terraform project directory
cloudwright export spec.yaml --format terraform -o ./infra

# Pulumi TypeScript or Python project
cloudwright export spec.yaml --format pulumi-ts -o ./infra
cloudwright export spec.yaml --format pulumi-python -o ./infra

# CloudFormation YAML
cloudwright export spec.yaml --format cloudformation -o template.yaml
```

All IaC exporters apply safe defaults: S3 public-access blocks, RDS encryption and deletion protection, EC2 IMDSv2, CloudFront TLSv1.2_2021.

---

## Prove the export deploys (requires Terraform or Pulumi on PATH)

```bash
# Offline proof: runs terraform validate, no cloud credentials needed
cloudwright plan spec.yaml --no-plan

# Full proof: runs terraform plan with a real resource diff
cloudwright plan spec.yaml
```

Nothing is applied. The verdict is `DEPLOYABLE` or `NOT DEPLOYABLE`.

---

## Commands that work fully offline

No LLM call, no cloud API call, no environment variables needed:

| Command | What it does |
|---|---|
| `cost` | Estimate monthly bill from bundled catalog |
| `validate` | Compliance and Well-Architected checks |
| `review` | Unified scorer + linter + validator (v1.6) |
| `export` | Generate Terraform / Pulumi / CloudFormation / diagrams |
| `diff` | Compare two ArchSpec files |
| `drift` | Compare spec against .tfstate or CloudFormation template |
| `lint` | Architecture anti-pattern detection |
| `score` | 5-dimension quality score (0-100) |
| `analyze` | Blast radius and SPOF analysis |
| `security` | Security anti-pattern scan |
| `compliance` | Control-mapped compliance scan (Checkov is optional) |
| `import` | Import .tfstate or CloudFormation into an ArchSpec |
| `schema` | Browse service configs and compliance checks |
| `catalog search` | Search cloud instance catalog |
| `catalog compare` | Compare instance types side by side |
| `init` | Create a spec from a pre-built template |

Commands that call an LLM (require `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`):

- `design` — generate a new architecture
- `modify` — update an existing spec with a natural-language instruction
- `compare` — translate a spec to other providers
- `chat` — multi-turn terminal or web session
- `adr` — generate an Architecture Decision Record

---

## Web canvas

```bash
pip install 'cloudwright-ai[web]'
cloudwright chat --web
```

Opens `http://localhost:8765`. The canvas lets you chat to design, drag and drop components, edit fields, add resources from the catalog drawer, and run Compliance and Plan checks in the UI.

Use a different port:

```bash
cloudwright chat --web --port 9000
```

---

## Machine-readable output

Every command accepts `--json` before the subcommand:

```bash
cloudwright --json cost spec.yaml
cloudwright --json validate spec.yaml --compliance hipaa

# NDJSON streaming: one JSON line per finding
cloudwright --json --stream security spec.yaml
```

---

## Next steps

- [CLI Reference](cli-reference.md) — every command with all options
- [Troubleshooting](troubleshooting.md) — common errors and fixes
- [MCP Reference](mcp-reference.md) — use Cloudwright from Claude Desktop or Cursor
