# Cloudwright Strategic Analysis Prompt

Use this prompt in a fresh Claude Code session from the `/Users/xavier/Desktop/cloudwright` directory.

---

```
Ultrathink about this. I need a comprehensive strategic analysis of Cloudwright — an open-source architecture intelligence tool I'm building. Read the full codebase, then produce a structured report covering gap analysis, competitive positioning, user journey failures, and prioritized recommendations.

## What Cloudwright Does

Read README.md and CLAUDE.md for full context. In short: natural language to cloud architecture spec (ArchSpec), with cost estimation, compliance validation (HIPAA/PCI-DSS/SOC2/FedRAMP/GDPR/Well-Architected), Terraform/CloudFormation export, Mermaid/D2 diagrams, SBOM/AIBOM, architecture diffing, linting, scoring, blast radius analysis, drift detection, policy engine, and infrastructure import. 100 service keys across AWS (47), GCP (25), Azure (28). Python monorepo: core library, CLI (17 commands), web UI (FastAPI + React).

## Known Benchmark Data (54 use cases, verified)

Overall: Cloudwright 68.1% vs Claude-raw 28.0%. Wins 6/8 metrics.

Critical failures:
- COST ACCURACY: 13% overall. 27 of 43 successful cases scored <10%. Estimates are systematically 10-100x too low. Example: $182 estimated vs $15,000 budget for healthcare EHR; $52 vs $4,000 for data lake. The catalog has pricing but the cost engine is dramatically underpricing everything.
- PIPELINE FAILURES: 11 of 54 cases (20%) generated NO spec at all. These are: import cases (FinOps review, Terraform import, CFN import, Serverless import), complex scenarios (multi-tenant B2B SaaS, monolith-to-serverless re-architecture, hybrid migration), multi-compliance (HIPAA+PCI+FedRAMP), and comparison cases (container orchestration, TCO analysis). The architect LLM call fails or returns unparseable output.
- SERVICE CORRECTNESS: 73.1% overall, dragged down by import/migration/comparison categories where the architect doesn't understand the use case type.

Strengths: structural validity (79.6%), compliance completeness (62.9%), export quality (55.7%), diff (100%), reproducibility (77.9%), time-to-IaC (82.5%).

## Competitor Landscape (read docs/competitor-landscape.md for full detail)

Key competitors:
- Brainboard: closest competitor. NL-to-arch + Terraform + visual designer + multi-cloud. SaaS, no compliance, no cost estimation from catalog. Paid.
- Pulumi Neo: NL-to-infrastructure code. Deployment-focused, not design-focused. No compliance validation. $34k/yr enterprise.
- Infracost: cost estimation from Terraform plans (code-time, not design-time). Open source CLI. 1000+ TF resources priced.
- Checkov: 2500+ compliance policies for IaC scanning. Post-code, not pre-code. Open source.
- Firefly.ai: cloud asset management, drift detection, 600+ compliance policies. Day 2 ops, not Day 0 design.
- DuploCloud: low-code DevOps, built-in compliance. $2-6.5k/mo. Platform lock-in.
- Terraform/OpenTofu: deployment engine, not design tool. Cloudwright generates TF as output.

No tool in market combines NL-to-arch + design-time cost + compliance validation + IaC export + diffing + open source.

## Analysis Required

### 1. User Persona & Journey Analysis

Identify 5-7 distinct user personas who would use a tool like this (cloud architects, DevOps engineers, compliance officers, CTOs, platform engineers, consultants, etc.). For each:
- What's their actual workflow today without Cloudwright?
- What pain point does Cloudwright solve for them?
- Where would they hit friction or failure with current Cloudwright?
- What would make them switch from their current tools?
- What would make them abandon Cloudwright after trying it?

### 2. Use Case Gap Analysis

Map these real-world use cases against Cloudwright's actual capabilities. For each, rate: works well / works partially / fails / not supported.

Core use cases:
- Greenfield architecture design from requirements doc
- Quick cost comparison across AWS/GCP/Azure for a workload
- Compliance pre-check before architecture review meeting
- Generate Terraform for a standard 3-tier app
- Architecture review / well-architected assessment
- Migrate architecture from one cloud to another
- Import existing Terraform and understand it as architecture
- Compare two architecture versions before and after changes
- Generate compliance documentation for auditors
- Capacity planning and right-sizing
- Disaster recovery architecture design
- Multi-region / active-active design
- Serverless-first architecture patterns
- Data pipeline / analytics architecture
- ML/AI infrastructure design

For each failed/partial case, explain WHY it fails (cite specific code/module limitations) and what would fix it.

### 3. Competitive Gap Analysis

For each competitor, identify:
- Features they have that Cloudwright lacks entirely
- Features where Cloudwright's implementation is weaker
- Features where Cloudwright is genuinely better
- Integration points (could Cloudwright complement rather than compete?)

Build a matrix of: must-have features Cloudwright is missing, nice-to-have features, and features that are unique differentiators.

### 4. Technical Debt & Architecture Issues

Read the actual source code (spec.py, architect.py, cost.py, catalog/, validator.py, exporter/terraform.py, linter.py, scorer.py) and identify:
- Design decisions that limit scalability or extensibility
- Hardcoded values that should be configurable
- Missing abstractions or leaky abstractions
- Test coverage gaps for critical paths
- Error handling weaknesses (especially in the LLM pipeline)
- The cost engine underpricing problem — what's the root cause?
- Why do 11 cases fail to generate any spec? Is it prompt engineering, parsing, or architecture?

### 5. Prioritized Roadmap Recommendations

Produce three tiers:

**P0 — Fix before anyone sees this (blocks adoption):**
Things that would embarrass the project if a serious user tried them.

**P1 — Next 30 days (drives adoption):**
Features that would make the first 100 users successful and want to tell others.

**P2 — Next 90 days (builds moat):**
Features that create sustainable competitive advantage vs Brainboard/Pulumi Neo.

For each recommendation: specific code changes needed, effort estimate (S/M/L), impact on benchmark scores, and which user persona it serves.

### 6. Go-to-Market Positioning

Based on the analysis:
- What's the sharpest one-line pitch?
- Which persona should be the primary target?
- What's the "aha moment" that hooks users?
- What's the biggest risk to adoption?
- Should this be positioned as a tool, a platform, or a library?
- Open source strategy: what stays open, what could be commercial?

## Output Format

Structured report with clear sections, tables where appropriate, and concrete code-level specifics (file paths, function names, line numbers). No vague recommendations — every suggestion should be actionable with a clear "done" definition. Use plain text bullets, no markdown tables wider than 100 chars.

Read the full codebase before writing anything. Start with the benchmark results, cost engine, and architect module — those are where the biggest issues are.
```
