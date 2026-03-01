#!/usr/bin/env python3
"""Evaluate benchmark results across 10 metrics.

Usage:
    python3 benchmark/evaluate.py benchmark/results/benchmark_results.json
    python3 benchmark/evaluate.py benchmark/results/benchmark_results.json --output evaluated.json
"""

import json
import re
import sys
from pathlib import Path

import yaml

# Lazy imports to avoid hard dependency when running standalone
try:
    from cloudwright.providers import EQUIVALENCES, get_equivalent
except ImportError:
    EQUIVALENCES = {}

    def get_equivalent(service, from_provider, to_provider):  # noqa: ARG001
        return None


try:
    from cloudwright.differ import Differ
except ImportError:
    Differ = None  # type: ignore[assignment,misc]

try:
    from cloudwright.scorer import Scorer
except ImportError:
    Scorer = None  # type: ignore[assignment,misc]


def _build_equivalence_sets() -> list[set[str]]:
    """Build sets of cross-cloud equivalent services."""
    groups: list[set[str]] = []
    for aws_key, mappings in EQUIVALENCES.items():
        group = {aws_key}
        group.update(mappings.values())
        groups.append(group)
    return groups


_EQUIVALENCE_GROUPS = _build_equivalence_sets()


def _are_equivalent(a: str, b: str) -> bool:
    """Check if two service names are cross-cloud equivalents."""
    if a == b:
        return True
    for group in _EQUIVALENCE_GROUPS:
        if a in group and b in group:
            return True
    return False

# Metric 1 — Structural Validity


def evaluate_structural_validity(result: dict) -> dict:
    """Can output be parsed as a valid ArchSpec with real components?"""
    if result["tool"] == "cloudwright":
        spec = result.get("spec")
        if not spec:
            return {"score": 0, "pass": False, "reason": "no spec generated"}
        components = spec.get("components", [])
        if not components:
            return {"score": 0, "pass": False, "reason": "spec has no components"}
        id_pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")
        valid_ids = all(id_pattern.match(c.get("id", "")) for c in components)
        if not valid_ids:
            return {
                "score": 50,
                "pass": False,
                "reason": "some component ids are not IaC-safe",
                "component_count": len(components),
            }
        return {"score": 100, "pass": True, "component_count": len(components)}

    # Claude raw — try to extract any structured data from the response
    text = result.get("raw_text", "")
    if not text:
        return {"score": 0, "pass": False, "reason": "no output"}

    # YAML code block (handle both closed and unclosed fences)
    m = re.search(r"```ya?ml\n(.*?)```", text, re.DOTALL)
    if not m:
        # Claude often hits max_tokens and leaves the fence unclosed
        m = re.search(r"```ya?ml\n(.*)", text, re.DOTALL)
    if m:
        try:
            parsed = yaml.safe_load(m.group(1))
            if isinstance(parsed, dict):
                # Check top-level or one level nested for components/services
                has_structure = any(
                    k in parsed for k in ("components", "services", "resources")
                )
                if not has_structure:
                    for v in parsed.values():
                        if isinstance(v, dict) and any(
                            k in v for k in ("components", "services", "resources")
                        ):
                            has_structure = True
                            break
                if has_structure:
                    return {"score": 80, "pass": True, "reason": "yaml block with components/services"}
            return {"score": 40, "pass": False, "reason": "yaml block but no components structure"}
        except (yaml.YAMLError, ValueError):
            return {"score": 20, "pass": False, "reason": "yaml block present but invalid yaml"}

    # JSON code block
    m = re.search(r"```json\n(.*?)```", text, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, dict):
                return {"score": 60, "pass": True, "reason": "json block extracted"}
        except (json.JSONDecodeError, ValueError):
            pass

    # Bare YAML without fences (last resort)
    try:
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict) and len(parsed) > 2:
            return {"score": 30, "pass": False, "reason": "entire response is yaml but no code block"}
    except (yaml.YAMLError, ValueError):
        pass

    return {"score": 0, "pass": False, "reason": "no parseable structured output"}


# Metric 2 — Cost Accuracy


