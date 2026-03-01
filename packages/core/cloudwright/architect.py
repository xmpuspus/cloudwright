"""LLM-powered architecture designer."""

from __future__ import annotations

import json
import logging
import re

from cloudwright.llm import get_llm
from cloudwright.llm.base import BaseLLM
from cloudwright.providers import get_equivalent
from cloudwright.spec import (
    Alternative,
    ArchSpec,
    Component,
    Connection,
    Constraints,
)

log = logging.getLogger(__name__)

# Services that are data stores — encryption and backup defaults applied
_DATA_STORE_SERVICES = {
    "rds",
    "aurora",
    "dynamodb",
    "s3",
    "elasticache",
    "redshift",
    "cloud_sql",
    "firestore",
    "spanner",
    "memorystore",
    "cloud_storage",
    "bigquery",
    "azure_sql",
    "cosmos_db",
    "azure_cache",
    "blob_storage",
    "synapse",
    "alloydb",
    "fsx",
    "efs",
}

# Databases that support multi-AZ / replication
_DATABASE_SERVICES = {
    "rds",
    "aurora",
    "cloud_sql",
    "azure_sql",
    "cosmos_db",
    "spanner",
    "synapse",
    "redshift",
    "bigquery",
    "alloydb",
}

_COMPUTE_SERVICES = {
    "ec2",
    "ecs",
    "eks",
    "lambda",
    "compute_engine",
    "gke",
    "cloud_run",
    "cloud_functions",
    "virtual_machines",
    "aks",
    "azure_functions",
    "app_service",
    "container_apps",
    "app_engine",
    "fargate",
}

# HIPAA required service types (by service key or category)
_HIPAA_REQUIRED = {
    "audit_logging": {"cloudtrail", "cloud_logging", "azure_monitor"},
    "access_control": {"cognito", "firebase_auth", "azure_ad", "iam"},
}

_COMPLIANCE_CONTROLS: dict[str, str] = {
    "hipaa": (
        "REQUIRED: encryption_at_rest on all data stores, encryption_in_transit on all "
        "connections, audit_logging service (cloudtrail/cloud_logging/azure_monitor), "
        "access_control via auth service (cognito/firebase_auth/azure_ad), "
        "all services must be BAA-eligible"
    ),
    "pci-dss": (
        "REQUIRED: WAF/firewall on entry points, encryption on all data stores and connections, "
        "audit logging, network segmentation (separate tiers), no cardholder data in logs"
    ),
    "soc2": (
        "REQUIRED: audit logging service, encryption on data stores, access control service, "
        "monitoring/alerting (cloudwatch/cloud_monitoring/azure_monitor)"
    ),
    "gdpr": (
        "REQUIRED: encryption on all data stores, audit logging, access control service, "
        "data residency controls — do not store data outside approved regions"
    ),
    "fedramp": (
        "REQUIRED: FIPS 140-2 compliant services only, MFA/access control, audit logging, "
        "encryption at rest and in transit, US regions only"
    ),
}

# Last updated: 2026-03-01
_SERVICE_KEYS = """VALID SERVICE KEYS — use exactly these strings:
AWS: cloudfront, route53, api_gateway, waf, alb, nlb, ec2, ecs, eks, lambda, fargate,
     rds, aurora, dynamodb, elasticache, sqs, sns, s3, kinesis, redshift, emr, sagemaker,
     cognito, iam, step_functions, eventbridge, cloudwatch, cloudtrail, dms, migration_hub,
     direct_connect, vpn, codepipeline, codecommit, codebuild, ecr, config, guardduty,
     inspector, kms, shield, security_hub, glue, athena, fsx, efs, ebs
GCP: cloud_cdn, cloud_dns, cloud_load_balancing, cloud_armor, compute_engine, gke,
     cloud_run, cloud_functions, app_engine, cloud_sql, firestore, spanner, memorystore,
     pub_sub, cloud_storage, bigquery, dataflow, vertex_ai, firebase_auth, cloud_logging,
     cloud_build, artifact_registry, cloud_composer, dataproc, cloud_interconnect, alloydb
Azure: azure_cdn, azure_dns, app_gateway, azure_waf, azure_lb, virtual_machines, aks,
       container_apps, azure_functions, app_service, azure_sql, cosmos_db, azure_cache,
       service_bus, event_hubs, blob_storage, synapse, azure_ml, azure_ad, logic_apps,
       azure_monitor, azure_devops, azure_migrate, expressroute, azure_firewall,
       azure_sentinel, azure_policy, data_factory, api_management"""

