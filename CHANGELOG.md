# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.10.0] - 2026-08-24

### Added

- **Read-only migration planning and evidence checks.** New portable models describe estate assets,
  dependencies, target mappings, migration dispositions, costs, waves, acceptance gates, observations,
  and closure results. The planner rejects cycles, orders dependencies first, honors safe wave hints,
  keeps retiring dependencies available until their consumers move, reports unresolved mappings, and
  calculates supplied one-time, dual-run, recurring, and retirement costs.
- **External migration domain packs.** Packaged YAML rules add gates by asset kind, data class, and tag
  without adding industry fields to the core. The first `ph_telco` pack adds 17 gates for subscriber,
  billing, usage-record, number-porting, privacy, access, recovery, failover, and source shutdown checks.
- **Two checked proof projects.** The PH telco hybrid project closes with 22 passing gates across five
  waves. Removing one blocking observation changes closure to blocked. A manufacturing ERP project uses
  the same planner and evaluator with no domain pack.
- **Migration CLI, API, and web view.** `cloudwright migrate packs|plan|verify|demo` supports human and
  JSON output. CLI and HTTP evidence checks rebuild the assessment from the submitted project so edited
  planner output cannot remove gates. HTTP routes cap each migration collection at 200 items, and numeric
  contracts reject non-finite values. Authentication and rate checks run before request-body validation.
  Four `/api/migration/*` routes return the same core results. The Migration tab accepts a protected
  server's API key and shows the closure decision, supplied economics, dependency route, and evidence groups.
- **Reproducible migration GIFs.** Browser and CLI recorders run local proof data with no model key or
  cloud account. A VHS tape supports systems with a working ffmpeg install.

### Documentation

- Added `docs/migrations.md`, README examples, CLI reference entries, package notes, limitations, pack
  extension steps, source references, and GIF reproduction commands.

## [1.9.0] - 2026-08-01

The canvas audit. v1.8.0 rebuilt the interface around the canvas and never measured the canvas
itself, so every pan, zoom and drag setting was still a React Flow default. Driving all 16 `init`
templates through the running app, and running 8 interactions at 1920, 1440 and 390px, found 14
defects. This release closes them. No backend contract changes, so the CLI, the MCP server and
every API route behave exactly as in 1.8.0.

### Fixed

- **Every connection now draws an arrowhead.** The computed `markerEnd` on every edge was `none`,
  so a directed architecture diagram showed no direction at all.
- **Connection lines clear the contrast floor.** They rendered at 1.42:1 in light and 1.81:1 in
  dark, against the 3:1 WCAG floor for meaningful graphics. `--edge` is now `#64748b` on the light
  canvas at 4.55:1 and `#94a3b8` on the dark canvas at 7.3:1, solid instead of dashed and 1.6px
  instead of 1px.
- **The canvas zooms out far enough to fit a phone.** React Flow's 0.5 floor left 2 of 8 nodes
  outside the pane at 390px, with the Zoom Out button already disabled on arrival. The floor is
  now 0.12 and Fit View honours the same value, so all 8 fit at 0.29.
- **A boundary no longer eats the drag that should pan the canvas.** Dragging a VPC moved the box
  and its children by 113px, the VPC itself did not follow, and nothing saved the move. Boundaries
  are decoration now: they take no drag, no click and no pointer event.
- **A node is no longer trapped in its tier.** `extent: "parent"` against a box that hugged its
  contents left a node 5 to 10px of travel and no way out. Nodes carry absolute positions, the
  boundary re-fits around wherever they land, and a drag moves the full distance asked for.
- **The Delete key removes a selected connection.** React Flow listens for Backspace alone by
  default, so Delete did nothing to a selected edge. Both keys work.
- **Connect-by-drag works at 390px.** Handles went from 6px to 9px with a 28px connect radius.
- **A connection leaves the side of the node that matches the tier gap.** One pair of handles sent
  a same-tier connection out of the bottom and back into the top of the node beside it. Neighbours
  in a row now link straight across, anything further apart dips under the row, and a connection
  that skips a tier runs down the outside. Connections that disappear behind a card they do not
  touch fall from 17 to 5 across the 16 templates, and labels sitting on a card fall from 18 to 13.
