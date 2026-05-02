"""Single-shot architecture designer with template matching."""

from __future__ import annotations

import json
import re
import time

from cloudwright.llm import get_llm
from cloudwright.llm.base import BaseLLM
from cloudwright.logging import get_logger
from cloudwright.parsing import _extract_json, _parse_arch_spec
from cloudwright.prompts import (
    COMPARISON_SYSTEM,
    COMPLIANCE_CONTROLS,
    DESIGN_PROJECTION_SYSTEM,
    DESIGN_REASONING_SYSTEM,
    DESIGN_SYSTEM,
    IMPORT_SYSTEM,
    MIGRATION_SYSTEM,
    MODIFY_REASONING_SYSTEM,
    MODIFY_SYSTEM,
)
from cloudwright.providers import get_equivalent
from cloudwright.spec import Alternative, ArchSpec, Component, Constraints

log = get_logger(__name__)

_STOPWORDS = {"a", "an", "the", "on", "in", "for", "with", "and", "or", "to", "my", "our", "that", "this", "using"}


class Architect:
    def __init__(self, llm: BaseLLM | None = None, two_stage: bool = True):
        self.llm = llm or get_llm()
        # Side-channel for the most recent usage dict produced by design()/modify().
        # The web routers read this to surface model/tokens/cost in API responses
        # without a breaking signature change to design().
        self.last_usage: dict = {}
        # When True (default in v1.4) use two-stage prompting: Stage 1 emits free
        # text architectural reasoning (Sonnet), Stage 2 projects to JSON (Haiku).
        # Per ai-llm-eval.md this recovers ~27pp of reasoning quality lost to
        # single-shot JSON-schema constraints. Flip to False to use the legacy
        # single-shot path (kept around for benchmarking and emergency fallback).
        self.two_stage = two_stage

    def design(self, description: str, constraints: Constraints | None = None) -> ArchSpec:
        self.last_usage = {}
        provider = constraints.regions[0].split("-")[0] if constraints and constraints.regions else None
        template_result = _match_template_for_design(description, provider)
        if template_result is not None:
            template, confidence = template_result
            if confidence >= 0.7:
                log.info("Template match (confidence=%.2f) — skipping LLM call", confidence)
                spec = _parse_arch_spec(template, constraints)
                spec = spec.model_copy(
                    update={
                        "metadata": {
                            **spec.metadata,
                            "template_confidence": confidence,
                            "template_name": template.get("name", ""),
                        }
                    }
                )
                if constraints and constraints.regions:
                    spec = spec.model_copy(update={"region": constraints.regions[0]})
                return spec

        if self.two_stage and self._select_system_prompt(description) is DESIGN_SYSTEM:
            spec = self._design_two_stage(description, constraints)
        else:
            spec = self._design_single_shot(description, constraints)

        if template_result is not None:
            _, confidence = template_result
            spec = spec.model_copy(update={"metadata": {**spec.metadata, "template_confidence": confidence}})
        return spec

    def _design_two_stage(self, description: str, constraints: Constraints | None) -> ArchSpec:
        """Two-stage: free-text reasoning -> strict JSON projection."""
        # Stage 1: free-text architectural reasoning (Sonnet, no JSON schema).
        stage1_system = DESIGN_REASONING_SYSTEM
        if constraints:
            stage1_system += _build_constraint_prompt(constraints)
        stage1_messages = [{"role": "user", "content": description}]

        stage1_start = time.perf_counter()
        reasoning, stage1_usage = self.llm.generate(stage1_messages, stage1_system, max_tokens=4000)
        stage1_enriched = self._enrich_usage(stage1_usage, stage1_start)

        # Stage 2: project the reasoning into ArchSpec JSON via Haiku (cheap, strict).
        stage2_messages = [
            {
                "role": "user",
                "content": (
                    f"Original user request:\n{description}\n\n"
                    f"Architect's reasoning:\n{reasoning}\n\n"
                    "Project this into the ArchSpec JSON schema now."
                ),
            }
        ]
        stage2_start = time.perf_counter()
        try:
            text, stage2_usage = self.llm.generate_fast(stage2_messages, DESIGN_PROJECTION_SYSTEM, max_tokens=10000)
            data = _extract_json(text)
        except (ValueError, json.JSONDecodeError) as first_err:
            log.warning("Stage 2 projection failed: %s — retrying with explicit JSON-only nudge", first_err)
            stage2_messages.append({"role": "assistant", "content": "Let me output only JSON."})
            stage2_messages.append(
                {"role": "user", "content": "Output ONLY the JSON object. No prose. Start with {."}
            )
            text, stage2_usage = self.llm.generate_fast(stage2_messages, DESIGN_PROJECTION_SYSTEM, max_tokens=10000)
            data = _extract_json(text)
        stage2_enriched = self._enrich_usage(stage2_usage, stage2_start)

        self.last_usage = self._merge_two_stage_usage(stage1_enriched, stage2_enriched, reasoning)
        return _parse_arch_spec(data, constraints)

    def _design_single_shot(self, description: str, constraints: Constraints | None) -> ArchSpec:
        """Legacy single-shot path. Used for IMPORT/MIGRATION/COMPARE prompts and as fallback."""
        system = self._select_system_prompt(description)
        if constraints:
            system += _build_constraint_prompt(constraints)

        max_tokens = 10000
        messages = [{"role": "user", "content": description}]

        start = time.perf_counter()
        try:
            text, usage = self.llm.generate(messages, system, max_tokens=max_tokens)
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
            text, usage = self.llm.generate(messages, system, max_tokens=max_tokens)
            data = _extract_json(text)

        self.last_usage = self._enrich_usage(usage, start)
        return _parse_arch_spec(data, constraints)

    def _enrich_usage(self, usage: dict, start: float) -> dict:
        if not usage:
            return {}
        enriched = dict(usage)
        model = enriched.get("model") or self.llm.model_name
        enriched.setdefault("model", model)
        pricing_for = getattr(self.llm, "pricing_for", None)
        if callable(pricing_for):
            pricing = pricing_for(model)
            if not (isinstance(pricing, dict) and "input" in pricing and "output" in pricing):
                pricing = self.llm.pricing
        else:
            pricing = self.llm.pricing
        inp = enriched.get("input_tokens", 0) or 0
        out = enriched.get("output_tokens", 0) or 0
        enriched["cost_usd"] = round((inp / 1000) * pricing["input"] + (out / 1000) * pricing["output"], 6)
        enriched["latency_ms"] = round((time.perf_counter() - start) * 1000)
        return enriched

    @staticmethod
    def _merge_two_stage_usage(stage1: dict, stage2: dict, reasoning_text: str) -> dict:
        """Combine stage 1 and stage 2 usage dicts into a single payload.

        The merged dict keeps the headline fields (input_tokens, output_tokens,
        cost_usd, model) for back-compat, plus per-stage breakdown that the web
        layer surfaces in API responses.
        """
        s1_in = stage1.get("input_tokens", 0) or 0
        s1_out = stage1.get("output_tokens", 0) or 0
        s2_in = stage2.get("input_tokens", 0) or 0
        s2_out = stage2.get("output_tokens", 0) or 0
        s1_cost = stage1.get("cost_usd", 0.0) or 0.0
        s2_cost = stage2.get("cost_usd", 0.0) or 0.0
        s1_lat = stage1.get("latency_ms", 0) or 0
        s2_lat = stage2.get("latency_ms", 0) or 0
        merged = {
            "input_tokens": s1_in + s2_in,
            "output_tokens": s1_out + s2_out,
            "cost_usd": round(s1_cost + s2_cost, 6),
            "latency_ms": s1_lat + s2_lat,
            # Headline model = the heavy reasoning model (Sonnet); Stage 2 model is
            # surfaced in the per-stage breakdown.
            "model": stage1.get("model"),
            "two_stage": True,
            "stage1": {
                "model": stage1.get("model"),
                "input_tokens": s1_in,
                "output_tokens": s1_out,
                "cost_usd": s1_cost,
                "latency_ms": s1_lat,
                "reasoning_chars": len(reasoning_text or ""),
            },
            "stage2": {
                "model": stage2.get("model"),
                "input_tokens": s2_in,
                "output_tokens": s2_out,
                "cost_usd": s2_cost,
                "latency_ms": s2_lat,
            },
            "total_cost_usd": round(s1_cost + s2_cost, 6),
            "stage1_tokens": s1_in + s1_out,
            "stage2_tokens": s2_in + s2_out,
        }
        return merged

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
        compare_phrases = {"compare", "versus", "cost comparison"}
        compare_word_patterns = {r"\bvs\b", r"\btco\b"}

        if any(kw in desc_lower for kw in import_keywords):
            return IMPORT_SYSTEM
        if any(kw in desc_lower for kw in migrate_keywords):
            return MIGRATION_SYSTEM
        if any(kw in desc_lower for kw in compare_phrases):
            return COMPARISON_SYSTEM
        if any(re.search(pat, desc_lower) for pat in compare_word_patterns):
            return COMPARISON_SYSTEM
        return DESIGN_SYSTEM

    @staticmethod
    def _is_complex_use_case(description: str) -> bool:
        desc_lower = description.lower()
        complex_keywords = {
            "import",
            "migrate",
            "re-architect",
            "compare",
            "versus",
            "modernize",
            "multi-cloud",
            "multi cloud",
            "hybrid",
            "bridging",
            "cross-cloud",
            "multi-tier",
            "multi tier",
            "6 tier",
            "5 tier",
            "microservice",
        }
        if any(kw in desc_lower for kw in complex_keywords):
            return True
        providers = sum(1 for p in ("aws", "gcp", "azure") if p in desc_lower)
        return providers >= 2

    def modify(self, spec: ArchSpec, instruction: str) -> ArchSpec:
        from cloudwright.session import _slim_for_modify

        self.last_usage = {}
        current = _slim_for_modify(spec)

        # Simple modifications (e.g. "rename db to mydb") still go through the
        # fast single-shot path — two-stage adds latency we don't need for trivial
        # edits. Complex modifications (compliance, migrate, redesign) get the
        # full reasoning + projection pipeline so the LLM can think about
        # boundaries and connection kinds explicitly.
        if self.two_stage and not _is_simple_modification(instruction):
            updated = self._modify_two_stage(spec, current, instruction)
        else:
            updated = self._modify_single_shot(spec, current, instruction)

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

        if spec.cost_estimate and not updated.cost_estimate:
            updated = updated.model_copy(update={"cost_estimate": spec.cost_estimate})
        return updated

    def _modify_single_shot(self, spec: ArchSpec, current: str, instruction: str) -> ArchSpec:
        prompt = f"Current architecture:\n{current}\n\nModification: {instruction}"
        messages = [{"role": "user", "content": prompt}]
        max_tokens = 10000

        if _is_simple_modification(instruction):
            generate = self.llm.generate_fast
        else:
            generate = self.llm.generate

        start = time.perf_counter()
        try:
            text, usage = generate(messages, MODIFY_SYSTEM, max_tokens=max_tokens)
            data = _extract_json(text)
        except (ValueError, json.JSONDecodeError) as first_err:
            log.warning("First modify attempt failed: %s — retrying", first_err)
            messages.append({"role": "assistant", "content": "I apologize, let me provide the JSON."})
            messages.append(
                {
                    "role": "user",
                    "content": "You must respond with ONLY a valid JSON object. No markdown, no explanation.",
                }
            )
            text, usage = self.llm.generate(messages, MODIFY_SYSTEM, max_tokens=max_tokens)
            data = _extract_json(text)
        self.last_usage = self._enrich_usage(usage, start)
        return _parse_arch_spec(data, spec.constraints)

    def _modify_two_stage(self, spec: ArchSpec, current: str, instruction: str) -> ArchSpec:
        # Stage 1: free-text reasoning about the modification.
        stage1_prompt = (
            f"Current architecture (slim JSON):\n{current}\n\n"
            f"Modification request: {instruction}\n\n"
            "Describe the updated architecture in plain bullets — what changed, what stayed, "
            "any boundary or connection-kind implications."
        )
        stage1_messages = [{"role": "user", "content": stage1_prompt}]
        stage1_start = time.perf_counter()
        reasoning, stage1_usage = self.llm.generate(stage1_messages, MODIFY_REASONING_SYSTEM, max_tokens=4000)
        stage1_enriched = self._enrich_usage(stage1_usage, stage1_start)

        # Stage 2: project to JSON.
        stage2_messages = [
            {
                "role": "user",
                "content": (
                    f"Original architecture:\n{current}\n\n"
                    f"Modification request: {instruction}\n\n"
                    f"Architect's reasoning about the update:\n{reasoning}\n\n"
                    "Project the COMPLETE updated architecture into the ArchSpec JSON schema."
                ),
            }
        ]
        stage2_start = time.perf_counter()
        try:
            text, stage2_usage = self.llm.generate_fast(stage2_messages, DESIGN_PROJECTION_SYSTEM, max_tokens=10000)
            data = _extract_json(text)
        except (ValueError, json.JSONDecodeError) as first_err:
            log.warning("Stage 2 modify projection failed: %s — retrying", first_err)
            stage2_messages.append({"role": "assistant", "content": "Let me output only JSON."})
            stage2_messages.append(
                {"role": "user", "content": "Output ONLY the JSON object. No prose. Start with {."}
            )
            text, stage2_usage = self.llm.generate_fast(stage2_messages, DESIGN_PROJECTION_SYSTEM, max_tokens=10000)
            data = _extract_json(text)
        stage2_enriched = self._enrich_usage(stage2_usage, stage2_start)

        self.last_usage = self._merge_two_stage_usage(stage1_enriched, stage2_enriched, reasoning)
        return _parse_arch_spec(data, spec.constraints)

    def compare(self, spec: ArchSpec, providers: list[str]) -> list[Alternative]:
        from cloudwright.cost import CostEngine

        engine = CostEngine()
        return engine.compare_providers(spec, providers)


