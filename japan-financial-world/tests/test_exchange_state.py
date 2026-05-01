from datetime import date

import pytest

from spaces.exchange.space import ExchangeSpace
from spaces.exchange.state import (
    DuplicateListingError,
    DuplicateMarketStateError,
    ListingState,
    MarketState,
)
from world.clock import Clock
from world.ledger import Ledger


def _market(
    market_id: str = "market:reference_equity_market",
    *,
    market_type: str = "stock_exchange",
    tier: str = "primary",
    status: str = "active",
    metadata: dict | None = None,
) -> MarketState:
    return MarketState(
        market_id=market_id,
        market_type=market_type,
        tier=tier,
        status=status,
        metadata=metadata or {},
    )


def _listing(
    market_id: str = "market:reference_equity_market",
    asset_id: str = "asset:reference_manufacturer_equity",
    *,
    listing_status: str = "listed",
    metadata: dict | None = None,
) -> ListingState:
    return ListingState(
        market_id=market_id,
        asset_id=asset_id,
        listing_status=listing_status,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# MarketState dataclass
# ---------------------------------------------------------------------------


def test_market_state_carries_required_fields():
    market = _market()
    assert market.market_id == "market:reference_equity_market"
    assert market.market_type == "stock_exchange"
    assert market.tier == "primary"
    assert market.status == "active"
    assert market.metadata == {}


def test_market_state_rejects_empty_market_id():
    with pytest.raises(ValueError):
        MarketState(market_id="")


def test_market_state_to_dict_is_serializable():
    market = _market(metadata={"timezone": "Asia/Tokyo"})
    assert market.to_dict() == {
        "market_id": "market:reference_equity_market",
        "market_type": "stock_exchange",
        "tier": "primary",
        "status": "active",
        "metadata": {"timezone": "Asia/Tokyo"},
    }


def test_market_state_is_immutable():
    market = _market()
    with pytest.raises(Exception):
        market.market_type = "bond_market"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ListingState dataclass
# ---------------------------------------------------------------------------


def test_listing_state_carries_required_fields():
    listing = _listing()
    assert listing.market_id == "market:reference_equity_market"
    assert listing.asset_id == "asset:reference_manufacturer_equity"
    assert listing.listing_status == "listed"
    assert listing.metadata == {}


def test_listing_state_rejects_empty_market_or_asset_id():
    with pytest.raises(ValueError):
        ListingState(market_id="", asset_id="asset:foo")
    with pytest.raises(ValueError):
        ListingState(market_id="market:reference_equity_market", asset_id="")


def test_listing_state_to_dict_is_serializable():
    listing = _listing(listing_status="suspended", metadata={"halted_until": "2026-02-01"})
    assert listing.to_dict() == {
        "market_id": "market:reference_equity_market",
        "asset_id": "asset:reference_manufacturer_equity",
        "listing_status": "suspended",
        "metadata": {"halted_until": "2026-02-01"},
    }


def test_listing_state_is_immutable():
    listing = _listing()
    with pytest.raises(Exception):
        listing.listing_status = "delisted"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExchangeSpace market CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_market_state():
    space = ExchangeSpace()
    market = _market()
    space.add_market_state(market)
    assert space.get_market_state("market:reference_equity_market") is market


def test_get_market_state_returns_none_for_unknown():
    space = ExchangeSpace()
    assert space.get_market_state("market:unknown") is None


def test_duplicate_market_state_rejected():
    space = ExchangeSpace()
    space.add_market_state(_market())
    with pytest.raises(DuplicateMarketStateError):
        space.add_market_state(_market())


def test_list_markets_returns_all_in_insertion_order():
    space = ExchangeSpace()
    space.add_market_state(_market("market:a"))
    space.add_market_state(_market("market:b"))
    space.add_market_state(_market("market:c"))

    listed = space.list_markets()
    assert [m.market_id for m in listed] == ["market:a", "market:b", "market:c"]


def test_list_markets_returns_empty_when_no_markets():
    space = ExchangeSpace()
    assert space.list_markets() == ()


# ---------------------------------------------------------------------------
# ExchangeSpace listing CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_listing():
    space = ExchangeSpace()
    listing = _listing()
    space.add_listing(listing)
    assert space.get_listing("market:reference_equity_market", "asset:reference_manufacturer_equity") is listing


def test_get_listing_returns_none_for_unknown_pair():
    space = ExchangeSpace()
    assert space.get_listing("market:reference_equity_market", "asset:ghost") is None


def test_duplicate_listing_rejected():
    space = ExchangeSpace()
    space.add_listing(_listing())
    with pytest.raises(DuplicateListingError):
        space.add_listing(_listing())


def test_same_asset_can_be_listed_on_multiple_markets():
    space = ExchangeSpace()
    space.add_listing(_listing(market_id="market:reference_equity_market", asset_id="asset:reference_manufacturer_equity"))
    space.add_listing(_listing(market_id="market:nyse", asset_id="asset:reference_manufacturer_equity"))
    assert space.get_listing("market:reference_equity_market", "asset:reference_manufacturer_equity") is not None
    assert space.get_listing("market:nyse", "asset:reference_manufacturer_equity") is not None


def test_list_listings_returns_all_in_insertion_order():
    space = ExchangeSpace()
    space.add_listing(_listing(market_id="market:reference_equity_market", asset_id="asset:a"))
    space.add_listing(_listing(market_id="market:reference_equity_market", asset_id="asset:b"))
    space.add_listing(_listing(market_id="market:nyse", asset_id="asset:c"))

    listings = space.list_listings()
    assert [(item.market_id, item.asset_id) for item in listings] == [
        ("market:reference_equity_market", "asset:a"),
        ("market:reference_equity_market", "asset:b"),
        ("market:nyse", "asset:c"),
    ]


def test_list_assets_on_market_filters_by_market():
    space = ExchangeSpace()
    space.add_listing(_listing(market_id="market:reference_equity_market", asset_id="asset:reference_manufacturer_equity"))
    space.add_listing(_listing(market_id="market:reference_equity_market", asset_id="asset:sony_eq"))
    space.add_listing(_listing(market_id="market:jgb", asset_id="asset:jgb_10y"))

    on_tse = space.list_assets_on_market("market:reference_equity_market")
    on_jgb = space.list_assets_on_market("market:jgb")
    on_unknown = space.list_assets_on_market("market:nyse")

    assert {item.asset_id for item in on_tse} == {"asset:reference_manufacturer_equity", "asset:sony_eq"}
    assert {item.asset_id for item in on_jgb} == {"asset:jgb_10y"}
    assert on_unknown == ()


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_sorts_markets_and_listings_deterministically():
    space = ExchangeSpace()
    space.add_market_state(_market("market:b"))
    space.add_market_state(_market("market:a"))
    space.add_listing(_listing(market_id="market:b", asset_id="asset:y"))
    space.add_listing(_listing(market_id="market:a", asset_id="asset:z"))
    space.add_listing(_listing(market_id="market:a", asset_id="asset:x"))

    snap = space.snapshot()
    assert snap["space_id"] == "exchange"
    assert snap["market_count"] == 2
    assert snap["listing_count"] == 3
    assert [m["market_id"] for m in snap["markets"]] == ["market:a", "market:b"]
    assert [(item["market_id"], item["asset_id"]) for item in snap["listings"]] == [
        ("market:a", "asset:x"),
        ("market:a", "asset:z"),
        ("market:b", "asset:y"),
    ]


def test_snapshot_returns_empty_structure_for_empty_space():
    snap = ExchangeSpace().snapshot()
    assert snap == {
        "space_id": "exchange",
        "market_count": 0,
        "listing_count": 0,
        "markets": [],
        "listings": [],
    }


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_market_state_records_to_ledger():
    ledger = Ledger()
    space = ExchangeSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_market_state(_market(market_type="bond_market", tier="secondary"))

    records = ledger.filter(event_type="market_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "market:reference_equity_market"
    assert record.payload["market_type"] == "bond_market"
    assert record.payload["tier"] == "secondary"
    assert record.simulation_date == "2026-01-01"
    assert record.space_id == "exchange"


def test_add_listing_records_to_ledger():
    ledger = Ledger()
    space = ExchangeSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_listing(_listing(listing_status="listed"))

    records = ledger.filter(event_type="listing_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "asset:reference_manufacturer_equity"
    assert record.target == "market:reference_equity_market"
    assert record.payload["market_id"] == "market:reference_equity_market"
    assert record.payload["asset_id"] == "asset:reference_manufacturer_equity"
    assert record.payload["listing_status"] == "listed"


def test_add_market_state_does_not_record_when_no_ledger():
    space = ExchangeSpace()
    space.add_market_state(_market())  # should not raise
    assert space.get_market_state("market:reference_equity_market") is not None


# ---------------------------------------------------------------------------
# Helper accessors return None / () when refs unbound
# ---------------------------------------------------------------------------


def test_get_latest_price_returns_none_when_unbound():
    space = ExchangeSpace()
    assert space.get_latest_price("asset:reference_manufacturer_equity") is None


def test_get_price_history_returns_empty_when_unbound():
    space = ExchangeSpace()
    assert space.get_price_history("asset:reference_manufacturer_equity") == ()


def test_get_visible_signals_returns_empty_when_unbound():
    space = ExchangeSpace()
    assert space.get_visible_signals("market:reference_equity_market") == ()
