from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_DATA_SERVICES = {
    "rds",
    "aurora",
    "dynamodb",
    "elasticache",
    "cloud_sql",
    "cosmos_db",
    "azure_cache",
    "blob_storage",
    "cloud_storage",
    "databricks_volume",
}

_STORAGE_SERVICES = {"s3"}

_DB_SERVICES = {"rds", "aurora", "cloud_sql", "sql_database"}

_MONITORING_SERVICES = {"cloudwatch", "stackdriver", "azure_monitor", "datadog"}

_LB_CDN_SERVICES = {"alb", "nlb", "cloudfront", "api_gateway", "cloud_load_balancing", "app_gateway", "azure_cdn"}


@dataclass
class SecurityFinding:
    severity: str
    rule: str
    component_id: str | None
    message: str
    remediation: str


@dataclass
class SecurityReport:
    passed: bool
    findings: list[SecurityFinding] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")


class SecurityScanner:
    def scan(self, spec: ArchSpec) -> SecurityReport:
        findings: list[SecurityFinding] = []

        for c in spec.components:
            findings.extend(self._check_open_access(c))
            if c.service in (_DATA_SERVICES | _STORAGE_SERVICES):
                findings.extend(self._check_encryption(c))
                findings.extend(self._check_backup(c))
            if c.service in _DB_SERVICES:
                findings.extend(self._check_multi_az(c))
            findings.extend(self._check_iam_wildcard(c))
            if c.service in _LB_CDN_SERVICES:
                findings.extend(self._check_https(c))
            findings.extend(self._check_permissive_role(c))

        findings.extend(self._check_monitoring(spec))

        passed = all(f.severity not in ("critical", "high") for f in findings)
        return SecurityReport(passed=passed, findings=findings)

    def _check_open_access(self, c) -> list[SecurityFinding]:
        if c.config.get("ingress_open") or c.config.get("allow_public"):
            return [
                SecurityFinding(
                    severity="high",
                    rule="open_ingress",
                    component_id=c.id,
                    message=f"{c.id}: Unrestricted public ingress allowed",
                    remediation="Remove ingress_open/allow_public and restrict to known CIDR ranges",
                )
            ]
        return []

    def _check_encryption(self, c) -> list[SecurityFinding]:
        if not c.config.get("encryption"):
            return [
                SecurityFinding(
                    severity="high",
                    rule="missing_encryption",
                    component_id=c.id,
                    message=f"{c.id}: Missing encryption at rest",
                    remediation="Set encryption=true in component config",
                )
            ]
        return []

    def _check_backup(self, c) -> list[SecurityFinding]:
        if not c.config.get("backup"):
            return [
                SecurityFinding(
                    severity="medium",
                    rule="missing_backup",
                    component_id=c.id,
                    message=f"{c.id}: No backup configuration",
                    remediation="Set backup=true to enable automated backups",
                )
            ]
        return []

    def _check_multi_az(self, c) -> list[SecurityFinding]:
        if not c.config.get("multi_az"):
            return [
                SecurityFinding(
                    severity="medium",
                    rule="no_multi_az",
                    component_id=c.id,
                    message=f"{c.id}: Database not configured for multi-AZ",
                    remediation="Set multi_az=true for production database resilience",
                )
            ]
        return []

    def _check_iam_wildcard(self, c) -> list[SecurityFinding]:
        policy = c.config.get("iam_policy", "")
        if policy and "*" in str(policy):
            return [
                SecurityFinding(
                    severity="high",
                    rule="iam_wildcard",
                    component_id=c.id,
                    message=f"{c.id}: IAM policy contains wildcard action",
                    remediation="Replace '*' with specific action strings (principle of least privilege)",
                )
            ]
        return []

    def _check_https(self, c) -> list[SecurityFinding]:
        if c.config.get("https") is False:
            return [
                SecurityFinding(
                    severity="high",
                    rule="no_https",
                    component_id=c.id,
                    message=f"{c.id}: HTTPS not enabled on load balancer / CDN",
                    remediation="Set https=true and configure an SSL/TLS certificate",
                )
            ]
        return []

    def _check_permissive_role(self, c) -> list[SecurityFinding]:
        if c.config.get("service_account") == "default" or c.config.get("iam_role") == "admin":
            return [
                SecurityFinding(
                    severity="medium",
                    rule="overly_permissive_role",
                    component_id=c.id,
                    message=f"{c.id}: Overly permissive service account or IAM role",
                    remediation="Create a dedicated service account with minimum required permissions",
                )
            ]
        return []

    def _check_monitoring(self, spec: ArchSpec) -> list[SecurityFinding]:
        if len(spec.components) < 4:
            return []
        has_monitoring = any(c.service in _MONITORING_SERVICES for c in spec.components)
        if not has_monitoring:
            return [
                SecurityFinding(
                    severity="medium",
                    rule="missing_monitoring",
                    component_id=None,
                    message="No monitoring service detected in architecture",
                    remediation="Add CloudWatch, Azure Monitor, Datadog, or equivalent",
                )
            ]
        return []


def scan_terraform(hcl: str) -> SecurityReport:
    findings: list[SecurityFinding] = []

    if re.search(r'cidr_blocks\s*=\s*\["0\.0\.0\.0/0"\]', hcl):
        findings.append(
            SecurityFinding(
                severity="high",
                rule="open_security_group",
                component_id=None,
                message="Security group allows traffic from 0.0.0.0/0",
                remediation="Restrict cidr_blocks to known IP ranges",
            )
        )

    if re.search(r'[Aa]ctions?\s*=\s*"\*"', hcl) or re.search(r'[Aa]ctions?\s*=\s*\["\*"\]', hcl):
        findings.append(
            SecurityFinding(
                severity="high",
                rule="iam_wildcard",
                component_id=None,
                message="IAM policy uses wildcard action '*'",
                remediation="Replace '*' with specific IAM actions",
            )
        )

    if re.search(r"encrypted\s*=\s*false", hcl):
        findings.append(
            SecurityFinding(
                severity="medium",
                rule="missing_encryption",
                component_id=None,
                message="Resource has encryption explicitly disabled",
                remediation="Set encrypted = true on all storage and database resources",
            )
        )

    if re.search(r"publicly_accessible\s*=\s*true", hcl):
        findings.append(
            SecurityFinding(
                severity="critical",
                rule="public_database",
                component_id=None,
                message="Database is publicly accessible from the internet",
                remediation="Set publicly_accessible = false and use VPC private subnets",
            )
        )

    passed = all(f.severity not in ("critical", "high") for f in findings)
    return SecurityReport(passed=passed, findings=findings)
