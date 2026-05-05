"""
Tests for v1.21.1 — Stress program storage.

Pins the v1.21.1 contract end-to-end:

- :class:`StressStep` validates required fields, rejects ``bool``
  / negative ``step_index``, rejects forbidden field / metadata
  keys, and accepts a v1.18.1 ``scenario_driver_template_id``
  as a plain-id citation **without** resolving it.
- :class:`StressProgramTemplate` enforces the v1.21.0a
  cardinality binding (``1 ≤ step_count ≤ 3``), rejects
  duplicate step ids, rejects duplicate step indices, and
  enforces a dense zero-based ordinal sequence on
  ``step_index``.
- :class:`StressProgramBook` is append-only, rejects duplicate
  ``stress_program_template_id``, emits exactly one
  ``stress_program_template_recorded`` ledger event per
  successful ``add_program(...)`` call, and never mutates any
  source-of-truth book.
- :class:`WorldKernel.stress_programs` is **empty by default**;
  the canonical ``quarterly_default`` /
  ``monthly_reference`` /
  ``scenario_monthly_reference_universe`` digests stay
  byte-identical when no program is registered.

Storage only — no scenario application, no context shift
emission, no interaction inference, no aggregate / composite /
net / dominant / interaction labels.
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
from world.scheduler import Scheduler
from world.state import State
from world.stress_programs import (
    DuplicateStressProgramTemplateError,
    EVENT_DATE_POLICY_LABELS,
    FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES,
    PROGRAM_MAX_STEP_COUNT,
    PROGRAM_MIN_STEP_COUNT,
    PROGRAM_PURPOSE_LABELS,
    SCHEDULED_MONTH_LABELS,
    STATUS_LABELS,
    StressProgramBook,
    StressProgramTemplate,
    StressStep,
    UnknownStressProgramTemplateError,
    VISIBILITY_LABELS,
)


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "world"
    / "stress_programs.py"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step(
    *,
    stress_step_id: str = "stress_step:demo:0",
    parent_stress_program_template_id: str = (
        "stress_program:demo:single_credit"
    ),
    step_index: int = 0,
    scenario_driver_template_id: str = (
        "scenario_driver:credit_tightening:reference"
    ),
    event_date_policy_label: str = "month_end",
    scheduled_month_label: str = "month_04",
    status: str = "active",
    visibility: str = "internal",
    metadata: dict | None = None,
) -> StressStep:
    return StressStep(
        stress_step_id=stress_step_id,
        parent_stress_program_template_id=(
            parent_stress_program_template_id
        ),
        step_index=step_index,
        scenario_driver_template_id=scenario_driver_template_id,
        event_date_policy_label=event_date_policy_label,
        scheduled_month_label=scheduled_month_label,
        status=status,
        visibility=visibility,
        metadata=metadata or {},
    )


def _program(
    *,
    stress_program_template_id: str = (
        "stress_program:demo:single_credit"
    ),
    program_label: str = "Demo single-credit stress program",
    program_purpose_label: str = (
        "single_credit_tightening_stress"
    ),
    stress_steps: tuple[StressStep, ...] | None = None,
    status: str = "active",
    visibility: str = "internal",
    metadata: dict | None = None,
) -> StressProgramTemplate:
    if stress_steps is None:
        stress_steps = (
            _step(
                stress_step_id="stress_step:demo:0",
                parent_stress_program_template_id=(
                    stress_program_template_id
                ),
                step_index=0,
            ),
        )
    return StressProgramTemplate(
        stress_program_template_id=stress_program_template_id,
        program_label=program_label,
        program_purpose_label=program_purpose_label,
        stress_steps=stress_steps,
        status=status,
        visibility=visibility,
        metadata=metadata or {},
    )


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _book_with_ledger() -> StressProgramBook:
    return StressProgramBook(ledger=Ledger())


# ---------------------------------------------------------------------------
# 1. test_stress_step_validates_required_fields
# ---------------------------------------------------------------------------


def test_stress_step_validates_required_fields():
    # Required strings: empty rejected.
    with pytest.raises(ValueError):
        _step(stress_step_id="")
    with pytest.raises(ValueError):
        _step(parent_stress_program_template_id="")
    with pytest.raises(ValueError):
        _step(scenario_driver_template_id="")
    with pytest.raises(ValueError):
        _step(event_date_policy_label="")
    with pytest.raises(ValueError):
        _step(scheduled_month_label="")
    # Closed-set labels: unknown values rejected.
    with pytest.raises(ValueError):
        _step(event_date_policy_label="not_a_real_policy")
    with pytest.raises(ValueError):
        _step(scheduled_month_label="month_99")
    with pytest.raises(ValueError):
        _step(status="not_a_status")
    with pytest.raises(ValueError):
        _step(visibility="not_a_visibility")
    # The happy path: a fully populated step instantiates.
    step = _step()
    assert step.stress_step_id == "stress_step:demo:0"
    assert step.step_index == 0


def test_stress_step_label_fields_carry_closed_set_labels():
    """Smoke check that the closed-set vocabularies are
    actually pinned (not silently widened)."""
    assert "month_end" in EVENT_DATE_POLICY_LABELS
    assert "month_04" in SCHEDULED_MONTH_LABELS
    assert "active" in STATUS_LABELS
    assert "internal" in VISIBILITY_LABELS
    assert "single_credit_tightening_stress" in (
        PROGRAM_PURPOSE_LABELS
    )


# ---------------------------------------------------------------------------
# 2. test_stress_step_rejects_bool_or_negative_step_index
# ---------------------------------------------------------------------------


def test_stress_step_rejects_bool_or_negative_step_index():
    # ``True`` / ``False`` are int subclasses but must be rejected
    # as a step_index (mirrors v1.20.2 period-index discipline).
    with pytest.raises(ValueError):
        _step(step_index=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        _step(step_index=False)  # type: ignore[arg-type]
    # Negative ints rejected.
    with pytest.raises(ValueError):
        _step(step_index=-1)
    with pytest.raises(ValueError):
        _step(step_index=-100)
    # Non-int rejected.
    with pytest.raises(ValueError):
        _step(step_index="0")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        _step(step_index=0.0)  # type: ignore[arg-type]
    # 0 and positives accepted.
    assert _step(step_index=0).step_index == 0
    assert _step(step_index=1).step_index == 1
    assert _step(step_index=2).step_index == 2


# ---------------------------------------------------------------------------
# 3. test_stress_program_requires_one_to_three_steps
# ---------------------------------------------------------------------------


def test_stress_program_requires_one_to_three_steps():
    assert PROGRAM_MIN_STEP_COUNT == 1
    assert PROGRAM_MAX_STEP_COUNT == 3
    pid = "stress_program:demo:cardinality"
    # Zero steps rejected.
    with pytest.raises(ValueError):
        _program(
            stress_program_template_id=pid,
            stress_steps=(),
        )
    # Four steps rejected.
    four_steps = tuple(
        _step(
            stress_step_id=f"stress_step:demo:{i}",
            parent_stress_program_template_id=pid,
            step_index=i,
        )
        for i in range(4)
    )
    with pytest.raises(ValueError):
        _program(
            stress_program_template_id=pid,
            stress_steps=four_steps,
        )
    # Five steps rejected.
    five_steps = tuple(
        _step(
            stress_step_id=f"stress_step:demo:{i}",
            parent_stress_program_template_id=pid,
            step_index=i,
        )
        for i in range(5)
    )
    with pytest.raises(ValueError):
        _program(
            stress_program_template_id=pid,
            stress_steps=five_steps,
        )
    # 1, 2, 3 all accepted.
    for n in (1, 2, 3):
        steps = tuple(
            _step(
                stress_step_id=f"stress_step:demo:{i}",
                parent_stress_program_template_id=pid,
                step_index=i,
            )
            for i in range(n)
        )
        program = _program(
            stress_program_template_id=pid,
            stress_steps=steps,
        )
        assert program.step_count == n


def test_stress_program_step_index_must_be_dense_zero_based():
    """``step_index`` must form a dense zero-based ordinal
    sequence (0, 1, …, n-1)."""
    pid = "stress_program:demo:dense"
    # Sparse indices (0, 2) rejected — missing 1.
    with pytest.raises(ValueError):
        _program(
            stress_program_template_id=pid,
            stress_steps=(
                _step(
                    stress_step_id="stress_step:demo:a",
                    parent_stress_program_template_id=pid,
                    step_index=0,
                ),
                _step(
                    stress_step_id="stress_step:demo:b",
                    parent_stress_program_template_id=pid,
                    step_index=2,
                ),
            ),
        )
    # Non-zero-starting (1, 2) rejected.
    with pytest.raises(ValueError):
        _program(
            stress_program_template_id=pid,
            stress_steps=(
                _step(
                    stress_step_id="stress_step:demo:a",
                    parent_stress_program_template_id=pid,
                    step_index=1,
                ),
                _step(
                    stress_step_id="stress_step:demo:b",
                    parent_stress_program_template_id=pid,
                    step_index=2,
                ),
            ),
        )


# ---------------------------------------------------------------------------
# 4. test_stress_program_rejects_duplicate_step_ids
# ---------------------------------------------------------------------------


def test_stress_program_rejects_duplicate_step_ids():
    pid = "stress_program:demo:dup_step_ids"
    # Two steps with the same stress_step_id but distinct
    # step_index values are still rejected.
    with pytest.raises(ValueError):
        _program(
            stress_program_template_id=pid,
            stress_steps=(
                _step(
                    stress_step_id="stress_step:demo:repeated",
                    parent_stress_program_template_id=pid,
                    step_index=0,
                ),
                _step(
                    stress_step_id="stress_step:demo:repeated",
                    parent_stress_program_template_id=pid,
                    step_index=1,
                ),
            ),
        )


# ---------------------------------------------------------------------------
# 5. test_stress_program_rejects_duplicate_step_indices
# ---------------------------------------------------------------------------


def test_stress_program_rejects_duplicate_step_indices():
    pid = "stress_program:demo:dup_step_indices"
    # Two steps with distinct ids but the same step_index
    # rejected (also catches the dense-zero-based check, but
    # the duplicate-index check fires first).
    with pytest.raises(ValueError):
        _program(
            stress_program_template_id=pid,
            stress_steps=(
                _step(
                    stress_step_id="stress_step:demo:a",
                    parent_stress_program_template_id=pid,
                    step_index=0,
                ),
                _step(
                    stress_step_id="stress_step:demo:b",
                    parent_stress_program_template_id=pid,
                    step_index=0,
                ),
            ),
        )


def test_stress_program_step_parent_id_must_match_program():
    pid = "stress_program:demo:parent"
    other_pid = "stress_program:demo:other"
    with pytest.raises(ValueError):
        _program(
            stress_program_template_id=pid,
            stress_steps=(
                _step(
                    stress_step_id="stress_step:demo:0",
                    parent_stress_program_template_id=other_pid,
                    step_index=0,
                ),
            ),
        )


# ---------------------------------------------------------------------------
# 6. test_stress_program_book_add_get_list_snapshot
# ---------------------------------------------------------------------------


def test_stress_program_book_add_get_list_snapshot():
    book = _book_with_ledger()
    program = _program()
    book.add_program(program)
    # get_program returns the same instance.
    assert book.get_program(
        program.stress_program_template_id
    ) is program
    # list_programs returns it.
    assert book.list_programs() == (program,)
    # list_by_status filters.
    assert book.list_by_status("active") == (program,)
    assert book.list_by_status("draft") == ()
    # list_by_purpose filters.
    assert book.list_by_purpose(
        "single_credit_tightening_stress"
    ) == (program,)
    assert book.list_by_purpose(
        "twin_credit_funding_stress"
    ) == ()
    # list_steps_by_program returns the steps in ordinal order.
    steps = book.list_steps_by_program(
        program.stress_program_template_id
    )
    assert len(steps) == 1
    assert steps[0].stress_step_id == "stress_step:demo:0"
    # snapshot is byte-deterministic.
    snap_a = book.snapshot()
    snap_b = book.snapshot()
    assert snap_a == snap_b
    assert isinstance(snap_a["stress_programs"], list)
    assert len(snap_a["stress_programs"]) == 1


def test_stress_program_book_get_unknown_id_raises():
    book = StressProgramBook()
    with pytest.raises(UnknownStressProgramTemplateError):
        book.get_program("stress_program:does_not_exist")


def test_stress_program_book_list_steps_by_program_unknown_raises():
    book = StressProgramBook()
    with pytest.raises(UnknownStressProgramTemplateError):
        book.list_steps_by_program(
            "stress_program:does_not_exist"
        )


def test_stress_program_book_steps_in_ordinal_order_regardless_of_construction_order():
    """The book's ``list_steps_by_program`` returns steps sorted
    by ``step_index`` even if the caller constructed the program
    with a non-sorted tuple."""
    pid = "stress_program:demo:reverse_construction"
    program = _program(
        stress_program_template_id=pid,
        stress_steps=(
            _step(
                stress_step_id="stress_step:demo:c",
                parent_stress_program_template_id=pid,
                step_index=2,
            ),
            _step(
                stress_step_id="stress_step:demo:a",
                parent_stress_program_template_id=pid,
                step_index=0,
            ),
            _step(
                stress_step_id="stress_step:demo:b",
                parent_stress_program_template_id=pid,
                step_index=1,
            ),
        ),
    )
    book = StressProgramBook()
    book.add_program(program)
    ordered = book.list_steps_by_program(pid)
    assert tuple(s.step_index for s in ordered) == (0, 1, 2)
    assert tuple(s.stress_step_id for s in ordered) == (
        "stress_step:demo:a",
        "stress_step:demo:b",
        "stress_step:demo:c",
    )


# ---------------------------------------------------------------------------
# 7. test_duplicate_program_emits_no_extra_ledger_record
# ---------------------------------------------------------------------------


def test_duplicate_program_emits_no_extra_ledger_record():
    """``add_program`` MUST emit exactly one
    ``stress_program_template_recorded`` event on success and
    raise ``DuplicateStressProgramTemplateError`` on a repeat
    add — without emitting an extra ledger record."""
    book = _book_with_ledger()
    program = _program()
    book.add_program(program)
    # Exactly one ledger record so far.
    types_after_first = [
        r.record_type for r in book.ledger.records
    ]
    assert types_after_first == [
        RecordType.STRESS_PROGRAM_TEMPLATE_RECORDED
    ]
    # Repeat add raises and does NOT add a second record.
    with pytest.raises(DuplicateStressProgramTemplateError):
        book.add_program(program)
    types_after_second = [
        r.record_type for r in book.ledger.records
    ]
    assert types_after_second == types_after_first


def test_add_program_with_three_steps_emits_one_program_record_only():
    """A program with three stress steps still emits only one
    ledger record (program-level, not per-step). The steps
    appear in the program record's payload."""
    book = _book_with_ledger()
    pid = "stress_program:demo:three_steps"
    program = _program(
        stress_program_template_id=pid,
        program_purpose_label="multi_stress_demonstration",
        stress_steps=tuple(
            _step(
                stress_step_id=f"stress_step:demo:{i}",
                parent_stress_program_template_id=pid,
                step_index=i,
            )
            for i in range(3)
        ),
    )
    book.add_program(program)
    types_seen = [
        r.record_type for r in book.ledger.records
    ]
    # Exactly one ledger record per add_program call.
    assert types_seen == [
        RecordType.STRESS_PROGRAM_TEMPLATE_RECORDED
    ]
    # The single record's payload carries all three steps.
    rec = book.ledger.records[0]
    assert rec.payload["step_count"] == 3
    assert len(rec.payload["stress_steps"]) == 3
    payload_step_ids = [
        s["stress_step_id"]
        for s in rec.payload["stress_steps"]
    ]
    assert payload_step_ids == [
        "stress_step:demo:0",
        "stress_step:demo:1",
        "stress_step:demo:2",
    ]


