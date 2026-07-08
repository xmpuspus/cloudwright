"""Age-based sweep for MCP session files.

`SessionStore` (`cloudwright.session_store`) persists every `chat_create_session`
call to `~/.cloudwright/sessions/*.json` with no expiry. A long-running MCP
server accumulates one file per session forever. This module adds an age-based
sweep on top of SessionStore's existing public API (`list_sessions` / `delete`)
without touching core: it never opens session files directly, so SessionStore's
atomic-write semantics (write-temp, fsync, `os.replace`) are unaffected.

Concurrency note: there is no cross-process lock between a sweep and a
concurrent `chat_send` that is about to re-save the same session. If a sweep
and a save race on the same session id, whichever filesystem operation lands
last wins: a session mid-save when a sweep runs may survive one extra sweep
cycle before the next one catches it, or a session deleted by a sweep just
before a save completes gets recreated by that save. Either outcome is safe
(atomic writes, whole-file delete). This is last-writer-wins housekeeping,
not a distributed lock.
"""

from __future__ import annotations

import logging
import os
import time

log = logging.getLogger(__name__)

DEFAULT_TTL_DAYS = 7
TTL_ENV_VAR = "CLOUDWRIGHT_MCP_SESSION_TTL_DAYS"


def session_ttl_seconds() -> float:
    """Resolve the configured session TTL, in seconds.

    Reads `CLOUDWRIGHT_MCP_SESSION_TTL_DAYS` (a float number of days). Unset
    or non-numeric falls back to `DEFAULT_TTL_DAYS`. A value <= 0 disables
    the sweep entirely (no expiry) so operators can opt out.
    """
    raw = os.environ.get(TTL_ENV_VAR, "").strip()
    if not raw:
        return DEFAULT_TTL_DAYS * 86400
    try:
        days = float(raw)
    except ValueError:
        log.warning("Invalid %s=%r; using default %d days", TTL_ENV_VAR, raw, DEFAULT_TTL_DAYS)
        return DEFAULT_TTL_DAYS * 86400
    return days * 86400


def sweep_expired_sessions(
    store=None,
    *,
    ttl_seconds: float | None = None,
    now: float | None = None,
) -> list[str]:
    """Delete session files older than the TTL. Returns the deleted session IDs.

    A session's age is `now - saved_at`, falling back to `created_at` for
    sessions written before the `saved_at` field existed. Called from
    `chat_list_sessions` and once at server start (`create_server`); safe to
    call repeatedly. It is a no-op once expired sessions are already gone.

    Args:
        store: SessionStore instance to sweep. Defaults to
               `SessionStore()` (the real `~/.cloudwright/sessions/` dir).
               Tests should always pass an explicit store pointed at a
               temp directory.
        ttl_seconds: Override for the resolved TTL. Defaults to
                     `session_ttl_seconds()`.
        now: Override for the current time (epoch seconds). Defaults to
             `time.time()`.
    """
    from cloudwright.session_store import SessionStore

    store = store or SessionStore()
    ttl = session_ttl_seconds() if ttl_seconds is None else ttl_seconds
    if ttl <= 0:
        return []

    current = time.time() if now is None else now
    deleted: list[str] = []
    for meta in store.list_sessions():
        stamp = meta.get("saved_at")
        if stamp is None:
            stamp = meta.get("created_at")
        if stamp is None:
            continue
        try:
            age = current - float(stamp)
        except (TypeError, ValueError):
            continue
        if age <= ttl:
            continue
        session_id = meta["session_id"]
        try:
            if store.delete(session_id):
                deleted.append(session_id)
        except ValueError:
            # session_id failed SessionStore's safe-id check. Skip, don't raise.
            log.warning("Skipping sweep of unsafe session_id %r", session_id)
    return deleted