# Last updated: 2026-03-01
_MODEL_VERSION_GUIDANCE = """
CURRENT AI/ML MODEL VERSIONS (as of March 2026):
GCP Vertex AI: gemini-3.1-pro (flagship), gemini-3-flash, gemini-2.5-pro, gemini-2.5-flash
AWS Bedrock: anthropic.claude-opus-4-6-v1, anthropic.claude-sonnet-4-6, amazon.nova-pro-v1
AWS SageMaker: meta.llama3.3-70b, mistral-large-3
Azure OpenAI: gpt-5 (GA), gpt-5-mini, gpt-5-nano, gpt-5.2 (preview)
When an architecture includes ML/AI services (vertex_ai, sagemaker, azure_ml), use these current
model versions in the config. Do NOT use outdated versions like gemini-1.5-pro or gpt-4-turbo."""

_DESIGN_SYSTEM = f"""You generate cloud architectures as structured JSON.

Given a natural language description, produce a JSON object with this exact structure:
{{
  "name": "Short descriptive name for the architecture",
  "provider": "aws|gcp|azure",
  "region": "primary region (e.g. us-east-1, us-central1, eastus)",
  "components": [
    {{
      "id": "unique_snake_case_id",
      "service": "<service_key>",
      "provider": "aws|gcp|azure",
      "label": "Human-readable label",
      "description": "Brief purpose note (instance type, config)",
      "tier": <integer 0-4>,
      "config": {{
        "instance_type": "optional",
        "multi_az": true,
        "encryption": true,
        "auto_scaling": true
      }}
    }}
  ],
  "connections": [
    {{
      "source": "component_id",
      "target": "component_id",
      "label": "HTTPS/443",
      "protocol": "HTTPS",
      "port": 443
    }}
  ],
  "rationale": [
    {{"decision": "Short description of a key design decision", "reason": "Why this choice was made"}}
  ],
  "suggestions": ["add a Redis cache for session management", "swap RDS for Aurora Serverless", "add CloudWatch monitoring"]
}}

TIER RULES (vertical positioning, top to bottom):
- Tier 0: Internet-facing entry points (CDN, DNS, API gateway, WAF, users)
- Tier 1: Load balancing and ingress
- Tier 2: Compute (VMs, containers, serverless functions)
- Tier 3: Data layer (databases, caches, message queues)
- Tier 4: Storage, backup, analytics, ML, monitoring

{_SERVICE_KEYS}

RULES:
- Use 4-12 components to keep architectures clear and practical
- Every component must connect to at least one other component
- Connections flow logically from entry points down to data layer
- Include meaningful labels on connections (protocols, ports, or data type)
- For production workloads, enable multi_az and encryption in config by default
- Match the provider to the user's description; default to aws if unspecified
- Respond with ONLY the JSON object — no markdown, no explanation text
- Include 2-4 "rationale" entries explaining key design decisions
- Include 3 "suggestions" for modifications the user might want to make next
- When the user mentions a specific service by name (e.g. "use RDS", "with Lambda"), INCLUDE that exact service in components. Do not substitute alternatives unless explicitly asked.
- Use EXACT service keys listed above. Do not invent compound keys like 'rds_postgres' — use 'rds' with `engine: postgres` in config.

For ALL architectures, ensure component configs include:
- encryption: true on all data stores and caches
- multi_az: true on all databases (for production workloads)
- backup: true on all databases
- auto_scaling: true on all compute services
- security_groups: true on all VPC-connected resources
- ALWAYS include instance_type in config for EC2/compute_engine/virtual_machines (e.g. m5.large, n2-standard-4, Standard_D4s_v3)
- ALWAYS include instance_class in config for RDS/Aurora/Cloud SQL/Azure SQL (e.g. db.r5.large, db-n1-standard-4)
- ALWAYS include node_type in config for ElastiCache/Memorystore (e.g. cache.r5.large)
- Include storage_gb on all database and storage components
- Include count on compute components when multiple instances needed
{_MODEL_VERSION_GUIDANCE}"""

_MODIFY_SYSTEM = f"""You modify an existing cloud architecture based on user instructions.

You will receive the current architecture JSON and a modification instruction.
Return the COMPLETE updated architecture JSON in the same format — never return partial updates.
Preserve all existing component IDs unless explicitly removing or renaming them.
Apply the requested change precisely without unnecessary restructuring.
Respond with ONLY the JSON object — no markdown, no explanation.
{_MODEL_VERSION_GUIDANCE}"""


_CHAT_SYSTEM = f"""You are a cloud architecture assistant. You help design and refine architectures through conversation.

When the user asks you to generate or modify an architecture, respond with a JSON object using the same schema as a design prompt (name, provider, region, components, connections).

When generating architecture JSON, also include:
- "rationale": key design decisions with reasons
- "suggestions": 3 concrete modifications the user could request next

When the user asks questions or wants to discuss trade-offs, respond conversationally — no JSON needed.

{_SERVICE_KEYS}
{_MODEL_VERSION_GUIDANCE}"""