# ---------------------------------------------------------------------------
# 8. test_stress_program_storage_does_not_resolve_scenario_driver_template
# ---------------------------------------------------------------------------


def test_stress_program_storage_does_not_resolve_scenario_driver_template():
    """A stress step may cite a ``scenario_driver_template_id``
    that does NOT exist in the kernel's scenario_drivers book.
    The storage layer never reads ScenarioDriverTemplateBook."""
    kernel = _bare_kernel()
    pid = "stress_program:demo:unresolved_citation"
    # Cite a v1.18.1 scenario_driver_template_id that the bare
    # kernel definitely does not have registered.
    program = _program(
        stress_program_template_id=pid,
        program_purpose_label="custom_synthetic",
        stress_steps=(
            _step(
                stress_step_id=f"{pid}:0",
                parent_stress_program_template_id=pid,
                step_index=0,
                scenario_driver_template_id=(
                    "scenario_driver:nonexistent:reference"
                ),
            ),
        ),
    )
    # The bare kernel has no scenario_drivers entries.
    assert kernel.scenario_drivers.list_templates() == ()
    # add_program succeeds anyway — storage does not resolve
    # the citation.
    kernel.stress_programs.add_program(program)
    stored = kernel.stress_programs.get_program(pid)
    assert (
        stored.stress_steps[0].scenario_driver_template_id
        == "scenario_driver:nonexistent:reference"
    )
    # The scenario_drivers book was not touched.
    assert kernel.scenario_drivers.list_templates() == ()


