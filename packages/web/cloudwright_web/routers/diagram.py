"""POST /api/diagram."""

from __future__ import annotations

from cloudwright import ArchSpec
from fastapi import APIRouter, Request
from fastapi.responses import Response

router = APIRouter()


@router.post("/diagram")
async def render_diagram(request: Request):
    data = await request.json()
    spec = ArchSpec.model_validate(data["spec"])
    fmt = data.get("format", "svg")
    from cloudwright.exporter.renderer import DiagramRenderer

    renderer = DiagramRenderer()
    if fmt == "png":
        png_data = renderer.render_png(spec)
        return Response(content=png_data, media_type="image/png")
    svg = renderer.render_svg(spec)
    return Response(content=svg, media_type="image/svg+xml")
