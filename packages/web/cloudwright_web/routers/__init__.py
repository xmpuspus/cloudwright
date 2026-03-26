"""Collects all API routers."""

from cloudwright_web.routers.catalog import router as catalog_router
from cloudwright_web.routers.chat import router as chat_router
from cloudwright_web.routers.cost import router as cost_router
from cloudwright_web.routers.design import router as design_router
from cloudwright_web.routers.diagram import router as diagram_router
from cloudwright_web.routers.export import router as export_router
from cloudwright_web.routers.health import router as health_router
from cloudwright_web.routers.validate import router as validate_router

__all__ = [
    "catalog_router",
    "chat_router",
    "cost_router",
    "design_router",
    "diagram_router",
    "export_router",
    "health_router",
    "validate_router",
]
