"""Compliance report exporter — audit-ready control-to-component mapping."""

from __future__ import annotations

import datetime
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, ValidationResult


def render(spec: "ArchSpec", validation: "ValidationResult") -> str:
    """Generate a markdown compliance report with control-to-component mapping."""
    lines = []
    lines.append(f"# Compliance Report: {spec.name}")
    lines.append("")
    lines.append(f"**Date:** {datetime.date.today().isoformat()}")
    lines.append(f"**Provider:** {spec.provider}")
    lines.append(f"**Region:** {spec.region}")
    lines.append(f"**Components:** {len(spec.components)}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Framework:** {validation.framework}")
    lines.append(f"- **Overall Score:** {validation.score:.0%}")
    lines.append(f"- **Result:** {'PASS' if validation.passed else 'FAIL'}")
    passed_count = sum(1 for c in validation.checks if c.passed)
    lines.append(f"- **Passed:** {passed_count}/{len(validation.checks)}")
    lines.append("")

    # Group checks by category
    by_category = defaultdict(list)
    for check in validation.checks:
        by_category[check.category].append(check)

    for category, checks in sorted(by_category.items()):
        lines.append(f"## {category.replace('_', ' ').title()}")
        lines.append("")
        cat_passed = sum(1 for c in checks if c.passed)
        lines.append(f"**{cat_passed}/{len(checks)} controls satisfied**")
        lines.append("")

        for check in checks:
            status = "PASS" if check.passed else "FAIL"
            severity = check.severity.upper()
            lines.append(f"### [{status}] {check.name.replace('_', ' ').title()} ({severity})")
            lines.append("")
            lines.append(check.detail)
            lines.append("")

            if not check.passed and check.recommendation:
                lines.append(f"**Recommendation:** {check.recommendation}")
                lines.append("")

            relevant = _find_relevant_components(spec, check)
            if relevant:
                lines.append("**Relevant Components:**")
                for comp_id, reason in relevant:
                    lines.append(f"- `{comp_id}`: {reason}")
                lines.append("")

    # Component inventory
    lines.append("## Component Inventory")
    lines.append("")
    lines.append("| ID | Service | Provider | Tier | Encrypted |")
    lines.append("|---|---|---|---|---|")
    for c in spec.components:
        encrypted = "Yes" if c.config.get("encryption") else "No"
        lines.append(f"| {c.id} | {c.service} | {c.provider} | {c.tier} | {encrypted} |")
    lines.append("")

    # Evidence checklist
    lines.append("## Evidence Checklist")
    lines.append("")
    lines.append("- [ ] Architecture spec reviewed and approved")
    lines.append("- [ ] Cost estimate within budget")
    lines.append("- [ ] All FAIL findings have remediation plan")
    lines.append("- [ ] Terraform/CloudFormation generated and validated")
    lines.append("- [ ] Security review completed")

    return "\n".join(lines)


def _find_relevant_components(spec: "ArchSpec", check) -> list[tuple[str, str]]:
    """Map a validation check to relevant components by check name heuristics."""
    relevant = []
    check_lower = check.name.lower()

    for c in spec.components:
        svc = c.service.lower()
        cfg = c.config

        if "encryption" in check_lower:
            if svc in (
                "rds",
                "aurora",
                "dynamodb",
                "elasticache",
                "redshift",
                "cloud_sql",
                "firestore",
                "spanner",
                "memorystore",
                "bigquery",
                "azure_sql",
                "cosmos_db",
                "azure_cache",
                "synapse",
                "s3",
                "cloud_storage",
                "blob_storage",
            ):
                reason = "encrypts data" if cfg.get("encryption") else "needs encryption"
                relevant.append((c.id, reason))
        elif "logging" in check_lower or "audit" in check_lower or "monitoring" in check_lower:
            if svc in ("cloudwatch", "cloudtrail", "cloud_logging", "azure_monitor", "cloud_monitoring"):
                relevant.append((c.id, "provides logging/monitoring"))
        elif "waf" in check_lower or "firewall" in check_lower:
            if svc in ("waf", "cloud_armor", "azure_waf"):
                relevant.append((c.id, "provides WAF protection"))
        elif "multi_az" in check_lower or "availability" in check_lower or "no_single" in check_lower:
            if cfg.get("multi_az"):
                relevant.append((c.id, "multi-AZ enabled"))
            elif svc in ("rds", "aurora", "cloud_sql", "azure_sql", "cosmos_db"):
                relevant.append((c.id, "single-AZ (risk)"))
        elif "access" in check_lower or "auth" in check_lower or "identity" in check_lower:
            if svc in ("cognito", "firebase_auth", "azure_ad", "iam"):
                relevant.append((c.id, "provides authentication/authorization"))
        elif "baa" in check_lower:
            relevant.append((c.id, f"service={svc}"))

    return relevant
