"""Tests for the architecture anti-pattern linter."""

from cloudwright.linter import LintWarning, lint
from cloudwright.spec import ArchSpec, Component


def _make_spec(components: list[Component], name: str = "Test") -> ArchSpec:
    return ArchSpec(name=name, provider="aws", region="us-east-1", components=components)


def _component(id: str, service: str, label: str | None = None, config: dict | None = None) -> Component:
    return Component(
        id=id,
        service=service,
        provider="aws",
        label=label or id,
        config=config or {},
    )


def _rule_ids(warnings: list[LintWarning]) -> set[str]:
    return {w.rule for w in warnings}


# ---------------------------------------------------------------------------
# no_encryption
# ---------------------------------------------------------------------------


class TestNoEncryption:
    def test_flags_unencrypted_rds(self):
        spec = _make_spec([_component("db", "rds", config={})])
        warnings = lint(spec)
        assert "no_encryption" in _rule_ids(warnings)

    def test_flags_unencrypted_s3(self):
        spec = _make_spec([_component("store", "s3", config={})])
        warnings = lint(spec)
        assert "no_encryption" in _rule_ids(warnings)

    def test_passes_encrypted_rds(self):
        spec = _make_spec([_component("db", "rds", config={"encryption": True})])
        warnings = lint(spec)
        assert "no_encryption" not in _rule_ids(warnings)

    def test_passes_encrypted_dynamodb(self):
        spec = _make_spec([_component("db", "dynamodb", config={"encryption": True})])
        warnings = lint(spec)
        assert "no_encryption" not in _rule_ids(warnings)

    def test_component_id_attached(self):
        spec = _make_spec([_component("mydb", "rds")])
        warnings = [w for w in lint(spec) if w.rule == "no_encryption"]
        assert warnings[0].component == "mydb"
        assert warnings[0].severity == "error"


# ---------------------------------------------------------------------------
# single_az
# ---------------------------------------------------------------------------


class TestSingleAz:
    def _three_component_spec(self, db_config: dict) -> ArchSpec:
        return _make_spec(
            [
                _component("web", "ec2"),
                _component("lb", "alb"),
                _component("db", "rds", config=db_config),
            ]
        )

    def test_flags_db_without_multi_az_in_large_spec(self):
        spec = self._three_component_spec({})
        warnings = lint(spec)
        assert "single_az" in _rule_ids(warnings)

    def test_passes_db_with_multi_az(self):
        spec = self._three_component_spec({"multi_az": True})
        warnings = lint(spec)
        assert "single_az" not in _rule_ids(warnings)

    def test_skips_small_spec(self):
        # Only 2 components — rule should not fire
        spec = _make_spec(
            [
                _component("web", "ec2"),
                _component("db", "rds"),
            ]
        )
        warnings = lint(spec)
        assert "single_az" not in _rule_ids(warnings)

    def test_severity_is_error(self):
        spec = self._three_component_spec({})
        warnings = [w for w in lint(spec) if w.rule == "single_az"]
        assert all(w.severity == "error" for w in warnings)


# ---------------------------------------------------------------------------
# oversized_instances
# ---------------------------------------------------------------------------


class TestOversizedInstances:
    def test_flags_16xlarge(self):
        spec = _make_spec([_component("web", "ec2", config={"instance_type": "m5.16xlarge"})])
        warnings = lint(spec)
        assert "oversized_instances" in _rule_ids(warnings)

    def test_flags_metal(self):
        spec = _make_spec([_component("web", "ec2", config={"instance_type": "i3.metal"})])
        warnings = lint(spec)
        assert "oversized_instances" in _rule_ids(warnings)

    def test_flags_24xlarge(self):
        spec = _make_spec([_component("web", "ec2", config={"instance_type": "r6g.24xlarge"})])
        warnings = lint(spec)
        assert "oversized_instances" in _rule_ids(warnings)

    def test_passes_normal_instance(self):
        spec = _make_spec([_component("web", "ec2", config={"instance_type": "m5.large"})])
        warnings = lint(spec)
        assert "oversized_instances" not in _rule_ids(warnings)

    def test_severity_is_warning(self):
        spec = _make_spec([_component("web", "ec2", config={"instance_type": "m5.16xlarge"})])
        warnings = [w for w in lint(spec) if w.rule == "oversized_instances"]
        assert all(w.severity == "warning" for w in warnings)


# ---------------------------------------------------------------------------
# no_load_balancer
# ---------------------------------------------------------------------------


