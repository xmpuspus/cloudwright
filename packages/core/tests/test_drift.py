"""Tests for the drift detection module."""

from unittest.mock import patch

from cloudwright.spec import ArchSpec, Component, Connection


def _make_spec(name: str, components: list[Component], connections: list[Connection] | None = None) -> ArchSpec:
    return ArchSpec(
        name=name,
        provider="aws",
        region="us-east-1",
        components=components,
        connections=connections or [],
    )


def _comps(*ids_services: tuple[str, str]) -> list[Component]:
    return [Component(id=cid, service=svc, provider="aws", label=cid.capitalize()) for cid, svc in ids_services]


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_no_drift(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    spec = _make_spec("app", _comps(("web", "ec2"), ("db", "rds")))
    mock_from_file.return_value = spec
    mock_import.return_value = spec

    report = detect_drift("design.yaml", "state.tfstate")

    assert report.drift_score == 0.0
    assert report.drifted_components == []
    assert report.extra_components == []
    assert report.missing_components == []


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_extra_components(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    design = _make_spec("app", _comps(("web", "ec2")))
    deployed = _make_spec("app", _comps(("web", "ec2"), ("cache", "elasticache"), ("queue", "sqs")))
    mock_from_file.return_value = design
    mock_import.return_value = deployed

    report = detect_drift("design.yaml", "state.tfstate")

    assert set(report.extra_components) == {"cache", "queue"}
    assert report.missing_components == []
    assert report.drifted_components == []
    assert report.drift_score > 0.0


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_missing_components(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    design = _make_spec("app", _comps(("web", "ec2"), ("db", "rds"), ("cache", "elasticache")))
    deployed = _make_spec("app", _comps(("web", "ec2")))
    mock_from_file.return_value = design
    mock_import.return_value = deployed

    report = detect_drift("design.yaml", "state.tfstate")

    assert set(report.missing_components) == {"db", "cache"}
    assert report.extra_components == []
    assert report.drifted_components == []
    assert report.drift_score > 0.0


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_config_drift(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    design = _make_spec(
        "app",
        [Component(id="web", service="ec2", provider="aws", label="Web", config={"instance_type": "t3.medium"})],
    )
    deployed = _make_spec(
        "app",
        [Component(id="web", service="ec2", provider="aws", label="Web", config={"instance_type": "m5.large"})],
    )
    mock_from_file.return_value = design
    mock_import.return_value = deployed

    report = detect_drift("design.yaml", "state.tfstate")

    assert "web" in report.drifted_components
    assert report.extra_components == []
    assert report.missing_components == []
    assert report.drift_score > 0.0


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_mixed_drift(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    design = _make_spec(
        "app",
        [
            Component(id="web", service="ec2", provider="aws", label="Web", config={"instance_type": "t3.medium"}),
            Component(id="db", service="rds", provider="aws", label="DB"),
            Component(id="cdn", service="cloudfront", provider="aws", label="CDN"),
        ],
    )
    deployed = _make_spec(
        "app",
        [
            # web changed config
            Component(id="web", service="ec2", provider="aws", label="Web", config={"instance_type": "m5.xlarge"}),
            # db present unchanged
            Component(id="db", service="rds", provider="aws", label="DB"),
            # cdn missing from deployed
            # cache extra in deployed
            Component(id="cache", service="elasticache", provider="aws", label="Cache"),
        ],
    )
    mock_from_file.return_value = design
    mock_import.return_value = deployed

    report = detect_drift("design.yaml", "state.tfstate")

    assert "web" in report.drifted_components
    assert "cdn" in report.missing_components
    assert "cache" in report.extra_components
    assert report.drift_score > 0.0


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_drift_score_calculation(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    # 4 design components, all missing from deployed → score = 4/4 = 1.0
    design = _make_spec("app", _comps(("a", "ec2"), ("b", "rds"), ("c", "s3"), ("d", "sqs")))
    deployed = _make_spec("app", [])
    mock_from_file.return_value = design
    mock_import.return_value = deployed

    report = detect_drift("design.yaml", "state.tfstate")

    assert report.drift_score == 1.0


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_drift_score_capped_at_one(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    # 1 design component, plus 5 extra deployed → total_issues=6, score capped at 1.0
    design = _make_spec("app", _comps(("web", "ec2")))
    deployed = _make_spec(
        "app",
        _comps(("a", "ec2"), ("b", "rds"), ("c", "s3"), ("d", "sqs"), ("e", "lambda"), ("f", "dynamodb")),
    )
    mock_from_file.return_value = design
    mock_import.return_value = deployed

    report = detect_drift("design.yaml", "state.tfstate")

    assert report.drift_score == 1.0


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_summary_no_drift(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    spec = _make_spec("app", _comps(("web", "ec2")))
    mock_from_file.return_value = spec
    mock_import.return_value = spec

    report = detect_drift("design.yaml", "state.tfstate")

    assert "No drift detected" in report.summary
    assert "matches design" in report.summary


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_summary_with_drift(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    design = _make_spec("app", _comps(("web", "ec2"), ("db", "rds")))
    deployed = _make_spec("app", _comps(("web", "ec2"), ("cache", "elasticache")))
    mock_from_file.return_value = design
    mock_import.return_value = deployed

    report = detect_drift("design.yaml", "state.tfstate")

    assert "db" in report.summary
    assert "cache" in report.summary
    assert "Drift score" in report.summary


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_summary_shows_field_changes(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    design = _make_spec(
        "app",
        [Component(id="web", service="ec2", provider="aws", label="Web", config={"instance_type": "t3.medium"})],
    )
    deployed = _make_spec(
        "app",
        [Component(id="web", service="ec2", provider="aws", label="Web", config={"instance_type": "m5.large"})],
    )
    mock_from_file.return_value = design
    mock_import.return_value = deployed

    report = detect_drift("design.yaml", "state.tfstate")

    # Summary should include the field-level change detail
    assert "web.config" in report.summary
    assert "t3.medium" in report.summary
    assert "m5.large" in report.summary


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_report_carries_both_specs(mock_from_file, mock_import):
    from cloudwright.drift import detect_drift

    design = _make_spec("design-app", _comps(("web", "ec2")))
    deployed = _make_spec("deployed-app", _comps(("web", "ec2")))
    mock_from_file.return_value = design
    mock_import.return_value = deployed

    report = detect_drift("design.yaml", "state.tfstate")

    assert report.design_spec.name == "design-app"
    assert report.deployed_spec.name == "deployed-app"


@patch("cloudwright.drift.import_spec")
@patch("cloudwright.drift.ArchSpec.from_file")
def test_infra_format_forwarded(mock_from_file, mock_import):
    """detect_drift passes infra_format through to import_spec."""
    from cloudwright.drift import detect_drift

    spec = _make_spec("app", _comps(("web", "ec2")))
    mock_from_file.return_value = spec
    mock_import.return_value = spec

    detect_drift("design.yaml", "template.yaml", infra_format="cloudformation")

    mock_import.assert_called_once_with("template.yaml", fmt="cloudformation")
