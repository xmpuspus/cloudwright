"""ArchSpec compliance and best-practice validator."""

from __future__ import annotations

from silmaril.spec import ArchSpec, ValidationCheck, ValidationResult

# Services that qualify for BAA / regulated workloads per provider
_BAA_ELIGIBLE = {
    "aws": {
        "ec2",
        "ecs",
        "eks",
        "lambda",
        "fargate",
        "rds",
        "aurora",
        "dynamodb",
        "elasticache",
        "s3",
        "sqs",
        "sns",
        "cloudfront",
        "alb",
        "nlb",
        "waf",
        "cloudwatch",
        "cloudtrail",
        "cognito",
        "iam",
        "kms",
        "route53",
        "api_gateway",
        "redshift",
        "emr",
        "sagemaker",
    },
    "gcp": {
        "compute_engine",
        "gke",
        "cloud_run",
        "cloud_functions",
        "cloud_sql",
        "firestore",
        "spanner",
        "cloud_storage",
        "pub_sub",
        "bigquery",
        "cloud_load_balancing",
        "cloud_armor",
        "cloud_dns",
        "cloud_cdn",
        "firebase_auth",
        "vertex_ai",
        "memorystore",
        "cloud_logging",
    },
    "azure": {
        "virtual_machines",
        "aks",
        "container_apps",
        "azure_functions",
        "app_service",
        "azure_sql",
        "cosmos_db",
        "azure_cache",
        "blob_storage",
        "service_bus",
        "event_hubs",
        "app_gateway",
        "azure_waf",
        "azure_lb",
        "azure_ad",
        "azure_monitor",
        "synapse",
        "azure_ml",
        "azure_cdn",
        "azure_dns",
    },
}

_DATA_STORE_SERVICES = {
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
}

_STORAGE_SERVICES = {"s3", "cloud_storage", "blob_storage"}

_LOGGING_SERVICES = {
    "cloudwatch",
    "cloudtrail",
    "cloud_logging",
    "azure_monitor",
}

_AUTH_SERVICES = {
    "cognito",
    "iam",
    "firebase_auth",
    "azure_ad",
}

_WAF_SERVICES = {"waf", "cloud_armor", "azure_waf"}

_LB_SERVICES = {"alb", "nlb", "cloud_load_balancing", "app_gateway", "azure_lb"}

_COMPUTE_SERVICES = {
    "ec2",
    "ecs",
    "eks",
    "lambda",
    "fargate",
    "compute_engine",
    "gke",
    "cloud_run",
    "cloud_functions",
    "app_engine",
    "virtual_machines",
    "aks",
    "container_apps",
    "azure_functions",
    "app_service",
}

_CICD_SERVICES = {
    "codepipeline",
    "codebuild",
    "cloud_build",
    "azure_devops",
}


class Validator:
    def validate(
        self,
        spec: ArchSpec,
        compliance: list[str] | None = None,
        well_architected: bool = False,
    ) -> list[ValidationResult]:
        results = []
        frameworks = [f.upper() for f in (compliance or [])]

        if "HIPAA" in frameworks:
            results.append(_check_hipaa(spec))
        if "PCI-DSS" in frameworks or "PCI_DSS" in frameworks:
            results.append(_check_pci_dss(spec))
        if "SOC2" in frameworks or "SOC 2" in frameworks:
            results.append(_check_soc2(spec))
        if well_architected:
            results.append(_check_well_architected(spec))

        return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _services(spec: ArchSpec) -> set[str]:
    return {c.service for c in spec.components}


def _has_encryption_in_transit(spec: ArchSpec) -> bool:
    """True if all connections use HTTPS/TLS, or no connections exist."""
    if not spec.connections:
        return True
    insecure = {"HTTP", "http", "PLAIN", "plain", "FTP", "ftp"}
    for conn in spec.connections:
        proto = (conn.protocol or "").upper()
        if proto in insecure:
            return False
    return True


