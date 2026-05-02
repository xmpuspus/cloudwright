# Cloudwright Product Audit, 2026-05-01

Audit of `main` at commit `0942b95` (v1.2.2, released 2026-04-26). Today: 2026-05-01.

This report is read-only. It does not modify the project; it asks the user to choose what to act on. Recommendations are ranked by impact/effort, not severity.

---

## 1. Snapshot

- 4 packages on PyPI (`cloudwright-ai`, `-cli`, `-web`, `-mcp`); 27k LOC core, 70 test files, 12 demo GIFs.
- Last meaningful feature: v1.2.0 Smart Canvas + Module Catalog (5 days ago).
- Last 4 commits are pipeline fixes (extras pin, PyPI publish token), not features.
- Two failing tests known and tolerated.
- Catalog data stamped 2026-02-01, three months stale, no scheduled refresh.

## 2. Scores by dimension

```
                        score   weight   note
  UX                   64/100    1.0x    powerful surface, rough first-touch
  Observability        38/100    1.0x    no correlation IDs, no metrics, broken --debug
  Reliability          64/100    1.5x    streaming + cancellation gaps
  Performance          67/100    1.0x    prompt cache defeated, catalog reconnects
  Intelligence         58/100    1.0x    single-shot JSON, defaults masquerade as reasoning
  Feature Gaps         45/100   0.75x    Day-2 story empty (no apply, drift, import, plugins)
  Security             58/100    1.5x    SECURITY.md vs HCL output mismatch, root container
  Operational          62/100    1.0x    multi-package extras brittle, dev-shaped self-host
  -----
  Overall             ~58/100             "Adequate, needs work"
```

The product has more capability than its current presentation reveals, and the IaC artifact does not yet deliver on the safety promise the docs make. Those two gaps drive most of the rest.

## 3. Cross-cutting themes (what the seven audits independently surfaced)

### Theme A: The product over-promises and under-shows.

- README is 1,279 lines with 14 image embeds, no hero artifact, no quickstart split, install buried below a 4-quadrant screenshot grid.
- `SECURITY.md` claims "encryption at rest, IMDSv2, public-access blocks" but none of these appear in the rendered AWS Terraform.
- Five compliance frameworks each implemented as a 5-7 box checklist; HIPAA passes with `audit_logging + auth + encryption=true`. No control-ID mapping. Auditor cannot use the output as evidence.
- Cost UI displays Sonnet pricing for all calls, including Haiku-routed ones; numbers are wrong by ~10x for fast-path traffic.
- Service-correctness in `benchmark/results/full_benchmark_report.md` shows Cloudwright trailing raw Claude (83.8 vs 97.1). The benchmark hides this behind 7 other metrics where Cloudwright wins.

### Theme B: The LLM is doing less than the parser is.

`prompts.py:413-494` ships a single-shot JSON-schema prompt with the schema, rules, and examples in one block. Per the project's own `ai-llm-eval.md`: direct JSON-schema output drops reasoning quality ~27pp. The symptoms:

- 60+ entry `SERVICE_NORMALIZATION` table to repair LLM output.
- `_post_validate` injects encryption=true, multi_az=true, count=2, instance_type=m5.large into every spec regardless of context. Sandbox/dev environments silently get production posture.
- `_enforce_connections` invents protocol+port from tier ordering; produces architecturally wrong wiring that Terraform inherits.
- `Boundary` (VPC, subnet, SG) defined in `spec.py` but never asked of the LLM. TF output is "soup" with no real network topology.

Two-stage prompting, free-text reasoning then a separate Haiku call to project to JSON, is the unlock the project's own rule already prescribes.

### Theme C: The Day-2 story is empty.

The competitor doc in the repo lists every gap; little has closed since Feb 2026, while competitors moved.

| Capability | Cloudwright | Spacelift Intent | Brainboard | Pulumi Neo | Firefly | StackGen |
|---|---|---|---|---|---|---|
| NL → architecture | yes | yes | yes (Bob) | yes | partial | yes (Aiden) |
| Cost in design loop | yes | no | yes | no | no | partial |
| Compliance in design | shallow | yes (policy) | yes | yes (Mar 2026) | yes | yes |
| IaC dialects beyond Terraform | none | TF | TF/OpenTofu | Pulumi | TF | TF |
| Live import (boto3/Asset/RG) | tfstate only | yes | yes | yes | yes | yes |
| Continuous drift | no | yes | yes | yes | yes | yes |
| Apply / plan integration | no | yes | yes | yes | partial | yes |
| Multi-user / share / comment | no | yes | yes | yes | yes | yes |
| GitHub App | no | yes | yes | yes | yes | yes |
| MCP server | yes (CLI mirror) | yes (Intent) | no | yes | no | no |

