"""GET /api/health, /api/version, and static icon serving."""

from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

import cloudwright_web.singletons as _singletons

router = APIRouter()

# Captured at module import for uptime reporting.
_START_MONOTONIC = time.monotonic()


def _llm_provider_and_model() -> tuple[str | None, str | None]:
    """Return (provider, model_name) based on env, without instantiating clients."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        from cloudwright.llm.anthropic import GENERATE_MODEL as ANTHROPIC_MODEL

        return "anthropic", ANTHROPIC_MODEL
    if os.environ.get("OPENAI_API_KEY"):
        from cloudwright.llm.openai import GENERATE_MODEL as OPENAI_MODEL

        return "openai", OPENAI_MODEL
    return None, None


def _version_payload() -> dict:
    from cloudwright import __version__

    provider, model = _llm_provider_and_model()
    return {
        "version": __version__,
        "build_sha": os.environ.get("CLOUDWRIGHT_BUILD_SHA"),
        "llm_provider": provider,
        "llm_model": model,
    }


@router.get("/health")
def health():
    has_llm_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    if not has_llm_key:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "reason": "No LLM API key configured (ANTHROPIC_API_KEY or OPENAI_API_KEY)",
                **_version_payload(),
                "catalog_loaded": False,
                "catalog_size": 0,
                "uptime_s": round(time.monotonic() - _START_MONOTONIC, 3),
            },
        )

    catalog_loaded = False
    catalog_size = 0
    try:
        catalog = _singletons.get_catalog()
        # Try to size the catalog; fall back to a sample search if no len.
        try:
            catalog_size = len(catalog)  # type: ignore[arg-type]
        except TypeError:
            catalog_size = len(catalog.search(query="m5", limit=1))
        catalog_loaded = True
    except Exception:
        catalog_loaded = False

    body = {
        "status": "ok" if catalog_loaded else "degraded",
        **_version_payload(),
        "catalog_loaded": catalog_loaded,
        "catalog_size": catalog_size,
        "uptime_s": round(time.monotonic() - _START_MONOTONIC, 3),
    }
    if not catalog_loaded:
        # Readiness probes (Kubernetes) should treat catalog-load failure as Not Ready.
        return JSONResponse(status_code=503, content=body)
    return body


@router.get("/version")
def version():
    return _version_payload()


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
