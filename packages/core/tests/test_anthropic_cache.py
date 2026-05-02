"""Anthropic prompt-cache surgery tests.

The fix splits the system prompt into a stable cached prefix + a small
variable suffix. The stable block carries ``cache_control: ephemeral`` so
follow-up turns hit Anthropic's prompt cache instead of paying full input-token
cost on a 23 KB system prompt.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from cloudwright.architect import ConversationSession
from cloudwright.llm.anthropic import AnthropicLLM


def _mk_anthropic_response(text="ok"):
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.usage.input_tokens = 100
    response.usage.output_tokens = 50
    response.usage.cache_read_input_tokens = 80
    response.usage.cache_creation_input_tokens = 0
    return response


def test_anthropic_string_system_wraps_in_block_with_cache_control():
    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()
    llm.client.messages.create.return_value = _mk_anthropic_response()

    llm.generate([{"role": "user", "content": "hi"}], "STABLE_SYSTEM_PROMPT")

    kwargs = llm.client.messages.create.call_args.kwargs
    system = kwargs["system"]
    assert isinstance(system, list), "system must be a list of blocks for Anthropic"
    assert system[0]["type"] == "text"
    assert system[0]["text"] == "STABLE_SYSTEM_PROMPT"
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_anthropic_list_system_passed_through():
    """Pre-built block lists from the session pass through unmodified."""
    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()
    llm.client.messages.create.return_value = _mk_anthropic_response()

    blocks = [
        {"type": "text", "text": "STABLE", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "VARIABLE_HINTS"},
    ]
    llm.generate([{"role": "user", "content": "hi"}], blocks)

    kwargs = llm.client.messages.create.call_args.kwargs
    assert kwargs["system"] == blocks


def test_anthropic_usage_surfaces_cache_read_tokens():
    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()
    llm.client.messages.create.return_value = _mk_anthropic_response()

    _, usage = llm.generate([{"role": "user", "content": "hi"}], "system")
    assert usage["cached_tokens"] == 80


def test_session_splits_system_into_stable_and_variable(monkeypatch):
    """ConversationSession must send 2 blocks for Anthropic when there are
    error hints — stable prefix cached, hints as a separate uncached block.

    We patch CHAT_SYSTEM to a known-large string so the cache_control assertion
    is independent of upstream prompt-size drift.
    """
    import cloudwright.session as session_mod

    big_prompt = "STABLE_PROMPT " * 400  # ~1400 estimated tokens
    monkeypatch.setattr(session_mod, "CHAT_SYSTEM", big_prompt)

    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()
    llm.client.messages.create.return_value = _mk_anthropic_response()

    session = ConversationSession(llm=llm)
    session._add_error_hint("Do not remove existing components unless explicitly asked")
    session.send("design a web app on aws")

    kwargs = llm.client.messages.create.call_args.kwargs
    system = kwargs["system"]
    assert isinstance(system, list)
    # Stable prefix + variable hints = 2 blocks.
    assert len(system) == 2
    # Above 1024 estimated tokens — cache_control must be set on the stable
    # block so follow-up turns hit the prompt cache.
    assert system[0].get("cache_control") == {"type": "ephemeral"}
    # Hints block should NOT have cache_control — it changes every turn.
    assert "cache_control" not in system[1]
    assert "Do not remove existing components" in system[1]["text"]


def test_session_omits_variable_block_when_no_hints(monkeypatch):
    """No hints, no trim summary — only the stable block is sent."""
    import cloudwright.session as session_mod

    big_prompt = "STABLE_PROMPT " * 400
    monkeypatch.setattr(session_mod, "CHAT_SYSTEM", big_prompt)

    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()
    llm.client.messages.create.return_value = _mk_anthropic_response()

    session = ConversationSession(llm=llm)
    session.send("design a web app on aws")

    kwargs = llm.client.messages.create.call_args.kwargs
    system = kwargs["system"]
    assert len(system) == 1
    assert system[0].get("cache_control") == {"type": "ephemeral"}


def test_session_skips_cache_control_below_threshold(monkeypatch):
    """Anthropic ignores cache_control below 1024 tokens — don't bother
    setting it for tiny system prompts."""
    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()
    llm.client.messages.create.return_value = _mk_anthropic_response()

    session = ConversationSession(llm=llm)
    # Force a tiny system prompt by patching CHAT_SYSTEM at the call site.
    import cloudwright.session as session_mod

    monkeypatch.setattr(session_mod, "CHAT_SYSTEM", "tiny")
    session.send("design a web app on aws")

    kwargs = llm.client.messages.create.call_args.kwargs
    system = kwargs["system"]
    assert system[0]["text"] == "tiny"
    # Below threshold — cache_control should not be set.
    assert "cache_control" not in system[0]
