"""
Tests for v1.17.1 Temporal Display Series — display-only
record types, the standalone ``DisplayTimelineBook``, and the
deterministic ``build_reporting_calendar`` /
``build_synthetic_display_path`` helpers.

Pinned invariants:

- closed-set vocabularies (``FREQUENCY_LABELS``,
  ``INTERPOLATION_LABELS``, ``ANNOTATION_TYPE_LABELS``,
  ``SEVERITY_LABELS``, ``STATUS_LABELS``, ``VISIBILITY_LABELS``);
- the v1.17.0 hard naming boundary
  (``FORBIDDEN_DISPLAY_NAMES``) disjoint from every other
  vocabulary;
- frozen dataclasses with bool / non-numeric / out-of-range
  rejection on every numeric field;
- ``to_dict`` is byte-identical across two calls with the same
  inputs;
- ``build_reporting_calendar`` produces deterministic
  ``date_points`` per ``frequency_label``;
- ``build_synthetic_display_path`` aligns
  ``len(date_points) == len(display_values)``;
- linear / step / hold_forward interpolation behaves as
  documented;
- ``DisplayTimelineBook`` add / get / list semantics;
- the module imports no source-of-truth book
  (no ``WorldKernel`` / ``Ledger`` / ``PriceBook`` import);
- a default-fixture run never registers a display object
  and never moves ``living_world_digest``;
- the module text never names a forbidden display name;
- jurisdiction-neutral identifier scan over module + test
  text.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from world.display_timeline import (
    ANNOTATION_TYPE_LABELS,
    CausalTimelineAnnotation,
    COMPARISON_AXIS_LABELS,
    DisplayTimelineBook,
    DuplicateCausalTimelineAnnotationError,
    DuplicateEventAnnotationError,
    DuplicateReferenceTimelineSeriesError,
    DuplicateRegimeComparisonPanelError,
    DuplicateReportingCalendarError,
    DuplicateSyntheticDisplayPathError,
    EventAnnotationRecord,
    FORBIDDEN_DISPLAY_NAMES,
    FREQUENCY_LABELS,
    INTERPOLATION_LABELS,
    NamedRegimePanel,
    ReferenceTimelineSeries,
    ReportingCalendar,
    SEVERITY_LABELS,
    STATUS_LABELS,
    SyntheticDisplayPath,
    UnknownCausalTimelineAnnotationError,
    UnknownEventAnnotationError,
    UnknownReferenceTimelineSeriesError,
    UnknownRegimeComparisonPanelError,
    UnknownReportingCalendarError,
    UnknownSyntheticDisplayPathError,
    VISIBILITY_LABELS,
    build_named_regime_panel,
    build_regime_comparison_panel,
    build_reporting_calendar,
    build_synthetic_display_path,
    render_regime_comparison_markdown,
)


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "world" / "display_timeline.py"
)


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


def test_frequency_labels_closed_set():
    assert FREQUENCY_LABELS == frozenset(
        {"quarterly", "monthly", "daily_like", "unknown"}
    )


def test_interpolation_labels_closed_set():
    assert INTERPOLATION_LABELS == frozenset(
        {"step", "linear", "hold_forward", "event_weighted", "unknown"}
    )


def test_annotation_type_labels_closed_set():
    assert ANNOTATION_TYPE_LABELS == frozenset(
        {
            "market_environment_change",
            "attention_shift",
            "market_pressure_change",
            "financing_constraint",
            "causal_checkpoint",
            "synthetic_event",
            "unknown",
        }
    )


def test_severity_labels_closed_set():
    assert SEVERITY_LABELS == frozenset(
        {"low", "medium", "high", "unknown"}
    )


def test_status_labels_closed_set():
    assert STATUS_LABELS == frozenset(
        {
            "draft",
            "active",
            "stale",
            "superseded",
            "archived",
            "unknown",
        }
    )


def test_visibility_labels_closed_set():
    assert VISIBILITY_LABELS == frozenset(
        {"internal_only", "shared_internal", "external_audit"}
    )


def test_forbidden_display_names_disjoint_from_every_vocabulary():
    """The v1.17.0 hard naming boundary must not overlap with any
    closed-set value used by display-layer fields."""
    for vocab in (
        FREQUENCY_LABELS,
        INTERPOLATION_LABELS,
        ANNOTATION_TYPE_LABELS,
        SEVERITY_LABELS,
        STATUS_LABELS,
        VISIBILITY_LABELS,
    ):
        assert not (FORBIDDEN_DISPLAY_NAMES & vocab)


def test_forbidden_display_names_includes_v1_17_0_pinned_set():
    """The v1.17.0 design pinned a binding forbidden list."""
    pinned = {
        "market_price",
        "predicted_index",
        "predicted_path",
        "expected_return",
        "target_price",
        "forecast_path",
        "forecast_index",
        "real_price_series",
        "actual_price",
        "quoted_price",
        "last_trade",
        "nav",
        "index_value",
        "benchmark_value",
        "valuation_target",
        "investment_recommendation",
        "price_prediction",
    }
    assert pinned <= FORBIDDEN_DISPLAY_NAMES


# ---------------------------------------------------------------------------
# build_reporting_calendar — deterministic date_points
# ---------------------------------------------------------------------------


def test_quarterly_calendar_date_points_deterministic():
    cal_a = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:2026:quarterly",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="quarterly",
        source_period_dates=(
            "2026-03-31",
            "2026-06-30",
            "2026-09-30",
            "2026-12-31",
        ),
    )
    cal_b = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:2026:quarterly",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="quarterly",
        source_period_dates=(
            "2026-03-31",
            "2026-06-30",
            "2026-09-30",
            "2026-12-31",
        ),
    )
    assert cal_a.to_dict() == cal_b.to_dict()
    assert cal_a.date_points == (
        "2026-03-31",
        "2026-06-30",
        "2026-09-30",
        "2026-12-31",
    )


def test_monthly_calendar_date_points_deterministic_and_dense():
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:2026:monthly",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="monthly",
    )
    # March (clamped at month end), April, May, ..., December.
    assert len(cal.date_points) == 10
    assert cal.date_points[0] == "2026-03-31"
    assert cal.date_points[-1] == "2026-12-31"


def test_daily_like_calendar_date_points_deterministic_and_dense():
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:2026:daily_like",
        start_date="2026-03-31",
        end_date="2026-04-04",
        frequency_label="daily_like",
    )
    assert cal.date_points == (
        "2026-03-31",
        "2026-04-01",
        "2026-04-02",
        "2026-04-03",
        "2026-04-04",
    )


def test_unknown_frequency_calendar_emits_no_date_points():
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:unknown",
        start_date="2026-03-31",
        end_date="2026-04-30",
        frequency_label="unknown",
    )
    assert cal.date_points == ()


def test_invalid_frequency_label_rejected_at_helper():
    with pytest.raises(ValueError):
        build_reporting_calendar(
            calendar_id="reporting_calendar:reference_run:bad",
            start_date="2026-03-31",
            end_date="2026-04-30",
            frequency_label="hourly",
        )


def test_invalid_frequency_label_rejected_at_record():
    with pytest.raises(ValueError):
        ReportingCalendar(
            calendar_id="reporting_calendar:reference_run:bad",
            start_date="2026-03-31",
            end_date="2026-04-30",
            frequency_label="hourly",
        )


def test_calendar_rejects_start_after_end():
    with pytest.raises(ValueError):
        ReportingCalendar(
            calendar_id="reporting_calendar:reference_run:bad",
            start_date="2026-12-31",
            end_date="2026-03-31",
            frequency_label="quarterly",
        )


def test_calendar_accepts_date_objects():
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:dates",
        start_date=date(2026, 3, 31),
        end_date=date(2026, 6, 30),
        frequency_label="monthly",
    )
    assert cal.start_date == "2026-03-31"
    assert cal.end_date == "2026-06-30"


# ---------------------------------------------------------------------------
# build_synthetic_display_path — alignment + interpolation
# ---------------------------------------------------------------------------


def _quarterly_calendar():
    return build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:2026:quarterly",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="quarterly",
        source_period_dates=(
            "2026-03-31",
            "2026-06-30",
            "2026-09-30",
            "2026-12-31",
        ),
    )


def _monthly_calendar():
    return build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:2026:monthly",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="monthly",
    )


def _daily_like_calendar():
    return build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:2026:daily_like",
        start_date="2026-03-31",
        end_date="2026-04-04",
        frequency_label="daily_like",
    )


def test_path_length_matches_calendar_date_points_quarterly():
    cal = _quarterly_calendar()
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:quarterly",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=cal.source_period_dates,
        anchor_values=(0.10, 0.40, 0.65, 0.30),
        interpolation_label="linear",
    )
    assert len(path.date_points) == len(path.display_values)
    assert len(path.date_points) == len(cal.date_points)


def test_path_length_matches_calendar_date_points_monthly():
    cal = _monthly_calendar()
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:monthly",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=(
            "2026-03-31",
            "2026-06-30",
            "2026-09-30",
            "2026-12-31",
        ),
        anchor_values=(0.10, 0.40, 0.65, 0.30),
        interpolation_label="linear",
    )
    assert len(path.date_points) == len(path.display_values)
    assert len(path.date_points) == len(cal.date_points)


def test_path_length_matches_calendar_date_points_daily_like():
    cal = _daily_like_calendar()
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:daily_like",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=("2026-03-31", "2026-04-04"),
        anchor_values=(0.10, 0.50),
        interpolation_label="linear",
    )
    assert len(path.date_points) == len(path.display_values)
    assert len(path.date_points) == len(cal.date_points)


def test_linear_interpolation_at_midpoint():
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:linear_test",
        start_date="2026-04-01",
        end_date="2026-04-03",
        frequency_label="daily_like",
    )
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:linear_test",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=("2026-04-01", "2026-04-03"),
        anchor_values=(0.0, 1.0),
        interpolation_label="linear",
    )
    # Mid-day should land at exactly 0.5.
    assert path.display_values[0] == 0.0
    assert abs(path.display_values[1] - 0.5) < 1e-12
    assert path.display_values[2] == 1.0


def test_step_interpolation_holds_anchor_then_jumps():
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:step_test",
        start_date="2026-04-01",
        end_date="2026-04-05",
        frequency_label="daily_like",
    )
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:step_test",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=("2026-04-02", "2026-04-04"),
        anchor_values=(0.2, 0.8),
        interpolation_label="step",
    )
    # Day 04-01 (before any anchor) holds first anchor's value;
    # 04-02 / 04-03 hold 0.2; 04-04 / 04-05 hold 0.8.
    assert path.display_values == (0.2, 0.2, 0.2, 0.8, 0.8)


def test_hold_forward_interpolation_matches_step():
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:hold_forward_test",
        start_date="2026-04-01",
        end_date="2026-04-05",
        frequency_label="daily_like",
    )
    step_path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:hold_forward_test:a",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=("2026-04-02", "2026-04-04"),
        anchor_values=(0.2, 0.8),
        interpolation_label="step",
    )
    hold_forward_path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:hold_forward_test:b",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=("2026-04-02", "2026-04-04"),
        anchor_values=(0.2, 0.8),
        interpolation_label="hold_forward",
    )
    assert step_path.display_values == hold_forward_path.display_values


def test_event_weighted_falls_back_to_hold_forward():
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:event_weighted_test",
        start_date="2026-04-01",
        end_date="2026-04-05",
        frequency_label="daily_like",
    )
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:event_weighted_test",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=("2026-04-02", "2026-04-04"),
        anchor_values=(0.2, 0.8),
        interpolation_label="event_weighted",
    )
    # event_weighted defers synthesis to v1.17.3 and falls back
    # to hold_forward in v1.17.1 — same as step.
    assert path.display_values == (0.2, 0.2, 0.2, 0.8, 0.8)


def test_path_clamps_outside_unit_range_via_anchor_validation():
    """Anchor values must lie in [0.0, 1.0]; bool / out-of-range
    rejected at construction."""
    cal = _quarterly_calendar()
    with pytest.raises(ValueError):
        build_synthetic_display_path(
            path_id="synthetic_display_path:reference_run:bad_range",
            calendar=cal,
            path_label="indicative_pressure_path",
            anchor_period_dates=cal.source_period_dates,
            anchor_values=(0.0, 1.5, 0.5, 0.0),
        )


def test_path_rejects_bool_anchor_value():
    cal = _quarterly_calendar()
    with pytest.raises(ValueError):
        build_synthetic_display_path(
            path_id="synthetic_display_path:reference_run:bad_bool",
            calendar=cal,
            path_label="indicative_pressure_path",
            anchor_period_dates=cal.source_period_dates,
            anchor_values=(True, 0.4, 0.6, 0.3),  # type: ignore[list-item]
        )


def test_path_rejects_non_numeric_anchor_value():
    cal = _quarterly_calendar()
    with pytest.raises(ValueError):
        build_synthetic_display_path(
            path_id="synthetic_display_path:reference_run:bad_str",
            calendar=cal,
            path_label="indicative_pressure_path",
            anchor_period_dates=cal.source_period_dates,
            anchor_values=("0.4", 0.4, 0.6, 0.3),  # type: ignore[list-item]
        )


def test_path_rejects_empty_anchor_set():
    cal = _quarterly_calendar()
    with pytest.raises(ValueError):
        build_synthetic_display_path(
            path_id="synthetic_display_path:reference_run:empty",
            calendar=cal,
            path_label="indicative_pressure_path",
            anchor_period_dates=(),
            anchor_values=(),
        )


def test_path_rejects_invalid_interpolation_label():
    cal = _quarterly_calendar()
    with pytest.raises(ValueError):
        build_synthetic_display_path(
            path_id="synthetic_display_path:reference_run:bad_kernel",
            calendar=cal,
            path_label="indicative_pressure_path",
            anchor_period_dates=cal.source_period_dates,
            anchor_values=(0.10, 0.40, 0.65, 0.30),
            interpolation_label="ema",
        )


def test_path_anchor_dates_sorted_before_interpolation():
    """Helper sorts anchors by date so the same set of pairs in
    any order produces the same path."""
    cal = _monthly_calendar()
    a = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:sort:a",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=(
            "2026-12-31",
            "2026-03-31",
            "2026-09-30",
            "2026-06-30",
        ),
        anchor_values=(0.30, 0.10, 0.65, 0.40),
        interpolation_label="linear",
    )
    b = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:sort:b",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=(
            "2026-03-31",
            "2026-06-30",
            "2026-09-30",
            "2026-12-31",
        ),
        anchor_values=(0.10, 0.40, 0.65, 0.30),
        interpolation_label="linear",
    )
    assert a.display_values == b.display_values


# ---------------------------------------------------------------------------
# Frozen / immutable
# ---------------------------------------------------------------------------


def test_calendar_record_immutable():
    cal = ReportingCalendar(
        calendar_id="reporting_calendar:test",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="quarterly",
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        cal.calendar_id = "other"  # type: ignore[misc]


def test_path_record_immutable():
    cal = _quarterly_calendar()
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:test",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=cal.source_period_dates,
        anchor_values=(0.10, 0.40, 0.65, 0.30),
    )
    with pytest.raises(Exception):
        path.path_id = "other"  # type: ignore[misc]


def test_event_annotation_record_immutable():
    a = EventAnnotationRecord(
        annotation_id="event_annotation:test",
        annotation_date="2026-04-15",
        annotation_label="market environment shifted to constrained",
        annotation_type_label="market_environment_change",
        severity_label="medium",
    )
    with pytest.raises(Exception):
        a.annotation_id = "other"  # type: ignore[misc]


def test_causal_annotation_record_immutable():
    a = CausalTimelineAnnotation(
        causal_annotation_id="causal_timeline:test",
        annotation_date="2026-04-15",
        event_label="pressure widened attention to risk + funding",
        causal_summary_label="causal_checkpoint",
    )
    with pytest.raises(Exception):
        a.causal_annotation_id = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# to_dict round-trip / determinism
# ---------------------------------------------------------------------------


def test_calendar_to_dict_round_trip_byte_identical():
    cal_a = ReportingCalendar(
        calendar_id="reporting_calendar:test",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="quarterly",
        date_points=("2026-03-31", "2026-06-30"),
        source_period_dates=("2026-03-31", "2026-06-30"),
    )
    cal_b = ReportingCalendar(
        calendar_id="reporting_calendar:test",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="quarterly",
        date_points=("2026-03-31", "2026-06-30"),
        source_period_dates=("2026-03-31", "2026-06-30"),
    )
    assert cal_a.to_dict() == cal_b.to_dict()


def test_path_to_dict_round_trip_byte_identical():
    cal = _quarterly_calendar()
    a = build_synthetic_display_path(
        path_id="synthetic_display_path:test",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=cal.source_period_dates,
        anchor_values=(0.10, 0.40, 0.65, 0.30),
    )
    b = build_synthetic_display_path(
        path_id="synthetic_display_path:test",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=cal.source_period_dates,
        anchor_values=(0.10, 0.40, 0.65, 0.30),
    )
    assert a.to_dict() == b.to_dict()


def test_event_annotation_to_dict_round_trip():
    a = EventAnnotationRecord(
        annotation_id="event_annotation:test:m1",
        annotation_date="2026-04-15",
        annotation_label="attention shifted to risk + funding",
        annotation_type_label="attention_shift",
        severity_label="medium",
        source_record_ids=(
            "indicative_market_pressure:reference_run:2026-03-31",
        ),
    )
    b = EventAnnotationRecord(**a.to_dict())  # type: ignore[arg-type]
    # to_dict returns lists; comparison is on dict structure.
    assert a.to_dict() == b.to_dict()


def test_causal_annotation_to_dict_round_trip():
    a = CausalTimelineAnnotation(
        causal_annotation_id="causal_timeline:test:m1",
        annotation_date="2026-04-15",
        event_label="pressure widened attention",
        affected_actor_ids=("investor:reference_pension_a",),
        source_record_ids=(
            "indicative_market_pressure:reference_run:2026-03-31",
        ),
        downstream_record_ids=(
            "attention_state:investor:reference_pension_a:2026-06-30",
        ),
        causal_summary_label="causal_checkpoint",
    )
    b = CausalTimelineAnnotation(**a.to_dict())  # type: ignore[arg-type]
    assert a.to_dict() == b.to_dict()


# ---------------------------------------------------------------------------
# Closed-set rejection
# ---------------------------------------------------------------------------


def test_event_annotation_rejects_unknown_type_label():
    with pytest.raises(ValueError):
        EventAnnotationRecord(
            annotation_id="event_annotation:bad",
            annotation_date="2026-04-15",
            annotation_label="x",
            annotation_type_label="custom_event",
            severity_label="medium",
        )


def test_event_annotation_rejects_unknown_severity_label():
    with pytest.raises(ValueError):
        EventAnnotationRecord(
            annotation_id="event_annotation:bad",
            annotation_date="2026-04-15",
            annotation_label="x",
            annotation_type_label="attention_shift",
            severity_label="catastrophic",
        )


def test_causal_annotation_rejects_unknown_summary_label():
    with pytest.raises(ValueError):
        CausalTimelineAnnotation(
            causal_annotation_id="causal_timeline:bad",
            annotation_date="2026-04-15",
            event_label="x",
            causal_summary_label="alpha_call",
        )


def test_calendar_rejects_unknown_status():
    with pytest.raises(ValueError):
        ReportingCalendar(
            calendar_id="reporting_calendar:bad",
            start_date="2026-03-31",
            end_date="2026-06-30",
            frequency_label="quarterly",
            status="committed",
        )


def test_calendar_rejects_unknown_visibility():
    with pytest.raises(ValueError):
        ReportingCalendar(
            calendar_id="reporting_calendar:bad",
            start_date="2026-03-31",
            end_date="2026-06-30",
            frequency_label="quarterly",
            visibility="public_marketing",
        )


# ---------------------------------------------------------------------------
# DisplayTimelineBook
# ---------------------------------------------------------------------------


def test_book_add_get_list_calendar():
    book = DisplayTimelineBook()
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:m",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="monthly",
    )
    book.add_calendar(cal)
    assert book.get_calendar(cal.calendar_id) is cal
    assert book.list_calendars() == (cal,)


def test_book_duplicate_calendar_id_raises():
    book = DisplayTimelineBook()
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:dup",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="monthly",
    )
    book.add_calendar(cal)
    with pytest.raises(DuplicateReportingCalendarError):
        book.add_calendar(cal)


def test_book_unknown_calendar_id_raises():
    book = DisplayTimelineBook()
    with pytest.raises(UnknownReportingCalendarError):
        book.get_calendar("missing")


def test_book_add_get_list_reference_series():
    book = DisplayTimelineBook()
    cal = _monthly_calendar()
    series = ReferenceTimelineSeries(
        series_id="reference_timeline:reference_run:s1",
        calendar_id=cal.calendar_id,
        series_label="indicative_pressure_path:firm:reference_manufacturer_a",
        frequency_label="monthly",
        date_points=cal.date_points,
        source_period_dates=(
            "2026-03-31",
            "2026-06-30",
            "2026-09-30",
            "2026-12-31",
        ),
        source_record_ids=(
            "indicative_market_pressure:reference_run:2026-03-31",
        ),
    )
    book.add_reference_series(series)
    assert book.get_reference_series(series.series_id) is series
    assert book.list_reference_series() == (series,)


def test_book_duplicate_series_id_raises():
    book = DisplayTimelineBook()
    series = ReferenceTimelineSeries(
        series_id="reference_timeline:dup",
        calendar_id="reporting_calendar:any",
        series_label="indicative_pressure_path",
        frequency_label="monthly",
    )
    book.add_reference_series(series)
    with pytest.raises(DuplicateReferenceTimelineSeriesError):
        book.add_reference_series(series)


def test_book_unknown_series_raises():
    book = DisplayTimelineBook()
    with pytest.raises(UnknownReferenceTimelineSeriesError):
        book.get_reference_series("missing")


def test_book_add_get_list_display_path():
    book = DisplayTimelineBook()
    cal = _quarterly_calendar()
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:p1",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=cal.source_period_dates,
        anchor_values=(0.10, 0.40, 0.65, 0.30),
    )
    book.add_display_path(path)
    assert book.get_display_path(path.path_id) is path
    assert book.list_display_paths() == (path,)
    assert book.list_paths_by_calendar(cal.calendar_id) == (path,)
    assert book.list_paths_by_calendar("missing") == ()


def test_book_duplicate_path_id_raises():
    book = DisplayTimelineBook()
    cal = _quarterly_calendar()
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:dup",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=cal.source_period_dates,
        anchor_values=(0.10, 0.40, 0.65, 0.30),
    )
    book.add_display_path(path)
    with pytest.raises(DuplicateSyntheticDisplayPathError):
        book.add_display_path(path)


def test_book_unknown_path_raises():
    book = DisplayTimelineBook()
    with pytest.raises(UnknownSyntheticDisplayPathError):
        book.get_display_path("missing")


def test_book_add_get_list_event_annotation():
    book = DisplayTimelineBook()
    a = EventAnnotationRecord(
        annotation_id="event_annotation:test:e1",
        annotation_date="2026-04-15",
        annotation_label="x",
        annotation_type_label="attention_shift",
        severity_label="medium",
    )
    book.add_event_annotation(a)
    assert book.get_event_annotation(a.annotation_id) is a
    assert book.list_event_annotations() == (a,)


def test_book_duplicate_event_annotation_raises():
    book = DisplayTimelineBook()
    a = EventAnnotationRecord(
        annotation_id="event_annotation:dup",
        annotation_date="2026-04-15",
        annotation_label="x",
        annotation_type_label="attention_shift",
        severity_label="medium",
    )
    book.add_event_annotation(a)
    with pytest.raises(DuplicateEventAnnotationError):
        book.add_event_annotation(a)


def test_book_unknown_event_annotation_raises():
    book = DisplayTimelineBook()
    with pytest.raises(UnknownEventAnnotationError):
        book.get_event_annotation("missing")


def test_book_add_get_list_causal_annotation():
    book = DisplayTimelineBook()
    a = CausalTimelineAnnotation(
        causal_annotation_id="causal_timeline:test:c1",
        annotation_date="2026-04-15",
        event_label="pressure widened attention",
        causal_summary_label="causal_checkpoint",
    )
    book.add_causal_annotation(a)
    assert book.get_causal_annotation(a.causal_annotation_id) is a
    assert book.list_causal_annotations() == (a,)


def test_book_duplicate_causal_annotation_raises():
    book = DisplayTimelineBook()
    a = CausalTimelineAnnotation(
        causal_annotation_id="causal_timeline:dup",
        annotation_date="2026-04-15",
        event_label="x",
        causal_summary_label="causal_checkpoint",
    )
    book.add_causal_annotation(a)
    with pytest.raises(DuplicateCausalTimelineAnnotationError):
        book.add_causal_annotation(a)


def test_book_unknown_causal_annotation_raises():
    book = DisplayTimelineBook()
    with pytest.raises(UnknownCausalTimelineAnnotationError):
        book.get_causal_annotation("missing")


def test_book_list_annotations_by_date_returns_events_and_causals():
    book = DisplayTimelineBook()
    target = "2026-04-15"
    e = EventAnnotationRecord(
        annotation_id="event_annotation:test:e1",
        annotation_date=target,
        annotation_label="x",
        annotation_type_label="attention_shift",
        severity_label="medium",
    )
    other_event = EventAnnotationRecord(
        annotation_id="event_annotation:test:e2",
        annotation_date="2026-05-15",
        annotation_label="y",
        annotation_type_label="attention_shift",
        severity_label="low",
    )
    c = CausalTimelineAnnotation(
        causal_annotation_id="causal_timeline:test:c1",
        annotation_date=target,
        event_label="z",
        causal_summary_label="causal_checkpoint",
    )
    book.add_event_annotation(e)
    book.add_event_annotation(other_event)
    book.add_causal_annotation(c)
    result = book.list_annotations_by_date(target)
    assert e in result
    assert c in result
    assert other_event not in result


def test_book_snapshot_deterministic():
    book = DisplayTimelineBook()
    cal = _quarterly_calendar()
    book.add_calendar(cal)
    path = build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:snapshot",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=cal.source_period_dates,
        anchor_values=(0.10, 0.40, 0.65, 0.30),
    )
    book.add_display_path(path)
    snap_a = book.snapshot()
    snap_b = book.snapshot()
    assert snap_a == snap_b


# ---------------------------------------------------------------------------
# Integration discipline — no kernel mutation, no ledger writes
# ---------------------------------------------------------------------------


def test_module_does_not_import_kernel_or_ledger_or_pricebook():
    """v1.17.1 keeps the display module standalone — it must
    import no source-of-truth book."""
    text = _MODULE_PATH.read_text(encoding="utf-8")
    forbidden_imports = (
        "from world.kernel import",
        "from world.ledger import",
        "from world.prices import",
        "from world.attention import ",
        "from world.attention_feedback import ",
        "from world.market_pressure import ",
        "from world.market_intents import ",
        "from world.financing_paths import ",
        "from world.firm_state import ",
        "from world.market_environment import ",
    )
    for needle in forbidden_imports:
        assert needle not in text, (
            f"display_timeline must not import a runtime book: "
            f"{needle!r}"
        )


def test_default_living_world_run_does_not_create_display_records():
    """Sanity: the v1.17.1 module is standalone, so a default
    living-world sweep does not register any display object and
    does not move ``living_world_digest``."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import _run_default, _seed_kernel

    k = _seed_kernel()
    r = _run_default(k)
    digest_before = living_world_digest(k, r)
    # Build a display calendar and path — must not change any
    # kernel attribute or the digest.
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:reference_run:test",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="monthly",
        source_period_dates=(
            "2026-03-31",
            "2026-06-30",
            "2026-09-30",
            "2026-12-31",
        ),
    )
    build_synthetic_display_path(
        path_id="synthetic_display_path:reference_run:test",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=cal.source_period_dates,
        anchor_values=(0.10, 0.40, 0.65, 0.30),
    )
    # Digest is computed from the kernel + the run result, not
    # the standalone display book — should be unchanged.
    digest_after = living_world_digest(k, r)
    assert digest_before == digest_after


