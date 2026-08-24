# Migration Intelligence and Assurance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an industry-neutral migration planning and evidence engine. Prove it with a PH telco pack and a manufacturing fixture. Expose it through Python, CLI, API, web UI, documentation, and recorded demos.

**Architecture:** Focused modules under `cloudwright/migration/` own models, domain-pack loading, planning, and evidence evaluation. CLI, HTTP, and React layers only adapt those deterministic interfaces. PH telco requirements stay in packaged YAML and example data.

**Tech Stack:** Python 3.12, Pydantic 2, PyYAML, Typer, Rich, FastAPI, React 18, TypeScript, Vite, Playwright, ffmpeg, VHS when available.

**Spec:** `docs/superpowers/specs/2026-08-24-migration-intelligence-design.md`

## Global Constraints

- Core types and algorithms must not contain telecommunications field names.
- Keep all planning and checking operations read-only and offline.
- Every production behavior starts with a failing test.
- Preserve the existing untracked `AGENTS.md` and catalog WAL/SHM files.
- Do not commit, push, publish, tag, or release without separate authorization.
- Run package test directories separately with API keys unset.
- Rebuild `packages/web/cloudwright_web/static/` after the frontend build.
- Check generated GIFs visually and inspect their file shape before completion.

## File map

- `packages/core/cloudwright/migration/models.py`: portable migration contracts.
- `packages/core/cloudwright/migration/packs.py`: packaged YAML pack loading and criterion matching.
- `packages/core/cloudwright/migration/planner.py`: mapping validation, dependency ordering, waves, and economics.
- `packages/core/cloudwright/migration/evidence.py`: criterion evaluation and closure decision.
- `packages/core/cloudwright/migration/__init__.py`: public migration API.
- `packages/core/cloudwright/data/migration_packs/ph_telco.yaml`: PH proof requirements only.
- `examples/migrations/*.yaml`: PH telco and manufacturing projects plus evidence.
- `packages/cli/cloudwright_cli/commands/migrate_cmd.py`: `migrate` sub-application.
- `packages/web/cloudwright_web/routers/migration.py`: migration HTTP endpoints.
- `packages/web/frontend/src/components/MigrationPanel.tsx`: proof-project UI.
- `scripts/record_migration_demo.py`: browser recording.
- `examples/tapes/cloudwright-migration.tape`: CLI recording.

### Task 1: Portable migration models

**Files:**
- Create: `packages/core/cloudwright/migration/models.py`
- Create: `packages/core/cloudwright/migration/__init__.py`
- Change: `packages/core/cloudwright/__init__.py`
- Test: `packages/core/tests/test_migration_models.py`

**Interfaces:**
- Produces: `MigrationProject.from_file(path)`, `MigrationAssessment.to_yaml()`, `EvidenceInput.from_file(path)`, and the model classes named in the design.

- [ ] Write model round-trip tests covering assets, dependencies, mappings, criteria, observations, and YAML files.
- [ ] Run `env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY python -m pytest packages/core/tests/test_migration_models.py -q -p no:cacheprovider --timeout=60` and confirm imports fail because the migration package does not exist.
- [ ] Implement the Pydantic models, enum literals, validators, and YAML helpers with no planning behavior.
- [ ] Export the stable public types from `cloudwright.migration` and lazy public entry points from `cloudwright`.
- [ ] Re-run the focused test and confirm it passes.

### Task 2: External domain-pack loader

**Files:**
- Create: `packages/core/cloudwright/migration/packs.py`
- Create: `packages/core/cloudwright/data/migration_packs/ph_telco.yaml`
- Change: `packages/core/pyproject.toml`
- Test: `packages/core/tests/test_migration_packs.py`
- Test: `packages/core/tests/test_packaging.py`

**Interfaces:**
- Consumes: `EstateAsset`, `AcceptanceCriterion`.
- Produces: `DomainPack`, `list_packs() -> list[PackSummary]`, `load_pack(name) -> DomainPack`, `criteria_for(pack, assets) -> list[AcceptanceCriterion]`.

