"""
Tests for v1.20.2 scenario-schedule storage —
``world.scenario_schedule``.

Pinned invariants:

- six closed-set vocabularies (``RUN_PROFILE_LABELS``,
  ``SCHEDULE_POLICY_LABELS``, ``APPLICATION_POLICY_LABELS``,
  ``SCHEDULED_MONTH_LABELS``, ``STATUS_LABELS``,
  ``VISIBILITY_LABELS``);
- v1.20.0 hard naming boundary
  (``FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES``) disjoint from
  every closed-set vocabulary; dataclass field names disjoint;
  payload + metadata keys rejected at construction;
- frozen dataclasses with strict construction-time validation;
- ``scheduled_period_index`` validation: rejects ``bool``,
  rejects negatives, rejects values > 11;
- duplicate id rejected on every add (no extra ledger record);
- unknown lookup raises;
- every list / filter method returns the right subset;
- snapshot determinism;
- ledger emits exactly one record per add;
- kernel wiring (``WorldKernel.scenario_schedule``);
- empty book does **not** move ``quarterly_default``
  (`f93bdf3f…b705897c`) or `monthly_reference`
  (`75a91cfa…91879d`) digest;
- :func:`build_default_scenario_monthly_schedule` produces
  exactly one schedule + one scheduled application at month_04
  / period index 3, with ``credit_tightening_driver`` on the
  ``generic_11_sector`` universe; does **not** auto-register;
- references stored as plain ids (no resolution at storage
  level);
- no ``PriceBook`` / source-of-truth book mutation;
- jurisdiction-neutral identifier scan + licensed-taxonomy
  scan over module + test text.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scenario_schedule import (
    APPLICATION_POLICY_LABELS,
    DuplicateScenarioScheduleError,
    DuplicateScheduledScenarioApplicationError,
    FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES,
    MONTHLY_PERIOD_INDEX_MAX,
    MONTHLY_PERIOD_INDEX_MIN,
    RUN_PROFILE_LABELS,
    SCHEDULED_MONTH_LABELS,
    SCHEDULE_POLICY_LABELS,
    STATUS_LABELS,
    ScenarioSchedule,
    ScenarioScheduleBook,
    ScheduledScenarioApplication,
    UnknownScenarioScheduleError,
    UnknownScheduledScenarioApplicationError,
    VISIBILITY_LABELS,
    build_default_scenario_monthly_schedule,
)
from world.scheduler import Scheduler
from world.state import State


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "world"
    / "scenario_schedule.py"
)


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


def test_run_profile_labels_closed_set():
    assert RUN_PROFILE_LABELS == frozenset(
        {
            "scenario_monthly_reference_universe",
            "monthly_reference",
            "scenario_monthly",
            "quarterly_default",
            "unknown",
        }
    )


def test_schedule_policy_labels_closed_set():
    assert SCHEDULE_POLICY_LABELS == frozenset(
        {
            "single_scenario",
            "multi_scenario_bounded",
            "display_only",
            "inactive",
            "unknown",
        }
    )


def test_application_policy_labels_closed_set():
    assert APPLICATION_POLICY_LABELS == frozenset(
        {
            "apply_at_period_start",
            "apply_before_information_arrivals",
            "apply_after_information_arrivals",
            "apply_before_attention_update",
            "display_only",
            "unknown",
        }
    )


def test_scheduled_month_labels_closed_set():
    assert SCHEDULED_MONTH_LABELS == frozenset(
        {
            "month_01",
            "month_02",
            "month_03",
            "month_04",
            "month_05",
            "month_06",
            "month_07",
            "month_08",
            "month_09",
            "month_10",
            "month_11",
            "month_12",
            "unknown",
        }
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
        {
            "public",
            "restricted",
            "internal",
            "private",
            "unknown",
        }
    )


def test_monthly_period_index_bounds():
    assert MONTHLY_PERIOD_INDEX_MIN == 0
    assert MONTHLY_PERIOD_INDEX_MAX == 11


# ---------------------------------------------------------------------------
# Forbidden field-name boundary
# ---------------------------------------------------------------------------


_V1_20_0_PINNED_FORBIDDEN_NAMES = (
    "firm_decision",
    "investor_action",
    "bank_approval",
    "trading_decision",
    "optimal_capital_structure",
    "buy",
    "sell",
    "order",
    "trade",
    "execution",
    "price",
    "market_price",
    "predicted_index",
    "forecast_path",
    "expected_return",
    "target_price",
    "recommendation",
    "investment_advice",
    "real_data_value",
    "japan_calibration",
    "llm_output",
    "llm_prose",
    "prompt_text",
    "real_company_name",
    "real_sector_weight",
    "gics",
    "msci",
    "factset",
    "bloomberg",
    "refinitiv",
    "topix",
    "nikkei",
    "jpx",
)


def test_forbidden_field_names_includes_v1_20_0_pinned_set():
    pinned = set(_V1_20_0_PINNED_FORBIDDEN_NAMES)
    assert pinned <= FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES


def test_forbidden_field_names_disjoint_from_every_closed_set():
    for vocab in (
        RUN_PROFILE_LABELS,
        SCHEDULE_POLICY_LABELS,
        APPLICATION_POLICY_LABELS,
        SCHEDULED_MONTH_LABELS,
        STATUS_LABELS,
        VISIBILITY_LABELS,
    ):
        assert not (
            FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES & vocab
        )


def test_dataclass_field_names_disjoint_from_forbidden():
    for cls in (
        ScenarioSchedule,
        ScheduledScenarioApplication,
    ):
        fields = set(cls.__dataclass_fields__.keys())
        assert not (
            fields & FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES
        ), f"{cls.__name__} has a forbidden field name"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schedule(
    *,
    scenario_schedule_id: str = "scenario_schedule:test:1",
    run_profile_label: str = (
        "scenario_monthly_reference_universe"
    ),
    reference_universe_id: str = (
        "reference_universe:generic_11_sector"
    ),
    scenario_driver_template_ids: tuple[str, ...] = (
        "scenario_driver:credit_tightening:reference",
    ),
    scheduled_month_labels: tuple[str, ...] = ("month_04",),
    scheduled_period_indices: tuple[int, ...] = (3,),
    schedule_policy_label: str = "single_scenario",
    status: str = "active",
    visibility: str = "internal",
    metadata: dict | None = None,
) -> ScenarioSchedule:
    return ScenarioSchedule(
        scenario_schedule_id=scenario_schedule_id,
        run_profile_label=run_profile_label,
        reference_universe_id=reference_universe_id,
        scenario_driver_template_ids=(
            scenario_driver_template_ids
        ),
        scheduled_month_labels=scheduled_month_labels,
        scheduled_period_indices=scheduled_period_indices,
        schedule_policy_label=schedule_policy_label,
        status=status,
        visibility=visibility,
        metadata=metadata or {},
    )


def _application(
    *,
    scheduled_scenario_application_id: str = (
        "scheduled_scenario_application:test:1:m04"
    ),
    scenario_schedule_id: str = "scenario_schedule:test:1",
    scenario_driver_template_id: str = (
        "scenario_driver:credit_tightening:reference"
    ),
    scheduled_period_index: int = 3,
    scheduled_month_label: str = "month_04",
    application_policy_label: str = (
        "apply_after_information_arrivals"
    ),
    affected_reference_universe_id: str = (
        "reference_universe:generic_11_sector"
    ),
    affected_sector_ids: tuple[str, ...] = (),
    affected_firm_profile_ids: tuple[str, ...] = (),
    status: str = "active",
    visibility: str = "internal",
    metadata: dict | None = None,
) -> ScheduledScenarioApplication:
    return ScheduledScenarioApplication(
        scheduled_scenario_application_id=(
            scheduled_scenario_application_id
        ),
        scenario_schedule_id=scenario_schedule_id,
        scenario_driver_template_id=(
            scenario_driver_template_id
        ),
        scheduled_period_index=scheduled_period_index,
        scheduled_month_label=scheduled_month_label,
        application_policy_label=application_policy_label,
        affected_reference_universe_id=(
            affected_reference_universe_id
        ),
        affected_sector_ids=affected_sector_ids,
        affected_firm_profile_ids=affected_firm_profile_ids,
        status=status,
        visibility=visibility,
        metadata=metadata or {},
    )


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


# ---------------------------------------------------------------------------
# ScenarioSchedule field validation
# ---------------------------------------------------------------------------


def test_schedule_accepts_minimal_required_fields():
    s = _schedule()
    assert s.scenario_schedule_id == "scenario_schedule:test:1"
    assert s.run_profile_label == (
        "scenario_monthly_reference_universe"
    )
    assert s.schedule_policy_label == "single_scenario"
    assert s.status == "active"


def test_schedule_rejects_empty_id():
    with pytest.raises(ValueError):
        _schedule(scenario_schedule_id="")


def test_schedule_rejects_empty_reference_universe_id():
    with pytest.raises(ValueError):
        _schedule(reference_universe_id="")


def test_schedule_rejects_unknown_run_profile_label():
    with pytest.raises(ValueError):
        _schedule(run_profile_label="hourly_simulation")


def test_schedule_rejects_unknown_schedule_policy_label():
    with pytest.raises(ValueError):
        _schedule(schedule_policy_label="ad_hoc")


def test_schedule_rejects_unknown_status():
    with pytest.raises(ValueError):
        _schedule(status="committed_for_audit")


def test_schedule_rejects_unknown_visibility():
    with pytest.raises(ValueError):
        _schedule(visibility="public_marketing")


def test_schedule_rejects_unknown_scheduled_month_label():
    with pytest.raises(ValueError):
        _schedule(scheduled_month_labels=("month_13",))


def test_schedule_rejects_negative_period_index_in_tuple():
    with pytest.raises(ValueError):
        _schedule(scheduled_period_indices=(-1,))


def test_schedule_rejects_period_index_above_11_in_tuple():
    with pytest.raises(ValueError):
        _schedule(scheduled_period_indices=(12,))


def test_schedule_rejects_bool_period_index_in_tuple():
    with pytest.raises(ValueError):
        _schedule(
            scheduled_period_indices=(True,)  # type: ignore[arg-type]
        )


def test_schedule_rejects_empty_string_in_template_ids():
    with pytest.raises(ValueError):
        _schedule(scenario_driver_template_ids=("",))


def test_schedule_rejects_metadata_with_forbidden_key():
    with pytest.raises(ValueError):
        _schedule(metadata={"target_price": 1.0})


def test_schedule_rejects_metadata_with_real_company_name_key():
    with pytest.raises(ValueError):
        _schedule(metadata={"real_company_name": "X"})


def test_schedule_rejects_metadata_with_real_sector_weight_key():
    with pytest.raises(ValueError):
        _schedule(metadata={"real_sector_weight": 0.05})


# ---------------------------------------------------------------------------
# ScheduledScenarioApplication field validation
# ---------------------------------------------------------------------------


def test_application_accepts_minimal_required_fields():
    a = _application()
    assert a.scheduled_scenario_application_id == (
        "scheduled_scenario_application:test:1:m04"
    )
    assert a.scheduled_period_index == 3
    assert a.scheduled_month_label == "month_04"
    assert a.application_policy_label == (
        "apply_after_information_arrivals"
    )


def test_application_rejects_empty_id():
    with pytest.raises(ValueError):
        _application(scheduled_scenario_application_id="")


def test_application_rejects_empty_template_id():
    with pytest.raises(ValueError):
        _application(scenario_driver_template_id="")


def test_application_rejects_unknown_scheduled_month_label():
    with pytest.raises(ValueError):
        _application(scheduled_month_label="month_13")


def test_application_rejects_unknown_application_policy_label():
    with pytest.raises(ValueError):
        _application(application_policy_label="autopilot")


def test_application_rejects_negative_period_index():
    with pytest.raises(ValueError):
        _application(scheduled_period_index=-1)


def test_application_rejects_period_index_above_11():
    with pytest.raises(ValueError):
        _application(scheduled_period_index=12)


def test_application_rejects_bool_period_index():
    """``bool`` is a subclass of ``int``; the dataclass must
    reject it explicitly."""
    with pytest.raises(ValueError):
        _application(
            scheduled_period_index=True  # type: ignore[arg-type]
        )


def test_application_rejects_string_period_index():
    with pytest.raises(ValueError):
        _application(
            scheduled_period_index="3"  # type: ignore[arg-type]
        )


def test_application_accepts_period_index_zero():
    a = _application(
        scheduled_period_index=0,
        scheduled_month_label="month_01",
    )
    assert a.scheduled_period_index == 0


def test_application_accepts_period_index_eleven():
    a = _application(
        scheduled_period_index=11,
        scheduled_month_label="month_12",
    )
    assert a.scheduled_period_index == 11


def test_application_rejects_metadata_with_llm_prose_key():
    with pytest.raises(ValueError):
        _application(metadata={"llm_prose": "the bank should approve"})


def test_application_rejects_metadata_with_real_company_name_key():
    with pytest.raises(ValueError):
        _application(metadata={"real_company_name": "X"})


def test_application_accepts_empty_affected_id_tuples():
    a = _application(
        affected_sector_ids=(),
        affected_firm_profile_ids=(),
    )
    assert a.affected_sector_ids == ()
    assert a.affected_firm_profile_ids == ()


def test_application_rejects_empty_string_in_affected_sectors():
    with pytest.raises(ValueError):
        _application(affected_sector_ids=("",))


def test_application_rejects_empty_string_in_affected_firm_profiles():
    with pytest.raises(ValueError):
        _application(affected_firm_profile_ids=("",))


def test_application_accepts_plain_id_citations_without_resolution():
    """v1.20.2 is storage-only — references are plain ids; the
    storage layer does not check that the cited records exist
    (v1.20.3 will validate at run time)."""
    a = _application(
        scenario_driver_template_id=(
            "scenario_driver:nonexistent:fictional"
        ),
        affected_reference_universe_id=(
            "reference_universe:nonexistent"
        ),
        affected_sector_ids=("sector:nonexistent:abc",),
        affected_firm_profile_ids=(
            "firm_profile:firm:nonexistent_a",
        ),
    )
    assert a.scenario_driver_template_id == (
        "scenario_driver:nonexistent:fictional"
    )


# ---------------------------------------------------------------------------
# Immutability + to_dict
# ---------------------------------------------------------------------------


def test_schedule_is_immutable():
    s = _schedule()
    with pytest.raises(Exception):
        s.scenario_schedule_id = "x"  # type: ignore[misc]


def test_application_is_immutable():
    a = _application()
    with pytest.raises(Exception):
        a.scheduled_scenario_application_id = "x"  # type: ignore[misc]


def test_to_dict_round_trip_byte_identical():
    a = _schedule()
    b = _schedule()
    assert a.to_dict() == b.to_dict()
    a = _application()
    b = _application()
    assert a.to_dict() == b.to_dict()


def test_to_dict_keys_disjoint_from_forbidden_for_each_class():
    for to_dict in (_schedule().to_dict(), _application().to_dict()):
        assert not (
            set(to_dict.keys())
            & FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES
        )
        assert not (
            set(to_dict["metadata"].keys())
            & FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES
        )


# ---------------------------------------------------------------------------
# ScenarioScheduleBook — schedule
# ---------------------------------------------------------------------------


def test_book_add_get_list_schedule():
    book = ScenarioScheduleBook()
    s = _schedule()
    book.add_schedule(s)
    assert book.get_schedule(s.scenario_schedule_id) is s
    assert book.list_schedules() == (s,)


def test_book_duplicate_schedule_id_raises():
    book = ScenarioScheduleBook()
    book.add_schedule(_schedule())
    with pytest.raises(DuplicateScenarioScheduleError):
        book.add_schedule(_schedule())


def test_book_unknown_schedule_id_raises():
    book = ScenarioScheduleBook()
    with pytest.raises(UnknownScenarioScheduleError):
        book.get_schedule("missing")


def test_book_list_schedules_by_run_profile():
    book = ScenarioScheduleBook()
    a = _schedule(
        scenario_schedule_id="scenario_schedule:smru:1",
        run_profile_label=(
            "scenario_monthly_reference_universe"
        ),
    )
    b = _schedule(
        scenario_schedule_id="scenario_schedule:mr:1",
        run_profile_label="monthly_reference",
    )
    book.add_schedule(a)
    book.add_schedule(b)
    assert book.list_by_run_profile(
        "scenario_monthly_reference_universe"
    ) == (a,)
    assert book.list_by_run_profile("monthly_reference") == (b,)


def test_book_list_schedules_by_reference_universe():
    book = ScenarioScheduleBook()
    a = _schedule(
        scenario_schedule_id="scenario_schedule:gen11:1",
        reference_universe_id=(
            "reference_universe:generic_11_sector"
        ),
    )
    b = _schedule(
        scenario_schedule_id="scenario_schedule:tiny:1",
        reference_universe_id="reference_universe:tiny_default",
    )
    book.add_schedule(a)
    book.add_schedule(b)
    assert book.list_by_reference_universe(
        "reference_universe:generic_11_sector"
    ) == (a,)
    assert book.list_by_reference_universe(
        "reference_universe:tiny_default"
    ) == (b,)


def test_book_list_schedules_by_schedule_policy():
    book = ScenarioScheduleBook()
    a = _schedule(
        scenario_schedule_id="scenario_schedule:single:1",
        schedule_policy_label="single_scenario",
    )
    b = _schedule(
        scenario_schedule_id="scenario_schedule:multi:1",
        schedule_policy_label="multi_scenario_bounded",
    )
    book.add_schedule(a)
    book.add_schedule(b)
    assert book.list_by_schedule_policy("single_scenario") == (a,)
    assert book.list_by_schedule_policy(
        "multi_scenario_bounded"
    ) == (b,)


def test_book_list_schedules_by_status():
    book = ScenarioScheduleBook()
    a = _schedule(
        scenario_schedule_id="scenario_schedule:active:1",
        status="active",
    )
    b = _schedule(
        scenario_schedule_id="scenario_schedule:draft:1",
        status="draft",
    )
    book.add_schedule(a)
    book.add_schedule(b)
    assert book.list_by_status("active") == (a,)
    assert book.list_by_status("draft") == (b,)


# ---------------------------------------------------------------------------
# ScenarioScheduleBook — scheduled application
# ---------------------------------------------------------------------------


def test_book_add_get_list_scheduled_application():
    book = ScenarioScheduleBook()
    a = _application()
    book.add_scheduled_application(a)
    assert book.get_scheduled_application(
        a.scheduled_scenario_application_id
    ) is a
    assert book.list_scheduled_applications() == (a,)


def test_book_duplicate_scheduled_application_raises():
    book = ScenarioScheduleBook()
    book.add_scheduled_application(_application())
    with pytest.raises(DuplicateScheduledScenarioApplicationError):
        book.add_scheduled_application(_application())


def test_book_unknown_scheduled_application_raises():
    book = ScenarioScheduleBook()
    with pytest.raises(UnknownScheduledScenarioApplicationError):
        book.get_scheduled_application("missing")


def test_book_list_applications_by_schedule():
    book = ScenarioScheduleBook()
    a = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:s1:a"
        ),
        scenario_schedule_id="scenario_schedule:s1",
    )
    b = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:s2:a"
        ),
        scenario_schedule_id="scenario_schedule:s2",
    )
    book.add_scheduled_application(a)
    book.add_scheduled_application(b)
    assert book.list_applications_by_schedule(
        "scenario_schedule:s1"
    ) == (a,)
    assert book.list_applications_by_schedule(
        "scenario_schedule:s2"
    ) == (b,)


def test_book_list_applications_by_template():
    book = ScenarioScheduleBook()
    a = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:credit:a"
        ),
        scenario_driver_template_id=(
            "scenario_driver:credit_tightening:reference"
        ),
    )
    b = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:rate:a"
        ),
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
    )
    book.add_scheduled_application(a)
    book.add_scheduled_application(b)
    assert book.list_applications_by_template(
        "scenario_driver:credit_tightening:reference"
    ) == (a,)
    assert book.list_applications_by_template(
        "scenario_driver:rate_repricing:reference"
    ) == (b,)


def test_book_list_applications_by_month():
    book = ScenarioScheduleBook()
    a = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:m04"
        ),
        scheduled_period_index=3,
        scheduled_month_label="month_04",
    )
    b = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:m08"
        ),
        scheduled_period_index=7,
        scheduled_month_label="month_08",
    )
    book.add_scheduled_application(a)
    book.add_scheduled_application(b)
    assert book.list_applications_by_month("month_04") == (a,)
    assert book.list_applications_by_month("month_08") == (b,)


def test_book_list_applications_by_period_index():
    book = ScenarioScheduleBook()
    a = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:p3"
        ),
        scheduled_period_index=3,
        scheduled_month_label="month_04",
    )
    b = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:p7"
        ),
        scheduled_period_index=7,
        scheduled_month_label="month_08",
    )
    book.add_scheduled_application(a)
    book.add_scheduled_application(b)
    assert book.list_applications_by_period_index(3) == (a,)
    assert book.list_applications_by_period_index(7) == (b,)


def test_book_list_applications_by_application_policy():
    book = ScenarioScheduleBook()
    a = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:after"
        ),
        application_policy_label=(
            "apply_after_information_arrivals"
        ),
    )
    b = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:before"
        ),
        application_policy_label="apply_at_period_start",
    )
    book.add_scheduled_application(a)
    book.add_scheduled_application(b)
    assert book.list_applications_by_application_policy(
        "apply_after_information_arrivals"
    ) == (a,)
    assert book.list_applications_by_application_policy(
        "apply_at_period_start"
    ) == (b,)


def test_book_list_applications_by_reference_universe():
    book = ScenarioScheduleBook()
    a = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:gen11"
        ),
        affected_reference_universe_id=(
            "reference_universe:generic_11_sector"
        ),
    )
    b = _application(
        scheduled_scenario_application_id=(
            "scheduled_scenario_application:tiny"
        ),
        affected_reference_universe_id=(
            "reference_universe:tiny_default"
        ),
    )
    book.add_scheduled_application(a)
    book.add_scheduled_application(b)
    assert book.list_applications_by_reference_universe(
        "reference_universe:generic_11_sector"
    ) == (a,)
    assert book.list_applications_by_reference_universe(
        "reference_universe:tiny_default"
    ) == (b,)


# ---------------------------------------------------------------------------
# Snapshot determinism
# ---------------------------------------------------------------------------


def test_book_snapshot_deterministic():
    book = ScenarioScheduleBook()
    book.add_schedule(_schedule())
    book.add_scheduled_application(_application())
    snap_a = book.snapshot()
    snap_b = book.snapshot()
    assert snap_a == snap_b
    assert "scenario_schedules" in snap_a
    assert "scheduled_scenario_applications" in snap_a
    assert len(snap_a["scenario_schedules"]) == 1
    assert len(snap_a["scheduled_scenario_applications"]) == 1


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_ledger_emits_one_record_per_add_schedule():
    kernel = _bare_kernel()
    before = len(kernel.ledger.records)
    kernel.scenario_schedule.add_schedule(_schedule())
    after = len(kernel.ledger.records)
    assert after - before == 1
    record = kernel.ledger.records[-1]
    assert record.record_type == (
        RecordType.SCENARIO_SCHEDULE_RECORDED
    )


def test_ledger_emits_one_record_per_add_scheduled_application():
    kernel = _bare_kernel()
    before = len(kernel.ledger.records)
    kernel.scenario_schedule.add_scheduled_application(
        _application()
    )
    after = len(kernel.ledger.records)
    assert after - before == 1
    record = kernel.ledger.records[-1]
    assert record.record_type == (
        RecordType.SCHEDULED_SCENARIO_APPLICATION_RECORDED
    )


def test_duplicate_schedule_emits_no_extra_ledger_record():
    kernel = _bare_kernel()
    kernel.scenario_schedule.add_schedule(_schedule())
    count_after_first = len(kernel.ledger.records)
    with pytest.raises(DuplicateScenarioScheduleError):
        kernel.scenario_schedule.add_schedule(_schedule())
    assert len(kernel.ledger.records) == count_after_first


def test_duplicate_scheduled_application_emits_no_extra_ledger_record():
    kernel = _bare_kernel()
    kernel.scenario_schedule.add_scheduled_application(
        _application()
    )
    count_after_first = len(kernel.ledger.records)
    with pytest.raises(DuplicateScheduledScenarioApplicationError):
        kernel.scenario_schedule.add_scheduled_application(
            _application()
        )
    assert len(kernel.ledger.records) == count_after_first


def test_ledger_payload_keys_disjoint_from_forbidden():
    kernel = _bare_kernel()
    kernel.scenario_schedule.add_schedule(_schedule())
    kernel.scenario_schedule.add_scheduled_application(
        _application()
    )
    for record in kernel.ledger.records:
        assert not (
            set(record.payload.keys())
            & FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES
        )


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_wires_scenario_schedule_book():
    kernel = _bare_kernel()
    assert isinstance(
        kernel.scenario_schedule, ScenarioScheduleBook
    )
    assert kernel.scenario_schedule.ledger is kernel.ledger
    assert kernel.scenario_schedule.list_schedules() == ()
    assert (
        kernel.scenario_schedule.list_scheduled_applications()
        == ()
    )


# ---------------------------------------------------------------------------
# No-mutation / digest invariants
# ---------------------------------------------------------------------------


def test_add_schedule_does_not_mutate_pricebook():
    kernel = _bare_kernel()
    snap_before = kernel.prices.snapshot()
    kernel.scenario_schedule.add_schedule(_schedule())
    snap_after = kernel.prices.snapshot()
    assert snap_before == snap_after


def test_add_scheduled_application_does_not_mutate_pricebook():
    kernel = _bare_kernel()
    snap_before = kernel.prices.snapshot()
    kernel.scenario_schedule.add_scheduled_application(
        _application()
    )
    snap_after = kernel.prices.snapshot()
    assert snap_before == snap_after


def test_empty_scenario_schedule_does_not_move_quarterly_default_digest():
    """Wiring an empty ScenarioScheduleBook into WorldKernel
    must leave the ``quarterly_default`` ``living_world_digest``
    byte-identical to v1.18.last / v1.19.last / v1.20.1."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import _run_default, _seed_kernel

    k = _seed_kernel()
    r = _run_default(k)
    assert (
        living_world_digest(k, r)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )


def test_empty_scenario_schedule_does_not_move_monthly_reference_digest():
    """Wiring an empty ScenarioScheduleBook into WorldKernel
    must leave the ``monthly_reference`` ``living_world_digest``
    byte-identical to v1.19.3."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _BANK_IDS,
        _FIRM_IDS,
        _INVESTOR_IDS,
        _seed_kernel,
    )
    from world.reference_living_world import (
        run_living_reference_world,
    )

    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        profile="monthly_reference",
    )
    assert (
        living_world_digest(k, r)
        == "75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d"
    )


def test_no_actor_decision_event_types_emitted_by_scenario_schedule_book():
    kernel = _bare_kernel()
    kernel.scenario_schedule.add_schedule(_schedule())
    kernel.scenario_schedule.add_scheduled_application(
        _application()
    )
    forbidden = {
        "order_submitted",
        "trade_executed",
        "price_updated",
        "quote_disseminated",
        "clearing_completed",
        "settlement_completed",
        "ownership_transferred",
        "loan_approved",
        "security_issued",
        "underwriting_executed",
        "investor_action_taken",
        "firm_decision_recorded",
        "bank_approval_recorded",
        # v1.18.2 application — must NOT be emitted by the
        # schedule book at v1.20.2; the schedule stores intent,
        # the v1.20.3 run profile fires the actual application.
        "scenario_driver_application_recorded",
        "scenario_context_shift_recorded",
    }
    seen = {rec.record_type.value for rec in kernel.ledger.records}
    assert not (seen & forbidden)


# ---------------------------------------------------------------------------
# Default monthly schedule fixture builder
# ---------------------------------------------------------------------------


def test_build_default_monthly_schedule_returns_one_schedule_one_application():
    schedule, application = build_default_scenario_monthly_schedule()
    assert isinstance(schedule, ScenarioSchedule)
    assert isinstance(application, ScheduledScenarioApplication)


def test_build_default_monthly_schedule_uses_month_04_period_index_3():
    schedule, application = build_default_scenario_monthly_schedule()
    assert schedule.scheduled_month_labels == ("month_04",)
    assert schedule.scheduled_period_indices == (3,)
    assert application.scheduled_month_label == "month_04"
    assert application.scheduled_period_index == 3


def test_build_default_monthly_schedule_uses_credit_tightening_driver():
    schedule, application = build_default_scenario_monthly_schedule()
    assert schedule.scenario_driver_template_ids == (
        "scenario_driver:credit_tightening:reference",
    )
    assert application.scenario_driver_template_id == (
        "scenario_driver:credit_tightening:reference"
    )


def test_build_default_monthly_schedule_targets_generic_11_sector_universe():
    schedule, application = build_default_scenario_monthly_schedule()
    assert schedule.reference_universe_id == (
        "reference_universe:generic_11_sector"
    )
    assert application.affected_reference_universe_id == (
        "reference_universe:generic_11_sector"
    )


def test_build_default_monthly_schedule_uses_scenario_monthly_reference_universe_profile():
    schedule, _ = build_default_scenario_monthly_schedule()
    assert schedule.run_profile_label == (
        "scenario_monthly_reference_universe"
    )
    assert schedule.schedule_policy_label == "single_scenario"


def test_build_default_monthly_schedule_application_policy_after_arrivals():
    """The default policy fires the scenario *after* the
    monthly information arrivals so the v1.18.2 context shift
    can cite the v1.19.3 InformationArrivalRecord ids if a
    future v1.20.3 mapping wants to."""
    _, application = build_default_scenario_monthly_schedule()
    assert application.application_policy_label == (
        "apply_after_information_arrivals"
    )


def test_build_default_monthly_schedule_does_not_auto_register():
    """The builder is pure — it does not write to the kernel's
    book."""
    kernel = _bare_kernel()
    schedule, application = build_default_scenario_monthly_schedule()
    assert schedule is not None
    assert application is not None
    # The kernel's book remains empty.
    assert kernel.scenario_schedule.list_schedules() == ()
    assert (
        kernel.scenario_schedule.list_scheduled_applications()
        == ()
    )
    # No ledger records emitted by the pure builder.
    assert len(kernel.ledger.records) == 0


def test_build_default_monthly_schedule_deterministic():
    a_schedule, a_application = build_default_scenario_monthly_schedule()
    b_schedule, b_application = build_default_scenario_monthly_schedule()
    assert a_schedule.to_dict() == b_schedule.to_dict()
    assert a_application.to_dict() == b_application.to_dict()


def test_build_default_monthly_schedule_application_id_contains_month_label():
    _, application = build_default_scenario_monthly_schedule()
    assert (
        "month_04"
        in application.scheduled_scenario_application_id
    )


def test_build_default_monthly_schedule_explicit_period_index_zero():
    """Calling the builder with ``scheduled_period_index=0``
    should produce a schedule for ``month_01``."""
    schedule, application = build_default_scenario_monthly_schedule(
        scheduled_period_index=0,
    )
    assert schedule.scheduled_month_labels == ("month_01",)
    assert application.scheduled_month_label == "month_01"
    assert application.scheduled_period_index == 0


def test_build_default_monthly_schedule_rejects_period_index_above_11():
    with pytest.raises(ValueError):
        build_default_scenario_monthly_schedule(
            scheduled_period_index=12,
        )


def test_build_default_monthly_schedule_rejects_negative_period_index():
    with pytest.raises(ValueError):
        build_default_scenario_monthly_schedule(
            scheduled_period_index=-1,
        )


# ---------------------------------------------------------------------------
# Forbidden-name + jurisdiction-neutral scans
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota",
    "mufg",
    "smbc",
    "mizuho",
    "boj",
    "fsa",
    "jpx",
    "gpif",
    "tse",
    "nikkei",
    "topix",
    "sony",
    "jgb",
    "nyse",
    "nasdaq",
)


_LICENSED_TAXONOMY_TOKENS = (
    "gics",
    "msci",
    "factset",
    "bloomberg",
    "refinitiv",
)


def _strip_module_docstring(text: str) -> str:
    lo = text.find('"""')
    if lo < 0:
        return text
    hi = text.find('"""', lo + 3)
    if hi < 0:
        return text
    return text[: lo] + text[hi + 3 :]


