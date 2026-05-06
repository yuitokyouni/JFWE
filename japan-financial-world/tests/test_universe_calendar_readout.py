"""
v1.26.3 — UniverseCalendarReadout pin tests.
"""

from __future__ import annotations

import re
from datetime import date

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.reporting_calendar_profiles import (
    ReportingCalendarProfile,
)
from world.scheduler import Scheduler
from world.state import State
from world.universe_calendar_readout import (
    build_universe_calendar_readout,
    render_universe_calendar_readout_markdown,
)
from world.universe_events import UniverseEventRecord


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _evt(uid: str, period: str, etype: str, **kw) -> UniverseEventRecord:
    affected = kw.get("affected_entity_ids", ("firm:default",))
    return UniverseEventRecord(
        universe_event_id=uid,
        effective_period_id=period,
        event_type_label=etype,
        affected_entity_ids=affected,
        predecessor_entity_ids=kw.get("predecessor_entity_ids", ()),
        successor_entity_ids=kw.get("successor_entity_ids", ()),
    )


def _prof(
    pid: str, eid: str,
    fye: str = "month_03",
    qmonths: tuple[str, ...] = ("month_03", "month_06", "month_09", "month_12"),
    cluster: str = "moderate",
    intensity: str = "medium",
) -> ReportingCalendarProfile:
    return ReportingCalendarProfile(
        reporting_calendar_profile_id=pid,
        entity_id=eid,
        fiscal_year_end_month_label=fye,
        quarterly_reporting_month_labels=qmonths,
        disclosure_cluster_label=cluster,
        reporting_intensity_label=intensity,
    )


def test_universe_calendar_readout_is_read_only() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        _evt("ue:1", "2026-Q1-month_03", "entity_listed", affected_entity_ids=("firm:a",))
    )
    kernel.reporting_calendars.add_profile(_prof("rcp:1", "firm:a"))
    snap_before = {
        "universe_events": kernel.universe_events.snapshot(),
        "reporting_calendars": kernel.reporting_calendars.snapshot(),
        "ledger_len": len(kernel.ledger.records),
    }
    a = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    snap_after = {
        "universe_events": kernel.universe_events.snapshot(),
        "reporting_calendars": kernel.reporting_calendars.snapshot(),
        "ledger_len": len(kernel.ledger.records),
    }
    assert snap_before == snap_after
    b = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    assert a.to_dict() == b.to_dict()


def test_active_set_changes_with_listed_and_delisted_events() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        _evt("ue:1", "2026-Q1-month_03", "entity_listed", affected_entity_ids=("firm:a",))
    )
    kernel.universe_events.add_event(
        _evt("ue:2", "2026-Q3-month_09", "entity_delisted", affected_entity_ids=("firm:a",))
    )
    # As of Q2 — firm:a active.
    r2 = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q2-month_06")
    assert "firm:a" in r2.active_entity_ids
    assert "firm:a" not in r2.inactive_entity_ids
    # As of Q4 — firm:a inactive.
    r4 = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    assert "firm:a" not in r4.active_entity_ids
    assert "firm:a" in r4.inactive_entity_ids
    assert r4.delisted_event_count == 1


def test_merged_renamed_split_events_preserve_predecessor_successor() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        _evt("ue:1", "2026-Q1-month_03", "entity_listed", affected_entity_ids=("firm:old_a", "firm:old_b"))
    )
    kernel.universe_events.add_event(
        _evt(
            "ue:2", "2026-Q3-month_09", "entity_merged",
            affected_entity_ids=("firm:successor",),
            predecessor_entity_ids=("firm:old_a", "firm:old_b"),
            successor_entity_ids=("firm:successor",),
        )
    )
    r = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    assert "firm:old_a" not in r.active_entity_ids
    assert "firm:old_b" not in r.active_entity_ids
    assert "firm:successor" in r.active_entity_ids
    assert {"firm:old_a", "firm:old_b"} <= set(r.inactive_entity_ids)
    assert r.merged_event_count == 1


