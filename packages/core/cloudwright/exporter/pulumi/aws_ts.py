"""AWS Pulumi TypeScript renderers.

Mirrors the AWS Terraform exporter's safe-by-default posture (see
``cloudwright/exporter/terraform/aws.py``):

- S3 buckets: ``forceDestroy: false``, public-access block, AES256 SSE,
  versioning enabled.
- RDS:        ``storageEncrypted``, ``backupRetentionPeriod: 7``,
              ``deletionProtection``, ``skipFinalSnapshot: false``.
- EC2:        IMDSv2 enforced via ``metadataOptions``, encrypted root EBS.
- DynamoDB:   SSE + point-in-time recovery.
- SQS:        managed SSE.
- Kinesis:    KMS encryption.
- ECR:        scan-on-push, AES256, immutable tags.
- CloudFront: ``minimumProtocolVersion: "TLSv1.2_2021"``,
              ``viewerProtocolPolicy: "redirect-to-https"``.
- CloudTrail: ``enableLogFileValidation: true``, multi-region trail.

Every user-controlled string field is emitted via :func:`_ts_string`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudwright.exporter.pulumi.common import _dns_name, _safe_comment, _ts_string, _var_name

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
            f"const {var} = new aws.ec2.Vpc({_ts_string(c.id)}, {{",
            f"  cidrBlock: {_ts_string(cidr)},",
            "  enableDnsSupport: true,",
            "  enableDnsHostnames: true,",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "ec2":
        instance_type = cfg.get("instance_type", "t3.medium")
        lines += [
            f"const {var} = new aws.ec2.Instance({_ts_string(c.id)}, {{",
            f"  instanceType: {_ts_string(instance_type)},",
            "  ami: amazonLinuxAmi.value,",
            # IMDSv2 enforced.
            "  metadataOptions: {",
            '    httpTokens: "required",',
            '    httpEndpoint: "enabled",',
            "    httpPutResponseHopLimit: 1,",
            "  },",
            "  rootBlockDevice: {",
            "    encrypted: true,",
            "  },",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "rds":
        engine = cfg.get("engine", "mysql")
        instance_class = cfg.get("instance_class", "db.t3.medium")
        wants_multi_az = bool(cfg.get("multi_az") or (c.tier >= 3 and (cfg.get("replicas") or 0) > 0))
        lines += [
            f"const {var} = new aws.rds.Instance({_ts_string(c.id)}, {{",
            f"  identifier: {_ts_string(c.id)},",
            f"  engine: {_ts_string(engine)},",
            f"  instanceClass: {_ts_string(instance_class)},",
            f"  allocatedStorage: {int(cfg.get('allocated_storage', 20))},",
            "  username: dbUsername,",
            "  password: dbPassword,",
            "  storageEncrypted: true,",
            "  backupRetentionPeriod: 7,",
            "  deletionProtection: true,",
            "  skipFinalSnapshot: false,",
            f"  multiAz: {str(wants_multi_az).lower()},",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "s3":
        bucket_var = var + "Bucket"
        lines += [
            f"const {bucket_var} = new aws.s3.Bucket({_ts_string(c.id)}, {{",
            f"  bucket: {_ts_string(_dns_name(c.id))},",
            "  forceDestroy: false,",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
            "",
            f"new aws.s3.BucketPublicAccessBlock({_ts_string(c.id + '-pab')}, {{",
            f"  bucket: {bucket_var}.id,",
            "  blockPublicAcls: true,",
            "  blockPublicPolicy: true,",
            "  ignorePublicAcls: true,",
            "  restrictPublicBuckets: true,",
            "});",
            "",
            f"new aws.s3.BucketServerSideEncryptionConfigurationV2({_ts_string(c.id + '-sse')}, {{",
            f"  bucket: {bucket_var}.id,",
            "  rules: [{",
            "    applyServerSideEncryptionByDefault: {",
            '      sseAlgorithm: "AES256",',
            "    },",
            "  }],",
            "});",
            "",
            f"new aws.s3.BucketVersioningV2({_ts_string(c.id + '-ver')}, {{",
            f"  bucket: {bucket_var}.id,",
            "  versioningConfiguration: {",
            '    status: "Enabled",',
            "  },",
            "});",
        ]

    elif svc in ("alb", "nlb"):
        lb_type = "application" if svc == "alb" else "network"
        lines += [
            f"const {var} = new aws.lb.LoadBalancer({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            "  internal: false,",
            f"  loadBalancerType: {_ts_string(lb_type)},",
            "  subnets: defaultSubnets.ids,",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "cloudfront":
        origin_id = c.id + "-origin"
        lines += [
            f"const {var} = new aws.cloudfront.Distribution({_ts_string(c.id)}, {{",
            "  enabled: true,",
            "  origins: [{",
            "    domainName: cloudfrontOriginDomain,",
            f"    originId: {_ts_string(origin_id)},",
            "  }],",
            "  defaultCacheBehavior: {",
            '    allowedMethods: ["GET", "HEAD"],',
            '    cachedMethods: ["GET", "HEAD"],',
            f"    targetOriginId: {_ts_string(origin_id)},",
            '    viewerProtocolPolicy: "redirect-to-https",',
            "    forwardedValues: {",
            "      queryString: false,",
            '      cookies: { forward: "none" },',
            "    },",
            "  },",
            "  restrictions: {",
            '    geoRestriction: { restrictionType: "none" },',
            "  },",
            "  viewerCertificate: {",
            "    cloudfrontDefaultCertificate: true,",
            '    minimumProtocolVersion: "TLSv1.2_2021",',
            "  },",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "lambda":
        runtime = cfg.get("runtime", "python3.11")
        lines += [
            f"const {var} = new aws.lambda.Function({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(c.id)},",
            "  role: lambdaRoleArn,",
            '  handler: "index.handler",',
            f"  runtime: {_ts_string(runtime)},",
            "  // TODO: replace with deployment package source",
            "  // (e.g. code: new pulumi.asset.FileArchive('./fn'),",
            "  //  or s3Bucket + s3Key, or imageUri for container deploys).",
            "  code: lambdaDeploymentPackage,",
            "  tracingConfig: {",
            '    mode: "Active",',
            "  },",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "dynamodb":
        hash_key = cfg.get("hash_key", "id")
        billing = cfg.get("billing_mode", "PAY_PER_REQUEST")
        lines += [
            f"const {var} = new aws.dynamodb.Table({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(c.id)},",
            f"  billingMode: {_ts_string(billing)},",
            f"  hashKey: {_ts_string(hash_key)},",
            "  attributes: [{",
            f"    name: {_ts_string(hash_key)},",
            '    type: "S",',
            "  }],",
            "  serverSideEncryption: {",
            "    enabled: true,",
            "  },",
            "  pointInTimeRecovery: {",
            "    enabled: true,",
            "  },",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "sqs":
        lines += [
            f"const {var} = new aws.sqs.Queue({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            "  sqsManagedSseEnabled: true,",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "kinesis":
        lines += [
            f"const {var} = new aws.kinesis.Stream({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            f"  shardCount: {int(cfg.get('shard_count', 2))},",
            '  encryptionType: "KMS",',
            '  kmsKeyId: "alias/aws/kinesis",',
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "ecr":
        lines += [
            f"const {var} = new aws.ecr.Repository({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            '  imageTagMutability: "IMMUTABLE",',
            "  imageScanningConfiguration: {",
            "    scanOnPush: true,",
            "  },",
            "  encryptionConfigurations: [{",
            '    encryptionType: "AES256",',
            "  }],",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "ecs":
        launch_type = cfg.get("launch_type", "FARGATE")
        lines += [
            f"const {var}Cluster = new aws.ecs.Cluster({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
            "",
            f"const {var}Service = new aws.ecs.Service({_ts_string(c.id + '-service')}, {{",
            f"  name: {_ts_string(c.id + '-service')},",
            f"  cluster: {var}Cluster.id,",
            f"  desiredCount: {int(cfg.get('desired_count', 1))},",
            f"  launchType: {_ts_string(launch_type)},",
            "  taskDefinition: taskDefinitionArn,",
        ]
        if launch_type == "FARGATE":
            lines += [
                "  networkConfiguration: {",
                "    subnets: defaultSubnets.ids,",
                "  },",
            ]
        lines.append("});")

    elif svc == "eks":
        lines += [
            f"const {var} = new aws.eks.Cluster({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            "  roleArn: eksRoleArn,",
            "  vpcConfig: {",
            "    subnetIds: defaultSubnets.ids,",
            "  },",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "cloudtrail":
        lines += [
            f"const {var} = new aws.cloudtrail.Trail({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(name)},",
            "  s3BucketName: trailBucket,",
            "  isMultiRegionTrail: true,",
            "  enableLogFileValidation: true,",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    elif svc == "cloudwatch":
        lines += [
            f"const {var} = new aws.cloudwatch.LogGroup({_ts_string(c.id)}, {{",
            f"  name: {_ts_string(f'/cloudwright/{c.id}')},",
            "  retentionInDays: 30,",
            "  tags: {",
            f"    Name: {_ts_string(label)},",
            "  },",
            "});",
        ]

    else:
        lines += [
            f"// Unsupported AWS service: {svc}",
            f"// component: {c.id} ({_safe_comment(label)})",
        ]

    return "\n".join(lines)


def render_aws_preamble() -> list[str]:
    """Top-level AWS imports + lookups shared across the file."""
    return [
        'import * as aws from "@pulumi/aws";',
        'import * as pulumi from "@pulumi/pulumi";',
        "",
        "const config = new pulumi.Config();",
        'const dbUsername = config.get("dbUsername") ?? "cloudwright_admin";',
        'const dbPassword = config.requireSecret("dbPassword");',
        'const lambdaRoleArn = config.get("lambdaRoleArn") ?? "";',
        'const eksRoleArn = config.get("eksRoleArn") ?? "";',
        'const cloudfrontOriginDomain = config.get("cloudfrontOriginDomain") ?? "origin.example.com";',
        'const trailBucket = config.get("trailBucket") ?? "";',
        'const taskDefinitionArn = config.get("taskDefinitionArn") ?? "";',
        'const lambdaDeploymentPackage = new pulumi.asset.FileArchive("./lambda.zip");',
        "",
        "const defaultVpc = aws.ec2.getVpcOutput({ default: true });",
        "const defaultSubnets = aws.ec2.getSubnetsOutput({",
        '  filters: [{ name: "vpc-id", values: [defaultVpc.id] }],',
        "});",
        "const amazonLinuxAmi = aws.ssm.getParameterOutput({",
        '  name: "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64",',
        "});",
        "",
    ]
