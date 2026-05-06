"""
v1.23.2 — Validation Category 1: Determinism.

The v1.21.3 stress field readout already asserts that two
consecutive ``build_stress_field_readout(...)`` calls on the
same kernel state produce the same ``StressFieldReadout``
``to_dict()`` output (see ``tests/test_stress_readout.py``
``test_stress_field_readout_is_read_only``). v1.23.2 promotes
this contract to a **named validation pin** that covers all
three load-bearing surfaces:

- the v1.21.3 markdown summary (byte-equal across two
  consecutive renders);
- the ``StressFieldReadout.to_dict()`` output (byte-equal
  across two consecutive readout builds);
- the v1.22.1 export entry (byte-equal across two consecutive
  ``stress_field_readout_to_export_entry`` calls).

The pin is read-only: it builds two consecutive readouts +
exports + markdown renders on the SAME kernel state and
asserts byte-identity. Failing this pin means the readout
layer accidentally introduced wall-clock / random-source /
unordered-iteration nondeterminism — a regression class the
existing per-attribute equality test would catch only by
coincidence.

The pin asserts no causality, no magnitude, no probability,
no interaction inference; it asserts the **format** is
deterministic.
"""

from __future__ import annotations

from datetime import date

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.scenario_drivers import ScenarioDriverTemplate
from world.scheduler import Scheduler
from world.state import State
from world.stress_applications import apply_stress_program
from world.stress_programs import (
    StressProgramTemplate,
    StressStep,
)
from world.stress_readout import (
    build_stress_field_readout,
    render_stress_field_summary_markdown,
)
from world.stress_readout_export import (
    stress_field_readout_to_export_entry,
)


# ---------------------------------------------------------------------------
# Local fixture (mirrors ``tests/test_stress_readout.py`` happy
# path — minimal, deterministic, no real-data).
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
) -> ScenarioDriverTemplate:
    return ScenarioDriverTemplate(
        scenario_driver_template_id=(
            scenario_driver_template_id
        ),
        scenario_family_label="credit_tightening_driver",
        driver_group_label="credit_liquidity",
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


def _seed_two_step_kernel() -> tuple[WorldKernel, str]:
    """Two-step program — exercises multi-step ordinal walking
    + per-step v1.18.2 record emission. Return
    ``(kernel, stress_program_application_id)``."""
    kernel = _bare_kernel()
    tpl_ids = (
        "scenario_driver:credit_tightening:reference",
        "scenario_driver:funding_window_closure:reference",
    )
    for tpl_id in tpl_ids:
        kernel.scenario_drivers.add_template(
            _build_template(scenario_driver_template_id=tpl_id)
        )
    program_id = "stress_program:test_validation_determinism:two_step"
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="Two-step determinism pin",
        program_purpose_label="twin_credit_funding_stress",
        stress_steps=(
            StressStep(
                stress_step_id=f"{program_id}:step:0",
                parent_stress_program_template_id=program_id,
                step_index=0,
                scenario_driver_template_id=tpl_ids[0],
                event_date_policy_label="quarter_end",
                scheduled_month_label="month_04",
            ),
            StressStep(
                stress_step_id=f"{program_id}:step:1",
                parent_stress_program_template_id=program_id,
                step_index=1,
                scenario_driver_template_id=tpl_ids[1],
                event_date_policy_label="quarter_end",
                scheduled_month_label="month_04",
            ),
        ),
    )
    kernel.stress_programs.add_program(program)
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=program_id,
        as_of_date="2026-04-30",
    )
    return kernel, receipt.stress_program_application_id


# ---------------------------------------------------------------------------
# Pin — ``test_validation_determinism_pin_v1_23_2`` (split
# into three named sub-tests for diagnostic clarity).
# ---------------------------------------------------------------------------


def test_validation_determinism_pin_v1_23_2_readout_dict() -> None:
    """Same kernel state + same arguments → byte-identical
    ``StressFieldReadout.to_dict()`` across two consecutive
    builds. v1.21.3 contract; v1.23.2 named pin."""
    kernel, receipt_id = _seed_two_step_kernel()
    a = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    b = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    assert a.to_dict() == b.to_dict()


def test_validation_determinism_pin_v1_23_2_markdown_summary() -> None:
    """Same readout → byte-identical markdown summary across
    two consecutive renders. The v1.21.3 renderer must not
    introduce wall-clock / random-source nondeterminism."""
    kernel, receipt_id = _seed_two_step_kernel()
    a = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    b = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    md_a = render_stress_field_summary_markdown(a)
    md_b = render_stress_field_summary_markdown(b)
    assert md_a == md_b
    # Cross-check: rendering the *same* readout twice is also
    # byte-identical (catches per-call mutation in the
    # renderer).
    assert (
        render_stress_field_summary_markdown(a)
        == render_stress_field_summary_markdown(a)
    )


def test_validation_determinism_pin_v1_23_2_export_entry() -> None:
    """Same readout → byte-identical v1.22.1 export entry
    across two consecutive projections."""
    kernel, receipt_id = _seed_two_step_kernel()
    a = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    b = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    entry_a = stress_field_readout_to_export_entry(a)
    entry_b = stress_field_readout_to_export_entry(b)
    assert entry_a == entry_b
