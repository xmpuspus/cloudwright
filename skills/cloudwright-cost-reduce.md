---
name: cloudwright-cost-reduce
version: 0.3.0
description: Reduce architecture cost while maintaining quality
layer: 2
mcp_tools: [estimate_cost, modify_architecture, estimate_cost]
tags: [cost, finops, reduce, optimize, chain]
---

# Cloudwright Cost Reduce

Estimate current cost, apply cost reduction changes, and show a before/after comparison.

## When to Use

- User wants to cut the monthly bill by a target percentage
- Architecture is over budget and needs right-sizing
- Exploring reserved pricing or spot instance options

## Chain

```
estimate_cost  →  modify_architecture (cost reduction instruction)  →  estimate_cost
```

1. **Estimate** — get current monthly total and breakdown by component
2. **Modify** — instruct the LLM to reduce costs (right-size, reserved pricing, remove idle resources)
3. **Re-estimate** — compute new cost and show savings

## CLI Usage

```bash
# Step 1: baseline cost
cloudwright cost arch.yaml

# Step 2: ask for cost reduction
cloudwright modify arch.yaml "reduce monthly cost to under $800 without removing core functionality"

# Step 3: confirm savings
cloudwright cost arch.yaml
```

## MCP Tool Usage

```json
// Step 1
{"tool": "estimate_cost", "arguments": {"spec_json": <spec>}}

// Step 2
{
  "tool": "modify_architecture",
  "arguments": {
    "spec_json": <spec>,
    "instruction": "Reduce monthly cost from $1,240 to under $900. Right-size over-provisioned instances. Switch RDS to reserved 1-year pricing. Use Spot for batch workers."
  }
}

// Step 3
{"tool": "estimate_cost", "arguments": {"spec_json": <modified_spec>, "pricing_tier": "reserved_1yr"}}
```

## Example Output

```
Before:
  Total: $1,240/month
  - api (ecs):      $320  m5.2xlarge × 3 tasks
  - db (rds):       $480  db.r5.2xlarge, on-demand
  - cache (elasticache): $180  cache.r6g.large × 2
  - worker (lambda):     $260  10M invocations/month

After:
  Total: $820/month  (-$420, -34%)
  - api (ecs):      $180  m5.xlarge × 3 tasks (right-sized)
  - db (rds):       $280  db.r5.xlarge, reserved 1yr
  - cache (elasticache): $120  cache.r6g.medium × 2
  - worker (lambda):     $240  optimized memory allocation

Changes made:
  - Right-sized ECS tasks from m5.2xlarge to m5.xlarge
  - Switched RDS to reserved 1-year pricing
  - Right-sized ElastiCache from large to medium
  - No functional changes to architecture
```

## Target Instructions

Adjust the modify instruction based on the goal:

| Goal | Instruction |
|------|-------------|
| Stay under $X/month | "Reduce monthly cost to under $X while keeping all services functional" |
| Cut by percentage | "Reduce monthly cost by 30% through right-sizing and reserved pricing" |
| Right-size only | "Right-size over-provisioned instances without changing architecture" |
| Reserved pricing | "Switch to reserved 1-year pricing for all steady-state services" |
| Spot for batch | "Move batch workers to Spot instances with on-demand fallback" |

## Follow-Up Actions

After cost reduction:
- `cloudwright score arch.yaml` — verify reliability score was not hurt by downsizing
- `cloudwright lint arch.yaml` — check that right-sizing did not introduce `OVERSIZED_INSTANCE` or `MISSING_AUTOSCALING` warnings
- `cloudwright validate arch.yaml --compliance <framework>` — confirm compliance is unaffected