def test_pricebook_byte_equal_around_display_helpers():
    """Building a calendar and path must not mutate the
    PriceBook even if a kernel is in scope."""
    from test_living_reference_world import _seed_kernel

    k = _seed_kernel()
    snap_before = k.prices.snapshot()
    cal = build_reporting_calendar(
        calendar_id="reporting_calendar:pricebook_test",
        start_date="2026-03-31",
        end_date="2026-12-31",
        frequency_label="quarterly",
        source_period_dates=(
            "2026-03-31",
            "2026-06-30",
            "2026-09-30",
            "2026-12-31",
        ),
    )
    build_synthetic_display_path(
        path_id="synthetic_display_path:pricebook_test",
        calendar=cal,
        path_label="indicative_pressure_path",
        anchor_period_dates=cal.source_period_dates,
        anchor_values=(0.10, 0.40, 0.65, 0.30),
    )
    snap_after = k.prices.snapshot()
    assert snap_before == snap_after


# ---------------------------------------------------------------------------
# Forbidden-name + jurisdiction-neutral scans
# ---------------------------------------------------------------------------


def test_module_text_does_not_use_forbidden_display_names():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    # We allow the names to APPEAR inside the
    # ``FORBIDDEN_DISPLAY_NAMES`` literal at module scope (that's
    # the closed-set definition itself); strip the literal and
    # then scan.
    open_idx = text.find("FORBIDDEN_DISPLAY_NAMES: frozenset[str] = frozenset(")
    close_idx = text.find(")", open_idx)
    if open_idx >= 0 and close_idx > open_idx:
        scrubbed = text[:open_idx] + text[close_idx:]
    else:  # pragma: no cover
        scrubbed = text
    for forbidden in FORBIDDEN_DISPLAY_NAMES:
        assert forbidden not in scrubbed, (
            f"forbidden display name {forbidden!r} appears in "
            f"display_timeline.py outside the closed-set literal"
        )


def test_payloads_do_not_carry_forbidden_display_names_as_keys():
    """Every record's ``to_dict`` keys must be disjoint from the
    forbidden display-name set."""
    cal = ReportingCalendar(
        calendar_id="reporting_calendar:test",
        start_date="2026-03-31",
        end_date="2026-06-30",
        frequency_label="quarterly",
    )
    series = ReferenceTimelineSeries(
        series_id="reference_timeline:test",
        calendar_id=cal.calendar_id,
        series_label="indicative_pressure_path",
        frequency_label="quarterly",
    )
    path = SyntheticDisplayPath(
        path_id="synthetic_display_path:test",
        calendar_id=cal.calendar_id,
        path_label="indicative_pressure_path",
    )
    event = EventAnnotationRecord(
        annotation_id="event_annotation:test",
        annotation_date="2026-04-15",
        annotation_label="x",
        annotation_type_label="attention_shift",
        severity_label="medium",
    )
    causal = CausalTimelineAnnotation(
        causal_annotation_id="causal_timeline:test",
        annotation_date="2026-04-15",
        event_label="x",
        causal_summary_label="causal_checkpoint",
    )
    for payload in (
        cal.to_dict(),
        series.to_dict(),
        path.to_dict(),
        event.to_dict(),
        causal.to_dict(),
    ):
        keys = set(payload.keys())
        assert not (keys & FORBIDDEN_DISPLAY_NAMES), (
            f"forbidden display names {keys & FORBIDDEN_DISPLAY_NAMES!r} "
            f"appeared in payload keys"
        )


