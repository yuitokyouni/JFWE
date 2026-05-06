"""
v1.25.4 — Investor mandate case study pin tests.

Pins ``world/investor_mandate_case_study.py``:

- the helper is deterministic (byte-identical report
  + markdown across two consecutive calls);
- two investors with different mandate profiles
  produce different ``review_context_labels`` and
  ``selected_attention_bias_labels`` over the same
  v1.21.3 stress readout;
- the report dict + rendered markdown carry no
  trade / order / allocation / recommendation /
  forecast wording (outside the pinned boundary
  statement);
- the helper does not mutate any kernel book;
- the helper emits no ledger record;
- the helper does not call any apply / intent helper;
- the rendered markdown contains the required
  sections.
"""

from __future__ import annotations

import re
from datetime import date

import pytest

from world.clock import Clock
from world.investor_mandate_case_study import (
    build_investor_mandate_case_study_report,
    render_investor_mandate_case_study_markdown,
)
from world.investor_mandates import (
    InvestorMandateProfile,
)
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


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _build_template() -> ScenarioDriverTemplate:
    return ScenarioDriverTemplate(
        scenario_driver_template_id=(
            "scenario_driver:credit_tightening:reference"
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


def _seed_kernel_with_stress_and_two_profiles() -> tuple[
    WorldKernel, str, str, str
]:
    """Seed a kernel with one stress program applied + two
    contrasting mandate profiles. Return
    ``(kernel, stress_program_application_id,
    mandate_profile_id_a, mandate_profile_id_b)``."""
    kernel = _bare_kernel()
    kernel.scenario_drivers.add_template(_build_template())
    program_id = "stress_program:test_v1_25_4:single"
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="v1.25.4 case study fixture",
        program_purpose_label=(
            "single_credit_tightening_stress"
        ),
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
        ),
    )
    kernel.stress_programs.add_program(program)
    receipt = apply_stress_program(
        kernel,
        stress_program_template_id=program_id,
        as_of_date="2026-04-30",
    )

    pension_profile = InvestorMandateProfile(
        mandate_profile_id="mp:test:pension_long",
        investor_id="investor:reference_pension_a",
        mandate_type_label="pension_like",
        benchmark_pressure_label="low",
        liquidity_need_label="low",
        liability_horizon_label="long",
        review_frequency_label="quarterly",
        concentration_tolerance_label="low",
        stewardship_priority_labels=(
            "capital_discipline",
            "governance_review",
        ),
    )
    active_profile = InvestorMandateProfile(
        mandate_profile_id="mp:test:active_short",
        investor_id="investor:reference_active_a",
        mandate_type_label="active_manager_like",
        benchmark_pressure_label="high",
        liquidity_need_label="high",
        liability_horizon_label="short",
        review_frequency_label="monthly",
        concentration_tolerance_label="high",
        stewardship_priority_labels=(
            "funding_access",
        ),
    )
    kernel.investor_mandates.add_profile(pension_profile)
    kernel.investor_mandates.add_profile(active_profile)

    return (
        kernel,
        receipt.stress_program_application_id,
        pension_profile.mandate_profile_id,
        active_profile.mandate_profile_id,
    )


# ---------------------------------------------------------------------------
# 1. Determinism — byte-identical across consecutive calls.
# ---------------------------------------------------------------------------


def test_investor_mandate_case_study_report_is_deterministic() -> None:
    """Same kernel state + same arguments → byte-identical
    report + markdown."""
    kernel, receipt_id, pid_a, pid_b = (
        _seed_kernel_with_stress_and_two_profiles()
    )
    a = build_investor_mandate_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
        mandate_profile_ids=(pid_a, pid_b),
    )
    b = build_investor_mandate_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
        mandate_profile_ids=(pid_a, pid_b),
    )
    assert a == b
    md_a = render_investor_mandate_case_study_markdown(a)
    md_b = render_investor_mandate_case_study_markdown(b)
    assert md_a == md_b