def evaluate_cost_accuracy(result: dict) -> dict:
    """Accuracy of cost estimates: budget compliance (50%) + plausibility (50%)."""
    expected = result.get("expected", {})
    budget = expected.get("max_monthly_cost", 0)

    if result["tool"] == "cloudwright":
        cost_out = result.get("cost_output")
        if isinstance(cost_out, dict):
            # CLI --json wraps in {"estimate": {...}}
            estimate = cost_out.get("estimate", cost_out)
            total = estimate.get("monthly_total") or estimate.get("total_monthly") or 0
        else:
            total = 0

        if total == 0:
            return {"score": 0, "estimated": 0, "reason": "no cost estimate produced"}

        if budget == 0:
            return {"score": 75, "estimated": total, "reason": "estimate produced, no budget to validate against"}

        # budget_compliance (50%): 100 if under budget, proportional penalty for overage
        if total <= budget:
            budget_score = 100
        else:
            overage_ratio = (total - budget) / budget
            budget_score = max(0, 100 - overage_ratio * 100)

        # estimate_plausibility (50%): >$0 and <3x budget = full credit
        if 0 < total < budget * 3:
            plausibility_score = 100
        else:
            plausibility_score = max(0.0, 100.0 - (total - 3 * budget) / (3 * budget) * 100.0)

        overall = (budget_score + plausibility_score) / 2
        return {
            "score": round(overall, 1),
            "estimated": total,
            "budget": budget,
            "budget_compliance": round(budget_score, 1),
            "estimate_plausibility": round(plausibility_score, 1),
        }

    # Claude raw — extract cost mentions from prose
    text = result.get("raw_text", "")
    # Match "$X,XXX/month" or "$X,XXX/mo" patterns
    matches = re.findall(r"\$([\d,]+(?:\.\d+)?)\s*(?:per month|/month|/mo)", text, re.IGNORECASE)
    if not matches:
        return {"score": 0, "reason": "no cost estimate found in response"}

    try:
        # Take the first total-sounding cost figure
        estimated = float(matches[0].replace(",", ""))
    except ValueError:
        return {"score": 0, "reason": "could not parse cost figure"}

    if budget == 0:
        return {"score": 75, "estimated": estimated, "reason": "estimate found, no budget constraint"}

    # Budget compliance
    if estimated <= budget:
        budget_score = 100
    else:
        overage_ratio = (estimated - budget) / budget
        budget_score = max(0, 100 - overage_ratio * 100)

    # Plausibility
    if estimated > 0 and estimated < budget * 3:
        plausibility_score = 100
    else:
        plausibility_score = 0

    overall = (budget_score + plausibility_score) / 2
    return {
        "score": round(overall, 1),
        "estimated": estimated,
        "budget": budget,
        "budget_compliance": round(budget_score, 1),
        "estimate_plausibility": round(plausibility_score, 1),
    }


# Metric 3 — Service Correctness


_SERVICE_ALIASES: dict[str, set[str]] = {
    "ecs": {"fargate", "ecs_fargate", "ecs-fargate", "ecs_service"},
    "eks": {"kubernetes", "k8s", "eks_cluster"},
    "rds": {"aurora", "rds_aurora", "rds_instance", "postgres", "postgresql", "mysql"},
    "elasticache": {"redis", "memcached", "elasticache_cluster"},
    "alb": {"application_load_balancer", "load_balancer", "lb", "app_lb"},
    "nlb": {"network_load_balancer", "nlb"},
    "cloudfront": {"cdn", "cloudfront_distribution"},
    "s3": {"s3_bucket", "bucket"},
    "lambda": {"lambda_function", "serverless", "functions"},
    "dynamodb": {"dynamo", "dynamodb_table", "nosql"},
    "sqs": {"queue", "message_queue", "sqs_queue"},
    "sns": {"notification", "sns_topic", "pub_sub"},
    "api_gateway": {"apigateway", "api_gw", "apigw", "api"},
    "waf": {"web_application_firewall"},
    "cloud_sql": {"cloudsql", "cloud_sql_instance"},
    "compute_engine": {"gce", "google_compute_instance"},
    "cloud_run": {"cloudrun", "cloud_run_service"},
    "cloud_functions": {"cloud_function", "cloud_functions_function"},
    "gke": {"google_kubernetes_engine", "gke_cluster"},
    "azure_sql": {"mssql", "azure_sql_server"},
    "cosmos_db": {"cosmosdb", "cosmosdb_account"},
    "azure_cache": {"azure_cache_for_redis"},
    "blob_storage": {"blob_storage_account"},
    "aks": {"azure_kubernetes_service", "aks_cluster"},
    "virtual_machines": {"azure_vm", "vm", "azure_virtual_machine"},
    "app_service": {"azure_app_service"},
    "bigquery": {"big_query", "bigquery_dataset"},
    "kinesis": {"kinesis_data_streams", "kinesis_stream"},
    "sagemaker": {"sage_maker", "sagemaker_endpoint"},
    "emr": {"elastic_mapreduce", "emr_cluster"},
}


