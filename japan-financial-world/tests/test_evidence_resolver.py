"""
Tests for v1.12.3 EvidenceRef + ActorContextFrame +
EvidenceResolver / ``resolve_actor_context``.

Covers field validation (including bounded ``confidence`` with
explicit bool rejection), immutability, prefix dispatch over
every v1.9 → v1.12.2 id type, selection-driven resolution,
explicit-id resolution, unresolved-ref capture, strict mode,
no-mutation against every other v0/v1 source-of-truth book in
the kernel, no-ledger-write-by-default invariant, no-content-
leak (dialogue records never leak content into the frame),
deterministic output across two fresh resolver calls, and a
jurisdiction-neutral identifier scan.

Identifier and tag strings used in this test suite are
jurisdiction-neutral and synthetic; no Japan-specific institution
name, regulator, exchange, vendor benchmark, code, or threshold
appears anywhere in the test body.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import date

import pytest

from world.attention import (
    AttentionProfile,
    ObservationMenu,
    SelectedObservationSet,
)
from world.clock import Clock
from world.engagement import (
    InvestorEscalationCandidate,
    PortfolioCompanyDialogueRecord,
)
from world.evidence import (
    ALL_BUCKETS,
    ActorContextFrame,
    EvidenceRef,
    EvidenceResolver,
    StrictEvidenceResolutionError,
    resolve_actor_context,
)
from world.exposures import ExposureRecord
from world.firm_state import FirmFinancialStateRecord
from world.industry import IndustryDemandConditionRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.market_conditions import MarketConditionRecord
from world.market_environment import MarketEnvironmentStateRecord
from world.market_surface_readout import build_capital_market_readout
from world.registry import Registry
from world.scheduler import Scheduler
from world.signals import InformationSignal
from world.state import State
from world.valuations import ValuationRecord
from world.variables import ReferenceVariableSpec, VariableObservation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _seed_signal(
    kernel: WorldKernel, *, signal_id: str = "signal:reference_corp_a:2026-03-31"
) -> str:
    kernel.signals.add_signal(
        InformationSignal(
            signal_id=signal_id,
            signal_type="reference_quarterly_report",
            subject_id="firm:reference_corp_a",
            source_id="firm:reference_corp_a",
            published_date="2026-03-31",
            payload={"note": "synthetic"},
            visibility="public",
        )
    )
    return signal_id


def _seed_variable_observation(
    kernel: WorldKernel,
    *,
    obs_id: str = "obs:variable:reference_long_rate_10y:2026-03-31",
) -> str:
    var = ReferenceVariableSpec(
        variable_id="variable:reference_long_rate_10y",
        variable_name="Reference Long Rate 10y",
        variable_group="reference_macro",
        variable_type="rate",
        source_space_id="reference_space",
        canonical_unit="reference_unit",
        frequency="MONTHLY",
        observation_kind="released",
    )
    if not kernel.variables.list_variables():
        kernel.variables.add_variable(var)
    kernel.variables.add_observation(
        VariableObservation(
            observation_id=obs_id,
            variable_id="variable:reference_long_rate_10y",
            as_of_date="2026-03-31",
            value=0.5,
            unit="reference_unit",
            vintage_id="2026-03-31_initial",
        )
    )
    return obs_id


def _seed_exposure(
    kernel: WorldKernel,
    *,
    exposure_id: str = "exposure:investor:reference_pension_a:fx",
) -> str:
    kernel.exposures.add_exposure(
        ExposureRecord(
            exposure_id=exposure_id,
            subject_id="investor:reference_pension_a",
            subject_type="investor",
            variable_id="variable:reference_long_rate_10y",
            exposure_type="reference_synthetic",
            metric="reference_metric",
            direction="long",
            magnitude=0.5,
            confidence=0.5,
        )
    )
    return exposure_id


def _seed_market_condition(
    kernel: WorldKernel,
    *,
    cid: str = "market_condition:reference_rates:2026-03-31",
) -> str:
    kernel.market_conditions.add_condition(
        MarketConditionRecord(
            condition_id=cid,
            market_id="market:reference_rates_general",
            market_type="reference_rates",
            as_of_date="2026-03-31",
            condition_type="rate_level",
            direction="supportive",
            strength=0.5,
            time_horizon="medium_term",
            confidence=0.5,
            status="active",
            visibility="internal_only",
        )
    )
    return cid


def _seed_market_readout(
    kernel: WorldKernel,
    *,
    as_of_date: str = "2026-03-31",
) -> tuple[str, tuple[str, ...]]:
    cids: list[str] = []
    for market_id, market_type, condition_type in (
        (
            "market:reference_rates_general",
            "reference_rates",
            "rate_level",
        ),
        (
            "market:reference_credit_spreads_general",
            "credit_spreads",
            "spread_level",
        ),
        (
            "market:reference_equity_general",
            "equity_market",
            "valuation_environment",
        ),
        (
            "market:reference_funding_general",
            "funding_market",
            "funding_window",
        ),
        (
            "market:reference_liquidity_general",
            "liquidity_market",
            "liquidity_regime",
        ),
    ):
        cid = f"market_condition:{market_id}:{as_of_date}"
        kernel.market_conditions.add_condition(
            MarketConditionRecord(
                condition_id=cid,
                market_id=market_id,
                market_type=market_type,
                as_of_date=as_of_date,
                condition_type=condition_type,
                direction="supportive",
                strength=0.5,
                time_horizon="medium_term",
                confidence=0.5,
                status="active",
                visibility="internal_only",
            )
        )
        cids.append(cid)
    readout = build_capital_market_readout(
        kernel,
        as_of_date=as_of_date,
        market_condition_ids=tuple(cids),
    )
    return readout.readout_id, tuple(cids)


def _seed_market_environment(
    kernel: WorldKernel,
    *,
    env_id: str = "market_environment:2026-03-31",
) -> str:
    kernel.market_environments.add_state(
        MarketEnvironmentStateRecord(
            environment_state_id=env_id,
            as_of_date="2026-03-31",
            liquidity_regime="normal",
            volatility_regime="calm",
            credit_regime="neutral",
            funding_regime="normal",
            risk_appetite_regime="neutral",
            rate_environment="low",
            refinancing_window="open",
            equity_valuation_regime="neutral",
            overall_market_access_label="open_or_constructive",
            status="active",
            visibility="internal_only",
            confidence=0.5,
        )
    )
    return env_id


def _seed_industry_condition(
    kernel: WorldKernel,
    *,
    cid: str = "industry_condition:reference_general:2026-03-31",
) -> str:
    kernel.industry_conditions.add_condition(
        IndustryDemandConditionRecord(
            condition_id=cid,
            industry_id="industry:reference_general",
            industry_label="Reference Industry",
            as_of_date="2026-03-31",
            condition_type="demand_state",
            demand_direction="stable",
            demand_strength=0.5,
            confidence=0.5,
            time_horizon="medium_term",
            status="active",
            visibility="internal_only",
        )
    )
    return cid


def _seed_firm_state(
    kernel: WorldKernel,
    *,
    state_id: str = "firm_state:firm:reference_corp_a:2026-03-31",
) -> str:
    kernel.firm_financial_states.add_state(
        FirmFinancialStateRecord(
            state_id=state_id,
            firm_id="firm:reference_corp_a",
            as_of_date="2026-03-31",
            status="active",
            visibility="internal_only",
            margin_pressure=0.5,
            liquidity_pressure=0.5,
            debt_service_pressure=0.5,
            market_access_pressure=0.5,
            funding_need_intensity=0.5,
            response_readiness=0.5,
            confidence=0.5,
        )
    )
    return state_id


def _seed_valuation(
    kernel: WorldKernel,
    *,
    val_id: str = "valuation:reference_lite:reference_corp_a:2026-03-31",
) -> str:
    kernel.valuations.add_valuation(
        ValuationRecord(
            valuation_id=val_id,
            subject_id="firm:reference_corp_a",
            valuer_id="investor:reference_pension_a",
            valuation_type="reference_synthetic",
            purpose="reference_synthetic_purpose",
            method="dcf",
            as_of_date="2026-03-31",
            estimated_value=100.0,
            currency="reference_unit",
            confidence=0.5,
        )
    )
    return val_id


def _seed_dialogue(
    kernel: WorldKernel,
    *,
    dlg_id: str = "dialogue:investor:reference_pension_a:firm:reference_corp_a:2026-03-31",
) -> str:
    kernel.engagement.add_dialogue(
        PortfolioCompanyDialogueRecord(
            dialogue_id=dlg_id,
            initiator_id="investor:reference_pension_a",
            counterparty_id="firm:reference_corp_a",
            initiator_type="investor",
            counterparty_type="firm",
            as_of_date="2026-03-31",
            dialogue_type="reference_engagement",
            status="completed",
            outcome_label="reference_outcome",
            next_step_label="reference_next_step",
            visibility="restricted",
        )
    )
    return dlg_id


def _seed_escalation(
    kernel: WorldKernel,
    *,
    esc_id: str = "escalation:investor:reference_pension_a:firm:reference_corp_a:2026-03-31",
) -> str:
    kernel.escalations.add_candidate(
        InvestorEscalationCandidate(
            escalation_candidate_id=esc_id,
            investor_id="investor:reference_pension_a",
            target_company_id="firm:reference_corp_a",
            as_of_date="2026-03-31",
            escalation_type="reference_escalation",
            status="draft",
            priority="medium",
            horizon="medium_term",
            rationale_label="reference_rationale",
            next_step_label="reference_next_step",
            visibility="restricted",
        )
    )
    return esc_id


def _seed_selection(
    kernel: WorldKernel,
    *,
    actor_id: str = "investor:reference_pension_a",
    selection_id: str = "selection:reference:investor:reference_pension_a:2026-03-31",
    selected_refs: tuple[str, ...] = (),
) -> str:
    profile_id = "profile:reference_pension_a"
    if not kernel.attention.list_profiles():
        kernel.attention.add_profile(
            AttentionProfile(
                profile_id=profile_id,
                actor_id=actor_id,
                actor_type="investor",
                update_frequency="QUARTERLY",
                watched_signal_types=("reference_quarterly_report",),
                priority_weights={"reference_quarterly_report": 0.5},
            )
        )
    menu_id = f"menu:{actor_id}:2026-03-31"
    try:
        kernel.attention.get_menu(menu_id)
    except Exception:
        kernel.attention.add_menu(
            ObservationMenu(
                menu_id=menu_id,
                actor_id=actor_id,
                as_of_date="2026-03-31",
            )
        )
    kernel.attention.add_selection(
        SelectedObservationSet(
            selection_id=selection_id,
            actor_id=actor_id,
            attention_profile_id=profile_id,
            menu_id=menu_id,
            selection_reason="explicit",
            as_of_date="2026-03-31",
            status="completed",
            selected_refs=selected_refs,
        )
    )
    return selection_id


# ---------------------------------------------------------------------------
# EvidenceRef — field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ref_id": ""},
        {"ref_type": ""},
        {"source_book": ""},
        {"status": ""},
    ],
)
def test_evidence_ref_rejects_empty_required_strings(kwargs):
    base = {
        "ref_id": "x",
        "ref_type": "y",
        "source_book": "z",
        "status": "resolved",
    }
    base.update(kwargs)
    with pytest.raises(ValueError):
        EvidenceRef(**base)


def test_evidence_ref_rejects_unknown_status():
    with pytest.raises(ValueError):
        EvidenceRef(
            ref_id="x", ref_type="y", source_book="z", status="bogus"
        )


def test_evidence_ref_is_frozen():
    r = EvidenceRef(
        ref_id="x", ref_type="y", source_book="z", status="resolved"
    )
    with pytest.raises(Exception):
        r.ref_id = "tampered"  # type: ignore[misc]


def test_evidence_ref_to_dict_round_trips():
    r = EvidenceRef(
        ref_id="signal:a",
        ref_type="signal",
        source_book="signals",
        status="resolved",
        metadata={"origin": "selection"},
    )
    out = r.to_dict()
    assert out == {
        "ref_id": "signal:a",
        "ref_type": "signal",
        "source_book": "signals",
        "status": "resolved",
        "metadata": {"origin": "selection"},
    }


# ---------------------------------------------------------------------------
# ActorContextFrame — field validation
# ---------------------------------------------------------------------------


def _frame(**overrides) -> ActorContextFrame:
    base = {
        "context_frame_id": "context_frame:investor:a:2026-03-31",
        "actor_id": "investor:a",
        "actor_type": "investor",
        "as_of_date": "2026-03-31",
        "status": "resolved",
        "confidence": 1.0,
    }
    base.update(overrides)
    return ActorContextFrame(**base)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"context_frame_id": ""},
        {"actor_id": ""},
        {"actor_type": ""},
        {"as_of_date": ""},
        {"status": ""},
    ],
)
def test_frame_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _frame(**kwargs)


@pytest.mark.parametrize("value", [-0.01, 1.01, -1.0, 1.5, 100.0])
def test_frame_confidence_rejects_out_of_range(value):
    with pytest.raises(ValueError):
        _frame(confidence=value)


@pytest.mark.parametrize("value", [0.0, 0.25, 1.0])
def test_frame_confidence_accepts_in_range(value):
    f = _frame(confidence=value)
    assert f.confidence == float(value)


def test_frame_confidence_rejects_bool_true():
    with pytest.raises(ValueError):
        _frame(confidence=True)


def test_frame_confidence_rejects_bool_false():
    with pytest.raises(ValueError):
        _frame(confidence=False)


@pytest.mark.parametrize(
    "value",
    ["high", None, [], object()],
)
def test_frame_confidence_rejects_non_numeric(value):
    with pytest.raises(ValueError):
        _frame(confidence=value)


@pytest.mark.parametrize(
    "tuple_field",
    [
        "selected_observation_set_ids",
        "resolved_signal_ids",
        "resolved_variable_observation_ids",
        "resolved_exposure_ids",
        "resolved_market_condition_ids",
        "resolved_market_readout_ids",
        "resolved_market_environment_state_ids",
        "resolved_industry_condition_ids",
        "resolved_firm_state_ids",
        "resolved_valuation_ids",
        "resolved_dialogue_ids",
        "resolved_escalation_candidate_ids",
    ],
)
def test_frame_rejects_empty_strings_in_tuple_fields(tuple_field):
    with pytest.raises(ValueError):
        _frame(**{tuple_field: ("",)})


def test_frame_unresolved_refs_must_be_evidence_ref():
    with pytest.raises(ValueError):
        _frame(unresolved_refs=("not_an_evidence_ref",))


def test_frame_coerces_as_of_date_to_iso_string():
    f = _frame(as_of_date=date(2026, 3, 31))
    assert f.as_of_date == "2026-03-31"


def test_frame_is_frozen():
    f = _frame()
    with pytest.raises(Exception):
        f.actor_id = "tampered"  # type: ignore[misc]


def test_frame_to_dict_round_trips_buckets():
    f = _frame(
        resolved_signal_ids=("signal:a",),
        resolved_market_environment_state_ids=("market_environment:a",),
        unresolved_refs=(
            EvidenceRef(
                ref_id="x",
                ref_type="unknown_prefix",
                source_book="unknown",
                status="unresolved",
            ),
        ),
    )
    out = f.to_dict()
    assert out["resolved_signal_ids"] == ["signal:a"]
    assert out["resolved_market_environment_state_ids"] == [
        "market_environment:a"
    ]
    assert out["unresolved_refs"][0]["ref_id"] == "x"


# ---------------------------------------------------------------------------
# Anti-fields — no content / order / recommendation / etc.
# ---------------------------------------------------------------------------


def test_frame_record_has_no_content_or_recommendation_field():
    """v1.12.3 frame must store ids only — never content,
    transcript, notes, minutes, attendees, order, trade,
    rebalance, target weight, expected return, target price,
    recommendation, investment advice, portfolio allocation,
    or execution. Pin the absence."""
    field_names = {f.name for f in dataclass_fields(ActorContextFrame)}
    forbidden = {
        "content",
        "transcript",
        "notes",
        "minutes",
        "attendees",
        "order",
        "trade",
        "buy",
        "sell",
        "rebalance",
        "target_weight",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "portfolio_allocation",
        "execution",
    }
    leaked = field_names & forbidden
    assert not leaked, (
        f"ActorContextFrame must not declare anti-fields; leaked: "
        f"{sorted(leaked)}"
    )


# ---------------------------------------------------------------------------
# All buckets accounted for
# ---------------------------------------------------------------------------


def test_all_buckets_have_a_frame_field():
    field_names = {f.name for f in dataclass_fields(ActorContextFrame)}
    for bucket in ALL_BUCKETS:
        slot = f"resolved_{bucket}_ids"
        assert slot in field_names, (
            f"frame must expose a '{slot}' tuple for bucket "
            f"{bucket!r}"
        )


# ---------------------------------------------------------------------------
# Resolver — basic
# ---------------------------------------------------------------------------


def test_resolver_attached_to_kernel():
    k = _kernel()
    assert isinstance(k.evidence_resolver, EvidenceResolver)
    assert k.evidence_resolver.kernel is k


def test_resolver_kernel_required():
    with pytest.raises(ValueError):
        resolve_actor_context(
            None,
            actor_id="investor:a",
            actor_type="investor",
            as_of_date="2026-03-31",
        )


def test_resolver_actor_id_required():
    k = _kernel()
    with pytest.raises(ValueError):
        resolve_actor_context(
            k,
            actor_id="",
            actor_type="investor",
            as_of_date="2026-03-31",
        )


def test_resolver_actor_type_required():
    k = _kernel()
    with pytest.raises(ValueError):
        resolve_actor_context(
            k,
            actor_id="investor:a",
            actor_type="",
            as_of_date="2026-03-31",
        )


def test_resolver_no_inputs_yields_empty_frame():
    k = _kernel()
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
    )
    assert f.status == "empty"
    assert f.confidence == 1.0
    for bucket in ALL_BUCKETS:
        assert getattr(f, f"resolved_{bucket}_ids") == ()
    assert f.unresolved_refs == ()


def test_resolver_default_id_format():
    k = _kernel()
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
    )
    assert f.context_frame_id == "context_frame:investor:a:2026-03-31"


def test_resolver_explicit_context_frame_id_overrides_default():
    k = _kernel()
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        context_frame_id="context_frame:custom",
    )
    assert f.context_frame_id == "context_frame:custom"


# ---------------------------------------------------------------------------
# Resolver — explicit ids by bucket
# ---------------------------------------------------------------------------


def test_resolver_explicit_signal_id_resolves():
    k = _kernel()
    sid = _seed_signal(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(sid,),
    )
    assert f.resolved_signal_ids == (sid,)
    assert f.status == "resolved"
    assert f.confidence == 1.0


def test_resolver_explicit_variable_observation_id_resolves():
    k = _kernel()
    obs = _seed_variable_observation(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_variable_observation_ids=(obs,),
    )
    assert f.resolved_variable_observation_ids == (obs,)


def test_resolver_explicit_exposure_id_resolves():
    k = _kernel()
    eid = _seed_exposure(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_exposure_ids=(eid,),
    )
    assert f.resolved_exposure_ids == (eid,)


def test_resolver_explicit_market_condition_id_resolves():
    k = _kernel()
    cid = _seed_market_condition(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_market_condition_ids=(cid,),
    )
    assert f.resolved_market_condition_ids == (cid,)


def test_resolver_explicit_market_readout_id_resolves():
    k = _kernel()
    readout_id, _ = _seed_market_readout(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_market_readout_ids=(readout_id,),
    )
    assert f.resolved_market_readout_ids == (readout_id,)


def test_resolver_explicit_market_environment_state_id_resolves():
    k = _kernel()
    env = _seed_market_environment(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_market_environment_state_ids=(env,),
    )
    assert f.resolved_market_environment_state_ids == (env,)


def test_resolver_explicit_industry_condition_id_resolves():
    k = _kernel()
    cid = _seed_industry_condition(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_industry_condition_ids=(cid,),
    )
    assert f.resolved_industry_condition_ids == (cid,)


def test_resolver_explicit_firm_state_id_resolves():
    k = _kernel()
    fsid = _seed_firm_state(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_firm_state_ids=(fsid,),
    )
    assert f.resolved_firm_state_ids == (fsid,)


def test_resolver_explicit_valuation_id_resolves():
    k = _kernel()
    vid = _seed_valuation(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_valuation_ids=(vid,),
    )
    assert f.resolved_valuation_ids == (vid,)


def test_resolver_explicit_dialogue_id_resolves():
    k = _kernel()
    did = _seed_dialogue(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_dialogue_ids=(did,),
    )
    assert f.resolved_dialogue_ids == (did,)


def test_resolver_explicit_escalation_candidate_id_resolves():
    k = _kernel()
    eid = _seed_escalation(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_escalation_candidate_ids=(eid,),
    )
    assert f.resolved_escalation_candidate_ids == (eid,)


# ---------------------------------------------------------------------------
# Resolver — selection-driven
# ---------------------------------------------------------------------------


def test_resolver_selection_resolves_signal_refs_by_prefix():
    k = _kernel()
    sid = _seed_signal(k)
    sel_id = _seed_selection(k, selected_refs=(sid,))
    f = resolve_actor_context(
        k,
        actor_id="investor:reference_pension_a",
        actor_type="investor",
        as_of_date="2026-03-31",
        selected_observation_set_ids=(sel_id,),
    )
    assert f.resolved_signal_ids == (sid,)
    assert f.unresolved_refs == ()


def test_resolver_selection_buckets_each_prefix_correctly():
    k = _kernel()
    refs = (
        _seed_signal(k),
        _seed_variable_observation(k),
        _seed_exposure(k),
        _seed_market_condition(k),
        _seed_market_environment(k),
        _seed_industry_condition(k),
        _seed_firm_state(k),
        _seed_valuation(k),
        _seed_dialogue(k),
        _seed_escalation(k),
    )
    readout_id, _ = _seed_market_readout(k, as_of_date="2026-03-31")
    refs = refs + (readout_id,)
    sel_id = _seed_selection(k, selected_refs=refs)
    f = resolve_actor_context(
        k,
        actor_id="investor:reference_pension_a",
        actor_type="investor",
        as_of_date="2026-03-31",
        selected_observation_set_ids=(sel_id,),
    )
    assert refs[0] in f.resolved_signal_ids
    assert refs[1] in f.resolved_variable_observation_ids
    assert refs[2] in f.resolved_exposure_ids
    assert refs[3] in f.resolved_market_condition_ids
    assert refs[4] in f.resolved_market_environment_state_ids
    assert refs[5] in f.resolved_industry_condition_ids
    assert refs[6] in f.resolved_firm_state_ids
    assert refs[7] in f.resolved_valuation_ids
    assert refs[8] in f.resolved_dialogue_ids
    assert refs[9] in f.resolved_escalation_candidate_ids
    assert readout_id in f.resolved_market_readout_ids
    assert f.status == "resolved"


def test_resolver_unknown_selection_id_goes_to_unresolved():
    k = _kernel()
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        selected_observation_set_ids=("selection:nonexistent",),
    )
    assert f.unresolved_refs
    assert f.unresolved_refs[0].ref_id == "selection:nonexistent"
    assert f.unresolved_refs[0].ref_type == "selection"
    assert f.unresolved_refs[0].source_book == "attention"
    assert f.status == "partially_resolved"
    assert 0.0 <= f.confidence < 1.0


def test_resolver_selection_with_unknown_prefix_goes_to_unresolved():
    k = _kernel()
    sel_id = _seed_selection(
        k, selected_refs=("totally_unknown_prefix:foo",)
    )
    f = resolve_actor_context(
        k,
        actor_id="investor:reference_pension_a",
        actor_type="investor",
        as_of_date="2026-03-31",
        selected_observation_set_ids=(sel_id,),
    )
    assert any(
        r.ref_type == "unknown_prefix"
        for r in f.unresolved_refs
    )


def test_resolver_unknown_explicit_id_goes_to_unresolved():
    k = _kernel()
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=("signal:does_not_exist",),
    )
    assert any(
        r.ref_id == "signal:does_not_exist" for r in f.unresolved_refs
    )
    assert f.status == "partially_resolved"


def test_resolver_dedup_preserves_first_seen_order():
    k = _kernel()
    s1 = _seed_signal(k, signal_id="signal:a")
    s2 = _seed_signal(k, signal_id="signal:b")
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(s2, s1, s2, s1),
    )
    assert f.resolved_signal_ids == (s2, s1)


def test_resolver_explicit_unknown_dedup_in_unresolved():
    k = _kernel()
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=("signal:nope", "signal:nope"),
    )
    # The same (id, bucket) pair should be reported once.
    matching = [r for r in f.unresolved_refs if r.ref_id == "signal:nope"]
    assert len(matching) == 1


# ---------------------------------------------------------------------------
# Resolver — strict mode
# ---------------------------------------------------------------------------


def test_resolver_strict_mode_raises_on_unknown_explicit_id():
    k = _kernel()
    with pytest.raises(StrictEvidenceResolutionError):
        resolve_actor_context(
            k,
            actor_id="investor:a",
            actor_type="investor",
            as_of_date="2026-03-31",
            explicit_signal_ids=("signal:nope",),
            strict=True,
        )


def test_resolver_strict_mode_passes_when_all_resolve():
    k = _kernel()
    sid = _seed_signal(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(sid,),
        strict=True,
    )
    assert f.status == "resolved"


def test_resolver_strict_mode_raises_on_unknown_selection():
    k = _kernel()
    with pytest.raises(StrictEvidenceResolutionError):
        resolve_actor_context(
            k,
            actor_id="investor:a",
            actor_type="investor",
            as_of_date="2026-03-31",
            selected_observation_set_ids=("selection:nope",),
            strict=True,
        )


# ---------------------------------------------------------------------------
# Resolver — invariants
# ---------------------------------------------------------------------------


def test_resolver_does_not_emit_any_ledger_record():
    """v1.12.3 default: no ledger writes, period."""
    k = _kernel()
    sid = _seed_signal(k)
    ledger_count_before = len(k.ledger.records)
    resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(sid,),
    )
    new_records = k.ledger.records[ledger_count_before:]
    # Only the signals book's add_signal call earlier emitted; no
    # additional records appear because of resolve_actor_context.
    assert all(
        r.record_type.value != "actor_context_frame_resolved"
        for r in new_records
    )
    # And specifically: the resolver did not append any records
    # *after* the snapshot we took.
    assert len(k.ledger.records) == ledger_count_before


def test_resolver_does_not_mutate_other_kernel_books():
    k = _kernel()
    sid = _seed_signal(k)
    _seed_market_environment(k)
    _seed_firm_state(k)

    snaps_before = {
        "ownership": k.ownership.snapshot(),
        "contracts": k.contracts.snapshot(),
        "prices": k.prices.snapshot(),
        "constraints": k.constraints.snapshot(),
        "signals": k.signals.snapshot(),
        "valuations": k.valuations.snapshot(),
        "institutions": k.institutions.snapshot(),
        "external_processes": k.external_processes.snapshot(),
        "relationships": k.relationships.snapshot(),
        "interactions": k.interactions.snapshot(),
        "routines": k.routines.snapshot(),
        "attention": k.attention.snapshot(),
        "variables": k.variables.snapshot(),
        "exposures": k.exposures.snapshot(),
        "stewardship": k.stewardship.snapshot(),
        "engagement": k.engagement.snapshot(),
        "escalations": k.escalations.snapshot(),
        "strategic_responses": k.strategic_responses.snapshot(),
        "industry_conditions": k.industry_conditions.snapshot(),
        "market_conditions": k.market_conditions.snapshot(),
        "capital_market_readouts": k.capital_market_readouts.snapshot(),
        "market_environments": k.market_environments.snapshot(),
        "firm_financial_states": k.firm_financial_states.snapshot(),
        "investor_intents": k.investor_intents.snapshot(),
    }
    ledger_before = len(k.ledger.records)

    resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(sid,),
        explicit_market_environment_state_ids=("market_environment:2026-03-31",),
        explicit_firm_state_ids=("firm_state:firm:reference_corp_a:2026-03-31",),
    )

    for name, before in snaps_before.items():
        after = getattr(k, name).snapshot()
        assert after == before, f"book {name!r} was mutated"
    assert len(k.ledger.records) == ledger_before


def test_resolver_does_not_scan_books_globally():
    """The resolver must not surface a record the caller did not
    cite — even if the record exists in the kernel and would
    have been a relevant piece of evidence."""
    k = _kernel()
    s_unrelated = _seed_signal(k, signal_id="signal:unrelated:2026-03-31")
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        # Do NOT cite the signal; resolver should leave it out.
    )
    assert s_unrelated not in f.resolved_signal_ids
    assert f.status == "empty"


def test_resolver_dialogue_resolution_does_not_leak_content():
    """Dialogue records carry restricted-visibility metadata.
    The resolver must surface only the dialogue_id; the frame
    must contain no ``content`` / ``transcript`` / etc."""
    k = _kernel()
    did = _seed_dialogue(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:reference_pension_a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_dialogue_ids=(did,),
    )
    assert f.resolved_dialogue_ids == (did,)
    out = f.to_dict()
    # The frame's serialized form must not contain any
    # confidential content key.
    forbidden = {
        "content",
        "transcript",
        "notes",
        "minutes",
        "attendees",
    }
    leaked = set(out.keys()) & forbidden
    assert not leaked, (
        f"frame serialization leaked confidential keys: "
        f"{sorted(leaked)}"
    )


def test_resolver_deterministic_for_identical_inputs():
    """Two fresh kernels with identical wiring + identical
    resolver calls produce byte-identical frames."""
    k_a = _kernel()
    sid_a = _seed_signal(k_a)
    f_a = resolve_actor_context(
        k_a,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(sid_a,),
    )
    k_b = _kernel()
    sid_b = _seed_signal(k_b)
    f_b = resolve_actor_context(
        k_b,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(sid_b,),
    )
    assert f_a.to_dict() == f_b.to_dict()


def test_resolver_partial_resolution_lowers_confidence():
    k = _kernel()
    sid = _seed_signal(k)
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(sid, "signal:nope"),
    )
    assert f.status == "partially_resolved"
    assert 0.0 < f.confidence < 1.0


def test_resolver_kwarg_bucket_overrides_prefix_dispatch():
    """An id passed in via ``explicit_signal_ids`` lands in the
    signal bucket regardless of its actual prefix. This is the
    escape hatch for callers whose ids do not follow the
    orchestrator's id conventions."""
    k = _kernel()
    # Seed a signal with an *off-prefix* id that the prefix
    # dispatch would not classify as a signal on its own.
    odd_signal_id = "intent:as_signal_evidence:2026-03-31"
    k.signals.add_signal(
        InformationSignal(
            signal_id=odd_signal_id,
            signal_type="reference_quarterly_report",
            subject_id="firm:reference_corp_a",
            source_id="firm:reference_corp_a",
            published_date="2026-03-31",
            payload={"note": "synthetic"},
            visibility="public",
        )
    )
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(odd_signal_id,),
    )
    assert f.resolved_signal_ids == (odd_signal_id,)