Cloudwright wins on local-first, MIT, and bundles cost+compliance+IaC+diagram in one install (Brainboard is closest but SaaS). Beyond design, every competitor has shipped further.

### Theme D: Distribution does not match the work invested.

- No `uvx cloudwright "<prompt>"` path. First-run friction is `pip install` then `cloudwright chat`.
- No `curl ... | sh` installer. No Homebrew tap. No live playground URL.
- MCP server published but not submitted to MCP Hunt, MCPRepository, ToolHive, or the official `modelcontextprotocol/servers` index. No `CLAUDE.md` snippet shipped that teaches agents to use the MCP tools.
- No GitHub App. No VSCode extension. No Backstage plugin. No Slack hook.
- README has 14 image embeds. None is The Hero. By Aider/uv/GitDiagram standards, Cloudwright currently has 14 wows, which is zero.

### Theme E: Operational visibility is dark.

- No request correlation IDs anywhere in the stack. A user-reported "design hung" cannot be traced to the upstream LLM call.
- `/api/health` returns 200 even when the catalog fails to load. No `/version`, no `/ready`.
- LLM retries are silent; user sees a 30-60s spinner and assumes hang.
- Anthropic prompt cache is set on the system block but `_build_system_with_hints` mutates the cached prefix every turn. Cache hit-rate near zero on a 23 KB system prompt. OpenAI provider has no caching wiring at all.
- Rate limiter is per-process; with `workers=4` the advertised "30/min" is actually "120/min".
- No metrics. No `--debug` that does anything (basicConfig is silently a no-op against structlog).

---

## 4. Ship-blocking findings (Critical, in audit-evidence terms)

These should block the next public release. All have file:line evidence in `/tmp/cw-audit-2026-05-01/01..04`.

1. `SECURITY.md` claims hardening the AWS Terraform exporter does not implement. Either render `aws_s3_bucket_public_access_block`, `server_side_encryption_configuration`, `aws_db_instance.storage_encrypted=true`, `metadata_options { http_tokens="required" }`, and minimal-egress security groups, or retract the claim. The credibility of the entire product rests here.
2. `check_api_key` uses non-constant-time `!=` (`packages/web/cloudwright_web/middleware.py:44`). Replace with `hmac.compare_digest`.
3. Generated AWS HCL interpolates `c.label`, `spec.region`, `metadata.gcp_project`, and module-instance metadata directly into f-strings without escape. `validate_export_config` only walks `comp.config`. A stray `"` in an LLM-generated label breaks HCL syntax; a crafted label can forge an extra HCL attribute.
4. OpenAI streaming `Stream` is not used as a context manager (`packages/core/cloudwright/llm/openai.py:63`). Connection-pool leak on disconnect. Anthropic equivalent is correct.
5. `chat/stream` worker thread orphaned on timeout/disconnect; keeps consuming LLM tokens after the server returns 504. Both providers.
6. Web server SPA catch-all returns `index.html` for missing `/api/...` paths; hides routing regressions and turns 404s into 200s.
7. README cost numbers are wrong for Haiku-routed calls. `AnthropicLLM.pricing` returns Sonnet rates for both fast and generate paths.
8. Web `/api/design` and `/api/modify` drop usage tokens on the floor; only `/api/chat` returns them. Frontend cannot show cost parity.
9. Compliance validators FedRAMP heuristic is `region.startswith("us-")`. `us-east-1` is NOT FedRAMP-authorized. This is a wrong answer, not a missing feature.

---

## 5. Top 10 unlocks ranked by impact/effort

These are the recommendations. Each closes multiple findings at once. Effort is rough: S = under a day, M = 1-3 days, L = a week.

