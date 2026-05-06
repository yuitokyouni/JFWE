"""
v1.25.2 — Investor mandate readout pin tests.

Pins ``world/investor_mandate_readout.py``:

- ``build_investor_mandate_readout`` is read-only (no
  kernel mutation, no ledger emission, no apply / intent
  helper call, no add_profile call);
- the readout produces only closed-set context / bias
  labels — never scores, never market intents, never
  recommendations;
- the readout's serialised + rendered outputs contain no
  v1.25.0 forbidden token (no allocation / target weight
  / trade / order / execution / expected return / target
  price / forecast / recommendation / impact / outcome);
- determinism: same kernel state → byte-identical
  readout + markdown;
- forbidden-token boundary scan rejects metadata keys;
- existing v1.21.3 stress readout + v1.24.2 manual
  annotation readout still work in the same kernel.
"""

from __future__ import annotations

import re
from datetime import date

import pytest

from world.clock import Clock
from world.investor_mandate_readout import (
    MANDATE_ATTENTION_BIAS_LABELS,
    MANDATE_REVIEW_CONTEXT_LABELS,
    InvestorMandateReadout,
    build_investor_mandate_readout,
    render_investor_mandate_readout_markdown,
)
from world.investor_mandates import (
    InvestorMandateProfile,
    UnknownInvestorMandateProfileError,
)
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.manual_annotation_readout import (
    build_manual_annotation_readout,
)
from world.manual_annotations import (
    ManualAnnotationRecord,
)
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


def _profile(
    *,
    mandate_profile_id: str = "investor_mandate_profile:test:1",
    investor_id: str = "investor:reference_pension_a",
    mandate_type_label: str = "pension_like",
    benchmark_pressure_label: str = "moderate",
    liquidity_need_label: str = "low",
    liability_horizon_label: str = "long",
    review_frequency_label: str = "quarterly",
    concentration_tolerance_label: str = "low",
    stewardship_priority_labels: tuple[str, ...] = (
        "capital_discipline",
        "governance_review",
    ),
) -> InvestorMandateProfile:
    return InvestorMandateProfile(
        mandate_profile_id=mandate_profile_id,
        investor_id=investor_id,
        mandate_type_label=mandate_type_label,
        benchmark_pressure_label=benchmark_pressure_label,
        liquidity_need_label=liquidity_need_label,
        liability_horizon_label=liability_horizon_label,
        review_frequency_label=review_frequency_label,
        concentration_tolerance_label=(
            concentration_tolerance_label
        ),
        stewardship_priority_labels=(
            stewardship_priority_labels
        ),
    )


# ---------------------------------------------------------------------------
# 1. Read-only — readout building does not mutate / re-add /
#    re-apply.
# ---------------------------------------------------------------------------


