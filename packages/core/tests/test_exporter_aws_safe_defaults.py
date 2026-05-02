"""Tests that the AWS Terraform exporter ships safe defaults.

These tests pin the v1.3 hardening commitments described in SECURITY.md:
- S3 buckets get public-access blocks, AES256 SSE, and versioning.
- RDS storage is encrypted, has backups, deletion protection, no skip-final-snapshot.
- EC2 instances enforce IMDSv2 via metadata_options.
- EBS volumes are encrypted at rest.
- CloudFront distributions enforce TLS 1.2+ on the viewer cert.
- Lambda no longer hardcodes lambda.zip; the package source is variable-driven.
"""

from __future__ import annotations

from cloudwright.exporter.terraform import render
from cloudwright.exporter.terraform.aws import render_resource
from cloudwright.spec import ArchSpec, Component


def _spec_with(component: Component) -> ArchSpec:
    return ArchSpec(
        name="Safe Defaults",
        provider="aws",
        region="us-east-1",
        components=[component],
        connections=[],
    )


# --- S3 ---------------------------------------------------------------------


def test_s3_emits_public_access_block_with_all_four_true():
    c = Component(id="data_bucket", service="s3", provider="aws", label="Data Bucket", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert 'resource "aws_s3_bucket_public_access_block" "data_bucket"' in hcl
    assert "block_public_acls       = true" in hcl
    assert "block_public_policy     = true" in hcl
    assert "ignore_public_acls      = true" in hcl
    assert "restrict_public_buckets = true" in hcl


def test_s3_emits_aes256_server_side_encryption():
    c = Component(id="data_bucket", service="s3", provider="aws", label="Data Bucket", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert 'resource "aws_s3_bucket_server_side_encryption_configuration" "data_bucket"' in hcl
    assert 'sse_algorithm = "AES256"' in hcl


def test_s3_emits_versioning_enabled():
    c = Component(id="data_bucket", service="s3", provider="aws", label="Data Bucket", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert 'resource "aws_s3_bucket_versioning" "data_bucket"' in hcl
    assert 'status = "Enabled"' in hcl


# --- RDS --------------------------------------------------------------------


def test_rds_renders_storage_encrypted_true():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert "storage_encrypted       = true" in hcl


def test_rds_renders_backup_retention_seven_days():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert "backup_retention_period = 7" in hcl


def test_rds_renders_deletion_protection_true():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert "deletion_protection     = true" in hcl


def test_rds_skip_final_snapshot_is_false():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert "skip_final_snapshot     = false" in hcl


def test_rds_multi_az_when_replicas_present():
    c = Component(
        id="db",
        service="rds",
        provider="aws",
        label="DB",
        tier=3,
        config={"replicas": 2},
    )
    hcl = render_resource(c, _spec_with(c))
    assert "multi_az                = true" in hcl


def test_rds_multi_az_off_for_single_node():
    c = Component(id="db", service="rds", provider="aws", label="DB", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert "multi_az                = false" in hcl


# --- EC2 (IMDSv2) -----------------------------------------------------------


def test_ec2_renders_imdsv2_metadata_options():
    c = Component(id="web", service="ec2", provider="aws", label="Web", tier=2)
    hcl = render_resource(c, _spec_with(c))
    assert "metadata_options {" in hcl
    assert 'http_tokens                 = "required"' in hcl
    assert 'http_endpoint               = "enabled"' in hcl
    assert "http_put_response_hop_limit = 1" in hcl


def test_ec2_root_block_device_encrypted():
    c = Component(id="web", service="ec2", provider="aws", label="Web", tier=2)
    hcl = render_resource(c, _spec_with(c))
    assert "root_block_device {" in hcl
    assert "encrypted = true" in hcl


# --- EBS --------------------------------------------------------------------


def test_ebs_volume_encrypted_by_default():
    c = Component(id="vol", service="ebs", provider="aws", label="Volume", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert "encrypted         = true" in hcl


# --- CloudFront -------------------------------------------------------------


def test_cloudfront_redirects_to_https():
    c = Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0)
    hcl = render_resource(c, _spec_with(c))
    assert 'viewer_protocol_policy = "redirect-to-https"' in hcl


def test_cloudfront_enforces_tls_1_2_minimum():
    c = Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0)
    hcl = render_resource(c, _spec_with(c))
    assert 'minimum_protocol_version       = "TLSv1.2_2021"' in hcl


# --- Lambda -----------------------------------------------------------------


def test_lambda_does_not_hardcode_zip_filename():
    c = Component(id="fn", service="lambda", provider="aws", label="Fn", tier=2)
    hcl = render_resource(c, _spec_with(c))
    # No literal "lambda.zip" is produced as the filename in the resource block.
    assert 'filename      = "lambda.zip"' not in hcl
    # Caller-provided variable instead.
    assert "var.lambda_deployment_package" in hcl
    # And there's a TODO comment guiding the deployer.
    assert "TODO" in hcl and "deployment package" in hcl


# --- DynamoDB ---------------------------------------------------------------


def test_dynamodb_server_side_encryption_enabled():
    c = Component(id="tbl", service="dynamodb", provider="aws", label="Table", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert "server_side_encryption {" in hcl
    assert "enabled = true" in hcl


def test_dynamodb_point_in_time_recovery_enabled():
    c = Component(id="tbl", service="dynamodb", provider="aws", label="Table", tier=3)
    hcl = render_resource(c, _spec_with(c))
    assert "point_in_time_recovery {" in hcl


# --- Full render integration ------------------------------------------------


def test_full_render_includes_lambda_deployment_variable():
    spec = ArchSpec(
        name="App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="fn", service="lambda", provider="aws", label="Fn", tier=2),
        ],
    )
    hcl = render(spec)
    assert 'variable "lambda_deployment_package"' in hcl


def test_full_render_s3_block_appears_in_main_render():
    spec = ArchSpec(
        name="App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3),
        ],
    )
    hcl = render(spec)
    assert 'resource "aws_s3_bucket_public_access_block" "bk"' in hcl
    assert 'resource "aws_s3_bucket_server_side_encryption_configuration" "bk"' in hcl
    assert 'resource "aws_s3_bucket_versioning" "bk"' in hcl
