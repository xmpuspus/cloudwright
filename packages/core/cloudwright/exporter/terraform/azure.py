"""Azure resource HCL renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

    if svc == "virtual_machines":
        lines += [
            f'resource "azurerm_network_interface" "{c.id}_nic" {{',
            f'  name                = "{c.id.replace("_", "-")}-nic"',
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
            f'  name                = "{c.id.replace("_", "-")}"',
            f"  resource_group_name = {_RG}",
            f"  location            = {_LOCATION}",
            f'  size                = "{cfg.get("size", "Standard_B2s")}"',
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
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "azure_sql":
        lines += [
            f'resource "azurerm_mssql_server" "{c.id}" {{',
            f'  name                         = "{c.id.replace("_", "-")}"',
            f"  resource_group_name          = {_RG}",
            f"  location                     = {_LOCATION}",
            '  version                      = "12.0"',
            "  administrator_login          = var.db_username",
            "  administrator_login_password = var.db_password",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
            "",
            f'resource "azurerm_mssql_database" "{c.id}_db" {{',
            f'  name      = "{c.id}-db"',
            f"  server_id = azurerm_mssql_server.{c.id}.id",
            f'  sku_name  = "{cfg.get("sku_name", "S0")}"',
            "}",
        ]

    elif svc == "blob_storage":
        lines += [
            f'resource "azurerm_storage_account" "{c.id}" {{',
            f'  name                     = "{c.id.replace("_", "")[:24]}"',
            f"  resource_group_name      = {_RG}",
            f"  location                 = {_LOCATION}",
            '  account_tier             = "Standard"',
            '  account_replication_type = "LRS"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "aks":
        lines += [
            f'resource "azurerm_kubernetes_cluster" "{c.id}" {{',
            f'  name                = "{c.id.replace("_", "-")}"',
            f"  location            = {_LOCATION}",
            f"  resource_group_name = {_RG}",
            f'  dns_prefix          = "{c.id.replace("_", "-")}"',
            "  default_node_pool {",
            '    name       = "default"',
            f"    node_count = {cfg.get('node_count', 1)}",
            f'    vm_size    = "{cfg.get("vm_size", "Standard_D2_v2")}"',
            "  }",
            "  identity {",
            '    type = "SystemAssigned"',
            "  }",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "azure_functions":
        storage_name = c.id.replace("_", "")[:20] + "stor"
        plan_name = c.id.replace("_", "-") + "-plan"
        lines += [
            f'resource "azurerm_storage_account" "{c.id}_storage" {{',
            f'  name                     = "{storage_name[:24]}"',
            f"  resource_group_name      = {_RG}",
            f"  location                 = {_LOCATION}",
            '  account_tier             = "Standard"',
            '  account_replication_type = "LRS"',
            "}",
            "",
            f'resource "azurerm_service_plan" "{c.id}_plan" {{',
            f'  name                = "{plan_name}"',
            f"  resource_group_name = {_RG}",
            f"  location            = {_LOCATION}",
            '  os_type             = "Linux"',
            '  sku_name            = "Y1"',
            "}",
            "",
            f'resource "azurerm_linux_function_app" "{c.id}" {{',
            f'  name                = "{c.id.replace("_", "-")}"',
            f"  resource_group_name = {_RG}",
            f"  location            = {_LOCATION}",
            f"  storage_account_name       = azurerm_storage_account.{c.id}_storage.name",
            f"  storage_account_access_key = azurerm_storage_account.{c.id}_storage.primary_access_key",
            f"  service_plan_id            = azurerm_service_plan.{c.id}_plan.id",
            "  site_config {}",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "cosmos_db":
        lines += [
            f'resource "azurerm_cosmosdb_account" "{c.id}" {{',
            f'  name                = "{c.id.replace("_", "-")}"',
            f"  location            = {_LOCATION}",
            f"  resource_group_name = {_RG}",
            '  offer_type          = "Standard"',
            f'  kind                = "{cfg.get("kind", "GlobalDocumentDB")}"',
            "  consistency_policy {",
            '    consistency_level = "Session"',
            "  }",
            "  geo_location {",
            f"    location          = {_LOCATION}",
            "    failover_priority = 0",
            "  }",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "azure_cache":
        lines += [
            f'resource "azurerm_redis_cache" "{c.id}" {{',
            f'  name                = "{c.id.replace("_", "-")}"',
            f"  location            = {_LOCATION}",
            f"  resource_group_name = {_RG}",
            f"  capacity            = {cfg.get('capacity', 1)}",
            '  family              = "C"',
            f'  sku_name            = "{cfg.get("sku_name", "Basic")}"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "app_gateway":
        lines += [
            f'resource "azurerm_application_gateway" "{c.id}" {{',
            f'  name                = "{c.id.replace("_", "-")}"',
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
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "service_bus":
        lines += [
            f'resource "azurerm_servicebus_namespace" "{c.id}" {{',
            f'  name                = "{c.id.replace("_", "-")}"',
            f"  location            = {_LOCATION}",
            f"  resource_group_name = {_RG}",
            f'  sku                 = "{cfg.get("sku", "Standard")}"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    else:
        lines += [
            f"# Unsupported Azure service: {svc}",
            f"# component: {c.id} ({c.label})",
        ]

    return "\n".join(lines)