# ---------------------------------------------------------------------------
# 9. test_stress_program_storage_emits_no_scenario_application
# ---------------------------------------------------------------------------


def test_stress_program_storage_emits_no_scenario_application():
    """add_program MUST NOT emit a v1.18.2
    ``scenario_driver_application_recorded`` ledger event, even
    when a stress step cites a real scenario_driver_template_id.
    v1.21.1 is storage only — scenario application lives at
    v1.21.2 (apply_stress_program) and v1.18.2
    (apply_scenario_driver)."""
    kernel = _bare_kernel()
    program = _program()
    kernel.stress_programs.add_program(program)
    types_seen = {
        r.record_type for r in kernel.ledger.records
    }
    assert (
        RecordType.SCENARIO_DRIVER_APPLICATION_RECORDED
        not in types_seen
    )
    # And the scenario_applications book remains empty.
    assert kernel.scenario_applications.list_applications() == ()


# ---------------------------------------------------------------------------
# 10. test_stress_program_storage_emits_no_context_shift
# ---------------------------------------------------------------------------


def test_stress_program_storage_emits_no_context_shift():
    """add_program MUST NOT emit a v1.18.2
    ``scenario_context_shift_recorded`` ledger event. Storage
    only — context-shift emission lives at v1.18.2 inside
    apply_scenario_driver(...), invoked indirectly only via
    v1.21.2's apply_stress_program(...) (not yet shipped)."""
    kernel = _bare_kernel()
    program = _program()
    kernel.stress_programs.add_program(program)
    types_seen = {
        r.record_type for r in kernel.ledger.records
    }
    assert (
        RecordType.SCENARIO_CONTEXT_SHIFT_RECORDED
        not in types_seen
    )
    # And the scenario_applications context-shift list remains
    # empty.
    assert (
        kernel.scenario_applications.list_context_shifts() == ()
    )