def _stores_encrypted(spec: ArchSpec) -> list[str]:
    """Return component IDs of data stores that lack encryption=true."""
    unencrypted = []
    for c in spec.components:
        if c.service in (_DATA_STORE_SERVICES | _STORAGE_SERVICES):
            if not c.config.get("encryption"):
                unencrypted.append(c.id)
    return unencrypted


def _score(checks: list[ValidationCheck]) -> float:
    if not checks:
        return 1.0
    return sum(1 for ch in checks if ch.passed) / len(checks)


# ---------------------------------------------------------------------------
# Frameworks
# ---------------------------------------------------------------------------


def _check_hipaa(spec: ArchSpec) -> ValidationResult:
    svcs = _services(spec)
    checks = []

    # encryption at rest
    unencrypted = _stores_encrypted(spec)
    checks.append(
        ValidationCheck(
            name="encryption_at_rest",
            category="data_protection",
            passed=len(unencrypted) == 0,
            severity="critical",
            detail=(
                "All data stores have encryption enabled"
                if not unencrypted
                else f"Missing encryption on: {', '.join(unencrypted)}"
            ),
            recommendation="Set encryption=true in config for all RDS, S3, DynamoDB, and cache components.",
        )
    )

    # encryption in transit
    in_transit = _has_encryption_in_transit(spec)
    checks.append(
        ValidationCheck(
            name="encryption_in_transit",
            category="data_protection",
            passed=in_transit,
            severity="critical",
            detail=(
                "All connections use encrypted protocols"
                if in_transit
                else "One or more connections use unencrypted protocols"
            ),
            recommendation="Use HTTPS or TLS for all connections. Avoid plain HTTP or FTP.",
        )
    )

    # audit logging
    has_logging = bool(svcs & _LOGGING_SERVICES)
    checks.append(
        ValidationCheck(
            name="audit_logging",
            category="monitoring",
            passed=has_logging,
            severity="high",
            detail=("Audit logging component present" if has_logging else "No logging/monitoring service found"),
            recommendation="Add CloudWatch + CloudTrail (AWS), Cloud Logging (GCP), or Azure Monitor.",
        )
    )

    # access control
    has_auth = bool(svcs & _AUTH_SERVICES)
    checks.append(
        ValidationCheck(
            name="access_control",
            category="identity",
            passed=has_auth,
            severity="high",
            detail=("IAM/auth component present" if has_auth else "No identity or access management service found"),
            recommendation="Add Cognito/IAM (AWS), Firebase Auth (GCP), or Azure AD.",
        )
    )

    # BAA eligibility
    provider_baa = _BAA_ELIGIBLE.get(spec.provider, set())
    non_baa = [c.id for c in spec.components if c.service not in provider_baa]
    checks.append(
        ValidationCheck(
            name="baa_eligible",
            category="compliance",
            passed=len(non_baa) == 0,
            severity="high",
            detail=(
                "All services are BAA-eligible"
                if not non_baa
                else f"Services not confirmed BAA-eligible: {', '.join(non_baa)}"
            ),
            recommendation="Replace non-BAA services or confirm BAA coverage with your provider.",
        )
    )

    passed = all(c.passed for c in checks if c.severity == "critical")
    return ValidationResult(
        framework="HIPAA",
        passed=passed,
        score=_score(checks),
        checks=checks,
    )


