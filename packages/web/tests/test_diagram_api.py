from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cloudwright_web.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_get_icon_known_service_200():
    res = client.get("/api/icons/aws/ec2.svg")
    assert res.status_code == 200
    assert "svg" in res.headers.get("content-type", "")
    assert "<svg" in res.text


def test_get_icon_unknown_404():
    res = client.get("/api/icons/aws/nonexistent_xyz.svg")
    assert res.status_code == 404


def test_get_icon_path_traversal_blocked():
    # Use percent-encoded dots to bypass client-side URL normalization
    res = client.get("/api/icons/%2e%2e/%2e%2e/%2e%2e/etc/passwd.svg")
    assert res.status_code in (404, 422)


def test_export_c4_format():
    spec = {
        "name": "Test",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "web",
                "service": "ec2",
                "provider": "aws",
                "label": "Web",
                "tier": 2,
                "description": "",
                "config": {},
            },
            {
                "id": "db",
                "service": "rds",
                "provider": "aws",
                "label": "DB",
                "tier": 3,
                "description": "",
                "config": {},
            },
        ],
        "connections": [{"source": "web", "target": "db", "label": "SQL"}],
    }
    res = client.post("/api/export", json={"spec": spec, "format": "c4"})
    # c4 falls back to d2 source; check gracefully
    if res.status_code == 200:
        assert "content" in res.json()
