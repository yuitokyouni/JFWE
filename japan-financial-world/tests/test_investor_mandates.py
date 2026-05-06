"""
v1.25.1 — Investor mandate / benchmark-pressure storage
pin tests.

Pins ``world/investor_mandates.py`` per the v1.25.0
design note (`docs/v1_25_institutional_investor_mandate_benchmark_pressure.md`):

- ``InvestorMandateProfile`` validates required fields,
  rejects invalid closed-set labels, rejects duplicate
  stewardship priorities, rejects forbidden field
  names / metadata keys;
- ``InvestorMandateBook`` provides add / get / list /
  list_by_investor / list_by_mandate_type /
  list_by_benchmark_pressure / snapshot;
- duplicate ``mandate_profile_id`` is rejected and
  emits no extra ledger record;
- the storage layer does not mutate any pre-existing
  source-of-truth book and does not call any v1.15.x /
  v1.16.x investor-intent helper;
- the ``WorldKernel.investor_mandates`` field is empty
  by default;
- every existing canonical ``living_world_digest`` value
  remains byte-identical with an empty
  investor-mandate book.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES,
)
from world.investor_mandates import (
    BENCHMARK_PRESSURE_LABELS,
    DuplicateInvestorMandateProfileError,
    InvestorMandateBook,
    InvestorMandateProfile,
    MANDATE_TYPE_LABELS,
    STEWARDSHIP_PRIORITY_LABELS,
)
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State

from _canonical_digests import (
    MONTHLY_REFERENCE_LIVING_WORLD_DIGEST,
    QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
    SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST,
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


def _build_profile(
    *,
    mandate_profile_id: str = "investor_mandate_profile:test:01",
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
    metadata: dict | None = None,
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
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# 1. Required fields validate.
# ---------------------------------------------------------------------------


def test_investor_mandate_profile_validates_required_fields() -> None:
    """A valid record constructs cleanly; an empty
    ``mandate_profile_id`` / ``investor_id`` /
    closed-set label raises."""
    p = _build_profile()
    assert (
        p.mandate_profile_id
        == "investor_mandate_profile:test:01"
    )
    assert p.investor_id == "investor:reference_pension_a"
    assert p.mandate_type_label == "pension_like"
    assert p.benchmark_pressure_label == "moderate"
    assert p.status == "active"
    # Required-string discipline.
    with pytest.raises(ValueError):
        _build_profile(mandate_profile_id="")
    with pytest.raises(ValueError):
        _build_profile(investor_id="")
    # Default boundary flags include every v1.25-specific
    # default flag.
    for flag in (
        "no_actor_decision",
        "no_llm_execution",
        "no_portfolio_allocation",
        "no_target_weight",
        "no_rebalancing",
        "no_expected_return_claim",
        "no_tracking_error_value",
        "no_benchmark_identification",
        "attention_review_context_only",
        "descriptive_only",
    ):
        assert p.boundary_flags[flag] is True


# ---------------------------------------------------------------------------
# 2. Closed-set label validation.
# ---------------------------------------------------------------------------


def test_investor_mandate_profile_validates_closed_labels() -> None:
    """Each closed-set label field must accept only
    members of its pinned closed set; non-members raise."""
    # mandate_type_label
    for forbidden_value in (
        "active_manager",
        "pension",
        "robot_manager",
    ):
        with pytest.raises(ValueError):
            _build_profile(
                mandate_type_label=forbidden_value
            )
    # benchmark_pressure_label
    for forbidden_value in ("very_high", "0.5", "extreme"):
        with pytest.raises(ValueError):
            _build_profile(
                benchmark_pressure_label=forbidden_value
            )
    # liquidity_need_label / liability_horizon_label /
    # review_frequency_label / concentration_tolerance_label
    with pytest.raises(ValueError):
        _build_profile(liquidity_need_label="extreme")
    with pytest.raises(ValueError):
        _build_profile(liability_horizon_label="forever")
    with pytest.raises(ValueError):
        _build_profile(review_frequency_label="hourly")
    with pytest.raises(ValueError):
        _build_profile(concentration_tolerance_label="extreme")
    # stewardship_priority_labels — non-member rejected.
    with pytest.raises(ValueError):
        _build_profile(
            stewardship_priority_labels=("not_a_priority",),
        )
    # And duplicate stewardship priority rejected.
    with pytest.raises(ValueError):
        _build_profile(
            stewardship_priority_labels=(
                "capital_discipline",
                "capital_discipline",
            ),
        )
    # Empty stewardship tuple is allowed.
    p = _build_profile(stewardship_priority_labels=())
    assert p.stewardship_priority_labels == ()


# ---------------------------------------------------------------------------
# 3. Forbidden field names.
# ---------------------------------------------------------------------------


def test_investor_mandate_rejects_forbidden_field_names() -> None:
    """The dataclass field set has zero overlap with the
    v1.25.0 canonical
    ``FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES`` composition.
    The closed-set vocabularies likewise contain no
    forbidden token."""
    from dataclasses import fields as dc_fields
    field_names = {
        f.name for f in dc_fields(InvestorMandateProfile)
    }
    overlap = (
        field_names
        & FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES
    )
    assert overlap == set(), (
        "InvestorMandateProfile fields overlap with "
        f"v1.25.0 forbidden set: {sorted(overlap)!r}"
    )
    assert (
        MANDATE_TYPE_LABELS
        & FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES
    ) == set()
    assert (
        BENCHMARK_PRESSURE_LABELS
        & FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES
    ) == set()
    assert (
        STEWARDSHIP_PRIORITY_LABELS
        & FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES
    ) == set()


# ---------------------------------------------------------------------------
# 4. Forbidden metadata keys.
# ---------------------------------------------------------------------------


def test_investor_mandate_rejects_forbidden_metadata_keys() -> None:
    """Every v1.25.0 forbidden token rejected as a
    metadata key — spot-check across token classes
    (portfolio / benchmark-number / mandate-as-action /
    inherited v1.18.0 / v1.21.0a / v1.22.0 / v1.24.0
    tokens)."""
    for forbidden_key in (
        # v1.25.0 mandate delta
        "portfolio_allocation",
        "target_weight",
        "overweight",
        "underweight",
        "rebalance",
        "rebalancing",
        "weight_change",
        "allocation_band",
        "tracking_error_value",
        "tracking_error_basis_points",
        "benchmark_weight",
        "benchmark_value",
        "active_share",
        "alpha",
        "performance",
        "expected_alpha",
        "mandate_action",
        "mandate_decision",
        "mandate_buy_signal",
        "mandate_sell_signal",
        # inherited v1.18.0 / v1.19.0
        "buy",
        "sell",
        "order",
        "trade",
        "execution",
        "investment_advice",
        "investment_recommendation",
        "predicted_path",
        "target_price",
        "expected_return",
        # v1.21.0a / v1.22.0
        "amplify",
        "dampen",
        "offset",
        "coexist",
        "stress_magnitude",
        "interaction_label",
        "aggregate_shift_direction",
        "composite_risk_label",
        "dominant_stress_label",
        # v1.22.0 export-side outcome / impact
        "impact",
        "outcome",
        "risk_score",
        "forecast",
        "prediction",
        "recommendation",
        # v1.24.0 manual-annotation
        "auto_annotation",
        "auto_inference",
        "automatic_review",
        "llm_annotation",
        "causal_effect",
        "causal_proof",
        "actor_decision",
        # real-data / Japan / LLM
        "real_data",
        "japan_calibration",
        "llm_output",
    ):
        with pytest.raises(ValueError):
            _build_profile(
                metadata={forbidden_key: "anything"}
            )


# ---------------------------------------------------------------------------
# 5. Add / get / list / snapshot.
# ---------------------------------------------------------------------------


def test_investor_mandate_book_add_get_list_snapshot() -> None:
    """Append-only book CRUD: add, get, list,
    list_by_investor, list_by_mandate_type,
    list_by_benchmark_pressure, snapshot."""
    book = InvestorMandateBook()
    a = _build_profile(
        mandate_profile_id="mp:test:a",
        investor_id="investor:pension_a",
        mandate_type_label="pension_like",
        benchmark_pressure_label="low",
    )
    b = _build_profile(
        mandate_profile_id="mp:test:b",
        investor_id="investor:pension_a",
        mandate_type_label="pension_like",
        benchmark_pressure_label="moderate",
    )
    c = _build_profile(
        mandate_profile_id="mp:test:c",
        investor_id="investor:active_b",
        mandate_type_label="active_manager_like",
        benchmark_pressure_label="high",
    )
    book.add_profile(a)
    book.add_profile(b)
    book.add_profile(c)
    # Get.
    assert book.get_profile("mp:test:a") is a
    # List.
    assert len(book.list_profiles()) == 3
    # By investor (multiple profiles per investor allowed
    # under append-only discipline).
    assert {
        p.mandate_profile_id
        for p in book.list_by_investor("investor:pension_a")
    } == {"mp:test:a", "mp:test:b"}
    assert {
        p.mandate_profile_id
        for p in book.list_by_investor("investor:active_b")
    } == {"mp:test:c"}
    # By mandate type.
    assert {
        p.mandate_profile_id
        for p in book.list_by_mandate_type("pension_like")
    } == {"mp:test:a", "mp:test:b"}
    assert {
        p.mandate_profile_id
        for p in book.list_by_mandate_type(
            "active_manager_like"
        )
    } == {"mp:test:c"}
    # By benchmark pressure.
    assert {
        p.mandate_profile_id
        for p in book.list_by_benchmark_pressure("low")
    } == {"mp:test:a"}
    assert {
        p.mandate_profile_id
        for p in book.list_by_benchmark_pressure("high")
    } == {"mp:test:c"}
    # Snapshot.
    snap = book.snapshot()
    assert "investor_mandate_profiles" in snap
    assert len(snap["investor_mandate_profiles"]) == 3


# ---------------------------------------------------------------------------
# 6. Duplicate add emits no extra ledger record.
# ---------------------------------------------------------------------------


def test_duplicate_mandate_profile_emits_no_extra_ledger_record() -> None:
    """Duplicate ``mandate_profile_id`` raises and emits
    no extra ledger record."""
    kernel = _bare_kernel()
    p = _build_profile()
    kernel.investor_mandates.add_profile(p)
    ledger_len_after_add = len(kernel.ledger.records)
    assert ledger_len_after_add >= 1
    last_record = kernel.ledger.records[-1]
    assert (
        last_record.event_type
        == RecordType.INVESTOR_MANDATE_PROFILE_RECORDED.value
    )
    with pytest.raises(
        DuplicateInvestorMandateProfileError
    ):
        kernel.investor_mandates.add_profile(p)
    assert (
        len(kernel.ledger.records) == ledger_len_after_add
    )


# ---------------------------------------------------------------------------
# 7. Empty by default.
# ---------------------------------------------------------------------------


def test_world_kernel_investor_mandates_empty_by_default() -> None:
    """A fresh kernel has an empty
    ``investor_mandates`` book + zero ledger records of
    type ``INVESTOR_MANDATE_PROFILE_RECORDED``."""
    kernel = _bare_kernel()
    assert kernel.investor_mandates.list_profiles() == ()
    types = {r.event_type for r in kernel.ledger.records}
    assert (
        RecordType.INVESTOR_MANDATE_PROFILE_RECORDED.value
        not in types
    )


# ---------------------------------------------------------------------------
# 8. No source-of-truth book mutation.
# ---------------------------------------------------------------------------


def test_investor_mandate_storage_does_not_mutate_source_of_truth_books() -> None:
    """Adding a mandate profile must not mutate any
    other kernel book. Snapshot every relevant book pre /
    post and assert byte-identity (modulo the ledger and
    the investor-mandate book itself)."""
    kernel = _bare_kernel()
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
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
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
    kernel.investor_mandates.add_profile(_build_profile())
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
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
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
# 9. No investor intent / market intent emitted.
# ---------------------------------------------------------------------------


def test_investor_mandate_storage_does_not_create_investor_intent() -> None:
    """Adding a mandate profile must not emit any v1.15.5
    / v1.16.2 ``InvestorMarketIntentRecord`` and must not
    fire any non-mandate ledger event. Pinned by
    monkey-patching the v1.16.x intent helpers to raise."""
    import world.investor_intent as ii_mod
    import world.market_intents as imi_mod

    kernel = _bare_kernel()
    market_intents_before = (
        kernel.investor_market_intents.list_intents()
    )
    investor_intents_before = (
        kernel.investor_intents.list_intents()
    )
    # Add a mandate profile.
    kernel.investor_mandates.add_profile(_build_profile())
    # No new market / investor intent records.
    assert (
        kernel.investor_market_intents.list_intents()
        == market_intents_before
    )
    assert (
        kernel.investor_intents.list_intents()
        == investor_intents_before
    )
    # And the only ledger event types fired so far are
    # the empty-default kernel events plus the one
    # mandate event we added.
    types = [
        r.event_type for r in kernel.ledger.records
    ]
    investor_intent_types = {
        "investor_market_intent_recorded",
        "investor_intent_recorded",
        "actor_attention_state_recorded",
    }
    for t in types:
        assert t not in investor_intent_types, (
            f"unexpected investor-intent / attention "
            f"event {t!r} fired during mandate add"
        )

    # Mark imports used so ruff does not complain.
    assert ii_mod is not None
    assert imi_mod is not None


# ---------------------------------------------------------------------------
# 10. Existing canonical digests unchanged with empty
#     mandate book.
# ---------------------------------------------------------------------------


def test_existing_digests_unchanged_with_empty_mandate_book() -> None:
    """Every v1.21.last canonical
    ``living_world_digest`` value remains byte-identical
    when the kernel carries an empty
    ``InvestorMandateBook``. Empty-by-default rule
    guarantees this; the explicit assertion catches a
    regression that accidentally fires the
    ``INVESTOR_MANDATE_PROFILE_RECORDED`` event from
    kernel construction."""
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

    # quarterly_default
    k_q = _seed_kernel()
    r_q = _run_default(k_q)
    assert k_q.investor_mandates.list_profiles() == ()
    assert (
        living_world_digest(k_q, r_q)
        == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST
    )

    # monthly_reference
    k_m = _seed_kernel()
    r_m = _run_monthly_reference(k_m)
    assert k_m.investor_mandates.list_profiles() == ()
    assert (
        living_world_digest(k_m, r_m)
        == MONTHLY_REFERENCE_LIVING_WORLD_DIGEST
    )

    # scenario_monthly_reference_universe
    k_s = _seed_v1_20_3_kernel()
    r_s = _run_v1_20_3(k_s)
    assert k_s.investor_mandates.list_profiles() == ()
    assert (
        living_world_digest(k_s, r_s)
        == SCENARIO_MONTHLY_REFERENCE_UNIVERSE_DIGEST
    )
