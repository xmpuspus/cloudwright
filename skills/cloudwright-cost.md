---
name: cloudwright-cost
version: 0.3.0
description: Estimate and compare cloud costs for an architecture spec
layer: 1
mcp_tools: [estimate_cost, compare_provider_costs]
tags: [cost, finops, pricing]
---

# Cloudwright Cost

Estimate monthly costs for an architecture and compare pricing across cloud providers.

## When to Use

- User wants to know how much an architecture will cost
- User is deciding between AWS, GCP, and Azure on budget
- User wants to see a cost breakdown by component

## CLI Usage

```bash
# Estimate cost for existing spec
cloudwright cost arch.yaml

# Compare across providers
cloudwright compare arch.yaml --providers aws,gcp,azure

# JSON output for scripting
cloudwright --json cost arch.yaml
```

## MCP Tool Usage

### Estimate cost for a spec

```json
{
  "tool": "estimate_cost",
  "arguments": {
    "spec_json": {
      "name": "web-app",
      "provider": "aws",
      "region": "us-east-1",
      "components": [
        {"id": "api", "service": "ecs", "label": "API Service"},
        {"id": "db", "service": "rds", "label": "Postgres DB"}
      ],
      "connections": [{"source": "api", "target": "db"}]
    },
    "pricing_tier": "on_demand"
  }
}
```

`pricing_tier` options: `on_demand` (default), `reserved_1yr`, `reserved_3yr`, `spot`.

### Compare costs across providers

```json
{
  "tool": "compare_provider_costs",
  "arguments": {
    "spec_json": <ArchSpec dict>,
    "providers": ["aws", "gcp", "azure"]
  }
}
```

Returns a list of cost estimates, one per provider, with equivalent services mapped.

## Output Structure

```json
{
  "total_monthly": 1240.50,
  "breakdown": [
    {"component_id": "api", "service": "ecs", "monthly": 320.00, "unit": "vCPU-hours"},
    {"component_id": "db", "service": "rds", "monthly": 185.00, "unit": "db.t3.medium"}
  ],
  "pricing_tier": "on_demand",
  "currency": "USD"
}
```

## Pricing Tiers

| Tier | Description | Typical Savings |
|------|-------------|-----------------|
| `on_demand` | Pay-as-you-go, no commitment | baseline |
| `reserved_1yr` | 1-year commitment | ~30-40% |
| `reserved_3yr` | 3-year commitment | ~50-60% |
| `spot` | Interruptible capacity | ~60-90% |

## Follow-Up Actions

After estimating cost:
- If over budget: `cloudwright modify arch.yaml "right-size to $500/month"` — reduce cost
- If comparing providers: pick the cheapest and `cloudwright compare arch.yaml --providers aws,gcp,azure`
- Use `cloudwright score arch.yaml` to see if cost optimization hurt reliability

## Notes

- Costs are estimates based on published list prices; actual bills depend on usage patterns.
- The `compare_provider_costs` tool maps each component to the equivalent service on the target provider before estimating.
- Databricks pricing uses DBU rates; set `pricing_tier` to `on_demand` for DBU-based estimates.
