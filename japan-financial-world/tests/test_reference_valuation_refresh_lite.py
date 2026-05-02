"""
Tests for v1.9.5 Reference Valuation Refresh Lite Mechanism.

Pins the v1.9.5 contract end-to-end:

- adapter satisfies the v1.9.3 / v1.9.3.1 :class:`MechanismAdapter`
  Protocol;
- :class:`MechanismSpec` is valid (model_family
  ``"valuation_mechanism"``, calibration ``"synthetic"``,
  deterministic);
- adapter does not accept a kernel argument;
- adapter runs without a kernel (reads ``request.evidence`` only);
- missing pressure evidence yields ``status="degraded"`` with a
  conservative output (baseline-only or ``None``);
- proposed valuation carries every required field including the
  method label ``"synthetic_lite_pressure_adjusted"``;
- metadata includes the four boundary flags
  (``no_price_movement`` / ``no_investment_advice`` /
  ``synthetic_only`` / ``model_id``) and the ``pressure_signal_id``
  when the pressure signal was supplied;
- adapter is deterministic across two byte-identical requests;
- request is not mutated by ``apply``;
- caller helper commits exactly one ``ValuationRecord`` through
  ``ValuationBook.add_valuation``;
- ``evidence_refs`` lineage is preserved verbatim on the
  :class:`MechanismRunRecord`;
- no mutation of prices / ownership / contracts / firm-state /
  variables / exposures / institutions / external_processes /
  relationships / routines / attention / interactions; signals
  grow only by the input pressure-signal we wrote in setup
  (the adapter does not emit a signal of its own);
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
from world.reference_firm_pressure import (
    run_reference_firm_pressure_mechanism,
)
from world.reference_valuation_refresh_lite import (
    VALUATION_REFRESH_MECHANISM_VERSION,
    VALUATION_REFRESH_METHOD_LABEL,
    VALUATION_REFRESH_MODEL_FAMILY,
    VALUATION_REFRESH_MODEL_ID,
    ValuationRefreshLiteAdapter,
    ValuationRefreshLiteResult,
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
_VALUER = "valuer:reference_analyst_desk_a"
_AS_OF = "2026-04-30"
_BASELINE = 1_000_000.0


_REFERENCE_VARIABLES: tuple[tuple[str, str], ...] = (
    ("variable:reference_oil_price", "energy_power"),
    ("variable:reference_long_rate_10y", "rates"),
    ("variable:reference_fx_pair_a", "fx"),
    ("variable:reference_steel_price", "material"),
)


_REFERENCE_EXPOSURES: tuple[tuple[str, str, str, float], ...] = (
    ("exposure:firm_a:energy", "variable:reference_oil_price", "input_cost", 0.4),
    ("exposure:firm_a:rates", "variable:reference_long_rate_10y", "funding_cost", 0.3),
    ("exposure:firm_a:fx", "variable:reference_fx_pair_a", "translation", 0.2),
    ("exposure:firm_a:steel", "variable:reference_steel_price", "input_cost", 0.5),
)


def _seed_kernel() -> WorldKernel:
    k = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )
    for vid, vgroup in _REFERENCE_VARIABLES:
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
    for exp_id, var_id, etype, mag in _REFERENCE_EXPOSURES:
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


def _all_observation_ids() -> tuple[str, ...]:
    return tuple(f"obs:{vid}:2026Q1" for vid, _ in _REFERENCE_VARIABLES)


def _all_exposure_ids() -> tuple[str, ...]:
    return tuple(eid for eid, *_ in _REFERENCE_EXPOSURES)


def _seed_with_pressure_signal() -> tuple[WorldKernel, str, float]:
    """Seed a kernel and run v1.9.4 to produce the pressure
    signal that v1.9.5 consumes."""
    k = _seed_kernel()
    pressure_result = run_reference_firm_pressure_mechanism(
        k,
        firm_id=_FIRM,
        as_of_date=_AS_OF,
        variable_observation_ids=_all_observation_ids(),
        exposure_ids=_all_exposure_ids(),
    )
    return k, pressure_result.signal_id, pressure_result.overall_pressure


def _run_default(
    k: WorldKernel, pressure_signal_id: str
) -> ValuationRefreshLiteResult:
    return run_reference_valuation_refresh_lite(
        k,
        firm_id=_FIRM,
        valuer_id=_VALUER,
        as_of_date=_AS_OF,
        pressure_signal_ids=(pressure_signal_id,),
        baseline_value=_BASELINE,
    )


# ---------------------------------------------------------------------------
# Spec / Protocol contract
# ---------------------------------------------------------------------------


def test_adapter_satisfies_mechanism_adapter_protocol():
    adapter = ValuationRefreshLiteAdapter()
    assert isinstance(adapter, MechanismAdapter)


def test_adapter_spec_has_required_fields():
    adapter = ValuationRefreshLiteAdapter()
    spec = adapter.spec
    assert isinstance(spec, MechanismSpec)
    assert spec.model_id == VALUATION_REFRESH_MODEL_ID
    assert spec.model_family == VALUATION_REFRESH_MODEL_FAMILY
    assert spec.model_family == "valuation_mechanism"
    assert spec.version == VALUATION_REFRESH_MECHANISM_VERSION
    assert spec.calibration_status == "synthetic"
    assert spec.stochasticity == "deterministic"
    assert "InformationSignal" in spec.required_inputs
    assert "ValuationRecord" in spec.output_types


def test_adapter_apply_returns_mechanism_output_bundle():
    adapter = ValuationRefreshLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
    )
    output = adapter.apply(request)
    assert isinstance(output, MechanismOutputBundle)


def test_adapter_does_not_accept_kernel_argument():
    adapter = ValuationRefreshLiteAdapter()
    with pytest.raises(TypeError):
        adapter.apply(_seed_kernel())  # type: ignore[arg-type]


def test_adapter_runs_without_a_kernel():
    """Adapter must compute proposals from request.evidence
    alone — no kernel reference."""
    adapter = ValuationRefreshLiteAdapter()
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
                    "payload": {"overall_pressure": 0.5, "status": "completed"},
                },
            ],
        },
        parameters={"baseline_value": _BASELINE, "valuer_id": _VALUER},
    )
    output = adapter.apply(request)
    assert output.status == "completed"
    assert len(output.proposed_valuation_records) == 1
    proposed = output.proposed_valuation_records[0]
    # baseline 1M × (1 − 0.30 × 0.5) = 850k
    assert abs(proposed["estimated_value"] - 850_000.0) < 1e-6
    # confidence 1 − 0.40 × 0.5 = 0.8
    assert abs(proposed["confidence"] - 0.8) < 1e-9


# ---------------------------------------------------------------------------
# Degraded path (missing pressure evidence)
# ---------------------------------------------------------------------------


def test_apply_with_no_pressure_signal_returns_degraded_with_baseline():
    adapter = ValuationRefreshLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
        parameters={"baseline_value": _BASELINE, "valuer_id": _VALUER},
    )
    output = adapter.apply(request)
    assert output.status == "degraded"
    proposed = output.proposed_valuation_records[0]
    # No pressure → no haircut → estimated_value == baseline
    assert proposed["estimated_value"] == _BASELINE
    assert proposed["confidence"] == 1.0


def test_apply_with_no_pressure_and_no_baseline_returns_degraded_none():
    adapter = ValuationRefreshLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
        parameters={"valuer_id": _VALUER},
    )
    output = adapter.apply(request)
    assert output.status == "degraded"
    proposed = output.proposed_valuation_records[0]
    assert proposed["estimated_value"] is None
    assert proposed["confidence"] == 0.0


def test_pressure_signal_for_other_actor_is_ignored():
    """The adapter only picks up pressure signals whose
    subject_id matches request.actor_id."""
    adapter = ValuationRefreshLiteAdapter()
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=adapter.spec.model_id,
        actor_id=_FIRM,
        as_of_date=_AS_OF,
        evidence={
            "InformationSignal": [
                {
                    "signal_id": "signal:firm_operating_pressure_assessment:other",
                    "signal_type": "firm_operating_pressure_assessment",
                    "subject_id": "firm:other",
                    "payload": {"overall_pressure": 0.9},
                },
            ],
        },
        parameters={"baseline_value": _BASELINE, "valuer_id": _VALUER},
    )
    output = adapter.apply(request)
    # No pressure signal matched our firm → degraded.
    assert output.status == "degraded"
    proposed = output.proposed_valuation_records[0]
    assert proposed["estimated_value"] == _BASELINE


# ---------------------------------------------------------------------------
# Pressure → valuation arithmetic
# ---------------------------------------------------------------------------


def test_zero_pressure_gives_baseline_value_unchanged():
    adapter = ValuationRefreshLiteAdapter()
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
                    "payload": {"overall_pressure": 0.0},
                },
            ],
        },
        parameters={"baseline_value": _BASELINE, "valuer_id": _VALUER},
    )
    proposed = adapter.apply(request).proposed_valuation_records[0]
    assert proposed["estimated_value"] == _BASELINE
    assert proposed["confidence"] == 1.0


def test_full_pressure_caps_haircut_and_decays_confidence():
    """At pressure=1, default haircut coefficient 0.30 trims
    baseline by 30%; confidence decays by 0.40."""
    adapter = ValuationRefreshLiteAdapter()
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
                    "payload": {"overall_pressure": 1.0},
                },
            ],
        },
        parameters={"baseline_value": _BASELINE, "valuer_id": _VALUER},
    )
    proposed = adapter.apply(request).proposed_valuation_records[0]
    assert abs(proposed["estimated_value"] - _BASELINE * 0.70) < 1e-6
    assert abs(proposed["confidence"] - 0.60) < 1e-9


def test_caller_supplied_coefficients_override_defaults():
    adapter = ValuationRefreshLiteAdapter()
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
        parameters={
            "baseline_value": _BASELINE,
            "valuer_id": _VALUER,
            "pressure_haircut_per_unit_pressure": 0.5,
            "confidence_decay_per_unit_pressure": 0.2,
        },
    )
    proposed = adapter.apply(request).proposed_valuation_records[0]
    # 0.5 * 0.5 = 0.25 haircut → 750k
    assert abs(proposed["estimated_value"] - 750_000.0) < 1e-6
    # 1 - 0.2 * 0.5 = 0.9 confidence
    assert abs(proposed["confidence"] - 0.9) < 1e-9


# ---------------------------------------------------------------------------
# Determinism + immutability
# ---------------------------------------------------------------------------


def test_apply_is_deterministic_across_two_calls():
    a = _run_default(*_seed_with_pressure_signal()[:2])
    # _seed_with_pressure_signal returns (kernel, signal_id, overall);
    # we only need (kernel, signal_id) for _run_default.
    b = _run_default(*_seed_with_pressure_signal()[:2])
    assert a.estimated_value == b.estimated_value
    assert a.confidence == b.confidence
    assert a.valuation_id == b.valuation_id


def test_apply_does_not_mutate_request():
    adapter = ValuationRefreshLiteAdapter()
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
        parameters={"baseline_value": _BASELINE, "valuer_id": _VALUER},
    )
    pre = request.to_dict()
    adapter.apply(request)
    post = request.to_dict()
    assert pre == post


# ---------------------------------------------------------------------------
# Proposed valuation shape + boundary flags
# ---------------------------------------------------------------------------


def test_proposed_valuation_has_required_fields():
    k, signal_id, _ = _seed_with_pressure_signal()
    result = _run_default(k, signal_id)
    proposed = result.output.proposed_valuation_records[0]
    for field in (
        "valuation_id",
        "subject_id",
        "valuer_id",
        "valuation_type",
        "purpose",
        "method",
        "as_of_date",
        "estimated_value",
        "currency",
        "numeraire",
        "confidence",
        "assumptions",
        "inputs",
        "related_ids",
        "metadata",
    ):
        assert field in proposed, f"missing field: {field}"


def test_proposed_valuation_method_label_is_synthetic_lite():
    k, signal_id, _ = _seed_with_pressure_signal()
    proposed = _run_default(k, signal_id).output.proposed_valuation_records[0]
    assert proposed["method"] == VALUATION_REFRESH_METHOD_LABEL
    assert proposed["method"] == "synthetic_lite_pressure_adjusted"


def test_proposed_valuation_metadata_carries_boundary_flags():
    k, signal_id, _ = _seed_with_pressure_signal()
    proposed = _run_default(k, signal_id).output.proposed_valuation_records[0]
    metadata = proposed["metadata"]
    assert metadata["no_price_movement"] is True
    assert metadata["no_investment_advice"] is True
    assert metadata["synthetic_only"] is True
    assert metadata["model_id"] == VALUATION_REFRESH_MODEL_ID
    assert metadata["pressure_signal_id"] == signal_id
    assert metadata["calibration_status"] == "synthetic"


def test_proposed_valuation_related_ids_include_pressure_signal():
    k, signal_id, _ = _seed_with_pressure_signal()
    proposed = _run_default(k, signal_id).output.proposed_valuation_records[0]
    assert signal_id in proposed["related_ids"]


# ---------------------------------------------------------------------------
# Caller helper
# ---------------------------------------------------------------------------


def test_caller_helper_commits_exactly_one_valuation_record():
    k, signal_id, _ = _seed_with_pressure_signal()
    before = len(k.valuations.all_valuations())
    result = _run_default(k, signal_id)
    after = k.valuations.all_valuations()
    assert len(after) - before == 1
    assert isinstance(result, ValuationRefreshLiteResult)
    record = k.valuations.get_valuation(result.valuation_id)
    assert record.valuation_type == "synthetic_firm_equity_estimate"
    assert record.method == VALUATION_REFRESH_METHOD_LABEL


def test_caller_helper_returns_run_record_with_lineage():
    k, signal_id, _ = _seed_with_pressure_signal()
    result = _run_default(k, signal_id)
    run = result.run_record
    assert isinstance(run, MechanismRunRecord)
    assert run.input_refs == result.request.evidence_refs
    assert run.committed_output_refs == (result.valuation_id,)
    assert run.model_id == VALUATION_REFRESH_MODEL_ID
    assert run.model_family == VALUATION_REFRESH_MODEL_FAMILY


def test_caller_helper_preserves_evidence_refs_verbatim():
    k, signal_id, _ = _seed_with_pressure_signal()
    custom = (
        signal_id,
        "exposure:firm_a:fx",
        "obs:variable:reference_oil_price:2026Q1",
    )
    result = run_reference_valuation_refresh_lite(
        k,
        firm_id=_FIRM,
        valuer_id=_VALUER,
        as_of_date=_AS_OF,
        pressure_signal_ids=(signal_id,),
        exposure_ids=("exposure:firm_a:fx",),
        variable_observation_ids=("obs:variable:reference_oil_price:2026Q1",),
        baseline_value=_BASELINE,
        evidence_refs=custom,
    )
    assert result.request.evidence_refs == custom
    assert result.run_record.input_refs == custom


def test_caller_helper_uses_kernel_clock_when_date_omitted():
    k, signal_id, _ = _seed_with_pressure_signal()
    result = run_reference_valuation_refresh_lite(
        k,
        firm_id=_FIRM,
        valuer_id=_VALUER,
        pressure_signal_ids=(signal_id,),
        baseline_value=_BASELINE,
        valuation_id="valuation:test_kernel_clock",
    )
    assert result.request.as_of_date == _AS_OF


# ---------------------------------------------------------------------------
# Defensive errors
# ---------------------------------------------------------------------------


def test_caller_helper_rejects_kernel_none():
    with pytest.raises(ValueError):
        run_reference_valuation_refresh_lite(
            None, firm_id=_FIRM, valuer_id=_VALUER, as_of_date=_AS_OF
        )


def test_caller_helper_rejects_empty_firm_id():
    k = _seed_kernel()
    with pytest.raises(ValueError):
        run_reference_valuation_refresh_lite(
            k, firm_id="", valuer_id=_VALUER, as_of_date=_AS_OF
        )


def test_caller_helper_rejects_empty_valuer_id():
    k = _seed_kernel()
    with pytest.raises(ValueError):
        run_reference_valuation_refresh_lite(
            k, firm_id=_FIRM, valuer_id="", as_of_date=_AS_OF
        )


# ---------------------------------------------------------------------------
# No-mutation guarantee
# ---------------------------------------------------------------------------


def _capture_state(k: WorldKernel) -> dict[str, Any]:
    return {
        "prices": k.prices.snapshot(),
        "ownership": k.ownership.snapshot(),
        "contracts": k.contracts.snapshot(),
        "constraints": k.constraints.snapshot(),
        "exposures": k.exposures.snapshot(),
        "variables": k.variables.snapshot(),
        "institutions": k.institutions.snapshot(),
        "external_processes": k.external_processes.snapshot(),
        "relationships": k.relationships.snapshot(),
        "routines": k.routines.snapshot(),
        "attention": k.attention.snapshot(),
        "interactions": k.interactions.snapshot(),
        "signal_count": len(k.signals.all_signals()),
    }


def test_caller_helper_does_not_mutate_other_books():
    k, signal_id, _ = _seed_with_pressure_signal()
    before = _capture_state(k)
    _run_default(k, signal_id)
    after = _capture_state(k)
    # Valuations grew by exactly 1 (the committed valuation);
    # everything else is byte-equal.
    assert before == after


def test_caller_helper_writes_only_one_valuation_record_no_other_records():
    k, signal_id, _ = _seed_with_pressure_signal()
    before_ledger = len(k.ledger.records)
    before_valuations = len(k.valuations.all_valuations())
    _run_default(k, signal_id)
    after_ledger = len(k.ledger.records)
    after_valuations = len(k.valuations.all_valuations())
    assert after_valuations - before_valuations == 1
    # Exactly one new ledger record (the valuation_added entry
    # from ValuationBook.add_valuation).
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
        VALUATION_REFRESH_MODEL_ID,
        VALUATION_REFRESH_MODEL_FAMILY,
        VALUATION_REFRESH_METHOD_LABEL,
    )
    for c in candidates:
        for token in _FORBIDDEN_TOKENS:
            assert token not in c.lower(), c


def test_committed_valuation_identifiers_are_synthetic():
    k, signal_id, _ = _seed_with_pressure_signal()
    result = _run_default(k, signal_id)
    record = k.valuations.get_valuation(result.valuation_id)
    candidates = [
        record.valuation_id,
        record.subject_id,
        record.valuer_id,
        record.valuation_type,
        record.method,
        record.purpose,
    ]
    for id_str in candidates:
        lower = id_str.lower()
        for token in _FORBIDDEN_TOKENS:
            for sep in (" ", ":", "/", "-", "_", "(", ")", ",", ".", "'", '"'):
                if f"{sep}{token}{sep}" in f" {lower} ":
                    pytest.fail(
                        f"forbidden token {token!r} appears in id {id_str!r}"
                    )
