"""Backend API tests for Cloudwright FastAPI app."""

import json
import os
import sys
from pathlib import Path

import pytest

# Add the web package to path so we can import cloudwright_web.app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

HAS_LLM = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
skip_no_llm = pytest.mark.skipif(not HAS_LLM, reason="No LLM API key available")


@pytest.fixture
def client():
    from cloudwright_web.app import app
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
def sample_spec():
    """A minimal valid spec as dict for API payloads."""
    return {
        "name": "Test App",
        "version": 1,
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {
                "id": "web",
                "service": "ec2",
                "provider": "aws",
                "label": "Web Server",
                "description": "Application server",
                "tier": 2,
                "config": {"instance_type": "m5.large"},
            },
            {
                "id": "db",
                "service": "rds",
                "provider": "aws",
                "label": "Database",
                "description": "PostgreSQL",
                "tier": 3,
                "config": {"engine": "postgres", "instance_class": "db.r5.large", "multi_az": True},
            },
        ],
        "connections": [
            {"source": "web", "target": "db", "label": "SQL", "protocol": "TCP", "port": 5432},
        ],
    }


@pytest.fixture
def serverless_spec():
    return {
        "name": "Serverless API",
        "version": 1,
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {"id": "api", "service": "api_gateway", "provider": "aws", "label": "API GW", "tier": 0, "config": {}},
            {
                "id": "fn",
                "service": "lambda",
                "provider": "aws",
                "label": "Handler",
                "tier": 2,
                "config": {"memory_mb": 512},
            },
            {"id": "table", "service": "dynamodb", "provider": "aws", "label": "DynamoDB", "tier": 3, "config": {}},
        ],
        "connections": [
            {"source": "api", "target": "fn"},
            {"source": "fn", "target": "table"},
        ],
    }


