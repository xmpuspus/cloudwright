from __future__ import annotations

from cloudwright.compliance import ComplianceScanner
from cloudwright.oscal import to_oscal
from cloudwright.spec import ArchSpec, Component, Constraints


def _component(id: str, service: str, config: dict | None = None, tier: int = 2) -> Component:
    return Component(id=id, service=service, provider="aws", label=id, tier=tier, config=config or {})


def _spec(components, compliance: list[str] | None = None) -> ArchSpec:
    return ArchSpec(
        name="Test",
        provider="aws",
        region="us-east-1",
        constraints=Constraints(compliance=compliance or []),
        components=components,
    )


class TestToOscalStructure:
    def test_returns_component_definition(self):
        spec = _spec([_component("db", "rds")], ["HIPAA"])
        report = ComplianceScanner().scan(spec, frameworks=["HIPAA"], run_checkov=False)
        doc = to_oscal(spec, report, ["HIPAA"])
        assert "component-definition" in doc

    def test_metadata_oscal_version(self):
        spec = _spec([_component("db", "rds")], ["HIPAA"])
        report = ComplianceScanner().scan(spec, frameworks=["HIPAA"], run_checkov=False)
        doc = to_oscal(spec, report, ["HIPAA"])
        assert doc["component-definition"]["metadata"]["oscal-version"] == "1.1.2"

    def test_metadata_version(self):
        spec = _spec([_component("db", "rds")], ["HIPAA"])
        report = ComplianceScanner().scan(spec, frameworks=["HIPAA"], run_checkov=False)
        doc = to_oscal(spec, report, ["HIPAA"])
        assert doc["component-definition"]["metadata"]["version"] == "1.6.0"

    def test_uuid_present(self):
        spec = _spec([_component("db", "rds")], ["HIPAA"])
        report = ComplianceScanner().scan(spec, frameworks=["HIPAA"], run_checkov=False)
        doc = to_oscal(spec, report, ["HIPAA"])
        assert doc["component-definition"]["uuid"]

    def test_components_length_matches_spec(self):
        components = [
            _component("web", "ec2"),
            _component("db", "rds", {"backup": True, "multi_az": True}, tier=3),
            _component("cache", "elasticache"),
        ]
        spec = _spec(components, ["HIPAA"])
        report = ComplianceScanner().scan(spec, frameworks=["HIPAA"], run_checkov=False)
        doc = to_oscal(spec, report, ["HIPAA"])
        assert len(doc["component-definition"]["components"]) == len(spec.components)


class TestDeterministicUuid:
    def test_uuid_stable_across_calls(self):
        spec = _spec([_component("db", "rds")], ["HIPAA"])
        report = ComplianceScanner().scan(spec, frameworks=["HIPAA"], run_checkov=False)
        doc1 = to_oscal(spec, report, ["HIPAA"])
        doc2 = to_oscal(spec, report, ["HIPAA"])
        assert doc1["component-definition"]["uuid"] == doc2["component-definition"]["uuid"]

    def test_uuid_differs_for_different_spec_names(self):
        spec_a = ArchSpec(name="Alpha", provider="aws", components=[_component("db", "rds")])
        spec_b = ArchSpec(name="Beta", provider="aws", components=[_component("db", "rds")])
        report_a = ComplianceScanner().scan(spec_a, frameworks=["HIPAA"], run_checkov=False)
        report_b = ComplianceScanner().scan(spec_b, frameworks=["HIPAA"], run_checkov=False)
        doc_a = to_oscal(spec_a, report_a, ["HIPAA"])
        doc_b = to_oscal(spec_b, report_b, ["HIPAA"])
        assert doc_a["component-definition"]["uuid"] != doc_b["component-definition"]["uuid"]

    def test_uuid_differs_for_different_frameworks(self):
        spec = _spec([_component("db", "rds")], ["HIPAA"])
        report = ComplianceScanner().scan(spec, frameworks=["HIPAA"], run_checkov=False)
        doc_hipaa = to_oscal(spec, report, ["HIPAA"])
        doc_fedramp = to_oscal(spec, report, ["FedRAMP"])
        assert doc_hipaa["component-definition"]["uuid"] != doc_fedramp["component-definition"]["uuid"]


class TestNotSatisfiedFindings:
    def test_hipaa_unencrypted_store_yields_not_satisfied(self):
        # RDS without encryption flag triggers missing_encryption -> HIPAA 164.312(a)(2)(iv)
        spec = _spec([_component("db", "rds", {"backup": True, "multi_az": True}, tier=3)], ["HIPAA"])
        report = ComplianceScanner().scan(spec, frameworks=["HIPAA"], run_checkov=False)

        doc = to_oscal(spec, report, ["HIPAA"])
        components = doc["component-definition"]["components"]

        # Collect all implemented-requirements across all components
        all_reqs = []
        for comp in components:
            for impl in comp.get("control-implementations", []):
                all_reqs.extend(impl.get("implemented-requirements", []))

        not_satisfied = [r for r in all_reqs if r["implementation-status"]["state"] == "not-satisfied"]
        assert not_satisfied, "expected at least one not-satisfied requirement"

        # The encryption control for HIPAA should appear
        control_ids = {r["control-id"] for r in not_satisfied}
        # HIPAA control kept verbatim (not NIST-shaped)
        assert "164.312(a)(2)(iv)" in control_ids

    def test_fedramp_control_ids_lowercased(self):
        spec = _spec([_component("db", "rds", {"backup": True, "multi_az": True}, tier=3)], ["FedRAMP"])
        report = ComplianceScanner().scan(spec, frameworks=["FedRAMP"], run_checkov=False)
        doc = to_oscal(spec, report, ["FedRAMP"])

        all_reqs = []
        for comp in doc["component-definition"]["components"]:
            for impl in comp.get("control-implementations", []):
                all_reqs.extend(impl.get("implemented-requirements", []))

        # FedRAMP is NIST-shaped so SC-28 should become sc-28
        control_ids = {r["control-id"] for r in all_reqs}
        assert "sc-28" in control_ids
        assert "SC-28" not in control_ids

    def test_clean_spec_has_no_not_satisfied(self):
        spec = _spec(
            [_component("db", "rds", {"encryption": True, "backup": True, "multi_az": True}, tier=3)],
            ["HIPAA"],
        )
        report = ComplianceScanner().scan(spec, frameworks=["HIPAA"], run_checkov=False)
        doc = to_oscal(spec, report, ["HIPAA"])

        all_reqs = []
        for comp in doc["component-definition"]["components"]:
            for impl in comp.get("control-implementations", []):
                all_reqs.extend(impl.get("implemented-requirements", []))

        not_satisfied = [r for r in all_reqs if r["implementation-status"]["state"] == "not-satisfied"]
        assert not_satisfied == []
