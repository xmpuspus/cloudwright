"""v1.6.0 control traceability chain."""

from cloudwright.compliance import ComplianceScanner, build_traceability
from cloudwright.spec import ArchSpec, Component


def _hipaa_spec() -> ArchSpec:
    return ArchSpec(
        name="trace",
        components=[
            Component(id="db", service="rds", provider="aws", label="Patient DB", tier=3, config={}),
        ],
        metadata={"compliance": ["hipaa"]},
    )


def test_traceability_links_component_resource_control():
    spec = _hipaa_spec()
    report = ComplianceScanner().scan(spec, frameworks=["hipaa"], run_checkov=False)
    chain = build_traceability(spec, report)
    assert chain, "an unencrypted HIPAA DB should produce at least one finding chain"
    db_rows = [r for r in chain if r["component_id"] == "db"]
    assert db_rows
    row = db_rows[0]
    assert row["service"] == "rds"
    assert row["resource_type"] == "aws_db_instance"  # mapped via the exporter resource map
    assert row["status"] == "violated"


def test_traceability_entries_carry_controls():
    spec = _hipaa_spec()
    report = ComplianceScanner().scan(spec, frameworks=["hipaa"], run_checkov=False)
    chain = build_traceability(spec, report)
    # at least one chain entry references a framework control id
    assert any(r["controls"] for r in chain)
