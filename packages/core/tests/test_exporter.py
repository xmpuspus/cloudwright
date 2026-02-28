"""Tests for all exporters — terraform, cloudformation, mermaid, sbom, aibom, compliance."""

import json

from cloudwright.spec import ArchSpec, Boundary, Component, Connection, ValidationCheck, ValidationResult


def _spec_with_boundaries() -> ArchSpec:
    return ArchSpec(
        name="Bounded App",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
        connections=[Connection(source="web", target="db")],
        boundaries=[
            Boundary(id="vpc_main", kind="vpc", label="Main VPC", component_ids=["web", "db"]),
        ],
    )


def _sample_spec() -> ArchSpec:
    return ArchSpec(
        name="Test Web App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="cdn", service="cloudfront", provider="aws", label="CDN", tier=0),
            Component(
                id="alb",
                service="alb",
                provider="aws",
                label="Load Balancer",
                tier=1,
            ),
            Component(
                id="web",
                service="ec2",
                provider="aws",
                label="Web Servers",
                tier=2,
                config={"instance_type": "m5.large", "count": 2},
            ),
            Component(
                id="db",
                service="rds",
                provider="aws",
                label="PostgreSQL",
                tier=3,
                config={"engine": "postgres", "instance_class": "db.r5.large", "multi_az": True},
            ),
        ],
        connections=[
            Connection(source="cdn", target="alb", label="HTTPS", protocol="HTTPS", port=443),
            Connection(source="alb", target="web", label="HTTP", protocol="HTTP", port=80),
            Connection(source="web", target="db", label="PostgreSQL", protocol="TCP", port=5432),
        ],
    )


