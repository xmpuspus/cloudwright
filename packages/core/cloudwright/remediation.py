"""Agentic drift -> remediation — closes the gap between current and desired spec.

Read-only: computes what *would* happen if the desired spec replaced the current
one. Never applies changes. Degrades gracefully when terraform/tofu is absent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec


def remediate(
    current_spec: "ArchSpec",
    desired_spec: "ArchSpec",
    *,
    run_plan: bool = False,
    skip_plan: bool = False,
) -> dict[str, Any]:
    """Compute the full remediation picture between current and desired spec.

    Args:
        current_spec: The spec reflecting what is currently deployed.
        desired_spec: The target spec to converge toward.
        run_plan: When True, attempt a real terraform plan (needs credentials).
            When False (default), only run init + validate — no credentials needed.

    Returns:
        A dict with keys:
        - drift: list of change dicts from the diff
        - cost_delta: {"current": float, "desired": float, "delta": float, "currency": str}
        - quality_delta: {"current": float, "desired": float, "delta": float,
                          "current_grade": str, "desired_grade": str}
        - plan: PlanResult.as_dict()
        - summary: human-readable summary string
    """
    from cloudwright.cost import CostEngine
    from cloudwright.critique import critique
    from cloudwright.differ import Differ
    from cloudwright.planner import plan_terraform

    # 1. Compute drift/diff between current and desired
    differ = Differ()
    diff = differ.diff(current_spec, desired_spec)

    drift_items: list[dict[str, Any]] = []
    for comp in diff.added:
        drift_items.append({"change": "add", "id": comp.id, "service": comp.service})
    for comp in diff.removed:
        drift_items.append({"change": "remove", "id": comp.id, "service": comp.service})
    for ch in diff.changed:
        drift_items.append(
            {
                "change": "modify",
                "id": ch.component_id,
                "field": ch.field,
                "from": ch.old_value,
                "to": ch.new_value,
            }
        )

    # 2. Cost delta
    engine = CostEngine()
    current_estimate = engine.estimate(current_spec)
    desired_estimate = engine.estimate(desired_spec)
    delta = round(desired_estimate.monthly_total - current_estimate.monthly_total, 2)
    cost_delta: dict[str, Any] = {
        "current": current_estimate.monthly_total,
        "desired": desired_estimate.monthly_total,
        "delta": delta,
        "currency": "USD",
    }

    # 3. Quality delta via critique (deterministic, no LLM)
    current_report = critique(current_spec)
    desired_report = critique(desired_spec)
    quality_delta: dict[str, Any] = {
        "current": round(current_report.score, 1),
        "desired": round(desired_report.score, 1),
        "delta": round(desired_report.score - current_report.score, 1),
        "current_grade": current_report.grade,
        "desired_grade": desired_report.grade,
    }

    # 4. Terraform/tofu plan preview of the desired spec (read-only). Skippable
    #    so callers (and tests) can get drift+cost+quality without invoking the
    #    IaC toolchain.
    if skip_plan:
        plan_dict: dict[str, Any] = {"skipped": True, "validated": False}
        plan_validated = False
    else:
        plan_result = plan_terraform(desired_spec, run_plan=run_plan)
        plan_dict = plan_result.as_dict()
        plan_validated = plan_result.validated

    # 5. Build summary
    n_drift = len(drift_items)
    cost_sign = "+" if delta >= 0 else ""
    quality_sign = "+" if quality_delta["delta"] >= 0 else ""
    plan_ok = "skipped" if skip_plan else ("valid" if plan_validated else "not validated")
    summary = (
        f"{n_drift} change(s) to close drift. "
        f"Cost: {cost_sign}${delta:,.2f}/mo "
        f"(${current_estimate.monthly_total:,.2f} -> ${desired_estimate.monthly_total:,.2f}). "
        f"Quality: {quality_sign}{quality_delta['delta']:.1f} pts "
        f"({current_report.grade} -> {desired_report.grade}). "
        f"Plan: {plan_ok}."
    )

    return {
        "drift": drift_items,
        "cost_delta": cost_delta,
        "quality_delta": quality_delta,
        "plan": plan_dict,
        "summary": summary,
    }
