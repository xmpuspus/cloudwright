"""Compliance scanning with framework control-ID mapping.

Every design-stage finding is mapped to the specific framework controls it
violates (HIPAA 164.312(a)(2)(iv), SOC2 CC6.1, FedRAMP SC-28, ...). This works
on the built-in SecurityScanner and the Terraform HCL scan with no external
tooling. When the Checkov binary is available it is run against the exported
Terraform and its findings are folded into the same control-mapped report.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from cloudwright.security import SecurityScanner, scan_terraform

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_CONTROLS_FILE = Path(__file__).parent / "data" / "compliance_controls.yaml"

# Canonical framework keys and the aliases users may type.
_FRAMEWORK_ALIASES = {
    "hipaa": "HIPAA",
    "soc2": "SOC2",
    "soc 2": "SOC2",
    "pci": "PCI-DSS",
    "pci-dss": "PCI-DSS",
    "pci_dss": "PCI-DSS",
    "pcidss": "PCI-DSS",
    "fedramp": "FedRAMP",
    "fedramp moderate": "FedRAMP",
    "gdpr": "GDPR",
    "iso27001": "ISO27001",
    "iso 27001": "ISO27001",
    "iso-27001": "ISO27001",
    "nist": "NIST-800-53",
    "nist-800-53": "NIST-800-53",
    "nist 800-53": "NIST-800-53",
}

_ALL_FRAMEWORKS = ["HIPAA", "SOC2", "PCI-DSS", "FedRAMP", "GDPR", "ISO27001", "NIST-800-53"]

_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}


def normalize_framework(name: str) -> str | None:
    """Map a user-supplied framework name to a canonical key, or None."""
    return _FRAMEWORK_ALIASES.get(name.strip().lower())


@dataclass(frozen=True)
class ControlRef:
    framework: str
    control_id: str
    title: str

    def as_dict(self) -> dict[str, str]:
        return {"framework": self.framework, "control_id": self.control_id, "title": self.title}


@dataclass
class ComplianceFinding:
    severity: str
    rule: str
    component_id: str | None
    message: str
    remediation: str
    source: str  # "builtin" | "terraform" | "checkov"
    category: str | None
    controls: list[ControlRef] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "component_id": self.component_id,
            "message": self.message,
            "remediation": self.remediation,
            "source": self.source,
            "category": self.category,
            "controls": [c.as_dict() for c in self.controls],
        }


@dataclass
class FrameworkSummary:
    framework: str
    controls_total: int
    controls_violated: list[str]
    findings: int
    status: str  # "pass" | "fail"

    def as_dict(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "controls_total": self.controls_total,
            "controls_violated": self.controls_violated,
            "controls_satisfied": self.controls_total - len(self.controls_violated),
            "findings": self.findings,
            "status": self.status,
        }


@dataclass
class ComplianceReport:
    passed: bool
    findings: list[ComplianceFinding] = field(default_factory=list)
    frameworks: list[FrameworkSummary] = field(default_factory=list)
    scanner: str = "builtin"  # "builtin" | "builtin+checkov"
    checkov_used: bool = False

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "scanner": self.scanner,
            "checkov_used": self.checkov_used,
            "findings": [f.as_dict() for f in self.findings],
            "frameworks": [s.as_dict() for s in self.frameworks],
        }


class ControlCatalog:
    """Loads and resolves the rule/Checkov -> framework-control mapping."""

    def __init__(self, path: Path | None = None) -> None:
        data = yaml.safe_load((path or _CONTROLS_FILE).read_text())
        self._categories: dict[str, dict] = data["categories"]
        self._rule_categories: dict[str, str] = data["rule_categories"]
        self._checkov_ids: dict[str, str] = data.get("checkov_ids", {})
        self._checkov_keywords: list[dict] = data.get("checkov_keywords", [])

    def category_for_rule(self, rule: str) -> str | None:
        return self._rule_categories.get(rule)

    def category_for_checkov(self, check_id: str, check_name: str) -> str | None:
        if check_id in self._checkov_ids:
            return self._checkov_ids[check_id]
        name = (check_name or "").lower()
        for entry in self._checkov_keywords:
            if entry["match"] in name:
                return entry["category"]
        return None

    def default_severity(self, category: str) -> str:
        cat = self._categories.get(category)
        return cat.get("default_severity", "medium") if cat else "medium"

    def controls(self, category: str | None, frameworks: list[str]) -> list[ControlRef]:
        if not category:
            return []
        cat = self._categories.get(category)
        if not cat:
            return []
        title = cat.get("title", category)
        refs: list[ControlRef] = []
        mapping: dict[str, list[str]] = cat.get("controls", {})
        for fw in frameworks:
            for cid in mapping.get(fw, []):
                refs.append(ControlRef(framework=fw, control_id=cid, title=title))
        return refs

    def total_controls(self, framework: str) -> int:
        return sum(len(cat.get("controls", {}).get(framework, [])) for cat in self._categories.values())


def checkov_available() -> bool:
    """True when the checkov binary is on PATH."""
    return shutil.which("checkov") is not None


class ComplianceScanner:
    """Runs design-stage checks and maps every finding to framework controls."""

    def __init__(self, catalog: ControlCatalog | None = None) -> None:
        self.catalog = catalog or ControlCatalog()

    def resolve_frameworks(self, spec: ArchSpec, requested: list[str] | None) -> list[str]:
        names = list(requested) if requested else []
        if not names and spec.constraints and spec.constraints.compliance:
            names = list(spec.constraints.compliance)
        canonical: list[str] = []
        for n in names:
            key = normalize_framework(n)
            if key and key not in canonical:
                canonical.append(key)
        return canonical or list(_ALL_FRAMEWORKS)

    def scan(
        self,
        spec: ArchSpec,
        frameworks: list[str] | None = None,
        run_checkov: bool | None = None,
    ) -> ComplianceReport:
        fws = self.resolve_frameworks(spec, frameworks)
        findings: list[ComplianceFinding] = []

        # 1. Built-in component-level scan.
        for f in SecurityScanner().scan(spec).findings:
            findings.append(self._map_rule(f, "builtin", fws))

        # 2. Terraform HCL scan on the exported infrastructure.
        hcl = self._export_terraform_text(spec)
        if hcl:
            for f in scan_terraform(hcl).findings:
                findings.append(self._map_rule(f, "terraform", fws))

        # 3. Optional Checkov deep scan against the exported Terraform.
        used_checkov = False
        want_checkov = checkov_available() if run_checkov is None else run_checkov
        if want_checkov and checkov_available():
            ck = self._run_checkov(spec, fws)
            if ck is not None:
                findings.extend(ck)
                used_checkov = True

        findings = _dedupe(findings)
        summaries = self._summarize(findings, fws)
        passed = all(f.severity not in ("critical", "high") for f in findings)
        scanner = "builtin+checkov" if used_checkov else "builtin"
        return ComplianceReport(
            passed=passed,
            findings=findings,
            frameworks=summaries,
            scanner=scanner,
            checkov_used=used_checkov,
        )

    def _map_rule(self, finding, source: str, frameworks: list[str]) -> ComplianceFinding:
        category = self.catalog.category_for_rule(finding.rule)
        return ComplianceFinding(
            severity=finding.severity,
            rule=finding.rule,
            component_id=finding.component_id,
            message=finding.message,
            remediation=finding.remediation,
            source=source,
            category=category,
            controls=self.catalog.controls(category, frameworks),
        )

    def _export_terraform_text(self, spec: ArchSpec) -> str | None:
        try:
            from cloudwright.exporter import export_spec

            return export_spec(spec, "terraform")
        except Exception:
            return None

    def _run_checkov(self, spec: ArchSpec, frameworks: list[str]) -> list[ComplianceFinding] | None:
        try:
            from cloudwright.exporter import export_spec
        except Exception:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            try:
                export_spec(spec, "terraform", output_dir=tmp)
            except Exception:
                return None
            try:
                proc = subprocess.run(
                    ["checkov", "-d", tmp, "-o", "json", "--compact", "--quiet", "--soft-fail"],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                return None
            try:
                payload = json.loads(proc.stdout)
            except (json.JSONDecodeError, ValueError):
                return None
        return self._parse_checkov(payload, frameworks)

    def _parse_checkov(self, payload: Any, frameworks: list[str]) -> list[ComplianceFinding]:
        blocks = payload if isinstance(payload, list) else [payload]
        findings: list[ComplianceFinding] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            failed = (block.get("results") or {}).get("failed_checks", [])
            for chk in failed:
                check_id = chk.get("check_id", "")
                check_name = chk.get("check_name", "")
                category = self.catalog.category_for_checkov(check_id, check_name)
                resource = chk.get("resource") or None
                severity = (chk.get("severity") or "").lower()
                if severity not in _SEVERITY_RANK:
                    severity = self.catalog.default_severity(category) if category else "medium"
                guideline = chk.get("guideline") or "See Checkov documentation for remediation steps."
                findings.append(
                    ComplianceFinding(
                        severity=severity,
                        rule=check_id or "checkov_finding",
                        component_id=resource,
                        message=f"{check_id}: {check_name}",
                        remediation=guideline,
                        source="checkov",
                        category=category,
                        controls=self.catalog.controls(category, frameworks),
                    )
                )
        return findings

    def _summarize(self, findings: list[ComplianceFinding], frameworks: list[str]) -> list[FrameworkSummary]:
        summaries: list[FrameworkSummary] = []
        for fw in frameworks:
            violated: set[str] = set()
            count = 0
            for f in findings:
                fw_controls = [c.control_id for c in f.controls if c.framework == fw]
                if fw_controls:
                    count += 1
                    violated.update(fw_controls)
            total = self.catalog.total_controls(fw)
            summaries.append(
                FrameworkSummary(
                    framework=fw,
                    controls_total=total,
                    controls_violated=sorted(violated),
                    findings=count,
                    status="fail" if violated else "pass",
                )
            )
        return summaries


def _dedupe(findings: list[ComplianceFinding]) -> list[ComplianceFinding]:
    """Drop duplicate (rule, component) findings, keeping the highest severity."""
    best: dict[tuple[str, str | None, str], ComplianceFinding] = {}
    for f in findings:
        key = (f.rule, f.component_id, f.source)
        cur = best.get(key)
        if cur is None or _SEVERITY_RANK.get(f.severity, 4) < _SEVERITY_RANK.get(cur.severity, 4):
            best[key] = f
    return sorted(best.values(), key=lambda f: _SEVERITY_RANK.get(f.severity, 4))


def render_markdown(spec: ArchSpec, report: ComplianceReport) -> str:
    """Audit-ready markdown report with control-ID mapping per finding."""
    import datetime

    lines: list[str] = []
    lines.append(f"# Compliance Control Report: {spec.name}")
    lines.append("")
    lines.append(f"**Date:** {datetime.date.today().isoformat()}")
    lines.append(f"**Provider:** {spec.provider}")
    lines.append(f"**Scanner:** {report.scanner}")
    lines.append(f"**Result:** {'PASS' if report.passed else 'FAIL'}")
    lines.append("")
    lines.append("## Framework Posture")
    lines.append("")
    lines.append("| Framework | Controls Satisfied | Controls Violated | Findings | Status |")
    lines.append("|---|---|---|---|---|")
    for s in report.frameworks:
        sat = s.controls_total - len(s.controls_violated)
        viol = ", ".join(s.controls_violated) if s.controls_violated else "—"
        lines.append(f"| {s.framework} | {sat}/{s.controls_total} | {viol} | {s.findings} | {s.status.upper()} |")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if not report.findings:
        lines.append("No findings. All mapped controls satisfied.")
        return "\n".join(lines)
    for f in report.findings:
        scope = f.component_id or "architecture"
        lines.append(f"### [{f.severity.upper()}] {f.message}")
        lines.append("")
        lines.append(f"- **Scope:** `{scope}`")
        lines.append(f"- **Source:** {f.source}")
        lines.append(f"- **Remediation:** {f.remediation}")
        if f.controls:
            ctrl = ", ".join(f"{c.framework} {c.control_id}" for c in f.controls)
            lines.append(f"- **Violated controls:** {ctrl}")
        lines.append("")
    return "\n".join(lines)
