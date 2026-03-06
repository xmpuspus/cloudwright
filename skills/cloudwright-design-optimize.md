---
name: cloudwright-design-optimize
version: 0.3.0
description: Optimize an existing architecture to improve quality score while staying within budget
layer: 2
mcp_tools: [score_architecture, lint_architecture, modify_architecture, estimate_cost]
tags: [optimize, score, quality, design, chain]
---

# Cloudwright Design Optimize

Score an architecture, identify the weakest dimensions, apply targeted improvements, and verify the result.

## When to Use

- User has an existing spec and wants to improve it
- Score is below 75 and user wants to know what to fix
- Pre-deployment quality improvement pass

## Chain

```
score_architecture  →  lint_architecture  →  modify_architecture  →  estimate_cost
```

1. **Score** — establish baseline across 5 dimensions
2. **Lint** — collect specific anti-pattern findings
3. **Modify** — instruct the LLM to fix the lowest-scoring areas
4. **Estimate cost** — confirm budget is not exceeded after changes

## CLI Usage

```bash
# Step 1: score
cloudwright score arch.yaml

# Step 2: lint
cloudwright lint arch.yaml

# Step 3: modify based on findings
cloudwright modify arch.yaml "fix all lint errors and improve reliability score"

# Step 4: verify
cloudwright score arch.yaml
cloudwright cost arch.yaml
```

## MCP Tool Usage

```python
# Step 1
score = score_architecture(spec_json=spec)

# Step 2
issues = lint_architecture(spec_json=spec)

# Step 3 - build instruction from lowest-scoring dimension
lowest = min(score["dimensions"], key=lambda d: score["dimensions"][d]["score"])
instruction = f"Improve {lowest} score: {', '.join(score['dimensions'][lowest]['notes'])}"
if issues:
    error_rules = [i["rule"] for i in issues if i["severity"] == "error"]
    instruction += f". Fix lint errors: {', '.join(error_rules)}"

new_spec = modify_architecture(spec_json=spec, instruction=instruction)

# Step 4
new_cost = estimate_cost(spec_json=new_spec)
```

## MCP Tool Calls

```json
// Step 1
{"tool": "score_architecture", "arguments": {"spec_json": <spec>}}

// Step 2
{"tool": "lint_architecture", "arguments": {"spec_json": <spec>}}

// Step 3
{
  "tool": "modify_architecture",
  "arguments": {
    "spec_json": <spec>,
    "instruction": "Enable Multi-AZ on RDS, add CloudFront, fix SINGLE_AZ and NO_CDN lint errors. Keep monthly cost under $1500."
  }
}

// Step 4
{"tool": "estimate_cost", "arguments": {"spec_json": <modified_spec>}}
```

## Example Output

```
Before optimization:
  Composite: 62  (C grade)
  Reliability: 55 — Single-AZ RDS, no health checks
  Security:   78 — OK
  Cost:       70 — m5.2xlarge over-provisioned
  Compliance: 80 — OK
  Complexity: 65 — 10 components

After optimization:
  Composite: 81  (B grade)
  Reliability: 82 — Multi-AZ enabled, health checks added
  Security:   78 — unchanged
  Cost:       76 — right-sized to m5.xlarge
  Compliance: 80 — unchanged
  Complexity: 62 — 11 components (added RDS replica)

Cost: $980/month → $1,120/month (+$140 for Multi-AZ)
```

## Follow-Up Actions

After optimization:
- If still below 75: re-run the chain, focusing on the next lowest dimension
- Export the improved spec: `cloudwright export arch.yaml --format terraform`
- Run security scan: `cloudwright security arch.yaml`