_IMPORT_SYSTEM = f"""You parse infrastructure descriptions or state into structured JSON architecture specs.

Given a description of existing infrastructure, produce a JSON object using the same schema as a design prompt
(name, provider, region, components, connections).
Focus on mapping existing resources to the correct service keys, preserving the actual topology,
and including real configuration values (instance types, storage sizes, etc.).

Respond with ONLY the JSON object — no markdown, no explanation.

{_SERVICE_KEYS}

TERRAFORM RESOURCE TYPE MAPPING (use these when parsing Terraform state/config):
- aws_instance, aws_autoscaling_group -> ec2
- aws_lb, aws_alb -> alb
- aws_rds_instance, aws_rds_cluster -> rds (aurora for clusters)
- aws_lambda_function -> lambda
- aws_ecs_service, aws_ecs_cluster -> ecs
- aws_eks_cluster -> eks
- aws_s3_bucket -> s3
- aws_dynamodb_table -> dynamodb
- aws_elasticache_cluster -> elasticache
- aws_cloudfront_distribution -> cloudfront
- aws_sqs_queue -> sqs
- google_compute_instance -> compute_engine
- google_container_cluster -> gke
- google_sql_database_instance -> cloud_sql
- google_cloud_run_service -> cloud_run
- google_storage_bucket -> cloud_storage
- azurerm_virtual_machine -> virtual_machines
- azurerm_kubernetes_cluster -> aks
- azurerm_mssql_server -> azure_sql
- azurerm_cosmosdb_account -> cosmos_db
- azurerm_storage_account -> blob_storage

RULES:
- Map every resource to its closest service key
- Preserve actual instance types and configurations
- Include all connections between resources
- Respond with ONLY the JSON object"""

_MIGRATION_SYSTEM = f"""You design target cloud architectures for migration scenarios.

Given a source architecture and migration requirements, produce a JSON object representing the target architecture.
Focus on service equivalence across cloud providers, preserving functionality while modernizing where appropriate,
and including realistic instance types for the target provider.

Respond with ONLY the JSON object — no markdown, no explanation.

{_SERVICE_KEYS}

RULES:
- Map each source service to its target provider equivalent
- Preserve capacity (instance sizes, storage, redundancy)
- Include instance_type/instance_class in all compute/database configs
- Respond with ONLY the JSON object"""

_COMPARISON_SYSTEM = f"""You generate a representative cloud architecture that can be compared across providers.

Given a workload description, produce a JSON object representing a single canonical architecture.
This architecture will be re-priced across multiple cloud providers for comparison.

Respond with ONLY the JSON object — no markdown, no explanation.

{_SERVICE_KEYS}

RULES:
- Design a single provider-agnostic architecture using the primary provider's service keys
- Include realistic instance types and configurations for accurate pricing
- Respond with ONLY the JSON object"""

# Valid services per provider — used for consistency validation
_PROVIDER_SERVICES: dict[str, set[str]] = {
    "aws": {
        "cloudfront",
        "route53",
        "api_gateway",
        "waf",
        "alb",
        "nlb",
        "ec2",
        "ecs",
        "eks",
        "lambda",
        "fargate",
        "rds",
        "aurora",
        "dynamodb",
        "elasticache",
        "sqs",
        "sns",
        "s3",
        "kinesis",
        "redshift",
        "emr",
        "sagemaker",
        "cognito",
        "iam",
        "step_functions",
        "eventbridge",
        "cloudwatch",
        "cloudtrail",
        "dms",
        "migration_hub",
        "direct_connect",
        "vpn",
        "codepipeline",
        "codecommit",
        "codebuild",
        "ecr",
        "config",
        "guardduty",
        "inspector",
        "kms",
        "shield",
        "security_hub",
        "glue",
        "athena",
        "fsx",
        "efs",
        "ebs",
    },
    "gcp": {
        "cloud_cdn",
        "cloud_dns",
        "cloud_load_balancing",
        "cloud_armor",
        "compute_engine",
        "gke",
        "cloud_run",
        "cloud_functions",
        "app_engine",
        "cloud_sql",
        "firestore",
        "spanner",
        "memorystore",
        "pub_sub",
        "cloud_storage",
        "bigquery",
        "dataflow",
        "vertex_ai",
        "firebase_auth",
        "cloud_logging",
        "cloud_build",
        "artifact_registry",
        "cloud_composer",
        "dataproc",
        "cloud_interconnect",
        "alloydb",
    },
    "azure": {
        "azure_cdn",
        "azure_dns",
        "app_gateway",
        "azure_waf",
        "azure_lb",
        "virtual_machines",
        "aks",
        "container_apps",
        "azure_functions",
        "app_service",
        "azure_sql",
        "cosmos_db",
        "azure_cache",
        "service_bus",
        "event_hubs",
        "blob_storage",
        "synapse",
        "azure_ml",
        "azure_ad",
        "logic_apps",
        "azure_monitor",
        "azure_devops",
        "azure_migrate",
        "expressroute",
        "azure_firewall",
        "azure_sentinel",
        "azure_policy",
        "data_factory",
        "api_management",
    },
}

