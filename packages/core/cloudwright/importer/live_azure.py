"""Live Azure importer — walks azure-mgmt SDK calls and produces an ArchSpec.

Use via the CLI:
``cloudwright import-live --provider azure --subscription <SUB_ID>``.

Requires the optional Azure SDKs:
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
    "virtual_machines": 2,
    "blob_storage": 4,
    "azure_sql": 3,
    "aks": 2,
}

SUPPORTED_SERVICES: tuple[str, ...] = ("virtual_machines", "blob_storage", "azure_sql", "aks")

_DISPLAY = {
    "virtual_machines": "Virtual Machines",
    "blob_storage": "Storage Accounts",
    "azure_sql": "Azure SQL",
    "aks": "AKS Clusters",
}


def _component(*, comp_id: str, service: str, label: str, config: dict[str, Any]) -> Component:
    return Component(
        id=comp_id,
        service=service,
        provider="azure",
        label=label,
        tier=_TIER.get(service, 2),
        config={k: v for k, v in config.items() if v is not None},
    )


def _is_access_denied(exc: Exception) -> bool:
    """Detect Azure authorization failures across SDK exception shapes."""
    name = type(exc).__name__
    if name in {"HttpResponseError", "ClientAuthenticationError", "PermissionError"}:
        status = getattr(exc, "status_code", None)
        if status in (401, 403):
            return True
    msg = str(exc).lower()
    return (
        "authorizationfailed" in msg
        or "does not have authorization" in msg
        or "forbidden" in msg
        or "401" in msg
        or "403" in msg
    )


def _scan_virtual_machines(clients, components, used_ids, log) -> int:
    count = 0
    for vm in clients["virtual_machines"].virtual_machines.list_all():
        cid = _unique_id(getattr(vm, "name", "vm") or "vm", used_ids)
        hw = getattr(vm, "hardware_profile", None)
        components.append(
            _component(
                comp_id=cid,
                service="virtual_machines",
                label=getattr(vm, "name", cid),
                config={
                    "vm_size": getattr(hw, "vm_size", None) if hw else None,
                    "location": getattr(vm, "location", None),
                    "os": getattr(getattr(vm, "storage_profile", None), "os_disk", None)
                    and getattr(vm.storage_profile.os_disk, "os_type", None),
                },
            )
        )
        count += 1
    return count


def _scan_blob_storage(clients, components, used_ids, log) -> int:
    count = 0
    for acct in clients["blob_storage"].storage_accounts.list():
        cid = _unique_id(getattr(acct, "name", "storage") or "storage", used_ids)
        enc = getattr(acct, "encryption", None)
        components.append(
            _component(
                comp_id=cid,
                service="blob_storage",
                label=getattr(acct, "name", cid),
                config={
                    "location": getattr(acct, "location", None),
                    "sku": getattr(getattr(acct, "sku", None), "name", None),
                    "encryption": bool(enc) or None,
                    "https_only": getattr(acct, "enable_https_traffic_only", None),
                    "allow_public_blob": getattr(acct, "allow_blob_public_access", None),
                    "min_tls_version": getattr(acct, "minimum_tls_version", None),
                },
            )
        )
        count += 1
    return count


def _scan_azure_sql(clients, components, used_ids, log) -> int:
    count = 0
    for server in clients["azure_sql"].servers.list():
        cid = _unique_id(getattr(server, "name", "sqlserver") or "sqlserver", used_ids)
        components.append(
            _component(
                comp_id=cid,
                service="azure_sql",
                label=getattr(server, "name", cid),
                config={
                    "location": getattr(server, "location", None),
                    "version": getattr(server, "version", None),
                    "public_network_access": getattr(server, "public_network_access", None),
                    "min_tls_version": getattr(server, "minimal_tls_version", None),
                },
            )
        )
        count += 1
    return count


def _scan_aks(clients, components, used_ids, log) -> int:
    count = 0
    for cluster in clients["aks"].managed_clusters.list():
        cid = _unique_id(getattr(cluster, "name", "aks") or "aks", used_ids)
        api = getattr(cluster, "api_server_access_profile", None)
        components.append(
            _component(
                comp_id=cid,
                service="aks",
                label=getattr(cluster, "name", cid),
                config={
                    "location": getattr(cluster, "location", None),
                    "kubernetes_version": getattr(cluster, "kubernetes_version", None),
                    "private_cluster": getattr(api, "enable_private_cluster", None) if api else None,
                },
            )
        )
        count += 1
    return count


_SCANNERS: dict[str, Any] = {
    "virtual_machines": _scan_virtual_machines,
    "blob_storage": _scan_blob_storage,
    "azure_sql": _scan_azure_sql,
    "aks": _scan_aks,
}


def _build_clients(subscription_id: str):
    """Return azure-mgmt clients keyed by service. Lazy import; clean errors."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.compute import ComputeManagementClient
        from azure.mgmt.containerservice import ContainerServiceClient
        from azure.mgmt.sql import SqlManagementClient
        from azure.mgmt.storage import StorageManagementClient
    except ImportError as exc:
        raise LiveImportError(
            "azure-mgmt SDKs are required for Azure import. Install with: pip install 'cloudwright-ai[live-import]'"
        ) from exc

    try:
        cred = DefaultAzureCredential()
    except Exception as exc:  # noqa: BLE001
        raise LiveImportError(f"Azure credentials not found ({exc}). Run `az login` or set AZURE_* env vars.") from exc

    return {
        "virtual_machines": ComputeManagementClient(cred, subscription_id),
        "blob_storage": StorageManagementClient(cred, subscription_id),
        "azure_sql": SqlManagementClient(cred, subscription_id),
        "aks": ContainerServiceClient(cred, subscription_id),
    }


