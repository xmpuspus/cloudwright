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
