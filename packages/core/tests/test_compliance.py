from __future__ import annotations

from cloudwright.compliance import (
    ComplianceScanner,
    ControlCatalog,
    normalize_framework,
)
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


class TestFrameworkNormalization:
    def test_aliases_resolve(self):
        assert normalize_framework("hipaa") == "HIPAA"
        assert normalize_framework("SOC 2") == "SOC2"
        assert normalize_framework("pci_dss") == "PCI-DSS"
        assert normalize_framework("FedRAMP Moderate") == "FedRAMP"
        assert normalize_framework("iso 27001") == "ISO27001"

    def test_unknown_returns_none(self):
        assert normalize_framework("not-a-framework") is None


class TestControlCatalog:
    def test_rule_maps_to_category(self):
        cat = ControlCatalog()
        assert cat.category_for_rule("missing_encryption") == "encryption_at_rest"
        assert cat.category_for_rule("public_database") == "public_access"

    def test_controls_filtered_by_framework(self):
        cat = ControlCatalog()
        refs = cat.controls("encryption_at_rest", ["HIPAA", "FedRAMP"])
        frameworks = {r.framework for r in refs}
        assert frameworks == {"HIPAA", "FedRAMP"}
        hipaa = [r for r in refs if r.framework == "HIPAA"][0]
        assert hipaa.control_id == "164.312(a)(2)(iv)"
        fedramp = [r for r in refs if r.framework == "FedRAMP"][0]
        assert fedramp.control_id == "SC-28"

    def test_checkov_id_explicit_mapping(self):
        cat = ControlCatalog()
        assert cat.category_for_checkov("CKV_AWS_16", "irrelevant") == "encryption_at_rest"
        assert cat.category_for_checkov("CKV_AWS_260", "x") == "network_exposure"

    def test_checkov_keyword_fallback(self):
        cat = ControlCatalog()
        # Unknown ID, but the name contains 'encrypt'
        assert cat.category_for_checkov("CKV_AWS_99999", "Ensure bucket is encrypted") == "encryption_at_rest"
        assert cat.category_for_checkov("CKV_X", "publicly accessible RDS") == "public_access"

    def test_total_controls_positive(self):
        cat = ControlCatalog()
        assert cat.total_controls("HIPAA") > 0
        assert cat.total_controls("FedRAMP") > 0


class TestComplianceScannerMapping:
    def test_unencrypted_rds_maps_to_controls(self):
        spec = _spec([_component("db", "rds", {"backup": True, "multi_az": True}, tier=3)], ["HIPAA", "FedRAMP"])
        report = ComplianceScanner().scan(spec)
        enc = [f for f in report.findings if f.rule == "missing_encryption"]
        assert enc, "expected a missing_encryption finding"
        controls = {(c.framework, c.control_id) for c in enc[0].controls}
        assert ("HIPAA", "164.312(a)(2)(iv)") in controls
        assert ("FedRAMP", "SC-28") in controls
        assert enc[0].category == "encryption_at_rest"

    def test_frameworks_from_spec_constraints(self):
        spec = _spec([_component("db", "rds", {}, tier=3)], ["soc2"])
        report = ComplianceScanner().scan(spec)
        assert any(s.framework == "SOC2" for s in report.frameworks)
        # SOC2 only requested -> no HIPAA controls attached to findings
        for f in report.findings:
            assert all(c.framework != "HIPAA" for c in f.controls)

    def test_explicit_frameworks_override_spec(self):
        spec = _spec([_component("db", "rds", {}, tier=3)], ["hipaa"])
        report = ComplianceScanner().scan(spec, frameworks=["fedramp"])
        assert [s.framework for s in report.frameworks] == ["FedRAMP"]

    def test_no_frameworks_defaults_to_all(self):
        spec = _spec([_component("db", "rds", {}, tier=3)])
        report = ComplianceScanner().scan(spec)
        names = {s.framework for s in report.frameworks}
        assert {"HIPAA", "SOC2", "PCI-DSS", "FedRAMP"}.issubset(names)

    def test_framework_summary_counts_violations(self):
        spec = _spec([_component("db", "rds", {}, tier=3)], ["HIPAA"])
        report = ComplianceScanner().scan(spec)
        hipaa = [s for s in report.frameworks if s.framework == "HIPAA"][0]
        assert hipaa.status == "fail"
        assert "164.312(a)(2)(iv)" in hipaa.controls_violated
        assert hipaa.controls_total > len(hipaa.controls_violated)

    def test_clean_spec_passes(self):
        spec = _spec(
            [
                _component("db", "rds", {"encryption": True, "backup": True, "multi_az": True}, tier=3),
                _component("store", "s3", {"encryption": True, "backup": True}, tier=4),
            ],
            ["HIPAA"],
        )
        report = ComplianceScanner().scan(spec, run_checkov=False)
        assert report.passed is True
        hipaa = [s for s in report.frameworks if s.framework == "HIPAA"][0]
        assert hipaa.status == "pass"

    def test_graceful_without_checkov(self):
        spec = _spec([_component("db", "rds", {}, tier=3)], ["HIPAA"])
        report = ComplianceScanner().scan(spec, run_checkov=False)
        assert report.checkov_used is False
        assert report.scanner == "builtin"
        # Built-in mapping still produced control-mapped findings.
        assert any(f.controls for f in report.findings)

    def test_report_serializes(self):
        spec = _spec([_component("db", "rds", {}, tier=3)], ["HIPAA"])
        report = ComplianceScanner().scan(spec, run_checkov=False)
        d = report.as_dict()
        assert "findings" in d and "frameworks" in d
        assert d["findings"][0]["controls"][0]["framework"]


class TestMarkdownReport:
    def test_render_markdown_includes_controls(self):
        from cloudwright.compliance import render_markdown

        spec = _spec([_component("db", "rds", {}, tier=3)], ["HIPAA"])
        report = ComplianceScanner().scan(spec, run_checkov=False)
        md = render_markdown(spec, report)
        assert "Compliance Control Report" in md
        assert "Framework Posture" in md
        assert "164.312(a)(2)(iv)" in md
