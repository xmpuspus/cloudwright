"""Serve cloudwright functions as an MCP server."""

from __future__ import annotations

from typing import Annotated

import typer


def mcp_serve(
    tools: Annotated[
        str | None,
        typer.Option("--tools", "-t", help="Comma-separated tool groups: design,cost,validate,analyze,export,session"),
    ] = None,
    transport: Annotated[str, typer.Option("--transport", help="Transport: stdio or sse")] = "stdio",
) -> None:
    """Start an MCP server exposing cloudwright tools."""
    try:
        from cloudwright_mcp.server import create_server
    except ImportError:
        from rich.console import Console

        Console(stderr=True).print(
            "[red]Error:[/red] cloudwright-ai-mcp not installed.\n"
            "  Install: pip install cloudwright-ai-mcp"
        )
        raise typer.Exit(1) from None

    tool_set: set[str] | None = None
    if tools:
        tool_set = {t.strip() for t in tools.split(",") if t.strip()}

    server = create_server(tools=tool_set)
    server.run(transport=transport)