_ALL_VALID_SERVICES: set[str] = set().union(*_PROVIDER_SERVICES.values())

# Default instance types when LLM omits them
_DEFAULT_INSTANCE_TYPES: dict[str, dict[str, str]] = {
    "aws": {"compute": "m5.large", "database": "db.r5.large", "cache": "cache.r5.large"},
    "gcp": {"compute": "n2-standard-4", "database": "db-n1-standard-4", "cache": "M1"},
    "azure": {"compute": "Standard_D4s_v3", "database": "GP_Gen5_4", "cache": "C3"},
}

# Default connection ports by tier relationship
_DEFAULT_CONNECTION_PROTOCOLS: list[tuple[tuple[int, int], str, int]] = [
    ((0, 1), "HTTPS", 443),
    ((1, 2), "HTTPS", 443),
    ((2, 3), "TCP", 5432),  # database tier
]


class ConversationSession:
    """Multi-turn architecture design conversation with history tracking."""

    def __init__(self, llm: BaseLLM | None = None, constraints: Constraints | None = None):
        self.llm = llm or get_llm()
        self.constraints = constraints
        self.history: list[dict] = []
        self.current_spec: ArchSpec | None = None
        self._error_hints: list[str] = []

    def send(self, message: str) -> tuple[str, ArchSpec | None]:
        """Send a user message and get response + optionally updated spec."""
        self.history.append({"role": "user", "content": message})
        system = self._build_system_with_hints(_CHAT_SYSTEM)
        text, _usage = self.llm.generate(self.history, system, max_tokens=4000)
        self.history.append({"role": "assistant", "content": text})

        spec = self._try_parse_spec(text)
        if spec is not None:
            if self.constraints:
                spec = spec.model_copy(update={"constraints": self.constraints})
            self.current_spec = spec

        return text, spec

    def modify(self, instruction: str) -> ArchSpec:
        """Modify the current spec with a natural language instruction."""
        if self.current_spec is None:
            raise ValueError("No current architecture to modify. Use send() to create one first.")

        current_json = _slim_for_modify(self.current_spec)
        prompt = f"Current architecture:\n{current_json}\n\nModification: {instruction}"

        self.history.append({"role": "user", "content": prompt})
        system = self._build_system_with_hints(_MODIFY_SYSTEM)
        text, _usage = self.llm.generate(self.history, system, max_tokens=3000)
        self.history.append({"role": "assistant", "content": text})

        data = _extract_json(text)
        updated = _parse_arch_spec(data, self.constraints)

        original_ids = {c.id for c in self.current_spec.components}
        updated_ids = {c.id for c in updated.components}
        dropped = original_ids - updated_ids
        if dropped:
            remove_words = {"remove", "delete", "drop", "eliminate", "get rid of"}
            explicitly_removed = any(w in instruction.lower() for w in remove_words)
            if not explicitly_removed:
                restored = list(updated.components)
                original_map = {c.id: c for c in self.current_spec.components}
                for cid in dropped:
                    restored.append(original_map[cid])
                updated = updated.model_copy(update={"components": restored})
                log.warning("Restored %d dropped components: %s", len(dropped), dropped)
                self._error_hints.append("Do not remove existing components unless explicitly asked")

        if self.current_spec.cost_estimate and not updated.cost_estimate:
            updated = updated.model_copy(update={"cost_estimate": self.current_spec.cost_estimate})

        self.current_spec = updated
        return updated

    def _try_parse_spec(self, text: str) -> ArchSpec | None:
        """Try to extract an ArchSpec from LLM response. Returns None if not parseable."""
        try:
            data = _extract_json(text)
            if "components" not in data or not data["components"]:
                return None
            return _parse_arch_spec(data, self.constraints)
        except (ValueError, KeyError, json.JSONDecodeError):
            return None

    def _build_system_with_hints(self, base_system: str) -> str:
        if not self._error_hints:
            return base_system
        hints = "\n".join(f"- {h}" for h in self._error_hints[-5:])
        return f"{base_system}\n\nLEARNINGS FROM THIS SESSION (avoid repeating):\n{hints}"


