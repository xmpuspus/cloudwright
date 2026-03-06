---
name: cloudwright-analyze
version: 0.3.0
description: Analyze blast radius, SPOFs, and dependency graph of an architecture
layer: 1
mcp_tools: [analyze_blast_radius]
tags: [analyze, blast-radius, spof, dependencies, reliability]
---

# Cloudwright Analyze

Identify single points of failure, critical dependency paths, and blast radius for each component.

## When to Use

- User wants to understand what breaks if component X fails
- Identifying SPOFs before production deployment
- Building incident runbooks that list downstream impact
- Architecture review for reliability concerns

## CLI Usage

```bash
# Full architecture analysis
cloudwright analyze arch.yaml

# Analyze a specific component
cloudwright analyze arch.yaml --component db

# JSON output for tooling integration
cloudwright --json analyze arch.yaml
```

## MCP Tool Usage

```json
{
  "tool": "analyze_blast_radius",
  "arguments": {
    "spec_json": <ArchSpec dict>,
    "component_id": "db"
  }
}
```

Omit `component_id` to analyze the full architecture. Include it to get blast radius for a specific component.

## Output Structure

```json
{
  "total_components": 8,
  "max_blast_radius": 6,
  "spofs": ["db", "auth"],
  "critical_paths": [
    ["api", "auth", "db"],
    ["api", "cache", "db"]
  ],
  "component_analysis": {
    "db": {
      "blast_radius": 6,
      "dependents": ["api", "worker", "cache", "reporting", "admin", "analytics"],
      "is_spof": true,
      "depth": 1
    },
    "auth": {
      "blast_radius": 5,
      "dependents": ["api", "worker", "admin", "reporting", "analytics"],
      "is_spof": true,
      "depth": 1
    }
  }
}
```

## Interpreting Results

**`spofs`:** Components whose failure would cascade to the majority of the system. Prioritize redundancy here.

**`max_blast_radius`:** The highest number of downstream components affected by any single failure. Lower is better.

**`critical_paths`:** Sequences of components where failure at any point brings down the whole path. These are your highest-risk dependency chains.

**`blast_radius` per component:** Number of components that depend (directly or transitively) on this component.

## Common Remediation Patterns

| Issue | Remediation |
|-------|-------------|
| SPOF database | Add read replica, enable Multi-AZ |
| SPOF auth service | Deploy across multiple AZs, add circuit breaker |
| Deep critical path (5+ hops) | Introduce caching layer or async queue |
| High blast radius on single component | Decompose into smaller services |

## Follow-Up Actions

After analysis:
- For each SPOF: `cloudwright modify arch.yaml "add redundancy for <component>"` — auto-fix
- `cloudwright score arch.yaml` — reliability dimension reflects SPOF count
- `cloudwright lint arch.yaml` — linter flags single-AZ and SPOF patterns separately

## Notes

- Blast radius is calculated via reverse dependency traversal from each node in the connection graph.
- A component with no incoming connections (leaf node) has blast_radius = 0.
- Analysis is deterministic — same spec always produces the same result, no LLM calls involved.
