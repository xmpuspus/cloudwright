"""POST /api/compliance — control-ID-mapped compliance scan."""

from __future__ import annotations

import asyncio
import logging

from cloudwright import ArchSpec
from cloudwright.compliance import ComplianceScanner
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from cloudwright_web.middleware import check_api_key, check_component_limit, check_rate_limit

log = logging.getLogger(__name__)
router = APIRouter()


class ComplianceRequest(BaseModel):
    spec: dict
    frameworks: list[str] = Field(default_factory=list)
    checkov: bool | None = None


@router.post("/compliance")
async def compliance(req: ComplianceRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        spec = ArchSpec.model_validate(req.spec)
        if err := check_component_limit(spec):
            return err
        report = await asyncio.to_thread(
            ComplianceScanner().scan,
            spec,
            req.frameworks or None,
            req.checkov,
        )
        return report.as_dict()
    except Exception as e:
        log.exception("Compliance endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
