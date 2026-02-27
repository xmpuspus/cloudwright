# cloudwright (core)

Core library for architecture intelligence. All business logic lives here.

## Module Map

- `spec.py` — ArchSpec Pydantic models. The central data format
- `architect.py` — LLM-powered architecture design. Uses llm/ for AI calls
- `catalog.py` — SQLite service catalog. Queries instance specs and pricing
- `cost.py` — Cost engine. Prices ArchSpec components from catalog data
- `validator.py` — Compliance validation (HIPAA, PCI-DSS, SOC 2, FedRAMP, GDPR, Well-Architected)
- `differ.py` — ArchSpec diff engine
- `llm/` — Multi-provider LLM abstraction (Anthropic, OpenAI)
- `exporter/` — Terraform, CloudFormation, Mermaid, SBOM, AIBOM
- `providers/` — Service definitions and cross-cloud equivalences

## Conventions

- All public API exposed via `__init__.py` with lazy imports
- ArchSpec is the universal interchange format — every module consumes or produces it
- Catalog uses SQLite shipped as `data/catalog.db`
- LLM provider auto-detected from env vars
- No external DB dependencies — everything is local
