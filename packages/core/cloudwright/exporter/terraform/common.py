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


def hcl_string(value: str) -> str:
    return f'"{value}"'


def provider_block(provider: str, spec: "ArchSpec") -> str:
    if provider == "aws":
        return f'provider "aws" {{\n  region = "{spec.region}"\n}}'
    if provider == "gcp":
        project = spec.metadata.get("gcp_project", "my-gcp-project")
        region = spec.metadata.get("gcp_region", spec.region)
        return f'provider "google" {{\n  project = "{project}"\n  region  = "{region}"\n}}'
    if provider == "azure":
        return 'provider "azurerm" {\n  features {}\n}'
    if provider == "databricks":
        return 'provider "databricks" {\n  host  = var.databricks_host\n  token = var.databricks_token\n}'
    return f"# Unknown provider: {provider}"


def variable_block(name: str, description: str = "", default: str | None = None, sensitive: bool = False) -> str:
    lines = [f'variable "{name}" {{']
    if description:
        lines.append(f'  description = "{description}"')
    if sensitive:
        lines.append("  sensitive   = true")
    if default is not None:
        lines.append(f'  default     = "{default}"')
    lines.append("}")
    return "\n".join(lines)


def output_block(name: str, value: str) -> str:
    return f'output "{name}" {{\n  value = "{value}"\n}}'