# Reuse the standard JFWE forbidden-token scan against the
# v1.17.1 module + this test file.
_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "jgb", "nyse",
    "nasdaq",
)


def test_module_jurisdiction_neutral_identifier_scan():
    """The display module must not name any jurisdiction-specific
    real-world entity / regulator / venue / index / issuer."""
    text = _MODULE_PATH.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in display_timeline.py"
        )


def test_test_file_jurisdiction_neutral_identifier_scan():
    """The test fixtures must not name any jurisdiction-specific
    real-world entity. The literal ``_FORBIDDEN_TOKENS`` tuple is
    scrubbed from the scanned text so it does not self-trigger."""
    text = Path(__file__).read_text(encoding="utf-8").lower()
    table_start = text.find("_forbidden_tokens = (")
    table_end = text.find(")", table_start) + 1
    if table_start != -1 and table_end > 0:
        text = text[:table_start] + text[table_end:]
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in test_display_timeline.py"
        )


# ---------------------------------------------------------------------------
# v1.17.2 — Regime comparison panel
# ---------------------------------------------------------------------------


def test_comparison_axis_labels_closed_set():
    assert COMPARISON_AXIS_LABELS == frozenset(
        {
            "attention_focus",
            "market_intent_direction",
            "aggregated_market_interest",
            "indicative_market_pressure",
            "financing_path_constraint",
            "financing_path_coherence",
            "unresolved_refs",
            "record_count_digest",
        }
    )


