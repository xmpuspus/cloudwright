# CLI Reference

Full reference for the `cloudwright` command. See [Getting Started](getting-started.md) for the quick path.

Related: [Troubleshooting](troubleshooting.md) | [MCP Reference](mcp-reference.md) | [README](../README.md)

---

## Global flags

These go **before** the subcommand:

```bash
cloudwright [--json] [--stream] [--verbose] [--dry-run] <subcommand> ...
```

| Flag | Description |
|---|---|
| `--json` | Output as JSON instead of rich terminal output |
| `--stream` | NDJSON streaming — one JSON object per line (combine with `--json`) |
| `--dry-run` | Preview LLM calls without making them (shows model, tokens, prompt preview) |
| `--verbose` / `-v` | Verbose logging |
| `--version` / `-V` | Print version and exit |

---

## Design and modify

### `design`

Generate a cloud architecture from a natural-language description.

**Requires:** `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

```bash
cloudwright design <description> [options]
```

| Option | Default | Description |
|---|---|---|
| `--provider` | `aws` | Cloud provider: `aws`, `gcp`, `azure`, `databricks` |
| `--region` | `us-east-1` | Primary region |
| `--budget` | none | Monthly budget cap in USD |
| `--compliance` | none | Compliance framework(s): `hipaa`, `pci-dss`, `soc2`, `fedramp`, `gdpr`. Repeatable. |
| `--output` / `-o` | auto-save | Write YAML to this file |
| `--yaml` | off | Show YAML panel instead of ASCII diagram |

Examples:

```bash
cloudwright design "HIPAA-compliant healthcare API on AWS with Postgres and Redis"
cloudwright design "serverless event pipeline" --provider gcp --region us-central1
cloudwright design "e-commerce platform" --compliance pci-dss --budget 3000 -o shop.yaml
```

v1.6 note: `design` now runs a generate->critique->repair loop. Blocking findings (missing encryption, SPOFs, missing load balancer) are fed back to the model so it self-corrects before the spec is returned.

---

### `modify`

Apply a natural-language modification to an existing spec. Shows a structured diff and cost delta before writing.

**Requires:** `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

```bash
cloudwright modify <spec.yaml> <instruction> [options]
```

| Option | Default | Description |
|---|---|---|
| `--output` / `-o` | overwrite input | Write modified spec here |
| `--dry-run` | off | Show changes without writing |

Examples:

```bash
cloudwright modify spec.yaml "add a Redis cache between the API and the database"
cloudwright modify spec.yaml "move compute from ECS to Lambda" -o serverless.yaml
cloudwright modify spec.yaml "upgrade the database to Aurora Serverless v2" --dry-run
```

---

### `compare`

Translate a spec to one or more other cloud providers and show a side-by-side service and cost comparison.

**Requires:** `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

```bash
cloudwright compare <spec.yaml> --providers <provider1,provider2,...>
```

Example:

```bash
cloudwright compare spec.yaml --providers gcp,azure
```

---

### `chat`

Multi-turn interactive architecture design. In terminal mode, type a description to get started; use `/help` to see in-session commands (`/yaml`, `/diagram`, `/cost`, `/validate`, `/terraform`, `/export <fmt>`, `/save`, `/new`).

**Requires:** `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

```bash
cloudwright chat [options]
```

| Option | Default | Description |
|---|---|---|
| `--web` | off | Launch web canvas at `http://localhost:8765` instead of terminal |
| `--port` | `8765` | Port for `--web` |
| `--resume` | none | Resume a saved session by ID |
| `--debug` | off | Log LLM requests and token counts to stderr |

```bash
cloudwright chat                 # terminal session
cloudwright chat --web           # browser canvas
cloudwright chat --resume abc123 # resume prior session
```

---

## Cost

### `cost`

Show monthly cost breakdown for an existing spec. Runs offline.

```bash
cloudwright cost <spec.yaml> [options]
```

| Option | Default | Description |
|---|---|---|
| `--compare` | none | Comma-separated providers for multi-cloud cost comparison |
| `--pricing-tier` | `on_demand` | `on_demand`, `reserved_1yr`, `reserved_3yr`, `spot` |
| `--workload-profile` / `-w` | none | `small`, `medium`, `large`, `enterprise` — sets realistic traffic/storage defaults |

Examples:

```bash
cloudwright cost spec.yaml
cloudwright cost spec.yaml --workload-profile medium
cloudwright cost spec.yaml --compare gcp,azure
cloudwright cost spec.yaml --pricing-tier reserved_1yr
```

---

## Validate and compliance

### `validate`

Run compliance or Well-Architected checks against a spec. Exit code 1 on any failure.

Runs offline.

