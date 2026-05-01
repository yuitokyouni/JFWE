from datetime import date

from spaces.investors.space import InvestorSpace
from spaces.investors.state import InvestorState
from world.clock import Clock
from world.constraints import ConstraintRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import RegisteredObject, Registry
from world.scheduler import Scheduler
from world.signals import InformationSignal
from world.state import State


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


# ---------------------------------------------------------------------------
# bind() wires kernel projections (mirror of corporate / bank tests)
# ---------------------------------------------------------------------------


def test_register_space_wires_kernel_projections_via_bind():
    kernel = _kernel()
    investor_space = InvestorSpace()

    assert investor_space.ownership is None
    assert investor_space.prices is None
    assert investor_space.balance_sheets is None
    assert investor_space.constraint_evaluator is None
    assert investor_space.signals is None

    kernel.register_space(investor_space)

    assert investor_space.registry is kernel.registry
    assert investor_space.ownership is kernel.ownership
    assert investor_space.prices is kernel.prices
    assert investor_space.balance_sheets is kernel.balance_sheets
    assert investor_space.constraint_evaluator is kernel.constraint_evaluator
    assert investor_space.signals is kernel.signals
    assert investor_space.ledger is kernel.ledger
    assert investor_space.clock is kernel.clock


def test_bind_does_not_overwrite_explicit_construction_refs():
    kernel = _kernel()
    other_ledger = Ledger()
    investor_space = InvestorSpace(ledger=other_ledger)

    kernel.register_space(investor_space)

    assert investor_space.ledger is other_ledger
    assert investor_space.ownership is kernel.ownership


def test_bind_is_idempotent():
    kernel = _kernel()
    investor_space = InvestorSpace()
    kernel.register_space(investor_space)

    ownership_after_first = investor_space.ownership
    prices_after_first = investor_space.prices

    investor_space.bind(kernel)

    assert investor_space.ownership is ownership_after_first
    assert investor_space.prices is prices_after_first


# ---------------------------------------------------------------------------
# Reading projections through the space
# ---------------------------------------------------------------------------


def test_investor_space_can_read_balance_sheet_view():
    kernel = _kernel()
    kernel.ownership.add_position("investor:reference_fund_a", "asset:aapl", 100)
    kernel.prices.set_price("asset:aapl", 150.0, "2026-01-01", "exchange")

    investor_space = InvestorSpace()
    kernel.register_space(investor_space)
    investor_space.add_investor_state(
        InvestorState(
            investor_id="investor:reference_fund_a",
            investor_type="pension_fund",
            tier="tier_1",
        )
    )

    view = investor_space.get_balance_sheet_view("investor:reference_fund_a")
    assert view is not None
    assert view.agent_id == "investor:reference_fund_a"
    assert view.asset_value == 15_000.0
    assert view.as_of_date == "2026-01-01"


def test_investor_space_can_read_constraint_evaluations():
    kernel = _kernel()
    kernel.ownership.add_position("investor:reference_fund_a", "asset:cash", 1_000_000)
    kernel.prices.set_price("asset:cash", 1.0, "2026-01-01", "system")
    kernel.constraints.add_constraint(
        ConstraintRecord(
            constraint_id="constraint:gpif_lev",
            owner_id="investor:reference_fund_a",
            constraint_type="max_leverage",
            threshold=0.7,
            comparison="<=",
        )
    )

    investor_space = InvestorSpace()
    kernel.register_space(investor_space)

    evaluations = investor_space.get_constraint_evaluations("investor:reference_fund_a")
    assert len(evaluations) == 1
    # No liabilities -> leverage = 0 -> ok
    assert evaluations[0].status == "ok"


def test_investor_space_can_read_visible_signals():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:earnings",
            signal_type="earnings_report",
            subject_id="firm:reference_manufacturer_a",
            source_id="firm:reference_manufacturer_a",
            published_date="2026-01-01",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:closed",
            signal_type="internal_memo",
            subject_id="investor:reference_fund_a",
            source_id="investor:reference_fund_a",
            published_date="2026-01-01",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:trustee",)},
        )
    )

    investor_space = InvestorSpace()
    kernel.register_space(investor_space)

    visible = investor_space.get_visible_signals("investor:reference_fund_a")
    visible_ids = {s.signal_id for s in visible}
    assert "signal:earnings" in visible_ids
    assert "signal:closed" not in visible_ids


# ---------------------------------------------------------------------------
# Ownership-derived views
# ---------------------------------------------------------------------------


def test_list_portfolio_positions_returns_raw_ownership_records():
    kernel = _kernel()
    kernel.ownership.add_position("investor:reference_fund_a", "asset:aapl", 100)
    kernel.ownership.add_position("investor:reference_fund_a", "asset:msft", 50)
    kernel.ownership.add_position("investor:other", "asset:aapl", 25)

    investor_space = InvestorSpace()
    kernel.register_space(investor_space)

    positions = investor_space.list_portfolio_positions("investor:reference_fund_a")
    asset_ids = {p.asset_id for p in positions}
    assert asset_ids == {"asset:aapl", "asset:msft"}
    # All positions belong to the requested investor.
    assert all(p.owner_id == "investor:reference_fund_a" for p in positions)


