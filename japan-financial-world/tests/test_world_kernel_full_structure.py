"""
v0.15 Cross-space read-only integration test.

This file verifies that the eight domain spaces enumerated in §2
(Corporate, Banking, Investors, Exchange, Real Estate, Information,
Policy, External) can coexist in a single WorldKernel, share the
common books / projections / signals, communicate through the
EventBus, and run for a full year without any space mutating any
other space's state and without any business behavior being
implemented.

This is the v0 closing test. After it passes, the world kernel
structure is considered complete; subsequent milestones (v1+) layer
behavior, calibration, and scenarios on top.
"""

from __future__ import annotations

from datetime import date

from spaces.banking.space import BankSpace
from spaces.banking.state import BankState
from spaces.corporate.space import CorporateSpace
from spaces.corporate.state import FirmState
from spaces.exchange.space import ExchangeSpace
from spaces.exchange.state import ListingState, MarketState
from spaces.external.space import ExternalSpace
from spaces.external.state import ExternalFactorState, ExternalSourceState
from spaces.information.space import InformationSpace
from spaces.information.state import (
    InformationChannelState,
    InformationSourceState,
)
from spaces.investors.space import InvestorSpace
from spaces.investors.state import InvestorState
from spaces.policy.space import PolicySpace
from spaces.policy.state import PolicyAuthorityState, PolicyInstrumentState
from spaces.real_estate.space import RealEstateSpace
from spaces.real_estate.state import PropertyAssetState, PropertyMarketState
from world.clock import Clock
from world.constraints import ConstraintRecord
from world.contracts import ContractRecord
from world.events import WorldEvent
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import RegisteredObject, Registry
from world.scheduler import Scheduler
from world.signals import InformationSignal
from world.state import State


# ---------------------------------------------------------------------------
# World builder
# ---------------------------------------------------------------------------


