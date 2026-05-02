"""JSON extraction and ArchSpec parsing from LLM output."""

from __future__ import annotations

import json
import re

from cloudwright.logging import get_logger
from cloudwright.prompts import (
    ALL_VALID_SERVICES,
    COMPUTE_SERVICES,
    DATA_STORE_SERVICES,
    DATABASE_SERVICES,
    DEFAULT_INSTANCE_TYPES,
    PROVIDER_SERVICES,
    SERVICE_ENGINE_SUFFIXES,
    SERVICE_NORMALIZATION,
)
from cloudwright.providers import get_equivalent
from cloudwright.spec import ArchSpec, Boundary, Component, Connection, Constraints

log = get_logger(__name__)


_JSON_DECODER = json.JSONDecoder()


def _extract_json(text: str) -> dict:
    """Extract the first complete JSON object/array from text.

    Strips markdown code fences and ``<json>`` XML wrappers, locates the first
    ``{`` or ``[``, then defers to the C-implemented stdlib JSONDecoder which
    handles strings, escapes, unicode, and nested-quoted JSON correctly.
    """
    # Strip markdown code fences (```json ... ```)
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.replace("```", "")
    # Strip optional <json>...</json> XML wrappers (some LLMs emit these)
    text = re.sub(r"</?json\s*>", "", text, flags=re.IGNORECASE)

    obj_start = text.find("{")
    arr_start = text.find("[")
    candidates = [i for i in (obj_start, arr_start) if i != -1]
    if not candidates:
        raise ValueError(f"No JSON object found in LLM response: {text[:300]}")
    start = min(candidates)

    try:
        parsed, _end = _JSON_DECODER.raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Unterminated or invalid JSON in LLM response: {text[:300]}") from exc
    return parsed


def _enforce_connections(spec: ArchSpec) -> ArchSpec:
    """Validate connection references and add defaults for isolated components."""
    component_ids = {c.id for c in spec.components}
    id_to_comp = {c.id: c for c in spec.components}

    valid_conns = [c for c in spec.connections if c.source in component_ids and c.target in component_ids]
    dropped_count = len(spec.connections) - len(valid_conns)
    if dropped_count:
        log.warning("Removed %d orphan connections (invalid component references)", dropped_count)

    connected_ids: set[str] = set()
    for c in valid_conns:
        connected_ids.add(c.source)
        connected_ids.add(c.target)

    isolated = [c for c in spec.components if c.id not in connected_ids]
    new_conns = list(valid_conns)

    if isolated and spec.components:
        tier_sorted = sorted(spec.components, key=lambda c: c.tier)
        for iso in isolated:
            candidate = None
            for comp in tier_sorted:
                if comp.id != iso.id and comp.id in connected_ids:
                    candidate = comp
                    if abs(comp.tier - iso.tier) <= 1:
                        break

            if candidate:
                if iso.tier <= candidate.tier:
                    src, tgt = iso.id, candidate.id
                else:
                    src, tgt = candidate.id, iso.id

                tgt_comp = id_to_comp.get(tgt)
                if tgt_comp and tgt_comp.service in DATABASE_SERVICES:
                    proto, port, label = "TCP", 5432, "TCP/5432"
                elif tgt_comp and tgt_comp.service in {"elasticache", "memorystore", "azure_cache"}:
                    proto, port, label = "TCP", 6379, "TCP/6379"
                else:
                    proto, port, label = "HTTPS", 443, "HTTPS/443"

                new_conns.append(Connection(source=src, target=tgt, label=label, protocol=proto, port=port))
                log.warning("Auto-connected isolated component %s -> %s", src, tgt)

    final_conns = []
    for conn in new_conns:
        if conn.protocol is None or conn.port is None:
            src_comp = id_to_comp.get(conn.source)
            tgt_comp = id_to_comp.get(conn.target)
            if tgt_comp and tgt_comp.service in DATABASE_SERVICES:
                conn = conn.model_copy(update={"protocol": "TCP", "port": 5432})
            elif tgt_comp and tgt_comp.service in {"elasticache", "memorystore", "azure_cache"}:
                conn = conn.model_copy(update={"protocol": "TCP", "port": 6379})
            elif src_comp and tgt_comp:
                if src_comp.tier <= 2:
                    conn = conn.model_copy(update={"protocol": "HTTPS", "port": 443})
        final_conns.append(conn)

    if final_conns != spec.connections or valid_conns != spec.connections:
        return spec.model_copy(update={"connections": final_conns})
    return spec


