"""Pulumi exporter — TypeScript and Python dialects from one ArchSpec.

Two entry points:

- :func:`render_pulumi_ts` returns the contents of an ``index.ts``.
- :func:`render_pulumi_python` returns the contents of a ``__main__.py``.

Both renderers honour the same safe-by-default posture as the v1.3 Terraform
exporter (S3 public access blocked, RDS encrypted with backups, EC2 IMDSv2,
DynamoDB SSE+PITR, etc.). User-controlled string fields are escaped via
``_ts_string`` / ``_py_string`` from :mod:`cloudwright.exporter.pulumi.common`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.pulumi import (
    aws_python,
    aws_ts,
    azure_python,
    azure_ts,
    common,
    gcp_python,
    gcp_ts,
)

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component


__all__ = [
    "render_pulumi_ts",
    "render_pulumi_python",
    "providers_in_spec",
]


def providers_in_spec(spec: "ArchSpec") -> set[str]:
    providers = {(spec.provider or "").lower()}
    for c in spec.components:
        providers.add((c.provider or "").lower())
    return {p for p in providers if p in {"aws", "gcp", "azure"}}


def _render_ts_resource(c: "Component", spec: "ArchSpec") -> str:
    provider = (c.provider or "").lower()
    if provider == "aws":
        return aws_ts.render_resource(c, spec)
    if provider == "gcp":
        return gcp_ts.render_resource(c, spec)
    if provider == "azure":
        return azure_ts.render_resource(c, spec)
    safe_label = common._safe_comment(c.label)
    return f"// Unsupported provider: {provider} (component: {c.id} - {safe_label})"


def _render_python_resource(c: "Component", spec: "ArchSpec") -> str:
    provider = (c.provider or "").lower()
    if provider == "aws":
        return aws_python.render_resource(c, spec)
    if provider == "gcp":
        return gcp_python.render_resource(c, spec)
    if provider == "azure":
        return azure_python.render_resource(c, spec)
    safe_label = common._safe_comment(c.label)
    return f"# Unsupported provider: {provider} (component: {c.id} - {safe_label})"


def render_pulumi_ts(spec: "ArchSpec") -> str:
    """Render an ArchSpec as a Pulumi TypeScript ``index.ts``."""
    providers = providers_in_spec(spec)
    parts: list[str] = []
    parts.extend(common.header_ts(spec.name))

    if "aws" in providers:
        parts.extend(aws_ts.render_aws_preamble())
    if "gcp" in providers:
        parts.extend(gcp_ts.render_gcp_preamble(spec))
    if "azure" in providers:
        parts.extend(azure_ts.render_azure_preamble())

    parts.append("// Resources")
    for c in spec.components:
        parts.append(_render_ts_resource(c, spec))
        parts.append("")

    parts.append(f"export const architectureName = {common._ts_string(spec.name)};")
    return "\n".join(parts) + "\n"


def render_pulumi_python(spec: "ArchSpec") -> str:
    """Render an ArchSpec as a Pulumi Python ``__main__.py``."""
    providers = providers_in_spec(spec)
    parts: list[str] = []
    parts.extend(common.header_py(spec.name))

    if "aws" in providers:
        parts.extend(aws_python.render_aws_preamble())
    if "gcp" in providers:
        parts.extend(gcp_python.render_gcp_preamble(spec))
    if "azure" in providers:
        parts.extend(azure_python.render_azure_preamble())

    parts.append("# Resources")
    for c in spec.components:
        parts.append(_render_python_resource(c, spec))
        parts.append("")

    parts.append(f"pulumi.export({common._py_string('architecture_name')}, {common._py_string(spec.name)})")
    return "\n".join(parts) + "\n"


def project_files_ts(spec: "ArchSpec") -> dict[str, str]:
    """Return all files for a Pulumi TypeScript project layout."""
    providers = providers_in_spec(spec)
    return {
        "index.ts": render_pulumi_ts(spec),
        "Pulumi.yaml": common.pulumi_yaml_ts(spec.name),
        "package.json": common.package_json(spec.name, providers),
        "tsconfig.json": common.tsconfig_json(),
    }


def project_files_python(spec: "ArchSpec") -> dict[str, str]:
    """Return all files for a Pulumi Python project layout."""
    providers = providers_in_spec(spec)
    return {
        "__main__.py": render_pulumi_python(spec),
        "Pulumi.yaml": common.pulumi_yaml_python(spec.name),
        "requirements.txt": common.requirements_txt(providers),
    }
