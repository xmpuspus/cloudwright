"""Terraform HCL exporter for ArchSpec."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component

_AWS_RESOURCES: dict[str, str] = {
    "ec2": "aws_instance",
    "rds": "aws_db_instance",
    "s3": "aws_s3_bucket",
    "alb": "aws_lb",
    "nlb": "aws_lb",
    "cloudfront": "aws_cloudfront_distribution",
    "lambda": "aws_lambda_function",
    "elasticache": "aws_elasticache_cluster",
    "dynamodb": "aws_dynamodb_table",
    "sqs": "aws_sqs_queue",
    "sns": "aws_sns_topic",
    "waf": "aws_wafv2_web_acl",
    "route53": "aws_route53_zone",
    "api_gateway": "aws_api_gateway_rest_api",
    "ecs": "aws_ecs_cluster",
    "eks": "aws_eks_cluster",
    "cognito": "aws_cognito_user_pool",
}

_GCP_RESOURCES: dict[str, str] = {
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

_AZURE_RESOURCES: dict[str, str] = {
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

_PROVIDER_REGISTRY: dict[str, dict[str, str]] = {
    "aws": _AWS_RESOURCES,
    "gcp": _GCP_RESOURCES,
    "azure": _AZURE_RESOURCES,
}

_REQUIRED_PROVIDERS: dict[str, dict] = {
    "aws": {
        "source": "hashicorp/aws",
        "version": "= 5.82.2",
    },
    "gcp": {
        "source": "hashicorp/google",
        "version": "= 6.14.1",
    },
    "azure": {
        "source": "hashicorp/azurerm",
        "version": "= 4.14.0",
    },
}


def _hcl_str(value: str) -> str:
    return f'"{value}"'


def _render_aws_resource(c: "Component") -> str:
    svc = c.service
    cfg = c.config
    lines: list[str] = []

    if svc == "ec2":
        instance_type = cfg.get("instance_type", "t3.medium")
        lines += [
            f'resource "aws_instance" "{c.id}" {{',
            "  ami           = data.aws_ssm_parameter.amazon_linux.value",
            f'  instance_type = "{instance_type}"',
            "  subnet_id     = tolist(data.aws_subnets.default.ids)[0]",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "rds":
        engine = cfg.get("engine", "mysql")
        instance_class = cfg.get("instance_class", "db.t3.medium")
        lines += [
            f'resource "aws_db_instance" "{c.id}" {{',
            f'  identifier        = "{c.id}"',
            f'  engine            = "{engine}"',
            f'  instance_class    = "{instance_class}"',
            f"  allocated_storage = {cfg.get('allocated_storage', 20)}",
            '  username          = "admin"',
            "  password          = var.db_password",
            "  skip_final_snapshot = true",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "s3":
        lines += [
            f'resource "aws_s3_bucket" "{c.id}" {{',
            f'  bucket = "{c.id.replace("_", "-")}"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc in ("alb", "nlb"):
        lb_type = "application" if svc == "alb" else "network"
        lines += [
            f'resource "aws_lb" "{c.id}" {{',
            f'  name               = "{c.id.replace("_", "-")}"',
            "  internal           = false",
            f'  load_balancer_type = "{lb_type}"',
            "  subnets            = data.aws_subnets.default.ids",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "cloudfront":
        lines += [
            f'resource "aws_cloudfront_distribution" "{c.id}" {{',
            "  enabled = true",
            "  origin {",
            "    domain_name = var.cloudfront_origin_domain",
            f'    origin_id   = "{c.id}-origin"',
            "  }",
            "  default_cache_behavior {",
            '    allowed_methods  = ["GET", "HEAD"]',
            '    cached_methods   = ["GET", "HEAD"]',
            f'    target_origin_id = "{c.id}-origin"',
            '    viewer_protocol_policy = "redirect-to-https"',
            "    forwarded_values {",
            "      query_string = false",
            '      cookies { forward = "none" }',
            "    }",
            "  }",
            "  restrictions {",
            '    geo_restriction { restriction_type = "none" }',
            "  }",
            "  viewer_certificate {",
            "    cloudfront_default_certificate = true",
            "  }",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "lambda":
        runtime = cfg.get("runtime", "python3.11")
        lines += [
            f'resource "aws_lambda_function" "{c.id}" {{',
            f'  function_name = "{c.id}"',
            "  role          = var.lambda_role_arn",
            '  handler       = "index.handler"',
            f'  runtime       = "{runtime}"',
            '  filename      = "lambda.zip"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "elasticache":
        engine = cfg.get("engine", "redis")
        node_type = cfg.get("node_type", "cache.t3.medium")
        lines += [
            f'resource "aws_elasticache_cluster" "{c.id}" {{',
            f'  cluster_id           = "{c.id.replace("_", "-")}"',
            f'  engine               = "{engine}"',
            f'  node_type            = "{node_type}"',
            f"  num_cache_nodes      = {cfg.get('num_cache_nodes', 1)}",
            f'  parameter_group_name = "default.{engine}7"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "dynamodb":
        lines += [
            f'resource "aws_dynamodb_table" "{c.id}" {{',
            f'  name         = "{c.id}"',
            f'  billing_mode = "{cfg.get("billing_mode", "PAY_PER_REQUEST")}"',
            f'  hash_key     = "{cfg.get("hash_key", "id")}"',
            "  attribute {",
            f'    name = "{cfg.get("hash_key", "id")}"',
            '    type = "S"',
            "  }",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "sqs":
        lines += [
            f'resource "aws_sqs_queue" "{c.id}" {{',
            f'  name = "{c.id.replace("_", "-")}"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "sns":
        lines += [
            f'resource "aws_sns_topic" "{c.id}" {{',
            f'  name = "{c.id.replace("_", "-")}"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "waf":
        lines += [
            f'resource "aws_wafv2_web_acl" "{c.id}" {{',
            f'  name  = "{c.id}"',
            '  scope = "REGIONAL"',
            "  default_action { allow {} }",
            "  visibility_config {",
            "    cloudwatch_metrics_enabled = true",
            f'    metric_name                = "{c.id}"',
            "    sampled_requests_enabled   = true",
            "  }",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "route53":
        lines += [
            f'resource "aws_route53_zone" "{c.id}" {{',
            f'  name = "{cfg.get("domain", "example.com")}"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "api_gateway":
        lines += [
            f'resource "aws_api_gateway_rest_api" "{c.id}" {{',
            f'  name = "{c.label}"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "ecs":
        launch_type = cfg.get("launch_type", "FARGATE")
        svc_lines = [
            f'resource "aws_ecs_cluster" "{c.id}" {{',
            f'  name = "{c.id.replace("_", "-")}"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
            "",
            f'resource "aws_ecs_service" "{c.id}_service" {{',
            f'  name            = "{c.id}-service"',
            f"  cluster         = aws_ecs_cluster.{c.id}.id",
            f"  desired_count   = {cfg.get('desired_count', 1)}",
            f'  launch_type     = "{launch_type}"',
            "  task_definition = var.task_definition_arn",
        ]
        if launch_type == "FARGATE":
            svc_lines += [
                "  network_configuration {",
                "    subnets = data.aws_subnets.default.ids",
                "  }",
            ]
        svc_lines.append("}")
        lines += svc_lines

    elif svc == "eks":
        lines += [
            f'resource "aws_eks_cluster" "{c.id}" {{',
            f'  name     = "{c.id.replace("_", "-")}"',
            "  role_arn = var.eks_role_arn",
            "  vpc_config {",
            "    subnet_ids = data.aws_subnets.default.ids",
            "  }",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "cognito":
        lines += [
            f'resource "aws_cognito_user_pool" "{c.id}" {{',
            f'  name = "{c.id.replace("_", "-")}"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "kms":
        lines += [
            f'resource "aws_kms_key" "{c.id}" {{',
            f'  description             = "{c.label}"',
            "  enable_key_rotation     = true",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "cloudtrail":
        lines += [
            f'resource "aws_cloudtrail" "{c.id}" {{',
            f'  name                  = "{c.id.replace("_", "-")}"',
            "  s3_bucket_name        = var.trail_bucket",
            "  is_multi_region_trail = true",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "guardduty":
        lines += [
            f'resource "aws_guardduty_detector" "{c.id}" {{',
            "  enable = true",
            "}",
        ]

    elif svc == "kinesis":
        lines += [
            f'resource "aws_kinesis_stream" "{c.id}" {{',
            f'  name        = "{c.id.replace("_", "-")}"',
            f"  shard_count = {cfg.get('shard_count', 2)}",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "ecr":
        lines += [
            f'resource "aws_ecr_repository" "{c.id}" {{',
            f'  name                 = "{c.id.replace("_", "-")}"',
            '  image_tag_mutability = "MUTABLE"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "cloudwatch":
        lines += [
            f'resource "aws_cloudwatch_log_group" "{c.id}" {{',
            f'  name              = "/cloudwright/{c.id}"',
            "  retention_in_days = 30",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "ebs":
        lines += [
            f'resource "aws_ebs_volume" "{c.id}" {{',
            "  availability_zone = data.aws_availability_zones.available.names[0]",
            f"  size              = {cfg.get('size', 100)}",
            '  type              = "gp3"',
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    elif svc == "codepipeline":
        lines += [
            f'resource "aws_codepipeline" "{c.id}" {{',
            f'  name     = "{c.id.replace("_", "-")}"',
            "  role_arn = var.codepipeline_role_arn",
            "  artifact_store {",
            '    type     = "S3"',
            "    location = var.artifact_bucket",
            "  }",
            "  stage {",
            '    name = "Source"',
            "    action {",
            '      name             = "Source"',
            '      category         = "Source"',
            '      owner            = "AWS"',
            '      provider         = "CodeStarSourceConnection"',
            '      version          = "1"',
            '      output_artifacts = ["source_output"]',
            "      configuration = {",
            "        ConnectionArn    = var.codestar_connection_arn",
            '        FullRepositoryId = "org/repo"',
            '        BranchName       = "main"',
            "      }",
            "    }",
            "  }",
            "  stage {",
            '    name = "Deploy"',
            "    action {",
            '      name            = "Deploy"',
            '      category        = "Deploy"',
            '      owner           = "AWS"',
            '      provider        = "ECS"',
            '      version         = "1"',
            '      input_artifacts = ["source_output"]',
            "    }",
            "  }",
            "  tags = {",
            f'    Name = "{c.label}"',
            "  }",
            "}",
        ]

    else:
        # Generic fallback with a comment
        lines += [
            f"# Unsupported AWS service: {svc}",
            f"# component: {c.id} ({c.label})",
        ]

    return "\n".join(lines)


def _render_gcp_resource(c: "Component") -> str:
    svc = c.service
    cfg = c.config
    lines: list[str] = []

    if svc == "compute_engine":
        machine_type = cfg.get("machine_type", "e2-medium")
        lines += [
            f'resource "google_compute_instance" "{c.id}" {{',
            f'  name         = "{c.id.replace("_", "-")}"',
            f'  machine_type = "{machine_type}"',
            f'  zone         = "{cfg.get("zone", "us-central1-a")}"',
            "  boot_disk {",
            "    initialize_params {",
            '      image = "debian-cloud/debian-11"',
            "    }",
            "  }",
            "  network_interface {",
            '    network = "default"',
            "  }",
            "  labels = {",
            f'    name = "{c.label.lower().replace(" ", "-")}"',
            "  }",
            "}",
        ]

    elif svc == "cloud_sql":
        db_version = cfg.get("database_version", "POSTGRES_15")
        lines += [
            f'resource "google_sql_database_instance" "{c.id}" {{',
            f'  name             = "{c.id.replace("_", "-")}"',
            f'  database_version = "{db_version}"',
            "  settings {",
            f'    tier = "{cfg.get("tier", "db-f1-micro")}"',
            "  }",
            "  deletion_protection = false",
            "}",
        ]

    elif svc == "cloud_storage":
        lines += [
            f'resource "google_storage_bucket" "{c.id}" {{',
            f'  name     = "{c.id.replace("_", "-")}"',
            '  location = "US"',
            "  labels = {",
            f'    name = "{c.label.lower().replace(" ", "-")}"',
            "  }",
            "}",
        ]

    elif svc == "gke":
        lines += [
            f'resource "google_container_cluster" "{c.id}" {{',
            f'  name     = "{c.id.replace("_", "-")}"',
            f'  location = "{cfg.get("location", "us-central1")}"',
            f"  initial_node_count = {cfg.get('initial_node_count', 1)}",
            "  node_config {",
            f'    machine_type = "{cfg.get("machine_type", "e2-medium")}"',
            "  }",
            "}",
        ]

    elif svc == "cloud_functions":
        lines += [
            f'resource "google_cloudfunctions2_function" "{c.id}" {{',
            f'  name     = "{c.id.replace("_", "-")}"',
            f'  location = "{cfg.get("location", "us-central1")}"',
            "  build_config {",
            f'    runtime     = "{cfg.get("runtime", "python311")}"',
            f'    entry_point = "{cfg.get("entry_point", "main")}"',
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
            f'  name     = "{c.id.replace("_", "-")}"',
            f'  location = "{cfg.get("location", "us-central1")}"',
            "  template {",
            "    containers {",
            f'      image = "{cfg.get("image", "gcr.io/cloudrun/hello")}"',
            "    }",
            "  }",
            "}",
        ]

    elif svc == "pub_sub":
        lines += [
            f'resource "google_pubsub_topic" "{c.id}" {{',
            f'  name   = "{c.id.replace("_", "-")}"',
            "  labels = {",
            f'    name = "{c.label.lower().replace(" ", "-")}"',
            "  }",
            "}",
        ]

    elif svc == "memorystore":
        lines += [
            f'resource "google_redis_instance" "{c.id}" {{',
            f'  name           = "{c.id.replace("_", "-")}"',
            '  tier           = "BASIC"',
            f"  memory_size_gb = {cfg.get('memory_size_gb', 1)}",
            f'  region         = "{cfg.get("region", "us-central1")}"',
            "}",
        ]

    elif svc in ("cloud_cdn", "cloud_load_balancing"):
        lines += [
            f'resource "google_compute_backend_service" "{c.id}" {{',
            f'  name = "{c.id.replace("_", "-")}"',
            "}",
        ]

    elif svc == "bigquery":
        lines += [
            f'resource "google_bigquery_dataset" "{c.id}" {{',
            f'  dataset_id = "{c.id}"',
            f'  location   = "{cfg.get("location", "US")}"',
            "  labels = {",
            f'    name = "{c.label.lower().replace(" ", "-")}"',
            "  }",
            "}",
        ]

    else:
        lines += [
            f"# Unsupported GCP service: {svc}",
            f"# component: {c.id} ({c.label})",
        ]

    return "\n".join(lines)


def _render_azure_resource(c: "Component") -> str:
    svc = c.service
    cfg = c.config
    rg = "azurerm_resource_group.main.name"
    location = "azurerm_resource_group.main.location"
    lines: list[str] = []

    if svc == "virtual_machines":
        nic_lines = [
            f'resource "azurerm_network_interface" "{c.id}_nic" {{',
            f'  name                = "{c.id.replace("_", "-")}-nic"',
            f"  location            = {location}",
            f"  resource_group_name = {rg}",
            "  ip_configuration {",
            '    name                          = "internal"',
            "    subnet_id                     = azurerm_subnet.main.id",
            '    private_ip_address_allocation = "Dynamic"',
            "  }",
            "}",
            "",
        ]
        lines += nic_lines
        lines += [
            f'resource "azurerm_linux_virtual_machine" "{c.id}" {{',
            f'  name                = "{c.id.replace("_", "-")}"',
            f"  resource_group_name = {rg}",
            f"  location            = {location}",
            f'  size                = "{cfg.get("size", "Standard_B2s")}"',
            '  admin_username      = "adminuser"',
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
            f"  resource_group_name          = {rg}",
            f"  location                     = {location}",
            '  version                      = "12.0"',
            '  administrator_login          = "sqladmin"',
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
            f"  resource_group_name      = {rg}",
            f"  location                 = {location}",
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
            f"  location            = {location}",
            f"  resource_group_name = {rg}",
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
            f"  resource_group_name      = {rg}",
            f"  location                 = {location}",
            '  account_tier             = "Standard"',
            '  account_replication_type = "LRS"',
            "}",
            "",
            f'resource "azurerm_service_plan" "{c.id}_plan" {{',
            f'  name                = "{plan_name}"',
            f"  resource_group_name = {rg}",
            f"  location            = {location}",
            '  os_type             = "Linux"',
            '  sku_name            = "Y1"',
            "}",
            "",
            f'resource "azurerm_linux_function_app" "{c.id}" {{',
            f'  name                = "{c.id.replace("_", "-")}"',
            f"  resource_group_name = {rg}",
            f"  location            = {location}",
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
            f"  location            = {location}",
            f"  resource_group_name = {rg}",
            '  offer_type          = "Standard"',
            f'  kind                = "{cfg.get("kind", "GlobalDocumentDB")}"',
            "  consistency_policy {",
            '    consistency_level = "Session"',
            "  }",
            "  geo_location {",
            f"    location          = {location}",
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
            f"  location            = {location}",
            f"  resource_group_name = {rg}",
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
            f"  resource_group_name = {rg}",
            f"  location            = {location}",
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
            f"  location            = {location}",
            f"  resource_group_name = {rg}",
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


def _render_resource(c: "Component") -> str:
    provider = c.provider.lower()
    if provider == "aws":
        return _render_aws_resource(c)
    if provider == "gcp":
        return _render_gcp_resource(c)
    if provider == "azure":
        return _render_azure_resource(c)
    return f"# Unsupported provider: {provider} (component: {c.id})"


def _providers_in_spec(spec: "ArchSpec") -> set[str]:
    providers = {spec.provider.lower()}
    for c in spec.components:
        providers.add(c.provider.lower())
    return providers & _REQUIRED_PROVIDERS.keys()


def render(spec: "ArchSpec") -> str:
    providers = _providers_in_spec(spec)
    parts: list[str] = []

    parts.append("# Generated by Cloudwright")
    parts.append(f"# Architecture: {spec.name}")
    parts.append("")

    # terraform block
    req_providers_lines = ["terraform {", "  required_providers {"]
    for p in sorted(providers):
        rp = _REQUIRED_PROVIDERS[p]
        req_providers_lines.append(f"    {p} = {{")
        req_providers_lines.append(f'      source  = "{rp["source"]}"')
        req_providers_lines.append(f'      version = "{rp["version"]}"')
        req_providers_lines.append("    }")
    req_providers_lines += ["  }", "}"]
    parts.append("\n".join(req_providers_lines))
    parts.append("")

    # provider blocks
    for p in sorted(providers):
        if p == "aws":
            parts.append(f'provider "aws" {{\n  region = "{spec.region}"\n}}')
        elif p == "gcp":
            project = spec.metadata.get("gcp_project", "my-gcp-project")
            region = spec.metadata.get("gcp_region", spec.region)
            parts.append(f'provider "google" {{\n  project = "{project}"\n  region  = "{region}"\n}}')
        elif p == "azure":
            parts.append('provider "azurerm" {\n  features {}\n}')
        parts.append("")

    # data sources and shared resources per provider
    if "aws" in providers:
        parts.append('data "aws_vpc" "default" {')
        parts.append("  default = true")
        parts.append("}")
        parts.append("")
        parts.append('data "aws_subnets" "default" {')
        parts.append("  filter {")
        parts.append('    name   = "vpc-id"')
        parts.append("    values = [data.aws_vpc.default.id]")
        parts.append("  }")
        parts.append("}")
        parts.append("")
        parts.append('data "aws_ssm_parameter" "amazon_linux" {')
        parts.append('  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"')
        parts.append("}")
        parts.append("")
        parts.append('data "aws_availability_zones" "available" {')
        parts.append('  state = "available"')
        parts.append("}")
        parts.append("")
        parts.append('data "aws_caller_identity" "current" {}')
        parts.append("")

    if "azure" in providers:
        parts.append('resource "azurerm_resource_group" "main" {')
        parts.append('  name     = "rg-cloudwright"')
        parts.append('  location = "East US"')
        parts.append("}")
        parts.append("")
        parts.append('resource "azurerm_virtual_network" "main" {')
        parts.append('  name                = "vnet-cloudwright"')
        parts.append('  address_space       = ["10.0.0.0/16"]')
        parts.append("  location            = azurerm_resource_group.main.location")
        parts.append("  resource_group_name = azurerm_resource_group.main.name")
        parts.append("}")
        parts.append("")
        parts.append('resource "azurerm_subnet" "main" {')
        parts.append('  name                 = "subnet-cloudwright"')
        parts.append("  resource_group_name  = azurerm_resource_group.main.name")
        parts.append("  virtual_network_name = azurerm_virtual_network.main.name")
        parts.append('  address_prefixes     = ["10.0.1.0/24"]')
        parts.append("}")
        parts.append("")

    # variables
    parts.append('variable "environment" {')
    parts.append('  default = "production"')
    parts.append("}")
    parts.append("")
    parts.append('variable "db_password" {')
    parts.append('  description = "Database password"')
    parts.append("  sensitive   = true")
    parts.append("}")
    parts.append("")
    parts.append('variable "account_id" {')
    parts.append('  description = "AWS account ID"')
    parts.append('  default     = ""')
    parts.append("}")
    parts.append("")
    parts.append('variable "lambda_role_arn" {')
    parts.append('  description = "IAM role ARN for Lambda functions"')
    parts.append("}")
    parts.append("")
    parts.append('variable "eks_role_arn" {')
    parts.append('  description = "IAM role ARN for EKS cluster"')
    parts.append("}")
    parts.append("")
    parts.append('variable "cloudfront_origin_domain" {')
    parts.append('  description = "Domain name for CloudFront origin"')
    parts.append('  default     = "origin.example.com"')
    parts.append("}")
    parts.append("")
    parts.append('variable "trail_bucket" {')
    parts.append('  description = "S3 bucket for CloudTrail logs"')
    parts.append('  default     = ""')
    parts.append("}")
    parts.append("")
    parts.append('variable "codepipeline_role_arn" {')
    parts.append('  description = "IAM role ARN for CodePipeline"')
    parts.append('  default     = ""')
    parts.append("}")
    parts.append("")
    parts.append('variable "artifact_bucket" {')
    parts.append('  description = "S3 bucket for pipeline artifacts"')
    parts.append('  default     = ""')
    parts.append("}")
    parts.append("")
    parts.append('variable "codestar_connection_arn" {')
    parts.append('  description = "CodeStar connection ARN for source"')
    parts.append('  default     = ""')
    parts.append("}")
    parts.append("")
    parts.append('variable "task_definition_arn" {')
    parts.append('  description = "ECS task definition ARN"')
    parts.append('  default     = ""')
    parts.append("}")
    parts.append("")

    # resources
    parts.append("# Resources")
    for c in spec.components:
        parts.append(_render_resource(c))
        parts.append("")

    # outputs
    parts.append('output "architecture_name" {')
    parts.append(f'  value = "{spec.name}"')
    parts.append("}")

    return "\n".join(parts)
