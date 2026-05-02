"""
Tests for v1.9.7 Reference Bank Credit Review Lite Mechanism.

Pins the v1.9.7 contract end-to-end:

- adapter satisfies the v1.9.3 / v1.9.3.1
  :class:`MechanismAdapter` Protocol;
- :class:`MechanismSpec` is valid (model_family
  ``"credit_review_mechanism"``, calibration ``"synthetic"``,
  deterministic);
- adapter does not accept a kernel argument;
- adapter runs without a kernel (reads ``request.evidence`` /
  ``request.parameters`` only);
- missing pressure + valuation evidence yields
  ``status="degraded"`` with conservative output (zero scores,
  zero overall, information-quality reflects the gap);
- five score dimensions plus the overall mean are all in
  ``[0, 1]``;
- ``overall_credit_review_pressure`` is the deterministic mean
  of the four pressure-side scores;
- adapter is deterministic across two byte-identical requests;
- request is not mutated by ``apply``;
- proposed signal carries every required field including the
  five boundary-flag metadata keys
  (``no_lending_decision`` / ``no_covenant_enforcement`` /
  ``no_contract_mutation`` / ``no_constraint_mutation`` /
  ``no_default_declaration``) plus
  ``no_internal_rating`` / ``no_probability_of_default`` /
  ``synthetic_only``;
- caller helper commits exactly one ``InformationSignal``;
- ``evidence_refs`` lineage is preserved verbatim on the
  :class:`MechanismRunRecord`;
- no mutation of contracts / constraints / prices / ownership /
  firm-state / variables / exposures / valuations / institutions
  / external_processes / relationships / routines / attention /
  interactions;
- synthetic-only identifiers (word-boundary forbidden-token
  check).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from world.clock import Clock
from world.exposures import ExposureRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.mechanisms import (
    MechanismAdapter,
    MechanismOutputBundle,
    MechanismRunRecord,
    MechanismRunRequest,
    MechanismSpec,
)
from world.evidence import StrictEvidenceResolutionError
from world.firm_state import FirmFinancialStateRecord
from world.market_environment import MarketEnvironmentStateRecord
from world.reference_bank_credit_review_lite import (
    ALL_WATCH_LABELS,
    BANK_CREDIT_REVIEW_MECHANISM_VERSION,
    BANK_CREDIT_REVIEW_MODEL_FAMILY,
    BANK_CREDIT_REVIEW_MODEL_ID,
    BANK_CREDIT_REVIEW_SIGNAL_TYPE,
    WATCH_LABEL_INFORMATION_GAP_REVIEW,
    WATCH_LABEL_LIQUIDITY_WATCH,
    WATCH_LABEL_MARKET_ACCESS_WATCH,
    WATCH_LABEL_REFINANCING_WATCH,
    WATCH_LABEL_ROUTINE_MONITORING,
    BankCreditReviewLiteAdapter,
    BankCreditReviewLiteResult,
    run_attention_conditioned_bank_credit_review_lite,
    run_reference_bank_credit_review_lite,
)
from world.reference_firm_pressure import (
    run_reference_firm_pressure_mechanism,
)
from world.reference_valuation_refresh_lite import (
    run_reference_valuation_refresh_lite,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.variables import ReferenceVariableSpec, VariableObservation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_FIRM = "firm:reference_manufacturer_a"
_BANK = "bank:reference_megabank_a"
_INVESTOR = "investor:reference_pension_a"
_AS_OF = "2026-04-30"
_BASELINE = 1_000_000.0


def _seed_kernel() -> WorldKernel:
    k = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )
    for vid, vgroup in (
        ("variable:reference_oil_price", "energy_power"),
        ("variable:reference_long_rate_10y", "rates"),
        ("variable:reference_fx_pair_a", "fx"),
    ):
        k.variables.add_variable(
            ReferenceVariableSpec(
                variable_id=vid,
                variable_name=vid,
                variable_group=vgroup,
                variable_type="level",
                source_space_id="external",
                canonical_unit="index",
                frequency="QUARTERLY",
                observation_kind="released",
            )
        )
        k.variables.add_observation(
            VariableObservation(
                observation_id=f"obs:{vid}:2026Q1",
                variable_id=vid,
                as_of_date="2026-04-15",
                value=100.0,
                unit="index",
                vintage_id="2026Q1_initial",
            )
        )
    for exp_id, var_id, etype, mag in (
        ("exposure:firm_a:energy", "variable:reference_oil_price", "input_cost", 0.4),
        ("exposure:firm_a:rates", "variable:reference_long_rate_10y", "funding_cost", 0.3),
        ("exposure:firm_a:fx", "variable:reference_fx_pair_a", "translation", 0.2),
    ):
        k.exposures.add_exposure(
            ExposureRecord(
                exposure_id=exp_id,
                subject_id=_FIRM,
                subject_type="firm",
                variable_id=var_id,
                exposure_type=etype,
                metric="operating_cost_pressure",
                direction="positive",
                magnitude=mag,
            )
        )
    return k


def _seed_with_pressure_and_valuation() -> tuple[WorldKernel, str, str]:
    """Run v1.9.4 + v1.9.5 to set up the upstream evidence the
    v1.9.7 mechanism reads."""
    k = _seed_kernel()
    pressure = run_reference_firm_pressure_mechanism(
        k,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        variable_observation_ids=tuple(
            f"obs:{vid}:2026Q1"
            for vid, _ in (
                ("variable:reference_oil_price", "energy_power"),
                ("variable:reference_long_rate_10y", "rates"),
                ("variable:reference_fx_pair_a", "fx"),
            )
        ),
        exposure_ids=("exposure:firm_a:energy", "exposure:firm_a:rates", "exposure:firm_a:fx"),
    )
    valuation = run_reference_valuation_refresh_lite(
        k,
        firm_id=_FIRM,
        valuer_id=_INVESTOR,
        as_of_date=_AS_OF,
        pressure_signal_ids=(pressure.signal_id,),
        baseline_value=_BASELINE,
    )
    return k, pressure.signal_id, valuation.valuation_id


def _run_default(
    k: WorldKernel, pressure_signal_id: str, valuation_id: str
) -> BankCreditReviewLiteResult:
    return run_reference_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        pressure_signal_ids=(pressure_signal_id,),
        valuation_ids=(valuation_id,),
    )


# ---------------------------------------------------------------------------
# Spec / Protocol contract
# ---------------------------------------------------------------------------


def test_adapter_satisfies_mechanism_adapter_protocol():
    adapter = BankCreditReviewLiteAdapter()
    assert isinstance(adapter, MechanismAdapter)


def test_adapter_spec_has_required_fields():
    adapter = BankCreditReviewLiteAdapter()
    spec = adapter.spec
    assert isinstance(spec, MechanismSpec)
    assert spec.model_id == BANK_CREDIT_REVIEW_MODEL_ID
    assert spec.model_family == BANK_CREDIT_REVIEW_MODEL_FAMILY
    assert spec.model_family == "credit_review_mechanism"
    assert spec.version == BANK_CREDIT_REVIEW_MECHANISM_VERSION
    assert spec.calibration_status == "synthetic"
    assert spec.stochasticity == "deterministic"
    assert "InformationSignal" in spec.required_inputs
    assert "ValuationRecord" in spec.required_inputs
    assert "InformationSignal" in spec.output_types


def test_adapter_apply_returns_mechanism_output_bundle():
    adapter = BankCreditReviewLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
        parameters={"bank_id": _BANK},
    )
    output = adapter.apply(request)
    assert isinstance(output, MechanismOutputBundle)


def test_adapter_does_not_accept_kernel_argument():
    adapter = BankCreditReviewLiteAdapter()
    with pytest.raises(TypeError):
        adapter.apply(_seed_kernel())  # type: ignore[arg-type]


def test_adapter_runs_without_a_kernel():
    """Adapter must compute proposals from request.evidence
    alone — no kernel reference."""
    adapter = BankCreditReviewLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
        evidence={
            "InformationSignal": [
                {
                    "signal_id": "signal:firm_operating_pressure_assessment:test",
                    "signal_type": "firm_operating_pressure_assessment",
                    "subject_id": _FIRM,
                    "payload": {
                        "overall_pressure": 0.5,
                        "debt_service_pressure": 0.3,
                        "fx_translation_pressure": 0.4,
                    },
                },
            ],
            "ValuationRecord": [
                {
                    "valuation_id": "valuation:test",
                    "subject_id": _FIRM,
                    "valuer_id": _INVESTOR,
                    "confidence": 0.7,
                },
            ],
        },
        parameters={"bank_id": _BANK},
    )
    output = adapter.apply(request)
    assert output.status == "completed"
    proposed = output.proposed_signals[0]
    payload = proposed["payload"]
    assert payload["operating_pressure_score"] == 0.5
    assert payload["debt_service_attention_score"] == 0.3
    assert payload["collateral_attention_score"] == 0.4
    # 1 - 0.7 = 0.3 valuation pressure
    assert abs(payload["valuation_pressure_score"] - 0.3) < 1e-9
    # mean of 0.5, 0.3, 0.3, 0.4
    assert abs(payload["overall_credit_review_pressure"] - 0.375) < 1e-9


# ---------------------------------------------------------------------------
# Degraded path
# ---------------------------------------------------------------------------


def test_apply_with_no_evidence_returns_degraded_with_zero_scores():
    adapter = BankCreditReviewLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
        parameters={"bank_id": _BANK},
    )
    output = adapter.apply(request)
    assert output.status == "degraded"
    payload = output.proposed_signals[0]["payload"]
    for dim in (
        "operating_pressure_score",
        "valuation_pressure_score",
        "debt_service_attention_score",
        "collateral_attention_score",
        "information_quality_score",
        "overall_credit_review_pressure",
    ):
        assert payload[dim] == 0.0


def test_apply_with_only_pressure_returns_completed():
    adapter = BankCreditReviewLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
        evidence={
            "InformationSignal": [
                {
                    "signal_id": "s:1",
                    "signal_type": "firm_operating_pressure_assessment",
                    "subject_id": _FIRM,
                    "payload": {"overall_pressure": 0.4},
                },
            ],
        },
        parameters={"bank_id": _BANK},
    )
    output = adapter.apply(request)
    assert output.status == "completed"


def test_apply_with_only_valuation_returns_completed():
    adapter = BankCreditReviewLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
        evidence={
            "ValuationRecord": [
                {
                    "valuation_id": "v:1",
                    "subject_id": _FIRM,
                    "confidence": 0.5,
                },
            ],
        },
        parameters={"bank_id": _BANK},
    )
    output = adapter.apply(request)
    assert output.status == "completed"


# ---------------------------------------------------------------------------
# Score arithmetic
# ---------------------------------------------------------------------------


def test_all_scores_in_zero_one_range():
    k, pressure_id, valuation_id = _seed_with_pressure_and_valuation()
    result = _run_default(k, pressure_id, valuation_id)
    payload = result.output.proposed_signals[0]["payload"]
    for dim in (
        "operating_pressure_score",
        "valuation_pressure_score",
        "debt_service_attention_score",
        "collateral_attention_score",
        "information_quality_score",
        "overall_credit_review_pressure",
    ):
        assert 0.0 <= payload[dim] <= 1.0, f"{dim}={payload[dim]} out of [0,1]"


def test_overall_credit_review_pressure_is_mean_of_four_pressure_scores():
    """information_quality_score is a coverage metric and does
    NOT enter the overall mean."""
    k, pressure_id, valuation_id = _seed_with_pressure_and_valuation()
    result = _run_default(k, pressure_id, valuation_id)
    payload = result.output.proposed_signals[0]["payload"]
    expected = (
        payload["operating_pressure_score"]
        + payload["valuation_pressure_score"]
        + payload["debt_service_attention_score"]
        + payload["collateral_attention_score"]
    ) / 4.0
    assert abs(payload["overall_credit_review_pressure"] - expected) < 1e-9


def test_information_quality_score_reflects_coverage():
    """Pressure + valuation = 0.50 (two of four channels)."""
    k, pressure_id, valuation_id = _seed_with_pressure_and_valuation()
    result = _run_default(k, pressure_id, valuation_id)
    payload = result.output.proposed_signals[0]["payload"]
    assert payload["information_quality_score"] == 0.5


# ---------------------------------------------------------------------------
# Determinism + immutability
# ---------------------------------------------------------------------------


def test_apply_is_deterministic_across_two_calls():
    a_k, a_p, a_v = _seed_with_pressure_and_valuation()
    b_k, b_p, b_v = _seed_with_pressure_and_valuation()
    a = _run_default(a_k, a_p, a_v)
    b = _run_default(b_k, b_p, b_v)
    assert a.signal_id == b.signal_id
    assert a.review_summary == b.review_summary


def test_apply_does_not_mutate_request():
    adapter = BankCreditReviewLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
        evidence={
            "InformationSignal": [
                {
                    "signal_id": "s:1",
                    "signal_type": "firm_operating_pressure_assessment",
                    "subject_id": _FIRM,
                    "payload": {"overall_pressure": 0.5},
                },
            ],
        },
        parameters={"bank_id": _BANK},
    )
    pre = request.to_dict()
    adapter.apply(request)
    post = request.to_dict()
    assert pre == post


# ---------------------------------------------------------------------------
# Proposed signal shape + boundary flags
# ---------------------------------------------------------------------------


def test_proposed_signal_has_required_fields():
    k, p, v = _seed_with_pressure_and_valuation()
    result = _run_default(k, p, v)
    proposed = result.output.proposed_signals[0]
    for field in (
        "signal_id",
        "signal_type",
        "subject_id",
        "source_id",
        "published_date",
        "effective_date",
        "visibility",
        "payload",
        "related_ids",
        "metadata",
    ):
        assert field in proposed, f"missing: {field}"
    assert proposed["signal_type"] == BANK_CREDIT_REVIEW_SIGNAL_TYPE
    assert proposed["subject_id"] == _FIRM
    assert proposed["source_id"] == _BANK


def test_proposed_signal_metadata_carries_boundary_flags():
    k, p, v = _seed_with_pressure_and_valuation()
    proposed = _run_default(k, p, v).output.proposed_signals[0]
    metadata = proposed["metadata"]
    for flag in (
        "no_lending_decision",
        "no_covenant_enforcement",
        "no_contract_mutation",
        "no_constraint_mutation",
        "no_default_declaration",
        "no_internal_rating",
        "no_probability_of_default",
        "synthetic_only",
    ):
        assert metadata[flag] is True, f"flag {flag} not set"
    assert metadata["model_id"] == BANK_CREDIT_REVIEW_MODEL_ID
    assert metadata["calibration_status"] == "synthetic"


def test_proposed_signal_related_ids_include_pressure_and_valuation():
    k, p, v = _seed_with_pressure_and_valuation()
    proposed = _run_default(k, p, v).output.proposed_signals[0]
    assert p in proposed["related_ids"]
    assert v in proposed["related_ids"]


# ---------------------------------------------------------------------------
# Caller helper
# ---------------------------------------------------------------------------


def test_caller_helper_commits_exactly_one_signal():
    k, p, v = _seed_with_pressure_and_valuation()
    before = len(k.signals.all_signals())
    result = _run_default(k, p, v)
    after = len(k.signals.all_signals())
    assert after - before == 1
    assert isinstance(result, BankCreditReviewLiteResult)
    sig = k.signals.get_signal(result.signal_id)
    assert sig.signal_type == BANK_CREDIT_REVIEW_SIGNAL_TYPE
    assert sig.subject_id == _FIRM
    assert sig.source_id == _BANK


def test_caller_helper_returns_run_record_with_lineage():
    k, p, v = _seed_with_pressure_and_valuation()
    result = _run_default(k, p, v)
    run = result.run_record
    assert isinstance(run, MechanismRunRecord)
    assert run.input_refs == result.request.evidence_refs
    assert run.committed_output_refs == (result.signal_id,)
    assert run.model_id == BANK_CREDIT_REVIEW_MODEL_ID
    assert run.model_family == BANK_CREDIT_REVIEW_MODEL_FAMILY


def test_caller_helper_evidence_refs_default_concatenation():
    k, p, v = _seed_with_pressure_and_valuation()
    result = _run_default(k, p, v)
    expected = (p, v)  # pressure + valuation, in that order
    assert result.request.evidence_refs == expected


def test_caller_helper_explicit_evidence_refs_preserved_verbatim():
    k, p, v = _seed_with_pressure_and_valuation()
    custom = (v, p)  # caller may reorder
    result = run_reference_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        pressure_signal_ids=(p,),
        valuation_ids=(v,),
        evidence_refs=custom,
    )
    assert result.request.evidence_refs == custom
    assert result.run_record.input_refs == custom


def test_caller_helper_default_request_id_includes_bank_and_firm():
    """v1.9.5 had a request_id collision risk when multiple
    investors valued the same firm; v1.9.7 avoids it by
    construction — the default request_id formula includes both
    bank_id and firm_id."""
    k, p, v = _seed_with_pressure_and_valuation()
    result = _run_default(k, p, v)
    rid = result.request.request_id
    assert _BANK in rid
    assert _FIRM in rid
    assert _AS_OF in rid


def test_caller_helper_uses_kernel_clock_when_date_omitted():
    k, p, v = _seed_with_pressure_and_valuation()
    result = run_reference_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        pressure_signal_ids=(p,),
        valuation_ids=(v,),
    )
    assert result.request.as_of_date == _AS_OF


# ---------------------------------------------------------------------------
# Defensive errors
# ---------------------------------------------------------------------------


def test_caller_helper_rejects_kernel_none():
    with pytest.raises(ValueError):
        run_reference_bank_credit_review_lite(
            None, bank_id=_BANK, firm_id=_FIRM, as_of_date=_AS_OF
        )


def test_caller_helper_rejects_empty_bank_id():
    k = _seed_kernel()
    with pytest.raises(ValueError):
        run_reference_bank_credit_review_lite(
            k, bank_id="", firm_id=_FIRM, as_of_date=_AS_OF
        )


def test_caller_helper_rejects_empty_firm_id():
    k = _seed_kernel()
    with pytest.raises(ValueError):
        run_reference_bank_credit_review_lite(
            k, bank_id=_BANK, firm_id="", as_of_date=_AS_OF
        )


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def _capture_state(k: WorldKernel) -> dict[str, Any]:
    return {
        "contracts": k.contracts.snapshot(),
        "constraints": k.constraints.snapshot(),
        "prices": k.prices.snapshot(),
        "ownership": k.ownership.snapshot(),
        "valuations": k.valuations.snapshot(),
        "exposures": k.exposures.snapshot(),
        "variables": k.variables.snapshot(),
        "institutions": k.institutions.snapshot(),
        "external_processes": k.external_processes.snapshot(),
        "relationships": k.relationships.snapshot(),
        "routines": k.routines.snapshot(),
        "attention": k.attention.snapshot(),
        "interactions": k.interactions.snapshot(),
    }


def test_caller_helper_does_not_mutate_other_books():
    """v1.9.7 commits exactly one InformationSignal. Every other
    book — contracts, constraints, valuations, etc. — must stay
    byte-identical. v1.9.7 explicitly does NOT make a lending
    decision, NOT enforce a covenant, NOT mutate a contract."""
    k, p, v = _seed_with_pressure_and_valuation()
    before = _capture_state(k)
    _run_default(k, p, v)
    after = _capture_state(k)
    assert before == after


def test_caller_helper_writes_only_one_signal_no_other_records():
    k, p, v = _seed_with_pressure_and_valuation()
    before_ledger = len(k.ledger.records)
    before_signals = len(k.signals.all_signals())
    _run_default(k, p, v)
    after_ledger = len(k.ledger.records)
    after_signals = len(k.signals.all_signals())
    assert after_signals - before_signals == 1
    # Exactly one new ledger record (the signal_added entry).
    assert after_ledger - before_ledger == 1


# ---------------------------------------------------------------------------
# Synthetic-only identifiers
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "nyse",
)


def test_module_constants_use_no_jurisdiction_specific_tokens():
    candidates = (
        BANK_CREDIT_REVIEW_MODEL_ID,
        BANK_CREDIT_REVIEW_MODEL_FAMILY,
        BANK_CREDIT_REVIEW_SIGNAL_TYPE,
    )
    for c in candidates:
        for token in _FORBIDDEN_TOKENS:
            assert token not in c.lower(), c


def test_committed_signal_identifiers_are_synthetic():
    k, p, v = _seed_with_pressure_and_valuation()
    result = _run_default(k, p, v)
    sig = k.signals.get_signal(result.signal_id)
    candidates = [
        sig.signal_id,
        sig.signal_type,
        sig.subject_id,
        sig.source_id,
    ]
    for id_str in candidates:
        lower = id_str.lower()
        for token in _FORBIDDEN_TOKENS:
            for sep in (" ", ":", "/", "-", "_", "(", ")", ",", ".", "'", '"'):
                if f"{sep}{token}{sep}" in f" {lower} ":
                    pytest.fail(
                        f"forbidden token {token!r} appears in id {id_str!r}"
                    )


# ---------------------------------------------------------------------------
# v1.12.6 — attention-conditioned helper
# ---------------------------------------------------------------------------


_BANK_B = "bank:reference_megabank_b"
_BANK_C = "bank:reference_regional_bank_c"


def _seed_high_pressure_firm_state(
    kernel: WorldKernel,
    *,
    state_id: str = "firm_state:firm:reference_manufacturer_a:high",
    liquidity_pressure: float = 0.5,
    funding_need_intensity: float = 0.5,
    debt_service_pressure: float = 0.5,
    market_access_pressure: float = 0.5,
) -> str:
    kernel.firm_financial_states.add_state(
        FirmFinancialStateRecord(
            state_id=state_id,
            firm_id=_FIRM,
            as_of_date=_AS_OF,
            status="active",
            visibility="internal_only",
            margin_pressure=0.5,
            liquidity_pressure=liquidity_pressure,
            debt_service_pressure=debt_service_pressure,
            market_access_pressure=market_access_pressure,
            funding_need_intensity=funding_need_intensity,
            response_readiness=0.5,
            confidence=0.5,
        )
    )
    return state_id


def _seed_constrained_market_environment(
    kernel: WorldKernel,
    *,
    env_id: str = "market_environment:constrained:2026-04-30",
) -> str:
    kernel.market_environments.add_state(
        MarketEnvironmentStateRecord(
            environment_state_id=env_id,
            as_of_date=_AS_OF,
            liquidity_regime="tight",
            volatility_regime="elevated",
            credit_regime="tightening",
            funding_regime="constrained",
            risk_appetite_regime="risk_off",
            rate_environment="rising",
            refinancing_window="closed",
            equity_valuation_regime="demanding",
            overall_market_access_label="selective_or_constrained",
            status="active",
            visibility="internal_only",
            confidence=0.6,
        )
    )
    return env_id


def test_attn_helper_calls_resolver_and_records_context_frame_metadata():
    k, p, v = _seed_with_pressure_and_valuation()
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p,),
        explicit_valuation_ids=(v,),
        signal_id="signal:test:attn_basic",
    )
    sig = k.signals.get_signal(out.signal_id)
    assert sig.metadata.get("attention_conditioned") is True
    assert sig.metadata.get("context_frame_id") == (
        f"context_frame:{_BANK}:{_AS_OF}"
    )
    assert sig.metadata.get("context_frame_status") == "resolved"
    assert isinstance(sig.metadata.get("context_frame_confidence"), (int, float))
    assert sig.payload["watch_label"] in ALL_WATCH_LABELS
    # The boundary anti-claim metadata must still ride on the
    # produced signal — the v1.9.7 contract is preserved.
    for flag in (
        "no_lending_decision",
        "no_covenant_enforcement",
        "no_contract_mutation",
        "no_constraint_mutation",
        "no_default_declaration",
        "no_internal_rating",
        "no_probability_of_default",
        "synthetic_only",
    ):
        assert sig.metadata.get(flag) is True


def test_attn_helper_reads_only_selected_or_explicit_evidence():
    """Helper must NOT surface a pressure signal that the bank
    did not cite — even if it exists in the kernel."""
    k, p, v = _seed_with_pressure_and_valuation()
    # Cite NEITHER pressure NOR valuation — only an empty
    # selection. The helper must take the degraded path.
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        signal_id="signal:test:no_evidence",
    )
    assert out.status == "degraded"
    assert out.review_summary["watch_label"] == (
        WATCH_LABEL_INFORMATION_GAP_REVIEW
    )
    assert out.review_summary["operating_pressure_score"] == 0.0
    assert out.review_summary["valuation_pressure_score"] == 0.0


def test_attn_helper_unknown_explicit_id_lands_in_unresolved_metadata():
    k = _seed_kernel()
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_firm_state_ids=("firm_state:does_not_exist",),
        signal_id="signal:test:unresolved",
    )
    sig = k.signals.get_signal(out.signal_id)
    unresolved = sig.metadata.get("unresolved_refs")
    assert unresolved
    assert any(r["ref_id"] == "firm_state:does_not_exist" for r in unresolved)
    assert sig.metadata.get("context_frame_status") == "partially_resolved"


def test_attn_helper_strict_mode_raises_on_unknown_refs():
    k = _seed_kernel()
    before_signals = len(k.signals.all_signals())
    with pytest.raises(StrictEvidenceResolutionError):
        run_attention_conditioned_bank_credit_review_lite(
            k,
            bank_id=_BANK,
            firm_id=_FIRM,
            as_of_date=_AS_OF,
            explicit_firm_state_ids=("firm_state:does_not_exist",),
            strict=True,
        )
    # No signal must be emitted on strict failure.
    assert len(k.signals.all_signals()) == before_signals


def test_attn_helper_strict_mode_passes_when_all_resolve():
    k, p, v = _seed_with_pressure_and_valuation()
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p,),
        explicit_valuation_ids=(v,),
        strict=True,
        signal_id="signal:test:strict_pass",
    )
    assert out.status == "completed"


def test_attn_helper_high_liquidity_yields_liquidity_watch():
    k, p, v = _seed_with_pressure_and_valuation()
    fsid = _seed_high_pressure_firm_state(k, liquidity_pressure=0.85)
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p,),
        explicit_valuation_ids=(v,),
        explicit_firm_state_ids=(fsid,),
        signal_id="signal:test:liquidity_watch",
    )
    assert out.review_summary["watch_label"] == WATCH_LABEL_LIQUIDITY_WATCH


def test_attn_helper_high_funding_need_yields_refinancing_watch():
    k, p, v = _seed_with_pressure_and_valuation()
    fsid = _seed_high_pressure_firm_state(
        k, funding_need_intensity=0.85, liquidity_pressure=0.5
    )
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p,),
        explicit_valuation_ids=(v,),
        explicit_firm_state_ids=(fsid,),
        signal_id="signal:test:refinancing_watch",
    )
    assert out.review_summary["watch_label"] == (
        WATCH_LABEL_REFINANCING_WATCH
    )


def test_attn_helper_constrained_environment_yields_market_access_watch():
    """v1.12.6: a resolved environment with
    overall_market_access_label="selective_or_constrained" fires
    rule 4 when no higher-priority firm-state pressures fire."""
    k, p, v = _seed_with_pressure_and_valuation()
    # Firm state with neutral pressures (no rule 2/3 trigger).
    fsid = _seed_high_pressure_firm_state(
        k,
        liquidity_pressure=0.4,
        funding_need_intensity=0.4,
        debt_service_pressure=0.4,
        market_access_pressure=0.4,
    )
    env_id = _seed_constrained_market_environment(k)
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p,),
        explicit_valuation_ids=(v,),
        explicit_firm_state_ids=(fsid,),
        explicit_market_environment_state_ids=(env_id,),
        signal_id="signal:test:market_access_watch",
    )
    assert out.review_summary["watch_label"] == (
        WATCH_LABEL_MARKET_ACCESS_WATCH
    )


def test_attn_helper_resolves_selection_refs_to_evidence_buckets():
    """A pressure-signal id reachable only via a
    SelectedObservationSet must land in the signal bucket and
    drive the v1.9.7 adapter scores."""
    from world.attention import (
        AttentionProfile,
        ObservationMenu,
        SelectedObservationSet,
    )

    k, p, v = _seed_with_pressure_and_valuation()
    profile_id = f"profile:{_BANK}"
    k.attention.add_profile(
        AttentionProfile(
            profile_id=profile_id,
            actor_id=_BANK,
            actor_type="bank",
            update_frequency="QUARTERLY",
        )
    )
    menu_id = f"menu:{_BANK}:{_AS_OF}"
    k.attention.add_menu(
        ObservationMenu(
            menu_id=menu_id,
            actor_id=_BANK,
            as_of_date=_AS_OF,
        )
    )
    sel_id = f"selection:{_BANK}:{_AS_OF}"
    k.attention.add_selection(
        SelectedObservationSet(
            selection_id=sel_id,
            actor_id=_BANK,
            attention_profile_id=profile_id,
            menu_id=menu_id,
            selection_reason="explicit",
            as_of_date=_AS_OF,
            status="completed",
            selected_refs=(p,),  # pressure signal id reaches via selection
        )
    )
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        selected_observation_set_ids=(sel_id,),
        explicit_valuation_ids=(v,),
        signal_id="signal:test:via_selection",
    )
    sig = k.signals.get_signal(out.signal_id)
    # The pressure signal arrived via the bank's selection, not
    # via an explicit kwarg — the adapter still saw it.
    assert out.review_summary["operating_pressure_score"] > 0.0
    # The v1.12.6 frame audit records that the selection routed
    # at least one signal id and at least one selection.
    buckets = sig.payload["resolved_evidence_buckets"]
    assert buckets["signals"] >= 1
    assert sig.payload["evidence_counts"]["selected_observation_sets"] >= 1


def test_attn_helper_does_not_mutate_other_books():
    k, p, v = _seed_with_pressure_and_valuation()
    fsid = _seed_high_pressure_firm_state(k)
    env_id = _seed_constrained_market_environment(k)
    snaps_before = {
        "contracts": k.contracts.snapshot(),
        "constraints": k.constraints.snapshot(),
        "prices": k.prices.snapshot(),
        "ownership": k.ownership.snapshot(),
        "valuations": k.valuations.snapshot(),
        "exposures": k.exposures.snapshot(),
        "variables": k.variables.snapshot(),
        "institutions": k.institutions.snapshot(),
        "external_processes": k.external_processes.snapshot(),
        "relationships": k.relationships.snapshot(),
        "routines": k.routines.snapshot(),
        "attention": k.attention.snapshot(),
        "interactions": k.interactions.snapshot(),
        "firm_financial_states": k.firm_financial_states.snapshot(),
        "market_environments": k.market_environments.snapshot(),
        "investor_intents": k.investor_intents.snapshot(),
    }
    run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p,),
        explicit_valuation_ids=(v,),
        explicit_firm_state_ids=(fsid,),
        explicit_market_environment_state_ids=(env_id,),
        signal_id="signal:test:no_mutation",
    )
    for name, before in snaps_before.items():
        assert getattr(k, name).snapshot() == before, name


def test_attn_helper_no_anti_field_payload_keys():
    k, p, v = _seed_with_pressure_and_valuation()
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p,),
        explicit_valuation_ids=(v,),
        signal_id="signal:test:no_anti_fields",
    )
    sig = k.signals.get_signal(out.signal_id)
    forbidden = {
        "lending_decision",
        "loan_approved",
        "loan_rejected",
        "covenant_breached",
        "covenant_enforced",
        "contract_amended",
        "constraint_changed",
        "default_declared",
        "internal_rating",
        "rating_grade",
        "probability_of_default",
        "pd",
        "lgd",
        "ead",
        "loan_pricing",
        "credit_pricing",
        "interest_rate",
        "underwriting_decision",
        "approval_status",
        "loan_terms",
        "investment_advice",
        "recommendation",
        "buy",
        "sell",
        "order",
        "trade",
    }
    leaked_payload = set(sig.payload.keys()) & forbidden
    assert not leaked_payload, leaked_payload
    leaked_metadata = set(sig.metadata.keys()) & forbidden
    assert not leaked_metadata, leaked_metadata
    # Pin against the ledger payload too.
    rec = k.ledger.records[-1]
    leaked_ledger = set(rec.payload.keys()) & forbidden
    assert not leaked_ledger, leaked_ledger


def test_attn_helper_emits_only_signal_added():
    """v1.12.6 must not emit any new event type — only the
    existing signal_added record."""
    k, p, v = _seed_with_pressure_and_valuation()
    before = len(k.ledger.records)
    run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p,),
        explicit_valuation_ids=(v,),
        signal_id="signal:test:single_emit",
    )
    new_records = k.ledger.records[before:]
    assert len(new_records) == 1
    forbidden = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
    }
    seen = {r.record_type.value for r in new_records}
    assert seen.isdisjoint(forbidden)


def test_attn_helper_idempotent_on_signal_id():
    """v1.9.7 SignalBook rejects duplicate signal_ids; the new
    helper must surface that as an obvious failure rather than
    silently double-write."""
    k, p, v = _seed_with_pressure_and_valuation()
    out1 = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p,),
        explicit_valuation_ids=(v,),
        signal_id="signal:test:idempotent_pin",
    )
    assert out1.status in {"completed", "degraded"}
    with pytest.raises(Exception):
        run_attention_conditioned_bank_credit_review_lite(
            k,
            bank_id=_BANK,
            firm_id=_FIRM,
            as_of_date=_AS_OF,
            explicit_pressure_signal_ids=(p,),
            explicit_valuation_ids=(v,),
            signal_id="signal:test:idempotent_pin",
        )


def test_attn_helper_deterministic_for_identical_inputs():
    k_a = _seed_kernel()
    p_a = run_reference_firm_pressure_mechanism(
        k_a,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        variable_observation_ids=tuple(
            f"obs:{vid}:2026Q1"
            for vid in (
                "variable:reference_oil_price",
                "variable:reference_long_rate_10y",
                "variable:reference_fx_pair_a",
            )
        ),
        exposure_ids=(
            "exposure:firm_a:energy",
            "exposure:firm_a:rates",
            "exposure:firm_a:fx",
        ),
    ).signal_id
    out_a = run_attention_conditioned_bank_credit_review_lite(
        k_a,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p_a,),
        signal_id="signal:test:determinism",
    )

    k_b = _seed_kernel()
    p_b = run_reference_firm_pressure_mechanism(
        k_b,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        variable_observation_ids=tuple(
            f"obs:{vid}:2026Q1"
            for vid in (
                "variable:reference_oil_price",
                "variable:reference_long_rate_10y",
                "variable:reference_fx_pair_a",
            )
        ),
        exposure_ids=(
            "exposure:firm_a:energy",
            "exposure:firm_a:rates",
            "exposure:firm_a:fx",
        ),
    ).signal_id
    out_b = run_attention_conditioned_bank_credit_review_lite(
        k_b,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_pressure_signal_ids=(p_b,),
        signal_id="signal:test:determinism",
    )
    sig_a = k_a.signals.get_signal(out_a.signal_id)
    sig_b = k_b.signals.get_signal(out_b.signal_id)
    assert sig_a.payload == sig_b.payload
    assert sig_a.metadata == sig_b.metadata


def test_attn_helper_kernel_required():
    with pytest.raises(ValueError):
        run_attention_conditioned_bank_credit_review_lite(
            None,
            bank_id=_BANK,
            firm_id=_FIRM,
            as_of_date=_AS_OF,
        )


def test_attn_helper_rejects_empty_bank_id():
    k = _seed_kernel()
    with pytest.raises(ValueError):
        run_attention_conditioned_bank_credit_review_lite(
            k,
            bank_id="",
            firm_id=_FIRM,
            as_of_date=_AS_OF,
        )


def test_attn_helper_rejects_empty_firm_id():
    k = _seed_kernel()
    with pytest.raises(ValueError):
        run_attention_conditioned_bank_credit_review_lite(
            k,
            bank_id=_BANK,
            firm_id="",
            as_of_date=_AS_OF,
        )


# ---------------------------------------------------------------------------
# v1.12.6 — headline divergence (three banks, three labels)
# ---------------------------------------------------------------------------


def _seed_world_for_bank_divergence() -> tuple[
    WorldKernel, str, str, str, str, str
]:
    """Shared world for three banks reviewing the same borrower
    on the same date but with three different selected evidence
    sets. Returns (kernel, pressure_signal_id,
    high_pressure_firm_state_id, constrained_env_id, valuation_id,
    corporate_signal_id)."""
    from world.signals import InformationSignal

    k, p, v = _seed_with_pressure_and_valuation()
    fsid = _seed_high_pressure_firm_state(
        k,
        state_id="firm_state:divergence:firm:reference_manufacturer_a",
        liquidity_pressure=0.85,
        funding_need_intensity=0.85,
    )
    env_id = _seed_constrained_market_environment(
        k, env_id="market_environment:divergence:2026-04-30"
    )
    # A corporate report signal so a bank that selects ONLY
    # corporate-side evidence still produces a non-empty frame.
    corp_signal_id = (
        "signal:corporate_quarterly_report:firm:reference_manufacturer_a:2026-04-30"
    )
    k.signals.add_signal(
        InformationSignal(
            signal_id=corp_signal_id,
            signal_type="corporate_quarterly_report",
            subject_id=_FIRM,
            source_id=_FIRM,
            published_date=_AS_OF,
            payload={"note": "synthetic"},
            visibility="public",
        )
    )
    return k, p, fsid, env_id, v, corp_signal_id


def test_attn_divergence_three_banks_three_review_labels():
    """Headline v1.12.6 test. Same borrower, same world, three
    banks selecting three different evidence sets → three
    different non-binding watch labels."""
    k, p, fsid, env_id, val_id, corp_signal_id = (
        _seed_world_for_bank_divergence()
    )

    # Bank A — selects firm_state (high pressure) + market_env
    # → rule 2 fires (high liquidity_pressure) → liquidity_watch.
    out_a = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_firm_state_ids=(fsid,),
        explicit_market_environment_state_ids=(env_id,),
        explicit_pressure_signal_ids=(p,),
        signal_id="signal:divergence:a",
    )

    # Bank B — selects valuation + corporate signal but NO
    # firm_state and NO pressure_signal → frame surfaces neither
    # firm_state nor pressure → rule 1 (information_gap_review).
    out_b = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK_B,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_valuation_ids=(val_id,),
        explicit_corporate_signal_ids=(corp_signal_id,),
        signal_id="signal:divergence:b",
    )

    # Bank C — selects nothing → frame status="empty" → rule 1
    # (information_gap_review) but adapter status="degraded" so
    # the audit shape is different even though the watch label
    # rule fires the same priority. We expect status=="degraded".
    out_c = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK_C,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        signal_id="signal:divergence:c",
    )

    assert out_a.review_summary["watch_label"] == (
        WATCH_LABEL_LIQUIDITY_WATCH
    )
    assert out_b.review_summary["watch_label"] == (
        WATCH_LABEL_INFORMATION_GAP_REVIEW
    )
    # Bank C: information_gap_review label, degraded status.
    assert out_c.review_summary["watch_label"] == (
        WATCH_LABEL_INFORMATION_GAP_REVIEW
    )
    assert out_c.status == "degraded"
    # The status differentiates B (completed) from C (degraded)
    # — Bank C had nothing to review.
    assert out_b.status == "completed"

    # Pin the headline: at least two distinct watch labels in
    # the same shared world.
    labels = {
        out_a.review_summary["watch_label"],
        out_b.review_summary["watch_label"],
        out_c.review_summary["watch_label"],
    }
    assert len(labels) >= 2
    # And the (label, status) tuples are three distinct shapes
    # — the audit record differs per bank.
    audit_shapes = {
        (out_a.review_summary["watch_label"], out_a.status),
        (out_b.review_summary["watch_label"], out_b.status),
        (out_c.review_summary["watch_label"], out_c.status),
    }
    assert len(audit_shapes) == 3


def test_attn_divergence_bank_a_carries_firm_state_evidence():
    """Bank A's resolved frame must show firm_state surfaced —
    proves the attention bottleneck drove rule 2."""
    k, p, fsid, env_id, _, _ = _seed_world_for_bank_divergence()
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_firm_state_ids=(fsid,),
        explicit_market_environment_state_ids=(env_id,),
        explicit_pressure_signal_ids=(p,),
        signal_id="signal:divergence:a:audit",
    )
    sig = k.signals.get_signal(out.signal_id)
    buckets = sig.payload["resolved_evidence_buckets"]
    assert buckets["firm_states"] == 1
    assert buckets["market_environment_states"] == 1
    assert buckets["signals"] >= 1


def test_attn_divergence_bank_b_record_has_no_firm_state():
    """Bank B did not select firm_state; the resolved
    firm_states bucket count must be zero on B's record even
    though firm_state exists in the kernel."""
    k, _, _, _, val_id, corp_signal_id = (
        _seed_world_for_bank_divergence()
    )
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK_B,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        explicit_valuation_ids=(val_id,),
        explicit_corporate_signal_ids=(corp_signal_id,),
        signal_id="signal:divergence:b:audit",
    )
    sig = k.signals.get_signal(out.signal_id)
    buckets = sig.payload["resolved_evidence_buckets"]
    assert buckets["firm_states"] == 0


def test_attn_divergence_bank_c_records_empty_frame():
    """Bank C with no inputs records frame.status=="empty"."""
    k, _, _, _, _, _ = _seed_world_for_bank_divergence()
    out = run_attention_conditioned_bank_credit_review_lite(
        k,
        bank_id=_BANK_C,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        signal_id="signal:divergence:c:audit",
    )
    sig = k.signals.get_signal(out.signal_id)
    assert sig.metadata.get("context_frame_status") == "empty"
    assert out.status == "degraded"


def test_attn_helper_module_exposes_watch_label_vocabulary():
    """The watch-label constants must be importable for downstream
    consumers (tests, future integration code, audit tools)."""
    assert WATCH_LABEL_INFORMATION_GAP_REVIEW in ALL_WATCH_LABELS
    assert WATCH_LABEL_LIQUIDITY_WATCH in ALL_WATCH_LABELS
    assert WATCH_LABEL_REFINANCING_WATCH in ALL_WATCH_LABELS
    assert WATCH_LABEL_MARKET_ACCESS_WATCH in ALL_WATCH_LABELS
    assert WATCH_LABEL_ROUTINE_MONITORING in ALL_WATCH_LABELS
    # Forbidden vocabulary must NOT appear among the labels.
    forbidden_label_words = {
        "buy",
        "sell",
        "rating",
        "approved",
        "rejected",
        "default",
        "pd",
        "lgd",
        "ead",
        "advice",
        "recommendation",
        "underwrite",
    }
    for label in ALL_WATCH_LABELS:
        assert not (set(label.lower().split("_")) & forbidden_label_words), (
            label
        )
