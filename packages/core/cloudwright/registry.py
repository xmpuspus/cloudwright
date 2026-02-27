"""Service registry — loads YAML category definitions for all cloud services.

Provides provider-agnostic service lookup and cross-cloud equivalence mapping.
Registry data lives in data/registry/*.yaml; one file per service category.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REGISTRY_DIR = Path(__file__).parent / "data" / "registry"


class ServiceDef:
    """A single cloud service definition."""

    __slots__ = ("service_key", "provider", "category", "name", "description", "pricing_formula", "default_config")

    def __init__(
        self,
        service_key: str,
        provider: str,
        category: str,
        name: str,
        description: str,
        pricing_formula: str,
        default_config: dict[str, Any],
    ):
        self.service_key = service_key
        self.provider = provider
        self.category = category
        self.name = name
        self.description = description
        self.pricing_formula = pricing_formula
        self.default_config = default_config

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_key": self.service_key,
            "provider": self.provider,
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "pricing_formula": self.pricing_formula,
            "default_config": self.default_config,
        }


class ServiceRegistry:
    """Registry of all cloud services loaded from YAML category files.

    Provides fast O(1) lookup by (provider, service_key) and cross-cloud
    equivalence resolution. Loaded once from disk; thread-safe after init.
    """

    def __init__(self, registry_dir: str | Path | None = None):
        self._dir = Path(registry_dir) if registry_dir else _REGISTRY_DIR
        # (provider, service_key) -> ServiceDef
        self._services: dict[tuple[str, str], ServiceDef] = {}
        # category -> list[ServiceDef]
        self._by_category: dict[str, list[ServiceDef]] = {}
        # List of equivalence groups: each is dict[provider_name -> service_key]
        self._equivalences: list[dict[str, str]] = []
        # service_key -> {feature_name -> {provider -> bool/value}}
        self._feature_parity: dict[str, dict[str, dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        for yaml_path in sorted(self._dir.glob("*.yaml")):
            data = yaml.safe_load(yaml_path.read_text())
            category = data["category"]
            services_block = data.get("services", {})

            for provider, provider_services in services_block.items():
                if not isinstance(provider_services, dict):
                    continue
                for service_key, svc in provider_services.items():
                    defn = ServiceDef(
                        service_key=service_key,
                        provider=provider,
                        category=category,
                        name=svc.get("name", service_key),
                        description=svc.get("description", ""),
                        pricing_formula=svc.get("pricing_formula", "per_hour"),
                        default_config=svc.get("default_config") or {},
                    )
                    self._services[(provider, service_key)] = defn
                    self._by_category.setdefault(category, []).append(defn)

            for equiv in data.get("equivalences", []):
                self._equivalences.append(equiv)

            for fp_group in data.get("feature_parity", []):
                equiv_keys = fp_group.get("equivalence", [])
                features = fp_group.get("features", {})
                for feature_name, provider_support in features.items():
                    for svc_key in equiv_keys:
                        for provider in ("aws", "gcp", "azure"):
                            if (provider, svc_key) in self._services:
                                val = provider_support.get(provider)
                                if val is not None:
                                    self._feature_parity.setdefault(svc_key, {})[feature_name] = provider_support
                                    break

    def get(self, provider: str, service_key: str) -> ServiceDef | None:
        """Return service definition or None if not registered."""
        return self._services.get((provider, service_key))

    def get_category(self, category: str) -> list[ServiceDef]:
        """All services in a category across all providers."""
        return list(self._by_category.get(category, []))

    def list_categories(self) -> list[str]:
        """Sorted list of all registered categories."""
        return sorted(self._by_category.keys())

    def list_providers(self) -> list[str]:
        """Sorted list of all providers with registered services."""
        providers = {provider for provider, _ in self._services}
        return sorted(providers)

    def list_services(self, provider: str) -> list[ServiceDef]:
        """All services for a specific provider."""
        return [svc for (p, _), svc in self._services.items() if p == provider]

    def get_equivalent(self, service_key: str, from_provider: str, to_provider: str) -> str | None:
        """Return the equivalent service key in another provider, or None."""
        if from_provider == to_provider:
            return service_key

        for equiv in self._equivalences:
            if equiv.get(from_provider) == service_key and to_provider in equiv:
                return equiv[to_provider]

        return None

    def get_pricing_formula(self, provider: str, service_key: str) -> str:
        """Return the pricing formula name for a service, defaulting to per_hour."""
        svc = self.get(provider, service_key)
        return svc.pricing_formula if svc else "per_hour"

    def get_default_config(self, provider: str, service_key: str) -> dict[str, Any]:
        """Return the default config dict for a service."""
        svc = self.get(provider, service_key)
        return dict(svc.default_config) if svc else {}

    def all_equivalences(self) -> list[dict[str, str]]:
        """All equivalence groups (list of {provider: service_key} dicts)."""
        return list(self._equivalences)

    def get_feature_parity(self, service_key: str) -> dict[str, dict[str, Any]]:
        """Return feature parity matrix for a service.

        Returns {feature_name: {provider: support_value}} where support_value
        is typically bool but can be int (e.g. max_memory_gb).
        """
        return dict(self._feature_parity.get(service_key, {}))

    def compare_features(self, service_a: str, service_b: str) -> list[dict[str, Any]]:
        """Compare features between two equivalent services.

        Returns a list of dicts with feature name and support per service.
        """
        parity_a = self._feature_parity.get(service_a, {})
        parity_b = self._feature_parity.get(service_b, {})
        all_features = set(parity_a) | set(parity_b)

        result = []
        for feature in sorted(all_features):
            entry: dict[str, Any] = {"feature": feature}
            if feature in parity_a:
                for provider, val in parity_a[feature].items():
                    entry[f"{service_a}_{provider}"] = val
            if feature in parity_b:
                for provider, val in parity_b[feature].items():
                    entry[f"{service_b}_{provider}"] = val
            result.append(entry)
        return result

    def feature_gaps(self, service_key: str, provider: str) -> list[str]:
        """List features NOT supported by a specific provider for a service.

        Useful for migration planning: "what will I lose moving RDS to Cloud SQL?"
        """
        parity = self._feature_parity.get(service_key, {})
        gaps = []
        for feature, support in parity.items():
            val = support.get(provider)
            if val is False or val == 0:
                gaps.append(feature)
        return gaps

    def stats(self) -> dict[str, Any]:
        """Summary counts for the loaded registry."""
        return {
            "total_services": len(self._services),
            "categories": len(self._by_category),
            "providers": len(self.list_providers()),
            "equivalences": len(self._equivalences),
            "feature_parity_services": len(self._feature_parity),
        }


# Module-level singleton — loaded lazily on first access
_registry: ServiceRegistry | None = None


def get_registry() -> ServiceRegistry:
    """Return the shared registry singleton, loading from disk if needed."""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry


def reload_registry(registry_dir: str | Path | None = None) -> ServiceRegistry:
    """Force-reload the registry (useful in tests or after YAML changes)."""
    global _registry
    _registry = ServiceRegistry(registry_dir)
    return _registry
