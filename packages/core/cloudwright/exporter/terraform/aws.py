"""AWS resource HCL renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component

RESOURCES: dict[str, str] = {
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


def render_resource(c: "Component", spec: "ArchSpec") -> str:
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
        lines += [
            f"# Unsupported AWS service: {svc}",
            f"# component: {c.id} ({c.label})",
        ]

    return "\n".join(lines)
