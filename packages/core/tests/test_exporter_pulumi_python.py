"""Tests for the Pulumi Python exporter.

Mirrors ``test_exporter_pulumi_ts.py``: same safe-by-default posture, same
escape guarantees on user-controlled strings.
"""

from __future__ import annotations

import pytest
from cloudwright.exporter.pulumi import render_pulumi_python
from cloudwright.exporter.pulumi.aws_python import render_resource as render_aws
from cloudwright.exporter.pulumi.azure_python import render_resource as render_azure
from cloudwright.exporter.pulumi.common import _py_string
from cloudwright.exporter.pulumi.gcp_python import render_resource as render_gcp
from cloudwright.spec import ArchSpec, Component


def _spec(component: Component) -> ArchSpec:
    return ArchSpec(
        name="Pulumi PY",
        provider=component.provider,
        region="us-east-1",
        components=[component],
        connections=[],
    )


# --- Escape helpers ---------------------------------------------------------


def test_py_string_escapes_double_quote():
    assert _py_string('a"b') == '"a\\"b"'


def test_py_string_escapes_backslash():
    assert _py_string("a\\b") == '"a\\\\b"'


def test_py_string_escapes_newline():
    assert _py_string("a\nb") == '"a\\nb"'


def test_hostile_label_escaped_in_py_output():
    c = Component(id="bk", service="s3", provider="aws", label='hi"; danger ##', tier=3)
    py = render_aws(c, _spec(c))
    assert 'hi\\";' in py
    assert 'hi"; danger ##' not in py


# --- AWS S3 -----------------------------------------------------------------


def test_s3_emits_public_access_block():
    c = Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3)
    py = render_aws(c, _spec(c))
    assert "aws.s3.BucketPublicAccessBlock" in py
    assert "block_public_acls=True," in py
    assert "block_public_policy=True," in py
    assert "ignore_public_acls=True," in py
    assert "restrict_public_buckets=True," in py


def test_s3_emits_aes256_sse():
    c = Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3)
    py = render_aws(c, _spec(c))
    assert "BucketServerSideEncryptionConfigurationV2" in py
    assert 'sse_algorithm="AES256",' in py


def test_s3_emits_versioning_enabled():
    c = Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3)
    py = render_aws(c, _spec(c))
    assert "BucketVersioningV2" in py
    assert 'status="Enabled",' in py


def test_s3_force_destroy_false():
    c = Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3)
    py = render_aws(c, _spec(c))
    assert "force_destroy=False," in py


# --- AWS RDS ----------------------------------------------------------------


def test_rds_storage_encrypted():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    py = render_aws(c, _spec(c))
    assert "storage_encrypted=True," in py


def test_rds_backup_retention_seven():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    py = render_aws(c, _spec(c))
    assert "backup_retention_period=7," in py


def test_rds_deletion_protection():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    py = render_aws(c, _spec(c))
    assert "deletion_protection=True," in py


def test_rds_skip_final_snapshot_false():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    py = render_aws(c, _spec(c))
    assert "skip_final_snapshot=False," in py


def test_rds_multi_az_when_replicas_present():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={"replicas": 2})
    py = render_aws(c, _spec(c))
    assert "multi_az=True," in py


# --- AWS EC2 ----------------------------------------------------------------


def test_ec2_imdsv2_metadata_options():
    c = Component(id="web", service="ec2", provider="aws", label="Web", tier=2)
    py = render_aws(c, _spec(c))
    assert 'http_tokens="required",' in py
    assert 'http_endpoint="enabled",' in py
    assert "http_put_response_hop_limit=1," in py


def test_ec2_root_block_device_encrypted():
    c = Component(id="web", service="ec2", provider="aws", label="Web", tier=2)
    py = render_aws(c, _spec(c))
    assert "encrypted=True," in py


# --- AWS DynamoDB / SQS / Kinesis / ECR -------------------------------------


def test_dynamodb_sse_and_pitr():
    c = Component(id="t", service="dynamodb", provider="aws", label="T", tier=3)
    py = render_aws(c, _spec(c))
    assert "TableServerSideEncryptionArgs" in py
    assert "TablePointInTimeRecoveryArgs" in py
    assert "enabled=True," in py


def test_sqs_managed_sse():
    c = Component(id="q", service="sqs", provider="aws", label="Q", tier=2)
    py = render_aws(c, _spec(c))
    assert "sqs_managed_sse_enabled=True," in py


