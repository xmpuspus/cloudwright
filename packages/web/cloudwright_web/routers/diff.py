"""Diff endpoint — compares two ArchSpecs."""

from __future__ import annotations

import logging

from cloudwright.differ import Differ
from cloudwright.spec import ArchSpec
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from cloudwright_web.middleware import check_api_key, check_rate_limit

log = logging.getLogger(__name__)

router = APIRouter()


class DiffRequest(BaseModel):
    old_spec: dict
    new_spec: dict


@router.post("/diff")
def diff(req: DiffRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        differ = Differ()
        old = ArchSpec.model_validate(req.old_spec)
        new = ArchSpec.model_validate(req.new_spec)
        result = differ.diff(old, new)
        return {"diff": result.model_dump()}
    except Exception as e:
        log.exception("Diff endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
