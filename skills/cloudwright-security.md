---
name: cloudwright-security
version: 0.3.0
description: Scan an architecture spec or Terraform HCL for security misconfigurations
layer: 1
mcp_tools: [security_scan, scan_terraform]
tags: [security, scanner, terraform, misconfig]
---

# Cloudwright Security

Detect security anti-patterns in architecture specs and Terraform HCL.

## When to Use

- Pre-deployment security gate
- Reviewing a spec before exporting to IaC
- Scanning existing Terraform for misconfigurations
- CI/CD pipeline step to block insecure deployments

## CLI Usage

```bash
# Scan a spec
cloudwright security arch.yaml

# Fail build on any critical finding
cloudwright security arch.yaml --fail-on critical

# Fail on critical or high (default)
cloudwright security arch.yaml --fail-on high

# JSON output for CI integration
cloudwright --json security arch.yaml --fail-on high
```

## MCP Tool Usage

### Scan an ArchSpec

```json
{
  "tool": "security_scan",
  "arguments": {
    "spec_json": <ArchSpec dict>,
    "fail_on": "high"
  }
}
```

### Scan Terraform HCL

```json
{
  "tool": "scan_terraform",
  "arguments": {
    "hcl": "resource \"aws_s3_bucket\" \"data\" {\n  bucket = \"my-bucket\"\n}\n"
  }
}
```

## Security Rules Checked

| Rule | Severity | Description |
|------|----------|-------------|
| `NO_ENCRYPTION_AT_REST` | critical | Data store without encryption |
| `OPEN_INGRESS` | critical | Security group allows 0.0.0.0/0 on non-HTTP ports |
| `NO_HTTPS` | high | API or load balancer serving plain HTTP |
| `IAM_WILDCARD` | high | IAM policy with `*` action or resource |
| `NO_BACKUP` | medium | Database without automated backups |
| `NO_MONITORING` | medium | Service with no metrics or alerting configured |
| `PUBLIC_S3_BUCKET` | critical | S3 bucket with public read/write ACL |
| `NO_MFA` | high | Root account or privileged role without MFA |
| `UNENCRYPTED_TRANSIT` | high | Internal service communication over HTTP |
| `HARDCODED_SECRET` | critical | Credentials in resource config blocks |

## Output Structure

```json
{
  "passed": false,
  "findings": [
    {
      "severity": "critical",
      "rule": "NO_ENCRYPTION_AT_REST",
      "component_id": "db",
      "message": "RDS instance 'db' has encryption disabled",
      "remediation": "Set storage_encrypted = true on the RDS instance"
    },
    {
      "severity": "high",
      "rule": "IAM_WILDCARD",
      "component_id": "lambda_role",
      "message": "IAM role uses wildcard action 'iam:*'",
      "remediation": "Restrict to minimum required actions"
    }
  ]
}
```

## `--fail-on` Thresholds

| Value | Exit code 1 when... |
|-------|---------------------|
| `critical` | Any critical finding exists |
| `high` | Any critical or high finding exists (default) |
| `medium` | Any finding of medium or higher exists |
| `none` | Never exit 1 (report only) |

## Follow-Up Actions

After scanning:
- On findings: `cloudwright modify arch.yaml "fix all security findings"` — auto-remediate
- Re-scan after modification to verify fixes
- For hardening loop, use the `cloudwright-security-harden` recipe skill

## Notes

- `scan_terraform` parses HCL text directly; it does not require Terraform to be installed.
- Security scan results do not include findings already addressed by explicit config (e.g., if `encryption_at_rest: true` is set, `NO_ENCRYPTION_AT_REST` is not raised).