def _build_full_world() -> tuple[
    WorldKernel,
    dict[str, object],
]:
    """
    Construct a populated WorldKernel with all 8 spaces registered and a
    coherent minimal seed of state / books / signals.

    Returns the kernel and a dict mapping space_id -> space instance so
    individual tests can inspect each one.
    """
    kernel = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )

    spaces: dict[str, object] = {
        "corporate": CorporateSpace(),
        "banking": BankSpace(),
        "investors": InvestorSpace(),
        "exchange": ExchangeSpace(),
        "real_estate": RealEstateSpace(),
        "information": InformationSpace(),
        "policy": PolicySpace(),
        "external": ExternalSpace(),
    }

    for space in spaces.values():
        kernel.register_space(space)

    # ---- Domain-space identity-level state ----
    spaces["corporate"].add_firm_state(  # type: ignore[attr-defined]
        FirmState(firm_id="firm:reference_manufacturer_a", sector="auto", tier="large")
    )
    spaces["banking"].add_bank_state(  # type: ignore[attr-defined]
        BankState(bank_id="bank:reference_bank_a", bank_type="city_bank", tier="large")
    )
    spaces["investors"].add_investor_state(  # type: ignore[attr-defined]
        InvestorState(
            investor_id="investor:reference_fund_a",
            investor_type="pension_fund",
            tier="tier_1",
        )
    )
    spaces["exchange"].add_market_state(  # type: ignore[attr-defined]
        MarketState(
            market_id="market:reference_equity_market",
            market_type="stock_exchange",
            tier="primary",
        )
    )
    spaces["exchange"].add_listing(  # type: ignore[attr-defined]
        ListingState(market_id="market:reference_equity_market", asset_id="asset:reference_manufacturer_equity")
    )
    spaces["real_estate"].add_property_market_state(  # type: ignore[attr-defined]
        PropertyMarketState(
            property_market_id="market:reference_central_office",
            region="reference_central",
            property_type="office",
        )
    )
    spaces["real_estate"].add_property_asset_state(  # type: ignore[attr-defined]
        PropertyAssetState(
            asset_id="asset:marunouchi_bldg_a",
            property_market_id="market:reference_central_office",
            asset_type="office_building",
        )
    )
    spaces["information"].add_source_state(  # type: ignore[attr-defined]
        InformationSourceState(
            source_id="source:reference_rating_agency_a",
            source_type="rating_agency",
            tier="tier_1",
        )
    )
    spaces["information"].add_channel_state(  # type: ignore[attr-defined]
        InformationChannelState(
            channel_id="channel:reuters_wire",
            channel_type="wire_service",
            visibility="public",
        )
    )
    spaces["policy"].add_authority_state(  # type: ignore[attr-defined]
        PolicyAuthorityState(
            authority_id="authority:reference_central_bank",
            authority_type="central_bank",
            tier="national",
        )
    )
    spaces["policy"].add_instrument_state(  # type: ignore[attr-defined]
        PolicyInstrumentState(
            instrument_id="instrument:boj_policy_rate",
            authority_id="authority:reference_central_bank",
            instrument_type="policy_rate",
        )
    )
    spaces["external"].add_factor_state(  # type: ignore[attr-defined]
        ExternalFactorState(
            factor_id="factor:usd_jpy",
            factor_type="fx_rate",
            unit="USD/JPY",
        )
    )
    spaces["external"].add_source_state(  # type: ignore[attr-defined]
        ExternalSourceState(
            source_id="source:imf",
            source_type="international_organization",
        )
    )

    # ---- Kernel-level books ----
    # Registry: a few representative assets so registry-derived asset
    # types resolve in projections.
    kernel.register_object(
        RegisteredObject(
            id="asset:reference_manufacturer_equity",
            kind="asset",
            type="equity",
            space="exchange",
        )
    )
    kernel.register_object(
        RegisteredObject(
            id="asset:cash_jpy",
            kind="asset",
            type="cash",
            space="exchange",
        )
    )
    kernel.register_object(
        RegisteredObject(
            id="asset:marunouchi_bldg_a",
            kind="asset",
            type="office_building",
            space="real_estate",
        )
    )

    # Ownership: the reference fund holds the reference manufacturer equity; firm holds some cash for
    # the leverage constraint to compute against.
    kernel.ownership.add_position("investor:reference_fund_a", "asset:reference_manufacturer_equity", 100)
    kernel.ownership.add_position("firm:reference_manufacturer_a", "asset:cash_jpy", 1_000_000)

    # Contracts: bank lends to firm.
    kernel.contracts.add_contract(
        ContractRecord(
            contract_id="contract:loan_001",
            contract_type="loan",
            parties=("bank:reference_bank_a", "firm:reference_manufacturer_a"),
            principal=500_000.0,
            metadata={
                "lender_id": "bank:reference_bank_a",
                "borrower_id": "firm:reference_manufacturer_a",
            },
        )
    )

    # Prices for every priced asset.
    kernel.prices.set_price("asset:reference_manufacturer_equity", 2_500.0, "2026-01-01", "exchange")
    kernel.prices.set_price("asset:cash_jpy", 1.0, "2026-01-01", "system")
    kernel.prices.set_price(
        "asset:marunouchi_bldg_a", 50_000_000_000.0, "2026-01-01", "appraisal"
    )

    # Constraint: leverage ceiling on the reference manufacturer.
    kernel.constraints.add_constraint(
        ConstraintRecord(
            constraint_id="constraint:reference_manufacturer_leverage",
            owner_id="firm:reference_manufacturer_a",
            constraint_type="max_leverage",
            threshold=0.7,
            comparison="<=",
        )
    )

    # Signals: a public rating action and a restricted internal memo.
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:reference_rating_agency_a_rating",
            signal_type="rating_action",
            subject_id="firm:reference_manufacturer_a",
            source_id="source:reference_rating_agency_a",
            published_date="2026-01-01",
            payload={"rating": "AA-"},
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:internal_minutes",
            signal_type="internal_memo",
            subject_id="authority:reference_central_bank",
            source_id="authority:reference_central_bank",
            published_date="2026-01-01",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:boj_committee",)},
        )
    )

    return kernel, spaces


