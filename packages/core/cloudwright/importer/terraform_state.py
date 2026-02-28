"""Terraform state importer — parses .tfstate and produces an ArchSpec."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from cloudwright.importer.utils import align_ids
from cloudwright.spec import ArchSpec, Component, Connection

# Mapping: resource type prefix → provider name
_PROVIDER_PREFIXES = {
    "aws_": "aws",
    "google_": "gcp",
    "azurerm_": "azure",
    "azuread_": "azure",
}

# Canonical tier per service (presentation → data, 0=edge, 1=gateway, 2=compute, 3=data, 4=storage)
_TIER = {
    "cloudfront": 0,
    "cloud_cdn": 0,
    "azure_cdn": 0,
    "alb": 1,
    "nlb": 1,
    "cloud_load_balancing": 1,
    "app_gateway": 1,
    "azure_lb": 1,
    "waf": 1,
    "cloud_armor": 1,
    "azure_waf": 1,
    "api_gateway": 1,
    "cloud_api_gateway": 1,
    "api_management": 1,
    "route53": 1,
    "cloud_dns": 1,
    "azure_dns": 1,
    "ec2": 2,
    "compute_engine": 2,
    "virtual_machines": 2,
    "app_engine": 2,
    "lambda": 2,
    "cloud_functions": 2,
    "azure_functions": 2,
    "ecs": 2,
    "eks": 2,
    "fargate": 2,
    "gke": 2,
    "aks": 2,
    "cloud_run": 2,
    "container_apps": 2,
    "cognito": 1,
    "firebase_auth": 1,
    "azure_ad": 1,
    "rds": 3,
    "aurora": 3,
    "cloud_sql": 3,
    "azure_sql": 3,
    "dynamodb": 3,
    "firestore": 3,
    "cosmos_db": 3,
    "elasticache": 3,
    "memorystore": 3,
    "azure_cache": 3,
    "sqs": 3,
    "sns": 3,
    "pub_sub": 3,
    "service_bus": 3,
    "kinesis": 3,
    "dataflow": 3,
    "event_hubs": 3,
    "s3": 4,
    "cloud_storage": 4,
    "blob_storage": 4,
    "ebs": 4,
    "persistent_disk": 4,
    "managed_disks": 4,
}

_REGISTRY_DIR = Path(__file__).parent.parent / "data" / "registry"


def _build_terraform_map() -> dict[str, str]:
    """Build terraform resource type → service_key map from registry YAML files."""
    tf_map: dict[str, str] = {}
    for yaml_path in _REGISTRY_DIR.glob("*.yaml"):
        data = yaml.safe_load(yaml_path.read_text())
        for provider_svcs in data.get("services", {}).values():
            if not isinstance(provider_svcs, dict):
                continue
            for service_key, svc in provider_svcs.items():
                for tf_type in (svc or {}).get("terraform_types", []):
                    if tf_type:
                        tf_map[tf_type] = service_key
    return tf_map


# Attributes to extract per service; checked in order, first match wins
_CONFIG_EXTRACTORS: list[tuple[str, list[str]]] = [
    ("instance_type", ["instance_type", "machine_type", "size", "vm_size", "node_type"]),
    ("engine", ["engine", "database_version"]),
    ("storage_gb", ["allocated_storage", "disk_size_gb", "size_gb", "storage_size"]),
    ("memory_mb", ["memory_size"]),
    ("count", ["desired_count", "node_count", "min_size", "num_nodes"]),
    ("instance_class", ["instance_class"]),
]

_BOOL_ATTRS = {
    "multi_az": "multi_az",
    "storage_encrypted": "encryption",
    "encryption_enabled": "encryption",
}


class TerraformStateImporter:
    """Parses Terraform state files (v3 and v4) into ArchSpec."""

    def __init__(self) -> None:
        self._tf_map = _build_terraform_map()

    @property
    def format_name(self) -> str:
        return "terraform"

    def can_import(self, path: str) -> bool:
        p = Path(path)
        return p.suffix == ".tfstate" or (p.suffix == ".json" and "tfstate" in p.name)

    def do_import(self, path: str, design_spec: ArchSpec | None = None) -> ArchSpec:
        data = json.loads(Path(path).read_text())
        version = data.get("version", 4)
        resources = self._parse_v3(data) if version <= 3 else self._parse_v4(data)
        spec = self._build_spec(resources, path)
        if design_spec:
            spec = align_ids(spec, design_spec)
        return spec

    # Parsing

    def _parse_v3(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        resources = []
        for module in data.get("modules", []):
            module_path = ".".join(module.get("path", ["root"])[1:])
            for addr, res in module.get("resources", {}).items():
                if res.get("mode") == "data":
                    continue
                primary = res.get("primary", {})
                resources.append(
                    {
                        "type": res["type"],
                        "name": res.get("name", addr.split(".")[-1]),
                        "module": module_path,
                        "attributes": primary.get("attributes", {}),
                        "id": primary.get("id", ""),
                    }
                )
        return resources

    def _parse_v4(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        resources = []
        for res in data.get("resources", []):
            if res.get("mode") == "data":
                continue
            module = res.get("module", "")
            for instance in res.get("instances", []):
                attrs = instance.get("attributes", {})
                resources.append(
                    {
                        "type": res["type"],
                        "name": res["name"],
                        "module": module,
                        "attributes": attrs,
                        "id": attrs.get("id", ""),
                    }
                )
        return resources

    # ArchSpec construction

    def _detect_provider(self, resources: list[dict[str, Any]]) -> str:
        counts: dict[str, int] = {"aws": 0, "gcp": 0, "azure": 0}
        for res in resources:
            for prefix, provider in _PROVIDER_PREFIXES.items():
                if res["type"].startswith(prefix):
                    counts[provider] += 1
                    break
        return max(counts, key=lambda k: counts[k]) if any(counts.values()) else "aws"

    def _build_spec(self, resources: list[dict[str, Any]], path: str) -> ArchSpec:
        provider = self._detect_provider(resources)
        name = _derive_name(path)

        components: list[Component] = []
        # service_key → first component with that service (for connection inference)
        svc_to_comp: dict[str, Component] = {}

        for res in resources:
            service_key = self._tf_map.get(res["type"])
            if service_key is None:
                continue

            comp_id = _make_id(service_key, res["name"], svc_to_comp)
            config = _extract_config(res["attributes"])
            svc_label = service_key.replace("_", " ").title()

            comp = Component(
                id=comp_id,
                service=service_key,
                provider=provider,
                label=svc_label,
                tier=_TIER.get(service_key, 2),
                config=config,
            )
            components.append(comp)
            svc_to_comp.setdefault(service_key, comp)

        connections = _infer_connections(svc_to_comp)
        return ArchSpec(name=name, provider=provider, components=components, connections=connections)


# Helpers


def _extract_config(attrs: dict[str, Any]) -> dict[str, Any]:
    config: dict[str, Any] = {}

    for config_key, attr_names in _CONFIG_EXTRACTORS:
        for attr in attr_names:
            val = attrs.get(attr)
            if val is not None and val != "" and val != 0:
                try:
                    val = int(val) if config_key in ("storage_gb", "count") else val
                except (TypeError, ValueError):
                    pass
                # GCP machine_type comes as zones/ZONE/machineTypes/TYPE — strip path
                if config_key == "instance_type" and isinstance(val, str) and "/" in val:
                    val = val.rsplit("/", 1)[-1]
                config[config_key] = val
                break

    for attr, config_key in _BOOL_ATTRS.items():
        if attrs.get(attr):
            config[config_key] = True

    return config


def _make_id(service_key: str, resource_name: str, existing: dict[str, Component]) -> str:
    """Generate a unique IaC-safe component ID."""
    if service_key not in existing:
        return _safe_id(service_key)
    # Already have this service — suffix with resource name to disambiguate
    candidate = _safe_id(f"{service_key}_{resource_name}")
    # Avoid collisions with already-generated IDs
    used = {c.id for c in existing.values()}
    if candidate not in used:
        return candidate
    return _safe_id(f"{service_key}_{resource_name}_2")


def _safe_id(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name).strip("_")
    if not safe or not (safe[0].isalpha() or safe[0] == "_"):
        safe = "svc_" + safe
    return safe[:64]


def _derive_name(path: str) -> str:
    stem = Path(path).stem
    return stem.replace("_", " ").replace("-", " ").title()


def _infer_connections(svc_to_comp: dict[str, Component]) -> list[Connection]:
    """Heuristic wiring between recognized service pairs."""
    conns: list[Connection] = []

    def get(*keys: str) -> Component | None:
        for k in keys:
            if k in svc_to_comp:
                return svc_to_comp[k]
        return None

    lb = get("alb", "nlb", "cloud_load_balancing", "app_gateway", "azure_lb")
    cdn = get("cloudfront", "cloud_cdn", "azure_cdn")
    compute = get("ec2", "ecs", "eks", "fargate", "compute_engine", "virtual_machines", "cloud_run", "gke", "aks")
    fn = get("lambda", "cloud_functions", "azure_functions")
    api = get("api_gateway", "cloud_api_gateway", "api_management")
    db = get("rds", "aurora", "cloud_sql", "azure_sql", "dynamodb", "firestore", "cosmos_db")
    cache = get("elasticache", "memorystore", "azure_cache")
    storage = get("s3", "cloud_storage", "blob_storage")
    queue = get("sqs", "pub_sub", "service_bus")
    app = compute or fn  # primary application layer

    if cdn and lb:
        conns.append(Connection(source=cdn.id, target=lb.id, label="HTTPS", protocol="HTTPS", port=443))
    elif cdn and compute:
        conns.append(Connection(source=cdn.id, target=compute.id, label="HTTPS", protocol="HTTPS", port=443))

    if lb and compute:
        conns.append(Connection(source=lb.id, target=compute.id, label="HTTP", protocol="HTTP", port=80))

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