class TestTerraformExporter:
    def test_renders_hcl(self):
        from cloudwright.exporter.terraform import render

        hcl = render(_sample_spec())
        assert "terraform" in hcl.lower() or "provider" in hcl.lower()
        assert "aws" in hcl

    def test_includes_all_components(self):
        from cloudwright.exporter.terraform import render

        hcl = render(_sample_spec())
        # Should reference all components
        assert "web" in hcl.lower()
        assert "db" in hcl.lower() or "rds" in hcl.lower() or "postgresql" in hcl.lower()

    def test_writes_to_dir(self, tmp_path):
        from cloudwright.exporter.terraform import render

        spec = _sample_spec()
        content = render(spec)
        out_dir = tmp_path / "infra"
        out_dir.mkdir()
        (out_dir / "main.tf").write_text(content)
        assert (out_dir / "main.tf").exists()
        assert len((out_dir / "main.tf").read_text()) > 100

    def test_terraform_validate(self, tmp_path):
        """Generated Terraform passes `terraform validate`."""
        import shutil
        import subprocess

        if not shutil.which("terraform"):
            import pytest

            pytest.skip("terraform not installed")

        from cloudwright.exporter.terraform import render

        hcl = render(_sample_spec())
        tf_dir = tmp_path / "tf"
        tf_dir.mkdir()
        (tf_dir / "main.tf").write_text(hcl)

        init = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=str(tf_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert init.returncode == 0, f"terraform init failed: {init.stderr}"

        validate = subprocess.run(
            ["terraform", "validate"],
            cwd=str(tf_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert validate.returncode == 0, f"terraform validate failed: {validate.stderr}"


class TestCloudFormationExporter:
    def test_renders_yaml(self):
        from cloudwright.exporter.cloudformation import render

        cfn = render(_sample_spec())
        assert "AWSTemplateFormatVersion" in cfn
        assert "Resources" in cfn

    def test_skips_non_aws(self):
        from cloudwright.exporter.cloudformation import render

        spec = ArchSpec(
            name="GCP App",
            provider="gcp",
            region="us-central1",
            components=[
                Component(id="vm", service="compute_engine", provider="gcp", label="VM", tier=2),
            ],
            connections=[],
        )
        cfn = render(spec)
        # Should still produce valid template structure even with no AWS components
        assert "AWSTemplateFormatVersion" in cfn


class TestMermaidExporter:
    def test_renders_flowchart(self):
        from cloudwright.exporter.mermaid import render

        mmd = render(_sample_spec())
        assert "flowchart" in mmd.lower() or "graph" in mmd.lower()

    def test_includes_nodes(self):
        from cloudwright.exporter.mermaid import render

        mmd = render(_sample_spec())
        assert "cdn" in mmd.lower() or "CDN" in mmd
        assert "web" in mmd.lower() or "Web" in mmd

    def test_includes_edges(self):
        from cloudwright.exporter.mermaid import render

        mmd = render(_sample_spec())
        assert "-->" in mmd

    def test_includes_classdefs(self):
        from cloudwright.exporter.mermaid import render

        mmd = render(_sample_spec())
        assert "classDef compute" in mmd

    def test_database_cylinder_shape(self):
        from cloudwright.exporter.mermaid import render

        mmd = render(_sample_spec())
        # RDS is database category -> cylinder -> [(Label)] syntax
        assert "db[(" in mmd or "[(PostgreSQL)]" in mmd or "[(DB" in mmd

    def test_serverless_hexagon_shape(self):
        from cloudwright.exporter.mermaid import render

        spec = ArchSpec(
            name="Lambda App",
            components=[
                Component(id="fn", service="lambda", provider="aws", label="Handler", tier=2),
            ],
            connections=[],
        )
        mmd = render(spec)
        # Lambda is serverless -> hexagon -> {{Label}} syntax
        assert "{{" in mmd and "}}" in mmd

    def test_class_assignment(self):
        from cloudwright.exporter.mermaid import render

        mmd = render(_sample_spec())
        assert "class " in mmd

    def test_backward_compat_no_boundaries(self):
        from cloudwright.exporter.mermaid import render

        # Spec without boundaries should still use tier subgraphs
        mmd = render(_sample_spec())
        assert "subgraph" in mmd
        assert "Tier" in mmd

    def test_boundary_rendering(self):
        from cloudwright.exporter.mermaid import render

        mmd = render(_spec_with_boundaries())
        assert "Main VPC" in mmd
        assert "subgraph" in mmd
        # Tier labels should NOT appear when boundaries are used
        assert "Tier 2" not in mmd


class TestSBOMExporter:
    def test_renders_cyclonedx(self):
        from cloudwright.exporter.sbom import render

        sbom = render(_sample_spec())
        data = json.loads(sbom)
        assert data["bomFormat"] == "CycloneDX"
        assert data["specVersion"] == "1.5"

    def test_includes_components(self):
        from cloudwright.exporter.sbom import render

        sbom = render(_sample_spec())
        data = json.loads(sbom)
        assert len(data["components"]) >= 4

    def test_includes_dependencies(self):
        from cloudwright.exporter.sbom import render

        sbom = render(_sample_spec())
        data = json.loads(sbom)
        assert "dependencies" in data


class TestAIBOMExporter:
    def test_renders_aibom(self):
        from cloudwright.exporter.aibom import render

        aibom = render(_sample_spec())
        data = json.loads(aibom)
        assert "aibomVersion" in data
        assert "metadata" in data

    def test_includes_cloudwright_ai(self):
        from cloudwright.exporter.aibom import render

        aibom = render(_sample_spec())
        data = json.loads(aibom)
        assert len(data["aiComponents"]) >= 1
        assert data["aiComponents"][0]["name"] == "Cloudwright Architecture AI"

    def test_detects_ai_services(self):
        from cloudwright.exporter.aibom import render

        spec = ArchSpec(
            name="ML App",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="ml", service="sagemaker", provider="aws", label="SageMaker", tier=4),
            ],
            connections=[],
        )
        aibom = render(spec)
        data = json.loads(aibom)
        assert len(data["architectureAIServices"]) >= 1


def _sample_validation() -> ValidationResult:
    return ValidationResult(
        framework="HIPAA",
        passed=False,
        score=0.6,
        checks=[
            ValidationCheck(
                name="encryption_at_rest",
                category="data_protection",
                passed=False,
                severity="critical",
                detail="Missing encryption on: db",
                recommendation="Set encryption=true in config for all data stores.",
            ),
            ValidationCheck(
                name="audit_logging",
                category="monitoring",
                passed=True,
                severity="high",
                detail="Audit logging component present",
            ),
            ValidationCheck(
                name="access_control",
                category="identity",
                passed=True,
                severity="high",
                detail="IAM/auth component present",
            ),
        ],
    )


class TestComplianceReportExporter:
    def test_renders_markdown(self):
        from cloudwright.exporter.compliance_report import render

        md = render(_sample_spec(), _sample_validation())
        assert "# Compliance Report" in md
        assert "HIPAA" in md

    def test_includes_summary(self):
        from cloudwright.exporter.compliance_report import render

        md = render(_sample_spec(), _sample_validation())
        assert "Summary" in md
        assert "60%" in md

    def test_includes_pass_fail_markers(self):
        from cloudwright.exporter.compliance_report import render

        md = render(_sample_spec(), _sample_validation())
        assert "[PASS]" in md
        assert "[FAIL]" in md

    def test_includes_recommendation_for_failures(self):
        from cloudwright.exporter.compliance_report import render

        md = render(_sample_spec(), _sample_validation())
        assert "Recommendation" in md
        assert "encryption=true" in md

    def test_includes_component_inventory(self):
        from cloudwright.exporter.compliance_report import render

        md = render(_sample_spec(), _sample_validation())
        assert "Component Inventory" in md
        assert "cdn" in md
        assert "db" in md

    def test_includes_evidence_checklist(self):
        from cloudwright.exporter.compliance_report import render

        md = render(_sample_spec(), _sample_validation())
        assert "Evidence Checklist" in md
        assert "- [ ]" in md

    def test_component_encryption_status(self):
        from cloudwright.exporter.compliance_report import render

        spec = ArchSpec(
            name="Encrypted App",
            provider="aws",
            region="us-east-1",
            components=[
                Component(
                    id="db",
                    service="rds",
                    provider="aws",
                    label="DB",
                    tier=3,
                    config={"encryption": True},
                ),
            ],
            connections=[],
        )
        validation = ValidationResult(
            framework="HIPAA",
            passed=True,
            score=1.0,
            checks=[
                ValidationCheck(
                    name="encryption_at_rest",
                    category="data_protection",
                    passed=True,
                    severity="critical",
                    detail="All data stores have encryption enabled",
                )
            ],
        )
        md = render(spec, validation)
        assert "Yes" in md  # encrypted component shows Yes

    def test_formats_listed_in_formats_tuple(self):
        from cloudwright.exporter import FORMATS

        assert "compliance" in FORMATS


class TestTerraformSecurity:
    """Verify no hardcoded secrets or fake account IDs in Terraform output."""

    def test_no_hardcoded_ami(self):
        from cloudwright.exporter.terraform import render

        hcl = render(_sample_spec())
        assert "ami-0c55b159" not in hcl, "Hardcoded AMI found in Terraform output"

    def test_no_hardcoded_account_id(self):
        from cloudwright.exporter.terraform import render

        hcl = render(_sample_spec())
        assert "123456789012" not in hcl, "Hardcoded account ID found in Terraform output"

    def test_provider_versions_pinned_exactly(self):
        from cloudwright.exporter.terraform import render

        hcl = render(_sample_spec())
        # Should use exact pin (= X.Y.Z), not ~> range
        assert "~>" not in hcl, "Provider versions should use exact pins, not ~>"

    def test_uses_ssm_parameter_for_ami(self):
        from cloudwright.exporter.terraform import render

        hcl = render(_sample_spec())
        assert "aws_ssm_parameter" in hcl, "Should use SSM parameter for AMI lookup"

    def test_uses_data_source_for_azs(self):
        from cloudwright.exporter.terraform import render

        hcl = render(_sample_spec())
        assert "aws_availability_zones" in hcl, "Should use data source for availability zones"


class TestCloudFormationSecurity:
    """Verify no plaintext passwords or hardcoded account IDs in CloudFormation output."""

    def test_no_plaintext_password(self):
        from cloudwright.exporter.cloudformation import render

        # Spec with RDS to trigger password reference
        spec = ArchSpec(
            name="CFN Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={"engine": "postgres"}),
            ],
            connections=[],
        )
        cfn = render(spec)
        assert "changeme" not in cfn.lower(), "Plaintext password found in CloudFormation"
        assert "DBPassword" in cfn, "Should reference DBPassword parameter"

    def test_no_hardcoded_account_id(self):
        from cloudwright.exporter.cloudformation import render

        spec = ArchSpec(
            name="CFN Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="fn", service="lambda", provider="aws", label="Lambda", tier=2, config={}),
                Component(id="cluster", service="eks", provider="aws", label="EKS", tier=2, config={}),
            ],
            connections=[],
        )
        cfn = render(spec)
        assert "ACCOUNT_ID" not in cfn, "Hardcoded ACCOUNT_ID in CloudFormation"
        assert "AWS::AccountId" in cfn, "Should use AWS::AccountId pseudo-parameter"

    def test_db_password_parameter_has_noecho(self):
        import yaml as _yaml
        from cloudwright.exporter.cloudformation import render

        spec = ArchSpec(
            name="CFN Test",
            provider="aws",
            region="us-east-1",
            components=[
                Component(id="db", service="rds", provider="aws", label="DB", tier=3, config={"engine": "postgres"}),
            ],
            connections=[],
        )
        cfn = render(spec)
        template = _yaml.safe_load(cfn)
        assert template["Parameters"]["DBPassword"]["NoEcho"] is True