def test_named_regime_panel_helper_builds_histogram():
    p = build_named_regime_panel(
        regime_id="constructive",
        digest="abc123",
        record_count=460,
        unresolved_refs_count=2,
        attention_focus_labels=(
            "memory",
            "firm_state",
            "firm_state",
        ),
        market_intent_direction_labels=(
            "hold_review",
            "engagement_linked_review",
        ),
        aggregated_market_interest_labels=(
            "balanced",
            "supportive",
        ),
        indicative_market_pressure_labels=("open",),
        financing_path_constraint_labels=("no_obvious_constraint",),
        financing_path_coherence_labels=("coherent",),
    )
    assert p.attention_focus_histogram == {"firm_state": 2, "memory": 1}
    assert p.market_intent_direction_histogram == {
        "engagement_linked_review": 1,
        "hold_review": 1,
    }
    assert p.aggregated_market_interest_histogram == {
        "balanced": 1,
        "supportive": 1,
    }
    assert p.indicative_market_pressure_histogram == {"open": 1}
    assert p.financing_path_constraint_histogram == {
        "no_obvious_constraint": 1
    }
    assert p.financing_path_coherence_histogram == {"coherent": 1}
    assert p.record_count == 460
    assert p.unresolved_refs_count == 2
    assert p.digest == "abc123"


def test_named_regime_panel_immutable():
    p = build_named_regime_panel(regime_id="constructive")
    with pytest.raises(Exception):
        p.regime_id = "other"  # type: ignore[misc]


def test_named_regime_panel_to_dict_round_trip_byte_identical():
    a = build_named_regime_panel(
        regime_id="constrained",
        digest="def456",
        record_count=460,
        unresolved_refs_count=5,
        attention_focus_labels=("risk", "funding"),
        market_intent_direction_labels=("liquidity_watch",),
        aggregated_market_interest_labels=("cautious",),
        indicative_market_pressure_labels=("constrained",),
        financing_path_constraint_labels=("market_access_constraint",),
        financing_path_coherence_labels=("conflicting_evidence",),
    )
    b = build_named_regime_panel(
        regime_id="constrained",
        digest="def456",
        record_count=460,
        unresolved_refs_count=5,
        attention_focus_labels=("risk", "funding"),
        market_intent_direction_labels=("liquidity_watch",),
        aggregated_market_interest_labels=("cautious",),
        indicative_market_pressure_labels=("constrained",),
        financing_path_constraint_labels=("market_access_constraint",),
        financing_path_coherence_labels=("conflicting_evidence",),
    )
    assert a.to_dict() == b.to_dict()


def test_named_regime_panel_rejects_negative_counts():
    with pytest.raises(ValueError):
        NamedRegimePanel(regime_id="constructive", record_count=-1)
    with pytest.raises(ValueError):
        NamedRegimePanel(regime_id="constructive", unresolved_refs_count=-1)


def test_named_regime_panel_rejects_bool_counts():
    with pytest.raises(ValueError):
        NamedRegimePanel(
            regime_id="constructive",
            record_count=True,  # type: ignore[arg-type]
        )


def test_named_regime_panel_rejects_negative_histogram_counts():
    with pytest.raises(ValueError):
        NamedRegimePanel(
            regime_id="constructive",
            attention_focus_histogram={"memory": -1},
        )


def test_named_regime_panel_rejects_empty_regime_id():
    with pytest.raises(ValueError):
        NamedRegimePanel(regime_id="")


def test_regime_comparison_panel_helper_bundles_two_regimes():
    p1 = build_named_regime_panel(regime_id="constructive")
    p2 = build_named_regime_panel(regime_id="constrained")
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(p1, p2),
    )
    assert panel.panel_id == "regime_comparison:test"
    assert tuple(p.regime_id for p in panel.regime_panels) == (
        "constructive",
        "constrained",
    )


def test_regime_comparison_panel_default_axes_full_closed_set():
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(build_named_regime_panel(regime_id="x"),),
    )
    assert set(panel.comparison_axes) <= COMPARISON_AXIS_LABELS
    # Default axes hit every label except unknowns.
    assert "attention_focus" in panel.comparison_axes
    assert "record_count_digest" in panel.comparison_axes


def test_regime_comparison_panel_rejects_unknown_axis():
    with pytest.raises(ValueError):
        build_regime_comparison_panel(
            panel_id="regime_comparison:test",
            regime_panels=(build_named_regime_panel(regime_id="x"),),
            comparison_axes=("alpha_call",),
        )


def test_regime_comparison_panel_rejects_duplicate_regime_ids():
    p = build_named_regime_panel(regime_id="constructive")
    with pytest.raises(ValueError):
        build_regime_comparison_panel(
            panel_id="regime_comparison:test",
            regime_panels=(p, p),
        )


def test_regime_comparison_panel_immutable():
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(build_named_regime_panel(regime_id="constructive"),),
    )
    with pytest.raises(Exception):
        panel.panel_id = "other"  # type: ignore[misc]


def test_regime_comparison_panel_to_dict_round_trip():
    panel_a = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(
            build_named_regime_panel(
                regime_id="constructive",
                attention_focus_labels=("memory", "memory"),
            ),
            build_named_regime_panel(
                regime_id="constrained",
                attention_focus_labels=("risk",),
            ),
        ),
    )
    panel_b = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(
            build_named_regime_panel(
                regime_id="constructive",
                attention_focus_labels=("memory", "memory"),
            ),
            build_named_regime_panel(
                regime_id="constrained",
                attention_focus_labels=("risk",),
            ),
        ),
    )
    assert panel_a.to_dict() == panel_b.to_dict()


def test_regime_comparison_markdown_deterministic():
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(
            build_named_regime_panel(
                regime_id="constructive",
                digest="abc",
                record_count=460,
                attention_focus_labels=("memory", "engagement"),
                market_intent_direction_labels=("hold_review",),
                aggregated_market_interest_labels=("balanced",),
                indicative_market_pressure_labels=("open",),
                financing_path_constraint_labels=("no_obvious_constraint",),
                financing_path_coherence_labels=("coherent",),
            ),
            build_named_regime_panel(
                regime_id="constrained",
                digest="def",
                record_count=460,
                attention_focus_labels=("risk", "funding"),
                market_intent_direction_labels=("reduce_interest",),
                aggregated_market_interest_labels=("cautious",),
                indicative_market_pressure_labels=("constrained",),
                financing_path_constraint_labels=(
                    "market_access_constraint",
                ),
                financing_path_coherence_labels=("conflicting_evidence",),
            ),
        ),
    )
    md_a = render_regime_comparison_markdown(panel)
    md_b = render_regime_comparison_markdown(panel)
    assert md_a == md_b
    # Headline + columns
    assert "## Regime comparison — regime_comparison:test" in md_a
    assert "| constructive | constrained |" in md_a
    # Per-axis rows render
    assert "| Attention focus |" in md_a
    assert "| Record count / digest |" in md_a
    # Boundary disclaimer present
    assert "Synthetic display only" in md_a


def test_regime_comparison_markdown_handles_empty_panel():
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:empty",
        regime_panels=(),
    )
    md = render_regime_comparison_markdown(panel)
    assert "regime_comparison:empty" in md
    assert "No regime panels supplied" in md


def test_regime_comparison_markdown_no_forbidden_display_names():
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(
            build_named_regime_panel(
                regime_id="constructive",
                attention_focus_labels=("memory",),
                market_intent_direction_labels=("hold_review",),
            ),
        ),
    )
    md = render_regime_comparison_markdown(panel)
    md_lower = md.lower()
    for forbidden in FORBIDDEN_DISPLAY_NAMES:
        assert forbidden not in md_lower, (
            f"forbidden display name {forbidden!r} in markdown"
        )


def test_book_add_get_list_regime_comparison_panel():
    book = DisplayTimelineBook()
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:reference_run:default",
        regime_panels=(
            build_named_regime_panel(regime_id="constructive"),
            build_named_regime_panel(regime_id="constrained"),
        ),
    )
    book.add_regime_comparison_panel(panel)
    assert (
        book.get_regime_comparison_panel(panel.panel_id) is panel
    )
    assert book.list_regime_comparison_panels() == (panel,)
    snap = book.snapshot()
    assert "regime_comparison_panels" in snap
    assert len(snap["regime_comparison_panels"]) == 1


def test_book_duplicate_regime_panel_id_raises():
    book = DisplayTimelineBook()
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:dup",
        regime_panels=(
            build_named_regime_panel(regime_id="constructive"),
        ),
    )
    book.add_regime_comparison_panel(panel)
    with pytest.raises(DuplicateRegimeComparisonPanelError):
        book.add_regime_comparison_panel(panel)


def test_book_unknown_regime_panel_raises():
    book = DisplayTimelineBook()
    with pytest.raises(UnknownRegimeComparisonPanelError):
        book.get_regime_comparison_panel("missing")


# ---------------------------------------------------------------------------
# v1.17.3 — Event annotation + causal timeline helpers
# ---------------------------------------------------------------------------


