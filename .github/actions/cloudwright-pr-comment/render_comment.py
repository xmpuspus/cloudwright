"""Render an idempotent PR comment summarizing arch diff + cost delta + compliance.

Reads JSON output from `cloudwright cost` and `cloudwright validate` (head/base)
plus the YAML specs themselves, and emits a Markdown comment with a magic
marker so the GitHub Action can update-in-place rather than re-create.

Designed to be testable: pure function `render(...)` returns Markdown text and a
delta dict. The CLI wrapper just shells inputs into render() and writes outputs.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MARKER = "<!-- cloudwright-pr-comment -->"


def _load_json(path: str | os.PathLike) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        with p.open() as fh:
            return json.load(fh)
    except json.JSONDecodeError:
        return None


def _unwrap(env: dict[str, Any] | None) -> dict[str, Any]:
    """Cloudwright JSON is wrapped in {"data": {...}}; unwrap if present."""
    if not env:
        return {}
    if isinstance(env, dict) and "data" in env and isinstance(env["data"], dict):
        return env["data"]
    return env


def _load_yaml(path: str | os.PathLike) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        import yaml  # type: ignore
    except ImportError:  # pragma: no cover - yaml ships with cloudwright-ai
        return None
    try:
        with p.open() as fh:
            return yaml.safe_load(fh) or {}
    except yaml.YAMLError:  # type: ignore[attr-defined]
        return None


@dataclass(frozen=True)
class CostSummary:
    monthly_total: float
    breakdown: dict[str, float]  # component_id -> monthly cost


def _summarize_cost(env: dict[str, Any] | None) -> CostSummary | None:
    data = _unwrap(env)
    estimate = data.get("estimate") if isinstance(data, dict) else None
    if not isinstance(estimate, dict):
        return None
    total = float(estimate.get("monthly_total") or 0.0)
    bd_list = estimate.get("breakdown") or []
    bd: dict[str, float] = {}
    for row in bd_list:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("component_id") or row.get("service") or "")
        if cid:
            bd[cid] = float(row.get("monthly") or 0.0)
    return CostSummary(monthly_total=total, breakdown=bd)


def _summarize_components(spec: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    if not isinstance(spec, dict):
        return {}
    components = spec.get("components") or []
    out: dict[str, dict[str, str]] = {}
    for comp in components:
        if not isinstance(comp, dict):
            continue
        cid = str(comp.get("id") or "")
        if not cid:
            continue
        out[cid] = {
            "service": str(comp.get("service") or ""),
            "label": str(comp.get("label") or comp.get("id") or ""),
            "provider": str(comp.get("provider") or ""),
        }
    return out


def _summarize_compliance(env: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Returns {framework -> {passed, failed_checks, score}}."""
    data = _unwrap(env)
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in results:
        if not isinstance(r, dict):
            continue
        fw = str(r.get("framework") or "")
        if not fw:
            continue
        checks = r.get("checks") or []
        failed = [
            str(c.get("name", "?"))
            for c in checks
            if isinstance(c, dict) and not c.get("passed", True)
        ]
        out[fw] = {
            "passed": bool(r.get("passed", False)),
            "score": float(r.get("score") or 0.0),
            "failed_checks": failed,
        }
    return out


