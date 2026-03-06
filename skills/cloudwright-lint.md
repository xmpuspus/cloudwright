---
name: cloudwright-lint
version: 0.3.0
description: Detect architecture anti-patterns in a spec
layer: 1
mcp_tools: [lint_architecture]
tags: [lint, anti-patterns, best-practices, review]
---

# Cloudwright Lint

Detect common architecture anti-patterns and get recommendations to fix them.

## When to Use

- Pre-deployment architecture review
- Automated gate in CI/CD pipelines
- Pair with `cloudwright score` for a complete quality check
- Catching issues that scores don't surface (e.g., SPOF + specific service misconfig)

## CLI Usage

```bash
# Text output (default)
cloudwright lint arch.yaml

# Strict mode — also fail on warnings
cloudwright lint arch.yaml --strict

# JSON output for pipeline integration
cloudwright lint arch.yaml --output json

# Combine with exit code for CI
cloudwright lint arch.yaml --output json; echo "exit: $?"
```

## MCP Tool Usage

```json
{
  "tool": "lint_architecture",
  "arguments": {
    "spec_json": <ArchSpec dict>
  }
}
```

## Rules Checked

| Rule | Severity | Description |
|------|----------|-------------|
| `SINGLE_AZ` | error | Database or stateful service in only one AZ |
| `OVERSIZED_INSTANCE` | warning | Instance type exceeds workload requirements |
| `SPOF_DETECTED` | error | Component with no redundancy on critical path |
| `NO_CDN` | warning | Static assets served directly without CDN |
| `NO_LOAD_BALANCER` | error | Multiple compute instances with no LB |
| `DIRECT_DB_ACCESS` | error | Frontend or API directly accessing DB without service layer |
| `UNENCRYPTED_STORAGE` | error | Object storage or DB without encryption |
| `MISSING_AUTOSCALING` | warning | Compute tier with no autoscaling policy |
| `OVER_PROVISIONED_CACHE` | warning | Cache instance larger than dataset estimate |
| `MISSING_HEALTH_CHECK` | warning | Service with no health check endpoint |

## Output Structure

```json
[
  {
    "rule": "SINGLE_AZ",
    "severity": "error",
    "component": "db",
    "message": "RDS instance 'db' is deployed in a single AZ",
    "recommendation": "Enable Multi-AZ deployment for automatic failover"
  },
  {
    "rule": "NO_CDN",
    "severity": "warning",
    "component": "frontend",
    "message": "Frontend S3 bucket has no CloudFront distribution",
    "recommendation": "Add CloudFront to reduce latency and egress costs"
  }
]
```

## Severity Levels

| Severity | Meaning | Blocks CI? |
|----------|---------|-----------|
| `error` | Anti-pattern that will cause production issues | Yes (default) |
| `warning` | Suboptimal but functional | Only with `--strict` |

## Follow-Up Actions

After linting:
- `cloudwright modify arch.yaml "fix all lint errors"` — auto-remediate errors
- `cloudwright analyze arch.yaml` — SPOF errors map to blast radius data
- `cloudwright score arch.yaml` — lint errors reduce reliability and complexity scores

## Notes

- `DIRECT_DB_ACCESS` is raised when a frontend component has a connection directly to a database with no intermediate service.
- `OVERSIZED_INSTANCE` uses heuristics based on component tier. A `presentation` tier service on `m5.16xlarge` is flagged; an `ml_training` service on the same instance type is not.
- Rules are deterministic — no LLM calls. Lint always returns the same result for the same spec.
