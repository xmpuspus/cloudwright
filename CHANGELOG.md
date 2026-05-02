# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-05-02

### Added

- **Live AWS import.** New `cloudwright import-live --provider aws --region us-east-1 [--profile NAME] [--services ec2,rds,s3] [-o spec.yaml]` walks `boto3 describe-*` calls (EC2, VPC + subnets + security groups, RDS, S3, Lambda, ECS, EKS, DynamoDB, ALB/NLB, CloudFront, SQS, API Gateway, CloudTrail) and produces an ArchSpec from running infrastructure. Captures security posture (S3 encryption + versioning + public-access-block, RDS multi-AZ + storage_encrypted + backup_retention, EC2 IMDSv2 http_tokens, SG ingress 0.0.0.0/0). Best-effort connection inference: ALB → EC2 (via target groups) and CloudFront → S3 (via origin domains). Per-service permission denials are non-fatal — other services keep scanning. GCP and Azure surface a clear "not yet implemented" error. Optional dep: `pip install 'cloudwright-ai[live-import]'` (boto3 1.34+).
- **GitHub Action `cloudwright-pr-comment`** posts an idempotent PR comment with architecture diff (added/removed/changed components), monthly cost delta (head vs. base, with annual rollup), and per-framework compliance changes (e.g. SOC 2 score deltas, newly-failing or newly-resolved checks). Reusable composite action at `.github/actions/cloudwright-pr-comment/`. Drop-in workflow template at `.github/workflows/cloudwright-pr-preview.yml` triggers on PRs touching `*.tf`, `*.tfstate`, `cloudwright.yaml`, or `spec.yaml`. Setup guide at `docs/github-action.md`.
- **Re-recorded Smart Canvas demo GIF** (`examples/cloudwright-smart-canvas-demo.gif`) reflecting the v1.3 UI: prompt → diagram → catalog drawer → add resource → side-panel edit → cost recompute. Reproducible via `python scripts/record_smart_canvas.py` against a local web server (mock LLM, template-matched prompt, no API key required for the recording).
- **Pulumi exporter (TypeScript + Python).** New `--format pulumi-ts` and `--format pulumi-python` export targets. `cloudwright export spec.yaml --format pulumi-ts -o ./infra` writes a complete Pulumi TypeScript project (`index.ts`, `Pulumi.yaml`, `package.json`, `tsconfig.json`) using `@pulumi/aws`, `@pulumi/gcp`, and `@pulumi/azure-native`. `--format pulumi-python` writes a Python project (`__main__.py`, `Pulumi.yaml`, `requirements.txt`) using `pulumi_aws`, `pulumi_gcp`, and `pulumi_azure_native`. Aliases `pulumi-typescript` and `pulumi-py` also work.
- **Same safe-by-default posture as the Terraform exporter.** Pulumi outputs ship S3 `forceDestroy: false` + public-access block + AES256 SSE + versioning, RDS `storageEncrypted` + `backupRetentionPeriod: 7` + `deletionProtection` + `skipFinalSnapshot: false`, EC2 IMDSv2 (`httpTokens: "required"`) + encrypted root EBS, DynamoDB SSE + PITR, SQS managed SSE, Kinesis KMS encryption, ECR scan-on-push + AES256, CloudFront `minimumProtocolVersion: "TLSv1.2_2021"` + `viewerProtocolPolicy: "redirect-to-https"`, CloudTrail `enableLogFileValidation` + multi-region. GCP Cloud Storage gets uniform-access + `publicAccessPrevention: "enforced"` + versioning. Azure Storage / SQL get `minimumTlsVersion: "TLS1_2"`.
- **Pulumi-flavoured string escaping.** New `_ts_string()` and `_py_string()` helpers escape `"`, `\\`, newlines, and backticks on every interpolated user-controlled field (`c.id`, `c.label`, `spec.region`, `spec.metadata.gcp_project`, architecture name) so hostile values cannot break out of the generated TypeScript / Python literal.
- **AWS service coverage:** vpc, ec2, rds, s3, alb, nlb, cloudfront, lambda, dynamodb, sqs, kinesis, ecr, ecs, eks, cloudtrail, cloudwatch.
- **GCP service coverage:** compute_engine, gke, cloud_sql, cloud_storage, cloud_run, pub_sub, bigquery.
- **Azure service coverage:** virtual_machines, aks, azure_sql, blob_storage, azure_functions, app_gateway.
## [1.4.0] - 2026-05-01

### Added

