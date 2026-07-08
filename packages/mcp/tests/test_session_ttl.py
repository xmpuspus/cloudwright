from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

from cloudwright.session_store import SessionStore
from cloudwright_mcp.ttl import DEFAULT_TTL_DAYS, session_ttl_seconds, sweep_expired_sessions


def _make_mock_cs():
    session = MagicMock()
    session.current_spec = None
    session.last_usage = {"input_tokens": 10, "output_tokens": 5}
    session.history = []
    session.send.return_value = ("ok", None)
    session.get_usage_summary.return_value = {"total_input": 10, "total_output": 5}
    session.to_dict.return_value = {
        "session_id": "test",
        "history": [],
        "current_spec": None,
        "constraints": None,
        "cumulative_usage": {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0},
        "_error_hints": [],
        "max_history_turns": 50,
        "created_at": 0,
    }
    return session


def _backdate(tmpdir: str, session_id: str, saved_at: float) -> None:
    path = Path(tmpdir) / f"{session_id}.json"
    data = json.loads(path.read_text())
    data["saved_at"] = saved_at
    path.write_text(json.dumps(data))


class TestSweepExpiredSessions:
    def test_old_session_is_swept(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=Path(tmpdir))
            store.save("old", _make_mock_cs())
            _backdate(tmpdir, "old", time.time() - (DEFAULT_TTL_DAYS + 1) * 86400)

            deleted = sweep_expired_sessions(store=store)

            assert deleted == ["old"]
            assert not (Path(tmpdir) / "old.json").exists()

    def test_fresh_session_is_kept(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=Path(tmpdir))
            store.save("fresh", _make_mock_cs())

            deleted = sweep_expired_sessions(store=store)

            assert deleted == []
            assert any(s["session_id"] == "fresh" for s in store.list_sessions())

    def test_old_and_fresh_sessions_together(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=Path(tmpdir))
            store.save("old", _make_mock_cs())
            store.save("fresh", _make_mock_cs())
            _backdate(tmpdir, "old", time.time() - (DEFAULT_TTL_DAYS + 1) * 86400)

            deleted = sweep_expired_sessions(store=store)
            remaining = {s["session_id"] for s in store.list_sessions()}

            assert deleted == ["old"]
            assert remaining == {"fresh"}

    def test_ttl_zero_disables_sweep(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=Path(tmpdir))
            store.save("old", _make_mock_cs())
            _backdate(tmpdir, "old", 0)

            deleted = sweep_expired_sessions(store=store, ttl_seconds=0)

            assert deleted == []
            assert (Path(tmpdir) / "old.json").exists()

    def test_custom_ttl_seconds_boundary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=Path(tmpdir))
            store.save("borderline", _make_mock_cs())
            _backdate(tmpdir, "borderline", time.time() - 120)

            deleted = sweep_expired_sessions(store=store, ttl_seconds=60)

            assert deleted == ["borderline"]

    def test_missing_timestamp_is_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=Path(tmpdir))
            store.save("no_stamp", _make_mock_cs())
            path = Path(tmpdir) / "no_stamp.json"
            data = json.loads(path.read_text())
            data.pop("saved_at", None)
            data.pop("created_at", None)
            path.write_text(json.dumps(data))

            deleted = sweep_expired_sessions(store=store)

            assert deleted == []
            assert path.exists()


class TestSessionTtlSecondsResolution:
    def test_env_var_overrides_default(self, monkeypatch):
        monkeypatch.setenv("CLOUDWRIGHT_MCP_SESSION_TTL_DAYS", "1")
        assert session_ttl_seconds() == 86400

    def test_unset_env_var_uses_default(self, monkeypatch):
        monkeypatch.delenv("CLOUDWRIGHT_MCP_SESSION_TTL_DAYS", raising=False)
        assert session_ttl_seconds() == DEFAULT_TTL_DAYS * 86400

    def test_invalid_env_var_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("CLOUDWRIGHT_MCP_SESSION_TTL_DAYS", "not-a-number")
        assert session_ttl_seconds() == DEFAULT_TTL_DAYS * 86400


class TestChatListSessionsTriggersSweep:
    def test_chat_list_sessions_invokes_sweep(self, monkeypatch, register_tools):
        import cloudwright_mcp.tools.session as mod

        called = {}

        def fake_sweep(*args, **kwargs):
            called["ran"] = True
            return []

        monkeypatch.setattr(mod, "sweep_expired_sessions", fake_sweep)
        fns = register_tools(mod)

        fns["chat_list_sessions"]()

        assert called.get("ran") is True


class TestCreateServerTriggersSweepAtStartup:
    def test_create_server_invokes_sweep_once(self, monkeypatch):
        import cloudwright_mcp.server as server_mod

        called = {"count": 0}

        def fake_sweep(*args, **kwargs):
            called["count"] += 1
            return []

        monkeypatch.setattr(server_mod, "sweep_expired_sessions", fake_sweep)

        server_mod.create_server(tools=set())

        assert called["count"] == 1