class TestNoLoadBalancer:
    def test_flags_two_compute_without_lb(self):
        spec = _make_spec(
            [
                _component("web1", "ec2"),
                _component("web2", "ec2"),
            ]
        )
        warnings = lint(spec)
        assert "no_load_balancer" in _rule_ids(warnings)

    def test_passes_two_compute_with_alb(self):
        spec = _make_spec(
            [
                _component("web1", "ec2"),
                _component("web2", "ec2"),
                _component("lb", "alb"),
            ]
        )
        warnings = lint(spec)
        assert "no_load_balancer" not in _rule_ids(warnings)

    def test_skips_single_compute(self):
        spec = _make_spec([_component("web", "ec2")])
        warnings = lint(spec)
        assert "no_load_balancer" not in _rule_ids(warnings)

    def test_passes_two_compute_with_nlb(self):
        spec = _make_spec(
            [
                _component("api1", "ecs"),
                _component("api2", "ecs"),
                _component("lb", "nlb"),
            ]
        )
        warnings = lint(spec)
        assert "no_load_balancer" not in _rule_ids(warnings)

    def test_severity_is_error(self):
        spec = _make_spec([_component("web1", "ec2"), _component("web2", "ec2")])
        warnings = [w for w in lint(spec) if w.rule == "no_load_balancer"]
        assert all(w.severity == "error" for w in warnings)


# ---------------------------------------------------------------------------
# public_database
# ---------------------------------------------------------------------------


class TestPublicDatabase:
    def test_flags_publicly_accessible_rds(self):
        spec = _make_spec([_component("db", "rds", config={"publicly_accessible": True})])
        warnings = lint(spec)
        assert "public_database" in _rule_ids(warnings)

    def test_passes_private_rds(self):
        spec = _make_spec([_component("db", "rds", config={"publicly_accessible": False})])
        warnings = lint(spec)
        assert "public_database" not in _rule_ids(warnings)

    def test_passes_rds_without_flag(self):
        spec = _make_spec([_component("db", "rds", config={})])
        warnings = lint(spec)
        assert "public_database" not in _rule_ids(warnings)

    def test_severity_is_error(self):
        spec = _make_spec([_component("db", "rds", config={"publicly_accessible": True})])
        warnings = [w for w in lint(spec) if w.rule == "public_database"]
        assert all(w.severity == "error" for w in warnings)


# ---------------------------------------------------------------------------
# no_waf
# ---------------------------------------------------------------------------


class TestNoWaf:
    def test_flags_alb_without_waf(self):
        spec = _make_spec([_component("lb", "alb")])
        warnings = lint(spec)
        assert "no_waf" in _rule_ids(warnings)

    def test_flags_api_gateway_without_waf(self):
        spec = _make_spec([_component("gw", "api_gateway")])
        warnings = lint(spec)
        assert "no_waf" in _rule_ids(warnings)

    def test_passes_alb_with_waf(self):
        spec = _make_spec(
            [
                _component("lb", "alb"),
                _component("fw", "waf"),
            ]
        )
        warnings = lint(spec)
        assert "no_waf" not in _rule_ids(warnings)

    def test_skips_when_no_ingress(self):
        spec = _make_spec([_component("db", "rds")])
        warnings = lint(spec)
        assert "no_waf" not in _rule_ids(warnings)

    def test_severity_is_warning(self):
        spec = _make_spec([_component("lb", "alb")])
        warnings = [w for w in lint(spec) if w.rule == "no_waf"]
        assert all(w.severity == "warning" for w in warnings)


# ---------------------------------------------------------------------------
# no_monitoring
# ---------------------------------------------------------------------------


class TestNoMonitoring:
    def _large_spec(self, extra: list[Component] | None = None) -> ArchSpec:
        components = [
            _component("web", "ec2"),
            _component("lb", "alb"),
            _component("db", "rds"),
        ]
        if extra:
            components.extend(extra)
        return _make_spec(components)

    def test_flags_three_components_no_monitoring(self):
        spec = self._large_spec()
        warnings = lint(spec)
        assert "no_monitoring" in _rule_ids(warnings)

    def test_passes_with_cloudwatch(self):
        spec = self._large_spec([_component("cw", "cloudwatch")])
        warnings = lint(spec)
        assert "no_monitoring" not in _rule_ids(warnings)

    def test_passes_with_monitoring_service(self):
        spec = self._large_spec([_component("mon", "monitoring")])
        warnings = lint(spec)
        assert "no_monitoring" not in _rule_ids(warnings)

    def test_skips_small_spec(self):
        spec = _make_spec([_component("web", "ec2"), _component("db", "rds")])
        warnings = lint(spec)
        assert "no_monitoring" not in _rule_ids(warnings)

    def test_severity_is_warning(self):
        spec = self._large_spec()
        warnings = [w for w in lint(spec) if w.rule == "no_monitoring"]
        assert all(w.severity == "warning" for w in warnings)