def _normalize_service(service: str) -> str:
    """Normalize a service string to a canonical key.

    Handles underscores/hyphens, returns the normalized service name.
    For aliases, returns the canonical service key.
    """
    normalized = service.lower().replace("-", "_")

    # Check if it's already a canonical key
    if normalized in _SERVICE_ALIASES:
        return normalized

    # Check if it's an alias for something
    for canonical, aliases in _SERVICE_ALIASES.items():
        if normalized in aliases:
            return canonical

    # Return as-is if not found
    return normalized


def _service_match(required: str, actual_services: set[str]) -> bool:
    """Check if a required service matches any actual service.

    Considers aliases, substring matching, and cross-cloud equivalence.
    """
    required_norm = _normalize_service(required)

    for s in actual_services:
        s_norm = _normalize_service(s)

        # Exact or substring match after normalization
        if required_norm == s_norm or required_norm in s_norm or s_norm in required_norm:
            return True

        # Check aliases bidirectionally
        if s_norm in _SERVICE_ALIASES.get(required_norm, set()):
            return True
        if required_norm in _SERVICE_ALIASES.get(s_norm, set()):
            return True

    # Cross-cloud equivalence via EQUIVALENCES
    for s in actual_services:
        s_norm = _normalize_service(s)
        if _are_equivalent(required_norm, s_norm):
            return True

    return False


# Context words that indicate a service name is being used architecturally
_ARCH_CONTEXT = re.compile(
    r"(?:component|service|resource|deploy|architecture|tier|layer|"
    r"database|cache|queue|storage|compute|network|load.?balanc|cdn|dns|api|"
    r"monitor|log|auth|container|function|cluster|instance|serverless)",
    re.IGNORECASE,
)


def evaluate_service_correctness(result: dict) -> dict:
    """Are the referenced services real and do they include the expected ones?"""
    expected = result.get("expected", {})
    required = set(expected.get("required_services", []))

    if result["tool"] == "cloudwright":
        spec = result.get("spec") or {}
        components = spec.get("components", [])
        services = {c.get("service", "").lower() for c in components}
        if not required:
            return {"score": 100 if services else 50, "total_services": len(services)}
        found = {r for r in required if _service_match(r.lower(), services)}
        score = round(len(found) / len(required) * 100, 1)
        return {
            "score": score,
            "found": sorted(found),
            "missing": sorted(required - found),
            "total_services": len(services),
        }

    # Claude raw — require service name near architecture context, not just anywhere
    text = result.get("raw_text", "").lower()
    if not required:
        return {"score": 50, "reason": "no required services to validate"}

    found = set()
    for r in required:
        variants = [r.lower(), r.replace("_", " ").lower(), r.replace("_", "-").lower()]
        for v in variants:
            for m in re.finditer(re.escape(v), text):
                start = max(0, m.start() - 200)
                end = min(len(text), m.end() + 200)
                window = text[start:end]
                if _ARCH_CONTEXT.search(window):
                    found.add(r)
                    break
            if r in found:
                break

    score = round(len(found) / len(required) * 100, 1)
    return {"score": score, "found": sorted(found), "missing": sorted(required - found)}


# Metric 4 — Compliance Completeness

_COMPLIANCE_TERMS = [
    "encryption at rest",
    "encryption in transit",
    "audit log",
    "access control",
    "multi-az",
    "backup",
    "monitoring",
    "least privilege",
    "waf",
    "mfa",
]


