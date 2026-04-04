"""FastAPI backend wrapping the Cloudwright core package."""

from __future__ import annotations

import multiprocessing
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from cloudwright_web import __version__
from cloudwright_web.middleware import (  # noqa: F401
    PathTraversalMiddleware,
    _rate_limiter,
    _RateLimiter,
    add_cors,
)
from cloudwright_web.routers import (
    catalog_router,
    chat_router,
    cost_router,
    design_router,
    diagram_router,
    export_router,
    health_router,
    validate_router,
)
from cloudwright_web.singletons import get_architect, get_catalog, get_cost_engine  # noqa: F401


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def create_app() -> FastAPI:
    application = FastAPI(
        title="Cloudwright",
        version=__version__,
        description="Architecture intelligence for cloud engineers",
    )

    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(PathTraversalMiddleware)
    add_cors(application)

    application.include_router(health_router, prefix="/api")
    application.include_router(design_router, prefix="/api")
    application.include_router(cost_router, prefix="/api")
    application.include_router(validate_router, prefix="/api")
    application.include_router(export_router, prefix="/api")
    application.include_router(catalog_router, prefix="/api")
    application.include_router(diagram_router, prefix="/api")
    application.include_router(chat_router, prefix="/api")

    from cloudwright_web.routers.diff import router as diff_router

    application.include_router(diff_router, prefix="/api")

    # Serve frontend static files if they exist
    frontend_dist = Path(__file__).parent / "static"
    if frontend_dist.exists():
        application.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

        @application.get("/{path:path}")
        def serve_frontend(path: str):
            file_path = (frontend_dist / path).resolve()
            if file_path.is_relative_to(frontend_dist.resolve()) and file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(frontend_dist / "index.html"))

    return application


app = create_app()


def serve(host: str = "127.0.0.1", port: int = 8000):
    """Start the Cloudwright web server."""
    import uvicorn

    from cloudwright.logging import configure_logging

    configure_logging()

    if not os.environ.get("CLOUDWRIGHT_API_KEY"):
        raise SystemExit(
            "CLOUDWRIGHT_API_KEY environment variable is required when running the web server. "
            "Set it to a secret value that clients must pass in the X-API-Key header."
        )

    workers = min(multiprocessing.cpu_count(), 4)
    uvicorn.run("cloudwright_web.app:app", host=host, port=port, workers=workers)
