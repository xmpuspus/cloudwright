"""Full demonstration of all 7 Cloudwright capabilities.

Runs without LLM API keys — uses ArchSpec.from_yaml() directly.

Capabilities demonstrated:
  1. ArchSpec from inline YAML
  2. Cost estimation with CostEngine
  3. HIPAA compliance validation
  4. Terraform HCL export
  5. Mermaid diagram export
  6. Cross-provider cost comparison
  7. Structured diff between spec versions
"""

from cloudwright import ArchSpec
from cloudwright.cost import CostEngine
from cloudwright.differ import Differ
from cloudwright.exporter import export_spec
from cloudwright.spec import Component, Connection
from cloudwright.validator import Validator

SPEC_YAML = """
name: healthcare-portal
version: 1
provider: aws
region: us-east-1
components:
  - id: cdn
    service: cloudfront
    provider: aws
    label: CloudFront CDN
    tier: 0
    config:
      origins: 1
  - id: alb
    service: alb
    provider: aws
    label: Application Load Balancer
    tier: 1
    config:
      listeners: 2
  - id: web
    service: ec2
    provider: aws
    label: Web Servers
    tier: 2
    config:
      instance_type: t3.medium
      count: 2
  - id: api
    service: ec2
    provider: aws
    label: API Servers
    tier: 2
    config:
      instance_type: m5.large
      count: 2
  - id: cache
    service: elasticache
    provider: aws
    label: Redis Cache
    tier: 2
    config:
      engine: redis
      node_type: cache.r6g.large
      count: 2
  - id: db
    service: rds
    provider: aws
    label: PostgreSQL Database
    tier: 3
    config:
      engine: postgresql
      instance_class: db.r5.large
      multi_az: true
      storage_gb: 100
  - id: queue
    service: sqs
    provider: aws
    label: SQS Queue
    tier: 2
    config:
      estimated_monthly_requests: 1000000
connections:
  - source: cdn
    target: alb
    protocol: https
  - source: alb
    target: web
    protocol: https
  - source: web
    target: api
    protocol: https
  - source: api
    target: cache
    protocol: tcp
    port: 6379
  - source: api
    target: db
    protocol: tcp
    port: 5432
  - source: api
    target: queue
    protocol: https
"""


