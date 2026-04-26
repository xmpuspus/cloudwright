from cloudwright.modules import ModuleCatalog, insert_module
from cloudwright.spec import ArchSpec
from cloudwright_web.app import app
from fastapi.testclient import TestClient


def test_modules_api_lists_approved_modules():
    client = TestClient(app)

    resp = client.get("/api/modules")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["modules"]) == 5
    assert all(module["approved"] for module in data["modules"])
    assert "fragment" not in data["modules"][0]


def test_modules_api_returns_full_module_details():
    client = TestClient(app)

    resp = client.get("/api/modules/aws-serverless-api")

    assert resp.status_code == 200
    module = resp.json()["module"]
    assert module["id"] == "aws-serverless-api"
    assert module["fragment"]["components"]
    assert module["terraform"]["source"]


def test_canvas_validate_returns_standards_result():
    client = TestClient(app)
    catalog = ModuleCatalog()
    spec = insert_module(
        ArchSpec(name="Canvas", provider="aws", region="us-east-1"),
        catalog.require("aws-serverless-api"),
    ).spec

    resp = client.post("/api/canvas/validate", json={"spec": spec.model_dump()})

    assert resp.status_code == 200
    assert resp.json() == {"passed": True, "violations": []}


def test_canvas_validate_reports_orphan_connections():
    client = TestClient(app)

    resp = client.post(
        "/api/canvas/validate",
        json={
            "spec": {
                "name": "Bad Canvas",
                "provider": "aws",
                "region": "us-east-1",
                "components": [{"id": "web", "service": "ec2", "provider": "aws", "label": "Web"}],
                "connections": [{"source": "web", "target": "missing", "label": "broken"}],
            }
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    assert data["violations"][0]["code"] == "orphan_connection"


def test_catalog_services_lists_registry_resources():
    client = TestClient(app)

    resp = client.get("/api/catalog/services?provider=aws")

    assert resp.status_code == 200
    services = resp.json()["services"]
    assert any(service["service_key"] == "lambda" for service in services)
