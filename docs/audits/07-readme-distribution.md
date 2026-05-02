# Cloudwright README + Demo + Distribution Playbook

**Date:** 2026-05-01
**Subject:** Research-backed recommendations for refreshing Cloudwright's README, demo strategy, and v2 launch distribution.
**Current state:** 1,279-line README, 14 sections, 14 image embeds, no clear hero artifact.

---

## 1. Structural Anatomy of a Viral OSS README in 2025–2026

The 12 references break into three archetypes. Cloudwright currently sits between Archetypes A and B and executes neither cleanly.

**Archetype A — Hero + Docs Redirect** ([shadcn](https://github.com/shadcn-ui/ui), [tldraw](https://github.com/tldraw/tldraw), [Excalidraw](https://github.com/excalidraw/excalidraw), [GitDiagram](https://github.com/ahmedkhaleel2004/gitdiagram)). First three elements: hero image, one-liner, link to live product or docs site. Minimal badges (topic tags or license + Discord). No TOC. The README is the trailer; the *next click is the live product, not more reading*. Excalidraw's hero banner is the link to excalidraw.com — there is no "scroll for more". GitDiagram's hook ("replace `hub` with `diagram` in any GitHub URL") IS the demo.

**Archetype B — Demo + Numbers + Install** ([Aider](https://github.com/Aider-AI/aider), [uv](https://github.com/astral-sh/uv), [Repomix](https://github.com/yamadashy/repomix)). First three elements: logo + tagline, demo (GIF or static benchmark chart), adoption-as-proof badge row. Install in three lines, immediately. Aider's row: 44.2k stars, 6.8M installs, 15B tokens/week, OpenRouter top 20, 88% of own code generated. uv's hero is a static bar chart — "10–100× faster than `pip`" — no motion needed because the number does the work. Repomix uses `npx repomix@latest` so install is *zero*. Each leverages a single comparative claim that's verifiable in 8 seconds.

**Archetype C — Toolkit One-liner + Code Sample** ([Bun](https://github.com/oven-sh/bun), [htmx](https://htmx.org)). Logo, badges, then immediately three code snippets. Bun: `bun run`, `bun test`, `bunx`. htmx: a live `hx-post` + `hx-swap` code example. No GIF. The pitch is the API surface. htmx sells minimalism with "~16k min.gz'd" and "67% reduction in code base sizes vs React".

**Archetype D — Web product landing** ([Bolt.new](https://bolt.new), [Lovable](https://lovable.dev), [v0.app](https://v0.app)). The CTA *is* a prompt input. Bolt's hero is "What will you build today?" with the input live above the fold. Trust elements are enterprise logos (Porsche, Material UI, Chakra). This is what HN readers expect when a "Try it" link sends them to your hosted demo.

**Cloudwright today:** 1 hero GIF, then a 4-quadrant screenshot grid, then install, then *every changelog since v0.1.0 inline*, then 7 worked examples, then 16 feature subsections. The 30-second skim never finds a single "wow" — there are 14 wows, which equals zero. Compare Aider: 1 hero GIF, 5 stat badges, install in 3 lines, done.

---

## 2. Demo GIF State of the Art

**Tool choice.** [VHS (charmbracelet)](https://github.com/charmbracelet/vhs) for terminal demos that need to regenerate in CI — tape files are scripts (Type, Sleep, Enter), and the same tape produces GIF/MP4/WebM. Settings (Set Framerate, PlaybackSpeed, font, dimensions) must go at the top of the tape — anything after a non-setting command is ignored. [asciinema](https://github.com/asciinema/asciinema) wins for "share a URL" but isn't GitHub-native. ScreenStudio and Kap are macOS-GUI tools for web-app recordings with cursor zoom on click. Playwright + ffmpeg (already in Cloudwright's `record-demo` skill) is the right path for the *web* demo because mock-LLM responses make it reproducible. The [terminal-recorder roundup](https://github.com/orangekame3/awesome-terminal-recorder) ranks VHS first for macOS/Linux scriptability.

**File-size and dimension targets** (from [GitHub community discussion #81359](https://github.com/orgs/community/discussions/81359) and the [2026 Rekort guide](https://rekort.app/blog/gif-for-github-readme)):

- Hard limit: GitHub silently shows the first frame as a static image when GIFs exceed 10 MB.
- Soft target: < 5 MB.
- Frame rate: 10–15 fps (default capture is 24–30 — overkill).
- Palette: 128–200 colors via `convert input.gif -colors 200 output.gif` cuts size 30–60%.
- Source dimensions: 800–1280 px (GitHub's content column is ~610 px; let HTML scale).
- Duration: 8–20 seconds. The best-performing demos in this research communicate the value prop in under 10.

**Format choice** (from the [DEV community guide](https://dev.to/brpaz/make-your-project-readme-file-stand-out-with-animated-gifs-svgs-4kpe) and [GitHub markup issue #1329](https://github.com/github/markup/issues/1329)): inline animation in README.md is GIF-only. GitHub doesn't render `<video>` or MP4 in README. Animated SVG works inline only if CSS is embedded in the SVG, and is best for diagrams (architecture morphs, before/after) rather than screen capture. The right pattern (used by [Scalar](https://blog.scalar.com/p/how-we-created-an-animated-responsive)): one optimized GIF inline + a "Watch full video" link to YouTube/Loom for the high-fidelity version.

**Aesthetic trends.** Three patterns converging in 2025–2026: (1) single magic-trick demo under 10 seconds (GitDiagram's URL substitution, [Show HN thread](https://news.ycombinator.com/item?id=42521769)); (2) before/after split (Linear, Cursor product launches: 12–18 seconds, manual workflow on the left, tool on the right); (3) recursion demos ("Bolt builds Bolt", "Cursor wrote 90% of Cursor"). What's *out:* 60-second feature tours. Aider's hero is a single edit-loop GIF on repeat. uv's hero is a static bar chart. Apple's Liquid Glass aesthetic in iOS 19 reinforces minimalism — heavy chrome looks dated.

**Viral case studies.** uv shipped no GIF; the static "pip 12.4s vs uv 0.3s" chart did the work ([uv on HN](https://news.ycombinator.com/item?id=42415602)). Aider's single screencast loops one edit cycle, paired with the "88% of code self-generated" stat ([Aider on HN](https://news.ycombinator.com/item?id=39995725)). GitDiagram's eight-second URL trick hit HN front page on a static screenshot. Bun's benchmarks are tabular (Bun vs Node vs Deno), not motion. **Common pattern: one keystroke or one number, under 10 seconds, no narration.**

---

## 3. Distribution Channels for a Python+Web Dev Tool v2 Launch

**Hacker News (Show HN)** is the single highest-leverage channel. From [Calmops](https://calmops.com/indie-hackers/hacker-news-launch-500-upvotes/), [markepear.dev](https://www.markepear.dev/blog/dev-tool-hacker-news-launch), and the [Viral Potential Predictor](https://hn-ph.vercel.app): use the title pattern `Show HN: <Tool> – <One concrete capability>` at 40–80 characters; avoid superlatives ("fastest", "best") — HN downweights them. Best window is Tuesday/Wednesday 7–9am Pacific (front-page residency lasts longer earlier in the week). Posts with images, a working demo URL, and the author replying in the first 30 minutes outperform. 93.2% of submissions never hit 50 points; the top 1% starts at 270 ([HN ranking analysis](https://news.ycombinator.com/item?id=44625897)). Titles that worked: *"Show HN: Sidekick – A browser extension that surfaces relevant docs"* (487 upvotes), *"Show HN: Codemod – Automate large-scale codebase refactors"* (623 upvotes, 10K stars).

**Reddit** is selective and rule-bound ([DevOps marketing guide](https://business.daily.dev/resources/how-to-market-developer-tools-on-reddit-practical-guide/), [r/devops guide](https://leadline.dev/guides/reddit-subreddits/r-devops)). r/devops (650k+) allows tool launches only with genuine technical depth (post-mortem, comparison data); surface-level launches get removed. r/Python (1.3M) accepts genuinely Python-native tools, not "general tool with a Python client". r/aws and r/Terraform are anti-promotion — best entry is to *comment* with your tool as a solution on others' problems. Most professional subs gate on 30–90 day account age and 100–500 karma.

**Lobsters** ([lobste.rs](https://lobste.rs)) is invite-only and ~10–20% of HN reach, but the discussion is higher quality. Cross-post if you have an invite; never primary.

**Newsletters** (from the [developer newsletter directory](https://github.com/jackbridger/developer-newsletters)): [TLDR](https://tldr.tech) (1.5M+ general dev, editorial submission via contact form), Pointer (engineering leaders, curator picks), Bytes (JS-heavy, sponsor model), [Pragmatic Engineer](https://newsletter.pragmaticengineer.com) (senior engineers; Gergely curates personally — pitch via Twitter/email with a deeply technical write-up, not a press release), Software Lead Weekly (eng managers), and Last Week in AWS (Corey Quinn — strong fit for Cloudwright's cost angle). TLDR drives volume but shallow visits; **Last Week in AWS + Pragmatic Engineer are the higher-leverage targets** for a cloud-architecture tool.

**YouTube creators** ([Fireship](https://www.youtube.com/@Fireship), [ThePrimeagen](https://www.youtube.com/@ThePrimeagen), [Theo](https://www.youtube.com/@t3dotgg)) have no formal submission. Get on HN front page first — Fireship's "X in 100 seconds" picks the week's trending tools. Have a 30-second magic-trick demo they can drop into a video without setting up. Tag on Twitter/X — Theo and Prime check mentions; cold email rarely lands.

**Conferences (late 2026)** from [LF Events](https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/): KubeCon NA 2026 in Salt Lake City Nov 9–12 — co-located events CFP opens **April 29, 2026** (now). KubeCon EU 2026 CFP closed Oct 12, 2025. AWS re:Invent CFPs typically open June with August decisions. [DevOpsDays](https://devopsdays.org) runs city-specific CFPs year-round.

**Podcasts:** [The Changelog](https://changelog.com) (OSS spotlights — submit at changelog.com/community/submit), [Practical AI](https://practicalai.fm) (AI tools), [Software Engineering Daily](https://softwareengineeringdaily.com) (senior engineers).

**Bluesky/Mastodon vs X:** X still dominates dev-tool launch reach. Bluesky has 5.3M MAU concentrated around tech-skeptical devs ([TechCrunch](https://techcrunch.com/2024/03/11/bluesky-is-funding-developer-projects-to-give-its-twitter-x-alternative-a-boost/)); Mastodon under 700K. Cross-post, don't replace. LinkedIn works for enterprise-positioned tools (compliance, FinOps, governance) — Cloudwright's compliance + cost angle has a real LinkedIn audience but a terminal-only tool doesn't.

---

## 4. Specific Tactics That Worked in 2025–2026 Launches

- **[Repomix](https://github.com/yamadashy/repomix):** rebranded from Repopack Dec 2024; > 24k stars by mid-2025. Hook: "pack your entire repo into a single AI-friendly file." Zero install (`npx repomix@latest`). Web playground at repomix.com.
- **[GitDiagram](https://news.ycombinator.com/item?id=42521769):** zero-friction hook — "replace `hub` with `diagram` in any GitHub URL". HN front page on a static screenshot.
- **Bolt.new:** "build itself" recursion (Bolt cloning Bolt's UI live during launch) was the talking point at every conference for two months in late 2024.
- **[Aider](https://github.com/Aider-AI/aider):** "% of own code written by Aider" stat (88%) became self-fulfilling proof. Updated on every release.
- **[uv](https://github.com/astral-sh/uv):** "10–100× faster than pip" with a benchmark chart, no GIF. Astral acquired by OpenAI Q1 2026 — uv is now de facto Python package manager.
- **[Cline](https://cline.bot/blog/top-9-cursor-alternatives-in-2025-best-open-source-ai-dev-tools-for-developers-2):** positioned as "free Cursor alternative" exactly when Cursor's June 2025 pricing change hit. 5M installs in 2025.
- **[vhs-action](https://github.com/charmbracelet/vhs-action):** reusable tape templates rendered fresh on every release in CI. Table stakes for terminal tools.

---

## 5. Bad Patterns to Avoid

From the README anti-pattern guides ([Tilburg Science Hub](https://www.tilburgsciencehub.com/topics/collaborate-share/share-your-work/content-creation/readme-best-practices/), [Medium / Shaun Fulton](https://medium.com/@fulton_shaun/readme-rules-structure-style-and-pro-tips-faea5eb5d252)):

1. **1000+ line README walls.** The Cloudwright README is 1,279 lines. Every changelog entry since v0.1.0 is inline. Collateral damage: the install block is buried below the fold for any user with a normal-height monitor scrolled past the hero GIF.
2. **Multiple competing demos with no hero.** Cloudwright has 14 image embeds — a CLI demo GIF, a Smart Canvas demo GIF, and 12 screenshots. None is The Hero. The reader's eye doesn't know where to land.
3. **Buried install instructions.** Install is at line 26 in the current README — but it's preceded by a 4-quadrant screenshot grid that pushes it visually below the fold on most monitors.
4. **Unclear "what does this do in one sentence."** Current line 11: *"Cloudwright bridges the gap between a whiteboard sketch and deployable infrastructure."* Two sentences, abstract. Compare uv: "An extremely fast Python package and project manager, written in Rust." Compare Repomix: "Packs your entire repository into a single, AI-friendly file." One concrete capability. Cloudwright's first line should be a verb the reader can imagine doing.
5. **No live playground.** Excalidraw, Bolt, Lovable, GitDiagram, Repomix, htmx all have a hosted try-it-now URL. Cloudwright's web UI requires `pip install 'cloudwright-ai[web]'` — friction kills the click-through funnel.
6. **Outdated screenshots.** The `examples/cloudwright-demo.gif` and `examples/cloudwright-smart-canvas-demo.gif` are not regenerated against latest UI per the project memory ("Demo GIFs stale" in `project_ui_revamp_apr2026.md`). The Soft UI Evolution rebrand isn't reflected in the hero.
7. **Marketing speak.** "Architecture intelligence for cloud engineers" is the kind of phrase a VP of Marketing approves. It tells the reader nothing they can verify in 8 seconds. The fix: a verb + a concrete object + a number.

---

## 6. Cloudwright Specifically

### The ONE hero demo (60-second GIF or interactive embed)

**Recommendation: a 12-second GIF that does the magic trick "natural-language → spec → cost + Terraform"**, in this exact rhythm:

| Time | Action | Visible result |
|---|---|---|
| 0–2s | Type `cloudwright design "HIPAA healthcare API on AWS"` and hit Enter | Streaming spec output |
| 2–6s | Spec materializes: 12 components, VPC boundaries, RDS, ALB, etc. | ASCII diagram appears |
| 6–9s | `cloudwright cost spec.yaml --workload-profile medium` runs | $2,263/mo breakdown |
| 9–12s | `cloudwright export spec.yaml --format terraform -o ./infra` | "Wrote 14 .tf files" |

This loops in 12 seconds, does not need narration, and shows three load-bearing claims: (1) it understands HIPAA, (2) it costs the architecture, (3) it produces real Terraform. **Generate via VHS tape file** in CI on every release using the project's existing `record-demo` skill. Pair with a *live* hosted version at `cloudwright.dev/playground` (or whatever domain) running the same prompt. That's the GitDiagram-style click-through — the reader can replay the trick in their own browser.

### The first 100 words of a redesigned README

> # Cloudwright
>
> *Describe a cloud architecture in English. Get Terraform, costs, and a compliance check.*
>
> [hero GIF: 12-second demo above]
>
> ```bash
> pip install 'cloudwright-ai[cli]'
> export ANTHROPIC_API_KEY=sk-ant-...
> cloudwright design "HIPAA healthcare API on AWS with Postgres and Redis"
> ```
>
> Cloudwright produces a structured architecture spec, cost estimate, compliance report (HIPAA, SOC2, PCI), and Terraform/CloudFormation code from a single natural-language prompt. Multi-cloud (AWS, GCP, Azure, Databricks). 17 templates, 5 approved modules, 200+ services costed.
>
> **Try it:** [cloudwright.dev/playground](#)  ·  **Docs:** [cloudwright.dev/docs](#)  ·  **MCP server:** `pip install cloudwright-ai-mcp`

Total: ~95 words. Three concrete claims, one CTA, install in three lines, demo above the fold.

### Top 3 distribution channels for week 1 of the next launch

1. **Show HN — Tuesday 7am Pacific.** Title: `Show HN: Cloudwright – Natural language to Terraform, costs, and HIPAA in one CLI`. 76 characters, no superlatives, three concrete capabilities. Author replies in the first 30 minutes.
2. **Last Week in AWS + Pragmatic Engineer.** Personal pitch to Corey Quinn (cost angle is irresistible) and Gergely Orosz (architecture-as-code positioning fits his audience). One paragraph each, with the playground URL.
3. **r/devops + r/Terraform + r/aws** with a *technical write-up*, not a launch post. Post a "we benchmarked our Terraform output against `terraform validate` on 100 generated specs" or "here's what HIPAA validation actually checks" post. The tool gets mentioned as the methodology.

Skip LinkedIn for week 1; revisit in week 3 with the enterprise/compliance angle once HN traffic has settled.

### 5 README anti-patterns currently present that should be cut

1. **Cut the inline changelog.** Move the v0.1.0–v1.2.0 history to `CHANGELOG.md` (it already exists) and link to it. Saves ~400 lines.
2. **Cut the 4-quadrant screenshot grid above install.** It's competing with the hero GIF for attention. Replace with one screenshot or move below the fold.
3. **Cut "Why Cloudwright" + "How it compares" sections from the top half.** These are appendix material, not above-the-fold material.
4. **Cut 14 feature subsections down to 6.** Group the secondary features ("Architecture Linter", "Architecture Scorer", "Blast Radius Analysis", "Drift Detection", "Policy Engine") under a single "Analysis" heading with a sentence each — or move to the docs site entirely.
5. **Cut "Architecture intelligence for cloud engineers" headline.** Replace with the verb+object+result one-liner above. The phrase tells the reader nothing they can verify; the new one is a literal capability.

### Viral-hook thesis: the 8-second moment

**The hook is: "Type one English sentence. Get a costed, compliant, Terraform-ready architecture."**

The 8-second moment is *the diff*: the reader sees 12 components materialize, then a `$2,263/mo` cost number, then `Wrote 14 .tf files`. Three concrete artifacts in eight seconds. This is the same rhythm as GitDiagram's "URL substitution" hook and uv's "10-100x" chart: one input, three obviously-useful outputs, no setup required.

The shareable Twitter/HN moment is a **side-by-side**: left panel shows a cloud architect manually drawing a whiteboard for 2 hours; right panel shows Cloudwright doing it in 8 seconds, with a checkable Terraform diff at the end. The "before/after" pattern from Linear and Cursor product launches.

A close-second hook is the **"watch it audit itself"** recursion: feed Cloudwright a Terraform file generated by Cloudwright, run `cloudwright security` + `cloudwright cost` + `cloudwright validate --compliance hipaa,soc2`, get back a green report. This is Bolt-style proof-by-recursion, and it leans into Cloudwright's actual differentiator (validation + cost as first-class outputs, not just generation).

---

## Cloudwright Next-Launch Playbook (one-page checklist)

**README**
- [ ] One-sentence pitch: verb + concrete object + measurable result
- [ ] Hero GIF: 12-second magic trick, < 5 MB, 10 fps, 800–1280 px source
- [ ] Install block in first 100 words, three lines max
- [ ] Live playground URL on the first screen
- [ ] Adoption-as-proof badges (PyPI version, downloads/month, stars, MCP score)
- [ ] Move 12 changelog entries to `CHANGELOG.md`
- [ ] Reduce 14 feature subsections to ~6 grouped headings
- [ ] Cut "Why" + "How it compares" from above-the-fold
- [ ] Re-record GIFs against the new Soft UI Evolution design tokens
- [ ] Pair every GIF with a "Watch full video" link to a 60-second YouTube/Loom

**Demo**
- [ ] VHS tape file checked in; CI regenerates GIF on every release
- [ ] Web demo: Playwright + ffmpeg pipeline (already in project memory)
- [ ] Two hero artifacts max: one CLI GIF, one web GIF — not 14 mixed images
- [ ] Static cost-comparison chart for the secondary "uv-style" hero, no motion
- [ ] Hosted playground at a domain users can click without `pip install`
- [ ] "Before/after" Twitter video: whiteboard vs Cloudwright, 24-second cut

**Distribution Week 1**
- [ ] Show HN, Tuesday 7am Pacific, 60–80 char title, no superlatives
- [ ] Author present in HN comments for first 30 minutes
- [ ] Pitch to Corey Quinn (Last Week in AWS) — cost angle
- [ ] Pitch to Gergely Orosz (Pragmatic Engineer) — architecture-as-code angle
- [ ] r/devops technical write-up (not launch post): "what generated-Terraform looks like at scale"
- [ ] r/Python launch post — tool is genuinely Python-native
- [ ] X/Bluesky cross-post the 24-second before/after video
- [ ] Skip LinkedIn week 1; circle back week 3 with compliance-buyer angle

**Distribution Week 2–4**
- [ ] DEV.to long-form: "How we ship a multi-cloud architect in one CLI"
- [ ] Hashnode mirror of the same post
- [ ] Submit to KubeCon NA 2026 co-located events CFP (opens April 29, 2026)
- [ ] Pitch The Changelog and Practical AI for podcast slots
- [ ] Tag Theo / Fireship / ThePrimeagen on the demo on X with a 30-second clip

**What good looks like at +30 days**
- 1,000+ GitHub stars
- 5,000+ PyPI downloads/week (currently a tiny fraction of that)
- HN front page > 100 points
- One newsletter feature (TLDR or Last Week in AWS)
- One YouTube creator video > 10k views

---

**Sources**

- [shadcn/ui](https://github.com/shadcn-ui/ui)
- [Aider](https://github.com/Aider-AI/aider)
- [uv (Astral)](https://github.com/astral-sh/uv)
- [Bun](https://github.com/oven-sh/bun)
- [htmx.org](https://htmx.org)
- [GitDiagram](https://github.com/ahmedkhaleel2004/gitdiagram)
- [Repomix](https://github.com/yamadashy/repomix)
- [tldraw](https://github.com/tldraw/tldraw)
- [Excalidraw](https://github.com/excalidraw/excalidraw)
- [Bolt.new](https://bolt.new)
- [Lovable](https://lovable.dev)
- [v0 / v0.app](https://v0.app)
- [VHS (charmbracelet)](https://github.com/charmbracelet/vhs)
- [vhs-action templates](https://github.com/charmbracelet/vhs-action)
- [asciinema](https://github.com/asciinema/asciinema)
- [awesome-terminal-recorder](https://github.com/orangekame3/awesome-terminal-recorder)
- [Rekort GIF for GitHub README guide](https://rekort.app/blog/gif-for-github-readme)
- [GitHub community: GIF embed discussion](https://github.com/orgs/community/discussions/81359)
- [DEV: animated GIFs/SVGs in README](https://dev.to/brpaz/make-your-project-readme-file-stand-out-with-animated-gifs-svgs-4kpe)
- [GitHub markup: MP4 instead of gif issue](https://github.com/github/markup/issues/1329)
- [Scalar: animated responsive README](https://blog.scalar.com/p/how-we-created-an-animated-responsive)
- [How to launch a dev tool on Hacker News (markepear)](https://www.markepear.dev/blog/dev-tool-hacker-news-launch)
- [Calmops: Hacker News launch guide](https://calmops.com/indie-hackers/hacker-news-launch-500-upvotes/)
- [Lucas Costa: HN launch post-mortem](https://lucasfcosta.com/2023/08/21/hn-launch.html)
- [Viral Potential Predictor for HN titles](https://hn-ph.vercel.app)
- [HN ranking discussion](https://news.ycombinator.com/item?id=44625897)
- [GitDiagram on HN](https://news.ycombinator.com/item?id=42521769)
- [Aider on HN](https://news.ycombinator.com/item?id=39995725)
- [uv on HN](https://news.ycombinator.com/item?id=42415602)
- [Astral on HN (OpenAI acquisition)](https://news.ycombinator.com/item?id=41993662)
- [Reddit dev marketing guide](https://business.daily.dev/resources/how-to-market-developer-tools-on-reddit-practical-guide/)
- [r/devops guide on Leadline](https://leadline.dev/guides/reddit-subreddits/r-devops)
- [Bluesky funding for devs (TechCrunch)](https://techcrunch.com/2024/03/11/bluesky-is-funding-developer-projects-to-give-its-twitter-x-alternative-a-boost/)
- [Mastodon vs Bluesky (Postiz)](https://postiz.com/blog/mastodon-vs-bluesky)
- [Cline: top Cursor alternatives 2025](https://cline.bot/blog/top-9-cursor-alternatives-in-2025-best-open-source-ai-dev-tools-for-developers-2)
- [Developer Newsletter directory](https://github.com/jackbridger/developer-newsletters)
- [TLDR Newsletter](https://tldr.tech)
- [Pragmatic Engineer Newsletter](https://newsletter.pragmaticengineer.com)
- [The Changelog podcast](https://changelog.com)
- [Practical AI podcast](https://practicalai.fm)
- [Software Engineering Daily](https://softwareengineeringdaily.com)
- [KubeCon NA 2026 LF Events](https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/)
- [KubeCon EU 2026 schedule](https://www.cncf.io/announcements/2025/12/10/cncf-unveils-schedule-for-kubecon-cloudnativecon-europe-2026/)
- [Tilburg Science Hub: README best practices](https://www.tilburgsciencehub.com/topics/collaborate-share/share-your-work/content-creation/readme-best-practices/)
- [Shaun Fulton: README rules](https://medium.com/@fulton_shaun/readme-rules-structure-style-and-pro-tips-faea5eb5d252)
- [readme-best-practices repo](https://github.com/jehna/readme-best-practices)
- [How to Write a Beginner-Friendly README 2025](https://www.readmecodegen.com/blog/beginner-friendly-readme-guide-open-source-projects)