def _check_pci_dss(spec: ArchSpec) -> ValidationResult:
    svcs = _services(spec)
    checks = []

    # WAF
    has_waf = bool(svcs & _WAF_SERVICES)
    checks.append(
        ValidationCheck(
            name="waf_present",
            category="network_security",
            passed=has_waf,
            severity="high",
            detail="WAF component present" if has_waf else "No WAF service found",
            recommendation="Add WAF (AWS), Cloud Armor (GCP), or Azure WAF in front of public endpoints.",
        )
    )

    # Network segmentation (WAF or security group config on compute)
    segmented = has_waf or any(
        c.config.get("security_groups") or c.config.get("private_subnet")
        for c in spec.components
        if c.service in _COMPUTE_SERVICES
    )
    checks.append(
        ValidationCheck(
            name="network_segmentation",
            category="network_security",
            passed=segmented,
            severity="high",
            detail=(
                "Network segmentation controls present"
                if segmented
                else "No network segmentation (WAF or subnet isolation) detected"
            ),
            recommendation="Use private subnets, security groups, and WAF for cardholder data environment isolation.",
        )
    )

    # Encryption
    unencrypted = _stores_encrypted(spec)
    checks.append(
        ValidationCheck(
            name="encryption",
            category="data_protection",
            passed=len(unencrypted) == 0,
            severity="critical",
            detail=("Data stores encrypted" if not unencrypted else f"Unencrypted stores: {', '.join(unencrypted)}"),
            recommendation="Enable encryption at rest on all storage and database components.",
        )
    )

    in_transit = _has_encryption_in_transit(spec)
    checks.append(
        ValidationCheck(
            name="encryption_in_transit",
            category="data_protection",
            passed=in_transit,
            severity="critical",
            detail=("Connections use TLS/HTTPS" if in_transit else "Unencrypted connections present"),
            recommendation="Enforce TLS 1.2+ on all service connections.",
        )
    )

    # Logging
    has_logging = bool(svcs & _LOGGING_SERVICES)
    checks.append(
        ValidationCheck(
            name="logging",
            category="monitoring",
            passed=has_logging,
            severity="high",
            detail=("Audit trail component present" if has_logging else "No logging service found"),
            recommendation="Add CloudTrail (AWS), Cloud Logging (GCP), or Azure Monitor for PCI audit trail.",
        )
    )

    passed = all(c.passed for c in checks if c.severity == "critical")
    return ValidationResult(
        framework="PCI-DSS",
        passed=passed,
        score=_score(checks),
        checks=checks,
    )


def _check_soc2(spec: ArchSpec) -> ValidationResult:
    svcs = _services(spec)
    checks = []

    # Logging
    has_logging = bool(svcs & _LOGGING_SERVICES)
    checks.append(
        ValidationCheck(
            name="logging",
            category="monitoring",
            passed=has_logging,
            severity="high",
            detail="Logging component present" if has_logging else "No logging service found",
            recommendation="Add CloudWatch, Cloud Logging, or Azure Monitor.",
        )
    )

    # Access controls
    has_auth = bool(svcs & _AUTH_SERVICES)
    checks.append(
        ValidationCheck(
            name="access_controls",
            category="identity",
            passed=has_auth,
            severity="high",
            detail="Auth/IAM component present" if has_auth else "No auth service found",
            recommendation="Add IAM, Cognito, Firebase Auth, or Azure AD.",
        )
    )

    # Availability — multi-AZ or multi-region
    multi_az = any(c.config.get("multi_az") or c.config.get("multi_region") for c in spec.components)
    has_lb = bool(svcs & _LB_SERVICES)
    availability_ok = multi_az or has_lb
    checks.append(
        ValidationCheck(
            name="availability",
            category="reliability",
            passed=availability_ok,
            severity="medium",
            detail=(
                "High-availability configuration detected"
                if availability_ok
                else "No multi-AZ or load balancer found — single point of failure risk"
            ),
            recommendation="Enable multi_az on databases, use a load balancer, and configure auto-scaling.",
        )
    )

    # Change management
    has_cicd = bool(svcs & _CICD_SERVICES)
    checks.append(
        ValidationCheck(
            name="change_management",
            category="operations",
            passed=has_cicd,
            severity="low",
            detail="CI/CD component present" if has_cicd else "No CI/CD service detected",
            recommendation="Add CodePipeline (AWS), Cloud Build (GCP), or Azure DevOps for change management.",
        )
    )

    passed = all(c.passed for c in checks if c.severity == "high")
    return ValidationResult(
        framework="SOC 2",
        passed=passed,
        score=_score(checks),
        checks=checks,
    )


