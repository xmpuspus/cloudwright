"""Shared HCL utilities for Terraform export."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_REQUIRED_PROVIDERS: dict[str, dict] = {
    "aws": {
        "source": "hashicorp/aws",
        "version": "= 5.82.2",
    },
    "gcp": {
        "source": "hashicorp/google",
        "version": "= 6.14.1",
    },
    "azure": {
        "source": "hashicorp/azurerm",
        "version": "= 4.14.0",
    },
    "databricks": {"source": "databricks/databricks", "version": "= 1.65.0"},
}


def _hcl_quote(value: object) -> str:
    """Return a safely-quoted HCL string literal for ``value``.

    Escapes backslashes, double quotes, newlines, and carriage returns so that
    user-controlled fields (component labels, ids, region, metadata, module
    sources) cannot break out of the string and inject HCL/Terraform code.

    The return value INCLUDES the surrounding double quotes — callers should
    use it directly in HCL like::

        f"  name = {_hcl_quote(c.label)}"
    """
    s = "" if value is None else str(value)
    # Order matters: escape backslash first so subsequent escapes are not
    # double-escaped.
    escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    return f'"{escaped}"'


def hcl_string(value: str) -> str:
    """Backward-compatible wrapper around :func:`_hcl_quote`."""
    return _hcl_quote(value)


def _hcl_num(value: object, default: float, *, allow_float: bool = False) -> str:
    """Return a safe numeric HCL literal for ``value``.

    Numeric config fields are interpolated into HCL without surrounding quotes,
    so a string value (e.g. from LLM drift or a hand-edited spec) would be
    emitted verbatim and could break out into arbitrary HCL — including a
    ``provisioner "local-exec"`` that runs on ``terraform apply``. Coercing to
    a real number here makes the numeric paths injection-proof regardless of the
    input type; uncoercible values fall back to ``default``.
    """
    try:
        num = float(value)  # type: ignore[arg-type]
        if not allow_float:
            num = int(num)
        else:
            num = int(num) if num.is_integer() else num
    except (TypeError, ValueError):
        num = int(default) if (not allow_float and float(default).is_integer()) else default
    return str(num)


def provider_block(provider: str, spec: "ArchSpec") -> str:
    if provider == "aws":
        return f'provider "aws" {{\n  region = {_hcl_quote(spec.region)}\n}}'
    if provider == "gcp":
        project = spec.metadata.get("gcp_project", "my-gcp-project")
        region = spec.metadata.get("gcp_region", spec.region)
        return f'provider "google" {{\n  project = {_hcl_quote(project)}\n  region  = {_hcl_quote(region)}\n}}'
    if provider == "azure":
        return 'provider "azurerm" {\n  features {}\n}'
    if provider == "databricks":
        return 'provider "databricks" {\n  host  = var.databricks_host\n  token = var.databricks_token\n}'
    return f"# Unknown provider: {provider}"


def variable_block(name: str, description: str = "", default: str | None = None, sensitive: bool = False) -> str:
    lines = [f'variable "{name}" {{']
    if description:
        lines.append(f"  description = {_hcl_quote(description)}")
    if sensitive:
        lines.append("  sensitive   = true")
    if default is not None:
        lines.append(f"  default     = {_hcl_quote(default)}")
    lines.append("}")
    return "\n".join(lines)


def output_block(name: str, value: str) -> str:
    return f'output "{name}" {{\n  value = {_hcl_quote(value)}\n}}'