- **A tier orders its components before it places them.** A barycentre sweep puts connected
  components near each other. Ties keep the spec's own order, so one spec always draws one picture.
- **The VPC border clears the tier borders inside it.** Both rectangles came from the same
  component positions with the same padding, so they shared a line in 12 of the 16 templates.
- **Boundary colours come from theme tokens.** Hardcoded light `rgba` painted the VPC as a pale
  slab on the dark canvas. Each tier keeps its hue and mixes its fill against the canvas.
- **A card holds a fixed 260px, the width the layout reserves for it.** The card grew with its
  content while the layout assumed 200px.
- **A row centres on its nodes, not on the column slots they sit in.** The old form sat 50px off.
- **Add Resource puts the resource in its tier.** It used to land on a fixed grid position that
  collided with whatever the generated layout had already put there.
- **The dead resize handle is gone.** `NodeResizer` rendered on every boundary with no handler to
  keep a resize, so any resize vanished on the next change.

### Notes

- Catalog drag and drop still does not exist, and no documentation claims it. README and
  `getting-started.md` say "drag components", which means dragging a node on the canvas, and that
  works. `docs/competitor-landscape.md` lists a drag-and-drop designer as a competitor's advantage.
- Connection crossings rise from 8 to 13 across the 16 templates. That is the deliberate half of
  the trade: a connection crossing another connection stays readable, while one that vanishes
  behind an unrelated card does not.

## [1.8.0] - 2026-07-31

A full rebuild of the web canvas interface. A UI audit of all 15 frontend components found 45
defects: 12 correctness, 11 accessibility, 6 responsive, 7 design-system, 9 content. This
release closes every one of them. No backend contract changes, so the CLI, the MCP server and
every API route behave exactly as in 1.7.0.

### Added

- **A design-token stylesheet and a dark theme.** `packages/web/frontend/src/styles.css` holds
  every colour, space, radius, shadow and type step as a CSS custom property. `[data-theme="dark"]`
  re-points the same tokens. The theme follows `prefers-color-scheme` until the user picks a side,
  then keeps that choice in `localStorage`. Nothing downloads a web font, so the strict
  Content-Security-Policy the server sends stays intact.
- **A responsive layout.** The frontend had zero media queries. It now has breakpoints at 1180px,
  900px and 620px. Below 900px the fixed 420px sidebar becomes a two-pane switch between Chat and
  Workspace. The nine workspace tabs scroll sideways instead of clipping. The shell uses
  `100dvh`, so the composer stays above the iOS URL bar.
- **The WAI-ARIA tabs pattern.** `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`,
  roving `tabindex`, and Arrow/Home/End keys. Each panel is a `role="tabpanel"` section.
- **Keyboard shortcuts and a skip link.** `Cmd/Ctrl+K` focuses the composer, `Cmd/Ctrl+1..9` picks
  a tab, `Escape` closes the catalog drawer and the node panel.
- **A stop button.** An `AbortController` now cancels a running design or change.
- **Error toasts.** A polite live region surfaces the failures the old code swallowed.
- **OpenTofu, Pulumi TypeScript and Pulumi Python in the Export tab.** All three shipped in
  `cloudwright.exporter.FORMATS` but had no button in the web UI. The tab now offers 13 formats in
  three groups.
- **`scripts/ui_screenshots.py`.** It screenshots every tab at three widths in both themes against
  the mock-LLM server, and `--readme` regenerates the exact `docs/screenshots/` filenames.
- **`packages/web/tests/test_static_bundle.py`.** Eight checks read the bundle in
  `cloudwright_web/static/`. They confirm that the hashed assets match `index.html`, that the tokens
  and the dark theme survive minification, that breakpoints exist, that the focus ring holds, and
  that no em-dash reaches user copy. A frontend change that never reaches the wheel now fails CI.

### Fixed

- **A mid-stream error billed a second generation.** `streamSucceeded` only became true after the
  stream loop returned, so an `error` event after the spec arrived left it false. The non-streaming
  fallback then ran a second design call and its result replaced the first. The fallback now runs
  only when the stream produced no spec.
