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
  core/     cloudwright-ai          Core library (models, architect, catalog, exporters)
  cli/      cloudwright-ai-cli     Typer CLI with Rich formatting
  web/      cloudwright-ai-web     FastAPI backend + React frontend
catalog/                     Service catalog JSON source data
```

## Pull Requests

- Create a feature branch from `main`
- Write tests for new functionality
- Run `ruff check` and `pytest` before submitting
- Keep PRs focused on a single change
- Update CHANGELOG.md for user-facing changes

## Architecture

Everything flows through `ArchSpec` — the central Pydantic model. The design pipeline:

1. User describes architecture in natural language
2. `Architect` calls LLM to generate an `ArchSpec`
3. `CostEngine` prices it from `Catalog` data
4. `Validator` checks compliance
5. Exporters turn it into Terraform, CloudFormation, diagrams

When adding a new exporter or service, update both the exporter module and the catalog data.
