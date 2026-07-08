"""POST /api/review — deterministic architecture critique (offline, no LLM)."""

from __future__ import annotations

import asyncio
import logging

from cloudwright import ArchSpec
from cloudwright.critique import critique
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from cloudwright_web.middleware import check_api_key, check_component_limit, check_rate_limit

log = logging.getLogger(__name__)
router = APIRouter()


class ReviewRequest(BaseModel):
    spec: dict
    compliance: list[str] = Field(default_factory=list)
    well_architected: bool = False


@router.post("/review")
async def review(req: ReviewRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        spec = ArchSpec.model_validate(req.spec)
        if err := check_component_limit(spec):
            return err
        report = await asyncio.to_thread(
            critique,
            spec,
            compliance=req.compliance or None,
            well_architected=req.well_architected,
        )
        return report.as_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("Review endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
