"""Tests for cloudwright.patterns — no LLM or cloud calls."""

from __future__ import annotations

from cloudwright.patterns import suggest_compliant_patterns


def test_hipaa_returns_at_least_one_pattern():
    results = suggest_compliant_patterns("hipaa")
    assert len(results) >= 1


def test_hipaa_patterns_all_include_hipaa():
    results = suggest_compliant_patterns("hipaa")
    for pattern in results:
        assert "hipaa" in pattern["frameworks"], f"{pattern['name']} missing hipaa in frameworks"


def test_soc2_returns_at_least_one_pattern():
    results = suggest_compliant_patterns("soc2")
    assert len(results) >= 1


def test_soc2_patterns_all_include_soc2():
    results = suggest_compliant_patterns("soc2")
    for pattern in results:
        assert "soc2" in pattern["frameworks"]


def test_pci_dss_returns_at_least_one_pattern():
    results = suggest_compliant_patterns("pci-dss")
    assert len(results) >= 1


def test_pci_dss_patterns_all_include_pci_dss():
    results = suggest_compliant_patterns("pci-dss")
    for pattern in results:
        assert "pci-dss" in pattern["frameworks"]


def test_fedramp_returns_at_least_one_pattern():
    results = suggest_compliant_patterns("fedramp")
    assert len(results) >= 1


def test_iso27001_returns_at_least_one_pattern():
    results = suggest_compliant_patterns("iso27001")
    assert len(results) >= 1


def test_gdpr_returns_at_least_one_pattern():
    results = suggest_compliant_patterns("gdpr")
    assert len(results) >= 1


def test_unknown_framework_returns_empty():
    assert suggest_compliant_patterns("unknown-framework") == []
    assert suggest_compliant_patterns("") == []
    assert suggest_compliant_patterns("sox") == []


def test_result_dict_has_required_keys():
    results = suggest_compliant_patterns("soc2")
    for pattern in results:
        assert "name" in pattern
        assert "source" in pattern
        assert "frameworks" in pattern
        assert "why" in pattern
        assert isinstance(pattern["frameworks"], list)
        assert isinstance(pattern["why"], str)
        assert len(pattern["why"]) > 0


def test_results_ranked_by_coverage_breadth():
    # Patterns with more frameworks should appear first
    results = suggest_compliant_patterns("soc2")
    if len(results) >= 2:
        first_count = len(results[0]["frameworks"])
        last_count = len(results[-1]["frameworks"])
        assert first_count >= last_count


def test_case_insensitive_lookup():
    lower = suggest_compliant_patterns("hipaa")
    upper = suggest_compliant_patterns("HIPAA")
    mixed = suggest_compliant_patterns("HiPaA")
    assert lower == upper == mixed


def test_source_field_has_expected_prefix():
    for fw in ("hipaa", "soc2", "pci-dss", "fedramp", "iso27001", "gdpr"):
        for pattern in suggest_compliant_patterns(fw):
            assert pattern["source"].startswith(("template:", "module:"))
