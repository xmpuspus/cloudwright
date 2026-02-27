"""LLM-powered architecture designer."""

from __future__ import annotations

import json
import re

from silmaril.llm import get_llm
from silmaril.llm.base import BaseLLM
from silmaril.providers import get_equivalent
from silmaril.spec import (
    Alternative,
    ArchSpec,
    Component,
    Connection,
    Constraints,
)

_DESIGN_SYSTEM = """You generate cloud architectures as structured JSON.

Given a natural language description, produce a JSON object with this exact structure:
{
  "name": "Short descriptive name for the architecture",
  "provider": "aws|gcp|azure",
  "region": "primary region (e.g. us-east-1, us-central1, eastus)",
  "components": [
    {
      "id": "unique_snake_case_id",
      "service": "<service_key>",
      "provider": "aws|gcp|azure",
      "label": "Human-readable label",
      "description": "Brief purpose note (instance type, config)",
      "tier": <integer 0-4>,
      "config": {
        "instance_type": "optional",
        "multi_az": true,
        "encryption": true,
        "auto_scaling": true
      }
    }
  ],
  "connections": [
    {
      "source": "component_id",
      "target": "component_id",
      "label": "HTTPS/443",
      "protocol": "HTTPS",
      "port": 443
    }
  ]
}

TIER RULES (vertical positioning, top to bottom):
- Tier 0: Internet-facing entry points (CDN, DNS, API gateway, WAF, users)
- Tier 1: Load balancing and ingress
- Tier 2: Compute (VMs, containers, serverless functions)
- Tier 3: Data layer (databases, caches, message queues)
- Tier 4: Storage, backup, analytics, ML, monitoring

VALID SERVICE KEYS — use exactly these strings:
AWS: cloudfront, route53, api_gateway, waf, alb, nlb, ec2, ecs, eks, lambda, fargate,
     rds, aurora, dynamodb, elasticache, sqs, sns, s3, kinesis, redshift, emr, sagemaker,
     cognito, iam, step_functions, eventbridge, cloudwatch, cloudtrail
GCP: cloud_cdn, cloud_dns, cloud_load_balancing, cloud_armor, compute_engine, gke,
     cloud_run, cloud_functions, app_engine, cloud_sql, firestore, spanner, memorystore,
     pub_sub, cloud_storage, bigquery, dataflow, vertex_ai, firebase_auth, cloud_logging
Azure: azure_cdn, azure_dns, app_gateway, azure_waf, azure_lb, virtual_machines, aks,
       container_apps, azure_functions, app_service, azure_sql, cosmos_db, azure_cache,
       service_bus, event_hubs, blob_storage, synapse, azure_ml, azure_ad, logic_apps,
       azure_monitor

RULES:
- Use 4-12 components to keep architectures clear and practical
- Every component must connect to at least one other component
- Connections flow logically from entry points down to data layer
- Include meaningful labels on connections (protocols, ports, or data type)
- For production workloads, enable multi_az and encryption in config by default
- Match the provider to the user's description; default to aws if unspecified
- Respond with ONLY the JSON object — no markdown, no explanation text"""

_MODIFY_SYSTEM = """You modify an existing cloud architecture based on user instructions.

You will receive the current architecture JSON and a modification instruction.
Return the COMPLETE updated architecture JSON in the same format — never return partial updates.
Preserve all existing component IDs unless explicitly removing or renaming them.
Apply the requested change precisely without unnecessary restructuring.
Respond with ONLY the JSON object — no markdown, no explanation."""


class Architect:
    def __init__(self, llm: BaseLLM | None = None):
        self.llm = llm or get_llm()

    def design(self, description: str, constraints: Constraints | None = None) -> ArchSpec:
        prompt = description
        if constraints:
            parts = []
            if constraints.compliance:
                parts.append(f"Compliance requirements: {', '.join(constraints.compliance)}")
            if constraints.budget_monthly:
                parts.append(f"Monthly budget: ${constraints.budget_monthly:.0f}")
            if constraints.availability:
                parts.append(f"Target availability: {constraints.availability * 100:.1f}%")
            if constraints.regions:
                parts.append(f"Regions: {', '.join(constraints.regions)}")
            if parts:
                prompt += "\n\nConstraints:\n" + "\n".join(f"- {p}" for p in parts)

        messages = [{"role": "user", "content": prompt}]
        text, _usage = self.llm.generate(messages, _DESIGN_SYSTEM, max_tokens=4000)
        data = _extract_json(text)
        return _parse_arch_spec(data, constraints)

    def modify(self, spec: ArchSpec, instruction: str) -> ArchSpec:
        current = spec.model_dump_json(indent=2, exclude_none=True)
        prompt = f"Current architecture:\n{current}\n\nModification: {instruction}"
        messages = [{"role": "user", "content": prompt}]
        text, _usage = self.llm.generate(messages, _MODIFY_SYSTEM, max_tokens=4000)
        data = _extract_json(text)
        updated = _parse_arch_spec(data, spec.constraints)
        # Preserve cost estimate and alternatives from original if LLM didn't regenerate them
        if spec.cost_estimate and not updated.cost_estimate:
            updated.cost_estimate = spec.cost_estimate
        return updated

    def compare(self, spec: ArchSpec, providers: list[str]) -> list[Alternative]:
        from silmaril.cost import CostEngine

        engine = CostEngine()
        return engine.compare_providers(spec, providers)


def _extract_json(text: str) -> dict:
    # Strip markdown code fences if present
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {text[:300]}")
    return json.loads(match.group())


def _parse_arch_spec(data: dict, constraints: Constraints | None) -> ArchSpec:
    components = [
        Component(
            id=c["id"],
            service=c["service"],
            provider=c.get("provider", data.get("provider", "aws")),
            label=c.get("label", c["id"]),
            description=c.get("description", ""),
            tier=c.get("tier", 2),
            config=c.get("config", {}),
        )
        for c in data.get("components", [])
    ]

    connections = [
        Connection(
            source=conn["source"],
            target=conn["target"],
            label=conn.get("label", ""),
            protocol=conn.get("protocol"),
            port=conn.get("port"),
        )
        for conn in data.get("connections", [])
    ]

    return ArchSpec(
        name=data.get("name", "Architecture"),
        provider=data.get("provider", "aws"),
        region=data.get("region", "us-east-1"),
        constraints=constraints,
        components=components,
        connections=connections,
    )


def _map_components(spec: ArchSpec, target_provider: str) -> ArchSpec:
    mapped_components = []
    for comp in spec.components:
        equivalent = get_equivalent(comp.service, comp.provider, target_provider)
        mapped_components.append(
            Component(
                id=comp.id,
                service=equivalent or comp.service,
                provider=target_provider,
                label=comp.label,
                description=comp.description,
                tier=comp.tier,
                config=comp.config.copy(),
            )
        )

    return ArchSpec(
        name=f"{spec.name} ({target_provider.upper()})",
        provider=target_provider,
        region=_default_region(target_provider),
        constraints=spec.constraints,
        components=mapped_components,
        connections=[c.model_copy() for c in spec.connections],
    )


def _diff_services(original: ArchSpec, mapped: ArchSpec) -> list[str]:
    diffs = []
    orig_map = {c.id: c for c in original.components}
    for comp in mapped.components:
        orig = orig_map.get(comp.id)
        if orig and orig.service != comp.service:
            diffs.append(f"{orig.service} -> {comp.service}")
        elif not orig:
            diffs.append(f"Added {comp.service}")
    return diffs


def _default_region(provider: str) -> str:
    return {"aws": "us-east-1", "gcp": "us-central1", "azure": "eastus"}.get(provider, "us-east-1")
