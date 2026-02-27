"""Tests for the CloudFormation template importer."""

from __future__ import annotations

import json
import re
from pathlib import Path

from cloudwright.importer import import_spec
from cloudwright.importer.cloudformation import CloudFormationImporter

FIXTURES = Path(__file__).parent / "fixtures"


class TestCloudFormationImporter:
    def test_can_import_cfn_yaml(self):
        imp = CloudFormationImporter()
        assert imp.can_import(str(FIXTURES / "three_tier.yaml"))

    def test_can_import_cfn_json(self):
        imp = CloudFormationImporter()
        assert imp.can_import(str(FIXTURES / "serverless_api.json"))

    def test_cannot_import_tfstate(self):
        imp = CloudFormationImporter()
        assert not imp.can_import(str(FIXTURES / "aws.tfstate"))

    def test_format_name(self):
        assert CloudFormationImporter().format_name == "cloudformation"


class TestThreeTierTemplate:
    def test_provider_is_aws(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        assert spec.provider == "aws"

    def test_name_from_description(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        assert spec.name == "Three-tier web application"

    def test_expected_services_present(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        services = {c.service for c in spec.components}
        assert "ec2" in services
        assert "rds" in services
        assert "s3" in services
        assert "waf" in services
        assert "cognito" in services

    def test_cdn_present(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        assert any(c.service == "cloudfront" for c in spec.components)

    def test_lb_present(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        assert any(c.service == "alb" for c in spec.components)

    def test_db_config_extracted(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        db = next(c for c in spec.components if c.service == "rds")
        assert db.config.get("engine") == "postgres"
        assert db.config.get("multi_az") is True
        assert db.config.get("encryption") is True
        assert db.config.get("storage_gb") == 100

    def test_s3_encryption_detected(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        s3 = next(c for c in spec.components if c.service == "s3")
        assert s3.config.get("encryption") is True

    def test_connections_inferred(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        assert len(spec.connections) > 0

    def test_cdn_connects_to_lb(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        cdn = next(c for c in spec.components if c.service == "cloudfront")
        lb = next(c for c in spec.components if c.service == "alb")
        conn = next((c for c in spec.connections if c.source == cdn.id and c.target == lb.id), None)
        assert conn is not None

    def test_component_ids_iac_safe(self):
        pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        for comp in spec.components:
            assert pattern.match(comp.id), f"ID {comp.id!r} is not IaC-safe"

    def test_tiers_set(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cloudformation")
        for comp in spec.components:
            assert comp.tier in (0, 1, 2, 3, 4)


class TestServerlessTemplate:
    def test_serverless_services(self):
        spec = import_spec(str(FIXTURES / "serverless_api.json"), fmt="cloudformation")
        services = {c.service for c in spec.components}
        assert "api_gateway" in services
        assert "lambda" in services
        assert "dynamodb" in services
        assert "s3" in services

    def test_lambda_memory_extracted(self):
        spec = import_spec(str(FIXTURES / "serverless_api.json"), fmt="cloudformation")
        fn = next(c for c in spec.components if c.service == "lambda")
        assert fn.config.get("memory_mb") == 512

    def test_api_to_lambda_connection(self):
        spec = import_spec(str(FIXTURES / "serverless_api.json"), fmt="cloudformation")
        api = next(c for c in spec.components if c.service == "api_gateway")
        fn = next(c for c in spec.components if c.service == "lambda")
        conn = next((c for c in spec.connections if c.source == api.id and c.target == fn.id), None)
        assert conn is not None


class TestAutoDetection:
    def test_auto_detects_cfn_yaml(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"))
        assert spec.provider == "aws"
        assert len(spec.components) > 0

    def test_auto_detects_cfn_json(self):
        spec = import_spec(str(FIXTURES / "serverless_api.json"))
        assert spec.provider == "aws"

    def test_cfn_alias_fmt(self):
        spec = import_spec(str(FIXTURES / "three_tier.yaml"), fmt="cfn")
        assert spec.provider == "aws"


class TestInlineTemplate:
    def test_minimal_template(self, tmp_path):
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "Minimal",
            "Resources": {
                "Web": {"Type": "AWS::EC2::Instance", "Properties": {"InstanceType": "t3.micro"}},
                "Bucket": {"Type": "AWS::S3::Bucket", "Properties": {}},
            },
        }
        p = tmp_path / "minimal.json"
        p.write_text(json.dumps(template))

        spec = import_spec(str(p), fmt="cloudformation")
        assert len(spec.components) == 2
        services = {c.service for c in spec.components}
        assert "ec2" in services
        assert "s3" in services

    def test_ec2_instance_type_extracted(self, tmp_path):
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "Web": {"Type": "AWS::EC2::Instance", "Properties": {"InstanceType": "m5.xlarge"}},
            },
        }
        p = tmp_path / "ec2.json"
        p.write_text(json.dumps(template))

        spec = import_spec(str(p), fmt="cloudformation")
        ec2 = next(c for c in spec.components if c.service == "ec2")
        assert ec2.config.get("instance_type") == "m5.xlarge"

    def test_unknown_resource_types_skipped(self, tmp_path):
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "CustomResource": {"Type": "Custom::MyThing", "Properties": {}},
                "IamRole": {"Type": "AWS::IAM::Role", "Properties": {}},
                "Web": {"Type": "AWS::EC2::Instance", "Properties": {}},
            },
        }
        p = tmp_path / "mixed.json"
        p.write_text(json.dumps(template))

        spec = import_spec(str(p), fmt="cloudformation")
        # Only ec2 should be imported
        assert len(spec.components) == 1
        assert spec.components[0].service == "ec2"
