from __future__ import annotations

from typing import Iterator

from cloudwright.adapters import InstancePrice, ManagedServicePrice, PricingAdapter


class DatabricksPricingAdapter(PricingAdapter):
    """Databricks pricing adapter — returns static DBU rates."""

    provider = "databricks"

    DBU_RATES = {
        "jobs": 0.15,
        "all_purpose": 0.40,
        "sql_serverless": 0.55,
        "sql_classic": 0.22,
        "model_serving": 0.07,
        "dlt_core": 0.20,
        "dlt_pro": 0.25,
        "dlt_advanced": 0.36,
        "vector_search": 0.40,
    }

    def fetch_instance_pricing(self, region: str) -> Iterator[InstancePrice]:
        # DBU-based pricing doesn't map to instance types
        return iter([])

    def fetch_managed_service_pricing(self, service: str, region: str) -> list[ManagedServicePrice]:
        rates = []
        for compute_type, rate in self.DBU_RATES.items():
            rates.append(
                ManagedServicePrice(
                    service=service,
                    tier_name=compute_type,
                    price_per_hour=rate,
                    price_per_month=round(rate * 730, 2),
                    description=f"DBU rate for {compute_type}",
                )
            )
        return rates

    def supported_managed_services(self) -> list[str]:
        return [
            "databricks_sql_warehouse",
            "databricks_cluster",
            "databricks_job",
            "databricks_pipeline",
            "databricks_model_serving",
            "databricks_vector_search",
            "databricks_genie",
            "databricks_notebook",
            "databricks_dashboard",
        ]


class DatabricksWorkspaceAdapter:
    """Validates ArchSpec components against a live Databricks workspace.

    Requires databricks-sdk: pip install cloudwright-ai[databricks]
    """

    def __init__(self, host: str | None = None, token: str | None = None):
        try:
            from databricks.sdk import WorkspaceClient
        except ImportError:
            raise ImportError(
                "databricks-sdk is required for workspace validation. "
                "Install with: pip install cloudwright-ai[databricks]"
            )
        kwargs = {}
        if host:
            kwargs["host"] = host
        if token:
            kwargs["token"] = token
        self._client = WorkspaceClient(**kwargs)

    def validate_spec(self, spec) -> list[dict]:
        """Validate Databricks components against the workspace."""
        issues = []
        for comp in spec.components:
            if comp.provider != "databricks":
                continue
            try:
                if comp.service == "databricks_sql_warehouse":
                    self._validate_warehouse(comp, issues)
                elif comp.service == "databricks_unity_catalog":
                    self._validate_catalog(comp, issues)
                elif comp.service == "databricks_cluster":
                    self._validate_cluster(comp, issues)
            except Exception as e:
                issues.append(
                    {
                        "component": comp.id,
                        "service": comp.service,
                        "severity": "warning",
                        "message": f"Could not validate: {e}",
                    }
                )
        return issues

    def _validate_warehouse(self, comp, issues):
        warehouses = list(self._client.warehouses.list())
        if not warehouses:
            issues.append(
                {
                    "component": comp.id,
                    "service": comp.service,
                    "severity": "info",
                    "message": "No existing SQL warehouses found; one will be created",
                }
            )

    def _validate_catalog(self, comp, issues):
        catalogs = [c.name for c in self._client.catalogs.list()]
        if not catalogs:
            issues.append(
                {
                    "component": comp.id,
                    "service": comp.service,
                    "severity": "warning",
                    "message": "No Unity Catalog catalogs found; Unity Catalog may not be enabled",
                }
            )

    def _validate_cluster(self, comp, issues):
        clusters = list(self._client.clusters.list())
        running = [c for c in clusters if c.state and c.state.value == "RUNNING"]
        if running:
            issues.append(
                {
                    "component": comp.id,
                    "service": comp.service,
                    "severity": "info",
                    "message": f"{len(running)} cluster(s) currently running",
                }
            )

    def list_warehouses(self) -> list[dict]:
        return [{"id": w.id, "name": w.name, "state": str(w.state)} for w in self._client.warehouses.list()]

    def list_catalogs(self) -> list[str]:
        return [c.name for c in self._client.catalogs.list()]

    def list_schemas(self, catalog: str) -> list[str]:
        return [s.name for s in self._client.schemas.list(catalog_name=catalog)]
