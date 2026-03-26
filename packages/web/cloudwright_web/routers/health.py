"""GET /api/health and static icon serving."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import cloudwright_web.singletons as _singletons

router = APIRouter()


@router.get("/health")
def health():
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