# Compliance frameworks that require encryption-at-rest and HA on data stores.
_HA_REQUIRING_FRAMEWORKS = {"hipaa", "pci-dss", "pci", "soc2", "gdpr", "fedramp", "hitrust", "iso27001"}
_ENCRYPTION_REQUIRING_FRAMEWORKS = {"hipaa", "pci-dss", "pci", "soc2", "gdpr", "fedramp", "hitrust", "iso27001"}

# Workload profiles that imply production-grade HA defaults. v1.4 makes these
# conditional rather than blanket-applied — sandbox/dev workloads don't get
# multi_az/count=2 forced on them.
_HA_PROFILES = {"medium", "large", "enterprise", "production", "prod"}
_NON_HA_PROFILES = {"sandbox", "dev", "development", "test", "demo", "poc"}


def _profile_requires_ha(spec: ArchSpec, constraints: Constraints | None) -> bool:
    """Return True when the spec/constraints imply production HA defaults."""
    profile = ""
    if spec.metadata and isinstance(spec.metadata, dict):
        profile = str(spec.metadata.get("workload_profile", "")).lower()
    if profile in _NON_HA_PROFILES:
        return False
    if profile in _HA_PROFILES:
        return True
    if constraints is None:
        # No signal either way — default to production posture (back-compat).
        return True
    # Compliance frameworks always pull in HA.
    if any(f.lower() in _HA_REQUIRING_FRAMEWORKS for f in constraints.compliance):
        return True
    if constraints.availability and constraints.availability >= 0.995:
        return True
    if constraints.throughput_rps and constraints.throughput_rps >= 1000:
        return True
    # If constraints exist but none of the production signals fire, treat as
    # non-production — caller asked for something modest.
    return True  # conservative default for back-compat


def _profile_requires_encryption(spec: ArchSpec, constraints: Constraints | None) -> bool:
    """Return True when defaults should force encryption=true on data stores."""
    profile = ""
    if spec.metadata and isinstance(spec.metadata, dict):
        profile = str(spec.metadata.get("workload_profile", "")).lower()
    if profile in _NON_HA_PROFILES:
        # Sandboxes get whatever the LLM picked — no forced encryption override.
        return False
    if constraints is None:
        return True  # back-compat default
    if any(f.lower() in _ENCRYPTION_REQUIRING_FRAMEWORKS for f in constraints.compliance):
        return True
    return True  # default true — better safe than encrypted-after-the-breach