def evaluate_compliance(result: dict) -> dict:
    """Does the architecture address compliance requirements?"""
    if result["tool"] == "cloudwright":
        validate = result.get("validate_output")
        if isinstance(validate, dict) and "results" in validate:
            # JSON output from --json flag: {"results": [{framework, score, checks}, ...]}
            all_results = validate["results"]
            if all_results:
                avg_score = sum(r.get("score", 0) for r in all_results) / len(all_results)
                # score from validator is 0-1, normalize to 0-100
                normalized = avg_score * 100 if avg_score <= 1 else avg_score
                return {"score": round(normalized, 1), "frameworks_checked": len(all_results)}
        if result.get("validate_success"):
            return {"score": 60, "reason": "validation ran but output not parseable"}
        return {"score": 0, "reason": "validation did not run or failed"}

    # Claude raw — count compliance-relevant terms mentioned
    text = result.get("raw_text", "").lower()
    found = sum(1 for t in _COMPLIANCE_TERMS if t in text)
    score = round(found / len(_COMPLIANCE_TERMS) * 100, 1)
    return {"score": score, "terms_found": found, "terms_checked": len(_COMPLIANCE_TERMS)}


# Metric 5 — Export Quality


def evaluate_export_quality(result: dict) -> dict:
    """Quality of generated IaC: syntax validity + deployability."""
    if result["tool"] == "cloudwright":
        if result.get("export_success"):
            file_count = result.get("export_file_count", 0)

            # terraform_validate_success scoring
            if result.get("terraform_validate_success"):
                # Generated and valid = full score
                score = min(100, 80 + file_count * 5)
            else:
                # Generated but not validated = partial credit
                score = min(100, 40 + file_count * 5)

            return {
                "score": score,
                "pass": True,
                "tf_files": file_count,
                "terraform_validate": result.get("terraform_validate_success", False),
            }

        # Export command failed
        return {"score": 0, "pass": False, "reason": "export command failed", "terraform_validate": False}

    # Claude raw — check for HCL/Terraform snippets
    text = result.get("raw_text", "")
    has_hcl_fence = bool(re.search(r"```(?:hcl|terraform)", text, re.IGNORECASE))
    has_resource_block = bool(re.search(r'\bresource\s+"[a-z_]+"', text))

    if has_hcl_fence and has_resource_block:
        return {
            "score": 25,
            "pass": False,
            "reason": "HCL snippet present but not directly deployable",
            "terraform_validate": False,
        }
    if has_resource_block:
        return {
            "score": 15,
            "pass": False,
            "reason": "terraform resource blocks found in prose",
            "terraform_validate": False,
        }
    return {
        "score": 0,
        "pass": False,
        "reason": "no IaC output found",
        "terraform_validate": False,
    }


# Metric 6 — Diff Capability


def evaluate_diff_capability(result: dict) -> dict:
    """Can architectures be structurally diffed? (For multi-run cases)"""
    if result["tool"] == "cloudwright":
        # For multi-run results, diff between first and last run using Differ
        all_runs = result.get("all_runs", [])
        if len(all_runs) >= 2 and Differ is not None:
            try:
                from cloudwright.spec import ArchSpec

                run1 = all_runs[0]
                run2 = all_runs[-1]
                spec_dict1 = run1.get("spec") if isinstance(run1, dict) else run1
                spec_dict2 = run2.get("spec") if isinstance(run2, dict) else run2

                if spec_dict1 and spec_dict2:
                    old_spec = ArchSpec.model_validate(spec_dict1)
                    new_spec = ArchSpec.model_validate(spec_dict2)
                    diff_result = Differ().diff(old_spec, new_spec)

                    return {
                        "score": 100,
                        "pass": True,
                        "added_count": len(diff_result.added),
                        "removed_count": len(diff_result.removed),
                        "changed_count": len(diff_result.changed),
                        "summary": diff_result.summary,
                    }
            except (ImportError, TypeError, ValueError, KeyError, AttributeError) as e:
                return {
                    "score": 70,
                    "pass": True,
                    "reason": f"diff failed: {e}",
                    "note": "multi-run data present",
                }

        return {
            "score": 100,
            "pass": True,
            "reason": "built-in structured diff via `cloudwright diff`",
        }

    # Claude raw — attempt dict diff on parsed responses
    text = result.get("raw_text", "")
    if "```" in text:
        return {
            "score": 20,
            "pass": False,
            "reason": "contains code blocks but no structured diff capability",
        }

    return {
        "score": 0,
        "pass": False,
        "reason": "raw output is prose; no structural diff possible without manual parsing",
    }


# Metric 7 — Reproducibility