- **Panel results no longer die on a tab switch.** Validation, compliance, plan and review results
  lived in component state that unmounted whenever the user changed tab. Panels now mount on first
  use and stay mounted.
- **The catalog drawer no longer covers the diagram on load.** It defaulted to open.
- **Silent failures now speak.** Diagram SVG/PNG export, module insertion, the standards check and
  the spec download all returned on `!res.ok` with no message.
- **The YAML tab shows the server's YAML.** It rendered a hand-written client-side serialiser that
  quoted nothing, so a value such as `no` or `2.0` read back as a boolean or a number. The panel now
  asks the server for the authoritative YAML, and the local serialiser (still the offline fallback)
  quotes anything that would change type.
- **Contrast.** 27 uses of `#94a3b8` (2.84:1 on white) and 2 of `#cbd5e1` (1.61:1) fell below the
  WCAG 1.4.3 AA floor. Every token now clears 4.5:1 in both themes.
- **Focus visibility.** Four `outline: none` rules removed the focus ring with no replacement, which
  fails WCAG 2.4.7. There is now one `:focus-visible` ring for the whole application.
- **The closed node panel left the tab order.** It stayed in the DOM at `translateX(100%)`, so
  keyboard focus walked into inputs parked off-screen. It unmounts when closed.
- **The streaming indicator animates.** It referenced a `pulse` keyframe that no file defined.
- **An input method no longer submits mid-word.** Enter now checks `isComposing`, so confirming a
  Japanese, Chinese or Korean candidate does not send the message.
- **A native `<dialog>` replaces `window.confirm`.** Three destructive actions used the browser
  dialog, which takes no styling and drops focus out of the page.
- **Error copy carries no em-dash.** `formatApiError` joined the message and the suggestion with
  one.
- **The dead session write is gone.** The reset button wrote `cloudwright_last_session` to
  `localStorage` and nothing ever read it.
- **The diagram fits its viewport.** `fitView` ran before the effect built any nodes, so the graph
  rendered at default zoom in a corner. It now refits when the node set changes, and leaves a
  hand-placed layout alone during a drag.
- **Diagram chrome stops overlapping.** The legend covered the React Flow zoom controls, and on a
  phone the Add Resource button sat on top of the export toolbar.

### Changed

- **The 90-line duplicate of the send path is gone.** The `Modify` tab re-implemented streaming,
  fallback, costing and error handling inline in a JSX prop. Both entry points now call one
  `runTurn`.
- **Empty states name the next action.** Six panels said "Design an architecture first." and stopped.
- **The composer is a textarea.** It grows with its content, Enter sends, Shift+Enter adds a line.
- **Browser tests use stable selectors.** Two assertions matched on inline style strings
  (`[style*="background: rgb(241, 245, 249)"]`), which a stylesheet removes. They now use
  `data-testid`. Nine new browser tests cover the tab pattern, the theme, panel persistence and the
  dialog.
- **Fresh screenshots and both web demo GIFs**, recorded against the new interface.

## [1.7.0] - 2026-07-08

Closes the July 2026 product audit findings. Offline review and OSCAL compliance now reach every
MCP-capable coding agent, not only the CLI. The web tier now handles event-loop stalls and large
payloads. Cost output no longer claims false freshness. The new `integrate` command connects
Cloudwright to 11 coding clients.

### Added

- **`cloudwright integrate`.** Generates the exact MCP server config for each supported coding client.
  It supports Claude Code, Cursor, Cline, Windsurf, GitHub Copilot, Zed, Codex, Junie, Kiro, and
  Antigravity. Each client gets its needed `mcpServers`, VS Code `servers`, Zed `context_servers`, or
  Codex TOML format. Aider gets a CLI pipe because it is not an MCP client. `--rules` writes a gate
  block for AGENTS.md, CLAUDE.md, or GEMINI.md. The block tells the agent to run `review`, `cost`, and
  `compliance` before it writes infrastructure.

  `--write` keeps existing server entries. See
  `docs/integrations.md`.
- **Review, compliance, and plan as MCP tools.** The server adds `review_architecture`,
  `scan_compliance_controls`, and `plan_infrastructure`. Review runs offline with no API key.
  Compliance can return an OSCAL 1.1.2 component definition. Plan validates only by default and
  never applies. Any MCP client can run these design checks in its agent loop.
