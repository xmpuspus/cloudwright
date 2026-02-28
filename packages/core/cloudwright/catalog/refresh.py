"""Catalog refresh pipeline — pull live pricing from provider APIs into SQLite."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.adapters import PricingAdapter

logger = logging.getLogger(__name__)

_ALL_PROVIDERS = ("aws", "gcp", "azure")

# provider -> default region for pricing fetch
_DEFAULT_REGIONS: dict[str, str] = {
    "aws": "us-east-1",
    "gcp": "us-central1",
    "azure": "eastus",
}


@dataclass
class RefreshResult:
    provider: str
    category: str = ""
    instances_fetched: int = 0
    managed_services_fetched: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False


@dataclass
class RefreshSummary:
    results: list[RefreshResult] = field(default_factory=list)

    @property
    def total_fetched(self) -> int:
        return sum(r.instances_fetched + r.managed_services_fetched for r in self.results)

    @property
    def total_errors(self) -> int:
        return sum(len(r.errors) for r in self.results)


def _load_adapter(provider: str) -> PricingAdapter:
    """Lazily import and instantiate the adapter for a provider."""
    if provider == "aws":
        from cloudwright.adapters.aws import AWSPricingAdapter

        return AWSPricingAdapter()
    elif provider == "gcp":
        from cloudwright.adapters.gcp import GCPPricingAdapter

        return GCPPricingAdapter()
    elif provider == "azure":
        from cloudwright.adapters.azure import AzurePricingAdapter

        return AzurePricingAdapter()
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _refresh_provider(
    adapter: PricingAdapter,
    region: str,
    category: str | None,
    dry_run: bool,
    _db_path=None,
) -> RefreshResult:
    """Fetch pricing for one provider and optionally upsert into catalog."""
    from cloudwright.catalog.store import REGION_MAP, Catalog

    provider = adapter.provider
    result = RefreshResult(provider=provider, category=category or "all", dry_run=dry_run)

    # Fetch instance pricing (skip if category is set and not "compute")
    if category is None or category == "compute":
        try:
            instances = list(adapter.fetch_instance_pricing(region))
            result.instances_fetched = len(instances)
            logger.info("Fetched %d instance prices for %s/%s", len(instances), provider, region)

            if not dry_run and instances:
                catalog = Catalog(_db_path)
                with catalog._connect() as conn:
                    # Upsert provider + region
                    conn.execute(
                        "INSERT OR IGNORE INTO providers (id, name) VALUES (?, ?)",
                        (provider, provider.upper()),
                    )
                    region_normalized = "us_east"
                    region_name = region
                    provider_regions = REGION_MAP.get(provider, {})
                    if region in provider_regions:
                        region_normalized, region_name = provider_regions[region]
                    region_id = f"{provider}:{region}"
                    conn.execute(
                        "INSERT OR IGNORE INTO regions (id, provider_id, code, name, normalized) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (region_id, provider, region, region_name, region_normalized),
                    )

                    for inst in instances:
                        inst_id = f"{provider}:{inst.instance_type}"
                        conn.execute(
                            "INSERT OR REPLACE INTO instance_types "
                            "(id, provider_id, name, vcpus, memory_gb, storage_desc, "
                            "network_bandwidth, arch) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                inst_id,
                                provider,
                                inst.instance_type,
                                inst.vcpus,
                                inst.memory_gb,
                                inst.storage_desc,
                                inst.network_bandwidth,
                                "x86_64",
                            ),
                        )
                        conn.execute(
                            "INSERT OR REPLACE INTO pricing "
                            "(instance_type_id, region_id, os, price_per_hour, price_type) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (inst_id, region_id, inst.os, inst.price_per_hour, inst.price_type),
                        )

                    conn.execute(
                        "INSERT OR REPLACE INTO catalog_metadata (key, value, updated_at) VALUES (?, ?, ?)",
                        (
                            f"refresh:{provider}:instances",
                            str(result.instances_fetched),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
        except Exception as exc:
            msg = f"{provider} instance pricing: {exc}"
            logger.warning(msg)
            result.errors.append(msg)

    # Fetch managed service pricing
    if category is None or category != "compute":
        try:
            services = adapter.supported_managed_services()
            if category and category != "compute":
                # Filter to matching services if a category hint was given
                services = [s for s in services if category in s]
                if not services:
                    services = adapter.supported_managed_services()

            managed_count = 0
            for svc in services:
                try:
                    tiers = adapter.fetch_managed_service_pricing(svc, region)
                    managed_count += len(tiers)

                    if not dry_run and tiers:
                        catalog = Catalog(_db_path)
                        with catalog._connect() as conn:
                            for tier in tiers:
                                tier_id = f"{provider}:{svc}:{tier.tier_name}"
                                conn.execute(
                                    "INSERT OR REPLACE INTO managed_services "
                                    "(id, provider_id, service, tier_name, price_per_hour, "
                                    "price_per_month, vcpus, memory_gb, notes) "
                                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    (
                                        tier_id,
                                        provider,
                                        svc,
                                        tier.tier_name,
                                        tier.price_per_hour,
                                        tier.price_per_month,
                                        tier.vcpus,
                                        tier.memory_gb,
                                        tier.description,
                                    ),
                                )
                except Exception as exc:
                    msg = f"{provider}/{svc}: {exc}"
                    logger.warning(msg)
                    result.errors.append(msg)

            result.managed_services_fetched = managed_count
            logger.info(
                "Fetched %d managed service tiers for %s/%s",
                managed_count,
                provider,
                region,
            )

            if not dry_run and managed_count > 0:
                catalog = Catalog(_db_path)
                with catalog._connect() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO catalog_metadata (key, value, updated_at) VALUES (?, ?, ?)",
                        (
                            f"refresh:{provider}:managed",
                            str(managed_count),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
        except Exception as exc:
            msg = f"{provider} managed services: {exc}"
            logger.warning(msg)
            result.errors.append(msg)

    return result


def refresh_catalog(
    provider: str | None = None,
    category: str | None = None,
    region: str | None = None,
    dry_run: bool = False,
    _db_path=None,
) -> RefreshSummary:
    """Orchestrate pricing refresh from provider adapters.

    Args:
        provider: Restrict to a single provider ("aws", "gcp", "azure").
                  None means refresh all.
        category: Filter to a category like "compute" or a service name.
        region: Override the default region for pricing lookups.
        dry_run: If True, fetch but don't write to the catalog DB.

    Returns:
        RefreshSummary with per-provider results.
    """
    summary = RefreshSummary()
    providers = [provider] if provider else list(_ALL_PROVIDERS)

    for p in providers:
        try:
            adapter = _load_adapter(p)
        except Exception as exc:
            result = RefreshResult(provider=p, errors=[f"Failed to load adapter: {exc}"])
            summary.results.append(result)
            continue

        r = region or _DEFAULT_REGIONS.get(p, "us-east-1")
        result = _refresh_provider(adapter, r, category, dry_run, _db_path)
        summary.results.append(result)

    return summary