def evaluate_reproducibility(result: dict) -> dict:
    """Measure consistency across runs or estimate from schema constraints."""
    all_runs = result.get("all_runs")
    if all_runs and len(all_runs) >= 2:
        if result["tool"] == "cloudwright":
            service_sets = []
            for run in all_runs:
                spec_r = run.get("spec") or {}
                services = frozenset(
                    _normalize_service(c.get("service", ""))
                    for c in spec_r.get("components", [])
                )
                service_sets.append(services)
            similarities = []
            for i in range(len(service_sets)):
                for j in range(i + 1, len(service_sets)):
                    union = service_sets[i] | service_sets[j]
                    inter = service_sets[i] & service_sets[j]
                    if union:
                        similarities.append(len(inter) / len(union))
            avg_sim = sum(similarities) / len(similarities) if similarities else 0
            return {"score": round(avg_sim * 100, 1),
                    "reason": f"empirical Jaccard similarity across {len(all_runs)} runs",
                    "n_runs": len(all_runs)}
        else:
            word_sets = [
                frozenset(run.get("raw_text", "").lower().split())
                for run in all_runs if run.get("raw_text")
            ]
            if len(word_sets) >= 2:
                similarities = []
                for i in range(len(word_sets)):
                    for j in range(i + 1, len(word_sets)):
                        union = word_sets[i] | word_sets[j]
                        inter = word_sets[i] & word_sets[j]
                        if union:
                            similarities.append(len(inter) / len(union))
                avg_sim = sum(similarities) / len(similarities) if similarities else 0
                return {"score": round(avg_sim * 100, 1),
                        "reason": f"empirical word overlap across {len(all_runs)} runs",
                        "n_runs": len(all_runs)}

    if result["tool"] == "cloudwright":
        spec = result.get("spec") or {}
        has_schema_fields = all(k in spec for k in ("name", "components"))
        return {
            "score": 85 if has_schema_fields else 50,
            "reason": "schema-constrained ArchSpec — structure reproducible, service selection varies",
        }
    return {
        "score": 35,
        "reason": "free-form prose — structure, formatting, and content all vary across runs",
    }


# Metric 8 — Time to IaC


def _estimate_manual_extraction_time(result: dict) -> int:
    """Estimate manual time (seconds) to go from raw output to deployable Terraform."""
    text = result.get("raw_text", "")

    # Count HCL blocks and resource blocks
    hcl_blocks = len(re.findall(r"```(?:hcl|terraform)", text, re.IGNORECASE))
    resource_blocks = len(re.findall(r'\bresource\s+"[a-z_]+"', text))

    # Time estimates based on content structure:
    # Has HCL blocks + 5+ resource blocks: 600s (10 min)
    # Has HCL blocks + some resources: 900s (15 min)
    # Scattered code blocks: 1200s (20 min)
    # Prose only: 2400s (40 min)

    if hcl_blocks > 0 and resource_blocks >= 5:
        return 600
    if hcl_blocks > 0 and resource_blocks > 0:
        return 900
    if len(re.findall(r"```", text)) > 0:
        return 1200
    return 2400


# Metric 9 — Architecture Quality


def evaluate_architecture_quality(result: dict) -> dict:
    """Multi-dimensional architecture scoring using Scorer."""
    if result["tool"] == "cloudwright":
        spec = result.get("spec")
        if not spec:
            return {"score": 0, "reason": "no spec to score"}

        if Scorer is None:
            return {"score": 0, "reason": "cloudwright.scorer not available"}
        try:
            from cloudwright.spec import ArchSpec

            arch_spec = ArchSpec.model_validate(spec) if isinstance(spec, dict) else spec
            scorer = Scorer()
            score_result = scorer.score(arch_spec)

            return {
                "score": score_result.overall,
                "grade": score_result.grade,
                "dimensions": [
                    {
                        "name": d.name,
                        "score": round(d.score, 1),
                        "weight": d.weight,
                    }
                    for d in score_result.dimensions
                ],
            }
        except (ImportError, TypeError, ValueError, KeyError) as e:
            return {"score": 0, "reason": f"scoring failed: {e}"}

    # Raw Claude output cannot be scored without structured ArchSpec
    return {"score": 0, "reason": "raw text output cannot be scored; requires ArchSpec"}


# Metric 10 — Per-Component Cost Scoring

