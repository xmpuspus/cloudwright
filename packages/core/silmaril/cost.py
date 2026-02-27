"""Cost engine — prices each component in an ArchSpec from catalog data."""

from __future__ import annotations

from datetime import date

from silmaril.catalog import Catalog
from silmaril.providers import get_equivalent
from silmaril.spec import Alternative, ArchSpec, Component, ComponentCost, CostEstimate


class CostEngine:
    def __init__(self, catalog: Catalog | None = None):
        self.catalog = catalog or Catalog()

    def estimate(self, spec: ArchSpec) -> CostEstimate:
        """Price every component in an ArchSpec and return a full breakdown."""
        breakdown: list[ComponentCost] = []

        for comp in spec.components:
            monthly = self._price_component(comp, spec.provider, spec.region)
            hourly = round(monthly / 730, 4) if monthly > 0 else None
            notes = self._cost_notes(comp)
            breakdown.append(
                ComponentCost(
                    component_id=comp.id,
                    service=comp.service,
                    monthly=monthly,
                    hourly=hourly,
                    notes=notes,
                )
            )

        total = round(sum(c.monthly for c in breakdown), 2)
        return CostEstimate(
            monthly_total=total,
            breakdown=breakdown,
            currency="USD",
            as_of=date.today().isoformat(),
        )

    def compare_providers(self, spec: ArchSpec, providers: list[str]) -> list[Alternative]:
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
                    # Map instance types across clouds using equivalences
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

            # Build alternative spec and price it
            alt_spec = spec.model_copy(
                update={
                    "provider": target_provider,
                    "components": mapped_components,
                }
            )
            alt_estimate = self.estimate(alt_spec)

            alternatives.append(
                Alternative(
                    provider=target_provider,
                    monthly_total=alt_estimate.monthly_total,
                    spec=alt_spec,
                    key_differences=differences[:5],  # top 5
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

        # Look up equivalence in catalog
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
                    # Use appropriate config key for the target provider
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
        except Exception:
            pass

        return config

    def _price_component(self, comp: Component, default_provider: str, region: str) -> float:
        """Get monthly cost for a single component."""
        provider = comp.provider or default_provider
        config = comp.config or {}

        price = self.catalog.get_service_pricing(comp.service, provider, config)
        if price is not None:
            return round(price, 2)

        # Fallback: use default pricing
        from silmaril.catalog import _default_managed_price

        return round(_default_managed_price(comp.service, config), 2)

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
