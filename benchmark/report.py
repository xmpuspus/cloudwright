#!/usr/bin/env python3
"""Generate a markdown benchmark report from evaluated results.

Usage:
    python3 benchmark/report.py benchmark/results/benchmark_results_evaluated.json
    python3 benchmark/report.py benchmark/results/benchmark_results_evaluated.json --output report.md
"""

import json
import sys
from datetime import date
from pathlib import Path

METRICS = [
    "structural_validity",
    "cost_accuracy",
    "service_correctness",
    "compliance_completeness",
    "export_quality",
    "diff_capability",
    "reproducibility",
    "time_to_iac",
]

METRIC_LABELS = {
    "structural_validity": "Structural Validity",
    "cost_accuracy": "Cost Accuracy",
    "service_correctness": "Service Correctness",
    "compliance_completeness": "Compliance Completeness",
    "export_quality": "Export Quality (IaC)",
    "diff_capability": "Diff Capability",
    "reproducibility": "Reproducibility",
    "time_to_iac": "Time to IaC",
}

CATEGORY_ORDER = [
    "greenfield",
    "compliance",
    "cost",
    "import",
    "microservices",
    "data",
    "industry",
    "migration",
    "edge",
    "comparison",
]


def avg_score(entries: list[dict], metric: str) -> float:
    if not entries:
        return 0.0
    return sum(e["scores"].get(metric, {}).get("score", 0) for e in entries) / len(entries)


def overall_avg(entries: list[dict]) -> float:
    if not entries:
        return 0.0
    return sum(avg_score(entries, m) for m in METRICS) / len(METRICS)


def wins(cw_entries: list[dict], raw_entries: list[dict]) -> int:
    """Number of metrics where Cloudwright outscores Claude raw."""
    count = 0
    for m in METRICS:
        if avg_score(cw_entries, m) > avg_score(raw_entries, m):
            count += 1
    return count


def format_score(s: float) -> str:
    return f"{s:.1f}%"


def format_delta(delta: float) -> str:
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}%"