# ---------------------------------------------------------------------------
# single_point_of_failure
# ---------------------------------------------------------------------------


class TestSinglePointOfFailure:
    def test_flags_sole_compute_without_auto_scaling(self):
        spec = _make_spec([_component("web", "ec2", config={})])
        warnings = lint(spec)
        assert "single_point_of_failure" in _rule_ids(warnings)

    def test_passes_with_auto_scaling(self):
        spec = _make_spec([_component("web", "ec2", config={"auto_scaling": True})])
        warnings = lint(spec)
        assert "single_point_of_failure" not in _rule_ids(warnings)

    def test_skips_multiple_compute(self):
        spec = _make_spec(
            [
                _component("web1", "ec2"),
                _component("web2", "ec2"),
                _component("lb", "alb"),
            ]
        )
        warnings = lint(spec)
        assert "single_point_of_failure" not in _rule_ids(warnings)

    def test_severity_is_error(self):
        spec = _make_spec([_component("web", "ec2")])
        warnings = [w for w in lint(spec) if w.rule == "single_point_of_failure"]
        assert all(w.severity == "error" for w in warnings)


# ---------------------------------------------------------------------------
# no_backup
# ---------------------------------------------------------------------------


class TestNoBackup:
    def test_flags_db_without_backup(self):
        spec = _make_spec([_component("db", "rds", config={})])
        warnings = lint(spec)
        assert "no_backup" in _rule_ids(warnings)

    def test_passes_with_backup(self):
        spec = _make_spec([_component("db", "rds", config={"backup": True})])
        warnings = lint(spec)
        assert "no_backup" not in _rule_ids(warnings)

    def test_passes_with_pitr(self):
        spec = _make_spec([_component("db", "rds", config={"point_in_time_recovery": True})])
        warnings = lint(spec)
        assert "no_backup" not in _rule_ids(warnings)

    def test_flags_aurora_without_backup(self):
        spec = _make_spec([_component("db", "aurora", config={})])
        warnings = lint(spec)
        assert "no_backup" in _rule_ids(warnings)

    def test_severity_is_warning(self):
        spec = _make_spec([_component("db", "rds")])
        warnings = [w for w in lint(spec) if w.rule == "no_backup"]
        assert all(w.severity == "warning" for w in warnings)


# ---------------------------------------------------------------------------
# no_auth
# ---------------------------------------------------------------------------


class TestNoAuth:
    def test_flags_alb_without_auth(self):
        spec = _make_spec([_component("lb", "alb")])
        warnings = lint(spec)
        assert "no_auth" in _rule_ids(warnings)

    def test_flags_api_gateway_without_auth(self):
        spec = _make_spec([_component("gw", "api_gateway")])
        warnings = lint(spec)
        assert "no_auth" in _rule_ids(warnings)

    def test_passes_alb_with_cognito(self):
        spec = _make_spec(
            [
                _component("lb", "alb"),
                _component("auth", "cognito"),
            ]
        )
        warnings = lint(spec)
        assert "no_auth" not in _rule_ids(warnings)

    def test_passes_alb_with_iam(self):
        spec = _make_spec(
            [
                _component("lb", "alb"),
                _component("perms", "iam"),
            ]
        )
        warnings = lint(spec)
        assert "no_auth" not in _rule_ids(warnings)

    def test_skips_when_no_ingress(self):
        spec = _make_spec([_component("db", "rds")])
        warnings = lint(spec)
        assert "no_auth" not in _rule_ids(warnings)

    def test_severity_is_warning(self):
        spec = _make_spec([_component("lb", "alb")])
        warnings = [w for w in lint(spec) if w.rule == "no_auth"]
        assert all(w.severity == "warning" for w in warnings)


# ---------------------------------------------------------------------------
# Integration: clean spec
# ---------------------------------------------------------------------------


class TestCleanSpec:
    def test_well_architected_spec_has_no_errors(self):
        spec = _make_spec(
            [
                _component("lb", "alb"),
                _component("waf", "waf"),
                _component("auth", "cognito"),
                _component("web1", "ec2", config={"auto_scaling": True}),
                _component("web2", "ec2"),
                _component(
                    "db",
                    "rds",
                    config={
                        "encryption": True,
                        "multi_az": True,
                        "backup": True,
                        "publicly_accessible": False,
                    },
                ),
                _component("cache", "elasticache", config={"encryption": True, "backup": True, "multi_az": True}),
                _component("mon", "cloudwatch"),
            ]
        )
        warnings = lint(spec)
        errors = [w for w in warnings if w.severity == "error"]
        assert len(errors) == 0
