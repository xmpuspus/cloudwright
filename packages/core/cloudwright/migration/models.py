"""Portable contracts for migration planning and evidence checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AssetKind = Literal[
    "infrastructure",
    "application",
    "data",
    "platform",
    "network",
    "facility",
    "business_service",
    "other",
]
Criticality = Literal["critical", "high", "medium", "low"]
Disposition = Literal[
    "retain",
    "retire",
    "rehost",
    "relocate",
    "replatform",
    "refactor",
    "repurchase",
    "replace",
]
CriterionCategory = Literal[
    "operational",
    "data",
    "financial",
    "security",
    "compliance",
    "resilience",
    "decommissioning",
]
Comparator = Literal["eq", "gte", "lte", "zero", "true"]
ScalarValue = bool | int | float | str

_ID_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")


class YamlModel(BaseModel):
    """Base model with strict fields and safe YAML helpers."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary."""
        return self.model_dump(mode="json")

    def to_yaml(self) -> str:
        """Serialize the model as stable YAML."""
        return yaml.safe_dump(self.as_dict(), sort_keys=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, content: str) -> Self:
        """Load a model from a YAML mapping."""
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError(f"{cls.__name__} YAML must contain a mapping")
        return cls.model_validate(data)

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        """Load a model from a YAML or JSON file."""
        return cls.from_yaml(Path(path).read_text())


class IdentifiedModel(YamlModel):
    """Base for records that use stable portable IDs."""

    id: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        """Reject IDs that cannot work as stable cross-format keys."""
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError("id must start with a letter or underscore and use letters, numbers, _ or -")
        return value


class DiscoveryProvenance(YamlModel):
    """Source and confidence for one discovered asset fact set."""

    source: str
    observed_at: str
    confidence: float = Field(ge=0, le=1)
    reference: str = ""