def build_report(evaluated: list[dict]) -> str:
    cw_all = [e for e in evaluated if e["tool"] == "cloudwright"]
    raw_all = [e for e in evaluated if e["tool"] == "claude_raw"]

    n_cases = max(len(cw_all), len(raw_all))
    run_date = date.today().isoformat()

    lines = []
    lines.append("# Cloudwright Benchmark Report")
    lines.append("")
    lines.append(f"**Date:** {run_date}  ")
    lines.append(f"**Use cases:** {n_cases}  ")
    lines.append(f"**Cloudwright wins:** {wins(cw_all, raw_all)}/8 metrics  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Cloudwright | Claude-raw | Delta |")
    lines.append("|--------|------------|-----------|-------|")
    for m in METRICS:
        cw_s = avg_score(cw_all, m)
        raw_s = avg_score(raw_all, m)
        delta = cw_s - raw_s
        winner = " [W]" if cw_s > raw_s else ("" if cw_s == raw_s else " [L]")
        lines.append(
            f"| {METRIC_LABELS[m]} | {format_score(cw_s)}{winner} | {format_score(raw_s)} | {format_delta(delta)} |"
        )
    lines.append(
        f"| **Overall** | **{format_score(overall_avg(cw_all))}** | **{format_score(overall_avg(raw_all))}** | **{format_delta(overall_avg(cw_all) - overall_avg(raw_all))}** |"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-category breakdown
    lines.append("## Results by Category")
    lines.append("")

    # Group by case_id prefix mapping to category — infer from case_id ranges
    def infer_category(case_id: str) -> str:
        try:
            n = int(case_id)
        except (ValueError, TypeError):
            return "unknown"
        if 1 <= n <= 5:
            return "greenfield"
        if 6 <= n <= 10:
            return "compliance"
        if 11 <= n <= 15:
            return "cost"
        if 16 <= n <= 20:
            return "import"
        if 21 <= n <= 25:
            return "microservices"
        if 26 <= n <= 30:
            return "data"
        if 31 <= n <= 35:
            return "industry"
        if 36 <= n <= 40:
            return "migration"
        if 41 <= n <= 45:
            return "edge"
        if 46 <= n <= 50:
            return "comparison"
        return "unknown"

    categories: dict[str, dict[str, list[dict]]] = {}
    for e in evaluated:
        cat = infer_category(e.get("case_id", ""))
        if cat not in categories:
            categories[cat] = {"cloudwright": [], "claude_raw": []}
        categories[cat][e["tool"]].append(e)

    for cat in CATEGORY_ORDER:
        if cat not in categories:
            continue
        cw_cat = categories[cat]["cloudwright"]
        raw_cat = categories[cat]["claude_raw"]
        n = max(len(cw_cat), len(raw_cat))
        if n == 0:
            continue

        lines.append(f"### {cat.replace('_', ' ').title()} ({n} cases)")
        lines.append("")
        lines.append("| Metric | Cloudwright | Claude-raw | Delta |")
        lines.append("|--------|------------|-----------|-------|")
        for m in METRICS:
            cw_s = avg_score(cw_cat, m)
            raw_s = avg_score(raw_cat, m)
            delta = cw_s - raw_s
            lines.append(
                f"| {METRIC_LABELS[m]} | {format_score(cw_s)} | {format_score(raw_s)} | {format_delta(delta)} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")

    # Failure analysis — cases where Cloudwright underperformed
    lines.append("## Failure Analysis")
    lines.append("")
    lines.append("Cases where Cloudwright scored lower than Claude-raw on any metric:")
    lines.append("")

    failures = []
    # Pair up results by case_id
    cw_by_id = {e["case_id"]: e for e in cw_all}
    raw_by_id = {e["case_id"]: e for e in raw_all}
    all_ids = sorted(set(cw_by_id) | set(raw_by_id))

    for case_id in all_ids:
        cw_e = cw_by_id.get(case_id)
        raw_e = raw_by_id.get(case_id)
        if not (cw_e and raw_e):
            continue
        for m in METRICS:
            cw_s = cw_e["scores"].get(m, {}).get("score", 0)
            raw_s = raw_e["scores"].get(m, {}).get("score", 0)
            if raw_s > cw_s + 5:  # 5-point tolerance for noise
                failures.append(
                    {
                        "case_id": case_id,
                        "case_name": cw_e.get("case_name", ""),
                        "metric": m,
                        "cloudwright": cw_s,
                        "claude_raw": raw_s,
                        "gap": raw_s - cw_s,
                    }
                )

    if failures:
        failures.sort(key=lambda x: -x["gap"])
        lines.append("| Case | Metric | Cloudwright | Claude-raw | Gap |")
        lines.append("|------|--------|------------|-----------|-----|")
        for f in failures[:20]:  # cap at 20 to keep report readable
            lines.append(
                f"| [{f['case_id']}] {f['case_name'][:35]} "
                f"| {METRIC_LABELS.get(f['metric'], f['metric'])} "
                f"| {format_score(f['cloudwright'])} "
                f"| {format_score(f['claude_raw'])} "
                f"| {format_delta(-f['gap'])} |"
            )
    else:
        lines.append("No significant failures — Cloudwright outperformed on all metrics.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("- **Cloudwright pipeline:** design -> cost -> validate -> export (Terraform)")
    lines.append(f"- **Claude raw:** same prompt, generic system prompt, `{date.today().year}` Claude Sonnet model")
    lines.append("- **Cost accuracy:** deviation from stated budget constraint")
    lines.append("- **Reproducibility:** estimated from schema constraints (multi-run data not collected)")
    lines.append(
        "- **Time to IaC:** Cloudwright = automated elapsed time; Claude raw = API time + 30min manual extraction estimate"
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate benchmark markdown report")
    parser.add_argument("evaluated_file", help="Path to *_evaluated.json from evaluate.py")
    parser.add_argument("--output", default=None, help="Output path for markdown report")
    args = parser.parse_args()

    evaluated_path = Path(args.evaluated_file)
    if not evaluated_path.exists():
        print(f"Error: {evaluated_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(evaluated_path) as f:
        evaluated = json.load(f)

    report = build_report(evaluated)

    if args.output:
        out = Path(args.output)
    else:
        out = evaluated_path.parent / "benchmark_report.md"

    out.write_text(report)
    print(f"Report written to {out}")

    # Also print summary to stdout
    cw = [e for e in evaluated if e["tool"] == "cloudwright"]
    raw = [e for e in evaluated if e["tool"] == "claude_raw"]
    print(f"\nCloudwright overall: {overall_avg(cw):.1f}%")
    print(f"Claude-raw overall:  {overall_avg(raw):.1f}%")
    print(f"Cloudwright wins:    {wins(cw, raw)}/8 metrics")


if __name__ == "__main__":
    main()