def test_kinesis_kms_encryption():
    c = Component(id="ks", service="kinesis", provider="aws", label="K", tier=2)
    py = render_aws(c, _spec(c))
    assert 'encryption_type="KMS",' in py
    assert 'kms_key_id="alias/aws/kinesis",' in py


def test_ecr_scan_and_aes256():
    c = Component(id="img", service="ecr", provider="aws", label="Img", tier=2)
    py = render_aws(c, _spec(c))
    assert "scan_on_push=True," in py
    assert 'encryption_type="AES256",' in py
    assert 'image_tag_mutability="IMMUTABLE",' in py


# --- AWS CloudFront / CloudTrail / Lambda -----------------------------------


def test_cloudfront_redirects_and_tls_minimum():
    c = Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0)
    py = render_aws(c, _spec(c))
    assert 'viewer_protocol_policy="redirect-to-https",' in py
    assert 'minimum_protocol_version="TLSv1.2_2021",' in py


def test_cloudtrail_log_validation_and_multi_region():
    c = Component(id="ct", service="cloudtrail", provider="aws", label="CT", tier=2)
    py = render_aws(c, _spec(c))
    assert "is_multi_region_trail=True," in py
    assert "enable_log_file_validation=True," in py


def test_lambda_no_inline_zip_and_has_todo():
    c = Component(id="fn", service="lambda", provider="aws", label="Fn", tier=2)
    py = render_aws(c, _spec(c))
    assert 'code="lambda.zip"' not in py
    assert "lambda_deployment_package" in py
    assert "TODO" in py and "deployment package" in py


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
    py = render_aws(c, _spec(c))
    assert "Unsupported AWS service" not in py


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
    py = render_gcp(c, _spec(c))
    assert "Unsupported GCP service" not in py


def test_gcp_storage_uniform_access_and_public_prevention():
    c = Component(id="bk", service="cloud_storage", provider="gcp", label="B", tier=3)
    py = render_gcp(c, _spec(c))
    assert "uniform_bucket_level_access=True," in py
    assert 'public_access_prevention="enforced",' in py


def test_gcp_cloud_sql_deletion_protection():
    c = Component(id="db", service="cloud_sql", provider="gcp", label="DB", tier=3)
    py = render_gcp(c, _spec(c))
    assert "deletion_protection=True," in py


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
    py = render_azure(c, _spec(c))
    assert "Unsupported Azure service" not in py


def test_azure_blob_storage_tls_1_2_minimum():
    c = Component(id="blob", service="blob_storage", provider="azure", label="Blob", tier=3)
    py = render_azure(c, _spec(c))
    assert 'minimum_tls_version="TLS1_2",' in py
    assert "allow_blob_public_access=False," in py


def test_azure_sql_minimal_tls_1_2():
    c = Component(id="sql", service="azure_sql", provider="azure", label="SQL", tier=3)
    py = render_azure(c, _spec(c))
    assert 'minimal_tls_version="1.2",' in py


# --- Top-level render -------------------------------------------------------


def test_top_level_render_includes_aws_preamble():
    spec = _spec(Component(id="bk", service="s3", provider="aws", label="B", tier=3))
    py = render_pulumi_python(spec)
    assert "import pulumi_aws as aws" in py
    assert "import pulumi" in py


def test_top_level_render_includes_gcp_preamble():
    spec = ArchSpec(
        name="GCP",
        provider="gcp",
        region="us-central1",
        components=[Component(id="bk", service="cloud_storage", provider="gcp", label="B", tier=3)],
    )
    py = render_pulumi_python(spec)
    assert "import pulumi_gcp as gcp" in py


def test_top_level_render_includes_azure_preamble():
    spec = ArchSpec(
        name="Azure",
        provider="azure",
        region="eastus",
        components=[Component(id="vm", service="virtual_machines", provider="azure", label="V", tier=2)],
    )
    py = render_pulumi_python(spec)
    assert "import pulumi_azure_native as azure_native" in py
    assert "ResourceGroup" in py


def test_top_level_render_exports_architecture_name():
    spec = _spec(Component(id="bk", service="s3", provider="aws", label="B", tier=3))
    py = render_pulumi_python(spec)
    assert "pulumi.export(" in py


def test_top_level_render_escapes_arch_name():
    spec = ArchSpec(
        name='Hostile "name"',
        provider="aws",
        region="us-east-1",
        components=[Component(id="bk", service="s3", provider="aws", label="B", tier=3)],
    )
    py = render_pulumi_python(spec)
    assert 'pulumi.export("architecture_name", "Hostile \\"name\\"")' in py
