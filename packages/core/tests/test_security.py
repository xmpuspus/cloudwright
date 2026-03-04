from __future__ import annotations

from cloudwright.security import SecurityFinding, SecurityReport, SecurityScanner, scan_terraform
from cloudwright.spec import ArchSpec, Component, Connection


def _make_spec(components: list[Component], connections: list[Connection] | None = None) -> ArchSpec:
    return ArchSpec(
        name="Test",
        provider="aws",
        region="us-east-1",
        components=components,
        connections=connections or [],
    )


def _component(id: str, service: str, config: dict | None = None, tier: int = 2) -> Component:
    return Component(
        id=id,
        service=service,
        provider="aws",
        label=id,
        tier=tier,
        config=config or {},
    )


def _rules(report: SecurityReport) -> set[str]:
    return {f.rule for f in report.findings}


class TestScannerCleanSpec:
    def test_scanner_passes_clean_spec(self):
        spec = _make_spec(
            [
                _component("alb", "alb", {"https": True}, tier=1),
                _component("web", "ec2", {}, tier=2),
                _component("db", "rds", {"encryption": True, "backup": True, "multi_az": True}, tier=3),
                _component("store", "s3", {"encryption": True, "backup": True}, tier=4),
                _component("mon", "cloudwatch", {}, tier=4),
            ]
        )
        report = SecurityScanner().scan(spec)
        assert report.passed is True
        assert not report.findings


class TestMissingEncryption:
    def test_flags_rds_without_encryption(self):
        spec = _make_spec([_component("db", "rds", {"backup": True, "multi_az": True}, tier=3)])
        report = SecurityScanner().scan(spec)
        assert "missing_encryption" in _rules(report)

    def test_flags_s3_without_encryption(self):
        spec = _make_spec([_component("store", "s3", {"backup": True}, tier=4)])
        report = SecurityScanner().scan(spec)
        assert "missing_encryption" in _rules(report)

    def test_finding_is_high_severity(self):
        spec = _make_spec([_component("db", "rds", {}, tier=3)])
        findings = [f for f in SecurityScanner().scan(spec).findings if f.rule == "missing_encryption"]
        assert findings[0].severity == "high"

    def test_passes_when_encrypted(self):
        spec = _make_spec([_component("db", "rds", {"encryption": True, "backup": True, "multi_az": True}, tier=3)])
        report = SecurityScanner().scan(spec)
        assert "missing_encryption" not in _rules(report)


class TestMissingBackup:
    def test_flags_s3_without_backup(self):
        spec = _make_spec([_component("store", "s3", {"encryption": True}, tier=4)])
        report = SecurityScanner().scan(spec)
        assert "missing_backup" in _rules(report)

    def test_finding_is_medium_severity(self):
        spec = _make_spec([_component("store", "s3", {"encryption": True}, tier=4)])
        findings = [f for f in SecurityScanner().scan(spec).findings if f.rule == "missing_backup"]
        assert findings[0].severity == "medium"

    def test_passes_when_backup_set(self):
        spec = _make_spec([_component("store", "s3", {"encryption": True, "backup": True}, tier=4)])
        report = SecurityScanner().scan(spec)
        assert "missing_backup" not in _rules(report)


class TestNoHttps:
    def test_flags_alb_with_https_false(self):
        spec = _make_spec([_component("alb", "alb", {"https": False}, tier=1)])
        report = SecurityScanner().scan(spec)
        assert "no_https" in _rules(report)

    def test_finding_is_high(self):
        spec = _make_spec([_component("lb", "alb", {"https": False}, tier=1)])
        findings = [f for f in SecurityScanner().scan(spec).findings if f.rule == "no_https"]
        assert findings[0].severity == "high"

    def test_passes_when_https_true(self):
        spec = _make_spec([_component("alb", "alb", {"https": True}, tier=1)])
        report = SecurityScanner().scan(spec)
        assert "no_https" not in _rules(report)

    def test_passes_when_https_not_set(self):
        # Only flag explicit https=False, not absence
        spec = _make_spec([_component("alb", "alb", {}, tier=1)])
        report = SecurityScanner().scan(spec)
        assert "no_https" not in _rules(report)


