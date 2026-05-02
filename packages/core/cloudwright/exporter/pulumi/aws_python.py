"""AWS Pulumi Python renderers.

Same safe-by-default posture as ``aws_ts.py``; see that module's docstring.
Every user-controlled string field is emitted via :func:`_py_string`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.pulumi.common import _dns_name, _py_string, _safe_comment, _var_name

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component


SUPPORTED: set[str] = {
    "ec2",
    "rds",
    "s3",
    "alb",
    "nlb",
    "cloudfront",
    "lambda",
    "dynamodb",
    "sqs",
    "kinesis",
    "ecr",
    "ecs",
    "eks",
    "cloudtrail",
    "cloudwatch",
    "vpc",
}


def render_resource(c: "Component", spec: "ArchSpec") -> str:
    svc = c.service
    cfg = c.config
    var = _var_name(c.id)
    name = _dns_name(c.id)
    label = c.label or c.id
    lines: list[str] = []

    if svc == "vpc":
        cidr = cfg.get("cidr_block", "10.0.0.0/16")
        lines += [
            f"{var} = aws.ec2.Vpc(",
            f"    {_py_string(c.id)},",
            f"    cidr_block={_py_string(cidr)},",
            "    enable_dns_support=True,",
            "    enable_dns_hostnames=True,",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "ec2":
        instance_type = cfg.get("instance_type", "t3.medium")
        lines += [
            f"{var} = aws.ec2.Instance(",
            f"    {_py_string(c.id)},",
            f"    instance_type={_py_string(instance_type)},",
            "    ami=amazon_linux_ami.value,",
            "    metadata_options=aws.ec2.InstanceMetadataOptionsArgs(",
            '        http_tokens="required",',
            '        http_endpoint="enabled",',
            "        http_put_response_hop_limit=1,",
            "    ),",
            "    root_block_device=aws.ec2.InstanceRootBlockDeviceArgs(",
            "        encrypted=True,",
            "    ),",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "rds":
        engine = cfg.get("engine", "mysql")
        instance_class = cfg.get("instance_class", "db.t3.medium")
        wants_multi_az = bool(cfg.get("multi_az") or (c.tier >= 3 and (cfg.get("replicas") or 0) > 0))
        lines += [
            f"{var} = aws.rds.Instance(",
            f"    {_py_string(c.id)},",
            f"    identifier={_py_string(c.id)},",
            f"    engine={_py_string(engine)},",
            f"    instance_class={_py_string(instance_class)},",
            f"    allocated_storage={int(cfg.get('allocated_storage', 20))},",
            "    username=db_username,",
            "    password=db_password,",
            "    storage_encrypted=True,",
            "    backup_retention_period=7,",
            "    deletion_protection=True,",
            "    skip_final_snapshot=False,",
            f"    multi_az={'True' if wants_multi_az else 'False'},",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "s3":
        bucket_var = var + "_bucket"
        lines += [
            f"{bucket_var} = aws.s3.Bucket(",
            f"    {_py_string(c.id)},",
            f"    bucket={_py_string(_dns_name(c.id))},",
            "    force_destroy=False,",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
            "",
            "aws.s3.BucketPublicAccessBlock(",
            f"    {_py_string(c.id + '-pab')},",
            f"    bucket={bucket_var}.id,",
            "    block_public_acls=True,",
            "    block_public_policy=True,",
            "    ignore_public_acls=True,",
            "    restrict_public_buckets=True,",
            ")",
            "",
            "aws.s3.BucketServerSideEncryptionConfigurationV2(",
            f"    {_py_string(c.id + '-sse')},",
            f"    bucket={bucket_var}.id,",
            "    rules=[aws.s3.BucketServerSideEncryptionConfigurationV2RuleArgs(",
            "        apply_server_side_encryption_by_default=aws.s3."
            "BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(",
            '            sse_algorithm="AES256",',
            "        ),",
            "    )],",
            ")",
            "",
            "aws.s3.BucketVersioningV2(",
            f"    {_py_string(c.id + '-ver')},",
            f"    bucket={bucket_var}.id,",
            "    versioning_configuration=aws.s3.BucketVersioningV2VersioningConfigurationArgs(",
            '        status="Enabled",',
            "    ),",
            ")",
        ]

    elif svc in ("alb", "nlb"):
        lb_type = "application" if svc == "alb" else "network"
        lines += [
            f"{var} = aws.lb.LoadBalancer(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            "    internal=False,",
            f"    load_balancer_type={_py_string(lb_type)},",
            "    subnets=default_subnets.ids,",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "cloudfront":
        origin_id = c.id + "-origin"
        lines += [
            f"{var} = aws.cloudfront.Distribution(",
            f"    {_py_string(c.id)},",
            "    enabled=True,",
            "    origins=[aws.cloudfront.DistributionOriginArgs(",
            "        domain_name=cloudfront_origin_domain,",
            f"        origin_id={_py_string(origin_id)},",
            "    )],",
            "    default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(",
            '        allowed_methods=["GET", "HEAD"],',
            '        cached_methods=["GET", "HEAD"],',
            f"        target_origin_id={_py_string(origin_id)},",
            '        viewer_protocol_policy="redirect-to-https",',
            "        forwarded_values=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(",
            "            query_string=False,",
            "            cookies=aws.cloudfront."
            'DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(forward="none"),',
            "        ),",
            "    ),",
            "    restrictions=aws.cloudfront.DistributionRestrictionsArgs(",
            "        geo_restriction=aws.cloudfront."
            'DistributionRestrictionsGeoRestrictionArgs(restriction_type="none"),',
            "    ),",
            "    viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(",
            "        cloudfront_default_certificate=True,",
            '        minimum_protocol_version="TLSv1.2_2021",',
            "    ),",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "lambda":
        runtime = cfg.get("runtime", "python3.11")
        lines += [
            f"{var} = aws.lambda_.Function(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(c.id)},",
            "    role=lambda_role_arn,",
            '    handler="index.handler",',
            f"    runtime={_py_string(runtime)},",
            "    # TODO: replace with deployment package source",
            "    # (e.g. code=pulumi.FileArchive('./fn'),",
            "    #  or s3_bucket+s3_key, or image_uri for container deploys).",
            "    code=lambda_deployment_package,",
            "    tracing_config=aws.lambda_.FunctionTracingConfigArgs(",
            '        mode="Active",',
            "    ),",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "dynamodb":
        hash_key = cfg.get("hash_key", "id")
        billing = cfg.get("billing_mode", "PAY_PER_REQUEST")
        lines += [
            f"{var} = aws.dynamodb.Table(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(c.id)},",
            f"    billing_mode={_py_string(billing)},",
            f"    hash_key={_py_string(hash_key)},",
            "    attributes=[aws.dynamodb.TableAttributeArgs(",
            f"        name={_py_string(hash_key)},",
            '        type="S",',
            "    )],",
            "    server_side_encryption=aws.dynamodb.TableServerSideEncryptionArgs(",
            "        enabled=True,",
            "    ),",
            "    point_in_time_recovery=aws.dynamodb.TablePointInTimeRecoveryArgs(",
            "        enabled=True,",
            "    ),",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "sqs":
        lines += [
            f"{var} = aws.sqs.Queue(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            "    sqs_managed_sse_enabled=True,",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "kinesis":
        lines += [
            f"{var} = aws.kinesis.Stream(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            f"    shard_count={int(cfg.get('shard_count', 2))},",
            '    encryption_type="KMS",',
            '    kms_key_id="alias/aws/kinesis",',
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "ecr":
        lines += [
            f"{var} = aws.ecr.Repository(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            '    image_tag_mutability="IMMUTABLE",',
            "    image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(",
            "        scan_on_push=True,",
            "    ),",
            "    encryption_configurations=[aws.ecr.RepositoryEncryptionConfigurationArgs(",
            '        encryption_type="AES256",',
            "    )],",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "ecs":
        launch_type = cfg.get("launch_type", "FARGATE")
        lines += [
            f"{var}_cluster = aws.ecs.Cluster(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
            "",
            f"{var}_service = aws.ecs.Service(",
            f"    {_py_string(c.id + '-service')},",
            f"    name={_py_string(c.id + '-service')},",
            f"    cluster={var}_cluster.id,",
            f"    desired_count={int(cfg.get('desired_count', 1))},",
            f"    launch_type={_py_string(launch_type)},",
            "    task_definition=task_definition_arn,",
        ]
        if launch_type == "FARGATE":
            lines += [
                "    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(",
                "        subnets=default_subnets.ids,",
                "    ),",
            ]
        lines.append(")")

    elif svc == "eks":
        lines += [
            f"{var} = aws.eks.Cluster(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            "    role_arn=eks_role_arn,",
            "    vpc_config=aws.eks.ClusterVpcConfigArgs(",
            "        subnet_ids=default_subnets.ids,",
            "    ),",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "cloudtrail":
        lines += [
            f"{var} = aws.cloudtrail.Trail(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(name)},",
            "    s3_bucket_name=trail_bucket,",
            "    is_multi_region_trail=True,",
            "    enable_log_file_validation=True,",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    elif svc == "cloudwatch":
        lines += [
            f"{var} = aws.cloudwatch.LogGroup(",
            f"    {_py_string(c.id)},",
            f"    name={_py_string(f'/cloudwright/{c.id}')},",
            "    retention_in_days=30,",
            f'    tags={{"Name": {_py_string(label)}}},',
            ")",
        ]

    else:
        lines += [
            f"# Unsupported AWS service: {svc}",
            f"# component: {c.id} ({_safe_comment(label)})",
        ]

    return "\n".join(lines)


def render_aws_preamble() -> list[str]:
    return [
        "import pulumi",
        "import pulumi_aws as aws",
        "",
        "config = pulumi.Config()",
        'db_username = config.get("dbUsername") or "cloudwright_admin"',
        'db_password = config.require_secret("dbPassword")',
        'lambda_role_arn = config.get("lambdaRoleArn") or ""',
        'eks_role_arn = config.get("eksRoleArn") or ""',
        'cloudfront_origin_domain = config.get("cloudfrontOriginDomain") or "origin.example.com"',
        'trail_bucket = config.get("trailBucket") or ""',
        'task_definition_arn = config.get("taskDefinitionArn") or ""',
        'lambda_deployment_package = pulumi.FileArchive("./lambda.zip")',
        "",
        "default_vpc = aws.ec2.get_vpc_output(default=True)",
        "default_subnets = aws.ec2.get_subnets_output(",
        '    filters=[aws.ec2.GetSubnetsFilterArgs(name="vpc-id", values=[default_vpc.id])],',
        ")",
        "amazon_linux_ami = aws.ssm.get_parameter_output(",
        '    name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64",',
        ")",
        "",
    ]
