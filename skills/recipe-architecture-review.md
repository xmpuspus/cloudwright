---
name: recipe-architecture-review
version: 0.3.0
description: Comprehensive architecture health review — lint, score, blast radius, and security
layer: 3
mcp_tools: [lint_architecture, score_architecture, analyze_blast_radius, security_scan]
tags: [recipe, review, health, report, lint, score, analyze, security]
---

# Recipe: Architecture Review

Run all analysis tools in parallel, then synthesize findings into a structured architecture health report.

## When to Use

- Peer review before an architecture design is approved
- Quarterly architecture health check
- Onboarding a new team member to understand a system's risks
- Preparing architecture documentation for stakeholders

## Pipeline

```
load spec
    ↓
┌─────────────────────────────────────────┐
│  lint + score + analyze + security_scan │  (parallel)
└─────────────────────────────────────────┘
    ↓
synthesize health report
```

## Steps

```bash
# All analysis in parallel
cloudwright lint arch.yaml &
cloudwright score arch.yaml &
cloudwright analyze arch.yaml &
cloudwright security arch.yaml &
wait
```

## MCP Tool Usage

```json
// Run all four in parallel
{"tool": "lint_architecture",   "arguments": {"spec_json": <spec>}}
{"tool": "score_architecture",  "arguments": {"spec_json": <spec>}}
{"tool": "analyze_blast_radius","arguments": {"spec_json": <spec>}}
{"tool": "security_scan",       "arguments": {"spec_json": <spec>}}
```

## Architecture Health Report Format

```
Architecture Health Report
System: payment-processing-platform
Reviewed: 2026-03-06

Overall Score: 74/100 (C)
  Reliability:  65  [WARN]  — Single-AZ RDS, no health checks on worker
  Security:     82  [PASS]  — No critical findings
  Cost:         78  [PASS]  — Well-sized for workload
  Compliance:   80  [PASS]  — SOC2 controls met
  Complexity:   62  [WARN]  — 12 components; review consolidation

Blast Radius Analysis:
  Total components: 12
  SPOFs detected:   2
    - db     (blast radius: 9 of 12 components)
    - auth   (blast radius: 8 of 12 components)
  Max blast radius: 9

Lint Findings:
  Errors:   1
    - SINGLE_AZ on 'db' — Enable Multi-AZ for automatic failover
  Warnings: 2
    - MISSING_AUTOSCALING on 'api'
    - NO_CDN on 'frontend'

Security Findings:
  Critical: 0
  High:     0
  Medium:   1
    - NO_BACKUP on 'cache' — Enable ElastiCache backup window

Recommendations (priority order):
  1. [CRITICAL] Enable Multi-AZ on RDS — 9-component blast radius
  2. [HIGH]     Add ElastiCache backup — medium security finding
  3. [MEDIUM]   Add autoscaling to ECS — operational risk
  4. [LOW]      Add CloudFront — performance optimization
```

## Synthesizing Findings

When writing the report summary, cross-reference results:

- A SPOF that also has a lint error (`SINGLE_AZ`) should be ranked as **critical** regardless of score
- Security medium findings on SPOF components should be elevated to high priority
- Score dimension gaps that match lint errors confirm the same root cause

## Follow-Up Actions

After the review:
- Address critical items: `cloudwright modify arch.yaml "enable Multi-AZ on RDS, add ElastiCache backup"`
- Re-run review to verify improvements
- For pre-deployment: escalate to `recipe-deploy-ready` after addressing all criticals
- For compliance: run `recipe-compliance-audit` if compliance dimension is flagged
