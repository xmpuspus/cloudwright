from __future__ import annotations

import uuid

from mcp.server.fastmcp import FastMCP

_sessions: dict[str, object] = {}


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

        constraints = Constraints(budget_monthly=budget_monthly, compliance=compliance or [])
        session = ConversationSession(constraints=constraints)
        session_id = uuid.uuid4().hex[:12]
        _sessions[session_id] = session
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
        }

    @mcp.tool()
    def chat_list_sessions() -> list[dict]:
        """List all active conversation sessions."""
        from cloudwright.architect import ConversationSession

        result = []
        for sid, session in _sessions.items():
            if isinstance(session, ConversationSession):
                result.append(
                    {
                        "session_id": sid,
                        "message_count": len(session.history),
                        "has_spec": session.current_spec is not None,
                    }
                )
        return result