class Architect:
    def __init__(self, llm: BaseLLM | None = None):
        self.llm = llm or get_llm()

    def design(self, description: str, constraints: Constraints | None = None) -> ArchSpec:
        # Check if a pre-computed template matches before calling the LLM
        provider = constraints.regions[0].split("-")[0] if constraints and constraints.regions else None
        template = _match_template_for_design(description, provider)
        if template is not None:
            log.info("Template match — skipping LLM call for design")
            spec = _parse_arch_spec(template, constraints)
            if constraints and constraints.regions:
                spec = spec.model_copy(update={"region": constraints.regions[0]})
            return spec

        system = self._select_system_prompt(description)
        if constraints:
            system += _build_constraint_prompt(constraints)

        max_tokens = 4000 if len(description) > 200 or self._is_complex_use_case(description) else 2500
        messages = [{"role": "user", "content": description}]

        try:
            text, _usage = self.llm.generate(messages, system, max_tokens=max_tokens)
            data = _extract_json(text)
        except (ValueError, json.JSONDecodeError) as first_err:
            log.warning("First design attempt failed: %s — retrying", first_err)
            messages.append({"role": "assistant", "content": "I apologize, let me provide the JSON."})
            messages.append(
                {
                    "role": "user",
                    "content": "You must respond with ONLY a valid JSON object. No markdown, no explanation.",
                }
            )
            text, _usage = self.llm.generate(messages, system, max_tokens=max_tokens)
            data = _extract_json(text)

        return _parse_arch_spec(data, constraints)

    @staticmethod
    def _select_system_prompt(description: str) -> str:
        desc_lower = description.lower()
        import_keywords = {
            "import",
            "terraform state",
            "cloudformation template",
            "existing infrastructure",
            "current setup",
        }
        migrate_keywords = {"migrate", "re-architect", "modernize", "move to", "transition to"}
        # Use word-boundary regex for short keywords to avoid substring false positives
        compare_phrases = {"compare", "versus", "cost comparison"}
        compare_word_patterns = {r"\bvs\b", r"\btco\b"}

        if any(kw in desc_lower for kw in import_keywords):
            return _IMPORT_SYSTEM
        if any(kw in desc_lower for kw in migrate_keywords):
            return _MIGRATION_SYSTEM
        if any(kw in desc_lower for kw in compare_phrases):
            return _COMPARISON_SYSTEM
        if any(re.search(pat, desc_lower) for pat in compare_word_patterns):
            return _COMPARISON_SYSTEM
        return _DESIGN_SYSTEM

    @staticmethod
    def _is_complex_use_case(description: str) -> bool:
        desc_lower = description.lower()
        complex_keywords = {"import", "migrate", "re-architect", "compare", "versus", "modernize"}
        return any(kw in desc_lower for kw in complex_keywords)

    def modify(self, spec: ArchSpec, instruction: str) -> ArchSpec:
        current = _slim_for_modify(spec)
        prompt = f"Current architecture:\n{current}\n\nModification: {instruction}"
        messages = [{"role": "user", "content": prompt}]

        # Route simple modifications to the fast model to reduce latency
        if _is_simple_modification(instruction):
            text, _usage = self.llm.generate_fast(messages, _MODIFY_SYSTEM, max_tokens=3000)
        else:
            text, _usage = self.llm.generate(messages, _MODIFY_SYSTEM, max_tokens=3000)

        data = _extract_json(text)
        updated = _parse_arch_spec(data, spec.constraints)

        # Verify no components were silently dropped by the LLM
        original_ids = {c.id for c in spec.components}
        updated_ids = {c.id for c in updated.components}
        dropped = original_ids - updated_ids
        if dropped:
            remove_words = {"remove", "delete", "drop", "eliminate", "get rid of"}
            explicitly_removed = any(w in instruction.lower() for w in remove_words)
            if not explicitly_removed:
                restored = list(updated.components)
                original_map = {c.id: c for c in spec.components}
                for cid in dropped:
                    restored.append(original_map[cid])
                updated = updated.model_copy(update={"components": restored})
                log.warning("Restored %d dropped components: %s", len(dropped), dropped)

        # Preserve cost estimate and alternatives from original if LLM didn't regenerate them
        if spec.cost_estimate and not updated.cost_estimate:
            updated.cost_estimate = spec.cost_estimate
        return updated

    def compare(self, spec: ArchSpec, providers: list[str]) -> list[Alternative]:
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        return engine.compare_providers(spec, providers)


def _is_simple_modification(instruction: str) -> bool:
    """Heuristic: short instructions without compliance/migration keywords are simple."""
    words = instruction.split()
    if len(words) > 25:
        return False
    complex_keywords = {
        "compliance",
        "hipaa",
        "pci",
        "soc2",
        "gdpr",
        "fedramp",
        "migrate",
        "redesign",
        "re-architect",
        "overhaul",
        "security audit",
    }
    return not any(kw in instruction.lower() for kw in complex_keywords)


def _slim_for_modify(spec: ArchSpec) -> str:
    """Serialize spec with minimal fields for LLM modify prompt."""
    data = spec.model_dump(exclude_none=True)
    data.pop("cost_estimate", None)
    data.pop("metadata", None)
    for comp in data.get("components", []):
        comp.pop("description", None)
        cfg = comp.get("config", {})
        keep_keys = {
            "instance_type",
            "instance_class",
            "node_type",
            "storage_gb",
            "count",
            "engine",
            "model",
            "cpu",
            "memory",
            "min_instances",
            "max_instances",
        }
        comp["config"] = {k: v for k, v in cfg.items() if k in keep_keys}
    return json.dumps(data, indent=2)


