from __future__ import annotations

import threading
import time
import uuid

from mcp.server.fastmcp import FastMCP

_sessions: dict[str, object] = {}
_session_created: dict[str, float] = {}
_lock = threading.Lock()
_SESSION_TTL = 3600
_MAX_SESSIONS = 100


def _cleanup_expired() -> None:
    now = time.time()
    with _lock:
        expired = [sid for sid, ts in _session_created.items() if now - ts > _SESSION_TTL]
        for sid in expired:
            _sessions.pop(sid, None)
            _session_created.pop(sid, None)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def chat_create_session(
        provider: str = "aws",
        budget_monthly: float | None = None,
        compliance: list[str] | None = None,
    ) -> dict:
        """Create a new stateful architecture design conversation session."""
        from cloudwright.architect import ConversationSession
        from cloudwright.spec import Constraints

        _cleanup_expired()

        constraints = Constraints(budget_monthly=budget_monthly, compliance=compliance or [])
        session = ConversationSession(constraints=constraints)
        session_id = uuid.uuid4().hex[:12]
        with _lock:
            # Evict oldest if at capacity
            while len(_sessions) >= _MAX_SESSIONS and _session_created:
                oldest = min(_session_created, key=_session_created.get)
                _sessions.pop(oldest, None)
                _session_created.pop(oldest, None)
            _sessions[session_id] = session
            _session_created[session_id] = time.time()
        return {"session_id": session_id}

    @mcp.tool()
    def chat_send(session_id: str, message: str) -> dict:
        """Send a message to an existing conversation session and get a response."""
        session = _sessions.get(session_id)
        if session is None:
            return {"error": f"Session {session_id!r} not found. Create one with chat_create_session."}

        text, spec = session.send(message)
        return {
            "response": text,
            "spec": spec.model_dump(exclude_none=True) if spec is not None else None,
            "usage": session.last_usage,
            "cumulative_usage": session.get_usage_summary(),
        }

    @mcp.tool()
    def chat_list_sessions() -> list[dict]:
        """List all active conversation sessions."""
        from cloudwright.architect import ConversationSession

        _cleanup_expired()
        result = []
        for sid, session in _sessions.items():
            if isinstance(session, ConversationSession):
                result.append(
                    {
                        "session_id": sid,
                        "message_count": len(session.history),
                        "has_spec": session.current_spec is not None,
                        "created_at": _session_created.get(sid),
                        "usage": session.get_usage_summary(),
                    }
                )
        return result

    @mcp.tool()
    def chat_delete_session(session_id: str) -> dict:
        """Delete a conversation session."""
        with _lock:
            if session_id in _sessions:
                _sessions.pop(session_id, None)
                _session_created.pop(session_id, None)
                return {"deleted": True}
        return {"error": f"Session {session_id!r} not found."}
