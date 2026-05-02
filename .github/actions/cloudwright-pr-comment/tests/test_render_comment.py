"""Tests for the cloudwright-pr-comment Markdown renderer.

Run from repo root:

    pytest .github/actions/cloudwright-pr-comment/tests
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ACTION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ACTION_DIR))

from render_comment import (  # type: ignore  # noqa: E402
    DEFAULT_MARKER,
    _format_delta,
    _format_money,
    _summarize_components,
    _summarize_compliance,
    _summarize_cost,
    _unwrap,
    render,
)


def _wrap_data(payload):
    return {"data": payload}


@pytest.fixture
def base_spec():
    return {
        "name": "test",
        "version": 1,
        "provider": "aws",
        "components": [
            {"id": "web", "service": "ec2", "label": "Web", "provider": "aws"},
            {"id": "db", "service": "rds", "label": "DB", "provider": "aws"},
        ],
    }


@pytest.fixture
def head_spec():
    return {
        "name": "test",
        "version": 1,
        "provider": "aws",
        "components": [
            {"id": "web", "service": "ec2", "label": "Web", "provider": "aws"},
            {"id": "db", "service": "rds", "label": "Postgres DB", "provider": "aws"},
            {"id": "cache", "service": "elasticache", "label": "Session cache", "provider": "aws"},
        ],
    }


@pytest.fixture
def base_cost():
    return _wrap_data(
        {
            "estimate": {
                "monthly_total": 260.74,
                "currency": "USD",
                "breakdown": [
                    {"component_id": "web", "service": "ec2", "monthly": 60.74},
                    {"component_id": "db", "service": "rds", "monthly": 200.0},
                ],
            }
        }
    )


@pytest.fixture
def head_cost():
    return _wrap_data(
        {
            "estimate": {
                "monthly_total": 440.74,
                "currency": "USD",
                "breakdown": [
                    {"component_id": "web", "service": "ec2", "monthly": 60.74},
                    {"component_id": "db", "service": "rds", "monthly": 200.0},
                    {"component_id": "cache", "service": "elasticache", "monthly": 180.0},
                ],
            }
        }
    )


@pytest.fixture
def base_validate():
    return _wrap_data(
        {
            "results": [
                {
                    "framework": "SOC 2",
                    "passed": False,
                    "score": 0.45,
                    "checks": [
                        {"name": "logging", "passed": False, "severity": "high"},
                        {"name": "encryption_at_rest", "passed": False, "severity": "high"},
                    ],
                }
            ]
        }
    )


@pytest.fixture
def head_validate():
    return _wrap_data(
        {
            "results": [
                {
                    "framework": "SOC 2",
                    "passed": False,
                    "score": 0.65,
                    "checks": [
                        {"name": "logging", "passed": False, "severity": "high"},
                        {"name": "encryption_at_rest", "passed": True, "severity": "high"},
                    ],
                }
            ]
        }
    )


# --- helpers ----------------------------------------------------------------

def test_unwrap_handles_envelope():
    assert _unwrap({"data": {"x": 1}}) == {"x": 1}
    assert _unwrap({"x": 1}) == {"x": 1}
    assert _unwrap(None) == {}


def test_format_money_negative():
    assert _format_money(-12.5) == "-$12.50"
    assert _format_money(0) == "$0.00"
    assert _format_money(1234.567) == "$1,234.57"


def test_format_delta_no_change():
    assert _format_delta(0.0) == "no change"
    assert _format_delta(0.001) == "no change"
    assert _format_delta(180.0) == "+$180.00/mo"
    assert _format_delta(-10.5) == "-$10.50/mo"


def test_summarize_cost(head_cost):
    summary = _summarize_cost(head_cost)
    assert summary is not None
    assert summary.monthly_total == 440.74
    assert summary.breakdown == {"web": 60.74, "db": 200.0, "cache": 180.0}


def test_summarize_cost_missing_estimate():
    assert _summarize_cost({"data": {}}) is None
    assert _summarize_cost(None) is None


def test_summarize_components(base_spec):
    out = _summarize_components(base_spec)
    assert set(out) == {"web", "db"}
    assert out["web"]["service"] == "ec2"
    assert out["db"]["label"] == "DB"


def test_summarize_compliance(head_validate):
    out = _summarize_compliance(head_validate)
    assert "SOC 2" in out
    assert out["SOC 2"]["passed"] is False
    assert out["SOC 2"]["failed_checks"] == ["logging"]


# --- end-to-end render ------------------------------------------------------

def test_render_full_diff(
    base_spec, head_spec, base_cost, head_cost, base_validate, head_validate
):
    body, delta = render(
        head_cost=head_cost,
        head_validate=head_validate,
        base_cost=base_cost,
        base_validate=base_validate,
        head_spec=head_spec,
        base_spec=base_spec,
        compliance="soc2",
        workload_profile="medium",
        head_path="cloudwright.yaml",
    )
    # marker is always present, exactly once
    assert body.count(DEFAULT_MARKER) == 1
    assert body.startswith(DEFAULT_MARKER)
    # core sections
    assert "## Cloudwright PR Preview" in body
    assert "Spec: `cloudwright.yaml`" in body
    assert "Workload profile: `medium`" in body
    assert "### Cost" in body
    # cost delta math
    assert "$260.74" in body
    assert "$440.74" in body
    assert "+$180.00/mo" in body
    assert "+$2,160.00/yr" in body
    # arch diff: cache is added, db is changed
    assert "### Architecture diff" in body
    assert "+ **Session cache**" in body
    assert "elasticache" in body
    assert "($180.00/mo)" in body
    assert "~ **Postgres DB**" in body  # label changed
    # compliance: encryption_at_rest resolved
    assert "### Compliance" in body
    assert "SOC 2" in body
    assert "resolved: `encryption_at_rest`" in body
    # delta dict
    assert delta["monthly_delta"] == 180.0
    assert delta["head_monthly"] == 440.74
    assert delta["base_monthly"] == 260.74
    assert delta["components_added"] == ["cache"]
    assert delta["components_removed"] == []
    assert delta["components_changed"] == ["db"]


def test_render_new_spec_no_base(head_cost, head_validate, head_spec):
    body, delta = render(
        head_cost=head_cost,
        head_validate=head_validate,
        base_cost=None,
        base_validate=None,
        head_spec=head_spec,
        base_spec=None,
        compliance="soc2",
    )
    assert "New spec — monthly cost: **$440.74**" in body
    # All components are "added" since there is no baseline
    assert delta["base_monthly"] == 0.0
    assert delta["head_monthly"] == 440.74
    assert delta["monthly_delta"] == 440.74


def test_render_no_compliance_input(base_spec, head_spec, base_cost, head_cost):
    body, _ = render(
        head_cost=head_cost,
        head_validate=None,
        base_cost=base_cost,
        base_validate=None,
        head_spec=head_spec,
        base_spec=base_spec,
        compliance="",
    )
    assert "### Compliance" not in body


def test_render_idempotent_marker(base_spec, head_spec, base_cost, head_cost):
    body1, _ = render(
        head_cost=head_cost, head_validate=None, base_cost=base_cost, base_validate=None,
        head_spec=head_spec, base_spec=base_spec,
    )
    body2, _ = render(
        head_cost=head_cost, head_validate=None, base_cost=base_cost, base_validate=None,
        head_spec=head_spec, base_spec=base_spec,
    )
    # Re-rendering the same inputs yields identical output (modulo nothing) so
    # the GitHub-side update-in-place can detect "no change" cheaply.
    assert body1 == body2


def test_render_custom_marker(base_spec, head_spec, base_cost, head_cost):
    body, _ = render(
        head_cost=head_cost, head_validate=None, base_cost=base_cost, base_validate=None,
        head_spec=head_spec, base_spec=base_spec,
        marker="<!-- my-custom -->",
    )
    assert body.startswith("<!-- my-custom -->")


def test_cli_writes_files(tmp_path, base_spec, head_spec, base_cost, head_cost):
    """Smoke test: invoke the CLI entrypoint via subprocess-equivalent imports."""
    # Write inputs
    (tmp_path / "head-cost.json").write_text(json.dumps(head_cost))
    (tmp_path / "head-validate.json").write_text("")  # empty -> None
    (tmp_path / "base-cost.json").write_text(json.dumps(base_cost))
    (tmp_path / "base-validate.json").write_text("")
    import yaml  # type: ignore
    (tmp_path / "head-spec.yaml").write_text(yaml.safe_dump(head_spec))
    (tmp_path / "base-spec.yaml").write_text(yaml.safe_dump(base_spec))
    out = tmp_path / "comment.md"

    sys.argv = [
        "render_comment.py",
        "--head-cost", str(tmp_path / "head-cost.json"),
        "--head-validate", str(tmp_path / "head-validate.json"),
        "--base-cost", str(tmp_path / "base-cost.json"),
        "--base-validate", str(tmp_path / "base-validate.json"),
        "--head-spec", str(tmp_path / "head-spec.yaml"),
        "--base-spec", str(tmp_path / "base-spec.yaml"),
        "--output", str(out),
    ]
    from render_comment import main  # re-import for clarity
    assert main() == 0
    assert out.exists()
    body = out.read_text()
    assert "+$180.00/mo" in body
    delta_path = tmp_path / "cost-delta.json"
    assert delta_path.exists()
    delta = json.loads(delta_path.read_text())
    assert delta["monthly_delta"] == 180.0