- **Review and OSCAL on the web canvas.** `POST /api/review` runs the offline critique.
  `POST /api/compliance` accepts an `oscal` flag. The Review tab shows score, grade, and findings.
  The Compliance panel can download OSCAL JSON.
- **Honest cost signals.** Cost estimates report `prices_as_of` for the catalog date and `estimated_on`
  for today. They also report a `pricing_confidence_detail` ratio, such as "17/20 line items
  catalog-backed." Cross-provider `compare` adds a confidence column. Region pricing uses a regional
  catalog row when one exists. Otherwise it uses the static multiplier. New
  `docs/provider-coverage.md` states coverage by provider.
- **MCP session TTL.** The server clears MCP sessions older than
  `CLOUDWRIGHT_MCP_SESSION_TTL_DAYS`. The default is 7 days. Cleanup runs at server start and session-list.
- **Release and security docs.** The repository adds `RELEASING.md` for release steps and
  `SECURITY.md` for disclosure policy. Persisted specs also add `schema_version` for future migrations.

### Fixed

- **Web tier no longer stalls the event loop.** Diagram rendering runs through
  `asyncio.to_thread`. The d2 subprocess can run for up to 300 seconds. One PNG request no longer
  freezes the worker. `/api/diagram` adds a request model, so bad input returns 4xx instead of 500.
- **Request-size and component-count caps.** A 1 MB body limit and a component cap protect endpoints
  that accept specs. The server now clears old per-IP rate-limit buckets.
- **Container no longer serves unauthenticated by accident.** The Dockerfile sets
  `CLOUDWRIGHT_REQUIRE_AUTH=1`. Without `CLOUDWRIGHT_API_KEY`, the app refuses to start. Docker Compose
  also fails on an empty key. Local `uvicorn` stays open by default for development.
- **Structured logging activates on real launch paths.** `create_app()` now calls
  `configure_logging()`. Both `cloudwright chat --web` and bare `uvicorn` get request IDs and structured
  logs. This no longer depends on `serve()`.
- **Clean CLI errors.** A malformed spec now prints a short field error instead of a Pydantic
  traceback. JSON mode emits an error object with a code and message. Full tracebacks stay available
  with `--verbose`.
- **CI gains a dependency-CVE gate and a version-sync check.** CI now runs `pip-audit` and
  `check_version_sync.py`. The version check confirms that all 13 version markers agree.

## [1.6.1] - 2026-07-08

Hotfix for a crash in the flagship command, found by the July 2026 product audit.

### Fixed

- **`cloudwright design` no longer crashes on a live API key.** The telemetry line sent structlog
  keyword arguments to a standard library logger. The CLI then raised `TypeError` after the model
  response and returned no spec. The Anthropic and OpenAI providers now use percent-style logging.
  This bug existed since v1.1.0. Tests did not see it because the root logger stayed at WARNING.
  `test_llm_telemetry_logging.py` now tests both providers with `configure_logging()`. Per-call model,
  latency, token, and cache data now reaches the log.

## [1.6.0] - 2026-06-16

This release closes the defensibility + relevance gaps from the June 2026 product audit:
the design engine now self-corrects, compliance binds at design time with OSCAL output, cost
estimates stop fabricating numbers, and the credibility holes a security review would flag
first are fixed.

### Added

