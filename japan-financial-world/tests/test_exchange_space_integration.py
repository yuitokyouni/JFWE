from datetime import date

from spaces.exchange.space import ExchangeSpace
from spaces.exchange.state import ListingState, MarketState
from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
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
# bind() wires kernel projections (mirror of corporate / bank / investor)
# ---------------------------------------------------------------------------


def test_register_space_wires_kernel_projections_via_bind():
    kernel = _kernel()
    exchange = ExchangeSpace()

    assert exchange.prices is None
    assert exchange.signals is None
    assert exchange.balance_sheets is None  # inherited from DomainSpace

    kernel.register_space(exchange)

    assert exchange.registry is kernel.registry
    assert exchange.prices is kernel.prices
    assert exchange.signals is kernel.signals
    assert exchange.ledger is kernel.ledger
    assert exchange.clock is kernel.clock
    # Inherited common refs are also wired even if Exchange does not use them.
    assert exchange.balance_sheets is kernel.balance_sheets
    assert exchange.constraint_evaluator is kernel.constraint_evaluator


def test_bind_does_not_overwrite_explicit_construction_refs():
    kernel = _kernel()
    other_ledger = Ledger()
    exchange = ExchangeSpace(ledger=other_ledger)

    kernel.register_space(exchange)

    assert exchange.ledger is other_ledger
    assert exchange.prices is kernel.prices


def test_bind_is_idempotent():
    kernel = _kernel()
    exchange = ExchangeSpace()
    kernel.register_space(exchange)

    prices_after_first = exchange.prices
    signals_after_first = exchange.signals

    exchange.bind(kernel)

    assert exchange.prices is prices_after_first
    assert exchange.signals is signals_after_first


# ---------------------------------------------------------------------------
# Reading prices through the space
# ---------------------------------------------------------------------------


def test_exchange_space_can_read_latest_price():
    kernel = _kernel()
    kernel.prices.set_price("asset:reference_manufacturer_equity", 2_500.0, "2026-01-01", "exchange")
    kernel.prices.set_price("asset:reference_manufacturer_equity", 2_550.0, "2026-01-02", "exchange")

    exchange = ExchangeSpace()
    kernel.register_space(exchange)

    latest = exchange.get_latest_price("asset:reference_manufacturer_equity")
    assert latest is not None
    assert latest.price == 2_550.0
    assert latest.simulation_date == "2026-01-02"


def test_exchange_space_can_read_price_history():
    kernel = _kernel()
    kernel.prices.set_price("asset:reference_manufacturer_equity", 2_500.0, "2026-01-01", "exchange")
    kernel.prices.set_price("asset:reference_manufacturer_equity", 2_550.0, "2026-01-02", "exchange")
    kernel.prices.set_price("asset:reference_manufacturer_equity", 2_510.0, "2026-01-03", "exchange")

    exchange = ExchangeSpace()
    kernel.register_space(exchange)

    history = exchange.get_price_history("asset:reference_manufacturer_equity")
    assert [h.price for h in history] == [2_500.0, 2_550.0, 2_510.0]


def test_missing_price_does_not_crash():
    kernel = _kernel()
    exchange = ExchangeSpace()
    kernel.register_space(exchange)

    # No price has been recorded for this asset; the calls must be safe.
    assert exchange.get_latest_price("asset:no_price") is None
    assert exchange.get_price_history("asset:no_price") == ()


def test_price_query_independent_of_listing():
    """
    v0.11 deliberately decouples price observations from listings.
    The exchange returns price data for any asset, regardless of
    whether that asset has been listed on any market.
    """
    kernel = _kernel()
    kernel.prices.set_price("asset:unlisted", 100.0, "2026-01-01", "system")

    exchange = ExchangeSpace()
    kernel.register_space(exchange)

    # No add_listing call for asset:unlisted, but price still readable.
    assert exchange.get_latest_price("asset:unlisted") is not None
    assert exchange.list_listings() == ()


# ---------------------------------------------------------------------------
# Reading signals through the space
# ---------------------------------------------------------------------------


def test_exchange_space_can_read_visible_signals():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:halt_announcement",
            signal_type="market_announcement",
            subject_id="asset:reference_manufacturer_equity",
            source_id="market:reference_equity_market",
            published_date="2026-01-01",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:internal_briefing",
            signal_type="internal_memo",
            subject_id="market:reference_equity_market",
            source_id="market:reference_equity_market",
            published_date="2026-01-01",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:regulator",)},
        )
    )

    exchange = ExchangeSpace()
    kernel.register_space(exchange)

    visible = exchange.get_visible_signals("market:reference_equity_market")
    visible_ids = {s.signal_id for s in visible}

    assert "signal:halt_announcement" in visible_ids
    assert "signal:internal_briefing" not in visible_ids


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_exchange_space_does_not_mutate_world_books():
    kernel = _kernel()
    kernel.prices.set_price("asset:reference_manufacturer_equity", 2_500.0, "2026-01-01", "exchange")
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:announce",
            signal_type="market_announcement",
            subject_id="asset:reference_manufacturer_equity",
            source_id="market:reference_equity_market",
            published_date="2026-01-01",
        )
    )

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    exchange = ExchangeSpace()
    kernel.register_space(exchange)
    exchange.add_market_state(MarketState(market_id="market:reference_equity_market"))
    exchange.add_listing(
        ListingState(market_id="market:reference_equity_market", asset_id="asset:reference_manufacturer_equity")
    )

    # Read every projection through the space.
    exchange.get_latest_price("asset:reference_manufacturer_equity")
    exchange.get_price_history("asset:reference_manufacturer_equity")
    exchange.get_visible_signals("market:reference_equity_market")
    exchange.list_assets_on_market("market:reference_equity_market")
    exchange.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


def test_exchange_space_runs_for_one_year_after_state_added():
    """
    v0.11 must preserve scheduler integration. Daily exchange tasks
    should fire 365 times over one year.
    """
    kernel = _kernel()
    exchange = ExchangeSpace()
    kernel.register_space(exchange)
    exchange.add_market_state(MarketState(market_id="market:reference_equity_market"))

    kernel.run(days=365)

    daily = kernel.ledger.filter(
        event_type="task_executed", task_id="task:exchange_daily"
    )
    assert len(daily) == 365