def test_unknown_event_type_does_not_alter_active_set_and_warns() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        _evt("ue:1", "2026-Q1-month_03", "entity_listed", affected_entity_ids=("firm:a",))
    )
    kernel.universe_events.add_event(
        _evt("ue:2", "2026-Q2-month_06", "unknown", affected_entity_ids=("firm:a",))
    )
    r = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    assert "firm:a" in r.active_entity_ids
    assert any(
        "unknown event_type_label" in w
        for w in r.warnings
    )


def test_reporting_due_entity_ids_respect_quarterly_month_labels() -> None:
    kernel = _bare_kernel()
    kernel.reporting_calendars.add_profile(
        _prof("rcp:a", "firm:a", qmonths=("month_03", "month_06", "month_09", "month_12"))
    )
    kernel.reporting_calendars.add_profile(
        _prof("rcp:b", "firm:b", qmonths=("month_06",))
    )
    r_jun = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q2-month_06")
    assert set(r_jun.reporting_due_entity_ids) == {"firm:a", "firm:b"}
    r_jul = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q3-month_07")
    assert r_jul.reporting_due_entity_ids == ()


def test_inactive_reporting_profile_warning_visible() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        _evt("ue:1", "2026-Q1-month_03", "entity_listed", affected_entity_ids=("firm:a",))
    )
    kernel.universe_events.add_event(
        _evt("ue:2", "2026-Q2-month_06", "entity_delisted", affected_entity_ids=("firm:a",))
    )
    kernel.reporting_calendars.add_profile(_prof("rcp:a", "firm:a"))
    r = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    assert any(
        "cites inactive entity" in w
        for w in r.warnings
    )


def test_readout_emits_no_ledger_record() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        _evt("ue:1", "2026-Q1-month_03", "entity_listed")
    )
    n = len(kernel.ledger.records)
    build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    assert len(kernel.ledger.records) == n


def test_readout_does_not_mutate_kernel() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        _evt("ue:1", "2026-Q1-month_03", "entity_listed")
    )
    snap = kernel.universe_events.snapshot()
    build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    assert kernel.universe_events.snapshot() == snap


def test_readout_no_forbidden_wording_in_markdown() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        _evt("ue:1", "2026-Q1-month_03", "entity_listed")
    )
    kernel.reporting_calendars.add_profile(_prof("rcp:1", "firm:default"))
    r = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    md = render_universe_calendar_readout_markdown(r)
    body = md.split("## Boundary statement")[0].lower()
    forbidden_phrases = (
        "earnings_surprise", "earnings surprise",
        "earnings_beat", "earnings beat",
        "earnings_miss", "earnings miss",
        "event_study_alpha", "event study alpha",
        "event_window_return",
        "post_event_drift", "post event drift",
        "calendar_arbitrage",
        "edinet", "tdnet", "j_quants",
        "universe_weight", "constituent_weight",
        "rebalance_event",
        "buy", "sell", "trade", "order", "execution",
        "forecast", "prediction", "recommendation",
        "expected_return", "target_price", "alpha", "performance",
        "amplify", "dampen", "offset", "coexist",
        "aggregate", "composite", "dominant",
    )
    for phrase in forbidden_phrases:
        pattern = rf"\b{re.escape(phrase)}\b"
        assert re.search(pattern, body) is None, (
            f"forbidden phrase {phrase!r} in markdown body"
        )


def test_readout_deterministic_across_runs() -> None:
    kernel = _bare_kernel()
    kernel.universe_events.add_event(
        _evt("ue:1", "2026-Q1-month_03", "entity_listed", affected_entity_ids=("firm:a",))
    )
    kernel.universe_events.add_event(
        _evt("ue:2", "2026-Q2-month_06", "entity_listed", affected_entity_ids=("firm:b",))
    )
    kernel.reporting_calendars.add_profile(_prof("rcp:a", "firm:a"))
    a = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    b = build_universe_calendar_readout(kernel, as_of_period_id="2026-Q4-month_12")
    assert a.to_dict() == b.to_dict()
    md_a = render_universe_calendar_readout_markdown(a)
    md_b = render_universe_calendar_readout_markdown(b)
    assert md_a == md_b
