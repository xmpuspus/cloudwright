"""Export architecture to Terraform example.

Shows how to design, validate, and export to IaC.
"""

from silmaril import ArchSpec, Validator
from silmaril.differ import Differ

# Load a spec from YAML
spec_yaml = """
name: Serverless API
version: 1
provider: aws
region: us-east-1
components:
  - id: api_gw
    service: api_gateway
    provider: aws
    label: API Gateway
    description: REST API endpoint
    tier: 0
  - id: auth
    service: cognito
    provider: aws
    label: Cognito Auth
    description: User authentication
    tier: 0
  - id: handler
    service: lambda
    provider: aws
    label: Lambda Handlers
    description: API request handlers
    tier: 2
    config:
      runtime: python3.12
      memory_mb: 256
      monthly_requests: 1000000
  - id: db
    service: dynamodb
    provider: aws
    label: DynamoDB
    description: NoSQL data store
    tier: 3
    config:
      billing_mode: provisioned
      read_capacity: 10
      write_capacity: 10
  - id: storage
    service: s3
    provider: aws
    label: S3 Bucket
    description: File storage
    tier: 4
    config:
      storage_gb: 50
connections:
  - source: api_gw
    target: auth
    label: Auth check
  - source: api_gw
    target: handler
    label: Invoke
  - source: handler
    target: db
    label: Read/Write
  - source: handler
    target: storage
    label: File upload
"""

spec = ArchSpec.from_yaml(spec_yaml)

# Validate
validator = Validator()
results = validator.validate(spec, well_architected=True)
for r in results:
    print(f"{r.framework}: {'PASS' if r.passed else 'FAIL'} ({r.score:.0%})")
    for c in r.checks:
        if not c.passed:
            print(f"  [FAIL] {c.name}: {c.recommendation}")

# Export to Terraform
print("\n--- Terraform ---")
tf = spec.export("terraform")
print(tf[:500] + "...\n")

# Export to Mermaid
print("--- Mermaid ---")
print(spec.export("mermaid"))

# Modify and diff
spec_v2 = ArchSpec.from_yaml(spec_yaml)
spec_v2.version = 2
# Add a cache layer
from silmaril.spec import Component, Connection

spec_v2.components.append(
    Component(
        id="cache",
        service="elasticache",
        provider="aws",
        label="ElastiCache Redis",
        description="API response cache",
        tier=3,
        config={"engine": "redis", "node_type": "cache.t3.medium"},
    )
)
spec_v2.connections.append(
    Connection(source="handler", target="cache", label="Cache lookup", protocol="TCP", port=6379)
)

differ = Differ()
diff = differ.diff(spec, spec_v2)
print(f"\n--- Diff ---")
print(diff.summary)
for comp in diff.added:
    print(f"  + {comp.label} ({comp.service})")
