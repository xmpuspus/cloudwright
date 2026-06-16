"""Compliance-gated component patterns.

Maps templates and approved modules to the compliance frameworks their
component sets actually cover. Tags are conservative: a framework is only
listed when the pattern's components address that framework's core technical
controls (encryption, HA, audit logging, access control, etc.).

Supported frameworks: hipaa, soc2, pci-dss, fedramp, iso27001, gdpr.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Pattern registry
#
# Each entry captures the pattern source (template key or module id), a
# display name, the frameworks it satisfies, and a per-framework justification.
#
# Rationale for framework inclusion:
#
# HIPAA  — needs encryption-at-rest + in-transit, access controls, audit logs,
#           and HA (uptime standard). Patterns with multi-AZ/HA + encryption on
#           all data tiers qualify.
# SOC 2  — availability, confidentiality, and security. Multi-AZ, HTTPS,
#           encryption, and access controls broadly satisfy trust service criteria.
# PCI-DSS — narrow: requires WAF, network segmentation (alb/gateway), encryption,
#           and TLS on every hop. Only patterns with an explicit WAF or gateway
#           with WAF config qualify.
# FedRAMP — requires FIPS-level encryption, HA across AZs, audit trails.
#           Patterns with multi-AZ encrypted managed services qualify at a
#           Moderate baseline; Databricks patterns do not (no FedRAMP ATOs).
# ISO 27001 — broad information security management. HTTPS, encryption, backup,
#             access controls, and HA are the technical pillars.
# GDPR    — data protection by design: encryption-at-rest, encryption-in-transit,
#           backup, and access controls. Does not require WAF. Most encrypted
#           multi-AZ patterns qualify.
# ---------------------------------------------------------------------------

_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "3-Tier Web Application (AWS)",
        "source": "template:3-tier-web-aws",
        "frameworks": {
            "soc2": "Multi-AZ RDS + HTTPS CDN/ALB + encryption satisfies availability and confidentiality criteria.",
            "hipaa": "Multi-AZ RDS with encryption + backup covers PHI durability and access control requirements.",
            "fedramp": "Multi-AZ managed RDS with encryption meets FedRAMP Moderate availability and data-protection controls.",
            "iso27001": "Encrypted RDS + HTTPS + backup + security groups address A.12 (operations security) and A.14 (secure development) controls.",
            "gdpr": "Encryption-at-rest and in-transit + backup aligns with GDPR Article 32 technical safeguards.",
        },
    },
    {
        "name": "Web Application (Azure)",
        "source": "template:web-app-azure",
        "frameworks": {
            "soc2": "App Gateway WAF + HTTPS CDN + Multi-AZ SQL + encryption covers availability and security trust criteria.",
            "hipaa": "Encrypted multi-AZ Azure SQL + WAF-backed gateway provides PHI protection and audit controls.",
            "pci-dss": "App Gateway with WAF enabled (waf: True) + HTTPS on every hop + encrypted SQL meets PCI-DSS requirements for cardholder-data environments.",
            "fedramp": "Multi-AZ Azure SQL with encryption meets FedRAMP Moderate data protection; WAF adds perimeter control.",
            "iso27001": "WAF + encryption + backup + HTTPS satisfies A.13 (communications security) and A.12 controls.",
            "gdpr": "Encrypted SQL + WAF + backup meets GDPR Article 32 technical safeguards.",
        },
    },
    {
        "name": "Microservices Platform (AWS)",
        "source": "template:microservices-aws",
        "frameworks": {
            "soc2": "ECS Fargate + encrypted RDS multi-AZ + encrypted ElastiCache + SQS encryption covers availability and confidentiality.",
            "hipaa": "Encryption on all data tiers (RDS, ElastiCache, SQS) + multi-AZ RDS meets HIPAA technical safeguard requirements.",
            "fedramp": "Multi-AZ RDS with encryption + encrypted messaging + managed container platform meets FedRAMP Moderate baseline.",
            "iso27001": "Full encryption stack + multi-AZ + backup satisfies A.10 (cryptography) and A.17 (business continuity) controls.",
            "gdpr": "Encryption-at-rest and in-transit on all data tiers + backup meets GDPR Article 32 obligations.",
        },
    },
    {
        "name": "Kubernetes Platform (AWS EKS)",
        "source": "template:kubernetes-aws",
        "frameworks": {
            "soc2": "EKS + encrypted RDS multi-AZ + encrypted ECR + HTTPS ingress covers availability and confidentiality criteria.",
            "hipaa": "Multi-AZ encrypted RDS + encrypted container images (ECR scan-on-push) + HTTPS meets HIPAA safeguards.",
            "fedramp": "Multi-AZ encrypted managed database + private container registry meets FedRAMP Moderate baseline.",
            "iso27001": "Encrypted RDS + ECR image scanning + multi-AZ + HTTPS aligns with ISO 27001 A.12 and A.14 controls.",
            "gdpr": "Encrypted storage + HTTPS + backup meets GDPR Article 32 technical safeguards.",
        },
    },
    {
        "name": "Data Warehouse (AWS)",
        "source": "template:data-warehouse-aws",
        "frameworks": {
            "soc2": "Encrypted Kinesis + encrypted S3 + encrypted Redshift multi-AZ + Athena covers availability and confidentiality.",
            "hipaa": "Full encryption stack (Kinesis, S3, Redshift) + multi-AZ + backup meets HIPAA data-at-rest and transit requirements.",
            "fedramp": "Encrypted managed streaming + S3 + multi-AZ Redshift meets FedRAMP Moderate data-protection controls.",
            "iso27001": "Encryption across all tiers + backup satisfies A.10 and A.17 controls.",
            "gdpr": "Encrypted storage and streaming + backup meets GDPR Article 32 for large-scale data processing.",
        },
    },
    {
        "name": "AWS Three-Tier Web (Module)",
        "source": "module:aws-three-tier-web",
        "frameworks": {
            "soc2": "Multi-AZ RDS + HTTPS CDN/ALB covers availability and confidentiality trust criteria.",
            "iso27001": "HTTPS + multi-AZ managed database aligns with A.12 and A.14 controls.",
            "gdpr": "HTTPS in-transit + multi-AZ persistence meets GDPR Article 32 baseline.",
        },
    },
    {
        "name": "AWS Serverless API (Module)",
        "source": "module:aws-serverless-api",
        "frameworks": {
            "soc2": "DynamoDB encryption + backup + HTTPS API Gateway meets confidentiality and availability criteria.",
            "gdpr": "DynamoDB encryption + backup provides GDPR Article 32 data protection for serverless APIs.",
        },
    },
    {
        "name": "Azure Three-Tier Web (Module)",
        "source": "module:azure-three-tier-web",
        "frameworks": {
            "soc2": "App Gateway WAF (WAF_v2 SKU) + HTTPS CDN + Azure SQL covers security and availability trust criteria.",
            "hipaa": "WAF-backed ingress + managed SQL with backup provides HIPAA technical safeguard controls.",
            "pci-dss": "App Gateway WAF_v2 SKU provides WAF on every inbound connection; HTTPS on all hops meets PCI-DSS network-security requirements.",
            "iso27001": "WAF + HTTPS + managed SQL satisfies A.13 and A.12 controls.",
            "gdpr": "HTTPS + WAF + managed SQL with backup meets GDPR Article 32 technical safeguards.",
        },
    },
]

# Build a flat lookup: framework -> sorted list of matching patterns
_BY_FRAMEWORK: dict[str, list[dict[str, Any]]] = {}
for _p in _PATTERNS:
    for _fw in _p["frameworks"]:
        _BY_FRAMEWORK.setdefault(_fw, []).append(_p)


def suggest_compliant_patterns(framework: str) -> list[dict[str, Any]]:
    """Return patterns pre-blessed for the given compliance framework.

    Patterns are returned in descending order of how many frameworks they
    satisfy (broader coverage first). Only patterns that honestly cover the
    framework's core technical controls are included.

    Args:
        framework: Lowercase framework name — hipaa, soc2, pci-dss,
            fedramp, iso27001, or gdpr.

    Returns:
        List of dicts with keys: name, source, frameworks (list), why (str).
        Empty list when the framework is unknown or no patterns qualify.
    """
    fw = framework.lower().strip()
    matches = _BY_FRAMEWORK.get(fw, [])

    results: list[dict[str, Any]] = []
    for pattern in matches:
        results.append(
            {
                "name": pattern["name"],
                "source": pattern["source"],
                "frameworks": sorted(pattern["frameworks"].keys()),
                "why": pattern["frameworks"][fw],
            }
        )

    # Rank by breadth of compliance coverage (most frameworks first)
    results.sort(key=lambda r: len(r["frameworks"]), reverse=True)
    return results
