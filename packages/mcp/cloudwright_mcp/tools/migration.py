from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def plan_migration(
        project_json: Annotated[
            dict,
            Field(
                description=(
                    "MigrationProject with the current estate, dependency graph, target assets, "
                    "source mappings, costs, rollback paths, and optional domain pack."
                )
            ),
        ],
        pack: Annotated[
            str | None,
            Field(description="Optional installed domain-pack name that replaces the project value."),
        ] = None,
    ) -> dict:
        """Build read-only migration waves, economics, and acceptance gates.

        Returns a MigrationAssessment dictionary. The tool does not copy data,
        change infrastructure, switch traffic, or run a cutover.
        """
        from cloudwright.migration import MigrationPlanner, MigrationProject, validate_migration_size

        try:
            validate_migration_size(project_json)
        except ValueError as exc:
            return {"error": str(exc)}
        try:
            project = MigrationProject.model_validate(project_json)
        except Exception as exc:
            return {"error": f"Invalid migration project: {exc}"}
        try:
            return MigrationPlanner().plan(project, pack_name=pack).as_dict()
        except ValueError as exc:
            return {"error": f"Migration planning failed: {exc}"}

    @mcp.tool()
    def verify_migration(
        project_json: Annotated[
            dict,
            Field(description="MigrationProject used to rebuild the transition and acceptance gates."),
        ],
        evidence_json: Annotated[
            dict,
            Field(description="EvidenceInput with one recorded observation per measured acceptance gate."),
        ],
        pack: Annotated[
            str | None,
            Field(description="Optional installed domain-pack name that replaces the project value."),
        ] = None,
    ) -> dict:
        """Rebuild migration gates and check recorded evidence for closure.

        Returns an EvidencePack dictionary. Missing or failed blocking evidence
        keeps `closed` false. The caller cannot replace the planner output.
        """
        from cloudwright.migration import (
            EvidenceEvaluator,
            EvidenceInput,
            MigrationPlanner,
            MigrationProject,
            validate_migration_size,
        )

        try:
            validate_migration_size(project_json, evidence_json)
        except ValueError as exc:
            return {"error": str(exc)}
        try:
            project = MigrationProject.model_validate(project_json)
            evidence = EvidenceInput.model_validate(evidence_json)
        except Exception as exc:
            return {"error": f"Invalid migration input: {exc}"}
        try:
            assessment = MigrationPlanner().plan(project, pack_name=pack)
            return EvidenceEvaluator().evaluate(assessment, evidence).as_dict()
        except ValueError as exc:
            return {"error": f"Migration evidence check failed: {exc}"}
