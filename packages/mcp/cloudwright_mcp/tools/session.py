from __future__ import annotations

import threading
import uuid

from mcp.server.fastmcp import FastMCP

_lock = threading.Lock()


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def chat_create_session(
        provider: str = "aws",
        budget_monthly: float | None = None,
        compliance: list[str] | None = None,
    ) -> dict:
        """Create a new stateful architecture design conversation session."""
        from cloudwright.architect import ConversationSession
        from cloudwright.session_store import SessionStore
        from cloudwright.spec import Constraints

        constraints = Constraints(budget_monthly=budget_monthly, compliance=compliance or [])
        session_id = uuid.uuid4().hex[:12]
        session = ConversationSession(constraints=constraints, session_id=session_id)

        with _lock:
            SessionStore().save(session_id, session)

        return {"session_id": session_id}

    @mcp.tool()
    def chat_send(session_id: str, message: str) -> dict:
        """Send a message to an existing conversation session and get a response."""
        from cloudwright.session_store import SessionStore

        store = SessionStore()
        with _lock:
            try:
                session = store.load(session_id)
            except FileNotFoundError:
                return {"error": f"Session {session_id!r} not found. Create one with chat_create_session."}

        text, spec = session.send(message)

        with _lock:
            store.save(session_id, session)

        return {
            "response": text,
            "spec": spec.model_dump(exclude_none=True) if spec is not None else None,
            "usage": session.last_usage,
            "cumulative_usage": session.get_usage_summary(),
        }

    @mcp.tool()
    def chat_list_sessions() -> list[dict]:
        """List all saved conversation sessions."""
        from cloudwright.session_store import SessionStore

        return SessionStore().list_sessions()

    @mcp.tool()
    def chat_delete_session(session_id: str) -> dict:
        """Delete a conversation session."""
        from cloudwright.session_store import SessionStore

        with _lock:
            deleted = SessionStore().delete(session_id)
        if deleted:
            return {"deleted": True}
        return {"error": f"Session {session_id!r} not found."}
