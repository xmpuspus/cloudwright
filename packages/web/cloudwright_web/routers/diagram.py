"""POST /api/diagram."""

from __future__ import annotations

import asyncio
import logging

from cloudwright import ArchSpec
from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel

from cloudwright_web.middleware import check_api_key, check_component_limit, check_rate_limit, error_response

log = logging.getLogger(__name__)
router = APIRouter()


class DiagramRequest(BaseModel):
    spec: dict
    format: str = "svg"


@router.post("/diagram")
async def render_diagram(req: DiagramRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        spec = ArchSpec.model_validate(req.spec)
    except Exception as e:
        return error_response("invalid_spec", str(e), "Check the spec matches the ArchSpec schema", 400)

    if err := check_component_limit(spec):
        return err

    from cloudwright.exporter.renderer import DiagramRenderer

    renderer = DiagramRenderer()
    try:
        # The D2 subprocess can run up to 300s (renderer.py's PNG timeout).
        # Running it inline would block the event loop for every other
        # request for that long; asyncio.to_thread pushes it off-loop, same
        # pattern as routers/plan.py's terraform/pulumi subprocess calls.
        if req.format == "png":
            png_data = await asyncio.to_thread(renderer.render_png, spec)
            return Response(content=png_data, media_type="image/png")
        svg = await asyncio.to_thread(renderer.render_svg, spec)
        return Response(content=svg, media_type="image/svg+xml")
    except Exception as e:
        log.exception("Diagram render failed")
        return error_response("render_failed", str(e), "Check the D2 binary is installed and the spec is valid", 500)
