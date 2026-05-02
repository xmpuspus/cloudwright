"""OpenAI streaming connection-pool-leak fix.

Pre-fix bug: ``openai.py:_call`` (streaming variant) iterated the SDK
``Stream`` object without ever closing it. On early consumer break (client
disconnect, exception in the consumer), the underlying HTTP response stayed
in the connection pool until garbage-collected.

The fix wraps iteration in ``try/finally`` and calls ``stream.close()``
unconditionally.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from cloudwright.llm.openai import OpenAILLM


class _FakeStream:
    """Stand-in for openai.Stream — tracks close()."""

    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.closed = False

    def __iter__(self):
        return iter(self._chunks)

    def close(self):
        self.closed = True


def _chunk(content: str | None):
    return MagicMock(choices=[MagicMock(delta=MagicMock(content=content))])


def test_stream_closed_after_normal_completion():
    llm = OpenAILLM(api_key="test")
    fake = _FakeStream([_chunk("hel"), _chunk("lo"), _chunk(None)])
    llm.client = MagicMock()
    llm.client.chat.completions.create.return_value = fake

    chunks = list(llm.generate_stream([{"role": "user", "content": "hi"}], "system"))

    assert chunks == ["hel", "lo"]
    assert fake.closed, "stream.close() must be called after normal completion"


def test_stream_closed_on_consumer_early_break():
    """Simulate a consumer that breaks out mid-stream (e.g. client disconnect)
    by raising inside the iteration. The finally block must still close()."""
    llm = OpenAILLM(api_key="test")
    fake = _FakeStream([_chunk("hel"), _chunk("lo"), _chunk("wor"), _chunk("ld")])
    llm.client = MagicMock()
    llm.client.chat.completions.create.return_value = fake

    gen = llm.generate_stream([{"role": "user", "content": "hi"}], "system")
    next(gen)  # consume first chunk
    # Drop the generator — Python will GeneratorExit it, triggering finally.
    gen.close()

    assert fake.closed, "stream.close() must be called on early break"


def test_stream_options_include_usage_set():
    """Per OpenAI streaming docs, must set stream_options.include_usage=True
    or the final chunk carries no token counts (and we can't bill or
    cache-track)."""
    llm = OpenAILLM(api_key="test")
    fake = _FakeStream([_chunk(None)])
    llm.client = MagicMock()
    llm.client.chat.completions.create.return_value = fake

    list(llm.generate_stream([{"role": "user", "content": "hi"}], "system"))

    kwargs = llm.client.chat.completions.create.call_args.kwargs
    assert kwargs.get("stream_options") == {"include_usage": True}
