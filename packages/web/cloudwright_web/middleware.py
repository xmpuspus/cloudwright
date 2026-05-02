"""Rate limiter, path traversal guard, CORS setup, and optional API key auth."""

from __future__ import annotations

import hmac
import os
import threading
import time
import uuid
from collections import deque
from urllib.parse import unquote

import structlog
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


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request correlation ID to every request.

    - Reads X-Request-Id from incoming headers, otherwise mints a UUID4 hex.
    - Binds the value into structlog's contextvars for the duration of the
      request so every log line carries it.
    - Echoes the same value back as the X-Request-Id response header.
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "").strip()
        request_id = incoming or uuid.uuid4().hex

        # Stash on request.state so handlers can read it if they need to.
        request.state.request_id = request_id

        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")

        response.headers["X-Request-Id"] = request_id
        return response


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
    """Validate the X-API-Key header in constant time.

    Using ``hmac.compare_digest`` prevents timing-based recovery of the
    configured key. Both sides are encoded to bytes (utf-8); mismatched
    lengths are rejected by ``compare_digest`` itself but we short-circuit
    empty input first to avoid leaking even a length signal.
    """
    if not _API_KEY:
        return None
    provided = request.headers.get("x-api-key", "")
    if not provided:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    expected_bytes = _API_KEY.encode("utf-8")
    provided_bytes = provided.encode("utf-8")
    if not hmac.compare_digest(provided_bytes, expected_bytes):
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


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For when behind a trusted proxy."""
    if os.environ.get("CLOUDWRIGHT_TRUST_PROXY"):
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request):
    ip = _get_client_ip(request)
    allowed, retry_after = _rate_limiter.is_allowed(ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "code": "rate_limited",
                "message": "Too many requests",
                "suggestion": f"Wait {retry_after} seconds before retrying",
            },
            headers={"Retry-After": str(retry_after)},
        )
    return None
