"""Persistent session storage for ConversationSession."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_DIR = Path.home() / ".cloudwright" / "sessions"


class SessionStore:
    """Save/load ConversationSession state to ~/.cloudwright/sessions/."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or _DEFAULT_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session_id: str, session) -> Path:
        """Persist a ConversationSession to disk."""
        data = session.to_dict()
        data["saved_at"] = time.time()
        path = self.base_dir / f"{session_id}.json"
        path.write_text(json.dumps(data, indent=2, default=str))
        return path

    def load(self, session_id: str, llm=None):
        """Load a ConversationSession from disk."""
        from cloudwright.architect import ConversationSession

        path = self.base_dir / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session {session_id!r} not found at {path}")
        data = json.loads(path.read_text())
        return ConversationSession.from_dict(data, llm=llm)

    def list_sessions(self) -> list[dict]:
        """List all saved sessions with metadata."""
        sessions = []
        for path in sorted(self.base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text())
                turn_count = sum(1 for m in data.get("history", []) if m.get("role") == "user")
                sessions.append(
                    {
                        "session_id": path.stem,
                        "created_at": data.get("created_at"),
                        "saved_at": data.get("saved_at"),
                        "turn_count": turn_count,
                        "has_spec": data.get("current_spec") is not None,
                        "spec_name": data.get("current_spec", {}).get("name") if data.get("current_spec") else None,
                    }
                )
            except (json.JSONDecodeError, OSError):
                log.warning("Skipping corrupt session file: %s", path)
        return sessions

    def delete(self, session_id: str) -> bool:
        """Delete a saved session. Returns True if deleted."""
        path = self.base_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