def test_stress_program_storage_does_not_mutate_pricebook():
    """add_program must NOT touch the kernel's PriceBook (or any
    other source-of-truth book)."""
    kernel = _bare_kernel()
    snap_prices_before = kernel.prices.snapshot()
    snap_contracts_before = kernel.contracts.snapshot()
    snap_constraints_before = kernel.constraints.snapshot()
    snap_ownership_before = kernel.ownership.snapshot()
    program = _program()
    kernel.stress_programs.add_program(program)
    assert kernel.prices.snapshot() == snap_prices_before
    assert kernel.contracts.snapshot() == snap_contracts_before
    assert (
        kernel.constraints.snapshot()
        == snap_constraints_before
    )
    assert kernel.ownership.snapshot() == snap_ownership_before


# ---------------------------------------------------------------------------
# 11. test_stress_program_fields_do_not_include_forbidden_names
# ---------------------------------------------------------------------------


def test_stress_program_fields_do_not_include_forbidden_names():
    """Trip-wire: dataclass field names + to_dict() keys + every
    rendered payload key MUST be disjoint from
    ``FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES``."""
    program = _program()
    step = program.stress_steps[0]
    # Dataclass field names.
    for fname in StressProgramTemplate.__dataclass_fields__:
        assert (
            fname not in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
        ), (
            f"StressProgramTemplate.{fname} collides with the "
            "v1.21.0a forbidden field-name list"
        )
    for fname in StressStep.__dataclass_fields__:
        assert (
            fname not in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
        ), (
            f"StressStep.{fname} collides with the v1.21.0a "
            "forbidden field-name list"
        )
    # to_dict() keys.
    for key in program.to_dict().keys():
        assert (
            key not in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
        )
    for key in step.to_dict().keys():
        assert (
            key not in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
        )
    # Ledger payload keys.
    book = _book_with_ledger()
    book.add_program(program)
    rec = book.ledger.records[0]
    for key in rec.payload.keys():
        assert (
            key not in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
        )
    # Each step in the payload.
    for step_payload in rec.payload["stress_steps"]:
        for key in step_payload.keys():
            assert (
                key not in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
            )


