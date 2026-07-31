"""The shipped static bundle carries the built UI, not a stale copy.

`cloudwright_web/static/` is what the server serves and what goes into the
wheel. A frontend change that is not copied there passes every other test and
still ships the old interface, so these checks read the bundle itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "cloudwright_web" / "static"


def _asset(suffix: str) -> Path:
    files = sorted((STATIC / "assets").glob(f"*{suffix}"))
    if not files:
        pytest.fail(f"No {suffix} asset in {STATIC / 'assets'}. Run the frontend build and copy dist.")
    return files[0]


def test_static_dir_has_an_index_and_assets():
    assert (STATIC / "index.html").is_file()
    assert (STATIC / "assets").is_dir()


def test_index_declares_both_colour_schemes():
    html = (STATIC / "index.html").read_text()
    assert 'name="color-scheme"' in html
    assert "light dark" in html
    assert 'name="theme-color"' in html


def test_index_references_the_hashed_assets_that_exist():
    html = (STATIC / "index.html").read_text()
    for suffix in (".css", ".js"):
        name = _asset(suffix).name
        assert name in html, f"index.html does not reference {name}; the static copy is stale"


def test_stylesheet_ships_the_design_tokens():
    css = _asset(".css").read_text()
    for token in ("--accent", "--text-muted", "--radius", "--space-4", "--surface"):
        assert token in css, f"design token {token} missing from the shipped stylesheet"


def test_stylesheet_ships_the_dark_theme():
    # The minifier drops the attribute-value quotes, so match either spelling.
    css = _asset(".css").read_text().replace('"', "")
    assert "[data-theme=dark]" in css


def test_stylesheet_ships_responsive_breakpoints():
    css = _asset(".css").read_text()
    assert css.count("@media") >= 3, "the shipped stylesheet has no responsive rules"
    assert "max-width:900px" in css.replace(" ", "")


def test_stylesheet_keeps_a_visible_focus_ring():
    css = _asset(".css").read_text().replace(" ", "")
    assert ":focus-visible{outline:" in css, "keyboard focus has no visible ring"


def test_bundle_carries_no_em_dash_in_ui_copy():
    """Em-dashes read as generated copy, so no user-visible string may hold one."""
    js = _asset(".js").read_text(encoding="utf-8")
    assert "—" not in js
