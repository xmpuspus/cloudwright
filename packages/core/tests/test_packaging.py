"""Packaging acceptance tests — verify the package is usable after install."""

from __future__ import annotations

import json
from pathlib import Path

import cloudwright
import pytest
from cloudwright.spec import ArchSpec, Component, Connection


class TestImports:
    """Verify all public API symbols are importable."""

    def test_core_models_importable(self):
        from cloudwright import (
            ArchSpec,
            Component,
        )

        assert ArchSpec is not None
        assert Component is not None

    def test_lazy_imports(self):
        from cloudwright import Architect, Catalog, Differ, Validator

        assert Architect is not None
        assert Catalog is not None
        assert Differ is not None
        assert Validator is not None

    def test_invalid_import_raises(self):
        with pytest.raises(AttributeError):
            _ = cloudwright.NoSuchThing  # type: ignore[attr-defined]


class TestVersion:
    def test_version_is_string(self):
        assert isinstance(cloudwright.__version__, str)

    def test_version_is_semver(self):
        parts = cloudwright.__version__.split(".")
        assert len(parts) >= 2
        assert all(p.isdigit() for p in parts[:2])


class TestPyTyped:
    def test_core_py_typed_exists(self):
        marker = Path(cloudwright.__file__).parent / "py.typed"
        assert marker.exists(), "Missing py.typed marker in core package"


class TestCatalogDb:
    def test_bundled_catalog_db_exists(self):
        db_path = Path(cloudwright.__file__).parent / "data" / "catalog.db"
        assert db_path.exists(), f"catalog.db not found at {db_path}"
        assert db_path.stat().st_size > 0, "catalog.db is empty"

    def test_catalog_initializes_from_bundled(self):
        from cloudwright import Catalog

        cat = Catalog()
        stats = cat.get_stats()
        assert stats["instance_count"] > 0

    def test_catalog_search_works(self):
        from cloudwright import Catalog

        results = Catalog().search(vcpus=4, memory_gb=16)
        assert isinstance(results, list)


class TestSpecRoundTrip:
    """Verify ArchSpec serializes and deserializes correctly."""

    def test_yaml_round_trip(self):
        spec = ArchSpec(
            name="Round Trip Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="app", service="ec2", provider="aws", label="App Server", tier=2),
            ],
            connections=[],
        )
        yaml_str = spec.to_yaml()
        restored = ArchSpec.from_yaml(yaml_str)
        assert restored.name == spec.name
        assert len(restored.components) == 1
        assert restored.components[0].id == "app"

    def test_json_round_trip(self):
        spec = ArchSpec(
            name="JSON Test",
            provider="gcp",
            region="us-central1",
            components=[
                Component(id="fn", service="cloud_functions", provider="gcp", label="Function", tier=2),
            ],
        )
        json_str = spec.to_json()
        data = json.loads(json_str)
        restored = ArchSpec.model_validate(data)
        assert restored.name == spec.name
        assert restored.provider == "gcp"

    def test_file_round_trip(self, tmp_path: Path):
        spec = ArchSpec(
            name="File Test",
            provider="azure",
            region="eastus",
            components=[
                Component(id="vm", service="virtual_machines", provider="azure", label="VM", tier=2),
            ],
        )
        yaml_path = tmp_path / "spec.yaml"
        yaml_path.write_text(spec.to_yaml())
        restored = ArchSpec.from_file(yaml_path)
        assert restored.name == "File Test"
        assert restored.provider == "azure"


class TestComponentValidation:
    def test_valid_id_accepted(self):
        c = Component(id="my_component", service="ec2", provider="aws", label="Test")
        assert c.id == "my_component"

    def test_hyphen_in_id(self):
        c = Component(id="my-component", service="ec2", provider="aws", label="Test")
        assert c.id == "my-component"

    def test_invalid_id_rejected(self):
        with pytest.raises(ValueError, match="IaC-safe"):
            Component(id="123invalid", service="ec2", provider="aws", label="Test")

    def test_special_chars_rejected(self):
        with pytest.raises(ValueError, match="IaC-safe"):
            Component(id="bad.id", service="ec2", provider="aws", label="Test")


class TestJsonSchema:
    def test_schema_generation(self):
        schema = ArchSpec.json_schema()
        assert isinstance(schema, dict)
        # Pydantic v2 uses $defs/$ref at top level
        defs = schema.get("$defs", {})
        arch_schema = defs.get("ArchSpec", schema)
        assert "properties" in arch_schema
        assert "name" in arch_schema["properties"]
        assert "components" in arch_schema["properties"]


class TestExporters:
    """Verify all export formats produce output."""

    @pytest.fixture
    def spec(self) -> ArchSpec:
        return ArchSpec(
            name="Export Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="api", service="api_gateway", provider="aws", label="API", tier=0),
                Component(id="fn", service="lambda", provider="aws", label="Lambda", tier=2),
                Component(id="db", service="dynamodb", provider="aws", label="DynamoDB", tier=3),
            ],
            connections=[
                Connection(source="api", target="fn"),
                Connection(source="fn", target="db"),
            ],
        )

    @pytest.mark.parametrize("fmt", ["terraform", "cloudformation", "mermaid", "sbom", "aibom"])
    def test_export_produces_output(self, spec: ArchSpec, fmt: str):
        content = spec.export(fmt)
        assert isinstance(content, str)
        assert len(content) > 10


class TestCostEngine:
    def test_price_returns_spec_with_estimate(self):
        from cloudwright.cost import CostEngine

        spec = ArchSpec(
            name="Cost Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(
                    id="web",
                    service="ec2",
                    provider="aws",
                    label="Web",
                    tier=2,
                    config={"instance_type": "m5.large"},
                ),
            ],
        )
        priced = CostEngine().price(spec)
        assert priced.cost_estimate is not None
        assert priced.cost_estimate.monthly_total > 0
        assert priced.cost_estimate.currency == "USD"
        assert len(priced.cost_estimate.breakdown) == 1


class TestDiffer:
    def test_diff_no_changes(self):
        from cloudwright import Differ

        spec = ArchSpec(
            name="Same",
            provider="aws",
            components=[
                Component(id="a", service="ec2", provider="aws", label="A"),
            ],
        )
        result = Differ().diff(spec, spec)
        assert len(result.added) == 0
        assert len(result.removed) == 0
        assert len(result.changed) == 0

    def test_diff_detects_addition(self):
        from cloudwright import Differ

        old = ArchSpec(
            name="Old",
            provider="aws",
            components=[
                Component(id="a", service="ec2", provider="aws", label="A"),
            ],
        )
        new = ArchSpec(
            name="New",
            provider="aws",
            components=[
                Component(id="a", service="ec2", provider="aws", label="A"),
                Component(id="b", service="rds", provider="aws", label="B"),
            ],
        )
        result = Differ().diff(old, new)
        assert len(result.added) == 1
        assert result.added[0].id == "b"


class TestValidator:
    def test_validate_hipaa(self):
        from cloudwright import Validator

        spec = ArchSpec(
            name="HIPAA Test",
            provider="aws",
            components=[
                Component(
                    id="db",
                    service="rds",
                    provider="aws",
                    label="DB",
                    tier=3,
                    config={"encryption": True, "multi_az": True},
                ),
            ],
        )
        results = Validator().validate(spec, compliance=["hipaa"])
        assert len(results) > 0
        assert results[0].framework.lower() == "hipaa"
        assert isinstance(results[0].score, float)
