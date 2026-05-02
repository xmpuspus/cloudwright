"""Azure Pulumi Python renderers (uses ``pulumi_azure_native``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.pulumi.common import _dns_name, _py_string, _safe_comment, _var_name

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component


SUPPORTED: set[str] = {
    "virtual_machines",
    "aks",
    "azure_sql",
    "blob_storage",
    "azure_functions",
    "app_gateway",
}


def render_resource(c: "Component", spec: "ArchSpec") -> str:
    svc = c.service
    cfg = c.config
    var = _var_name(c.id)
    name = _dns_name(c.id)
    label = c.label or c.id
    lines: list[str] = []

    if svc == "virtual_machines":
        size = cfg.get("size", "Standard_B2s")
        lines += [
            f"{var}_nic = azure_native.network.NetworkInterface(",
            f"    {_py_string(c.id + '-nic')},",
            "    resource_group_name=resource_group.name,",
            "    location=resource_group.location,",
            "    ip_configurations=[azure_native.network.NetworkInterfaceIPConfigurationArgs(",
            '        name="internal",',
            "        subnet=azure_native.network.SubnetArgs(id=subnet.id),",
            '        private_ip_allocation_method="Dynamic",',
            "    )],",
            ")",
            "",
            f"{var} = azure_native.compute.VirtualMachine(",
            f"    {_py_string(c.id)},",
            "    resource_group_name=resource_group.name,",
            "    location=resource_group.location,",
            "    hardware_profile=azure_native.compute.HardwareProfileArgs(",
            f"        vm_size={_py_string(size)},",
            "    ),",
            "    os_profile=azure_native.compute.OSProfileArgs(",
            f"        computer_name={_py_string(name)},",
            "        admin_username=db_username,",
            "        admin_password=db_password,",
            "    ),",
            "    network_profile=azure_native.compute.NetworkProfileArgs(",
            "        network_interfaces=[azure_native.compute.NetworkInterfaceReferenceArgs(",
            f"            id={var}_nic.id,",
            "        )],",
            "    ),",
            "    storage_profile=azure_native.compute.StorageProfileArgs(",
            "        image_reference=azure_native.compute.ImageReferenceArgs(",
            '            publisher="Canonical",',
            '            offer="UbuntuServer",',
            '            sku="18.04-LTS",',
            '            version="latest",',
            "        ),",
            "        os_disk=azure_native.compute.OSDiskArgs(",
            '            caching="ReadWrite",',
            '            create_option="FromImage",',
            "        ),",
            "    ),",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "aks":
        node_count = int(cfg.get("node_count", 1))
        vm_size = cfg.get("vm_size", "Standard_D2_v2")
        lines += [
            f"{var} = azure_native.containerservice.ManagedCluster(",
            f"    {_py_string(c.id)},",
            "    resource_group_name=resource_group.name,",
            "    location=resource_group.location,",
            f"    dns_prefix={_py_string(name)},",
            "    agent_pool_profiles=[azure_native.containerservice.ManagedClusterAgentPoolProfileArgs(",
            '        name="default",',
            f"        count={node_count},",
            f"        vm_size={_py_string(vm_size)},",
            '        mode="System",',
            "    )],",
            '    identity=azure_native.containerservice.ManagedClusterIdentityArgs(type="SystemAssigned"),',
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "azure_sql":
        sku = cfg.get("sku_name", "S0")
        lines += [
            f"{var}_server = azure_native.sql.Server(",
            f"    {_py_string(c.id)},",
            "    resource_group_name=resource_group.name,",
            "    location=resource_group.location,",
            "    administrator_login=db_username,",
            "    administrator_login_password=db_password,",
            '    version="12.0",',
            '    minimal_tls_version="1.2",',
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
            "",
            f"{var}_db = azure_native.sql.Database(",
            f"    {_py_string(c.id + '-db')},",
            "    resource_group_name=resource_group.name,",
            "    location=resource_group.location,",
            f"    server_name={var}_server.name,",
            "    sku=azure_native.sql.SkuArgs(",
            f"        name={_py_string(sku)},",
            "    ),",
            ")",
        ]

    elif svc == "blob_storage":
        storage_name = c.id.replace("_", "").replace("-", "")[:24].lower() or "stor"
        lines += [
            f"{var} = azure_native.storage.StorageAccount(",
            f"    {_py_string(c.id)},",
            f"    account_name={_py_string(storage_name)},",
            "    resource_group_name=resource_group.name,",
            "    location=resource_group.location,",
            '    kind="StorageV2",',
            "    sku=azure_native.storage.SkuArgs(",
            '        name="Standard_LRS",',
            "    ),",
            '    minimum_tls_version="TLS1_2",',
            "    allow_blob_public_access=False,",
            "    enable_https_traffic_only=True,",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "azure_functions":
        lines += [
            f"{var}_plan = azure_native.web.AppServicePlan(",
            f"    {_py_string(c.id + '-plan')},",
            "    resource_group_name=resource_group.name,",
            "    location=resource_group.location,",
            '    kind="Linux",',
            "    reserved=True,",
            "    sku=azure_native.web.SkuDescriptionArgs(",
            '        name="Y1",',
            '        tier="Dynamic",',
            "    ),",
            ")",
            "",
            f"{var} = azure_native.web.WebApp(",
            f"    {_py_string(c.id)},",
            "    resource_group_name=resource_group.name,",
            "    location=resource_group.location,",
            f"    server_farm_id={var}_plan.id,",
            '    kind="FunctionApp,linux",',
            "    https_only=True,",
            "    site_config=azure_native.web.SiteConfigArgs(",
            '        linux_fx_version="PYTHON|3.11",',
            '        min_tls_version="1.2",',
            "    ),",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "app_gateway":
        lines += [
            f"{var} = azure_native.network.ApplicationGateway(",
            f"    {_py_string(c.id)},",
            "    resource_group_name=resource_group.name,",
            "    location=resource_group.location,",
            "    sku=azure_native.network.ApplicationGatewaySkuArgs(",
            '        name="Standard_v2",',
            '        tier="Standard_v2",',
            "        capacity=2,",
            "    ),",
            "    gateway_ip_configurations=[azure_native.network.ApplicationGatewayIPConfigurationArgs(",
            '        name="gateway-ip-config",',
            "        subnet=azure_native.network.SubResourceArgs(id=subnet.id),",
            "    )],",
            "    frontend_ports=[azure_native.network.ApplicationGatewayFrontendPortArgs(",
            '        name="frontend-port",',
            "        port=80,",
            "    )],",
            "    backend_address_pools=[azure_native.network.ApplicationGatewayBackendAddressPoolArgs(",
            '        name="backend-pool",',
            "    )],",
            "    backend_http_settings_collection=[azure_native.network.ApplicationGatewayBackendHttpSettingsArgs(",
            '        name="backend-settings",',
            '        cookie_based_affinity="Disabled",',
            "        port=80,",
            '        protocol="Http",',
            "        request_timeout=60,",
            "    )],",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    else:
        lines += [
            f"# Unsupported Azure service: {svc}",
            f"# component: {c.id} ({_safe_comment(label)})",
        ]

    return "\n".join(lines)


def render_azure_preamble() -> list[str]:
    return [
        "import pulumi",
        "import pulumi_azure_native as azure_native",
        "",
        'resource_group = azure_native.resources.ResourceGroup("rg-cloudwright", location="eastus")',
        "",
        "vnet = azure_native.network.VirtualNetwork(",
        '    "vnet-cloudwright",',
        "    resource_group_name=resource_group.name,",
        "    location=resource_group.location,",
        '    address_space=azure_native.network.AddressSpaceArgs(address_prefixes=["10.0.0.0/16"]),',
        ")",
        "",
        "subnet = azure_native.network.Subnet(",
        '    "subnet-cloudwright",',
        "    resource_group_name=resource_group.name,",
        "    virtual_network_name=vnet.name,",
        '    address_prefix="10.0.1.0/24",',
        ")",
        "",
        "azure_config = pulumi.Config()",
        'db_username = azure_config.get("dbUsername") or "cloudwright_admin"',
        'db_password = azure_config.require_secret("dbPassword")',
        "",
    ]