- **Generate -> critique -> repair loop + `cloudwright review`.** `Architect.design()` now runs the deterministic critics that already lived in the tree (scorer, linter, validator) against every generated spec and, when blocking (high/critical) findings remain, asks the model once to fix them. The loop is bounded, falls back to the original spec, and records a `critique` block in `spec.metadata` (score, grade, findings/blocking before and after, repair iterations). The same engine is exposed standalone as `cloudwright review spec.yaml [--compliance hipaa,soc2] [--well-architected]`, a free offline severity-ranked architecture review with no API key. Disable repair with `Architect(repair=False)`.
- **OSCAL 1.1.2 export.** `cloudwright compliance spec.yaml --frameworks fedramp --oscal [-o report.md]` also emits an OSCAL `component-definition` document (deterministic UUIDs, NIST-style lowercased control IDs, per-component `control-implementations` with satisfied / not-satisfied status). This targets the FedRAMP 20x / OSCAL direction. It maps controls at design time, before a CSPM or evidence tool can.
- **Control traceability.** `cloudwright compliance spec.yaml --traceability` shows the full chain design intent -> component -> Terraform resource type -> framework control ID -> status, as an audit artifact (`build_traceability()` in `compliance.py`).
- **Compliance-gated component patterns.** New `cloudwright/patterns.py` tags the bundled templates and modules with the frameworks they satisfy; `suggest_compliant_patterns("hipaa")` returns pre-blessed architectures so the tool proposes compliant designs instead of only flagging violations after the fact.
- **Agentic drift -> remediation.** New `cloudwright/remediation.py` `remediate(current, desired)` closes the loop read-only: drift diff -> monthly cost delta -> critique quality delta -> terraform/tofu plan preview, with an honest summary. Exposed via `cloudwright drift ... --remediate`. Never applies; `skip_plan=True` skips the IaC toolchain entirely.
- **Credible cost estimates.** Region-aware pricing (every region was previously priced as us-east-1), per-connection data-transfer/egress estimation, a per-line-item pricing `confidence` (`high` = catalog row, `low` = formula/fallback) with a top-level `pricing_confidence`, design-time carbon estimation (`cloudwright cost --carbon`), and FOCUS-spec CSV export (`cloudwright cost --focus`) for downstream FinOps tools.
- **OpenTofu support.** `cloudwright export spec.yaml --format opentofu` (alias for the Terraform HCL) and a tofu-aware planner that prefers `tofu` when present (override with `CLOUDWRIGHT_TF_BINARY`), falling back to `terraform`.
- **Self-serve docs.** New `docs/getting-started.md`, `docs/cli-reference.md`, `docs/troubleshooting.md`, `docs/mcp-reference.md`.
- **Surfaced telemetry.** The web canvas now renders the model / tokens / cost / latency the backend already computed, and a shared `parseApiError()` makes the canvas show the backend's structured `{code, message, suggestion}` errors and `Retry-After` instead of a generic "Request failed".

### Fixed

- **Compliance now overrides the workload profile.** A `sandbox`/`dev` spec carrying a compliance framework (e.g. HIPAA) no longer skips forced encryption / HA. The framework check moved ahead of the non-production early-return in `parsing.py`, with a real regression test (the prior test passed only because it set `production`).
- **WAF Terraform export is deployable.** `aws_wafv2_web_acl` now emits a multi-line `default_action { allow {} }`; the previous single-line nested block was rejected by `terraform validate`.
- **Cost region + fabricated prices.** The `region` parameter is now applied to catalog, formula, and fallback prices; the silent `$10` fallback for unknown services is marked low-confidence/estimated and logged at WARNING.
- **LLM parse failures keep the full response.** `_extract_json` logs the complete model output at debug before raising, instead of discarding everything past 300 characters. This output reproduces the most common LLM bug.

### Security

- **Terraform exporter injection hardening.** The 13 numeric resource fields (e.g. `allocated_storage`) are now coerced to real numbers via `_hcl_num`, and the export validator rejects newlines and braces in string values. This closes a path where a string-typed numeric field could inject a `provisioner "local-exec"` into the generated HCL. Pulumi and CloudFormation paths were already safe. Regression test included.
- **`cloudwright plan` secret scoping.** The subprocess environment no longer carries the LLM/app API keys (terraform never needs them), only credential-shaped keys are merged from a project `.env`, and any secret-shaped value is redacted from returned `output_tail`.

## [1.5.0] - 2026-05-19

### Added

