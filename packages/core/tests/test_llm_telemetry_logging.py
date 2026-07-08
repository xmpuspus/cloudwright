"""Regression: the llm_call telemetry line must survive configure_logging().

The CLI enables root INFO via configure_logging() on every invocation. Passing
structlog-style kwargs to the stdlib logger returned by get_logger() raised
TypeError: Logger._log() got an unexpected keyword argument 'model'
AFTER the SDK call returned, so every live design/modify billed tokens and then
crashed. pytest masked it because root stays at WARNING and info() short-circuits.
These tests pin the fix by running the providers with root at INFO.
"""

from __future__ import annotations

import logging as stdlib_logging
from unittest.mock import MagicMock

import cloudwright.logging as cw_logging
import pytest
from cloudwright.llm.anthropic import AnthropicLLM
from cloudwright.llm.openai import OpenAILLM


@pytest.fixture()
def info_level_logging():
    root = stdlib_logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_flag = cw_logging._configured
    cw_logging._configured = False
    cw_logging.configure_logging()
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
    cw_logging._configured = saved_flag


def _anthropic_response(text="ok"):
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.usage.input_tokens = 10
    response.usage.output_tokens = 5
    response.usage.cache_read_input_tokens = 0
    response.usage.cache_creation_input_tokens = 0
    return response


def _openai_response(text="ok"):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=text))]
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 5
    response.usage.prompt_tokens_details = MagicMock(cached_tokens=0)
    return response


def test_anthropic_call_survives_configure_logging(info_level_logging):
    llm = AnthropicLLM(api_key="test")
    llm.client = MagicMock()
    llm.client.messages.create.return_value = _anthropic_response("result")

    text, usage = llm.generate([{"role": "user", "content": "hi"}], "system")

    assert text == "result"
    assert usage["input_tokens"] == 10


def test_openai_call_survives_configure_logging(info_level_logging):
    llm = OpenAILLM(api_key="test")
    llm.client = MagicMock()
    llm.client.chat.completions.create.return_value = _openai_response("result")

    text, usage = llm.generate([{"role": "user", "content": "hi"}], "system")

    assert text == "result"
    assert usage["input_tokens"] == 10
