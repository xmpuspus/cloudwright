"""POST /api/plan — prove the exported infrastructure is deployable."""

from __future__ import annotations

import asyncio
import logging

from cloudwright import ArchSpec
from cloudwright.planner import plan as run_plan
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from cloudwright_web.middleware import check_api_key, check_rate_limit

log = logging.getLogger(__name__)
router = APIRouter()


class PlanRequest(BaseModel):
    spec: dict
    target: str = "terraform"
    run_plan: bool = True


@router.post("/plan")
async def plan(req: PlanRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        spec = ArchSpec.model_validate(req.spec)
        result = await asyncio.to_thread(run_plan, spec, req.target, run_plan=req.run_plan, timeout=180)
        return result.as_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("Plan endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
