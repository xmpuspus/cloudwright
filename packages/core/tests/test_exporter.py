"""Tests for all exporters — terraform, cloudformation, mermaid, sbom, aibom."""

import json

from silmaril.spec import ArchSpec, Component, Connection


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
        from silmaril.exporter.terraform import render

        hcl = render(_sample_spec())
        assert "terraform" in hcl.lower() or "provider" in hcl.lower()
        assert "aws" in hcl

    def test_includes_all_components(self):
        from silmaril.exporter.terraform import render

        hcl = render(_sample_spec())
        # Should reference all components
        assert "web" in hcl.lower()
        assert "db" in hcl.lower() or "rds" in hcl.lower() or "postgresql" in hcl.lower()

    def test_writes_to_dir(self, tmp_path):
        from silmaril.exporter.terraform import render

        spec = _sample_spec()
        content = render(spec)
        out_dir = tmp_path / "infra"
        out_dir.mkdir()
        (out_dir / "main.tf").write_text(content)
        assert (out_dir / "main.tf").exists()
        assert len((out_dir / "main.tf").read_text()) > 100


class TestCloudFormationExporter:
    def test_renders_yaml(self):
        from silmaril.exporter.cloudformation import render

        cfn = render(_sample_spec())
        assert "AWSTemplateFormatVersion" in cfn
        assert "Resources" in cfn

    def test_skips_non_aws(self):
        from silmaril.exporter.cloudformation import render

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
        from silmaril.exporter.mermaid import render

        mmd = render(_sample_spec())
        assert "flowchart" in mmd.lower() or "graph" in mmd.lower()

    def test_includes_nodes(self):
        from silmaril.exporter.mermaid import render

        mmd = render(_sample_spec())
        assert "cdn" in mmd.lower() or "CDN" in mmd
        assert "web" in mmd.lower() or "Web" in mmd

    def test_includes_edges(self):
        from silmaril.exporter.mermaid import render

        mmd = render(_sample_spec())
        assert "-->" in mmd


class TestSBOMExporter:
    def test_renders_cyclonedx(self):
        from silmaril.exporter.sbom import render

        sbom = render(_sample_spec())
        data = json.loads(sbom)
        assert data["bomFormat"] == "CycloneDX"
        assert data["specVersion"] == "1.5"

    def test_includes_components(self):
        from silmaril.exporter.sbom import render

        sbom = render(_sample_spec())
        data = json.loads(sbom)
        assert len(data["components"]) >= 4

    def test_includes_dependencies(self):
        from silmaril.exporter.sbom import render

        sbom = render(_sample_spec())
        data = json.loads(sbom)
        assert "dependencies" in data


class TestAIBOMExporter:
    def test_renders_aibom(self):
        from silmaril.exporter.aibom import render

        aibom = render(_sample_spec())
        data = json.loads(aibom)
        assert "aibomVersion" in data
        assert "metadata" in data

    def test_includes_silmaril_ai(self):
        from silmaril.exporter.aibom import render

        aibom = render(_sample_spec())
        data = json.loads(aibom)
        assert len(data["aiComponents"]) >= 1
        assert data["aiComponents"][0]["name"] == "Silmaril Architecture AI"

    def test_detects_ai_services(self):
        from silmaril.exporter.aibom import render

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
