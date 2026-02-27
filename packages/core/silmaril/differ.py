"""Compares two ArchSpecs and produces a structured diff."""

from __future__ import annotations

from silmaril.spec import ArchSpec, Component, ComponentChange, DiffResult

_SECURITY_SERVICES = {
    "waf",
    "cloud_armor",
    "azure_waf",
    "cognito",
    "firebase_auth",
    "azure_ad",
    "iam",
    "cloudtrail",
    "cloud_logging",
    "azure_monitor",
}

_COMPLIANCE_FIELDS = {"service", "config"}


class Differ:
    def diff(self, old: ArchSpec, new: ArchSpec) -> DiffResult:
        old_map = {c.id: c for c in old.components}
        new_map = {c.id: c for c in new.components}

        added = [new_map[cid] for cid in new_map if cid not in old_map]
        removed = [old_map[cid] for cid in old_map if cid not in new_map]
        changed = _find_changes(old_map, new_map)

        cost_delta = 0.0
        if old.cost_estimate and new.cost_estimate:
            cost_delta = round(new.cost_estimate.monthly_total - old.cost_estimate.monthly_total, 2)

        compliance_impact = _assess_compliance_impact(added, removed, changed, old_map, new_map)
        summary = _build_summary(added, removed, changed, old, new, cost_delta)

        return DiffResult(
            added=added,
            removed=removed,
            changed=changed,
            cost_delta=cost_delta,
            summary=summary,
            compliance_impact=compliance_impact,
        )


def _find_changes(old_map: dict, new_map: dict) -> list[ComponentChange]:
    changes = []
    for cid in old_map:
        if cid not in new_map:
            continue
        old_c = old_map[cid]
        new_c = new_map[cid]

        for field in ("service", "provider", "label", "config"):
            old_val = getattr(old_c, field)
            new_val = getattr(new_c, field)
            if old_val != new_val:
                changes.append(
                    ComponentChange(
                        component_id=cid,
                        field=field,
                        old_value=str(old_val),
                        new_value=str(new_val),
                    )
                )
    return changes


def _assess_compliance_impact(
    added: list[Component],
    removed: list[Component],
    changed: list[ComponentChange],
    old_map: dict,
    new_map: dict,
) -> list[str]:
    impacts = []

    for comp in removed:
        if comp.service in _SECURITY_SERVICES:
            impacts.append(f"Removed {comp.service} ({comp.id}) — may affect compliance posture")

    for change in changed:
        if change.field == "service":
            old_svc = change.old_value
            new_svc = change.new_value
            if old_svc in _SECURITY_SERVICES and new_svc not in _SECURITY_SERVICES:
                impacts.append(f"{change.component_id}: replaced security service {old_svc} with {new_svc}")
        if change.field == "config":
            # Config changed on a security-relevant component
            cid = change.component_id
            comp = new_map.get(cid) or old_map.get(cid)
            if comp and comp.service in _SECURITY_SERVICES:
                impacts.append(f"{cid}: security component config changed")
            # Check if encryption was disabled
            if "encryption" in change.old_value and "True" in change.old_value and "False" in change.new_value:
                impacts.append(f"{cid}: encryption may have been disabled")

    return impacts


def _build_summary(
    added: list[Component],
    removed: list[Component],
    changed: list[ComponentChange],
    old: ArchSpec,
    new: ArchSpec,
    cost_delta: float,
) -> str:
    parts = []

    for comp in added:
        parts.append(f"Added {comp.service} ({comp.id})")

    for comp in removed:
        parts.append(f"Removed {comp.service} ({comp.id})")

    # Collapse service changes for readability
    service_changes = [c for c in changed if c.field == "service"]
    for change in service_changes:
        parts.append(f"{change.component_id}: {change.old_value} -> {change.new_value}")

    other_changes = [c for c in changed if c.field != "service"]
    if other_changes:
        parts.append(f"{len(other_changes)} config/label change(s)")

    if not parts:
        summary = "No changes detected."
    else:
        summary = ". ".join(parts) + "."

    if old.cost_estimate and new.cost_estimate:
        old_total = old.cost_estimate.monthly_total
        new_total = new.cost_estimate.monthly_total
        sign = "+" if cost_delta >= 0 else ""
        summary += f" Cost: ${old_total:,.2f} -> ${new_total:,.2f} ({sign}${cost_delta:,.2f}/mo)."

    return summary
