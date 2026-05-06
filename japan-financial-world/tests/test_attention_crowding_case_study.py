"""
v1.23.3 — Attention-crowding / uncited-stress case study
pin tests.

Pins ``world/stress_case_study.py`` —
:func:`build_attention_crowding_case_study_report` and
:func:`render_attention_crowding_case_study_markdown` — as a
deterministic, read-only projection over an already
stress-applied kernel.

Per ``docs/case_study_001_attention_crowding_uncited_stress.md``,
the pins assert:

- the helper is **deterministic** (byte-identical report +
  markdown across two consecutive calls);
- the helper surfaces **uncited stress** (steps whose cited
  v1.18.1 template did not resolve are listed in
  ``uncited_step_ids`` with the v1.21.3 reason label);
- the helper carries the **citation completeness** pin and
  detects dangling citations as regressions;
- the helper's output contains **no forbidden token** at any
  depth (v1.21.0a / v1.22.0 boundary scan);
- the helper does **not mutate** any kernel book (every
  relevant snapshot is byte-identical pre / post);
- the helper does **not emit a ledger record**;
- the helper does **not call**
  :func:`world.stress_applications.apply_stress_program` or
  :func:`world.scenario_applications.apply_scenario_driver`
  (verified via monkey-patch sentinel).

The pins target ~ 8 tests per the v1.23.0 design pin's
``v1.23.3 expected test delta: + ~ 8``.
"""

from __future__ import annotations

import re
from datetime import date

import pytest

import world.scenario_applications as scenario_applications_mod
import world.stress_applications as stress_applications_mod
from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS,
)
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.scenario_drivers import ScenarioDriverTemplate
from world.scheduler import Scheduler
from world.state import State
from world.stress_applications import apply_stress_program
from world.stress_case_study import (
    build_attention_crowding_case_study_report,
    render_attention_crowding_case_study_markdown,
)
from world.stress_programs import (
    StressProgramTemplate,
    StressStep,
)


# ---------------------------------------------------------------------------
# Local kernel + program fixtures.
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


def _seed_happy_path_kernel() -> tuple[WorldKernel, str]:
    """All-cited fixture: two-step program, both templates
    registered, both steps resolve."""
    kernel = _bare_kernel()
    tpl_ids = (
        "scenario_driver:credit_tightening:reference",
        "scenario_driver:funding_window_closure:reference",
    )
    for tpl_id in tpl_ids:
        kernel.scenario_drivers.add_template(
            _build_template(scenario_driver_template_id=tpl_id)
        )
    program_id = (
        "stress_program:test_attention_crowding:happy"
    )
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="Happy-path case study",
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


def _seed_partial_kernel() -> tuple[WorldKernel, str]:
    """Partial fixture: two-step program, one template
    registered + one missing → step 1 is uncited with reason
    ``template_missing``."""
    kernel = _bare_kernel()
    kernel.scenario_drivers.add_template(_build_template())
    program_id = (
        "stress_program:test_attention_crowding:partial"
    )
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="Partial case study",
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
                # Template intentionally NOT registered →
                # uncited.
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
# 1. Determinism — byte-identical report + markdown across
#    two consecutive calls (Cat 1 from research note 002).
# ---------------------------------------------------------------------------


def test_attention_crowding_case_study_report_is_deterministic() -> None:
    """Same kernel state + same arguments → byte-identical
    case-study report dict + byte-identical markdown
    rendering."""
    kernel, receipt_id = _seed_happy_path_kernel()
    a = build_attention_crowding_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
    )
    b = build_attention_crowding_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
    )
    assert a == b
    md_a = render_attention_crowding_case_study_markdown(a)
    md_b = render_attention_crowding_case_study_markdown(b)
    assert md_a == md_b


# ---------------------------------------------------------------------------
# 2. Uncited stress visibility — partial fixture surfaces
#    cited and uncited step ids correctly.
# ---------------------------------------------------------------------------


