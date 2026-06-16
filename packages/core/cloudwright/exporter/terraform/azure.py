"""Azure resource HCL renderers.

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
    "virtual_machines": "azurerm_linux_virtual_machine",
    "azure_sql": "azurerm_mssql_server",
    "blob_storage": "azurerm_storage_account",
    "aks": "azurerm_kubernetes_cluster",
    "azure_functions": "azurerm_linux_function_app",
    "cosmos_db": "azurerm_cosmosdb_account",
    "azure_cache": "azurerm_redis_cache",
    "app_gateway": "azurerm_application_gateway",
    "service_bus": "azurerm_servicebus_namespace",
}

_RG = "azurerm_resource_group.main.name"
_LOCATION = "azurerm_resource_group.main.location"


def render_resource(c: "Component", spec: "ArchSpec") -> str:
    svc = c.service
    cfg = c.config
    lines: list[str] = []
    safe_id = c.id.replace("_", "-")

    if svc == "virtual_machines":
        lines += [
            f'resource "azurerm_network_interface" "{c.id}_nic" {{',
            f"  name                = {_hcl_quote(f'{safe_id}-nic')}",
            f"  location            = {_LOCATION}",
            f"  resource_group_name = {_RG}",
            "  ip_configuration {",
            '    name                          = "internal"',
            "    subnet_id                     = azurerm_subnet.main.id",
            '    private_ip_address_allocation = "Dynamic"',
            "  }",
            "}",
            "",
            f'resource "azurerm_linux_virtual_machine" "{c.id}" {{',
            f"  name                = {_hcl_quote(safe_id)}",
            f"  resource_group_name = {_RG}",
            f"  location            = {_LOCATION}",
            f"  size                = {_hcl_quote(cfg.get('size', 'Standard_B2s'))}",
            "  admin_username      = var.db_username",
            f"  network_interface_ids = [azurerm_network_interface.{c.id}_nic.id]",
            "  os_disk {",
            '    caching              = "ReadWrite"',
            '    storage_account_type = "Standard_LRS"',
            "  }",
            "  source_image_reference {",
            '    publisher = "Canonical"',
            '    offer     = "UbuntuServer"',
            '    sku       = "18.04-LTS"',
            '    version   = "latest"',
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "azure_sql":
        lines += [
            f'resource "azurerm_mssql_server" "{c.id}" {{',
            f"  name                         = {_hcl_quote(safe_id)}",
            f"  resource_group_name          = {_RG}",
            f"  location                     = {_LOCATION}",
            '  version                      = "12.0"',
            "  administrator_login          = var.db_username",
            "  administrator_login_password = var.db_password",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
            "",
            f'resource "azurerm_mssql_database" "{c.id}_db" {{',
            f"  name      = {_hcl_quote(c.id + '-db')}",
            f"  server_id = azurerm_mssql_server.{c.id}.id",
            f"  sku_name  = {_hcl_quote(cfg.get('sku_name', 'S0'))}",
            "}",
        ]

    elif svc == "blob_storage":
        # Storage account names: 3-24 lowercase alphanumeric.
        storage_name = c.id.replace("_", "")[:24]
        lines += [
            f'resource "azurerm_storage_account" "{c.id}" {{',
            f"  name                     = {_hcl_quote(storage_name)}",
            f"  resource_group_name      = {_RG}",
            f"  location                 = {_LOCATION}",
            '  account_tier             = "Standard"',
            '  account_replication_type = "LRS"',
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "aks":
        lines += [
            f'resource "azurerm_kubernetes_cluster" "{c.id}" {{',
            f"  name                = {_hcl_quote(safe_id)}",
            f"  location            = {_LOCATION}",
            f"  resource_group_name = {_RG}",
            f"  dns_prefix          = {_hcl_quote(safe_id)}",
            "  default_node_pool {",
            '    name       = "default"',
            f"    node_count = {_hcl_num(cfg.get('node_count', 1), 1)}",
            f"    vm_size    = {_hcl_quote(cfg.get('vm_size', 'Standard_D2_v2'))}",
            "  }",
            "  identity {",
            '    type = "SystemAssigned"',
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "azure_functions":
        storage_name = (c.id.replace("_", "")[:20] + "stor")[:24]
        plan_name = safe_id + "-plan"
        lines += [
            f'resource "azurerm_storage_account" "{c.id}_storage" {{',
            f"  name                     = {_hcl_quote(storage_name)}",
            f"  resource_group_name      = {_RG}",
            f"  location                 = {_LOCATION}",
            '  account_tier             = "Standard"',
            '  account_replication_type = "LRS"',
            "}",
            "",
            f'resource "azurerm_service_plan" "{c.id}_plan" {{',
            f"  name                = {_hcl_quote(plan_name)}",
            f"  resource_group_name = {_RG}",
            f"  location            = {_LOCATION}",
            '  os_type             = "Linux"',
            '  sku_name            = "Y1"',
            "}",
            "",
            f'resource "azurerm_linux_function_app" "{c.id}" {{',
            f"  name                = {_hcl_quote(safe_id)}",
            f"  resource_group_name = {_RG}",
            f"  location            = {_LOCATION}",
            f"  storage_account_name       = azurerm_storage_account.{c.id}_storage.name",
            f"  storage_account_access_key = azurerm_storage_account.{c.id}_storage.primary_access_key",
            f"  service_plan_id            = azurerm_service_plan.{c.id}_plan.id",
            "  site_config {}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "cosmos_db":
        lines += [
            f'resource "azurerm_cosmosdb_account" "{c.id}" {{',
            f"  name                = {_hcl_quote(safe_id)}",
            f"  location            = {_LOCATION}",
            f"  resource_group_name = {_RG}",
            '  offer_type          = "Standard"',
            f"  kind                = {_hcl_quote(cfg.get('kind', 'GlobalDocumentDB'))}",
            "  consistency_policy {",
            '    consistency_level = "Session"',
            "  }",
            "  geo_location {",
            f"    location          = {_LOCATION}",
            "    failover_priority = 0",
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "azure_cache":
        lines += [
            f'resource "azurerm_redis_cache" "{c.id}" {{',
            f"  name                = {_hcl_quote(safe_id)}",
            f"  location            = {_LOCATION}",
            f"  resource_group_name = {_RG}",
            f"  capacity            = {_hcl_num(cfg.get('capacity', 1), 1)}",
            '  family              = "C"',
            f"  sku_name            = {_hcl_quote(cfg.get('sku_name', 'Basic'))}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "app_gateway":
        lines += [
            f'resource "azurerm_application_gateway" "{c.id}" {{',
            f"  name                = {_hcl_quote(safe_id)}",
            f"  resource_group_name = {_RG}",
            f"  location            = {_LOCATION}",
            "  sku {",
            '    name     = "Standard_v2"',
            '    tier     = "Standard_v2"',
            "    capacity = 2",
            "  }",
            "  gateway_ip_configuration {",
            '    name      = "gateway-ip-config"',
            "    subnet_id = azurerm_subnet.main.id",
            "  }",
            "  frontend_port {",
            '    name = "frontend-port"',
            "    port = 80",
            "  }",
            "  frontend_ip_configuration {",
            '    name                 = "frontend-ip"',
            '    public_ip_address_id = "public_ip_id"',
            "  }",
            "  backend_address_pool {",
            '    name = "backend-pool"',
            "  }",
            "  backend_http_settings {",
            '    name                  = "backend-settings"',
            '    cookie_based_affinity = "Disabled"',
            "    port                  = 80",
            '    protocol              = "Http"',
            "    request_timeout       = 60",
            "  }",
            "  http_listener {",
            '    name                           = "listener"',
            '    frontend_ip_configuration_name = "frontend-ip"',
            '    frontend_port_name             = "frontend-port"',
            '    protocol                       = "Http"',
            "  }",
            "  request_routing_rule {",
            '    name                       = "routing-rule"',
            "    priority                   = 1",
            '    rule_type                  = "Basic"',
            '    http_listener_name         = "listener"',
            '    backend_address_pool_name  = "backend-pool"',
            '    backend_http_settings_name = "backend-settings"',
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "service_bus":
        lines += [
            f'resource "azurerm_servicebus_namespace" "{c.id}" {{',
            f"  name                = {_hcl_quote(safe_id)}",
            f"  location            = {_LOCATION}",
            f"  resource_group_name = {_RG}",
            f"  sku                 = {_hcl_quote(cfg.get('sku', 'Standard'))}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    else:
        safe_label = (c.label or "").replace("\n", " ").replace("\r", " ")
        lines += [
            f"# Unsupported Azure service: {svc}",
            f"# component: {c.id} ({safe_label})",
        ]

    return "\n".join(lines)
