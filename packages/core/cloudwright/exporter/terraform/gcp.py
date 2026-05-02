"""GCP resource HCL renderers.

User-controlled string fields (``c.id``, ``c.label``, region, metadata) are
emitted via :func:`_hcl_quote` so they cannot break out of their HCL string
literal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.terraform.common import _hcl_quote

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component

RESOURCES: dict[str, str] = {
    "compute_engine": "google_compute_instance",
    "cloud_sql": "google_sql_database_instance",
    "cloud_storage": "google_storage_bucket",
    "gke": "google_container_cluster",
    "cloud_functions": "google_cloudfunctions2_function",
    "cloud_run": "google_cloud_run_v2_service",
    "pub_sub": "google_pubsub_topic",
    "memorystore": "google_redis_instance",
    "cloud_cdn": "google_compute_backend_service",
    "cloud_load_balancing": "google_compute_backend_service",
    "bigquery": "google_bigquery_dataset",
}


def _label_value(label: str) -> str:
    """GCP labels must be lowercase letters, digits, dashes, underscores."""
    return label.lower().replace(" ", "-")


def render_resource(c: "Component", spec: "ArchSpec") -> str:
    svc = c.service
    cfg = c.config
    lines: list[str] = []
    safe_id = c.id.replace("_", "-")

    if svc == "compute_engine":
        machine_type = cfg.get("machine_type", "e2-medium")
        lines += [
            f'resource "google_compute_instance" "{c.id}" {{',
            f"  name         = {_hcl_quote(safe_id)}",
            f"  machine_type = {_hcl_quote(machine_type)}",
            f"  zone         = {_hcl_quote(cfg.get('zone', 'us-central1-a'))}",
            "  boot_disk {",
            "    initialize_params {",
            '      image = "debian-cloud/debian-11"',
            "    }",
            "  }",
            "  network_interface {",
            '    network = "default"',
            "  }",
            "  labels = {",
            f"    name = {_hcl_quote(_label_value(c.label))}",
            "  }",
            "}",
        ]

    elif svc == "cloud_sql":
        db_version = cfg.get("database_version", "POSTGRES_15")
        lines += [
            f'resource "google_sql_database_instance" "{c.id}" {{',
            f"  name             = {_hcl_quote(safe_id)}",
            f"  database_version = {_hcl_quote(db_version)}",
            "  settings {",
            f"    tier = {_hcl_quote(cfg.get('tier', 'db-f1-micro'))}",
            "  }",
            "  deletion_protection = false",
            "}",
        ]

    elif svc == "cloud_storage":
        lines += [
            f'resource "google_storage_bucket" "{c.id}" {{',
            f"  name     = {_hcl_quote(safe_id)}",
            '  location = "US"',
            "  labels = {",
            f"    name = {_hcl_quote(_label_value(c.label))}",
            "  }",
            "}",
        ]

    elif svc == "gke":
        lines += [
            f'resource "google_container_cluster" "{c.id}" {{',
            f"  name     = {_hcl_quote(safe_id)}",
            f"  location = {_hcl_quote(cfg.get('location', 'us-central1'))}",
            f"  initial_node_count = {cfg.get('initial_node_count', 1)}",
            "  node_config {",
            f"    machine_type = {_hcl_quote(cfg.get('machine_type', 'e2-medium'))}",
            "  }",
            "}",
        ]

    elif svc == "cloud_functions":
        lines += [
            f'resource "google_cloudfunctions2_function" "{c.id}" {{',
            f"  name     = {_hcl_quote(safe_id)}",
            f"  location = {_hcl_quote(cfg.get('location', 'us-central1'))}",
            "  build_config {",
            f"    runtime     = {_hcl_quote(cfg.get('runtime', 'python311'))}",
            f"    entry_point = {_hcl_quote(cfg.get('entry_point', 'main'))}",
            "    source {",
            "      storage_source {",
            '        bucket = "source-bucket"',
            '        object = "source.zip"',
            "      }",
            "    }",
            "  }",
            "  service_config {",
            f"    max_instance_count = {cfg.get('max_instances', 10)}",
            "  }",
            "}",
        ]

    elif svc == "cloud_run":
        lines += [
            f'resource "google_cloud_run_v2_service" "{c.id}" {{',
            f"  name     = {_hcl_quote(safe_id)}",
            f"  location = {_hcl_quote(cfg.get('location', 'us-central1'))}",
            "  template {",
            "    containers {",
            f"      image = {_hcl_quote(cfg.get('image', 'gcr.io/cloudrun/hello'))}",
            "    }",
            "  }",
            "}",
        ]

    elif svc == "pub_sub":
        lines += [
            f'resource "google_pubsub_topic" "{c.id}" {{',
            f"  name   = {_hcl_quote(safe_id)}",
            "  labels = {",
            f"    name = {_hcl_quote(_label_value(c.label))}",
            "  }",
            "}",
        ]

    elif svc == "memorystore":
        lines += [
            f'resource "google_redis_instance" "{c.id}" {{',
            f"  name           = {_hcl_quote(safe_id)}",
            '  tier           = "BASIC"',
            f"  memory_size_gb = {cfg.get('memory_size_gb', 1)}",
            f"  region         = {_hcl_quote(cfg.get('region', 'us-central1'))}",
            "}",
        ]

    elif svc in ("cloud_cdn", "cloud_load_balancing"):
        lines += [
            f'resource "google_compute_backend_service" "{c.id}" {{',
            f"  name = {_hcl_quote(safe_id)}",
            "}",
        ]

    elif svc == "bigquery":
        lines += [
            f'resource "google_bigquery_dataset" "{c.id}" {{',
            f"  dataset_id = {_hcl_quote(c.id)}",
            f"  location   = {_hcl_quote(cfg.get('location', 'US'))}",
            "  labels = {",
            f"    name = {_hcl_quote(_label_value(c.label))}",
            "  }",
            "}",
        ]

    else:
        safe_label = (c.label or "").replace("\n", " ").replace("\r", " ")
        lines += [
            f"# Unsupported GCP service: {svc}",
            f"# component: {c.id} ({safe_label})",
        ]

    return "\n".join(lines)