- **Compliance scanner with framework control-ID mapping.** New `cloudwright compliance spec.yaml [--frameworks hipaa,soc2,fedramp] [--checkov/--no-checkov] [--fail-on high] [-o report.md]` maps every design-stage finding to the specific framework control it violates. This includes HIPAA `164.312(a)(2)(iv)`, SOC 2 `CC6.1`, FedRAMP `SC-28`, PCI-DSS, GDPR, ISO 27001, and NIST 800-53. The mapping runs before infrastructure exists. The built-in `SecurityScanner` and Terraform HCL scan need no external tool. When Checkov is on PATH, its `CKV_*` findings join the same report (explicit ID map plus keyword fallback). Output includes a per-framework posture table and an audit-ready markdown report. The control catalog is `cloudwright/data/compliance_controls.yaml`. Web: `POST /api/compliance` and a Compliance tab. Optional dependency: `pip install 'cloudwright-ai[compliance]'` (checkov 3.x). The control mapping still works without Checkov.
- **`cloudwright plan`: prove the exported infrastructure is deployable.** New `cloudwright plan spec.yaml [--target terraform|pulumi-python|pulumi-ts] [--no-plan] [--timeout N]` runs `terraform init -backend=false` and `terraform validate`. It can also run `terraform plan` with cloud credentials or `pulumi preview`. It never applies. `validate` needs no credentials. `plan` adds a real `+add ~change -destroy` resource diff when credentials resolve. Output states why a full plan was skipped: missing credentials, needed input variables, invalid config, or provider network access. It works without the optional binary. Web: `POST /api/plan` and a Plan tab with a DEPLOYABLE or NOT DEPLOYABLE verdict.
- **Live GCP and Azure import.** `cloudwright import-live --provider gcp --project PROJECT` walks Compute Engine, Cloud Storage, and Cloud SQL; `cloudwright import-live --provider azure --subscription SUB_ID` walks Virtual Machines, Storage Accounts, Azure SQL, and AKS. Both mirror the AWS importer: lazy SDK import, fast-fail on missing credentials, non-fatal per-service permission guards, canonical registry service keys, security posture capture (GCS public-access-prevention + versioning + CMEK, Storage Account HTTPS-only + public-blob + min-TLS, SQL public network access, AKS private cluster). GCP project falls back to `GOOGLE_CLOUD_PROJECT`; Azure subscription to `AZURE_SUBSCRIPTION_ID`. The CLI now routes `--provider gcp|azure` instead of returning "not yet implemented". Optional deps split into `live-import-gcp` / `live-import-azure` extras (also bundled in `live-import`).

## [1.4.0] - 2026-05-02

### Added

- **Live AWS import.** New `cloudwright import-live --provider aws --region us-east-1 [--profile NAME] [--services ec2,rds,s3] [-o spec.yaml]` walks `boto3 describe-*` calls (EC2, VPC + subnets + security groups, RDS, S3, Lambda, ECS, EKS, DynamoDB, ALB/NLB, CloudFront, SQS, API Gateway, CloudTrail) and produces an ArchSpec from running infrastructure. Captures security posture (S3 encryption + versioning + public-access-block, RDS multi-AZ + storage_encrypted + backup_retention, EC2 IMDSv2 http_tokens, SG ingress 0.0.0.0/0). Best-effort connection inference: ALB to EC2 (via target groups) and CloudFront to S3 (via origin domains). Per-service permission denials are non-fatal. Other services keep scanning. GCP and Azure surface a clear "not yet implemented" error. Optional dep: `pip install 'cloudwright-ai[live-import]'` (boto3 1.34+).
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

- **Two-stage prompting for design and complex modify.** Per `ai-llm-eval.md` ("Two-Stage Prompting Recovers Reasoning Quality Lost to JSON Schema Constraints"), `Architect.design()` now runs Stage 1 (free-text architectural reasoning via Sonnet, `DESIGN_REASONING_SYSTEM`) followed by Stage 2 (strict JSON projection via Haiku, `DESIGN_PROJECTION_SYSTEM`). Stage 2 gets the canonical service keys, allowed connection kinds, and boundary kinds. It projects without redesigning. Single-shot path remains as fallback (`Architect(two_stage=False)`). `IMPORT/MIGRATION/COMPARE` flows still use the legacy single-shot prompts since their contracts are tighter.
- **`Connection.kind` enum.** New optional field on `Connection`: `sync_request | async_event | stream | replication | batch`. Default `None` for back-compat. Stage 2 projector populates it based on the Stage 1 reasoning's verbs ("calls" → `sync_request`, "publishes to" → `async_event`, "streams" → `stream`, etc.). Parser accepts canonical and aliased values (`sync`, `async`, `http`, `Sync-Request`) and silently drops invalid values to `None`.
- **First-class boundaries in the LLM contract.** `Boundary` (VPC / subnet / security_group / availability_zone / region / account) was previously in the schema but never asked of the LLM. The Stage 1 prompt now instructs the architect to reason about networking topology explicitly; Stage 2 projects named VPCs, subnets, and SGs into a `boundaries` array with parent linkage. Parser tolerates malformed boundary entries (missing `id`/`kind`, invalid IDs, ghost component refs) by dropping them with a warning.
- **Per-stage usage in API responses.** When a request goes through two-stage prompting, the `usage` payload returned by `/api/design`, `/api/design/stream`, `/api/modify`, `/api/modify/stream` now includes `stage1` (`{model, input_tokens, output_tokens, cost_usd, latency_ms, reasoning_chars}`), `stage2` (same shape), `stage1_tokens`, `stage2_tokens`, `total_cost_usd`, and a `two_stage: true` flag. Aggregate `input_tokens`/`output_tokens`/`cost_usd` fields still present for back-compat.

