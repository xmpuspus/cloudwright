"""The canvas keeps the interaction and drawing contracts fixed in v1.9.0.

Each check names the defect it guards. The measurements behind them come from
driving the running app; these run in CI with no browser and no API key, so a
refactor that silently restores a default fails here first.
"""

from __future__ import annotations

from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1]
STATIC = WEB / "cloudwright_web" / "static"
SRC = WEB / "frontend" / "src"
DIAGRAM = SRC / "components" / "ArchitectureDiagram.tsx"
MIGRATION = SRC / "components" / "MigrationPanel.tsx"


def _asset(suffix: str) -> str:
    files = sorted((STATIC / "assets").glob(f"*{suffix}"))
    if not files:
        pytest.fail(f"No {suffix} asset in {STATIC / 'assets'}. Run the frontend build and copy dist.")
    return files[0].read_text(encoding="utf-8")


# Interaction contracts


def test_zoom_floor_is_low_enough_for_a_phone():
    """At ReactFlow's 0.5 default, Fit View left 2 of 8 nodes outside a 390px pane."""
    source = DIAGRAM.read_text()
    assert "const MIN_ZOOM = 0.12" in source
    assert "minZoom={MIN_ZOOM}" in source
    assert "minZoom: MIN_ZOOM" in source, "fitView must honour the same floor as the canvas"


def test_delete_key_removes_a_connection():
    """ReactFlow listens for Backspace alone, so Delete did nothing to a selected edge."""
    source = DIAGRAM.read_text()
    assert 'const DELETE_KEYS = ["Backspace", "Delete"]' in source
    assert "deleteKeyCode={DELETE_KEYS}" in source


def test_workspace_has_a_standalone_migration_view():
    """Migration planning must work before an architecture is generated in chat."""
    app = (SRC / "App.tsx").read_text()

    assert 'import MigrationPanel from "./components/MigrationPanel"' in app
    assert '| "migration"' in app
    assert '{ key: "migration", icon: "route" }' in app
    assert "<MigrationPanel apiBase={API_BASE} />" in app


def test_migration_view_names_its_action_and_outcome_for_assistive_technology():
    source = MIGRATION.read_text()

    assert "fetch(`${apiBase}/migration/demo`" in source
    assert '"X-API-Key"' in source
    assert "sessionStorage" in source
    assert "Server API key" in source
    assert "Run PH telco proof project" in source
    assert 'role="status"' in source
    assert "Ready to close" in source
    assert "Blocked" in source
    assert "This view plans and checks evidence. It does not move data or change systems." in source


def test_boundaries_take_no_drag_and_no_selection():
    """Dragging a boundary moved it and its children, and nothing saved the move."""
    source = DIAGRAM.read_text()
    assert "draggable: false" in source
    assert "selectable: false" in source
    css = _asset(".css").replace(" ", "")
    assert ".react-flow__node-boundaryGroup{pointer-events:none}" in css


def test_no_node_is_trapped_inside_its_boundary():
    """`extent: "parent"` plus a 32px hug left a node 5 to 10px of travel."""
    source = DIAGRAM.read_text()
    assert 'extent: hasBoundary ? "parent" : undefined' not in source
    assert "extent:" not in source


def test_a_boundary_has_no_dead_resize_handle():
    """NodeResizer rendered on every boundary with no handler to persist a resize."""
    assert "NodeResizer" not in (SRC / "components" / "BoundaryNode.tsx").read_text()


def test_handles_are_big_enough_to_hit_when_zoomed_out():
    css = _asset(".css").replace(" ", "")
    assert ".react-flow__handle{width:9px;height:9px" in css


# Drawing contracts


def test_every_connection_draws_an_arrowhead():
    """The diagram is directed and shipped with `markerEnd: none` on every edge."""
    assert "MarkerType.ArrowClosed" in DIAGRAM.read_text()
    assert "arrowclosed" in _asset(".js")


def test_connection_ink_clears_the_contrast_floor():
    """1.42:1 in light and 1.81:1 in dark, against a 3:1 floor for meaningful graphics.

    #64748b on #f8fafc is 4.55:1 and #94a3b8 on #0c1220 is 7.3:1.
    """
    css = _asset(".css")
    assert "--edge: #64748b" in css
    assert "--edge: #94a3b8" in css
    assert 'stroke: "var(--edge)"' in DIAGRAM.read_text()


def test_boundary_colours_come_from_theme_tokens():
    """Hardcoded light rgba painted the VPC as a pale slab on the dark canvas."""
    source = DIAGRAM.read_text()
    assert "rgba(241, 245, 249" not in source
    assert "color-mix(in srgb, var(--${token})" in source
    css = _asset(".css")
    assert "--tier-vpc:" in css
    assert "--boundary-fill:" in css


def test_a_connection_leaves_the_side_that_matches_the_tier_gap():
    """One pair of handles sent a same-tier connection out of the bottom and back
    into the top of the node beside it, which caused most of the crossings."""
    source = DIAGRAM.read_text()
    for handle in ("s-bottom", "t-top", "s-right", "t-left", "s-left", "t-right"):
        assert f'"{handle}"' in source
    js = _asset(".js")
    for handle in ("s-bottom", "t-top", "s-right", "t-left"):
        assert handle in js, f"handle {handle} missing from the shipped bundle"


def test_the_layout_orders_a_tier_before_it_places_it():
    assert "function orderTiers" in DIAGRAM.read_text()
    assert "barycentre" in DIAGRAM.read_text()


def test_a_row_is_centred_on_its_nodes_not_on_its_slots():
    """`(1200 - rowCount * H_GAP) / 2` left every row 50px off centre."""
    source = DIAGRAM.read_text()
    assert "rowCount * NODE_WIDTH + (rowCount - 1) * (H_GAP - NODE_WIDTH)" in source
    assert "(1200 - totalWidth) / 2" not in source


def test_the_vpc_box_clears_the_tier_boxes_inside_it():
    """Both rects came from the same component positions, so they shared a border."""
    source = DIAGRAM.read_text()
    assert "const VPC_GAP" in source
    assert "Wrap the tier boxes, not the raw components" in source
