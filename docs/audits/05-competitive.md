# Cloudwright Competitive Landscape — Update May 2026

Cutoff: 2026-05-01. This addendum updates `docs/competitor-landscape.md` (~Feb 2026) with what shipped, pivoted, or launched between Mar 2026 and May 2026, and surfaces adjacent tools the existing doc misses.

---

## 1. New / Updated Competitors Since Feb 2026

### Pulumi Neo — moved from "preview" to "platform" (Feb–Apr 2026)

Pulumi has hardened Neo from "an AI agent for IaC" into a full platform layer in three steps over Q1/Q2 2026.

- **AGENTS.md support (Feb 2026)** — Neo now reads `AGENTS.md` files, the open standard already supported by Cursor, Windsurf, Copilot, and Zed. ([Pulumi Neo Now Supports AGENTS.md](https://www.pulumi.com/blog/pulumi-neo-now-supports-agentsmd/)) Direct competitive read: Neo is positioning to be the "agent that already knows your team's conventions" — Cloudwright has no equivalent context-loading primitive.
- **Integration Catalog (Apr 2026)** — six MCP integrations at launch (Atlassian, PagerDuty, Datadog, Honeycomb, Linear, Jira), all over MCP. ([Neo's Integration Catalog](https://www.pulumi.com/blog/neo-integration-catalog/))
- **Compliance backlog framing (Mar 2026)** — Pulumi explicitly markets Neo for "infrastructure compliance backlogs" — direct adjacency to one of Cloudwright's pillars. ([The New Stack: Pulumi's AI Agent Tackles Compliance Backlogs](https://thenewstack.io/pulumis-ai-agent-tackles-infrastructure-compliance-backlogs/), [Intellyx coverage 2026-03-29](https://intellyx.com/2026/03/29/pulumi-adding-cloud-automation-ai-agent-to-mature-iac-platform/))
- Operating modes: Review / Balanced / Auto, mirroring Aider's manage-by-confirmation pattern. ([Pulumi Neo product page](https://www.pulumi.com/product/neo/))

### HashiCorp / Terraform — MCP server is now the agent surface (2026)

HashiCorp shipped two MCP servers (Terraform + Vault) and has joined Microsoft to ship Azure Copilot + Terraform integration in public beta. The Terraform MCP server reads HCP Terraform / Enterprise auth so agents can run workspaces directly — no context switching. ([Build secure AI workflows with Terraform and Vault MCP](https://www.hashicorp.com/en/blog/build-secure-ai-driven-workflows-with-new-terraform-and-vault-mcp-servers), [terraform-mcp-server repo](https://github.com/hashicorp/terraform-mcp-server))

### Crossplane v2.2 (Mar 2026)

Crossplane shipped v2.2 with a **pipeline inspector** sidecar (alpha) for debugging composition functions, RequiredSchemas in `RunFunctionRequest`, and capability advertisement. ([Crossplane v2.2 release post](https://blog.crossplane.io/crossplane-v2-2-more-capable-more-reliable-more-observable/), [Crossplane What's New](https://docs.crossplane.io/latest/whats-new/)) Crossplane v2.0 (released earlier) added managed resource definitions and dropped the requirement that XRs only compose Crossplane MRs — they can now compose any K8s resource directly. ([Announcing Crossplane 2.0](https://blog.crossplane.io/announcing-crossplane-2-0/))

### OpenTofu — staying on the 1.x train

No "OpenTofu 2.0" exists. OpenTofu **1.12.0-beta1** dropped 2026-04-07 with concurrent provider downloads, `const = true` for static-eval-required vars, and a new `language` block for separating engine constraints from third-party software. Final 1.12.0 expected May 2026. ([OpenTofu 1.12.0-beta1 announcement](https://opentofu.org/blog/help-us-test-opentofu-1-12-0-beta1/), [OpenTofu releases](https://github.com/opentofu/opentofu/releases))

### Spacelift Intent + Intelligence (Oct 2025 GA, demoed at KubeCon EU Mar 2026)

[Spacelift Intent](https://spacelift.io/intent) is the most direct natural-language-IaC competitor to Cloudwright — provision and manage infrastructure with NL, governance preserved. The repo is **open-source on GitHub**: [spacelift-io/spacelift-intent](https://github.com/spacelift-io/spacelift-intent). They demoed it as "vibe-coding infrastructure" at KubeCon EU 2026. ([Spacelift Intelligence Vibe-Codes Infrastructure — DevOps.com](https://devops.com/spacelift-intelligence-vibe-codes-infrastructure/), [SiliconANGLE coverage](https://siliconangle.com/2025/10/08/spacelift-enables-instant-codeless-infrastructure-provisioning-cloud-workloads/)) **This is the single closest open-source competitor and the existing doc almost certainly under-weights it.**

### StackGen — "Aiden" autonomous infrastructure agent (2026)

[StackGen](https://stackgen.com/platform-overview) describes itself as an "Autonomous Infrastructure Platform (AIP)" with **Aiden for Infrastructure** — describe a system in English, get validated, policy-compliant Terraform. Stated benchmarks: 95% reduction in iteration time, 85% fewer policy violations, 4–6 week deploys, 350% ROI. They integrate with Wiz for security. ([StackGen + Wiz integration blog](https://stackgen.com/blog/securing-infrastructure-at-the-speed-of-development-introducing-stackgens-integration-with-wiz)) Competitive note: Aiden's pitch is essentially Cloudwright + an enterprise pipeline.

### System Initiative — multi-cloud expansion (Q1 2026)

System Initiative added Microsoft Azure, DigitalOcean, and Hetzner support, plus "live multiplayer automation" — real-time collaboration on infrastructure changes. Live demos shown at AWS re:Invent 2025; multi-cloud capability went GA early 2026. ([InfoQ: System Initiative Multi-Cloud Expansion](https://www.infoq.com/news/2025/12/system-initiative-multi-cloud/)) Their core pitch ("replace IaC entirely") is more radical than Cloudwright's "generate IaC" but they're chasing the same user.

### Brainboard "Bob" AI architect

Brainboard shipped its AI assistant Bob — diagram → Terraform with multi-cloud (AWS / Azure / GCP) on a single canvas, plus integrated plan/apply gates, policy checks, security scans, cost checks, and drift detection. ([Brainboard Smart Cloud Designer](https://www.brainboard.co/features/smart-cloud-designer), [AI-Enhanced Architecture Design with Bob](https://dev.to/brainboard/ai-enhanced-architecture-design-with-bob-38dm)) **This is feature-for-feature the visual-canvas-plus-cost-plus-policy story Cloudwright tells, just SaaS.**

### Massdriver, Resourcely

[Massdriver](https://www.massdriver.cloud/) is positioning around scaling IaC adoption with packaged compliance/operational workflows; Series A-stage, current platform release v1.2.0. ([Massdriver platform update v1.2.0](https://www.massdriver.cloud/blogs/changelog-version-1.2.0)) Resourcely focuses on "guided configuration patterns" + policy-as-code — they sit upstream of generation, enforcing guardrails on what gets shipped. ([Resourcely + Terraform modules](https://www.resourcely.io/and/terraform-modules))

---

## 2. Adjacent Tools the Existing Doc Likely Misses

### AWS Cloud Control API MCP Server (official AWS, 2026)

AWS shipped an official [Cloud Control API MCP Server](https://aws.amazon.com/blogs/devops/introducing-aws-cloud-control-api-mcp-server-natural-language-infrastructure-management-on-aws/) for natural-language CRUDL on **any** AWS resource via Cloud Control API. AWS also has 60+ official MCP servers in [awslabs/mcp](https://github.com/awslabs/mcp). This is direct competition for any "talk to AWS in natural language" pitch.

### Azure MCP suite (official Microsoft, 2026)

40+ MCP tools spanning best practices, AI/ML, analytics, compute, containers, databases, devops, IoT, storage. Azure Copilot + Terraform integration in public beta. ([InfoWorld: Five MCP servers to rule the cloud](https://www.infoworld.com/article/4129024/five-mcp-servers-to-rule-the-cloud.html))

### Google Cloud managed MCP servers

Announced Dec 2025; AlloyDB / Cloud SQL / Spanner / Firestore / Bigtable went GA in 2026. ([Google Cloud Next '26 coverage](https://earezki.com/ai-news/2026-04-28-the-quiet-revolution-at-google-cloud-next-26-your-database-can-talk-to-your-ai-agent-no-bridge-required-published/))

### Clanker Cloud — unified multi-cloud MCP

[Clanker Cloud's MCP server](https://clankercloud.ai/blog/headless-ai-apis-mcp-infrastructure-layer-2026) exposes AWS, GCP, Azure, Kubernetes, Cloudflare, Hetzner, DigitalOcean, and GitHub through a single local endpoint — direct overlap with Cloudwright's "one tool, all clouds" framing.

### Excalidraw + tldraw MCP servers (Mar 2026 wave)

Multiple Excalidraw MCP implementations launched in March 2026: official [excalidraw/excalidraw-mcp](https://github.com/excalidraw/excalidraw-mcp), community [yctimlin/mcp_excalidraw](https://github.com/yctimlin/mcp_excalidraw), and the layout-engine-bundled [BV-Venky/excalidraw-architect-mcp](https://github.com/BV-Venky/excalidraw-architect-mcp). The pitch: describe a system in English, Claude generates a fully editable Excalidraw diagram. ([dev.to writeup on AI-driven architecture diagrams via MCP](https://dev.to/thangchung/ai-driven-software-architecture-diagram-generation-automating-excalidraw-and-drawio-with-mcp-apps-3edc), [Medium walkthrough Mar 2026](https://medium.com/@siddharthkharche/claude-ai-excalidraw-how-to-generate-instant-system-architecture-diagrams-with-mcp-11d42f610948))

### Eraser DiagramGPT

[Eraser](https://www.eraser.io/) ships [DiagramGPT](https://www.eraser.io/diagramgpt) and an [AI Architecture Diagram Generator](https://www.eraser.io/ai/architecture-diagram-generator) — plain-English to sequence/flow/ER/cloud/data-flow diagrams. Strongest of the diagram-only AI tools.

### Cloudcraft (Datadog) — Live experience

[Cloudcraft](https://www.cloudcraft.co/) (acquired by Datadog) revamped "Live experience" auto-generates and continuously updates diagrams of multi-region AWS/Azure environments, with cost calculator + region/VPC/SG filters. ([Cloudcraft Live announcement](https://blog.cloudcraft.co/produce-clear-easy-to-understand-diagrams-instantly-with-cloudcrafts-new-live-experience/)) Reverse direction from Cloudwright (live cloud → diagram, vs prompt → diagram), but covers the cost story Cloudwright covers.

### gofireflyio/aiac

Open-source CLI ([gofireflyio/aiac on GitHub](https://github.com/gofireflyio/aiac), [aiac.dev](https://aiac.dev/)) — generates Terraform/Pulumi/Helm/CloudFormation/Dockerfile/CI configs from NL via OpenAI/Bedrock/Ollama. Apache-2.0. Closest in spirit to Cloudwright's CLI but does not produce a structured ArchSpec, no diagrams, no cost/compliance.

### TerraFormer (academic)

[TerraFormer arXiv paper](https://arxiv.org/html/2601.08734) — fine-tunes LLMs for Terraform via policy-guided verifier feedback. Reports +15.94% on IaC-Eval, +11.65% on TF-Gen, +19.60% on TF-Mutn over base LLM. Worth tracking as an evaluation methodology even if not a product.

### Wing (winglang)

[Winglang](https://www.winglang.io/) — preflight (infra) + inflight (runtime) in one language, compiles to Terraform/CloudFormation. The startup is reportedly winding down but the open-source language continues. ([The New Stack: Wing — startup failed but language has potential](https://thenewstack.io/wing-the-startup-failed-but-the-language-has-potential/)) Different abstraction (program → infra, not prompt → infra) but in the same conceptual neighborhood.

### Diagrid, Zeet — adjacent dev platforms

The existing doc lists these but neither is a direct Cloudwright competitor in 2026; both stayed in their lanes (Dapr-as-a-service / app deploy). Mention only to keep the matrix honest.

---

## 3. MCP / Agent-Tool Landscape

The MCP server space exploded in early 2026 — [Glama's registry now indexes 22,536 servers](https://glama.ai/mcp/servers) and provides health checks, quality scores, in-browser inspector sessions, and usage telemetry. Curated lists in the cloud/IaC slice:

- [TensorBlock/awesome-mcp-servers — infrastructure docs](https://github.com/TensorBlock/awesome-mcp-servers/blob/main/docs/infrastructure.md)
- [rohitg00/awesome-devops-mcp-servers](https://github.com/rohitg00/awesome-devops-mcp-servers)
- [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)
- [awslabs/mcp](https://github.com/awslabs/mcp) — AWS official
- [hashicorp/terraform-mcp-server](https://github.com/hashicorp/terraform-mcp-server)
- [severity1/terraform-cloud-mcp](https://github.com/severity1/terraform-cloud-mcp)

**Direct cloud/IaC MCP overlap with Cloudwright:**

| Server | What it does | Overlap with Cloudwright |
|---|---|---|
| AWS Cloud Control MCP | NL CRUD on AWS resources | Same NL surface, different scope (provisions, doesn't design) |
| HashiCorp Terraform MCP | Provider/module/policy lookup + workspace mgmt | Lookup overlap, not design-time |
| Spacelift Intent | NL-to-IaC with policy gates | **Direct competitor** |
| Excalidraw Architect MCP | NL → diagram (with auto-layout) | **Direct competitor on diagrams** |
| Pulumi Neo + Integration Catalog | Pulumi-flavored execution agent | Adjacent, not identical |
| Clanker Cloud MCP | Unified multi-cloud control plane | **Direct competitor on "one tool, all clouds"** |

**White space (MCP-specific):** No MCP server today produces a **structured ArchSpec as an artifact you can pass between agents**. Every existing MCP either (a) takes NL and acts on a cloud, or (b) takes NL and renders a diagram. None emit a typed, validated, agent-friendly intermediate representation that downstream agents can consume. Cloudwright's `cloudwright-ai-mcp` package can stake this ground if positioned correctly.

---

## 4. Virality Case Studies (with attribution and the lever they pulled)

### Lovable — $0 → $100M ARR in 8 months

[Lovable hit $100M ARR in 8 months](https://medium.com/@aftab001x/the-2026-ai-coding-platform-wars-replit-vs-windsurf-vs-bolt-new-f908b9f76325), reportedly the fastest-growing startup in history. Lever: **deploy on the same screen as you describe** — no handoff, no terminal. The friction-removal is brutal and obvious in 30 seconds.

### Replit Agent 3 (Sep 2025)

Revenue jumped from $10M to $100M in 9 months after launching Agent. Agent 3 added 10x more autonomy, real-browser testing, and the ability to generate *other* agents and automations. ([digitalapplied comparison](https://www.digitalapplied.com/blog/v0-lovable-bolt-ai-app-builder-comparison)) Lever: **autonomy ladder** — let people start in chat-mode and graduate to "go fix it yourself" without re-learning the tool.

### Bolt.new — WebContainer surprise

StackBlitz's Bolt.new ran a full Node.js environment **in the browser** — no setup, no install. Lever: **the demo IS the product** — first 5 seconds of the URL are the entire pitch.

### GitDiagram — 23k stars from a URL trick

[GitDiagram](https://gitdiagram.com/) — paste a GitHub URL, swap "hub" for "diagram" in the URL bar, get a Mermaid map of the repo. ([BrightCoding writeup](https://www.blog.brightcoding.dev/2025/10/24/%F0%9F%9A%80-gitdiagram-the-viral-tool-that-converts-github-repos-into-interactive-diagrams-2025-safety-seo-guide), [Product Hunt listing](https://www.producthunt.com/products/gitdiagram-2)) Lever: **the URL hack itself is the meme** — it's screenshot-able, shareable on Twitter without context, and the discovery moment ("wait you can really just swap a word?") does the marketing for free.

### Repomix

[Repomix](https://repomix.com/) packs a repo into a single AI-friendly file. Nominated for JSNation Open Source Awards 2025. Lever: **a single command that produces a single file** — solves a specific, painful, recurring developer problem (feeding a codebase to an LLM) in one shell call.

### Astral uv — 126M monthly downloads

[uv](https://github.com/astral-sh/uv) is now reportedly being acquired by OpenAI. Lever: **strict drop-in replacement** with a 10–100x speedup; no behavior change required. Combined with `curl ... | sh` install simplicity. ([Aihola: OpenAI Acquires Astral](https://aihola.com/article/openai-acquires-astral))

### Bun

Lever: **all-in-one binary** (runtime + package manager + bundler + test runner). The pitch "no ecosystem gymnastics" resonates because Node tooling fatigue is real. ([Medium: Why everyone is suddenly talking about Bun, HTMX, and Server Actions](https://medium.com/@thedevinsider/why-everyone-is-suddenly-talking-about-bun-htmx-and-server-actions-c2d59154a0d1))

### htmx

Lever: **selective minimalism** — write less JS, get most of the JS app outcomes. Sells nostalgia + relief simultaneously.

### Shadcn UI — 85.5k stars, "default UI lib of LLMs"

[Shadcn/ui](https://github.com/shadcn-ui/ui) introduced **copy-paste-and-own-the-code** distribution. Vercel v0, Bolt, and Lovable all build on it. ([RedMonk: The Revenge of Copypasta](https://redmonk.com/kholterhoff/2025/04/22/ui-component-libraries-shadcn-ui-and-the-revenge-of-copypasta/)) Lever: **distribution-as-a-philosophy** — own your code, no version-bump dread, AI tools love it because the source is right there.

### Warp — open-sourced terminal Apr 2026

[Warp open-sourced its terminal client on 2026-04-28 under Apache-2.0](https://www.everydev.ai/p/news-warp-opensourced-its-terminal-code-the-real-product-is-oz). Repo went to ~26k stars within hours; the "real product" remained Oz (their AI dev environment). Lever: **monetize the agent layer, give away the surface** — a model Cloudwright could mirror (give away local CLI/web; build an "Oz" for teams).

### Cursor

Won 2024–2025 by being the best VS Code fork with AI baked in. Lever: **familiar shell + AI native** — minimal switching cost, telepathic tab completion. ([NxCode comparison 2026](https://www.nxcode.io/resources/news/best-ai-code-editor-2026-cursor-windsurf-copilot-zed-compared))

### Vercel v0

Drop a sketch / Figma / prompt → working React + Tailwind code, all running in StackBlitz. Lever: **paste-and-iterate in browser**, no clone-and-install gate.

---

## 5. White-Space Gaps in IaC-AI / Architecture-AI

After surveying ~30 tools, these gaps are real and Cloudwright can stake unique ground in several:

1. **Local-first, MIT-licensed, runnable-without-an-account.** Every serious "NL → Terraform" tool except Spacelift Intent and aiac is SaaS or commercial-source. Cloudwright is the only one that bundles cost + compliance + IaC + diagrams in one local install. Spacelift Intent is the closest competitor; its association with the Spacelift commercial product limits "I can run this offline" framing.
2. **Structured intermediate representation (ArchSpec).** Every tool today goes prompt → code or prompt → diagram. None expose a typed, validated, agent-consumable spec as the artifact. Cloudwright's ArchSpec is unique. Brainboard has a model internally but it's not exposed.
3. **MCP server that returns a diff/spec instead of a side effect.** Existing cloud-IaC MCPs (AWS Cloud Control, Terraform MCP, Pulumi Neo) all act on infrastructure or registries. None produce a planning artifact agents can pass around.
4. **One-shot demo that fits a single GIF.** The market is full of multi-step product tours. Lovable and v0 won by having a 30-second demo. Cloudwright's "type one sentence, get diagram + cost + compliance + Terraform" fits that bar — but the demo GIF on the README needs to be the entire pitch, not just the chat box.
5. **Pricing-aware design.** Cloudcraft (Datadog) covers cost on existing infra; Brainboard covers cost in design. No open-source tool combines NL design + provider-accurate pricing in one shot.
6. **Compliance-aware design.** AccuKnox, Aikido, Wiz, Orca all scan post-hoc. StackGen claims policy-aware generation. Cloudwright's "compliance at design time" pitch has only Brainboard and StackGen as direct competition, both SaaS.
7. **Agent-team collaboration on shared spec.** No tool today supports "two agents argue over the same architecture spec, return reconciled output." This is a clear next step given MCP momentum.
8. **AGENTS.md-aware generation.** Pulumi Neo just shipped this. Cloudwright should match — read AGENTS.md to learn project conventions before generating.
9. **Reverse-direction (live cloud → ArchSpec).** Cloudcraft and System Initiative do live import; nobody emits a Cloudwright-shaped spec from real infrastructure. Bidirectional spec sync is unclaimed.
10. **Demo distribution: GitDiagram-style URL trick.** No IaC-AI tool has a viral URL hack. A `cloudwright.dev/<github-org>/<repo>` URL that auto-generates an architecture spec from a public repo would be a GitDiagram-class moment.

---

## 6. Specific Copy-Worthy Patterns (with attribution)

### Distribution & demo

- **GitDiagram URL hack** — swap one word in the URL, get a different artifact. Cloudwright equivalent: paste a GitHub URL, get an inferred ArchSpec + cost estimate. ([GitDiagram on Product Hunt](https://www.producthunt.com/products/gitdiagram-2))
- **Repomix one-liner** — `npx repomix` produces a single file. Cloudwright equivalent: `pipx run cloudwright-ai 'a fastapi service on aws with rds'` produces spec + tf + diagram + cost. ([Repomix repo](https://github.com/yamadashy/repomix))
- **VHS .tape demos** — Charm's [VHS](https://github.com/charmbracelet/vhs) compiles a `.tape` script to a deterministic GIF. Better than asciinema for README pyrotechnics because frames are reproducible. The Cloudwright README should ship `.tape` files alongside its GIFs.
- **Warp's "open-source the surface, monetize the agent"** — Apache-2.0 the terminal, build "Oz" on top. Cloudwright's MIT core is already aligned; "Cloudwright Cloud" / "Cloudwright Enterprise" can fit the same envelope without changing the license posture. ([Warp open-source story](https://www.everydev.ai/p/news-warp-opensourced-its-terminal-code-the-real-product-is-oz))

### Product framing

- **Lovable's "describe and deploy on one screen"** — collapse the design → ship gap. Cloudwright equivalent: "describe an architecture and merge a Terraform PR on one screen." A button that opens a draft PR against a target repo from the web UI would be a directly Lovable-shaped move.
- **Pulumi's "Review / Balanced / Auto" modes** — graduated autonomy. Cloudwright equivalent: dry-run / review-each-step / generate-and-apply. ([Pulumi Neo](https://www.pulumi.com/product/neo/))
- **AGENTS.md as a context primitive** — Cloudwright reading `AGENTS.md` and `.cloudwright/conventions.md` would let teams encode "we always use VPC X, never use Glacier, prefer eu-west-3" as constraints. ([AGENTS.md adoption](https://www.pulumi.com/blog/pulumi-neo-now-supports-agentsmd/))
- **Shadcn's "own your code" framing** — the Terraform Cloudwright generates lives in your repo, no version pinning, no upgrade dread. Frame this explicitly in marketing copy. ([Shadcn philosophy](https://ui.shadcn.com/docs))
- **Spacelift's "vibe-coding infrastructure"** — claim the headline space before someone else does. Cloudwright's actual positioning is more rigorous than vibe-coding (we emit a spec) but the term is doing real work in the market. ([DevOps.com Spacelift coverage](https://devops.com/spacelift-intelligence-vibe-codes-infrastructure/))

### Technical positioning

- **TerraFormer's verifier-feedback loop** — they train against IaC-Eval / TF-Gen / TF-Mutn. Cloudwright should publish benchmark numbers on the same eval suites; "we evaluate against the same IaC-Eval that academia uses" is credibility-building copy. ([TerraFormer arXiv](https://arxiv.org/html/2601.08734))
- **Excalidraw Architect MCP's split** — "AI focuses on structure, the engine handles the pixel math." Cloudwright already does this with Mermaid; the framing is the right one to copy. ([excalidraw-architect-mcp](https://github.com/BV-Venky/excalidraw-architect-mcp))
- **MCP gateway pattern (Glama)** — a hosted MCP gateway can become the "registry" surface Cloudwright doesn't yet have. ([Glama](https://glama.ai/))

### Differentiation hypotheses — validated or challenged

| Cloudwright claim | Verdict | Notes |
|---|---|---|
| (a) Structured ArchSpec as source-of-truth | **Validated** — no other tool exposes a typed agent-consumable spec | Brainboard / Spacelift / StackGen have internal models but none expose them as the artifact |
| (b) Local / open / Python | **Mostly validated** — Spacelift Intent is the closest open-source competitor | aiac is local + open but Go-flavored CLI only; no diagrams, no cost, no compliance |
| (c) Cost + compliance + IaC + diagram in one shot | **Validated** — Brainboard is closest but SaaS; Cloudcraft covers cost; StackGen covers policy; nobody bundles all four locally | This is the strongest moat |
| (d) MCP server | **Increasingly contested** — AWS, Azure, GCP, HashiCorp, Spacelift, Pulumi all have MCP servers now | Cloudwright's MCP needs to differentiate on the *artifact* (returns ArchSpec) not the surface |
| (e) Free | **Validated but commoditizing** — aiac, Spacelift Intent, Crossplane, OpenTofu are all free | Free is table stakes; the moat is what you do with the spec |

---

## Sources

- [Pulumi Neo product page](https://www.pulumi.com/product/neo/)
- [Pulumi Neo + AGENTS.md](https://www.pulumi.com/blog/pulumi-neo-now-supports-agentsmd/)
- [Pulumi Integration Catalog](https://www.pulumi.com/blog/neo-integration-catalog/)
- [Pulumi 2025 launches recap](https://www.pulumi.com/blog/2025-product-launches/)
- [The New Stack — Pulumi compliance backlog](https://thenewstack.io/pulumis-ai-agent-tackles-infrastructure-compliance-backlogs/)
- [Intellyx — Pulumi cloud automation agent (Mar 2026)](https://intellyx.com/2026/03/29/pulumi-adding-cloud-automation-ai-agent-to-mature-iac-platform/)
- [HashiCorp Terraform + Vault MCP launch](https://www.hashicorp.com/en/blog/build-secure-ai-driven-workflows-with-new-terraform-and-vault-mcp-servers)
- [hashicorp/terraform-mcp-server](https://github.com/hashicorp/terraform-mcp-server)
- [Crossplane v2.2 release](https://blog.crossplane.io/crossplane-v2-2-more-capable-more-reliable-more-observable/)
- [Crossplane v2.0 announcement](https://blog.crossplane.io/announcing-crossplane-2-0/)
- [Crossplane What's New](https://docs.crossplane.io/latest/whats-new/)
- [OpenTofu 1.12.0-beta1 announcement](https://opentofu.org/blog/help-us-test-opentofu-1-12-0-beta1/)
- [OpenTofu releases](https://github.com/opentofu/opentofu/releases)
- [Spacelift Intent product page](https://spacelift.io/intent)
- [spacelift-io/spacelift-intent (open source)](https://github.com/spacelift-io/spacelift-intent)
- [Spacelift Intelligence vibe-coding (DevOps.com)](https://devops.com/spacelift-intelligence-vibe-codes-infrastructure/)
- [SiliconANGLE — Spacelift codeless](https://siliconangle.com/2025/10/08/spacelift-enables-instant-codeless-infrastructure-provisioning-cloud-workloads/)
- [StackGen platform overview](https://stackgen.com/platform-overview)
- [StackGen + Wiz integration](https://stackgen.com/blog/securing-infrastructure-at-the-speed-of-development-introducing-stackgens-integration-with-wiz)
- [InfoQ — System Initiative multi-cloud](https://www.infoq.com/news/2025/12/system-initiative-multi-cloud/)
- [Brainboard Smart Cloud Designer](https://www.brainboard.co/features/smart-cloud-designer)
- [Brainboard "Bob" walkthrough](https://dev.to/brainboard/ai-enhanced-architecture-design-with-bob-38dm)
- [Massdriver platform v1.2.0](https://www.massdriver.cloud/blogs/changelog-version-1.2.0)
- [Resourcely + Terraform modules](https://www.resourcely.io/and/terraform-modules)
- [AWS Cloud Control API MCP Server](https://aws.amazon.com/blogs/devops/introducing-aws-cloud-control-api-mcp-server-natural-language-infrastructure-management-on-aws/)
- [awslabs/mcp](https://github.com/awslabs/mcp)
- [InfoWorld — Five MCP servers to rule the cloud](https://www.infoworld.com/article/4129024/five-mcp-servers-to-rule-the-cloud.html)
- [Google Cloud Next '26 managed MCP coverage](https://earezki.com/ai-news/2026-04-28-the-quiet-revolution-at-google-cloud-next-26-your-database-can-talk-to-your-ai-agent-no-bridge-required-published/)
- [Clanker Cloud MCP](https://clankercloud.ai/blog/headless-ai-apis-mcp-infrastructure-layer-2026)
- [excalidraw/excalidraw-mcp](https://github.com/excalidraw/excalidraw-mcp)
- [yctimlin/mcp_excalidraw](https://github.com/yctimlin/mcp_excalidraw)
- [BV-Venky/excalidraw-architect-mcp](https://github.com/BV-Venky/excalidraw-architect-mcp)
- [Excalidraw + draw.io + MCP guide](https://dev.to/thangchung/ai-driven-software-architecture-diagram-generation-automating-excalidraw-and-drawio-with-mcp-apps-3edc)
- [Eraser DiagramGPT](https://www.eraser.io/diagramgpt)
- [Eraser AI Architecture Generator](https://www.eraser.io/ai/architecture-diagram-generator)
- [Cloudcraft Live experience](https://blog.cloudcraft.co/produce-clear-easy-to-understand-diagrams-instantly-with-cloudcrafts-new-live-experience/)
- [gofireflyio/aiac](https://github.com/gofireflyio/aiac)
- [aiac.dev](https://aiac.dev/)
- [TerraFormer arXiv paper](https://arxiv.org/html/2601.08734)
- [Winglang](https://www.winglang.io/)
- [The New Stack — Wing](https://thenewstack.io/wing-the-startup-failed-but-the-language-has-potential/)
- [Glama MCP registry](https://glama.ai/)
- [Glama servers index](https://glama.ai/mcp/servers)
- [TensorBlock awesome-mcp-servers infrastructure docs](https://github.com/TensorBlock/awesome-mcp-servers/blob/main/docs/infrastructure.md)
- [rohitg00/awesome-devops-mcp-servers](https://github.com/rohitg00/awesome-devops-mcp-servers)
- [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)
- [shuaibiyy/awesome-tf](https://github.com/shuaibiyy/awesome-tf)
- [pulumiverse/awesome-pulumi](https://github.com/pulumiverse/awesome-pulumi)
- [awesomelistsio/awesome-iac](https://github.com/awesomelistsio/awesome-iac)
- [GitDiagram on BrightCoding](https://www.blog.brightcoding.dev/2025/10/24/%F0%9F%9A%80-gitdiagram-the-viral-tool-that-converts-github-repos-into-interactive-diagrams-2025-safety-seo-guide)
- [GitDiagram on Product Hunt](https://www.producthunt.com/products/gitdiagram-2)
- [Repomix](https://repomix.com/)
- [yamadashy/repomix](https://github.com/yamadashy/repomix)
- [Lovable / Bolt / Replit / v0 comparison (Medium 2026)](https://medium.com/@aftab001x/the-2026-ai-coding-platform-wars-replit-vs-windsurf-vs-bolt-new-f908b9f76325)
- [v0 vs Lovable vs Bolt comparison](https://www.digitalapplied.com/blog/v0-lovable-bolt-ai-app-builder-comparison)
- [Astral uv](https://github.com/astral-sh/uv)
- [Aihola — OpenAI acquires Astral](https://aihola.com/article/openai-acquires-astral)
- [Why everyone is talking about Bun, HTMX, Server Actions](https://medium.com/@thedevinsider/why-everyone-is-suddenly-talking-about-bun-htmx-and-server-actions-c2d59154a0d1)
- [shadcn-ui/ui repo](https://github.com/shadcn-ui/ui)
- [RedMonk — Revenge of Copypasta](https://redmonk.com/kholterhoff/2025/04/22/ui-component-libraries-shadcn-ui-and-the-revenge-of-copypasta/)
- [Warp open-sources terminal Apr 2026](https://www.everydev.ai/p/news-warp-opensourced-its-terminal-code-the-real-product-is-oz)
- [Cursor / Windsurf / Zed comparison (NxCode 2026)](https://www.nxcode.io/resources/news/best-ai-code-editor-2026-cursor-windsurf-copilot-zed-compared)
- [Charm VHS (terminal GIF recorder)](https://github.com/charmbracelet/vhs)
- [Show HN: Terraform LLM plan summaries](https://news.ycombinator.com/item?id=43427770)
