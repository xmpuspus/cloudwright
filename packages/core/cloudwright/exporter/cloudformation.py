"""CloudFormation YAML exporter for ArchSpec. AWS components only."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec, Component

_CFN_TYPES: dict[str, str] = {
    "ec2": "AWS::EC2::Instance",
    "rds": "AWS::RDS::DBInstance",
    "s3": "AWS::S3::Bucket",
    "alb": "AWS::ElasticLoadBalancingV2::LoadBalancer",
    "nlb": "AWS::ElasticLoadBalancingV2::LoadBalancer",
    "cloudfront": "AWS::CloudFront::Distribution",
    "lambda": "AWS::Lambda::Function",
    "elasticache": "AWS::ElastiCache::CacheCluster",
    "dynamodb": "AWS::DynamoDB::Table",
    "sqs": "AWS::SQS::Queue",
    "sns": "AWS::SNS::Topic",
    "waf": "AWS::WAFv2::WebACL",
    "route53": "AWS::Route53::HostedZone",
    "api_gateway": "AWS::ApiGateway::RestApi",
    "ecs": "AWS::ECS::Cluster",
    "eks": "AWS::EKS::Cluster",
    "cognito": "AWS::Cognito::UserPool",
}


def _to_pascal(s: str) -> str:
    """Convert snake_case or kebab-case id to PascalCase for CFN resource names."""
    return re.sub(r"[^a-zA-Z0-9]", " ", s).title().replace(" ", "")


def _build_properties(c: "Component") -> dict[str, Any]:
    svc = c.service
    cfg = c.config
    tags = [{"Key": "Name", "Value": c.label}]

    if svc == "ec2":
        return {
            "InstanceType": cfg.get("instance_type", "t3.medium"),
            "ImageId": "ami-0c55b159cbfafe1f0",
            "Tags": tags,
        }

    if svc == "rds":
        return {
            "DBInstanceIdentifier": c.id,
            "DBInstanceClass": cfg.get("instance_class", "db.t3.medium"),
            "Engine": cfg.get("engine", "mysql"),
            "AllocatedStorage": str(cfg.get("allocated_storage", 20)),
            "MasterUsername": "admin",
            "MasterUserPassword": "changeme",
            "Tags": tags,
        }

    if svc == "s3":
        return {
            "BucketName": c.id.replace("_", "-"),
            "Tags": tags,
        }

    if svc in ("alb", "nlb"):
        return {
            "Name": c.id.replace("_", "-"),
            "Type": "application" if svc == "alb" else "network",
            "Scheme": "internet-facing",
            "Tags": tags,
        }

    if svc == "cloudfront":
        return {
            "DistributionConfig": {
                "Enabled": True,
                "Origins": [
                    {
                        "DomainName": "origin.example.com",
                        "Id": f"{c.id}-origin",
                        "CustomOriginConfig": {"HTTPPort": 80, "OriginProtocolPolicy": "http-only"},
                    }
                ],
                "DefaultCacheBehavior": {
                    "TargetOriginId": f"{c.id}-origin",
                    "ViewerProtocolPolicy": "redirect-to-https",
                    "ForwardedValues": {"QueryString": False, "Cookies": {"Forward": "none"}},
                },
            }
        }

    if svc == "lambda":
        return {
            "FunctionName": c.id,
            "Runtime": cfg.get("runtime", "python3.11"),
            "Handler": "index.handler",
            "Role": "arn:aws:iam::ACCOUNT_ID:role/lambda-role",
            "Code": {"ZipFile": "def handler(event, context): pass"},
            "Tags": tags,
        }

    if svc == "elasticache":
        return {
            "ClusterName": c.id.replace("_", "-"),
            "Engine": cfg.get("engine", "redis"),
            "CacheNodeType": cfg.get("node_type", "cache.t3.medium"),
            "NumCacheNodes": cfg.get("num_cache_nodes", 1),
        }

    if svc == "dynamodb":
        return {
            "TableName": c.id,
            "BillingMode": cfg.get("billing_mode", "PAY_PER_REQUEST"),
            "AttributeDefinitions": [{"AttributeName": cfg.get("hash_key", "id"), "AttributeType": "S"}],
            "KeySchema": [{"AttributeName": cfg.get("hash_key", "id"), "KeyType": "HASH"}],
            "Tags": tags,
        }

    if svc == "sqs":
        return {
            "QueueName": c.id.replace("_", "-"),
            "Tags": tags,
        }

    if svc == "sns":
        return {
            "TopicName": c.id.replace("_", "-"),
            "Tags": tags,
        }

    if svc == "waf":
        return {
            "Name": c.id,
            "Scope": "REGIONAL",
            "DefaultAction": {"Allow": {}},
            "VisibilityConfig": {
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": c.id,
            },
            "Rules": [],
            "Tags": tags,
        }

    if svc == "route53":
        return {
            "Name": cfg.get("domain", "example.com"),
        }

    if svc == "api_gateway":
        return {
            "Name": c.label,
            "Tags": {t["Key"]: t["Value"] for t in tags},
        }

    if svc == "ecs":
        return {
            "ClusterName": c.id.replace("_", "-"),
            "Tags": tags,
        }

    if svc == "eks":
        return {
            "Name": c.id.replace("_", "-"),
            "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/eks-role",
            "ResourcesVpcConfig": {"SubnetIds": [], "SecurityGroupIds": []},
            "Tags": tags,
        }

    if svc == "cognito":
        return {
            "UserPoolName": c.id.replace("_", "-"),
            "UserPoolTags": {t["Key"]: t["Value"] for t in tags},
        }

    return {}


def render(spec: "ArchSpec") -> str:
    aws_components = [c for c in spec.components if c.provider.lower() == "aws"]

    resources: dict[str, Any] = {}
    for c in aws_components:
        cfn_type = _CFN_TYPES.get(c.service)
        if not cfn_type:
            continue
        resource_id = _to_pascal(c.id)
        resources[resource_id] = {
            "Type": cfn_type,
            "Properties": _build_properties(c),
        }

    template: dict[str, Any] = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": spec.name,
        "Parameters": {
            "Environment": {
                "Type": "String",
                "Default": "production",
            }
        },
        "Resources": resources,
        "Outputs": {
            "ArchitectureName": {
                "Value": spec.name,
            }
        },
    }

    return yaml.dump(template, default_flow_style=False, sort_keys=False, allow_unicode=True)
