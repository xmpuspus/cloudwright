"""Tests for the Pulumi TypeScript exporter.

Pins the v1.4 commitment that the Pulumi TS renderer ships the same
safe-by-default posture as the Terraform exporter (S3 public access blocked,
RDS encrypted with backups, EC2 IMDSv2, DynamoDB SSE+PITR, CloudFront TLS
1.2+, etc.) and that user-controlled string fields cannot escape the
TypeScript string literal.
"""

from __future__ import annotations

import pytest

from cloudwright.exporter.pulumi import render_pulumi_ts
from cloudwright.exporter.pulumi.aws_ts import render_resource as render_aws
from cloudwright.exporter.pulumi.azure_ts import render_resource as render_azure
from cloudwright.exporter.pulumi.common import _ts_string
from cloudwright.exporter.pulumi.gcp_ts import render_resource as render_gcp
from cloudwright.spec import ArchSpec, Component


def _spec(component: Component) -> ArchSpec:
    return ArchSpec(
        name="Pulumi TS",
        provider=component.provider,
        region="us-east-1",
        components=[component],
        connections=[],
    )


# --- Escape helpers ---------------------------------------------------------


def test_ts_string_escapes_double_quote():
    assert _ts_string('a"b') == '"a\\"b"'


def test_ts_string_escapes_backslash():
    assert _ts_string("a\\b") == '"a\\\\b"'


def test_ts_string_escapes_newline():
    assert _ts_string("a\nb") == '"a\\nb"'


def test_ts_string_escapes_backtick():
    assert _ts_string("a`b") == '"a\\`b"'


def test_hostile_label_does_not_break_out_of_string():
    c = Component(id="bk", service="s3", provider="aws", label='hi"; danger //', tier=3)
    ts = render_aws(c, _spec(c))
    # Label appears with the quote escaped, so it stays inside the literal.
    assert 'hi\\";' in ts
    # And no raw, unescaped instance of the dangerous suffix appears either.
    assert 'hi"; danger //' not in ts


# --- AWS S3 -----------------------------------------------------------------


def test_s3_emits_public_access_block():
    c = Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3)
    ts = render_aws(c, _spec(c))
    assert "aws.s3.BucketPublicAccessBlock" in ts
    assert "blockPublicAcls: true," in ts
    assert "blockPublicPolicy: true," in ts
    assert "ignorePublicAcls: true," in ts
    assert "restrictPublicBuckets: true," in ts


def test_s3_emits_aes256_sse():
    c = Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3)
    ts = render_aws(c, _spec(c))
    assert "aws.s3.BucketServerSideEncryptionConfigurationV2" in ts
    assert 'sseAlgorithm: "AES256",' in ts


def test_s3_emits_versioning_enabled():
    c = Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3)
    ts = render_aws(c, _spec(c))
    assert "aws.s3.BucketVersioningV2" in ts
    assert 'status: "Enabled",' in ts


def test_s3_force_destroy_false():
    c = Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3)
    ts = render_aws(c, _spec(c))
    assert "forceDestroy: false," in ts


# --- AWS RDS ----------------------------------------------------------------


def test_rds_storage_encrypted():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    ts = render_aws(c, _spec(c))
    assert "storageEncrypted: true," in ts


def test_rds_backup_retention_seven_days():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    ts = render_aws(c, _spec(c))
    assert "backupRetentionPeriod: 7," in ts


def test_rds_deletion_protection_true():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    ts = render_aws(c, _spec(c))
    assert "deletionProtection: true," in ts


def test_rds_skip_final_snapshot_false():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    ts = render_aws(c, _spec(c))
    assert "skipFinalSnapshot: false," in ts


def test_rds_multi_az_when_replicas_present():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={"replicas": 2})
    ts = render_aws(c, _spec(c))
    assert "multiAz: true," in ts


# --- AWS EC2 (IMDSv2) -------------------------------------------------------


