"""Tests for Databricks provider integration."""

from __future__ import annotations

from cloudwright.spec import ArchSpec, Component, Connection


def _databricks_spec() -> ArchSpec:
    """Build a 4-component Databricks lakehouse spec."""
    return ArchSpec(
        name="Lakehouse",
        provider="databricks",
        region="us-east-1",
        components=[
            Component(
                id="uc",
                service="databricks_unity_catalog",
                provider="databricks",
                label="Unity Catalog",
            ),
            Component(
                id="wh",
                service="databricks_sql_warehouse",
                provider="databricks",
                label="SQL Warehouse",
                config={"compute_type": "sql_serverless", "dbu_per_hour": 4.0},
            ),
            Component(
                id="dlt",
                service="databricks_pipeline",
                provider="databricks",
                label="DLT Pipeline",
                config={"compute_type": "dlt_core", "dbu_per_hour": 3.0},
            ),
            Component(
                id="vol",
                service="databricks_volume",
                provider="databricks",
                label="Data Volume",
                config={"storage_gb": 500},
            ),
        ],
        connections=[
            Connection(source="uc", target="wh"),
            Connection(source="dlt", target="vol"),
            Connection(source="vol", target="wh"),
        ],
    )


class TestDatabricksProvider:
    def test_provider_registered(self):
        from cloudwright.providers import PROVIDERS

        assert "databricks" in PROVIDERS

    def test_all_12_services_present(self):
        from cloudwright.providers import PROVIDERS

        assert len(PROVIDERS["databricks"]) == 12

    def test_service_keys_start_with_databricks(self):
        from cloudwright.providers import PROVIDERS

        for key in PROVIDERS["databricks"]:
            assert key.startswith("databricks_"), f"Service key {key} missing prefix"

    def test_equivalences_include_databricks(self):
        from cloudwright.providers import get_equivalent

        assert get_equivalent("redshift", "aws", "databricks") == "databricks_sql_warehouse"
        assert get_equivalent("sagemaker", "aws", "databricks") == "databricks_model_serving"
        assert get_equivalent("kinesis", "aws", "databricks") == "databricks_pipeline"
        assert get_equivalent("step_functions", "aws", "databricks") == "databricks_job"
        assert get_equivalent("s3", "aws", "databricks") == "databricks_volume"

    def test_reverse_equivalences(self):
        from cloudwright.providers import get_equivalent

        assert get_equivalent("databricks_sql_warehouse", "databricks", "aws") == "redshift"
        assert get_equivalent("databricks_model_serving", "databricks", "gcp") == "vertex_ai"

    def test_cross_provider_equivalences(self):
        from cloudwright.providers import get_equivalent

        assert get_equivalent("bigquery", "gcp", "databricks") == "databricks_sql_warehouse"
        assert get_equivalent("synapse", "azure", "databricks") == "databricks_sql_warehouse"


class TestDatabricksArchitect:
    def test_provider_services_registered(self):
        from cloudwright.architect import _PROVIDER_SERVICES

        assert "databricks" in _PROVIDER_SERVICES
        assert len(_PROVIDER_SERVICES["databricks"]) == 12

    def test_service_normalization(self):
        from cloudwright.architect import _SERVICE_NORMALIZATION

        assert _SERVICE_NORMALIZATION.get("sql_warehouse") == "databricks_sql_warehouse"
        assert _SERVICE_NORMALIZATION.get("dlt") == "databricks_pipeline"
        assert _SERVICE_NORMALIZATION.get("delta_live_tables") == "databricks_pipeline"
        assert _SERVICE_NORMALIZATION.get("dbx_cluster") == "databricks_cluster"

    def test_parse_databricks_spec(self):
        from cloudwright.architect import _parse_arch_spec

        raw = {
            "name": "Test Lakehouse",
            "provider": "databricks",
            "region": "us-east-1",
            "components": [
                {
                    "id": "wh",
                    "service": "databricks_sql_warehouse",
                    "provider": "databricks",
                    "label": "SQL Warehouse",
                },
            ],
            "connections": [],
        }
        spec = _parse_arch_spec(raw, None)
        assert spec.provider == "databricks"
        assert spec.components[0].service == "databricks_sql_warehouse"


