"""
v1.26.2 — ReportingCalendarProfile storage pin tests.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES,
)
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.reporting_calendar_profiles import (
    DISCLOSURE_CLUSTER_LABELS,
    DuplicateReportingCalendarProfileError,
    MONTH_LABELS,
    QUARTERLY_REPORTING_MONTHS_MAX_LEN,
    REPORTING_INTENSITY_LABELS,
    ReportingCalendarProfile,
    ReportingCalendarProfileBook,
)
from world.scheduler import Scheduler
from world.state import State

from _canonical_digests import (
    MONTHLY_REFERENCE_LIVING_WORLD_DIGEST,
    QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
    SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST,
)


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _profile(
    *,
    reporting_calendar_profile_id: str = "rcp:test:01",
    entity_id: str = "firm:test_a",
    fiscal_year_end_month_label: str = "month_03",
    quarterly_reporting_month_labels: tuple[str, ...] = (
        "month_03",
        "month_06",
        "month_09",
        "month_12",
    ),
    disclosure_cluster_label: str = "moderate",
    reporting_intensity_label: str = "medium",
    metadata: dict | None = None,
) -> ReportingCalendarProfile:
    return ReportingCalendarProfile(
        reporting_calendar_profile_id=(
            reporting_calendar_profile_id
        ),
        entity_id=entity_id,
        fiscal_year_end_month_label=(
            fiscal_year_end_month_label
        ),
        quarterly_reporting_month_labels=(
            quarterly_reporting_month_labels
        ),
        disclosure_cluster_label=disclosure_cluster_label,
        reporting_intensity_label=reporting_intensity_label,
        metadata=metadata or {},
    )


def test_reporting_calendar_profile_validates_required_fields() -> None:
    p = _profile()
    assert p.reporting_calendar_profile_id == "rcp:test:01"
    with pytest.raises(ValueError):
        _profile(reporting_calendar_profile_id="")
    with pytest.raises(ValueError):
        _profile(entity_id="")
    for flag in (
        "no_real_data_ingestion",
        "no_japan_calibration",
        "no_real_company_name",
        "no_event_to_price_mapping",
        "no_market_effect_inference",
        "descriptive_only",
    ):
        assert p.boundary_flags[flag] is True


def test_reporting_calendar_profile_validates_month_labels() -> None:
    for forbidden in (
        "Q1", "01", "January", "month_13", "month_00",
    ):
        with pytest.raises(ValueError):
            _profile(fiscal_year_end_month_label=forbidden)
    for label in MONTH_LABELS:
        if label == "unknown":
            continue
        rec = _profile(
            reporting_calendar_profile_id=f"rcp:test:{label}",
            fiscal_year_end_month_label=label,
        )
        assert rec.fiscal_year_end_month_label == label
    # Closed-set labels for cluster + intensity.
    for label in DISCLOSURE_CLUSTER_LABELS:
        rec = _profile(
            reporting_calendar_profile_id=f"rcp:test:{label}",
            disclosure_cluster_label=label,
        )
        assert rec.disclosure_cluster_label == label
    for label in REPORTING_INTENSITY_LABELS:
        rec = _profile(
            reporting_calendar_profile_id=(
                f"rcp:test:int:{label}"
            ),
            reporting_intensity_label=label,
        )
        assert rec.reporting_intensity_label == label


def test_reporting_calendar_profile_rejects_duplicate_quarterly_months() -> None:
    with pytest.raises(ValueError):
        _profile(
            quarterly_reporting_month_labels=(
                "month_03",
                "month_03",
            ),
        )


def test_reporting_calendar_profile_rejects_too_many_quarterly_months() -> None:
    overlong = (
        "month_01",
        "month_04",
        "month_07",
        "month_10",
        "month_12",
    )
    assert len(overlong) > QUARTERLY_REPORTING_MONTHS_MAX_LEN
    with pytest.raises(ValueError):
        _profile(quarterly_reporting_month_labels=overlong)


def test_reporting_calendar_profile_rejects_forbidden_field_names() -> None:
    from dataclasses import fields as dc_fields
    field_names = {
        f.name for f in dc_fields(ReportingCalendarProfile)
    }
    overlap = (
        field_names
        & FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES
    )
    assert overlap == set()


def test_reporting_calendar_profile_rejects_forbidden_metadata_keys() -> None:
    for forbidden in (
        "earnings_surprise",
        "edinet",
        "tdnet",
        "j_quants",
        "fsa_filing",
        "universe_weight",
        "rebalance_event",
        "buy",
        "forecast",
        "alpha",
        "performance",
        "japan_calibration",
        "amplify",
        "auto_annotation",
    ):
        with pytest.raises(ValueError):
            _profile(metadata={forbidden: "x"})


def test_reporting_calendar_profile_book_add_get_list_snapshot() -> None:
    book = ReportingCalendarProfileBook()
    a = _profile(
        reporting_calendar_profile_id="rcp:a",
        entity_id="firm:a",
        fiscal_year_end_month_label="month_03",
    )
    b = _profile(
        reporting_calendar_profile_id="rcp:b",
        entity_id="firm:b",
        fiscal_year_end_month_label="month_12",
        quarterly_reporting_month_labels=(),
    )
    book.add_profile(a)
    book.add_profile(b)
    assert book.get_profile("rcp:a") is a
    assert len(book.list_profiles()) == 2
    snap = book.snapshot()
    assert "reporting_calendar_profiles" in snap
    assert len(snap["reporting_calendar_profiles"]) == 2


def test_reporting_calendar_profile_list_by_entity_and_fiscal_year_end_month() -> None:
    book = ReportingCalendarProfileBook()
    a = _profile(
        reporting_calendar_profile_id="rcp:a",
        entity_id="firm:a",
        fiscal_year_end_month_label="month_03",
        quarterly_reporting_month_labels=("month_03",),
    )
    b = _profile(
        reporting_calendar_profile_id="rcp:b",
        entity_id="firm:b",
        fiscal_year_end_month_label="month_12",
        quarterly_reporting_month_labels=("month_06",),
    )
    book.add_profile(a)
    book.add_profile(b)
    assert {p.reporting_calendar_profile_id for p in book.list_by_entity("firm:a")} == {"rcp:a"}
    assert {p.reporting_calendar_profile_id for p in book.list_by_fiscal_year_end_month("month_03")} == {"rcp:a"}
    assert {p.reporting_calendar_profile_id for p in book.list_by_reporting_month("month_06")} == {"rcp:b"}
    assert book.list_by_reporting_month("month_07") == ()


def test_duplicate_reporting_calendar_profile_emits_no_extra_ledger_record() -> None:
    kernel = _bare_kernel()
    p = _profile()
    kernel.reporting_calendars.add_profile(p)
    n = len(kernel.ledger.records)
    assert n >= 1
    assert kernel.ledger.records[-1].event_type == RecordType.REPORTING_CALENDAR_PROFILE_RECORDED.value
    with pytest.raises(DuplicateReportingCalendarProfileError):
        kernel.reporting_calendars.add_profile(p)
    assert len(kernel.ledger.records) == n


def test_world_kernel_reporting_calendars_empty_by_default() -> None:
    kernel = _bare_kernel()
    assert kernel.reporting_calendars.list_profiles() == ()
    types = {r.event_type for r in kernel.ledger.records}
    assert RecordType.REPORTING_CALENDAR_PROFILE_RECORDED.value not in types


def test_reporting_calendar_storage_does_not_mutate_source_of_truth_books() -> None:
    kernel = _bare_kernel()
    snap_before = {
        "scenario_drivers": kernel.scenario_drivers.snapshot(),
        "scenario_applications": kernel.scenario_applications.snapshot(),
        "stress_applications": kernel.stress_applications.snapshot(),
        "manual_annotations": kernel.manual_annotations.snapshot(),
        "investor_mandates": kernel.investor_mandates.snapshot(),
        "universe_events": kernel.universe_events.snapshot(),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
    }
    kernel.reporting_calendars.add_profile(_profile())
    snap_after = {
        "scenario_drivers": kernel.scenario_drivers.snapshot(),
        "scenario_applications": kernel.scenario_applications.snapshot(),
        "stress_applications": kernel.stress_applications.snapshot(),
        "manual_annotations": kernel.manual_annotations.snapshot(),
        "investor_mandates": kernel.investor_mandates.snapshot(),
        "universe_events": kernel.universe_events.snapshot(),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
    }
    assert snap_before == snap_after


def test_existing_digests_unchanged_with_empty_reporting_calendar_book() -> None:
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _run_default,
        _run_monthly_reference,
        _seed_kernel,
    )
    from test_living_reference_world_performance_boundary import (
        _run_v1_20_3,
        _seed_v1_20_3_kernel,
    )

    k_q = _seed_kernel()
    r_q = _run_default(k_q)
    assert k_q.reporting_calendars.list_profiles() == ()
    assert living_world_digest(k_q, r_q) == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST

    k_m = _seed_kernel()
    r_m = _run_monthly_reference(k_m)
    assert living_world_digest(k_m, r_m) == MONTHLY_REFERENCE_LIVING_WORLD_DIGEST

    k_s = _seed_v1_20_3_kernel()
    r_s = _run_v1_20_3(k_s)
    assert living_world_digest(k_s, r_s) == SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST
