"""Architecture anti-pattern linter."""

from __future__ import annotations

from dataclasses import dataclass

from cloudwright.spec import ArchSpec

_DATA_STORE_KEYWORDS = ("rds", "dynamodb", "s3", "elasticache", "redshift", "aurora", "cosmos", "cloud_sql", "storage")
_COMPUTE_KEYWORDS = ("ec2", "ecs", "eks", "compute", "vm", "app_service", "cloud_run")
_LB_KEYWORDS = ("alb", "nlb", "load_balancer", "elb", "app_gateway")
_DB_KEYWORDS = ("rds", "dynamodb", "elasticache", "redshift", "aurora", "cosmos", "cloud_sql")
_MONITORING_KEYWORDS = ("monitoring", "cloudwatch", "logging", "stackdriver", "azure_monitor", "datadog", "newrelic")
_WAF_KEYWORDS = ("waf", "shield")
_AUTH_KEYWORDS = ("cognito", "auth", "iam", "azure_ad", "identity", "okta")
_API_GATEWAY_KEYWORDS = ("api_gateway", "apigw", "api-gateway")
_OVERSIZED_KEYWORDS = ("16xlarge", "24xlarge", "metal")


@dataclass
class LintWarning:
    rule: str
    severity: str  # "error", "warning", "info"
    component: str | None
    message: str
    recommendation: str


def _is_data_store(service: str) -> bool:
    s = service.lower()
    return any(k in s for k in _DATA_STORE_KEYWORDS)


def _is_db(service: str) -> bool:
    s = service.lower()
    return any(k in s for k in _DB_KEYWORDS)


def _is_compute(service: str) -> bool:
    s = service.lower()
    return any(k in s for k in _COMPUTE_KEYWORDS)


def _is_lb(service: str) -> bool:
    s = service.lower()
    return any(k in s for k in _LB_KEYWORDS)


def _is_waf(service: str) -> bool:
    s = service.lower()
    return any(k in s for k in _WAF_KEYWORDS)


def _is_monitoring(service: str) -> bool:
    s = service.lower()
    return any(k in s for k in _MONITORING_KEYWORDS)


def _is_auth(service: str) -> bool:
    s = service.lower()
    return any(k in s for k in _AUTH_KEYWORDS)


def _is_api_gateway_or_lb(service: str) -> bool:
    s = service.lower()
    return _is_lb(s) or any(k in s for k in _API_GATEWAY_KEYWORDS)


def lint(spec: ArchSpec) -> list[LintWarning]:
    warnings: list[LintWarning] = []
    warnings.extend(_check_no_encryption(spec))
    warnings.extend(_check_single_az(spec))
    warnings.extend(_check_oversized_instances(spec))
    warnings.extend(_check_no_load_balancer(spec))
    warnings.extend(_check_public_database(spec))
    warnings.extend(_check_no_waf(spec))
    warnings.extend(_check_no_monitoring(spec))
    warnings.extend(_check_single_point_of_failure(spec))
    warnings.extend(_check_no_backup(spec))
    warnings.extend(_check_no_auth(spec))
    return warnings


def _check_no_encryption(spec: ArchSpec) -> list[LintWarning]:
    out = []
    for c in spec.components:
        if _is_data_store(c.service) and not c.config.get("encryption"):
            out.append(
                LintWarning(
                    rule="no_encryption",
                    severity="error",
                    component=c.id,
                    message=f"{c.label} ({c.service}) has no encryption configured",
                    recommendation="Set encryption: true in the component config",
                )
            )
    return out


def _check_single_az(spec: ArchSpec) -> list[LintWarning]:
    if len(spec.components) < 3:
        return []
    out = []
    for c in spec.components:
        if _is_db(c.service) and not c.config.get("multi_az"):
            out.append(
                LintWarning(
                    rule="single_az",
                    severity="error",
                    component=c.id,
                    message=f"{c.label} ({c.service}) is not configured for multi-AZ",
                    recommendation="Enable multi_az: true to prevent a single availability zone failure from causing downtime",
                )
            )
    return out


