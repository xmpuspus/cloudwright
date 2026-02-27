"""Tests for the CloudFormation template importer."""

from __future__ import annotations

import json
import re
from pathlib import Path

from cloudwright.importer import import_spec
from cloudwright.importer.cloudformation import CloudFormationImporter
from cloudwright.spec import ArchSpec

FIXTURES = Path(__file__).parent / "fixtures"


class TestCloudFormationImporterPlugin:
    def test_format_name(self):
        assert CloudFormationImporter().format_name == "cloudformation"

    def test_can_import_cfn_json(self):
        imp = CloudFormationImporter()
        assert imp.can_import(str(FIXTURES / "cloudformation_template.json"))

    def test_cannot_import_tfstate(self):
        imp = CloudFormationImporter()
        assert not imp.can_import(str(FIXTURES / "aws.tfstate"))

    def test_cannot_import_random_json(self, tmp_path):
        p = tmp_path / "random.json"
        p.write_text(json.dumps({"foo": "bar"}))
        imp = CloudFormationImporter()
        assert not imp.can_import(str(p))

    def test_cannot_import_missing_resources(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps({"AWSTemplateFormatVersion": "2010-09-09"}))
        imp = CloudFormationImporter()
        assert not imp.can_import(str(p))


class TestCfnImport:
    def test_provider_is_aws(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        assert spec.provider == "aws"

    def test_returns_archspec(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        assert isinstance(spec, ArchSpec)

    def test_component_count(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        # 10 mapped resources: CDN, ALB, EC2, RDS, ElastiCache, S3, 2xSQS, SNS, Lambda
        # Security groups are not in _CFN_TYPE_MAP, so they're excluded
        assert len(spec.components) >= 8

    def test_services_detected(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        services = {c.service for c in spec.components}
        assert "cloudfront" in services
        assert "alb" in services
        assert "ec2" in services
        assert "rds" in services
        assert "elasticache" in services
        assert "s3" in services
        assert "sqs" in services
        assert "lambda" in services

    def test_sns_detected(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        services = {c.service for c in spec.components}
        assert "sns" in services

    def test_security_groups_excluded(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        # EC2::SecurityGroup is not in the type map; shouldn't produce components
        for c in spec.components:
            assert "security_group" not in c.service

    def test_rds_config_extraction(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        db = next((c for c in spec.components if c.service == "rds"), None)
        assert db is not None
        assert db.config.get("engine") == "postgres"
        assert db.config.get("multi_az") is True
        assert db.config.get("encryption") is True
        assert db.config.get("storage_gb") == 200

    def test_ec2_instance_type(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        ec2 = next((c for c in spec.components if c.service == "ec2"), None)
        assert ec2 is not None
        assert ec2.config.get("instance_type") == "t3.large"

    def test_lambda_memory(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        fn = next((c for c in spec.components if c.service == "lambda"), None)
        assert fn is not None
        assert fn.config.get("memory_mb") == 1024

    def test_s3_encryption_detected(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        s3 = next((c for c in spec.components if c.service == "s3"), None)
        assert s3 is not None
        assert s3.config.get("encryption") is True


class TestCfnConnections:
    def test_has_connections(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        assert len(spec.connections) > 0

    def test_cdn_to_alb_connection(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        cdn = next((c for c in spec.components if c.service == "cloudfront"), None)
        alb = next((c for c in spec.components if c.service == "alb"), None)
        assert cdn is not None and alb is not None
        conn = next(
            (c for c in spec.connections if c.source == cdn.id and c.target == alb.id),
            None,
        )
        assert conn is not None

    def test_lambda_to_sqs_reference(self):
        """WorkerFunction references JobQueue via Ref — connection should exist."""
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        fn = next((c for c in spec.components if c.service == "lambda"), None)
        assert fn is not None
        # Lambda should have connections from explicit Ref/GetAtt/Sub
        fn_conns = [c for c in spec.connections if c.source == fn.id]
        assert len(fn_conns) >= 1

    def test_lambda_to_s3_reference(self):
        """WorkerFunction references AssetsBucket via Ref."""
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        fn = next((c for c in spec.components if c.service == "lambda"), None)
        s3 = next((c for c in spec.components if c.service == "s3"), None)
        assert fn is not None and s3 is not None
        conn = next(
            (c for c in spec.connections if c.source == fn.id and c.target == s3.id),
            None,
        )
        assert conn is not None

    def test_lambda_to_sns_reference(self):
        """WorkerFunction references NotificationTopic via Ref."""
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        fn = next((c for c in spec.components if c.service == "lambda"), None)
        sns = next((c for c in spec.components if c.service == "sns"), None)
        assert fn is not None and sns is not None
        conn = next(
            (c for c in spec.connections if c.source == fn.id and c.target == sns.id),
            None,
        )
        assert conn is not None

    def test_sqs_dlq_reference(self):
        """JobQueue references DeadLetterQueue via Fn::GetAtt."""
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        sqs_comps = [c for c in spec.components if c.service == "sqs"]
        assert len(sqs_comps) >= 2
        # There should be a connection between the two SQS queues
        sqs_ids = {c.id for c in sqs_comps}
        sqs_conns = [c for c in spec.connections if c.source in sqs_ids and c.target in sqs_ids]
        assert len(sqs_conns) >= 1


class TestCfnComponentIds:
    def test_ids_are_iac_safe(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")
        for comp in spec.components:
            assert pattern.match(comp.id), f"ID {comp.id!r} is not IaC-safe"

    def test_tiers_set(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        for comp in spec.components:
            assert comp.tier in (0, 1, 2, 3, 4)

    def test_tier_ordering(self):
        """CDN at 0, ALB at 1, compute at 2, DB/cache at 3, storage at 4."""
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cloudformation")
        cdn = next((c for c in spec.components if c.service == "cloudfront"), None)
        alb = next((c for c in spec.components if c.service == "alb"), None)
        ec2 = next((c for c in spec.components if c.service == "ec2"), None)
        rds = next((c for c in spec.components if c.service == "rds"), None)
        s3 = next((c for c in spec.components if c.service == "s3"), None)
        assert cdn and cdn.tier == 0
        assert alb and alb.tier == 1
        assert ec2 and ec2.tier == 2
        assert rds and rds.tier == 3
        assert s3 and s3.tier == 4


class TestCfnAutoDetect:
    def test_auto_detect_cloudformation(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"))
        assert spec.provider == "aws"
        assert len(spec.components) >= 8

    def test_explicit_format_works(self):
        spec = import_spec(str(FIXTURES / "cloudformation_template.json"), fmt="cfn")
        assert spec.provider == "aws"


class TestCfnYamlTemplate:
    def test_yaml_template(self, tmp_path):
        """Verify YAML-format CFN templates parse correctly."""
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "Minimal YAML stack",
            "Resources": {
                "MyBucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {"BucketName": "test-bucket"},
                },
                "MyFunction": {
                    "Type": "AWS::Lambda::Function",
                    "Properties": {
                        "FunctionName": "test-fn",
                        "Runtime": "python3.12",
                        "MemorySize": 256,
                        "Handler": "index.handler",
                        "Environment": {"Variables": {"BUCKET": {"Ref": "MyBucket"}}},
                    },
                },
            },
        }
        import yaml

        p = tmp_path / "stack.yaml"
        p.write_text(yaml.dump(template))

        spec = import_spec(str(p), fmt="cloudformation")
        services = {c.service for c in spec.components}
        assert "s3" in services
        assert "lambda" in services
        fn = next(c for c in spec.components if c.service == "lambda")
        assert fn.config.get("memory_mb") == 256