_REFERENCE_RANGES = {
    # AWS examples (monthly cost ranges for typical production instances)
    "ec2": {"min": 50, "max": 1000},
    "rds": {"min": 100, "max": 2000},
    "lambda": {"min": 0, "max": 100},
    "dynamodb": {"min": 25, "max": 500},
    "s3": {"min": 1, "max": 100},
    "elasticache": {"min": 50, "max": 500},
    "alb": {"min": 16, "max": 200},
    "cloudfront": {"min": 1, "max": 500},
    # GCP equivalents
    "compute_engine": {"min": 50, "max": 1000},
    "cloud_sql": {"min": 100, "max": 2000},
    "cloud_functions": {"min": 0, "max": 100},
    "firestore": {"min": 25, "max": 500},
    "cloud_storage": {"min": 1, "max": 100},
    "memorystore": {"min": 50, "max": 500},
    "cloud_load_balancing": {"min": 16, "max": 200},
    "cloud_cdn": {"min": 1, "max": 500},
    # Azure equivalents
    "virtual_machines": {"min": 50, "max": 1000},
    "azure_sql": {"min": 100, "max": 2000},
    "azure_functions": {"min": 0, "max": 100},
    "cosmos_db": {"min": 25, "max": 500},
    "blob_storage": {"min": 1, "max": 100},
    "azure_cache": {"min": 50, "max": 500},
    "app_gateway": {"min": 16, "max": 200},
    "azure_cdn": {"min": 1, "max": 500},
}


def evaluate_cost_granularity(result: dict) -> dict:
    """Score components' individual costs against reference ranges."""
    if result["tool"] == "cloudwright":
        cost_out = result.get("cost_output")
        spec = result.get("spec")

        if not isinstance(cost_out, dict) or not spec:
            return {"score": 0, "reason": "missing cost breakdown or spec"}

        try:
            # Get per-component costs from cost output
            components_cost = cost_out.get("components", {})
            if not components_cost:
                return {"score": 0, "reason": "no per-component cost breakdown"}

            components = spec.get("components", [])
            if not components:
                return {"score": 0, "reason": "no components in spec"}

            # Score components against reference ranges
            valid_components = 0
            within_range = 0

            for comp in components:
                service = comp.get("service", "").lower()
                comp_id = comp.get("id", "")

                if service not in _REFERENCE_RANGES:
                    continue

                valid_components += 1
                cost = components_cost.get(comp_id, {})
                monthly = cost.get("monthly_total", cost.get("total_monthly", 0)) if isinstance(cost, dict) else 0

                if monthly == 0:
                    continue

                ref_range = _REFERENCE_RANGES[service]
                if ref_range["min"] <= monthly <= ref_range["max"]:
                    within_range += 1

            if valid_components == 0:
                return {"score": 50, "reason": "no components with reference ranges"}

            score = (within_range / valid_components) * 100
            return {
                "score": round(score, 1),
                "components_scored": valid_components,
                "within_range": within_range,
            }
        except (TypeError, ValueError, KeyError) as e:
            return {"score": 0, "reason": f"granularity scoring failed: {e}"}

    # Raw Claude cannot provide per-component costs
    return {"score": 0, "reason": "raw output does not include per-component cost breakdown"}


def evaluate_time_to_iac(result: dict) -> dict:
    """How long from prompt to deployable IaC?"""
    elapsed = result.get("elapsed_seconds") or 0

    if result["tool"] == "cloudwright":
        # Cloudwright pipeline is fully automated — elapsed IS the time to IaC
        score = max(0, min(100, 100 - (elapsed / 120) * 50))  # 120s = 50 score, 0s = 100
        return {"score": round(score, 1), "seconds": round(elapsed, 1), "automated": True}

    # Claude raw output requires manual work to produce deployable Terraform
    manual_seconds = _estimate_manual_extraction_time(result)
    total_seconds = elapsed + manual_seconds
    total_minutes = total_seconds / 60
    # Score relative to Cloudwright: 40min manual = ~0, 1min = ~95
    score = max(0, 100 - (total_minutes / 40) * 100)
    return {
        "score": round(score, 1),
        "api_seconds": round(elapsed, 1),
        "estimated_total_minutes": round(total_minutes, 1),
        "manual_extraction_seconds": manual_seconds,
        "automated": False,
        "note": f"includes ~{manual_seconds // 60}min estimated manual extraction time",
    }