def test_ec2_imdsv2_metadata_options():
    c = Component(id="web", service="ec2", provider="aws", label="Web", tier=2)
    ts = render_aws(c, _spec(c))
    assert "metadataOptions: {" in ts
    assert 'httpTokens: "required",' in ts
    assert 'httpEndpoint: "enabled",' in ts
    assert "httpPutResponseHopLimit: 1," in ts


def test_ec2_root_block_device_encrypted():
    c = Component(id="web", service="ec2", provider="aws", label="Web", tier=2)
    ts = render_aws(c, _spec(c))
    assert "rootBlockDevice: {" in ts
    assert "encrypted: true," in ts


# --- AWS DynamoDB -----------------------------------------------------------


def test_dynamodb_sse_enabled():
    c = Component(id="t", service="dynamodb", provider="aws", label="T", tier=3)
    ts = render_aws(c, _spec(c))
    assert "serverSideEncryption: {" in ts
    assert "enabled: true," in ts


def test_dynamodb_pitr_enabled():
    c = Component(id="t", service="dynamodb", provider="aws", label="T", tier=3)
    ts = render_aws(c, _spec(c))
    assert "pointInTimeRecovery: {" in ts


# --- AWS SQS ----------------------------------------------------------------


def test_sqs_managed_sse_enabled():
    c = Component(id="q", service="sqs", provider="aws", label="Q", tier=2)
    ts = render_aws(c, _spec(c))
    assert "sqsManagedSseEnabled: true," in ts


# --- AWS Kinesis ------------------------------------------------------------


def test_kinesis_kms_encryption():
    c = Component(id="ks", service="kinesis", provider="aws", label="K", tier=2)
    ts = render_aws(c, _spec(c))
    assert 'encryptionType: "KMS",' in ts
    assert 'kmsKeyId: "alias/aws/kinesis",' in ts


# --- AWS ECR ----------------------------------------------------------------


def test_ecr_scan_on_push_and_aes256():
    c = Component(id="img", service="ecr", provider="aws", label="Img", tier=2)
    ts = render_aws(c, _spec(c))
    assert "scanOnPush: true," in ts
    assert 'encryptionType: "AES256",' in ts
    assert 'imageTagMutability: "IMMUTABLE",' in ts


# --- AWS CloudFront ---------------------------------------------------------


def test_cloudfront_redirects_to_https():
    c = Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0)
    ts = render_aws(c, _spec(c))
    assert 'viewerProtocolPolicy: "redirect-to-https",' in ts


def test_cloudfront_minimum_tls_1_2():
    c = Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0)
    ts = render_aws(c, _spec(c))
    assert 'minimumProtocolVersion: "TLSv1.2_2021",' in ts


# --- AWS CloudTrail ---------------------------------------------------------


def test_cloudtrail_log_file_validation_enabled():
    c = Component(id="ct", service="cloudtrail", provider="aws", label="CT", tier=2)
    ts = render_aws(c, _spec(c))
    assert "enableLogFileValidation: true," in ts
    assert "isMultiRegionTrail: true," in ts


# --- AWS Lambda -------------------------------------------------------------


def test_lambda_does_not_hardcode_inline_zip_filename():
    c = Component(id="fn", service="lambda", provider="aws", label="Fn", tier=2)
    ts = render_aws(c, _spec(c))
    # No literal `code: "lambda.zip"` string property set on the function.
    assert 'code: "lambda.zip"' not in ts
    # Caller-driven config variable instead.
    assert "lambdaDeploymentPackage" in ts
    # And there's a TODO guiding the deployer.
    assert "TODO" in ts and "deployment package" in ts


# --- AWS service coverage ---------------------------------------------------


@pytest.mark.parametrize(
    "svc",
    [
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
    ],
)
def test_aws_service_renders_without_unsupported_marker(svc: str):
    c = Component(id=f"r_{svc}", service=svc, provider="aws", label=svc.upper(), tier=2)
    ts = render_aws(c, _spec(c))
    assert "Unsupported AWS service" not in ts


