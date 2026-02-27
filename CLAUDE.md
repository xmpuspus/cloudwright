# Cloudwright

Architecture intelligence tool for cloud engineers. Python monorepo with core library, CLI, and web UI.

## Project Structure

- `packages/core/` — `pip install cloudwright` — ArchSpec models, LLM-powered architect, catalog, cost engine, exporters
- `packages/cli/` — `pip install cloudwright[cli]` — Typer CLI with Rich formatting
- `packages/web/` — `pip install cloudwright[web]` — FastAPI + React web UI
- `catalog/` — Service catalog JSON data (compute, database, storage, networking per provider)

## Core Concepts

- **ArchSpec** (`spec.py`) — the central data format. Everything flows through it: design generates it, diagrams render it, cost engine prices it, exporters turn it into Terraform
- **Architect** (`architect.py`) — LLM-powered design from natural language. Multi-turn conversation
- **Catalog** (`catalog.py`) — SQLite service catalog with instance specs, pricing, cross-cloud equivalences
- **CostEngine** (`cost.py`) — prices each component in an ArchSpec from catalog data
- **Validator** (`validator.py`) — compliance checks (HIPAA, PCI-DSS, SOC 2, FedRAMP, GDPR, Well-Architected)
- **Differ** (`differ.py`) — structured diff between two ArchSpecs
- **Exporters** (`exporter/`) — Terraform, CloudFormation, Mermaid, CycloneDX SBOM, OWASP AIBOM

## Tech Stack

- Python 3.12+, Pydantic v2, ruff
- Dual LLM: Anthropic (Haiku + Sonnet) or OpenAI (GPT-5 mini + GPT-5.2)
- SQLite for catalog (ships with package)
- Typer + Rich for CLI
- FastAPI + React for web UI
- YAML as human-facing spec format

## Development

```bash
pip install -e packages/core
pip install -e packages/cli
pip install -e packages/web
pytest packages/core/tests/
ruff check packages/
```

## Key Commands

```bash
cloudwright design "3-tier web app on AWS"
cloudwright cost spec.yaml
cloudwright validate spec.yaml --compliance hipaa
cloudwright export spec.yaml --format terraform -o ./infra
cloudwright diff v1.yaml v2.yaml
cloudwright catalog search "4 vcpu 16gb"
cloudwright chat
```
