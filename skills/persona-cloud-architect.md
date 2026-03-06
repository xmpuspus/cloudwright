---
name: persona-cloud-architect
version: 0.3.0
description: Senior cloud architect persona for architecture design, validation, and optimization
layer: 4
mcp_tools: [design_architecture, validate_compliance, score_architecture, analyze_blast_radius]
tags: [persona, architect, design]
---

# Persona: Cloud Architect

Role-based configuration for a senior cloud architect using Cloudwright for architecture design, validation, and performance optimization.

## Role Description

A cloud architect is responsible for designing scalable, resilient, and cost-effective cloud systems. They validate designs against compliance requirements, identify single points of failure, and optimize for operational maturity. Their workflow blends strategic design decisions with detailed technical validation.

## Default Workflow

```
1. Design → Validate → Score → Analyze
   • Start with natural-language requirements
   • Check compliance against regulatory frameworks
   • Assess overall quality and maturity
   • Identify architectural risks and SPOFs
```

When iterating:
```
2. Modify → Re-validate → Re-score → Document
   • Make targeted improvements based on findings
   • Re-run validation to confirm compliance
   • Track quality metrics across iterations
   • Generate deployment-ready documentation
```

## Suggested Tool Chain

| Tool | When | Output |
|------|------|--------|
| `design_architecture` | Initial design or exploring alternatives | ArchSpec with components and connections |
| `validate_compliance` | After design, before escalation | Compliance violations and remediation steps |
| `score_architecture` | Quality checkpoint before approval | Maturity score across 5 dimensions |
| `analyze_blast_radius` | Risk assessment phase | SPOF analysis and cascade impact |

**Multi-step pipeline:**
```bash
# Full architecture review
cloudwright design "..." > arch.yaml
cloudwright validate arch.yaml --compliance hipaa,pci-dss
cloudwright score arch.yaml
cloudwright analyze arch.yaml
# Synthesize findings into review document
```

## Quick Commands

```bash
# Design with compliance constraints
cloudwright design "Microservices platform" \
  --provider aws \
  --compliance pci-dss,soc2 \
  --budget 10000

# Validate multiple frameworks at once
cloudwright validate arch.yaml \
  --compliance hipaa,soc2,gdpr

# Score and get detailed breakdown
cloudwright score arch.yaml --verbose

# Analyze blast radius for all components
cloudwright analyze arch.yaml --show-paths
```

## Example Interaction

**Scenario:** New fintech payment service requiring PCI-DSS and SOC2 compliance.

```
Architect: Design a payment processing system for an e-commerce platform
          that needs PCI-DSS and SOC2 compliance, with < $5000/month budget.

Cloudwright: [generates ArchSpec with 8 components]
            - API Gateway (encrypted)
            - Payment Processor (vaulting)
            - Database (Multi-AZ, encrypted at rest)
            - Audit Logger
            - Monitoring/Alerting
            - ...

Architect: cloudwright validate arch.yaml --compliance pci-dss,soc2
Cloudwright: [PASS] PCI-DSS — encryption, vaulting, audit trail present
            [PASS] SOC2 — monitoring, backups, access controls configured
            [WARN] MFA not explicitly on admin access — remediate?

Architect: cloudwright score arch.yaml
Cloudwright: Reliability: 82 (Multi-AZ, no single-AZ, health checks)
            Security:    88 (encrypted, vaulted, audit trail)
            Cost:        76 (on budget, room for HA improvements)
            Compliance:  94 (PCI-DSS ready)
            Complexity:  71 (8 components, moderate operational overhead)

Architect: cloudwright analyze arch.yaml
Cloudwright: SPOF detected: Payment Processor (blast radius: 6 of 8)
            → Recommend failover or multi-region strategy

Architect: Modifies spec to add secondary payment processor in different AZ,
          re-runs validate → score → analyze, then exports to Terraform.
```

## Integration with Other Personas

- **Security Reviewer:** Uses same spec but runs `security_scan` and `scan_terraform` instead
- **Cost Engineer:** Takes validated spec and runs `estimate_cost`, `compare_provider_costs`, optimization loops
- **DevOps Engineer:** Takes approved spec and runs `export`, generates IaC, executes deployment

## Tips

1. **Always design before validating.** Validation catches gaps in an existing design; it doesn't create designs.
2. **Compliance drives components.** When compliance is specified upfront, the design includes required controls automatically.
3. **Score for maturity, not perfection.** A 75/100 architecture is production-ready if it scores high on Reliability and Security.
4. **Analyze blast radius early.** SPOFs identified during design are cheaper to fix than discovered post-deployment.
5. **Iterate with constraints.** Re-run design with stricter budgets or compliance to explore tradeoffs.
