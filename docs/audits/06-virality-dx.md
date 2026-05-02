# Cloudwright DX Research: What Makes a Developer Tool Feel Invisible

Date: 2026-05-01
Scope: Patterns from npx/uvx/pipx, curl-pipe-sh installers, BYOK UX, viral READMEs, MCP/IDE distribution, background-magic tools, trust/transparency surfaces, and cost UI. Tailored to Cloudwright's user (cloud engineer, platform team) and product (pip-installable CLI + web UI + MCP server, NL-to-cloud-architecture).

---

## 1. One-Command Magic — the State of the Art

### Pattern: "npx create" / "uvx run"

The dominant viral onboarding shape today is `<runner> <package> [args]`. No global install, no prereq, immediate output. `npx vercel` famously deploys a project to a public URL in under 60 seconds, often before the user has even created an account, hitting the industry's "time to first working example" benchmark of under 5 minutes ([Developer Onboarding Optimization](https://business.daily.dev/resources/developer-onboarding-optimization-from-first-click-to-paying-customer/)). The "three-command rule" (`init` → `cd` → `dev`) underpins almost every successful framework, from Next.js to Astro.

`bunx` is roughly 100x faster than `npx` for locally cached packages ([bunx — Bun](https://bun.com/docs/pm/bunx)). `pnpm dlx` does the same on the pnpm side ([pnpm dlx](https://pnpm.io/cli/dlx)). The Python equivalents are `pipx run` and `uvx`. `uv` itself is the standout: a single 2 MB Rust binary that replaces pip + virtualenv + poetry and installs packages 10–100× faster, with `uv run` auto-creating environments behind the scenes ([uv — astral-sh/uv](https://github.com/astral-sh/uv), [uv: A Complete Guide](https://pydevtools.com/handbook/explanation/uv-complete-guide/)).

The friction differential is real. Switching between managers "creates more friction than any speed difference could justify" ([pnpm vs npm vs yarn vs Bun: 2026 Showdown](https://dev.to/pockit_tools/pnpm-vs-npm-vs-yarn-vs-bun-the-2026-package-manager-showdown-51dc)) — but inside one ecosystem, instant-run commands are now the default expectation.

**Translation to Cloudwright:** Ship a `uvx cloudwright "build me a serverless image pipeline"` invocation that works without `pip install` first. This is the single highest-leverage move — the entry experience becomes "paste one line, get a Terraform plan." Today users still need `pip install 'cloudwright-ai[cli]'` then `cloudwright chat`; that's two steps too many for the viral demo.

### Pattern: `curl ... | sh` installers

Tailscale, Bun, uv, Fly.io, Deno, and Rust's rustup all ship `curl … | sh` installers. The tradeoff is well-understood: max convenience, but every careful user is now trained to look for the security framing.

Astral (uv) leans hard into transparency: their installer hardcodes checksums of the binaries it fetches into its source, and they generate Sigstore-based attestations linking each release artifact to the GitHub Actions workflow that produced it ([Open source security at Astral](https://astral.sh/blog/open-source-security-at-astral), [Installer options | uv](https://docs.astral.sh/uv/reference/installer/)). Tailscale uses the same shape (`curl -fsSL https://tailscale.com/install.sh | sh`) and provides manual-install docs side-by-side ([Install Tailscale on Linux](https://tailscale.com/docs/install/linux)).

Sigstore's keyless signing has become the trust primitive: developers authenticate via OIDC, Fulcio issues a short-lived signing certificate, Rekor logs the signing event publicly ([Sigstore: Software Supply Chain Trust](https://www.redhat.com/en/blog/sigstore-open-answer-software-supply-chain-trust-and-security)). cosign verification is now standard for npm provenance, GitHub Artifact Attestations, and Homebrew ([cosign Verification of npm Provenance](https://blog.sigstore.dev/cosign-verify-bundles/)).

**Translation to Cloudwright:** Add a `curl -fsSL https://cloudwright.dev/install.sh | sh` route alongside pip. Most cloud engineers ALREADY trust the same curl-pipe-sh shape from Tailscale/Terraform/Bun. Pair with Sigstore attestations on the GitHub release workflow so security-sensitive teams can verify the wheel back to the source SHA.

### Pattern: Homebrew tap + cask

Raycast ships as `brew install --cask raycast`; Ollama ships as `brew install ollama` ([raycast — Homebrew Formulae](https://formulae.brew.sh/cask/raycast)). For Mac-heavy developer audiences (cloud engineers skew Mac), this is non-negotiable distribution. A formula keeps install/update one command for the lifetime of the tool.

**Translation to Cloudwright:** Open `brew tap cloudwright/cloudwright` + `brew install cloudwright`. Homebrew handles the auto-update path that pip currently doesn't. Many cloud engineers have `brew bundle` Brewfiles checked into their dotfiles — being one line in there is durable distribution.

---

## 2. Zero-Config Setup — No API Key on First Run

The trust threshold for "I will paste this into my terminal" is much lower than "I will go get an API key." Three patterns dominate:

### Local model fallback

Ollama exposes a localhost API at `http://localhost:11434` by default — no key, no signup, offline-capable, and "Docker for AI models" as the mental model ([The Complete Guide to Ollama](https://dev.to/ajitkumar/the-complete-guide-to-ollama-run-large-language-models-locally-2mge)). Llamafile is even more aggressive: a single double-clickable binary that runs a CLI chatbot in the foreground and a server in the background ([Ollama Alternatives — Llamafile](https://localllm.in/blog/complete-guide-ollama-alternatives)).

### Hosted free tier with rate limit

v0.dev gives $5 of credits monthly with no credit card ([v0 vs Bolt.new vs Lovable](https://www.nxcode.io/resources/news/v0-vs-bolt-vs-lovable-ai-app-builder-comparison-2025)). Bolt.new offers 1M tokens/month with a 300K daily cap on a free Bolt URL ([Bolt vs Lovable Pricing 2026](https://www.nocode.mba/articles/bolt-vs-lovable-pricing)). Lovable: 5 credits/day, hit $20M ARR in 2 months partly because of zero-friction first-touch ([v0 vs Bolt.new vs Lovable](https://www.nxcode.io/resources/news/v0-vs-bolt-vs-lovable-ai-app-builder-comparison-2025)).

### BYOK that doesn't suck

Cursor's BYOK lives in `Cursor Settings > Models` and supports OpenAI/Anthropic/Google/Azure/Bedrock with paste-and-validate ([Cursor — API Keys](https://docs.cursor.com/settings/api-keys)). Cline (open-source, VS Code) puts provider config behind a gear icon, with "one of the most flexible provider configs among AI coding tools" ([Cline VS Code Guide](https://www.deployhq.com/guides/cline)). The shared shape: paste key, sees a green check, you're in.

A subtle anti-pattern: Cursor's "Agent and Edit" features cannot be billed to an API key — they require Cursor's metered subscription. This created backlash because users expected BYOK to mean "all features" ([How to Fix Cursor BYOK Ban](https://apidog.com/blog/cursor-byok-ban-alternative/)). Honesty about what BYOK covers matters more than coverage itself.

**Translation to Cloudwright:** Cloudwright already supports BYOK for Anthropic. The missing piece is a **no-key first-run path**: ship a tiny canned demo that runs without any API call (a pre-baked "S3 + Lambda + DynamoDB" arch spec rendered locally), so `cloudwright chat --demo` produces a Terraform plan + diagram in under 5 seconds with zero setup. Plus an Ollama fallback (`--llm ollama:llama3`) for cloud engineers who refuse to send YAML/Terraform to Anthropic. The "I have to trust my YAML to ChatGPT" friction is real — local-first-as-an-option is a credibility multiplier.

---

## 3. Demo Virality — README/Landing Formula

### The 3-second GIF rule

The README gold standard: a single animated GIF immediately under the H1 that answers "what does this do" before any text. Tools that nailed it:

- **GitDiagram** went viral on a 30-second mental-model demo ("Day 1 at OpenAI – they handed us a 400k-line codebase. GitDiagram gave me the mental model in 30s" — 1.2M views) ([GitDiagram — viral tool](https://www.blog.brightcoding.dev/2025/10/24/%F0%9F%9A%80-gitdiagram-the-viral-tool-that-converts-github-repos-into-interactive-diagrams-2025-safety-seo-guide), [ahmedkhaleel2004/gitdiagram](https://github.com/ahmedkhaleel2004/gitdiagram)). The hook: replace `hub` with `diagram` in any GitHub URL.
- **Aider, uv, Bun** — every release post leads with a terminal GIF.
- **shadcn/ui** leads with the literal `npx shadcn add button` command, no marketing copy first.

### Recording tooling

The two reigning stacks:

- **VHS (charmbracelet)** — write the demo as a `.tape` file, version-control it, regenerate on every release. Reproducible terminal demos as code ([charmbracelet/vhs](https://github.com/charmbracelet/vhs), [orangekame3/awesome-terminal-recorder](https://github.com/orangekame3/awesome-terminal-recorder)).
- **asciinema + agg** — record once, render to GIF deterministically ([agg — asciinema gif generator](https://github.com/asciinema/agg)). agg has 1.6k stars and is the canonical converter.

For web app demos, ScreenStudio and Kap dominate Mac; LICEcap remains the cross-platform fallback.

### Live embeds

"Open in StackBlitz" / "Open in Codespaces" buttons let a reader try the tool before deciding to install ([Adding a GitHub Codespace button to your README](https://dev.to/azure/adding-a-github-codespace-button-to-your-readme-5f6l), [StackBlitz launch from GitHub](https://developer.stackblitz.com/guides/integration/open-from-github)). StackBlitz's `pr.new` lets PR reviewers open a PR-as-IDE in one click ([Using pr.new](https://developer.stackblitz.com/codeflow/using-pr-new)).

### shadcn/ui's distribution model — copy/paste over npm-install

shadcn/ui is the most-copied DX pattern of 2025–2026. Its registry isn't an npm package; it's source code that the CLI copies into your project. `npx shadcn add` is "npm for components that you own outright" — no version pinning, no breaking-change anxiety, you fork on day one ([Introduction — shadcn/ui Registry](https://ui.shadcn.com/docs/registry), [What is a Component Registry?](https://vercel.academy/shadcn-ui/what-is-a-component-registry)). Registries can now distribute an entire design system as a single payload ([shadcn/cli v4 changelog](https://ui.shadcn.com/docs/changelog/2026-03-cli-v4)).

**Translation to Cloudwright:** Three actions:
1. Replace the current README hero with a 6-second GIF of `cloudwright "image upload pipeline" → diagram + terraform plan`. Use VHS so it regenerates on each release (Cloudwright already has a [demo recording playbook](reference_demo_recording.md)).
2. Add an "Open in StackBlitz" button for the web UI demo (the React app already builds locally; a StackBlitz template is one config away).
3. Build a Cloudwright "module catalog" registry on the shadcn pattern — `cloudwright add module/serverless-image-pipeline` copies the YAML into the user's repo. v1.2.0 already has the module catalog primitive; the missing layer is the public registry + CLI install path.

---

## 4. Editor / Agent Integration as Distribution

### MCP server registries

The MCP ecosystem matured fast. Claude Desktop now ships a native Connectors panel + Extensions marketplace; users browse and install MCP servers without editing JSON ([How to Set Up MCP in Claude Desktop 2026](https://mcpplaygroundonline.com/blog/how-to-setup-mcp-claude-desktop)). ToolHive Desktop has a Skills section that installs MCP servers across Claude Code, Cursor, and Windsurf from a shared registry ([Stacklok ToolHive updates](https://docs.stacklok.com/toolhive/updates/2026/04/27/updates)). The official `modelcontextprotocol/servers` GitHub registry is the canonical list; secondary discovery happens via MCPRepository.com, MCP Linker, and MCP Hunt ([MCP Servers List 2026](https://tokenmix.ai/blog/mcp-servers-list-2026-complete-directory)). The MCP config JSON is now identical across Claude Desktop / Claude Code / Cursor — one config covers three clients ([Complete Guide to MCP Config Files](https://mcpplaygroundonline.com/blog/complete-guide-mcp-config-files-claude-desktop-cursor-lovable)).

### VS Code marketplace dynamics

The marketplace's primary surface metric is install count, sortable via `@sort:installs` ([Extension Marketplace](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace)). VSCodeRank (using the official Marketplace API) confirms install count + ratings drive ranking ([VSCodeRank](https://www.vscoderank.com/)). Translation for new tools: getting the first 1k installs from a single viral GIF is the entire game.

### Rule files as embedded distribution

Cursor's `.cursorrules`, Claude Code's `CLAUDE.md`, Cline's instruction files — these are distribution surfaces. Tools that ship a recommended rules file get pulled into every "starter pack" repo. The shadcn-style copy-paste applies again.

**Translation to Cloudwright:** Cloudwright already ships an MCP server. The missing distribution work:
1. Submit `cloudwright-mcp` to the official MCP registry, MCP Hunt, MCPRepository — a one-time action with multi-year discovery upside.
2. Ship a `CLAUDE.md`/`.cursorrules` snippet that teaches agents how to call Cloudwright's MCP tools effectively. When users `npx shadcn add`-style copy these into their repos, Cloudwright becomes ambient.
3. The MCP config-once-works-everywhere story should be the README's second screenshot.

---

## 5. Background Magic — the Invisible Pattern

Tools that run *as you work* without asking. The canonical examples:

- **Vercel preview URLs** — every PR gets a live URL automatically. No command, no menu, just a comment from the bot.
- **Copilot completions** — fires on every keystroke; you accept or reject.
- **Sentry alerts** — detect, no setup beyond the initial DSN.
- **Stripe Atlas** — handles incorporation paperwork in the background; you click "go" and emails arrive.
- **Doppler env sync** — replaces `.env` files; secrets show up locally without a manual pull.

### Just-in-time triggers

Pre-commit hooks, GitHub Apps that auto-comment, IDE squigglies, "you might want to" nudges. The collaborative-vs-annoying split is mostly about volume control:

- **Dependabot** opens 1 PR per dependency — 100 deps = 100 PRs, classic alert fatigue. "Wall of PRs."
- **Renovate** groups updates intelligently (e.g., 20 eslint plugins → 1 PR), reducing noise 80–90%, plus a Dependency Dashboard ([Renovate vs Dependabot 2026](https://appsecsanta.com/sca-tools/dependabot-vs-renovate), [Bot comparison — Renovate Docs](https://docs.renovatebot.com/bot-comparison/)).

The lesson: a bot that fires often must group, batch, and have a dashboard. A bot that fires rarely (Vercel preview, once per push) doesn't.

**Translation to Cloudwright:** The infrastructure-equivalent of "Vercel preview URLs" doesn't exist yet. Concrete moves:

1. **GitHub App that previews infra changes**: when a PR touches `.tf` or `cloudwright.yaml`, the app posts a comment with the diagram diff + projected cost delta + security findings. One trigger per push, grouped, no key needed if BYOK is in repo secrets.
2. **terraform plan-style dry run by default**: every Cloudwright run already shows the plan before apply (`terraform plan` is the dominant trust pattern in IaC — preview catches "creating a VM with a duplicate name" or "missing security group" before damage; saved plans like `tfplan` lock proposed state for code review ([terraform plan command reference](https://developer.hashicorp.com/terraform/cli/commands/plan), [Terraform Dry Run Explained](https://spacelift.io/blog/terraform-dry-run))). Lean into this — every `cloudwright build` should make the plan/diff the headline output.
3. **Pre-commit hook**: `cloudwright lint` on staged Terraform files. Fast, local, zero-key.

---

## 6. Trust + Adoption Levers

### Show your work

v0.dev shows the prompt that produced the result. Lovable shows iterative diff. Eraser AI shows the diagram source. The shared pattern: the AI step is auditable — a human can see the input, the output, and the artifact between them, so trust is inspectable, not asserted ([AI System Prompts: 131K stars](https://www.augmentcode.com/learn/ai-tool-system-prompts-github)). The `system-prompts-and-models-of-ai-tools` GitHub repo (>131k stars) shows how much the developer audience cares about prompt transparency.

### Free tier honesty

The Cursor June 2025 pricing change was the cautionary tale: usage-based credits replaced fast-request allotments overnight, the UI didn't expose per-request cost, and the community erupted ([Changes in Cursor Pricing](https://shekhargulati.com/2025/07/05/changes-in-cursor-pricing/), [Cursor Pricing Explained 2026](https://www.vantage.sh/blog/cursor-pricing-explained)). Cursor publicly apologized and refunded ([Cursor — How can I determine per-query cost](https://forum.cursor.com/t/how-can-i-determine-the-per-query-cost-of-a-given-llm-request-in-cursor-ide/155513)). Lesson: surprise paywalls + opaque cost = brand damage that takes months to repair.

### Open-core vs full-OSS

The shadcn pattern (full source, MIT, you own it) is winning attention. Aider is open-source, you only pay for API calls — and this framing converts ([Aider Review](https://www.blott.com/blog/post/aider-review-a-developers-month-with-this-terminal-based-code-assistant)).

**Translation to Cloudwright:** Cloudwright is already open-source MIT. Surface the prompt + LLM response in the web UI as a collapsible "show your work" panel. A skeptical cloud engineer should see the system prompt, the user prompt, the parsed JSON, and the rendered Terraform side-by-side. This kills the "is this AI hallucinating my IAM policy" objection.

---

## 7. Cost / Usage Transparency

### Per-call surfaces

Cline shows total tokens and per-request cost in the chat panel, in real time, with running session totals ([Cline VS Code Guide](https://www.deployhq.com/guides/cline)). Typical session: 50k–200k tokens, $0.50–$2.00 with Sonnet ([The Real Cost of AI Coding 2026](https://www.morphllm.com/ai-coding-costs)). Aider has `/tokens` to inspect current context, `/drop` and `/clear` to prune, and tracks repo-map tokens against a `--map-tokens` budget (default 1k) so users know the floor ([Repository map | aider](https://aider.chat/docs/repomap.html), [Aider FAQ](https://aider.chat/docs/faq.html)).

Cursor's UI weakness is instructive: there's no in-editor usage panel — users must check the dashboard ([Cursor — How can I determine per-query cost](https://forum.cursor.com/t/how-can-i-determine-the-per-query-cost-of-a-given-llm-request-in-cursor-ide/155513)). That gap fueled the pricing-change backlash.

### Pre-flight estimation

Aider's `/tokens` and the repo-map budget are the canonical "before you spend" surfaces. A user can preview cost before committing.

**Translation to Cloudwright:** Cloudwright already exposes `get_usage_summary()` and `last_usage` per session. Surface these prominently:
1. Web UI footer: live "session: 12.3k tokens, $0.04" widget.
2. CLI: every `cloudwright chat` response ends with a one-line cost line `[42 tokens in / 1.2k out / $0.003 / 1.4s]`.
3. A `--dry-run --estimate` flag that runs the cheap Haiku planner and reports projected total cost before the Sonnet generation step kicks in.

---

## 8. Cloudwright-Specific Friction Dimensions

| Friction | Today | Pattern fix | Reference |
|---|---|---|---|
| "Need API key first run" | Required | Demo mode + Ollama fallback | Llamafile / v0 free credits |
| "Need to run a server" | `--web` spawns localhost | Auto-launch on first command, kill on exit | Vercel preview URLs |
| "Can't remember syntax" | `cloudwright chat` then prompt | Direct `cloudwright "<NL prompt>"` shorthand | `npx vercel`, `gh` |
| "Have to switch tools" | Standalone CLI/web | MCP server in Cursor + Claude Desktop | MCP cross-client config |
| "Trusting YAML to ChatGPT" | Anthropic-only | Local Ollama backend + on-prem story | Ollama, llamafile |

---

## Top 10 Friction-Removers Ranked by Impact (Cloudwright)

Each ranked by (a) magnitude of friction removed, (b) effort to ship, (c) virality leverage.

1. **Single-command first-run**: `uvx cloudwright "<prompt>"` — works without `pip install`. Pair with `curl ... | sh` script. Highest leverage; the README hero becomes one line. (Patterns: uv/uvx, Tailscale install.sh)

2. **Demo mode that needs no API key**: `cloudwright demo` returns a canned arch spec + Terraform plan + diagram from a prebaked example in <2 seconds. Removes "I need an Anthropic key before I can see anything." (Patterns: v0 free credits, llamafile)

3. **Replace README hero with a 6-second VHS GIF** showing `cloudwright "<NL>"` → diagram + plan + cost. Regenerated on every release via `.tape` file. (Patterns: GitDiagram, shadcn, Aider)

4. **MCP registry submission + `CLAUDE.md` snippet**: get listed on the official MCP servers repo, MCP Hunt, MCPRepository. Ship a copy-paste `CLAUDE.md` block that teaches Claude Code how to call Cloudwright's MCP tools. (Patterns: shadcn registry, MCP Linker)

5. **GitHub App that posts arch-diff + cost-delta on every PR**: zero command, fires automatically. Comment includes the diagram, terraform plan diff, and projected monthly cost change. (Patterns: Vercel preview URLs, Renovate dashboard)

6. **In-product cost transparency**: every CLI response shows `[tokens / cost / latency]`; web UI footer carries running session cost. Adds a `--estimate` flag for pre-flight. (Patterns: Cline cost tracking, Aider `/tokens`)

7. **"Show your work" panel in the web UI**: collapsible drawer with the system prompt, user prompt, parsed JSON spec, raw LLM response. Inspectable trust beats asserted trust. (Patterns: v0.dev, Eraser, Lovable diff view)

8. **Local LLM backend**: `cloudwright chat --llm ollama:llama3.1` runs entirely against localhost:11434. Removes "I won't paste my YAML into ChatGPT" objection for security-sensitive teams. (Patterns: Ollama, llamafile)

9. **Homebrew tap**: `brew install cloudwright/tap/cloudwright`. Many cloud engineers have Brewfile dotfiles — being one line in there is durable. (Patterns: Raycast, Ollama brew install)

10. **Sigstore attestations on every release**: `cosign verify cloudwright-X.Y.Z.whl` resolves back to the GitHub Actions workflow + commit SHA. Removes the "supply chain risk" friction for enterprise procurement reviews. (Patterns: Astral/uv security posture, Sigstore keyless signing)

Bottom of the iceberg, ranked by the same criteria: a Cloudwright "module registry" on the shadcn pattern (`cloudwright add module/<x>` copies YAML into the user's repo), an "Open in StackBlitz" button for the web UI, a pre-commit hook for `.tf`/`cloudwright.yaml` linting. These all compound but ship after the top 10.

---

## Sources

- [npx create-next-app — npm](https://www.npmjs.com/package/create-next-app)
- [pnpm dlx | pnpm](https://pnpm.io/cli/dlx)
- [bunx — Bun](https://bun.com/docs/pm/bunx)
- [pnpm vs npm vs yarn vs Bun: 2026 Showdown](https://dev.to/pockit_tools/pnpm-vs-npm-vs-yarn-vs-bun-the-2026-package-manager-showdown-51dc)
- [uv — astral-sh/uv](https://github.com/astral-sh/uv)
- [uv: A Complete Guide](https://pydevtools.com/handbook/explanation/uv-complete-guide/)
- [What's the difference between pip and uv?](https://pydevtools.com/handbook/explanation/whats-the-difference-between-pip-and-uv/)
- [Open source security at Astral](https://astral.sh/blog/open-source-security-at-astral)
- [Installer options | uv](https://docs.astral.sh/uv/reference/installer/)
- [Install Tailscale on Linux](https://tailscale.com/docs/install/linux)
- [Sigstore: Software Supply Chain Trust](https://www.redhat.com/en/blog/sigstore-open-answer-software-supply-chain-trust-and-security)
- [cosign Verification of npm Provenance](https://blog.sigstore.dev/cosign-verify-bundles/)
- [raycast — Homebrew Formulae](https://formulae.brew.sh/cask/raycast)
- [The Complete Guide to Ollama](https://dev.to/ajitkumar/the-complete-guide-to-ollama-run-large-language-models-locally-2mge)
- [Ollama Alternatives — Llamafile](https://localllm.in/blog/complete-guide-ollama-alternatives)
- [Cursor — API Keys](https://docs.cursor.com/settings/api-keys)
- [Cursor — Bring your own API key](https://cursor.com/help/models-and-usage/api-keys)
- [How to Fix Cursor BYOK Ban](https://apidog.com/blog/cursor-byok-ban-alternative/)
- [Cline VS Code Guide](https://www.deployhq.com/guides/cline)
- [Cline — cline/cline](https://github.com/cline/cline)
- [The Real Cost of AI Coding 2026](https://www.morphllm.com/ai-coding-costs)
- [Repository map | aider](https://aider.chat/docs/repomap.html)
- [Aider FAQ](https://aider.chat/docs/faq.html)
- [Aider Review](https://www.blott.com/blog/post/aider-review-a-developers-month-with-this-terminal-based-code-assistant)
- [Cursor — Models & Pricing](https://cursor.com/docs/models-and-pricing)
- [Changes in Cursor Pricing](https://shekhargulati.com/2025/07/05/changes-in-cursor-pricing/)
- [Cursor Pricing Explained 2026](https://www.vantage.sh/blog/cursor-pricing-explained)
- [Cursor — How can I determine per-query cost](https://forum.cursor.com/t/how-can-i-determine-the-per-query-cost-of-a-given-llm-request-in-cursor-ide/155513)
- [v0 vs Bolt.new vs Lovable](https://www.nxcode.io/resources/news/v0-vs-bolt-vs-lovable-ai-app-builder-comparison-2025)
- [Bolt vs Lovable Pricing 2026](https://www.nocode.mba/articles/bolt-vs-lovable-pricing)
- [AI System Prompts: 131K stars on GitHub](https://www.augmentcode.com/learn/ai-tool-system-prompts-github)
- [Eraser AI](https://www.eraser.io/ai)
- [charmbracelet/vhs](https://github.com/charmbracelet/vhs)
- [agg — asciinema gif generator](https://github.com/asciinema/agg)
- [orangekame3/awesome-terminal-recorder](https://github.com/orangekame3/awesome-terminal-recorder)
- [GitDiagram — viral tool](https://www.blog.brightcoding.dev/2025/10/24/%F0%9F%9A%80-gitdiagram-the-viral-tool-that-converts-github-repos-into-interactive-diagrams-2025-safety-seo-guide)
- [ahmedkhaleel2004/gitdiagram](https://github.com/ahmedkhaleel2004/gitdiagram)
- [Introduction — shadcn/ui Registry](https://ui.shadcn.com/docs/registry)
- [What is a Component Registry?](https://vercel.com/academy/shadcn-ui/what-is-a-component-registry)
- [shadcn/cli v4 changelog](https://ui.shadcn.com/docs/changelog/2026-03-cli-v4)
- [Adding a GitHub Codespace button to your README](https://dev.to/azure/adding-a-github-codespace-button-to-your-readme-5f6l)
- [StackBlitz launch from GitHub](https://developer.stackblitz.com/guides/integration/open-from-github)
- [Using pr.new | StackBlitz](https://developer.stackblitz.com/codeflow/using-pr-new)
- [How to Set Up MCP in Claude Desktop 2026](https://mcpplaygroundonline.com/blog/how-to-setup-mcp-claude-desktop)
- [MCP Servers List 2026](https://tokenmix.ai/blog/mcp-servers-list-2026-complete-directory)
- [Stacklok ToolHive updates](https://docs.stacklok.com/toolhive/updates/2026/04/27/updates)
- [Complete Guide to MCP Config Files](https://mcpplaygroundonline.com/blog/complete-guide-mcp-config-files-claude-desktop-cursor-lovable)
- [Extension Marketplace — VS Code](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace)
- [VSCodeRank](https://www.vscoderank.com/)
- [Renovate vs Dependabot 2026](https://appsecsanta.com/sca-tools/dependabot-vs-renovate)
- [Bot comparison — Renovate Docs](https://docs.renovatebot.com/bot-comparison/)
- [terraform plan command reference](https://developer.hashicorp.com/terraform/cli/commands/plan)
- [Terraform Dry Run Explained](https://spacelift.io/blog/terraform-dry-run)
- [Developer Onboarding Optimization](https://business.daily.dev/resources/developer-onboarding-optimization-from-first-click-to-paying-customer/)
