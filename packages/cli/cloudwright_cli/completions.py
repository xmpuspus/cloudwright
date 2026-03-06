"""Shell completion callbacks for common CLI parameters."""

from __future__ import annotations


def complete_provider(incomplete: str) -> list[tuple[str, str]]:
    providers = [
        ("aws", "Amazon Web Services"),
        ("gcp", "Google Cloud Platform"),
        ("azure", "Microsoft Azure"),
        ("databricks", "Databricks Lakehouse"),
    ]
    return [(p, h) for p, h in providers if p.startswith(incomplete)]


def complete_compliance(incomplete: str) -> list[tuple[str, str]]:
    frameworks = [
        ("hipaa", "Health Insurance Portability and Accountability Act"),
        ("pci-dss", "Payment Card Industry Data Security Standard"),
        ("soc2", "Service Organization Control 2"),
        ("fedramp", "Federal Risk and Authorization Management Program"),
        ("gdpr", "General Data Protection Regulation"),
    ]
    return [(f, h) for f, h in frameworks if f.startswith(incomplete)]


def complete_export_format(incomplete: str) -> list[tuple[str, str]]:
    formats = [
        ("terraform", "HashiCorp Terraform HCL"),
        ("cloudformation", "AWS CloudFormation YAML"),
        ("mermaid", "Mermaid diagram syntax"),
        ("d2", "D2 diagram language"),
        ("c4", "C4 model diagram"),
        ("svg", "SVG vector diagram"),
        ("png", "PNG raster diagram"),
        ("sbom", "Software Bill of Materials"),
        ("aibom", "AI Bill of Materials"),
    ]
    return [(f, h) for f, h in formats if f.startswith(incomplete)]
