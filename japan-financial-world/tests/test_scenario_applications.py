"""
Tests for v1.18.2 scenario-driver application —
``world.scenario_applications`` module.

Pinned invariants:

- closed-set vocabularies (``APPLICATION_STATUS_LABELS``,
  ``CONTEXT_SURFACE_LABELS``, ``SHIFT_DIRECTION_LABELS``);
- v1.18.0 hard naming boundary
  (``FORBIDDEN_SCENARIO_FIELD_NAMES``) disjoint from every new
  v1.18.2 closed-set vocabulary, dataclass field names, payload
  keys, metadata keys, and boundary-flag keys;
- frozen dataclasses with strict construction-time validation;
- duplicate application id / context-shift id rejected; duplicate
  emits no extra ledger record;
- unknown application / context-shift id raises;
- every list / filter method;
- snapshot determinism;
- ledger emits exactly one record per ``add_application`` /
  ``add_context_shift`` call;
- kernel wiring (``WorldKernel.scenario_applications``);
- helper reads only the cited template + cited context ids
  (no global book scan);
- helper does not mutate ``MarketEnvironmentBook`` /
  ``FirmFinancialStateBook`` / ``PriceBook`` /
  ``CorporateFinancingPathBook`` /
  ``InterbankLiquidityStateBook``;
- helper does not create actor decisions / investor actions /
  bank approvals / forbidden-event-type ledger records;
- helper carries v1.18.0 audit-metadata block on every emitted
  record;
- empty scenario-application book does not move the
  default-fixture ``living_world_digest``; an explicit
  application moves a scenario-specific ledger but the unmodified
  default sweep stays byte-identical;
- helper is deterministic and idempotent on identical inputs;
- jurisdiction-neutral identifier scan over module + test text.
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
from world.scenario_applications import (
    APPLICATION_STATUS_LABELS,
    CONTEXT_SURFACE_LABELS,
    DEFAULT_APPLICATION_REASONING_POLICY_ID,
    DuplicateScenarioApplicationError,
    DuplicateScenarioContextShiftError,
    SHIFT_DIRECTION_LABELS,
    ScenarioApplicationBook,
    ScenarioContextShiftRecord,
    ScenarioDriverApplicationRecord,
    UnknownScenarioApplicationError,
    UnknownScenarioContextShiftError,
    apply_scenario_driver,
)
from world.scenario_drivers import (
    DEFAULT_REASONING_MODE,
    DEFAULT_REASONING_SLOT,
    FORBIDDEN_SCENARIO_FIELD_NAMES,
    ScenarioDriverTemplate,
    UnknownScenarioDriverTemplateError,
)
from world.scheduler import Scheduler
from world.state import State


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "world"
    / "scenario_applications.py"
)


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


def test_application_status_labels_closed_set():
    assert APPLICATION_STATUS_LABELS == frozenset(
        {
            "prepared",
            "applied_as_context_shift",
            "degraded_missing_template",
            "degraded_unresolved_refs",
            "rejected",
            "unknown",
        }
    )


def test_context_surface_labels_closed_set():
    assert CONTEXT_SURFACE_LABELS == frozenset(
        {
            "market_environment",
            "firm_financial_state",
            "interbank_liquidity",
            "industry_condition",
            "attention_surface",
            "market_pressure_surface",
            "financing_review_surface",
            "display_annotation_surface",
            "unknown",
        }
    )


def test_shift_direction_labels_closed_set():
    assert SHIFT_DIRECTION_LABELS == frozenset(
        {
            "tighten",
            "loosen",
            "deteriorate",
            "improve",
            "increase_uncertainty",
            "reduce_uncertainty",
            "attention_amplify",
            "information_gap",
            "no_direct_shift",
            "unknown",
        }
    )


# ---------------------------------------------------------------------------
# Forbidden field-name boundary
# ---------------------------------------------------------------------------


def test_forbidden_field_names_disjoint_from_v1_18_2_closed_sets():
    for vocab in (
        APPLICATION_STATUS_LABELS,
        CONTEXT_SURFACE_LABELS,
        SHIFT_DIRECTION_LABELS,
    ):
        assert not (FORBIDDEN_SCENARIO_FIELD_NAMES & vocab)


def test_application_dataclass_fields_disjoint_from_forbidden():
    fields = set(
        ScenarioDriverApplicationRecord.__dataclass_fields__.keys()
    )
    assert not (fields & FORBIDDEN_SCENARIO_FIELD_NAMES)


def test_shift_dataclass_fields_disjoint_from_forbidden():
    fields = set(
        ScenarioContextShiftRecord.__dataclass_fields__.keys()
    )
    assert not (fields & FORBIDDEN_SCENARIO_FIELD_NAMES)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _template(
    *,
    scenario_driver_template_id: str = (
        "scenario_driver:rate_repricing:reference"
    ),
    scenario_family_label: str = "rate_repricing_driver",
    driver_group_label: str = "macro_rates",
    severity_label: str = "medium",
    affected_actor_scope_label: str = "market_wide",
    expected_annotation_type_label: str = (
        "market_environment_change"
    ),
    affected_evidence_bucket_labels: tuple[str, ...] = (
        "market_environment_state",
    ),
) -> ScenarioDriverTemplate:
    return ScenarioDriverTemplate(
        scenario_driver_template_id=scenario_driver_template_id,
        scenario_family_label=scenario_family_label,
        driver_group_label=driver_group_label,
        driver_label="Synthetic test driver",
        event_date_policy_label="quarter_start",
        severity_label=severity_label,
        affected_actor_scope_label=affected_actor_scope_label,
        expected_annotation_type_label=(
            expected_annotation_type_label
        ),
        affected_evidence_bucket_labels=(
            affected_evidence_bucket_labels
        ),
    )


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _seeded_kernel_with_template(
    template: ScenarioDriverTemplate | None = None,
) -> WorldKernel:
    k = _bare_kernel()
    k.scenario_drivers.add_template(template or _template())
    return k


def _application(
    *,
    scenario_application_id: str = "scenario_application:test:1",
    scenario_driver_template_id: str = (
        "scenario_driver:rate_repricing:reference"
    ),
    as_of_date: str = "2026-03-31",
    application_status_label: str = "applied_as_context_shift",
    source_context_record_ids: tuple[str, ...] = (),
    emitted_context_shift_ids: tuple[str, ...] = (),
    unresolved_ref_count: int = 0,
    metadata: dict | None = None,
) -> ScenarioDriverApplicationRecord:
    return ScenarioDriverApplicationRecord(
        scenario_application_id=scenario_application_id,
        scenario_driver_template_id=scenario_driver_template_id,
        as_of_date=as_of_date,
        application_status_label=application_status_label,
        source_template_ids=(scenario_driver_template_id,),
        source_context_record_ids=source_context_record_ids,
        emitted_context_shift_ids=emitted_context_shift_ids,
        unresolved_ref_count=unresolved_ref_count,
        metadata=metadata or {},
    )


def _shift(
    *,
    scenario_context_shift_id: str = (
        "scenario_context_shift:test:1:00"
    ),
    scenario_application_id: str = "scenario_application:test:1",
    scenario_driver_template_id: str = (
        "scenario_driver:rate_repricing:reference"
    ),
    as_of_date: str = "2026-03-31",
    context_surface_label: str = "market_environment",
    driver_group_label: str = "macro_rates",
    scenario_family_label: str = "rate_repricing_driver",
    shift_direction_label: str = "tighten",
    severity_label: str = "medium",
    affected_actor_scope_label: str = "market_wide",
    expected_annotation_type_label: str = (
        "market_environment_change"
    ),
    affected_context_record_ids: tuple[str, ...] = (
        "env:test:1",
    ),
    evidence_ref_ids: tuple[str, ...] = (
        "scenario_driver:rate_repricing:reference",
        "env:test:1",
    ),
) -> ScenarioContextShiftRecord:
    return ScenarioContextShiftRecord(
        scenario_context_shift_id=scenario_context_shift_id,
        scenario_application_id=scenario_application_id,
        scenario_driver_template_id=scenario_driver_template_id,
        as_of_date=as_of_date,
        context_surface_label=context_surface_label,
        driver_group_label=driver_group_label,
        scenario_family_label=scenario_family_label,
        shift_direction_label=shift_direction_label,
        severity_label=severity_label,
        affected_actor_scope_label=affected_actor_scope_label,
        affected_context_record_ids=(
            affected_context_record_ids
        ),
        affected_evidence_bucket_labels=(
            "market_environment_state",
        ),
        expected_annotation_type_label=(
            expected_annotation_type_label
        ),
        evidence_ref_ids=evidence_ref_ids,
    )


# ---------------------------------------------------------------------------
# Application record validation
# ---------------------------------------------------------------------------


def test_application_record_minimal_fields():
    a = _application()
    assert a.reasoning_mode == "rule_based_fallback"
    assert a.reasoning_slot == "future_llm_compatible"
    assert a.reasoning_policy_id == (
        DEFAULT_APPLICATION_REASONING_POLICY_ID
    )
    assert a.status == "active"
    assert a.visibility == "internal_only"


def test_application_record_rejects_empty_id():
    with pytest.raises(ValueError):
        _application(scenario_application_id="")


def test_application_record_rejects_unknown_status_label():
    with pytest.raises(ValueError):
        _application(application_status_label="committed_for_audit")


def test_application_record_rejects_negative_unresolved_ref_count():
    with pytest.raises(ValueError):
        _application(unresolved_ref_count=-1)


def test_application_record_rejects_metadata_with_forbidden_key():
    with pytest.raises(ValueError):
        _application(metadata={"target_price": 1.0})


def test_application_record_rejects_metadata_with_llm_prose_key():
    with pytest.raises(ValueError):
        _application(
            metadata={"llm_prose": "the bank should approve"}
        )


def test_application_record_is_immutable():
    a = _application()
    with pytest.raises(Exception):
        a.scenario_application_id = "other"  # type: ignore[misc]


def test_application_record_to_dict_round_trip_byte_identical():
    a = _application()
    b = _application()
    assert a.to_dict() == b.to_dict()


def test_application_record_to_dict_keys_disjoint_from_forbidden():
    payload = _application().to_dict()
    assert not (
        set(payload.keys()) & FORBIDDEN_SCENARIO_FIELD_NAMES
    )
    assert not (
        set(payload["metadata"].keys())
        & FORBIDDEN_SCENARIO_FIELD_NAMES
    )
    assert not (
        set(payload["boundary_flags"].keys())
        & FORBIDDEN_SCENARIO_FIELD_NAMES
    )


# ---------------------------------------------------------------------------
# Context-shift record validation
# ---------------------------------------------------------------------------


def test_shift_record_minimal_fields():
    s = _shift()
    assert s.reasoning_mode == "rule_based_fallback"
    assert s.reasoning_slot == "future_llm_compatible"
    assert s.context_surface_label == "market_environment"
    assert s.shift_direction_label == "tighten"
    assert s.expected_annotation_type_label == (
        "market_environment_change"
    )


def test_shift_record_rejects_unknown_context_surface_label():
    with pytest.raises(ValueError):
        _shift(context_surface_label="custom_surface")


def test_shift_record_rejects_unknown_shift_direction_label():
    with pytest.raises(ValueError):
        _shift(shift_direction_label="catastrophe")


def test_shift_record_is_immutable():
    s = _shift()
    with pytest.raises(Exception):
        s.scenario_context_shift_id = "other"  # type: ignore[misc]


def test_shift_record_to_dict_keys_disjoint_from_forbidden():
    payload = _shift().to_dict()
    assert not (
        set(payload.keys()) & FORBIDDEN_SCENARIO_FIELD_NAMES
    )
    assert not (
        set(payload["metadata"].keys())
        & FORBIDDEN_SCENARIO_FIELD_NAMES
    )
    assert not (
        set(payload["boundary_flags"].keys())
        & FORBIDDEN_SCENARIO_FIELD_NAMES
    )


def test_shift_record_default_boundary_flags():
    s = _shift()
    assert s.boundary_flags == {
        "no_actor_decision": True,
        "no_llm_execution": True,
        "no_price_formation": True,
        "no_trading": True,
        "no_financing_execution": True,
        "no_investment_advice": True,
        "synthetic_only": True,
    }


# ---------------------------------------------------------------------------
# Default reasoning fields
# ---------------------------------------------------------------------------


def test_default_reasoning_mode_is_rule_based_fallback():
    assert DEFAULT_REASONING_MODE == "rule_based_fallback"
    assert DEFAULT_REASONING_SLOT == "future_llm_compatible"
    a = _application()
    assert a.reasoning_mode == "rule_based_fallback"
    s = _shift()
    assert s.reasoning_mode == "rule_based_fallback"


# ---------------------------------------------------------------------------
# ScenarioApplicationBook — applications
# ---------------------------------------------------------------------------


def test_book_add_get_list_application():
    book = ScenarioApplicationBook()
    a = _application()
    book.add_application(a)
    assert book.get_application(a.scenario_application_id) is a
    assert book.list_applications() == (a,)


def test_book_duplicate_application_id_raises():
    book = ScenarioApplicationBook()
    a = _application()
    book.add_application(a)
    with pytest.raises(DuplicateScenarioApplicationError):
        book.add_application(a)


def test_book_unknown_application_id_raises():
    book = ScenarioApplicationBook()
    with pytest.raises(UnknownScenarioApplicationError):
        book.get_application("missing")


def test_book_list_by_template():
    book = ScenarioApplicationBook()
    a = _application(
        scenario_application_id="scenario_application:rate:1",
        scenario_driver_template_id="scenario_driver:rate:1",
    )
    b = _application(
        scenario_application_id="scenario_application:credit:1",
        scenario_driver_template_id="scenario_driver:credit:1",
    )
    book.add_application(a)
    book.add_application(b)
    assert book.list_by_template("scenario_driver:rate:1") == (a,)
    assert book.list_by_template("scenario_driver:credit:1") == (b,)


def test_book_list_by_application_status():
    book = ScenarioApplicationBook()
    a = _application(
        scenario_application_id="scenario_application:applied:1",
        application_status_label="applied_as_context_shift",
    )
    b = _application(
        scenario_application_id="scenario_application:degraded:1",
        application_status_label="degraded_unresolved_refs",
        unresolved_ref_count=2,
    )
    book.add_application(a)
    book.add_application(b)
    assert book.list_by_application_status(
        "applied_as_context_shift"
    ) == (a,)
    assert book.list_by_application_status(
        "degraded_unresolved_refs"
    ) == (b,)


def test_book_list_by_date():
    book = ScenarioApplicationBook()
    a = _application(
        scenario_application_id="scenario_application:q1:1",
        as_of_date="2026-03-31",
    )
    b = _application(
        scenario_application_id="scenario_application:q2:1",
        as_of_date="2026-06-30",
    )
    book.add_application(a)
    book.add_application(b)
    assert book.list_by_date("2026-03-31") == (a,)
    assert book.list_by_date(date(2026, 6, 30)) == (b,)


# ---------------------------------------------------------------------------
# ScenarioApplicationBook — context shifts
# ---------------------------------------------------------------------------


def test_book_add_get_list_context_shift():
    book = ScenarioApplicationBook()
    s = _shift()
    book.add_context_shift(s)
    assert book.get_context_shift(s.scenario_context_shift_id) is s
    assert book.list_context_shifts() == (s,)


def test_book_duplicate_shift_id_raises():
    book = ScenarioApplicationBook()
    s = _shift()
    book.add_context_shift(s)
    with pytest.raises(DuplicateScenarioContextShiftError):
        book.add_context_shift(s)


def test_book_unknown_shift_id_raises():
    book = ScenarioApplicationBook()
    with pytest.raises(UnknownScenarioContextShiftError):
        book.get_context_shift("missing")


def test_book_list_shifts_by_template():
    book = ScenarioApplicationBook()
    a = _shift(
        scenario_context_shift_id="scenario_context_shift:rate:1:00",
        scenario_driver_template_id="scenario_driver:rate:1",
    )
    b = _shift(
        scenario_context_shift_id="scenario_context_shift:credit:1:00",
        scenario_driver_template_id="scenario_driver:credit:1",
        scenario_family_label="credit_tightening_driver",
        driver_group_label="credit_liquidity",
    )
    book.add_context_shift(a)
    book.add_context_shift(b)
    assert book.list_shifts_by_template(
        "scenario_driver:rate:1"
    ) == (a,)
    assert book.list_shifts_by_template(
        "scenario_driver:credit:1"
    ) == (b,)


def test_book_list_shifts_by_application():
    book = ScenarioApplicationBook()
    a = _shift(
        scenario_context_shift_id=(
            "scenario_context_shift:app1:00"
        ),
        scenario_application_id="scenario_application:app1",
    )
    b = _shift(
        scenario_context_shift_id=(
            "scenario_context_shift:app2:00"
        ),
        scenario_application_id="scenario_application:app2",
    )
    book.add_context_shift(a)
    book.add_context_shift(b)
    assert book.list_shifts_by_application(
        "scenario_application:app1"
    ) == (a,)
    assert book.list_shifts_by_application(
        "scenario_application:app2"
    ) == (b,)


def test_book_list_shifts_by_context_surface():
    book = ScenarioApplicationBook()
    a = _shift(
        scenario_context_shift_id=(
            "scenario_context_shift:env:00"
        ),
        context_surface_label="market_environment",
    )
    b = _shift(
        scenario_context_shift_id=(
            "scenario_context_shift:fin:00"
        ),
        context_surface_label="financing_review_surface",
        shift_direction_label="deteriorate",
        scenario_family_label="funding_window_closure_driver",
        driver_group_label="credit_liquidity",
        expected_annotation_type_label="financing_constraint",
    )
    book.add_context_shift(a)
    book.add_context_shift(b)
    assert book.list_shifts_by_context_surface(
        "market_environment"
    ) == (a,)
    assert book.list_shifts_by_context_surface(
        "financing_review_surface"
    ) == (b,)


def test_book_list_shifts_by_driver_group():
    book = ScenarioApplicationBook()
    a = _shift(
        scenario_context_shift_id=(
            "scenario_context_shift:macro:00"
        ),
        driver_group_label="macro_rates",
    )
    b = _shift(
        scenario_context_shift_id=(
            "scenario_context_shift:liq:00"
        ),
        driver_group_label="credit_liquidity",
        scenario_family_label="liquidity_stress_driver",
        shift_direction_label="deteriorate",
    )
    book.add_context_shift(a)
    book.add_context_shift(b)
    assert book.list_shifts_by_driver_group("macro_rates") == (a,)
    assert book.list_shifts_by_driver_group("credit_liquidity") == (
        b,
    )


def test_book_list_shifts_by_scenario_family():
    book = ScenarioApplicationBook()
    a = _shift(
        scenario_context_shift_id=(
            "scenario_context_shift:rate:00"
        ),
        scenario_family_label="rate_repricing_driver",
    )
    b = _shift(
        scenario_context_shift_id=(
            "scenario_context_shift:liq:00"
        ),
        scenario_family_label="liquidity_stress_driver",
        driver_group_label="credit_liquidity",
        shift_direction_label="deteriorate",
    )
    book.add_context_shift(a)
    book.add_context_shift(b)
    assert book.list_shifts_by_scenario_family(
        "rate_repricing_driver"
    ) == (a,)
    assert book.list_shifts_by_scenario_family(
        "liquidity_stress_driver"
    ) == (b,)


def test_book_snapshot_deterministic():
    book = ScenarioApplicationBook()
    book.add_application(_application())
    book.add_context_shift(_shift())
    snap_a = book.snapshot()
    snap_b = book.snapshot()
    assert snap_a == snap_b
    assert "scenario_applications" in snap_a
    assert "scenario_context_shifts" in snap_a
    assert len(snap_a["scenario_applications"]) == 1
    assert len(snap_a["scenario_context_shifts"]) == 1


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_ledger_emits_one_record_per_add_application():
    kernel = _bare_kernel()
    before = len(kernel.ledger.records)
    kernel.scenario_applications.add_application(_application())
    after = len(kernel.ledger.records)
    assert after - before == 1
    record = kernel.ledger.records[-1]
    assert record.record_type == (
        RecordType.SCENARIO_DRIVER_APPLICATION_RECORDED
    )
    assert record.payload["scenario_application_id"] == (
        "scenario_application:test:1"
    )
    assert record.payload["reasoning_mode"] == "rule_based_fallback"


def test_ledger_emits_one_record_per_add_context_shift():
    kernel = _bare_kernel()
    before = len(kernel.ledger.records)
    kernel.scenario_applications.add_context_shift(_shift())
    after = len(kernel.ledger.records)
    assert after - before == 1
    record = kernel.ledger.records[-1]
    assert record.record_type == (
        RecordType.SCENARIO_CONTEXT_SHIFT_RECORDED
    )
    assert record.payload["scenario_context_shift_id"] == (
        "scenario_context_shift:test:1:00"
    )


def test_duplicate_application_emits_no_extra_ledger_record():
    kernel = _bare_kernel()
    kernel.scenario_applications.add_application(_application())
    count_after_first = len(kernel.ledger.records)
    with pytest.raises(DuplicateScenarioApplicationError):
        kernel.scenario_applications.add_application(_application())
    assert len(kernel.ledger.records) == count_after_first


def test_duplicate_shift_emits_no_extra_ledger_record():
    kernel = _bare_kernel()
    kernel.scenario_applications.add_context_shift(_shift())
    count_after_first = len(kernel.ledger.records)
    with pytest.raises(DuplicateScenarioContextShiftError):
        kernel.scenario_applications.add_context_shift(_shift())
    assert len(kernel.ledger.records) == count_after_first


def test_ledger_payload_keys_disjoint_from_forbidden():
    kernel = _bare_kernel()
    kernel.scenario_applications.add_application(_application())
    kernel.scenario_applications.add_context_shift(_shift())
    for record in kernel.ledger.records:
        assert not (
            set(record.payload.keys())
            & FORBIDDEN_SCENARIO_FIELD_NAMES
        )


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_wires_scenario_applications_book():
    kernel = _bare_kernel()
    assert isinstance(
        kernel.scenario_applications, ScenarioApplicationBook
    )
    assert kernel.scenario_applications.ledger is kernel.ledger
    assert kernel.scenario_applications.list_applications() == ()
    assert kernel.scenario_applications.list_context_shifts() == ()


# ---------------------------------------------------------------------------
# apply_scenario_driver — happy path + family mappings
# ---------------------------------------------------------------------------


def test_apply_scenario_driver_rate_repricing_emits_one_shift():
    k = _seeded_kernel_with_template()
    app = apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
        source_context_record_ids=("env:test:1",),
    )
    assert app.application_status_label == "applied_as_context_shift"
    shifts = k.scenario_applications.list_context_shifts()
    assert len(shifts) == 1
    s = shifts[0]
    assert s.context_surface_label == "market_environment"
    assert s.shift_direction_label == "tighten"
    assert s.expected_annotation_type_label == (
        "market_environment_change"
    )
    assert "scenario_driver:rate_repricing:reference" in (
        s.evidence_ref_ids
    )
    assert s.affected_context_record_ids == ("env:test:1",)


def test_apply_scenario_driver_rate_repricing_low_severity_uncertainty():
    """Low-severity rate_repricing maps to ``increase_uncertainty``
    rather than ``tighten`` — pinned by the v1.18.2 minimal mapping."""
    k = _seeded_kernel_with_template(
        _template(severity_label="low")
    )
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    shifts = k.scenario_applications.list_context_shifts()
    assert shifts[0].shift_direction_label == "increase_uncertainty"


def test_apply_scenario_driver_credit_tightening_emits_two_shifts():
    template = _template(
        scenario_driver_template_id=(
            "scenario_driver:credit_tightening:reference"
        ),
        scenario_family_label="credit_tightening_driver",
        driver_group_label="credit_liquidity",
    )
    k = _seeded_kernel_with_template(template)
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:credit_tightening:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    shifts = k.scenario_applications.list_context_shifts()
    assert len(shifts) == 2
    surfaces = {s.context_surface_label for s in shifts}
    assert surfaces == {
        "market_environment",
        "financing_review_surface",
    }
    assert all(
        s.shift_direction_label == "tighten" for s in shifts
    )


def test_apply_scenario_driver_funding_window_closure_emits_financing_shift():
    template = _template(
        scenario_driver_template_id=(
            "scenario_driver:funding_window_closure:reference"
        ),
        scenario_family_label=(
            "funding_window_closure_driver"
        ),
        driver_group_label="credit_liquidity",
        expected_annotation_type_label="financing_constraint",
    )
    k = _seeded_kernel_with_template(template)
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:funding_window_closure:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    shifts = k.scenario_applications.list_context_shifts()
    assert len(shifts) == 1
    s = shifts[0]
    assert s.context_surface_label == "financing_review_surface"
    assert s.shift_direction_label == "deteriorate"
    assert s.expected_annotation_type_label == (
        "financing_constraint"
    )


def test_apply_scenario_driver_liquidity_stress_emits_two_shifts():
    template = _template(
        scenario_driver_template_id=(
            "scenario_driver:liquidity_stress:reference"
        ),
        scenario_family_label="liquidity_stress_driver",
        driver_group_label="credit_liquidity",
    )
    k = _seeded_kernel_with_template(template)
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:liquidity_stress:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    shifts = k.scenario_applications.list_context_shifts()
    assert len(shifts) == 2
    surfaces = {s.context_surface_label for s in shifts}
    assert surfaces == {"interbank_liquidity", "market_environment"}
    assert all(
        s.shift_direction_label == "deteriorate" for s in shifts
    )


def test_apply_scenario_driver_information_gap_emits_attention_shift():
    template = _template(
        scenario_driver_template_id=(
            "scenario_driver:information_gap:reference"
        ),
        scenario_family_label="information_gap_driver",
        driver_group_label="information_attention",
        expected_annotation_type_label="attention_shift",
    )
    k = _seeded_kernel_with_template(template)
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:information_gap:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    shifts = k.scenario_applications.list_context_shifts()
    assert len(shifts) == 1
    s = shifts[0]
    assert s.context_surface_label == "attention_surface"
    assert s.shift_direction_label == "information_gap"
    assert s.expected_annotation_type_label == "attention_shift"


def test_apply_scenario_driver_unmapped_family_emits_no_direct_shift():
    template = _template(
        scenario_driver_template_id=(
            "scenario_driver:thematic_attention:reference"
        ),
        scenario_family_label="thematic_attention_driver",
        driver_group_label="information_attention",
        expected_annotation_type_label="attention_shift",
    )
    k = _seeded_kernel_with_template(template)
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:thematic_attention:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    shifts = k.scenario_applications.list_context_shifts()
    assert len(shifts) == 1
    s = shifts[0]
    assert s.shift_direction_label == "no_direct_shift"
    assert s.context_surface_label == "unknown"
    assert s.expected_annotation_type_label == "attention_shift"


def test_apply_scenario_driver_unknown_template_raises():
    k = _bare_kernel()
    with pytest.raises(UnknownScenarioDriverTemplateError):
        apply_scenario_driver(
            k,
            scenario_driver_template_id="scenario_driver:missing",
            as_of_date=date(2026, 3, 31),
        )


def test_apply_scenario_driver_carries_audit_metadata():
    k = _seeded_kernel_with_template()
    app = apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
        source_context_record_ids=("env:test:1", "env:test:2"),
    )
    assert app.reasoning_mode == "rule_based_fallback"
    assert app.reasoning_slot == "future_llm_compatible"
    assert app.reasoning_policy_id == (
        DEFAULT_APPLICATION_REASONING_POLICY_ID
    )
    assert app.unresolved_ref_count == 0
    assert app.boundary_flags == {
        "no_actor_decision": True,
        "no_llm_execution": True,
        "no_price_formation": True,
        "no_trading": True,
        "no_financing_execution": True,
        "no_investment_advice": True,
        "synthetic_only": True,
    }
    assert app.source_context_record_ids == (
        "env:test:1",
        "env:test:2",
    )
    shifts = k.scenario_applications.list_context_shifts()
    s = shifts[0]
    assert s.reasoning_mode == "rule_based_fallback"
    assert s.reasoning_slot == "future_llm_compatible"
    assert s.evidence_ref_ids == (
        "scenario_driver:rate_repricing:reference",
        "env:test:1",
        "env:test:2",
    )


def test_apply_scenario_driver_deterministic_application_id():
    k1 = _seeded_kernel_with_template()
    k2 = _seeded_kernel_with_template()
    a1 = apply_scenario_driver(
        k1,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
        source_context_record_ids=("env:1",),
    )
    a2 = apply_scenario_driver(
        k2,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
        source_context_record_ids=("env:1",),
    )
    assert a1.scenario_application_id == a2.scenario_application_id
    snap1 = k1.scenario_applications.snapshot()
    snap2 = k2.scenario_applications.snapshot()
    assert snap1 == snap2


def test_apply_scenario_driver_explicit_application_id():
    k = _seeded_kernel_with_template()
    app = apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
        application_id="scenario_application:custom:abc",
    )
    assert app.scenario_application_id == (
        "scenario_application:custom:abc"
    )


def test_apply_scenario_driver_unresolved_refs_marks_degraded():
    k = _seeded_kernel_with_template()
    app = apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
        unresolved_ref_count=3,
    )
    assert app.application_status_label == (
        "degraded_unresolved_refs"
    )
    assert app.unresolved_ref_count == 3
    shifts = k.scenario_applications.list_context_shifts()
    assert all(s.unresolved_ref_count == 3 for s in shifts)


def test_apply_scenario_driver_emits_application_then_shift_records():
    k = _seeded_kernel_with_template()
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    types = [r.record_type for r in k.ledger.records]
    assert (
        RecordType.SCENARIO_DRIVER_APPLICATION_RECORDED in types
    )
    assert (
        RecordType.SCENARIO_CONTEXT_SHIFT_RECORDED in types
    )


# ---------------------------------------------------------------------------
# No-mutation invariants for apply_scenario_driver
# ---------------------------------------------------------------------------


def _snap_books(k: WorldKernel) -> dict:
    """Snapshot every book the helper must NOT mutate."""
    return {
        "prices": k.prices.snapshot(),
        "market_environments": (
            k.market_environments.snapshot()
            if hasattr(k.market_environments, "snapshot")
            else None
        ),
        "firm_financial_states": (
            k.firm_financial_states.snapshot()
            if hasattr(k.firm_financial_states, "snapshot")
            else None
        ),
        "interbank_liquidity": (
            k.interbank_liquidity.snapshot()
            if hasattr(k.interbank_liquidity, "snapshot")
            else None
        ),
        "financing_paths": (
            k.financing_paths.snapshot()
            if hasattr(k.financing_paths, "snapshot")
            else None
        ),
        "investor_market_intents": (
            k.investor_market_intents.snapshot()
            if hasattr(k.investor_market_intents, "snapshot")
            else None
        ),
    }


def test_apply_scenario_driver_does_not_mutate_pricebook():
    k = _seeded_kernel_with_template()
    snap_before = k.prices.snapshot()
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    snap_after = k.prices.snapshot()
    assert snap_before == snap_after


def test_apply_scenario_driver_does_not_mutate_market_environment_book():
    k = _seeded_kernel_with_template()
    snap_before = k.market_environments.snapshot()
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    snap_after = k.market_environments.snapshot()
    assert snap_before == snap_after


def test_apply_scenario_driver_does_not_mutate_firm_financial_state_book():
    k = _seeded_kernel_with_template()
    snap_before = k.firm_financial_states.snapshot()
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    snap_after = k.firm_financial_states.snapshot()
    assert snap_before == snap_after


def test_apply_scenario_driver_does_not_mutate_interbank_liquidity():
    template = _template(
        scenario_driver_template_id=(
            "scenario_driver:liquidity_stress:reference"
        ),
        scenario_family_label="liquidity_stress_driver",
        driver_group_label="credit_liquidity",
    )
    k = _seeded_kernel_with_template(template)
    snap_before = k.interbank_liquidity.snapshot()
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:liquidity_stress:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    snap_after = k.interbank_liquidity.snapshot()
    assert snap_before == snap_after


def test_apply_scenario_driver_does_not_mutate_financing_paths():
    template = _template(
        scenario_driver_template_id=(
            "scenario_driver:funding_window_closure:reference"
        ),
        scenario_family_label="funding_window_closure_driver",
        driver_group_label="credit_liquidity",
        expected_annotation_type_label="financing_constraint",
    )
    k = _seeded_kernel_with_template(template)
    snap_before = k.financing_paths.snapshot()
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:funding_window_closure:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    snap_after = k.financing_paths.snapshot()
    assert snap_before == snap_after


def test_apply_scenario_driver_does_not_mutate_investor_market_intents():
    k = _seeded_kernel_with_template()
    snap_before = k.investor_market_intents.snapshot()
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    snap_after = k.investor_market_intents.snapshot()
    assert snap_before == snap_after


def test_apply_scenario_driver_does_not_mutate_scenario_drivers_book():
    """The cited template itself is byte-identical pre / post call."""
    k = _seeded_kernel_with_template()
    snap_before = k.scenario_drivers.snapshot()
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    snap_after = k.scenario_drivers.snapshot()
    assert snap_before == snap_after


# ---------------------------------------------------------------------------
# Forbidden-event-type invariant
# ---------------------------------------------------------------------------


def test_apply_scenario_driver_emits_no_actor_decision_event_types():
    k = _seeded_kernel_with_template()
    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    forbidden_event_names = {
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
    }
    seen = {rec.record_type.value for rec in k.ledger.records}
    assert not (seen & forbidden_event_names)


# ---------------------------------------------------------------------------
# Helper does not scan books globally
# ---------------------------------------------------------------------------


def test_apply_scenario_driver_uses_only_cited_ids_and_template():
    """Trip-wire: the helper reads the named template via
    ``get_template`` and the cited ids passed in
    ``source_context_record_ids``. It does not enumerate any
    other source-of-truth book. We pin this by patching
    ``list_*`` methods on every other book to raise — the helper
    must still succeed."""

    class _Tripwire(Exception):
        pass

    def _trip(*_a, **_kw):
        raise _Tripwire("global scan forbidden in v1.18.2 helper")

    k = _seeded_kernel_with_template()
    books_to_lock = (
        k.market_environments,
        k.firm_financial_states,
        k.industry_conditions,
        k.market_conditions,
        k.interbank_liquidity,
        k.financing_paths,
        k.investor_market_intents,
        k.aggregated_market_interest,
        k.indicative_market_pressure,
        k.prices,
    )
    for book in books_to_lock:
        for attr in dir(book):
            if attr.startswith("list_") or attr in {
                "snapshot",
                "all",
                "items",
            }:
                method = getattr(book, attr, None)
                if callable(method):
                    try:
                        setattr(book, attr, _trip)
                    except (AttributeError, TypeError):
                        pass

    apply_scenario_driver(
        k,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
        source_context_record_ids=("env:1",),
    )
    assert (
        len(k.scenario_applications.list_applications()) == 1
    )


# ---------------------------------------------------------------------------
# Default living_world_digest invariants
# ---------------------------------------------------------------------------


def test_empty_scenario_applications_does_not_move_default_living_world_digest():
    """Wiring an empty ScenarioApplicationBook into WorldKernel
    must leave the default-fixture ``living_world_digest``
    byte-identical to v1.17.last (matches the v1.18.1 invariant)."""
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


def test_explicit_scenario_application_does_not_touch_default_run():
    """The default fixture digest is for runs *without* any
    explicit scenario application. An explicit
    ``apply_scenario_driver`` invocation populates only the
    scenario_applications book and emits scenario-specific ledger
    records; running the default sweep on a *fresh* kernel
    afterwards still produces the pinned digest."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import _run_default, _seed_kernel

    scratch = _bare_kernel()
    scratch.scenario_drivers.add_template(_template())
    apply_scenario_driver(
        scratch,
        scenario_driver_template_id=(
            "scenario_driver:rate_repricing:reference"
        ),
        as_of_date=date(2026, 3, 31),
    )
    assert (
        len(scratch.scenario_applications.list_applications()) == 1
    )

    k = _seed_kernel()
    r = _run_default(k)
    assert (
        living_world_digest(k, r)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )


# ---------------------------------------------------------------------------
# Future-LLM-compatibility metadata accepted
# ---------------------------------------------------------------------------


def test_application_record_accepts_external_policy_slot_reasoning_mode():
    a = ScenarioDriverApplicationRecord(
        scenario_application_id="scenario_application:test:ext",
        scenario_driver_template_id="scenario_driver:test",
        as_of_date="2026-03-31",
        application_status_label="prepared",
        reasoning_mode="external_policy_slot",
    )
    assert a.reasoning_mode == "external_policy_slot"


def test_shift_record_accepts_external_policy_slot_reasoning_mode():
    s = _shift()
    other = ScenarioContextShiftRecord(
        scenario_context_shift_id=(
            "scenario_context_shift:test:ext:00"
        ),
        scenario_application_id=s.scenario_application_id,
        scenario_driver_template_id=s.scenario_driver_template_id,
        as_of_date=s.as_of_date,
        context_surface_label=s.context_surface_label,
        driver_group_label=s.driver_group_label,
        scenario_family_label=s.scenario_family_label,
        shift_direction_label=s.shift_direction_label,
        severity_label=s.severity_label,
        affected_actor_scope_label=s.affected_actor_scope_label,
        expected_annotation_type_label=(
            s.expected_annotation_type_label
        ),
        reasoning_mode="external_policy_slot",
    )
    assert other.reasoning_mode == "external_policy_slot"


