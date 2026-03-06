# Cloudwright Skills Directory

This directory contains all Cloudwright CLI skills organized by layers of abstraction and functionality. Skills are modular, composable, and designed to be mixed and matched for different workflows.

## Skill Layers

Cloudwright skills are organized into 5 layers, from lowest-level primitives to highest-level role configurations:

### Layer 0: Shared
Foundation utilities shared across all skills. Covers authentication, CLI flags, output formatting, and common patterns.

- **auth**: Authentication and API key management
- **flags**: Standard CLI flags (--json, --verbose, --provider, etc.)
- **output**: Output formatting (JSON, YAML, Markdown, table)

### Layer 1: Individual Commands
Atomic operations that do one thing well. Each maps to a single MCP tool or a tight workflow.

- **cloudwright-design**: Design a cloud architecture from description
- **cloudwright-cost**: Estimate costs for an architecture
- **cloudwright-validate**: Validate compliance against frameworks (HIPAA, PCI-DSS, SOC2, etc.)
- **cloudwright-security**: Security audit of an architecture
- **cloudwright-score**: Rate architecture maturity across 5 dimensions
- **cloudwright-lint**: Find anti-patterns and best-practice violations
- **cloudwright-analyze**: Blast radius analysis and SPOF detection
- **cloudwright-export**: Generate infrastructure-as-code (Terraform, CloudFormation, Pulumi)
- **cloudwright-catalog**: List available services, providers, and pricing models
- **cloudwright-chat**: Conversational architecture assistant (web UI)

### Layer 2: Multi-Step Helpers
Workflows combining 2-3 commands for a specific optimization task.

- **cloudwright-design-optimize**: Design → Score → Modify for better maturity
- **cloudwright-cost-reduce**: Estimate → Compare → Optimize for savings
- **cloudwright-security-harden**: Security Scan → Validate → Lint → Fix
- **cloudwright-migrate-provider**: Design on source → Cost compare → Export to destination

### Layer 3: Recipes
Multi-command pipelines (3+ commands) that synthesize results into comprehensive reports.

- **recipe-architecture-review**: Lint + Score + Analyze + Security → Health Report
- **recipe-compliance-audit**: Validate + Scan → Compliance Report with remediation
- **recipe-cost-optimize**: Estimate + Compare + Score → Cost optimization roadmap
- **recipe-deploy-ready**: Lint + Validate + Export → Deployment checklist

### Layer 4: Personas
Role-based configurations that bundle tool chains, defaults, and guidance for specific job functions.

- **persona-cloud-architect**: Design, validate, score, analyze — for senior architects
- **persona-cost-engineer**: Estimate, compare, optimize — for FinOps engineers
- **persona-security-reviewer**: Scan, validate, lint — for security auditors
- (Future) **persona-devops-engineer**: Export, deploy, monitor — for infrastructure engineers
- (Future) **persona-product-manager**: Chat, estimate, compare — for product strategy

---

## Skills Directory

