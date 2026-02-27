"""CloudFormation template importer — parses CFN JSON/YAML and produces an ArchSpec."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from cloudwright.spec import ArchSpec, Component, Connection

# CloudFormation resource type → service_key
_CFN_TYPE_MAP: dict[str, str] = {
    # Compute
    "AWS::EC2::Instance": "ec2",
    "AWS::EC2::LaunchTemplate": "ec2",
    "AWS::AutoScaling::AutoScalingGroup": "ec2",
    # Containers
    "AWS::ECS::Cluster": "ecs",
    "AWS::ECS::Service": "ecs",
    "AWS::ECS::TaskDefinition": "ecs",
    "AWS::EKS::Cluster": "eks",
    "AWS::EKS::Nodegroup": "eks",
    # Serverless
    "AWS::Lambda::Function": "lambda",
    # Databases
    "AWS::RDS::DBInstance": "rds",
    "AWS::RDS::DBCluster": "aurora",
    "AWS::DynamoDB::Table": "dynamodb",
    # Storage
    "AWS::S3::Bucket": "s3",
    "AWS::EBS::Volume": "ebs",
    # Networking
    "AWS::ElasticLoadBalancingV2::LoadBalancer": "alb",
    "AWS::ElasticLoadBalancing::LoadBalancer": "alb",
    "AWS::CloudFront::Distribution": "cloudfront",
    "AWS::Route53::HostedZone": "route53",
    "AWS::Route53::RecordSet": "route53",
    "AWS::ApiGatewayV2::Api": "api_gateway",
    "AWS::ApiGateway::RestApi": "api_gateway",
    # Security
    "AWS::WAFv2::WebACL": "waf",
    "AWS::WAF::WebACL": "waf",
    "AWS::Cognito::UserPool": "cognito",
    "AWS::Cognito::IdentityPool": "cognito",
    # Caching
    "AWS::ElastiCache::CacheCluster": "elasticache",
    "AWS::ElastiCache::ReplicationGroup": "elasticache",
    # Messaging
    "AWS::SQS::Queue": "sqs",
    "AWS::SNS::Topic": "sns",
    "AWS::Events::EventBus": "eventbridge",
    "AWS::Events::Rule": "eventbridge",
    # DNS / CDN helpers
    "AWS::CloudFront::CloudFrontOriginAccessIdentity": "cloudfront",
    # Analytics
    "AWS::Redshift::Cluster": "redshift",
    # ML
    "AWS::SageMaker::Endpoint": "sagemaker",
    "AWS::SageMaker::Model": "sagemaker",
}

_TIER = {
    "cloudfront": 0,
    "alb": 1,
    "waf": 1,
    "route53": 1,
    "api_gateway": 1,
    "cognito": 1,
    "ec2": 2,
    "lambda": 2,
    "ecs": 2,
    "eks": 2,
    "rds": 3,
    "aurora": 3,
    "dynamodb": 3,
    "elasticache": 3,
    "sqs": 3,
    "sns": 3,
    "eventbridge": 3,
    "redshift": 3,
    "s3": 4,
    "ebs": 4,
}


class CloudFormationImporter:
    """Parses CloudFormation templates (JSON or YAML) into an ArchSpec."""

    @property
    def format_name(self) -> str:
        return "cloudformation"

    def can_import(self, path: str) -> bool:
        p = Path(path)
        if p.suffix in (".json", ".yaml", ".yml", ".template"):
            try:
                data = _load_template(p)
                return isinstance(data, dict) and "Resources" in data and "AWSTemplateFormatVersion" in data
            except Exception:
                return False
        return False

    def do_import(self, path: str) -> ArchSpec:
        data = _load_template(Path(path))
        resources = data.get("Resources", {})
        name = _derive_name(path, data)
        return _build_spec(name, resources)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _load_template(path: Path) -> dict[str, Any]:
    text = path.read_text()
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def _derive_name(path: str, data: dict[str, Any]) -> str:
    # Prefer Description field if short enough
    desc = data.get("Description", "")
    if desc and len(desc) <= 60:
        return desc
    stem = Path(path).stem
    return stem.replace("_", " ").replace("-", " ").title()


def _build_spec(name: str, resources: dict[str, Any]) -> ArchSpec:
    components: list[Component] = []
    svc_to_comp: dict[str, Component] = {}
    logical_to_comp: dict[str, Component] = {}

    for logical_id, res in resources.items():
        cfn_type = res.get("Type", "")
        service_key = _CFN_TYPE_MAP.get(cfn_type)
        if service_key is None:
            continue

        comp_id = _make_id(service_key, logical_id, svc_to_comp)
        props = res.get("Properties", {}) or {}
        config = _extract_config(service_key, props)

        comp = Component(
            id=comp_id,
            service=service_key,
            provider="aws",
            label=_label(service_key, logical_id),
            tier=_TIER.get(service_key, 2),
            config=config,
        )
        components.append(comp)
        svc_to_comp.setdefault(service_key, comp)
        logical_to_comp[logical_id] = comp

    # Extract Ref/GetAtt/Sub references from template properties
    ref_connections = _extract_ref_connections(resources, logical_to_comp)
    # Add heuristic connections for pairs not already covered by explicit refs
    heuristic = _infer_connections(svc_to_comp)
    seen = {(c.source, c.target) for c in ref_connections}
    for conn in heuristic:
        if (conn.source, conn.target) not in seen:
            ref_connections.append(conn)

    return ArchSpec(name=name, provider="aws", components=components, connections=ref_connections)


def _extract_config(service_key: str, props: dict[str, Any]) -> dict[str, Any]:
    config: dict[str, Any] = {}

    # Instance type
    for key in ("InstanceType", "MachineType"):
        if key in props:
            config["instance_type"] = _resolve(props[key])
            break

    # DB specifics
    if "DBInstanceClass" in props:
        config["instance_class"] = _resolve(props["DBInstanceClass"])
    if "Engine" in props:
        config["engine"] = _resolve(props["Engine"])
    if "AllocatedStorage" in props:
        try:
            config["storage_gb"] = int(_resolve(props["AllocatedStorage"]))
        except (TypeError, ValueError):
            pass
    if props.get("MultiAZ") is True or _resolve(props.get("MultiAZ")) == "true":
        config["multi_az"] = True
    if props.get("StorageEncrypted") is True or _resolve(props.get("StorageEncrypted")) == "true":
        config["encryption"] = True

    # Lambda
    if "MemorySize" in props:
        try:
            config["memory_mb"] = int(_resolve(props["MemorySize"]))
        except (TypeError, ValueError):
            pass

    # ECS desired count
    if "DesiredCount" in props:
        try:
            config["count"] = int(_resolve(props["DesiredCount"]))
        except (TypeError, ValueError):
            pass

    # S3 encryption
    server_side = props.get("BucketEncryption", {})
    if server_side:
        config["encryption"] = True

    return config


def _resolve(value: Any) -> Any:
    """Strip CloudFormation intrinsic functions, returning the raw value if possible."""
    if isinstance(value, dict):
        # Return the Ref/value as a placeholder string so it doesn't crash comparisons
        return next(iter(value.values()), "")
    return value


def _label(service_key: str, logical_id: str) -> str:
    return logical_id.replace("_", " ").replace("-", " ")


def _make_id(service_key: str, logical_id: str, existing: dict[str, Component]) -> str:
    if service_key not in existing:
        return _safe_id(service_key)
    candidate = _safe_id(logical_id)
    used = {c.id for c in existing.values()}
    if candidate not in used:
        return candidate
    return _safe_id(f"{service_key}_{logical_id}")


def _safe_id(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name).strip("_")
    if not safe or not (safe[0].isalpha() or safe[0] == "_"):
        safe = "res_" + safe
    return safe[:64]


def _find_refs(obj: Any, valid_ids: set[str]) -> set[str]:
    """Recursively find Ref, Fn::GetAtt, and Fn::Sub references to other logical resources."""
    found: set[str] = set()
    if isinstance(obj, dict):
        if "Ref" in obj and obj["Ref"] in valid_ids:
            found.add(obj["Ref"])
        if "Fn::GetAtt" in obj:
            att = obj["Fn::GetAtt"]
            target = att[0] if isinstance(att, list) else str(att).split(".")[0]
            if target in valid_ids:
                found.add(target)
        if "Fn::Sub" in obj:
            sub_val = obj["Fn::Sub"]
            template = sub_val if isinstance(sub_val, str) else sub_val[0] if isinstance(sub_val, list) else ""
            for match in re.finditer(r"\$\{(\w+)(?:\.\w+)?\}", template):
                ref = match.group(1)
                if ref in valid_ids:
                    found.add(ref)
        for v in obj.values():
            found |= _find_refs(v, valid_ids)
    elif isinstance(obj, list):
        for item in obj:
            found |= _find_refs(item, valid_ids)
    return found


def _connection_label(source_svc: str, target_svc: str) -> str:
    """Pick a label based on the service pair."""
    if target_svc in ("rds", "aurora"):
        return "SQL"
    if target_svc == "dynamodb":
        return "read/write"
    if target_svc == "s3":
        return "read/write"
    if target_svc == "lambda":
        return "invoke"
    if target_svc in ("sqs", "sns"):
        return "enqueue"
    if target_svc == "elasticache":
        return "cache"
    if target_svc in ("alb",):
        return "HTTPS"
    return "depends"


def _extract_ref_connections(
    resources: dict[str, Any],
    logical_to_comp: dict[str, Component],
) -> list[Connection]:
    """Build connections from explicit CFN references (Ref, Fn::GetAtt, Fn::Sub)."""
    all_logical_ids = set(resources.keys())
    connections: list[Connection] = []
    seen: set[tuple[str, str]] = set()

    for logical_id, res in resources.items():
        props = res.get("Properties", {}) or {}
        targets = _find_refs(props, all_logical_ids)
        src = logical_to_comp.get(logical_id)
        if not src:
            continue
        for target_id in targets:
            if target_id == logical_id:
                continue
            tgt = logical_to_comp.get(target_id)
            if not tgt:
                continue
            pair = (src.id, tgt.id)
            if pair in seen:
                continue
            seen.add(pair)
            label = _connection_label(src.service, tgt.service)
            connections.append(Connection(source=src.id, target=tgt.id, label=label))

    return connections


def _infer_connections(svc_to_comp: dict[str, Component]) -> list[Connection]:
    conns: list[Connection] = []

    def get(*keys: str) -> Component | None:
        for k in keys:
            if k in svc_to_comp:
                return svc_to_comp[k]
        return None

    cdn = get("cloudfront")
    lb = get("alb")
    compute = get("ec2", "ecs", "eks")
    fn = get("lambda")
    api = get("api_gateway")
    db = get("rds", "aurora", "dynamodb")
    cache = get("elasticache")
    storage = get("s3")
    queue = get("sqs", "sns")
    app = compute or fn

    if cdn and lb:
        conns.append(Connection(source=cdn.id, target=lb.id, label="HTTPS", protocol="HTTPS", port=443))
    elif cdn and app:
        conns.append(Connection(source=cdn.id, target=app.id, label="HTTPS", protocol="HTTPS", port=443))

    if lb and app:
        conns.append(Connection(source=lb.id, target=app.id, label="HTTP", protocol="HTTP", port=80))

    if api and fn:
        conns.append(Connection(source=api.id, target=fn.id, label="invoke"))
    elif api and compute:
        conns.append(Connection(source=api.id, target=compute.id, label="HTTP", protocol="HTTP", port=80))

    if app and db:
        conns.append(Connection(source=app.id, target=db.id, label="SQL", protocol="TCP"))
    if app and cache:
        conns.append(Connection(source=app.id, target=cache.id, label="cache", protocol="TCP"))
    if app and storage:
        conns.append(Connection(source=app.id, target=storage.id, label="read/write"))
    if app and queue:
        conns.append(Connection(source=app.id, target=queue.id, label="enqueue"))

    return conns