def test_list_portfolio_exposures_combines_ownership_prices_and_registry():
    kernel = _kernel()
    kernel.registry.register(
        RegisteredObject(
            id="asset:aapl", kind="asset", type="equity", space="market"
        )
    )
    kernel.registry.register(
        RegisteredObject(
            id="asset:cash_jpy", kind="asset", type="cash", space="market"
        )
    )
    kernel.ownership.add_position("investor:reference_fund_a", "asset:aapl", 100)
    kernel.ownership.add_position("investor:reference_fund_a", "asset:cash_jpy", 1_000_000)
    kernel.prices.set_price("asset:aapl", 150.0, "2026-01-01", "exchange")
    kernel.prices.set_price("asset:cash_jpy", 1.0, "2026-01-01", "system")

    investor_space = InvestorSpace()
    kernel.register_space(investor_space)

    exposures = investor_space.list_portfolio_exposures("investor:reference_fund_a")
    by_asset = {e.asset_id: e for e in exposures}

    assert by_asset["asset:aapl"].quantity == 100.0
    assert by_asset["asset:aapl"].latest_price == 150.0
    assert by_asset["asset:aapl"].market_value == 15_000.0
    assert by_asset["asset:aapl"].asset_type == "equity"
    assert by_asset["asset:aapl"].metadata == {}

    assert by_asset["asset:cash_jpy"].quantity == 1_000_000.0
    assert by_asset["asset:cash_jpy"].latest_price == 1.0
    assert by_asset["asset:cash_jpy"].market_value == 1_000_000.0
    assert by_asset["asset:cash_jpy"].asset_type == "cash"
    assert by_asset["asset:cash_jpy"].metadata == {}


def test_list_portfolio_exposures_handles_missing_price_without_crashing():
    kernel = _kernel()
    kernel.ownership.add_position("investor:reference_fund_a", "asset:no_price", 100)
    # No price recorded for asset:no_price.

    investor_space = InvestorSpace()
    kernel.register_space(investor_space)

    exposures = investor_space.list_portfolio_exposures("investor:reference_fund_a")
    assert len(exposures) == 1
    exposure = exposures[0]
    assert exposure.asset_id == "asset:no_price"
    assert exposure.quantity == 100.0
    assert exposure.latest_price is None
    assert exposure.market_value is None
    assert exposure.metadata.get("missing_price") is True


def test_list_portfolio_exposures_handles_missing_registry_entry():
    kernel = _kernel()
    kernel.ownership.add_position("investor:reference_fund_a", "asset:unregistered", 50)
    kernel.prices.set_price("asset:unregistered", 10.0, "2026-01-01", "system")

    investor_space = InvestorSpace()
    kernel.register_space(investor_space)

    exposures = investor_space.list_portfolio_exposures("investor:reference_fund_a")
    assert len(exposures) == 1
    exposure = exposures[0]
    assert exposure.asset_type is None
    assert exposure.metadata.get("missing_asset_type") is True
    # But valuation still works because price exists.
    assert exposure.latest_price == 10.0
    assert exposure.market_value == 500.0


def test_list_portfolio_exposures_returns_empty_for_investor_with_no_positions():
    kernel = _kernel()
    investor_space = InvestorSpace()
    kernel.register_space(investor_space)

    assert investor_space.list_portfolio_exposures("investor:reference_fund_a") == ()


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_investor_space_does_not_mutate_world_books():
    kernel = _kernel()
    kernel.registry.register(
        RegisteredObject(
            id="asset:aapl", kind="asset", type="equity", space="market"
        )
    )
    kernel.ownership.add_position("investor:reference_fund_a", "asset:aapl", 100)
    kernel.prices.set_price("asset:aapl", 150.0, "2026-01-01", "exchange")
    kernel.constraints.add_constraint(
        ConstraintRecord(
            constraint_id="constraint:gpif_nav",
            owner_id="investor:reference_fund_a",
            constraint_type="min_net_asset_value",
            threshold=0.0,
            comparison=">=",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:macro",
            signal_type="macro_indicator",
            subject_id="agent:central_bank",
            source_id="agent:central_bank",
            published_date="2026-01-01",
        )
    )

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    investor_space = InvestorSpace()
    kernel.register_space(investor_space)
    investor_space.add_investor_state(InvestorState(investor_id="investor:reference_fund_a"))

    investor_space.get_balance_sheet_view("investor:reference_fund_a")
    investor_space.get_constraint_evaluations("investor:reference_fund_a")
    investor_space.get_visible_signals("investor:reference_fund_a")
    investor_space.list_portfolio_positions("investor:reference_fund_a")
    investor_space.list_portfolio_exposures("investor:reference_fund_a")
    investor_space.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


def test_investor_space_runs_for_one_year_after_state_added():
    """
    InvestorSpace's scheduler integration must continue to work.
    Daily and monthly tasks should still fire at expected counts.
    """
    kernel = _kernel()
    investor_space = InvestorSpace()
    kernel.register_space(investor_space)
    investor_space.add_investor_state(InvestorState(investor_id="investor:reference_fund_a"))

    kernel.run(days=365)

    daily = kernel.ledger.filter(
        event_type="task_executed", task_id="task:investors_daily"
    )
    monthly = kernel.ledger.filter(
        event_type="task_executed", task_id="task:investors_monthly"
    )
    assert len(daily) == 365
    assert len(monthly) == 12
