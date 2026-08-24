"""FastMCP server for Cloudwright architecture intelligence."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from cloudwright_mcp.tools import analyze, compliance, cost, design, export, migration, plan, review, session, validate
from cloudwright_mcp.ttl import sweep_expired_sessions

log = logging.getLogger(__name__)

_GROUPS = {
    "design": design,
    "cost": cost,
    "validate": validate,
    "analyze": analyze,
    "export": export,
    "session": session,
    "review": review,
    "compliance": compliance,
    "plan": plan,
    "migration": migration,
}


def create_server(tools: set[str] | None = None) -> FastMCP:
    """Create a FastMCP server with selected tool groups.

    Args:
        tools: Set of group names to register. None = all groups.
               Valid groups: design, cost, validate, analyze, export, session,
               review, compliance, plan, migration.
    """
    mcp = FastMCP("cloudwright", instructions="Architecture and migration intelligence for cloud engineers")

    try:
        sweep_expired_sessions()
    except Exception:
        log.warning("Session TTL sweep failed at server start", exc_info=True)

    for name, module in _GROUPS.items():
        if tools is None or name in tools:
            module.register(mcp)

    return mcp
