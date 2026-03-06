"""FastMCP server for Cloudwright architecture intelligence."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from cloudwright_mcp.tools import analyze, cost, design, export, session, validate

_GROUPS = {
    "design": design,
    "cost": cost,
    "validate": validate,
    "analyze": analyze,
    "export": export,
    "session": session,
}


def create_server(tools: set[str] | None = None) -> FastMCP:
    """Create a FastMCP server with selected tool groups.

    Args:
        tools: Set of group names to register. None = all groups.
               Valid groups: design, cost, validate, analyze, export, session.
    """
    mcp = FastMCP("cloudwright", description="Architecture intelligence for cloud engineers")

    for name, module in _GROUPS.items():
        if tools is None or name in tools:
            module.register(mcp)

    return mcp
