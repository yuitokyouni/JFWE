from datetime import date

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.phases import IntradayPhaseSpec, PhaseSequence
from world.registry import Registry
from world.scheduler import Frequency, Phase, Scheduler, TaskSpec
from world.state import State


def _kernel(start: date = date(2026, 1, 1)) -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=start),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _make_task(
    task_id: str,
    *,
    frequency: Frequency = Frequency.DAILY,
    phase: Phase = Phase.MAIN,
    space: str = "test_space",
    order: int = 0,
) -> TaskSpec:
    return TaskSpec(
        id=task_id,
        frequency=frequency,
        name=task_id,
        space=space,
        order=order,
        phase=phase,
    )


# ---------------------------------------------------------------------------
# Scheduler still works with extended Phase enum
# ---------------------------------------------------------------------------


def test_scheduler_accepts_extended_phase_values():
    """The scheduler must continue to accept TaskSpec with any Phase value."""
    kernel = _kernel()
    kernel.register_task(
        _make_task("task:overnight", phase=Phase.OVERNIGHT)
    )
    kernel.register_task(
        _make_task("task:opening", phase=Phase.OPENING_AUCTION)
    )
    kernel.register_task(_make_task("task:main"))  # legacy v0 default

    all_tasks = kernel.scheduler.all_tasks()
    assert len(all_tasks) == 3


def test_v0_due_tasks_returns_all_phases_when_no_filter():
    """Backward-compat: due_tasks(clock) without phase filter returns all phases."""
    kernel = _kernel()
    kernel.register_task(
        _make_task("task:morning", phase=Phase.OVERNIGHT)
    )
    kernel.register_task(_make_task("task:legacy"))  # MAIN

    due = kernel.scheduler.due_tasks(kernel.clock)
    task_ids = {t.id for t in due}
    assert task_ids == {"task:morning", "task:legacy"}


def test_due_tasks_filters_by_phase_when_phase_given():
    kernel = _kernel()
    kernel.register_task(
        _make_task("task:morning", phase=Phase.OVERNIGHT)
    )
    kernel.register_task(_make_task("task:legacy"))  # MAIN
    kernel.register_task(
        _make_task("task:opening", phase=Phase.OPENING_AUCTION)
    )

    overnight_only = kernel.scheduler.due_tasks(kernel.clock, phase=Phase.OVERNIGHT)
    assert {t.id for t in overnight_only} == {"task:morning"}

    main_only = kernel.scheduler.due_tasks(kernel.clock, phase=Phase.MAIN)
    assert {t.id for t in main_only} == {"task:legacy"}


# ---------------------------------------------------------------------------
# iter_intraday_phases
# ---------------------------------------------------------------------------


def test_iter_intraday_phases_yields_all_six_phases_with_due_tasks():
    kernel = _kernel()
    kernel.register_task(
        _make_task("task:morning", phase=Phase.OVERNIGHT)
    )
    kernel.register_task(
        _make_task("task:opening", phase=Phase.OPENING_AUCTION)
    )

    yielded = list(kernel.iter_intraday_phases())
    assert len(yielded) == 6

    by_phase = {spec.phase_id: due for spec, due in yielded}
    assert {t.id for t in by_phase["overnight"]} == {"task:morning"}
    assert {t.id for t in by_phase["opening_auction"]} == {"task:opening"}
    # Phases without registered tasks yield empty tuples.
    assert by_phase["pre_open"] == ()
    assert by_phase["continuous_session"] == ()
    assert by_phase["closing_auction"] == ()
    assert by_phase["post_close"] == ()


def test_iter_intraday_phases_excludes_main_tasks():
    """Phase.MAIN tasks are intentionally excluded from intraday dispatch."""
    kernel = _kernel()
    kernel.register_task(_make_task("task:legacy"))  # MAIN

    for _, due in kernel.iter_intraday_phases():
        assert all(t.phase != Phase.MAIN for t in due)


def test_iter_intraday_phases_accepts_custom_sequence():
    kernel = _kernel()
    kernel.register_task(
        _make_task("task:opening", phase=Phase.OPENING_AUCTION)
    )

    custom = PhaseSequence(
        phases=(
            IntradayPhaseSpec(phase_id="opening_auction", order=0, label="Open"),
        )
    )
    yielded = list(kernel.iter_intraday_phases(custom))
    assert len(yielded) == 1
    assert yielded[0][0].phase_id == "opening_auction"
    assert {t.id for t in yielded[0][1]} == {"task:opening"}


# ---------------------------------------------------------------------------
# run_day_with_phases
# ---------------------------------------------------------------------------


