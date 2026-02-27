"""Tests for the Architect — these require LLM API keys so are skipped in CI.

Run with: ANTHROPIC_API_KEY=... pytest packages/core/tests/test_architect.py -v
"""

import os

import pytest
from cloudwright.spec import ArchSpec, Constraints

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

HAS_LLM = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
skip_no_llm = pytest.mark.skipif(not HAS_LLM, reason="No LLM API key available")


@skip_no_llm
class TestArchitect:
    def test_design_basic(self):
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design("Simple 2-tier web app on AWS with EC2 and RDS")
        assert isinstance(spec, ArchSpec)
        assert spec.name
        assert len(spec.components) >= 2
        assert spec.provider == "aws"

    def test_design_with_constraints(self):
        from cloudwright.architect import Architect

        arch = Architect()
        constraints = Constraints(budget_monthly=200.0, compliance=["hipaa"])
        spec = arch.design("Web app with database", constraints=constraints)
        assert isinstance(spec, ArchSpec)
        assert spec.constraints is not None

    def test_modify(self):
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design("Web app on AWS with EC2 and RDS")
        modified = arch.modify(spec, "Add ElastiCache Redis between EC2 and RDS")
        assert isinstance(modified, ArchSpec)
        assert len(modified.components) >= len(spec.components)

    def test_compare_providers(self):
        from cloudwright.architect import Architect

        arch = Architect()
        spec = arch.design("3-tier web app on AWS")
        alternatives = arch.compare(spec, providers=["gcp", "azure"])
        assert len(alternatives) >= 1
        for alt in alternatives:
            assert alt.provider in ("gcp", "azure")