- [ ] Write failing tests for pack listing, loading, matcher behavior, criterion deduplication, missing packs, and packaged data presence.
- [ ] Run the focused pack and packaging tests and confirm the expected missing-module or missing-data failures.
- [ ] Implement resource-based YAML loading with Pydantic validation and deterministic criterion instantiation.
- [ ] Add the migration-pack glob to Hatch artifacts.
- [ ] Add the PH telco rules and primary-source URLs only to the YAML pack.
- [ ] Re-run the focused tests and confirm they pass.

### Task 3: Dependency-aware planner and economics

**Files:**
- Create: `packages/core/cloudwright/migration/planner.py`
- Test: `packages/core/tests/test_migration_planner.py`

**Interfaces:**
- Consumes: `MigrationProject`, optional pack name.
- Produces: `MigrationPlanner.plan(project, pack_name=None) -> MigrationAssessment`.

- [ ] Write failing tests for dependency order, shared waves, postponed hints, cycles, retired assets, and unresolved mappings.
- [ ] Add failing tests for illegal early hints and cost totals.
- [ ] Run the focused planner test and confirm the planner import fails.
- [ ] Implement reference validation, topological levels, mapping actions, wave construction, generic criteria, optional pack criteria, warnings, and economics.
- [ ] Make sure a complete plan is false when unresolved mappings exist.
- [ ] Re-run the planner tests and confirm they pass.

### Task 4: Evidence evaluation

**Files:**
- Create: `packages/core/cloudwright/migration/evidence.py`
- Test: `packages/core/tests/test_migration_evidence.py`

**Interfaces:**
- Consumes: `MigrationAssessment.assurance`, `EvidenceInput`.
- Produces: `EvidenceEvaluator.evaluate(assessment, evidence) -> EvidencePack`.

- [ ] Write failing tests for `eq`, `gte`, `lte`, `zero`, `true`, missing observations, non-blocking failures, and unknown criterion IDs.
- [ ] Run the focused evidence test and confirm the evaluator import fails.
- [ ] Implement typed comparison, result creation, blocking counts, and closure status.
- [ ] Re-run the evidence tests and confirm they pass.

### Task 5: End-to-end proof fixtures

**Files:**
- Create: `examples/migrations/ph-telco-project.yaml`
- Create: `examples/migrations/ph-telco-evidence.yaml`
- Create: `examples/migrations/manufacturing-erp-project.yaml`
- Create: `examples/migrations/manufacturing-erp-evidence.yaml`
- Test: `packages/core/tests/test_migration_e2e.py`

**Interfaces:**
- Consumes: public planner and evaluator APIs.
- Produces: two portable example projects and checked evidence files.

- [ ] Write failing end-to-end tests that load both fixture families, plan them, evaluate evidence, and assert closure.
- [ ] Add a mutation test. Remove one PH blocking observation and check that it blocks closure.
- [ ] Run the focused test and confirm fixture-not-found failures.
- [ ] Add the PH telco fixture with BSS/OSS, subscriber data, billing, CDR, hybrid placement, costs, and ordered dependencies.
- [ ] Add the manufacturing ERP and plant-data fixture without a domain pack.
- [ ] Add passing evidence for both projects and re-run the focused test.

### Task 6: CLI migration sub-application

**Files:**
- Create: `packages/cli/cloudwright_cli/commands/migrate_cmd.py`
- Change: `packages/cli/cloudwright_cli/main.py`
- Test: `packages/cli/tests/test_migrate_cmd.py`

**Interfaces:**
- Produces: `cloudwright migrate packs|plan|verify|demo` with existing global JSON envelope support.

- [ ] Write failing CLI tests for help, packs, human plan, JSON plan, successful checks, blocked checks, the demo, and output files.
- [ ] Run the focused CLI test and confirm `migrate` is not registered.
- [ ] Implement the Typer sub-application using only public core APIs and existing error/output helpers.
- [ ] Render summary, economics, wave, and gate tables without duplicating planner behavior.
- [ ] Re-run the focused CLI tests and confirm they pass.

### Task 7: HTTP migration API

**Files:**
- Create: `packages/web/cloudwright_web/routers/migration.py`
- Change: `packages/web/cloudwright_web/routers/__init__.py`
- Change: `packages/web/cloudwright_web/app.py`
- Test: `packages/web/tests/test_migration_api.py`

