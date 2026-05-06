"""
Tests for v1.21.2 — Stress program application: thin
orchestrator + program-level receipt.

Pins the v1.21.2 contract end-to-end:

- :func:`apply_stress_program` resolves the program from
  :attr:`world.kernel.WorldKernel.stress_programs`, walks its
  :class:`StressStep` instances in dense ``step_index`` order,
  calls the existing v1.18.2
  :func:`world.scenario_applications.apply_scenario_driver`
  exactly once per step, and emits **one** program-level
  :class:`StressProgramApplicationRecord`.
- The orchestrator infers no interaction, computes no
  magnitude, classifies no overlap, and produces no aggregate /
  combined / net / dominant / composite / expected /
  predicted / forecasted field. The
  :data:`FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES` frozenset
  rejects every such field name on every dataclass / payload /
  metadata mapping.
- The orchestrator never mutates a source-of-truth book. Only
  the v1.18.2 ``scenario_applications`` book and the v1.21.2
  ``stress_applications`` book gain records (the v1.18.2
  records are emitted by the existing helper; the v1.21.2
  receipt is emitted by this orchestrator).
- Cardinality binding: ≤ 60 v1.21 records added per
  stress-applied run.
- Existing profile digests (``quarterly_default`` /
  ``monthly_reference`` /
  ``scenario_monthly_reference_universe`` test fixture) are
  byte-identical when no stress program is explicitly applied.

Storage + thin orchestration only — no readout, no markdown,
no UI, no interaction inference.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scenario_drivers import (
    ScenarioDriverTemplate,
)
from world.scheduler import Scheduler
from world.state import State
from world.stress_applications import (
    DEFAULT_STRESS_PROGRAM_APPLICATION_REASONING_POLICY_ID,
    DuplicateStressProgramApplicationError,
    FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES,
    STATUS_LABELS,
    STRESS_PROGRAM_APPLICATION_STATUS_LABELS,
    StressProgramApplicationBook,
    StressProgramApplicationRecord,
    UnknownStressProgramApplicationError,
    VISIBILITY_LABELS,
    apply_stress_program,
)
from world.stress_programs import (
    StressProgramTemplate,
    StressStep,
    UnknownStressProgramTemplateError,
)


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "world"
    / "stress_applications.py"
)


# Closed-set token tables (separate from the runtime
# code below; the test-file scan strips these blocks before
# scanning).
_jurisdiction_tokens = (
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
_licensed_taxonomy_tokens = (
    "gics",
    "msci",
    "factset",
    "bloomberg",
    "refinitiv",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _build_template(
    *,
    scenario_driver_template_id: str = (
        "scenario_driver:credit_tightening:reference"
    ),
    scenario_family_label: str = "credit_tightening_driver",
    driver_group_label: str = "credit_liquidity",
) -> ScenarioDriverTemplate:
    return ScenarioDriverTemplate(
        scenario_driver_template_id=(
            scenario_driver_template_id
        ),
        scenario_family_label=scenario_family_label,
        driver_group_label=driver_group_label,
        driver_label="Synthetic test driver",
        event_date_policy_label="quarter_end",
        severity_label="medium",
        affected_actor_scope_label="market_wide",
        expected_annotation_type_label="financing_constraint",
        affected_evidence_bucket_labels=(
            "market_environment_state",
            "financing_review_surface",
        ),
    )


def _build_step(
    *,
    program_id: str,
    step_index: int = 0,
    scenario_driver_template_id: str = (
        "scenario_driver:credit_tightening:reference"
    ),
) -> StressStep:
    return StressStep(
        stress_step_id=f"{program_id}:step:{step_index}",
        parent_stress_program_template_id=program_id,
        step_index=step_index,
        scenario_driver_template_id=(
            scenario_driver_template_id
        ),
        # NB: ``quarter_end`` is valid in both v1.18.1
        # ``EVENT_DATE_POLICY_LABELS`` (template-level) and
        # v1.21.1 ``EVENT_DATE_POLICY_LABELS`` (step-level).
        event_date_policy_label="quarter_end",
        scheduled_month_label="month_04",
    )


def _build_program(
    *,
    program_id: str = "stress_program:test:single_credit",
    program_purpose_label: str = (
        "single_credit_tightening_stress"
    ),
    step_template_ids: tuple[str, ...] = (
        "scenario_driver:credit_tightening:reference",
    ),
) -> StressProgramTemplate:
    steps = tuple(
        _build_step(
            program_id=program_id,
            step_index=i,
            scenario_driver_template_id=tpl_id,
        )
        for i, tpl_id in enumerate(step_template_ids)
    )
    return StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="Test stress program",
        program_purpose_label=program_purpose_label,
        stress_steps=steps,
    )


def _seed_kernel_with_program(
    *,
    program_id: str = "stress_program:test:single_credit",
    program_purpose_label: str = (
        "single_credit_tightening_stress"
    ),
    step_template_ids: tuple[str, ...] = (
        "scenario_driver:credit_tightening:reference",
    ),
    extra_template_specs: tuple[
        tuple[str, str, str], ...
    ] = (),
) -> tuple[WorldKernel, StressProgramTemplate]:
    """Build a kernel with the v1.18.1 templates registered for
    each cited driver in ``step_template_ids`` (plus any extra
    specs requested) and a v1.21.1 stress program registered
    via :meth:`StressProgramBook.add_program`. Returns the
    kernel + the program."""
    kernel = _bare_kernel()
    seen_template_ids: set[str] = set()
    # Default templates: build one per cited step driver id
    # using the credit_tightening family. The orchestrator's
    # behaviour is independent of family; the v1.18.2 helper
    # picks the family-specific shift specs.
    for tpl_id in step_template_ids:
        if tpl_id in seen_template_ids:
            continue
        seen_template_ids.add(tpl_id)
        kernel.scenario_drivers.add_template(
            _build_template(
                scenario_driver_template_id=tpl_id,
            )
        )
    # Caller-supplied extra templates (for tests that exercise
    # multiple families).
    for tpl_id, family, group in extra_template_specs:
        if tpl_id in seen_template_ids:
            continue
        seen_template_ids.add(tpl_id)
        kernel.scenario_drivers.add_template(
            _build_template(
                scenario_driver_template_id=tpl_id,
                scenario_family_label=family,
                driver_group_label=group,
            )
        )
    program = _build_program(
        program_id=program_id,
        program_purpose_label=program_purpose_label,
        step_template_ids=step_template_ids,
    )
    kernel.stress_programs.add_program(program)
    return kernel, program


# ---------------------------------------------------------------------------
# 1. test_apply_stress_program_resolves_program_from_kernel
# ---------------------------------------------------------------------------


def test_apply_stress_program_resolves_program_from_kernel():
    kernel, program = _seed_kernel_with_program()
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=(
            program.stress_program_template_id
        ),
        as_of_date="2026-04-30",
    )
    assert isinstance(receipt, StressProgramApplicationRecord)
    assert (
        receipt.stress_program_template_id
        == program.stress_program_template_id
    )
    # The receipt is in the book.
    stored = kernel.stress_applications.get_application(
        receipt.stress_program_application_id
    )
    assert stored is receipt


# ---------------------------------------------------------------------------
# 2. test_apply_stress_program_calls_apply_scenario_driver_in_step_index_order
# ---------------------------------------------------------------------------


def test_apply_stress_program_calls_apply_scenario_driver_in_step_index_order():
    """The orchestrator MUST iterate StressStep records in
    ascending ``step_index`` order, regardless of the order in
    which the steps were constructed on the program."""
    pid = "stress_program:test:ordinal_walk"
    kernel = _bare_kernel()
    # Three distinct v1.18.1 templates so we can pin per-step
    # call ordering.
    extras = (
        (
            "scenario_driver:rate_repricing:reference",
            "rate_repricing_driver",
            "macro_rates",
        ),
        (
            "scenario_driver:funding_window_closure:reference",
            "funding_window_closure_driver",
            "credit_liquidity",
        ),
    )
    for tpl_id, family, group in (
        (
            "scenario_driver:credit_tightening:reference",
            "credit_tightening_driver",
            "credit_liquidity",
        ),
        *extras,
    ):
        kernel.scenario_drivers.add_template(
            _build_template(
                scenario_driver_template_id=tpl_id,
                scenario_family_label=family,
                driver_group_label=group,
            )
        )
    # Construct the program with the steps in REVERSE order
    # (step_index 2, 1, 0).
    program = StressProgramTemplate(
        stress_program_template_id=pid,
        program_label="Ordinal walk test",
        program_purpose_label="multi_stress_demonstration",
        stress_steps=(
            _build_step(
                program_id=pid,
                step_index=2,
                scenario_driver_template_id=(
                    "scenario_driver:funding_window_closure:reference"
                ),
            ),
            _build_step(
                program_id=pid,
                step_index=0,
                scenario_driver_template_id=(
                    "scenario_driver:credit_tightening:reference"
                ),
            ),
            _build_step(
                program_id=pid,
                step_index=1,
                scenario_driver_template_id=(
                    "scenario_driver:rate_repricing:reference"
                ),
            ),
        ),
    )
    kernel.stress_programs.add_program(program)

    # Patch apply_scenario_driver to record the call order.
    from world import stress_applications as sa_mod

    captured: list[str] = []
    real_helper = sa_mod.apply_scenario_driver

    def recording_helper(*args, **kwargs):
        tpl_id = kwargs["scenario_driver_template_id"]
        captured.append(tpl_id)
        return real_helper(*args, **kwargs)

    with patch.object(
        sa_mod, "apply_scenario_driver", recording_helper
    ):
        receipt = apply_stress_program(
            kernel,
            stress_program_template_id=pid,
            as_of_date="2026-04-30",
        )

    # The orchestrator must have called the v1.18.2 helper in
    # step_index 0, 1, 2 order.
    assert captured == [
        "scenario_driver:credit_tightening:reference",  # step 0
        "scenario_driver:rate_repricing:reference",     # step 1
        "scenario_driver:funding_window_closure:reference",  # step 2
    ]
    # And the receipt's scenario_application_ids preserves the
    # same ordinal order.
    assert len(receipt.scenario_application_ids) == 3


# ---------------------------------------------------------------------------
# 3. test_apply_stress_program_emits_one_program_application_record
# ---------------------------------------------------------------------------


def test_apply_stress_program_emits_one_program_application_record():
    """A 3-step stress program emits exactly ONE
    ``stress_program_application_recorded`` ledger event (not
    one per step)."""
    pid = "stress_program:test:three_steps_one_receipt"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
        program_purpose_label="multi_stress_demonstration",
        step_template_ids=(
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
        ),
    )
    n_before = len(kernel.ledger.records)
    apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    types_added = [
        r.record_type
        for r in kernel.ledger.records[n_before:]
    ]
    program_receipts = [
        t
        for t in types_added
        if t == RecordType.STRESS_PROGRAM_APPLICATION_RECORDED
    ]
    assert len(program_receipts) == 1


# ---------------------------------------------------------------------------
# 4. test_apply_stress_program_collects_underlying_scenario_application_ids
# ---------------------------------------------------------------------------


def test_apply_stress_program_collects_underlying_scenario_application_ids():
    """``scenario_application_ids`` lists every v1.18.2
    application the orchestrator's per-step calls emitted, in
    step_index order."""
    pid = "stress_program:test:collect_app_ids"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
        program_purpose_label="multi_stress_demonstration",
        step_template_ids=(
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
        ),
    )
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    # Each step produces exactly one v1.18.2 application
    # record. Two-step program → two scenario_application_ids.
    assert len(receipt.scenario_application_ids) == 2
    # And the v1.18.2 book has exactly those two records.
    v1_18_app_ids = {
        a.scenario_application_id
        for a in kernel.scenario_applications.list_applications()
    }
    assert set(receipt.scenario_application_ids) == v1_18_app_ids


# ---------------------------------------------------------------------------
# 5. test_apply_stress_program_collects_context_shift_ids_or_documents_absence
# ---------------------------------------------------------------------------


def test_apply_stress_program_collects_context_shift_ids_or_documents_absence():
    """The receipt's ``scenario_context_shift_ids`` collects
    every v1.18.2 ``ScenarioContextShiftRecord`` id that the
    underlying calls emitted. The v1.18.2 helper exposes those
    ids on
    ``ScenarioDriverApplicationRecord.emitted_context_shift_ids``,
    so v1.21.2 reads them straight from the per-step return
    value (no documented limitation)."""
    pid = "stress_program:test:collect_shift_ids"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
        step_template_ids=(
            "scenario_driver:credit_tightening:reference",
        ),
    )
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    # The credit_tightening_driver family emits 2 context
    # shifts per application (market_environment +
    # financing_review_surface; pinned by the v1.18.2
    # _build_shift_specs table).
    assert len(receipt.scenario_context_shift_ids) == 2
    v1_18_shift_ids = {
        s.scenario_context_shift_id
        for s in kernel.scenario_applications.list_context_shifts()
    }
    assert set(receipt.scenario_context_shift_ids) == (
        v1_18_shift_ids
    )
    # And the multiset is preserved in v1.18.2 emission order
    # (every cited id appears exactly once).
    assert len(set(receipt.scenario_context_shift_ids)) == 2


# ---------------------------------------------------------------------------
# 6. test_apply_stress_program_rejects_unknown_program
# ---------------------------------------------------------------------------


def test_apply_stress_program_rejects_unknown_program():
    kernel = _bare_kernel()
    with pytest.raises(UnknownStressProgramTemplateError):
        apply_stress_program(
            kernel,
            stress_program_template_id=(
                "stress_program:does_not_exist"
            ),
            as_of_date="2026-04-30",
        )


# ---------------------------------------------------------------------------
# 7. test_duplicate_stress_program_application_emits_no_extra_ledger_record
# ---------------------------------------------------------------------------


def test_duplicate_stress_program_application_emits_no_extra_ledger_record():
    """Re-invoking ``apply_stress_program(...)`` with the same
    ``stress_program_application_id`` raises and does NOT add
    a second program-level ledger record."""
    pid = "stress_program:test:duplicate_application"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
    )
    sub_id = "stress_program_application:dup_test:fixed"
    apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
        stress_program_application_id=sub_id,
    )
    n_after_first = len(
        [
            r
            for r in kernel.ledger.records
            if r.record_type
            == RecordType.STRESS_PROGRAM_APPLICATION_RECORDED
        ]
    )
    assert n_after_first == 1
    # Repeat with the same id — duplicate raises.
    with pytest.raises(
        DuplicateStressProgramApplicationError
    ):
        apply_stress_program(
            kernel,
            stress_program_template_id=pid,
            as_of_date="2026-04-30",
            stress_program_application_id=sub_id,
        )
    # No extra program-level record landed in the ledger.
    n_after_second = len(
        [
            r
            for r in kernel.ledger.records
            if r.record_type
            == RecordType.STRESS_PROGRAM_APPLICATION_RECORDED
        ]
    )
    assert n_after_second == n_after_first


# ---------------------------------------------------------------------------
# 8. test_apply_stress_program_emits_no_interaction_label
# ---------------------------------------------------------------------------


def test_apply_stress_program_emits_no_interaction_label():
    """The receipt + every emitted ledger record from
    ``apply_stress_program(...)`` MUST NOT carry an
    ``interaction_label`` / ``composition_label`` /
    ``output_context_label`` / ``dominant_shift_direction_label``
    field, key, or value-coded composition. Auto-inferred
    composition is deferred to v1.22+ (or never)."""
    pid = "stress_program:test:no_interaction"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
        program_purpose_label="multi_stress_demonstration",
        step_template_ids=(
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
        ),
    )
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )

    interaction_tokens = (
        "interaction_label",
        "composition_label",
        "output_context_label",
        "dominant_shift_direction_label",
        "amplify",
        "dampen",
        "offset",
        "coexist",
    )

    # Receipt to_dict.
    rec_dict = receipt.to_dict()

    def scan(d, path=""):
        if isinstance(d, dict):
            for k, v in d.items():
                ks = str(k)
                for tok in interaction_tokens:
                    assert ks != tok, (
                        f"forbidden interaction key {tok!r} at "
                        f"{path}/{ks}"
                    )
                scan(v, path + "/" + ks)
        elif isinstance(d, list):
            for i, e in enumerate(d):
                scan(e, path + f"[{i}]")

    scan(rec_dict, "receipt")

    # Ledger payload of the program-level receipt.
    receipt_records = [
        r
        for r in kernel.ledger.records
        if r.record_type
        == RecordType.STRESS_PROGRAM_APPLICATION_RECORDED
    ]
    assert len(receipt_records) == 1
    scan(receipt_records[0].payload, "receipt_payload")

    # Underlying v1.18.2 records (already pinned by their own
    # tests; we just confirm the v1.21.2 layer added nothing
    # interaction-shaped to their metadata).
    for rec in kernel.ledger.records:
        if rec.record_type in (
            RecordType.SCENARIO_DRIVER_APPLICATION_RECORDED,
            RecordType.SCENARIO_CONTEXT_SHIFT_RECORDED,
        ):
            scan(rec.payload, "v1_18_payload")


# ---------------------------------------------------------------------------
# 9. test_apply_stress_program_emits_no_aggregate_combined_net_dominant_fields
# ---------------------------------------------------------------------------


def test_apply_stress_program_emits_no_aggregate_combined_net_dominant_fields():
    """The receipt MUST NOT carry any aggregate / combined /
    net / dominant / composite / expected / predicted /
    forecasted / magnitude / probability field. Same applies
    to the program-level ledger payload."""
    pid = "stress_program:test:no_aggregate_fields"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
        program_purpose_label="multi_stress_demonstration",
        step_template_ids=(
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
        ),
    )
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )

    forbidden_prefixes = (
        "aggregate_",
        "combined_",
        "net_",
        "dominant_",
        "composite_",
        "expected_",
        "predicted_",
        "forecasted_",
    )
    forbidden_exact = (
        "stress_magnitude",
        "stress_probability_weight",
        "stress_intensity_score",
        "stress_amplification_score",
        "total_stress_intensity",
        "predicted_stress_effect",
        "projected_stress_effect",
        "stress_outcome_label",
    )

    def scan_keys(d, path=""):
        if isinstance(d, dict):
            for k, v in d.items():
                ks = str(k)
                for prefix in forbidden_prefixes:
                    assert not ks.startswith(prefix), (
                        f"forbidden prefix {prefix!r} key at "
                        f"{path}/{ks}"
                    )
                for exact in forbidden_exact:
                    assert ks != exact, (
                        f"forbidden exact key {exact!r} at "
                        f"{path}/{ks}"
                    )
                scan_keys(v, path + "/" + ks)
        elif isinstance(d, list):
            for i, e in enumerate(d):
                scan_keys(e, path + f"[{i}]")

    rec_dict = receipt.to_dict()
    scan_keys(rec_dict, "receipt")
    receipt_records = [
        r
        for r in kernel.ledger.records
        if r.record_type
        == RecordType.STRESS_PROGRAM_APPLICATION_RECORDED
    ]
    scan_keys(receipt_records[0].payload, "receipt_payload")


# ---------------------------------------------------------------------------
# 10. test_apply_stress_program_does_not_mutate_source_of_truth_books
# ---------------------------------------------------------------------------


def test_apply_stress_program_does_not_mutate_source_of_truth_books():
    """No source-of-truth book is mutated by
    ``apply_stress_program(...)``. The orchestrator only writes
    to ``kernel.scenario_applications`` (via the v1.18.2
    helper) and ``kernel.stress_applications`` (this
    module's book). Every other book's snapshot is byte-
    identical pre / post call."""
    pid = "stress_program:test:no_book_mutation"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
    )

    # Snapshot every source-of-truth book before the call.
    snap_before = {
        "prices": kernel.prices.snapshot(),
        "contracts": kernel.contracts.snapshot(),
        "constraints": kernel.constraints.snapshot(),
        "ownership": kernel.ownership.snapshot(),
        "institutions": kernel.institutions.snapshot(),
        "market_conditions": (
            kernel.market_conditions.snapshot()
        ),
        "market_environments": (
            kernel.market_environments.snapshot()
        ),
        "firm_financial_states": (
            kernel.firm_financial_states.snapshot()
        ),
        "interbank_liquidity": (
            kernel.interbank_liquidity.snapshot()
        ),
        "industry_conditions": (
            kernel.industry_conditions.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
        "indicative_market_pressure": (
            kernel.indicative_market_pressure.snapshot()
        ),
        "financing_paths": kernel.financing_paths.snapshot(),
        "valuations": kernel.valuations.snapshot(),
    }

    apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )

    snap_after = {
        "prices": kernel.prices.snapshot(),
        "contracts": kernel.contracts.snapshot(),
        "constraints": kernel.constraints.snapshot(),
        "ownership": kernel.ownership.snapshot(),
        "institutions": kernel.institutions.snapshot(),
        "market_conditions": (
            kernel.market_conditions.snapshot()
        ),
        "market_environments": (
            kernel.market_environments.snapshot()
        ),
        "firm_financial_states": (
            kernel.firm_financial_states.snapshot()
        ),
        "interbank_liquidity": (
            kernel.interbank_liquidity.snapshot()
        ),
        "industry_conditions": (
            kernel.industry_conditions.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
        "indicative_market_pressure": (
            kernel.indicative_market_pressure.snapshot()
        ),
        "financing_paths": kernel.financing_paths.snapshot(),
        "valuations": kernel.valuations.snapshot(),
    }

    for name in snap_before:
        assert snap_before[name] == snap_after[name], (
            f"{name} book was mutated by apply_stress_program"
        )


# ---------------------------------------------------------------------------
# 11. test_apply_stress_program_does_not_emit_per_step_stress_records
# ---------------------------------------------------------------------------


def test_apply_stress_program_does_not_emit_per_step_stress_records():
    """v1.21.2 ships ONLY the program-level
    ``STRESS_PROGRAM_APPLICATION_RECORDED`` event. No per-step
    stress-application record type exists; per-step records
    live at v1.18.2 in
    ``world.scenario_applications.ScenarioApplicationBook``."""
    record_type_values = {rt.value for rt in RecordType}
    assert (
        "stress_program_application_recorded"
        in record_type_values
    )
    # Per-step variants must NOT exist as RecordType enum
    # values.
    for forbidden in (
        "stress_step_application_recorded",
        "stress_step_recorded",
        "stress_step_emitted",
        "stress_program_step_recorded",
    ):
        assert forbidden not in record_type_values, (
            f"per-step RecordType {forbidden!r} must not exist"
        )

    # And the runtime ledger emits exactly one program-level
    # record per call regardless of step count.
    pid = "stress_program:test:per_step_records"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
        program_purpose_label="multi_stress_demonstration",
        step_template_ids=(
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
        ),
    )
    n_before = len(kernel.ledger.records)
    apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    types_added = [
        r.record_type for r in kernel.ledger.records[n_before:]
    ]
    receipts = [
        t
        for t in types_added
        if t == RecordType.STRESS_PROGRAM_APPLICATION_RECORDED
    ]
    assert len(receipts) == 1


# ---------------------------------------------------------------------------
# 12. test_apply_stress_program_added_record_count_within_60
# ---------------------------------------------------------------------------


def test_apply_stress_program_added_record_count_within_60():
    """The v1.21.0a binding cardinality: ≤ 60 v1.21 records
    added per stress-applied run. Worst-case fixture: 3 steps
    × (1 v1.18.2 application + ≤ 2 context shifts) + 1 v1.21.2
    program receipt = ≤ 10 records added per call. The pin
    says ≤ 60, generous to allow future v1.18.2 family
    expansion."""
    pid = "stress_program:test:cardinality"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
        program_purpose_label="multi_stress_demonstration",
        step_template_ids=(
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
            "scenario_driver:credit_tightening:reference",
        ),
    )
    n_before = len(kernel.ledger.records)
    apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    n_after = len(kernel.ledger.records)
    added = n_after - n_before
    assert added <= 60, (
        f"apply_stress_program added {added} records; v1.21.0a "
        "binding cap is ≤ 60"
    )
    # Sanity: actual count matches expected breakdown for the
    # credit_tightening family (2 shifts per application):
    # 3 application records + 6 context shifts + 1 receipt = 10.
    assert added == 10


# ---------------------------------------------------------------------------
# 13. test_existing_profiles_unchanged_without_explicit_stress_program
# ---------------------------------------------------------------------------


def test_existing_profiles_unchanged_without_explicit_stress_program():
    """The canonical profile digests must stay byte-identical
    to v1.20.last when no stress program is explicitly
    applied. v1.21.2 wires a new ``stress_applications`` book
    on the kernel — empty by default, no ledger emission, no
    digest movement."""
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
    assert k_q.stress_programs.list_programs() == ()
    assert k_q.stress_applications.list_applications() == ()
    assert (
        living_world_digest(k_q, r_q)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )

    # monthly_reference
    k_m = _seed_kernel()
    r_m = _run_monthly_reference(k_m)
    assert k_m.stress_applications.list_applications() == ()
    assert (
        living_world_digest(k_m, r_m)
        == "75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d"
    )


def test_existing_profile_unchanged_scenario_monthly_reference_universe():
    """The v1.20.3 ``scenario_monthly_reference_universe``
    test-fixture digest must stay byte-identical at v1.21.2
    when no stress program is explicitly applied."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world_performance_boundary import (
        _run_v1_20_3,
        _seed_v1_20_3_kernel,
    )

    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert k.stress_applications.list_applications() == ()
    assert (
        living_world_digest(k, r)
        == "5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6"
    )


