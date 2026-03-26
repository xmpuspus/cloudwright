# Cloudwright Full Overhaul Design

**Date:** 2026-03-26
**Version target:** v0.5.0 (non-breaking) then v1.0.0 (breaking)
**Approach:** Risk-First — correctness/security fixes and high-ROI refactors first, full structural overhaul second

## Context

Cloudwright is a cloud architecture intelligence platform (v0.4.0) organized as a 4-package monorepo: core (~6,900 LOC), CLI (~2,000 LOC), web (~720 LOC backend + ~1,500 LOC frontend), MCP (~180 LOC). The codebase has 1,347 tests (40.7% test-to-code ratio) and strong fundamentals, but accumulated structural debt across its rapid 21-day development sprint (165 commits).

### Audit findings (18 issues across 3 severity tiers)

**High priority:**
1. `architect.py` god module (1,491 LOC — session + design + 1,100 LOC prompts + helpers)
2. Monolithic web backend (720 LOC, 19 endpoints in single file)
3. Frontend state explosion (App.tsx manages everything via useState)
4. Zero frontend unit tests (only Playwright E2E)
5. MCP session impermanence (in-memory dict, lost on restart)

**Medium priority:**
6. Cost tracking hardcoded (model detection via string matching on module name)
7. Terraform exporter monolith (1,161 LOC, 4 providers in one file)
8. CLI chat command mixes UI/session/streaming in ~400 LOC
9. No shared streaming abstraction (SSE reimplemented per endpoint)
10. Error hints never pruned (grow unbounded in session)
11. Connection validation missing (can reference non-existent component IDs)
12. Config values not sanitized (passed directly to Terraform exporter)
13. Template matching is fuzzy (keyword-based, no confidence score)

**Low priority:**
14. TS types defined only in App.tsx
15. No API client library (raw fetch)
16. CLI command boilerplate (repeated try/except per command)
17. Naive history trimming
18. Spec cache uses simple TTL

---

## Phase 1: v0.5.0 — Correctness, Security, and High-ROI Refactors

All changes in this phase are non-breaking. No public API signatures change. Existing imports continue to work.

### 1.1 Prompt Extraction

**Problem:** `architect.py` is 1,491 LOC. ~1,100 LOC are pure constants (system prompts, service catalogs, default configs).

**Solution:** Extract all prompt constants into `cloudwright/prompts.py`.

**What moves:**
- `_CHAT_SYSTEM`, `_DESIGN_SYSTEM`, `_MODIFY_SYSTEM`, `_IMPORT_SYSTEM` (4 system prompt strings)
- `_PROVIDER_SERVICES` (4 dicts mapping providers to service sets, ~100 services total)
- `_DEFAULT_CONNECTION_PROTOCOLS` (tier-pair → protocol/port tuples)
- `_CLOUD_KEYWORDS` (set of cloud-related keywords for ambiguity detection)
- `_DEFAULT_INSTANCE_TYPES` (3-tier lookup per provider)
- Compliance control templates (HIPAA, PCI-DSS, SOC2, GDPR, FedRAMP prompt fragments)
- Service keys list (115+ services across AWS/GCP/Azure/Databricks)

**Result:** `architect.py` drops to ~391 LOC. `prompts.py` becomes ~1,100 LOC of pure data. All imports are internal — nothing in the public API changes.

**New file:** `packages/core/cloudwright/prompts.py`

**Tests:** Existing tests pass unchanged (they import `Architect`/`ConversationSession`, not the constants directly). Add one test verifying all expected constants exist in `prompts.py`.

### 1.2 Connection Validation

**Problem:** `ArchSpec` allows connections referencing non-existent component IDs. Exporters then generate invalid Terraform/CloudFormation that references undefined resources.

**Solution:** Add a Pydantic `model_validator(mode='after')` on `ArchSpec` that validates all connection `source` and `target` values exist in the component ID set.

**Where:** `packages/core/cloudwright/spec.py`, `ArchSpec` class.