def _match_template_for_design(description: str, provider: str | None) -> dict | None:
    """Return a template dict if the description matches with high confidence."""
    from cloudwright.templates import match_template

    return match_template(description, provider)


def _build_constraint_prompt(constraints: Constraints) -> str:
    """Build a structured constraint section to inject into the system prompt."""
    sections: list[str] = []

    if constraints.budget_monthly:
        sections.append(
            f"HARD LIMIT: Total monthly cost MUST NOT exceed ${constraints.budget_monthly:.0f}. "
            "If a component would push the total over budget, use a smaller instance type or "
            "remove non-essential components."
        )

    for framework in constraints.compliance:
        key = framework.lower()
        if key in _COMPLIANCE_CONTROLS:
            sections.append(f"COMPLIANCE ({framework.upper()}): {_COMPLIANCE_CONTROLS[key]}")
        else:
            sections.append(f"COMPLIANCE ({framework.upper()}): Follow all controls for {framework}.")

    if constraints.regions:
        region = constraints.regions[0]
        sections.append(f"ALL components must be in region: {region}. Do not use services unavailable in this region.")

    if constraints.availability and constraints.availability > 0.99:
        sections.append(
            "REQUIRED: multi_az=true on all data stores, auto_scaling on compute, load balancer "
            f"(target availability: {constraints.availability * 100:.2f}%)"
        )

    if constraints.latency_ms:
        sections.append(
            f"LATENCY TARGET: {constraints.latency_ms:.0f}ms max — prefer low-latency services and regions."
        )

    if constraints.data_residency:
        regions_str = ", ".join(constraints.data_residency)
        sections.append(
            f"DATA RESIDENCY: Data must remain in: {regions_str}. Do not route or replicate outside these locations."
        )

    if constraints.throughput_rps:
        sections.append(
            f"THROUGHPUT TARGET: {constraints.throughput_rps:,} RPS — ensure auto_scaling and "
            "sufficient capacity on compute and data layers."
        )

    if not sections:
        return ""
    return "\n\nCONSTRAINTS — these are non-negotiable:\n" + "\n".join(f"- {s}" for s in sections)


def _post_validate(spec: ArchSpec, constraints: Constraints | None) -> ArchSpec:
    """Apply safe defaults to all architectures and enforce constraint-specific controls."""
    components = [c.model_copy(deep=True) for c in spec.components]
    changed = False
    multi_component = len(components) > 3

    for i, comp in enumerate(components):
        cfg = dict(comp.config)
        updated = False

        # Encryption and backup on all data stores
        if comp.service in _DATA_STORE_SERVICES:
            if not cfg.get("encryption"):
                cfg["encryption"] = True
                updated = True
            if not cfg.get("backup"):
                cfg["backup"] = True
                updated = True

        # multi_az on databases when there are enough components to warrant it
        if comp.service in _DATABASE_SERVICES and multi_component:
            if not cfg.get("multi_az"):
                cfg["multi_az"] = True
                updated = True

        # auto_scaling on all compute
        if comp.service in _COMPUTE_SERVICES:
            if not cfg.get("auto_scaling"):
                cfg["auto_scaling"] = True
                updated = True

        # Fill missing instance type/class/node_type defaults
        provider = comp.provider or spec.provider
        defaults = _DEFAULT_INSTANCE_TYPES.get(provider, _DEFAULT_INSTANCE_TYPES["aws"])

        if comp.service in _COMPUTE_SERVICES and "instance_type" not in cfg:
            cfg["instance_type"] = defaults["compute"]
            updated = True
            log.warning("Set default instance_type '%s' on component %s", defaults["compute"], comp.id)

        if comp.service in _DATABASE_SERVICES and "instance_class" not in cfg:
            cfg["instance_class"] = defaults["database"]
            updated = True
            log.warning("Set default instance_class '%s' on component %s", defaults["database"], comp.id)

        if comp.service in {"elasticache", "memorystore", "azure_cache"} and "node_type" not in cfg:
            cfg["node_type"] = defaults["cache"]
            updated = True
            log.warning("Set default node_type '%s' on component %s", defaults["cache"], comp.id)

        if comp.service in _DATABASE_SERVICES and "storage_gb" not in cfg:
            cfg["storage_gb"] = 100
            updated = True
            log.warning("Set default storage_gb 100 on component %s", comp.id)

        if comp.service in _COMPUTE_SERVICES and "count" not in cfg:
            cfg["count"] = 2
            updated = True
            log.warning("Set default count 2 on component %s", comp.id)

        if updated:
            components[i] = comp.model_copy(update={"config": cfg})
            changed = True

    if constraints:
        # Budget check — warn when over limit
        if constraints.budget_monthly and spec.cost_estimate:
            total = spec.cost_estimate.monthly_total
            if total > constraints.budget_monthly:
                log.warning(
                    "Architecture cost $%.2f/mo exceeds budget limit of $%.2f/mo",
                    total,
                    constraints.budget_monthly,
                )

    if not changed:
        return spec

    return spec.model_copy(update={"components": components})


