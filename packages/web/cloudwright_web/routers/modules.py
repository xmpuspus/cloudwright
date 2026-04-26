"""Module catalog and canvas standards APIs."""

from __future__ import annotations

import logging
from typing import Any

from cloudwright.modules import ModuleCatalog, validate_standards_from_dict
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from cloudwright_web.middleware import check_api_key, check_rate_limit

log = logging.getLogger(__name__)
router = APIRouter()


class CanvasValidateRequest(BaseModel):
    spec: dict[str, Any]


@router.get("/modules")
def list_modules(request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        catalog = ModuleCatalog()
        return {"modules": catalog.summaries(approved_only=True)}
    except Exception as e:
        log.exception("Module list endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/modules/{module_id}")
def get_module(module_id: str, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        module = ModuleCatalog().get(module_id)
        if module is None or not module.approved:
            raise HTTPException(status_code=404, detail="Module not found")
        return {"module": module.model_dump(mode="json")}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Module detail endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/canvas/validate")
def validate_canvas(req: CanvasValidateRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        result = validate_standards_from_dict(req.spec, catalog=ModuleCatalog())
        return result.model_dump(mode="json")
    except Exception as e:
        log.exception("Canvas validate endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