def test_v1_21_0a_forbidden_tokens_are_in_forbidden_set():
    """Pin every v1.21.0a aggregate / composite / net / dominant
    / forecast-shaped / interaction token in
    ``FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES``."""
    pinned: tuple[str, ...] = (
        # v1.21.0a forecast-shaped tokens
        "stress_magnitude",
        "stress_magnitude_in_basis_points",
        "stress_magnitude_in_percent",
        "stress_probability_weight",
        "expected_field_response",
        "expected_stress_path",
        "stress_forecast_path",
        "stress_buy_signal",
        "stress_sell_signal",
        "stress_target_price",
        "stress_expected_return",
        "stress_outcome_label",
        # aggregate / composite / net / dominant tokens
        "aggregate_shift_direction",
        "aggregate_context_label",
        "combined_context_label",
        "combined_shift_direction",
        "net_pressure_label",
        "net_stress_direction",
        "composite_risk_label",
        "composite_market_access_label",
        "dominant_stress_label",
        "total_stress_intensity",
        "stress_amplification_score",
        "predicted_stress_effect",
        "projected_stress_effect",
        # interaction tokens (deferred to v1.22+ as
        # manual_annotation only)
        "interaction_label",
        "amplify",
        "dampen",
        "offset",
        "coexist",
    )
    for token in pinned:
        assert (
            token in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
        ), (
            f"v1.21.0a token {token!r} missing from "
            "FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES"
        )


