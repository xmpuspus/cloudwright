"""AsyncAnthropic cancel-safe streaming.

Audit unlock #5 from ``docs/audits/03-reliability-perf.md``: the sync
``threading.Thread`` + ``asyncio.Queue`` bridge in ``routers/chat.py``
orphaned the worker thread on client disconnect or timeout, so the upstream
LLM call kept billing tokens after the server returned 504. The fix is a
native ``AsyncAnthropic`` streaming path that propagates ``CancelledError``
all the way into the SDK's ``async with`` block, which closes the underlying
httpx connection.

These tests verify:
1. ``AnthropicLLM.generate_stream_async`` yields chunks via ``async for``.
2. Closing the iterator early (simulating a client disconnect) triggers the
   ``async with`` cleanup path in the SDK — i.e. ``__aexit__`` runs.
3. The system block is preserved as a list-of-blocks (so the v1.3.0 cache
   prefix still hits).
4. Per-call ``timeout=`` is forwarded to the SDK.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from cloudwright.llm.anthropic import AnthropicLLM


class _FakeAsyncTextStream:
    """Async iterator that yields text chunks."""

    def __init__(self, chunks: list[str]):
        self._chunks = list(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._chunks:
            raise StopAsyncIteration
        # Yield to the loop so cancellation between chunks is observable.
        await asyncio.sleep(0)
        return self._chunks.pop(0)


class _FakeAsyncStream:
    """Stand-in for the AsyncAnthropic ``messages.stream`` async-context
    manager. Tracks whether ``__aexit__`` ran (i.e. cleanup happened)."""

    def __init__(self, chunks: list[str]):
        self.text_stream = _FakeAsyncTextStream(chunks)
        self.entered = False
        self.exited = False
        self.exit_exc_type: type | None = None

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        self.exit_exc_type = exc_type
        return False  # never swallow exceptions


class _FakeAsyncMessages:
    def __init__(self, fake_stream: _FakeAsyncStream):
        self._fake_stream = fake_stream
        self.last_kwargs: dict | None = None

    def stream(self, **kwargs):
        self.last_kwargs = kwargs
        return self._fake_stream


class _FakeAsyncClient:
    def __init__(self, fake_stream: _FakeAsyncStream):
        self.messages = _FakeAsyncMessages(fake_stream)


@pytest.mark.asyncio
async def test_generate_stream_async_yields_chunks():
    fake = _FakeAsyncStream(["Hel", "lo ", "world"])
    llm = AnthropicLLM(api_key="test")
    llm._async_client = _FakeAsyncClient(fake)

    chunks: list[str] = []
    async for c in llm.generate_stream_async([{"role": "user", "content": "hi"}], "system"):
        chunks.append(c)

    assert chunks == ["Hel", "lo ", "world"]
    # Cleanup ran (no orphaned upstream connection).
    assert fake.exited, "async with __aexit__ must run after normal completion"


@pytest.mark.asyncio
async def test_generate_stream_async_closes_on_consumer_disconnect():
    """Simulate a client disconnect mid-stream: the consumer breaks out of
    the ``async for`` after the first chunk. The SDK's ``async with`` must
    tear down the upstream connection — without this, AsyncAnthropic would
    keep consuming tokens until the LLM finished its full response."""
    fake = _FakeAsyncStream(["chunk-1", "chunk-2", "chunk-3"])
    llm = AnthropicLLM(api_key="test")
    llm._async_client = _FakeAsyncClient(fake)

    agen = llm.generate_stream_async([{"role": "user", "content": "hi"}], "system")
    first = await agen.__anext__()
    assert first == "chunk-1"
    # Consumer aborts. ``aclose()`` propagates ``GeneratorExit`` into the
    # async-gen body, which exits the ``async with`` block.
    await agen.aclose()

    assert fake.exited, "stream must be closed when consumer aborts mid-iteration"


@pytest.mark.asyncio
async def test_generate_stream_async_preserves_cache_prefix_blocks():
    """v1.3.0 prompt cache: when ``system`` is a list of blocks (with
    ``cache_control``), it must be forwarded as-is to the SDK so the cached
    prefix actually hits."""
    fake = _FakeAsyncStream(["x"])
    llm = AnthropicLLM(api_key="test")
    llm._async_client = _FakeAsyncClient(fake)

    blocks = [
        {"type": "text", "text": "stable system", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "variable hint"},
    ]
    async for _ in llm.generate_stream_async([{"role": "user", "content": "hi"}], blocks):
        pass

    sent_system = llm._async_client.messages.last_kwargs["system"]
    assert sent_system == blocks


@pytest.mark.asyncio
async def test_generate_stream_async_forwards_timeout():
    fake = _FakeAsyncStream(["x"])
    llm = AnthropicLLM(api_key="test")
    llm._async_client = _FakeAsyncClient(fake)

    async for _ in llm.generate_stream_async(
        [{"role": "user", "content": "hi"}], "system", timeout=42.0
    ):
        pass

    assert llm._async_client.messages.last_kwargs.get("timeout") == 42.0


def test_async_client_lazy_constructed():
    """The async client should not be built at AnthropicLLM construction —
    it's lazy so existing sync-only callers don't pay the import-time cost
    or break in environments without async deps."""
    llm = AnthropicLLM(api_key="test")
    assert llm._async_client is None  # sentinel

    # Touching the async_client property constructs it.
    client = llm.async_client
    assert client is not None
    assert llm._async_client is client  # cached


def test_pricing_for_still_works_on_async_path():
    """v1.3.0 per-model pricing: ``pricing_for`` must still return the right
    rate after the async additions (regression check on the audit fix)."""
    llm = AnthropicLLM(api_key="test")
    haiku = llm.pricing_for("claude-haiku-4-5-20251001")
    sonnet = llm.pricing_for("claude-sonnet-4-6")
    assert haiku["input"] < sonnet["input"], "haiku should still be cheaper than sonnet"


def test_sync_generate_stream_unchanged():
    """Back-compat: the sync ``generate_stream`` path keeps working after
    we added the async sibling."""
    llm = AnthropicLLM(api_key="test")
    fake_sync_stream = MagicMock()
    fake_sync_stream.__enter__ = MagicMock(return_value=fake_sync_stream)
    fake_sync_stream.__exit__ = MagicMock(return_value=False)
    fake_sync_stream.text_stream = iter(["a", "b"])
    llm.client = MagicMock()
    llm.client.messages.stream.return_value = fake_sync_stream

    out = list(llm.generate_stream([{"role": "user", "content": "hi"}], "system"))
    assert out == ["a", "b"]
