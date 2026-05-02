"""Tests for RequestIdMiddleware (audit-fix v1.3)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CLOUDWRIGHT_API_KEY", "test-key")
    from cloudwright_web.app import create_app
    from fastapi.testclient import TestClient

    return TestClient(create_app())


def test_request_id_minted_when_missing(client):
    r = client.get("/api/version")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-Id")
    assert rid is not None
    assert len(rid) >= 16


def test_request_id_preserved_when_provided(client):
    incoming = "deadbeefdeadbeefdeadbeefdeadbeef"
    r = client.get("/api/version", headers={"X-Request-Id": incoming})
    assert r.status_code == 200
    assert r.headers["X-Request-Id"] == incoming


def test_request_ids_are_unique_per_request(client):
    rid1 = client.get("/api/version").headers["X-Request-Id"]
    rid2 = client.get("/api/version").headers["X-Request-Id"]
    assert rid1 != rid2


def test_request_id_present_on_404(client):
    r = client.get("/api/this-does-not-exist")
    # path traversal middleware lets unknown routes through to 404 from FastAPI
    assert "X-Request-Id" in r.headers


def test_request_id_present_on_health(client):
    r = client.get("/api/health", headers={"X-API-Key": "test-key"})
    assert "X-Request-Id" in r.headers