# Health


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_has_catalog(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert "catalog_loaded" in data


# Cost


class TestCostAPI:
    def test_cost_basic(self, client, sample_spec):
        resp = client.post("/api/cost", json={"spec": sample_spec})
        assert resp.status_code == 200
        data = resp.json()
        assert "estimate" in data
        assert data["estimate"]["monthly_total"] > 0
        assert len(data["estimate"]["breakdown"]) == 2

    def test_cost_with_comparison(self, client, sample_spec):
        resp = client.post("/api/cost", json={"spec": sample_spec, "compare_providers": ["gcp"]})
        assert resp.status_code == 200
        data = resp.json()
        assert "estimate" in data
        assert "alternatives" in data
        assert len(data["alternatives"]) >= 1

    def test_cost_serverless(self, client, serverless_spec):
        resp = client.post("/api/cost", json={"spec": serverless_spec})
        assert resp.status_code == 200
        data = resp.json()
        assert data["estimate"]["monthly_total"] > 0

    def test_cost_minimal_spec(self, client):
        # Pydantic fills defaults for missing fields, so a minimal dict is valid
        resp = client.post(
            "/api/cost",
            json={
                "spec": {
                    "name": "Minimal",
                    "provider": "aws",
                    "region": "us-east-1",
                    "components": [],
                    "connections": [],
                }
            },
        )
        assert resp.status_code == 200
        assert resp.json()["estimate"]["monthly_total"] == 0

    def test_cost_empty_components(self, client):
        spec = {
            "name": "Empty",
            "provider": "aws",
            "region": "us-east-1",
            "components": [],
            "connections": [],
        }
        resp = client.post("/api/cost", json={"spec": spec})
        assert resp.status_code == 200
        data = resp.json()
        assert data["estimate"]["monthly_total"] == 0

    def test_cost_multi_cloud_comparison(self, client, sample_spec):
        resp = client.post("/api/cost", json={"spec": sample_spec, "compare_providers": ["gcp", "azure"]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["alternatives"]) == 2
        for alt in data["alternatives"]:
            assert alt["monthly_total"] > 0


# Validate


class TestValidateAPI:
    def test_validate_hipaa(self, client, sample_spec):
        resp = client.post("/api/validate", json={"spec": sample_spec, "compliance": ["hipaa"]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["framework"] == "HIPAA"

    def test_validate_multiple_frameworks(self, client, sample_spec):
        resp = client.post(
            "/api/validate",
            json={
                "spec": sample_spec,
                "compliance": ["hipaa", "pci-dss", "soc2"],
                "well_architected": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        frameworks = {r["framework"] for r in data["results"]}
        assert "HIPAA" in frameworks
        assert "Well-Architected" in frameworks

    def test_validate_well_architected_only(self, client, sample_spec):
        resp = client.post("/api/validate", json={"spec": sample_spec, "well_architected": True})
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["framework"] == "Well-Architected" for r in data["results"])

    def test_validate_no_frameworks(self, client, sample_spec):
        resp = client.post("/api/validate", json={"spec": sample_spec})
        assert resp.status_code == 200


# Export


class TestExportAPI:
    def test_export_terraform(self, client, sample_spec):
        resp = client.post("/api/export", json={"spec": sample_spec, "format": "terraform"})
        assert resp.status_code == 200
        data = resp.json()
        assert "resource" in data["content"].lower() or "terraform" in data["content"].lower()

    def test_export_cloudformation(self, client, sample_spec):
        resp = client.post("/api/export", json={"spec": sample_spec, "format": "cloudformation"})
        assert resp.status_code == 200
        assert "AWSTemplateFormatVersion" in resp.json()["content"]

    def test_export_mermaid(self, client, sample_spec):
        resp = client.post("/api/export", json={"spec": sample_spec, "format": "mermaid"})
        assert resp.status_code == 200
        assert "flowchart" in resp.json()["content"].lower()

    def test_export_sbom(self, client, sample_spec):
        resp = client.post("/api/export", json={"spec": sample_spec, "format": "sbom"})
        assert resp.status_code == 200
        data = json.loads(resp.json()["content"])
        assert data["bomFormat"] == "CycloneDX"

    def test_export_aibom(self, client, sample_spec):
        resp = client.post("/api/export", json={"spec": sample_spec, "format": "aibom"})
        assert resp.status_code == 200
        data = json.loads(resp.json()["content"])
        assert "aiComponents" in data

    def test_export_invalid_format(self, client, sample_spec):
        resp = client.post("/api/export", json={"spec": sample_spec, "format": "banana"})
        assert resp.status_code == 400

    def test_export_all_formats(self, client, sample_spec):
        for fmt in ["terraform", "cloudformation", "mermaid", "sbom", "aibom"]:
            resp = client.post("/api/export", json={"spec": sample_spec, "format": fmt})
            assert resp.status_code == 200, f"Export {fmt} failed: {resp.text}"
            assert resp.json()["content"], f"Empty content for {fmt}"


# Diff


class TestDiffAPI:
    def test_diff_identical(self, client, sample_spec):
        resp = client.post("/api/diff", json={"old_spec": sample_spec, "new_spec": sample_spec})
        assert resp.status_code == 200
        data = resp.json()["diff"]
        assert len(data["added"]) == 0
        assert len(data["removed"]) == 0

    def test_diff_added_component(self, client, sample_spec):
        new_spec = dict(sample_spec)
        new_spec["components"] = list(sample_spec["components"]) + [
            {"id": "cache", "service": "elasticache", "provider": "aws", "label": "Cache", "tier": 3, "config": {}},
        ]
        resp = client.post("/api/diff", json={"old_spec": sample_spec, "new_spec": new_spec})
        assert resp.status_code == 200
        data = resp.json()["diff"]
        assert len(data["added"]) == 1

    def test_diff_removed_component(self, client, sample_spec):
        new_spec = dict(sample_spec)
        new_spec["components"] = [sample_spec["components"][0]]  # only keep web
        resp = client.post("/api/diff", json={"old_spec": sample_spec, "new_spec": new_spec})
        assert resp.status_code == 200
        data = resp.json()["diff"]
        assert len(data["removed"]) == 1

    def test_diff_between_architectures(self, client, sample_spec, serverless_spec):
        resp = client.post("/api/diff", json={"old_spec": sample_spec, "new_spec": serverless_spec})
        assert resp.status_code == 200
        data = resp.json()["diff"]
        total = len(data["added"]) + len(data["removed"]) + len(data["changed"])
        assert total > 0


# Catalog


class TestCatalogAPI:
    def test_catalog_search_query(self, client):
        resp = client.post("/api/catalog/search", json={"query": "m5"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["instances"]) > 0

    def test_catalog_search_by_provider(self, client):
        resp = client.post("/api/catalog/search", json={"provider": "gcp"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["instances"]) > 0

    def test_catalog_search_by_vcpus(self, client):
        resp = client.post("/api/catalog/search", json={"vcpus": 4})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["instances"]) > 0
        for inst in data["instances"]:
            assert inst["vcpus"] == 4

    def test_catalog_search_by_memory(self, client):
        resp = client.post("/api/catalog/search", json={"memory_gb": 16})
        assert resp.status_code == 200
        assert len(resp.json()["instances"]) > 0

    def test_catalog_search_with_limit(self, client):
        resp = client.post("/api/catalog/search", json={"query": "m5", "limit": 3})
        assert resp.status_code == 200
        assert len(resp.json()["instances"]) <= 3

    def test_catalog_search_no_results(self, client):
        resp = client.post("/api/catalog/search", json={"query": "nonexistent_instance_xyz123"})
        assert resp.status_code == 200
        assert len(resp.json()["instances"]) == 0

    def test_catalog_compare(self, client):
        resp = client.post("/api/catalog/compare", json={"instance_names": ["m5.xlarge", "n2-standard-4"]})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["comparison"]) == 2


# Design (LLM-dependent)


@skip_no_llm
class TestDesignAPI:
    @pytest.mark.timeout(60)
    def test_design_basic(self, client):
        resp = client.post(
            "/api/design",
            json={
                "description": "Simple web app with EC2 and RDS on AWS",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "spec" in data
        assert "yaml" in data
        assert len(data["spec"]["components"]) >= 2

    @pytest.mark.timeout(60)
    def test_design_with_constraints(self, client):
        resp = client.post(
            "/api/design",
            json={
                "description": "Healthcare app on AWS",
                "compliance": ["hipaa"],
                "budget_monthly": 500.0,
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["spec"]["components"]) >= 2

    @pytest.mark.timeout(60)
    def test_design_gcp(self, client):
        resp = client.post(
            "/api/design",
            json={
                "description": "API backend on GCP with Cloud Run and Firestore",
                "provider": "gcp",
                "region": "us-central1",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["spec"]["provider"] == "gcp"

    def test_design_too_short(self, client):
        resp = client.post("/api/design", json={"description": "ab"})
        assert resp.status_code == 422  # validation error

    @pytest.mark.timeout(120)
    def test_modify(self, client, sample_spec):
        resp = client.post(
            "/api/modify",
            json={
                "spec": sample_spec,
                "instruction": "Add an ElastiCache Redis cluster",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["spec"]["components"]) >= 2

    @pytest.mark.timeout(60)
    def test_chat(self, client):
        resp = client.post(
            "/api/chat",
            json={
                "message": "Design a simple blog on AWS with EC2 and RDS",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert "spec" in data


# Integration: Design -> Cost -> Validate -> Export


@skip_no_llm
class TestFullPipelineAPI:
    @pytest.mark.timeout(120)
    def test_design_cost_validate_export(self, client):
        # Design
        resp = client.post(
            "/api/design",
            json={
                "description": "3-tier web app on AWS with ALB, EC2, and RDS PostgreSQL",
            },
        )
        assert resp.status_code == 200
        spec = resp.json()["spec"]

        # Cost
        resp = client.post("/api/cost", json={"spec": spec})
        assert resp.status_code == 200
        assert resp.json()["estimate"]["monthly_total"] > 0

        # Validate
        resp = client.post(
            "/api/validate",
            json={
                "spec": spec,
                "compliance": ["hipaa"],
                "well_architected": True,
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["results"]) >= 2

        # Export all formats
        for fmt in ["terraform", "cloudformation", "mermaid", "sbom", "aibom"]:
            resp = client.post("/api/export", json={"spec": spec, "format": fmt})
            assert resp.status_code == 200, f"Export {fmt} failed"
