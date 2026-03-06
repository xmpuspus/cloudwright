---
name: persona-security-reviewer
version: 0.3.0
description: Security auditor persona for architecture security validation, compliance checks, and infrastructure scanning
layer: 4
mcp_tools: [security_scan, scan_terraform, validate_compliance, lint_architecture]
tags: [persona, security, audit]
---

# Persona: Security Reviewer

Role-based configuration for a security auditor reviewing cloud architectures for vulnerabilities, compliance violations, and security best practices.

## Role Description

A security reviewer (security auditor) is responsible for identifying architectural security risks, validating compliance controls, and ensuring infrastructure-as-code follows security hardening guidelines. They review designs before deployment, audit running systems, and provide remediation guidance. Their focus is on finding and fixing security gaps early.

## Default Workflow

```
1. Scan → Validate → Lint → Remediate
   • Run security scan to identify architectural vulnerabilities
   • Validate compliance frameworks to check control coverage
   • Lint for anti-patterns and hardening gaps
   • Document findings and remediation steps
```

When reviewing infrastructure-as-code (Terraform, CloudFormation):
```
2. Scan Terraform → Identify gaps → Recommend hardening
   • Parse HCL and scan for misconfigurations
   • Check encryption, access controls, logging
   • Cross-reference with compliance requirements
   • Provide specific remediation code
```

## Suggested Tool Chain

| Tool | When | Output |
|------|------|--------|
| `security_scan` | Architecture review, baseline audit | Vulnerabilities by severity |
| `scan_terraform` | IaC review, before deployment | Misconfiguration findings + remediation |
| `validate_compliance` | Compliance-driven review | Framework violations and missing controls |
| `lint_architecture` | Best-practices audit | Anti-patterns and hardening recommendations |

**Typical workflow:**
```bash
# Baseline security scan
cloudwright security arch.yaml

# Validate against compliance frameworks
cloudwright validate arch.yaml --compliance hipaa,pci-dss,soc2

# Lint for best practices
cloudwright lint arch.yaml --level strict

# Scan generated Terraform (after export)
cloudwright security arch-terraform/*.tf
```

## Quick Commands

```bash
# Comprehensive security audit
cloudwright security arch.yaml --verbose

# Security scan with failure threshold
cloudwright security arch.yaml --fail-on critical

# Validate compliance with detailed remediation
cloudwright validate arch.yaml --compliance pci-dss --verbose

# Lint with strict security rules
cloudwright lint arch.yaml --security strict

# Scan Terraform files
cloudwright security terraform/main.tf

# Export findings as JSON for compliance reports
cloudwright security arch.yaml --json > security-report.json
```

## Example Interaction

**Scenario:** Pre-deployment security review of a healthcare platform requiring HIPAA compliance.

```
Security Reviewer: Run a comprehensive security audit on this healthcare platform spec.

Cloudwright: [scans architecture]
            Security Findings (8 total):

            CRITICAL (1):
              - Database encryption at rest: disabled
                → HIPAA requirement: all PII must be encrypted at rest
                → Fix: add config encryption_at_rest: true to RDS

            HIGH (3):
              - No audit logging configured (HIPAA audit trail required)
              - IAM policy too permissive (admin wildcard on non-admin role)
              - Data egress not monitored (regulatory tracking gap)

            MEDIUM (4):
              - No backup encryption specified (best practice)
              - Missing VPC Flow Logs (AWS security best practice)
              - Lambda environment variables not encrypted (sensitive config)
              - No WAF on API Gateway (optional but recommended for PII)

Reviewer: cloudwright validate arch.yaml --compliance hipaa
Cloudwright: HIPAA Validation Results:
            ✓ PASS: Encryption at rest (after fix above)
            ✓ PASS: Encryption in transit (TLS configured)
            ✓ PASS: Access controls (RBAC via IAM)
            ✓ PASS: Audit trail (CloudTrail enabled)
            ✓ PASS: Data retention (30-day backup retention)
            ✓ PASS: Incident response plan (documented)
            ⚠ WARN: PHI access logs — must be reviewed quarterly (note for ops)

Reviewer: cloudwright lint arch.yaml --security strict
Cloudwright: Lint Findings (6):
            ERROR: DB not in private subnet (CRITICAL SECURITY)
              → Move RDS to private-only VPC, expose via proxy
            ERROR: No network segmentation between tiers
              → Add security groups: app→db only on port 5432
            WARN: Lambda timeout set to 60s (may abort mid-operation)
              → Increase to 300s for data consistency during anomaly
            WARN: No MFA on root user (best practice)
            WARN: KMS key rotation not enabled
            INFO: Consider IMDSv2 for EC2 instances (defense-in-depth)

Reviewer: Documents all findings with severity and remediation.

Architect: Modifies spec to add encryption, audit logging, and network segmentation.

Reviewer: Re-runs security scan.
Cloudwright: Updated Findings (1 remaining):
            MEDIUM: No WAF on API Gateway (optional, but recommended)
              → Suggested config: enable WAF with managed OWASP rules

Reviewer: "WAF is optional, let's make it a post-launch item."
         Approves spec for deployment.
```

