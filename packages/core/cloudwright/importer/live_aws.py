"""Live AWS importer — walks boto3 describe-* calls and produces an ArchSpec.

Use via the CLI: ``cloudwright import-live --provider aws --region us-east-1``.

Requires the optional ``boto3`` dependency:
``pip install 'cloudwright-ai[live-import]'``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Any

from cloudwright.spec import ArchSpec, Boundary, Component, Connection

# Maximum results pulled per service to keep walks bounded on huge accounts.
_MAX_PER_SERVICE = 1000

# Canonical tier (matches cloudwright.importer.terraform_state._TIER values).
_TIER = {
    "ec2": 2,
    "lambda": 2,
    "ecs": 2,
    "eks": 2,
    "rds": 3,
    "dynamodb": 3,
    "elasticache": 3,
    "sqs": 3,
    "s3": 4,
    "alb": 1,
    "nlb": 1,
    "cloudfront": 0,
    "api_gateway": 1,
    "cloudtrail": 2,
}

# Service ordering — most-common-deployed first. The CLI scans in this order.
SUPPORTED_SERVICES: tuple[str, ...] = (
    "ec2",
    "vpc",
    "rds",
    "s3",
    "lambda",
    "ecs",
    "eks",
    "dynamodb",
    "alb",
    "cloudfront",
    "sqs",
    "api_gateway",
    "cloudtrail",
)


class LiveImportError(Exception):
    """Raised when the importer cannot complete (e.g. missing credentials)."""


def _safe_id(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name).strip("_")
    if not safe or not (safe[0].isalpha() or safe[0] == "_"):
        safe = "svc_" + safe
    return safe[:64]


def _unique_id(base: str, used: set[str]) -> str:
    candidate = _safe_id(base)
    if candidate not in used:
        used.add(candidate)
        return candidate
    n = 2
    while f"{candidate}_{n}" in used:
        n += 1
    final = f"{candidate}_{n}"
    used.add(final)
    return final


def _component(
    *,
    comp_id: str,
    service: str,
    label: str,
    config: dict[str, Any],
) -> Component:
    return Component(
        id=comp_id,
        service=service,
        provider="aws",
        label=label,
        tier=_TIER.get(service, 2),
        config={k: v for k, v in config.items() if v is not None},
    )


def _is_access_denied(exc: Exception) -> bool:
    """Detect AWS access-denied errors regardless of which boto3 exception class."""
    name = type(exc).__name__
    if name in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
        return True
    code = getattr(getattr(exc, "response", None), "get", lambda *_: {})("Error", {}) or {}
    err_code = code.get("Code", "") if isinstance(code, dict) else ""
    if err_code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "AuthFailure"}:
        return True
    msg = str(exc).lower()
    return "accessdenied" in msg or "not authorized" in msg or "unauthorizedoperation" in msg


# Per-service scanners
#
# Each scanner takes a boto3.Session, the running list of components/boundaries/
# connections, and the set of used IDs. It mutates those lists. Each scanner
# guards its own access-denied / API exceptions and returns a count for the
# progress message.


def _scan_ec2(session, components, boundaries, used_ids, log):
    client = session.client("ec2")
    count = 0
    paginator = client.get_paginator("describe_instances")
    for page in paginator.paginate(PaginationConfig={"MaxItems": _MAX_PER_SERVICE}):
        for reservation in page.get("Reservations", []) or []:
            for inst in reservation.get("Instances", []) or []:
                state = (inst.get("State") or {}).get("Name")
                if state in {"terminated", "shutting-down"}:
                    continue
                instance_id = inst.get("InstanceId", "")
                comp_id = _unique_id(f"ec2_{instance_id}", used_ids)
                config = {
                    "instance_type": inst.get("InstanceType"),
                    "count": 1,
                    "vpc_id": inst.get("VpcId"),
                    "subnet_id": inst.get("SubnetId"),
                    "az": (inst.get("Placement") or {}).get("AvailabilityZone"),
                }
                # Surface IMDSv2 posture so downstream scoring can use it.
                metadata_options = inst.get("MetadataOptions") or {}
                if metadata_options.get("HttpTokens"):
                    config["http_tokens"] = metadata_options["HttpTokens"]
                components.append(
                    _component(
                        comp_id=comp_id,
                        service="ec2",
                        label=f"EC2 {instance_id}",
                        config=config,
                    )
                )
                count += 1
                if count >= _MAX_PER_SERVICE:
                    return count
    return count


def _scan_vpc(session, components, boundaries, used_ids, log):
    client = session.client("ec2")
    count = 0

    vpcs = client.describe_vpcs().get("Vpcs", []) or []
    for vpc in vpcs[:_MAX_PER_SERVICE]:
        vpc_id = vpc.get("VpcId", "")
        b_id = _unique_id(f"vpc_{vpc_id}", used_ids)
        boundaries.append(
            Boundary(
                id=b_id,
                kind="vpc",
                label=f"VPC {vpc_id}",
                config={
                    "cidr_block": vpc.get("CidrBlock"),
                    "is_default": vpc.get("IsDefault", False),
                },
            )
        )
        count += 1

    subnets = client.describe_subnets().get("Subnets", []) or []
    for subnet in subnets[:_MAX_PER_SERVICE]:
        subnet_id = subnet.get("SubnetId", "")
        b_id = _unique_id(f"subnet_{subnet_id}", used_ids)
        boundaries.append(
            Boundary(
                id=b_id,
                kind="subnet",
                label=f"Subnet {subnet_id}",
                config={
                    "cidr_block": subnet.get("CidrBlock"),
                    "az": subnet.get("AvailabilityZone"),
                    "vpc_id": subnet.get("VpcId"),
                    "public": subnet.get("MapPublicIpOnLaunch", False),
                },
            )
        )
        count += 1

    sgs = client.describe_security_groups().get("SecurityGroups", []) or []
    for sg in sgs[:_MAX_PER_SERVICE]:
        sg_id = sg.get("GroupId", "")
        b_id = _unique_id(f"sg_{sg_id}", used_ids)
        # Capture wide-open ingress for downstream linters.
        wide_open = False
        for rule in sg.get("IpPermissions", []) or []:
            for ip_range in rule.get("IpRanges", []) or []:
                if ip_range.get("CidrIp") == "0.0.0.0/0":
                    wide_open = True
                    break
        boundaries.append(
            Boundary(
                id=b_id,
                kind="security_group",
                label=sg.get("GroupName") or f"SG {sg_id}",
                config={
                    "vpc_id": sg.get("VpcId"),
                    "ingress_open_internet": wide_open,
                },
            )
        )
        count += 1

    return count


def _scan_rds(session, components, boundaries, used_ids, log):
    client = session.client("rds")
    count = 0
    paginator = client.get_paginator("describe_db_instances")
    for page in paginator.paginate(PaginationConfig={"MaxItems": _MAX_PER_SERVICE}):
        for db in page.get("DBInstances", []) or []:
            db_id = db.get("DBInstanceIdentifier", "")
            comp_id = _unique_id(f"rds_{db_id}", used_ids)
            config = {
                "engine": db.get("Engine"),
                "engine_version": db.get("EngineVersion"),
                "instance_class": db.get("DBInstanceClass"),
                "multi_az": db.get("MultiAZ", False),
                "storage_encrypted": db.get("StorageEncrypted", False),
                "backup_retention_period": db.get("BackupRetentionPeriod", 0),
                "publicly_accessible": db.get("PubliclyAccessible", False),
            }
            components.append(
                _component(
                    comp_id=comp_id,
                    service="rds",
                    label=f"RDS {db_id}",
                    config=config,
                )
            )
            count += 1
            if count >= _MAX_PER_SERVICE:
                return count
    return count


def _scan_s3(session, components, boundaries, used_ids, log):
    client = session.client("s3")
    buckets = client.list_buckets().get("Buckets", []) or []
    count = 0
    for bucket in buckets[:_MAX_PER_SERVICE]:
        name = bucket.get("Name", "")
        comp_id = _unique_id(f"s3_{name}", used_ids)

        encryption = False
        try:
            enc = client.get_bucket_encryption(Bucket=name)
            rules = (enc.get("ServerSideEncryptionConfiguration") or {}).get("Rules", [])
            encryption = bool(rules)
        except Exception as exc:  # noqa: BLE001 — encryption call may legitimately 404
            # ServerSideEncryptionConfigurationNotFoundError -> means none configured
            err = getattr(getattr(exc, "response", None), "get", lambda *_: {})("Error", {}) or {}
            if isinstance(err, dict) and err.get("Code") == "ServerSideEncryptionConfigurationNotFoundError":
                encryption = False
            else:
                log(f"  warn: get_bucket_encryption({name}) failed: {exc}")

        versioning = False
        try:
            ver = client.get_bucket_versioning(Bucket=name)
            versioning = ver.get("Status") == "Enabled"
        except Exception as exc:  # noqa: BLE001
            log(f"  warn: get_bucket_versioning({name}) failed: {exc}")

        public_block = None
        try:
            pab = client.get_public_access_block(Bucket=name)
            cfg = pab.get("PublicAccessBlockConfiguration") or {}
            public_block = all(
                bool(cfg.get(k))
                for k in ("BlockPublicAcls", "BlockPublicPolicy", "IgnorePublicAcls", "RestrictPublicBuckets")
            )
        except Exception as exc:  # noqa: BLE001
            err = getattr(getattr(exc, "response", None), "get", lambda *_: {})("Error", {}) or {}
            if isinstance(err, dict) and err.get("Code") == "NoSuchPublicAccessBlockConfiguration":
                public_block = False
            else:
                log(f"  warn: get_public_access_block({name}) failed: {exc}")

        components.append(
            _component(
                comp_id=comp_id,
                service="s3",
                label=f"S3 {name}",
                config={
                    "bucket": name,
                    "encryption": encryption,
                    "versioning": versioning,
                    "public_access_block": public_block,
                },
            )
        )
        count += 1
    return count


def _scan_lambda(session, components, boundaries, used_ids, log):
    client = session.client("lambda")
    count = 0
    paginator = client.get_paginator("list_functions")
    for page in paginator.paginate(PaginationConfig={"MaxItems": _MAX_PER_SERVICE}):
        for fn in page.get("Functions", []) or []:
            name = fn.get("FunctionName", "")
            comp_id = _unique_id(f"lambda_{name}", used_ids)
            config = {
                "runtime": fn.get("Runtime"),
                "memory_mb": fn.get("MemorySize"),
                "timeout_s": fn.get("Timeout"),
                "role": fn.get("Role"),
                "function_name": name,
            }
            components.append(
                _component(
                    comp_id=comp_id,
                    service="lambda",
                    label=f"Lambda {name}",
                    config=config,
                )
            )
            count += 1
            if count >= _MAX_PER_SERVICE:
                return count
    return count


def _scan_ecs(session, components, boundaries, used_ids, log):
    client = session.client("ecs")
    cluster_arns: list[str] = []
    paginator = client.get_paginator("list_clusters")
    for page in paginator.paginate(PaginationConfig={"MaxItems": _MAX_PER_SERVICE}):
        cluster_arns.extend(page.get("clusterArns", []) or [])

    if not cluster_arns:
        return 0

    described = client.describe_clusters(clusters=cluster_arns[:_MAX_PER_SERVICE]).get("clusters", []) or []
    count = 0
    for cluster in described:
        name = cluster.get("clusterName", "")
        comp_id = _unique_id(f"ecs_{name}", used_ids)
        config = {
            "cluster_name": name,
            "running_tasks": cluster.get("runningTasksCount", 0),
            "active_services": cluster.get("activeServicesCount", 0),
            "registered_instances": cluster.get("registeredContainerInstancesCount", 0),
        }
        components.append(
            _component(
                comp_id=comp_id,
                service="ecs",
                label=f"ECS {name}",
                config=config,
            )
        )
        count += 1
    return count


def _scan_eks(session, components, boundaries, used_ids, log):
    client = session.client("eks")
    names: list[str] = []
    paginator = client.get_paginator("list_clusters")
    for page in paginator.paginate(PaginationConfig={"MaxItems": _MAX_PER_SERVICE}):
        names.extend(page.get("clusters", []) or [])

    count = 0
    for name in names[:_MAX_PER_SERVICE]:
        try:
            described = client.describe_cluster(name=name).get("cluster", {}) or {}
        except Exception as exc:  # noqa: BLE001
            log(f"  warn: describe_cluster({name}) failed: {exc}")
            described = {}
        comp_id = _unique_id(f"eks_{name}", used_ids)
        config = {
            "cluster_name": name,
            "version": described.get("version"),
            "status": described.get("status"),
            "endpoint_public_access": (described.get("resourcesVpcConfig") or {}).get("endpointPublicAccess"),
        }
        components.append(
            _component(
                comp_id=comp_id,
                service="eks",
                label=f"EKS {name}",
                config=config,
            )
        )
        count += 1
    return count


def _scan_dynamodb(session, components, boundaries, used_ids, log):
    client = session.client("dynamodb")
    names: list[str] = []
    paginator = client.get_paginator("list_tables")
    for page in paginator.paginate(PaginationConfig={"MaxItems": _MAX_PER_SERVICE}):
        names.extend(page.get("TableNames", []) or [])

    count = 0
    for name in names[:_MAX_PER_SERVICE]:
        try:
            described = client.describe_table(TableName=name).get("Table", {}) or {}
        except Exception as exc:  # noqa: BLE001
            log(f"  warn: describe_table({name}) failed: {exc}")
            described = {}
        pitr = False
        try:
            pitr_desc = client.describe_continuous_backups(TableName=name).get("ContinuousBackupsDescription", {}) or {}
            pitr = (pitr_desc.get("PointInTimeRecoveryDescription") or {}).get("PointInTimeRecoveryStatus") == "ENABLED"
        except Exception as exc:  # noqa: BLE001
            log(f"  warn: describe_continuous_backups({name}) failed: {exc}")
        comp_id = _unique_id(f"dynamodb_{name}", used_ids)
        config = {
            "table_name": name,
            "billing_mode": (described.get("BillingModeSummary") or {}).get("BillingMode")
            or ("PAY_PER_REQUEST" if not described.get("ProvisionedThroughput") else "PROVISIONED"),
            "point_in_time_recovery": pitr,
            "item_count": described.get("ItemCount"),
        }
        components.append(
            _component(
                comp_id=comp_id,
                service="dynamodb",
                label=f"DynamoDB {name}",
                config=config,
            )
        )
        count += 1
    return count


def _scan_alb(session, components, boundaries, used_ids, log):
    """Both ALB and NLB are returned by elbv2 describe_load_balancers."""
    client = session.client("elbv2")
    count = 0
    paginator = client.get_paginator("describe_load_balancers")
    for page in paginator.paginate(PaginationConfig={"MaxItems": _MAX_PER_SERVICE}):
        for lb in page.get("LoadBalancers", []) or []:
            name = lb.get("LoadBalancerName", "")
            lb_type = lb.get("Type", "application")  # application | network | gateway
            service = "alb" if lb_type == "application" else "nlb"
            comp_id = _unique_id(f"{service}_{name}", used_ids)
            config = {
                "lb_name": name,
                "scheme": lb.get("Scheme"),
                "type": lb_type,
                "vpc_id": lb.get("VpcId"),
                "lb_arn": lb.get("LoadBalancerArn"),
            }
            components.append(
                _component(
                    comp_id=comp_id,
                    service=service,
                    label=f"{service.upper()} {name}",
                    config=config,
                )
            )
            count += 1
            if count >= _MAX_PER_SERVICE:
                return count
    return count


def _scan_cloudfront(session, components, boundaries, used_ids, log):
    client = session.client("cloudfront")
    count = 0
    paginator = client.get_paginator("list_distributions")
    for page in paginator.paginate():
        dl = page.get("DistributionList") or {}
        for dist in dl.get("Items", []) or []:
            dist_id = dist.get("Id", "")
            comp_id = _unique_id(f"cloudfront_{dist_id}", used_ids)
            origins = (dist.get("Origins") or {}).get("Items", []) or []
            origin_domains = [o.get("DomainName") for o in origins if o.get("DomainName")]
            viewer_cert = dist.get("ViewerCertificate") or {}
            config = {
                "distribution_id": dist_id,
                "domain_name": dist.get("DomainName"),
                "enabled": dist.get("Enabled"),
                "origin_domains": origin_domains,
                "minimum_protocol_version": viewer_cert.get("MinimumProtocolVersion"),
            }
            components.append(
                _component(
                    comp_id=comp_id,
                    service="cloudfront",
                    label=f"CloudFront {dist_id}",
                    config=config,
                )
            )
            count += 1
            if count >= _MAX_PER_SERVICE:
                return count
    return count


def _scan_sqs(session, components, boundaries, used_ids, log):
    client = session.client("sqs")
    queue_urls: list[str] = []
    paginator = client.get_paginator("list_queues")
    for page in paginator.paginate(PaginationConfig={"MaxItems": _MAX_PER_SERVICE}):
        queue_urls.extend(page.get("QueueUrls", []) or [])

    count = 0
    for url in queue_urls[:_MAX_PER_SERVICE]:
        # Queue name is the last URL segment.
        name = url.rsplit("/", 1)[-1]
        attrs: dict[str, Any] = {}
        try:
            attrs = (
                client.get_queue_attributes(
                    QueueUrl=url,
                    AttributeNames=["KmsMasterKeyId", "SqsManagedSseEnabled", "FifoQueue"],
                ).get("Attributes", {})
                or {}
            )
        except Exception as exc:  # noqa: BLE001
            log(f"  warn: get_queue_attributes({name}) failed: {exc}")
        comp_id = _unique_id(f"sqs_{name}", used_ids)
        encryption = bool(attrs.get("KmsMasterKeyId")) or attrs.get("SqsManagedSseEnabled") == "true"
        config = {
            "queue_name": name,
            "queue_url": url,
            "fifo": attrs.get("FifoQueue") == "true",
            "encryption": encryption,
        }
        components.append(
            _component(
                comp_id=comp_id,
                service="sqs",
                label=f"SQS {name}",
                config=config,
            )
        )
        count += 1
    return count


def _scan_api_gateway(session, components, boundaries, used_ids, log):
    client = session.client("apigateway")
    count = 0
    paginator = client.get_paginator("get_rest_apis")
    for page in paginator.paginate(PaginationConfig={"MaxItems": _MAX_PER_SERVICE}):
        for api in page.get("items", []) or []:
            api_id = api.get("id", "")
            name = api.get("name") or api_id
            comp_id = _unique_id(f"api_gateway_{name}", used_ids)
            config = {
                "api_id": api_id,
                "name": name,
                "endpoint_types": (api.get("endpointConfiguration") or {}).get("types", []) or [],
            }
            components.append(
                _component(
                    comp_id=comp_id,
                    service="api_gateway",
                    label=f"APIGW {name}",
                    config=config,
                )
            )
            count += 1
            if count >= _MAX_PER_SERVICE:
                return count
    return count


def _scan_cloudtrail(session, components, boundaries, used_ids, log):
    client = session.client("cloudtrail")
    trails = client.describe_trails().get("trailList", []) or []
    count = 0
    for trail in trails[:_MAX_PER_SERVICE]:
        name = trail.get("Name", "")
        comp_id = _unique_id(f"cloudtrail_{name}", used_ids)
        config = {
            "trail_name": name,
            "is_multi_region": trail.get("IsMultiRegionTrail", False),
            "log_file_validation": trail.get("LogFileValidationEnabled", False),
            "s3_bucket": trail.get("S3BucketName"),
            "kms_key_id": trail.get("KmsKeyId"),
        }
        components.append(
            _component(
                comp_id=comp_id,
                service="cloudtrail",
                label=f"CloudTrail {name}",
                config=config,
            )
        )
        count += 1
    return count


_SCANNERS: dict[str, Callable[..., int]] = {
    "ec2": _scan_ec2,
    "vpc": _scan_vpc,
    "rds": _scan_rds,
    "s3": _scan_s3,
    "lambda": _scan_lambda,
    "ecs": _scan_ecs,
    "eks": _scan_eks,
    "dynamodb": _scan_dynamodb,
    "alb": _scan_alb,
    "cloudfront": _scan_cloudfront,
    "sqs": _scan_sqs,
    "api_gateway": _scan_api_gateway,
    "cloudtrail": _scan_cloudtrail,
}

# Friendly per-service display names for the progress line.
_DISPLAY = {
    "ec2": "EC2",
    "vpc": "VPC + subnets + SGs",
    "rds": "RDS",
    "s3": "S3",
    "lambda": "Lambda",
    "ecs": "ECS",
    "eks": "EKS",
    "dynamodb": "DynamoDB",
    "alb": "ALB / NLB",
    "cloudfront": "CloudFront",
    "sqs": "SQS",
    "api_gateway": "API Gateway",
    "cloudtrail": "CloudTrail",
}


def _infer_connections(components: list[Component], session, log) -> list[Connection]:
    """Best-effort connection inference for live-imported components.

    Currently:
      - ALB -> EC2 (via target group describe_target_health, instance targets)
      - CloudFront -> S3 (via distribution origin domains)

    Lambda -> DynamoDB inference via IAM policy parsing is intentionally
    deferred; it requires walking attached + inline policies which is brittle
    and noisy. Logged as 'could not infer' so the user knows.
    """
    conns: list[Connection] = []

    # Index components for lookup.
    ec2_by_instance_id: dict[str, Component] = {}
    for c in components:
        if c.service == "ec2":
            inst_id = (c.config or {}).get("vpc_id"), (c.config or {}).get("subnet_id")  # noqa: F841 — placeholder
            # Recover instance id from the label "EC2 i-abc123"
            label = c.label or ""
            if label.startswith("EC2 "):
                ec2_by_instance_id[label.removeprefix("EC2 ").strip()] = c

    s3_by_bucket: dict[str, Component] = {}
    for c in components:
        if c.service == "s3":
            bucket = (c.config or {}).get("bucket")
            if bucket:
                s3_by_bucket[bucket] = c

    # ALB -> EC2 via target groups.
    alb_components = [c for c in components if c.service in {"alb", "nlb"}]
    if alb_components:
        try:
            elbv2 = session.client("elbv2")
            for alb in alb_components:
                lb_arn = (alb.config or {}).get("lb_arn")
                if not lb_arn:
                    continue
                try:
                    tgs = elbv2.describe_target_groups(LoadBalancerArn=lb_arn).get("TargetGroups", []) or []
                except Exception as exc:  # noqa: BLE001
                    log(f"  warn: describe_target_groups({alb.label}) failed: {exc}")
                    continue
                for tg in tgs:
                    tg_arn = tg.get("TargetGroupArn")
                    if not tg_arn:
                        continue
                    try:
                        health = (
                            elbv2.describe_target_health(TargetGroupArn=tg_arn).get("TargetHealthDescriptions", [])
                            or []
                        )
                    except Exception as exc:  # noqa: BLE001
                        log(f"  warn: describe_target_health failed: {exc}")
                        continue
                    for desc in health:
                        target = desc.get("Target") or {}
                        target_id = target.get("Id", "")
                        if target_id.startswith("i-") and target_id in ec2_by_instance_id:
                            ec2_comp = ec2_by_instance_id[target_id]
                            conns.append(
                                Connection(
                                    source=alb.id,
                                    target=ec2_comp.id,
                                    label="HTTP",
                                    protocol="HTTP",
                                    port=80,
                                )
                            )
        except Exception as exc:  # noqa: BLE001
            log(f"  warn: ALB->EC2 inference failed: {exc}")

    # CloudFront -> S3 via origin domains.
    for c in components:
        if c.service != "cloudfront":
            continue
        for origin_domain in (c.config or {}).get("origin_domains", []) or []:
            # S3 origins look like 'bucket.s3.amazonaws.com' or
            # 'bucket.s3.us-east-1.amazonaws.com' or 'bucket.s3-website-...'.
            for bucket, s3_comp in s3_by_bucket.items():
                if origin_domain.startswith(f"{bucket}.s3"):
                    conns.append(
                        Connection(
                            source=c.id,
                            target=s3_comp.id,
                            label="origin",
                            protocol="HTTPS",
                            port=443,
                        )
                    )
                    break

    # Lambda -> DynamoDB: heuristic deferred. Log so the user is not surprised.
    if any(c.service == "lambda" for c in components) and any(c.service == "dynamodb" for c in components):
        log("  note: could not infer Lambda -> DynamoDB connections (IAM walk not implemented)")

    # De-dupe (an EC2 instance can be in multiple target groups).
    seen: set[tuple[str, str]] = set()
    deduped: list[Connection] = []
    for conn in conns:
        key = (conn.source, conn.target)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(conn)
    return deduped


def import_live_aws(
    *,
    region: str,
    profile: str | None = None,
    services: Iterable[str] | None = None,
    progress: Callable[[str], None] | None = None,
    name: str | None = None,
) -> ArchSpec:
    """Walk live AWS APIs and produce an ArchSpec.

    Args:
        region: AWS region to scan (e.g. ``us-east-1``).
        profile: Named profile from ``~/.aws/credentials``. None = default chain.
        services: Subset of services to scan. None = all of ``SUPPORTED_SERVICES``.
        progress: Optional callback for per-service status lines. None = silent.
        name: Override the spec name. Default = ``aws-live-{region}``.

    Returns:
        ArchSpec populated with components, boundaries, and best-effort
        connections from the running AWS environment.

    Raises:
        LiveImportError: When boto3 isn't installed or AWS credentials are missing.
    """
    log = progress or (lambda _msg: None)

    try:
        import boto3
        from botocore.exceptions import (  # type: ignore[import-not-found]
            NoCredentialsError,
            PartialCredentialsError,
        )
    except ImportError as exc:
        raise LiveImportError(
            "boto3 is required for live AWS import. Install it with: pip install 'cloudwright-ai[live-import]'"
        ) from exc

    try:
        session = boto3.Session(region_name=region, profile_name=profile)
        # Force a credential resolve up front so we fail fast with a clean message.
        creds = session.get_credentials()
        if creds is None:
            raise LiveImportError("AWS credentials not found. Configure with `aws configure` or set AWS_PROFILE.")
    except (NoCredentialsError, PartialCredentialsError) as exc:
        raise LiveImportError("AWS credentials not found. Configure with `aws configure` or set AWS_PROFILE.") from exc
    except LiveImportError:
        raise
    except Exception as exc:  # noqa: BLE001
        # ProfileNotFound and similar config errors land here.
        raise LiveImportError(f"Failed to initialise AWS session: {exc}") from exc

    requested = list(services) if services else list(SUPPORTED_SERVICES)
    unknown = [s for s in requested if s not in _SCANNERS]
    if unknown:
        raise LiveImportError(f"Unknown service(s): {sorted(set(unknown))}. Supported: {list(SUPPORTED_SERVICES)}")

    components: list[Component] = []
    boundaries: list[Boundary] = []
    used_ids: set[str] = set()

    for svc in requested:
        scanner = _SCANNERS[svc]
        display = _DISPLAY.get(svc, svc)
        try:
            n = scanner(session, components, boundaries, used_ids, log)
            log(f"Scanning {display}... found {n}")
        except Exception as exc:  # noqa: BLE001 — we want broad guard per service
            if _is_access_denied(exc):
                log(f"Scanning {display}... permission denied, skipping")
            else:
                log(f"Scanning {display}... error: {exc}")

    connections = _infer_connections(components, session, log)

    spec_name = name or f"aws-live-{region}"
    spec = ArchSpec(
        name=spec_name,
        provider="aws",
        region=region,
        components=components,
        connections=connections,
        boundaries=boundaries,
        metadata={
            "imported_from": "live_aws",
            "region": region,
            "profile": profile or "default",
            "services_scanned": requested,
        },
    )
    return spec


__all__ = [
    "LiveImportError",
    "SUPPORTED_SERVICES",
    "import_live_aws",
]
