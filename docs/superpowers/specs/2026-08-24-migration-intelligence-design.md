# Migration Intelligence and Assurance Design

## Product decision

Cloudwright will add an industry-neutral migration intelligence and assurance subsystem. It will turn a discovered estate and proposed target into a dependency-aware transition plan. It will also calculate migration economics, define acceptance gates, and evaluate evidence after cutover.

The first proof project is a Philippine telecommunications migration. Telecommunications terms, controls, and thresholds will live in an external domain pack. They will not appear in the core migration types or algorithms.

The product stays read-only. It may describe and check work that migration tools, vendors, or operators did. It never copies production data, applies infrastructure, redirects traffic, or executes a cutover.

## Goals

- Show infrastructure, data, applications, platforms, facilities, and business services in one estate model.
- Map source assets to target assets using standard migration dispositions.
- Order migration actions from declared dependencies.
- Calculate one-time, dual-run, recurring, and decommissioning economics.
- Define machine-readable operational, data, financial, security, compliance, resilience, and decommissioning gates.
- Evaluate recorded evidence and block closure when evidence is missing or outside its threshold.
- Load industry requirements from external YAML packs.
- Expose the same deterministic behavior through Python, CLI, HTTP API, and web UI.
- Ship a complete PH telco proof project and a non-telco fixture.
- Keep every migration operation offline and free of model calls.

## Non-goals

- Packet or network-flow discovery.
- VM, database, object, or file replication.
- Infrastructure apply, traffic switching, or network orchestration.
- A billing system, mobile core, OSS, BSS, CMDB, or migration execution engine.
- Live operator certification without operator-owned data and systems.
- Automatic invention of missing evidence.

## Architecture

The subsystem has five layers:

1. `migration.models` defines the portable contract.
2. `migration.packs` loads and validates optional industry packs.
3. `migration.planner` validates mappings, orders waves, and calculates economics.
4. `migration.evidence` evaluates observations against acceptance criteria.
5. CLI, API, and web adapters serialize the same core results.

No adapter has planning or evaluation rules. The core package stays the single behavior owner.

## Portable model

### EstateSpec

An estate has assets and directed dependencies.

Each `EstateAsset` has:

- Stable ID and name.
- Kind: `infrastructure`, `application`, `data`, `platform`, `network`, `facility`, `business_service`, or `other`.
- Environment, provider, location, owner, criticality, and lifecycle.
- Data classes and tags.
- Current monthly cost.
- Free-form attributes for importer-specific facts.
- Discovery provenance records with source, observation time, and confidence.

Each dependency states that one asset depends on another and records its kind, criticality, and description.

### TargetSpec

A target has target assets plus `TargetMapping` records. A mapping connects one source asset to zero or more target assets and declares:

- Migration disposition: `retain`, `retire`, `rehost`, `relocate`, `replatform`, `refactor`, `repurchase`, or `replace`.
- Strategy and responsible owner.
- Expected downtime and optional wave hint.
- Rollback procedure.
- One-time implementation cost.
- Target monthly cost.
- Dual-run duration.
- Decommission credit.

Retired assets may have no target. Every other non-retained source asset must map to at least one existing target asset.

### TransitionSpec

The planner produces ordered `MigrationWave` records. Each wave has actions, prerequisites, rollback procedures, and gate IDs. A transition also has planning warnings, unresolved assets, and a `MigrationEconomics` summary.

Dependency direction is explicit: `source` depends on `target`, so the target dependency migrates first. If the target will be retired, its moving consumers become retirement prerequisites and cut over first. Cycles are rejected with a readable path because silently choosing an order would make the plan unsafe.

Wave hints may postpone an action but may not place it before a dependency.

### AssurancePlan

An acceptance criterion has:

- Stable ID and name.
- Category.
- Metric name.
- Comparator: `eq`, `gte`, `lte`, `zero`, or `true`.
- Target value and unit.
- Blocking flag.
- Needed evidence source.
- Optional control references.
- The wave that consumes it.

The planner always creates a generic rollback criterion for each wave. A selected domain pack adds requirements by matching asset kinds, data classes, and tags.

### EvidencePack

An observation links to one criterion and records a value, source, observation time, and notes. The evaluator returns one result per criterion, including missing observations. A blocking failure prevents closure. The evaluator rejects unknown criterion IDs.

## Domain packs

Domain packs are packaged YAML files under `cloudwright/data/migration_packs/`. A pack has metadata, source references, and criterion templates.

Matcher fields are lists of asset kinds, data classes, or tags. A template is instantiated once when any migrated source asset matches it. Stable IDs prevent duplicate gates.

The first `ph_telco` pack has:

- Subscriber and SIM record reconciliation.
- Activation and deactivation journeys.
- Prepaid balance and billing reconciliation.
- CDR completeness.
- Mobile-number-porting duration and cutover outage.
- Call, SMS, and data-session journeys.
- Privacy-impact assessment and authorized-access evidence.
- Backup, restore, and regional failover.
- Source-traffic and source-write closure checks.

The pack cites Philippine primary sources but does not claim legal certification.

## Economics

The migration economics summary reports:

- Current monthly run cost.
- Target monthly run cost.
- Monthly delta.
- One-time implementation cost.
- Dual-run cost.
- Decommission credit.
- Net migration cost.
- Payback months when recurring savings are positive.

Costs come from explicit mapping and estate values. The migration engine will not invent prices. Cloudwright's existing architecture cost engine can supply target figures upstream. Migration economics stay valid for on-premises, colocation, licensing, connectivity, and labor values that other importers supply.

## CLI

`cloudwright migrate` is a Typer sub-application with:

- `packs`: list available domain packs.
- `plan PROJECT`: build and print or write a migration assessment.
- `verify PROJECT EVIDENCE`: rebuild the assessment, evaluate evidence, and return a non-zero exit when blocking criteria fail.
- `demo`: run the packaged PH telco project and evidence end to end.

Global `--json` continues to use the existing success envelope. Human output uses concise summary, wave, economics, and gate tables.

## HTTP API

- `GET /api/migration/packs`
- `POST /api/migration/plan`
- `POST /api/migration/verify`
- `GET /api/migration/demo`

Request bodies use the core Pydantic models. Existing body-size, request-ID, rate-limit, authentication, and error middleware stay in force.

## Web UI

The workspace gains a `migration` tab. The first version is a deterministic proof-project view rather than an editor.

The panel loads `/api/migration/demo` and presents:

- Project outcome and closure status.
- Source, target, wave, and gate counts.
- Migration economics.
- Ordered wave cards with action and rollback summaries.
- Acceptance results grouped by category.
- Clear distinction between passed, failed, and missing evidence.

The panel uses generic migration labels. `PH telecommunications` appears only as the selected proof project.

## Proof projects

### PH telco

The packaged project shows a hybrid migration of CRM, billing, charging, subscriber records, CDR analytics, and observability. It moves them from on-premises facilities to a mixed local and regional target. It includes realistic dependency ordering, migration costs, and passing evidence.

### Manufacturing

A smaller manufacturing ERP and plant-data project runs through the same planner without a domain pack. Its test proves that the core has no telecommunications dependency.

## Error handling

- Invalid dependency references fail model validation.
- Dependency cycles fail planning and name the affected assets.
- Missing source mappings appear as unresolved assets and block a complete plan.
- Invalid pack files name the file and help users find the validation error.
- Missing observations create explicit failed results.
- Unknown observation criterion IDs fail evaluation.
- CLI and API adapters use existing Cloudwright error envelopes.

## Testing

- Model round-trip and validation tests.
- Pack loading, matching, deduplication, and packaging tests.
- Planner dependency order, wave hints, cycle, unresolved mapping, and economics tests.
- Evidence comparator, missing evidence, unknown criterion, and closure tests.
- PH telco end-to-end fixture test.
- Manufacturing end-to-end fixture test.
- CLI human and JSON tests.
- API contract tests.
- Frontend TypeScript build and browser interaction checks.
- Full package tests and Ruff checks using repository CI parity.

## Documentation and demos

- Root README introduces the migration contract and embeds the new web GIF.
- `docs/migrations.md` documents schemas, commands, packs, boundaries, and extension points.
- CLI and package READMEs include the new command surface.
- CHANGELOG records the work under Unreleased.
- A Playwright recording script produces the web migration GIF from the mock server.
- A VHS tape produces a CLI migration GIF when VHS is available.
- Inspect generated GIF dimensions, frame count, and representative frames.

## Acceptance criteria

- The PH telco proof project plans and checks evidence without a model or network access.
- At least one missing or failed blocking observation changes closure to blocked.
- Schedule each moving dependency before its consumer, and retire a dependency after its moving consumers.
- Reject a consumer with the `retain` disposition when any direct or transitive dependency changes.
- The manufacturing fixture completes using the same API with no telco pack.
- CLI JSON is stable and machine-readable.
- The API, MCP tools, and web panel return the same assessment produced by the core.
- The served static bundle has the migration panel.
- README, detailed docs, CLI reference, package READMEs, CHANGELOG, and GIF assets agree with implemented behavior.
- Relevant package tests, frontend build, Ruff, and demo verification pass in the current session.