# ---------------------------------------------------------------------------
# Resolver class wrapper
# ---------------------------------------------------------------------------


def test_resolver_class_wraps_module_helper():
    k = _kernel()
    sid = _seed_signal(k)
    via_class = k.evidence_resolver.resolve_actor_context(
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(sid,),
    )
    via_module = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        explicit_signal_ids=(sid,),
    )
    assert via_class.to_dict() == via_module.to_dict()


def test_resolver_metadata_kwarg_lands_on_frame():
    k = _kernel()
    f = resolve_actor_context(
        k,
        actor_id="investor:a",
        actor_type="investor",
        as_of_date="2026-03-31",
        metadata={"note": "synthetic"},
    )
    assert f.metadata == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Resolver — selection + explicit composition
# ---------------------------------------------------------------------------


def test_resolver_selection_then_explicit_preserves_order():
    """Selection refs come first, then explicit kwargs in
    declared order. Within a bucket, first-seen wins on dups."""
    k = _kernel()
    s1 = _seed_signal(k, signal_id="signal:a")
    s2 = _seed_signal(k, signal_id="signal:b")
    s3 = _seed_signal(k, signal_id="signal:c")
    sel_id = _seed_selection(k, selected_refs=(s1, s2))
    f = resolve_actor_context(
        k,
        actor_id="investor:reference_pension_a",
        actor_type="investor",
        as_of_date="2026-03-31",
        selected_observation_set_ids=(sel_id,),
        # s2 is a dup with selection; s3 is a new explicit add.
        explicit_signal_ids=(s2, s3),
    )
    assert f.resolved_signal_ids == (s1, s2, s3)


# ---------------------------------------------------------------------------
# Jurisdiction-neutral identifier scan
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "jgb", "nyse",
)


def test_test_file_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    text = Path(__file__).read_text(encoding="utf-8").lower()
    table_start = text.find("_forbidden_tokens = (")
    table_end = text.find(")", table_start) + 1
    if table_start != -1 and table_end > 0:
        text = text[:table_start] + text[table_end:]

    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in test file"
        )


def test_evidence_module_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parent.parent / "world" / "evidence.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in "
            f"world/evidence.py"
        )