def test_v1_x_public_boundary_tokens_are_in_forbidden_set():
    """Pin every public-v1 boundary token carried forward."""
    carried: tuple[str, ...] = (
        # bare trading verbs / surfaces
        "buy",
        "sell",
        "order",
        "trade",
        "execution",
        # forecast / advice
        "predicted_index",
        "forecast_path",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        # price family
        "price",
        "market_price",
        # actor decisions
        "firm_decision",
        "investor_action",
        "bank_approval",
        # real data / Japan / LLM
        "real_data",
        "japan_calibration",
        "llm_output",
    )
    for token in carried:
        assert (
            token in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
        ), (
            f"public-v1 boundary token {token!r} missing from "
            "FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES"
        )


# ---------------------------------------------------------------------------
# 12. test_stress_program_metadata_rejects_forbidden_keys
# ---------------------------------------------------------------------------


def test_stress_program_metadata_rejects_forbidden_keys():
    """Metadata mappings on both StressProgramTemplate and
    StressStep MUST reject any forbidden key."""
    forbidden_samples: tuple[str, ...] = (
        "stress_magnitude",
        "stress_magnitude_in_basis_points",
        "stress_probability_weight",
        "expected_field_response",
        "stress_forecast_path",
        "aggregate_shift_direction",
        "combined_context_label",
        "net_pressure_label",
        "dominant_stress_label",
        "composite_risk_label",
        "stress_amplification_score",
        "interaction_label",
        "amplify",
        "dampen",
        "offset",
        "coexist",
        "buy",
        "sell",
        "order",
        "japan_calibration",
        "llm_output",
        "firm_decision",
        "investor_action",
        "bank_approval",
    )
    for token in forbidden_samples:
        with pytest.raises(ValueError):
            _step(metadata={token: "any value"})
        with pytest.raises(ValueError):
            _program(metadata={token: "any value"})


