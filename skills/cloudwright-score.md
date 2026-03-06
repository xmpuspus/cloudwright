---
name: cloudwright-score
version: 0.3.0
description: Score an architecture on 5 quality dimensions
layer: 1
mcp_tools: [score_architecture]
tags: [score, quality, reliability, security, cost, compliance, complexity]
---

# Cloudwright Score

Score an architecture spec on 5 weighted dimensions, returning a composite 0-100 score.

## When to Use

- Establishing a quality baseline before optimizing
- Comparing two architectures objectively
- Architecture review gate (e.g., reject if score < 70)
- Tracking improvement across iterations

## CLI Usage

```bash
# Basic scoring
cloudwright score arch.yaml

# Include cost analysis in scoring
cloudwright score arch.yaml --with-cost

# JSON output
cloudwright --json score arch.yaml
```

## MCP Tool Usage

```json
{
  "tool": "score_architecture",
  "arguments": {
    "spec_json": <ArchSpec dict>
  }
}
```

## Scoring Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Reliability | 30% | Multi-AZ, redundancy, SPOFs, health checks |
| Security | 25% | Encryption, IAM, network isolation, compliance flags |
| Cost Efficiency | 20% | Right-sized instances, reserved pricing, idle resources |
| Compliance | 15% | Controls mapped to declared compliance frameworks |
| Complexity | 10% | Component count, dependency depth, cyclomatic paths |

## Output Structure

```json
{
  "composite": 74,
  "dimensions": {
    "reliability": {"score": 68, "weight": 0.30, "notes": ["Single-AZ RDS", "No health checks on worker"]},
    "security": {"score": 82, "weight": 0.25, "notes": []},
    "cost": {"score": 71, "weight": 0.20, "notes": ["m5.2xlarge over-provisioned for current load"]},
    "compliance": {"score": 90, "weight": 0.15, "notes": []},
    "complexity": {"score": 60, "weight": 0.10, "notes": ["11 components; consider consolidation"]}
  },
  "grade": "B"
}
```

## Grade Thresholds

| Grade | Score | Interpretation |
|-------|-------|---------------|
| A | 90-100 | Production-ready |
| B | 75-89 | Minor improvements recommended |
| C | 60-74 | Significant issues; address before deploy |
| D | 40-59 | Major structural problems |
| F | 0-39 | Not suitable for production |

## Follow-Up Actions

After scoring:
- Low reliability: `cloudwright analyze arch.yaml` — identify SPOFs
- Low security: `cloudwright security arch.yaml` — get specific findings
- Low cost: `cloudwright cost arch.yaml` — see breakdown
- Low compliance: `cloudwright validate arch.yaml --compliance <framework>`
- Optimize overall: use `cloudwright-design-optimize` recipe skill

## Notes

- `--with-cost` fetches live cost data before scoring, making the cost dimension more accurate.
- Without `--with-cost`, cost scoring is based on instance types and service choices, not actual spend.
- Complexity score penalizes both over-engineered and under-engineered designs. A simple 3-tier app that works well scores higher than a 20-service mesh.
