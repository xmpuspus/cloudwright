---
name: cloudwright-security-harden
version: 0.3.0
description: Iteratively harden an architecture until all critical and high security findings are resolved
layer: 2
mcp_tools: [security_scan, modify_architecture]
tags: [security, harden, scan, loop, chain]
---

# Cloudwright Security Harden

Scan for security findings, auto-remediate, and re-scan until no critical or high findings remain.

## When to Use

- Pre-deployment security hardening pass
- After designing a new architecture that has not been security-reviewed
- Satisfying a security gate before exporting to IaC

## Chain

```
security_scan  →  modify_architecture (fix findings)  →  security_scan  →  [loop until clean]
```

1. **Scan** — identify all security findings with severity
2. **Modify** — instruct the LLM to fix critical and high findings
3. **Re-scan** — verify fixes were applied
4. **Repeat** if new findings introduced (max 3 iterations)

## CLI Usage

```bash
# Step 1: initial scan
cloudwright security arch.yaml --fail-on high

# Step 2: fix findings
cloudwright modify arch.yaml "fix all security findings: enable encryption at rest on RDS, remove IAM wildcard from lambda role, enforce HTTPS on ALB"

# Step 3: re-scan
cloudwright security arch.yaml --fail-on high

# If still failing, iterate
cloudwright modify arch.yaml "fix remaining security finding: NO_HTTPS on internal ALB"
cloudwright security arch.yaml --fail-on high
```

## MCP Tool Usage

```python
MAX_ITERATIONS = 3
for i in range(MAX_ITERATIONS):
    report = security_scan(spec_json=spec, fail_on="high")
    critical_high = [f for f in report["findings"] if f["severity"] in ("critical", "high")]

    if not critical_high:
        break  # clean

    # Build remediation instruction from findings
    messages = [f["message"] for f in critical_high]
    remediations = [f["remediation"] for f in critical_high]
    instruction = "Fix security findings: " + "; ".join(remediations)

    spec = modify_architecture(spec_json=spec, instruction=instruction)
```

## MCP Tool Calls

```json
// Scan
{
  "tool": "security_scan",
  "arguments": {"spec_json": <spec>, "fail_on": "high"}
}

// Fix findings
{
  "tool": "modify_architecture",
  "arguments": {
    "spec_json": <spec>,
    "instruction": "Fix these security issues: (1) Enable encryption at rest on RDS instance 'db'. (2) Remove IAM wildcard action from lambda execution role. (3) Redirect HTTP to HTTPS on the ALB."
  }
}

// Re-scan
{
  "tool": "security_scan",
  "arguments": {"spec_json": <modified_spec>, "fail_on": "high"}
}
```

## Example Output

```
Iteration 1:
  Findings: 3 (1 critical, 2 high)
  - [CRITICAL] NO_ENCRYPTION_AT_REST — RDS 'db'
  - [HIGH]     IAM_WILDCARD — lambda execution role
  - [HIGH]     NO_HTTPS — ALB listener

Applying fixes...

Iteration 2:
  Findings: 0
  [PASS] No critical or high findings.

Result: Architecture hardened in 2 iterations.
```

## Stopping Conditions

- **Clean** — zero critical/high findings after any iteration
- **Max iterations** — stop after 3 iterations; report remaining findings for manual review
- **New findings introduced** — if a fix introduces a new finding not in the original list, flag it rather than silently looping

## Follow-Up Actions

After hardening:
- `cloudwright validate arch.yaml --compliance <framework>` — confirm compliance post-hardening
- `cloudwright export arch.yaml --format terraform` — export the hardened spec
- `cloudwright score arch.yaml` — security dimension should improve