## IaC Scanning Workflow

**Scenario:** Reviewing generated Terraform before applying to production.

```
Reviewer: cloudwright security terraform/ --show-fixes
Cloudwright: Terraform Security Scan Results:

            File: terraform/rds.tf
            Line 12: db_subnet_group_name unset (DB publicly accessible)
              Fix:
                - name = aws_db_subnet_group.private.id
                  db_subnet_group_name = aws_db_subnet_group.private.name

            File: terraform/security-groups.tf
            Line 8: Ingress rule allows 0.0.0.0/0 on port 5432
              Fix:
                - cidr_blocks = ["0.0.0.0/0"]
                  cidr_blocks = ["10.0.0.0/8"]  # Private VPC CIDR

            File: terraform/lambda.tf
            Line 15: Environment variable stores API key (plaintext)
              Fix:
                - environment {
                -   variables = { API_KEY = "sk-xxx" }
                - }
                + environment {
                +   variables = { API_KEY_SECRET = aws_secretsmanager_secret.api_key.arn }
                + }

Reviewer: Applies recommended fixes, commits remediated Terraform.
```

## Integration with Other Personas

- **Cloud Architect:** Provides architecture spec for security review; works with reviewer to harden design before validation
- **DevOps Engineer:** Implements security hardening recommendations in IaC, scans before deployment
- **Cost Engineer:** May suggest cost optimizations that trade off security (e.g., removing WAF); reviewer escalates as policy decision

## Security Audit Checklist

Before approving an architecture:

- [ ] **Encryption:** All data at rest and in transit uses approved standards (AES-256, TLS 1.2+)
- [ ] **Access Control:** RBAC configured, no wildcard permissions, MFA on sensitive operations
- [ ] **Audit & Logging:** CloudTrail, VPC Flow Logs, application logs enabled and retained per policy
- [ ] **Network:** Private subnets for sensitive components, security groups enforcing least privilege
- [ ] **Data Protection:** PII encrypted, no plaintext credentials in code/env, secrets stored in vault
- [ ] **Compliance:** All required controls mapped and verified (HIPAA, PCI-DSS, SOC2, etc.)
- [ ] **Backup & Recovery:** Backup encryption enabled, retention policy set, restore tested
- [ ] **Incident Response:** Alerts configured for critical events, runbooks documented
- [ ] **Patching:** Automated patching for OS and dependencies, or manual process documented
- [ ] **Monitoring:** Security events monitored, SIEM integration or log aggregation configured

## Common Findings & Fixes

### Database Encryption

```yaml
# Before: Unencrypted
components:
  - id: db
    service: rds_postgres
    config:
      encryption_at_rest: false
      encrypted_backups: false

# After: Encrypted
components:
  - id: db
    service: rds_postgres
    config:
      encryption_at_rest: true
      kms_key: aws_kms_key.db
      encrypted_backups: true
      backup_retention_days: 30
```

### Audit Logging

```yaml
# Before: No audit trail
components:
  - id: app
    service: lambda
    config:
      logging: null

# After: Full audit trail
components:
  - id: app
    service: lambda
    config:
      logging: cloudwatch
      log_retention_days: 90
      log_encryption: true
```

### Network Segmentation

```yaml
# Before: Cross-tier access
connections:
  - source: frontend
    target: db
    config:
      port: 5432  # Direct database access

# After: API layer only
connections:
  - source: frontend
    target: api
  - source: api
    target: db
    config:
      port: 5432  # DB only accessible from app tier
```

## Tips

1. **Shift left.** Audit during design, not after deployment. Fixing security in IaC is 10x cheaper than fixing production incidents.
2. **Compliance ≠ Security.** Passing HIPAA doesn't mean the architecture is secure. Run both compliance validation and security scan.
3. **Document findings with context.** "Missing encryption" is useless; "Database stores unencrypted PII, violates HIPAA §164.312(a)(2)(i)" is actionable.
4. **Provide fixes, not just findings.** Include specific Terraform/spec changes reviewees can implement.
5. **Threat model the architecture.** Consider data flows, trust boundaries, and attack surface. Ask "How would an attacker compromise PII?"
