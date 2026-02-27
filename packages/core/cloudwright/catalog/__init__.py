"""Service catalog package — SQLite-backed instance specs, pricing, and cross-cloud equivalences."""

from cloudwright.catalog.formula import PRICING_FORMULAS, default_managed_price
from cloudwright.catalog.store import (
    _BUNDLED_DB,
    _CATALOG_DIR,
    _PRICING_MULTIPLIERS,
    REGION_MAP,
    SCHEMA,
    Catalog,
)

# Backward compatibility alias
_default_managed_price = default_managed_price

__all__ = [
    "Catalog",
    "SCHEMA",
    "REGION_MAP",
    "_PRICING_MULTIPLIERS",
    "_CATALOG_DIR",
    "_BUNDLED_DB",
    "_default_managed_price",
    "default_managed_price",
    "PRICING_FORMULAS",
]
