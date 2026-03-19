from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

HAS_LLM = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
skip_no_llm = pytest.mark.skipif(not HAS_LLM, reason="No LLM API key available")


@pytest.fixture
def client():
    from cloudwright_web.app import app

    return TestClient(app)


@pytest.fixture
def sample_spec():
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
                "tier": 2,
                "config": {"instance_type": "m5.large"},
            },
            {
                "id": "db",
                "service": "rds",
                "provider": "aws",
                "label": "Database",
                "tier": 3,
                "config": {"engine": "postgres", "instance_class": "db.r5.large"},
            },
        ],
        "connections": [
            {"source": "web", "target": "db", "label": "SQL", "protocol": "TCP", "port": 5432},
        ],
    }


@pytest.mark.e2e
@skip_no_llm
class TestDesignEndpointBehavioral:
    @pytest.mark.timeout(90)
    def test_design_returns_spec_with_components(self, client):
        resp = client.post(
            "/api/design",
            json={"description": "Simple web app with a load balancer, app servers, and a database on AWS"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "spec" in data, "Response missing 'spec' field"
        assert "yaml" in data, "Response missing 'yaml' field"
        spec = data["spec"]
        assert len(spec["components"]) >= 2, (
            f"Expected at least 2 components, got {len(spec['components'])}: {spec['components']}"
        )

    @pytest.mark.timeout(90)
    def test_design_yaml_is_non_empty(self, client):
        resp = client.post(
            "/api/design",
            json={"description": "Serverless API on AWS with Lambda and DynamoDB"},
        )
        assert resp.status_code == 200
        yaml_text = resp.json()["yaml"]
        assert yaml_text and len(yaml_text) > 50, "YAML output is empty or suspiciously short"

    @pytest.mark.timeout(90)
    def test_design_spec_has_required_fields(self, client):
        resp = client.post(
            "/api/design",
            json={"description": "Container-based microservices on AWS with ECS and RDS"},
        )
        assert resp.status_code == 200
        spec = resp.json()["spec"]
        for field in ("name", "provider", "components"):
            assert field in spec, f"Spec missing required field: {field}"


@pytest.mark.e2e
@skip_no_llm
class TestChatStreamBehavioral:
    @pytest.mark.timeout(90)
    def test_stream_yields_token_events(self, client):
        resp = client.post(
            "/api/chat/stream",
            json={"message": "What cloud services would you use for a high-traffic e-commerce site?"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        lines = [ln for ln in resp.text.splitlines() if ln.startswith("data:")]
        events = [json.loads(ln[5:].strip()) for ln in lines]
        token_events = [e for e in events if e.get("stage") == "token"]
        assert len(token_events) >= 1, f"No token events received. Stages: {[e.get('stage') for e in events]}"

    @pytest.mark.timeout(90)
    def test_stream_ends_with_done_event(self, client):
        resp = client.post(
            "/api/chat/stream",
            json={"message": "Compare AWS S3 and GCP Cloud Storage briefly"},
        )
        assert resp.status_code == 200

        lines = [ln for ln in resp.text.splitlines() if ln.startswith("data:")]
        events = [json.loads(ln[5:].strip()) for ln in lines]
        stages = [e.get("stage") for e in events]
        assert "done" in stages, f"Stream never emitted 'done' event. Stages seen: {stages}"

    @pytest.mark.timeout(90)
    def test_stream_done_event_has_usage(self, client):
        resp = client.post(
            "/api/chat/stream",
            json={"message": "Name three AWS compute services"},
        )
        assert resp.status_code == 200

        lines = [ln for ln in resp.text.splitlines() if ln.startswith("data:")]
        events = [json.loads(ln[5:].strip()) for ln in lines]
        done = next((e for e in events if e.get("stage") == "done"), None)
        assert done is not None, "No 'done' event found in stream"
        assert "usage" in done, f"'done' event missing 'usage': {done}"


@pytest.mark.e2e
@skip_no_llm
class TestChatWithUsage:
    @pytest.mark.timeout(90)
    def test_chat_usage_has_token_counts(self, client):
        resp = client.post(
            "/api/chat",
            json={"message": "Design a simple blog platform on AWS"},
        )
        assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "usage" in data, "Response missing 'usage' field"
        usage = data["usage"]
        # usage may be None if the LLM backend doesn't report it
        if usage is not None:
            assert "input_tokens" in usage, f"usage missing 'input_tokens': {usage}"
            assert "output_tokens" in usage, f"usage missing 'output_tokens': {usage}"
            assert usage["input_tokens"] > 0, f"input_tokens should be > 0, got {usage['input_tokens']}"
            assert usage["output_tokens"] > 0, f"output_tokens should be > 0, got {usage['output_tokens']}"

    @pytest.mark.timeout(90)
    def test_chat_reply_is_non_empty(self, client):
        resp = client.post(
            "/api/chat",
            json={"message": "What is the difference between EC2 and Lambda?"},
        )
        assert resp.status_code == 200
        reply = resp.json().get("reply", "")
        assert reply and len(reply) > 20, f"Reply is empty or too short: {repr(reply)}"


@pytest.mark.e2e
@skip_no_llm
class TestDesignThenCost:
    @pytest.mark.timeout(120)
    def test_design_then_cost_returns_breakdown(self, client):
        design_resp = client.post(
            "/api/design",
            json={"description": "Three-tier web application on AWS with ALB, EC2 auto-scaling, and RDS"},
        )
        assert design_resp.status_code == 200, f"Design failed: {design_resp.text}"
        spec = design_resp.json()["spec"]
        assert len(spec["components"]) >= 2, "Design produced fewer components than expected"

        cost_resp = client.post("/api/cost", json={"spec": spec})
        assert cost_resp.status_code == 200, f"Cost estimate failed: {cost_resp.text}"
        cost_data = cost_resp.json()
        assert "estimate" in cost_data, "Cost response missing 'estimate'"
        estimate = cost_data["estimate"]
        assert "monthly_total" in estimate, f"Estimate missing 'monthly_total': {estimate}"
        assert estimate["monthly_total"] >= 0, f"monthly_total is negative: {estimate['monthly_total']}"
        assert "breakdown" in estimate, "Estimate missing 'breakdown'"
        assert len(estimate["breakdown"]) > 0, "Cost breakdown is empty for a multi-component spec"


@pytest.mark.e2e
class TestRateLimiterDoesNotBlockNormalUse:
    def test_three_requests_all_succeed(self, client):
        # The rate limit is 30/min — 3 requests should never be blocked
        for i in range(3):
            resp = client.get("/api/health")
            assert resp.status_code == 200, (
                f"Request {i + 1} of 3 was unexpectedly blocked or failed: {resp.status_code}"
            )

    def test_health_followed_by_cost_requests_succeed(self, client, sample_spec):
        resp1 = client.get("/api/health")
        assert resp1.status_code == 200

        resp2 = client.post("/api/cost", json={"spec": sample_spec})
        assert resp2.status_code == 200

        resp3 = client.post("/api/cost", json={"spec": sample_spec})
        assert resp3.status_code == 200, "Third request was unexpectedly rate-limited"


@pytest.mark.e2e
class TestStructuredErrorResponses:
    def test_missing_api_key_error_has_required_fields(self, client):
        from unittest.mock import patch

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.design.side_effect = RuntimeError("No LLM provider configured")
            resp = client.post("/api/design", json={"description": "simple web app on AWS"})

        assert resp.status_code == 503
        data = resp.json()
        assert "code" in data, f"Error response missing 'code': {data}"
        assert "message" in data, f"Error response missing 'message': {data}"
        assert "suggestion" in data, f"Error response missing 'suggestion': {data}"
        assert data["code"] == "missing_api_key"

    def test_rate_limit_error_has_required_fields(self, client):
        from unittest.mock import patch

        from cloudwright_web.app import _RateLimiter

        tight = _RateLimiter(max_requests=0, window_seconds=60)
        with patch("cloudwright_web.app._rate_limiter", tight):
            resp = client.post("/api/design", json={"description": "simple web app on AWS"})

        assert resp.status_code == 429
        data = resp.json()
        assert "code" in data, f"Rate limit response missing 'code': {data}"
        assert "message" in data, f"Rate limit response missing 'message': {data}"
        assert "suggestion" in data, f"Rate limit response missing 'suggestion': {data}"
        assert data["code"] == "rate_limited"

    def test_internal_error_has_required_fields(self, client):
        from unittest.mock import patch

        with patch("cloudwright_web.app.get_architect") as mock_arch:
            mock_arch.return_value.design.side_effect = Exception("unexpected internal failure")
            resp = client.post("/api/design", json={"description": "simple web app on AWS"})

        assert resp.status_code == 500
        data = resp.json()
        assert "code" in data, f"Internal error response missing 'code': {data}"
        assert "message" in data, f"Internal error response missing 'message': {data}"
        assert "suggestion" in data, f"Internal error response missing 'suggestion': {data}"
        assert data["code"] == "internal_error"

    def test_validation_error_returns_422(self, client):
        # description below min_length=5 triggers Pydantic validation before any LLM call
        resp = client.post("/api/design", json={"description": "ab"})
        assert resp.status_code == 422, f"Expected 422 for too-short description, got {resp.status_code}"

    def test_timeout_error_has_required_fields(self, client):
        import asyncio
        from unittest.mock import patch

        with patch("cloudwright_web.app.get_architect"), \
             patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            resp = client.post("/api/design", json={"description": "simple web app on AWS"})

        assert resp.status_code == 504
        data = resp.json()
        assert "code" in data, f"Timeout error response missing 'code': {data}"
        assert "suggestion" in data, f"Timeout error response missing 'suggestion': {data}"
        assert data["code"] == "llm_timeout"
