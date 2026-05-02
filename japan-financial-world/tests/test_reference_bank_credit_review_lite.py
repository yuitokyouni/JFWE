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
from world.reference_bank_credit_review_lite import (
    BANK_CREDIT_REVIEW_MECHANISM_VERSION,
    BANK_CREDIT_REVIEW_MODEL_FAMILY,
    BANK_CREDIT_REVIEW_MODEL_ID,
    BANK_CREDIT_REVIEW_SIGNAL_TYPE,
    BankCreditReviewLiteAdapter,
    BankCreditReviewLiteResult,
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