def _extract_json(text: str) -> dict:
    """Extract the first complete JSON object from text using brace counting."""
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.replace("```", "")

    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in LLM response: {text[:300]}")

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\":
            if in_string:
                escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])

    raise ValueError(f"Unterminated JSON object in LLM response: {text[:300]}")


_SERVICE_NORMALIZATION: dict[str, str] = {
    "aws_rds": "rds",
    "aws_lambda": "lambda",
    "aws_ec2": "ec2",
    "aws_ecs": "ecs",
    "aws_eks": "eks",
    "aws_s3": "s3",
    "lambda_function": "lambda",
    "s3_bucket": "s3",
    "gcp_gke": "gke",
    "gcp_cloud_run": "cloud_run",
    "azure_aks": "aks",
    "azure_vm": "virtual_machines",
    "rds_postgres": "rds",
    "rds_mysql": "rds",
    "aurora_postgres": "aurora",
    "aurora_mysql": "aurora",
    "gcp_alloydb": "alloydb",
    "gcp_cloud_armor": "cloud_armor",
    "gcp_vertex_ai": "vertex_ai",
    "gcp_firestore": "firestore",
    "gcp_spanner": "spanner",
    "gcp_dataflow": "dataflow",
    "gcp_dataproc": "dataproc",
    "gcp_cloud_composer": "cloud_composer",
    "aws_eventbridge": "eventbridge",
    "aws_athena": "athena",
    "aws_glue": "glue",
    "aws_fargate": "fargate",
    "aws_shield": "shield",
    "azure_api_management": "api_management",
    "azure_data_factory": "data_factory",
    "azure_logic_apps": "logic_apps",
    "azure_cosmos_db": "cosmos_db",
    "azure_sentinel": "azure_sentinel",
    # Additional LLM mistakes
    "cloud_function": "cloud_functions",
    "pubsub": "pub_sub",
    "pub/sub": "pub_sub",
    "cloud_run_service": "cloud_run",
    "gcs": "cloud_storage",
    "bq": "bigquery",
    "big_query": "bigquery",
    "cloud_sql_instance": "cloud_sql",
    "aws_sqs": "sqs",
    "aws_sns": "sns",
    "aws_cloudwatch": "cloudwatch",
    "aws_cloudtrail": "cloudtrail",
    "aws_kinesis": "kinesis",
    "azure_blob": "blob_storage",
    "azure_cosmosdb": "cosmos_db",
    "azure_redis": "azure_cache",
    "redis": "elasticache",
    "postgres": "rds",
    "mysql": "rds",
    "mongodb": "cosmos_db",
    "kubernetes": "eks",
    "docker": "ecs",
}

# Services that carry engine info in their compound name
_SERVICE_ENGINE_SUFFIXES: dict[str, str] = {
    "rds_postgres": "postgres",
    "rds_mysql": "mysql",
    "aurora_postgres": "postgres",
    "aurora_mysql": "mysql",
}


