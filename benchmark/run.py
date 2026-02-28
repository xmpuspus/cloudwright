#!/usr/bin/env python3
"""Cloudwright Benchmark Runner — Cloudwright vs raw Claude API.

Usage:
    python3 benchmark/run.py --dry-run
    python3 benchmark/run.py --tool cloudwright --cases 01 02 03
    python3 benchmark/run.py --tool both
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

BENCHMARK_DIR = Path(__file__).parent
USE_CASES_DIR = BENCHMARK_DIR / "use_cases"
RESULTS_DIR = BENCHMARK_DIR / "results"

# Model to use for raw Claude comparison
CLAUDE_MODEL = "claude-sonnet-4-6"


def discover_use_cases() -> list[dict]:
    """Find all use case YAML files, sorted by id."""
    cases = []
    for yaml_file in sorted(USE_CASES_DIR.rglob("*.yaml")):
        with open(yaml_file) as f:
            case = yaml.safe_load(f)
            case["_file"] = str(yaml_file)
            cases.append(case)
    # Sort by id so tier1/01 < tier1/06 < tier2/21 etc.
    cases.sort(key=lambda c: c.get("id", "99"))
    return cases


def run_cloudwright(case: dict) -> dict:
    """Run full Cloudwright pipeline on a use case and collect all outputs."""
    import tempfile

    prompt = case["prompt"]
    constraints = case.get("constraints", {})

    start = time.time()
    result = {
        "tool": "cloudwright",
        "case_id": case["id"],
        "case_name": case["name"],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = os.path.join(tmpdir, "spec.yaml")
        tf_dir = os.path.join(tmpdir, "terraform")
        os.makedirs(tf_dir, exist_ok=True)

        # 1. Design
        design_cmd = [
            sys.executable,
            "-m",
            "cloudwright_cli",
            "design",
            prompt,
            "-o",
            spec_path,
        ]
        if constraints.get("provider"):
            design_cmd += ["--provider", constraints["provider"]]
        if constraints.get("budget_monthly"):
            design_cmd += ["--budget", str(constraints["budget_monthly"])]
        if constraints.get("compliance"):
            for c in constraints["compliance"]:
                design_cmd += ["--compliance", c]

        try:
            dr = subprocess.run(design_cmd, capture_output=True, text=True, timeout=120)
            result["design_success"] = dr.returncode == 0
            if dr.stderr:
                result["design_stderr"] = dr.stderr[:500]
        except subprocess.TimeoutExpired:
            result["design_success"] = False
            result["design_error"] = "timeout after 120s"
            result["elapsed_seconds"] = time.time() - start
            return result
        except FileNotFoundError as e:
            result["design_success"] = False
            result["design_error"] = f"command not found: {e}"
            result["elapsed_seconds"] = time.time() - start
            return result

        if not os.path.exists(spec_path):
            result["design_success"] = False
            result["design_error"] = "spec file not created"
            result["elapsed_seconds"] = time.time() - start
            return result

        # Read spec for downstream evaluation
        with open(spec_path) as f:
            result["spec"] = yaml.safe_load(f)

        # 2. Cost
        try:
            cost_cmd = [
                sys.executable,
                "-m",
                "cloudwright_cli",
                "--json",
                "cost",
                spec_path,
            ]
            cr = subprocess.run(cost_cmd, capture_output=True, text=True, timeout=30)
            result["cost_success"] = cr.returncode == 0
            if cr.returncode == 0 and cr.stdout:
                try:
                    result["cost_output"] = json.loads(cr.stdout)
                except json.JSONDecodeError:
                    result["cost_output"] = cr.stdout[:1000]
        except Exception as e:
            result["cost_success"] = False
            result["cost_error"] = str(e)

        # 3. Validate — use compliance from constraints, fall back to well-architected
        try:
            compliance_list = constraints.get("compliance") or []
            validate_cmd = [
                sys.executable,
                "-m",
                "cloudwright_cli",
                "--json",
                "validate",
                spec_path,
            ]
            if compliance_list:
                validate_cmd += ["--compliance", ",".join(compliance_list)]
            else:
                validate_cmd += ["--well-architected"]

            vr = subprocess.run(validate_cmd, capture_output=True, text=True, timeout=30)
            result["validate_success"] = vr.returncode in (0, 1)  # 1 = failed checks, not crash
            if vr.stdout:
                try:
                    result["validate_output"] = json.loads(vr.stdout)
                except json.JSONDecodeError:
                    result["validate_output"] = vr.stdout[:1000]
        except Exception as e:
            result["validate_success"] = False
            result["validate_error"] = str(e)

        # 4. Export to Terraform
        try:
            export_cmd = [
                sys.executable,
                "-m",
                "cloudwright_cli",
                "export",
                spec_path,
                "--format",
                "terraform",
                "-o",
                tf_dir,
            ]
            er = subprocess.run(export_cmd, capture_output=True, text=True, timeout=30)
            result["export_success"] = er.returncode == 0
            # Count generated files as a quality signal
            tf_files = list(Path(tf_dir).glob("*.tf"))
            result["export_file_count"] = len(tf_files)
        except Exception as e:
            result["export_success"] = False
            result["export_error"] = str(e)

    result["elapsed_seconds"] = time.time() - start
    return result


def run_claude_raw(case: dict) -> dict:
    """Run the same prompt through raw Claude API with a generic system prompt."""
    start = time.time()
    result = {
        "tool": "claude_raw",
        "case_id": case["id"],
        "case_name": case["name"],
    }

    try:
        from anthropic import Anthropic

        client = Anthropic()
        system_prompt = (
            "You are a cloud architect. When given a requirement, produce a complete "
            "cloud architecture design. Include: all components with their service types, "
            "connections between components, estimated monthly cost, and if compliance is "
            "mentioned, list which controls are satisfied. Output as YAML if possible."
        )

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": case["prompt"]}],
        )
        text = response.content[0].text
        result["raw_text"] = text
        result["design_success"] = True
        result["token_usage"] = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }
    except ImportError:
        result["design_success"] = False
        result["design_error"] = "anthropic package not installed"
    except Exception as e:
        result["design_success"] = False
        result["design_error"] = str(e)

    result["elapsed_seconds"] = time.time() - start
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Cloudwright Benchmark Runner")
    parser.add_argument(
        "--cases",
        nargs="*",
        metavar="ID",
        help="Specific case IDs to run, e.g. --cases 01 06 21 (default: all)",
    )
    parser.add_argument(
        "--tool",
        choices=["cloudwright", "claude", "both"],
        default="both",
        help="Which tool to benchmark (default: both)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List discovered use cases without running anything",
    )
    parser.add_argument(
        "--output",
        default=str(RESULTS_DIR / "benchmark_results.json"),
        metavar="PATH",
        help="Output file for raw results JSON",
    )
    args = parser.parse_args()

    cases = discover_use_cases()
    if args.cases:
        cases = [c for c in cases if c["id"] in args.cases]

    if not cases:
        print("No matching use cases found.")
        return

    print(f"Discovered {len(cases)} use cases")

    if args.dry_run:
        for c in cases:
            tier_dir = Path(c["_file"]).parent.name
            print(f"  [{c['id']}] {c['name']:<55} ({tier_dir})")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for i, case in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}] {case['name']}")

        if args.tool in ("cloudwright", "both"):
            print("  -> Cloudwright pipeline...", end=" ", flush=True)
            cw = run_cloudwright(case)
            cw["expected"] = case.get("expected", {})
            results.append(cw)
            design_status = "OK" if cw.get("design_success") else "FAIL"
            cost_status = "OK" if cw.get("cost_success") else "FAIL"
            export_status = "OK" if cw.get("export_success") else "FAIL"
            print(
                f"{cw.get('elapsed_seconds', 0):.1f}s  design={design_status} cost={cost_status} export={export_status}"
            )

        if args.tool in ("claude", "both"):
            print("  -> Claude raw API...", end=" ", flush=True)
            raw = run_claude_raw(case)
            raw["expected"] = case.get("expected", {})
            results.append(raw)
            status = "OK" if raw.get("design_success") else "FAIL"
            tokens = raw.get("token_usage", {})
            print(
                f"{raw.get('elapsed_seconds', 0):.1f}s  "
                f"design={status}  "
                f"tokens={tokens.get('input', 0)}in+{tokens.get('output', 0)}out"
            )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nSaved {len(results)} results -> {output_path}")
    print(f"Run: python3 benchmark/evaluate.py {output_path}")


if __name__ == "__main__":
    main()
