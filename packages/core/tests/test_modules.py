from cloudwright.modules import ModuleCatalog, insert_module, validate_standards, validate_standards_from_dict
from cloudwright.spec import ArchSpec


def test_module_catalog_loads_bundled_yaml():
    catalog = ModuleCatalog()

    modules = catalog.list_modules()

    assert len(modules) == 5
    assert {module.id for module in modules} >= {
        "aws-three-tier-web",
        "aws-serverless-api",
        "aws-data-lake",
        "gcp-serverless-api",
        "azure-three-tier-web",
    }
    for module in modules:
        assert module.approved
        assert isinstance(module.fragment, ArchSpec)
        assert module.fragment.components


def test_insert_module_uses_collision_safe_component_and_connection_ids():
    catalog = ModuleCatalog()
    spec = ArchSpec(
        name="Canvas",
        provider="aws",
        region="us-east-1",
        components=[
            {
                "id": "aws_api_gateway",
                "service": "api_gateway",
                "provider": "aws",
                "label": "Existing API",
            }
        ],
        connections=[],
    )

    result = insert_module(spec, catalog.require("aws-serverless-api"))

    ids = [component.id for component in result.spec.components]
    assert len(ids) == len(set(ids))
    assert "aws_api_gateway-2" in ids
    assert all(connection.source in ids and connection.target in ids for connection in result.spec.connections)
    assert (
        result.spec.metadata["modules"]["instances"][result.module_instance_id]["component_ids"] == result.component_ids
    )


def test_standards_checker_reports_module_violations():
    catalog = ModuleCatalog()
    inserted = insert_module(
        ArchSpec(name="Canvas", provider="aws", region="us-east-1"), catalog.require("aws-serverless-api")
    )
    spec_data = inserted.spec.model_dump()
    instance_id = inserted.module_instance_id
    first_component_id = spec_data["metadata"]["modules"]["instances"][instance_id]["component_ids"][0]

    spec_data["components"][0]["id"] = "bad_name"
    spec_data["metadata"]["modules"]["instances"][instance_id]["component_ids"][0] = "bad_name"
    for connection in spec_data["connections"]:
        if connection["source"] == first_component_id:
            connection["source"] = "bad_name"
        if connection["target"] == first_component_id:
            connection["target"] = "bad_name"
    spec_data["components"][0]["config"]["tags"].pop("owner")
    spec_data["metadata"]["modules"]["instances"][instance_id]["approved"] = False

    result = validate_standards(ArchSpec.model_validate(spec_data), catalog=catalog)
    codes = {violation.code for violation in result.violations}

    assert not result.passed
    assert {"missing_required_tag", "unapproved_module", "bad_component_name"} <= codes
    assert first_component_id.startswith("aws_api_")


def test_standards_checker_reports_orphan_connections_from_raw_dict():
    result = validate_standards_from_dict(
        {
            "name": "Bad Canvas",
            "provider": "aws",
            "region": "us-east-1",
            "components": [
                {"id": "web", "service": "ec2", "provider": "aws", "label": "Web"},
            ],
            "connections": [{"source": "web", "target": "missing", "label": "broken"}],
        }
    )

    assert not result.passed
    assert result.violations[0].code == "orphan_connection"


def test_terraform_export_emits_module_blocks_for_catalog_instances():
    catalog = ModuleCatalog()
    result = insert_module(
        ArchSpec(name="Canvas", provider="aws", region="us-east-1"), catalog.require("aws-serverless-api")
    )

    hcl = result.spec.export("terraform")

    assert "# Modules" in hcl
    assert 'module "aws_serverless_api"' in hcl
    assert 'source = "registry.terraform.io/cloudwright/aws-serverless-api/aws"' in hcl
    assert 'version = "1.0.0"' in hcl
    assert 'resource "aws_lambda_function" "aws_api_function"' not in hcl