# ---------------------------------------------------------------------------
# 2. Two investors → different review-context label sets.
# ---------------------------------------------------------------------------


def test_two_investors_get_different_review_contexts() -> None:
    """Two distinct mandate profiles must produce
    different ``review_context_labels`` tuples — that is
    the whole point of the case study."""
    kernel, receipt_id, pid_a, pid_b = (
        _seed_kernel_with_stress_and_two_profiles()
    )
    report = build_investor_mandate_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
        mandate_profile_ids=(pid_a, pid_b),
    )
    rclbi = report["review_context_labels_by_investor"]
    assert (
        len(set(tuple(sorted(v)) for v in rclbi.values()))
        == 2
    ), (
        "the two profiles produced the same review_"
        "context_labels — case study is degenerate"
    )
    ablbi = report["attention_bias_labels_by_investor"]
    assert (
        len(set(tuple(sorted(v)) for v in ablbi.values()))
        == 2
    ), (
        "the two profiles produced the same attention "
        "bias labels — case study is degenerate"
    )


# ---------------------------------------------------------------------------
# 3. No action / trade / allocation wording.
# ---------------------------------------------------------------------------


def _strip_boundary_statement(markdown: str) -> str:
    idx = markdown.find("## Boundary statement")
    if idx < 0:
        return markdown
    return markdown[:idx]


def test_case_study_no_action_trade_allocation_words() -> None:
    """The rendered markdown body (excluding the
    ``## Boundary statement`` section) carries no
    trade / order / allocation / target_weight / buy /
    sell / forecast / recommendation wording."""
    kernel, receipt_id, pid_a, pid_b = (
        _seed_kernel_with_stress_and_two_profiles()
    )
    report = build_investor_mandate_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
        mandate_profile_ids=(pid_a, pid_b),
    )
    md = render_investor_mandate_case_study_markdown(report)
    body = _strip_boundary_statement(md).lower()
    forbidden_phrases = (
        "buy",
        "sell",
        "order",
        "trade",
        "execution",
        "allocation",
        "target_weight",
        "target weight",
        "overweight",
        "underweight",
        "rebalance",
        "alpha",
        "performance",
        "tracking_error",
        "tracking error",
        "expected_return",
        "expected return",
        "target_price",
        "target price",
        "forecast",
        "prediction",
        "recommendation",
        "investment_advice",
        "investment advice",
        "amplify",
        "dampen",
        "offset",
        "coexist",
        "aggregate",
        "composite",
        "dominant",
        "actor_decision",
        "actor decision",
    )
    for phrase in forbidden_phrases:
        pattern = rf"\b{re.escape(phrase)}\b"
        assert re.search(pattern, body) is None, (
            f"forbidden phrase {phrase!r} appears in "
            "case study markdown body"
        )


# ---------------------------------------------------------------------------
# 4. No mutation.
# ---------------------------------------------------------------------------


def test_case_study_does_not_mutate_kernel() -> None:
    """Building the report must not mutate any kernel
    book and must not emit any ledger record."""
    kernel, receipt_id, pid_a, pid_b = (
        _seed_kernel_with_stress_and_two_profiles()
    )
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
        "investor_mandates": (
            kernel.investor_mandates.snapshot()
        ),
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "investor_intents": (
            kernel.investor_intents.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
    }
    build_investor_mandate_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
        mandate_profile_ids=(pid_a, pid_b),
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
        "investor_mandates": (
            kernel.investor_mandates.snapshot()
        ),
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "investor_intents": (
            kernel.investor_intents.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
    }
    assert snap_before == snap_after


# ---------------------------------------------------------------------------
# 5. No ledger emission.
# ---------------------------------------------------------------------------


def test_case_study_does_not_emit_ledger_records() -> None:
    """Ledger length unchanged after report build."""
    kernel, receipt_id, pid_a, pid_b = (
        _seed_kernel_with_stress_and_two_profiles()
    )
    ledger_len_before = len(kernel.ledger.records)
    build_investor_mandate_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
        mandate_profile_ids=(pid_a, pid_b),
    )
    assert len(kernel.ledger.records) == ledger_len_before


