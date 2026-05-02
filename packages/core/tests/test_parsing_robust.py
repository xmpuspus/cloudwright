"""Tests for the JSONDecoder-based _extract_json (audit-fix v1.3)."""

from __future__ import annotations

import json

import pytest
from cloudwright.parsing import _extract_json


def test_parsing_plain_json():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_parsing_with_code_fence():
    text = 'Here you go:\n```json\n{"a": 1, "b": 2}\n```\n'
    assert _extract_json(text) == {"a": 1, "b": 2}


def test_parsing_with_xml_wrapper():
    """LLMs sometimes wrap JSON in <json>...</json> XML tags."""
    text = '<json>{"a": 1, "b": [1, 2, 3]}</json>'
    assert _extract_json(text) == {"a": 1, "b": [1, 2, 3]}


def test_parsing_nested_json_string():
    """A JSON string value containing escaped JSON must not truncate parsing.

    The hand-rolled brace counter previously could miscount when a string
    value contained an embedded ``{`` or ``}``. JSONDecoder.raw_decode
    handles this correctly.
    """
    payload = {"description": 'see {"foo": 1}', "id": "x"}
    text = "preamble " + json.dumps(payload) + " trailing prose"
    assert _extract_json(text) == payload


def test_parsing_nested_object():
    text = 'noise {"outer": {"inner": {"deep": "value"}}, "list": [1, {"a": 2}]}\n'
    assert _extract_json(text) == {
        "outer": {"inner": {"deep": "value"}},
        "list": [1, {"a": 2}],
    }


def test_parsing_unicode_and_escapes():
    """Backslash escapes and unicode must be preserved."""
    text = '{"name": "caf\\u00e9", "path": "C:\\\\Users\\\\me"}'
    parsed = _extract_json(text)
    assert parsed == {"name": "café", "path": "C:\\Users\\me"}


def test_parsing_array_top_level():
    text = '```json\n[1, 2, {"x": 3}]\n```'
    assert _extract_json(text) == [1, 2, {"x": 3}]


def test_parsing_no_json_raises():
    with pytest.raises(ValueError, match="No JSON object found"):
        _extract_json("just some prose without any json")


def test_parsing_invalid_json_raises():
    with pytest.raises(ValueError):
        _extract_json('{"unterminated": ')