from dataclasses import dataclass as _dc  # noqa: E402

from world.display_timeline import (  # noqa: E402
    build_causal_timeline_annotations_from_closed_loop_data,
    build_event_annotations_from_closed_loop_data,
)


@_dc
class _FakeEnv:
    environment_state_id: str
    as_of_date: str
    overall_market_access_label: str = "open_or_constructive"
    credit_regime: str = "neutral"
    liquidity_regime: str = "normal"
    funding_regime: str = "normal"
    volatility_regime: str = "calm"
    risk_appetite_regime: str = "balanced"
    rate_environment: str = "neutral"
    refinancing_window: str = "open"
    equity_valuation_regime: str = "neutral"


@_dc
class _FakePressure:
    market_pressure_id: str
    as_of_date: str
    market_access_label: str = "open"
    liquidity_pressure_label: str = "normal"
    financing_relevance_label: str = "neutral_for_financing"
    source_market_environment_state_ids: tuple[str, ...] = ()


@_dc
class _FakeFinancingPath:
    financing_path_id: str
    as_of_date: str
    firm_id: str = "firm:test"
    constraint_label: str = "no_obvious_constraint"
    coherence_label: str = "coherent"
    indicative_market_pressure_ids: tuple[str, ...] = ()


@_dc
class _FakeAttention:
    attention_state_id: str
    as_of_date: str
    actor_id: str = "investor:test"
    focus_labels: tuple[str, ...] = ()
    source_indicative_market_pressure_ids: tuple[str, ...] = ()
    source_corporate_financing_path_ids: tuple[str, ...] = ()


def test_event_helper_market_environment_change_fires_on_selective_or_constrained():
    env = _FakeEnv(
        environment_state_id="market_environment:test:2026-03-31",
        as_of_date="2026-03-31",
        overall_market_access_label="selective_or_constrained",
        credit_regime="tightening",
        funding_regime="expensive",
    )
    annotations = build_event_annotations_from_closed_loop_data(
        market_environment_states=(env,)
    )
    matching = [
        a for a in annotations
        if a.annotation_type_label == "market_environment_change"
    ]
    assert len(matching) == 1
    a = matching[0]
    assert a.annotation_date == "2026-03-31"
    assert a.severity_label == "medium"
    assert a.source_record_ids == (env.environment_state_id,)
    # Subfield differentiators land in metadata + label.
    assert a.metadata["credit_regime"] == "tightening"
    assert a.metadata["funding_regime"] == "expensive"
    assert "credit=tightening" in a.annotation_label
    assert "funding=expensive" in a.annotation_label


def test_event_helper_market_environment_change_does_not_fire_on_open():
    env = _FakeEnv(
        environment_state_id="market_environment:test:2026-03-31",
        as_of_date="2026-03-31",
        overall_market_access_label="open_or_constructive",
    )
    annotations = build_event_annotations_from_closed_loop_data(
        market_environment_states=(env,)
    )
    assert not any(
        a.annotation_type_label == "market_environment_change"
        for a in annotations
    )


def test_event_helper_market_pressure_change_fires_on_constrained():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="constrained",
        liquidity_pressure_label="tight",
        financing_relevance_label="adverse_for_market_access",
    )
    annotations = build_event_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    matching = [
        a for a in annotations
        if a.annotation_type_label == "market_pressure_change"
    ]
    assert len(matching) == 1
    a = matching[0]
    assert a.severity_label == "medium"
    assert a.metadata["market_access_label"] == "constrained"
    assert a.metadata["liquidity_pressure_label"] == "tight"
    assert (
        a.metadata["financing_relevance_label"]
        == "adverse_for_market_access"
    )


def test_event_helper_market_pressure_change_severity_high_when_closed():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="closed",
    )
    annotations = build_event_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    matching = [
        a for a in annotations
        if a.annotation_type_label == "market_pressure_change"
    ]
    assert len(matching) == 1
    assert matching[0].severity_label == "high"


def test_event_helper_market_pressure_change_does_not_fire_on_open():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="open",
    )
    annotations = build_event_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    assert not any(
        a.annotation_type_label == "market_pressure_change"
        for a in annotations
    )


def test_event_helper_financing_constraint_fires_on_market_access_constraint():
    fp = _FakeFinancingPath(
        financing_path_id="corporate_financing_path:firm:test:2026-03-31",
        as_of_date="2026-03-31",
        firm_id="firm:test",
        constraint_label="market_access_constraint",
    )
    annotations = build_event_annotations_from_closed_loop_data(
        financing_paths=(fp,)
    )
    matching = [
        a for a in annotations
        if a.annotation_type_label == "financing_constraint"
    ]
    assert len(matching) == 1
    a = matching[0]
    assert a.source_record_ids == (fp.financing_path_id,)
    assert a.metadata["firm_id"] == "firm:test"


def test_event_helper_financing_coherence_conflict_emits_causal_checkpoint():
    fp = _FakeFinancingPath(
        financing_path_id="corporate_financing_path:firm:test:2026-03-31",
        as_of_date="2026-03-31",
        coherence_label="conflicting_evidence",
    )
    annotations = build_event_annotations_from_closed_loop_data(
        financing_paths=(fp,)
    )
    matching = [
        a for a in annotations
        if a.annotation_type_label == "causal_checkpoint"
    ]
    assert len(matching) == 1
    assert (
        matching[0].metadata["coherence_label"] == "conflicting_evidence"
    )


def test_event_helper_attention_shift_fires_on_v1_16_3_focus_label():
    s = _FakeAttention(
        attention_state_id="attention_state:investor:test:2026-03-31",
        as_of_date="2026-03-31",
        focus_labels=("memory", "risk", "market_access"),
    )
    annotations = build_event_annotations_from_closed_loop_data(
        attention_states=(s,)
    )
    matching = [
        a for a in annotations
        if a.annotation_type_label == "attention_shift"
    ]
    assert len(matching) == 1
    a = matching[0]
    assert a.severity_label == "low"
    # Sorted v1.16.3 fresh labels in metadata.
    assert a.metadata["v1_16_3_focus_present"] == [
        "market_access",
        "risk",
    ]


def test_event_helper_attention_shift_does_not_fire_on_v1_12_8_focus_only():
    s = _FakeAttention(
        attention_state_id="attention_state:investor:test:2026-03-31",
        as_of_date="2026-03-31",
        focus_labels=("memory", "engagement", "dialogue"),
    )
    annotations = build_event_annotations_from_closed_loop_data(
        attention_states=(s,)
    )
    assert not any(
        a.annotation_type_label == "attention_shift"
        for a in annotations
    )


def test_event_helper_deterministic_same_inputs_byte_identical():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="constrained",
    )
    fp = _FakeFinancingPath(
        financing_path_id="corporate_financing_path:firm:test:2026-03-31",
        as_of_date="2026-03-31",
        constraint_label="market_access_constraint",
    )
    a = build_event_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,),
        financing_paths=(fp,),
    )
    b = build_event_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,),
        financing_paths=(fp,),
    )
    assert tuple(x.to_dict() for x in a) == tuple(
        x.to_dict() for x in b
    )