def _post_validate(spec: ArchSpec, constraints: Constraints | None) -> ArchSpec:
    """Apply safe defaults and enforce constraint-specific controls.

    v1.4 change: defaults are conditional on workload profile + compliance.
    Sandbox/dev profiles get the LLM's chosen values without overrides; only
    production / compliance-bound workloads get encryption=true / multi_az=true /
    count=2 forced. Per audit finding #4 — over-aggressive default injection
    masked Stage 1 reasoning quality.
    """
    components = [c.model_copy(deep=True) for c in spec.components]
    changed = False
    multi_component = len(components) > 3

    needs_encryption = _profile_requires_encryption(spec, constraints)
    needs_ha = _profile_requires_ha(spec, constraints)

    for i, comp in enumerate(components):
        cfg = dict(comp.config)
        updated = False

        if comp.service in DATA_STORE_SERVICES:
            if needs_encryption and not cfg.get("encryption"):
                cfg["encryption"] = True
                updated = True
            if needs_ha and not cfg.get("backup"):
                cfg["backup"] = True
                updated = True

        if comp.service in DATABASE_SERVICES and multi_component and needs_ha:
            if not cfg.get("multi_az"):
                cfg["multi_az"] = True
                updated = True

        if comp.service in COMPUTE_SERVICES and needs_ha:
            if not cfg.get("auto_scaling"):
                cfg["auto_scaling"] = True
                updated = True

        provider = comp.provider or spec.provider
        defaults = DEFAULT_INSTANCE_TYPES.get(provider, DEFAULT_INSTANCE_TYPES["aws"])

        if comp.service in COMPUTE_SERVICES and "instance_type" not in cfg:
            cfg["instance_type"] = defaults["compute"]
            updated = True

        if comp.service in DATABASE_SERVICES and "instance_class" not in cfg:
            cfg["instance_class"] = defaults["database"]
            updated = True

        if comp.service in {"elasticache", "memorystore", "azure_cache"} and "node_type" not in cfg:
            cfg["node_type"] = defaults["cache"]
            updated = True

        if comp.service in DATABASE_SERVICES and "storage_gb" not in cfg:
            cfg["storage_gb"] = 100
            updated = True

        if comp.service in COMPUTE_SERVICES and "count" not in cfg and needs_ha:
            cfg["count"] = 2
            updated = True

        if updated:
            components[i] = comp.model_copy(update={"config": cfg})
            changed = True

    if constraints:
        if constraints.budget_monthly and spec.cost_estimate:
            total = spec.cost_estimate.monthly_total
            if total > constraints.budget_monthly:
                log.warning(
                    "Architecture cost $%.2f/mo exceeds budget limit of $%.2f/mo",
                    total,
                    constraints.budget_monthly,
                )

    if not changed:
        return spec

    return spec.model_copy(update={"components": components})


