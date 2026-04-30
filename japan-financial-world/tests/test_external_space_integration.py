from datetime import date

from spaces.external.space import ExternalSpace
from spaces.external.state import ExternalFactorState, ExternalSourceState
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
# bind() wires kernel projections (no override needed for ExternalSpace)
# ---------------------------------------------------------------------------


def test_register_space_wires_kernel_projections_via_bind():
    kernel = _kernel()
    external = ExternalSpace()

    assert external.signals is None
    assert external.registry is None

    kernel.register_space(external)

    assert external.registry is kernel.registry
    assert external.signals is kernel.signals
    assert external.ledger is kernel.ledger
    assert external.clock is kernel.clock


def test_bind_does_not_overwrite_explicit_construction_refs():
    kernel = _kernel()
    other_ledger = Ledger()
    external = ExternalSpace(ledger=other_ledger)

    kernel.register_space(external)

    assert external.ledger is other_ledger
    assert external.signals is kernel.signals


# ---------------------------------------------------------------------------
# Reading SignalBook through the space
# ---------------------------------------------------------------------------


def test_external_space_can_read_visible_signals():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:fed_decision",
            signal_type="foreign_policy_announcement",
            subject_id="authority:fed",
            source_id="source:fed",
            published_date="2026-01-01",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:internal_research",
            signal_type="internal_memo",
            subject_id="factor:usd_jpy",
            source_id="agent:internal_strategy",
            published_date="2026-01-01",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:strategy_committee",)},
        )
    )

    external = ExternalSpace()
    kernel.register_space(external)

    visible = external.get_visible_signals("agent:strategy_observer")
    visible_ids = {s.signal_id for s in visible}
    assert "signal:fed_decision" in visible_ids
    assert "signal:internal_research" not in visible_ids


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_external_space_does_not_mutate_world_books():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:macro_release",
            signal_type="macro_indicator",
            subject_id="factor:us_cpi",
            source_id="source:bls",
            published_date="2026-01-01",
        )
    )

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    external = ExternalSpace()
    kernel.register_space(external)
    external.add_factor_state(
        ExternalFactorState(
            factor_id="factor:usd_jpy",
            factor_type="fx_rate",
            unit="USD/JPY",
        )
    )
    external.add_source_state(
        ExternalSourceState(
            source_id="source:imf",
            source_type="international_organization",
        )
    )

    external.get_visible_signals("agent:somebody")
    external.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


def test_external_space_runs_for_one_year_after_state_added():
    """ExternalSpace declares DAILY frequency; should fire 365 times/year."""
    kernel = _kernel()
    external = ExternalSpace()
    kernel.register_space(external)
    external.add_factor_state(
        ExternalFactorState(factor_id="factor:usd_jpy")
    )

    kernel.run(days=365)

    daily = kernel.ledger.filter(
        event_type="task_executed", task_id="task:external_daily"
    )
    assert len(daily) == 365