- **Two-stage prompting for design and complex modify.** Per `ai-llm-eval.md` ("Two-Stage Prompting Recovers Reasoning Quality Lost to JSON Schema Constraints"), `Architect.design()` now runs Stage 1 (free-text architectural reasoning via Sonnet, `DESIGN_REASONING_SYSTEM`) followed by Stage 2 (strict JSON projection via Haiku, `DESIGN_PROJECTION_SYSTEM`). Stage 2 is told the canonical service keys, allowed connection kinds, and boundary kinds — so it projects faithfully without redesigning. Single-shot path retained as fallback (`Architect(two_stage=False)`). `IMPORT/MIGRATION/COMPARE` flows still use the legacy single-shot prompts since their contracts are tighter.
- **`Connection.kind` enum.** New optional field on `Connection`: `sync_request | async_event | stream | replication | batch`. Default `None` for back-compat. Stage 2 projector populates it based on the Stage 1 reasoning's verbs ("calls" → `sync_request`, "publishes to" → `async_event`, "streams" → `stream`, etc.). Parser accepts canonical and aliased values (`sync`, `async`, `http`, `Sync-Request`) and silently drops invalid values to `None`.
- **First-class boundaries in the LLM contract.** `Boundary` (VPC / subnet / security_group / availability_zone / region / account) was previously in the schema but never asked of the LLM. The Stage 1 prompt now instructs the architect to reason about networking topology explicitly; Stage 2 projects named VPCs, subnets, and SGs into a `boundaries` array with parent linkage. Parser tolerates malformed boundary entries (missing `id`/`kind`, invalid IDs, ghost component refs) by dropping them with a warning.
- **Per-stage usage in API responses.** When a request goes through two-stage prompting, the `usage` payload returned by `/api/design`, `/api/design/stream`, `/api/modify`, `/api/modify/stream` now includes `stage1` (`{model, input_tokens, output_tokens, cost_usd, latency_ms, reasoning_chars}`), `stage2` (same shape), `stage1_tokens`, `stage2_tokens`, `total_cost_usd`, and a `two_stage: true` flag. Aggregate `input_tokens`/`output_tokens`/`cost_usd` fields still present for back-compat.

### Changed