```bash
cloudwright validate <spec.yaml> --compliance <frameworks> [options]
cloudwright validate <spec.yaml> --well-architected [options]
```

| Option | Default | Description |
|---|---|---|
| `--compliance` | none | Comma-separated frameworks: `hipaa`, `pci-dss`, `soc2`, `fedramp`, `gdpr` |
| `--well-architected` | off | Run Well-Architected pillar checks |
| `--report` | none | Write a markdown compliance report to this path |
| `--pdf` | none | Write a PDF compliance report (requires `cloudwright-ai[pdf]`) |

Examples:

```bash
cloudwright validate spec.yaml --compliance hipaa,soc2
cloudwright validate spec.yaml --well-architected
cloudwright validate spec.yaml --compliance pci-dss --report report.md
```

---

### `compliance`

Deeper scan that maps every finding to its exact framework control ID. Optionally folds in a Checkov deep scan against the exported Terraform.

Runs offline. Checkov integration requires `pip install 'cloudwright-ai[compliance]'` and `checkov` on PATH.

```bash
cloudwright compliance <spec.yaml> [options]
```

| Option | Default | Description |
|---|---|---|
| `--frameworks` / `-f` | all | Comma-separated: `hipaa`, `soc2`, `pci-dss`, `fedramp`, `gdpr`, `iso27001`, `nist` |
| `--checkov` / `--no-checkov` | auto-detect | Force or skip the Checkov deep scan |
| `--fail-on` | `high` | Fail on: `critical`, `high`, `medium`, `none` |
| `--output` / `-o` | none | Write a markdown control report to this path |

Examples:

```bash
cloudwright compliance spec.yaml
cloudwright compliance spec.yaml --frameworks hipaa,soc2 -o controls.md
cloudwright compliance spec.yaml --checkov --fail-on critical
```

---

### `security`

Scan for security anti-patterns: unencrypted stores, public-facing databases, missing WAF, weak auth, overly permissive protocols.

Runs offline.

```bash
cloudwright security <spec.yaml> [options]
```

| Option | Default | Description |
|---|---|---|
| `--fail-on` | `high` | Fail on: `critical`, `high`, `medium`, `none` |
| `--output` / `-o` | none | Write findings to a file |

Example:

```bash
cloudwright security spec.yaml --fail-on medium
```

---

### `review` (v1.6)

Unified offline review: runs scorer, linter, and validator together and returns a single severity-ranked finding list. Free, no API key required.

```bash
cloudwright review <spec.yaml> [options]
```

| Option | Default | Description |
|---|---|---|
| `--compliance` | none | Comma-separated frameworks to include in the validator pass |
| `--well-architected` | off | Include Well-Architected checks |

Examples:

```bash
cloudwright review spec.yaml
cloudwright review spec.yaml --compliance hipaa --well-architected
cloudwright --json review spec.yaml
```

---

## Export and plan

### `export`

Export an ArchSpec to IaC, diagram, or audit formats.

Runs offline (SVG/PNG require the D2 binary: `curl -fsSL https://d2lang.com/install.sh | sh`).

```bash
cloudwright export <spec.yaml> --format <fmt> [options]
```

| Option | Description |
|---|---|
| `--format` / `-f` | `terraform`, `pulumi-ts`, `pulumi-python`, `cloudformation`, `mermaid`, `d2`, `svg`, `png`, `sbom`, `aibom` |
| `--output` / `-o` | Output file or directory. For `terraform`, `pulumi-ts`, `pulumi-python`: pass a directory path for a full project layout. |

Examples:

```bash
cloudwright export spec.yaml --format terraform -o ./infra
cloudwright export spec.yaml --format pulumi-ts -o ./infra
cloudwright export spec.yaml --format cloudformation -o template.yaml
cloudwright export spec.yaml --format mermaid
cloudwright export spec.yaml --format sbom -o sbom.json
```

---

### `plan`

Prove the exported infrastructure is deployable. Runs `terraform validate` and optionally `terraform plan` (or `pulumi preview`). Nothing is applied.

Requires Terraform or Pulumi on PATH. `--no-plan` skips the credential-requiring plan step.

```bash
cloudwright plan <spec.yaml> [options]
```

| Option | Default | Description |
|---|---|---|
| `--target` / `-t` | `terraform` | `terraform`, `pulumi-python`, `pulumi-ts` |
| `--no-plan` | off | Validate only (no credentials needed) |
| `--timeout` | `180` | Seconds before the plan step is aborted |

Examples:

```bash
cloudwright plan spec.yaml
cloudwright plan spec.yaml --no-plan
cloudwright plan spec.yaml --target pulumi-ts
cloudwright --json plan spec.yaml
```

---

## Import and drift

### `import`

Import an existing Terraform state file or CloudFormation template into an ArchSpec YAML.