def _enforce_connections(spec: ArchSpec) -> ArchSpec:
    """Validate connection references and add defaults for isolated components."""
    component_ids = {c.id for c in spec.components}
    id_to_comp = {c.id: c for c in spec.components}

    # Remove connections with invalid source/target references
    valid_conns = [c for c in spec.connections if c.source in component_ids and c.target in component_ids]
    dropped_count = len(spec.connections) - len(valid_conns)
    if dropped_count:
        log.warning("Removed %d orphan connections (invalid component references)", dropped_count)

    # Find components with no connections
    connected_ids: set[str] = set()
    for c in valid_conns:
        connected_ids.add(c.source)
        connected_ids.add(c.target)

    isolated = [c for c in spec.components if c.id not in connected_ids]
    new_conns = list(valid_conns)

    if isolated and spec.components:
        # Sort all components by tier for nearest-neighbor wiring
        tier_sorted = sorted(spec.components, key=lambda c: c.tier)
        for iso in isolated:
            # Find the nearest non-isolated component at an adjacent tier
            candidate = None
            for comp in tier_sorted:
                if comp.id != iso.id and comp.id in connected_ids:
                    candidate = comp
                    if abs(comp.tier - iso.tier) <= 1:
                        break

            if candidate:
                # Pick source/target based on tier ordering
                if iso.tier <= candidate.tier:
                    src, tgt = iso.id, candidate.id
                else:
                    src, tgt = candidate.id, iso.id

                # Choose protocol/port based on target service
                tgt_comp = id_to_comp.get(tgt)
                if tgt_comp and tgt_comp.service in _DATABASE_SERVICES:
                    proto, port, label = "TCP", 5432, "TCP/5432"
                elif tgt_comp and tgt_comp.service in {"elasticache", "memorystore", "azure_cache"}:
                    proto, port, label = "TCP", 6379, "TCP/6379"
                else:
                    proto, port, label = "HTTPS", 443, "HTTPS/443"

                new_conns.append(Connection(source=src, target=tgt, label=label, protocol=proto, port=port))
                log.warning("Auto-connected isolated component %s -> %s", src, tgt)

    # Add default protocol/port to connections missing them
    final_conns = []
    for conn in new_conns:
        if conn.protocol is None or conn.port is None:
            src_comp = id_to_comp.get(conn.source)
            tgt_comp = id_to_comp.get(conn.target)
            if tgt_comp and tgt_comp.service in _DATABASE_SERVICES:
                conn = conn.model_copy(update={"protocol": "TCP", "port": 5432})
            elif tgt_comp and tgt_comp.service in {"elasticache", "memorystore", "azure_cache"}:
                conn = conn.model_copy(update={"protocol": "TCP", "port": 6379})
            elif src_comp and tgt_comp:
                # Higher-tier to lower-tier → HTTPS by default
                if src_comp.tier <= 2:
                    conn = conn.model_copy(update={"protocol": "HTTPS", "port": 443})
        final_conns.append(conn)

    if final_conns != spec.connections or valid_conns != spec.connections:
        return spec.model_copy(update={"connections": final_conns})
    return spec


def _parse_arch_spec(data: dict, constraints: Constraints | None) -> ArchSpec:
    components = [
        Component(
            id=c["id"],
            service=c["service"],
            provider=c.get("provider", data.get("provider", "aws")),
            label=c.get("label", c["id"]),
            description=c.get("description", ""),
            tier=int(c.get("tier", 2)),
            config=c.get("config", {}),
        )
        for c in data.get("components", [])
    ]

    # Normalize common LLM service key mistakes
    normalized = []
    for comp in components:
        raw = comp.service
        if raw in _SERVICE_NORMALIZATION:
            fixed = _SERVICE_NORMALIZATION[raw]
            log.warning("Normalizing service key '%s' -> '%s' (component: %s)", raw, fixed, comp.id)
            cfg = dict(comp.config)
            if raw in _SERVICE_ENGINE_SUFFIXES:
                cfg.setdefault("engine", _SERVICE_ENGINE_SUFFIXES[raw])
            comp = comp.model_copy(update={"service": fixed, "config": cfg})
        elif raw not in _ALL_VALID_SERVICES:
            # Try stripping cloud provider prefix (e.g. aws_firehose -> firehose)
            for prefix in ("aws_", "gcp_", "azure_", "google_"):
                if raw.startswith(prefix):
                    stripped = raw[len(prefix) :]
                    if stripped in _ALL_VALID_SERVICES:
                        log.warning(
                            "Stripping prefix from service key '%s' -> '%s' (component: %s)",
                            raw,
                            stripped,
                            comp.id,
                        )
                        comp = comp.model_copy(update={"service": stripped})
                        break
        normalized.append(comp)
    components = normalized

    # Validate provider consistency — auto-fix cross-provider service keys
    validated = []
    for comp in components:
        provider = comp.provider or data.get("provider", "aws")
        valid_for_provider = _PROVIDER_SERVICES.get(provider, set())
        if comp.service not in valid_for_provider:
            # Try equivalence mapping to correct provider
            equivalent = get_equivalent(comp.service, _infer_service_provider(comp.service), provider)
            if equivalent:
                log.warning(
                    "Provider mismatch: service '%s' not valid for %s, mapped to '%s'",
                    comp.service,
                    provider,
                    equivalent,
                )
                comp = comp.model_copy(update={"service": equivalent})
            else:
                log.warning(
                    "Service '%s' not in valid set for provider '%s' — keeping as-is",
                    comp.service,
                    provider,
                )
        validated.append(comp)
    components = validated

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

    metadata = {}
    if "rationale" in data:
        metadata["rationale"] = data["rationale"]
    if "suggestions" in data:
        metadata["suggestions"] = data["suggestions"]

    spec = ArchSpec(
        name=data.get("name", "Architecture"),
        provider=data.get("provider", "aws"),
        region=data.get("region", "us-east-1"),
        constraints=constraints,
        components=components,
        connections=connections,
        metadata=metadata,
    )
    spec = _enforce_connections(spec)
    return _post_validate(spec, constraints)


def _infer_service_provider(service: str) -> str:
    """Infer which provider owns a service key for equivalence lookups."""
    for provider, services in _PROVIDER_SERVICES.items():
        if service in services:
            return provider
    return "aws"


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
