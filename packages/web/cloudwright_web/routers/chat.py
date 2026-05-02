"""POST /api/chat, /api/chat/stream."""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

from cloudwright.session import ConversationSession
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import cloudwright_web.singletons as _singletons
from cloudwright_web.middleware import check_api_key, check_rate_limit, error_response
from cloudwright_web.streaming import sse_event

log = logging.getLogger(__name__)
router = APIRouter()

# Per-call SDK timeout passed into the async LLM client. Matches the previous
# route-level ``asyncio.wait_for(..., timeout=120)`` budget but pushes the
# enforcement down into the SDK so cancellation actually short-circuits the
# upstream LLM call (sync paths used to keep billing tokens after the route
# timed out).
_LLM_STREAM_TIMEOUT_S = 120.0

# Headers attached to every SSE response. ``X-Accel-Buffering: no`` disables
# nginx (and most reverse-proxy) buffering so token chunks reach the browser
# as soon as we yield them — without it, first-token latency observed by the
# user can balloon to 2-4s waiting for the proxy buffer to fill.
_SSE_HEADERS = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        architect = _singletons.get_architect()
        session = ConversationSession(llm=architect.llm)

        for msg in req.history:
            if msg.role != "user":
                continue  # only accept user-role messages from client history
            session.history.append({"role": msg.role, "content": msg.content})

        try:
            text, spec = await asyncio.wait_for(asyncio.to_thread(session.send, req.message), timeout=120)
        except asyncio.TimeoutError:
            return error_response("llm_timeout", "Request timed out", "Try a simpler architecture description", 504)

        if spec is None and not req.history:
            try:
                spec = await asyncio.wait_for(asyncio.to_thread(architect.design, req.message), timeout=120)
                text = f"Architecture: {spec.name}"
            except asyncio.TimeoutError:
                return error_response("llm_timeout", "Request timed out", "Try a simpler architecture description", 504)

        result: dict = {
            "reply": text,
            "history": session.history,
            "usage": session.last_usage,
        }
        if spec:
            result["spec"] = spec.model_dump(exclude_none=True)
            result["yaml"] = spec.to_yaml()
        return result
    except RuntimeError as e:
        if "No LLM provider" in str(e):
            return error_response("missing_api_key", str(e), "Set an LLM provider API key in your environment", 503)
        log.exception("Chat endpoint failed")
        return error_response("internal_error", "Internal server error", "Check server logs for details", 500)
    except Exception:
        log.exception("Chat endpoint failed")
        return error_response("internal_error", "Internal server error", "Check server logs for details", 500)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err

    async def event_generator():
        architect = _singletons.get_architect()
        session = ConversationSession(llm=architect.llm)

        for msg in req.history:
            if msg.role != "user":
                continue  # only accept user-role messages from client history
            session.history.append({"role": msg.role, "content": msg.content})

        # Push the stream timeout into the SDK call; on the async path this
        # cancels the upstream httpx connection, so we stop billing tokens the
        # moment the deadline passes (the old thread-bridge could not).
        try:
            session.llm.timeout = _LLM_STREAM_TIMEOUT_S  # best-effort hint for legacy adapters
        except Exception:
            pass

        try:
            agen = session.send_stream_async(req.message)
            try:
                while True:
                    try:
                        chunk = await asyncio.wait_for(agen.__anext__(), timeout=_LLM_STREAM_TIMEOUT_S)
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        # ``aclose`` cancels the inner ``async for`` and the
                        # SDK's ``async with`` tears down the upstream connection,
                        # so we do not orphan a coroutine billing tokens.
                        await agen.aclose()
                        yield sse_event(
                            "error",
                            code="llm_timeout",
                            message="Request timed out",
                            suggestion="Try a simpler architecture description",
                        )
                        return
                    yield sse_event("token", data=chunk)
            finally:
                # If the consumer disconnects (or anything else aborts the
                # generator), explicitly close the inner async-gen so the
                # SDK's ``async with`` cleanup runs synchronously here rather
                # than at GC time.
                await agen.aclose()

            spec = session.current_spec
            done_kwargs: dict = {"usage": session.last_usage}
            if spec:
                done_kwargs["data"] = spec.model_dump(exclude_none=True)
                done_kwargs["yaml"] = spec.to_yaml()
            yield sse_event("done", **done_kwargs)
        except asyncio.CancelledError:
            # Re-raised so Starlette can finish the request unwind. We do NOT
            # emit an SSE error event here — the consumer is gone, nobody is
            # listening, and yielding into a closed connection raises again.
            raise
        except Exception as e:
            log.exception("Chat stream failed")
            yield sse_event("error", message=str(e))

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=_SSE_HEADERS)
