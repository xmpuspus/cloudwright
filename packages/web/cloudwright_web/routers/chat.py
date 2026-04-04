"""POST /api/chat, /api/chat/stream."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
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

        try:
            queue: asyncio.Queue = asyncio.Queue(maxsize=256)
            loop = asyncio.get_running_loop()

            def _run_stream():
                try:
                    for chunk in session.send_stream(req.message):
                        loop.call_soon_threadsafe(queue.put_nowait, ("token", chunk))
                    loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))

            thread = threading.Thread(target=_run_stream, daemon=True)
            thread.start()

            deadline = time.time() + 120
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    yield sse_event(
                        "error",
                        code="llm_timeout",
                        message="Request timed out",
                        suggestion="Try a simpler architecture description",
                    )
                    return
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), timeout=min(remaining, 5))
                except asyncio.TimeoutError:
                    continue

                if kind == "token":
                    yield sse_event("token", data=payload)
                elif kind == "error":
                    yield sse_event("error", message=payload)
                    return
                else:  # done
                    spec = session.current_spec
                    done_kwargs: dict = {"usage": session.last_usage}
                    if spec:
                        done_kwargs["data"] = spec.model_dump(exclude_none=True)
                        done_kwargs["yaml"] = spec.to_yaml()
                    yield sse_event("done", **done_kwargs)
                    return
        except Exception as e:
            yield sse_event("error", message=str(e))

    return StreamingResponse(event_generator(), media_type="text/event-stream")