def _parse_arch_spec(data: dict, constraints: Constraints | None) -> ArchSpec:
    """Parse a JSON dict (from LLM output) into a validated ArchSpec."""
    components = [
        Component(
            id=c["id"],
            service=c.get("service") or c.get("type") or c["service_key"],
            provider=c.get("provider", data.get("provider", "aws")),
            label=c.get("label", c["id"]),
            description=c.get("description", ""),
            tier=int(c.get("tier", 2)),
            config=c.get("config", {}),
        )
        for c in data.get("components", [])
    ]

    # Normalize service keys.
    # v1.4 note: with the Stage 2 projector explicitly told which canonical
    # service keys to use, normalization should be a rare fallback. Each hit
    # logs a WARNING so we can track LLM drift and trim the table over time.
    normalized = []
    for comp in components:
        raw = comp.service
        if raw in SERVICE_NORMALIZATION:
            fixed = SERVICE_NORMALIZATION[raw]
            log.warning(
                "SERVICE_NORMALIZATION fallback triggered: '%s' -> '%s' (component: %s). "
                "Stage 2 projector should have emitted the canonical key directly.",
                raw,
                fixed,
                comp.id,
            )
            cfg = dict(comp.config)
            if raw in SERVICE_ENGINE_SUFFIXES:
                cfg.setdefault("engine", SERVICE_ENGINE_SUFFIXES[raw])
            comp = comp.model_copy(update={"service": fixed, "config": cfg})
        elif raw not in ALL_VALID_SERVICES:
            for prefix in ("aws_", "gcp_", "azure_", "google_"):
                if raw.startswith(prefix):
                    stripped = raw[len(prefix) :]
                    if stripped in ALL_VALID_SERVICES:
                        log.warning(
                            "Stripping prefix from service key '%s' -> '%s' (component: %s)", raw, stripped, comp.id
                        )
                        comp = comp.model_copy(update={"service": stripped})
                        break
        normalized.append(comp)
    components = normalized

    # Validate provider consistency
    validated = []
    for comp in components:
        provider = (comp.provider or data.get("provider", "aws")).lower()
        valid_for_provider = PROVIDER_SERVICES.get(provider, set())
        if comp.service not in valid_for_provider:
            equivalent = get_equivalent(comp.service, _infer_service_provider(comp.service), provider)
            if equivalent:
                log.warning(
                    "Provider mismatch: service '%s' not valid for %s, mapped to '%s'",
                    comp.service,
                    provider,
                    equivalent,
                )
                comp = comp.model_copy(update={"service": equivalent})
            else:
                log.warning("Service '%s' not in valid set for provider '%s' — keeping as-is", comp.service, provider)
        validated.append(comp)
    components = validated

    connections = []
    _VALID_KINDS = {"sync_request", "async_event", "stream", "replication", "batch"}
    for conn in data.get("connections", []):
        src = conn.get("source") or conn.get("from")
        tgt = conn.get("target") or conn.get("to")
        if not src or not tgt:
            log.warning("Skipping connection with missing source/target: %s", conn)
            continue
        # v1.4: parse Connection.kind. Coerce variants and drop invalid values
        # silently (back-compat with older specs that didn't have the field).
        raw_kind = conn.get("kind") or conn.get("type")
        kind: str | None = None
        if raw_kind:
            normalized_kind = str(raw_kind).lower().strip().replace("-", "_").replace(" ", "_")
            if normalized_kind in _VALID_KINDS:
                kind = normalized_kind
            elif normalized_kind in {"sync", "request", "rpc", "http"}:
                kind = "sync_request"
            elif normalized_kind in {"async", "event", "queue", "pubsub"}:
                kind = "async_event"
        connections.append(
            Connection(
                source=src,
                target=tgt,
                label=conn.get("label", ""),
                protocol=conn.get("protocol"),
                port=conn.get("port"),
                kind=kind,
            )
        )

    # v1.4: parse boundaries (VPC/subnet/SG) when present.
    boundaries: list[Boundary] = []
    component_ids_for_boundaries = {c.id for c in components}
    for b in data.get("boundaries", []) or []:
        bid = b.get("id")
        bkind = b.get("kind")
        if not bid or not bkind:
            log.warning("Skipping boundary with missing id/kind: %s", b)
            continue
        comp_ids = [cid for cid in (b.get("component_ids") or []) if cid in component_ids_for_boundaries]
        try:
            boundaries.append(
                Boundary(
                    id=bid,
                    kind=str(bkind).lower(),
                    label=b.get("label", ""),
                    parent=b.get("parent"),
                    component_ids=comp_ids,
                    config=b.get("config", {}),
                )
            )
        except ValueError as exc:
            log.warning("Skipping invalid boundary %s: %s", bid, exc)

    metadata = {}
    if "rationale" in data:
        metadata["rationale"] = data["rationale"]
    if "suggestions" in data:
        metadata["suggestions"] = data["suggestions"]
    if "workload_profile" in data:
        metadata["workload_profile"] = data["workload_profile"]

    # Filter out connections with invalid references before constructing ArchSpec
    component_ids = {c.id for c in components}
    valid_connections = [c for c in connections if c.source in component_ids and c.target in component_ids]
    if len(valid_connections) < len(connections):
        log.warning("Removed %d orphan connections during parsing", len(connections) - len(valid_connections))

    spec = ArchSpec(
        name=data.get("name", "Architecture"),
        provider=data.get("provider", "aws"),
        region=data.get("region", "us-east-1"),
        constraints=constraints,
        components=components,
        connections=valid_connections,
        boundaries=boundaries,
        metadata=metadata,
    )
    spec = _enforce_connections(spec)
    return _post_validate(spec, constraints)


def _infer_service_provider(service: str) -> str:
    for provider, services in PROVIDER_SERVICES.items():
        if service in services:
            return provider
    return "aws"