Runs offline.

```bash
cloudwright import <source> [options]
```

| Option | Default | Description |
|---|---|---|
| `--format` / `-f` | auto-detect | `terraform` or `cloudformation` |
| `--output` / `-o` | stdout | Write ArchSpec YAML to this file |
| `--name` | from source | Override the architecture name |

Examples:

```bash
cloudwright import terraform.tfstate -o spec.yaml
cloudwright import stack.yaml --format cloudformation -o spec.yaml
```

---

### `import-live`

Walk live cloud APIs to produce an ArchSpec from running infrastructure. Requires `pip install 'cloudwright-ai[live-import]'` and cloud credentials.

```bash
cloudwright import-live [options]
```

| Option | Default | Description |
|---|---|---|
| `--provider` | `aws` | `aws`, `gcp`, `azure` |
| `--region` | `us-east-1` | Cloud region |
| `--profile` | none | AWS named profile (`~/.aws/credentials`) |
| `--project` | none | GCP project ID (or `GOOGLE_CLOUD_PROJECT` env) |
| `--subscription` | none | Azure subscription ID (or `AZURE_SUBSCRIPTION_ID` env) |
| `--services` | all | Comma-separated subset, e.g. `ec2,rds,s3` |
| `--output` / `-o` | stdout | Write ArchSpec YAML to this file |
| `--name` | auto | Override the architecture name |

Examples:

```bash
cloudwright import-live --provider aws --region us-east-1 -o spec.yaml
cloudwright import-live --provider aws --profile staging --services ec2,rds
cloudwright import-live --provider gcp --project my-project-123 -o gcp-spec.yaml
cloudwright import-live --provider azure --subscription xxxxxxxx-xxxx-... -o azure.yaml
```

---

### `drift`

Compare a design spec against deployed infrastructure to detect configuration drift.

Runs offline.

```bash
cloudwright drift <spec.yaml> <infra-file> [options]
```

| Option | Default | Description |
|---|---|---|
| `--format` / `-f` | `auto` | Infrastructure format: `auto`, `terraform`, `cloudformation` |

Example:

```bash
cloudwright drift spec.yaml terraform.tfstate
cloudwright --json drift spec.yaml stack.yaml --format cloudformation
```

---

### `diff`

Show the structural diff between two ArchSpec files: added, removed, and changed components, and total cost delta.

Runs offline.

```bash
cloudwright diff <spec-a.yaml> <spec-b.yaml>
```

Example:

```bash
cloudwright diff v1.yaml v2.yaml
cloudwright --json diff v1.yaml v2.yaml
```

---

## Analysis

### `lint`

Detect architecture anti-patterns: unencrypted data stores, single-AZ databases, missing load balancer on public compute, missing auth, oversized instances.

Runs offline.

```bash
cloudwright lint <spec.yaml> [options]
```

| Option | Default | Description |
|---|---|---|
| `--strict` | off | Fail on warnings in addition to errors |

Example:

```bash
cloudwright lint spec.yaml
cloudwright lint spec.yaml --strict
cloudwright --json --stream lint spec.yaml
```

---

### `score`

Score an architecture across 5 dimensions: reliability (30%), security (25%), cost efficiency (20%), compliance (15%), complexity (10%). Returns 0-100 with a letter grade.

Runs offline.

```bash
cloudwright score <spec.yaml> [options]
```

| Option | Default | Description |
|---|---|---|
| `--with-cost` | off | Run cost estimation before scoring (improves cost-dimension accuracy) |

Example:

```bash
cloudwright score spec.yaml
cloudwright score spec.yaml --with-cost
```

---

### `analyze`

Analyze blast radius, single points of failure, and dependency structure.

Runs offline.

```bash
cloudwright analyze <spec.yaml> [options]
```

| Option | Default | Description |
|---|---|---|
| `--component` / `-c` | all | Focus analysis on a specific component ID |

Examples:

```bash
cloudwright analyze spec.yaml
cloudwright analyze spec.yaml --component rds_primary
```

---

### `policy`

Evaluate a spec against custom policy rules defined in a YAML file. Built-in checks cover budget limits, provider constraints, required components, and compliance flags.

Runs offline.

```bash
cloudwright policy <spec.yaml> --rules <rules.yaml>
```

Exit code 1 when any `deny` rule fires.

---

### `adr`

Generate an Architecture Decision Record (MADR format) from a spec.