# ---------------------------------------------------------------------------
# 1. Full one-year run with all 8 spaces
# ---------------------------------------------------------------------------


def test_full_world_runs_for_one_year_without_exceptions():
    kernel, _ = _build_full_world()

    kernel.run(days=365)

    assert kernel.clock.current_date == date(2027, 1, 1)


def test_each_space_fires_its_declared_frequencies_over_one_year():
    kernel, _ = _build_full_world()

    kernel.run(days=365)

    expected_counts = {
        # Corporate: monthly + quarterly + yearly
        "task:corporate_monthly": 12,
        "task:corporate_quarterly": 4,
        "task:corporate_yearly": 1,
        # Banking: daily + quarterly
        "task:banking_daily": 365,
        "task:banking_quarterly": 4,
        # Investors: daily + monthly
        "task:investors_daily": 365,
        "task:investors_monthly": 12,
        # Exchange: daily
        "task:exchange_daily": 365,
        # Real estate: monthly + quarterly
        "task:real_estate_monthly": 12,
        "task:real_estate_quarterly": 4,
        # Information: daily
        "task:information_daily": 365,
        # Policy: monthly
        "task:policy_monthly": 12,
        # External: daily
        "task:external_daily": 365,
    }
    for task_id, expected in expected_counts.items():
        records = kernel.ledger.filter(
            event_type="task_executed", task_id=task_id
        )
        assert len(records) == expected, (
            f"{task_id} fired {len(records)} times, expected {expected}"
        )


def test_state_snapshots_are_created_on_month_ends():
    kernel, _ = _build_full_world()
    kernel.run(days=365)

    snapshots = kernel.ledger.filter(event_type="state_snapshot_created")
    assert len(snapshots) == 12  # one per month-end across 2026


# ---------------------------------------------------------------------------
# 2. Each space reads its relevant projections
# ---------------------------------------------------------------------------


def test_corporate_space_reads_balance_sheet_constraints_signals():
    kernel, spaces = _build_full_world()
    corporate = spaces["corporate"]

    view = corporate.get_balance_sheet_view("firm:reference_manufacturer_a")
    assert view is not None
    assert view.agent_id == "firm:reference_manufacturer_a"
    # the reference manufacturer holds 1M of cash @ 1.0 -> asset_value=1_000_000
    # the reference manufacturer borrows 500k from the reference bank -> liabilities=500_000
    assert view.asset_value == 1_000_000.0
    assert view.liabilities == 500_000.0
    assert view.net_asset_value == 500_000.0

    evaluations = corporate.get_constraint_evaluations("firm:reference_manufacturer_a")
    assert len(evaluations) == 1
    assert evaluations[0].constraint_id == "constraint:reference_manufacturer_leverage"
    # leverage = 500k / 1M = 0.5 <= 0.7 -> ok
    assert evaluations[0].status == "ok"

    visible = corporate.get_visible_signals("firm:reference_manufacturer_a")
    visible_ids = {s.signal_id for s in visible}
    assert "signal:reference_rating_agency_a_rating" in visible_ids
    # Restricted signal not visible to firm:reference_manufacturer_a.
    assert "signal:internal_minutes" not in visible_ids


def test_bank_space_reads_contracts_lending_balance_sheet_constraints_signals():
    kernel, spaces = _build_full_world()
    bank = spaces["banking"]

    contracts = bank.list_contracts_for_bank("bank:reference_bank_a")
    assert len(contracts) == 1
    assert contracts[0].contract_id == "contract:loan_001"

    exposures = bank.list_lending_exposures("bank:reference_bank_a")
    assert len(exposures) == 1
    assert exposures[0].borrower_id == "firm:reference_manufacturer_a"
    assert exposures[0].principal == 500_000.0

    view = bank.get_balance_sheet_view("bank:reference_bank_a")
    assert view is not None
    # Bank is lender; principal counts as financial asset.
    assert view.asset_value == 500_000.0
    assert view.liabilities == 0.0

    evaluations = bank.get_constraint_evaluations("bank:reference_bank_a")
    assert evaluations == ()  # no constraints attached to the bank

    visible = bank.get_visible_signals("bank:reference_bank_a")
    assert {s.signal_id for s in visible} == {"signal:reference_rating_agency_a_rating"}


