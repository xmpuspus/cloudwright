from __future__ import annotations

import threading
import uuid
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

_lock = threading.Lock()


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def chat_create_session(
        provider: Annotated[
            str,
            Field(
                description=(
                    "Default cloud provider for the session. Every subsequent `chat_send` "
                    "within this session uses this provider unless overridden in the message."
                ),
                examples=["aws", "gcp", "azure", "databricks"],
            ),
        ] = "aws",
        budget_monthly: Annotated[
            float | None,
            Field(
                description=(
                    "Optional monthly budget cap (USD). Applied across all design turns "
                    "within the session — the architect will bias toward fitting under it."
                ),
                examples=[2000, 5000, 10000],
            ),
        ] = None,
        compliance: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional compliance frameworks enforced across the session's design "
                    "turns. Values: 'hipaa', 'pci-dss', 'soc2', 'fedramp', 'gdpr'."
                ),
                examples=[["hipaa"], ["soc2", "gdpr"]],
            ),
        ] = None,
    ) -> dict:
        """Create a new stateful architecture-design conversation session.

        Returns `{'session_id': <12-char hex>}`. The session_id is the handle
        for subsequent `chat_send` / `chat_delete_session` calls.

        When to use: Multi-turn architecture design where each turn depends on
        the prior one (e.g. 'design it', 'now add a cache', 'now move to GCP').
        For single-shot design use `design_architecture`; for one-shot edits
        of an existing spec use `modify_architecture`.

        Behavior: Writes a new session file to the session store (persisted on
        disk). Does not call the LLM — the first LLM call happens on the first
        `chat_send`. Constraints are frozen at session creation and apply to
        every turn.
        """
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
    def chat_send(
        session_id: Annotated[
            str,
            Field(
                description=(
                    "Session handle returned by `chat_create_session`. Must reference an "
                    "existing session; otherwise the tool returns `{'error': ...}`."
                ),
            ),
        ],
        message: Annotated[
            str,
            Field(
                description=(
                    "User message for this conversation turn. Can be a design request, a "
                    "modification instruction, a question about the current spec, or "
                    "meta-commands (e.g. 'show me the cost')."
                ),
                examples=[
                    "Design a 3-tier web app with PostgreSQL",
                    "Add a Redis cache in front of the database",
                    "What's the monthly cost?",
                ],
            ),
        ],
    ) -> dict:
        """Send a message to an existing conversation session and get a response.

        Returns `{'response': str, 'spec': dict|None, 'usage': dict, 'cumulative_usage': dict}`.
        `spec` is populated when the turn produced or modified an ArchSpec.
        `usage` reports LLM token counts for this turn; `cumulative_usage` totals
        across the whole session.

        When to use: Every turn after `chat_create_session`. For zero-state
        single-shot calls use `design_architecture` / `modify_architecture`
        instead.

        Behavior: Calls an LLM — incurs API costs proportional to the
        conversation history length (history grows each turn). Persists
        updated session state back to the session store.
        """
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
        """List all saved conversation sessions.

        Returns a list of session metadata: session_id, creation timestamp,
        last-activity timestamp, cumulative token usage, and whether the session
        currently owns a spec.

        When to use: Resuming prior work, cleaning up abandoned sessions, or
        auditing session token spend.

        Behavior: Pure disk read — no LLM, no network. Read-only.
        """
        from cloudwright.session_store import SessionStore

        return SessionStore().list_sessions()

    @mcp.tool()
    def chat_delete_session(
        session_id: Annotated[
            str,
            Field(
                description=(
                    "Session handle to delete. If the session doesn't exist, the tool "
                    "returns `{'error': ...}` and does nothing."
                ),
            ),
        ],
    ) -> dict:
        """Delete a conversation session.

        Returns `{'deleted': True}` on success or `{'error': ...}` if the session
        did not exist. Destructive: the session's conversation history and any
        uncommitted spec are lost. There is no undo.

        When to use: Clean-up after a completed design, or abandoning a
        dead-end conversation. Does not affect any deployed infrastructure —
        cloudwright never deploys anything.

        Behavior: Removes the session file from the session store. No LLM, no
        network.
        """
        from cloudwright.session_store import SessionStore

        with _lock:
            deleted = SessionStore().delete(session_id)
        if deleted:
            return {"deleted": True}
        return {"error": f"Session {session_id!r} not found."}
