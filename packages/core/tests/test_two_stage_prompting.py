"""Tests for v1.4 two-stage prompting: Stage 1 free-text reasoning -> Stage 2 JSON projection."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from cloudwright.designer import Architect
from cloudwright.spec import Constraints

# Stage 1 returns free text — no JSON object in the first 200 chars.
_STAGE1_REASONING = """
- API Gateway at the edge to handle TLS termination, throttling, and routing
- Single Lambda function written in Python 3.12, 1024 MB memory, owns business logic
- DynamoDB on-demand table named 'orders' for the persistence layer
- Boundary: VPC 'main_vpc' in us-east-1, with private subnet for Lambda VPC config
- Connection kinds: API Gateway -> Lambda is sync_request (REST invoke);
  Lambda -> DynamoDB is sync_request over the DynamoDB endpoint
- Trade-off: chose DynamoDB over RDS to keep cold start cheap and avoid VPC egress costs
- Rejected ECS Fargate because the load is bursty and serverless wins on idle cost
""".strip()

_STAGE2_JSON = json.dumps(
    {
        "name": "Serverless Orders API",
        "provider": "aws",
        "region": "us-east-1",
        "components": [
            {"id": "apigw", "service": "api_gateway", "provider": "aws", "label": "API GW", "tier": 0, "config": {}},
            {
                "id": "fn",
                "service": "lambda",
                "provider": "aws",
                "label": "Order Handler",
                "tier": 2,
                "config": {"memory_mb": 1024, "runtime": "python3.12"},
            },
            {
                "id": "orders",
                "service": "dynamodb",
                "provider": "aws",
                "label": "Orders Table",
                "tier": 3,
                "config": {},
            },
        ],
        "connections": [
            {"source": "apigw", "target": "fn", "label": "invoke", "kind": "sync_request"},
            {"source": "fn", "target": "orders", "label": "read/write", "kind": "sync_request"},
        ],
        "boundaries": [
            {
                "id": "main_vpc",
                "kind": "vpc",
                "label": "Main VPC",
                "component_ids": ["fn"],
            }
        ],
        "rationale": [{"decision": "DynamoDB", "reason": "cold-start cheap"}],
        "suggestions": ["Add Cognito", "Add SQS dead-letter", "Add CloudWatch alarms"],
    }
)


def _two_stage_mock_llm() -> MagicMock:
    """LLM mock where generate() returns Stage 1 text, generate_fast() returns Stage 2 JSON."""
    llm = MagicMock()
    llm.model_name = "claude-sonnet-4-6"
    llm.pricing = {"input": 0.003, "output": 0.015}
    llm.pricing_for = MagicMock(return_value={"input": 0.003, "output": 0.015})
    llm.generate.return_value = (
        _STAGE1_REASONING,
        {"input_tokens": 200, "output_tokens": 350, "model": "claude-sonnet-4-6"},
    )
    llm.generate_fast.return_value = (
        _STAGE2_JSON,
        {"input_tokens": 600, "output_tokens": 400, "model": "claude-haiku-4-5"},
    )
    return llm


class TestTwoStagePrompting:
    def test_stage1_returns_free_text_no_json_braces_in_prefix(self):
        """Stage 1 reasoning must be free text — no JSON object in the first 200 chars."""
        # The reasoning fixture itself enforces the constraint; verify defensively.
        assert "{" not in _STAGE1_REASONING[:200]
        assert "}" not in _STAGE1_REASONING[:200]

    def test_stage2_returns_valid_json(self):
        """Stage 2 output must parse as a complete ArchSpec dict."""
        data = json.loads(_STAGE2_JSON)
        assert data["name"]
        assert data["provider"] == "aws"
        assert len(data["components"]) == 3

    def test_design_calls_both_stages(self):
        llm = _two_stage_mock_llm()
        architect = Architect(llm=llm, two_stage=True)

        spec = architect.design("Build a serverless orders API on AWS")

        # Stage 1 must use generate() (Sonnet).
        assert llm.generate.call_count == 1
        # Stage 2 must use generate_fast() (Haiku).
        assert llm.generate_fast.call_count == 1
        # Spec is correctly parsed from the projection.
        assert spec.name == "Serverless Orders API"
        assert {c.id for c in spec.components} == {"apigw", "fn", "orders"}

    def test_design_records_per_stage_usage(self):
        llm = _two_stage_mock_llm()
        architect = Architect(llm=llm, two_stage=True)

        architect.design("Build a serverless orders API on AWS")

        usage = architect.last_usage
        assert usage["two_stage"] is True
        assert "stage1" in usage and "stage2" in usage
        assert usage["stage1"]["input_tokens"] == 200
        assert usage["stage1"]["output_tokens"] == 350
        assert usage["stage2"]["input_tokens"] == 600
        assert usage["stage2"]["output_tokens"] == 400
        # Aggregate fields exist for backwards-compatible consumers.
        assert usage["input_tokens"] == 800
        assert usage["output_tokens"] == 750
        assert usage["stage1_tokens"] == 550
        assert usage["stage2_tokens"] == 1000
        assert usage["total_cost_usd"] > 0

    def test_design_falls_back_to_single_shot_when_disabled(self):
        """two_stage=False bypasses Stage 1 — only generate() is called."""
        llm = MagicMock()
        llm.model_name = "claude-sonnet-4-6"
        llm.pricing = {"input": 0.003, "output": 0.015}
        llm.pricing_for = MagicMock(return_value={"input": 0.003, "output": 0.015})
        llm.generate.return_value = (
            _STAGE2_JSON,
            {"input_tokens": 800, "output_tokens": 600, "model": "claude-sonnet-4-6"},
        )

        architect = Architect(llm=llm, two_stage=False)
        spec = architect.design("Build a serverless orders API on AWS")

        assert llm.generate.call_count == 1
        assert llm.generate_fast.call_count == 0
        assert spec.name == "Serverless Orders API"

    def test_modify_with_complex_instruction_uses_two_stage(self):
        """Complex modifications (compliance, redesign) trigger two-stage."""
        from cloudwright.spec import ArchSpec, Component

        llm = _two_stage_mock_llm()
        architect = Architect(llm=llm, two_stage=True)

        base_spec = ArchSpec(
            name="Base",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
                Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={}),
            ],
            constraints=Constraints(),
        )

        architect.modify(base_spec, "Add HIPAA compliance with full encryption and audit logging")

        # Both stages fired.
        assert llm.generate.call_count == 1
        assert llm.generate_fast.call_count == 1

    def test_modify_with_simple_instruction_uses_single_shot(self):
        """Trivial modifications skip Stage 1 to keep latency low."""
        from cloudwright.spec import ArchSpec, Component

        llm = MagicMock()
        llm.model_name = "claude-sonnet-4-6"
        llm.pricing = {"input": 0.003, "output": 0.015}
        llm.pricing_for = MagicMock(return_value={"input": 0.003, "output": 0.015})
        llm.generate_fast.return_value = (_STAGE2_JSON, {"input_tokens": 100, "output_tokens": 200})
        llm.generate.return_value = (_STAGE2_JSON, {"input_tokens": 100, "output_tokens": 200})

        architect = Architect(llm=llm, two_stage=True)
        base_spec = ArchSpec(
            name="Base",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="web", service="ec2", provider="aws", label="Web", tier=2, config={}),
            ],
        )

        architect.modify(base_spec, "rename web to webapp")

        # Single-shot path used generate_fast (simple instruction).
        # No Stage 1 reasoning call.
        assert llm.generate.call_count == 0  # generate not called at all
        assert llm.generate_fast.call_count == 1  # single-shot fast path

    def test_two_stage_spec_includes_boundaries_and_kinds(self):
        """Stage 2 output containing boundaries + connection.kind is preserved into the spec."""
        llm = _two_stage_mock_llm()
        architect = Architect(llm=llm, two_stage=True)

        spec = architect.design("Build a serverless orders API on AWS")

        # Boundary parsed.
        assert len(spec.boundaries) == 1
        assert spec.boundaries[0].id == "main_vpc"
        assert spec.boundaries[0].kind == "vpc"
        # Connection kinds parsed.
        kinds = {(c.source, c.target): c.kind for c in spec.connections}
        assert kinds[("apigw", "fn")] == "sync_request"
        assert kinds[("fn", "orders")] == "sync_request"
