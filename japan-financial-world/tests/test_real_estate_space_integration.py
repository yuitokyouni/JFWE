from datetime import date

from spaces.real_estate.space import RealEstateSpace
from spaces.real_estate.state import PropertyAssetState, PropertyMarketState
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
# bind() wires kernel projections (mirror of exchange tests)
# ---------------------------------------------------------------------------


def test_register_space_wires_kernel_projections_via_bind():
    kernel = _kernel()
    real_estate = RealEstateSpace()

    assert real_estate.prices is None
    assert real_estate.signals is None

    kernel.register_space(real_estate)

    assert real_estate.registry is kernel.registry
    assert real_estate.prices is kernel.prices
    assert real_estate.signals is kernel.signals
    assert real_estate.ledger is kernel.ledger
    assert real_estate.clock is kernel.clock
    # Inherited common refs are also wired.
    assert real_estate.balance_sheets is kernel.balance_sheets
    assert real_estate.constraint_evaluator is kernel.constraint_evaluator


def test_bind_does_not_overwrite_explicit_construction_refs():
    kernel = _kernel()
    other_ledger = Ledger()
    real_estate = RealEstateSpace(ledger=other_ledger)

    kernel.register_space(real_estate)

    assert real_estate.ledger is other_ledger
    assert real_estate.prices is kernel.prices


def test_bind_is_idempotent():
    kernel = _kernel()
    real_estate = RealEstateSpace()
    kernel.register_space(real_estate)

    prices_after_first = real_estate.prices
    signals_after_first = real_estate.signals

    real_estate.bind(kernel)

    assert real_estate.prices is prices_after_first
    assert real_estate.signals is signals_after_first


# ---------------------------------------------------------------------------
# Reading prices through the space
# ---------------------------------------------------------------------------


def test_real_estate_space_can_read_latest_price():
    kernel = _kernel()
    kernel.prices.set_price(
        "asset:marunouchi_bldg_a", 50_000_000_000.0, "2026-01-01", "appraisal"
    )
    kernel.prices.set_price(
        "asset:marunouchi_bldg_a", 51_000_000_000.0, "2026-04-01", "appraisal"
    )

    real_estate = RealEstateSpace()
    kernel.register_space(real_estate)

    latest = real_estate.get_latest_price("asset:marunouchi_bldg_a")
    assert latest is not None
    assert latest.price == 51_000_000_000.0
    assert latest.simulation_date == "2026-04-01"


def test_real_estate_space_can_read_price_history():
    kernel = _kernel()
    kernel.prices.set_price(
        "asset:marunouchi_bldg_a", 50_000_000_000.0, "2026-01-01", "appraisal"
    )
    kernel.prices.set_price(
        "asset:marunouchi_bldg_a", 51_000_000_000.0, "2026-04-01", "appraisal"
    )
    kernel.prices.set_price(
        "asset:marunouchi_bldg_a", 49_500_000_000.0, "2026-07-01", "appraisal"
    )

    real_estate = RealEstateSpace()
    kernel.register_space(real_estate)

    history = real_estate.get_price_history("asset:marunouchi_bldg_a")
    assert [h.price for h in history] == [
        50_000_000_000.0,
        51_000_000_000.0,
        49_500_000_000.0,
    ]


def test_missing_price_does_not_crash():
    kernel = _kernel()
    real_estate = RealEstateSpace()
    kernel.register_space(real_estate)

    assert real_estate.get_latest_price("asset:no_price_property") is None
    assert real_estate.get_price_history("asset:no_price_property") == ()


def test_price_query_independent_of_property_asset_registration():
    """
    v0.12 mirrors v0.11: price reads do not require the asset to be
    registered in the space. PriceBook is the canonical source.
    """
    kernel = _kernel()
    kernel.prices.set_price(
        "asset:unregistered_property", 100_000.0, "2026-01-01", "system"
    )

    real_estate = RealEstateSpace()
    kernel.register_space(real_estate)

    # No add_property_asset_state call, but price still readable.
    assert real_estate.get_latest_price("asset:unregistered_property") is not None
    assert real_estate.list_property_assets() == ()


# ---------------------------------------------------------------------------
# Reading signals through the space
# ---------------------------------------------------------------------------


def test_real_estate_space_can_read_visible_signals():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:zoning_change",
            signal_type="regulatory_announcement",
            subject_id="market:reference_central_office",
            source_id="agent:reference_metropolitan_govt",
            published_date="2026-01-01",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:internal_underwriting",
            signal_type="internal_memo",
            subject_id="asset:marunouchi_bldg_a",
            source_id="agent:appraiser",
            published_date="2026-01-01",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:owner",)},
        )
    )

    real_estate = RealEstateSpace()
    kernel.register_space(real_estate)

    visible = real_estate.get_visible_signals("market:reference_central_office")
    visible_ids = {s.signal_id for s in visible}
    assert "signal:zoning_change" in visible_ids
    assert "signal:internal_underwriting" not in visible_ids


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_real_estate_space_does_not_mutate_world_books():
    kernel = _kernel()
    kernel.prices.set_price(
        "asset:marunouchi_bldg_a", 50_000_000_000.0, "2026-01-01", "appraisal"
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:zoning",
            signal_type="regulatory_announcement",
            subject_id="market:reference_central_office",
            source_id="agent:govt",
            published_date="2026-01-01",
        )
    )

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    real_estate = RealEstateSpace()
    kernel.register_space(real_estate)
    real_estate.add_property_market_state(
        PropertyMarketState(
            property_market_id="market:reference_central_office",
            region="reference_central",
            property_type="office",
        )
    )
    real_estate.add_property_asset_state(
        PropertyAssetState(
            asset_id="asset:marunouchi_bldg_a",
            property_market_id="market:reference_central_office",
            asset_type="office_building",
        )
    )

    # Read every projection through the space.
    real_estate.get_latest_price("asset:marunouchi_bldg_a")
    real_estate.get_price_history("asset:marunouchi_bldg_a")
    real_estate.get_visible_signals("market:reference_central_office")
    real_estate.list_assets_in_property_market("market:reference_central_office")
    real_estate.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


def test_real_estate_space_runs_for_one_year_after_state_added():
    """
    v0.12 must preserve scheduler integration. RealEstateSpace declares
    MONTHLY + QUARTERLY frequencies; both should fire correctly.
    """
    kernel = _kernel()
    real_estate = RealEstateSpace()
    kernel.register_space(real_estate)
    real_estate.add_property_market_state(
        PropertyMarketState(property_market_id="market:reference_central_office")
    )

    kernel.run(days=365)

    monthly = kernel.ledger.filter(
        event_type="task_executed", task_id="task:real_estate_monthly"
    )
    quarterly = kernel.ledger.filter(
        event_type="task_executed", task_id="task:real_estate_quarterly"
    )
    assert len(monthly) == 12
    assert len(quarterly) == 4
