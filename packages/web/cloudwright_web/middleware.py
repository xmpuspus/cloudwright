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
from cloudwright.migration import validate_migration_size
from fastapi import HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

MAX_BODY_BYTES = 1_000_000  # 1 MB


class BodySizeLimitMiddleware:
    """Reject request bodies over ``max_bytes`` before a route handler ever
    buffers or parses them.

    Pure ASGI middleware (not ``BaseHTTPMiddleware``) so we can check the
    declared ``Content-Length`` up front AND wrap ``receive`` to enforce the
    same cap against the actual bytes streamed in, since a client can lie
    about (or omit) Content-Length.
    """

    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES):
        self.app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                pass

        total = 0

        async def limited_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self._max_bytes:
                    raise _BodyTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _BodyTooLargeError:
            await self._reject(send)

    async def _reject(self, send):
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": (
                    b'{"code":"payload_too_large","message":"Request body too large",'
                    b'"suggestion":"Reduce the request size"}'
                ),
            }
        )


class _BodyTooLargeError(Exception):
    pass


class MigrationRequestGuardMiddleware:
    """Authenticate and rate-limit migration routes before body parsing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] == "http" and path.startswith("/api/migration/") and scope.get("method") != "OPTIONS":
            request = Request(scope)
            try:
                check_api_key(request)
            except HTTPException as exc:
                response = JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                    headers=exc.headers,
                )
                await response(scope, receive, send)
                return
            if response := check_rate_limit(request):
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


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

    def __init__(self, max_requests: int = 30, window_seconds: int = 60, max_buckets: int = 10_000):
        self._max = max_requests
        self._window = window_seconds
        self._max_buckets = max_buckets
        self._buckets: dict[str, deque] = {}
        self._lock = threading.Lock()
        self._next_sweep = 0.0

    def _sweep_expired(self, cutoff: float) -> None:
        """Remove buckets that have no request inside the active window."""
        for other_ip, other_bucket in list(self._buckets.items()):
            while other_bucket and other_bucket[0] < cutoff:
                other_bucket.popleft()
            if not other_bucket:
                del self._buckets[other_ip]

    def is_allowed(self, ip: str) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds)."""
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            if now >= self._next_sweep:
                self._sweep_expired(cutoff)
                self._next_sweep = now + self._window
            if self._max <= 0:
                return False, int(self._window) + 1

            bucket = self._buckets.get(ip)
            if bucket is None:
                if len(self._buckets) >= self._max_buckets:
                    retry_after = max(1, int(self._next_sweep - now) + 1)
                    return False, retry_after
                bucket = self._buckets.setdefault(ip, deque())
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


# --- Request work caps ---

MAX_SPEC_COMPONENTS = 200


def check_component_limit(spec) -> JSONResponse | None:
    """Reject a validated ``ArchSpec`` with an unreasonable component count.

    Downstream work (cost estimation, rendering, terraform export, LLM
    modify calls) scales with component count, so an attacker-controlled
    spec with thousands of components turns one request into unbounded
    server-side work. Mirrors the ``check_rate_limit`` return-on-error
    pattern so callers do ``if err := check_component_limit(spec): return err``
    regardless of whether that router otherwise raises HTTPException.
    """
    count = len(spec.components)
    if count > MAX_SPEC_COMPONENTS:
        return error_response(
            "spec_too_large",
            f"Spec has {count} components; max allowed is {MAX_SPEC_COMPONENTS}",
            "Split the architecture into smaller specs",
            422,
        )
    return None


def check_migration_limit(project, evidence=None) -> JSONResponse | None:
    """Reject migration collections that exceed the request work limit."""
    try:
        validate_migration_size(project, evidence)
    except ValueError as exc:
        return error_response(
            "migration_too_large",
            str(exc),
            "Split the migration into smaller projects",
            422,
        )
    return None
