"""Deterministic dependency-aware migration planning."""

from __future__ import annotations

from collections import defaultdict

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

        dependency_map: dict[str, list[str]] = defaultdict(list)
        for dependency in project.estate.dependencies:
            if dependency.source in mappings and dependency.target in mappings:
                dependency_map[dependency.source].append(dependency.target)

        self._check_cycles(mappings, dependency_map)
        orders = self._schedule_orders(mappings, dependency_map)
        waves = self._build_waves(assets, mappings, dependency_map, orders, warnings)
        assurance = self._build_assurance(waves, project, mappings, pack_name)
        economics = self._calculate_economics(assets, mappings)

        return MigrationAssessment(
            project_name=project.name,
            industry=project.industry,
            domain_pack=pack_name or project.domain_pack,
            transition=TransitionSpec(
                project_name=project.name,
                complete=not unresolved,
                waves=waves,
                warnings=warnings,
                unresolved_assets=unresolved,
                economics=economics,
            ),
            assurance=assurance,
        )

    @staticmethod
    def _check_cycles(mappings: dict[str, TargetMapping], dependencies: dict[str, list[str]]) -> None:
        state: dict[str, int] = {}
        stack: list[str] = []

        def visit(asset_id: str) -> None:
            if state.get(asset_id) == 2:
                return
            if state.get(asset_id) == 1:
                start = stack.index(asset_id)
                cycle = stack[start:] + [asset_id]
                raise ValueError(f"dependency cycle detected: {' -> '.join(cycle)}")
            state[asset_id] = 1
            stack.append(asset_id)
            for dependency_id in dependencies.get(asset_id, []):
                if dependency_id in mappings:
                    visit(dependency_id)
            stack.pop()
            state[asset_id] = 2

        for mapped_asset_id in mappings:
            visit(mapped_asset_id)

    @staticmethod
    def _schedule_orders(mappings: dict[str, TargetMapping], dependencies: dict[str, list[str]]) -> dict[str, int]:
        orders: dict[str, int] = {}

        def schedule(asset_id: str) -> int:
            if asset_id in orders:
                return orders[asset_id]
            mapping = mappings[asset_id]
            if mapping.disposition == "retain":
                orders[asset_id] = 0
                return 0
            dependency_orders = [schedule(item) for item in dependencies.get(asset_id, [])]
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
            return orders[asset_id]

        for mapped_asset_id in mappings:
            schedule(mapped_asset_id)

        movable_orders = [
            order for asset_id, order in orders.items() if mappings[asset_id].disposition not in {"retain", "retire"}
        ]
        retirement_order = max(movable_orders, default=0) + 1
        for asset_id, mapping in mappings.items():
            if mapping.disposition == "retire":
                orders[asset_id] = max(retirement_order, mapping.wave_hint or retirement_order)
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
    def _calculate_economics(assets: dict[str, EstateAsset], mappings: dict[str, TargetMapping]) -> MigrationEconomics:
        current = sum(asset.current_monthly_cost for asset in assets.values())
        target = 0.0
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
        payback = round(net / savings, 2) if savings > 0 and net > 0 else (0.0 if net <= 0 else None)
        return MigrationEconomics(
            current_monthly_cost=round(current, 2),
            target_monthly_cost=round(target, 2),
            monthly_delta=round(monthly_delta, 2),
            one_time_cost=round(one_time, 2),
            dual_run_cost=round(dual_run, 2),
            decommission_credit=round(credit, 2),
            net_migration_cost=round(net, 2),
            payback_months=payback,
        )
