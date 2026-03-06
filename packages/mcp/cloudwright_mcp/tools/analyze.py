from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def analyze_blast_radius(spec_json: dict, component_id: str | None = None) -> dict:
        """Analyze blast radius and dependency structure of an architecture."""
        from cloudwright.analyzer import Analyzer
        from cloudwright.spec import ArchSpec

        from cloudwright_mcp.serializers import analysis_result_to_dict

        spec = ArchSpec.model_validate(spec_json)
        result = Analyzer().analyze(spec, component_id=component_id)
        return analysis_result_to_dict(result)

    @mcp.tool()
    def score_architecture(spec_json: dict) -> dict:
        """Score an architecture across reliability, security, cost, compliance, and complexity."""
        from cloudwright.scorer import Scorer
        from cloudwright.spec import ArchSpec

        from cloudwright_mcp.serializers import score_result_to_dict

        spec = ArchSpec.model_validate(spec_json)
        result = Scorer().score(spec)
        return score_result_to_dict(result)

    @mcp.tool()
    def diff_architectures(old_spec_json: dict, new_spec_json: dict) -> dict:
        """Diff two architecture specs and return a structured change report."""
        from cloudwright.differ import Differ
        from cloudwright.spec import ArchSpec

        old = ArchSpec.model_validate(old_spec_json)
        new = ArchSpec.model_validate(new_spec_json)
        result = Differ().diff(old, new)
        return result.model_dump(exclude_none=True)
