"""Rate limiter, path traversal guard, CORS setup, and optional API key auth."""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from urllib.parse import unquote

from fastapi import HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class PathTraversalMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        raw_path = request.scope.get("path", "") or request.url.path
        if ".." in raw_path or ".." in unquote(raw_path):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        return await call_next(request)


def add_cors(app):
    origins = os.environ.get("CLOUDWRIGHT_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )


# --- Optional API key auth ---

_API_KEY = os.environ.get("CLOUDWRIGHT_API_KEY")


def check_api_key(request: Request):
    if not _API_KEY:
        return None
    provided = request.headers.get("x-api-key", "")
    if provided != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return None


# --- Rate limiter ---


class _RateLimiter:
    """Simple in-memory per-IP rate limiter."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._buckets: dict[str, deque] = {}
        self._lock = threading.Lock()

    def is_allowed(self, ip: str) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds)."""
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            if ip not in self._buckets:
                self._buckets[ip] = deque()
            bucket = self._buckets[ip]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self._max:
                retry_after = int(self._window - (now - bucket[0])) + 1 if bucket else int(self._window) + 1
                return False, retry_after
            bucket.append(now)
            return True, 0


_rate_limiter = _RateLimiter(max_requests=30, window_seconds=60)


def error_response(code: str, message: str, suggestion: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "suggestion": suggestion},
    )


def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    allowed, retry_after = _rate_limiter.is_allowed(ip)
    if not allowed:
        return error_response(
            "rate_limited",
            "Too many requests",
            f"Wait {retry_after} seconds before retrying",
            status_code=429,
        )
    return None