def test_event_helper_skips_records_with_missing_id_or_date():
    bad_pressure = _FakePressure(
        market_pressure_id="",
        as_of_date="2026-03-31",
        market_access_label="constrained",
    )
    annotations = build_event_annotations_from_closed_loop_data(
        indicative_market_pressures=(bad_pressure,)
    )
    assert annotations == ()


def test_causal_helper_env_to_pressure_fires_on_constrained():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="constrained",
        source_market_environment_state_ids=(
            "market_environment:test:2026-03-31",
        ),
    )
    causals = build_causal_timeline_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    env_to_pressure = [
        c for c in causals
        if c.causal_summary_label == "market_pressure_change"
    ]
    assert len(env_to_pressure) == 1
    c = env_to_pressure[0]
    assert c.source_record_ids == (
        "market_environment:test:2026-03-31",
    )
    assert c.downstream_record_ids == (pressure.market_pressure_id,)


def test_causal_helper_env_to_pressure_skips_when_open():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="open",
        source_market_environment_state_ids=(
            "market_environment:test:2026-03-31",
        ),
    )
    causals = build_causal_timeline_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    assert causals == ()


def test_causal_helper_pressure_to_financing_fires_on_market_access_constraint():
    fp = _FakeFinancingPath(
        financing_path_id="corporate_financing_path:firm:test:2026-06-30",
        as_of_date="2026-06-30",
        firm_id="firm:test",
        constraint_label="market_access_constraint",
        indicative_market_pressure_ids=(
            "indicative_market_pressure:firm:test:2026-03-31",
        ),
    )
    causals = build_causal_timeline_annotations_from_closed_loop_data(
        financing_paths=(fp,)
    )
    matching = [
        c for c in causals
        if c.causal_summary_label == "financing_constraint"
    ]
    assert len(matching) == 1
    c = matching[0]
    assert c.source_record_ids == (
        "indicative_market_pressure:firm:test:2026-03-31",
    )
    assert c.downstream_record_ids == (fp.financing_path_id,)
    assert c.affected_actor_ids == ("firm:test",)


def test_causal_helper_prior_to_attention_fires_when_pressure_cited_and_focus_widened():
    s = _FakeAttention(
        attention_state_id="attention_state:investor:test:2026-06-30",
        as_of_date="2026-06-30",
        actor_id="investor:test",
        focus_labels=("memory", "risk"),
        source_indicative_market_pressure_ids=(
            "indicative_market_pressure:firm:test:2026-03-31",
        ),
    )
    causals = build_causal_timeline_annotations_from_closed_loop_data(
        attention_states=(s,)
    )
    matching = [
        c for c in causals
        if c.causal_summary_label == "attention_shift"
    ]
    assert len(matching) == 1
    c = matching[0]
    assert c.source_record_ids == (
        "indicative_market_pressure:firm:test:2026-03-31",
    )
    assert c.downstream_record_ids == (s.attention_state_id,)
    assert c.affected_actor_ids == ("investor:test",)


def test_causal_helper_prior_to_attention_skips_without_v1_16_3_focus():
    s = _FakeAttention(
        attention_state_id="attention_state:investor:test:2026-06-30",
        as_of_date="2026-06-30",
        focus_labels=("memory",),
        source_indicative_market_pressure_ids=(
            "indicative_market_pressure:firm:test:2026-03-31",
        ),
    )
    causals = build_causal_timeline_annotations_from_closed_loop_data(
        attention_states=(s,)
    )
    assert causals == ()


def test_causal_helper_deterministic():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="constrained",
        source_market_environment_state_ids=(
            "market_environment:test:2026-03-31",
        ),
    )
    a = build_causal_timeline_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    b = build_causal_timeline_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    assert tuple(x.to_dict() for x in a) == tuple(
        x.to_dict() for x in b
    )


def test_named_regime_panel_accepts_event_and_causal_annotations():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="constrained",
    )
    events = build_event_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    panel = build_named_regime_panel(
        regime_id="constrained",
        event_annotations=events,
    )
    assert panel.event_annotations == events
    assert panel.causal_annotations == ()


def test_named_regime_panel_rejects_non_event_annotation_in_event_slot():
    with pytest.raises(ValueError):
        build_named_regime_panel(
            regime_id="constrained",
            event_annotations=("not an event",),  # type: ignore[arg-type]
        )


def test_named_regime_panel_rejects_non_causal_annotation_in_causal_slot():
    with pytest.raises(ValueError):
        build_named_regime_panel(
            regime_id="constrained",
            causal_annotations=("not a causal",),  # type: ignore[arg-type]
        )


def test_named_regime_panel_to_dict_includes_event_and_causal_annotations():
    fp = _FakeFinancingPath(
        financing_path_id="corporate_financing_path:firm:test:2026-03-31",
        as_of_date="2026-03-31",
        constraint_label="market_access_constraint",
    )
    events = build_event_annotations_from_closed_loop_data(
        financing_paths=(fp,)
    )
    panel = build_named_regime_panel(
        regime_id="constrained",
        event_annotations=events,
    )
    payload = panel.to_dict()
    assert "event_annotations" in payload
    assert "causal_annotations" in payload
    assert len(payload["event_annotations"]) == 1


def test_regime_comparison_markdown_renders_event_section_when_present():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="constrained",
        source_market_environment_state_ids=(
            "market_environment:test:2026-03-31",
        ),
    )
    events = build_event_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    causals = build_causal_timeline_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(
            build_named_regime_panel(
                regime_id="constrained",
                event_annotations=events,
                causal_annotations=causals,
            ),
            build_named_regime_panel(regime_id="constructive"),
        ),
    )
    md = render_regime_comparison_markdown(panel)
    assert "Event annotations (by type)" in md
    assert "Top events (date · type · source)" in md
    assert "Causal arrows (by kind)" in md
    assert "constrained — events & causal trace" in md
    assert "market_pressure_change" in md
    assert "Causal arrows:" in md


def test_regime_comparison_markdown_skips_event_section_when_absent():
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(
            build_named_regime_panel(regime_id="constrained"),
            build_named_regime_panel(regime_id="constructive"),
        ),
    )
    md = render_regime_comparison_markdown(panel)
    assert "Event annotations (by type)" not in md
    assert "events & causal trace" not in md


def test_regime_comparison_markdown_with_events_no_forbidden_display_names():
    pressure = _FakePressure(
        market_pressure_id="indicative_market_pressure:test:2026-03-31",
        as_of_date="2026-03-31",
        market_access_label="constrained",
    )
    events = build_event_annotations_from_closed_loop_data(
        indicative_market_pressures=(pressure,)
    )
    panel = build_regime_comparison_panel(
        panel_id="regime_comparison:test",
        regime_panels=(
            build_named_regime_panel(
                regime_id="constrained",
                event_annotations=events,
            ),
        ),
    )
    md = render_regime_comparison_markdown(panel).lower()
    for forbidden in FORBIDDEN_DISPLAY_NAMES:
        assert forbidden not in md, (
            f"forbidden display name {forbidden!r} in event-enriched markdown"
        )
