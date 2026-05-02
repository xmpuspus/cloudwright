"""``/api/design/stream`` and ``/api/modify/stream`` v1.4 async path.

The design SSE endpoint doesn't stream tokens (the ``architect.design`` call
is still a single sync request), but the v1.4 refactor:
1. Wraps the sync call in ``asyncio.wait_for`` so the route-level timeout
   actually unwinds (the old code awaited a bare ``to_thread`` with no
   deadline on ``/design/stream``).
2. Adds ``X-Accel-Buffering: no`` headers so the SSE event sequence reaches
   the browser without proxy buffering.
3. Emits the same event sequence as before: ``generating`` → ``generated``
   → ``costing`` → ``costed`` → ``validating`` → ``validated`` → ``done``.
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cloudwright.spec import ArchSpec, Component, CostEstimate
from cloudwright_web.routers import design as design_router


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


def _sample_spec() -> ArchSpec:
    return ArchSpec(
        name="X",
        version=1,
        provider="aws",
        region="us-east-1",
        components=[Component(id="c", service="lambda", provider="aws", label="L", tier=2, config={})],
        connections=[],
    )


def _sample_cost() -> CostEstimate:
    return CostEstimate(monthly_total=10.0, breakdown=[], currency="USD")


def test_design_stream_uses_wait_for_for_cancel_safe_timeout():
    src = inspect.getsource(design_router)
    assert "asyncio.wait_for" in src, (
        "design_stream must use asyncio.wait_for so route-level cancellation "
        "actually unwinds the SDK call (audit-2 cancel-safety)."
    )


def test_design_stream_emits_sse_headers(client):
    spec = _sample_spec()
    cost = _sample_cost()

    fake_arch = MagicMock()
    fake_arch.design.return_value = spec
    fake_arch.last_usage = {"input_tokens": 1, "output_tokens": 1}
    fake_engine = MagicMock()
    fake_engine.estimate.return_value = cost

    with patch("cloudwright_web.singletons.get_architect", return_value=fake_arch):
        with patch("cloudwright_web.singletons.get_cost_engine", return_value=fake_engine):
            resp = client.post(
                "/api/design/stream",
                json={"description": "simple lambda app"},
            )

    assert resp.status_code == 200
    assert resp.headers.get("x-accel-buffering") == "no"


def test_design_stream_full_event_sequence(client):
    spec = _sample_spec()
    cost = _sample_cost()

    fake_arch = MagicMock()
    fake_arch.design.return_value = spec
    fake_arch.last_usage = {"input_tokens": 1, "output_tokens": 1}
    fake_engine = MagicMock()
    fake_engine.estimate.return_value = cost

    with patch("cloudwright_web.singletons.get_architect", return_value=fake_arch):
        with patch("cloudwright_web.singletons.get_cost_engine", return_value=fake_engine):
            resp = client.post(
                "/api/design/stream",
                json={"description": "simple lambda app"},
            )

    lines = [ln for ln in resp.text.splitlines() if ln.startswith("data:")]
    events = [json.loads(ln[5:].strip()) for ln in lines]
    stages = [e.get("stage") for e in events]
    # The sequence may include validation events; required ones:
    assert "generating" in stages
    assert "generated" in stages
    assert "costing" in stages
    assert "costed" in stages
    assert "done" in stages


def test_modify_stream_emits_sse_headers(client):
    spec = _sample_spec()
    updated = spec
    cost = _sample_cost()

    fake_arch = MagicMock()
    fake_arch.modify.return_value = updated
    fake_arch.last_usage = {"input_tokens": 1, "output_tokens": 1}
    fake_engine = MagicMock()
    fake_engine.estimate.return_value = cost

    with patch("cloudwright_web.singletons.get_architect", return_value=fake_arch):
        with patch("cloudwright_web.singletons.get_cost_engine", return_value=fake_engine):
            resp = client.post(
                "/api/modify/stream",
                json={"spec": spec.model_dump(exclude_none=True), "instruction": "add a queue"},
            )

    assert resp.status_code == 200
    assert resp.headers.get("x-accel-buffering") == "no"


def test_modify_stream_emits_modified_and_done(client):
    spec = _sample_spec()
    updated = spec
    cost = _sample_cost()

    fake_arch = MagicMock()
    fake_arch.modify.return_value = updated
    fake_arch.last_usage = {"input_tokens": 1, "output_tokens": 1}
    fake_engine = MagicMock()
    fake_engine.estimate.return_value = cost

    with patch("cloudwright_web.singletons.get_architect", return_value=fake_arch):
        with patch("cloudwright_web.singletons.get_cost_engine", return_value=fake_engine):
            resp = client.post(
                "/api/modify/stream",
                json={"spec": spec.model_dump(exclude_none=True), "instruction": "add a queue"},
            )

    lines = [ln for ln in resp.text.splitlines() if ln.startswith("data:")]
    events = [json.loads(ln[5:].strip()) for ln in lines]
    stages = [e.get("stage") for e in events]
    assert "modifying" in stages
    assert "modified" in stages
    assert "done" in stages
