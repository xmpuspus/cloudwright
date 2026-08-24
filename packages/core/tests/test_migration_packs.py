"""Domain-pack behavior tests."""

from __future__ import annotations

import pytest
from cloudwright.migration import EstateAsset
from cloudwright.migration.packs import criteria_for, list_packs, load_pack


def test_pack_catalog_lists_ph_telco_with_human_metadata():
    summaries = list_packs()

    ph_pack = next(item for item in summaries if item.name == "ph_telco")
    assert ph_pack.title == "Philippine telecommunications"
    assert ph_pack.jurisdiction == "PH"


def test_pack_loads_primary_sources_and_portable_criteria():
    pack = load_pack("ph_telco")

    assert pack.version == "1.0"
    assert any(
        source.url == "https://lawphil.net/statutes/repacts/ra2022/ra_11934_2022.html" for source in pack.sources
    )
    criterion = next(item for item in pack.criteria if item.id == "mnp-porting-duration")
    assert criterion.metric == "porting_duration_hours"
    assert criterion.comparator == "lte"
    assert criterion.target_value == 48


def test_pack_matches_assets_and_deduplicates_shared_requirements():
    assets = [
        EstateAsset(
            id="subscriber-primary",
            name="Subscriber store",
            kind="data",
            data_classes=["subscriber_identity", "personal_data"],
            tags=["sim_registration"],
        ),
        EstateAsset(
            id="subscriber-replica",
            name="Subscriber replica",
            kind="data",
            data_classes=["subscriber_identity"],
            tags=["sim_registration"],
        ),
        EstateAsset(
            id="billing",
            name="Billing",
            kind="application",
            data_classes=["financial_balance"],
            tags=["billing"],
        ),
    ]

    criteria = criteria_for(load_pack("ph_telco"), assets)
    criterion_ids = [item.id for item in criteria]

    assert criterion_ids.count("subscriber-record-parity") == 1
    assert "privacy-impact-assessment" in criterion_ids
    assert "billing-total-delta" in criterion_ids
    assert len(criterion_ids) == len(set(criterion_ids))


def test_pack_does_not_add_telco_criteria_to_unmatched_assets():
    assets = [EstateAsset(id="erp", name="ERP", kind="application", tags=["manufacturing"])]

    assert criteria_for(load_pack("ph_telco"), assets) == []


def test_missing_pack_fails_with_available_names():
    with pytest.raises(ValueError, match="ph_telco"):
        load_pack("missing")
