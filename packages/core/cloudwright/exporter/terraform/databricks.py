"""Databricks resource HCL renderers.

User-controlled string fields (``c.id``, ``c.label``, region, metadata) are
emitted via :func:`_hcl_quote` so they cannot break out of their HCL string
literal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.terraform.common import _hcl_num, _hcl_quote

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
            f"  name         = {_hcl_quote(c.label)}",
            f"  cluster_size = {_hcl_quote(cfg.get('cluster_size', 'Small'))}",
            f"  auto_stop_mins = {_hcl_num(cfg.get('auto_stop_mins', 30), 30)}",
            "}",
        ]

    elif svc == "databricks_cluster":
        lines += [
            f'resource "databricks_cluster" "{c.id}" {{',
            f"  cluster_name            = {_hcl_quote(c.label)}",
            f"  spark_version           = {_hcl_quote(cfg.get('spark_version', '13.3.x-scala2.12'))}",
            f"  node_type_id            = {_hcl_quote(cfg.get('node_type_id', 'i3.xlarge'))}",
            f"  autotermination_minutes = {_hcl_num(cfg.get('autotermination_minutes', 60), 60)}",
            f"  num_workers             = {_hcl_num(cfg.get('num_workers', 2), 2)}",
            "}",
        ]

    elif svc == "databricks_job":
        lines += [
            f'resource "databricks_job" "{c.id}" {{',
            f"  name = {_hcl_quote(c.label)}",
            "  task {",
            f"    task_key = {_hcl_quote(c.id + '_task')}",
            "    notebook_task {",
            f"      notebook_path = {_hcl_quote(cfg.get('notebook_path', '/Shared/job_notebook'))}",
            "    }",
            "  }",
            "}",
        ]

    elif svc == "databricks_pipeline":
        lines += [
            f'resource "databricks_pipeline" "{c.id}" {{',
            f"  name    = {_hcl_quote(c.label)}",
            f"  target  = {_hcl_quote(cfg.get('target', 'default'))}",
            f"  channel = {_hcl_quote(cfg.get('channel', 'CURRENT'))}",
            "}",
        ]

    elif svc == "databricks_model_serving":
        lines += [
            f'resource "databricks_serving_endpoint" "{c.id}" {{',
            f"  name = {_hcl_quote(c.label)}",
            "  config {",
            "    served_models {",
            f"      name                  = {_hcl_quote(c.id + '_model')}",
            f"      model_name            = {_hcl_quote(cfg.get('model_name', 'my_model'))}",
            f"      model_version         = {_hcl_quote(cfg.get('model_version', '1'))}",
            f"      workload_size         = {_hcl_quote(cfg.get('workload_size', 'Small'))}",
            "      scale_to_zero_enabled = true",
            "    }",
            "  }",
            "}",
        ]

    elif svc == "databricks_unity_catalog":
        lines += [
            f'resource "databricks_catalog" "{c.id}" {{',
            f"  name    = {_hcl_quote(c.id)}",
            f"  comment = {_hcl_quote(cfg.get('comment', c.label))}",
            "}",
        ]

    elif svc == "databricks_vector_search":
        lines += [
            f'resource "databricks_vector_search_endpoint" "{c.id}" {{',
            f"  name          = {_hcl_quote(c.label)}",
            f"  endpoint_type = {_hcl_quote(cfg.get('endpoint_type', 'STANDARD'))}",
            "}",
        ]

    elif svc == "databricks_notebook":
        lines += [
            f'resource "databricks_notebook" "{c.id}" {{',
            f"  path           = {_hcl_quote(cfg.get('path', f'/Shared/{c.id}'))}",
            f"  language       = {_hcl_quote(cfg.get('language', 'PYTHON'))}",
            f"  content_base64 = {_hcl_quote(cfg.get('content_base64', ''))}",
            "}",
        ]

    elif svc == "databricks_secret_scope":
        lines += [
            f'resource "databricks_secret_scope" "{c.id}" {{',
            f"  name = {_hcl_quote(c.id)}",
            "}",
        ]

    elif svc == "databricks_volume":
        lines += [
            f'resource "databricks_volume" "{c.id}" {{',
            f"  name         = {_hcl_quote(c.label)}",
            f"  catalog_name = {_hcl_quote(cfg.get('catalog_name', 'main'))}",
            f"  schema_name  = {_hcl_quote(cfg.get('schema_name', 'default'))}",
            f"  volume_type  = {_hcl_quote(cfg.get('volume_type', 'MANAGED'))}",
            "}",
        ]

    elif svc == "databricks_dashboard":
        lines += [
            f'resource "databricks_sql_dashboard" "{c.id}" {{',
            f"  name = {_hcl_quote(c.label)}",
            "}",
        ]

    elif svc == "databricks_genie":
        lines += [
            f'resource "databricks_sql_query" "{c.id}" {{',
            f"  name  = {_hcl_quote(c.label)}",
            f"  query = {_hcl_quote(cfg.get('query', 'SELECT 1'))}",
            "}",
        ]

    else:
        safe_label = (c.label or "").replace("\n", " ").replace("\r", " ")
        lines += [
            f"# Unsupported Databricks service: {svc}",
            f"# component: {c.id} ({safe_label})",
        ]

    return "\n".join(lines)
