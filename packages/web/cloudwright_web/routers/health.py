"""GET /api/health and static icon serving."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

import cloudwright_web.singletons as _singletons

router = APIRouter()


@router.get("/health")
def health():
    # Check LLM key presence
    has_llm_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    if not has_llm_key:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "reason": "No LLM API key configured (ANTHROPIC_API_KEY or OPENAI_API_KEY)"},
        )
    try:
        catalog = _singletons.get_catalog()
        results = catalog.search(query="m5", limit=1)
        return {"status": "ok", "catalog_loaded": True, "sample_count": len(results)}
    except Exception:
        return {"status": "ok", "catalog_loaded": False}


@router.get("/icons/{provider}/{service}.svg")
def get_icon(provider: str, service: str):
    import cloudwright

    icons_dir = Path(cloudwright.__file__).parent / "data" / "icons"
    icon_path = icons_dir / provider / f"{service}.svg"
    if not icon_path.exists():
        raise HTTPException(status_code=404, detail=f"Icon not found: {provider}/{service}")
    if not icon_path.resolve().is_relative_to(icons_dir.resolve()):
        raise HTTPException(status_code=404, detail="Invalid path")
    return FileResponse(str(icon_path), media_type="image/svg+xml")