def import_live_azure(
    *,
    subscription: str | None = None,
    region: str | None = None,
    services: Iterable[str] | None = None,
    progress: Callable[[str], None] | None = None,
    name: str | None = None,
    _clients: dict[str, Any] | None = None,
) -> ArchSpec:
    """Walk live Azure APIs and produce an ArchSpec.

    Args:
        subscription: Azure subscription ID. Falls back to AZURE_SUBSCRIPTION_ID.
        region: Optional region label recorded in metadata.
        services: Subset of services to scan. None = all of SUPPORTED_SERVICES.
        progress: Optional callback for per-service status lines.
        name: Override the spec name. Default = ``azure-live-{subscription}``.
        _clients: Test injection point (fake clients). Not for public use.

    Raises:
        LiveImportError: when SDKs are missing or credentials cannot resolve.
    """
    import os

    log = progress or (lambda _msg: None)
    subscription = subscription or os.environ.get("AZURE_SUBSCRIPTION_ID")
    if not subscription:
        raise LiveImportError("Azure subscription not set. Pass --subscription or set AZURE_SUBSCRIPTION_ID.")

    clients = _clients if _clients is not None else _build_clients(subscription)

    requested = list(services) if services else list(SUPPORTED_SERVICES)
    unknown = [s for s in requested if s not in _SCANNERS]
    if unknown:
        raise LiveImportError(f"Unknown service(s): {sorted(set(unknown))}. Supported: {list(SUPPORTED_SERVICES)}")

    components: list[Component] = []
    connections: list[Connection] = []
    used_ids: set[str] = set()

    for svc in requested:
        display = _DISPLAY.get(svc, svc)
        try:
            n = _SCANNERS[svc](clients, components, used_ids, log)
            log(f"Scanning {display}... found {n}")
        except Exception as exc:  # noqa: BLE001 — broad per-service guard
            if _is_access_denied(exc):
                log(f"Scanning {display}... permission denied, skipping")
            else:
                log(f"Scanning {display}... error: {exc}")

    return ArchSpec(
        name=name or f"azure-live-{subscription}",
        provider="azure",
        region=region or "global",
        components=components,
        connections=connections,
        metadata={
            "imported_from": "live_azure",
            "subscription": subscription,
            "region": region or "global",
            "services_scanned": requested,
        },
    )
