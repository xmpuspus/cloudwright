from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def register_tools():
    """Register a tools module's functions against a fake FastMCP.

    Mirrors the `mcp.tool()` decorator contract (a zero-arg call returning a
    decorator) without a real FastMCP server or transport, so tool functions
    can be invoked directly in tests. Same pattern as the inline
    `_register_tools` helper in test_session_lifecycle.py, shared here for
    the newer tool modules.
    """

    def _register(module) -> dict:
        mcp = MagicMock()
        captured_fn: dict = {}

        def tool_decorator():
            def decorator(fn):
                captured_fn[fn.__name__] = fn
                return fn

            return decorator

        mcp.tool = tool_decorator
        module.register(mcp)
        return captured_fn

    return _register
