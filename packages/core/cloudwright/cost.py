"""Cost engine — prices each component in an ArchSpec from catalog data."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from cloudwright.catalog import _PRICING_MULTIPLIERS, Catalog
from cloudwright.catalog.formula import PRICING_FORMULAS, default_managed_price
from cloudwright.providers import get_equivalent
from cloudwright.registry import ServiceRegistry, get_registry
from cloudwright.spec import Alternative, ArchSpec, Component, ComponentCost, CostEstimate

log = logging.getLogger(__name__)

_CONTAINER_ORCHESTRATION = {"eks", "gke", "aks", "ecs", "databricks_cluster"}

# Per-provider internet egress rates ($/GB) by transfer type
_EGRESS_RATES = {
    "aws": {"same_region": 0.01, "cross_region": 0.02, "internet": 0.09},
    "gcp": {"same_region": 0.01, "cross_region": 0.08, "internet": 0.12},
    "azure": {"same_region": 0.01, "cross_region": 0.02, "internet": 0.087},
    "databricks": {"same_region": 0.01, "cross_region": 0.02, "internet": 0.09},
    "cross_provider": 0.09,
}

# Service-level egress overrides for intra-cloud transfer (lower than internet egress)
# These apply when source and target are on the same provider
_SERVICE_EGRESS_OVERRIDES = {
    "cloudfront": 0.085,
    "cloud_cdn": 0.08,
    "azure_cdn": 0.087,
    "alb": 0.01,
    "nlb": 0.01,
    "app_gateway": 0.01,
    # Object storage intra-cloud transfer is cheaper than internet egress
    "s3": 0.01,
    "cloud_storage": 0.01,
    "blob_storage": 0.01,
}
_DEFAULT_EGRESS_RATE = 0.09

# ---------------------------------------------------------------------------
# Workload profiles — realistic sizing defaults per environment tier
# ---------------------------------------------------------------------------

# Config overrides applied to components when a workload profile is active.
# Only fills in missing config keys; never overwrites explicit values.
_PROFILE_DEFAULTS: dict[str, dict[str, dict[str, Any]]] = {
    "small": {
        # Serverless
        "lambda": {"monthly_requests": 5_000_000, "avg_duration_ms": 300, "memory_mb": 512},
        "cloud_functions": {"monthly_requests": 5_000_000, "avg_duration_ms": 300, "memory_mb": 512},
        "azure_functions": {"monthly_requests": 5_000_000, "avg_duration_ms": 300, "memory_mb": 512},
        # Databases
        "rds": {"storage_gb": 50},
        "aurora": {"storage_gb": 50},
        "cloud_sql": {"storage_gb": 50},
        "azure_sql": {"storage_gb": 50},
        "dynamodb": {"monthly_requests": 5_000_000},
        # Storage
        "s3": {"storage_gb": 100},
        "cloud_storage": {"storage_gb": 100},
        "blob_storage": {"storage_gb": 100},
        # CDN
        "cloudfront": {"estimated_gb": 200},
        "cloud_cdn": {"estimated_gb": 200},
        "azure_cdn": {"estimated_gb": 200},
        # Analytics
        "bigquery": {"monthly_query_tb": 2, "storage_gb": 200},
        "redshift": {"num_nodes": 2, "storage_gb": 500},
        "synapse": {"num_nodes": 2, "storage_gb": 500},
    },
    "medium": {
        # Serverless
        "lambda": {"monthly_requests": 50_000_000, "avg_duration_ms": 400, "memory_mb": 1024},
        "cloud_functions": {"monthly_requests": 50_000_000, "avg_duration_ms": 400, "memory_mb": 1024},
        "azure_functions": {"monthly_requests": 50_000_000, "avg_duration_ms": 400, "memory_mb": 1024},
        # Databases
        "rds": {"storage_gb": 200, "multi_az": True},
        "aurora": {"storage_gb": 200, "multi_az": True},
        "cloud_sql": {"storage_gb": 200},
        "azure_sql": {"storage_gb": 200},
        "dynamodb": {"monthly_requests": 50_000_000},
        # Storage
        "s3": {"storage_gb": 500},
        "cloud_storage": {"storage_gb": 500},
        "blob_storage": {"storage_gb": 500},
        # Compute
        "ec2": {"count": 3},
        "compute_engine": {"count": 3},
        "virtual_machines": {"count": 3},
        # Container orchestration
        "eks": {"node_count": 6},
        "gke": {"node_count": 6},
        "aks": {"node_count": 6},
        "ecs": {"count": 4},
        # CDN
        "cloudfront": {"estimated_gb": 1000},
        "cloud_cdn": {"estimated_gb": 1000},
        "azure_cdn": {"estimated_gb": 1000},
        # Analytics
        "bigquery": {"monthly_query_tb": 10, "storage_gb": 1000},
        "redshift": {"num_nodes": 4, "storage_gb": 2000},
        "synapse": {"num_nodes": 4, "storage_gb": 2000},
        # Cache
        "elasticache": {"memory_gb": 13},
        "memorystore": {"memory_gb": 13},
        "azure_cache": {"memory_gb": 13},
    },
    "large": {
        # Serverless
        "lambda": {"monthly_requests": 500_000_000, "avg_duration_ms": 500, "memory_mb": 2048},
        "cloud_functions": {"monthly_requests": 500_000_000, "avg_duration_ms": 500, "memory_mb": 2048},
        "azure_functions": {"monthly_requests": 500_000_000, "avg_duration_ms": 500, "memory_mb": 2048},
        # Databases
        "rds": {"storage_gb": 1000, "multi_az": True},
        "aurora": {"storage_gb": 1000, "multi_az": True},
        "cloud_sql": {"storage_gb": 1000},
        "azure_sql": {"storage_gb": 1000},
        "dynamodb": {"monthly_requests": 200_000_000},
        # Storage
        "s3": {"storage_gb": 5000},
        "cloud_storage": {"storage_gb": 5000},
        "blob_storage": {"storage_gb": 5000},
        # Compute
        "ec2": {"count": 6},
        "compute_engine": {"count": 6},
        "virtual_machines": {"count": 6},
        # Container orchestration
        "eks": {"node_count": 15},
        "gke": {"node_count": 15},
        "aks": {"node_count": 15},
        "ecs": {"count": 10},
        # CDN
        "cloudfront": {"estimated_gb": 5000},
        "cloud_cdn": {"estimated_gb": 5000},
        "azure_cdn": {"estimated_gb": 5000},
        # Analytics
        "bigquery": {"monthly_query_tb": 50, "storage_gb": 5000},
        "redshift": {"num_nodes": 8, "storage_gb": 10000},
        "synapse": {"num_nodes": 8, "storage_gb": 10000},
        # Cache
        "elasticache": {"memory_gb": 52},
        "memorystore": {"memory_gb": 52},
        "azure_cache": {"memory_gb": 52},
    },
    "enterprise": {
        # Serverless
        "lambda": {"monthly_requests": 2_000_000_000, "avg_duration_ms": 600, "memory_mb": 3072},
        "cloud_functions": {"monthly_requests": 2_000_000_000, "avg_duration_ms": 600, "memory_mb": 3072},
        "azure_functions": {"monthly_requests": 2_000_000_000, "avg_duration_ms": 600, "memory_mb": 3072},
        # Databases
        "rds": {"storage_gb": 5000, "multi_az": True},
        "aurora": {"storage_gb": 5000, "multi_az": True},
        "cloud_sql": {"storage_gb": 5000},
        "azure_sql": {"storage_gb": 5000},
        "dynamodb": {"monthly_requests": 1_000_000_000},
        # Storage
        "s3": {"storage_gb": 50000},
        "cloud_storage": {"storage_gb": 50000},
        "blob_storage": {"storage_gb": 50000},
        # Compute
        "ec2": {"count": 20},
        "compute_engine": {"count": 20},
        "virtual_machines": {"count": 20},
        # Container orchestration
        "eks": {"node_count": 50},
        "gke": {"node_count": 50},
        "aks": {"node_count": 50},
        "ecs": {"count": 30},
        # CDN
        "cloudfront": {"estimated_gb": 50000},
        "cloud_cdn": {"estimated_gb": 50000},
        "azure_cdn": {"estimated_gb": 50000},
        # Analytics
        "bigquery": {"monthly_query_tb": 200, "storage_gb": 50000},
        "redshift": {"num_nodes": 16, "storage_gb": 50000},
        "synapse": {"num_nodes": 16, "storage_gb": 50000},
        # Cache
        "elasticache": {"memory_gb": 200},
        "memorystore": {"memory_gb": 200},
        "azure_cache": {"memory_gb": 200},
    },
}

# Default data transfer (GB/month) per connection when a workload profile is active
# but the connection has no explicit estimated_monthly_gb.
_PROFILE_TRANSFER_DEFAULTS: dict[str, float] = {
    "small": 50.0,
    "medium": 200.0,
    "large": 1000.0,
    "enterprise": 5000.0,
}

VALID_WORKLOAD_PROFILES = set(_PROFILE_DEFAULTS.keys())


def _apply_profile(comp: Component, profile: str) -> Component:
    """Return a copy of the component with profile defaults merged into its config.

    Profile defaults only fill in missing keys — explicit config always wins.
    """
    svc_defaults = _PROFILE_DEFAULTS.get(profile, {}).get(comp.service)
    if not svc_defaults:
        return comp
    merged = dict(svc_defaults)
    merged.update(comp.config or {})
    return comp.model_copy(update={"config": merged})


class CostEngine:
    def __init__(self, catalog: Catalog | None = None, registry: ServiceRegistry | None = None):
        self.catalog = catalog or Catalog()
        self.registry = registry or get_registry()

    def estimate(
        self,
        spec: ArchSpec,
        pricing_tier: str = "on_demand",
        workload_profile: str | None = None,
    ) -> CostEstimate:
        """Price every component in an ArchSpec and return a full breakdown.

        Args:
            spec: The architecture specification to price.
            pricing_tier: Pricing model — on_demand, reserved_1yr, reserved_3yr, spot.
            workload_profile: Optional sizing profile — small, medium, large, enterprise.
                When set, applies realistic defaults for request volumes, storage sizes,
                node counts, and data transfer that match production workloads.
        """
        breakdown: list[ComponentCost] = []

        for comp in spec.components:
            effective = _apply_profile(comp, workload_profile) if workload_profile else comp
            monthly = self._price_component(effective, spec.provider, spec.region, pricing_tier)
            hourly = round(monthly / 730, 4) if monthly > 0 else None
            notes = self._cost_notes(effective)
            breakdown.append(
                ComponentCost(
                    component_id=comp.id,
                    service=comp.service,
                    monthly=monthly,
                    hourly=hourly,
                    notes=notes,
                )
            )

        component_total = round(sum(c.monthly for c in breakdown), 2)
        data_transfer = self._estimate_data_transfer(spec, workload_profile=workload_profile)
        total = round(component_total + data_transfer, 2)

        return CostEstimate(
            monthly_total=total,
            breakdown=breakdown,
            data_transfer_monthly=data_transfer,
            currency="USD",
            as_of=date.today().isoformat(),
        )

    def price(
        self,
        spec: ArchSpec,
        pricing_tier: str = "on_demand",
        workload_profile: str | None = None,
    ) -> ArchSpec:
        """Estimate costs and return a new ArchSpec with cost_estimate attached."""
        estimate = self.estimate(spec, pricing_tier=pricing_tier, workload_profile=workload_profile)
        return spec.model_copy(update={"cost_estimate": estimate})

    def compare_providers(
        self,
        spec: ArchSpec,
        providers: list[str],
        workload_profile: str | None = None,
    ) -> list[Alternative]:
        """Price the architecture across multiple cloud providers."""
        alternatives: list[Alternative] = []

        for target_provider in providers:
            if target_provider == spec.provider:
                continue

            mapped_components: list[Component] = []
            differences: list[str] = []

            for comp in spec.components:
                equiv_service = get_equivalent(comp.service, comp.provider, target_provider)
                if equiv_service:
                    new_config = dict(comp.config) if comp.config else {}
                    new_config = self._map_instance_config(new_config, comp.provider, target_provider)
                    new_comp = comp.model_copy(
                        update={
                            "service": equiv_service,
                            "provider": target_provider,
                            "config": new_config,
                        }
                    )
                    mapped_components.append(new_comp)
                    if equiv_service != comp.service:
                        differences.append(f"{equiv_service} instead of {comp.service}")
                else:
                    mapped_components.append(comp.model_copy(update={"provider": target_provider}))
                    differences.append(f"No direct equivalent for {comp.service}")

            alt_spec = spec.model_copy(
                update={
                    "provider": target_provider,
                    "components": mapped_components,
                }
            )
            alt_estimate = self.estimate(alt_spec, workload_profile=workload_profile)

            alternatives.append(
                Alternative(
                    provider=target_provider,
                    monthly_total=alt_estimate.monthly_total,
                    spec=alt_spec,
                    key_differences=differences[:5],
                )
            )

        return alternatives

    def _map_instance_config(self, config: dict, from_provider: str, to_provider: str) -> dict:
        """Map instance type names across clouds using catalog equivalences."""
        instance_key = None
        instance_name = None
        for key in ("instance_type", "machine_type", "vm_size", "instance_class", "node_type"):
            if key in config:
                instance_key = key
                instance_name = config[key]
                break

        if not instance_name:
            return config

        try:
            with self.catalog._connect() as conn:
                src_id = f"{from_provider}:{instance_name}"
                row = conn.execute(
                    """SELECT CASE WHEN e.instance_a_id = ? THEN e.instance_b_id ELSE e.instance_a_id END as equiv_id
                    FROM equivalences e
                    WHERE (e.instance_a_id = ? OR e.instance_b_id = ?)
                    AND (e.instance_a_id LIKE ? OR e.instance_b_id LIKE ?)""",
                    (src_id, src_id, src_id, f"{to_provider}:%", f"{to_provider}:%"),
                ).fetchone()
                if row:
                    equiv_name = row["equiv_id"].split(":", 1)[1] if ":" in row["equiv_id"] else row["equiv_id"]
                    target_key = instance_key
                    if to_provider == "gcp":
                        target_key = "machine_type" if instance_key == "instance_type" else instance_key
                    elif to_provider == "azure":
                        target_key = "vm_size" if instance_key == "instance_type" else instance_key
                    new_config = dict(config)
                    if target_key != instance_key:
                        del new_config[instance_key]
                    new_config[target_key] = equiv_name
                    return new_config
        except (KeyError, TypeError, AttributeError) as exc:
            log.debug("Instance config mapping failed for %s->%s: %s", from_provider, to_provider, exc)

        return config

    def _price_component(
        self, comp: Component, default_provider: str, region: str, pricing_tier: str = "on_demand"
    ) -> float:
        """Get monthly cost for a single component using 3-tier resolution + multipliers."""
        provider = comp.provider or default_provider
        config = comp.config or {}
        base: float | None = None
        from_catalog = False

        # Tier 1: catalog DB (has instance-level pricing and pricing_tier support)
        base = self.catalog.get_service_pricing(comp.service, provider, config, pricing_tier=pricing_tier)
        if base is not None:
            from_catalog = True

        if base is None:
            # Tier 2: registry formula dispatch
            svc_def = self.registry.get(provider, comp.service)
            if svc_def:
                formula_fn = PRICING_FORMULAS.get(svc_def.pricing_formula)
                if formula_fn:
                    merged_config = dict(svc_def.default_config)
                    merged_config.update(config)
                    result = formula_fn(merged_config)
                    if result is not None and result > 0:
                        multiplier = _PRICING_MULTIPLIERS.get(pricing_tier, 1.0)
                        base = result * multiplier

        if base is None:
            # Tier 3: static fallback table
            base = default_managed_price(comp.service, config)
            multiplier = _PRICING_MULTIPLIERS.get(pricing_tier, 1.0)
            base = base * multiplier

        # Post-resolution multipliers (only for non-catalog tiers — catalog handles these internally)
        if not from_catalog and config.get("multi_az"):
            base *= 2.0

        if comp.service in _CONTAINER_ORCHESTRATION:
            has_explicit_count = (
                config.get("count", 1) > 1 or config.get("node_count", 0) > 1 or config.get("desired_count", 0) > 1
            )
            if not has_explicit_count:
                base *= 3

        return round(base, 2)

    def _estimate_data_transfer(self, spec: ArchSpec, workload_profile: str | None = None) -> float:
        """Estimate monthly data transfer (egress) costs from connections."""
        total = 0.0
        component_map = {c.id: c for c in spec.components}
        profile_default_gb = _PROFILE_TRANSFER_DEFAULTS.get(workload_profile or "", 0.0)

        for conn in spec.connections:
            gb = conn.estimated_monthly_gb
            if not gb and profile_default_gb:
                gb = profile_default_gb
            if not gb:
                continue
            source = component_map.get(conn.source)
            if not source:
                continue
            target = component_map.get(conn.target)

            src_provider = source.provider or spec.provider
            tgt_provider = target.provider if target else src_provider
            cross_provider = tgt_provider != src_provider

            if cross_provider:
                # Cross-cloud egress always uses the flat cross-provider rate
                rate = _EGRESS_RATES["cross_provider"]
            elif source.service in _SERVICE_EGRESS_OVERRIDES:
                # CDN/LB/object-storage intra-cloud have negotiated or cheaper rates
                rate = _SERVICE_EGRESS_OVERRIDES[source.service]
            else:
                provider_rates = _EGRESS_RATES.get(src_provider, {})
                rate = provider_rates.get("internet", _DEFAULT_EGRESS_RATE)

            total += gb * rate

        return round(total, 2)

    def _cost_notes(self, comp: Component) -> str:
        """Generate human-readable notes for a cost line item."""
        config = comp.config or {}
        parts: list[str] = []

        if "instance_type" in config:
            parts.append(config["instance_type"])
        elif "instance_class" in config:
            parts.append(config["instance_class"])
        elif "node_type" in config:
            parts.append(config["node_type"])
        elif "tier" in config:
            parts.append(config["tier"])
        elif "vm_size" in config:
            parts.append(config["vm_size"])

        if config.get("count", 1) > 1:
            parts.append(f"{config['count']}x")

        if config.get("multi_az"):
            parts.append("Multi-AZ")

        if config.get("storage_gb"):
            parts.append(f"{config['storage_gb']}GB storage")

        if config.get("estimated_gb"):
            parts.append(f"{config['estimated_gb']}GB egress")

        if config.get("engine"):
            parts.append(config["engine"])

        return ", ".join(parts) if parts else ""
