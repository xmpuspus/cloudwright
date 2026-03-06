---
name: persona-cost-engineer
version: 0.3.0
description: FinOps engineer persona focused on cloud cost optimization and provider comparison
layer: 4
mcp_tools: [estimate_cost, compare_provider_costs, score_architecture]
tags: [persona, finops, cost]
---

# Persona: Cost Engineer (FinOps)

Role-based configuration for a FinOps engineer optimizing cloud spend and comparing cost tradeoffs across providers.

## Role Description

A FinOps engineer (Cost Engineer) is responsible for rightsizing architectures, optimizing spend, and comparing provider options to maximize cloud efficiency. They work with architects and finance teams to balance cost, performance, and compliance. Their focus is on per-component pricing, scaling strategies, and multi-provider comparisons.

## Default Workflow

```
1. Estimate → Compare → Optimize
   • Get baseline cost estimate on current provider
   • Compare with alternatives (AWS, GCP, Azure, Databricks)
   • Identify high-cost components and optimization opportunities
   • Score cost dimension to track improvement over time
```

When optimizing:
```
2. Modify → Re-estimate → Track
   • Right-size components (change instance types, scaling policies)
   • Re-run estimation to verify savings
   • Run score to track cost dimension improvement
   • Document cost improvements for stakeholder reporting
```

## Suggested Tool Chain

| Tool | When | Output |
|------|------|--------|
| `estimate_cost` | Baseline, after any spec change | Monthly/annual cost breakdown |
| `compare_provider_costs` | Evaluating multi-cloud options | Cost comparison table: AWS vs GCP vs Azure |
| `score_architecture` | Tracking cost optimization progress | Cost dimension score (0-100) |

**Typical sequence:**
```bash
# Baseline estimate
cloudwright cost arch.yaml

# Compare across providers
cloudwright cost arch.yaml --compare

# Optimize (modify spec)
# Re-estimate to verify savings
cloudwright cost arch-optimized.yaml

# Track improvement in cost score
cloudwright score arch.yaml
cloudwright score arch-optimized.yaml
```

## Quick Commands

```bash
# Estimate cost of current design
cloudwright cost arch.yaml

# Compare same architecture across all providers
cloudwright cost arch.yaml --compare aws,gcp,azure,databricks

# Get annual projection
cloudwright cost arch.yaml --annual

# Show cost breakdown by tier (presentation, application, data)
cloudwright cost arch.yaml --by-tier

# Compare two architectures
cloudwright cost arch-v1.yaml --vs arch-v2.yaml
```

## Example Interaction

**Scenario:** FinOps review of an analytics platform. Budget is $15k/month, current spend is $18.2k.

```
FinOps: Show me the baseline costs and compare providers for our analytics platform.

Cloudwright: [estimates cost on AWS]
            Current: $18,234/month ($218.8k/year)
            Components:
              - RDS PostgreSQL (db-1): $2,400/month (t3.xlarge, Multi-AZ)
              - EMR (processing):     $9,100/month (on-demand nodes, always-on)
              - S3 (storage):          $1,800/month
              - Redshift (warehouse):  $4,500/month (ra3.xlplusds, 2 nodes)
              - [other components]:     $434/month

FinOps: Compare with GCP and Azure.

Cloudwright: Cost Comparison (same architecture):
            AWS:       $18,234/month  (baseline)
            GCP:       $16,800/month  (-7.9%, BigQuery replaces Redshift)
            Azure:     $17,100/month  (-6.2%, better instance pricing)
            Databricks: $15,900/month (-12.8%, warehouse + compute unified)

FinOps: What's driving the difference?

Cloudwright: Biggest variance: data warehouse
            - Redshift (AWS):       $4,500/month (always-on)
            - BigQuery (GCP):       $3,200/month (on-demand query pricing)
            - Synapse (Azure):      $3,800/month (on-demand)
            - Databricks SQL:       $2,100/month (shared compute pool)

FinOps: Let's optimize on AWS first. Can we reduce Redshift spend?

Architect: Modifies spec:
           - Redshift: pause warehouse during off-hours → auto-resume
           - EMR: use spot instances for non-critical jobs (30% savings)

FinOps: cloudwright cost arch-optimized.yaml
Cloudwright: Optimized (AWS): $14,820/month (-18.8%)
            Breakdown:
              - RDS:        $2,400 (no change)
              - EMR:        $6,370 (was $9,100, spot + on-demand mix)
              - Redshift:   $3,200 (was $4,500, scheduled pause)
              - S3:         $1,800 (no change)
              - [other]:      $50

FinOps: That gets us under budget. Let me score the architecture.

Cloudwright: Cost Score: 84/100 (was 76)
            Reliability: 78/100 (Redshift pause adds failover latency)
            [trade-off noted: slight reliability hit for 18.8% savings]

FinOps: Acceptable. Now compare optimized version to Databricks.

Cloudwright: Databricks architecture (optimized):
            $15,120/month (vs. $14,820 AWS optimized)
            Single warehouse + compute (simpler ops)
            [Databricks wins on operationsl complexity, AWS on total cost]

FinOps: Present AWS optimized + Databricks as options to leadership.
```

## Integration with Other Personas

- **Cloud Architect:** Provides validated, compliance-approved specs for cost optimization
- **Security Reviewer:** Ensures cost optimizations (e.g., spot instances) don't violate security policies
- **DevOps Engineer:** Implements the cost-optimized spec and monitors actual spend vs. estimate

## Cost Optimization Patterns

### Right-Sizing Components

```bash
# Before: db instance too large
components:
  - service: rds_postgres
    config:
      instance_type: db.r5.2xlarge  # $4,500/month
      multi_az: true

# After: size down based on utilization
components:
  - service: rds_postgres
    config:
      instance_type: db.r5.large    # $1,100/month
      multi_az: true
```

### Scaling Strategy

```bash
# Before: always-on cluster
components:
  - service: emr
    config:
      scaling: static
      nodes: 5  # always running, $9,100/month

# After: auto-scaling + spot
components:
  - service: emr
    config:
      scaling: auto
      min_nodes: 1
      max_nodes: 5
      spot_percentage: 70  # 30% savings
```

### Scheduled Operations

```bash
# Before: 24/7 warehouse
components:
  - service: redshift
    config:
      pause_schedule: null

# After: pause during off-hours
components:
  - service: redshift
    config:
      pause_schedule: "0 20 * * *"  # 8 PM UTC
      resume_schedule: "0 6 * * *"  # 6 AM UTC
```

## Tips

1. **Compare early, decide late.** Multi-cloud cost comparisons often reveal 10-20% swings; comparing before architecture is locked saves rework.
2. **Optimize in order:** Components, scaling, schedules, then provider switch. Each gives diminishing returns.
3. **Track actual vs. estimate.** Use score cost dimension monthly to validate estimates and catch cost drift.
4. **Document assumptions.** Estimates depend on workload patterns (9-5 vs. 24/7, batch vs. streaming). Document for stakeholders.
5. **Watch for hidden costs.** Data egress, inter-region transfers, and API calls are often overlooked — compare provider cost models carefully.
