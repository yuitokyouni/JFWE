from datetime import date

from spaces.information.space import InformationSpace
from spaces.information.state import (
    InformationChannelState,
    InformationSourceState,
)
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
# bind() wires kernel projections (sixth domain space, same pattern)
# ---------------------------------------------------------------------------


def test_register_space_wires_kernel_projections_via_bind():
    kernel = _kernel()
    info = InformationSpace()

    assert info.signals is None
    assert info.registry is None

    kernel.register_space(info)

    assert info.registry is kernel.registry
    assert info.signals is kernel.signals
    assert info.ledger is kernel.ledger
    assert info.clock is kernel.clock


def test_bind_does_not_overwrite_explicit_construction_refs():
    kernel = _kernel()
    other_ledger = Ledger()
    info = InformationSpace(ledger=other_ledger)

    kernel.register_space(info)

    assert info.ledger is other_ledger
    assert info.signals is kernel.signals


def test_bind_is_idempotent():
    kernel = _kernel()
    info = InformationSpace()
    kernel.register_space(info)

    signals_after_first = info.signals
    registry_after_first = info.registry

    info.bind(kernel)

    assert info.signals is signals_after_first
    assert info.registry is registry_after_first


# ---------------------------------------------------------------------------
# Reading SignalBook through the space
# ---------------------------------------------------------------------------


def test_information_space_can_list_signals_by_source():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:moodys_rating_001",
            signal_type="rating_action",
            subject_id="firm:reference_manufacturer_a",
            source_id="source:moodys",
            published_date="2026-01-01",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:moodys_rating_002",
            signal_type="rating_action",
            subject_id="firm:sony",
            source_id="source:moodys",
            published_date="2026-01-01",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:sp_rating_001",
            signal_type="rating_action",
            subject_id="firm:reference_manufacturer_a",
            source_id="source:sp",
            published_date="2026-01-01",
        )
    )

    info = InformationSpace()
    kernel.register_space(info)

    moodys = info.list_signals_by_source("source:moodys")
    sp = info.list_signals_by_source("source:sp")

    assert {s.signal_id for s in moodys} == {
        "signal:moodys_rating_001",
        "signal:moodys_rating_002",
    }
    assert {s.signal_id for s in sp} == {"signal:sp_rating_001"}


def test_information_space_can_list_signals_by_type():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:rating_a",
            signal_type="rating_action",
            subject_id="firm:reference_manufacturer_a",
            source_id="source:moodys",
            published_date="2026-01-01",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:earnings_a",
            signal_type="earnings_report",
            subject_id="firm:reference_manufacturer_a",
            source_id="firm:reference_manufacturer_a",
            published_date="2026-01-01",
        )
    )

    info = InformationSpace()
    kernel.register_space(info)

    ratings = info.list_signals_by_type("rating_action")
    earnings = info.list_signals_by_type("earnings_report")

    assert {s.signal_id for s in ratings} == {"signal:rating_a"}
    assert {s.signal_id for s in earnings} == {"signal:earnings_a"}


def test_information_space_can_list_visible_signals():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:public_news",
            signal_type="news",
            subject_id="firm:reference_manufacturer_a",
            source_id="source:reuters",
            published_date="2026-01-01",
        )
    )
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:internal_briefing",
            signal_type="internal_memo",
            subject_id="firm:reference_manufacturer_a",
            source_id="firm:reference_manufacturer_a",
            published_date="2026-01-01",
            visibility="restricted",
            metadata={"allowed_viewers": ("agent:legal",)},
        )
    )

    info = InformationSpace()
    kernel.register_space(info)

    visible_to_public = info.list_visible_signals("agent:public_observer")
    visible_to_legal = info.list_visible_signals("agent:legal")

    assert {s.signal_id for s in visible_to_public} == {"signal:public_news"}
    assert {s.signal_id for s in visible_to_legal} == {
        "signal:public_news",
        "signal:internal_briefing",
    }


def test_signal_queries_independent_of_source_or_channel_registration():
    """
    v0.13 mirrors the v0.11 / v0.12 separation: signal queries do not
    require sources or channels to be registered in the space. The
    SignalBook is the canonical store; the space only classifies.
    """
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:from_unregistered",
            signal_type="news",
            subject_id="firm:reference_manufacturer_a",
            source_id="source:not_registered_in_info_space",
            published_date="2026-01-01",
        )
    )

    info = InformationSpace()
    kernel.register_space(info)

    # No add_source_state for source:not_registered_in_info_space, but
    # the signal is still readable.
    found = info.list_signals_by_source("source:not_registered_in_info_space")
    assert len(found) == 1
    assert info.list_sources() == ()


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def test_information_space_does_not_mutate_world_books():
    kernel = _kernel()
    kernel.signals.add_signal(
        InformationSignal(
            signal_id="signal:rating_001",
            signal_type="rating_action",
            subject_id="firm:reference_manufacturer_a",
            source_id="source:moodys",
            published_date="2026-01-01",
        )
    )

    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    prices_before = kernel.prices.snapshot()
    constraints_before = kernel.constraints.snapshot()
    signals_before = kernel.signals.snapshot()

    info = InformationSpace()
    kernel.register_space(info)
    info.add_source_state(
        InformationSourceState(
            source_id="source:moodys",
            source_type="rating_agency",
            tier="tier_1",
        )
    )
    info.add_channel_state(
        InformationChannelState(
            channel_id="channel:reuters_wire",
            channel_type="wire_service",
            visibility="public",
        )
    )

    # Read through the space.
    info.list_signals_by_source("source:moodys")
    info.list_signals_by_type("rating_action")
    info.list_visible_signals("agent:somebody")
    info.snapshot()

    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.prices.snapshot() == prices_before
    assert kernel.constraints.snapshot() == constraints_before
    assert kernel.signals.snapshot() == signals_before


def test_information_space_runs_for_one_year_after_state_added():
    """
    InformationSpace's scheduler integration must continue to work.
    Daily tasks should fire 365 times.
    """
    kernel = _kernel()
    info = InformationSpace()
    kernel.register_space(info)
    info.add_source_state(
        InformationSourceState(source_id="source:moodys")
    )
    info.add_channel_state(
        InformationChannelState(channel_id="channel:reuters_wire")
    )

    kernel.run(days=365)

    daily = kernel.ledger.filter(
        event_type="task_executed", task_id="task:information_daily"
    )
    assert len(daily) == 365
