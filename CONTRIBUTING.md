# Contributing to Cloudwright

## Development Setup

```bash
git clone https://github.com/xmpuspus/cloudwright.git
cd cloudwright
pip install -e packages/core -e packages/cli -e packages/web
pip install pytest pytest-timeout ruff
```

## Running Tests

```bash
# All tests
pytest

# Core only
pytest packages/core/tests/ -x -q

# Web API tests
pytest packages/web/tests/ -x -q

# CLI tests
pytest packages/cli/tests/ -x -q

# MCP tests
pytest packages/mcp/tests/ -x -q

# Frontend unit tests (requires npm install in packages/web/frontend/)
cd packages/web/frontend && npx vitest run

# With coverage
pytest --cov=cloudwright --cov-report=term-missing
```

## Linting

```bash
ruff check packages/
ruff format packages/
```

## Project Structure

```
packages/
  core/     cloudwright         Core library
    cloudwright/
      prompts.py              Prompt constants and service catalogs
      session.py              ConversationSession (multi-turn chat)
      designer.py             Architect (single-shot design + template matching)
      parsing.py              JSON extraction and ArchSpec parsing
      spec.py                 ArchSpec model and related types
      cost.py                 Cost engine
      validator.py            Compliance validation
      security.py             Security scanner
      differ.py               Spec diffing
      linter.py               Anti-pattern detection
      session_store.py        File-based session persistence
      exporter/               12 export formats
        terraform/            Per-provider HCL generation (aws.py, gcp.py, azure.py, databricks.py)
      catalog/                Service catalog and pricing
  cli/      cloudwright-cli     Typer CLI with Rich formatting
    cloudwright_cli/
      commands/
        chat.py               Entry point (arg parsing)
        chat_ui.py            Rich Live terminal UI
        chat_session.py       Session lifecycle
        chat_streaming.py     Stream consumer
      decorators.py           Command output/error wrapper
  web/      cloudwright-web     FastAPI backend + React frontend
    cloudwright_web/
      app.py                  App factory (create_app)
      middleware.py           Rate limiter, path guard, API key auth
      singletons.py           Thread-safe service factories
      streaming.py            Shared SSE helper
      routers/                Per-domain endpoint modules
    frontend/                 React + Vite + Zustand
  mcp/      cloudwright-mcp     MCP server bridge
```

## Where to Add Things

- **New prompts or service keys**: `packages/core/cloudwright/prompts.py`
- **New cloud provider (terraform)**: `packages/core/cloudwright/exporter/terraform/{provider}.py`
- **New export format**: `packages/core/cloudwright/exporter/{format}.py` + register in `__init__.py`
- **New web endpoint**: `packages/web/cloudwright_web/routers/{domain}.py` + mount in `app.py`
- **New CLI command**: `packages/cli/cloudwright_cli/commands/{cmd}.py` + register in `main.py`

## Pull Requests

- Create a feature branch from `main`
- Write tests for new functionality
- Run `ruff check` and `pytest` before submitting
- Keep PRs focused on a single change
- Update CHANGELOG.md for user-facing changes

## Architecture

Everything flows through `ArchSpec` — the central Pydantic model. The design pipeline:

1. User describes architecture in natural language
2. `Architect` (designer.py) calls LLM to generate an `ArchSpec`
3. `CostEngine` prices it from `Catalog` data
4. `Validator` checks compliance
5. Exporters turn it into Terraform, CloudFormation, diagrams

`ConversationSession` (session.py) wraps multi-turn conversations with history tracking,
streaming, cost tracking, and session persistence.