def test_phase_aware_daily_task_fires_once_per_day_at_its_phase():
    kernel = _kernel()
    kernel.register_task(
        _make_task("task:opening", phase=Phase.OPENING_AUCTION)
    )

    kernel.run_with_phases(days=5)

    records = kernel.ledger.filter(
        event_type="task_executed", task_id="task:opening"
    )
    assert len(records) == 5
    # Phase information is recorded in the payload.
    assert all(r.payload["phase"] == "opening_auction" for r in records)


def test_phase_aware_monthly_task_fires_only_at_month_end():
    kernel = _kernel()
    kernel.register_task(
        _make_task(
            "task:closing_monthly",
            frequency=Frequency.MONTHLY,
            phase=Phase.CLOSING_AUCTION,
        )
    )

    # Start at Jan 1, 2026; run 90 days covers Jan / Feb / Mar.
    kernel.run_with_phases(days=90)

    records = kernel.ledger.filter(
        event_type="task_executed", task_id="task:closing_monthly"
    )
    # 3 month-ends in the window: Jan 31, Feb 28, Mar 31.
    assert len(records) == 3
    assert {r.simulation_date for r in records} == {
        "2026-01-31",
        "2026-02-28",
        "2026-03-31",
    }
    assert all(r.payload["phase"] == "closing_auction" for r in records)


def test_phase_aware_quarterly_task_fires_only_at_quarter_end():
    kernel = _kernel()
    kernel.register_task(
        _make_task(
            "task:close_quarterly",
            frequency=Frequency.QUARTERLY,
            phase=Phase.POST_CLOSE,
        )
    )

    kernel.run_with_phases(days=365)

    records = kernel.ledger.filter(
        event_type="task_executed", task_id="task:close_quarterly"
    )
    assert len(records) == 4  # 4 quarter-ends in 2026
    assert {r.simulation_date for r in records} == {
        "2026-03-31",
        "2026-06-30",
        "2026-09-30",
        "2026-12-31",
    }


def test_run_day_with_phases_advances_clock_once_per_day():
    kernel = _kernel(start=date(2026, 1, 1))
    kernel.register_task(
        _make_task("task:morning", phase=Phase.OVERNIGHT)
    )

    kernel.run_with_phases(days=10)
    assert kernel.clock.current_date == date(2026, 1, 11)


def test_run_day_with_phases_emits_month_end_snapshot():
    kernel = _kernel(start=date(2026, 1, 1))
    kernel.register_task(
        _make_task("task:morning", phase=Phase.OVERNIGHT)
    )

    # 31 days reaches month-end on 2026-01-31.
    kernel.run_with_phases(days=31)

    snapshots = kernel.ledger.filter(event_type="state_snapshot_created")
    assert len(snapshots) == 1
    assert snapshots[0].simulation_date == "2026-01-31"


# ---------------------------------------------------------------------------
# Multiple tasks in same phase — deterministic ordering
# ---------------------------------------------------------------------------


def test_multiple_tasks_in_same_phase_execute_in_deterministic_order():
    kernel = _kernel()
    # Tasks registered out of natural order; sorter should normalize
    # by (phase, frequency, order, space, name).
    kernel.register_task(
        _make_task(
            "task:b_second",
            phase=Phase.OPENING_AUCTION,
            order=2,
            space="space_b",
        )
    )
    kernel.register_task(
        _make_task(
            "task:a_first",
            phase=Phase.OPENING_AUCTION,
            order=1,
            space="space_a",
        )
    )
    kernel.register_task(
        _make_task(
            "task:a_third",
            phase=Phase.OPENING_AUCTION,
            order=3,
            space="space_a",
        )
    )

    kernel.run_day_with_phases()

    records = kernel.ledger.filter(event_type="task_executed")
    ids_in_order = [r.task_id for r in records]
    # Sort key: order ascending, then space, then name.
    assert ids_in_order == ["task:a_first", "task:b_second", "task:a_third"]


# ---------------------------------------------------------------------------
# Backward compatibility — v0 paths still work alongside v1.2 paths
# ---------------------------------------------------------------------------


def test_v0_tick_path_still_fires_main_tasks_unaffected():
    """Adding intraday phases must not change the v0 tick path."""
    kernel = _kernel()
    kernel.register_task(_make_task("task:legacy"))  # MAIN, daily

    kernel.run(days=10)

    records = kernel.ledger.filter(
        event_type="task_executed", task_id="task:legacy"
    )
    assert len(records) == 10


