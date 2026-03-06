---
name: recipe-cost-optimize
version: 0.3.0
description: Iterative cost optimization loop with score verification (max 3 iterations)
layer: 3
mcp_tools: [estimate_cost, score_architecture, modify_architecture]
tags: [recipe, cost, optimize, finops, loop, iteration]
---

# Recipe: Cost Optimize

Iteratively reduce cost while monitoring quality score. Stops when target is met or 3 iterations complete.

## When to Use

- Architecture is over budget and needs multiple rounds of optimization
- User wants maximum cost reduction without dropping below a quality threshold
- FinOps review cycle requiring documented cost improvements

## Pipeline

```
estimate_cost  →  score_architecture
      ↓
  identify expensive components
      ↓
  modify_architecture (cost reduction)
      ↓
  estimate_cost  →  score_architecture
      ↓
  [repeat max 3 iterations]
```

## Steps

```bash
# Iteration 1
cloudwright cost arch.yaml           # baseline: $1,240/month
cloudwright score arch.yaml          # baseline: 62/100

cloudwright modify arch.yaml "right-size compute: use m5.xlarge instead of m5.2xlarge for API, switch RDS to t3.medium"
cloudwright cost arch.yaml           # $980/month
cloudwright score arch.yaml          # 65/100

# Iteration 2
cloudwright modify arch.yaml "switch RDS and ElastiCache to reserved 1-year pricing"
cloudwright cost arch.yaml           # $780/month
cloudwright score arch.yaml          # 64/100

# Iteration 3
cloudwright modify arch.yaml "move Lambda workers to Spot, add autoscaling on ECS"
cloudwright cost arch.yaml           # $680/month
cloudwright score arch.yaml          # 70/100
```

## MCP Tool Usage

```python
target_monthly = 800  # USD
min_score = 65
max_iterations = 3

baseline_cost = estimate_cost(spec_json=spec)
baseline_score = score_architecture(spec_json=spec)

for i in range(max_iterations):
    cost = estimate_cost(spec_json=spec)
    score = score_architecture(spec_json=spec)

    if cost["total_monthly"] <= target_monthly:
        break  # target met

    # Find top 3 most expensive components
    breakdown = sorted(cost["breakdown"], key=lambda x: x["monthly"], reverse=True)[:3]
    expensive = ", ".join(f"{b['component_id']} (${b['monthly']:.0f}/mo)" for b in breakdown)

    instruction = (
        f"Iteration {i+1}: Reduce cost. Most expensive components: {expensive}. "
        f"Right-size or switch to reserved/spot pricing. Keep score above {min_score}."
    )
    spec = modify_architecture(spec_json=spec, instruction=instruction)

# Verify score did not drop below minimum
final_score = score_architecture(spec_json=spec)
if final_score["composite"] < min_score:
    # Warn but don't revert — let user decide
    print(f"Warning: score dropped to {final_score['composite']} (below min {min_score})")
```

## Example Output

```
Cost Optimization: arch.yaml
Target: $800/month  Quality floor: 65/100  Max iterations: 3

Iteration 1:
  Cost:  $1,240 → $980  (-21%)  [RIGHT-SIZED api, db]
  Score: 62 → 65

Iteration 2:
  Cost:  $980 → $780  (-20%)   [RESERVED RDS, ElastiCache]
  Score: 65 → 64

Target met at $780/month in 2 iterations.

Summary:
  Total savings: $460/month  (-37%)
  Score change:  62 → 64  (within floor)
  Changes applied:
    - api: m5.2xlarge → m5.xlarge
    - db: on_demand → reserved_1yr
    - cache: on_demand → reserved_1yr
```

## Guardrails

- Never remove required components (auth, database, monitoring)
- If a modification would drop score below floor, reject and try a less aggressive instruction
- Maximum 3 iterations to prevent infinite loops on architectures with little optimization headroom
- Always report final cost vs target and score vs floor

## Follow-Up Actions

After optimization:
- `cloudwright validate arch.yaml --compliance <framework>` — reserved pricing doesn't affect compliance
- `cloudwright export arch.yaml --format terraform` — export the cost-optimized spec
