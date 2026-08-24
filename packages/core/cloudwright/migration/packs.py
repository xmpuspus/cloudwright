"""Load and apply packaged migration-domain acceptance rules."""

from __future__ import annotations

from importlib.resources import files
from typing import Self

import yaml
from pydantic import Field, model_validator

from cloudwright.migration.models import (
    AcceptanceCriterion,
    AssetKind,
    Comparator,
    CriterionCategory,
    EstateAsset,
    IdentifiedModel,
    ScalarValue,
    YamlModel,
)


class PackSource(YamlModel):
    """Primary source cited by a migration domain pack."""

    title: str
    url: str


class CriterionMatcher(YamlModel):
    """Asset fields that activate one criterion template."""

    asset_kinds: list[AssetKind] = Field(default_factory=list)
    data_classes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    def matches(self, asset: EstateAsset) -> bool:
        """Return whether an asset satisfies every populated matcher field."""
        if not (self.asset_kinds or self.data_classes or self.tags):
            return False
        if self.asset_kinds and asset.kind not in self.asset_kinds:
            return False
        if self.data_classes and not set(self.data_classes).intersection(asset.data_classes):
            return False
        return not self.tags or bool(set(self.tags).intersection(asset.tags))


class PackCriterion(IdentifiedModel):
    """Acceptance criterion template activated by matching estate assets."""

    name: str
    category: CriterionCategory
    metric: str
    comparator: Comparator
    target_value: ScalarValue
    unit: str = ""
    blocking: bool = True
    required_evidence: str
    control_references: list[str] = Field(default_factory=list)
    description: str = ""
    match: CriterionMatcher

    def instantiate(self) -> AcceptanceCriterion:
        """Create the portable criterion consumed by the planner."""
        return AcceptanceCriterion(
            id=self.id,
            name=self.name,
            category=self.category,
            metric=self.metric,
            comparator=self.comparator,
            target_value=self.target_value,
            unit=self.unit,
            blocking=self.blocking,
            required_evidence=self.required_evidence,
            control_references=self.control_references,
            description=self.description,
        )


class DomainPack(YamlModel):
    """Pack metadata, sources, and optional industry criteria."""

    name: str
    title: str
    version: str
    jurisdiction: str = ""
    description: str
    sources: list[PackSource] = Field(default_factory=list)
    criteria: list[PackCriterion] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_criterion_ids(self) -> Self:
        """Reject ambiguous duplicate criterion IDs."""
        ids = [criterion.id for criterion in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("domain-pack criterion ids must be unique")
        return self


class PackSummary(YamlModel):
    """Small catalog entry returned by CLI and HTTP discovery."""

    name: str
    title: str
    version: str
    jurisdiction: str = ""
    description: str


def _pack_files():
    """Return packaged YAML resources in deterministic order."""
    pack_dir = files("cloudwright").joinpath("data", "migration_packs")
    return sorted(
        (item for item in pack_dir.iterdir() if item.name.endswith((".yaml", ".yml"))),
        key=lambda item: item.name,
    )


def _load_resource(resource) -> DomainPack:
    """Parse and validate one packaged YAML resource."""
    data = yaml.safe_load(resource.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"migration pack {resource.name} must contain a mapping")
    return DomainPack.model_validate(data)


def list_packs() -> list[PackSummary]:
    """List available migration domain packs."""
    return [
        PackSummary(
            name=pack.name,
            title=pack.title,
            version=pack.version,
            jurisdiction=pack.jurisdiction,
            description=pack.description,
        )
        for pack in (_load_resource(resource) for resource in _pack_files())
    ]


def load_pack(name: str) -> DomainPack:
    """Load a named migration domain pack."""
    packs = {_load_resource(resource).name: resource for resource in _pack_files()}
    resource = packs.get(name)
    if resource is None:
        available = ", ".join(sorted(packs)) or "none"
        raise ValueError(f"unknown migration pack {name!r}; available packs: {available}")
    return _load_resource(resource)


def criteria_for(pack: DomainPack, assets: list[EstateAsset]) -> list[AcceptanceCriterion]:
    """Instantiate each matching pack criterion once."""
    return [
        template.instantiate() for template in pack.criteria if any(template.match.matches(asset) for asset in assets)
    ]