| Skill Name | Layer | Description | MCP Tools | Tags |
|----------|-------|-------------|-----------|------|
| cloudwright-shared | 0 | Auth, flags, output modes | — | shared, foundation |
| cloudwright-design | 1 | Design architecture from description | design_architecture, estimate_cost | design, architect, llm |
| cloudwright-cost | 1 | Estimate monthly/annual costs | estimate_cost | cost, pricing |
| cloudwright-validate | 1 | Check compliance (HIPAA, PCI-DSS, SOC2, etc.) | validate_compliance | compliance, validate, audit |
| cloudwright-security | 1 | Security vulnerability scan | security_scan | security, audit, scan |
| cloudwright-score | 1 | Rate architecture maturity (reliability, security, cost, compliance, complexity) | score_architecture | score, maturity, quality |
| cloudwright-lint | 1 | Find anti-patterns and best-practice violations | lint_architecture | lint, bestpractices |
| cloudwright-analyze | 1 | Blast radius & SPOF detection | analyze_blast_radius | analyze, risk, spof |
| cloudwright-export | 1 | Generate IaC (Terraform, CloudFormation, Pulumi) | export_infrastructure | export, iac, deploy |
| cloudwright-catalog | 1 | List services, regions, pricing models | list_services | catalog, reference |
| cloudwright-chat | 1 | Conversational assistant (web UI, streaming) | design_architecture, estimate_cost, etc. | chat, assistant, conversational |
| cloudwright-design-optimize | 2 | Design → Score → iterate for maturity | design_architecture, score_architecture | design, optimize, iteration |
| cloudwright-cost-reduce | 2 | Estimate → Compare providers → Optimize | estimate_cost, compare_provider_costs | cost, optimize, providers |
| cloudwright-security-harden | 2 | Scan → Validate → Lint → Generate fixes | security_scan, validate_compliance, lint_architecture | security, harden, optimize |
| cloudwright-migrate-provider | 2 | Design on provider A → Compare → Export for provider B | design_architecture, compare_provider_costs, export_infrastructure | migrate, multi-cloud, export |
| recipe-architecture-review | 3 | Lint + Score + Analyze + Security → Health Report | lint_architecture, score_architecture, analyze_blast_radius, security_scan | recipe, review, health, report |
| recipe-compliance-audit | 3 | Validate compliance frameworks → Report with remediation | validate_compliance, security_scan | recipe, compliance, audit, report |
| recipe-cost-optimize | 3 | Estimate → Compare → Score → Cost roadmap | estimate_cost, compare_provider_costs, score_architecture | recipe, cost, optimize, roadmap |
| recipe-deploy-ready | 3 | Lint → Validate → Score → Export → Checklist | lint_architecture, validate_compliance, score_architecture, export_infrastructure | recipe, deploy, checklist |
| persona-cloud-architect | 4 | Design, validate, score, analyze workflows for architects | design_architecture, validate_compliance, score_architecture, analyze_blast_radius | persona, architect, design |
| persona-cost-engineer | 4 | Cost estimate, compare, optimize workflows for FinOps | estimate_cost, compare_provider_costs, score_architecture | persona, finops, cost |
| persona-security-reviewer | 4 | Security scan, validate, lint workflows for auditors | security_scan, scan_terraform, validate_compliance, lint_architecture | persona, security, audit |

---

## Usage Examples

### Using Layer 1 (Individual Commands)

```bash
# Design a new system
cloudwright design "Web app with React, Python, PostgreSQL"

# Estimate cost
cloudwright cost arch.yaml

# Validate HIPAA compliance
cloudwright validate arch.yaml --compliance hipaa

# Score maturity
cloudwright score arch.yaml

# Find problems
cloudwright lint arch.yaml

# Scan for security issues
cloudwright security arch.yaml

# Detect single points of failure
cloudwright analyze arch.yaml

# Generate Terraform
cloudwright export arch.yaml --format terraform
```

### Using Layer 2 (Multi-Step Helpers)

```bash
# Design and optimize for maturity
cloudwright design-optimize "E-commerce platform"

# Reduce costs through multi-cloud comparison
cloudwright cost-reduce arch.yaml

# Harden security posture
cloudwright security-harden arch.yaml

# Migrate to a different cloud provider
cloudwright migrate-provider arch.yaml --from aws --to gcp
```

### Using Layer 3 (Recipes)

```bash
# Full architecture health review
cloudwright recipe architecture-review arch.yaml

# Pre-deployment readiness checklist
cloudwright recipe deploy-ready arch.yaml

# Cost optimization roadmap with benchmarking
cloudwright recipe cost-optimize arch.yaml

# Compliance audit report (HIPAA, SOC2, PCI-DSS)
cloudwright recipe compliance-audit arch.yaml --frameworks hipaa,soc2,pci-dss
```

### Using Layer 4 (Personas)

Personas activate a role-specific workflow and defaults:

```bash
# Cloud Architect: Design → Validate → Score → Analyze
cloudwright --persona architect design "Payment platform"
# Then runs persona's suggested next steps

# Cost Engineer: Estimate → Compare → Optimize
cloudwright --persona cost-engineer cost arch.yaml
# Defaults to --compare all providers

# Security Reviewer: Scan → Validate → Lint
cloudwright --persona security-reviewer security arch.yaml --fail-on critical
# Strict defaults, comprehensive output
```

---

## Skill Composition Patterns

### Pattern 1: Quick Audit (5 min)

```bash
cloudwright score arch.yaml
cloudwright lint arch.yaml
```

### Pattern 2: Security Review (15 min)

```bash
cloudwright security arch.yaml
cloudwright validate arch.yaml --compliance pci-dss
cloudwright lint arch.yaml --security strict
```

### Pattern 3: Cost Optimization (30 min)

```bash
cloudwright cost arch.yaml
cloudwright cost arch.yaml --compare  # Multi-cloud
cloudwright cost arch.yaml --by-tier  # Breakdown
# Modify arch.yaml
cloudwright cost arch-optimized.yaml
cloudwright score arch.yaml vs arch-optimized.yaml
```

### Pattern 4: Full Pre-Deployment Review (45 min)

```bash
# Health
cloudwright recipe architecture-review arch.yaml

# Compliance
cloudwright recipe compliance-audit arch.yaml --frameworks hipaa,soc2

# Cost
cloudwright recipe cost-optimize arch.yaml

# Deploy
cloudwright recipe deploy-ready arch.yaml
```

---

## MCP Tool Matrix

Which tools does each skill use?

| Skill | design_arch | estimate_cost | validate_compliance | security_scan | score_arch | lint_arch | analyze_blast | export_iac | scan_tf |
|-------|---|---|---|---|---|---|---|---|---|
| cloudwright-design | ✓ | ✓ | — | — | — | — | — | — | — |
| cloudwright-cost | — | ✓ | — | — | — | — | — | — | — |
| cloudwright-validate | — | — | ✓ | — | — | — | — | — | — |
| cloudwright-security | — | — | — | ✓ | — | — | — | — | ✓ |
| cloudwright-score | — | — | — | — | ✓ | — | — | — | — |
| cloudwright-lint | — | — | — | — | — | ✓ | — | — | — |
| cloudwright-analyze | — | — | — | — | — | — | ✓ | — | — |
| cloudwright-export | — | — | — | — | — | — | — | ✓ | — |
| recipe-architecture-review | — | — | — | ✓ | ✓ | ✓ | ✓ | — | — |
| recipe-compliance-audit | — | — | ✓ | ✓ | — | — | — | — | — |
| recipe-cost-optimize | — | ✓ | — | — | ✓ | — | — | — | — |
| recipe-deploy-ready | — | — | ✓ | — | ✓ | ✓ | — | ✓ | — |
| persona-cloud-architect | ✓ | — | ✓ | — | ✓ | — | ✓ | — | — |
| persona-cost-engineer | — | ✓ | — | — | ✓ | — | — | — | — |
| persona-security-reviewer | — | — | ✓ | ✓ | — | ✓ | — | — | ✓ |

---

## Extending Skills

To add a new skill:

1. **Choose the layer:**
   - Layer 0 (shared): New auth method or output format
   - Layer 1 (command): New analysis tool or workflow
   - Layer 2 (helper): Combine 2-3 Layer 1 commands
   - Layer 3 (recipe): Combine 3+ commands with synthesis
   - Layer 4 (persona): New role-based configuration

2. **Create the file:** `skills/{layer-prefix}-{name}.md`
   - Format: YAML frontmatter + Markdown body
   - Include: description, MCP tools, usage examples, integration notes

3. **Update this README** with the new skill in the table

4. **Test** the skill against MCP tools and document any edge cases

---

## Notes for Skill Authors

- **Composability:** Skills should be usable in isolation and in combination
- **Idempotency:** Running a skill twice should produce the same output (or note what changed)
- **Clarity:** Every skill needs usage examples, expected output, and integration points
- **Attribution:** Link to other skills that complement yours
- **Versioning:** Skills follow the same semantic version as cloudwright core (e.g., 0.3.0)
