"""Shared SSE helper used by all streaming endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class StreamEvent:
    stage: str
    data: dict[str, Any] | None = None

    def encode(self) -> str:
        payload: dict[str, Any] = {"stage": self.stage}
        if self.data:
            payload.update(self.data)
        return f"data: {json.dumps(payload)}\n\n"


def sse_event(stage: str, **kwargs: Any) -> str:
    """Format a single SSE data line."""
    payload: dict[str, Any] = {"stage": stage, **kwargs}
    return f"data: {json.dumps(payload)}\n\n"
