"""Basic architecture design example.

Requires: ANTHROPIC_API_KEY or OPENAI_API_KEY set in environment.
"""

from silmaril import Architect, ArchSpec

# Design from natural language
arch = Architect()
spec = arch.design("3-tier web app on AWS with CloudFront, ALB, 2x EC2 m5.large, and RDS PostgreSQL")

print(f"Architecture: {spec.name}")
print(f"Components: {len(spec.components)}")
print(f"Provider: {spec.provider}")
print(f"Region: {spec.region}")
print()

# Print YAML
print("--- ArchSpec YAML ---")
print(spec.to_yaml())

# Cost breakdown
if spec.cost_estimate:
    print(f"\nTotal monthly cost: ${spec.cost_estimate.monthly_total:.2f}")
    for item in spec.cost_estimate.breakdown:
        print(f"  {item.component_id}: ${item.monthly:.2f}/mo ({item.service})")

# Export to Mermaid diagram
print("\n--- Mermaid Diagram ---")
print(spec.export("mermaid"))

# Save to file
spec_yaml = spec.to_yaml()
with open("my_architecture.yaml", "w") as f:
    f.write(spec_yaml)
print("\nSaved to my_architecture.yaml")