def _check_oversized_instances(spec: ArchSpec) -> list[LintWarning]:
    out = []
    for c in spec.components:
        instance_type = c.config.get("instance_type", "") or c.config.get("instance_class", "")
        if any(k in str(instance_type).lower() for k in _OVERSIZED_KEYWORDS):
            out.append(
                LintWarning(
                    rule="oversized_instances",
                    severity="warning",
                    component=c.id,
                    message=f"{c.label} uses oversized instance type '{instance_type}'",
                    recommendation="Validate that this instance size is justified by workload requirements; consider right-sizing",
                )
            )
    return out


def _check_no_load_balancer(spec: ArchSpec) -> list[LintWarning]:
    compute = [c for c in spec.components if _is_compute(c.service)]
    if len(compute) < 2:
        return []
    has_lb = any(_is_lb(c.service) for c in spec.components)
    if has_lb:
        return []
    return [
        LintWarning(
            rule="no_load_balancer",
            severity="error",
            component=None,
            message=f"Architecture has {len(compute)} compute components but no load balancer",
            recommendation="Add a load balancer (ALB/NLB) to distribute traffic across compute instances",
        )
    ]


def _check_public_database(spec: ArchSpec) -> list[LintWarning]:
    out = []
    for c in spec.components:
        if _is_db(c.service) and c.config.get("publicly_accessible"):
            out.append(
                LintWarning(
                    rule="public_database",
                    severity="error",
                    component=c.id,
                    message=f"{c.label} ({c.service}) is publicly accessible",
                    recommendation="Set publicly_accessible: false and restrict access via VPC security groups",
                )
            )
    return out


def _check_no_waf(spec: ArchSpec) -> list[LintWarning]:
    has_ingress = any(_is_api_gateway_or_lb(c.service) for c in spec.components)
    if not has_ingress:
        return []
    has_waf = any(_is_waf(c.service) for c in spec.components)
    if has_waf:
        return []
    return [
        LintWarning(
            rule="no_waf",
            severity="warning",
            component=None,
            message="Load balancer or API gateway present but no WAF/Shield configured",
            recommendation="Add a WAF to protect against common web exploits and DDoS attacks",
        )
    ]


def _check_no_monitoring(spec: ArchSpec) -> list[LintWarning]:
    if len(spec.components) < 3:
        return []
    has_monitoring = any(_is_monitoring(c.service) for c in spec.components)
    if has_monitoring:
        return []
    return [
        LintWarning(
            rule="no_monitoring",
            severity="warning",
            component=None,
            message=f"Architecture has {len(spec.components)} components but no monitoring or logging service",
            recommendation="Add a monitoring service (CloudWatch, Datadog, etc.) to observe system health",
        )
    ]


def _check_single_point_of_failure(spec: ArchSpec) -> list[LintWarning]:
    compute = [c for c in spec.components if _is_compute(c.service)]
    if len(compute) != 1:
        return []
    c = compute[0]
    if c.config.get("auto_scaling"):
        return []
    return [
        LintWarning(
            rule="single_point_of_failure",
            severity="error",
            component=c.id,
            message=f"{c.label} is the sole compute component with no auto-scaling configured",
            recommendation="Enable auto_scaling or add a second compute component behind a load balancer",
        )
    ]


def _check_no_backup(spec: ArchSpec) -> list[LintWarning]:
    out = []
    for c in spec.components:
        if _is_db(c.service):
            has_backup = c.config.get("backup") or c.config.get("point_in_time_recovery")
            if not has_backup:
                out.append(
                    LintWarning(
                        rule="no_backup",
                        severity="warning",
                        component=c.id,
                        message=f"{c.label} ({c.service}) has no backup or point-in-time recovery configured",
                        recommendation="Enable backup: true or point_in_time_recovery: true to protect against data loss",
                    )
                )
    return out


def _check_no_auth(spec: ArchSpec) -> list[LintWarning]:
    has_ingress = any(_is_api_gateway_or_lb(c.service) for c in spec.components)
    if not has_ingress:
        return []
    has_auth = any(_is_auth(c.service) for c in spec.components)
    if has_auth:
        return []
    return [
        LintWarning(
            rule="no_auth",
            severity="warning",
            component=None,
            message="API gateway or load balancer present but no authentication service configured",
            recommendation="Add an auth service (Cognito, Azure AD, IAM) to secure public-facing endpoints",
        )
    ]
