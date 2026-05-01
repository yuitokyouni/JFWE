from datetime import date

import pytest

from spaces.real_estate.space import RealEstateSpace
from spaces.real_estate.state import (
    DuplicatePropertyAssetStateError,
    DuplicatePropertyMarketStateError,
    PropertyAssetState,
    PropertyMarketState,
)
from world.clock import Clock
from world.ledger import Ledger


def _market(
    property_market_id: str = "market:reference_central_office",
    *,
    region: str = "reference_central",
    property_type: str = "office",
    tier: str = "prime",
    status: str = "active",
    metadata: dict | None = None,
) -> PropertyMarketState:
    return PropertyMarketState(
        property_market_id=property_market_id,
        region=region,
        property_type=property_type,
        tier=tier,
        status=status,
        metadata=metadata or {},
    )


def _asset(
    asset_id: str = "asset:marunouchi_bldg_a",
    *,
    property_market_id: str = "market:reference_central_office",
    asset_type: str = "office_building",
    status: str = "active",
    metadata: dict | None = None,
) -> PropertyAssetState:
    return PropertyAssetState(
        asset_id=asset_id,
        property_market_id=property_market_id,
        asset_type=asset_type,
        status=status,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# PropertyMarketState dataclass
# ---------------------------------------------------------------------------


def test_property_market_state_carries_required_fields():
    market = _market()
    assert market.property_market_id == "market:reference_central_office"
    assert market.region == "reference_central"
    assert market.property_type == "office"
    assert market.tier == "prime"
    assert market.status == "active"
    assert market.metadata == {}


def test_property_market_state_rejects_empty_id():
    with pytest.raises(ValueError):
        PropertyMarketState(property_market_id="")


def test_property_market_state_to_dict_is_serializable():
    market = _market(metadata={"sub_market": "marunouchi"})
    assert market.to_dict() == {
        "property_market_id": "market:reference_central_office",
        "region": "reference_central",
        "property_type": "office",
        "tier": "prime",
        "status": "active",
        "metadata": {"sub_market": "marunouchi"},
    }


def test_property_market_state_is_immutable():
    market = _market()
    with pytest.raises(Exception):
        market.region = "osaka"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PropertyAssetState dataclass
# ---------------------------------------------------------------------------


def test_property_asset_state_carries_required_fields():
    asset = _asset()
    assert asset.asset_id == "asset:marunouchi_bldg_a"
    assert asset.property_market_id == "market:reference_central_office"
    assert asset.asset_type == "office_building"
    assert asset.status == "active"
    assert asset.metadata == {}


def test_property_asset_state_rejects_empty_asset_id():
    with pytest.raises(ValueError):
        PropertyAssetState(asset_id="", property_market_id="market:x")


def test_property_asset_state_rejects_empty_property_market_id():
    with pytest.raises(ValueError):
        PropertyAssetState(asset_id="asset:x", property_market_id="")


def test_property_asset_state_to_dict_is_serializable():
    asset = _asset(asset_type="warehouse", status="under_renovation")
    assert asset.to_dict() == {
        "asset_id": "asset:marunouchi_bldg_a",
        "property_market_id": "market:reference_central_office",
        "asset_type": "warehouse",
        "status": "under_renovation",
        "metadata": {},
    }


def test_property_asset_state_is_immutable():
    asset = _asset()
    with pytest.raises(Exception):
        asset.status = "demolished"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RealEstateSpace property market CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_property_market_state():
    space = RealEstateSpace()
    market = _market()
    space.add_property_market_state(market)
    assert space.get_property_market_state("market:reference_central_office") is market


def test_get_property_market_state_returns_none_for_unknown():
    space = RealEstateSpace()
    assert space.get_property_market_state("market:unknown") is None


def test_duplicate_property_market_rejected():
    space = RealEstateSpace()
    space.add_property_market_state(_market())
    with pytest.raises(DuplicatePropertyMarketStateError):
        space.add_property_market_state(_market())


def test_list_property_markets_returns_all_in_insertion_order():
    space = RealEstateSpace()
    space.add_property_market_state(_market("market:a"))
    space.add_property_market_state(_market("market:b"))
    space.add_property_market_state(_market("market:c"))

    listed = space.list_property_markets()
    assert [m.property_market_id for m in listed] == [
        "market:a",
        "market:b",
        "market:c",
    ]


def test_list_property_markets_returns_empty_when_none_added():
    space = RealEstateSpace()
    assert space.list_property_markets() == ()


# ---------------------------------------------------------------------------
# RealEstateSpace property asset CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_property_asset_state():
    space = RealEstateSpace()
    asset = _asset()
    space.add_property_asset_state(asset)
    assert space.get_property_asset_state("asset:marunouchi_bldg_a") is asset


def test_get_property_asset_state_returns_none_for_unknown():
    space = RealEstateSpace()
    assert space.get_property_asset_state("asset:ghost") is None


def test_duplicate_property_asset_rejected():
    space = RealEstateSpace()
    space.add_property_asset_state(_asset())
    with pytest.raises(DuplicatePropertyAssetStateError):
        space.add_property_asset_state(_asset())


def test_list_property_assets_returns_all_in_insertion_order():
    space = RealEstateSpace()
    space.add_property_asset_state(_asset("asset:a"))
    space.add_property_asset_state(_asset("asset:b"))
    space.add_property_asset_state(_asset("asset:c"))

    listed = space.list_property_assets()
    assert [a.asset_id for a in listed] == ["asset:a", "asset:b", "asset:c"]


def test_property_asset_can_reference_unregistered_market():
    """
    v0.12 does not validate that property_market_id refers to a
    registered market. Adding an asset that points to an unknown
    market is allowed; it is the caller's responsibility to keep the
    references consistent if they care.
    """
    space = RealEstateSpace()
    asset = _asset(property_market_id="market:not_yet_registered")
    space.add_property_asset_state(asset)
    assert space.get_property_asset_state("asset:marunouchi_bldg_a") is asset


def test_list_assets_in_property_market_filters_by_market():
    space = RealEstateSpace()
    space.add_property_asset_state(
        _asset(asset_id="asset:a", property_market_id="market:reference_office")
    )
    space.add_property_asset_state(
        _asset(asset_id="asset:b", property_market_id="market:reference_office")
    )
    space.add_property_asset_state(
        _asset(asset_id="asset:c", property_market_id="market:osaka_residential")
    )

    on_tokyo = space.list_assets_in_property_market("market:reference_office")
    on_osaka = space.list_assets_in_property_market("market:osaka_residential")
    on_unknown = space.list_assets_in_property_market("market:fukuoka")

    assert {a.asset_id for a in on_tokyo} == {"asset:a", "asset:b"}
    assert {a.asset_id for a in on_osaka} == {"asset:c"}
    assert on_unknown == ()


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_sorts_markets_and_assets_deterministically():
    space = RealEstateSpace()
    space.add_property_market_state(_market("market:b"))
    space.add_property_market_state(_market("market:a"))
    space.add_property_asset_state(_asset("asset:y", property_market_id="market:b"))
    space.add_property_asset_state(_asset("asset:z", property_market_id="market:a"))
    space.add_property_asset_state(_asset("asset:x", property_market_id="market:a"))

    snap = space.snapshot()
    assert snap["space_id"] == "real_estate"
    assert snap["property_market_count"] == 2
    assert snap["property_asset_count"] == 3
    assert [m["property_market_id"] for m in snap["property_markets"]] == [
        "market:a",
        "market:b",
    ]
    assert [a["asset_id"] for a in snap["property_assets"]] == [
        "asset:x",
        "asset:y",
        "asset:z",
    ]


def test_snapshot_returns_empty_structure_for_empty_space():
    snap = RealEstateSpace().snapshot()
    assert snap == {
        "space_id": "real_estate",
        "property_market_count": 0,
        "property_asset_count": 0,
        "property_markets": [],
        "property_assets": [],
    }


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_property_market_state_records_to_ledger():
    ledger = Ledger()
    space = RealEstateSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_property_market_state(
        _market(region="osaka_central", property_type="residential")
    )

    records = ledger.filter(event_type="property_market_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "market:reference_central_office"
    assert record.payload["region"] == "osaka_central"
    assert record.payload["property_type"] == "residential"
    assert record.simulation_date == "2026-01-01"
    assert record.space_id == "real_estate"


def test_add_property_asset_state_records_to_ledger():
    ledger = Ledger()
    space = RealEstateSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_property_asset_state(_asset(asset_type="warehouse"))

    records = ledger.filter(event_type="property_asset_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "asset:marunouchi_bldg_a"
    assert record.target == "market:reference_central_office"
    assert record.payload["asset_type"] == "warehouse"
    assert record.payload["property_market_id"] == "market:reference_central_office"


def test_add_state_does_not_record_when_no_ledger():
    space = RealEstateSpace()
    space.add_property_market_state(_market())  # should not raise
    space.add_property_asset_state(_asset())
    assert space.get_property_market_state("market:reference_central_office") is not None
    assert space.get_property_asset_state("asset:marunouchi_bldg_a") is not None


# ---------------------------------------------------------------------------
# Helper accessors return None / () when refs unbound
# ---------------------------------------------------------------------------


def test_get_latest_price_returns_none_when_unbound():
    space = RealEstateSpace()
    assert space.get_latest_price("asset:marunouchi_bldg_a") is None


def test_get_price_history_returns_empty_when_unbound():
    space = RealEstateSpace()
    assert space.get_price_history("asset:marunouchi_bldg_a") == ()


def test_get_visible_signals_returns_empty_when_unbound():
    space = RealEstateSpace()
    assert space.get_visible_signals("market:reference_central_office") == ()
