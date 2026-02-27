"""ArchSpec — the core data format for Silmaril.

Everything flows through ArchSpec: chat generates it, diagrams render it,
cost engine prices it, exporters turn it into Terraform/CloudFormation/Mermaid.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Constraints(BaseModel):
    compliance: list[str] = Field(default_factory=list)
    budget_monthly: float | None = None
    availability: float | None = None
    regions: list[str] = Field(default_factory=list)


class Component(BaseModel):
    id: str
    service: str
    provider: str
    label: str
    description: str = ""
    tier: int = 2
    config: dict[str, Any] = Field(default_factory=dict)


class Connection(BaseModel):
    source: str
    target: str
    label: str = ""
    protocol: str | None = None
    port: int | None = None


class ComponentCost(BaseModel):
    component_id: str
    service: str
    monthly: float
    hourly: float | None = None
    notes: str = ""


class CostEstimate(BaseModel):
    monthly_total: float
    breakdown: list[ComponentCost] = Field(default_factory=list)
    currency: str = "USD"
    as_of: str = Field(default_factory=lambda: date.today().isoformat())


class Alternative(BaseModel):
    provider: str
    monthly_total: float
    spec: ArchSpec | None = None
    key_differences: list[str] = Field(default_factory=list)


class ComponentChange(BaseModel):
    component_id: str
    field: str
    old_value: str
    new_value: str
    cost_delta: float = 0.0


class DiffResult(BaseModel):
    added: list[Component] = Field(default_factory=list)
    removed: list[Component] = Field(default_factory=list)
    changed: list[ComponentChange] = Field(default_factory=list)
    cost_delta: float = 0.0
    summary: str = ""
    compliance_impact: list[str] = Field(default_factory=list)


class ValidationCheck(BaseModel):
    name: str
    category: str
    passed: bool
    severity: str = "medium"
    detail: str = ""
    recommendation: str = ""


class ValidationResult(BaseModel):
    framework: str
    passed: bool
    score: float = 0.0
    checks: list[ValidationCheck] = Field(default_factory=list)


class ArchSpec(BaseModel):
    """The core data format. Everything flows through this."""

    name: str
    version: int = 1
    provider: str = "aws"
    region: str = "us-east-1"
    constraints: Constraints | None = None
    components: list[Component] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    cost_estimate: CostEstimate | None = None
    alternatives: list[Alternative] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_yaml(self) -> str:
        data = self.model_dump(exclude_none=True, exclude_defaults=False)
        # Remove empty lists and dicts for cleaner output
        data = _clean_empty(data)
        return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent, exclude_none=True)

    def export(self, fmt: str, output: str | None = None, output_dir: str | None = None) -> str:
        from silmaril.exporter import export_spec

        return export_spec(self, fmt, output=output, output_dir=output_dir)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> ArchSpec:
        data = yaml.safe_load(yaml_str)
        return cls.model_validate(data)

    @classmethod
    def from_file(cls, path: str | Path) -> ArchSpec:
        p = Path(path)
        text = p.read_text()
        if p.suffix in (".yaml", ".yml"):
            return cls.from_yaml(text)
        return cls.model_validate_json(text)

    @classmethod
    def json_schema(cls) -> dict:
        return cls.model_json_schema()


def _clean_empty(d: Any) -> Any:
    if isinstance(d, dict):
        return {k: _clean_empty(v) for k, v in d.items() if v not in ([], {}, None, "")}
    if isinstance(d, list):
        return [_clean_empty(i) for i in d]
    return d
