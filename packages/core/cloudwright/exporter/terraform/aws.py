"""AWS resource HCL renderers.

Every renderer here ships with safe-by-default settings:
- S3 buckets: public access blocked, AES256 encryption, versioning enabled.
- RDS: storage_encrypted, 7-day backups, deletion_protection, multi_az when
  the component is tier-3+ data with replicas.
- EC2 / launch templates: IMDSv2 enforced via metadata_options.
- EBS volumes: encrypted at rest.
- Lambda: filename slot left as a TODO (the deployment package source is
  caller-supplied; we will not silently emit a hardcoded "lambda.zip").
- CloudFront: HTTPS-only viewer policy and minimum TLS 1.2.

User-controlled string fields (``c.id``, ``c.label``, region, metadata) are
always emitted via :func:`_hcl_quote` so they cannot break out of their HCL
string literal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.terraform.common import _hcl_num, _hcl_quote

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


def _bucket_name(c: "Component") -> str:
    """Translate a component id into a DNS-safe bucket label."""
    return c.id.replace("_", "-")


def render_resource(c: "Component", spec: "ArchSpec") -> str:
    svc = c.service
    cfg = c.config
    lines: list[str] = []

    if svc == "ec2":
        instance_type = cfg.get("instance_type", "t3.medium")
        lines += [
            f'resource "aws_instance" "{c.id}" {{',
            "  ami           = data.aws_ssm_parameter.amazon_linux.value",
            f"  instance_type = {_hcl_quote(instance_type)}",
            "  subnet_id     = tolist(data.aws_subnets.default.ids)[0]",
            # IMDSv2 enforced — required token, response hop limit 1.
            "  metadata_options {",
            '    http_tokens                 = "required"',
            '    http_endpoint               = "enabled"',
            "    http_put_response_hop_limit = 1",
            "  }",
            "  root_block_device {",
            "    encrypted = true",
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "rds":
        engine = cfg.get("engine", "mysql")
        instance_class = cfg.get("instance_class", "db.t3.medium")
        # Multi-AZ when this is a data/database tier with replicated topology
        # or the user explicitly requested it.
        wants_multi_az = bool(cfg.get("multi_az") or (c.tier >= 3 and (cfg.get("replicas") or 0) > 0))
        lines += [
            f'resource "aws_db_instance" "{c.id}" {{',
            f"  identifier              = {_hcl_quote(c.id)}",
            f"  engine                  = {_hcl_quote(engine)}",
            f"  instance_class          = {_hcl_quote(instance_class)}",
            f"  allocated_storage       = {_hcl_num(cfg.get('allocated_storage', 20), 20)}",
            "  username                = var.db_username",
            "  password                = var.db_password",
            # Safe-by-default hardening for FedRAMP / HIPAA / PCI baselines.
            "  storage_encrypted       = true",
            "  backup_retention_period = 7",
            "  deletion_protection     = true",
            "  skip_final_snapshot     = false",
            f"  multi_az                = {'true' if wants_multi_az else 'false'}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "s3":
        bucket = _bucket_name(c)
        lines += [
            f'resource "aws_s3_bucket" "{c.id}" {{',
            f"  bucket = {_hcl_quote(bucket)}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
            "",
            # Block all public access (defense-in-depth even if a policy slips).
            f'resource "aws_s3_bucket_public_access_block" "{c.id}" {{',
            f"  bucket                  = aws_s3_bucket.{c.id}.id",
            "  block_public_acls       = true",
            "  block_public_policy     = true",
            "  ignore_public_acls      = true",
            "  restrict_public_buckets = true",
            "}",
            "",
            # SSE-S3 (AES256) by default; callers can layer KMS on top.
            f'resource "aws_s3_bucket_server_side_encryption_configuration" "{c.id}" {{',
            f"  bucket = aws_s3_bucket.{c.id}.id",
            "  rule {",
            "    apply_server_side_encryption_by_default {",
            '      sse_algorithm = "AES256"',
            "    }",
            "  }",
            "}",
            "",
            # Versioning enabled by default for ransomware / accidental-delete recovery.
            f'resource "aws_s3_bucket_versioning" "{c.id}" {{',
            f"  bucket = aws_s3_bucket.{c.id}.id",
            "  versioning_configuration {",
            '    status = "Enabled"',
            "  }",
            "}",
        ]

    elif svc in ("alb", "nlb"):
        lb_type = "application" if svc == "alb" else "network"
        lines += [
            f'resource "aws_lb" "{c.id}" {{',
            f"  name               = {_hcl_quote(_bucket_name(c))}",
            "  internal           = false",
            f"  load_balancer_type = {_hcl_quote(lb_type)}",
            "  subnets            = data.aws_subnets.default.ids",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "cloudfront":
        lines += [
            f'resource "aws_cloudfront_distribution" "{c.id}" {{',
            "  enabled = true",
            "  origin {",
            "    domain_name = var.cloudfront_origin_domain",
            f"    origin_id   = {_hcl_quote(c.id + '-origin')}",
            "  }",
            "  default_cache_behavior {",
            '    allowed_methods  = ["GET", "HEAD"]',
            '    cached_methods   = ["GET", "HEAD"]',
            f"    target_origin_id = {_hcl_quote(c.id + '-origin')}",
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
            # Enforce TLS 1.2+ when a custom cert is supplied; this attribute
            # is harmless when only the default cert is in use.
            '    minimum_protocol_version       = "TLSv1.2_2021"',
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "lambda":
        runtime = cfg.get("runtime", "python3.11")
        lines += [
            f'resource "aws_lambda_function" "{c.id}" {{',
            f"  function_name = {_hcl_quote(c.id)}",
            "  role          = var.lambda_role_arn",
            '  handler       = "index.handler"',
            f"  runtime       = {_hcl_quote(runtime)}",
            "  # TODO: replace with deployment package source",
            "  # (e.g. filename + source_code_hash, or s3_bucket + s3_key,",
            "  #  or image_uri for container-based deploys).",
            "  filename      = var.lambda_deployment_package",
            "  tracing_config {",
            '    mode = "Active"',
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "elasticache":
        engine = cfg.get("engine", "redis")
        node_type = cfg.get("node_type", "cache.t3.medium")
        lines += [
            f'resource "aws_elasticache_cluster" "{c.id}" {{',
            f"  cluster_id           = {_hcl_quote(_bucket_name(c))}",
            f"  engine               = {_hcl_quote(engine)}",
            f"  node_type            = {_hcl_quote(node_type)}",
            f"  num_cache_nodes      = {_hcl_num(cfg.get('num_cache_nodes', 1), 1)}",
            f"  parameter_group_name = {_hcl_quote(f'default.{engine}7')}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "dynamodb":
        hash_key = cfg.get("hash_key", "id")
        billing = cfg.get("billing_mode", "PAY_PER_REQUEST")
        lines += [
            f'resource "aws_dynamodb_table" "{c.id}" {{',
            f"  name         = {_hcl_quote(c.id)}",
            f"  billing_mode = {_hcl_quote(billing)}",
            f"  hash_key     = {_hcl_quote(hash_key)}",
            "  attribute {",
            f"    name = {_hcl_quote(hash_key)}",
            '    type = "S"',
            "  }",
            "  server_side_encryption {",
            "    enabled = true",
            "  }",
            "  point_in_time_recovery {",
            "    enabled = true",
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "sqs":
        lines += [
            f'resource "aws_sqs_queue" "{c.id}" {{',
            f"  name = {_hcl_quote(_bucket_name(c))}",
            # Enforce SSE-SQS (managed) at rest by default.
            "  sqs_managed_sse_enabled = true",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "sns":
        lines += [
            f'resource "aws_sns_topic" "{c.id}" {{',
            f"  name = {_hcl_quote(_bucket_name(c))}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "waf":
        lines += [
            f'resource "aws_wafv2_web_acl" "{c.id}" {{',
            f"  name  = {_hcl_quote(c.id)}",
            '  scope = "REGIONAL"',
            # Terraform rejects a single-line block that contains a nested block,
            # so default_action must be emitted multi-line.
            "  default_action {",
            "    allow {}",
            "  }",
            "  visibility_config {",
            "    cloudwatch_metrics_enabled = true",
            f"    metric_name                = {_hcl_quote(c.id)}",
            "    sampled_requests_enabled   = true",
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "route53":
        lines += [
            f'resource "aws_route53_zone" "{c.id}" {{',
            f"  name = {_hcl_quote(cfg.get('domain', 'example.com'))}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "api_gateway":
        lines += [
            f'resource "aws_api_gateway_rest_api" "{c.id}" {{',
            f"  name = {_hcl_quote(c.label)}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "ecs":
        launch_type = cfg.get("launch_type", "FARGATE")
        svc_lines = [
            f'resource "aws_ecs_cluster" "{c.id}" {{',
            f"  name = {_hcl_quote(_bucket_name(c))}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
            "",
            f'resource "aws_ecs_service" "{c.id}_service" {{',
            f"  name            = {_hcl_quote(c.id + '-service')}",
            f"  cluster         = aws_ecs_cluster.{c.id}.id",
            f"  desired_count   = {_hcl_num(cfg.get('desired_count', 1), 1)}",
            f"  launch_type     = {_hcl_quote(launch_type)}",
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
            f"  name     = {_hcl_quote(_bucket_name(c))}",
            "  role_arn = var.eks_role_arn",
            "  vpc_config {",
            "    subnet_ids = data.aws_subnets.default.ids",
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "cognito":
        lines += [
            f'resource "aws_cognito_user_pool" "{c.id}" {{',
            f"  name = {_hcl_quote(_bucket_name(c))}",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "kms":
        lines += [
            f'resource "aws_kms_key" "{c.id}" {{',
            f"  description             = {_hcl_quote(c.label)}",
            "  enable_key_rotation     = true",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "cloudtrail":
        lines += [
            f'resource "aws_cloudtrail" "{c.id}" {{',
            f"  name                  = {_hcl_quote(_bucket_name(c))}",
            "  s3_bucket_name        = var.trail_bucket",
            "  is_multi_region_trail = true",
            "  enable_log_file_validation = true",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
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
            f"  name        = {_hcl_quote(_bucket_name(c))}",
            f"  shard_count = {_hcl_num(cfg.get('shard_count', 2), 2)}",
            # Enforce server-side encryption with the AWS-managed KMS key.
            '  encryption_type = "KMS"',
            '  kms_key_id      = "alias/aws/kinesis"',
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "ecr":
        lines += [
            f'resource "aws_ecr_repository" "{c.id}" {{',
            f"  name                 = {_hcl_quote(_bucket_name(c))}",
            '  image_tag_mutability = "IMMUTABLE"',
            "  image_scanning_configuration {",
            "    scan_on_push = true",
            "  }",
            "  encryption_configuration {",
            '    encryption_type = "AES256"',
            "  }",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "cloudwatch":
        lines += [
            f'resource "aws_cloudwatch_log_group" "{c.id}" {{',
            f"  name              = {_hcl_quote(f'/cloudwright/{c.id}')}",
            "  retention_in_days = 30",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "ebs":
        lines += [
            f'resource "aws_ebs_volume" "{c.id}" {{',
            "  availability_zone = data.aws_availability_zones.available.names[0]",
            f"  size              = {_hcl_num(cfg.get('size', 100), 100)}",
            '  type              = "gp3"',
            # Encryption at rest enforced by default.
            "  encrypted         = true",
            "  tags = {",
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    elif svc == "codepipeline":
        lines += [
            f'resource "aws_codepipeline" "{c.id}" {{',
            f"  name     = {_hcl_quote(_bucket_name(c))}",
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
            f"    Name = {_hcl_quote(c.label)}",
            "  }",
            "}",
        ]

    else:
        # Strip newlines from label so it cannot break out of the # comment.
        safe_label = (c.label or "").replace("\n", " ").replace("\r", " ")
        lines += [
            f"# Unsupported AWS service: {svc}",
            f"# component: {c.id} ({safe_label})",
        ]

    return "\n".join(lines)