| # | Unlock | Closes | Effort | Why now |
|---|---|---|---|---|
| 1 | Make IaC actually safe by default | Critical #1, #9; Operational trust; SECURITY.md honesty | M | Highest leverage on user trust. The whole pitch hinges on this. |
| 2 | Two-stage prompting + boundary-aware spec | Theme B; Intelligence headline; service-correctness vs raw Claude | M | The audit's biggest unmet promise; recovers ~27pp reasoning. |
| 3 | README hero rewrite + 12-second VHS GIF + live playground | Theme A, D; first-touch conversion | M | Distribution is the floor on every other improvement. |
| 4 | `uvx cloudwright "<prompt>"` + brew tap + curl install script | Theme D; first-run friction | S | Single-line invocation is the one move that compounds. |
| 5 | Cancel-safe streaming via AsyncAnthropic / AsyncOpenAI | Critical #4, #5; orphan threads; queue-full data loss | M | One refactor kills three reliability findings, simplifies ~50 LOC. |
| 6 | Live import: `cloudwright import-live --provider aws` (boto3) | Day-2 story; Brainboard/Firefly parity | L | Closes the largest competitor gap with a high-recall feature. |
| 7 | Anthropic prompt-cache surgery + OpenAI cache parity | Performance; cost; first-token latency | S | Stable prefix, variable suffix. ~70-80% input-token savings. |
| 8 | GitHub App: arch-diff + cost-delta + compliance on every PR | Theme A integration gap; "Vercel preview URLs for infra" | L | Only IaC tool that shows up where engineers already work. |
| 9 | Cost transparency: per-call `[tokens / $ / latency]` everywhere | Cost-trust; Cline-pattern parity | S | Cursor's June 2025 backlash is the cautionary tale. |
| 10 | "Show your work" panel in web UI: prompts + raw LLM + parsed spec | Trust; differentiates from black-box SaaS | S | Inspectable trust beats asserted trust. |

The numbered ordering is the sequencing recommendation, not just the priority. Item 1 makes the marketing claim true; items 2 and 3 make the marketing claim worth making; items 4 through 10 are how it spreads.

---

## 6. Differentiation: where the audit says Cloudwright can stake unique ground

After surveying ~30 tools (full notes in `/tmp/cw-audit-2026-05-01/05-competitive.md`):

| Cloudwright claim | Verdict | Notes |
|---|---|---|
| (a) Structured ArchSpec as artifact | Validated. Uncontested. | Brainboard, Spacelift, StackGen have internal models; none expose them. |
| (b) Local, MIT, runnable without account | Mostly validated. | Spacelift Intent is the closest open competitor. aiac is local but Go-CLI only, no diagrams, no cost, no compliance. |
| (c) Cost + compliance + IaC + diagram in one install | Validated. Strongest moat. | Brainboard is closest but SaaS. Cloudcraft only does cost. StackGen only does policy. Nobody bundles all four locally. |
| (d) MCP server | Now contested. | AWS, Azure, GCP, HashiCorp, Spacelift, Pulumi all have MCP servers. Differentiate on the artifact (returns ArchSpec), not the surface. |
| (e) Free | Commoditizing. Table stakes. | aiac, Spacelift Intent, Crossplane, OpenTofu are all free. The moat is what the user does with the artifact, not the price. |

White-space gaps that are not yet filled:

1. **MCP server that returns a typed planning artifact** (not a side effect or a diagram). Today every cloud-IaC MCP either acts on cloud or renders pixels. Cloudwright can claim this ground by promoting the ArchSpec.
2. **Reverse-direction live cloud → ArchSpec.** Cloudcraft and System Initiative do live import to their own internal models. Nobody emits a portable spec. Cloudwright + the ArchSpec format makes "live infra to portable design" a real product.
3. **GitDiagram-class URL hack.** No IaC-AI tool has shipped one. `cloudwright.dev/<github-org>/<repo>` that auto-generates an ArchSpec from a public repo (parsed from existing `.tf`, `Dockerfile`, `docker-compose.yml`, `serverless.yml`) is a screenshot-able, shareable moment that fits the IaC audience and uses Cloudwright's existing `import` primitive.
4. **AGENTS.md-aware generation.** Pulumi Neo just shipped this in Feb. Cloudwright reading `AGENTS.md` + `.cloudwright/conventions.md` so a team encodes "we use VPC X, never Glacier, prefer eu-west-3" lets agents speak the team's own grammar.
5. **shadcn-style module registry.** v1.2.0 already has the module catalog primitive. Add a public registry + `cloudwright add module/<x>` that copies YAML into the user's repo. Modules are owned by the user; no version pinning, no upgrade dread.