**Behavior:**
- Collects all component IDs into a set
- Checks every `Connection.source` and `Connection.target` against that set
- On invalid reference: raises `ValueError` with the bad ID and the list of valid IDs
- Fires on construction and deserialization (`from_yaml`, `from_file`)
- `_parse_arch_spec` in `architect.py` constructs `ArchSpec` — validation fires automatically

**Tests:** Add tests for valid connections (pass), invalid source (fail), invalid target (fail), empty connections (pass).

### 1.3 Config Value Sanitization

**Problem:** Component `config` dict values from LLM output pass directly to Terraform/CloudFormation exporters. Shell metacharacters in values could produce dangerous IaC.

**Solution:** Add `validate_export_config(config: dict) -> None` in `packages/core/cloudwright/exporter/__init__.py`. Called by all exporters before generating output. Raises on invalid values (does not silently strip — rejection is safer than silent mutation).

**Rules:**
- String values: reject characters dangerous in HCL string interpolation (`;`, `|`, `&`, `` ` ``, `$()`, `${`)
- Raises `ValueError` on dangerous content with the specific field and value
- Numeric values: validate as `int` or `float`
- Boolean values: validate as `bool`
- Nested dicts: recursive validation
- Applied at export time only (preserves raw LLM output in `ArchSpec` for debugging/display)

**Tests:** Add tests for clean configs (pass), shell injection attempts (fail), nested dicts (recursive), numeric/boolean coercion.

### 1.4 Error Hint Pruning

**Problem:** `ConversationSession._error_hints` list grows unbounded. Every hint is sent to every subsequent LLM call, potentially causing cascading false corrections in long sessions.

**Solution:** Cap `_error_hints` to last 5 entries using a sliding window.

**Where:** `packages/core/cloudwright/architect.py`, in `ConversationSession` — wherever hints are appended, trim to last 5.

**Why 5:** Each hint is 1-2 sentences. 5 provides enough recent context without polluting the system prompt. Stale hints (>5 turns old) are more likely to mislead than help.

**Tests:** Add test that appending 10 hints results in only the last 5 being present. Verify hints appear in LLM system prompt.

### 1.5 MCP Session Persistence

**Problem:** MCP sessions are stored in an in-memory dict (`_sessions`). Process restart loses all sessions. CLI uses `SessionStore` for file-based persistence — inconsistent UX.

**Solution:** Replace in-memory storage with `SessionStore` from `cloudwright.session_store`.

**Where:** `packages/mcp/cloudwright_mcp/tools/session.py`

**Changes:**
- Initialize a module-level `SessionStore` (default path `~/.cloudwright/sessions/`)
- `chat_create_session()` → creates `ConversationSession`, calls `store.save(session_id, session)`
- `chat_send()` → loads session via `store.load()`, sends message, calls `store.save()` after
- `chat_list_sessions()` → delegates to `store.list_sessions()`
- `chat_delete_session()` → delegates to `store.delete()`
- Remove `_sessions` dict, `_session_created` dict, TTL cleanup logic, max session eviction
- Keep `threading.Lock` for concurrent access safety

**Tests:** Update `test_session_lifecycle.py` — verify sessions survive simulated "restart" (new SessionStore instance pointing at same directory).

### 1.6 Cost Tracking Fix

**Problem:** Model pricing detection uses string matching on the LLM module name (`"anthropic" in llm_module`). New models or class renames break pricing silently.

**Solution:** Add explicit `model_name` property and `pricing` dict to `BaseLLM`.

**Where:**
- `packages/core/cloudwright/llm/base.py` — add abstract properties:
  - `model_name: str` (e.g., `"claude-sonnet-4-6"`)
  - `pricing: dict[str, float]` (keys: `input_per_1k`, `output_per_1k`)
- `packages/core/cloudwright/llm/anthropic.py` — implement with actual model IDs and pricing
- `packages/core/cloudwright/llm/openai.py` — same
- `packages/core/cloudwright/architect.py` — replace `"anthropic" in type(self._llm).__module__` with `self._llm.pricing`

**Tests:** Verify pricing dict is accessible on both LLM implementations. Verify cost tracking uses LLM-provided pricing, not hardcoded.

### 1.7 Template Match Confidence

**Problem:** Template matching is keyword-based with no confidence signal. A partial keyword overlap can match the wrong template. Users have no way to know a template was used vs. a full LLM design.

**Solution:** Return a confidence score (0.0-1.0) from `_match_template_for_design()`.

**Where:** `packages/core/cloudwright/architect.py` (moves to `designer.py` in v1.0, but stays here for now)

**Scoring:** `matched_keywords / total_description_keywords` (normalized, stopwords excluded)

**Thresholds:**
- >= 0.7: use template directly (current behavior)
- 0.4-0.7: use template as seed, call LLM to refine/customize
- < 0.4: no match, full LLM design

**Metadata:** Score stored in `spec.metadata['template_confidence']` and `spec.metadata['template_name']` (if matched).

**Tests:** Add tests for high-confidence match (exact keywords), medium-confidence (partial), no match (unrelated description). Verify metadata populated.

---

## Phase 2: v1.0.0 — Full Structural Overhaul

Breaking changes allowed. Import paths change. Public APIs may be redesigned.

### 2.1 architect.py Decomposition

**Problem:** Even after prompt extraction (v0.5.0), `architect.py` has three distinct responsibilities: conversation management, one-shot design, and JSON parsing. These should be independent modules.

**New structure:**
```
packages/core/cloudwright/
  prompts.py              # Constants (from v0.5.0)
  session.py              # ConversationSession class (~500 LOC)
  designer.py             # Architect class + template matching (~200 LOC)
  parsing.py              # _parse_arch_spec, _extract_json, _enforce_connections (~300 LOC)
  architect.py            # Backward-compat shim (re-exports with deprecation warnings)
```

**Backward compatibility:** `architect.py` re-exports `ConversationSession` and `Architect` with `warnings.warn(DeprecationWarning)`. Removed in v1.1+.

**Migration path for users:**
```python
# Old (deprecated, works in v1.0)
from cloudwright.architect import ConversationSession, Architect

# New (v1.0+)
from cloudwright.session import ConversationSession
from cloudwright.designer import Architect
```

### 2.2 Web Backend Route Split

**Problem:** All 19 FastAPI endpoints live in a single 720 LOC `app.py`. No route-level isolation, testing, or organization.

**New structure:**
```
packages/web/cloudwright_web/
  app.py                  # App factory + middleware registration (~100 LOC)
  middleware.py            # Rate limiter, path traversal guard, API key auth
  singletons.py           # Thread-safe lazy factories for Architect, Catalog, CostEngine
  streaming.py            # Shared SSE helper (Section 2.5)
  routers/
    __init__.py           # Collects all routers
    design.py             # POST /api/design, /api/design/stream, /api/modify, /api/modify/stream
    cost.py               # POST /api/cost
    validate.py           # POST /api/validate
    export.py             # POST /api/export, /api/download
    chat.py               # POST /api/chat, /api/chat/stream
    catalog.py            # POST /api/catalog/search, /api/catalog/compare
    diagram.py            # POST /api/diagram
    health.py             # GET /api/health, /api/icons/{provider}/{service}.svg
```

**App factory pattern:**
```python
def create_app() -> FastAPI:
    app = FastAPI(title="Cloudwright", version="1.0.0")
    app.add_middleware(...)
    app.include_router(design.router, prefix="/api")
    app.include_router(cost.router, prefix="/api")
    # ... etc
    return app
```

**Tests:** Split `test_api.py` into per-router test files. Each router testable with its own `TestClient(create_test_app())`.

### 2.3 Frontend Rewrite

**Problem:** `App.tsx` manages all state via `useState`. No separation between data, UI state, and side effects. Components can't access state without prop drilling.

**State management with Zustand:**
```
packages/web/frontend/src/
  stores/
    useSpecStore.ts         # currentSpec, isLoading, error, setSpec, clearSpec
    useChatStore.ts         # messages[], streamingText, sessionId, sendMessage, loadSession
    useCostStore.ts         # costEstimate, comparison[], isCosting
    useValidationStore.ts   # validationResult, selectedFramework, isValidating
    useUIStore.ts           # activePanel, selectedNode, exportFormat, dialogStates
```

**Component architecture:**
```
  components/
    Layout/
      AppShell.tsx          # Top-level layout (sidebar + main + panels)
      Sidebar.tsx           # Navigation, session list
    ChatPanel/
      ChatPanel.tsx         # Container: message list + input
      MessageList.tsx       # Renders message history
      ChatInput.tsx         # Input + send button + streaming indicator
    SpecViewer/
      SpecViewer.tsx        # Architecture diagram + node details
      NodeDetail.tsx        # Selected component inspector
    CostPanel/
      CostPanel.tsx         # Cost breakdown table + comparison chart
    ValidationPanel/
      ValidationPanel.tsx   # Compliance results + framework selector
    ExportDialog/
      ExportDialog.tsx      # Format picker + download trigger
  lib/
    api.ts                  # Typed API client (all endpoints, SSE helpers, error handling)
    types.ts                # Shared TypeScript interfaces
```

**Key decisions:**
- Zustand over Redux: lighter, selector-based renders, built-in persist middleware
- No React Context for app state: Context re-renders entire subtree on change
- SSE consumption centralized in `api.ts` with typed event discriminators
- Types in `types.ts` mirror Pydantic models from core (manual for now, codegen later)

### 2.4 Frontend Test Infrastructure

**Problem:** ~14 TSX component files with zero unit tests. Only coverage is Playwright E2E.

**Setup:**
- Vitest (aligned with Vite build) + React Testing Library + `@testing-library/user-event`
- MSW (Mock Service Worker) for API mocking — intercepts `fetch`, no implementation coupling
- `vitest.config.ts` alongside `vite.config.ts`

**Coverage targets for v1.0:**
- Zustand stores: 100% (pure logic, no DOM)
- `api.ts` client: 100% (mock HTTP responses, verify request shapes)
- Components: happy-path render + key user interactions (click, type, select)
- Playwright E2E: unchanged (stays as integration safety net)

**Test naming:** `*.test.tsx` co-located with components (e.g., `ChatPanel.test.tsx` next to `ChatPanel.tsx`).

### 2.5 Shared Streaming Abstraction

**Problem:** Each streaming endpoint (design, modify, chat) reimplements SSE wire format, timeout handling, error serialization, and client disconnect detection.

**Solution:** `packages/web/cloudwright_web/streaming.py`

```python
@dataclass
class StreamEvent:
    event: str          # "token", "stage", "error", "done"
    data: str | dict    # Payload — strings sent as-is, dicts JSON-serialized

async def sse_stream(
    generator: AsyncIterator[StreamEvent],
    timeout: float = 120.0,
) -> EventSourceResponse:
    """Wraps any async generator into a well-formed SSE response.

    Handles: timeout enforcement via asyncio.wait_for, structured error
    serialization on exception, client disconnect detection via
    request.is_disconnected(), keep-alive pings every 15s of inactivity.
    """
```

**Router usage:**
```python
@router.post("/design/stream")
async def design_stream(req: DesignRequest):
    async def generate():
        yield StreamEvent("stage", "generating")
        spec = await run_design(req)
        yield StreamEvent("stage", "generated")
        yield StreamEvent("data", spec.model_dump())
        yield StreamEvent("done", "")
    return sse_stream(generate())
```

### 2.6 CLI Chat Decomposition

**Problem:** The `chat` command (~400 LOC) mixes Typer argument parsing, Rich Live terminal UI, session lifecycle management, subcommand dispatch, and stream consumption in a single function.

**New structure:**
```
packages/cli/cloudwright_cli/commands/
  chat.py                 # Typer command — arg parsing, dispatch to ui (~50 LOC)
  chat_ui.py              # Rich Live loop, input handling, subcommand routing (~150 LOC)
  chat_session.py         # Create/save/load/resume session lifecycle (~100 LOC)
  chat_streaming.py       # Stream consumer + Rich Live panel update (~80 LOC)
```

**Interaction:** `chat.py` parses args → creates session via `chat_session.py` → launches UI loop via `chat_ui.py` → streaming handled by `chat_streaming.py`.

### 2.7 Terraform Exporter Split

**Problem:** `terraform.py` (1,161 LOC) contains HCL generation for 4 cloud providers in a single file. Adding a provider means editing a 1,161-line file.

**New structure:**
```
packages/core/cloudwright/exporter/
  terraform/
    __init__.py           # TerraformExporter class — dispatches to provider modules
    common.py             # Shared: provider blocks, variable declarations, output exports, HCL utils
    aws.py                # AWS resource type → HCL resource mappings
    gcp.py                # GCP resource type → HCL resource mappings
    azure.py              # Azure resource type → HCL resource mappings
    databricks.py         # Databricks resource type → HCL resource mappings
```

**Each provider module exports:** `render_resource(component: Component, config: dict) -> str` returning HCL block text.

**Backward compat:** `exporter/__init__.py` still resolves `fmt="terraform"` to the new package. No external API change.

### 2.8 CLI Command Decorator

**Problem:** 20+ CLI commands each manually implement try/except, Console output, JSON envelope formatting, verbose/dry-run mode. ~10 lines of boilerplate per command.

**Solution:** `packages/cli/cloudwright_cli/decorators.py`

```python
def cloudwright_command(json_output: bool = True, dry_run: bool = False):
    """Decorator that wraps command functions with standard output handling.

    The decorated function returns a dict (success) or raises an exception (error).
    The decorator handles: JSON envelope wrapping, Rich console formatting,
    --verbose stack traces, --dry-run interception, exit codes.
    """
```

**Usage:**
```python
@app.command()
@cloudwright_command(json_output=True, dry_run=True)
def design(description: str, provider: str = "aws"):
    spec = architect.design(description, provider=provider)
    return spec.model_dump()
```

---

## Phase 3: Documentation Updates

All markdown files updated to reflect the structural changes in v0.5.0 and v1.0.

### 3.1 Root README.md (510 lines)

**Updates needed:**
- Update version references from v0.4.0 to current
- Update project structure section to reflect new module layout (`prompts.py`, `session.py`, `designer.py`, `parsing.py`)
- Update import examples if any reference `architect.py` directly
- Add section on v1.0 breaking changes (new import paths)
- Update architecture diagram/description if present
- Verify all CLI command examples still work
- Update feature list if new capabilities added (template confidence, connection validation)

### 3.2 CHANGELOG.md (360 lines)

**Updates needed:**
- Add v0.5.0 entry documenting:
  - Prompt extraction from architect.py
  - Connection validation on ArchSpec
  - Config value sanitization in exporters
  - Error hint sliding window (5 max)
  - MCP session persistence via SessionStore
  - Cost tracking: explicit model_name/pricing on BaseLLM
  - Template match confidence scores
- Add v1.0.0 entry documenting:
  - Breaking: new import paths (cloudwright.session, cloudwright.designer, cloudwright.parsing)
  - Web backend route split (app factory pattern)
  - Frontend rewrite (Zustand stores, component architecture)
  - Frontend test infrastructure (Vitest + RTL + MSW)
  - Shared SSE streaming abstraction
  - CLI chat decomposition
  - Terraform exporter split by provider
  - CLI command decorator
  - Documentation overhaul

### 3.3 CONTRIBUTING.md (67 lines)

**Updates needed:**
- Update project structure section with new module layout
- Add section on where to add new prompts (prompts.py)
- Add section on where to add new cloud providers (exporter/terraform/{provider}.py)
- Update testing commands if test file structure changes
- Add frontend testing instructions (Vitest)
- Add router-level testing guidance for web package

### 3.4 packages/core/README.md (511 lines)

**Updates needed:**
- Update module reference table (new files: prompts.py, session.py, designer.py, parsing.py)
- Update import examples to new paths
- Add deprecation notice for old `from cloudwright.architect import ...` paths
- Update architecture diagram showing module decomposition
- Document new validation behavior (connection validation)
- Document template confidence metadata
- Update API reference if ConversationSession/Architect signatures changed

### 3.5 packages/cli/README.md (24 lines)

**Updates needed:**
- Expand with more complete command reference
- Add session management examples (save/load)
- Document chat subcommands
- Add streaming examples

### 3.6 packages/web/README.md (21 lines)

**Updates needed:**
- Update endpoint reference (router-based organization)
- Add frontend development instructions (Vite dev server, Vitest)
- Document environment variables (CORS, API key, rate limiting)
- Add architecture overview (app factory, routers, stores)

### 3.7 packages/mcp/README.md (43 lines)

**Updates needed:**
- Document session persistence (sessions survive restarts)
- Remove TTL/max session references (no longer applicable)
- Update tool descriptions if signatures changed

### 3.8 docs/archspec.md (152 lines)

**Updates needed:**
- Document connection validation rules (source/target must reference valid component IDs)
- Document template confidence metadata fields
- Add config sanitization rules (what values are rejected in export)

### 3.9 .github/SECURITY.md (46 lines)

**Updates needed:**
- Add config sanitization as a security measure
- Add connection validation as an integrity measure
- Update supported versions table (add v0.5.0, v1.0.0)

### 3.10 skills/README.md (266 lines)

**Updates needed:**
- Update any references to architect.py module paths
- Update tool matrix if MCP tools changed
- Verify all skill examples still reference correct imports

### 3.11 Individual Skill Files (22 files)

**Updates needed (if any reference internal module paths):**
- `cloudwright-design.md` — update if it references architect.py internals
- `cloudwright-chat.md` — update if it references ConversationSession import path
- `cloudwright-export.md` — update if it references terraform exporter internals
- Other skill files: scan for hardcoded module paths and update

### 3.12 Benchmark Documentation

**Updates needed:**
- `benchmark/results/benchmark_report.md` — add v0.5.0 and v1.0 benchmark runs
- `benchmark/results/full_benchmark_report.md` — same
- Verify benchmark scripts still work with new module structure

---

## Success Criteria

### v0.5.0
- All 1,347 existing tests pass (zero regressions)
- `architect.py` under 400 LOC
- Connections to non-existent components raise ValueError
- Config with shell metacharacters rejected at export time
- MCP sessions persist across process restarts
- Template confidence visible in spec metadata
- Cost tracking works with any BaseLLM subclass (no string matching)
- All documentation updated to reflect v0.5.0 changes

### v1.0.0
- New import paths work (`cloudwright.session`, `cloudwright.designer`, `cloudwright.parsing`)
- Old import paths emit DeprecationWarning
- Web backend: each router independently testable
- Frontend: Zustand stores with 100% test coverage
- Frontend: component tests via Vitest + RTL
- CLI chat: layers independently testable
- Terraform exporter: new provider addable in single file
- SSE streaming: single shared helper, no per-endpoint reimplementation
- All documentation updated to reflect v1.0 changes
- No references to old module paths in any markdown file

---

## Out of Scope

- Multi-tenancy or user authentication (future feature)
- New cloud provider support (infrastructure ready, but not adding new providers in this overhaul)
- New export formats (plugin architecture exists, not expanding)
- LLM provider additions beyond Anthropic/OpenAI
- Performance optimization (no profiling-driven changes in this overhaul)
- Database migration from SQLite catalog (works fine at current scale)
