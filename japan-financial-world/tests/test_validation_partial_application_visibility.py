"""
v1.23.2 — Validation Category 4: Partial-application visibility.

When ``readout.is_partial`` is True (at least one stress
step did not produce a v1.18.2 application record), the
v1.21.3 readout MUST surface every required visibility
field — and that visibility must propagate through both the
v1.21.3 markdown summary AND the v1.22.1 export entry.

The v1.21.3 dataclass already enforces the field-level
visibility (``unresolved_step_count``, ``unresolved_step_ids``,
``unresolved_reason_labels``, ``warnings``); v1.23.2 adds an
end-to-end pin that confirms the visibility makes it through
both downstream surfaces unchanged. A regression that
silently dropped the partial-application banner from either
surface would otherwise let a downstream reviewer mistake a
partial application for a complete one.

Pin name:
``test_validation_partial_application_visibility_pin_v1_23_2``.
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
# Local fixture: build a kernel where one of two cited
# templates is intentionally absent → step-1 is unresolved.
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


def _seed_partial_kernel() -> tuple[WorldKernel, str]:
    kernel = _bare_kernel()
    kernel.scenario_drivers.add_template(_build_template())
    program_id = (
        "stress_program:test_validation_partial:two_step"
    )
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="Partial visibility pin",
        program_purpose_label="multi_stress_demonstration",
        stress_steps=(
            StressStep(
                stress_step_id=f"{program_id}:step:0",
                parent_stress_program_template_id=program_id,
                step_index=0,
                scenario_driver_template_id=(
                    "scenario_driver:credit_tightening:reference"
                ),
                event_date_policy_label="quarter_end",
                scheduled_month_label="month_04",
            ),
            StressStep(
                stress_step_id=f"{program_id}:step:1",
                parent_stress_program_template_id=program_id,
                step_index=1,
                # The template for this step is intentionally
                # NOT registered → step 1 is unresolved with
                # reason ``template_missing``.
                scenario_driver_template_id=(
                    "scenario_driver:nonexistent:reference"
                ),
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
# 1. Markdown surface — PARTIAL APPLICATION banner +
#    per-step reason rendering.
# ---------------------------------------------------------------------------


def test_validation_partial_application_visibility_pin_v1_23_2_markdown() -> None:
    """When ``readout.is_partial`` is True, the v1.21.3
    markdown summary MUST surface a clear PARTIAL APPLICATION
    banner before any other section, list each unresolved
    step's reason label, and report the resolved /
    unresolved / total step counts."""
    kernel, receipt_id = _seed_partial_kernel()
    readout = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    assert readout.is_partial, (
        "fixture should be partial — second step's template "
        "is intentionally missing"
    )
    md = render_stress_field_summary_markdown(readout)

    # PARTIAL APPLICATION banner must appear before the first
    # section heading after the title (i.e., before any of
    # ``## Emitted scenario applications`` etc.).
    banner_idx = md.find("PARTIAL APPLICATION")
    assert banner_idx >= 0, (
        "markdown summary missing PARTIAL APPLICATION banner"
    )
    first_emission_section_idx = md.find(
        "## Emitted scenario applications"
    )
    assert first_emission_section_idx > banner_idx, (
        "PARTIAL APPLICATION banner must precede the first "
        "emission section"
    )

    # The reason label is rendered for the unresolved step.
    assert "template_missing" in md
    # The unresolved step id is rendered.
    for step_id in readout.unresolved_step_ids:
        assert step_id in md, (
            f"unresolved step id {step_id!r} not rendered "
            "in markdown summary"
        )
    # Step counts visible.
    assert (
        f"Total step count**: {readout.total_step_count}"
        in md
    )
    assert (
        f"Resolved step count**: "
        f"{readout.resolved_step_count}"
        in md
    )
    assert (
        f"Unresolved step count**: "
        f"{readout.unresolved_step_count}"
        in md
    )


# ---------------------------------------------------------------------------
# 2. v1.22.1 export-entry surface — every visibility field
#    is preserved verbatim.
# ---------------------------------------------------------------------------


def test_validation_partial_application_visibility_pin_v1_23_2_export() -> None:
    """The v1.22.1 export entry preserves every
    partial-application visibility field — ``is_partial``,
    ``unresolved_step_count``, ``unresolved_step_ids``,
    ``unresolved_reason_labels``, ``resolved_step_count``,
    ``total_step_count``, ``warnings`` — verbatim from the
    readout."""
    kernel, receipt_id = _seed_partial_kernel()
    readout = build_stress_field_readout(
        kernel, stress_program_application_id=receipt_id
    )
    entry = stress_field_readout_to_export_entry(readout)

    assert entry["is_partial"] is True
    assert (
        entry["unresolved_step_count"]
        == readout.unresolved_step_count
    )
    assert (
        entry["resolved_step_count"]
        == readout.resolved_step_count
    )
    assert (
        entry["total_step_count"]
        == readout.total_step_count
    )
    assert entry["unresolved_step_ids"] == list(
        readout.unresolved_step_ids
    )
    assert entry["unresolved_reason_labels"] == list(
        readout.unresolved_reason_labels
    )
    # Warnings include a partial-application warning entry.
    assert entry["warnings"] == list(readout.warnings)
    assert any(
        "partial application" in w.lower()
        for w in entry["warnings"]
    ), (
        "export entry warnings missing the "
        "'partial application' summary"
    )