def test_investor_mandate_readout_is_read_only() -> None:
    """Same kernel state → byte-identical readout +
    byte-identical markdown across two consecutive calls.
    Snapshots of every relevant book are byte-identical
    pre / post."""
    kernel = _bare_kernel()
    p = _profile()
    kernel.investor_mandates.add_profile(p)

    snap_before = {
        "scenario_drivers": (
            kernel.scenario_drivers.snapshot()
        ),
        "scenario_applications": (
            kernel.scenario_applications.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "investor_mandates": (
            kernel.investor_mandates.snapshot()
        ),
        "investor_intents": (
            kernel.investor_intents.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
        "ledger_len": len(kernel.ledger.records),
    }
    a = build_investor_mandate_readout(
        kernel, mandate_profile_id=p.mandate_profile_id
    )
    snap_after_1 = {
        "scenario_drivers": (
            kernel.scenario_drivers.snapshot()
        ),
        "scenario_applications": (
            kernel.scenario_applications.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "investor_mandates": (
            kernel.investor_mandates.snapshot()
        ),
        "investor_intents": (
            kernel.investor_intents.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
        "ownership": kernel.ownership.snapshot(),
        "prices": kernel.prices.snapshot(),
        "ledger_len": len(kernel.ledger.records),
    }
    assert snap_before == snap_after_1
    b = build_investor_mandate_readout(
        kernel, mandate_profile_id=p.mandate_profile_id
    )
    assert a.to_dict() == b.to_dict()
    md_a = render_investor_mandate_readout_markdown(a)
    md_b = render_investor_mandate_readout_markdown(b)
    assert md_a == md_b


# ---------------------------------------------------------------------------
# 2. Context labels only — no scores / no portfolio /
#    no intents.
# ---------------------------------------------------------------------------


def test_mandate_readout_produces_context_labels_only() -> None:
    """The readout emits only closed-set
    review_context_labels +
    selected_attention_bias_labels (no numeric scores,
    no portfolio shape, no recommendation)."""
    kernel = _bare_kernel()
    p = _profile(
        benchmark_pressure_label="high",
        liquidity_need_label="high",
        liability_horizon_label="short",
        stewardship_priority_labels=(
            "capital_discipline",
            "climate_disclosure",
            "governance_review",
        ),
    )
    kernel.investor_mandates.add_profile(p)
    r = build_investor_mandate_readout(
        kernel, mandate_profile_id=p.mandate_profile_id
    )
    # Every emitted review-context label is in the closed
    # set.
    for lbl in r.review_context_labels:
        assert lbl in MANDATE_REVIEW_CONTEXT_LABELS
    # Every emitted attention-bias label is in the closed
    # set.
    for lbl in r.selected_attention_bias_labels:
        assert lbl in MANDATE_ATTENTION_BIAS_LABELS
    # Cited mandate fields drawn from a small known set.
    for fname in r.cited_mandate_fields:
        assert fname in {
            "benchmark_pressure_label",
            "liquidity_need_label",
            "liability_horizon_label",
            "stewardship_priority_labels",
        }
    # No numeric "score" key in the serialised readout.
    d = r.to_dict()
    for forbidden_key in (
        "score",
        "weight",
        "performance",
        "alpha",
        "expected_return",
        "target_price",
        "tracking_error",
        "tracking_error_value",
        "allocation",
        "portfolio_allocation",
    ):
        assert forbidden_key not in d


# ---------------------------------------------------------------------------
# 3. Does not create investor intent.
# ---------------------------------------------------------------------------


def test_mandate_readout_does_not_create_investor_intent() -> None:
    """Building the readout does not emit any v1.16.x
    investor intent / market intent / actor attention
    state record."""
    kernel = _bare_kernel()
    p = _profile()
    kernel.investor_mandates.add_profile(p)
    market_intents_before = (
        kernel.investor_market_intents.list_intents()
    )
    investor_intents_before = (
        kernel.investor_intents.list_intents()
    )
    ledger_event_types_before = [
        r.event_type for r in kernel.ledger.records
    ]
    build_investor_mandate_readout(
        kernel, mandate_profile_id=p.mandate_profile_id
    )
    assert (
        kernel.investor_market_intents.list_intents()
        == market_intents_before
    )
    assert (
        kernel.investor_intents.list_intents()
        == investor_intents_before
    )
    # Ledger length unchanged (no event fires from
    # readout build).
    assert [
        r.event_type for r in kernel.ledger.records
    ] == ledger_event_types_before


# ---------------------------------------------------------------------------
# 4. Does not mutate portfolio / ownership.
# ---------------------------------------------------------------------------


def test_mandate_readout_does_not_mutate_portfolio_or_ownership() -> None:
    """Snapshots of ownership / contracts / prices /
    constraints / institutions / investor_intents /
    investor_market_intents are byte-identical pre /
    post readout build."""
    kernel = _bare_kernel()
    p = _profile()
    kernel.investor_mandates.add_profile(p)
    snap_before = {
        "ownership": kernel.ownership.snapshot(),
        "contracts": kernel.contracts.snapshot(),
        "prices": kernel.prices.snapshot(),
        "constraints": kernel.constraints.snapshot(),
        "institutions": kernel.institutions.snapshot(),
        "investor_intents": (
            kernel.investor_intents.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
    }
    build_investor_mandate_readout(
        kernel, mandate_profile_id=p.mandate_profile_id
    )
    snap_after = {
        "ownership": kernel.ownership.snapshot(),
        "contracts": kernel.contracts.snapshot(),
        "prices": kernel.prices.snapshot(),
        "constraints": kernel.constraints.snapshot(),
        "institutions": kernel.institutions.snapshot(),
        "investor_intents": (
            kernel.investor_intents.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
    }
    assert snap_before == snap_after


# ---------------------------------------------------------------------------
# 5. No trade / order / allocation wording.
# ---------------------------------------------------------------------------


def test_mandate_readout_has_no_trade_order_allocation_words() -> None:
    """The rendered markdown body (excluding the
    ``## Boundary statement`` section, which legitimately
    negates each forbidden token) carries no
    trade / order / allocation / target_weight / buy /
    sell / forecast / recommendation wording."""
    kernel = _bare_kernel()
    p = _profile(
        benchmark_pressure_label="high",
        stewardship_priority_labels=(
            "capital_discipline",
            "governance_review",
            "funding_access",
        ),
    )
    kernel.investor_mandates.add_profile(p)
    r = build_investor_mandate_readout(
        kernel, mandate_profile_id=p.mandate_profile_id
    )
    md = render_investor_mandate_readout_markdown(r)
    body = md.split("## Boundary statement")[0].lower()
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
    )
    for phrase in forbidden_phrases:
        # Whole-word boundary scan.
        pattern = rf"\b{re.escape(phrase)}\b"
        assert re.search(pattern, body) is None, (
            f"forbidden phrase {phrase!r} appears in "
            "the markdown body (outside boundary statement)"
        )


# ---------------------------------------------------------------------------
# 6. Forbidden metadata rejected at construction.
# ---------------------------------------------------------------------------


def test_mandate_readout_rejects_forbidden_metadata() -> None:
    """Caller-supplied metadata containing a forbidden
    key raises at construction. Direct dataclass
    construction with forbidden metadata also raises."""
    kernel = _bare_kernel()
    p = _profile()
    kernel.investor_mandates.add_profile(p)
    with pytest.raises(ValueError):
        build_investor_mandate_readout(
            kernel,
            mandate_profile_id=p.mandate_profile_id,
            metadata={"target_weight": "any"},
        )
    with pytest.raises(ValueError):
        InvestorMandateReadout(
            readout_id="r:1",
            investor_id="investor:test",
            mandate_profile_id="mp:test",
            mandate_type_label="pension_like",
            benchmark_pressure_label="moderate",
            liquidity_need_label="low",
            liability_horizon_label="long",
            stewardship_priority_labels=(),
            review_context_labels=(),
            selected_attention_bias_labels=(),
            cited_mandate_fields=(),
            metadata={"forecast": "no"},
        )


# ---------------------------------------------------------------------------
# 7. Deterministic across runs.
# ---------------------------------------------------------------------------


def test_mandate_readout_deterministic() -> None:
    """Re-building the readout on the same kernel state
    produces a byte-identical readout dict + markdown.
    Distinct profiles produce distinct readouts."""
    kernel = _bare_kernel()
    p1 = _profile(
        mandate_profile_id="mp:test:pension",
        mandate_type_label="pension_like",
        benchmark_pressure_label="low",
        liability_horizon_label="long",
    )
    p2 = _profile(
        mandate_profile_id="mp:test:active",
        investor_id="investor:reference_active_a",
        mandate_type_label="active_manager_like",
        benchmark_pressure_label="high",
        liquidity_need_label="moderate",
        liability_horizon_label="short",
        stewardship_priority_labels=(
            "capital_discipline",
        ),
    )
    kernel.investor_mandates.add_profile(p1)
    kernel.investor_mandates.add_profile(p2)
    r1a = build_investor_mandate_readout(
        kernel,
        mandate_profile_id=p1.mandate_profile_id,
    )
    r1b = build_investor_mandate_readout(
        kernel,
        mandate_profile_id=p1.mandate_profile_id,
    )
    r2 = build_investor_mandate_readout(
        kernel,
        mandate_profile_id=p2.mandate_profile_id,
    )
    assert r1a.to_dict() == r1b.to_dict()
    assert r1a.to_dict() != r2.to_dict()
    # And different profiles produce different review-
    # context label sets (long-horizon pension vs. short-
    # horizon active).
    assert (
        set(r1a.review_context_labels)
        != set(r2.review_context_labels)
    )

    # Also verify Unknown profile id raises.
    with pytest.raises(
        UnknownInvestorMandateProfileError
    ):
        build_investor_mandate_readout(
            kernel,
            mandate_profile_id="nonexistent",
        )


# ---------------------------------------------------------------------------
# 8. Existing stress + manual-annotation readouts still
#    work alongside.
# ---------------------------------------------------------------------------


def _build_stress_template() -> ScenarioDriverTemplate:
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


def test_existing_stress_and_annotation_readouts_still_work() -> None:
    """The v1.21.3 stress readout + the v1.24.2 manual
    annotation readout still build cleanly when a
    v1.25.1 mandate profile is also present in the same
    kernel."""
    kernel = _bare_kernel()
    # Mandate profile.
    p = _profile()
    kernel.investor_mandates.add_profile(p)
    # Stress program.
    kernel.scenario_drivers.add_template(
        _build_stress_template()
    )
    program_id = "stress_program:test_v1_25_2:s"
    program = StressProgramTemplate(
        stress_program_template_id=program_id,
        program_label="v1.25.2 mandate-readout fixture",
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
    # Manual annotation citing the stress readout.
    kernel.manual_annotations.add_annotation(
        ManualAnnotationRecord(
            annotation_id="manual_annotation:test:v1_25_2",
            annotation_scope_label="stress_readout",
            annotation_label="same_review_frame",
            cited_record_ids=(
                f"stress_field_readout:"
                f"{receipt.stress_program_application_id}",
            ),
            reviewer_role_label="reviewer",
        )
    )

    # All three readouts build cleanly.
    stress_readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=(
            receipt.stress_program_application_id
        ),
    )
    assert stress_readout.total_step_count == 1

    manual_readout = build_manual_annotation_readout(kernel)
    assert manual_readout.annotation_count == 1

    mandate_readout = build_investor_mandate_readout(
        kernel,
        mandate_profile_id=p.mandate_profile_id,
    )
    assert (
        mandate_readout.investor_id
        == "investor:reference_pension_a"
    )
    # And the mandate readout's serialised dict mentions
    # neither stress nor annotation surfaces.
    md_dict = mandate_readout.to_dict()
    assert "stress_readout" not in md_dict
    assert "manual_annotation" not in md_dict
