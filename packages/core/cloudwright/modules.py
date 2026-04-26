"""Repo-backed module catalog and canvas standards checks."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from cloudwright.spec import ArchSpec

_MODULES_DIR = Path(__file__).parent / "data" / "modules"
_SAFE_ID_RE = re.compile(r"[^a-z0-9_-]+")


class TerraformModuleRef(BaseModel):
    source: str
    version: str = ""


class ModuleNaming(BaseModel):
    component_id_prefix: str


class ModuleSpec(BaseModel):
    id: str
    name: str
    provider: str
    category: str
    description: str = ""
    approved: bool = False
    tags: list[str] = Field(default_factory=list)
    required_tags: list[str] = Field(default_factory=list)
    default_tags: dict[str, str] = Field(default_factory=dict)
    naming: ModuleNaming
    terraform: TerraformModuleRef
    fragment: ArchSpec

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "category": self.category,
            "description": self.description,
            "approved": self.approved,
            "tags": self.tags,
            "required_tags": self.required_tags,
            "naming_prefix": self.naming.component_id_prefix,
            "terraform": self.terraform.model_dump(),
        }


class StandardViolation(BaseModel):
    code: str
    severity: str = "error"
    message: str
    component_id: str | None = None
    connection: dict[str, str] | None = None
    module_instance_id: str | None = None


class StandardsResult(BaseModel):
    passed: bool
    violations: list[StandardViolation] = Field(default_factory=list)


@dataclass(frozen=True)
class ModuleInsertResult:
    spec: ArchSpec
    module_instance_id: str
    component_ids: list[str]
    connection_count: int


def safe_id(value: str, fallback: str = "resource") -> str:
    """Return a deterministic IaC-safe lower snake/kebab compatible id."""
    value = _SAFE_ID_RE.sub("_", value.strip().lower()).strip("_-")
    if not value:
        value = fallback
    if not re.match(r"^[a-z_]", value):
        value = f"{fallback}_{value}"
    return value


def unique_id(base: str, used: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


class ModuleCatalog:
    """Loads approved architecture modules from bundled YAML package data."""

    def __init__(self, modules_dir: str | Path | None = None):
        self.modules_dir = Path(modules_dir) if modules_dir else _MODULES_DIR
        self._modules = self._load()

    def _load(self) -> dict[str, ModuleSpec]:
        index_path = self.modules_dir / "_index.yaml"
        if not index_path.exists():
            return {}

        index = yaml.safe_load(index_path.read_text()) or {}
        entries = index.get("modules", [])
        modules: dict[str, ModuleSpec] = {}
        for entry in entries:
            module_path = self.modules_dir / entry
            data = yaml.safe_load(module_path.read_text()) or {}
            module = ModuleSpec.model_validate(data)
            modules[module.id] = module
        return modules

    def list_modules(self, approved_only: bool = True) -> list[ModuleSpec]:
        modules = sorted(self._modules.values(), key=lambda m: (m.provider, m.category, m.name))
        if approved_only:
            modules = [m for m in modules if m.approved]
        return modules

    def summaries(self, approved_only: bool = True) -> list[dict[str, Any]]:
        return [module.summary() for module in self.list_modules(approved_only=approved_only)]

    def get(self, module_id: str) -> ModuleSpec | None:
        return self._modules.get(module_id)

    def require(self, module_id: str) -> ModuleSpec:
        module = self.get(module_id)
        if module is None:
            raise KeyError(module_id)
        return module


def _metadata_dict(spec: ArchSpec) -> dict[str, Any]:
    return copy.deepcopy(spec.metadata or {})


def insert_module(spec: ArchSpec, module: ModuleSpec, instance_id: str | None = None) -> ModuleInsertResult:
    """Insert a module fragment into a spec with deterministic collision-safe ids."""
    data = spec.model_dump(exclude_none=True)
    metadata = _metadata_dict(spec)
    module_meta = metadata.setdefault("modules", {}).setdefault("instances", {})

    used_component_ids = {component["id"] for component in data.get("components", [])}
    used_instance_ids = set(module_meta.keys())
    base_instance_id = safe_id(instance_id or module.id, fallback="module")
    module_instance_id = unique_id(base_instance_id, used_instance_ids)

    prefix = safe_id(module.naming.component_id_prefix, fallback=module_instance_id)
    remap: dict[str, str] = {}
    for component in module.fragment.components:
        base = safe_id(f"{prefix}_{component.id}", fallback=prefix)
        remap[component.id] = unique_id(base, used_component_ids)

    inserted_ids: list[str] = []
    for component in module.fragment.components:
        component_data = component.model_dump(exclude_none=True)
        component_data["id"] = remap[component.id]
        tags = dict(module.default_tags)
        tags.update(component_data.setdefault("config", {}).get("tags") or {})
        component_data["config"]["tags"] = tags
        component_data.setdefault("description", "")
        data.setdefault("components", []).append(component_data)
        inserted_ids.append(component_data["id"])

    for connection in module.fragment.connections:
        conn_data = connection.model_dump(exclude_none=True)
        conn_data["source"] = remap[connection.source]
        conn_data["target"] = remap[connection.target]
        data.setdefault("connections", []).append(conn_data)

    module_meta[module_instance_id] = {
        "module_id": module.id,
        "module_version": module.terraform.version,
        "component_ids": inserted_ids,
        "expected_component_count": len(inserted_ids),
        "required_tags": list(module.required_tags),
        "naming_prefix": prefix,
        "approved": module.approved,
        "terraform": module.terraform.model_dump(),
    }
    data["metadata"] = metadata

    return ModuleInsertResult(
        spec=ArchSpec.model_validate(data),
        module_instance_id=module_instance_id,
        component_ids=inserted_ids,
        connection_count=len(module.fragment.connections),
    )


def _orphan_connection_violations(spec_data: dict[str, Any]) -> list[StandardViolation]:
    component_ids = {c.get("id") for c in spec_data.get("components", []) if isinstance(c, dict)}
    violations: list[StandardViolation] = []
    for connection in spec_data.get("connections", []):
        if not isinstance(connection, dict):
            continue
        source = connection.get("source")
        target = connection.get("target")
        if source not in component_ids or target not in component_ids:
            violations.append(
                StandardViolation(
                    code="orphan_connection",
                    message=f"Connection {source!r} -> {target!r} references a missing component",
                    connection={"source": str(source), "target": str(target)},
                )
            )
    return violations


def validate_standards_from_dict(
    spec_data: dict[str, Any],
    catalog: ModuleCatalog | None = None,
) -> StandardsResult:
    violations = _orphan_connection_violations(spec_data)
    if violations:
        return StandardsResult(passed=False, violations=violations)

    try:
        spec = ArchSpec.model_validate(spec_data)
    except ValidationError as exc:
        return StandardsResult(
            passed=False,
            violations=[
                StandardViolation(
                    code="invalid_spec",
                    message=str(exc.errors()[0].get("msg", exc)),
                )
            ],
        )

    result = validate_standards(spec, catalog=catalog)
    return StandardsResult(passed=not violations and result.passed, violations=violations + result.violations)


def validate_standards(spec: ArchSpec, catalog: ModuleCatalog | None = None) -> StandardsResult:
    catalog = catalog or ModuleCatalog()
    violations: list[StandardViolation] = []
    components_by_id = {component.id: component for component in spec.components}
    instances = (spec.metadata or {}).get("modules", {}).get("instances", {})

    if not isinstance(instances, dict):
        return StandardsResult(
            passed=False,
            violations=[
                StandardViolation(
                    code="invalid_module_metadata",
                    message="spec.metadata.modules.instances must be an object",
                )
            ],
        )

    for instance_id, instance in instances.items():
        if not isinstance(instance, dict):
            violations.append(
                StandardViolation(
                    code="invalid_module_metadata",
                    message="Module instance metadata must be an object",
                    module_instance_id=str(instance_id),
                )
            )
            continue

        module_id = str(instance.get("module_id", ""))
        module = catalog.get(module_id)
        approved = bool(instance.get("approved"))
        component_ids = instance.get("component_ids") or []
        if not isinstance(component_ids, list):
            component_ids = []

        if module is None or not module.approved or not approved:
            violations.append(
                StandardViolation(
                    code="unapproved_module",
                    message=f"Module instance {instance_id!r} does not reference an approved catalog module",
                    module_instance_id=str(instance_id),
                )
            )
        expected_component_count = instance.get("expected_component_count")
        if instance.get("partial") or (
            isinstance(expected_component_count, int) and len(component_ids) != expected_component_count
        ):
            violations.append(
                StandardViolation(
                    code="partial_module_instance",
                    message=f"Module instance {instance_id!r} has been partially modified and no longer matches its catalog fragment",
                    module_instance_id=str(instance_id),
                )
            )

        required_tags = instance.get("required_tags") or (module.required_tags if module else [])
        naming_prefix = str(instance.get("naming_prefix") or (module.naming.component_id_prefix if module else ""))

        for component_id in component_ids:
            component = components_by_id.get(component_id)
            if component is None:
                violations.append(
                    StandardViolation(
                        code="missing_module_component",
                        message=f"Module instance {instance_id!r} references missing component {component_id!r}",
                        component_id=str(component_id),
                        module_instance_id=str(instance_id),
                    )
                )
                continue

            if naming_prefix and not component.id.startswith(naming_prefix):
                violations.append(
                    StandardViolation(
                        code="bad_component_name",
                        message=f"Component {component.id!r} must start with module prefix {naming_prefix!r}",
                        component_id=component.id,
                        module_instance_id=str(instance_id),
                    )
                )

            tags = component.config.get("tags") if isinstance(component.config, dict) else {}
            if not isinstance(tags, dict):
                tags = {}
            for tag in required_tags:
                if not tags.get(tag):
                    violations.append(
                        StandardViolation(
                            code="missing_required_tag",
                            message=f"Component {component.id!r} is missing required tag {tag!r}",
                            component_id=component.id,
                            module_instance_id=str(instance_id),
                        )
                    )

    return StandardsResult(passed=len(violations) == 0, violations=violations)