def _format_money(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _format_delta(delta: float) -> str:
    if abs(delta) < 0.005:
        return "no change"
    arrow = "+" if delta > 0 else "-"
    return f"{arrow}{_format_money(abs(delta))}/mo"


def render(
    *,
    head_cost: dict[str, Any] | None,
    head_validate: dict[str, Any] | None,
    base_cost: dict[str, Any] | None,
    base_validate: dict[str, Any] | None,
    head_spec: dict[str, Any] | None,
    base_spec: dict[str, Any] | None,
    marker: str = DEFAULT_MARKER,
    compliance: str = "",
    workload_profile: str = "",
    head_path: str = "spec.yaml",
) -> tuple[str, dict[str, Any]]:
    """Render the PR comment and return (markdown, delta_summary)."""
    head_summary = _summarize_cost(head_cost)
    base_summary = _summarize_cost(base_cost)

    head_total = head_summary.monthly_total if head_summary else 0.0
    base_total = base_summary.monthly_total if base_summary else 0.0
    monthly_delta = head_total - base_total

    head_components = _summarize_components(head_spec)
    base_components = _summarize_components(base_spec)
    added_ids = sorted(set(head_components) - set(base_components))
    removed_ids = sorted(set(base_components) - set(head_components))
    changed_ids = sorted(
        cid for cid in set(head_components) & set(base_components)
        if head_components[cid] != base_components[cid]
    )

    head_compliance = _summarize_compliance(head_validate)
    base_compliance = _summarize_compliance(base_validate)

    lines: list[str] = []
    lines.append(marker)
    lines.append("## Cloudwright PR Preview")
    lines.append("")
    lines.append(f"Spec: `{head_path}`")
    if workload_profile:
        lines.append(f"Workload profile: `{workload_profile}`")
    lines.append("")

    # Cost summary
    lines.append("### Cost")
    if base_summary is None and head_summary is not None:
        lines.append(f"- New spec — monthly cost: **{_format_money(head_total)}**")
    elif head_summary is None and base_summary is not None:
        lines.append(f"- Spec removed — was **{_format_money(base_total)}**/mo")
    elif head_summary is None and base_summary is None:
        lines.append("- Cost data unavailable for both base and head.")
    else:
        annual_delta = monthly_delta * 12
        lines.append(
            f"- Monthly: {_format_money(base_total)} → **{_format_money(head_total)}** "
            f"({_format_delta(monthly_delta)}, {_format_delta(annual_delta).replace('/mo', '/yr')})"
        )

    # Component diff
    if added_ids or removed_ids or changed_ids:
        lines.append("")
        lines.append("### Architecture diff")
        if added_ids:
            for cid in added_ids:
                comp = head_components[cid]
                cost = (head_summary.breakdown.get(cid) if head_summary else None)
                cost_str = f" ({_format_money(cost)}/mo)" if cost else ""
                lines.append(f"- + **{comp['label']}** ({comp['service']}{', ' + comp['provider'] if comp['provider'] else ''}){cost_str}")
        if removed_ids:
            for cid in removed_ids:
                comp = base_components[cid]
                cost = (base_summary.breakdown.get(cid) if base_summary else None)
                cost_str = f" (was {_format_money(cost)}/mo)" if cost else ""
                lines.append(f"- - ~~{comp['label']}~~ ({comp['service']}{', ' + comp['provider'] if comp['provider'] else ''}){cost_str}")
        if changed_ids:
            for cid in changed_ids:
                head_comp = head_components[cid]
                base_comp = base_components[cid]
                changes = []
                for key in ("service", "label", "provider"):
                    if head_comp.get(key) != base_comp.get(key):
                        changes.append(f"{key}: `{base_comp.get(key)}` → `{head_comp.get(key)}`")
                lines.append(f"- ~ **{head_comp['label']}** ({', '.join(changes)})")

    # Compliance
    if compliance:
        lines.append("")
        lines.append("### Compliance")
        frameworks = sorted(set(head_compliance) | set(base_compliance))
        if not frameworks:
            lines.append(f"- No compliance results returned for: {compliance}")
        else:
            for fw in frameworks:
                head_r = head_compliance.get(fw)
                base_r = base_compliance.get(fw)
                if head_r and base_r:
                    head_status = "passed" if head_r["passed"] else "failed"
                    base_status = "passed" if base_r["passed"] else "failed"
                    head_failed = set(head_r["failed_checks"])
                    base_failed = set(base_r["failed_checks"])
                    new_failures = sorted(head_failed - base_failed)
                    fixed = sorted(base_failed - head_failed)
                    line = f"- **{fw}**: {base_status} → {head_status} (score {base_r['score']:.2f} → {head_r['score']:.2f})"
                    lines.append(line)
                    if new_failures:
                        lines.append(f"  - new failing checks: {', '.join(f'`{c}`' for c in new_failures)}")
                    if fixed:
                        lines.append(f"  - resolved: {', '.join(f'`{c}`' for c in fixed)}")
                elif head_r:
                    status = "passed" if head_r["passed"] else "failed"
                    lines.append(f"- **{fw}**: {status} (score {head_r['score']:.2f}, {len(head_r['failed_checks'])} failing checks)")
                elif base_r:
                    lines.append(f"- **{fw}**: removed from spec")

    lines.append("")
    lines.append("---")
    lines.append(
        "_Generated by [`cloudwright-ai`](https://pypi.org/project/cloudwright-ai/). "
        "See `docs/github-action.md` for setup._"
    )

    delta = {
        "monthly_delta": round(monthly_delta, 2),
        "head_monthly": round(head_total, 2),
        "base_monthly": round(base_total, 2),
        "components_added": added_ids,
        "components_removed": removed_ids,
        "components_changed": changed_ids,
    }
    return "\n".join(lines), delta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-cost", required=True)
    parser.add_argument("--head-validate", required=True)
    parser.add_argument("--base-cost", required=True)
    parser.add_argument("--base-validate", required=True)
    parser.add_argument("--head-spec", required=True)
    parser.add_argument("--base-spec", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--compliance", default="")
    parser.add_argument("--workload-profile", default="")
    args = parser.parse_args()

    body, delta = render(
        head_cost=_load_json(args.head_cost),
        head_validate=_load_json(args.head_validate),
        base_cost=_load_json(args.base_cost),
        base_validate=_load_json(args.base_validate),
        head_spec=_load_yaml(args.head_spec),
        base_spec=_load_yaml(args.base_spec),
        marker=args.marker,
        compliance=args.compliance,
        workload_profile=args.workload_profile,
        head_path=args.head_spec,
    )
    Path(args.output).write_text(body)
    delta_path = Path(args.output).with_name("cost-delta.json")
    delta_path.write_text(json.dumps(delta))
    print(f"Wrote {args.output} ({len(body)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
