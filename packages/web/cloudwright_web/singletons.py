"""Thread-safe lazy factories for shared service instances."""

from __future__ import annotations

import threading

from cloudwright.architect import Architect
from cloudwright.catalog import Catalog
from cloudwright.cost import CostEngine

_architect: Architect | None = None
_catalog: Catalog | None = None
_cost_engine: CostEngine | None = None
_architect_lock = threading.Lock()
_catalog_lock = threading.Lock()
_cost_engine_lock = threading.Lock()


def get_architect() -> Architect:
    global _architect
    if _architect is None:
        with _architect_lock:
            if _architect is None:
                _architect = Architect()
    return _architect


def get_catalog() -> Catalog:
    global _catalog
    if _catalog is None:
        with _catalog_lock:
            if _catalog is None:
                _catalog = Catalog()
    return _catalog


def get_cost_engine() -> CostEngine:
    global _cost_engine
    if _cost_engine is None:
        with _cost_engine_lock:
            if _cost_engine is None:
                _cost_engine = CostEngine()
    return _cost_engine