def _strip_forbidden_literal(text: str) -> str:
    """Strip the ``FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES``
    frozenset literal block (case-insensitive)."""
    lower = text.lower()
    open_idx = lower.find("forbidden_scenario_schedule_field_names")
    if open_idx < 0:
        return text
    close_idx = text.find(")", open_idx)
    if close_idx <= open_idx:
        return text
    return text[: open_idx] + text[close_idx:]


def test_module_jurisdiction_neutral_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_module_docstring(text)
    text = _strip_forbidden_literal(text).lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "scenario_schedule.py outside docstring + FORBIDDEN literal"
        )


def test_module_no_licensed_taxonomy_dependency_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_module_docstring(text)
    text = _strip_forbidden_literal(text).lower()
    for token in _LICENSED_TAXONOMY_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"licensed-taxonomy token {token!r} appears in "
            "scenario_schedule.py outside docstring + FORBIDDEN literal"
        )


def test_test_file_jurisdiction_neutral_scan():
    text = Path(__file__).read_text(encoding="utf-8").lower()
    for marker in (
        "_forbidden_tokens = (",
        "_licensed_taxonomy_tokens = (",
        "_v1_20_0_pinned_forbidden_names = (",
    ):
        idx = text.find(marker)
        if idx != -1:
            close = text.find(")", idx) + 1
            if close > 0:
                text = text[:idx] + text[close:]
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "test_scenario_schedule.py outside the token tables"
        )


def test_module_text_does_not_carry_forbidden_phrases():
    """The module imports nothing from the forbidden list and
    does not declare any forbidden field name as a bare
    identifier outside the FORBIDDEN literal."""
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_module_docstring(text)
    text = _strip_forbidden_literal(text)
    for phrase in (
        "real_company_name",
        "real_sector_weight",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
        "investment_advice",
        "target_price",
        "expected_return",
        "forecast_path",
        "predicted_index",
    ):
        assert phrase not in text, (
            f"forbidden phrase {phrase!r} appears in "
            "scenario_schedule.py outside docstring + FORBIDDEN literal"
        )
