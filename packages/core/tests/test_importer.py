"""Tests for the Terraform state importer."""

from __future__ import annotations

from pathlib import Path

import pytest
from cloudwright.importer import import_spec
from cloudwright.importer.terraform_state import TerraformStateImporter

FIXTURES = Path(__file__).parent / "fixtures"


class TestTerraformStateImporter:
    def test_can_import_tfstate_extension(self):
        imp = TerraformStateImporter()
        assert imp.can_import(str(FIXTURES / "aws.tfstate"))

    def test_can_import_json_with_tfstate_in_name(self):
        imp = TerraformStateImporter()
        assert imp.can_import("terraform.tfstate.json")

    def test_cannot_import_generic_json(self):
        imp = TerraformStateImporter()
        assert not imp.can_import("config.json")

    def test_format_name(self):
        assert TerraformStateImporter().format_name == "terraform"


class TestAwsImport:
    def test_aws_spec_provider(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        assert spec.provider == "aws"

    def test_aws_spec_has_components(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        assert len(spec.components) >= 4

    def test_aws_services_detected(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        services = {c.service for c in spec.components}
        assert "ec2" in services
        assert "rds" in services
        assert "s3" in services

    def test_aws_data_resources_excluded(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        # aws_ami is a data resource — should not be imported
        services = {c.service for c in spec.components}
        assert "ami" not in services

    def test_aws_config_extraction(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        db = next((c for c in spec.components if c.service == "rds"), None)
        assert db is not None
        assert db.config.get("engine") == "postgres"
        assert db.config.get("multi_az") is True
        assert db.config.get("encryption") is True
        assert db.config.get("storage_gb") == 100

    def test_aws_ec2_instance_type(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        ec2 = next((c for c in spec.components if c.service == "ec2"), None)
        assert ec2 is not None
        assert ec2.config.get("instance_type") == "t3.medium"

    def test_aws_connections_inferred(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        assert len(spec.connections) > 0

    def test_aws_lb_to_compute_connection(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        alb = next((c for c in spec.components if c.service == "alb"), None)
        ec2 = next((c for c in spec.components if c.service == "ec2"), None)
        if alb and ec2:
            conn = next((c for c in spec.connections if c.source == alb.id and c.target == ec2.id), None)
            assert conn is not None

    def test_aws_cdn_to_lb_connection(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        cdn = next((c for c in spec.components if c.service == "cloudfront"), None)
        alb = next((c for c in spec.components if c.service == "alb"), None)
        if cdn and alb:
            conn = next((c for c in spec.connections if c.source == cdn.id), None)
            assert conn is not None

    def test_aws_component_ids_are_iac_safe(self):
        import re

        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")
        for comp in spec.components:
            assert pattern.match(comp.id), f"ID {comp.id!r} is not IaC-safe"

    def test_aws_tiers_set(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        for comp in spec.components:
            assert comp.tier in (0, 1, 2, 3, 4)


class TestGcpImport:
    def test_gcp_spec_provider(self):
        spec = import_spec(str(FIXTURES / "gcp.tfstate"))
        assert spec.provider == "gcp"

    def test_gcp_services_detected(self):
        spec = import_spec(str(FIXTURES / "gcp.tfstate"))
        services = {c.service for c in spec.components}
        assert "compute_engine" in services
        assert "cloud_sql" in services
        assert "cloud_storage" in services

    def test_gcp_data_resources_excluded(self):
        spec = import_spec(str(FIXTURES / "gcp.tfstate"))
        # google_project is a data resource
        services = {c.service for c in spec.components}
        assert "project" not in services

    def test_gcp_machine_type_extracted(self):
        spec = import_spec(str(FIXTURES / "gcp.tfstate"))
        vm = next((c for c in spec.components if c.service == "compute_engine"), None)
        assert vm is not None
        assert vm.config.get("instance_type") == "e2-medium"


class TestAzureImport:
    def test_azure_spec_provider(self):
        spec = import_spec(str(FIXTURES / "azure.tfstate"))
        assert spec.provider == "azure"

    def test_azure_services_detected(self):
        spec = import_spec(str(FIXTURES / "azure.tfstate"))
        services = {c.service for c in spec.components}
        assert "virtual_machines" in services
        assert "azure_sql" in services
        assert "blob_storage" in services
        assert "aks" in services

    def test_azure_data_resources_excluded(self):
        spec = import_spec(str(FIXTURES / "azure.tfstate"))
        services = {c.service for c in spec.components}
        assert "client_config" not in services

    def test_azure_vm_size_extracted(self):
        spec = import_spec(str(FIXTURES / "azure.tfstate"))
        vm = next((c for c in spec.components if c.service == "virtual_machines"), None)
        assert vm is not None
        assert vm.config.get("instance_type") == "Standard_D2s_v5"


class TestServerlessImport:
    def test_serverless_services(self):
        spec = import_spec(str(FIXTURES / "aws_serverless.tfstate"))
        services = {c.service for c in spec.components}
        assert "lambda" in services
        assert "dynamodb" in services
        assert "s3" in services

    def test_api_to_lambda_connection(self):
        spec = import_spec(str(FIXTURES / "aws_serverless.tfstate"))
        api = next((c for c in spec.components if c.service == "api_gateway"), None)
        fn = next((c for c in spec.components if c.service == "lambda"), None)
        if api and fn:
            conn = next((c for c in spec.connections if c.source == api.id and c.target == fn.id), None)
            assert conn is not None

    def test_lambda_memory_extracted(self):
        spec = import_spec(str(FIXTURES / "aws_serverless.tfstate"))
        fn = next((c for c in spec.components if c.service == "lambda"), None)
        assert fn is not None
        assert fn.config.get("memory_mb") == 512


class TestImportSpecApi:
    def test_import_spec_auto_detects_terraform(self):
        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        assert spec is not None
        assert len(spec.components) > 0

    def test_import_spec_explicit_format(self):
        spec = import_spec(str(FIXTURES / "gcp.tfstate"), fmt="terraform")
        assert spec.provider == "gcp"

    def test_import_spec_unknown_format_raises(self):
        with pytest.raises(ValueError, match="Unknown import format"):
            import_spec(str(FIXTURES / "aws.tfstate"), fmt="pulumi")

    def test_spec_is_valid_archspec(self):
        from cloudwright.spec import ArchSpec

        spec = import_spec(str(FIXTURES / "aws.tfstate"))
        assert isinstance(spec, ArchSpec)
        assert spec.name
        assert spec.provider in ("aws", "gcp", "azure")


class TestV3Format:
    def test_v3_parse(self, tmp_path):
        """Verify the v3 format parser works."""
        v3_state = {
            "version": 3,
            "modules": [
                {
                    "path": ["root"],
                    "resources": {
                        "aws_instance.web": {
                            "type": "aws_instance",
                            "name": "web",
                            "mode": "managed",
                            "primary": {
                                "id": "i-123",
                                "attributes": {"instance_type": "m5.large"},
                            },
                        },
                        "aws_s3_bucket.data": {
                            "type": "aws_s3_bucket",
                            "name": "data",
                            "mode": "managed",
                            "primary": {"id": "my-bucket", "attributes": {}},
                        },
                    },
                }
            ],
        }
        import json

        state_file = tmp_path / "v3.tfstate"
        state_file.write_text(json.dumps(v3_state))

        spec = import_spec(str(state_file))
        services = {c.service for c in spec.components}
        assert "ec2" in services
        assert "s3" in services
