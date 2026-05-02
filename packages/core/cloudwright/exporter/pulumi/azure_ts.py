"""Azure Pulumi TypeScript renderers (uses ``@pulumi/azure-native``).

We default to the modern ``azure-native`` SDK rather than ``@pulumi/azure``
(classic) because azure-native is the path Microsoft and Pulumi recommend
for new projects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.pulumi.common import _dns_name, _safe_comment, _ts_string, _var_name

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
            f"const {var}Nic = new azure.network.NetworkInterface({_ts_string(c.id + '-nic')}, {{",
            "  resourceGroupName: resourceGroup.name,",
            "  location: resourceGroup.location,",
            "  ipConfigurations: [{",
            '    name: "internal",',
            "    subnet: { id: subnet.id },",
            '    privateIPAllocationMethod: "Dynamic",',
            "  }],",
            "});",
            "",
            f"const {var} = new azure.compute.VirtualMachine({_ts_string(c.id)}, {{",
            "  resourceGroupName: resourceGroup.name,",
            "  location: resourceGroup.location,",
            "  hardwareProfile: {",
            f"    vmSize: {_ts_string(size)},",
            "  },",
            "  osProfile: {",
            f"    computerName: {_ts_string(name)},",
            "    adminUsername: dbUsername,",
            "    adminPassword: dbPassword,",
            "  },",
            "  networkProfile: {",
            f"    networkInterfaces: [{{ id: {var}Nic.id }}],",
            "  },",
            "  storageProfile: {",
            "    imageReference: {",
            '      publisher: "Canonical",',
            '      offer: "UbuntuServer",',
            '      sku: "18.04-LTS",',
            '      version: "latest",',
            "    },",
            "    osDisk: {",
            '      caching: "ReadWrite",',
            '      createOption: "FromImage",',
            "    },",
            "  },",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "aks":
        node_count = int(cfg.get("node_count", 1))
        vm_size = cfg.get("vm_size", "Standard_D2_v2")
        lines += [
            f"const {var} = new azure.containerservice.ManagedCluster({_ts_string(c.id)}, {{",
            "  resourceGroupName: resourceGroup.name,",
            "  location: resourceGroup.location,",
            f"  dnsPrefix: {_ts_string(name)},",
            "  agentPoolProfiles: [{",
            '    name: "default",',
            f"    count: {node_count},",
            f"    vmSize: {_ts_string(vm_size)},",
            '    mode: "System",',
            "  }],",
            '  identity: { type: "SystemAssigned" },',
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "azure_sql":
        sku = cfg.get("sku_name", "S0")
        lines += [
            f"const {var}Server = new azure.sql.Server({_ts_string(c.id)}, {{",
            "  resourceGroupName: resourceGroup.name,",
            "  location: resourceGroup.location,",
            "  administratorLogin: dbUsername,",
            "  administratorLoginPassword: dbPassword,",
            '  version: "12.0",',
            '  minimalTlsVersion: "1.2",',
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
            "",
            f"const {var}Db = new azure.sql.Database({_ts_string(c.id + '-db')}, {{",
            "  resourceGroupName: resourceGroup.name,",
            "  location: resourceGroup.location,",
            f"  serverName: {var}Server.name,",
            "  sku: {",
            f"    name: {_ts_string(sku)},",
            "  },",
            "});",
        ]

    elif svc == "blob_storage":
        # Storage account names: 3-24 lowercase alphanumeric.
        storage_name = c.id.replace("_", "").replace("-", "")[:24].lower() or "stor"
        lines += [
            f"const {var} = new azure.storage.StorageAccount({_ts_string(c.id)}, {{",
            f"  accountName: {_ts_string(storage_name)},",
            "  resourceGroupName: resourceGroup.name,",
            "  location: resourceGroup.location,",
            '  kind: "StorageV2",',
            "  sku: {",
            '    name: "Standard_LRS",',
            "  },",
            '  minimumTlsVersion: "TLS1_2",',
            "  allowBlobPublicAccess: false,",
            "  enableHttpsTrafficOnly: true,",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "azure_functions":
        lines += [
            f"const {var}Plan = new azure.web.AppServicePlan({_ts_string(c.id + '-plan')}, {{",
            "  resourceGroupName: resourceGroup.name,",
            "  location: resourceGroup.location,",
            '  kind: "Linux",',
            "  reserved: true,",
            "  sku: {",
            '    name: "Y1",',
            '    tier: "Dynamic",',
            "  },",
            "});",
            "",
            f"const {var} = new azure.web.WebApp({_ts_string(c.id)}, {{",
            "  resourceGroupName: resourceGroup.name,",
            "  location: resourceGroup.location,",
            f"  serverFarmId: {var}Plan.id,",
            '  kind: "FunctionApp,linux",',
            "  httpsOnly: true,",
            "  siteConfig: {",
            '    linuxFxVersion: "PYTHON|3.11",',
            '    minTlsVersion: "1.2",',
            "  },",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "app_gateway":
        lines += [
            f"const {var} = new azure.network.ApplicationGateway({_ts_string(c.id)}, {{",
            "  resourceGroupName: resourceGroup.name,",
            "  location: resourceGroup.location,",
            "  sku: {",
            '    name: "Standard_v2",',
            '    tier: "Standard_v2",',
            "    capacity: 2,",
            "  },",
            "  gatewayIPConfigurations: [{",
            '    name: "gateway-ip-config",',
            "    subnet: { id: subnet.id },",
            "  }],",
            "  frontendPorts: [{",
            '    name: "frontend-port",',
            "    port: 80,",
            "  }],",
            "  backendAddressPools: [{",
            '    name: "backend-pool",',
            "  }],",
            "  backendHttpSettingsCollection: [{",
            '    name: "backend-settings",',
            '    cookieBasedAffinity: "Disabled",',
            "    port: 80,",
            '    protocol: "Http",',
            "    requestTimeout: 60,",
            "  }],",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    else:
        lines += [
            f"// Unsupported Azure service: {svc}",
            f"// component: {c.id} ({_safe_comment(label)})",
        ]

    return "\n".join(lines)


def render_azure_preamble() -> list[str]:
    return [
        'import * as azure from "@pulumi/azure-native";',
        "",
        'const resourceGroup = new azure.resources.ResourceGroup("rg-cloudwright", {',
        '  location: "eastus",',
        "});",
        "",
        'const vnet = new azure.network.VirtualNetwork("vnet-cloudwright", {',
        "  resourceGroupName: resourceGroup.name,",
        "  location: resourceGroup.location,",
        "  addressSpace: {",
        '    addressPrefixes: ["10.0.0.0/16"],',
        "  },",
        "});",
        "",
        'const subnet = new azure.network.Subnet("subnet-cloudwright", {',
        "  resourceGroupName: resourceGroup.name,",
        "  virtualNetworkName: vnet.name,",
        '  addressPrefix: "10.0.1.0/24",',
        "});",
        "",
        'import * as pulumi from "@pulumi/pulumi";',
        "const azureConfig = new pulumi.Config();",
        'const dbUsername = azureConfig.get("dbUsername") ?? "cloudwright_admin";',
        'const dbPassword = azureConfig.requireSecret("dbPassword");',
        "",
    ]