### Changed

- **Conditional safe-default injection in `_post_validate`.** The pre-v1.4 implementation forced `encryption=true`, `multi_az=true`, `backup=true`, `auto_scaling=true`, and `count=2` onto every spec. This masked Stage 1 reasoning and produced the same monolithic shape for sandbox/dev workloads as for HIPAA-bound production. v1.4 makes these conditional on workload profile (`spec.metadata.workload_profile`) and declared compliance:
  - `sandbox`, `dev`, `development`, `test`, `demo`, `poc` profiles get the LLM's chosen values without overrides.
  - `production`, `prod`, `medium`, `large`, `enterprise` profiles get the safe defaults forced.
  - Compliance frameworks (HIPAA, PCI-DSS, SOC 2, GDPR, FedRAMP, HITRUST, ISO 27001) always force encryption + HA regardless of profile.
  - Instance type / class / node-type defaults still always applied (they're sane fallbacks, not safety settings).
- **`SERVICE_NORMALIZATION` is now a fallback.** With Stage 2 explicitly told the canonical service keys, the 60-entry normalization table should rarely trigger. Each hit now logs a louder WARNING ("Stage 2 projector should have emitted the canonical key directly") so we can track LLM drift and trim the table over time.

### Notes

- All 4 new test files added: `test_two_stage_prompting.py` (8 tests), `test_boundary_in_spec.py` (5 tests), `test_connection_kind.py` (8 tests), `test_post_validate_conditional.py` (8 tests). 29 new tests, all passing.
- Existing `_post_validate` tests retain their behavior because `_profile_requires_encryption` / `_profile_requires_ha` default to `True` when no profile metadata and no overriding signal is present, preserving the previous defaults for callers that didn't tag specs.
- **Cancel-safe LLM streaming via `AsyncAnthropic` + `AsyncOpenAI`.** `AnthropicLLM.generate_stream_async` and `OpenAILLM.generate_stream_async` use the providers' native async clients with `async with` cleanup, so consumer cancellation propagates into the SDK and closes the upstream httpx connection. The lazy-built `async_client` property means sync callers pay no async-import cost.
- **`ConversationSession.send_stream_async`.** Async generator mirror of `send_stream`. Pops the orphan user message on `BaseException` (covers `asyncio.CancelledError`) so a disconnected stream doesn't leave a user-without-assistant turn at the end of history.
- **`BaseLLM.generate_stream_async` default.** Bridges the sync `generate_stream` through `asyncio.to_thread` for any third-party provider that has not implemented the native async path yet. It is not cancel-safe, but provides a working default.
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

- Smart Canvas: web diagram is now a fully editable architecture canvas (add/connect/drag nodes, edit label/description/tier/config/tags, delete resources/connections) with deterministic frontend state mutations and no LLM `modify` calls.
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
- Spec diff integration. Modifications show added/removed/changed components via existing `Differ` class
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

- Workload profiles for cost estimation (small, medium, large, enterprise). Injects production-realistic sizing defaults before pricing formulas run
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
- Global error handler in all commands. Clean error messages with `--verbose` for stack traces
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