def test_investor_space_reads_portfolio_balance_sheet_constraints_signals():
    kernel, spaces = _build_full_world()
    investor = spaces["investors"]

    positions = investor.list_portfolio_positions("investor:reference_fund_a")
    assert len(positions) == 1
    assert positions[0].asset_id == "asset:reference_manufacturer_equity"
    assert positions[0].quantity == 100.0

    exposures = investor.list_portfolio_exposures("investor:reference_fund_a")
    assert len(exposures) == 1
    e = exposures[0]
    assert e.asset_id == "asset:reference_manufacturer_equity"
    assert e.quantity == 100.0
    assert e.latest_price == 2_500.0
    assert e.market_value == 250_000.0
    assert e.asset_type == "equity"

    view = investor.get_balance_sheet_view("investor:reference_fund_a")
    assert view is not None
    assert view.asset_value == 250_000.0

    evaluations = investor.get_constraint_evaluations("investor:reference_fund_a")
    assert evaluations == ()

    visible = investor.get_visible_signals("investor:reference_fund_a")
    assert {s.signal_id for s in visible} == {"signal:reference_rating_agency_a_rating"}


def test_exchange_space_reads_listings_prices_signals():
    kernel, spaces = _build_full_world()
    exchange = spaces["exchange"]

    listings = exchange.list_assets_on_market("market:reference_equity_market")
    assert len(listings) == 1
    assert listings[0].asset_id == "asset:reference_manufacturer_equity"

    latest = exchange.get_latest_price("asset:reference_manufacturer_equity")
    assert latest is not None
    assert latest.price == 2_500.0

    history = exchange.get_price_history("asset:reference_manufacturer_equity")
    assert len(history) == 1

    visible = exchange.get_visible_signals("market:reference_equity_market")
    assert {s.signal_id for s in visible} == {"signal:reference_rating_agency_a_rating"}


def test_real_estate_space_reads_property_assets_prices_signals():
    kernel, spaces = _build_full_world()
    real_estate = spaces["real_estate"]

    assets = real_estate.list_assets_in_property_market(
        "market:reference_central_office"
    )
    assert len(assets) == 1
    assert assets[0].asset_id == "asset:marunouchi_bldg_a"

    latest = real_estate.get_latest_price("asset:marunouchi_bldg_a")
    assert latest is not None
    assert latest.price == 50_000_000_000.0

    visible = real_estate.get_visible_signals("market:reference_central_office")
    assert {s.signal_id for s in visible} == {"signal:reference_rating_agency_a_rating"}


def test_information_space_reads_signals_by_source_type_visibility():
    kernel, spaces = _build_full_world()
    info = spaces["information"]

    by_source = info.list_signals_by_source("source:reference_rating_agency_a")
    assert {s.signal_id for s in by_source} == {"signal:reference_rating_agency_a_rating"}

    by_type = info.list_signals_by_type("rating_action")
    assert {s.signal_id for s in by_type} == {"signal:reference_rating_agency_a_rating"}

    visible = info.list_visible_signals("agent:somebody_public")
    assert {s.signal_id for s in visible} == {"signal:reference_rating_agency_a_rating"}

    # The restricted signal is visible to its allowed viewer.
    visible_committee = info.list_visible_signals("agent:boj_committee")
    assert {s.signal_id for s in visible_committee} == {
        "signal:reference_rating_agency_a_rating",
        "signal:internal_minutes",
    }


def test_policy_space_reads_visible_signals():
    kernel, spaces = _build_full_world()
    policy = spaces["policy"]

    visible = policy.get_visible_signals("authority:reference_central_bank")
    # Policy authority sees the public rating action; the restricted
    # internal memo is invisible because authority:reference_central_bank is not in the
    # allowed_viewers list (which contains agent:boj_committee only).
    assert {s.signal_id for s in visible} == {"signal:reference_rating_agency_a_rating"}