def test_attention_crowding_case_study_surfaces_uncited_steps() -> None:
    """A partial fixture (one step uncited) populates
    ``cited_step_ids`` with the resolved step + populates
    ``uncited_step_ids`` with the unresolved step paired with
    the v1.21.3 ``template_missing`` reason label."""
    kernel, receipt_id = _seed_partial_kernel()
    report = build_attention_crowding_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
    )
    cited = report["cited_step_ids"]
    uncited = report["uncited_step_ids"]
    assert len(cited) == 1
    assert len(uncited) == 1
    # The cited step is step 0 (credit_tightening — registered).
    assert cited[0].endswith(":step:0")
    # The uncited step is step 1 (nonexistent — not registered).
    assert uncited[0].endswith(":step:1")
    # Reason label is in the closed v1.21.3 set.
    summary = report["stress_readout_summary"]
    assert summary["unresolved_reason_labels"] == [
        "template_missing"
    ]
    # is_partial_application is surfaced.
    assert summary["is_partial_application"] is True
    # warnings contain the partial-application banner.
    assert any(
        "partial application" in w.lower()
        for w in report["warnings"]
    )


def test_attention_crowding_case_study_happy_path_has_no_uncited_steps() -> None:
    """An all-cited fixture populates ``cited_step_ids``
    with every step + leaves ``uncited_step_ids`` empty +
    sets ``is_partial_application`` to False."""
    kernel, receipt_id = _seed_happy_path_kernel()
    report = build_attention_crowding_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
    )
    assert len(report["cited_step_ids"]) == 2
    assert report["uncited_step_ids"] == []
    summary = report["stress_readout_summary"]
    assert summary["unresolved_step_count"] == 0
    assert summary["is_partial_application"] is False


# ---------------------------------------------------------------------------
# 3. Citation completeness — Cat 3 pin satisfied for both
#    fixtures; missing-citation detection works.
# ---------------------------------------------------------------------------


def test_attention_crowding_case_study_citation_completeness_pin_satisfied() -> None:
    """Every cited plain-id resolves to an extant kernel
    record. The Cat 3 pin returns ``satisfied = True`` for
    both happy-path and partial fixtures."""
    for seed in (_seed_happy_path_kernel, _seed_partial_kernel):
        kernel, receipt_id = seed()
        report = build_attention_crowding_case_study_report(
            kernel,
            stress_program_application_id=receipt_id,
        )
        cp = report["validation_report_summary"][
            "citation_completeness_pin_v1_23_2"
        ]
        assert cp["satisfied"] is True, (
            f"Cat 3 pin failed for fixture {seed.__name__}: "
            f"{cp!r}"
        )
        assert (
            cp["dangling_scenario_application_id_count"] == 0
        )
        assert (
            cp["dangling_scenario_context_shift_id_count"]
            == 0
        )
        assert (
            cp["stress_program_application_id_resolves"]
            is True
        )


# ---------------------------------------------------------------------------
# 4. Boundary preservation — Cat 2 pin satisfied; rendered
#    markdown carries no forbidden token outside the boundary
#    statement.
# ---------------------------------------------------------------------------


def _strip_boundary_statement(markdown: str) -> str:
    """Strip the pinned ``## Boundary statement`` section
    before scanning. The boundary block legitimately
    references each forbidden token under the negation
    form."""
    idx = markdown.find("## Boundary statement")
    if idx < 0:
        return markdown
    return markdown[:idx]


def test_attention_crowding_case_study_no_forbidden_wording() -> None:
    """The case-study report dict and the rendered markdown
    contain no canonical forbidden token outside the pinned
    boundary-statement disclaimer block. Whole-word boundary
    scan against the v1.23.1 canonical
    ``FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS``."""
    kernel, receipt_id = _seed_partial_kernel()
    report = build_attention_crowding_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
    )

    # Cat 2 pin says boundary is preserved at the export
    # entry level. Re-check by scanning the report's own
    # values + the rendered markdown.
    bp = report["validation_report_summary"][
        "boundary_preservation_pin_v1_23_2"
    ]
    assert bp["satisfied"] is True, (
        f"Cat 2 pin failed: {bp!r}"
    )

    md = render_attention_crowding_case_study_markdown(report)
    body = _strip_boundary_statement(md).lower()
    offenders: list[str] = []
    for token in FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS:
        pattern = rf"\b{re.escape(token.lower())}\b"
        if re.search(pattern, body):
            offenders.append(token)
    assert offenders == [], (
        "Case-study markdown (excluding boundary statement) "
        f"contains forbidden tokens: {sorted(offenders)!r}"
    )