def _check_well_architected(spec: ArchSpec) -> ValidationResult:
    svcs = _services(spec)
    checks = []

    # Multi-AZ
    has_multi_az = any(c.config.get("multi_az") for c in spec.components)
    checks.append(
        ValidationCheck(
            name="multi_az",
            category="reliability",
            passed=has_multi_az,
            severity="high",
            detail=(
                "Multi-AZ enabled on one or more components" if has_multi_az else "No multi-AZ configuration found"
            ),
            recommendation="Enable multi_az=true on RDS, caches, and other stateful components.",
        )
    )

    # Auto-scaling
    has_auto_scale = any(c.config.get("auto_scaling") for c in spec.components if c.service in _COMPUTE_SERVICES)
    checks.append(
        ValidationCheck(
            name="auto_scaling",
            category="reliability",
            passed=has_auto_scale,
            severity="medium",
            detail=(
                "Auto-scaling configured on compute" if has_auto_scale else "No auto-scaling on compute components"
            ),
            recommendation="Set auto_scaling=true on EC2/ECS/GKE/AKS components.",
        )
    )

    # Backup
    has_backup = any(c.config.get("backup") for c in spec.components if c.service in _DATA_STORE_SERVICES)
    checks.append(
        ValidationCheck(
            name="backup",
            category="reliability",
            passed=has_backup,
            severity="medium",
            detail=("Backup configured on data stores" if has_backup else "No backup configuration on data stores"),
            recommendation="Enable automated backups on RDS, DynamoDB, Cloud SQL, and Cosmos DB.",
        )
    )

    # Monitoring
    has_monitoring = bool(svcs & _LOGGING_SERVICES)
    checks.append(
        ValidationCheck(
            name="monitoring",
            category="operations",
            passed=has_monitoring,
            severity="high",
            detail=("Monitoring/logging component present" if has_monitoring else "No monitoring service detected"),
            recommendation="Add CloudWatch, Cloud Logging, or Azure Monitor.",
        )
    )

    # No single point of failure: LB in front of compute + replicated DB
    has_lb = bool(svcs & _LB_SERVICES)
    has_replicated_db = any(
        c.config.get("multi_az") or c.config.get("replicas", 0) > 1
        for c in spec.components
        if c.service in _DATA_STORE_SERVICES
    )
    no_spof = has_lb and (has_replicated_db or not bool(svcs & _DATA_STORE_SERVICES))
    checks.append(
        ValidationCheck(
            name="no_single_point_of_failure",
            category="reliability",
            passed=no_spof,
            severity="high",
            detail=(
                "Load balancer and replicated DB present"
                if no_spof
                else "Single point of failure detected (no LB or unreplicated DB)"
            ),
            recommendation="Place a load balancer in front of compute and enable multi-AZ or read replicas on databases.",
        )
    )

    # Cost optimization — flag oversized instances
    oversized = [
        c.id
        for c in spec.components
        if any(tier in c.config.get("instance_type", "") for tier in ["32xlarge", "24xlarge", "16xlarge"])
    ]
    checks.append(
        ValidationCheck(
            name="cost_optimization",
            category="cost",
            passed=len(oversized) == 0,
            severity="low",
            detail=(
                "No obviously oversized instances detected"
                if not oversized
                else f"Potentially oversized instances: {', '.join(oversized)}"
            ),
            recommendation="Right-size instances based on actual workload metrics. Use Savings Plans or Reserved Instances.",
        )
    )

    # Security
    has_waf = bool(svcs & _WAF_SERVICES)
    has_auth = bool(svcs & _AUTH_SERVICES)
    unencrypted = _stores_encrypted(spec)
    security_ok = has_waf and has_auth and len(unencrypted) == 0
    checks.append(
        ValidationCheck(
            name="security",
            category="security",
            passed=security_ok,
            severity="high",
            detail=(
                "WAF, auth, and encryption all present"
                if security_ok
                else "Missing: "
                + ", ".join(
                    filter(
                        None,
                        [
                            "WAF" if not has_waf else None,
                            "auth/IAM" if not has_auth else None,
                            f"encryption on {', '.join(unencrypted)}" if unencrypted else None,
                        ],
                    )
                )
            ),
            recommendation="Add WAF, IAM/auth service, and enable encryption on all data stores.",
        )
    )

    passed = all(c.passed for c in checks if c.severity == "high")
    return ValidationResult(
        framework="Well-Architected",
        passed=passed,
        score=_score(checks),
        checks=checks,
    )
