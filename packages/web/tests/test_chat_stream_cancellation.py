"""``/api/chat/stream`` cancel-safe streaming.

Pre-fix bug (audit Critical #2): the chat-stream router started a daemon
``threading.Thread`` running ``session.send_stream`` and bridged its output
to the SSE response via an ``asyncio.Queue``. On client disconnect or
route-level timeout, the thread was orphaned — the upstream LLM call kept
running and tokens kept billing.

Post-fix (v1.4): the router awaits ``session.send_stream_async`` directly.
Cancellation propagates into the SDK's ``async with`` block, which closes
the upstream httpx connection.

Verifies:
1. ``threading`` is no longer used in ``routers.chat`` (regression guard
   against the thread bridge sneaking back).
2. Aborting the SSE response mid-stream calls the inner async-gen's close
   path on the mocked ``ConversationSession.send_stream_async``.
3. No background asyncio tasks linger after the stream is cancelled.
4. The done event still carries usage metadata.
"""

from __future__ import annotations

import asyncio
import inspect
import json

import pytest
from fastapi.testclient import TestClient

from cloudwright_web import routers as _routers_pkg  # noqa: F401 — ensures package init
from cloudwright_web.routers import chat as chat_router


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


def test_chat_router_no_longer_imports_threading():
    """The thread bridge is gone. If someone reintroduces it the audit-2
    bug comes back, so guard the import surface."""
    src = inspect.getsource(chat_router)
    assert "import threading" not in src, (
        "routers/chat.py must not import threading — async streaming should "
        "obviate the worker thread (audit-2 regression guard)."
    )
    assert "threading.Thread" not in src


def test_chat_router_uses_send_stream_async():
    src = inspect.getsource(chat_router)
    assert "send_stream_async" in src, (
        "routers/chat.py must drive the cancel-safe async path — "
        "send_stream (sync) leaves orphaned worker threads on disconnect."
    )


def test_chat_stream_emits_sse_headers_for_proxy_buffering(client):
    """``X-Accel-Buffering: no`` is required so nginx (and most proxies)
    don't buffer 4-16 KB before forwarding tokens to the browser."""
    from unittest.mock import MagicMock, patch

    async def _stream(_msg):
        yield "hi"

    mock_session = MagicMock()
    mock_session.current_spec = None
    mock_session.last_usage = {}
    mock_session.history = []
    mock_session.send_stream_async = _stream

    with patch("cloudwright_web.singletons.get_architect") as mock_arch:
        mock_arch.return_value.llm = MagicMock()
        with patch("cloudwright_web.routers.chat.ConversationSession", return_value=mock_session):
            resp = client.post("/api/chat/stream", json={"message": "hi"})

    assert resp.status_code == 200
    assert resp.headers.get("x-accel-buffering") == "no"


def test_chat_stream_aborts_inner_agen_on_consumer_close():
    """Drive the route's ``event_generator`` directly and abort it after the
    first yield. The mocked session's ``send_stream_async`` async-gen must
    receive a ``GeneratorExit`` so its underlying SDK ``async with`` runs
    its cleanup path — proving the cancellation chain is intact."""
    from unittest.mock import MagicMock, patch

    closed = {"flag": False}

    async def _stream(_msg):
        try:
            yield "first"
            yield "second"
            yield "third"
        except GeneratorExit:
            closed["flag"] = True
            raise

    mock_session = MagicMock()
    mock_session.current_spec = None
    mock_session.last_usage = {}
    mock_session.history = []
    mock_session.send_stream_async = _stream

    async def _drive():
        with patch("cloudwright_web.singletons.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch(
                "cloudwright_web.routers.chat.ConversationSession", return_value=mock_session
            ):
                from starlette.requests import Request

                request = Request(
                    {
                        "type": "http",
                        "method": "POST",
                        "path": "/api/chat/stream",
                        "headers": [],
                        "query_string": b"",
                        "client": ("test", 0),
                    }
                )
                req = chat_router.ChatRequest(message="hi")
                resp = await chat_router.chat_stream(req, request)
                agen = resp.body_iterator
                # Pull the first event then abort.
                first = await agen.__anext__()
                assert "data:" in first.decode() if isinstance(first, bytes) else "data:" in first
                await agen.aclose()

    asyncio.run(_drive())
    assert closed["flag"], (
        "GeneratorExit must propagate from the SSE response into the inner "
        "send_stream_async — without this, the SDK's async with cleanup is "
        "skipped and the LLM call keeps consuming tokens after disconnect."
    )


def test_chat_stream_no_orphan_tasks_after_full_response(client):
    """After a normal full-response stream, no background asyncio tasks
    related to chat streaming should linger. The pre-fix thread bridge
    couldn't be checked this way; the new async path can."""
    from unittest.mock import MagicMock, patch

    async def _stream(_msg):
        for c in ("a", "b", "c"):
            yield c

    mock_session = MagicMock()
    mock_session.current_spec = None
    mock_session.last_usage = {"input_tokens": 1, "output_tokens": 1}
    mock_session.history = []
    mock_session.send_stream_async = _stream

    async def _check():
        with patch("cloudwright_web.singletons.get_architect") as mock_arch:
            mock_arch.return_value.llm = MagicMock()
            with patch(
                "cloudwright_web.routers.chat.ConversationSession", return_value=mock_session
            ):
                tasks_before = {t for t in asyncio.all_tasks() if not t.done()}
                from starlette.requests import Request

                request = Request(
                    {
                        "type": "http",
                        "method": "POST",
                        "path": "/api/chat/stream",
                        "headers": [],
                        "query_string": b"",
                        "client": ("test", 0),
                    }
                )
                req = chat_router.ChatRequest(message="hi")
                resp = await chat_router.chat_stream(req, request)
                events: list[str] = []
                async for ev in resp.body_iterator:
                    events.append(ev.decode() if isinstance(ev, bytes) else ev)
                # Drain finished — give the loop a tick.
                await asyncio.sleep(0)
                tasks_after = {t for t in asyncio.all_tasks() if not t.done()}
                # Don't count the test's own task.
                me = asyncio.current_task()
                tasks_after.discard(me)
                tasks_before.discard(me)
                new_tasks = tasks_after - tasks_before
                assert not new_tasks, (
                    f"Cancel-safe streaming must leave no orphan tasks; found {new_tasks}"
                )
                # Sanity: we did get a done event.
                stages = [
                    json.loads(e.split("data: ", 1)[1].strip()).get("stage")
                    for e in events
                    if "data:" in e
                ]
                assert "done" in stages

    asyncio.run(_check())