---

## 7. The demo recommendation

Replace the current 14-image README with a single 12-second hero GIF, regenerated by VHS in CI on every release.

```
0–2s  user types: cloudwright design "HIPAA healthcare API on AWS"
2–6s  spec materializes: 12 components, VPC boundaries, RDS, ALB
6–9s  cloudwright cost spec.yaml --workload-profile medium  →  $2,263/mo
9–12s cloudwright export spec.yaml --format terraform -o ./infra  →  Wrote 14 .tf files
```

One input. Three concrete outputs. No narration. Loops.

Pair with a hosted playground at `cloudwright.dev/playground` running the same prompt against a rate-limited shared key (or canned response with no LLM call). That is the GitDiagram-shape click-through; the reader can replay the trick in a browser without `pip install`.

The shareable Twitter/HN moment is a side-by-side: cloud architect at a whiteboard for two hours on the left, Cloudwright in 8 seconds on the right, with a `terraform validate` green check at the end.

The first 100 words of the redesigned README:

> # Cloudwright
>
> *Describe a cloud architecture in English. Get Terraform, costs, and a compliance check.*
>
> [hero GIF, 12s, under 5 MB]
>
> ```bash
> uvx cloudwright "HIPAA healthcare API on AWS with Postgres and Redis"
> ```
>
> Cloudwright produces a structured architecture spec, cost estimate, compliance report (HIPAA, SOC2, PCI), and Terraform/CloudFormation code from a single prompt. Multi-cloud (AWS, GCP, Azure, Databricks). 17 templates, 5 modules, 200+ services costed.
>
> Try it: cloudwright.dev/playground · Docs: cloudwright.dev/docs · MCP: `pip install cloudwright-ai-mcp`

---

## 8. Distribution playbook for the next launch (one page)

**README**
- One-sentence pitch: verb + concrete object + measurable result.
- Hero GIF: 12 seconds, under 5 MB, 10 fps, 800-1280 px source.
- Install in three lines, in the first 100 words.
- Live playground URL on the first screen.
- Move the inline changelog to `CHANGELOG.md`. Saves ~400 lines.
- Reduce 14 feature subsections to 6 grouped headings.
- Cut "Why" + "How it compares" from above-the-fold.
- Re-record GIFs against the Soft UI Evolution design tokens (currently stale per the project memory).

**Distribution week 1**
- Show HN, Tuesday 7am Pacific. Title: `Show HN: Cloudwright – Natural language to Terraform, costs, and HIPAA in one CLI`. 76 chars, no superlatives. Author present in comments for the first 30 minutes.
- Direct pitch to Corey Quinn (Last Week in AWS, cost angle) and Gergely Orosz (Pragmatic Engineer, architecture-as-code angle).
- r/devops as a technical write-up ("we ran `terraform validate` against 100 generated specs"), not a launch post.
- r/Python launch post.
- X/Bluesky cross-post the 24-second before/after video.
- Skip LinkedIn week 1; circle back week 3 with the compliance buyer angle.

**Distribution weeks 2-4**
- DEV.to + Hashnode long-form: "How we ship a multi-cloud architect in one CLI."
- KubeCon NA 2026 co-located events CFP (opens 2026-04-29).
- The Changelog and Practical AI podcast pitches.
- Tag Theo / Fireship / ThePrimeagen on X with a 30-second clip.

**What good looks like at +30 days**: 1,000+ stars, 5,000+ PyPI weekly downloads, HN front page over 100 points, one newsletter feature, one YouTube creator video over 10k views.

---

## 9. What this report is not

This is a recommendation document. It does not modify any code, configuration, or content in the project. None of the recommendations have been implemented. The seven raw audit reports live in `/tmp/cw-audit-2026-05-01/` (UX+Obs, Intelligence+Gaps, Reliability+Perf, Security+Ops, Competitive, DX+Virality, README+Distribution), with file:line evidence for every finding. The competitive scan and DX research draw from ~150 cited public sources.

The user should pick which of the Top 10 unlocks (section 5) to act on next, in what order, and whether to do them as separate PRs or bundled into a v1.3 release.
