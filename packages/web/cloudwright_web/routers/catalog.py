"""POST /api/catalog/search, /api/catalog/compare."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cloudwright_web.singletons import get_catalog

log = logging.getLogger(__name__)
router = APIRouter()


class CatalogSearchRequest(BaseModel):
    query: str | None = None
    provider: str | None = None
    vcpus: int | None = None
    memory_gb: float | None = None
    max_price_per_hour: float | None = None
    limit: int = Field(default=20, ge=1, le=100)


class CatalogCompareRequest(BaseModel):
    instance_names: list[str] = Field(..., min_length=2)


@router.post("/catalog/search")
def catalog_search(req: CatalogSearchRequest):
    try:
        catalog = get_catalog()
        instances = catalog.search(
            query=req.query,
            vcpus=req.vcpus,
            memory_gb=req.memory_gb,
            provider=req.provider,
            max_price_per_hour=req.max_price_per_hour,
            limit=req.limit,
        )
        return {"instances": instances}
    except Exception as e:
        log.exception("Catalog search endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/catalog/compare")
def catalog_compare(req: CatalogCompareRequest):
    try:
        catalog = get_catalog()
        result = catalog.compare(*req.instance_names)
        return {"comparison": result}
    except Exception as e:
        log.exception("Catalog compare endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