def test_v0_tick_fires_phase_aware_tasks_when_phase_filter_absent():
    """
    The v0 tick path applies no phase filter, so phase-aware tasks also
    fire on every tick when the kernel runs in v0 mode. This is the
    documented backward-compatible behavior — callers who want
    phase-aware dispatch must use run_day_with_phases.
    """
    kernel = _kernel()
    kernel.register_task(
        _make_task("task:opening", phase=Phase.OPENING_AUCTION)
    )

    kernel.run(days=5)

    records = kernel.ledger.filter(
        event_type="task_executed", task_id="task:opening"
    )
    assert len(records) == 5  # fires every tick under v0 mode


# ---------------------------------------------------------------------------
# No market behavior is implemented
# ---------------------------------------------------------------------------


def test_phase_dispatch_creates_no_prices_or_signals_or_book_mutations():
    """v1.2 must not introduce any market behavior."""
    kernel = _kernel()
    kernel.register_task(
        _make_task("task:opening", phase=Phase.OPENING_AUCTION)
    )

    prices_before = kernel.prices.snapshot()
    ownership_before = kernel.ownership.snapshot()
    contracts_before = kernel.contracts.snapshot()
    signals_before = kernel.signals.snapshot()
    valuations_before = kernel.valuations.snapshot()

    kernel.run_with_phases(days=10)

    # No source-of-truth book is touched by the phase dispatcher.
    assert kernel.prices.snapshot() == prices_before
    assert kernel.ownership.snapshot() == ownership_before
    assert kernel.contracts.snapshot() == contracts_before
    assert kernel.signals.snapshot() == signals_before
    assert kernel.valuations.snapshot() == valuations_before


# ---------------------------------------------------------------------------
# v1.2.1 run-mode guard
#
# The kernel rejects calls that would mix the v0 date-based path
# (tick / run) with the v1.2 intraday phase path (run_day_with_phases /
# run_with_phases) on the same simulation date. The natural advance-
# clock semantics means the guard never fires during ordinary
# sequential use — it only fires when callers manually rewind the clock
# or otherwise revisit a date that has already been processed in the
# other mode.
# ---------------------------------------------------------------------------


def test_tick_then_run_day_with_phases_on_same_date_raises():
    kernel = _kernel(start=date(2026, 1, 1))
    kernel.tick()  # processes 2026-01-01, advances to 2026-01-02
    # Manually rewind to revisit the same date in a different mode.
    kernel.clock.current_date = date(2026, 1, 1)

    with pytest.raises(RuntimeError, match="mix run modes"):
        kernel.run_day_with_phases()


def test_run_day_with_phases_then_tick_on_same_date_raises():
    kernel = _kernel(start=date(2026, 1, 1))
    kernel.run_day_with_phases()  # processes 2026-01-01, advances
    kernel.clock.current_date = date(2026, 1, 1)

    with pytest.raises(RuntimeError, match="mix run modes"):
        kernel.tick()


def test_repeated_tick_in_same_mode_at_same_date_does_not_raise():
    """Same-mode reentry is idempotent — only mode mixing is rejected."""
    kernel = _kernel(start=date(2026, 1, 1))
    kernel.tick()
    kernel.clock.current_date = date(2026, 1, 1)
    # Calling tick again at the same date is the same mode, so it is
    # allowed (and processes the day again).
    kernel.tick()
    # Both ticks marked the date with date_tick mode, no error.


def test_tick_across_multiple_days_still_works():
    kernel = _kernel(start=date(2026, 1, 1))
    kernel.run(days=10)
    assert kernel.clock.current_date == date(2026, 1, 11)


def test_run_with_phases_across_multiple_days_still_works():
    kernel = _kernel(start=date(2026, 1, 1))
    kernel.register_task(
        _make_task("task:opening", phase=Phase.OPENING_AUCTION)
    )
    kernel.run_with_phases(days=10)
    assert kernel.clock.current_date == date(2026, 1, 11)
    records = kernel.ledger.filter(
        event_type="task_executed", task_id="task:opening"
    )
    assert len(records) == 10


def test_sequential_use_of_both_modes_on_different_dates_works():
    """
    The guard is per-date. After tick() at date D and the natural clock
    advance to D+1, calling run_day_with_phases() at D+1 is allowed:
    D+1 has not been processed in any mode yet.
    """
    kernel = _kernel(start=date(2026, 1, 1))
    kernel.tick()  # D=2026-01-01 in date_tick mode, clock → 2026-01-02
    kernel.run_day_with_phases()  # D=2026-01-02 in intraday_phase mode
    kernel.tick()  # D=2026-01-03 in date_tick mode
    assert kernel.clock.current_date == date(2026, 1, 4)
