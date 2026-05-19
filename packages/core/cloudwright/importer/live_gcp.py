"""Live GCP importer — walks google-cloud SDK calls and produces an ArchSpec.

Use via the CLI: ``cloudwright import-live --provider gcp --project my-proj``.

Requires the optional GCP SDKs:
``pip install 'cloudwright-ai[live-import]'``.

Mirrors the AWS importer: lazy SDK import, fast-fail on missing credentials,
non-fatal per-service permission guards, canonical registry service keys.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from cloudwright.importer.live_aws import LiveImportError, _unique_id
from cloudwright.spec import ArchSpec, Component, Connection

_TIER = {
    "compute_engine": 2,
    "cloud_storage": 4,
    "cloud_sql": 3,
}

# Most-common-first scan order.
SUPPORTED_SERVICES: tuple[str, ...] = ("compute_engine", "cloud_storage", "cloud_sql")

_DISPLAY = {
    "compute_engine": "Compute Engine",
    "cloud_storage": "Cloud Storage",
    "cloud_sql": "Cloud SQL",
}


def _component(*, comp_id: str, service: str, label: str, config: dict[str, Any]) -> Component:
    return Component(
        id=comp_id,
        service=service,
        provider="gcp",
        label=label,
        tier=_TIER.get(service, 2),
        config={k: v for k, v in config.items() if v is not None},
    )


def _is_access_denied(exc: Exception) -> bool:
    """Detect GCP permission-denied errors across SDK exception shapes."""
    name = type(exc).__name__
    if name in {"Forbidden", "PermissionDenied", "Unauthorized"}:
        return True
    code = getattr(exc, "code", None)
    if code in (403, 401):
        return True
    msg = str(exc).lower()
    return "permission denied" in msg or "forbidden" in msg or "403" in msg or "does not have" in msg


def _scan_compute_engine(client, project, components, used_ids, log) -> int:
    count = 0
    for _zone, scoped in client.aggregated_list(project=project):
        instances = getattr(scoped, "instances", None) or []
        for inst in instances:
            machine = (getattr(inst, "machine_type", "") or "").rsplit("/", 1)[-1]
            zone = (getattr(inst, "zone", "") or "").rsplit("/", 1)[-1]
            cid = _unique_id(getattr(inst, "name", "vm") or "vm", used_ids)
            shielded = getattr(inst, "shielded_instance_config", None)
            components.append(
                _component(
                    comp_id=cid,
                    service="compute_engine",
                    label=getattr(inst, "name", cid),
                    config={
                        "machine_type": machine or None,
                        "zone": zone or None,
                        "status": getattr(inst, "status", None),
                        "shielded_vm": bool(getattr(shielded, "enable_secure_boot", False)) if shielded else None,
                    },
                )
            )
            count += 1
    return count


def _scan_cloud_storage(client, project, components, used_ids, log) -> int:
    count = 0
    for bucket in client.list_buckets():
        cid = _unique_id(getattr(bucket, "name", "bucket") or "bucket", used_ids)
        iam_cfg = getattr(bucket, "iam_configuration", None)
        pap = getattr(iam_cfg, "public_access_prevention", None) if iam_cfg else None
        components.append(
            _component(
                comp_id=cid,
                service="cloud_storage",
                label=getattr(bucket, "name", cid),
                config={
                    "location": getattr(bucket, "location", None),
                    "storage_class": getattr(bucket, "storage_class", None),
                    "encryption": bool(getattr(bucket, "default_kms_key_name", None)) or None,
                    "versioning": getattr(bucket, "versioning_enabled", None),
                    "public_access_prevention": pap,
                },
            )
        )
        count += 1
    return count


def _scan_cloud_sql(client, project, components, used_ids, log) -> int:
    """Cloud SQL via the Admin REST client (sqladmin). Best-effort."""
    count = 0
    resp = client.instances().list(project=project).execute()
    for item in resp.get("items", []) or []:
        cid = _unique_id(item.get("name", "sql") or "sql", used_ids)
        settings = item.get("settings", {}) or {}
        ip_cfg = settings.get("ipConfiguration", {}) or {}
        components.append(
            _component(
                comp_id=cid,
                service="cloud_sql",
                label=item.get("name", cid),
                config={
                    "database_version": item.get("databaseVersion"),
                    "tier": (settings.get("tier")),
                    "region": item.get("region"),
                    "backup_enabled": (settings.get("backupConfiguration", {}) or {}).get("enabled"),
                    "public_ip": bool(ip_cfg.get("ipv4Enabled")),
                },
            )
        )
        count += 1
    return count


_SCANNERS: dict[str, Any] = {
    "compute_engine": _scan_compute_engine,
    "cloud_storage": _scan_cloud_storage,
    "cloud_sql": _scan_cloud_sql,
}


def _build_clients(project: str):
    """Return {service: client}. Lazy SDK import; raises LiveImportError cleanly."""
    clients: dict[str, Any] = {}
    try:
        from google.cloud import compute_v1

        clients["compute_engine"] = compute_v1.InstancesClient()
    except ImportError as exc:
        raise LiveImportError(
            "google-cloud-compute is required for GCP import. Install with: pip install 'cloudwright-ai[live-import]'"
        ) from exc
    try:
        from google.cloud import storage

        clients["cloud_storage"] = storage.Client(project=project)
    except ImportError as exc:
        raise LiveImportError(
            "google-cloud-storage is required for GCP import. Install with: pip install 'cloudwright-ai[live-import]'"
        ) from exc
    try:
        from googleapiclient.discovery import build  # type: ignore[import-not-found]

        clients["cloud_sql"] = build("sqladmin", "v1beta4", cache_discovery=False)
    except ImportError:
        # Cloud SQL admin client is optional; skip if google-api-python-client absent.
        pass
    return clients


def import_live_gcp(
    *,
    project: str | None = None,
    region: str | None = None,
    services: Iterable[str] | None = None,
    progress: Callable[[str], None] | None = None,
    name: str | None = None,
    _clients: dict[str, Any] | None = None,
) -> ArchSpec:
    """Walk live GCP APIs and produce an ArchSpec.

    Args:
        project: GCP project ID. Falls back to GOOGLE_CLOUD_PROJECT env var.
        region: Optional region label recorded in metadata.
        services: Subset of services to scan. None = all of SUPPORTED_SERVICES.
        progress: Optional callback for per-service status lines.
        name: Override the spec name. Default = ``gcp-live-{project}``.
        _clients: Test injection point (fake clients). Not for public use.

    Raises:
        LiveImportError: when SDKs are missing or credentials cannot resolve.
    """
    import os

    log = progress or (lambda _msg: None)
    project = project or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not project:
        raise LiveImportError("GCP project not set. Pass --project or set GOOGLE_CLOUD_PROJECT.")

    if _clients is None:
        clients = _build_clients(project)
        try:
            import google.auth

            creds, _ = google.auth.default()
            if creds is None:
                raise LiveImportError("GCP credentials not found. Run `gcloud auth application-default login`.")
        except ImportError as exc:
            raise LiveImportError(
                "google-auth is required for GCP import. Install with: pip install 'cloudwright-ai[live-import]'"
            ) from exc
        except LiveImportError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LiveImportError(
                f"GCP credentials not found ({exc}). Run `gcloud auth application-default login`."
            ) from exc
    else:
        clients = _clients

    requested = list(services) if services else list(SUPPORTED_SERVICES)
    unknown = [s for s in requested if s not in _SCANNERS]
    if unknown:
        raise LiveImportError(f"Unknown service(s): {sorted(set(unknown))}. Supported: {list(SUPPORTED_SERVICES)}")

    components: list[Component] = []
    connections: list[Connection] = []
    used_ids: set[str] = set()

    for svc in requested:
        display = _DISPLAY.get(svc, svc)
        client = clients.get(svc)
        if client is None:
            log(f"Scanning {display}... SDK unavailable, skipping")
            continue
        try:
            n = _SCANNERS[svc](client, project, components, used_ids, log)
            log(f"Scanning {display}... found {n}")
        except Exception as exc:  # noqa: BLE001 — broad per-service guard
            if _is_access_denied(exc):
                log(f"Scanning {display}... permission denied, skipping")
            else:
                log(f"Scanning {display}... error: {exc}")

    return ArchSpec(
        name=name or f"gcp-live-{project}",
        provider="gcp",
        region=region or "global",
        components=components,
        connections=connections,
        metadata={
            "imported_from": "live_gcp",
            "project": project,
            "region": region or "global",
            "services_scanned": requested,
        },
    )