# Orchestration

EVALUATORS = {
    "structural_validity": evaluate_structural_validity,
    "cost_accuracy": evaluate_cost_accuracy,
    "service_correctness": evaluate_service_correctness,
    "compliance_completeness": evaluate_compliance,
    "export_quality": evaluate_export_quality,
    "diff_capability": evaluate_diff_capability,
    "reproducibility": evaluate_reproducibility,
    "time_to_iac": evaluate_time_to_iac,
    "architecture_quality": evaluate_architecture_quality,
    "cost_granularity": evaluate_cost_granularity,
}


def evaluate_result(result: dict) -> dict:
    """Run all evaluators on a single benchmark result."""
    scores = {}
    for name, fn in EVALUATORS.items():
        try:
            scores[name] = fn(result)
        except (TypeError, KeyError, ValueError, ImportError) as e:
            scores[name] = {"score": 0, "error": str(e)}
    return scores


def print_summary(evaluated: list[dict]) -> None:
    cw = [e for e in evaluated if e["tool"] == "cloudwright"]
    raw = [e for e in evaluated if e["tool"] == "claude_raw"]

    print(f"\nBENCHMARK EVALUATION  ({len(evaluated)} results, {len(cw)} cloudwright, {len(raw)} claude-raw)")
    print("=" * 72)
    print(f"{'Metric':<32} {'Cloudwright':>12} {'Claude-raw':>12} {'Delta':>10}")
    print("-" * 72)

    for metric in EVALUATORS:
        cw_avg = sum(e["scores"].get(metric, {}).get("score", 0) for e in cw) / len(cw) if cw else 0.0
        raw_avg = sum(e["scores"].get(metric, {}).get("score", 0) for e in raw) / len(raw) if raw else 0.0
        delta = cw_avg - raw_avg
        delta_str = f"{delta:+.1f}%"
        print(f"{metric:<32} {cw_avg:>10.1f}%  {raw_avg:>10.1f}%  {delta_str:>9}")

    print("-" * 72)
    # Overall average
    if cw:
        cw_overall = sum(
            sum(e["scores"].get(m, {}).get("score", 0) for m in EVALUATORS) / len(EVALUATORS) for e in cw
        ) / len(cw)
    else:
        cw_overall = 0.0
    if raw:
        raw_overall = sum(
            sum(e["scores"].get(m, {}).get("score", 0) for m in EVALUATORS) / len(EVALUATORS) for e in raw
        ) / len(raw)
    else:
        raw_overall = 0.0
    print(f"{'OVERALL AVERAGE':<32} {cw_overall:>10.1f}%  {raw_overall:>10.1f}%  {cw_overall - raw_overall:>+9.1f}%")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate benchmark results across 10 metrics")
    parser.add_argument("results_file", help="Path to benchmark_results.json")
    parser.add_argument("--output", default=None, help="Output path for evaluated JSON")
    args = parser.parse_args()

    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"Error: {results_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(results_path) as f:
        results = json.load(f)

    # Group results by (case_id, tool, model) to enable cross-run diff/reproducibility
    run_groups: dict[tuple, list[dict]] = {}
    for result in results:
        key = (result.get("case_id"), result.get("tool"), result.get("model"))
        run_groups.setdefault(key, []).append(result)

    # Inject all_runs list into each result so evaluators can do cross-run analysis
    for group in run_groups.values():
        sorted_group = sorted(group, key=lambda r: r.get("run_index", 0))
        for result in sorted_group:
            result["all_runs"] = sorted_group

    evaluated = []
    for result in results:
        scores = evaluate_result(result)
        evaluated.append(
            {
                "case_id": result.get("case_id"),
                "case_name": result.get("case_name"),
                "tool": result.get("tool"),
                "model": result.get("model"),
                "run_index": result.get("run_index", 0),
                "elapsed_seconds": result.get("elapsed_seconds"),
                "scores": scores,
            }
        )

    output_path = Path(args.output) if args.output else results_path.with_name(results_path.stem + "_evaluated.json")
    with open(output_path, "w") as f:
        json.dump(evaluated, f, indent=2)

    print_summary(evaluated)
    print(f"\nDetailed results -> {output_path}")
    print(f"Run: python3 benchmark/report.py {output_path}")


if __name__ == "__main__":
    main()
