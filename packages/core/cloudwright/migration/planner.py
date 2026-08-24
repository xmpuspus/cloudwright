"""Deterministic dependency-aware migration planning."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque

from cloudwright.migration.models import (
    AcceptanceCriterion,
    AssurancePlan,
    EstateAsset,
    MigrationAction,
    MigrationAssessment,
    MigrationEconomics,
    MigrationProject,
    MigrationWave,
    TargetMapping,
    TransitionSpec,
)
from cloudwright.migration.packs import criteria_for, load_pack


class MigrationPlanner:
    """Build transition waves, economics, and acceptance gates."""

    def plan(self, project: MigrationProject, pack_name: str | None = None) -> MigrationAssessment:
        """Build a complete deterministic assessment for one project."""
        project = MigrationProject.model_validate(project.model_dump())
        assets = {asset.id: asset for asset in project.estate.assets}
        mappings = {mapping.source_asset_id: mapping for mapping in project.target.mappings}
        unresolved = sorted(set(assets) - set(mappings))
        warnings = [f"Source asset {asset_id} has no target mapping" for asset_id in unresolved]

        for dependency in project.estate.dependencies:
            dependency_mapping = mappings.get(dependency.target)
            if (
                dependency.source not in mappings
                and dependency_mapping is not None
                and dependency_mapping.disposition == "retire"
            ):
                raise ValueError(
                    f"cannot retire {dependency.target} while dependent asset {dependency.source} has no target mapping"
                )

        dependency_map: dict[str, list[str]] = defaultdict(list)
        for dependency in project.estate.dependencies:
            if dependency.source in mappings and dependency.target in mappings:
                dependency_map[dependency.source].append(dependency.target)

        source_dependency_order = self._dependency_order(mappings, dependency_map)
        self._check_retained_dependencies(mappings, dependency_map, source_dependency_order)
        scheduling_dependencies = self._scheduling_dependencies(mappings, dependency_map)
        dependency_order = self._dependency_order(mappings, scheduling_dependencies)
        orders = self._schedule_orders(mappings, scheduling_dependencies, dependency_order)
        waves = self._build_waves(assets, mappings, scheduling_dependencies, orders, warnings)
        assurance = self._build_assurance(waves, project, mappings, pack_name)
        raw_currency = project.metadata.get("currency", "USD")
        if not isinstance(raw_currency, str) or not raw_currency.strip():
            raise ValueError("metadata.currency must be a non-empty currency code")
        economics = self._calculate_economics(assets, mappings, currency=raw_currency.strip().upper())
        rollbacks_ready = all(action.rollback for wave in waves for action in wave.actions)

        assessment = MigrationAssessment(
            assessment_id="0" * 64,
            project_name=project.name,
            evidence_not_before=project.evidence_not_before,
            industry=project.industry,
            domain_pack=pack_name or project.domain_pack,
            transition=TransitionSpec(
                project_name=project.name,
                complete=not unresolved and rollbacks_ready,
                waves=waves,
                warnings=warnings,
                unresolved_assets=unresolved,
                economics=economics,
            ),
            assurance=assurance,
        )
        fingerprint_payload = {
            "project": project.model_dump(mode="json"),
            "assessment": assessment.model_dump(mode="json", exclude={"assessment_id"}),
        }
        canonical = json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        assessment_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return assessment.model_copy(update={"assessment_id": assessment_id})

    @staticmethod
    def _dependency_order(mappings: dict[str, TargetMapping], dependencies: dict[str, list[str]]) -> list[str]:
        """Return a dependency-first order without recursive graph traversal."""
        dependency_counts = {
            asset_id: sum(dependency_id in mappings for dependency_id in dependencies.get(asset_id, []))
            for asset_id in mappings
        }
        dependents: dict[str, list[str]] = defaultdict(list)
        for asset_id, dependency_ids in dependencies.items():
            for dependency_id in dependency_ids:
                if asset_id in mappings and dependency_id in mappings:
                    dependents[dependency_id].append(asset_id)

        ready = deque(asset_id for asset_id in mappings if dependency_counts[asset_id] == 0)
        ordered: list[str] = []
        while ready:
            asset_id = ready.popleft()
            ordered.append(asset_id)
            for dependent_id in dependents.get(asset_id, []):
                dependency_counts[dependent_id] -= 1
                if dependency_counts[dependent_id] == 0:
                    ready.append(dependent_id)

        if len(ordered) != len(mappings):
            cycle = sorted(asset_id for asset_id, count in dependency_counts.items() if count > 0)
            raise ValueError(f"dependency cycle detected involving: {' -> '.join(cycle)}")
        return ordered

    @staticmethod
    def _check_retained_dependencies(
        mappings: dict[str, TargetMapping],
        dependencies: dict[str, list[str]],
        dependency_order: list[str],
    ) -> None:
        """Reject retained assets whose dependency chain contains a changed asset."""
        changed_dependency: dict[str, str] = {}
        for asset_id in dependency_order:
            for dependency_id in dependencies.get(asset_id, []):
                if mappings[dependency_id].disposition != "retain":
                    changed_dependency[asset_id] = dependency_id
                    break
                if dependency_id in changed_dependency:
                    changed_dependency[asset_id] = changed_dependency[dependency_id]
                    break
            if mappings[asset_id].disposition == "retain" and asset_id in changed_dependency:
                dependency_id = changed_dependency[asset_id]
                disposition = mappings[dependency_id].disposition
                if disposition == "retire":
                    raise ValueError(f"retained asset {asset_id} depends on retired asset {dependency_id}")
                raise ValueError(f"retained asset {asset_id} depends on {disposition} asset {dependency_id}")

    @staticmethod
    def _scheduling_dependencies(
        mappings: dict[str, TargetMapping], dependencies: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """Keep dependencies available until every moving consumer has cut over."""
        scheduled: dict[str, list[str]] = defaultdict(list)
        for asset_id, dependency_ids in dependencies.items():
            for dependency_id in dependency_ids:
                if mappings[dependency_id].disposition == "retire" and mappings[asset_id].disposition != "retain":
                    if asset_id not in scheduled[dependency_id]:
                        scheduled[dependency_id].append(asset_id)
                elif dependency_id not in scheduled[asset_id]:
                    scheduled[asset_id].append(dependency_id)
        return scheduled

    @staticmethod
    def _schedule_orders(
        mappings: dict[str, TargetMapping],
        dependencies: dict[str, list[str]],
        dependency_order: list[str],
    ) -> dict[str, int]:
        orders: dict[str, int] = {}

        for asset_id in dependency_order:
            mapping = mappings[asset_id]
            if mapping.disposition == "retire":
                continue
            if mapping.disposition == "retain":
                orders[asset_id] = 0
                continue
            dependency_orders = [orders[item] for item in dependencies.get(asset_id, [])]
            minimum = max(dependency_orders, default=0) + 1
            if mapping.wave_hint is not None and mapping.wave_hint < minimum:
                blocker = max(
                    dependencies.get(asset_id, []),
                    key=lambda item: orders.get(item, 0),
                    default="dependency",
                )
                raise ValueError(
                    f"wave hint for {asset_id} runs before dependency {blocker}; minimum wave is {minimum}"
                )
            orders[asset_id] = max(minimum, mapping.wave_hint or 1)

        retirement_floor = max(
            (order for asset_id, order in orders.items() if mappings[asset_id].disposition not in {"retain", "retire"}),
            default=0,
        )
        for asset_id in dependency_order:
            mapping = mappings[asset_id]
            if mapping.disposition != "retire":
                continue
            dependency_orders = [orders[item] for item in dependencies.get(asset_id, [])]
            minimum = max([retirement_floor, *dependency_orders]) + 1
            if mapping.wave_hint is not None and mapping.wave_hint < minimum:
                blocker = max(
                    dependencies.get(asset_id, []),
                    key=lambda item: orders.get(item, 0),
                    default="moving assets",
                )
                raise ValueError(
                    f"wave hint for {asset_id} runs before dependency {blocker}; minimum wave is {minimum}"
                )
            orders[asset_id] = max(minimum, mapping.wave_hint or minimum)

        return orders

    @staticmethod
    def _build_waves(
        assets: dict[str, EstateAsset],
        mappings: dict[str, TargetMapping],
        dependencies: dict[str, list[str]],
        orders: dict[str, int],
        warnings: list[str],
    ) -> list[MigrationWave]:
        grouped: dict[int, list[str]] = defaultdict(list)
        for asset_id in assets:
            mapping = mappings.get(asset_id)
            if mapping and mapping.disposition != "retain":
                grouped[orders[asset_id]].append(asset_id)

        waves: list[MigrationWave] = []
        for order in sorted(grouped):
            action_ids = grouped[order]
            actions: list[MigrationAction] = []
            prerequisites: set[str] = set()
            rollbacks: list[str] = []
            for asset_id in action_ids:
                asset = assets[asset_id]
                mapping = mappings[asset_id]
                actions.append(
                    MigrationAction(
                        source_asset_id=asset_id,
                        source_name=asset.name,
                        target_asset_ids=mapping.target_asset_ids,
                        disposition=mapping.disposition,
                        strategy=mapping.strategy,
                        owner=mapping.owner,
                        expected_downtime_minutes=mapping.expected_downtime_minutes,
                        rollback=mapping.rollback,
                    )
                )
                prerequisites.update(
                    dependency_id
                    for dependency_id in dependencies.get(asset_id, [])
                    if orders.get(dependency_id, 0) > 0 and orders[dependency_id] < order
                )
                if mapping.rollback:
                    rollbacks.append(mapping.rollback)
                else:
                    warnings.append(f"Source asset {asset_id} has no rollback procedure")
            gate_id = f"wave-{order}-rollback-ready"
            waves.append(
                MigrationWave(
                    id=f"wave-{order}",
                    order=order,
                    name=f"Wave {order}",
                    actions=actions,
                    prerequisites=sorted(prerequisites),
                    rollback_procedures=rollbacks,
                    gate_ids=[gate_id],
                )
            )
        return waves

    @staticmethod
    def _build_assurance(
        waves: list[MigrationWave],
        project: MigrationProject,
        mappings: dict[str, TargetMapping],
        pack_name: str | None,
    ) -> AssurancePlan:
        criteria = [
            AcceptanceCriterion(
                id=f"wave-{wave.order}-rollback-ready",
                name=f"Wave {wave.order} rollback is ready",
                category="operational",
                metric=f"wave_{wave.order}_rollback_ready",
                comparator="true",
                target_value=True,
                blocking=True,
                required_evidence="change-record",
                wave=wave.order,
            )
            for wave in waves
        ]
        selected_pack = pack_name or project.domain_pack
        if selected_pack:
            migrated_assets = [
                asset
                for asset in project.estate.assets
                if asset.id in mappings and mappings[asset.id].disposition != "retain"
            ]
            pack_criteria = criteria_for(load_pack(selected_pack), migrated_assets)
            final_wave = max((wave.order for wave in waves), default=1)
            for criterion in pack_criteria:
                criteria.append(criterion.model_copy(update={"wave": final_wave}))
                if waves:
                    waves[-1].gate_ids.append(criterion.id)
        return AssurancePlan(criteria=criteria)

    @staticmethod
    def _calculate_economics(
        assets: dict[str, EstateAsset], mappings: dict[str, TargetMapping], *, currency: str = "USD"
    ) -> MigrationEconomics:
        current = sum(asset.current_monthly_cost for asset in assets.values())
        target = sum(asset.current_monthly_cost for asset_id, asset in assets.items() if asset_id not in mappings)
        one_time = 0.0
        dual_run = 0.0
        credit = 0.0
        for asset_id, mapping in mappings.items():
            source_cost = assets[asset_id].current_monthly_cost
            target_cost = mapping.target_monthly_cost
            if mapping.disposition == "retain" and not target_cost:
                target_cost = source_cost
            if mapping.disposition == "retire":
                target_cost = 0
            target += target_cost
            one_time += mapping.one_time_cost
            dual_run += (source_cost + target_cost) * mapping.dual_run_months
            credit += mapping.decommission_credit
        net = one_time + dual_run - credit
        monthly_delta = target - current
        savings = current - target
        payback = round(net / savings, 2) if savings > 0 and net > 0 else (0.0 if savings > 0 else None)
        return MigrationEconomics(
            current_monthly_cost=round(current, 2),
            target_monthly_cost=round(target, 2),
            monthly_delta=round(monthly_delta, 2),
            one_time_cost=round(one_time, 2),
            dual_run_cost=round(dual_run, 2),
            decommission_credit=round(credit, 2),
            net_migration_cost=round(net, 2),
            payback_months=payback,
            currency=currency,
        )
