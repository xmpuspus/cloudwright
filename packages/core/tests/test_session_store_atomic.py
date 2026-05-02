"""Tests for atomic SessionStore writes (audit-fix v1.3)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from cloudwright.architect import ConversationSession
from cloudwright.session_store import SessionStore, _atomic_write_text


def _mock_llm():
    llm = MagicMock()
    llm.model_name = "mock-model"
    llm.pricing = {"input": 0.003, "output": 0.015}
    return llm


def _make_session() -> ConversationSession:
    return ConversationSession(llm=_mock_llm())


def test_atomic_write_creates_file(tmp_path):
    target = tmp_path / "demo.json"
    _atomic_write_text(target, '{"hello": "world"}')
    assert target.exists()
    assert json.loads(target.read_text()) == {"hello": "world"}


def test_atomic_write_leaves_no_tmp_files_on_success(tmp_path):
    target = tmp_path / "demo.json"
    _atomic_write_text(target, '{"a": 1}')
    leftovers = [p for p in tmp_path.iterdir() if p.name != "demo.json"]
    assert leftovers == [], f"unexpected leftover tmp files: {leftovers}"


def test_atomic_write_failure_does_not_leak_tmp(tmp_path):
    target = tmp_path / "demo.json"
    target.write_text('{"old": true}')

    # Simulate a crash by making os.replace raise
    with patch("cloudwright.session_store.os.replace", side_effect=OSError("boom")):
        with pytest.raises(OSError):
            _atomic_write_text(target, '{"new": true}')

    # Original file is intact
    assert json.loads(target.read_text()) == {"old": True}
    # No .tmp leftovers
    tmp_leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
    assert tmp_leftovers == [], f"tmp file leaked: {tmp_leftovers}"


def test_save_uses_atomic_replace(tmp_path):
    """The save() path must call os.replace, not write_text directly."""
    store = SessionStore(base_dir=tmp_path)
    session = _make_session()

    with patch("cloudwright.session_store.os.replace") as mock_replace:
        # raise after replace would have run, so just don't perform it
        mock_replace.side_effect = lambda src, dst: None
        store.save("alpha", session)

    assert mock_replace.called, "atomic save must use os.replace"


def test_save_simulated_kill_mid_write_preserves_old_file(tmp_path):
    """If the process is killed mid-write, the old session file must survive."""
    store = SessionStore(base_dir=tmp_path)
    session = _make_session()

    # First successful save establishes baseline content.
    store.save("alpha", session)
    target = tmp_path / "alpha.json"
    original = target.read_text()
    assert original  # sanity

    # Now simulate a SIGKILL between tmp write and replace by mocking os.replace
    # so it never runs. The temp file gets cleaned, and the original file stays.
    with patch("cloudwright.session_store.os.replace", side_effect=OSError("simulated kill")):
        with pytest.raises(OSError):
            store.save("alpha", session)

    # Original file must be untouched and still parseable
    assert target.read_text() == original
    assert json.loads(target.read_text())  # still valid JSON


def test_save_then_load_round_trip(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = _make_session()
    store.save("alpha", session)

    # No tmp files left behind
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == []

    # File is valid JSON
    data = json.loads((tmp_path / "alpha.json").read_text())
    assert "saved_at" in data
