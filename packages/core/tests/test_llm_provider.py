"""Tests for LLM provider routing and model override."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from cloudwright.llm import get_llm
from cloudwright.llm.anthropic import AnthropicLLM
from cloudwright.llm.base import BaseLLM
from cloudwright.llm.openai import OpenAILLM


class TestGetLLM:
    """Tests for get_llm() factory routing."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False)
    def test_auto_detect_anthropic(self):
        env = dict(os.environ)
        env.pop("CLOUDWRIGHT_LLM_PROVIDER", None)
        env.pop("OPENAI_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            llm = get_llm()
            assert isinstance(llm, AnthropicLLM)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False)
    def test_auto_detect_openai(self):
        env = dict(os.environ)
        env.pop("CLOUDWRIGHT_LLM_PROVIDER", None)
        env.pop("ANTHROPIC_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            llm = get_llm()
            assert isinstance(llm, OpenAILLM)

    @patch.dict(os.environ, {"CLOUDWRIGHT_LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test"})
    def test_explicit_openai_provider(self):
        llm = get_llm()
        assert isinstance(llm, OpenAILLM)

    @patch.dict(os.environ, {"CLOUDWRIGHT_LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-ant-test"})
    def test_explicit_anthropic_provider(self):
        llm = get_llm()
        assert isinstance(llm, AnthropicLLM)

    def test_no_keys_raises(self):
        env = dict(os.environ)
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("OPENAI_API_KEY", None)
        env.pop("CLOUDWRIGHT_LLM_PROVIDER", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="No LLM provider"):
                get_llm()


class TestModelOverride:
    """Tests for CLOUDWRIGHT_MODEL env var override."""

    @patch.dict(os.environ, {"CLOUDWRIGHT_MODEL": "claude-opus-4-6"})
    def test_anthropic_model_override(self):
        # Re-import to pick up env var at module level
        import importlib

        import cloudwright.llm.anthropic as mod

        importlib.reload(mod)
        assert mod.GENERATE_MODEL == "claude-opus-4-6"
        # Restore
        os.environ.pop("CLOUDWRIGHT_MODEL", None)
        importlib.reload(mod)

    @patch.dict(os.environ, {"CLOUDWRIGHT_MODEL": "gpt-5"})
    def test_openai_model_override(self):
        import importlib

        import cloudwright.llm.openai as mod

        importlib.reload(mod)
        assert mod.GENERATE_MODEL == "gpt-5"
        # Restore
        os.environ.pop("CLOUDWRIGHT_MODEL", None)
        importlib.reload(mod)


class TestOpenAILLM:
    """Tests for OpenAI LLM provider."""

    def test_implements_base_interface(self):
        llm = OpenAILLM(api_key="test")
        assert isinstance(llm, BaseLLM)
        assert llm.model_name is not None
        assert "input" in llm.pricing
        assert "output" in llm.pricing

    def test_generate_prepends_system_message(self):
        llm = OpenAILLM(api_key="test")
        llm.client = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content="hello"))]
        response.usage.prompt_tokens = 10
        response.usage.completion_tokens = 5
        llm.client.chat.completions.create.return_value = response

        text, usage = llm.generate([{"role": "user", "content": "hi"}], "You are helpful")
        assert text == "hello"

        call_args = llm.client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"

    def test_generate_stream_yields_chunks(self):
        llm = OpenAILLM(api_key="test")
        llm.client = MagicMock()

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="hel"))]
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content="lo"))]
        chunk3 = MagicMock()
        chunk3.choices = [MagicMock(delta=MagicMock(content=None))]

        llm.client.chat.completions.create.return_value = iter([chunk1, chunk2, chunk3])

        chunks = list(llm.generate_stream([{"role": "user", "content": "hi"}], "system"))
        assert chunks == ["hel", "lo"]

    def test_estimate_tokens(self):
        llm = OpenAILLM(api_key="test")
        assert llm.estimate_tokens("hello world") > 0
