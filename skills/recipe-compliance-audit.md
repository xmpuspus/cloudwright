---
name: recipe-compliance-audit
version: 0.3.0
description: Full compliance audit across all frameworks with security and lint scoring
layer: 3
mcp_tools: [validate_compliance, security_scan, lint_architecture, score_architecture]
tags: [recipe, compliance, audit, hipaa, pci-dss, soc2, fedramp, gdpr, report]
---

# Recipe: Compliance Audit

Run a comprehensive compliance audit across all frameworks, combine with security and lint findings, and produce a scorecard.

## When to Use

- Annual or quarterly compliance audit
- Pre-certification preparation (SOC 2, HIPAA, FedRAMP)
- Board or auditor reporting on security posture
- Due diligence for enterprise sales

## Pipeline

```
load spec
    ↓
┌─────────────────────────────────────────────┐
│  validate (all frameworks)                  │
│  + security_scan                            │  (parallel)
│  + lint_architecture                        │
│  + score_architecture                       │
└─────────────────────────────────────────────┘
    ↓
generate compliance scorecard
```

## Steps

### 1. Run all checks in parallel

```bash
cloudwright validate arch.yaml --compliance hipaa,pci-dss,soc2,fedramp,gdpr &
cloudwright security arch.yaml &
cloudwright lint arch.yaml &
cloudwright score arch.yaml &
wait
```

### 2. Generate report

```bash
cloudwright validate arch.yaml --compliance hipaa,pci-dss,soc2 --pdf compliance-audit-2026.pdf
```

## MCP Tool Usage

```json
// All checks in parallel
{"tool": "validate_compliance", "arguments": {"spec_json": <spec>, "frameworks": ["hipaa", "pci-dss", "soc2", "fedramp", "gdpr"]}}
{"tool": "security_scan", "arguments": {"spec_json": <spec>}}
{"tool": "lint_architecture", "arguments": {"spec_json": <spec>}}
{"tool": "score_architecture", "arguments": {"spec_json": <spec>}}
```

## Compliance Scorecard Format

```
Compliance Audit Report
Architecture: payment-processing-platform
Date: 2026-03-06

Framework Results:
  HIPAA     [PASS]  24/24 controls  0 violations
  PCI-DSS   [PASS]  32/32 controls  0 violations
  SOC 2     [PASS]  18/18 controls  0 violations
  FedRAMP   [FAIL]   9/12 controls  3 violations
    - [CRITICAL] Non-FedRAMP-authorized service: 'elasticache'
    - [HIGH]     Region us-east-1 not IL4 authorized
    - [HIGH]     Missing FIPS 140-2 endpoint for RDS
  GDPR      [PASS]  10/10 controls  0 violations

Security:
  Findings: 0 critical, 0 high, 1 medium
  - [MEDIUM] NO_BACKUP: DynamoDB has no point-in-time recovery

Lint:
  Errors: 0  Warnings: 1
  - [WARNING] MISSING_AUTOSCALING on ECS service 'api'

Score: 81/100 (B)
  Reliability: 78  Security: 88  Cost: 75  Compliance: 72  Complexity: 70

Overall: 4/5 frameworks PASS
```

## Output Options

```bash
# Print to terminal
cloudwright validate arch.yaml --compliance hipaa,pci-dss,soc2

# Markdown report
cloudwright validate arch.yaml --compliance hipaa,soc2 --report audit.md

# PDF report (requires reportlab)
cloudwright validate arch.yaml --compliance hipaa,soc2 --pdf audit.pdf
```

## Follow-Up Actions

After audit:
- Framework failures: `cloudwright modify arch.yaml "fix all FedRAMP violations"` then re-audit
- Security findings: use `cloudwright-security-harden` recipe
- Send PDF to auditors or store in compliance management system