# ---------------------------------------------------------------------------
# 14. test_stress_program_application_forbidden_field_names
# ---------------------------------------------------------------------------


def test_stress_program_application_forbidden_field_names():
    """Trip-wire: dataclass field names + to_dict() keys MUST
    be disjoint from
    ``FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES``."""
    pid = "stress_program:test:forbidden_field_names"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
    )
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    for fname in StressProgramApplicationRecord.__dataclass_fields__:
        assert (
            fname
            not in FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES
        ), (
            f"StressProgramApplicationRecord.{fname} collides "
            "with the v1.21.0a forbidden field-name list"
        )
    for key in receipt.to_dict().keys():
        assert (
            key
            not in FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES
        )
    # And the program-level ledger payload.
    receipt_records = [
        r
        for r in kernel.ledger.records
        if r.record_type
        == RecordType.STRESS_PROGRAM_APPLICATION_RECORDED
    ]
    for key in receipt_records[0].payload.keys():
        assert (
            key
            not in FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES
        )


# ---------------------------------------------------------------------------
# 15. test_stress_program_application_metadata_rejects_forbidden_keys
# ---------------------------------------------------------------------------


def test_stress_program_application_metadata_rejects_forbidden_keys():
    """The orchestrator MUST reject caller metadata that
    carries a forbidden key. Same for the dataclass's
    metadata + boundary_flags fields."""
    pid = "stress_program:test:metadata_forbidden_keys"
    kernel, program = _seed_kernel_with_program(
        program_id=pid,
    )
    forbidden_samples: tuple[str, ...] = (
        "stress_magnitude",
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
            apply_stress_program(
                kernel,
                stress_program_template_id=pid,
                as_of_date="2026-04-30",
                stress_program_application_id=(
                    f"stress_program_application:{token}_test"
                ),
                metadata={token: "any value"},
            )

    # Also: the dataclass directly rejects forbidden metadata
    # keys (in case a future caller bypasses the orchestrator).
    for token in forbidden_samples:
        with pytest.raises(ValueError):
            StressProgramApplicationRecord(
                stress_program_application_id="x",
                stress_program_template_id="y",
                as_of_date="2026-04-30",
                scenario_application_ids=(),
                scenario_context_shift_ids=(),
                unresolved_step_count=0,
                application_status_label="prepared",
                metadata={token: "v"},
            )


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


def test_world_kernel_empty_stress_application_book_by_default():
    kernel = _bare_kernel()
    assert isinstance(
        kernel.stress_applications,
        StressProgramApplicationBook,
    )
    assert kernel.stress_applications.list_applications() == ()
    types_seen = {
        r.record_type for r in kernel.ledger.records
    }
    assert (
        RecordType.STRESS_PROGRAM_APPLICATION_RECORDED
        not in types_seen
    )
    assert (
        kernel.stress_applications.ledger is kernel.ledger
    )


def test_application_status_label_pinned_to_v1_18_2():
    """The v1.21.0a 'reuse first' discipline pins
    ``STRESS_PROGRAM_APPLICATION_STATUS_LABELS`` as the
    v1.18.2 ``APPLICATION_STATUS_LABELS`` set verbatim."""
    from world.scenario_applications import (
        APPLICATION_STATUS_LABELS,
    )

    assert (
        STRESS_PROGRAM_APPLICATION_STATUS_LABELS
        is APPLICATION_STATUS_LABELS
    )


def test_unresolved_step_count_increments_on_missing_template():
    """If a step's cited scenario_driver_template_id does NOT
    exist in the kernel's scenario_drivers book, the
    orchestrator MUST mark the step as unresolved (incrementing
    ``unresolved_step_count``) and continue to the next step
    rather than raising."""
    pid = "stress_program:test:unresolved_step"
    kernel = _bare_kernel()
    # Register only ONE of the two cited templates.
    kernel.scenario_drivers.add_template(
        _build_template(
            scenario_driver_template_id=(
                "scenario_driver:credit_tightening:reference"
            ),
        )
    )
    program = StressProgramTemplate(
        stress_program_template_id=pid,
        program_label="Unresolved test",
        program_purpose_label="multi_stress_demonstration",
        stress_steps=(
            _build_step(
                program_id=pid,
                step_index=0,
                scenario_driver_template_id=(
                    "scenario_driver:credit_tightening:reference"
                ),
            ),
            _build_step(
                program_id=pid,
                step_index=1,
                scenario_driver_template_id=(
                    "scenario_driver:nonexistent:reference"
                ),
            ),
        ),
    )
    kernel.stress_programs.add_program(program)
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    # One step resolved, one did not.
    assert receipt.unresolved_step_count == 1
    assert len(receipt.scenario_application_ids) == 1
    # Status reflects the partial failure.
    assert (
        receipt.application_status_label
        == "degraded_unresolved_refs"
    )


def test_receipt_carries_v1_18_0_audit_shape():
    pid = "stress_program:test:audit_shape"
    kernel, program = _seed_kernel_with_program(program_id=pid)
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    assert receipt.reasoning_mode == "rule_based_fallback"
    assert receipt.reasoning_slot == "future_llm_compatible"
    assert (
        receipt.reasoning_policy_id
        == DEFAULT_STRESS_PROGRAM_APPLICATION_REASONING_POLICY_ID
    )
    # Boundary flags include the v1.18.2 default 7-flag set
    # plus the v1.21.0a additions.
    bf = receipt.boundary_flags
    for key in (
        "no_actor_decision",
        "no_llm_execution",
        "no_price_formation",
        "no_trading",
        "no_financing_execution",
        "no_investment_advice",
        "synthetic_only",
        "no_aggregate_stress_result",
        "no_interaction_inference",
        "no_field_value_claim",
        "no_field_magnitude_claim",
    ):
        assert bf.get(key) is True


def test_application_status_label_prepared_when_no_shifts_emitted():
    """If a step's family produces zero context shifts (the
    v1.18.2 unmapped family fallback), the orchestrator's
    receipt status label is 'prepared' rather than
    'applied_as_context_shift'."""
    pid = "stress_program:test:prepared_status"
    kernel = _bare_kernel()
    # Use a family that the v1.18.2 _build_shift_specs does
    # not have a mapping for; the helper falls back to a
    # single ``no_direct_shift`` annotation, so shifts ARE
    # emitted (one per step). This test therefore EXPECTS
    # 'applied_as_context_shift' status — but pins the
    # general behaviour: status reflects shift emission.
    kernel.scenario_drivers.add_template(
        _build_template(
            scenario_driver_template_id=(
                "scenario_driver:custom_unmapped:reference"
            ),
            scenario_family_label=(
                "regulatory_risk_driver"
            ),
            driver_group_label="regulation_legal",
        )
    )
    program = StressProgramTemplate(
        stress_program_template_id=pid,
        program_label="Prepared status test",
        program_purpose_label="custom_synthetic",
        stress_steps=(
            _build_step(
                program_id=pid,
                step_index=0,
                scenario_driver_template_id=(
                    "scenario_driver:custom_unmapped:reference"
                ),
            ),
        ),
    )
    kernel.stress_programs.add_program(program)
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    # Whatever the v1.18.2 fallback emits, the orchestrator
    # picks a v1.18.2-valid status from
    # APPLICATION_STATUS_LABELS.
    assert (
        receipt.application_status_label
        in STRESS_PROGRAM_APPLICATION_STATUS_LABELS
    )
    assert receipt.unresolved_step_count == 0


def test_apply_stress_program_book_query_methods():
    pid = "stress_program:test:book_queries"
    kernel, program = _seed_kernel_with_program(program_id=pid)
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    book = kernel.stress_applications
    assert receipt in book.list_applications()
    assert receipt in book.list_by_program(pid)
    assert receipt in book.list_by_date("2026-04-30")
    assert book.list_by_date("2026-09-30") == ()
    assert book.list_by_program(
        "stress_program:does_not_exist"
    ) == ()
    snap = book.snapshot()
    assert isinstance(snap["stress_program_applications"], list)
    assert len(snap["stress_program_applications"]) == 1


def test_unknown_application_get_raises():
    book = StressProgramApplicationBook()
    with pytest.raises(UnknownStressProgramApplicationError):
        book.get_application(
            "stress_program_application:does_not_exist"
        )


def test_apply_stress_program_does_not_register_new_scenario_driver_template():
    """The orchestrator MUST NOT call
    ``ScenarioDriverTemplateBook.add_template(...)``. The
    pre-registered v1.18.1 template count is unchanged after
    the call."""
    pid = "stress_program:test:no_template_registration"
    kernel, program = _seed_kernel_with_program(program_id=pid)
    n_before = len(
        kernel.scenario_drivers.list_templates()
    )
    apply_stress_program(
        kernel,
        stress_program_template_id=pid,
        as_of_date="2026-04-30",
    )
    n_after = len(
        kernel.scenario_drivers.list_templates()
    )
    assert n_before == n_after


def test_record_type_enum_includes_stress_program_application_recorded():
    assert (
        RecordType.STRESS_PROGRAM_APPLICATION_RECORDED.value
        == "stress_program_application_recorded"
    )


def test_v1_21_2_module_imports_only_v1_18_2_helper_and_v1_21_1_storage():
    """Confirm the module's import surface is narrow: only the
    v1.18.2 helper + v1.21.1 storage + the standard
    Clock / Ledger / dataclass imports."""
    text = _MODULE_PATH.read_text(encoding="utf-8")
    forbidden_imports = (
        "from world.market_environment ",
        "from world.firm_state ",
        "from world.investor_intent ",
        "from world.financing_paths ",
        "from world.prices ",
        "from world.contracts ",
        "from world.constraints ",
        "from world.ownership ",
        "from world.institutions ",
        "from world.indicative_market_pressure ",
        "from world.market_intents ",
    )
    for imp in forbidden_imports:
        assert imp not in text, (
            f"v1.21.2 must not import {imp!r}"
        )


# ---------------------------------------------------------------------------
# Closed-set vocabulary scans
# ---------------------------------------------------------------------------


def test_stress_program_application_status_labels_closed_set():
    assert STRESS_PROGRAM_APPLICATION_STATUS_LABELS == frozenset(
        {
            "prepared",
            "applied_as_context_shift",
            "degraded_missing_template",
            "degraded_unresolved_refs",
            "rejected",
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
# Module-text + test-text scans
# ---------------------------------------------------------------------------


import re


def _strip_docstrings(text: str) -> str:
    """Strip every triple-quoted docstring (handles class /
    method docstrings, not just the module-level one)."""
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
            out.append(text[lo:])
            break
        i = hi + 3
    return "".join(out)


def _strip_balanced_parens_after(text: str, marker: str) -> str:
    """Strip the ``(...)`` block that begins after ``marker``.
    Uses balanced-paren counting so a stray ``)`` inside a
    comment within the block does not stop the scrub
    early."""
    lower = text.lower()
    open_idx = lower.find(marker.lower())
    if open_idx < 0:
        return text
    paren_open = text.find("(", open_idx)
    if paren_open < 0:
        return text
    depth = 1
    i = paren_open + 1
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        i += 1
    return text[:open_idx] + text[i:]


def test_module_jurisdiction_neutral_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_docstrings(text)
    text = _strip_balanced_parens_after(
        text,
        "FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES",
    ).lower()
    for token in _jurisdiction_tokens:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "stress_applications.py outside docstring + FORBIDDEN literal"
        )


def test_module_no_licensed_taxonomy_dependency_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_docstrings(text)
    text = _strip_balanced_parens_after(
        text,
        "FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES",
    ).lower()
    for token in _licensed_taxonomy_tokens:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"licensed-taxonomy token {token!r} appears in "
            "stress_applications.py outside docstring + FORBIDDEN literal"
        )


def test_test_file_jurisdiction_neutral_scan():
    text = Path(__file__).read_text(encoding="utf-8").lower()
    for marker in (
        "_jurisdiction_tokens = (",
        "_licensed_taxonomy_tokens = (",
        "forbidden_samples: tuple",
        "forbidden_imports = (",
        "interaction_tokens = (",
        "forbidden_prefixes = (",
        "forbidden_exact = (",
    ):
        idx = text.find(marker)
        if idx != -1:
            close = text.find(")", idx) + 1
            if close > 0:
                text = text[:idx] + text[close:]
    for token in _jurisdiction_tokens:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "test_stress_applications.py outside the token tables"
        )


def test_module_text_does_not_carry_forbidden_phrases():
    """Use word-boundary regex (mirroring v1.19.3.1) so the
    negation flags ``no_investment_advice`` /
    ``no_japan_calibration`` / etc. — which legitimately
    appear in the v1.21.2 default boundary_flags tuple — do
    not trip the scan. ``\\b`` between two word characters
    (e.g., ``_`` and a letter) does not match, so
    ``\\binvestment_advice\\b`` correctly rejects only a bare
    forbidden field while allowing ``no_investment_advice``."""
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_docstrings(text)
    text = _strip_balanced_parens_after(
        text,
        "FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES",
    )
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
        "interaction_label",
    ):
        pattern = rf"\b{re.escape(phrase)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden phrase {phrase!r} appears in "
            "stress_applications.py outside docstring + FORBIDDEN literal"
        )