**Interfaces:**
- Produces: `GET /api/migration/packs`, `POST /api/migration/plan`, `POST /api/migration/verify`, `GET /api/migration/demo`.

- [ ] Write failing API tests for all endpoints, invalid input, and blocked evidence.
- [ ] Run the focused API test and confirm 404 responses.
- [ ] Implement request models and thin endpoint adapters.
- [ ] Load proof fixtures through paths derived from the repository in development and packaged core resources in installed builds.
- [ ] Re-run the focused API tests and confirm they pass.

### Task 8: Web migration experience

**Files:**
- Create: `packages/web/frontend/src/components/MigrationPanel.tsx`
- Change: `packages/web/frontend/src/App.tsx`
- Change: `packages/web/frontend/src/styles.css`
- Change: `packages/web/tests/test_canvas_contract.py`
- Change: `packages/web/tests/test_static_bundle.py`

**Interfaces:**
- Consumes: `GET /api/migration/demo`.
- Produces: accessible `migration` tab with summary, economics, wave, and evidence views.

- [ ] Add failing source-contract tests for the migration tab, endpoint, accessible outcome text, and generic copy.
- [ ] Run those tests and confirm the expected source assertions fail.
- [ ] Implement `MigrationPanel` with loading, retry, error, plan, and evidence states.
- [ ] Add the tab and lazy panel mounting to `App.tsx`.
- [ ] Add responsive styles using existing tokens, badges, cards, and typography.
- [ ] Run the source-contract tests.
- [ ] Run `npm run build`, replace the served static directory with `frontend/dist`, and run the static-bundle test.

### Task 9: Documentation and changelog

**Files:**
- Create: `docs/migrations.md`
- Change: `README.md`
- Change: `CHANGELOG.md`
- Change: `docs/cli-reference.md`
- Change: `packages/core/README.md`
- Change: `packages/cli/README.md`

**Interfaces:**
- Documents only checked command names, fields, limits, and examples.

- [ ] Add migration documentation with model diagrams, file examples, extension guidance, and read-only boundaries.
- [ ] Add README positioning, quickstart, PH proof explanation, and GIF references.
- [ ] Add the CLI commands to every relevant command inventory.
- [ ] Add an Unreleased changelog entry without changing package versions.
- [ ] Search reader-facing files for stale command counts and migration claims, then correct only affected text.

### Task 10: Reproducible GIF demos

**Files:**
- Create: `scripts/record_migration_demo.py`
- Create: `examples/tapes/cloudwright-migration.tape`
- Create: `examples/cloudwright-migration-web-demo.gif`
- Create when VHS is available: `examples/cloudwright-migration-cli-demo.gif`

**Interfaces:**
- Web recorder drives the built static UI against `scripts/_serve_with_mock_llm.py`.
- CLI tape runs the packaged offline example through `cloudwright migrate demo`.

- [ ] Write the browser script to open the migration tab and run the proof project.
- [ ] Move through waves and evidence, and record at 1280 by 720.
- [ ] Start the mock server and run the recorder. Check that the GIF is not empty.
- [ ] Add and run the VHS tape when the binary is available.
- [ ] Otherwise, record the CLI with a local terminal capture method. Keep the recording offline.
- [ ] Inspect dimensions, frame count, duration, and representative PNG frames for each GIF.
- [ ] Add accurate alt text and reproduction commands to documentation.

### Task 11: Full verification and scope audit

**Files:**
- Inspect all changed paths.

- [ ] Run Ruff check and format check on `packages/` plus new scripts.
- [ ] Run core, CLI, web, and MCP tests separately with API keys unset and repository timeout settings.
- [ ] Run the frontend TypeScript/Vite build and sync the served static bundle.
- [ ] Run the PH telco CLI demo in human and JSON modes.
- [ ] Run verification with deliberately missing blocking evidence and confirm a blocked result and non-zero CLI exit.
- [ ] Run package build or packaging tests to prove the YAML pack ships.
- [ ] Re-read the design acceptance criteria and map each one to recorded evidence.
- [ ] Inspect `git status --short` and `git diff --check`.
- [ ] Preserve all pre-existing untracked files.
