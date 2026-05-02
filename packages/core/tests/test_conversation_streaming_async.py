"""Tests for ``ConversationSession.send_stream_async``.

Mirrors ``test_conversation_streaming.py`` but exercises the cancel-safe
async path the v1.4 web routers use.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from cloudwright.session import ConversationSession


def _make_spec_json(name="Test App"):
    components = [
        {"id": "web", "service": "ec2", "provider": "aws", "label": "Web", "tier": 2, "config": {}},
        {"id": "db", "service": "rds", "provider": "aws", "label": "DB", "tier": 3, "config": {}},
    ]
    return json.dumps(
        {
            "name": name,
            "provider": "aws",
            "region": "us-east-1",
            "components": components,
            "connections": [{"source": "web", "target": "db", "label": "SQL"}],
        }
    )


def _mock_async_llm(chunks):
    llm = MagicMock()
    llm.model_name = "mock-model"
    llm.pricing = {"input": 0.003, "output": 0.015}

    async def _stream(messages, system, max_tokens=2000, timeout=None):
        for c in chunks:
            yield c

    llm.generate_stream_async = _stream
    return llm


@pytest.mark.asyncio
async def test_send_stream_async_yields_chunks():
    llm = _mock_async_llm(["Here ", "is ", "your ", "architecture."])
    session = ConversationSession(llm=llm)

    chunks: list[str] = []
    async for c in session.send_stream_async("design a web app on aws"):
        chunks.append(c)

    assert chunks == ["Here ", "is ", "your ", "architecture."]


@pytest.mark.asyncio
async def test_send_stream_async_updates_history():
    llm = _mock_async_llm(["Here is your aws architecture."])
    session = ConversationSession(llm=llm)

    async for _ in session.send_stream_async("design a web app on aws"):
        pass

    assert len(session.history) == 2
    assert session.history[0]["role"] == "user"
    assert session.history[1]["role"] == "assistant"
    assert session.history[1]["content"] == "Here is your aws architecture."


@pytest.mark.asyncio
async def test_send_stream_async_extracts_spec():
    spec_json = _make_spec_json("Streamed App")
    llm = _mock_async_llm([spec_json])
    session = ConversationSession(llm=llm)

    async for _ in session.send_stream_async("design a web app on aws"):
        pass

    assert session.current_spec is not None
    assert session.current_spec.name == "Streamed App"


@pytest.mark.asyncio
async def test_send_stream_async_pops_history_on_cancellation():
    """If the consumer cancels mid-stream, the orphan user message must be
    rolled back so the next turn doesn't see a user-without-assistant in
    history."""
    import asyncio

    async def _hang(messages, system, max_tokens=2000, timeout=None):
        # Yield once, then never finish — the consumer will cancel.
        yield "first"
        await asyncio.sleep(60)
        yield "never reached"

    llm = MagicMock()
    llm.model_name = "mock-model"
    llm.pricing = {"input": 0.003, "output": 0.015}
    llm.generate_stream_async = _hang

    session = ConversationSession(llm=llm)
    initial_len = len(session.history)

    agen = session.send_stream_async("hello aws")
    first = await agen.__anext__()
    assert first == "first"
    # Simulate client disconnect — async-gen close.
    await agen.aclose()

    # The orphan user message was rolled back.
    assert len(session.history) == initial_len, (
        "send_stream_async must pop the orphan user message on cancellation "
        "(otherwise next turn re-sends it as the prior user turn)."
    )


def test_send_stream_async_is_async_generator():
    """Cheap structural check: the method must be an async generator
    function so the routers can ``async for`` over it."""
    import inspect

    assert inspect.isasyncgenfunction(ConversationSession.send_stream_async)


def test_sync_send_stream_still_exists():
    """Back-compat: CLI/tests still call the sync ``send_stream``."""
    import inspect

    assert inspect.isgeneratorfunction(ConversationSession.send_stream)