class EstateAsset(IdentifiedModel):
    """One portable asset in a current or target estate."""

    name: str
    kind: AssetKind
    environment: str = "production"
    provider: str = "unknown"
    location: str = ""
    owner: str = ""
    criticality: Criticality = "medium"
    lifecycle: str = "active"
    data_classes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    current_monthly_cost: float = Field(default=0, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    provenance: list[DiscoveryProvenance] = Field(default_factory=list)


class AssetDependency(YamlModel):
    """A directed dependency where source depends on target."""

    source: str
    target: str
    kind: str = "runtime"
    criticality: Criticality = "medium"
    description: str = ""


class EstateSpec(YamlModel):
    """The current estate and its directed dependency graph."""

    name: str
    assets: list[EstateAsset]
    dependencies: list[AssetDependency] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_asset_graph(self) -> Self:
        """Reject duplicate asset IDs and dangling dependency references."""
        asset_ids = [asset.id for asset in self.assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("estate asset ids must be unique")
        known = set(asset_ids)
        for dependency in self.dependencies:
            missing = {dependency.source, dependency.target} - known
            if missing:
                raise ValueError(f"dependency references missing asset(s): {', '.join(sorted(missing))}")
            if dependency.source == dependency.target:
                raise ValueError(f"asset {dependency.source} cannot depend on itself")
        return self


class TargetMapping(YamlModel):
    """The migration decision and economics for one source asset."""

    source_asset_id: str
    target_asset_ids: list[str] = Field(default_factory=list)
    disposition: Disposition
    strategy: str = ""
    owner: str = ""
    expected_downtime_minutes: int = Field(default=0, ge=0)
    wave_hint: int | None = Field(default=None, ge=1)
    rollback: str = ""
    one_time_cost: float = Field(default=0, ge=0)
    target_monthly_cost: float = Field(default=0, ge=0)
    dual_run_months: float = Field(default=0, ge=0)
    decommission_credit: float = Field(default=0, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("rollback")
    @classmethod
    def normalize_rollback(cls, value: str) -> str:
        """Treat whitespace-only rollback text as missing."""
        return value.strip()

    @model_validator(mode="after")
    def validate_targets_for_disposition(self) -> Self:
        """Need a target for each disposition that moves or replaces an asset."""
        if self.disposition not in {"retain", "retire"} and not self.target_asset_ids:
            raise ValueError(f"{self.disposition} mapping needs at least one target asset")
        return self


class TargetSpec(YamlModel):
    """Proposed target assets and source-to-target decisions."""

    name: str
    assets: list[EstateAsset] = Field(default_factory=list)
    mappings: list[TargetMapping]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target_references(self) -> Self:
        """Reject duplicate targets, mappings, and dangling target references."""
        target_ids = [asset.id for asset in self.assets]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("target asset ids must be unique")
        source_ids = [mapping.source_asset_id for mapping in self.mappings]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("each source asset may have only one target mapping")
        known = set(target_ids)
        for mapping in self.mappings:
            missing = set(mapping.target_asset_ids) - known
            if missing:
                raise ValueError(f"mapping references missing target asset(s): {', '.join(sorted(missing))}")
        return self


class MigrationProject(YamlModel):
    """Source estate, proposed target, and optional domain pack."""

    schema_version: str = "1.0"
    name: str
    industry: str = "general"
    domain_pack: str | None = None
    estate: EstateSpec
    target: TargetSpec
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source_references(self) -> Self:
        """Reject mappings that name a source asset outside the estate."""
        known = {asset.id for asset in self.estate.assets}
        missing = {mapping.source_asset_id for mapping in self.target.mappings} - known
        if missing:
            raise ValueError(f"mapping references missing source asset(s): {', '.join(sorted(missing))}")
        return self


class MigrationAction(YamlModel):
    """One source-to-target action in a migration wave."""

    source_asset_id: str
    source_name: str
    target_asset_ids: list[str] = Field(default_factory=list)
    disposition: Disposition
    strategy: str = ""
    owner: str = ""
    expected_downtime_minutes: int = 0
    rollback: str = ""


class MigrationWave(IdentifiedModel):
    """An ordered group of migration actions and gates."""

    order: int = Field(ge=1)
    name: str
    actions: list[MigrationAction]
    prerequisites: list[str] = Field(default_factory=list)
    rollback_procedures: list[str] = Field(default_factory=list)
    gate_ids: list[str] = Field(default_factory=list)


class MigrationEconomics(YamlModel):
    """Explicit migration and recurring cost summary."""

    current_monthly_cost: float = 0
    target_monthly_cost: float = 0
    monthly_delta: float = 0
    one_time_cost: float = 0
    dual_run_cost: float = 0
    decommission_credit: float = 0
    net_migration_cost: float = 0
    payback_months: float | None = None
    currency: str = "USD"


class AcceptanceCriterion(IdentifiedModel):
    """One measurable gate that migration evidence must satisfy."""

    name: str
    category: CriterionCategory
    metric: str
    comparator: Comparator
    target_value: ScalarValue
    unit: str = ""
    blocking: bool = True
    required_evidence: str
    control_references: list[str] = Field(default_factory=list)
    wave: int | None = Field(default=None, ge=1)
    description: str = ""


class AssurancePlan(YamlModel):
    """The complete acceptance contract for a transition."""

    criteria: list[AcceptanceCriterion] = Field(default_factory=list)


class TransitionSpec(YamlModel):
    """Ordered migration plan plus unresolved work and economics."""

    project_name: str
    complete: bool
    waves: list[MigrationWave]
    warnings: list[str] = Field(default_factory=list)
    unresolved_assets: list[str] = Field(default_factory=list)
    economics: MigrationEconomics


class MigrationAssessment(YamlModel):
    """Planner output consumed by the CLI, API, UI, and evaluator."""

    schema_version: str = "1.0"
    project_name: str
    industry: str = "general"
    domain_pack: str | None = None
    transition: TransitionSpec
    assurance: AssurancePlan


class EvidenceObservation(YamlModel):
    """One measured or attested value for an acceptance criterion."""

    criterion_id: str
    value: ScalarValue
    source: str
    observed_at: str
    notes: str = ""


class EvidenceInput(YamlModel):
    """Recorded evidence submitted for one migration project."""

    project_name: str
    observations: list[EvidenceObservation]


class CriterionResult(YamlModel):
    """Evaluation result for one acceptance criterion."""

    criterion_id: str
    name: str
    category: CriterionCategory
    passed: bool
    blocking: bool
    expected: ScalarValue
    actual: ScalarValue | None = None
    source: str = ""
    detail: str = ""


class EvidencePack(YamlModel):
    """Closure decision and complete result set for a migration."""

    schema_version: str = "1.0"
    project_name: str
    closed: bool
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    missing: int = Field(ge=0)
    blocking_failures: int = Field(ge=0)
    results: list[CriterionResult]
