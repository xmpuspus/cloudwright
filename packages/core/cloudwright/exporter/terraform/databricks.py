"""Databricks resource HCL renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component

RESOURCES: dict[str, str] = {
    "databricks_sql_warehouse": "databricks_sql_endpoint",
    "databricks_cluster": "databricks_cluster",
    "databricks_job": "databricks_job",
    "databricks_pipeline": "databricks_pipeline",
    "databricks_model_serving": "databricks_serving_endpoint",
    "databricks_unity_catalog": "databricks_catalog",
    "databricks_vector_search": "databricks_vector_search_endpoint",
    "databricks_notebook": "databricks_notebook",
    "databricks_secret_scope": "databricks_secret_scope",
    "databricks_volume": "databricks_volume",
    "databricks_dashboard": "databricks_sql_dashboard",
    "databricks_genie": "databricks_sql_query",
}


def render_resource(c: "Component", spec: "ArchSpec") -> str:
    svc = c.service
    cfg = c.config
    lines: list[str] = []

    if svc == "databricks_sql_warehouse":
        lines += [
            f'resource "databricks_sql_endpoint" "{c.id}" {{',
            f'  name         = "{c.label}"',
            f'  cluster_size = "{cfg.get("cluster_size", "Small")}"',
            f"  auto_stop_mins = {cfg.get('auto_stop_mins', 30)}",
            "}",
        ]

    elif svc == "databricks_cluster":
        lines += [
            f'resource "databricks_cluster" "{c.id}" {{',
            f'  cluster_name            = "{c.label}"',
            f'  spark_version           = "{cfg.get("spark_version", "13.3.x-scala2.12")}"',
            f'  node_type_id            = "{cfg.get("node_type_id", "i3.xlarge")}"',
            f"  autotermination_minutes = {cfg.get('autotermination_minutes', 60)}",
            f"  num_workers             = {cfg.get('num_workers', 2)}",
            "}",
        ]

    elif svc == "databricks_job":
        lines += [
            f'resource "databricks_job" "{c.id}" {{',
            f'  name = "{c.label}"',
            "  task {",
            f'    task_key = "{c.id}_task"',
            "    notebook_task {",
            f'      notebook_path = "{cfg.get("notebook_path", "/Shared/job_notebook")}"',
            "    }",
            "  }",
            "}",
        ]

    elif svc == "databricks_pipeline":
        lines += [
            f'resource "databricks_pipeline" "{c.id}" {{',
            f'  name    = "{c.label}"',
            f'  target  = "{cfg.get("target", "default")}"',
            f'  channel = "{cfg.get("channel", "CURRENT")}"',
            "}",
        ]

    elif svc == "databricks_model_serving":
        lines += [
            f'resource "databricks_serving_endpoint" "{c.id}" {{',
            f'  name = "{c.label}"',
            "  config {",
            "    served_models {",
            f'      name                  = "{c.id}_model"',
            f'      model_name            = "{cfg.get("model_name", "my_model")}"',
            f'      model_version         = "{cfg.get("model_version", "1")}"',
            f'      workload_size         = "{cfg.get("workload_size", "Small")}"',
            "      scale_to_zero_enabled = true",
            "    }",
            "  }",
            "}",
        ]

    elif svc == "databricks_unity_catalog":
        lines += [
            f'resource "databricks_catalog" "{c.id}" {{',
            f'  name    = "{c.id}"',
            f'  comment = "{cfg.get("comment", c.label)}"',
            "}",
        ]

    elif svc == "databricks_vector_search":
        lines += [
            f'resource "databricks_vector_search_endpoint" "{c.id}" {{',
            f'  name          = "{c.label}"',
            f'  endpoint_type = "{cfg.get("endpoint_type", "STANDARD")}"',
            "}",
        ]

    elif svc == "databricks_notebook":
        lines += [
            f'resource "databricks_notebook" "{c.id}" {{',
            f'  path           = "{cfg.get("path", f"/Shared/{c.id}")}"',
            f'  language       = "{cfg.get("language", "PYTHON")}"',
            f'  content_base64 = "{cfg.get("content_base64", "")}"',
            "}",
        ]

    elif svc == "databricks_secret_scope":
        lines += [
            f'resource "databricks_secret_scope" "{c.id}" {{',
            f'  name = "{c.id}"',
            "}",
        ]

    elif svc == "databricks_volume":
        lines += [
            f'resource "databricks_volume" "{c.id}" {{',
            f'  name         = "{c.label}"',
            f'  catalog_name = "{cfg.get("catalog_name", "main")}"',
            f'  schema_name  = "{cfg.get("schema_name", "default")}"',
            f'  volume_type  = "{cfg.get("volume_type", "MANAGED")}"',
            "}",
        ]

    elif svc == "databricks_dashboard":
        lines += [
            f'resource "databricks_sql_dashboard" "{c.id}" {{',
            f'  name = "{c.label}"',
            "}",
        ]

    elif svc == "databricks_genie":
        lines += [
            f'resource "databricks_sql_query" "{c.id}" {{',
            f'  name  = "{c.label}"',
            f'  query = "{cfg.get("query", "SELECT 1")}"',
            "}",
        ]

    else:
        lines += [
            f"# Unsupported Databricks service: {svc}",
            f"# component: {c.id} ({c.label})",
        ]

    return "\n".join(lines)