# ---------------------------------------------------------------------------
# Forbidden-name + jurisdiction-neutral scans
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "jgb", "nyse",
    "nasdaq",
)


def test_module_jurisdiction_neutral_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "scenario_applications.py"
        )


def test_test_file_jurisdiction_neutral_scan():
    text = Path(__file__).read_text(encoding="utf-8").lower()
    table_start = text.find("_forbidden_tokens = (")
    table_end = text.find(")", table_start) + 1
    if table_start != -1 and table_end > 0:
        text = text[:table_start] + text[table_end:]
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "test_scenario_applications.py"
        )


def test_module_text_does_not_carry_forbidden_phrases_outside_imports():
    """The module imports ``FORBIDDEN_SCENARIO_FIELD_NAMES`` from
    ``world.scenario_drivers`` and may mention some forbidden
    phrases inside the docstring (e.g. ``no_price_formation`` is
    fine because that key starts with ``no_``). We scan for
    *exact* forbidden tokens that read as canonical business
    judgment outside any safe context."""
    text = _MODULE_PATH.read_text(encoding="utf-8")
    for phrase in (
        "firm_decision",
        "investor_action",
        "bank_approval",
        "trading_decision",
        "optimal_capital_structure",
        "predicted_index",
        "forecast_path",
        "expected_return",
        "target_price",
        "real_data_value",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
    ):
        assert phrase not in text, (
            f"forbidden phrase {phrase!r} appears in "
            "scenario_applications.py"
        )