def _is_simple_modification(instruction: str) -> bool:
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


def _match_template_for_design(description: str, provider: str | None) -> tuple[dict, float] | None:
    from cloudwright.templates import TEMPLATES

    desc_lower = description.lower()
    desc_words = {w for w in re.split(r"\W+", desc_lower) if w not in _STOPWORDS and len(w) > 1}
    if not desc_words:
        return None

    best_match = None
    best_score = 0.0

    for _key, tmpl in TEMPLATES.items():
        keywords: list[str] = tmpl.get("keywords", [])
        if not keywords:
            continue
        if provider and tmpl.get("provider", "").lower() != provider.lower():
            continue
        hits = sum(1 for kw in keywords if kw in desc_lower)
        score = hits / len(keywords) if keywords else 0.0
        if score > best_score:
            best_score = score
            best_match = tmpl

    if best_match is None or best_score < 0.4:
        return None
    return best_match, best_score


def _build_constraint_prompt(constraints: Constraints) -> str:
    sections: list[str] = []

    if constraints.budget_monthly:
        sections.append(
            f"HARD LIMIT: Total monthly cost MUST NOT exceed ${constraints.budget_monthly:.0f}. "
            "If a component would push the total over budget, use a smaller instance type or "
            "remove non-essential components."
        )

    for framework in constraints.compliance:
        key = framework.lower()
        if key in COMPLIANCE_CONTROLS:
            sections.append(f"COMPLIANCE ({framework.upper()}): {COMPLIANCE_CONTROLS[key]}")
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
    return {"aws": "us-east-1", "gcp": "us-central1", "azure": "eastus", "databricks": "us-east-1"}.get(
        provider, "us-east-1"
    )
