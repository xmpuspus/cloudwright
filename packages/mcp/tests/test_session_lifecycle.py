from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from cloudwright.session_store import SessionStore


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


def _register_tools():
    mcp = MagicMock()
    captured_fn = {}

    def tool_decorator():
        def decorator(fn):
            captured_fn[fn.__name__] = fn
            return fn

        return decorator

    mcp.tool = tool_decorator

    import cloudwright_mcp.tools.session as mod

    mod.register(mcp)
    return captured_fn


class TestSessionCreation:
    def test_session_creation_via_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=Path(tmpdir))
            mock_cs = _make_mock_cs()
            store.save("test123", mock_cs)
            sessions = store.list_sessions()
            assert any(s["session_id"] == "test123" for s in sessions)


class TestSessionSend:
    def test_session_send_unknown_id(self):
        fns = _register_tools()
        result = fns["chat_send"](session_id="doesnotexist", message="hi")
        assert "error" in result


class TestSessionDelete:
    def test_session_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=Path(tmpdir))
            mock_cs = _make_mock_cs()
            store.save("del_test", mock_cs)
            assert store.delete("del_test") is True
            sessions = store.list_sessions()
            assert not any(s["session_id"] == "del_test" for s in sessions)

    def test_delete_unknown_session(self):
        fns = _register_tools()
        result = fns["chat_delete_session"](session_id="ghost")
        assert "error" in result


class TestSessionPersistence:
    def test_sessions_survive_restart(self):
        """Sessions persisted via SessionStore survive across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = SessionStore(base_dir=Path(tmpdir))
            mock_cs = _make_mock_cs()
            store1.save("persist_test", mock_cs)

            # Simulate restart — new SessionStore instance, same directory
            store2 = SessionStore(base_dir=Path(tmpdir))
            sessions = store2.list_sessions()
            assert any(s["session_id"] == "persist_test" for s in sessions)


class TestListSessions:
    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(base_dir=Path(tmpdir))
            for i in range(3):
                mock_cs = _make_mock_cs()
                store.save(f"list_test_{i}", mock_cs)
            sessions = store.list_sessions()
            assert len(sessions) == 3