def test_external_space_reads_visible_signals():
    kernel, spaces = _build_full_world()
    external = spaces["external"]

    visible = external.get_visible_signals("agent:strategy_observer")
    assert {s.signal_id for s in visible} == {"signal:reference_rating_agency_a_rating"}


# ---------------------------------------------------------------------------
# 3. EventBus integration
# ---------------------------------------------------------------------------


def test_event_bus_delivers_signal_referencing_event_to_two_target_spaces():
    """
    A WorldEvent that references a signal_id must be deliverable to
    multiple target spaces. Per v0.3 (§22), delivery happens at least
    one tick after publication. Per v0.7 (§26.5), event delivery is
    independent of signal visibility.

    The two target spaces below (banking, investors) are chosen
    because both declare DAILY frequencies — their tasks fire on
    every tick, including day 2, so collection happens immediately.
    Spaces that fire only on month-ends would receive the event
    later in the month, which is also valid v0.3 behavior but harder
    to assert in a short-running test.
    """
    kernel, _ = _build_full_world()

    # Publish on day 1 (before any tick) targeting two daily-firing spaces.
    kernel.event_bus.publish(
        WorldEvent(
            event_id="event:rating_announcement",
            simulation_date="2026-01-01",
            source_space="information",
            target_spaces=("banking", "investors"),
            event_type="signal_emitted",
            payload={"signal_id": "signal:reference_rating_agency_a_rating"},
            related_ids=("signal:reference_rating_agency_a_rating",),
        )
    )

    # Day 1 tick: publication_date == current_date, so no delivery yet.
    kernel.run(days=1)
    delivered_after_day_1 = kernel.ledger.filter(event_type="event_delivered")
    assert len(delivered_after_day_1) == 0

    # Day 2 tick: publication_date < current_date and delivery_date <=
    # current_date, so each target receives.
    kernel.run(days=1)
    delivered_after_day_2 = kernel.ledger.filter(event_type="event_delivered")
    assert len(delivered_after_day_2) == 2
    targets = {record.target for record in delivered_after_day_2}
    assert targets == {"banking", "investors"}

    # The same signal_id is reachable through SignalBook regardless of
    # whether the EventBus delivered the announcement.
    fetched = kernel.signals.get_signal("signal:reference_rating_agency_a_rating")
    assert fetched.signal_type == "rating_action"


def test_event_bus_delivery_is_independent_of_signal_visibility():
    """
    Even a restricted signal can be referenced from a WorldEvent and
    delivered through the EventBus. Visibility is enforced when a
    space queries SignalBook directly, not by transport.
    """
    kernel, _ = _build_full_world()

    kernel.event_bus.publish(
        WorldEvent(
            event_id="event:internal_circulation",
            simulation_date="2026-01-01",
            source_space="policy",
            target_spaces=("banking",),
            event_type="signal_emitted",
            payload={"signal_id": "signal:internal_minutes"},
            related_ids=("signal:internal_minutes",),
        )
    )

    kernel.run(days=2)

    delivered = kernel.ledger.filter(event_type="event_delivered")
    targets = {record.target for record in delivered}
    assert "banking" in targets

    # But SignalBook still hides the restricted signal from banking.
    visible_to_banking = kernel.signals.list_visible_to(
        "banking", as_of_date="2026-01-03"
    )
    visible_ids = {s.signal_id for s in visible_to_banking}
    assert "signal:internal_minutes" not in visible_ids


# ---------------------------------------------------------------------------
# 4. Read operations do not mutate world books
# ---------------------------------------------------------------------------