- **Conditional safe-default injection in `_post_validate`.** The pre-v1.4 implementation forced `encryption=true`, `multi_az=true`, `backup=true`, `auto_scaling=true`, and `count=2` onto every spec — masking Stage 1 reasoning and producing the same monolithic shape for sandbox/dev workloads as for HIPAA-bound production. v1.4 makes these conditional on workload profile (`spec.metadata.workload_profile`) and declared compliance:
  - `sandbox`, `dev`, `development`, `test`, `demo`, `poc` profiles get the LLM's chosen values without overrides.
  - `production`, `prod`, `medium`, `large`, `enterprise` profiles get the safe defaults forced.
  - Compliance frameworks (HIPAA, PCI-DSS, SOC 2, GDPR, FedRAMP, HITRUST, ISO 27001) always force encryption + HA regardless of profile.
  - Instance type / class / node-type defaults still always applied (they're sane fallbacks, not safety settings).
- **`SERVICE_NORMALIZATION` is now a fallback.** With Stage 2 explicitly told the canonical service keys, the 60-entry normalization table should rarely trigger. Each hit now logs a louder WARNING ("Stage 2 projector should have emitted the canonical key directly") so we can track LLM drift and trim the table over time.

### Notes

- All 4 new test files added: `test_two_stage_prompting.py` (8 tests), `test_boundary_in_spec.py` (5 tests), `test_connection_kind.py` (8 tests), `test_post_validate_conditional.py` (8 tests). 29 new tests, all passing.
- Existing `_post_validate` tests retain their behavior because `_profile_requires_encryption` / `_profile_requires_ha` default to `True` when no profile metadata and no overriding signal is present, preserving the previous defaults for callers that didn't tag specs.
- **Cancel-safe LLM streaming via `AsyncAnthropic` + `AsyncOpenAI`.** `AnthropicLLM.generate_stream_async` and `OpenAILLM.generate_stream_async` use the providers' native async clients with `async with` cleanup, so consumer cancellation propagates into the SDK and closes the upstream httpx connection. Lazy-built `async_client` property on each provider — sync callers pay no async-import cost.
- **`ConversationSession.send_stream_async`.** Async generator mirror of `send_stream`. Pops the orphan user message on `BaseException` (covers `asyncio.CancelledError`) so a disconnected stream doesn't leave a user-without-assistant turn at the end of history.
- **`BaseLLM.generate_stream_async` default.** Bridges the sync `generate_stream` through `asyncio.to_thread` for any third-party provider that hasn't implemented the native async path yet — not cancel-safe, but provides a working default.
- **SSE proxy-buffering headers.** `/api/chat/stream`, `/api/design/stream`, `/api/modify/stream` now ship `X-Accel-Buffering: no` and `Cache-Control: no-cache` so nginx (and most reverse proxies) forward token chunks immediately instead of waiting on a 4-16 KB buffer fill.

### Changed

- **`/api/chat/stream` no longer uses a worker thread.** The `threading.Thread` + `asyncio.Queue` bridge is gone. The route now `async for`s over `session.send_stream_async` directly, so client disconnect or timeout cancels the upstream LLM call instead of orphaning a thread that keeps consuming tokens. Net ~50 LOC simplification (audit `docs/audits/03-reliability-perf.md` Critical #2).
- **`/api/design/stream` and `/api/modify/stream` route-level timeouts.** Replaced bare `asyncio.to_thread(...)` with `asyncio.wait_for(asyncio.to_thread(...), timeout=120)` and a graceful `llm_timeout` SSE error event. Matches the cancel-safety contract of `/api/chat/stream`. (`/api/design/stream` previously had no route-level timeout at all.)

### Fixed

- **Orphan thread on chat-stream disconnect.** Audit Critical #2: a daemon `threading.Thread` ran `session.send_stream` to completion even after the client disconnected or the route returned `llm_timeout`. The async refactor kills this entirely.
- **`asyncio.Queue` full → token loss.** Audit High: the 256-slot queue between the worker thread and the SSE consumer dropped tokens past the 256-chunk mark on slow networks (manifesting as truncated specs that `_try_parse_spec` rejected). Removed with the queue.
- **Timeout doesn't cancel LLM bill.** Audit High: route-level `asyncio.wait_for(..., 120)` cancelled the awaiting coroutine but left the SDK call running for up to 60 more seconds in the worker thread. Async path makes the timeout actually short-circuit the SDK call.

## [1.3.0] - 2026-05-02

### Added

- **Safe-by-default Terraform output.** AWS exporter now emits `aws_s3_bucket_public_access_block` (all four blocks true), `aws_s3_bucket_server_side_encryption_configuration` (AES256), `aws_s3_bucket_versioning`, RDS `storage_encrypted = true` + `backup_retention_period = 7` + `deletion_protection`, EC2 IMDSv2 `metadata_options { http_tokens = "required" }` + encrypted root EBS, DynamoDB SSE + PITR, SQS managed SSE, Kinesis KMS encryption, ECR scan-on-push + AES256, CloudFront `minimum_protocol_version = "TLSv1.2_2021"`, and CloudTrail log-file validation. The README "safe defaults" claim now matches the rendered HCL.
- **HCL injection-safe escaping** across every Terraform exporter (`aws.py`, `azure.py`, `gcp.py`, `databricks.py`, `__init__.py`). New `_hcl_quote()` helper escapes `"`, `\`, and newlines on every interpolated user-controlled string (`c.label`, `spec.region`, `spec.metadata.gcp_project`, module-instance metadata). 152 escape sites converted.
- **Per-model LLM pricing.** `BaseLLM.pricing_for(model)` returns the right rate per model. `claude-haiku-4-5*` = `{input: 0.0008, output: 0.004}`; `claude-sonnet-4-6*` = `{input: 0.003, output: 0.015}`; `gpt-5*` and `gpt-5.2` = `{input: 0.0025, output: 0.01}`; `gpt-5-mini*` = `{input: 0.0005, output: 0.002}`. Cost numbers shown to users are no longer 10x wrong on Haiku-routed traffic.
- **Anthropic prompt caching surgery.** System prompt is now sent as a list of blocks with `cache_control: {"type": "ephemeral"}` on a stable prefix and a separate variable block for per-turn hints. Cache hit-rate on follow-up chat turns goes from near-zero to high, surfaced via `usage.cached_tokens`.
- **OpenAI cache parity.** `stream_options={"include_usage": True}` is now set so `usage.prompt_tokens_details.cached_tokens` is captured and surfaced.
- **Cost transparency in API.** `/api/design`, `/api/design/stream`, `/api/modify`, `/api/modify/stream` now return a `usage` object: `{model, input_tokens, output_tokens, cached_tokens, cost_usd, latency_ms}`. Previously only `/api/chat` returned it.
- **Atomic SessionStore writes.** `SessionStore.save()` writes to a temp file in the same directory, calls `fsync`, then `os.replace` for an atomic rename. SIGKILL mid-write no longer corrupts session JSON.
- **Robust JSON extraction.** `_extract_json` now uses `json.JSONDecoder().raw_decode` instead of a hand-rolled brace counter. Handles nested-JSON-strings, escapes, and `<json>` XML wrappers correctly.
- **Health endpoint with version + readiness.** `/api/health` now returns `{status, version, build_sha, llm_provider, llm_model, catalog_loaded, catalog_size, uptime_s}`. Returns 503 when the catalog fails to load (Kubernetes readiness probes are now correct). New `/api/version` endpoint for lightweight polling.
- **Request correlation IDs.** New `RequestIdMiddleware` reads `X-Request-Id` from incoming requests or mints a UUID, binds it to `structlog.contextvars`, and echoes it on the response. All log lines for a single request now share the same `request_id`.
- **Hero demo + VHS tape.** New `examples/cloudwright-hero.gif` (under 1 MB, 12 seconds) shows init → cost → validate → export → ls in one continuous capture. Tape file at `examples/tapes/cloudwright-hero.tape` regenerates the GIF deterministically.

### Changed

- **README rewritten.** Reduced from 1,279 lines to 140 lines. Hero GIF + 3-line install in the first 100 words. Inline changelog moved to this file. Old release notes for v0.1 through v1.2.x trimmed from above-the-fold.
- **`cloudwright chat --web` pinned to port 8765** (matches what the README always claimed). Pass `--port` to override. The previous 8000-8099 scan was a source of "the URL doesn't work" first-run friction.
- **`--debug` flag works.** Previously `chat --debug` called `logging.basicConfig` which is a no-op against the already-configured structlog. Now sets the structlog log level correctly. Also accepts `CLOUDWRIGHT_LOG_LEVEL=DEBUG`.
- **FedRAMP region check.** Replaced `region.startswith("us-")` heuristic with explicit per-provider allowlists. `us-east-1` and `us-west-2` now correctly pass FedRAMP Moderate; `us-iso-east-1` and `us-west-1` correctly fail. GCP and Azure use explicit lists too.

### Security

- **Constant-time API key comparison.** `check_api_key` now uses `hmac.compare_digest` instead of `!=`. Closes a timing-attack vector on `CLOUDWRIGHT_API_KEY`.
- **Swagger UI gated by environment.** `/docs`, `/redoc`, `/openapi.json` are now disabled by default unless `CLOUDWRIGHT_DOCS_ENABLED=true` or `CLOUDWRIGHT_ENV` is unset (dev). Production deploys no longer expose a free reconnaissance map.
- **OpenAI `Stream` connection-pool leak fix.** `Stream` is now closed via `try/finally: stream.close()`, fixing pool exhaustion when consumers disconnect mid-stream.

### Notes

The following audit unlocks are deferred to future releases because they require larger architectural shifts:

- Live import (`cloudwright import-live --provider aws` boto3 sweep)
- Two-stage prompting refactor (free-text reasoning then JSON projection)
- Cancel-safe streaming via `AsyncAnthropic`/`AsyncOpenAI` (eliminates the worker-thread bridge)
- GitHub App for arch-diff + cost-delta on PRs
- Boundary-aware spec generation (VPC/subnet/SG promoted into the LLM schema)
- Pulumi/CDK/Bicep/Crossplane export targets

See `docs/audits/2026-05-01-product-audit.md` for the full audit + roadmap.

## [1.2.2] - 2026-04-26

### Fixed

- PyPI publish workflow switched from PyPI Trusted Publishing (which had been failing on `cloudwright-ai`/`cloudwright-ai-cli`/`cloudwright-ai-web` with `invalid-publisher`) to a `PYPI_API_TOKEN` GitHub secret. Tag pushes now publish all four wheels through CI without manual `twine upload` fallback.

## [1.2.1] - 2026-04-26

### Fixed

- `cloudwright-ai`'s `[cli]`, `[web]`, `[mcp]`, and `[all]` extras pinned to a non-existent `0.4.0` release, so `pip install 'cloudwright-ai[cli]'` and `pip install 'cloudwright-ai[web]'` failed with `No matching distribution`. Pins now match the current release. All four packages bumped together to keep extras in lockstep.

## [1.1.0] - 2026-04-04

### Added

- OpenAI provider implementation (`OpenAILLM`) with `generate`, `generate_fast`, and streaming. Auto-detects from `OPENAI_API_KEY`; override the model with `CLOUDWRIGHT_MODEL`.
- `SecurityHeadersMiddleware` adds `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy`, and `Referrer-Policy` to all web responses.
- `Retry-After` header on 429 rate-limit responses.
- `X-Forwarded-For` parsing behind reverse proxy via `CLOUDWRIGHT_TRUST_PROXY`.
- Provider-aware service normalization: `redis` maps to `elasticache` on AWS, `memorystore` on GCP, `azure_cache` on Azure (same for `postgres`, `mongodb`, `kubernetes`, `docker`).
- Dockerfile (`python:3.12-slim`) and `docker-compose.yml` for containerized web server.
- Usage tracking on streaming responses.
- Tab completions for provider and compliance flags.
- GDPR validator now recognizes GCP `europe-*` and Azure `northeurope`/`westeurope` regions.

### Changed

- Web server fails fast at startup if `CLOUDWRIGHT_API_KEY` is missing (was previously optional).
- Terraform exporter applies safer defaults: `username -> var.db_username`, `skip_final_snapshot -> false`, ECR `IMMUTABLE` tags. CloudFormation: `MasterUsername -> !Ref DBUsername`. Config validation applied to all export formats, not just IaC.
- History trimming places summaries in the system prompt instead of injecting a synthetic user message (was causing Anthropic 400 errors on 50+ turn sessions).
- PyPI publish workflow now requires the test job to pass (`needs: [test]`).
- Coverage floor enforced at 70%.
- `create_version()` is now called before `modify()`.
- MCP lock scoped to store I/O only.
- Health endpoint returns 503 when no LLM key is configured.
- SSE queue bounded to 256 events.

### Fixed

- Client-supplied `assistant`-role messages are now rejected from chat history (prompt-injection guard).
- `send()` and `send_stream()` pop orphaned history entries on LLM failure.
- `generate_stream` retries on rate limits for both Anthropic and OpenAI providers.
- `configure_logging()` is invoked in both CLI and web entrypoints.
- Architecture review GitHub Action YAML.

## [1.2.0] - 2026-04-26

### Added

- Smart Canvas: web diagram is now a fully editable architecture canvas (add/connect/drag nodes, edit label/description/tier/config/tags, delete resources/connections) with deterministic frontend state mutations — no LLM `modify` calls.
- Catalog drawer with three tabs (Resources, Modules, Standards) on the diagram tab.
- `GET /api/catalog/services?provider={provider}` endpoint backing the Resources tab. Provider casing is normalized (e.g., `?provider=GCP` and `?provider=gcp` return the same set).
- Approved module catalog: `GET /api/modules` and `GET /api/modules/{id}` expose curated multi-resource patterns from `packages/core/cloudwright/data/modules/`.
- Bundled approved modules: AWS Three-Tier Web, AWS Serverless API, AWS Data Lake, GCP Serverless API, Azure Three-Tier Web.
- `cloudwright.modules` core module: `ModuleCatalog`, `ModuleSpec`, `insert_module`, `validate_standards`, `validate_standards_from_dict` for canvas standards checks.
- `POST /api/canvas/validate` endpoint for naming-prefix, required-tag, orphan-connection, partial-module, and unapproved-module checks.
- `spec.metadata.canvas.nodes` namespace persisting dragged node positions (`{node_id: {x, y}}`).
- `spec.metadata.modules.instances` namespace persisting module provenance (source module id, version, expected component count, naming prefix, required tags, generated component ids).
- Terraform exporter emits `module "<instance_id>"` blocks with pinned `source` and `version` for intact catalog module instances; falls back to per-component resource rendering when an instance is partial.
- `var.db_username` Terraform variable so module-aware specs `terraform validate` cleanly.

### Changed

- Frontend `ArchitectureDiagram` accepts an `onSpecChange` callback so the canvas can push deterministic edits back into the app-level spec, then refresh cost/validation in the background.
- `Component.config` is now optional in the frontend type to match the canvas-add resource flow.

### Fixed

- Provider lookups in `/api/catalog/services` now lowercase the query parameter, so uppercase providers like `GCP` and `Azure` work.

## [1.0.0] - 2026-03-26

### Breaking

- Import paths changed: `cloudwright.session.ConversationSession`, `cloudwright.designer.Architect`, `cloudwright.parsing._parse_arch_spec` are the canonical locations. Old `from cloudwright.architect import ...` still works via re-export shim.
- Web backend restructured: `app.py` is now an app factory (`create_app()`), endpoints split into routers under `cloudwright_web/routers/`
- Frontend rewritten with Zustand state management and restructured component architecture
- Terraform exporter split into per-provider modules under `exporter/terraform/` (import path unchanged)
- CLI chat command decomposed into `chat.py`, `chat_ui.py`, `chat_session.py`, `chat_streaming.py`

### Added

- Shared SSE streaming abstraction (`cloudwright_web/streaming.py`) used by all streaming endpoints
- CLI command decorator (`cloudwright_cli/decorators.py`) for standardized output/error handling
- Frontend test infrastructure: Vitest + React Testing Library + MSW
- Zustand stores for spec, chat, cost, validation, and UI state

### Changed

- `architect.py` decomposed into `session.py` (ConversationSession), `designer.py` (Architect), `parsing.py` (JSON extraction, spec parsing), `prompts.py` (all constants)

## [0.5.0] - 2026-03-26

### Added

- Connection validation: `ArchSpec` model validator rejects connections referencing non-existent component IDs
- Config value sanitization: `validate_export_config()` rejects shell metacharacters before Terraform/CloudFormation export
- Template match confidence scores (0.0-1.0) stored in `spec.metadata['template_confidence']`
- `BaseLLM.model_name` and `BaseLLM.pricing` abstract properties for explicit cost tracking

### Changed

- Extracted ~600 LOC of prompt constants from `architect.py` into `prompts.py` (pure data, no behavior change)
- Error hints capped to sliding window of 5 (prevents unbounded growth in long sessions)
- MCP sessions now persist to disk via `SessionStore` (survive process restarts)
- Cost tracking uses `llm.pricing` instead of string-matching on module name

### Removed

- MCP in-memory session storage, TTL cleanup, and max session eviction (replaced by SessionStore)

## [0.4.0] - 2026-03-20

### Added

- FedRAMP and GDPR frameworks in web UI validation panel
- Self-contained HTML export format (`--format html`) for shareable architecture reports
- "Designed with Cloudwright" attribution on exported diagrams and IaC
- Optional API key authentication for web API (`CLOUDWRIGHT_API_KEY` env var)
- Configurable CORS origins via `CLOUDWRIGHT_CORS_ORIGINS` env var
- Structured logging with structlog (JSON or console output, `CLOUDWRIGHT_LOG_FORMAT`)
- LLM call timing instrumentation
- SVG/PNG diagram export from web UI
- `.env.example` for easy setup

### Fixed

- `SessionStore` path traversal vulnerability (session_id now validated against `[A-Za-z0-9_-]`)
- Streaming endpoints (`/api/design/stream`, `/api/modify/stream`) now enforce rate limiting
- MCP session tools thread safety with `threading.Lock`
- LLM empty response handling (IndexError on content-filtered responses)
- Silent exception swallowing in web API cost/validation paths (now logged)
- CI publish workflow action version alignment (`checkout@v4`, `setup-python@v5`)
- Modify tab in web UI now uses SSE streaming (consistent with chat sidebar)
- Web UI suggestion buttons use LLM-generated suggestions when available

### Changed

- Minimum `structlog` version requirement added to core package

## [0.3.5] - 2026-03-14

### Added

- Token-level streaming in CLI via Rich Live display and Web via SSE `/api/chat/stream` endpoint
- Session persistence: `SessionStore` class with save/load/list/delete, CLI `/save-session`, `/load-session`, `/sessions` commands, `--resume SESSION_ID` flag
- Per-turn and cumulative usage tracking (input/output tokens, estimated cost) across all interfaces
- Context window management with automatic history trimming at 50 turns
- Spec diff integration — modifications show added/removed/changed components via existing `Differ` class
- Clarification-first routing for ambiguous single-word inputs (skips LLM, asks for more detail)
- Few-shot examples in design and modify system prompts to reduce JSON parsing failures
- `--debug` flag for CLI chat (shows prompts, responses, timing, token counts)
- `/help` and `/?` commands in CLI chat showing all available slash commands
- Rate limiting in Web API (30 requests/minute per IP, sliding window)
- Structured error responses in Web API with `code`, `message`, `suggestion` fields
- Thread-safe singletons for web server concurrency (double-checked locking)
- Suggestion buttons in React frontend (context-aware based on current spec)
- Confirmation dialog on "New" button with auto-save to localStorage
- MCP session TTL (1 hour), max sessions (100), automatic cleanup of expired sessions
- `chat_delete_session` MCP tool
- Usage and cumulative usage in MCP `chat_send` and `chat_list_sessions` responses
- Per-call `timeout` parameter on all LLM methods (`generate`, `generate_fast`, `generate_stream`)
- Expanded retry logic with jitter: RateLimitError, APIConnectionError, InternalServerError, APITimeoutError
- Configurable max retries via `CLOUDWRIGHT_LLM_MAX_RETRIES` environment variable
- Actionable error messages in CLI chat (missing API key, rate limit, timeout, JSON parse failure)
- 44 Playwright browser tests covering every README feature: page layout, architecture design, diagram rendering, cost breakdown, compliance validation, export panel, spec YAML, modify tab, suggestion buttons, multi-turn chat, streaming indicators, confirmation dialogs, summary bar, download buttons, and all API endpoints
- 21 new test files: unit, integration, e2e (real LLM), behavioral, API, and browser tests
- `SessionStore` exported from `cloudwright` package

### Changed

- `ConversationSession.send()` now tracks usage in `last_usage` and `cumulative_usage` properties
- `ConversationSession.modify()` now computes spec diff in `last_diff` property
- CLI chat rewritten to use `ConversationSession` directly instead of `Architect`
- Web `/api/chat` response now includes `usage` field
- MCP `chat_list_sessions` response now includes `created_at` and `usage` per session

## [0.3.4] - 2026-03-09

### Changed

- Restructured README with What's New release timeline, demo GIFs at the top, and installation section

## [0.3.3] - 2026-03-09

### Added

- Workload profiles for cost estimation (small, medium, large, enterprise) — injects production-realistic sizing defaults before pricing formulas run
- `--workload-profile` / `-w` flag on `cost` command
- Shell completion callbacks for workload profiles and pricing tiers
- 20 new CloudFormation resource types (IAM, VPC, CloudWatch, Kinesis, StepFunctions, SecretsManager, KMS, ECR, MSK, EventBridge)
- 50 hardcoded Terraform resource type mappings (AWS, GCP, Azure) as fallback when registry lookup fails
- Post-import encryption defaults for databases and storage services
- MCP package build and publish steps in CI/CD workflow
- MCP package metadata (readme, keywords, classifiers, URLs)

### Fixed

- Cost estimates 10-100x too low for production workloads (workload profiles fix formula input defaults)
- Import pipeline ~20% failure rate on unrecognized resource types (expanded type maps)
- MCP package not included in publish workflow

## [0.3.2] - 2026-03-06

### Fixed

- Extras version pins updated for core 0.3.2

## [0.3.1] - 2026-03-05

### Added

- ASCII exporter for terminal-friendly architecture diagrams
- MCP (Model Context Protocol) server package for Claude Code integration
- Structured CLI output with `--stream` NDJSON mode
- Skills system for CLI extensibility

## [0.3.0] - 2026-03-04

### Added

- Security scanner (`cloudwright security`) with 6 checks: missing encryption, open ingress, no HTTPS, IAM wildcards, missing backups, no monitoring
- `scan_terraform()` for HCL static analysis
- ADR generator (`cloudwright adr`) with LLM-powered and deterministic fallback modes
- Databricks cost governance template (job clusters, SQL Warehouse auto-stop, Secret Scope)

### Fixed

- PNG renderer CDN 403 errors (disabled icon fetching)

## [0.2.27] - 2026-03-04

### Added

- PyPI, CI, license, and Python version badges in README
- CODE_OF_CONDUCT.md (Contributor Covenant)
- GitHub issue templates (bug report, feature request) and PR template
- Changelog backfill for all versions from v0.2.1 to v0.2.26

### Changed

- Development status classifier upgraded from Alpha to Beta across all packages
- Python 3.13 classifier added to CLI and web packages

### Fixed

- GitHub Action installed wrong PyPI package name (`cloudwright` instead of `cloudwright-ai`)
- CI workflow pinned to verified GitHub Actions versions (checkout@v4, setup-python@v5)
- README git clone URL pointed to wrong GitHub org
- SECURITY.md listed implemented features as "Not Yet Implemented"
- README template names used hyphens instead of underscores (`databricks_lakehouse`)

## [0.2.26] - 2026-03-04

### Added

- Databricks provider init templates

## [0.2.25] - 2026-03-04

### Added

- Databricks as fourth cloud provider (alongside AWS, GCP, Azure)

## [0.2.24] - 2026-03-02

### Added

- Draggable and resizable boundary boxes in diagram canvas
- VPC and tier boundary rendering for all component groupings

### Fixed

- Label collision between VPC nests and tier boundary labels

## [0.2.23] - 2026-03-01

### Changed

- Set max_tokens to 10000 uniformly for all LLM calls (prevents truncation on any architecture)

## [0.2.22] - 2026-03-01

### Fixed

- Truncated JSON responses on complex architectures (raised max_tokens, expanded complexity detection)

## [0.2.21] - 2026-03-01

### Added

- Color-coded boundary labels with tier-specific styling

## [0.2.20] - 2026-03-01

### Fixed

- Boundary rendering now shown for all tiers including single-component tiers

## [0.2.19] - 2026-03-01

### Added

- Diagram boundaries inferred from tier layout automatically

## [0.2.18] - 2026-03-01

### Fixed

- Connection field name mismatch in chat LLM responses

## [0.2.17] - 2026-03-01

### Fixed

- ConversationSession field name mismatch causing chat failures

## [0.2.16] - 2026-03-01

### Fixed

- Modify retry logic on failed LLM responses
- Template selection threshold tuning

## [0.2.15] - 2026-03-01

### Added

- Async endpoints with streaming SSE for real-time diagram updates
- Spec caching layer to avoid redundant LLM calls
- Progressive loading in frontend during generation

### Changed

- Parallel LLM requests in frontend for reduced latency
- Worker config tuned for concurrent web traffic

### Fixed

- Latency and accuracy regressions introduced in v0.2.14

## [0.2.14] - 2026-02-28

### Fixed

- Modify timeout on large architectures

## [0.2.13] - 2026-02-28

### Fixed

- Multi-turn chat continuity across web UI and CLI

## [0.2.12] - 2026-02-28

### Added

- Rich UI panels for Validation, Export, and Spec tabs in web UI

## [0.2.11] - 2026-02-28

### Fixed

- Sub-package versions pinned in extras to prevent dependency drift

## [0.2.10] - 2026-02-28

### Changed

- Diagram UX improvements and model selection guidance

## [0.2.7] - 2026-02-28

### Added

- Frontend bundle included in wheel for offline use
- Browser auto-opens on `cloudwright chat --web`

## [0.2.6] - 2026-02-28

### Added

- Auto-detection of available port for web UI server

## [0.2.5] - 2026-02-28

### Fixed

- Web extra now correctly includes CLI dependency

## [0.2.4] - 2026-02-28

### Added

- Light theme UI redesign with improved contrast
- Markdown rendering fix in chat responses
- Four UI screenshots added to README

## [0.2.3] - 2026-02-28

### Added

- Web UI screenshots in README

### Fixed

- zsh pip install quoting for extras syntax

## [0.2.2] - 2026-02-28

### Added

- Six real-world CLI examples with actual output in README

## [0.2.1] - 2026-02-28

### Fixed

- CLI bugs discovered during v0.2.0 PyPI testing

## [0.2.0] - 2026-03-01

### Added

- `--json` flag for machine-readable JSON output on all commands (design, cost, compare, validate, export, diff, catalog search, catalog compare)
- `--version` flag to print the installed version string
- `--verbose` / `-v` flag to show full tracebacks on errors
- `--pricing-tier` option on `cost` command (on_demand, reserved_1yr, reserved_3yr, spot)
- D2 diagram export formats: `d2`, `d2-svg`, `d2-png`
- `mermaid-svg` and `mermaid-png` export format variants
- `cloudwright policy` command for policy-as-code compliance engine
- Global error handler in all commands — clean error messages with `--verbose` for stack traces
- JSON error responses when `--json` flag is active and a command fails

### Changed

- Architect: enforce exact service keys from LLM (no invented compound keys like `rds_postgres`)
- Architect: add Terraform resource type mapping for state/config parsing
- Architect: service name normalization layer with engine suffix extraction
- Catalog: adjust fallback prices for container orchestrators (EKS, GKE, AKS, ECS)
- Catalog: add debug logging for fallback pricing lookups

### Fixed

- README/CLAUDE.md: correct PyPI package name from `cloudwright` to `cloudwright-ai`

## [0.1.0] - 2026-02-27

### Added

- Natural language architecture design via LLM (Anthropic Claude, OpenAI GPT)
- ArchSpec data model with YAML/JSON serialization
- Cost engine with catalog-backed pricing for AWS, GCP, Azure
- Cross-cloud provider comparison with service mapping
- Compliance validation (HIPAA, PCI-DSS, SOC 2, Well-Architected Framework)
- Export to Terraform HCL, CloudFormation YAML, Mermaid diagrams
- CycloneDX SBOM and OWASP AIBOM export
- Structured diff between architecture versions
- SQLite service catalog with 58 instance types, 242 pricing entries, 66 cross-cloud equivalences
- CLI with Rich formatting (design, cost, validate, export, diff, catalog, chat)
- FastAPI web backend with React frontend
- Security-hardened IaC output (IMDSv2, encryption at rest, KMS, access logging)
- API key authentication and rate limiting for web API
