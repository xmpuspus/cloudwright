"""GCP Pulumi TypeScript renderers (uses ``@pulumi/gcp``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.pulumi.common import _dns_name, _safe_comment, _ts_string, _var_name

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component


SUPPORTED: set[str] = {
    "compute_engine",
    "gke",
    "cloud_sql",
    "cloud_storage",
    "cloud_run",
    "pub_sub",
    "bigquery",
}


def render_resource(c: "Component", spec: "ArchSpec") -> str:
    svc = c.service
    cfg = c.config
    var = _var_name(c.id)
    name = _dns_name(c.id)
    label = c.label or c.id
    lines: list[str] = []

    if svc == "compute_engine":
        machine_type = cfg.get("machine_type", "e2-medium")
        zone = cfg.get("zone", "us-central1-a")
        lines += [
            f"const {var} = new gcp.compute.Instance({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            f"  machineType: {_ts_string(machine_type)},",
            f"  zone: {_ts_string(zone)},",
            "  bootDisk: {",
            "    initializeParams: {",
            '      image: "debian-cloud/debian-11",',
            "    },",
            "  },",
            "  networkInterfaces: [{",
            '    network: "default",',
            "  }],",
            "  labels: {",
            f"    name: {_ts_string(_dns_name(label))},",
            "  },",
            "});",
        ]

    elif svc == "cloud_sql":
        db_version = cfg.get("database_version", "POSTGRES_15")
        tier = cfg.get("tier", "db-f1-micro")
        lines += [
            f"const {var} = new gcp.sql.DatabaseInstance({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            f"  databaseVersion: {_ts_string(db_version)},",
            "  settings: {",
            f"    tier: {_ts_string(tier)},",
            "  },",
            "  deletionProtection: true,",
            "});",
        ]

    elif svc == "cloud_storage":
        location = cfg.get("location", "US")
        lines += [
            f"const {var} = new gcp.storage.Bucket({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            f"  location: {_ts_string(location)},",
            "  uniformBucketLevelAccess: true,",
            '  publicAccessPrevention: "enforced",',
            "  versioning: { enabled: true },",
            "  labels: {",
            f"    name: {_ts_string(_dns_name(label))},",
            "  },",
            "});",
        ]

    elif svc == "gke":
        location = cfg.get("location", "us-central1")
        machine_type = cfg.get("machine_type", "e2-medium")
        node_count = int(cfg.get("initial_node_count", 1))
        lines += [
            f"const {var} = new gcp.container.Cluster({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            f"  location: {_ts_string(location)},",
            f"  initialNodeCount: {node_count},",
            "  nodeConfig: {",
            f"    machineType: {_ts_string(machine_type)},",
            "  },",
            "});",
        ]

    elif svc == "cloud_run":
        location = cfg.get("location", "us-central1")
        image = cfg.get("image", "gcr.io/cloudrun/hello")
        lines += [
            f"const {var} = new gcp.cloudrunv2.Service({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            f"  location: {_ts_string(location)},",
            "  template: {",
            "    containers: [{",
            f"      image: {_ts_string(image)},",
            "    }],",
            "  },",
            "});",
        ]

    elif svc == "pub_sub":
        lines += [
            f"const {var} = new gcp.pubsub.Topic({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            "  labels: {",
            f"    name: {_ts_string(_dns_name(label))},",
            "  },",
            "});",
        ]

    elif svc == "bigquery":
        location = cfg.get("location", "US")
        lines += [
            f"const {var} = new gcp.bigquery.Dataset({_ts_string(c.id)}, {{",
            f"  datasetId: {_ts_string(c.id)},",
            f"  location: {_ts_string(location)},",
            "  labels: {",
            f"    name: {_ts_string(_dns_name(label))},",
            "  },",
            "});",
        ]

    else:
        lines += [
            f"// Unsupported GCP service: {svc}",
            f"// component: {c.id} ({_safe_comment(label)})",
        ]

    return "\n".join(lines)


def render_gcp_preamble(spec: "ArchSpec") -> list[str]:
    project = (spec.metadata or {}).get("gcp_project", "my-gcp-project")
    region = (spec.metadata or {}).get("gcp_region", spec.region)
    return [
        'import * as gcp from "@pulumi/gcp";',
        "",
        f"const gcpProject = {_ts_string(project)};",
        f"const gcpRegion = {_ts_string(region)};",
        "",
    ]
