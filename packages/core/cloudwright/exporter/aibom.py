"""OWASP AI BOM exporter for ArchSpec."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from cloudwright import __version__


def _get_model_name() -> str:
    """Detect the active LLM provider and return its model name."""
    import os

    provider = os.environ.get("CLOUDWRIGHT_LLM_PROVIDER", "").lower()
    if provider == "openai" or (
        not provider and os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY")
    ):
        from cloudwright.llm.openai import GENERATE_MODEL

        return GENERATE_MODEL
    from cloudwright.llm.anthropic import GENERATE_MODEL

    return GENERATE_MODEL


if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_AI_SERVICES = frozenset(
    {
        "sagemaker",
        "vertex_ai",
        "azure_ml",
        "bedrock",
        "comprehend",
        "rekognition",
        "textract",
        "translate",
    }
)

_AI_SERVICE_PROVIDERS: dict[str, str] = {
    "sagemaker": "aws",
    "bedrock": "aws",
    "comprehend": "aws",
    "rekognition": "aws",
    "textract": "aws",
    "translate": "aws",
    "vertex_ai": "gcp",
    "azure_ml": "azure",
}


def render(spec: "ArchSpec") -> str:
    now = datetime.now(timezone.utc).isoformat()

    model_name = _get_model_name()
    ai_components: list[dict[str, Any]] = [
        {
            "name": "Cloudwright Architecture AI",
            "type": "llm",
            "provider": "OpenAI" if "gpt" in model_name.lower() else "Anthropic",
            "model": model_name,
            "use_case": "Architecture design and natural language understanding",
            "data_handling": "User architecture descriptions processed via API. No data stored by the model.",
            "risks": [
                "Hallucinated service names",
                "Inaccurate pricing estimates",
            ],
            "mitigations": [
                "Catalog validation",
                "Human review of generated specs",
            ],
        }
    ]

    architecture_ai_services: list[dict[str, Any]] = []
    for c in spec.components:
        if c.service not in _AI_SERVICES:
            continue
        svc_entry: dict[str, Any] = {
            "component_id": c.id,
            "service": c.service,
            "provider": c.provider,
            "description": c.description or c.label,
            "model_details": "Configured via component config",
            "data_handling": "As configured in deployment",
        }
        if c.config:
            svc_entry["config"] = c.config
        architecture_ai_services.append(svc_entry)

    bom: dict[str, Any] = {
        "aibomVersion": "1.0",
        "metadata": {
            "timestamp": now,
            "generator": {"name": "Cloudwright", "version": __version__},
            "architecture": spec.name,
        },
        "aiComponents": ai_components,
        "architectureAIServices": architecture_ai_services,
    }

    return json.dumps(bom, indent=2)