def test_read_operations_across_all_spaces_do_not_mutate_world_books():
    kernel, spaces = _build_full_world()

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    # Exercise every read accessor on every space.
    spaces["corporate"].get_balance_sheet_view("firm:reference_manufacturer_a")
    spaces["corporate"].get_constraint_evaluations("firm:reference_manufacturer_a")
    spaces["corporate"].get_visible_signals("firm:reference_manufacturer_a")
    spaces["corporate"].snapshot()

    spaces["banking"].list_contracts_for_bank("bank:reference_bank_a")
    spaces["banking"].list_lending_exposures("bank:reference_bank_a")
    spaces["banking"].get_balance_sheet_view("bank:reference_bank_a")
    spaces["banking"].get_constraint_evaluations("bank:reference_bank_a")
    spaces["banking"].get_visible_signals("bank:reference_bank_a")
    spaces["banking"].snapshot()

    spaces["investors"].list_portfolio_positions("investor:reference_fund_a")
    spaces["investors"].list_portfolio_exposures("investor:reference_fund_a")
    spaces["investors"].get_balance_sheet_view("investor:reference_fund_a")
    spaces["investors"].get_constraint_evaluations("investor:reference_fund_a")
    spaces["investors"].get_visible_signals("investor:reference_fund_a")
    spaces["investors"].snapshot()

    spaces["exchange"].list_assets_on_market("market:reference_equity_market")
    spaces["exchange"].get_latest_price("asset:reference_manufacturer_equity")
    spaces["exchange"].get_price_history("asset:reference_manufacturer_equity")
    spaces["exchange"].get_visible_signals("market:reference_equity_market")
    spaces["exchange"].snapshot()

    spaces["real_estate"].list_assets_in_property_market("market:reference_central_office")
    spaces["real_estate"].get_latest_price("asset:marunouchi_bldg_a")
    spaces["real_estate"].get_visible_signals("market:reference_central_office")
    spaces["real_estate"].snapshot()

    spaces["information"].list_signals_by_source("source:reference_rating_agency_a")
    spaces["information"].list_signals_by_type("rating_action")
    spaces["information"].list_visible_signals("agent:somebody")
    spaces["information"].snapshot()

    spaces["policy"].list_instruments_by_authority("authority:reference_central_bank")
    spaces["policy"].get_visible_signals("authority:reference_central_bank")
    spaces["policy"].snapshot()

    spaces["external"].get_visible_signals("agent:any")
    spaces["external"].snapshot()

    # Books are unchanged. (Note: get_constraint_evaluations DOES
    # write `constraint_evaluated` records to the ledger, but those
    # are ledger entries, not mutations of the source books.)
    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


# ---------------------------------------------------------------------------
# 5. Full ledger audit trail
# ---------------------------------------------------------------------------


def test_ledger_carries_complete_audit_trail_after_setup_and_one_year_run():
    kernel, _ = _build_full_world()
    kernel.run(days=365)

    expected_event_types = {
        # Setup
        "object_registered",
        "task_scheduled",
        # State additions across all 8 spaces
        "firm_state_added",
        "bank_state_added",
        "investor_state_added",
        "market_state_added",
        "listing_added",
        "property_market_state_added",
        "property_asset_state_added",
        "information_source_state_added",
        "information_channel_state_added",
        "policy_authority_state_added",
        "policy_instrument_state_added",
        "external_factor_state_added",
        "external_source_state_added",
        # World book mutations
        "ownership_position_added",
        "contract_created",
        "price_updated",
        "constraint_added",
        "signal_added",
        # Runtime events
        "task_executed",
        "state_snapshot_created",
    }

    actual_event_types = {record.event_type for record in kernel.ledger.records}
    missing = expected_event_types - actual_event_types
    assert missing == set(), f"Missing ledger event types: {missing}"


def test_ledger_records_object_registrations_for_assets_and_spaces():
    kernel, _ = _build_full_world()

    object_registrations = kernel.ledger.filter(event_type="object_registered")
    registered_ids = {record.object_id for record in object_registrations}

    # Three explicitly registered assets.
    for asset_id in (
        "asset:reference_manufacturer_equity",
        "asset:cash_jpy",
        "asset:marunouchi_bldg_a",
    ):
        assert asset_id in registered_ids

    # All eight spaces are also recorded as object_registered when
    # register_space is called.
    for space_id in (
        "space:corporate",
        "space:banking",
        "space:investors",
        "space:exchange",
        "space:real_estate",
        "space:information",
        "space:policy",
        "space:external",
    ):
        assert space_id in registered_ids
