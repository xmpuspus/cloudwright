"""AsyncOpenAI cancel-safe streaming.

Mirror of ``test_async_anthropic_stream.py`` for the OpenAI provider. The
async streaming path is the v1.4 fix for the orphan-thread + LLM-bill
findings in ``docs/audits/03-reliability-perf.md``.

Verifies:
1. ``OpenAILLM.generate_stream_async`` yields chunks via ``async for``.
2. Closing the iterator early triggers the SDK's close path so the upstream
   httpx connection is released — no orphaned coroutine billing tokens.
3. ``stream_options={"include_usage": True}`` is set so the final chunk
   carries token counts (otherwise the cost UI silently estimates from
   character count, which the audit caught drifting 5-15%).
4. Per-call ``timeout=`` is forwarded.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from cloudwright.llm.openai import OpenAILLM


def _chunk(content: str | None):
    return MagicMock(choices=[MagicMock(delta=MagicMock(content=content))])


class _FakeAsyncStream:
    """Stand-in for the AsyncOpenAI streaming iterator. Tracks ``aclose``."""

    def __init__(self, chunks: list):
        self._chunks = list(chunks)
        self.aclosed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._chunks:
            raise StopAsyncIteration
        await asyncio.sleep(0)  # yield, so cancellation between chunks is observable
        return self._chunks.pop(0)

    async def aclose(self):
        self.aclosed = True


class _FakeAsyncCompletions:
    def __init__(self, fake_stream: _FakeAsyncStream):
        self._fake_stream = fake_stream
        self.last_kwargs: dict | None = None

    async def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._fake_stream


class _FakeAsyncChat:
    def __init__(self, fake_stream: _FakeAsyncStream):
        self.completions = _FakeAsyncCompletions(fake_stream)


class _FakeAsyncClient:
    def __init__(self, fake_stream: _FakeAsyncStream):
        self.chat = _FakeAsyncChat(fake_stream)


@pytest.mark.asyncio
async def test_generate_stream_async_yields_chunks():
    fake = _FakeAsyncStream([_chunk("hel"), _chunk("lo"), _chunk(None)])
    llm = OpenAILLM(api_key="test")
    llm._async_client = _FakeAsyncClient(fake)

    chunks: list[str] = []
    async for c in llm.generate_stream_async([{"role": "user", "content": "hi"}], "system"):
        chunks.append(c)

    assert chunks == ["hel", "lo"]
    assert fake.aclosed, "AsyncStream.aclose must run after normal completion"


@pytest.mark.asyncio
async def test_generate_stream_async_closes_on_consumer_disconnect():
    """Consumer breaks early; the ``finally`` block in
    ``generate_stream_async`` must call ``aclose`` so the upstream httpx
    connection is released."""
    fake = _FakeAsyncStream([_chunk("a"), _chunk("b"), _chunk("c"), _chunk(None)])
    llm = OpenAILLM(api_key="test")
    llm._async_client = _FakeAsyncClient(fake)

    agen = llm.generate_stream_async([{"role": "user", "content": "hi"}], "system")
    first = await agen.__anext__()
    assert first == "a"
    await agen.aclose()

    assert fake.aclosed, "stream must be aclosed when consumer aborts mid-iteration"


@pytest.mark.asyncio
async def test_generate_stream_async_sets_include_usage():
    """Without ``stream_options.include_usage``, the final chunk carries no
    token counts and we silently fall back to a 5-15% wrong estimate."""
    fake = _FakeAsyncStream([_chunk(None)])
    llm = OpenAILLM(api_key="test")
    llm._async_client = _FakeAsyncClient(fake)

    async for _ in llm.generate_stream_async([{"role": "user", "content": "hi"}], "system"):
        pass

    kwargs = llm._async_client.chat.completions.last_kwargs
    assert kwargs.get("stream_options") == {"include_usage": True}


@pytest.mark.asyncio
async def test_generate_stream_async_forwards_timeout():
    fake = _FakeAsyncStream([_chunk(None)])
    llm = OpenAILLM(api_key="test")
    llm._async_client = _FakeAsyncClient(fake)

    async for _ in llm.generate_stream_async([{"role": "user", "content": "hi"}], "system", timeout=42.0):
        pass

    assert llm._async_client.chat.completions.last_kwargs.get("timeout") == 42.0


@pytest.mark.asyncio
async def test_generate_stream_async_prepends_system_message():
    """OpenAI sends system as the first ``role: system`` message (unlike
    Anthropic which uses a top-level ``system`` arg)."""
    fake = _FakeAsyncStream([_chunk(None)])
    llm = OpenAILLM(api_key="test")
    llm._async_client = _FakeAsyncClient(fake)

    async for _ in llm.generate_stream_async([{"role": "user", "content": "hi"}], "you are a bot"):
        pass

    msgs = llm._async_client.chat.completions.last_kwargs["messages"]
    assert msgs[0] == {"role": "system", "content": "you are a bot"}
    assert msgs[1] == {"role": "user", "content": "hi"}


def test_async_client_lazy_constructed():
    llm = OpenAILLM(api_key="test")
    assert llm._async_client is None

    client = llm.async_client
    assert client is not None
    assert llm._async_client is client


def test_pricing_for_still_works_on_async_path():
    llm = OpenAILLM(api_key="test")
    mini = llm.pricing_for("gpt-5-mini-2024-12-01")
    full = llm.pricing_for("gpt-5.2")
    assert mini["input"] < full["input"]
