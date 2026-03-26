"""POST /api/validate."""

from __future__ import annotations

import asyncio
import logging

from cloudwright import ArchSpec
from cloudwright.validator import Validator
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from cloudwright_web.middleware import check_api_key, check_rate_limit
from cloudwright_web.routers.cost import cache

log = logging.getLogger(__name__)
router = APIRouter()


class ValidateRequest(BaseModel):
    spec: dict
    compliance: list[str] = Field(default_factory=list)
    well_architected: bool = False


@router.post("/validate")
async def validate(req: ValidateRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        key_suffix = ",".join(sorted(req.compliance)) + str(req.well_architected)
        cached = cache.get_validation(req.spec, key_suffix)
        if cached is not None:
            return {"results": cached}

        validator = Validator()
        spec = ArchSpec.model_validate(req.spec)
        frameworks = req.compliance if req.compliance else []
        results = await asyncio.to_thread(
            validator.validate, spec, compliance=frameworks or None, well_architected=req.well_architected
        )
        serialized = [r.model_dump() for r in results]
        cache.set_validation(req.spec, serialized, key_suffix)
        return {"results": serialized}
    except Exception as e:
        log.exception("Validate endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