class TestD2Export:
    """Test D2 diagram exporter."""

    def test_renders_d2(self):
        from cloudwright.exporter.d2 import render

        d2 = render(_sample_spec())
        assert "# Test Web App" in d2
        assert "->" in d2

    def test_includes_tier_containers(self):
        from cloudwright.exporter.d2 import render

        d2 = render(_sample_spec())
        assert "Edge" in d2 or "tier_0" in d2
        assert "Compute" in d2 or "tier_2" in d2

    def test_d2_in_formats(self):
        from cloudwright.exporter import FORMATS

        assert "d2" in FORMATS

    def test_export_spec_dispatches_d2(self):
        from cloudwright.exporter import export_spec

        content = export_spec(_sample_spec(), "d2")
        assert "->" in content
        assert "Test Web App" in content

    def test_includes_theme(self):
        from cloudwright.exporter.d2 import render

        d2 = render(_sample_spec())
        assert "theme-id" in d2

    def test_node_has_shape(self):
        from cloudwright.exporter.d2 import render

        d2 = render(_sample_spec())
        # RDS is database -> cylinder
        assert "shape: cylinder" in d2

    def test_node_has_icon(self):
        from cloudwright.exporter.d2 import render

        d2 = render(_sample_spec())
        assert "icon:" in d2

    def test_boundary_containers(self):
        from cloudwright.exporter.d2 import render

        d2 = render(_spec_with_boundaries())
        assert "Main VPC" in d2
        # Tier containers should NOT appear when boundaries are present
        assert "tier_2" not in d2
        assert "tier_3" not in d2

    def test_backward_compat_tier_grouping(self):
        from cloudwright.exporter.d2 import render

        # Spec without boundaries should fall back to tier containers
        d2 = render(_sample_spec())
        assert "tier_2" in d2 or "Compute" in d2