# ---------------------------------------------------------------------------
# 13. test_world_kernel_empty_stress_program_book_by_default
# ---------------------------------------------------------------------------


def test_world_kernel_empty_stress_program_book_by_default():
    """A freshly-built WorldKernel carries an empty
    StressProgramBook. The book is wired with the kernel's
    ledger via __post_init__. No stress program records appear
    in the ledger by default."""
    kernel = _bare_kernel()
    # The book exists.
    assert isinstance(
        kernel.stress_programs, StressProgramBook
    )
    # It is empty.
    assert kernel.stress_programs.list_programs() == ()
    # The ledger contains no STRESS_PROGRAM_TEMPLATE_RECORDED
    # event.
    types_seen = {
        r.record_type for r in kernel.ledger.records
    }
    assert (
        RecordType.STRESS_PROGRAM_TEMPLATE_RECORDED
        not in types_seen
    )
    # The book's ledger reference was wired by __post_init__.
    assert kernel.stress_programs.ledger is kernel.ledger


# ---------------------------------------------------------------------------
# 14. test_existing_profiles_digests_unchanged_after_empty_storage_wiring
# ---------------------------------------------------------------------------


def test_existing_profiles_digests_unchanged_after_empty_storage_wiring():
    """The canonical ``quarterly_default`` /
    ``monthly_reference`` /
    ``scenario_monthly_reference_universe`` digests must stay
    byte-identical to the v1.20.last pinned values when no
    stress program is registered. v1.21.1 is opt-in storage —
    only when a caller explicitly calls add_program(...) does
    the kernel ledger gain a stress-program record."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _run_default,
        _run_monthly_reference,
        _seed_kernel,
    )

    # quarterly_default
    k_q = _seed_kernel()
    r_q = _run_default(k_q)
    # Wire-only check: stress_programs is empty.
    assert k_q.stress_programs.list_programs() == ()
    assert (
        living_world_digest(k_q, r_q)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )

    # monthly_reference
    k_m = _seed_kernel()
    r_m = _run_monthly_reference(k_m)
    assert k_m.stress_programs.list_programs() == ()
    assert (
        living_world_digest(k_m, r_m)
        == "75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d"
    )


def test_existing_profiles_digest_unchanged_scenario_monthly_reference_universe():
    """The v1.20.3 ``scenario_monthly_reference_universe`` test-
    fixture digest must stay byte-identical at v1.21.1."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world_performance_boundary import (
        _seed_v1_20_3_kernel,
        _run_v1_20_3,
    )

    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert k.stress_programs.list_programs() == ()
    assert (
        living_world_digest(k, r)
        == "5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6"
    )


