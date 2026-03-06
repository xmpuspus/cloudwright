---
name: cloudwright-validate
version: 0.3.0
description: Validate an architecture spec against compliance frameworks
layer: 1
mcp_tools: [validate_compliance]
tags: [compliance, hipaa, pci-dss, soc2, fedramp, gdpr, well-architected]
---

# Cloudwright Validate

Check an architecture against compliance frameworks and well-architected principles.

## When to Use

- User needs HIPAA, PCI-DSS, SOC 2, FedRAMP, or GDPR compliance verification
- User wants to run an AWS Well-Architected Framework review
- Pre-deployment compliance gate

## CLI Usage

```bash
# Single framework
cloudwright validate arch.yaml --compliance hipaa

# Multiple frameworks
cloudwright validate arch.yaml --compliance hipaa,pci-dss,soc2

# Well-Architected review
cloudwright validate arch.yaml --well-architected

# Both compliance and well-architected
cloudwright validate arch.yaml --compliance soc2 --well-architected

# Generate markdown compliance report
cloudwright validate arch.yaml --compliance hipaa --report compliance-report.md

# Generate PDF report
cloudwright validate arch.yaml --compliance hipaa,soc2 --pdf compliance-report.pdf
```

## MCP Tool Usage

```json
{
  "tool": "validate_compliance",
  "arguments": {
    "spec_json": <ArchSpec dict>,
    "frameworks": ["hipaa", "soc2"]
  }
}
```

## Supported Frameworks

| Framework | Key Requirements |
|-----------|-----------------|
| `hipaa` | Encryption at rest/transit, audit logs, BAA-eligible services, no PHI in logs |
| `pci-dss` | Network segmentation, WAF, no plaintext card data, quarterly vulnerability scans |
| `soc2` | Availability, confidentiality, change management, incident response |
| `fedramp` | FedRAMP-authorized services only, FIPS 140-2, MFA, US regions |
| `gdpr` | EU region options, data retention controls, right-to-erasure support |
| `well-architected` | Operational excellence, security, reliability, performance, cost |

## Output Structure

```json
{
  "framework": "hipaa",
  "passed": false,
  "violations": [
    {
      "rule": "HIPAA-164.312(a)",
      "severity": "critical",
      "component_id": "db",
      "message": "RDS instance has encryption_at_rest=false",
      "remediation": "Enable storage encryption on the RDS instance"
    }
  ],
  "controls_checked": 24,
  "controls_passed": 21
}
```

## Follow-Up Actions

After validation:
- On violations: `cloudwright modify arch.yaml "fix all HIPAA violations"` — auto-remediate
- On pass: proceed to `cloudwright export arch.yaml --format terraform`
- For audit trail: `cloudwright validate arch.yaml --compliance hipaa --pdf audit.pdf`

## Notes

- FedRAMP validation checks that all services used are on the FedRAMP Authorized list. Non-authorized services are flagged as critical violations.
- Running `--compliance hipaa,pci-dss` checks both frameworks independently and returns two result objects.
- Well-Architected review does not map to a pass/fail — it returns pillar scores and recommendations.