class TestDatabricksCost:
    def test_per_dbu_formula(self):
        from cloudwright.catalog.formula import per_dbu

        result = per_dbu({"compute_type": "jobs", "dbu_per_hour": 2.0, "hours_per_month": 200})
        assert result == 60.0  # 0.15 * 2.0 * 200

    def test_per_dbu_formula_defaults(self):
        from cloudwright.catalog.formula import per_dbu

        result = per_dbu({})
        assert result == 584.0  # 0.40 * 2.0 * 730

    def test_fallback_prices_exist(self):
        from cloudwright.catalog.formula import _FALLBACK_PRICES

        expected = [
            "databricks_sql_warehouse",
            "databricks_cluster",
            "databricks_job",
            "databricks_pipeline",
            "databricks_model_serving",
            "databricks_unity_catalog",
            "databricks_vector_search",
            "databricks_genie",
            "databricks_notebook",
            "databricks_secret_scope",
            "databricks_dashboard",
            "databricks_volume",
        ]
        for key in expected:
            assert key in _FALLBACK_PRICES, f"Missing fallback price for {key}"

    def test_free_services_zero(self):
        from cloudwright.catalog.formula import _FALLBACK_PRICES

        assert _FALLBACK_PRICES["databricks_unity_catalog"] == 0.0
        assert _FALLBACK_PRICES["databricks_secret_scope"] == 0.0
        assert _FALLBACK_PRICES["databricks_notebook"] == 0.0
        assert _FALLBACK_PRICES["databricks_dashboard"] == 0.0

    def test_estimate_returns_nonzero(self):
        from cloudwright.cost import CostEngine

        spec = _databricks_spec()
        estimate = CostEngine().estimate(spec)
        assert estimate.monthly_total > 0


class TestDatabricksTerraform:
    def test_renders_hcl(self):
        from cloudwright.exporter.terraform import render

        spec = _databricks_spec()
        hcl = render(spec)
        assert "terraform" in hcl
        assert "resource" in hcl

    def test_provider_block(self):
        from cloudwright.exporter.terraform import render

        spec = _databricks_spec()
        hcl = render(spec)
        assert "databricks/databricks" in hcl

    def test_resource_types(self):
        from cloudwright.exporter.terraform import render

        spec = _databricks_spec()
        hcl = render(spec)
        assert "databricks_sql_endpoint" in hcl
        assert "databricks_catalog" in hcl

    def test_no_hardcoded_secrets(self):
        from cloudwright.exporter.terraform import render

        spec = _databricks_spec()
        hcl = render(spec)
        assert "dapi" not in hcl.lower()

    def test_variables_included(self):
        from cloudwright.exporter.terraform import render

        spec = _databricks_spec()
        hcl = render(spec)
        assert "databricks_host" in hcl
        assert "databricks_token" in hcl


class TestDatabricksMermaid:
    def test_renders_flowchart(self):
        from cloudwright.exporter.mermaid import render

        spec = _databricks_spec()
        mermaid = render(spec)
        assert "flowchart" in mermaid or "graph" in mermaid


class TestDatabricksIcons:
    def test_provider_color_registered(self):
        from cloudwright.icons import PROVIDER_COLORS

        assert "databricks" in PROVIDER_COLORS
        assert PROVIDER_COLORS["databricks"] == "#FF3621"

    def test_all_services_have_icons(self):
        from cloudwright.icons import ICON_REGISTRY
        from cloudwright.providers import PROVIDERS

        for service in PROVIDERS["databricks"]:
            assert ("databricks", service) in ICON_REGISTRY, f"Missing icon for {service}"


class TestDatabricksTemplate:
    def test_lakehouse_template_exists(self):
        from cloudwright.templates import TEMPLATES

        assert "lakehouse-databricks" in TEMPLATES

    def test_ml_platform_template_exists(self):
        from cloudwright.templates import TEMPLATES

        assert "ml-platform-databricks" in TEMPLATES

    def test_template_keyword_match(self):
        from cloudwright.templates import match_template

        t = match_template("databricks lakehouse analytics")
        assert t is not None
