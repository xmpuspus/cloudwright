"""Tests for the SVG/PNG rendering pipeline."""

from __future__ import annotations

import pytest
from cloudwright.exporter.renderer import DiagramRenderer
from cloudwright.spec import ArchSpec, Component, Connection


def _sample_spec() -> ArchSpec:
    return ArchSpec(
        name="Test",
        provider="aws",
        region="us-east-1",
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
            Component(id="db", service="rds", provider="aws", label="DB", tier=3),
        ],
        connections=[Connection(source="web", target="db")],
    )


def test_d2_available_check():
    result = DiagramRenderer.is_available()
    assert isinstance(result, bool)


def test_graceful_degradation_without_d2(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    renderer = DiagramRenderer()
    result = renderer.render_svg(_sample_spec())
    assert isinstance(result, str)
    # Should contain D2 source text as fallback
    assert "theme-id" in result or "D2" in result


def test_fallback_contains_install_hint(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    renderer = DiagramRenderer()
    result = renderer.render_svg(_sample_spec())
    assert "D2 binary not installed" in result or "d2lang.com" in result


def test_render_png_raises_without_d2(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    renderer = DiagramRenderer()
    with pytest.raises(RuntimeError, match="D2 binary not installed"):
        renderer.render_png(_sample_spec())


@pytest.mark.skipif(not DiagramRenderer.is_available(), reason="D2 binary not installed")
def test_render_svg_produces_valid_svg():
    renderer = DiagramRenderer()
    svg = renderer.render_svg(_sample_spec())
    assert "<svg" in svg or "svg" in svg.lower()


@pytest.mark.skipif(not DiagramRenderer.is_available(), reason="D2 binary not installed")
@pytest.mark.slow
def test_render_png_produces_bytes():
    # D2 PNG rendering downloads Chromium on first run — can take several minutes
    renderer = DiagramRenderer()
    data = renderer.render_png(_sample_spec())
    assert isinstance(data, bytes)
    assert len(data) > 0


@pytest.mark.skipif(not DiagramRenderer.is_available(), reason="D2 binary not installed")
@pytest.mark.slow
def test_render_png_is_png_magic_bytes():
    renderer = DiagramRenderer()
    data = renderer.render_png(_sample_spec())
    # PNG magic bytes: \x89PNG
    assert data[:4] == b"\x89PNG"


def test_render_svg_fallback_without_mmdc(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    renderer = DiagramRenderer()
    result = renderer.render_svg_fallback(_sample_spec())
    assert isinstance(result, str)
    # Should contain mermaid source as fallback
    assert "flowchart" in result.lower() or "graph" in result.lower() or "mmdc" in result


def test_svg_in_formats():
    from cloudwright.exporter import FORMATS

    assert "svg" in FORMATS


def test_png_in_formats():
    from cloudwright.exporter import FORMATS

    assert "png" in FORMATS


def test_c4_in_formats():
    from cloudwright.exporter import FORMATS

    assert "c4" in FORMATS


def test_export_spec_svg_without_d2(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: None)
    from cloudwright.exporter import export_spec

    content = export_spec(_sample_spec(), "svg")
    assert isinstance(content, str)
    # Fallback should include D2 source
    assert "->" in content


def test_export_spec_c4_dispatches():
    from cloudwright.exporter import export_spec

    content = export_spec(_sample_spec(), "c4")
    assert isinstance(content, str)
    # C4 L2 container diagram output
    assert "Test" in content
    assert "Container" in content or "c4" in content.lower() or "->" in content