**Requires:** `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (falls back to a deterministic template if the LLM is unavailable).

```bash
cloudwright adr <spec.yaml> [options]
```

| Option | Default | Description |
|---|---|---|
| `--output` / `-o` | stdout | Write the ADR markdown to this file |
| `--title` | auto | ADR title |
| `--decision` | auto | Specific decision to document |

Example:

```bash
cloudwright adr spec.yaml -o docs/adr-001.md
cloudwright adr spec.yaml --decision "use Aurora Serverless over standard RDS"
```

---

## Misc

### `init`

Create an ArchSpec from a pre-built template. Use `--list` to see available templates.

Runs offline.

```bash
cloudwright init --template <name> [options]
cloudwright init --list
```

| Option | Default | Description |
|---|---|---|
| `--template` / `-t` | none | Template name (see `--list`) |
| `--output` / `-o` | `spec.yaml` | Output file |
| `--list` / `-l` | off | List available templates |
| `--provider` | from template | Override provider |
| `--region` | from template | Override region |
| `--name` | from template | Override architecture name |
| `--compliance` | none | Comma-separated compliance frameworks |
| `--budget` | none | Monthly budget in USD |
| `--project` / `-p` | off | Create a `.cloudwright/` project directory with a config file |

Examples:

```bash
cloudwright init --list
cloudwright init --template aws-three-tier -o infra.yaml
cloudwright init --template aws-three-tier --compliance hipaa --budget 5000
```

---

### `schema`

Look up service config fields, pricing formula, and cross-cloud equivalents, or list the checks for a compliance framework.

Runs offline.

```bash
cloudwright schema <query>
```

`query` is either a `provider.service` key (e.g. `aws.ec2`, `gcp.cloud_sql`) or a compliance framework name (`hipaa`, `soc2`).

Examples:

```bash
cloudwright schema aws.ec2
cloudwright schema gcp.cloud_run
cloudwright schema hipaa
cloudwright --json schema aws.rds
```

---

### `catalog`

Search and compare cloud instances from the bundled pricing catalog.

Runs offline.

```bash
cloudwright catalog search <query> [options]
cloudwright catalog compare <instance1> <instance2> ...
```

| `search` option | Description |
|---|---|
| `--provider` | Filter by provider: `aws`, `gcp`, `azure` |
| `--vcpus` | Minimum vCPUs |
| `--memory` | Minimum memory in GB |

Examples:

```bash
cloudwright catalog search "memory-optimized aws"
cloudwright catalog search "4 vcpu 32gb" --provider aws
cloudwright catalog compare m5.xlarge m6i.xlarge
```

---

### `refresh`

Fetch live pricing from cloud provider APIs and write into the local catalog database.

Requires network access. Does not require an LLM key.

```bash
cloudwright refresh [options]
```

| Option | Default | Description |
|---|---|---|
| `--provider` / `-p` | all | `aws`, `gcp`, or `azure` |
| `--category` / `-c` | all | Filter to a category or service name |
| `--region` / `-r` | default | Override region for pricing lookups |
| `--dry-run` | off | Fetch but don't write to catalog |

---

### `databricks-validate`

Validate Databricks components in a spec against a live workspace. Requires `pip install 'cloudwright-ai[databricks]'` and `DATABRICKS_HOST` / `DATABRICKS_TOKEN`.

```bash
cloudwright databricks-validate <spec.yaml> [--host URL] [--token TOKEN]
```

---

### `mcp`

Start an MCP server exposing Cloudwright tools to AI agents (Claude Desktop, Cursor, Cline).

```bash
cloudwright mcp [options]
```

| Option | Default | Description |
|---|---|---|
| `--tools` / `-t` | all | Comma-separated tool groups: `design`, `cost`, `validate`, `analyze`, `export`, `session` |
| `--transport` | `stdio` | `stdio` or `sse` |

See [MCP Reference](mcp-reference.md) for setup instructions.

## New flags in v1.6.0

| Command | Flag | Purpose |
|---|---|---|
| `compliance` | `--oscal` / `-O` | Also emit an OSCAL 1.1.2 component-definition JSON (to `<output>.oscal.json` when `--output` is set, else stdout). |
| `compliance` | `--traceability` | Print the chain component -> Terraform resource -> framework control ID -> status. |
| `cost` | `--carbon` | Include a design-time carbon (kg CO2e/month) estimate. |
| `cost` | `--focus` | Emit a FinOps FOCUS-spec CSV of the cost line items (`-o file.csv` or stdout). |
| `export` | `--format opentofu` | Alias for the Terraform HCL target (OpenTofu-compatible). `tofu`/`terraform` for `plan` is auto-detected; override with `CLOUDWRIGHT_TF_BINARY`. |
| `drift` | `--remediate` | Turn detected drift into a read-only remediation preview: diff -> cost delta -> quality delta -> terraform/tofu plan. |

`cloudwright design` now runs a generate -> critique -> repair loop by default and records a `critique` block (score, grade, findings, repair iterations) in `spec.metadata`. The same critics are exposed offline as `cloudwright review <spec>`.
