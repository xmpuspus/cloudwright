"""GCP Pulumi Python renderers (uses ``pulumi_gcp``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.pulumi.common import _dns_name, _py_string, _safe_comment, _var_name

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
            f"{var} = gcp.compute.Instance(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            f"    machine_type={_py_string(machine_type)},",
            f"    zone={_py_string(zone)},",
            "    boot_disk=gcp.compute.InstanceBootDiskArgs(",
            "        initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(",
            '            image="debian-cloud/debian-11",',
            "        ),",
            "    ),",
            "    network_interfaces=[gcp.compute.InstanceNetworkInterfaceArgs(",
            '        network="default",',
            "    )],",
            f'    labels={{"name": {_py_string(_dns_name(label))}}},',
            ")",
        ]

    elif svc == "cloud_sql":
        db_version = cfg.get("database_version", "POSTGRES_15")
        tier = cfg.get("tier", "db-f1-micro")
        lines += [
            f"{var} = gcp.sql.DatabaseInstance(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            f"    database_version={_py_string(db_version)},",
            "    settings=gcp.sql.DatabaseInstanceSettingsArgs(",
            f"        tier={_py_string(tier)},",
            "    ),",
            "    deletion_protection=True,",
            ")",
        ]

    elif svc == "cloud_storage":
        location = cfg.get("location", "US")
        lines += [
            f"{var} = gcp.storage.Bucket(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            f"    location={_py_string(location)},",
            "    uniform_bucket_level_access=True,",
            '    public_access_prevention="enforced",',
            "    versioning=gcp.storage.BucketVersioningArgs(enabled=True),",
            f'    labels={{"name": {_py_string(_dns_name(label))}}},',
            ")",
        ]

    elif svc == "gke":
        location = cfg.get("location", "us-central1")
        machine_type = cfg.get("machine_type", "e2-medium")
        node_count = int(cfg.get("initial_node_count", 1))
        lines += [
            f"{var} = gcp.container.Cluster(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            f"    location={_py_string(location)},",
            f"    initial_node_count={node_count},",
            "    node_config=gcp.container.ClusterNodeConfigArgs(",
            f"        machine_type={_py_string(machine_type)},",
            "    ),",
            ")",
        ]

    elif svc == "cloud_run":
        location = cfg.get("location", "us-central1")
        image = cfg.get("image", "gcr.io/cloudrun/hello")
        lines += [
            f"{var} = gcp.cloudrunv2.Service(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            f"    location={_py_string(location)},",
            "    template=gcp.cloudrunv2.ServiceTemplateArgs(",
            "        containers=[gcp.cloudrunv2.ServiceTemplateContainerArgs(",
            f"            image={_py_string(image)},",
            "        )],",
            "    ),",
            ")",
        ]

    elif svc == "pub_sub":
        lines += [
            f"{var} = gcp.pubsub.Topic(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            f'    labels={{"name": {_py_string(_dns_name(label))}}},',
            ")",
        ]

    elif svc == "bigquery":
        location = cfg.get("location", "US")
        lines += [
            f"{var} = gcp.bigquery.Dataset(",
            f"    {_py_string(c.id)},",
            f"    dataset_id={_py_string(c.id)},",
            f"    location={_py_string(location)},",
            f'    labels={{"name": {_py_string(_dns_name(label))}}},',
            ")",
        ]

    else:
        lines += [
            f"# Unsupported GCP service: {svc}",
            f"# component: {c.id} ({_safe_comment(label)})",
        ]

    return "\n".join(lines)


def render_gcp_preamble(spec: "ArchSpec") -> list[str]:
    project = (spec.metadata or {}).get("gcp_project", "my-gcp-project")
    region = (spec.metadata or {}).get("gcp_region", spec.region)
    return [
        "import pulumi_gcp as gcp",
        "",
        f"gcp_project = {_py_string(project)}",
        f"gcp_region = {_py_string(region)}",
        "",
    ]