# --- GCP --------------------------------------------------------------------


@pytest.mark.parametrize(
    "svc",
    [
        "compute_engine",
        "gke",
        "cloud_sql",
        "cloud_storage",
        "cloud_run",
        "pub_sub",
        "bigquery",
    ],
)
def test_gcp_service_renders(svc: str):
    c = Component(id=f"r_{svc}", service=svc, provider="gcp", label=svc.upper(), tier=2)
    ts = render_gcp(c, _spec(c))
    assert "Unsupported GCP service" not in ts


def test_gcp_storage_uniform_access_and_public_prevention():
    c = Component(id="bk", service="cloud_storage", provider="gcp", label="B", tier=3)
    ts = render_gcp(c, _spec(c))
    assert "uniformBucketLevelAccess: true," in ts
    assert 'publicAccessPrevention: "enforced",' in ts


def test_gcp_cloud_sql_deletion_protection():
    c = Component(id="db", service="cloud_sql", provider="gcp", label="DB", tier=3)
    ts = render_gcp(c, _spec(c))
    assert "deletionProtection: true," in ts


# --- Azure ------------------------------------------------------------------


@pytest.mark.parametrize(
    "svc",
    [
        "virtual_machines",
        "aks",
        "azure_sql",
        "blob_storage",
        "azure_functions",
        "app_gateway",
    ],
)
def test_azure_service_renders(svc: str):
    c = Component(id=f"r_{svc}", service=svc, provider="azure", label=svc.upper(), tier=2)
    ts = render_azure(c, _spec(c))
    assert "Unsupported Azure service" not in ts


def test_azure_blob_storage_tls_1_2_minimum():
    c = Component(id="blob", service="blob_storage", provider="azure", label="Blob", tier=3)
    ts = render_azure(c, _spec(c))
    assert 'minimumTlsVersion: "TLS1_2",' in ts
    assert "allowBlobPublicAccess: false," in ts


def test_azure_sql_minimal_tls_1_2():
    c = Component(id="sql", service="azure_sql", provider="azure", label="SQL", tier=3)
    ts = render_azure(c, _spec(c))
    assert 'minimalTlsVersion: "1.2",' in ts


# --- Top-level render -------------------------------------------------------


def test_top_level_render_includes_aws_preamble_when_aws_present():
    spec = _spec(Component(id="bk", service="s3", provider="aws", label="B", tier=3))
    ts = render_pulumi_ts(spec)
    assert 'import * as aws from "@pulumi/aws";' in ts
    assert 'import * as pulumi from "@pulumi/pulumi";' in ts


def test_top_level_render_includes_gcp_preamble_when_gcp_present():
    spec = ArchSpec(
        name="GCP",
        provider="gcp",
        region="us-central1",
        components=[Component(id="bk", service="cloud_storage", provider="gcp", label="B", tier=3)],
    )
    ts = render_pulumi_ts(spec)
    assert 'import * as gcp from "@pulumi/gcp";' in ts


def test_top_level_render_includes_azure_preamble_when_azure_present():
    spec = ArchSpec(
        name="Azure",
        provider="azure",
        region="eastus",
        components=[Component(id="vm", service="virtual_machines", provider="azure", label="V", tier=2)],
    )
    ts = render_pulumi_ts(spec)
    assert 'import * as azure from "@pulumi/azure-native";' in ts
    assert "ResourceGroup" in ts


def test_top_level_render_exports_architecture_name():
    spec = _spec(Component(id="bk", service="s3", provider="aws", label="B", tier=3))
    ts = render_pulumi_ts(spec)
    assert "export const architectureName =" in ts


def test_top_level_render_escapes_arch_name():
    spec = ArchSpec(
        name='Hostile "name"',
        provider="aws",
        region="us-east-1",
        components=[Component(id="bk", service="s3", provider="aws", label="B", tier=3)],
    )
    ts = render_pulumi_ts(spec)
    assert 'export const architectureName = "Hostile \\"name\\"";' in ts
