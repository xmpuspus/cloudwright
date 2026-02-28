#!/usr/bin/env python3
"""Evaluate benchmark results across 8 metrics.

Usage:
    python3 benchmark/evaluate.py benchmark/results/benchmark_results.json
    python3 benchmark/evaluate.py benchmark/results/benchmark_results.json --output evaluated.json
"""

import json
import re
import sys
from pathlib import Path

import yaml

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
        except Exception:
            return {"score": 20, "pass": False, "reason": "yaml block present but invalid yaml"}

    # JSON code block
    m = re.search(r"```json\n(.*?)```", text, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, dict):
                return {"score": 60, "pass": True, "reason": "json block extracted"}
        except Exception:
            pass

    # Bare YAML without fences (last resort)
    try:
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict) and len(parsed) > 2:
            return {"score": 30, "pass": False, "reason": "entire response is yaml but no code block"}
    except Exception:
        pass

    return {"score": 0, "pass": False, "reason": "no parseable structured output"}


# Metric 2 — Cost Accuracy


def evaluate_cost_accuracy(result: dict) -> dict:
    """How close is the cost estimate to the stated budget constraint?"""
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
            # No budget to compare against — give partial credit for producing any estimate
            return {"score": 50, "estimated": total, "reason": "estimate produced, no budget to validate against"}

        # Penalize both over- and under-estimation equally
        score = max(0, 100 - abs(total - budget) / budget * 100)
        return {"score": round(score, 1), "estimated": total, "budget": budget}

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
        return {"score": 50, "estimated": estimated, "reason": "estimate found, no budget constraint"}

    deviation = abs(estimated - budget) / budget
    score = max(0, 100 - deviation * 100)
    return {"score": round(score, 1), "estimated": estimated, "budget": budget}


# Metric 3 — Service Correctness


_SERVICE_ALIASES: dict[str, set[str]] = {
    "ecs": {"fargate", "ecs_fargate", "ecs-fargate"},
    "eks": {"kubernetes", "k8s"},
    "rds": {"aurora", "rds_aurora", "postgres", "postgresql", "mysql"},
    "elasticache": {"redis", "memcached"},
    "alb": {"application_load_balancer", "load_balancer", "lb"},
    "nlb": {"network_load_balancer"},
    "cloudfront": {"cdn"},
    "s3": {"s3_bucket"},
    "lambda": {"lambda_function"},
    "dynamodb": {"dynamo"},
    "sqs": {"queue", "message_queue"},
    "sns": {"notification"},
    "api_gateway": {"apigateway", "api_gw", "apigw"},
    "waf": {"web_application_firewall"},
    "cloud_sql": {"cloudsql"},
    "compute_engine": {"gce"},
}


def _service_match(required: str, actual_services: set[str]) -> bool:
    """Check if a required service name matches any actual service, considering aliases."""
    for s in actual_services:
        if required in s or s in required:
            return True
    aliases = _SERVICE_ALIASES.get(required, set())
    for s in actual_services:
        if s in aliases or any(a in s for a in aliases):
            return True
    return False


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

    # Claude raw — check if required service names appear in the response text
    text = result.get("raw_text", "").lower()
    if not required:
        return {"score": 50, "reason": "no required services to validate"}
    found = {r for r in required if r.replace("_", " ") in text or r.replace("_", "-") in text or r in text}
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
    """Does the output include deployable IaC?"""
    if result["tool"] == "cloudwright":
        if result.get("export_success"):
            file_count = result.get("export_file_count", 0)
            # More .tf files = richer export
            score = min(100, 60 + file_count * 10)
            return {"score": score, "pass": True, "tf_files": file_count}
        return {"score": 0, "pass": False, "reason": "export command failed"}

    # Claude raw — check for HCL/Terraform snippets in the response
    text = result.get("raw_text", "")
    has_hcl_fence = bool(re.search(r"```(?:hcl|terraform)", text, re.IGNORECASE))
    has_resource_block = bool(re.search(r'\bresource\s+"[a-z_]+"', text))

    if has_hcl_fence and has_resource_block:
        return {"score": 25, "pass": False, "reason": "HCL snippet present but not directly deployable"}
    if has_resource_block:
        return {"score": 15, "pass": False, "reason": "terraform resource blocks found in prose"}
    return {"score": 0, "pass": False, "reason": "no IaC output found"}


# Metric 6 — Diff Capability


def evaluate_diff_capability(result: dict) -> dict:
    """Can architectures be structurally diffed?"""
    if result["tool"] == "cloudwright":
        return {
            "score": 100,
            "pass": True,
            "reason": "built-in structured diff via `cloudwright diff`",
        }
    return {
        "score": 0,
        "pass": False,
        "reason": "raw output is prose; no structural diff possible without manual parsing",
    }


# Metric 7 — Reproducibility


def evaluate_reproducibility(result: dict) -> dict:
    """Estimate consistency potential (multi-run comparison not available in single run)."""
    if result["tool"] == "cloudwright":
        # Schema-constrained output means structure is consistent even when services vary
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

# Estimated manual time (seconds) to go from Claude raw output to deployable Terraform:
# extract code -> fix imports -> add provider block -> fix resource references -> terraform init
_MANUAL_EXTRACTION_SECONDS = 1800  # 30 minutes (conservative; practitioners report 30-90 min)


def evaluate_time_to_iac(result: dict) -> dict:
    """How long from prompt to deployable IaC?"""
    elapsed = result.get("elapsed_seconds") or 0

    if result["tool"] == "cloudwright":
        # Cloudwright pipeline is fully automated — elapsed IS the time to IaC
        score = max(0, min(100, 100 - (elapsed / 120) * 50))  # 120s = 50 score, 0s = 100
        return {"score": round(score, 1), "seconds": round(elapsed, 1), "automated": True}

    # Claude raw output requires manual work to produce deployable Terraform
    total_seconds = elapsed + _MANUAL_EXTRACTION_SECONDS
    total_minutes = total_seconds / 60
    # Score relative to Cloudwright: 30min manual = ~0, 1min = ~95
    score = max(0, 100 - (total_minutes / 30) * 100)
    return {
        "score": round(score, 1),
        "api_seconds": round(elapsed, 1),
        "estimated_total_minutes": round(total_minutes, 1),
        "automated": False,
        "note": f"includes ~{_MANUAL_EXTRACTION_SECONDS // 60}min estimated manual extraction time",
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
}


def evaluate_result(result: dict) -> dict:
    """Run all 8 evaluators on a single benchmark result."""
    scores = {}
    for name, fn in EVALUATORS.items():
        try:
            scores[name] = fn(result)
        except Exception as e:
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

    parser = argparse.ArgumentParser(description="Evaluate benchmark results across 8 metrics")
    parser.add_argument("results_file", help="Path to benchmark_results.json")
    parser.add_argument("--output", default=None, help="Output path for evaluated JSON")
    args = parser.parse_args()

    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"Error: {results_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(results_path) as f:
        results = json.load(f)

    evaluated = []
    for result in results:
        scores = evaluate_result(result)
        evaluated.append(
            {
                "case_id": result.get("case_id"),
                "case_name": result.get("case_name"),
                "tool": result.get("tool"),
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
