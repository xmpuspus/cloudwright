"""Tests for /api/health and /api/version (audit-fix v1.3)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CLOUDWRIGHT_API_KEY", "test-key")
    from cloudwright_web.app import create_app
    from fastapi.testclient import TestClient

    return TestClient(create_app())


def test_health_returns_version_and_uptime(client):
    r = client.get("/api/health", headers={"X-API-Key": "test-key"})
    # status code may be 200 or 503 depending on catalog load in test env
    body = r.json()
    assert "version" in body
    assert isinstance(body["version"], str)
    assert "uptime_s" in body
    assert isinstance(body["uptime_s"], (int, float))
    assert "catalog_loaded" in body
    assert "catalog_size" in body
    assert "llm_provider" in body
    assert "llm_model" in body


def test_health_503_when_catalog_fails(client):
    """When catalog loading fails, health returns 503 (Kubernetes readiness)."""
    with patch("cloudwright_web.singletons.get_catalog", side_effect=RuntimeError("catalog dead")):
        r = client.get("/api/health", headers={"X-API-Key": "test-key"})
    assert r.status_code == 503
    body = r.json()
    assert body["catalog_loaded"] is False
    assert body["status"] == "degraded"


def test_health_503_when_no_llm_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CLOUDWRIGHT_API_KEY", "test-key")
    from cloudwright_web.app import create_app
    from fastapi.testclient import TestClient

    c = TestClient(create_app())
    r = c.get("/api/health")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert "version" in body


def test_version_endpoint(client):
    r = client.get("/api/version")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"version", "build_sha", "llm_provider", "llm_model"}
    assert isinstance(body["version"], str)


def test_version_includes_build_sha_from_env(monkeypatch):
    monkeypatch.setenv("CLOUDWRIGHT_API_KEY", "test-key")
    monkeypatch.setenv("CLOUDWRIGHT_BUILD_SHA", "abc1234")
    from cloudwright_web.app import create_app
    from fastapi.testclient import TestClient

    c = TestClient(create_app())
    r = c.get("/api/version")
    assert r.json()["build_sha"] == "abc1234"


def _is_openapi_json(response) -> bool:
    """A real OpenAPI doc is JSON whose body starts with `{"openapi"`.

    The SPA fallback (frontend index.html) returns 200 with text/html, which
    we treat as "openapi disabled" — Swagger UI cannot render against it.
    """
    if response.status_code != 200:
        return False
    if "application/json" not in response.headers.get("content-type", ""):
        return False
    return response.text.lstrip().startswith('{"openapi"')


def test_docs_disabled_in_production(monkeypatch):
    monkeypatch.setenv("CLOUDWRIGHT_ENV", "production")
    monkeypatch.delenv("CLOUDWRIGHT_DOCS_ENABLED", raising=False)
    monkeypatch.setenv("CLOUDWRIGHT_API_KEY", "test-key")
    from cloudwright_web.app import create_app
    from fastapi.testclient import TestClient

    c = TestClient(create_app())
    assert not _is_openapi_json(c.get("/openapi.json"))


def test_docs_enabled_outside_production(monkeypatch):
    monkeypatch.delenv("CLOUDWRIGHT_ENV", raising=False)
    monkeypatch.delenv("CLOUDWRIGHT_DOCS_ENABLED", raising=False)
    monkeypatch.setenv("CLOUDWRIGHT_API_KEY", "test-key")
    from cloudwright_web.app import create_app
    from fastapi.testclient import TestClient

    c = TestClient(create_app())
    assert _is_openapi_json(c.get("/openapi.json"))


def test_docs_enabled_override(monkeypatch):
    monkeypatch.setenv("CLOUDWRIGHT_ENV", "production")
    monkeypatch.setenv("CLOUDWRIGHT_DOCS_ENABLED", "true")
    monkeypatch.setenv("CLOUDWRIGHT_API_KEY", "test-key")
    from cloudwright_web.app import create_app
    from fastapi.testclient import TestClient

    c = TestClient(create_app())
    assert _is_openapi_json(c.get("/openapi.json"))
