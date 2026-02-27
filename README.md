# Cloudwright

Architecture intelligence for cloud engineers.

Cloudwright bridges the gap between whiteboard architecture and deployable infrastructure. You describe a system in natural language or YAML, and Cloudwright produces cost estimates, compliance reports, Terraform, diagrams, and structured diffs — all from the same central data format called **ArchSpec**.

Every capability — design, pricing, validation, export, diffing — operates on ArchSpec. It is the universal format that lets these tools compose cleanly without custom glue code.

## Capabilities

- **Natural language design** — describe your system in plain English, get a fully structured ArchSpec back
- **Cost estimation** — per-component monthly pricing from a built-in catalog, no external API calls required
- **Pricing tiers** — `--pricing-tier` flag on `cost` for on-demand, reserved 1yr/3yr, and spot pricing
- **Multi-cloud comparison** — map equivalent instance types across AWS, GCP, and Azure and compare costs side by side
- **Compliance checks** — HIPAA, PCI-DSS, SOC 2, and AWS Well-Architected Framework validation with actionable findings
- **Policy-as-code engine** — define custom compliance rules via `cloudwright policy`
- **Infrastructure export** — generate production-ready Terraform HCL or CloudFormation YAML directly from your spec
- **D2 diagram export** — D2 diagram format (d2, d2-svg, d2-png) for rich architecture diagrams
- **Architecture diagrams** — Mermaid flowchart output for documentation and review
- **SBOM / AIBOM** — CycloneDX software bill of materials and OWASP AI bill of materials for supply chain visibility
- **Structured diffing** — compare two ArchSpec versions with component-level changes, cost delta, and compliance impact
- **JSON output** — `--json` flag for machine-readable output on all commands
- **Version flag** — `--version` to print the installed version
- **Verbose errors** — `--verbose` / `-v` to show full tracebacks on errors

## Quick Start

```bash
pip install cloudwright[cli]
```

Set at least one LLM provider key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

```bash
# Design an architecture from natural language
cloudwright design "3-tier web app on AWS with Redis cache and RDS PostgreSQL"

# Estimate monthly cost
cloudwright cost spec.yaml

# Validate compliance
cloudwright validate spec.yaml --compliance hipaa

# Export to Terraform
cloudwright export spec.yaml --format terraform -o ./infra
```

## Repository Structure

```
cloudwright/
  packages/
    core/       pip install cloudwright          ArchSpec models, LLM architect, catalog, cost engine, exporters
    cli/        pip install cloudwright[cli]     Typer CLI with Rich formatting
    web/        pip install cloudwright[web]     FastAPI + React web UI
  catalog/                                   Service catalog JSON (compute, database, storage, networking)
  examples/                                  Runnable demos, no API key required for most
```

## ArchSpec Format

ArchSpec is the central interchange format. It is plain YAML, human-editable, and version-controlled naturally alongside code.

```yaml
name: healthcare-portal
version: 1
provider: aws
region: us-east-1

components:
  - id: web
    service: ec2
    provider: aws
    label: Web Servers
    tier: 2
    config:
      instance_type: t3.medium
      count: 2

  - id: db
    service: rds
    provider: aws
    label: PostgreSQL Database
    tier: 3
    config:
      engine: postgresql
      instance_class: db.r5.large
      multi_az: true
      storage_gb: 100

connections:
  - source: web
    target: db
    protocol: tcp
    port: 5432
```

Optional `constraints` block:

```yaml
constraints:
  compliance: [hipaa]
  budget_monthly: 5000
  availability: 99.9
```

## CLI Reference

| Command | Description |
|---|---|
| `cloudwright design <prompt>` | Generate ArchSpec from natural language |
| `cloudwright cost <spec.yaml>` | Monthly cost breakdown from catalog |
| `cloudwright cost <spec.yaml> --compare gcp,azure` | Multi-cloud cost comparison |
| `cloudwright validate <spec.yaml> --compliance hipaa` | Compliance check (hipaa, pci-dss, soc2, well-architected) |
| `cloudwright export <spec.yaml> --format terraform -o ./infra` | Export to IaC |
| `cloudwright diff v1.yaml v2.yaml` | Structured diff with cost delta |
| `cloudwright catalog search "4 vcpu 16gb"` | Search instance catalog |
| `cloudwright chat` | Interactive multi-turn design session |

## Python API

The core library is usable directly without the CLI.

**Cost estimation:**

```python
from cloudwright import ArchSpec
from cloudwright.cost import CostEngine

spec = ArchSpec.from_yaml(Path("spec.yaml").read_text())
engine = CostEngine()
priced = engine.price(spec)

for item in priced.cost_estimate.breakdown:
    print(f"{item.component_id}: ${item.monthly:,.2f}/mo")

print(f"Total: ${priced.cost_estimate.monthly_total:,.2f}/mo")
```

**Compliance validation:**

```python
from cloudwright.validator import Validator

validator = Validator()
results = validator.validate(spec, compliance=["hipaa", "pci-dss"])

for result in results:
    status = "PASS" if result.passed else "FAIL"
    print(f"{result.framework}: {status} ({result.score:.0%})")
    for check in result.checks:
        if not check.passed:
            print(f"  [{check.severity.upper()}] {check.name}: {check.recommendation}")
```

**Multi-cloud comparison:**

```python
alternatives = engine.compare_providers(spec, providers=["gcp", "azure"])

for alt in alternatives:
    delta = alt.monthly_total - priced.cost_estimate.monthly_total
    print(f"{alt.provider}: ${alt.monthly_total:,.2f}/mo ({delta:+,.2f})")
```

**Export:**

```python
from cloudwright.exporter import export_spec

hcl = export_spec(spec, "terraform", output_dir="./infra")
diagram = export_spec(spec, "mermaid")
sbom = export_spec(spec, "sbom", output="sbom.json")
```

## Service Catalog

The catalog ships as a SQLite database bundled with the package — no network calls, no rate limits.

- 58 compute instances across AWS, GCP, and Azure
- 39 managed services (RDS, ElastiCache, S3, CloudFront, SQS, and equivalents)
- Cross-cloud instance equivalences with confidence scores (e.g., `m5.large` → `n2-standard-2` → `Standard_D2s_v5`)
- Pricing data current as of the catalog build date, shown in each cost estimate

Search the catalog:

```bash
cloudwright catalog search "8 vcpu 32gb memory"
cloudwright catalog compare m5.xlarge --providers gcp,azure
```

## Export Formats

| Format | Flag | Output |
|---|---|---|
| Terraform HCL | `terraform` | `main.tf` with provider-native resources |
| CloudFormation | `cloudformation` | YAML template |
| Mermaid diagram | `mermaid` | Flowchart for embedding in docs or GitHub |
| CycloneDX SBOM | `sbom` | JSON bill of materials for all infrastructure components |
| OWASP AIBOM | `aibom` | AI bill of materials for LLM-backed components |

## Development

```bash
git clone https://github.com/theAtticAI/cloudwright
pip install -e packages/core
pip install -e packages/cli
pip install -e packages/web
```

Run tests:

```bash
pytest packages/core/tests/
```

Lint:

```bash
ruff check packages/
ruff format packages/
```

The full demo runs without any API keys — it uses `ArchSpec.from_yaml()` directly:

```bash
python examples/full_demo.py
```

## License

MIT
