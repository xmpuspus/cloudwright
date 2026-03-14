"""Tests for retry logic in Anthropic and OpenAI LLM providers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import anthropic
import openai
import pytest
from cloudwright.llm.anthropic import AnthropicLLM
from cloudwright.llm.openai import OpenAILLM


def _make_anthropic_response(text="ok"):
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.usage.input_tokens = 10
    response.usage.output_tokens = 5
    return response


def _make_openai_response(text="ok"):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=text))]
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 5
    return response


@patch("time.sleep")
def test_anthropic_retries_on_rate_limit(mock_sleep):
    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()
    good_response = _make_anthropic_response("result")

    llm.client.messages.create.side_effect = [
        anthropic.RateLimitError("rate limit", response=MagicMock(status_code=429), body={}),
        good_response,
    ]

    text, usage = llm.generate([{"role": "user", "content": "hi"}], "system")

    assert text == "result"
    assert llm.client.messages.create.call_count == 2
    mock_sleep.assert_called_once()


@patch("time.sleep")
def test_anthropic_retries_on_connection_error(mock_sleep):
    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()
    good_response = _make_anthropic_response("result")

    llm.client.messages.create.side_effect = [
        anthropic.APIConnectionError(request=MagicMock()),
        good_response,
    ]

    text, _ = llm.generate([{"role": "user", "content": "hi"}], "system")

    assert text == "result"
    assert llm.client.messages.create.call_count == 2


@patch("time.sleep")
def test_anthropic_raises_after_max_retries(mock_sleep):
    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()

    llm.client.messages.create.side_effect = anthropic.RateLimitError(
        "rate limit", response=MagicMock(status_code=429), body={}
    )

    with pytest.raises(anthropic.RateLimitError):
        llm.generate([{"role": "user", "content": "hi"}], "system")

    assert llm.client.messages.create.call_count == 3


@patch("time.sleep")
def test_openai_retries_on_rate_limit(mock_sleep):
    llm = OpenAILLM(api_key="test")
    llm.client = MagicMock()
    good_response = _make_openai_response("result")

    llm.client.chat.completions.create.side_effect = [
        openai.RateLimitError("rate limit", response=MagicMock(status_code=429), body={}),
        good_response,
    ]

    text, _ = llm.generate([{"role": "user", "content": "hi"}], "system")

    assert text == "result"
    assert llm.client.chat.completions.create.call_count == 2
    mock_sleep.assert_called_once()


@patch("time.sleep")
def test_openai_retries_on_connection_error(mock_sleep):
    llm = OpenAILLM(api_key="test")
    llm.client = MagicMock()
    good_response = _make_openai_response("result")

    llm.client.chat.completions.create.side_effect = [
        openai.APIConnectionError(request=MagicMock()),
        good_response,
    ]

    text, _ = llm.generate([{"role": "user", "content": "hi"}], "system")

    assert text == "result"
    assert llm.client.chat.completions.create.call_count == 2


@patch("time.sleep")
def test_openai_raises_after_max_retries(mock_sleep):
    llm = OpenAILLM(api_key="test")
    llm.client = MagicMock()

    llm.client.chat.completions.create.side_effect = openai.RateLimitError(
        "rate limit", response=MagicMock(status_code=429), body={}
    )

    with pytest.raises(openai.RateLimitError):
        llm.generate([{"role": "user", "content": "hi"}], "system")

    assert llm.client.chat.completions.create.call_count == 3