# ---------------------------------------------------------------------------
# 6. No call to apply / intent / add_profile helpers.
# ---------------------------------------------------------------------------


def test_case_study_does_not_call_apply_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The helper must not call apply_stress_program /
    apply_scenario_driver / add_profile. Set up the
    fixture FIRST, then monkey-patch each helper to
    raise — the case-study build must still succeed
    because the helper does not call any of them."""
    # Set up first.
    kernel, receipt_id, pid_a, pid_b = (
        _seed_kernel_with_stress_and_two_profiles()
    )
    # Then forbid further calls.
    import world.investor_mandates as im_mod
    import world.scenario_applications as sa_mod
    import world.stress_applications as sap_mod

    def _forbid(*args, **kwargs):
        raise AssertionError(
            "case study helper called a forbidden helper "
            "— read-only discipline violated"
        )

    monkeypatch.setattr(
        sap_mod, "apply_stress_program", _forbid
    )
    monkeypatch.setattr(
        sa_mod, "apply_scenario_driver", _forbid
    )
    monkeypatch.setattr(
        im_mod.InvestorMandateBook,
        "add_profile",
        _forbid,
    )
    report = build_investor_mandate_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
        mandate_profile_ids=(pid_a, pid_b),
    )
    assert isinstance(report, dict)


# ---------------------------------------------------------------------------
# 7. Markdown contains required sections.
# ---------------------------------------------------------------------------


def test_case_study_markdown_contains_required_sections() -> None:
    """The renderer emits every required section, in
    order."""
    kernel, receipt_id, pid_a, pid_b = (
        _seed_kernel_with_stress_and_two_profiles()
    )
    report = build_investor_mandate_case_study_report(
        kernel,
        stress_program_application_id=receipt_id,
        mandate_profile_ids=(pid_a, pid_b),
    )
    md = render_investor_mandate_case_study_markdown(report)
    required_sections = (
        "## Investor mandate case study",
        "## Investors compared",
        "## Review context labels by investor",
        "## Selected attention bias labels by investor",
        "## Cited mandate fields",
        "## Warnings",
        "## Boundary statement",
    )
    last_idx = -1
    for section in required_sections:
        idx = md.find(section)
        assert idx >= 0, (
            f"markdown missing required section "
            f"{section!r}"
        )
        assert idx > last_idx, (
            f"section {section!r} out of order"
        )
        last_idx = idx


# ---------------------------------------------------------------------------
# 8. Existing canonical digests unchanged.
# ---------------------------------------------------------------------------


def test_existing_canonical_digests_unchanged_at_v1_25_4() -> None:
    """v1.25.4 is read-only and adds no fixture; the
    v1.21.last canonical digests remain byte-identical
    when the case-study helper is invoked alongside the
    v1.25.x storage fixture."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from _canonical_digests import (
        QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
    )
    from test_living_reference_world import (
        _run_default,
        _seed_kernel,
    )

    # v1.25.4 helper requires a stress-applied kernel +
    # mandate profiles to run; the digest preservation we
    # actually pin is on the SEPARATE quarterly_default
    # fixture (no stress, no mandate, default kernel),
    # which the v1.25.1 storage event-by-default
    # discipline already preserves.
    k = _seed_kernel()
    r = _run_default(k)
    assert (
        living_world_digest(k, r)
        == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST
    )

    # And a separate kernel exercising the v1.25.4
    # helper does not mutate any cross-kernel state
    # (case study helpers are pure projections).
    kernel2, receipt_id, pid_a, pid_b = (
        _seed_kernel_with_stress_and_two_profiles()
    )
    build_investor_mandate_case_study_report(
        kernel2,
        stress_program_application_id=receipt_id,
        mandate_profile_ids=(pid_a, pid_b),
    )
    # The canonical fixture's digest is still pinned.
    assert (
        living_world_digest(k, r)
        == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST
    )
