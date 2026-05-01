from datetime import date

from spaces.policy.space import PolicySpace
from spaces.policy.state import PolicyAuthorityState, PolicyInstrumentState
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
# bind() wires kernel projections (no override needed for PolicySpace)
# ---------------------------------------------------------------------------


def test_register_space_wires_kernel_projections_via_bind():
    kernel = _kernel()
    policy = PolicySpace()

    assert policy.signals is None
    assert policy.registry is None

    kernel.register_space(policy)

    assert policy.registry is kernel.registry
    assert policy.signals is kernel.signals
    assert policy.ledger is kernel.ledger
    assert policy.clock is kernel.clock


def test_bind_does_not_overwrite_explicit_construction_refs():
    kernel = _kernel()
    other_ledger = Ledger()
    policy = PolicySpace(ledger=other_ledger)

    kernel.register_space(policy)

    assert policy.ledger is other_ledger
    assert policy.signals is kernel.signals


# ---------------------------------------------------------------------------
# Reading SignalBook through the space
# ---------------------------------------------------------------------------


def test_policy_space_can_read_visible_signals():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:rate_decision",
            signal_type="policy_announcement",
            subject_id="authority:reference_central_bank",
            source_id="authority:reference_central_bank",
            published_date="2026-01-01",
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
            metadata={"allowed_viewers": ("agent:internal_committee",)},
        )
    )

    policy = PolicySpace()
    kernel.register_space(policy)

    visible = policy.get_visible_signals("authority:reference_central_bank")
    visible_ids = {s.signal_id for s in visible}
    assert "signal:rate_decision" in visible_ids
    assert "signal:internal_minutes" not in visible_ids


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_policy_space_does_not_mutate_world_books():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:announcement",
            signal_type="policy_announcement",
            subject_id="authority:reference_central_bank",
            source_id="authority:reference_central_bank",
            published_date="2026-01-01",
        )
    )

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    policy = PolicySpace()
    kernel.register_space(policy)
    policy.add_authority_state(
        PolicyAuthorityState(
            authority_id="authority:reference_central_bank",
            authority_type="central_bank",
        )
    )
    policy.add_instrument_state(
        PolicyInstrumentState(
            instrument_id="instrument:boj_policy_rate",
            authority_id="authority:reference_central_bank",
            instrument_type="policy_rate",
        )
    )

    policy.get_visible_signals("authority:reference_central_bank")
    policy.list_instruments_by_authority("authority:reference_central_bank")
    policy.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


def test_policy_space_runs_for_one_year_after_state_added():
    """PolicySpace declares MONTHLY frequency; should fire 12 times/year."""
    kernel = _kernel()
    policy = PolicySpace()
    kernel.register_space(policy)
    policy.add_authority_state(PolicyAuthorityState(authority_id="authority:reference_central_bank"))

    kernel.run(days=365)

    monthly = kernel.ledger.filter(
        event_type="task_executed", task_id="task:policy_monthly"
    )
    assert len(monthly) == 12
