"""Tests for the Pulumi format dispatch in cloudwright.exporter.export_spec.

Verifies that ``export_spec(spec, "pulumi-ts", output_dir=...)`` writes a
TypeScript Pulumi project and ``export_spec(spec, "pulumi-python", ...)``
writes a Python Pulumi project.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from cloudwright.exporter import FORMATS, export_spec
from cloudwright.spec import ArchSpec, Component


def _demo_spec() -> ArchSpec:
    return ArchSpec(
        name="Demo",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="bk", service="s3", provider="aws", label="Bucket", tier=3),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
    )


def test_pulumi_ts_in_supported_formats():
    assert "pulumi-ts" in FORMATS


def test_pulumi_python_in_supported_formats():
    assert "pulumi-python" in FORMATS


def test_pulumi_ts_returns_ts_string():
    spec = _demo_spec()
    out = export_spec(spec, "pulumi-ts")
    assert 'import * as aws from "@pulumi/aws";' in out
    assert "aws.s3.Bucket(" in out


def test_pulumi_python_returns_python_string():
    spec = _demo_spec()
    out = export_spec(spec, "pulumi-python")
    assert "import pulumi_aws as aws" in out
    assert "aws.s3.Bucket(" in out


def test_pulumi_ts_typescript_alias_works():
    spec = _demo_spec()
    out = export_spec(spec, "pulumi-typescript")
    assert 'import * as aws from "@pulumi/aws";' in out


def test_pulumi_py_alias_works():
    spec = _demo_spec()
    out = export_spec(spec, "pulumi-py")
    assert "import pulumi_aws as aws" in out


def test_pulumi_ts_writes_project_files_to_directory(tmp_path: Path):
    spec = _demo_spec()
    out_dir = tmp_path / "infra"
    export_spec(spec, "pulumi-ts", output_dir=str(out_dir))
    files = sorted(p.name for p in out_dir.iterdir())
    assert files == ["Pulumi.yaml", "index.ts", "package.json", "tsconfig.json"]
    index_ts = (out_dir / "index.ts").read_text()
    assert 'import * as aws from "@pulumi/aws";' in index_ts
    assert "@pulumi/aws" in (out_dir / "package.json").read_text()
    assert "runtime: nodejs" in (out_dir / "Pulumi.yaml").read_text()


def test_pulumi_python_writes_project_files_to_directory(tmp_path: Path):
    spec = _demo_spec()
    out_dir = tmp_path / "infra"
    export_spec(spec, "pulumi-python", output_dir=str(out_dir))
    files = sorted(p.name for p in out_dir.iterdir())
    assert files == ["Pulumi.yaml", "__main__.py", "requirements.txt"]
    main_py = (out_dir / "__main__.py").read_text()
    assert "import pulumi_aws as aws" in main_py
    assert "pulumi-aws" in (out_dir / "requirements.txt").read_text()
    assert "runtime: python" in (out_dir / "Pulumi.yaml").read_text()


def test_pulumi_ts_writes_to_single_file_when_output_is_file(tmp_path: Path):
    spec = _demo_spec()
    out_file = tmp_path / "stack.ts"
    export_spec(spec, "pulumi-ts", output=str(out_file))
    assert out_file.exists()
    assert 'import * as aws from "@pulumi/aws";' in out_file.read_text()


def test_pulumi_python_writes_to_single_file_when_output_is_file(tmp_path: Path):
    spec = _demo_spec()
    out_file = tmp_path / "stack.py"
    export_spec(spec, "pulumi-python", output=str(out_file))
    assert out_file.exists()
    assert "import pulumi_aws as aws" in out_file.read_text()


def test_unknown_format_still_rejects():
    spec = _demo_spec()
    with pytest.raises(ValueError, match="Unknown export format"):
        export_spec(spec, "pulumi-bogus")


def test_pulumi_ts_multi_provider_renders_all_three(tmp_path: Path):
    spec = ArchSpec(
        name="Multi",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="bk", service="s3", provider="aws", label="B", tier=3),
            Component(id="vm", service="compute_engine", provider="gcp", label="VM", tier=2),
            Component(id="azv", service="virtual_machines", provider="azure", label="A", tier=2),
        ],
    )
    out = export_spec(spec, "pulumi-ts")
    assert "@pulumi/aws" in out
    assert "@pulumi/gcp" in out
    assert "@pulumi/azure-native" in out


def test_pulumi_python_multi_provider_renders_all_three(tmp_path: Path):
    spec = ArchSpec(
        name="Multi",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="bk", service="s3", provider="aws", label="B", tier=3),
            Component(id="vm", service="compute_engine", provider="gcp", label="VM", tier=2),
            Component(id="azv", service="virtual_machines", provider="azure", label="A", tier=2),
        ],
    )
    out = export_spec(spec, "pulumi-python")
    assert "pulumi_aws" in out
    assert "pulumi_gcp" in out
    assert "pulumi_azure_native" in out
