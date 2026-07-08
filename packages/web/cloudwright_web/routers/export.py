"""POST /api/export, /api/download."""

from __future__ import annotations

import logging
import re

from cloudwright import ArchSpec
from cloudwright.exporter import FORMATS, export_spec
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from cloudwright_web.middleware import check_api_key, check_component_limit, check_rate_limit

log = logging.getLogger(__name__)
router = APIRouter()


class ExportRequest(BaseModel):
    spec: dict
    format: str


@router.post("/export")
def export(req: ExportRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        spec = ArchSpec.model_validate(req.spec)
        if err := check_component_limit(spec):
            return err
        if req.format not in FORMATS:
            raise HTTPException(
                status_code=400, detail=f"Unknown format: {req.format}. Supported: {', '.join(FORMATS)}"
            )
        content = export_spec(spec, req.format)
        return {"content": content, "format": req.format}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Export endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/download")
async def download(request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        data = await request.json()
        spec = ArchSpec.model_validate(data["spec"])
        if err := check_component_limit(spec):
            return err
        fmt = data.get("format", "terraform")
        safe_name = re.sub(r"[^\w\-.]", "-", spec.name.lower())
        if fmt == "yaml":
            content = spec.to_yaml()
            filename = f"{safe_name}.yaml"
        elif fmt not in FORMATS:
            raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}. Supported: yaml, {', '.join(FORMATS)}")
        else:
            content = export_spec(spec, fmt)
            ext_map = {"terraform": "tf", "cloudformation": "yaml", "mermaid": "mmd", "d2": "d2"}
            ext = ext_map.get(fmt, "txt")
            filename = f"{safe_name}.{ext}"
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Download endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e
