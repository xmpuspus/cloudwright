"""POST /api/compliance — control-ID-mapped compliance scan, with optional OSCAL export."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

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
    oscal: bool = False


def _scan_and_maybe_oscal(spec: ArchSpec, frameworks: list[str], checkov: bool | None, want_oscal: bool) -> dict:
    """Run the compliance scan and, when requested, attach the OSCAL document.

    Mirrors ``cloudwright compliance --oscal`` line for line: ``scan()`` gets
    the raw requested frameworks (it resolves them itself), and a second,
    independent ``resolve_frameworks`` call feeds ``to_oscal`` — the exact
    builder the CLI uses — so the web surface can never drift from the CLI's
    OSCAL output.
    """
    scanner = ComplianceScanner()
    report = scanner.scan(spec, frameworks or None, checkov)
    payload = report.as_dict()
    if want_oscal:
        from cloudwright.oscal import to_oscal

        resolved = scanner.resolve_frameworks(spec, frameworks or None)
        payload["oscal"] = to_oscal(spec, report, resolved)
    return payload


@router.post("/compliance")
async def compliance(req: ComplianceRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        spec = ArchSpec.model_validate(req.spec)
        if err := check_component_limit(spec):
            return err
        payload: dict[str, Any] = await asyncio.to_thread(
            _scan_and_maybe_oscal, spec, req.frameworks, req.checkov, req.oscal
        )
        return payload
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("Compliance endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