class TestMissingMonitoring:
    def _five_component_spec(self, include_monitoring: bool) -> ArchSpec:
        comps = [
            _component("cdn", "cloudfront", {}, tier=0),
            _component("alb", "alb", {"https": True}, tier=1),
            _component("web", "ec2", {}, tier=2),
            _component("db", "rds", {"encryption": True, "backup": True, "multi_az": True}, tier=3),
            _component("store", "s3", {"encryption": True, "backup": True}, tier=4),
        ]
        if include_monitoring:
            comps.append(_component("mon", "cloudwatch", {}, tier=4))
        return _make_spec(comps)

    def test_flags_missing_monitoring_on_large_spec(self):
        spec = self._five_component_spec(include_monitoring=False)
        report = SecurityScanner().scan(spec)
        assert "missing_monitoring" in _rules(report)

    def test_passes_when_monitoring_present(self):
        spec = self._five_component_spec(include_monitoring=True)
        report = SecurityScanner().scan(spec)
        assert "missing_monitoring" not in _rules(report)

    def test_no_flag_on_small_spec(self):
        spec = _make_spec(
            [
                _component("web", "ec2", {}),
                _component("db", "rds", {"encryption": True, "backup": True, "multi_az": True}),
            ]
        )
        report = SecurityScanner().scan(spec)
        assert "missing_monitoring" not in _rules(report)


class TestScanTerraform:
    def test_open_sg_flagged(self):
        hcl = 'cidr_blocks = ["0.0.0.0/0"]'
        report = scan_terraform(hcl)
        assert "open_security_group" in _rules(report)
        assert report.passed is False

    def test_iam_wildcard_flagged(self):
        hcl = 'Actions = "*"'
        report = scan_terraform(hcl)
        assert "iam_wildcard" in _rules(report)
        assert report.passed is False

    def test_iam_wildcard_action_array(self):
        hcl = 'actions = ["*"]'
        report = scan_terraform(hcl)
        assert "iam_wildcard" in _rules(report)

    def test_public_database_critical(self):
        hcl = "publicly_accessible = true"
        report = scan_terraform(hcl)
        assert "public_database" in _rules(report)
        findings = [f for f in report.findings if f.rule == "public_database"]
        assert findings[0].severity == "critical"
        assert report.passed is False

    def test_encrypted_false_flagged(self):
        hcl = "encrypted = false"
        report = scan_terraform(hcl)
        assert "missing_encryption" in _rules(report)

    def test_clean_terraform_passes(self):
        hcl = """
resource "aws_db_instance" "main" {
  engine         = "postgres"
  instance_class = "db.r5.large"
  encrypted      = true
  multi_az       = true
}
"""
        report = scan_terraform(hcl)
        assert report.passed is True
        assert not report.findings


class TestReportPassedProperty:
    def test_no_findings_passes(self):
        report = SecurityReport(passed=True, findings=[])
        assert report.passed is True

    def test_critical_count(self):
        report = SecurityReport(
            passed=False,
            findings=[
                SecurityFinding("critical", "x", None, "msg", "fix"),
                SecurityFinding("high", "y", None, "msg", "fix"),
            ],
        )
        assert report.critical_count == 1
        assert report.high_count == 1

    def test_with_high_finding_not_passed(self):
        spec = _make_spec([_component("db", "rds", {}, tier=3)])
        report = SecurityScanner().scan(spec)
        assert report.passed is False

    def test_medium_only_passed(self):
        # Only medium findings (no backup on s3, but encryption present) → passed
        spec = _make_spec([_component("store", "s3", {"encryption": True}, tier=4)])
        report = SecurityScanner().scan(spec)
        assert report.passed is True
        assert any(f.severity == "medium" for f in report.findings)