def sep(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# Load ArchSpec from YAML

sep("1. ArchSpec from YAML")

spec = ArchSpec.from_yaml(SPEC_YAML)
print(f"Name:       {spec.name}")
print(f"Provider:   {spec.provider}")
print(f"Region:     {spec.region}")
print(f"Components: {len(spec.components)}")
print(f"Connections:{len(spec.connections)}")
print()
print("Components:")
for c in spec.components:
    print(f"  {c.id:8s}  {c.service:15s}  {c.label}")

# Cost estimation

sep("2. Monthly Cost Breakdown")

engine = CostEngine()
priced = engine.price(spec)
est = priced.cost_estimate

print(f"{'Component':<10}  {'Service':<15}  {'Monthly':>10}  Notes")
print("-" * 60)
for item in est.breakdown:
    notes = f"  {item.notes}" if item.notes else ""
    print(f"{item.component_id:<10}  {item.service:<15}  ${item.monthly:>9,.2f}{notes}")
print("-" * 60)
print(f"{'TOTAL':<10}  {'':15}  ${est.monthly_total:>9,.2f}/mo")

# Keep the priced spec for diffing later
spec = priced

# HIPAA validation

sep("3. HIPAA Compliance Check")

validator = Validator()
results = validator.validate(spec, compliance=["hipaa"])
hipaa = results[0]

status = "PASS" if hipaa.passed else "FAIL"
print(f"Framework: {hipaa.framework}")
print(f"Status:    {status}")
print(f"Score:     {hipaa.score:.0%} ({sum(1 for c in hipaa.checks if c.passed)}/{len(hipaa.checks)} checks passed)")
print()
for check in hipaa.checks:
    icon = "[PASS]" if check.passed else "[FAIL]"
    print(f"  {icon} [{check.severity.upper():<8}] {check.name}")
    print(f"           {check.detail}")
    if not check.passed:
        print(f"           Fix: {check.recommendation}")

# Terraform export

sep("4. Terraform HCL Export")

tf_hcl = export_spec(spec, "terraform")
# Show first 50 lines — enough to demonstrate structure without flooding output
lines = tf_hcl.splitlines()
preview_lines = lines[:50]
print("\n".join(preview_lines))
if len(lines) > 50:
    print(f"\n... ({len(lines) - 50} more lines)")

# Mermaid diagram

sep("5. Mermaid Architecture Diagram")

mermaid = export_spec(spec, "mermaid")
print(mermaid)

# Cross-provider comparison

sep("6. Cross-Provider Cost Comparison")

alternatives = engine.compare_providers(spec, providers=["gcp", "azure"])

print(f"{'Provider':<8}  {'Monthly':>10}  {'vs AWS':>10}")
print("-" * 35)
aws_total = est.monthly_total
print(f"{'aws (base)':<8}  ${aws_total:>9,.2f}")
for alt in alternatives:
    delta = alt.monthly_total - aws_total
    sign = "+" if delta >= 0 else "-"
    print(f"{alt.provider:<8}  ${alt.monthly_total:>9,.2f}  {sign}${abs(delta):,.2f}")
    for diff_note in alt.key_differences[:3]:
        print(f"           - {diff_note}")

# Diff v1 -> v2 (add S3 audit log bucket)

sep("7. Spec Diff: v1 -> v2 (add audit log storage)")

# Build v2 by adding an S3 component for audit logs
spec_v2 = spec.model_copy(deep=True)
spec_v2 = spec_v2.model_copy(update={"version": 2})

audit_bucket = Component(
    id="audit_logs",
    service="s3",
    provider="aws",
    label="Audit Log Bucket",
    description="Immutable audit trail for HIPAA compliance",
    tier=3,
    config={
        "storage_gb": 500,
        "encryption": True,
        "versioning": True,
    },
)
spec_v2.components.append(audit_bucket)
spec_v2.connections.append(
    Connection(source="api", target="audit_logs", label="Audit write", protocol="https")
)

# Price v2 so the diff can compute cost delta
spec_v2 = engine.price(spec_v2)

differ = Differ()
diff = differ.diff(spec, spec_v2)

print(f"Summary: {diff.summary}")
print()

if diff.added:
    print("Added:")
    for c in diff.added:
        print(f"  + {c.id}  ({c.service})  {c.label}")

if diff.removed:
    print("Removed:")
    for c in diff.removed:
        print(f"  - {c.id}  ({c.service})")

if diff.changed:
    print(f"Changed: {len(diff.changed)} field(s)")
    for ch in diff.changed[:5]:
        print(f"  ~ {ch.component_id}.{ch.field}")

cost_sign = "+" if diff.cost_delta >= 0 else ""
print(f"\nCost delta: {cost_sign}${diff.cost_delta:,.2f}/mo")

if diff.compliance_impact:
    print("\nCompliance impact:")
    for note in diff.compliance_impact:
        print(f"  ! {note}")
else:
    print("\nNo adverse compliance impact detected.")

# Summary

sep("Summary")

print(f"Architecture:  {spec.name} ({spec.provider}/{spec.region})")
print(f"Components:    {len(spec.components)}")
print(f"Monthly cost:  ${est.monthly_total:,.2f}")
print(f"HIPAA:         {'PASS' if hipaa.passed else 'FAIL'} ({hipaa.score:.0%})")
print(f"Providers compared: AWS, {', '.join(a.provider.upper() for a in alternatives)}")
print(f"Diff (v2):     +{len(diff.added)} component(s), {cost_sign}${diff.cost_delta:,.2f}/mo")
print()
print("All 7 capabilities demonstrated successfully.")