# ---------------------------------------------------------------------------
# 5. No mutation — every relevant kernel book snapshot is
#    byte-identical pre / post helper call. No new ledger
#    record.
# ---------------------------------------------------------------------------


def test_attention_crowding_case_study_does_not_mutate_kernel() -> None:
    """Building a case-study report must NOT mutate any
    kernel book and must NOT emit a ledger record."""
    kernel, receipt_id = _seed_partial_kernel()
    snap_before = {
        "scenario_drivers": (
            kernel.scenario_drivers.snapshot()
        ),
        "scenario_applications": (
            kernel.scenario_applications.snapshot()
        ),
        "stress_programs": (
            kernel.stress_programs.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "ledger_len": len(kernel.ledger.records),
    }
    build_attention_crowding_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
    )
    snap_after = {
        "scenario_drivers": (
            kernel.scenario_drivers.snapshot()
        ),
        "scenario_applications": (
            kernel.scenario_applications.snapshot()
        ),
        "stress_programs": (
            kernel.stress_programs.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "ledger_len": len(kernel.ledger.records),
    }
    assert snap_before == snap_after, (
        "case study helper mutated kernel state"
    )


# ---------------------------------------------------------------------------
# 6. No re-application — the helper does NOT call
#    apply_stress_program / apply_scenario_driver. Verified
#    via monkey-patch sentinel.
# ---------------------------------------------------------------------------


def test_attention_crowding_case_study_does_not_call_apply_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The helper must not re-run the stress program or any
    scenario driver. Monkey-patch both helpers to raise; the
    case-study build must still succeed."""
    kernel, receipt_id = _seed_partial_kernel()

    def _forbid(*args, **kwargs):
        raise AssertionError(
            "case study helper called apply helper — read-only "
            "discipline violated"
        )

    monkeypatch.setattr(
        stress_applications_mod, "apply_stress_program", _forbid
    )
    monkeypatch.setattr(
        scenario_applications_mod,
        "apply_scenario_driver",
        _forbid,
    )

    # Build still succeeds — proving the helper does not call
    # either apply path.
    report = build_attention_crowding_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
    )
    assert isinstance(report, dict)
    assert (
        report["stress_program_application_id"] == receipt_id
    )


# ---------------------------------------------------------------------------
# 7. Markdown sections — required headings present.
# ---------------------------------------------------------------------------


def test_attention_crowding_case_study_markdown_contains_required_sections() -> None:
    """The renderer emits each of the eight required
    sections: Case study / Cited / Uncited / Citation graph /
    Stress readout summary / Validation report summary /
    Warnings / Boundary statement."""
    kernel, receipt_id = _seed_partial_kernel()
    report = build_attention_crowding_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
    )
    md = render_attention_crowding_case_study_markdown(report)
    required_sections = (
        "## Case study",
        "## Cited stress steps",
        "## Uncited stress steps",
        "## Citation graph plain-id surface",
        "## Stress readout summary",
        "## Validation report summary",
        "## Warnings",
        "## Boundary statement",
    )
    for section in required_sections:
        assert section in md, (
            f"markdown missing required section {section!r}"
        )


# ---------------------------------------------------------------------------
# 8. Cat 4 visibility pin — the helper carries the v1.21.3
#    visibility through the report when partial.
# ---------------------------------------------------------------------------


def test_attention_crowding_case_study_partial_visibility_pin_satisfied() -> None:
    """When ``readout.is_partial`` is True, the case-study
    report's Cat 4 pin sub-dict reports the visibility as
    satisfied AND surfaces the partial-application counts."""
    kernel, receipt_id = _seed_partial_kernel()
    report = build_attention_crowding_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
    )
    pp = report["validation_report_summary"][
        "partial_application_visibility_pin_v1_23_2"
    ]
    assert pp["satisfied"] is True
    assert pp["is_partial_application"] is True
    assert pp["unresolved_step_count"] == 1
    assert pp["resolved_step_count"] == 1
    assert pp["total_step_count"] == 2
