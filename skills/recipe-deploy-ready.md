---
name: recipe-deploy-ready
version: 0.3.0
description: Full deployment pipeline — validate, secure, lint, then export Terraform
layer: 3
mcp_tools: [validate_compliance, security_scan, lint_architecture, score_architecture, export_architecture]
tags: [recipe, deploy, pipeline, terraform, gate]
---

# Recipe: Deploy Ready

Run all quality gates in parallel, evaluate results, and export Terraform only if all gates pass.

## When to Use

- Final step before deploying a new architecture
- CI/CD pipeline gate before `terraform plan`
- Generating production-ready IaC from a reviewed spec

> [!CAUTION]
> This recipe exports files to disk. Confirm the output path with the user before running.

## Pipeline

```
design (or load spec)
        ↓
┌───────────────────────────────────┐
│  validate + security + lint       │  (parallel)
│  + score                          │
└───────────────────────────────────┘
        ↓
   evaluate gates
        ↓
   export terraform  (only if all pass)
```

## Steps

### 1. Load or design the spec

```bash
cloudwright design "SaaS platform with auth, API, Postgres on AWS" --output arch.yaml
# OR load existing:
# arch.yaml already exists
```

### 2. Run all gates in parallel

```bash
cloudwright validate arch.yaml --compliance hipaa,soc2 &
cloudwright security arch.yaml --fail-on high &
cloudwright lint arch.yaml &
cloudwright score arch.yaml &
wait
```

### 3. Evaluate gates

All three must pass:
- `validate` — zero compliance violations
- `security` — zero critical/high findings
- `lint` — zero errors (warnings allowed)
- `score` — composite >= 75

### 4. Export Terraform (only on pass)

```bash
cloudwright export arch.yaml --format terraform --output infra/
```

## MCP Tool Usage

```python
import asyncio

# Run gates concurrently
results = await asyncio.gather(
    validate_compliance(spec_json=spec, frameworks=["hipaa", "soc2"]),
    security_scan(spec_json=spec, fail_on="high"),
    lint_architecture(spec_json=spec),
    score_architecture(spec_json=spec),
)

validate_results, security_report, lint_issues, score = results

# Evaluate
passed = (
    all(r["passed"] for r in validate_results) and
    security_report["passed"] and
    all(i["severity"] != "error" for i in lint_issues) and
    score["composite"] >= 75
)

if passed:
    export_architecture(spec_json=spec, format="terraform", output_path="infra/")
```

## Gate Summary Format

```
Deploy Readiness Check: arch.yaml

  [PASS] Compliance (HIPAA, SOC2) — 0 violations
  [PASS] Security — 0 critical/high findings
  [PASS] Lint — 0 errors, 2 warnings
  [PASS] Score — 82/100 (B)

All gates passed. Exporting Terraform to infra/
```

```
Deploy Readiness Check: arch.yaml

  [PASS] Compliance (HIPAA) — 0 violations
  [FAIL] Security — 1 critical finding: NO_ENCRYPTION_AT_REST on 'db'
  [FAIL] Lint — 1 error: SINGLE_AZ on 'db'
  [PASS] Score — 68/100 (C)

2 gates failed. Fix issues and re-run.
```

## Follow-Up Actions

On failure:
- Security failures: use `cloudwright-security-harden` recipe
- Compliance failures: `cloudwright modify arch.yaml "fix HIPAA violations"`
- Lint errors: `cloudwright modify arch.yaml "fix all lint errors"`
- Low score: use `cloudwright-design-optimize` recipe
