"""Multi-cloud architecture comparison example.

Requires: ANTHROPIC_API_KEY or OPENAI_API_KEY set in environment.
"""

from silmaril import Architect, Validator

# Design an architecture
arch = Architect()
spec = arch.design("3-tier web app with CDN, load balancer, 2 compute instances, and managed PostgreSQL database")

print(f"Primary architecture: {spec.name} on {spec.provider.upper()}")
if spec.cost_estimate:
    print(f"Monthly cost: ${spec.cost_estimate.monthly_total:.2f}")
print()

# Compare across clouds
alternatives = arch.compare(spec, providers=["gcp", "azure"])
for alt in alternatives:
    print(f"{alt.provider.upper()}: ${alt.monthly_total:.2f}/mo")
    for diff in alt.key_differences:
        print(f"  - {diff}")
    print()

# Validate against HIPAA
validator = Validator()
results = validator.validate(spec, compliance=["hipaa"])
for result in results:
    status = "PASSED" if result.passed else "FAILED"
    print(f"\n{result.framework.upper()} Review: {status} (score: {result.score:.0%})")
    for check in result.checks:
        icon = "[PASS]" if check.passed else "[FAIL]"
        print(f"  {icon} {check.name}: {check.detail}")
        if not check.passed and check.recommendation:
            print(f"        Recommendation: {check.recommendation}")
