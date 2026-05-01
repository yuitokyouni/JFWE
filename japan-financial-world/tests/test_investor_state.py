from datetime import date

import pytest

from spaces.investors.space import InvestorSpace
from spaces.investors.state import (
    DuplicateInvestorStateError,
    InvestorState,
    PortfolioExposure,
)
from world.clock import Clock
from world.ledger import Ledger


def _investor(
    investor_id: str = "investor:reference_fund_a",
    *,
    investor_type: str = "pension_fund",
    tier: str = "tier_1",
    status: str = "active",
    metadata: dict | None = None,
) -> InvestorState:
    return InvestorState(
        investor_id=investor_id,
        investor_type=investor_type,
        tier=tier,
        status=status,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# InvestorState dataclass
# ---------------------------------------------------------------------------


def test_investor_state_carries_required_fields():
    investor = _investor()
    assert investor.investor_id == "investor:reference_fund_a"
    assert investor.investor_type == "pension_fund"
    assert investor.tier == "tier_1"
    assert investor.status == "active"
    assert investor.metadata == {}


def test_investor_state_rejects_empty_investor_id():
    with pytest.raises(ValueError):
        InvestorState(investor_id="")


def test_investor_state_to_dict_is_serializable():
    investor = _investor(metadata={"mandate": "diversified"})
    payload = investor.to_dict()
    assert payload == {
        "investor_id": "investor:reference_fund_a",
        "investor_type": "pension_fund",
        "tier": "tier_1",
        "status": "active",
        "metadata": {"mandate": "diversified"},
    }


def test_investor_state_is_immutable():
    investor = _investor()
    with pytest.raises(Exception):
        investor.investor_type = "hedge_fund"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PortfolioExposure dataclass
# ---------------------------------------------------------------------------


def test_portfolio_exposure_carries_full_fields():
    exposure = PortfolioExposure(
        investor_id="investor:reference_fund_a",
        asset_id="asset:aapl",
        quantity=100.0,
        latest_price=150.0,
        market_value=15_000.0,
        asset_type="equity",
        metadata={},
    )
    assert exposure.investor_id == "investor:reference_fund_a"
    assert exposure.asset_id == "asset:aapl"
    assert exposure.quantity == 100.0
    assert exposure.latest_price == 150.0
    assert exposure.market_value == 15_000.0
    assert exposure.asset_type == "equity"


def test_portfolio_exposure_allows_missing_values():
    exposure = PortfolioExposure(
        investor_id="investor:reference_fund_a",
        asset_id="asset:foo",
        quantity=10.0,
        latest_price=None,
        market_value=None,
        asset_type=None,
        metadata={"missing_price": True, "missing_asset_type": True},
    )
    assert exposure.latest_price is None
    assert exposure.market_value is None
    assert exposure.asset_type is None
    assert exposure.metadata["missing_price"] is True


def test_portfolio_exposure_to_dict_is_serializable():
    exposure = PortfolioExposure(
        investor_id="investor:reference_fund_a",
        asset_id="asset:aapl",
        quantity=100.0,
        latest_price=150.0,
        market_value=15_000.0,
        asset_type="equity",
    )
    assert exposure.to_dict() == {
        "investor_id": "investor:reference_fund_a",
        "asset_id": "asset:aapl",
        "quantity": 100.0,
        "latest_price": 150.0,
        "market_value": 15_000.0,
        "asset_type": "equity",
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# InvestorSpace state CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_investor_state():
    space = InvestorSpace()
    investor = _investor()
    space.add_investor_state(investor)
    assert space.get_investor_state("investor:reference_fund_a") is investor


def test_get_investor_state_returns_none_for_unknown():
    space = InvestorSpace()
    assert space.get_investor_state("investor:unknown") is None


def test_duplicate_investor_state_rejected():
    space = InvestorSpace()
    space.add_investor_state(_investor())
    with pytest.raises(DuplicateInvestorStateError):
        space.add_investor_state(_investor())


def test_list_investors_returns_all_in_insertion_order():
    space = InvestorSpace()
    space.add_investor_state(_investor("investor:a"))
    space.add_investor_state(_investor("investor:b"))
    space.add_investor_state(_investor("investor:c"))

    listed = space.list_investors()
    assert [i.investor_id for i in listed] == [
        "investor:a",
        "investor:b",
        "investor:c",
    ]


def test_list_investors_returns_empty_when_no_investors():
    space = InvestorSpace()
    assert space.list_investors() == ()


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_includes_all_investors_sorted():
    space = InvestorSpace()
    space.add_investor_state(_investor("investor:b", investor_type="hedge_fund"))
    space.add_investor_state(_investor("investor:a", investor_type="pension_fund"))

    snap = space.snapshot()
    assert snap["space_id"] == "investors"
    assert snap["count"] == 2
    assert [item["investor_id"] for item in snap["investors"]] == [
        "investor:a",
        "investor:b",
    ]


def test_snapshot_returns_empty_structure_for_empty_space():
    snap = InvestorSpace().snapshot()
    assert snap == {"space_id": "investors", "count": 0, "investors": []}


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_add_investor_state_records_to_ledger():
    ledger = Ledger()
    space = InvestorSpace(
        ledger=ledger, clock=Clock(current_date=date(2026, 1, 1))
    )
    space.add_investor_state(
        _investor(investor_type="hedge_fund", tier="tier_2")
    )

    records = ledger.filter(event_type="investor_state_added")
    assert len(records) == 1
    record = records[0]
    assert record.object_id == "investor:reference_fund_a"
    assert record.agent_id == "investor:reference_fund_a"
    assert record.payload["investor_type"] == "hedge_fund"
    assert record.payload["tier"] == "tier_2"
    assert record.payload["status"] == "active"
    assert record.simulation_date == "2026-01-01"
    assert record.space_id == "investors"


def test_add_investor_state_does_not_record_when_no_ledger():
    space = InvestorSpace()
    space.add_investor_state(_investor())  # should not raise
    assert space.get_investor_state("investor:reference_fund_a") is not None


# ---------------------------------------------------------------------------
# Helper accessors return None / () when world refs are missing
# ---------------------------------------------------------------------------


def test_get_balance_sheet_view_returns_none_when_unbound():
    space = InvestorSpace()
    assert space.get_balance_sheet_view("investor:reference_fund_a") is None


def test_get_constraint_evaluations_returns_empty_when_unbound():
    space = InvestorSpace()
    assert space.get_constraint_evaluations("investor:reference_fund_a") == ()


def test_get_visible_signals_returns_empty_when_unbound():
    space = InvestorSpace()
    assert space.get_visible_signals("investor:reference_fund_a") == ()


def test_list_portfolio_positions_returns_empty_when_unbound():
    space = InvestorSpace()
    assert space.list_portfolio_positions("investor:reference_fund_a") == ()


def test_list_portfolio_exposures_returns_empty_when_unbound():
    space = InvestorSpace()
    assert space.list_portfolio_exposures("investor:reference_fund_a") == ()