def test_record_type_enum_includes_stress_program_template_recorded():
    """Pin the new RecordType enum value at v1.21.1."""
    assert (
        RecordType.STRESS_PROGRAM_TEMPLATE_RECORDED.value
        == "stress_program_template_recorded"
    )


# ---------------------------------------------------------------------------
# Closed-set vocabulary scans
# ---------------------------------------------------------------------------


def test_program_purpose_labels_closed_set():
    assert PROGRAM_PURPOSE_LABELS == frozenset(
        {
            "single_credit_tightening_stress",
            "single_funding_window_closure_stress",
            "single_information_gap_stress",
            "twin_credit_funding_stress",
            "twin_credit_information_gap_stress",
            "multi_stress_demonstration",
            "custom_synthetic",
            "unknown",
        }
    )


def test_event_date_policy_labels_closed_set():
    assert EVENT_DATE_POLICY_LABELS == frozenset(
        {
            "quarter_start",
            "quarter_end",
            "month_start",
            "month_end",
            "ad_hoc",
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


# ---------------------------------------------------------------------------
# Forbidden-name + jurisdiction-neutral scans
# ---------------------------------------------------------------------------


_JURISDICTION_TOKENS = (
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
    """Strip every triple-quoted docstring in the module text.
    The v1.21.1 module legitimately mentions the v1.21.0a
    forbidden tokens inside class / method docstrings to
    document the boundary; those mentions are textual, not
    code, and must be excluded from the scan."""
    out: list[str] = []
    i = 0
    while True:
        lo = text.find('"""', i)
        if lo < 0:
            out.append(text[i:])
            break
        out.append(text[i:lo])
        hi = text.find('"""', lo + 3)
        if hi < 0:
            # Unterminated docstring: leave the rest untouched
            # (defensive — should never happen in valid Python).
            out.append(text[lo:])
            break
        i = hi + 3
    return "".join(out)


def _strip_forbidden_literal(text: str) -> str:
    """Strip the ``FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES``
    frozenset literal block (case-insensitive)."""
    lower = text.lower()
    open_idx = lower.find("forbidden_stress_program_field_names")
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
    for token in _JURISDICTION_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "stress_programs.py outside docstring + FORBIDDEN literal"
        )


def test_module_no_licensed_taxonomy_dependency_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_module_docstring(text)
    text = _strip_forbidden_literal(text).lower()
    for token in _LICENSED_TAXONOMY_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"licensed-taxonomy token {token!r} appears in "
            "stress_programs.py outside docstring + FORBIDDEN literal"
        )


def test_test_file_jurisdiction_neutral_scan():
    text = Path(__file__).read_text(encoding="utf-8").lower()
    for marker in (
        "_jurisdiction_tokens = (",
        "_licensed_taxonomy_tokens = (",
    ):
        idx = text.find(marker)
        if idx != -1:
            close = text.find(")", idx) + 1
            if close > 0:
                text = text[:idx] + text[close:]
    for token in _JURISDICTION_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "test_stress_programs.py outside the token tables"
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
        "stress_magnitude_in_basis_points",
        "stress_probability_weight",
        "expected_field_response",
        "stress_forecast_path",
        "aggregate_shift_direction",
        "combined_context_label",
        "net_pressure_label",
        "dominant_stress_label",
        "composite_risk_label",
        "stress_amplification_score",
    ):
        assert phrase not in text, (
            f"forbidden phrase {phrase!r} appears in "
            "stress_programs.py outside docstring + FORBIDDEN literal"
        )
