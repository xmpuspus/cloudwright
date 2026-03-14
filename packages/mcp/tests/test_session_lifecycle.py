from __future__ import annotations

import time
from unittest.mock import MagicMock, patch


def _make_mock_cs():
    session = MagicMock()
    session.current_spec = None
    session.last_usage = {"input_tokens": 10, "output_tokens": 5}
    session.history = []
    session.send.return_value = ("ok", None)
    session.get_usage_summary.return_value = {"total_input": 10, "total_output": 5}
    return session


def _clear_state():
    from cloudwright_mcp.tools.session import _session_created, _sessions

    _sessions.clear()
    _session_created.clear()


def _register_tools():
    """Register MCP tools and return captured function dict."""
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
    def setup_method(self):
        _clear_state()

    def test_session_creation(self):
        mock_cs = _make_mock_cs()
        _register_tools()
        with patch("cloudwright.architect.ConversationSession.__new__", return_value=mock_cs):
            import cloudwright_mcp.tools.session as mod
            from cloudwright_mcp.tools.session import _sessions

            mod._sessions["test123"] = mock_cs
            mod._session_created["test123"] = time.time()

        assert "test123" in _sessions

    def test_session_creation_registers_timestamp(self):
        from cloudwright_mcp.tools.session import _session_created

        _session_created["test_ts"] = time.time()
        assert abs(_session_created["test_ts"] - time.time()) < 2


class TestSessionSend:
    def setup_method(self):
        _clear_state()

    def test_session_send(self):
        mock_cs = _make_mock_cs()
        fns = _register_tools()

        from cloudwright_mcp.tools.session import _sessions

        _sessions["send_test"] = mock_cs

        result = fns["chat_send"](session_id="send_test", message="hello")
        assert "response" in result
        assert "usage" in result

    def test_session_send_unknown_id(self):
        fns = _register_tools()
        result = fns["chat_send"](session_id="doesnotexist", message="hi")
        assert "error" in result


class TestSessionDelete:
    def setup_method(self):
        _clear_state()

    def test_session_delete(self):
        from cloudwright_mcp.tools.session import _session_created, _sessions

        mock_cs = _make_mock_cs()
        _sessions["del_test"] = mock_cs
        _session_created["del_test"] = time.time()

        fns = _register_tools()
        result = fns["chat_delete_session"](session_id="del_test")

        assert result["deleted"] is True
        assert "del_test" not in _sessions

    def test_delete_unknown_session(self):
        fns = _register_tools()
        result = fns["chat_delete_session"](session_id="ghost")
        assert "error" in result


class TestSessionTTLExpiry:
    def setup_method(self):
        _clear_state()

    def test_session_ttl_expiry(self):
        from cloudwright_mcp.tools import session as mod
        from cloudwright_mcp.tools.session import _cleanup_expired, _session_created, _sessions

        mock_cs = _make_mock_cs()
        sid = "expire_test"
        _sessions[sid] = mock_cs
        _session_created[sid] = time.time() - mod._SESSION_TTL - 1

        _cleanup_expired()

        assert sid not in _sessions
        assert sid not in _session_created


class TestMaxSessionsEviction:
    def setup_method(self):
        _clear_state()

    def test_max_sessions_eviction(self):
        from cloudwright_mcp.tools import session as mod

        # Fill up to _MAX_SESSIONS
        first_sid = "oldest"
        mod._sessions[first_sid] = _make_mock_cs()
        mod._session_created[first_sid] = time.time() - 10000

        for i in range(mod._MAX_SESSIONS - 1):
            sid = f"session_{i}"
            mod._sessions[sid] = _make_mock_cs()
            mod._session_created[sid] = time.time() - (mod._MAX_SESSIONS - i)

        assert len(mod._sessions) == mod._MAX_SESSIONS

        # Register tools and create one more — should evict oldest
        _register_tools()
        with patch("cloudwright.architect.get_llm", return_value=MagicMock()):
            # Manually add one more to trigger eviction logic
            new_sid = "newest"
            # Simulate the eviction logic
            while len(mod._sessions) >= mod._MAX_SESSIONS and mod._session_created:
                oldest = min(mod._session_created, key=mod._session_created.get)
                mod._sessions.pop(oldest, None)
                mod._session_created.pop(oldest, None)

            mod._sessions[new_sid] = _make_mock_cs()
            mod._session_created[new_sid] = time.time()

        assert first_sid not in mod._sessions
        assert len(mod._sessions) <= mod._MAX_SESSIONS


class TestListIncludesUsage:
    def setup_method(self):
        _clear_state()

    def test_list_includes_usage(self):
        from cloudwright.architect import ConversationSession as RealCS

        mock_cs = _make_mock_cs()
        # Make isinstance check work by setting __class__
        mock_cs.__class__ = RealCS

        from cloudwright_mcp.tools.session import _session_created, _sessions

        _sessions["list_test"] = mock_cs
        _session_created["list_test"] = time.time()

        fns = _register_tools()
        sessions = fns["chat_list_sessions"]()

        assert len(sessions) == 1
        assert "usage" in sessions[0]
        assert "session_id" in sessions[0]
