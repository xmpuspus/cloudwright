"""Resource-boundary tests for migration service inputs."""

from __future__ import annotations

import pytest
from cloudwright.migration import validate_migration_size


def test_nested_collections_share_a_bounded_item_budget():
    project = {
        "name": "Nested oversized move",
        "estate": {
            "name": "Current",
            "assets": [
                {
                    "id": f"asset-{index}",
                    "name": f"Asset {index}",
                    "kind": "application",
                    "data_classes": [f"class-{item}" for item in range(100)],
                }
                for index in range(200)
            ],
        },
        "target": {
            "name": "Target",
            "mappings": [{"source_asset_id": f"asset-{index}", "disposition": "retain"} for index in range(200)],
        },
    }

    with pytest.raises(ValueError, match="nested items"):
        validate_migration_size(project)


def test_oversized_collection_is_rejected_before_iteration():
    class MustNotIterate(list):
        def __iter__(self):
            raise AssertionError("oversized collection was copied before its length was checked")

    project = {
        "estate": {"assets": []},
        "target": {"mappings": []},
        "metadata": {"oversized": MustNotIterate([None] * 10_001)},
    }

    with pytest.raises(ValueError, match="nested items"):
        validate_migration_size(project)


def test_pack_override_has_a_small_identifier_limit():
    project = {"estate": {"assets": []}, "target": {"mappings": []}}

    with pytest.raises(ValueError, match="pack name.*text characters"):
        validate_migration_size(project, pack="x" * 129)
