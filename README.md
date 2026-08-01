# Cloudwright

*Describe a cloud architecture in English. Get Terraform, costs, and a compliance check.*

[![PyPI](https://img.shields.io/pypi/v/cloudwright-ai.svg)](https://pypi.org/project/cloudwright-ai/) [![CI](https://github.com/xmpuspus/cloudwright/actions/workflows/ci.yml/badge.svg)](https://github.com/xmpuspus/cloudwright/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python 3.12+](https://img.shields.io/pypi/pyversions/cloudwright-ai)](https://pypi.org/project/cloudwright-ai/) [![xmpuspus/cloudwright MCP server](https://glama.ai/mcp/servers/xmpuspus/cloudwright/badges/score.svg)](https://glama.ai/mcp/servers/xmpuspus/cloudwright)

<p align="center"><img src="examples/cloudwright-hero.gif" alt="A terminal runs cloudwright init, cost, compliance and plan. The compliance table maps every finding to a HIPAA and SOC 2 control ID. The plan step ends on a DEPLOYABLE verdict from terraform validate." width="820"></p>

```bash
pip install 'cloudwright-ai[cli]'
export ANTHROPIC_API_KEY=sk-ant-...
cloudwright design "HIPAA healthcare API on AWS with Postgres and Redis"
```

Cloudwright turns one line of English into a typed spec, a cost breakdown, a control-mapped compliance report,
and infrastructure code. It covers AWS, GCP, Azure and Databricks across 114 service keys. Only `design`,
`modify`, `chat` and `adr` call a model. Every other command runs offline and needs no API key.

[Quickstart](#quickstart) &middot; [Compliance](#every-finding-carries-the-control-id-it-violates) &middot; [Agents](#one-mcp-server-reaches-11-coding-agents) &middot; [Docs](docs/) &middot; [Changelog](CHANGELOG.md)

## A prompt produces a spec, a cost, a control-mapped report, and Terraform

- **Spec.** Typed YAML you commit, diff and review. Everything below reads from it.
- **Cost.** Per component and region-aware, with a confidence flag on every line.
- **Compliance.** HIPAA, SOC 2, PCI-DSS, FedRAMP, GDPR, ISO 27001 and NIST 800-53 control IDs.
- **Infrastructure code.** Terraform, OpenTofu, Pulumi (TypeScript or Python) and CloudFormation.
- **Diagrams.** ASCII, Mermaid, D2, and a web canvas you can edit by hand.
- **An MCP server**, so any coding agent runs the same checks inside its own loop.

Exports carry safe defaults. S3 gets a public-access block, SSE and versioning. RDS gets encryption, multi-AZ
and deletion protection. EC2 gets IMDSv2. A compliance framework overrides the workload profile, and always
forces encryption and high availability.

## Quickstart

```bash
cloudwright design "HIPAA healthcare API on AWS with Postgres and Redis"
cloudwright cost spec.yaml --workload-profile medium
cloudwright compliance spec.yaml --frameworks hipaa,soc2
cloudwright export spec.yaml --format terraform -o ./infra
cloudwright plan spec.yaml --target terraform          # proves it deploys, never applies
cloudwright chat --web                                 # canvas at http://localhost:8765
```

Add `--json` before any subcommand for machine-readable output, or `--stream` to watch tokens arrive. Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` for the four commands that need a model.

## Every finding carries the control ID it violates

<p align="center"><img src="examples/cloudwright-controls-web-demo.gif" alt="The web canvas Compliance tab shows a per-framework table for HIPAA, SOC 2 and FedRAMP. Each row carries satisfied and violated control IDs. The Plan tab then returns a DEPLOYABLE verdict." width="820"></p>

Other tools scan infrastructure after you deploy it. Cloudwright maps each finding to its control before any
resource exists. The fix then costs a spec edit, not a change ticket. HIPAA `164.312(a)(2)(iv)`, SOC 2 `CC6.1`
and FedRAMP `SC-28` come from the built-in scanner, with no extra tooling. Checkov folds into the same report
when it sits on your PATH.

- `--oscal` writes an OSCAL 1.1.2 component-definition with deterministic UUIDs.
- `--traceability` prints the chain from component to resource to control to status.
- `cloudwright plan` runs `terraform validate` against the export, and never applies.

## The review needs no API key and no network

<p align="center"><img src="examples/cloudwright-review-demo.gif" alt="cloudwright review prints a severity-ranked table for the patient-portal spec. It scores the spec 39 out of 100, with 15 findings and 8 blocking. A second command traces each component and Terraform resource to a violated HIPAA control." width="760"></p>

`cloudwright review` runs the scorer, the linter and the validator over a spec, and returns one severity-ranked
report. The same three critics run inside `cloudwright design`. When blocking findings survive generation, the
architect repairs the spec once and records the change in `spec.metadata.critique`. Pass
`Architect(repair=False)` to turn that off.

## Canvas edits never call the model, so they are instant and free

<p align="center"><img src="examples/cloudwright-smart-canvas-demo.gif" alt="The web canvas with a boundary-aware diagram. A catalog drawer adds an ElastiCache node, a side panel edits its label and config, and the cost total updates." width="820"></p>

Add, drag, connect, edit and delete are deterministic frontend mutations. The Catalog drawer serves the resource
list per provider and five approved multi-resource modules. Its standards check flags orphan connections,
partial modules and missing tags. An intact module exports as a single Terraform `module` block, with the
catalog's pinned source and version.

## One MCP server reaches 11 coding agents

```bash
cloudwright integrate --harness claude-code       # exact wiring, in that client's format
cloudwright integrate --harness cursor --write    # merge it into the right file
cloudwright integrate --rules --agent-file claude # a gate block for CLAUDE.md
```

Do not hand-write the config. `cloudwright integrate` emits it for Claude Code, Cursor, Cline, Windsurf, GitHub
Copilot, Zed, Codex CLI, Junie, Kiro and Antigravity. Aider gets a CLI-pipe recipe instead, because it speaks
no MCP. Every client wants a different shape: Zed wants `context_servers`, Copilot wants `servers`, and Codex
wants a TOML table.

The server exposes 22 tools in 9 groups: design, cost, validate, analyze, export, session, review, compliance
and plan. Full matrix in [docs/integrations.md](docs/integrations.md).

## Nine offline commands grade, scan and compare a spec

`lint` runs 10 anti-pattern checks. `score` grades 5 dimensions. `analyze` reports blast radius and single
points of failure. `policy` enforces policy-as-code with 9 built-in rules. `security` scans the spec and the
exported HCL. `drift` compares a design against a `tfstate`, and `--remediate` turns the gap into a cost,
compliance and plan preview.

`review`, `compliance` and `plan` are above. See [docs/cli-reference.md](docs/cli-reference.md).

## Python API

```python
from cloudwright import ArchSpec
from cloudwright.cost import CostEngine
from cloudwright.validator import Validator
from cloudwright.exporter import export_spec

spec = ArchSpec.from_file("spec.yaml")
priced = CostEngine().estimate(spec, workload_profile="medium")
findings = Validator().validate(spec, compliance=["hipaa", "pci-dss"])
hcl = export_spec(spec, "terraform", output_dir="./infra")
```

## v1.8.0 rebuilt the canvas and stopped a mid-stream double bill

- **One token set and a dark theme.** The theme follows your operating system until you pick a side.
- **Every text colour clears the 4.5:1 contrast floor.** 29 sites did not.
- **It works on a phone.** Below 900px the layout becomes a two-pane switch, and the nine tabs scroll.
- **A mid-stream error no longer bills twice.** The old fallback ran a second generation over the first.
- **A real `tablist` with arrow-key roving focus**, a live region for progress, `Cmd/Ctrl+K` for the composer.
- **Panel results survive a tab switch.** The Export tab now offers all thirteen formats.

Earlier releases added control-ID mapping and `plan` (v1.5.0), the self-correcting architect and OSCAL (v1.6.0), and `cloudwright integrate` (v1.7.0). Full history in [CHANGELOG.md](CHANGELOG.md).

## Compatibility

- Python 3.12+
- Models: Anthropic (Claude Sonnet, Haiku) and OpenAI (GPT-5+ family), auto-detected from env.
- Clouds: AWS, GCP, Azure, Databricks. 114 service keys total.
- Install variants: `cloudwright-ai[cli]`, `cloudwright-ai[web]`, `cloudwright-ai-mcp`.

## Contributing, license, changelog

- Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- License: MIT, see [LICENSE](LICENSE)
- Full release history: [CHANGELOG.md](CHANGELOG.md)
