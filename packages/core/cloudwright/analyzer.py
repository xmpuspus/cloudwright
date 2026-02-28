"""Blast radius analyzer — dependency graph, SPOFs, and impact analysis."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from cloudwright.spec import ArchSpec


@dataclass
class ComponentImpact:
    component_id: str
    service: str
    label: str
    direct_dependents: list[str] = field(default_factory=list)
    transitive_dependents: list[str] = field(default_factory=list)
    blast_radius: int = 0  # total affected components
    is_spof: bool = False  # single point of failure
    tier: int = 0


@dataclass
class AnalysisResult:
    components: list[ComponentImpact] = field(default_factory=list)
    spofs: list[str] = field(default_factory=list)  # component IDs
    critical_path: list[str] = field(default_factory=list)  # highest-impact path
    total_components: int = 0
    max_blast_radius: int = 0
    graph: dict[str, list[str]] = field(default_factory=dict)  # adjacency list
    reverse_graph: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_components": self.total_components,
            "max_blast_radius": self.max_blast_radius,
            "spofs": self.spofs,
            "critical_path": self.critical_path,
            "components": [
                {
                    "component_id": c.component_id,
                    "service": c.service,
                    "label": c.label,
                    "tier": c.tier,
                    "direct_dependents": c.direct_dependents,
                    "transitive_dependents": c.transitive_dependents,
                    "blast_radius": c.blast_radius,
                    "is_spof": c.is_spof,
                }
                for c in self.components
            ],
            "graph": self.graph,
        }


class Analyzer:
    """Analyzes blast radius and dependency structure of an ArchSpec."""

    def analyze(self, spec: ArchSpec, component_id: str | None = None) -> AnalysisResult:
        """Analyze the full architecture or a specific component."""
        # Build directed dependency graphs
        # forward: A -> [B, C] means A feeds into B and C (B and C depend on A)
        # reverse: B -> [A] means B's upstream providers are [A]
        forward: dict[str, list[str]] = defaultdict(list)
        reverse: dict[str, list[str]] = defaultdict(list)

        comp_map = {c.id: c for c in spec.components}
        all_ids = set(comp_map.keys())

        for conn in spec.connections:
            if conn.source in all_ids and conn.target in all_ids:
                forward[conn.source].append(conn.target)
                reverse[conn.target].append(conn.source)

        # Include isolated components (no connections)
        for cid in all_ids:
            if cid not in forward:
                forward[cid] = []
            if cid not in reverse:
                reverse[cid] = []

        # Compute impact for each component
        impacts = []
        for comp in spec.components:
            direct = list(forward[comp.id])
            transitive = self._get_transitive(comp.id, forward, all_ids)
            blast = len(transitive)
            is_spof = self._is_spof(comp.id, forward, reverse)

            impacts.append(
                ComponentImpact(
                    component_id=comp.id,
                    service=comp.service,
                    label=comp.label,
                    direct_dependents=direct,
                    transitive_dependents=list(transitive),
                    blast_radius=blast,
                    is_spof=is_spof,
                    tier=comp.tier,
                )
            )

        # Sort by blast radius descending
        impacts.sort(key=lambda x: x.blast_radius, reverse=True)

        spofs = [i.component_id for i in impacts if i.is_spof]
        max_blast = impacts[0].blast_radius if impacts else 0
        critical_path = self._find_critical_path(impacts, forward)

        result = AnalysisResult(
            components=impacts,
            spofs=spofs,
            critical_path=critical_path,
            total_components=len(spec.components),
            max_blast_radius=max_blast,
            graph=dict(forward),
            reverse_graph=dict(reverse),
        )

        # Filter to a specific component if requested (graph context still full)
        if component_id:
            filtered = [i for i in impacts if i.component_id == component_id]
            if filtered:
                result.components = filtered

        return result

    def _get_transitive(self, start: str, forward: dict[str, list[str]], all_ids: set[str]) -> set[str]:
        """Get all transitively affected components via BFS."""
        visited: set[str] = set()
        queue = list(forward.get(start, []))
        while queue:
            node = queue.pop(0)
            if node in visited or node == start:
                continue
            visited.add(node)
            queue.extend(forward.get(node, []))
        return visited

    def _is_spof(self, comp_id: str, forward: dict[str, list[str]], reverse: dict[str, list[str]]) -> bool:
        """Return True if this component is the sole upstream for any of its dependents."""
        for dependent in forward.get(comp_id, []):
            upstream = reverse.get(dependent, [])
            if len(upstream) == 1 and upstream[0] == comp_id:
                return True
        return False

    def _find_critical_path(self, impacts: list[ComponentImpact], forward: dict[str, list[str]]) -> list[str]:
        """Find the path through the graph with the most hops from a high-impact root."""
        if not impacts:
            return []

        impact_map = {i.component_id: i.blast_radius for i in impacts}
        best_path: list[str] = []

        for impact in impacts:
            path = self._trace_path(impact.component_id, forward, impact_map)
            if len(path) > len(best_path):
                best_path = path

        return best_path

    def _trace_path(self, start: str, forward: dict[str, list[str]], impact_map: dict[str, int]) -> list[str]:
        """Greedily trace a path by always following the highest-blast-radius neighbor."""
        path = [start]
        current = start
        visited = {start}

        while True:
            dependents = forward.get(current, [])
            unvisited = [d for d in dependents if d not in visited]
            if not unvisited:
                break
            next_node = max(unvisited, key=lambda x: impact_map.get(x, 0))
            path.append(next_node)
            visited.add(next_node)
            current = next_node

        return path
