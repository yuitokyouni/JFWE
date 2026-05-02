"""
Tests for the v1.9.3 mechanism interface contract + v1.9.3.1
hardening.

These tests pin the **shape** of the five types in
``world/mechanisms.py`` so v1.9.4+ concrete mechanisms cannot
break the contract by adding / removing required fields.

v1.9.3.1 adds three pinned properties on top of v1.9.3:

1. *Deep-ish freeze*: nested mappings inside the four immutable
   dataclasses are read-only — subscript-assign on any nested
   ``dict`` raises ``TypeError``.
2. *Rename*: ``MechanismInputBundle`` is now an alias for
   :class:`MechanismRunRequest`. The new shape introduces
   ``evidence_refs`` and ``evidence`` (the resolved input data
   the adapter reads, grouped by record type / logical key).
3. *Caller-preserved input_refs ordering*: :class:`MechanismRunRecord`
   preserves caller-supplied order verbatim — no auto-dedupe,
   no auto-sort.

If a test in this file fails, a v1.9.4 mechanism cannot be safely
landed without first updating the inventory and the contract.
"""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass

import pytest

from world.mechanisms import (
    CALIBRATION_STATUSES,
    MECHANISM_FAMILIES,
    STOCHASTICITY_LABELS,
    MechanismAdapter,
    MechanismInputBundle,
    MechanismOutputBundle,
    MechanismRunRecord,
    MechanismRunRequest,
    MechanismSpec,
    _freeze_json_like,
    _thaw_json_like,
)


# ---------------------------------------------------------------------------
# Required-field contract
# ---------------------------------------------------------------------------


_REQUIRED_SPEC_FIELDS: frozenset[str] = frozenset(
    {
        "model_id",
        "model_family",
        "version",
        "assumptions",
        "calibration_status",
        "stochasticity",
        "required_inputs",
        "output_types",
        "metadata",
    }
)


_REQUIRED_REQUEST_FIELDS: frozenset[str] = frozenset(
    {
        "request_id",
        "model_id",
        "actor_id",
        "as_of_date",
        "selected_observation_set_ids",
        "evidence_refs",
        "evidence",
        "state_views",
        "parameters",
        "metadata",
    }
)


_REQUIRED_OUTPUT_FIELDS: frozenset[str] = frozenset(
    {
        "request_id",
        "model_id",
        "status",
        "proposed_signals",
        "proposed_valuation_records",
        "proposed_constraint_pressure_deltas",
        "proposed_intent_records",
        "proposed_run_records",
        "output_summary",
        "warnings",
        "metadata",
    }
)


_REQUIRED_RUN_RECORD_FIELDS: frozenset[str] = frozenset(
    {
        "run_id",
        "request_id",
        "model_id",
        "model_family",
        "version",
        "actor_id",
        "as_of_date",
        "status",
        "input_refs",
        "committed_output_refs",
        "parent_record_ids",
        "input_summary_hash",
        "output_summary_hash",
        "metadata",
    }
)


def test_every_required_dataclass_is_a_dataclass():
    assert is_dataclass(MechanismSpec)
    assert is_dataclass(MechanismRunRequest)
    assert is_dataclass(MechanismOutputBundle)
    assert is_dataclass(MechanismRunRecord)


def test_mechanism_spec_required_fields():
    actual = {f.name for f in fields(MechanismSpec)}
    missing = _REQUIRED_SPEC_FIELDS - actual
    assert missing == set()


def test_mechanism_run_request_required_fields():
    actual = {f.name for f in fields(MechanismRunRequest)}
    missing = _REQUIRED_REQUEST_FIELDS - actual
    assert missing == set()


def test_mechanism_input_bundle_alias_points_to_run_request():
    """v1.9.3.1 keeps the old name as a one-line alias for one
    milestone. Both names must refer to the same class."""
    assert MechanismInputBundle is MechanismRunRequest


def test_mechanism_output_bundle_required_fields():
    actual = {f.name for f in fields(MechanismOutputBundle)}
    missing = _REQUIRED_OUTPUT_FIELDS - actual
    assert missing == set()


def test_mechanism_run_record_required_fields():
    actual = {f.name for f in fields(MechanismRunRecord)}
    missing = _REQUIRED_RUN_RECORD_FIELDS - actual
    assert missing == set()


# ---------------------------------------------------------------------------
# Top-level immutability (frozen dataclass)
# ---------------------------------------------------------------------------


def _spec() -> MechanismSpec:
    return MechanismSpec(
        model_id="mechanism:firm_financial_mechanism:reference_v0",
        model_family="firm_financial_mechanism",
        version="0.1",
    )


def _request() -> MechanismRunRequest:
    return MechanismRunRequest(
        request_id="req:1",
        model_id=_spec().model_id,
        actor_id="firm:reference_a",
        as_of_date="2026-04-30",
    )


def test_spec_is_frozen():
    spec = _spec()
    with pytest.raises(Exception):
        spec.model_id = "tampered"  # type: ignore[misc]


def test_run_request_is_frozen():
    req = _request()
    with pytest.raises(Exception):
        req.request_id = "tampered"  # type: ignore[misc]


def test_output_bundle_is_frozen():
    output = MechanismOutputBundle(request_id="req:1", model_id=_spec().model_id)
    with pytest.raises(Exception):
        output.request_id = "tampered"  # type: ignore[misc]


def test_run_record_is_frozen():
    run = MechanismRunRecord(
        run_id="mechanism_run:req:1",
        request_id="req:1",
        model_id=_spec().model_id,
        model_family="firm_financial_mechanism",
        version="0.1",
        actor_id="firm:reference_a",
        as_of_date="2026-04-30",
    )
    with pytest.raises(Exception):
        run.run_id = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# v1.9.3.1 deep-freeze property — nested mutation rejected
# ---------------------------------------------------------------------------


def test_spec_metadata_nested_mutation_rejected():
    spec = MechanismSpec(
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
        metadata={"nested": {"k": "v"}},
    )
    with pytest.raises(TypeError):
        spec.metadata["nested"]["k"] = "mutated"


def test_spec_metadata_top_level_mutation_rejected():
    spec = MechanismSpec(
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
        metadata={"k": "v"},
    )
    with pytest.raises(TypeError):
        spec.metadata["k"] = "mutated"


def test_request_evidence_nested_mutation_rejected():
    req = MechanismRunRequest(
        request_id="req:1",
        model_id="m:1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        evidence={
            "InformationSignal": [
                {"signal_id": "s:1", "payload": {"k": "v"}},
            ],
        },
    )
    with pytest.raises(TypeError):
        # nested mapping inside evidence -> mappingproxy.
        req.evidence["InformationSignal"][0]["payload"]["k"] = "mutated"


def test_request_evidence_top_level_mutation_rejected():
    req = MechanismRunRequest(
        request_id="req:1",
        model_id="m:1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        evidence={"InformationSignal": []},
    )
    with pytest.raises(TypeError):
        req.evidence["InformationSignal"] = [{"signal_id": "tampered"}]


def test_request_evidence_lists_become_tuples():
    """Lists inside evidence are converted to tuples so the per-
    record-type sequence is also immutable."""
    req = MechanismRunRequest(
        request_id="req:1",
        model_id="m:1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        evidence={"InformationSignal": [{"signal_id": "s:1"}]},
    )
    assert isinstance(req.evidence["InformationSignal"], tuple)


def test_request_state_views_nested_mutation_rejected():
    req = MechanismRunRequest(
        request_id="req:1",
        model_id="m:1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        state_views={"balance_sheet": {"cash": 100.0}},
    )
    with pytest.raises(TypeError):
        req.state_views["balance_sheet"]["cash"] = 0.0


def test_request_parameters_nested_mutation_rejected():
    req = MechanismRunRequest(
        request_id="req:1",
        model_id="m:1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        parameters={"sensitivity": {"fx": 0.4}},
    )
    with pytest.raises(TypeError):
        req.parameters["sensitivity"]["fx"] = 0.0


def test_output_proposed_signals_nested_mutation_rejected():
    output = MechanismOutputBundle(
        request_id="req:1",
        model_id="m:1",
        proposed_signals=({"signal_id": "s:1", "metadata": {"k": "v"}},),
    )
    with pytest.raises(TypeError):
        output.proposed_signals[0]["metadata"]["k"] = "mutated"


def test_output_summary_nested_mutation_rejected():
    output = MechanismOutputBundle(
        request_id="req:1",
        model_id="m:1",
        output_summary={"counts": {"signals": 1}},
    )
    with pytest.raises(TypeError):
        output.output_summary["counts"]["signals"] = 99


def test_run_record_metadata_nested_mutation_rejected():
    rec = MechanismRunRecord(
        run_id="mr:1",
        request_id="req:1",
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        metadata={"audit": {"checked_by": "human"}},
    )
    with pytest.raises(TypeError):
        rec.metadata["audit"]["checked_by"] = "mutated"


# ---------------------------------------------------------------------------
# to_dict returns mutable copies
# ---------------------------------------------------------------------------


def test_spec_to_dict_returns_mutable_copy():
    spec = MechanismSpec(
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
        metadata={"nested": {"k": "v"}},
    )
    d = spec.to_dict()
    assert isinstance(d["metadata"], dict)
    assert isinstance(d["metadata"]["nested"], dict)
    # Mutation on the thawed copy succeeds — proving it is a real
    # dict, not a MappingProxyType.
    d["metadata"]["nested"]["k"] = "now-mutable"
    assert d["metadata"]["nested"]["k"] == "now-mutable"


def test_request_to_dict_returns_mutable_copies_throughout():
    req = MechanismRunRequest(
        request_id="req:1",
        model_id="m:1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        evidence={"InformationSignal": [{"signal_id": "s:1", "payload": {"k": "v"}}]},
        state_views={"balance_sheet": {"cash": 100.0}},
        parameters={"sensitivity": {"fx": 0.4}},
        metadata={"k": {"nested": "v"}},
    )
    d = req.to_dict()
    # Nested dicts inside the thawed projection are real dicts.
    assert isinstance(d["evidence"], dict)
    assert isinstance(d["evidence"]["InformationSignal"], list)
    assert isinstance(d["evidence"]["InformationSignal"][0], dict)
    assert isinstance(d["state_views"]["balance_sheet"], dict)
    assert isinstance(d["parameters"]["sensitivity"], dict)
    assert isinstance(d["metadata"]["k"], dict)
    # And mutation succeeds on every nested layer.
    d["evidence"]["InformationSignal"][0]["payload"]["k"] = "now-mutable"
    d["state_views"]["balance_sheet"]["cash"] = 0.0
    d["parameters"]["sensitivity"]["fx"] = 0.0
    d["metadata"]["k"]["nested"] = "mutated"


def test_output_to_dict_returns_mutable_copies():
    output = MechanismOutputBundle(
        request_id="req:1",
        model_id="m:1",
        proposed_signals=({"signal_id": "s:1", "metadata": {"k": "v"}},),
        output_summary={"counts": {"signals": 1}},
        metadata={"k": {"nested": "v"}},
    )
    d = output.to_dict()
    assert isinstance(d["proposed_signals"], list)
    assert isinstance(d["proposed_signals"][0], dict)
    assert isinstance(d["proposed_signals"][0]["metadata"], dict)
    d["proposed_signals"][0]["metadata"]["k"] = "now-mutable"
    d["output_summary"]["counts"]["signals"] = 99
    d["metadata"]["k"]["nested"] = "mutated"


def test_run_record_to_dict_returns_mutable_copy():
    rec = MechanismRunRecord(
        run_id="mr:1",
        request_id="req:1",
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        metadata={"audit": {"checked_by": "human"}},
    )
    d = rec.to_dict()
    assert isinstance(d["metadata"]["audit"], dict)
    d["metadata"]["audit"]["checked_by"] = "mutated"


# ---------------------------------------------------------------------------
# JSON round-trip (the thawed projection is JSON-friendly)
# ---------------------------------------------------------------------------


def test_spec_to_dict_round_trips_through_json():
    spec = MechanismSpec(
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
        assumptions=("a",),
        required_inputs=("VariableObservation",),
        output_types=("InformationSignal",),
        metadata={"k": "v", "nested": {"x": 1}},
    )
    encoded = json.dumps(spec.to_dict(), sort_keys=True, ensure_ascii=False)
    decoded = json.loads(encoded)
    assert decoded["assumptions"] == ["a"]
    assert decoded["metadata"]["nested"] == {"x": 1}


def test_request_to_dict_round_trips_through_json():
    req = MechanismRunRequest(
        request_id="req:1",
        model_id="m:1",
        actor_id="firm:reference_a",
        as_of_date="2026-04-30",
        selected_observation_set_ids=("sel:1",),
        evidence_refs=("s:1", "s:2"),
        evidence={"InformationSignal": [{"signal_id": "s:1"}]},
        state_views={"balance_sheet": {"cash": 100.0}},
        parameters={"sensitivity": 0.5},
    )
    encoded = json.dumps(req.to_dict(), sort_keys=True, ensure_ascii=False)
    decoded = json.loads(encoded)
    assert decoded["evidence_refs"] == ["s:1", "s:2"]
    assert decoded["evidence"] == {"InformationSignal": [{"signal_id": "s:1"}]}
    assert decoded["state_views"] == {"balance_sheet": {"cash": 100.0}}


def test_output_total_proposed_count_sums_correctly():
    output = MechanismOutputBundle(
        request_id="req:1",
        model_id="m:1",
        proposed_signals=({"id": "s:1"}, {"id": "s:2"}),
        proposed_valuation_records=({"id": "v:1"},),
    )
    assert output.total_proposed_count == 3


# ---------------------------------------------------------------------------
# Validation: empty / wrong-type inputs are rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"model_id": ""},
        {"model_family": ""},
        {"version": ""},
        {"calibration_status": ""},
        {"stochasticity": ""},
    ],
)
def test_spec_rejects_empty_required_strings(kwargs):
    base = {
        "model_id": "mechanism:x:y",
        "model_family": "firm_financial_mechanism",
        "version": "0.1",
    }
    base.update(kwargs)
    with pytest.raises(ValueError):
        MechanismSpec(**base)


@pytest.mark.parametrize(
    "tuple_field",
    ["assumptions", "required_inputs", "output_types"],
)
def test_spec_rejects_empty_strings_in_tuple_fields(tuple_field):
    with pytest.raises(ValueError):
        MechanismSpec(
            model_id="mechanism:x:y",
            model_family="firm_financial_mechanism",
            version="0.1",
            **{tuple_field: ("ok", "")},
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"request_id": ""},
        {"model_id": ""},
        {"actor_id": ""},
        {"as_of_date": ""},
    ],
)
def test_run_request_rejects_empty_required_strings(kwargs):
    base = {
        "request_id": "req:1",
        "model_id": "mechanism:x:y",
        "actor_id": "firm:reference_a",
        "as_of_date": "2026-04-30",
    }
    base.update(kwargs)
    with pytest.raises(ValueError):
        MechanismRunRequest(**base)


def test_run_request_evidence_must_be_mapping():
    with pytest.raises(ValueError):
        MechanismRunRequest(
            request_id="req:1",
            model_id="m:1",
            actor_id="firm:a",
            as_of_date="2026-04-30",
            evidence=["not", "a", "mapping"],  # type: ignore[arg-type]
        )


def test_run_request_evidence_keys_must_be_non_empty_strings():
    with pytest.raises(ValueError):
        MechanismRunRequest(
            request_id="req:1",
            model_id="m:1",
            actor_id="firm:a",
            as_of_date="2026-04-30",
            evidence={"": []},
        )


def test_output_bundle_rejects_non_mapping_proposals():
    with pytest.raises(ValueError):
        MechanismOutputBundle(
            request_id="req:1",
            model_id="mechanism:x:y",
            proposed_signals=("not-a-mapping",),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"run_id": ""},
        {"request_id": ""},
        {"model_id": ""},
        {"model_family": ""},
        {"version": ""},
        {"actor_id": ""},
        {"as_of_date": ""},
        {"status": ""},
    ],
)
def test_run_record_rejects_empty_required_strings(kwargs):
    base = {
        "run_id": "mechanism_run:req:1",
        "request_id": "req:1",
        "model_id": "mechanism:x:y",
        "model_family": "firm_financial_mechanism",
        "version": "0.1",
        "actor_id": "firm:reference_a",
        "as_of_date": "2026-04-30",
    }
    base.update(kwargs)
    with pytest.raises(ValueError):
        MechanismRunRecord(**base)


# ---------------------------------------------------------------------------
# Evidence accepts grouped resolved records
# ---------------------------------------------------------------------------


def test_run_request_evidence_accepts_grouped_records():
    """Evidence is a mapping from record-type key to a list of
    resolved record dicts. v1.9.4 mechanisms will read e.g.
    ``request.evidence["VariableObservation"]`` for the
    pre-resolved observation list."""
    req = MechanismRunRequest(
        request_id="req:1",
        model_id="m:1",
        actor_id="firm:reference_a",
        as_of_date="2026-04-30",
        evidence={
            "InformationSignal": [
                {"signal_id": "s:1", "signal_type": "corporate_quarterly_report"},
            ],
            "VariableObservation": [
                {"observation_id": "o:1", "value": 1.0},
                {"observation_id": "o:2", "value": 2.0},
            ],
            "ExposureRecord": [
                {"exposure_id": "e:1", "magnitude": 0.4},
            ],
        },
        evidence_refs=("s:1", "o:1", "o:2", "e:1"),
    )
    assert "InformationSignal" in req.evidence
    assert "VariableObservation" in req.evidence
    assert "ExposureRecord" in req.evidence
    assert req.evidence_refs == ("s:1", "o:1", "o:2", "e:1")


# ---------------------------------------------------------------------------
# v1.9.3.1 input_refs ordering is the caller's responsibility
# ---------------------------------------------------------------------------


def test_run_record_input_refs_preserved_verbatim_with_duplicates():
    """v1.9.3.1: MechanismRunRecord must NOT auto-dedupe or sort
    input_refs. Caller-supplied order is preserved verbatim,
    including duplicates."""
    rec = MechanismRunRecord(
        run_id="mr:1",
        request_id="req:1",
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        input_refs=("s:2", "s:1", "s:2", "s:3"),  # not sorted, duplicates
    )
    assert rec.input_refs == ("s:2", "s:1", "s:2", "s:3")


def test_run_record_committed_output_refs_preserved_verbatim():
    rec = MechanismRunRecord(
        run_id="mr:1",
        request_id="req:1",
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
        committed_output_refs=("s:b", "s:a"),
    )
    assert rec.committed_output_refs == ("s:b", "s:a")


# ---------------------------------------------------------------------------
# Protocol structural check (v1.9.3.1 signature uses MechanismRunRequest)
# ---------------------------------------------------------------------------


def test_minimal_adapter_with_run_request_signature_satisfies_protocol():
    spec = _spec()

    class _Stub:
        def __init__(self, s: MechanismSpec) -> None:
            self.spec = s

        def apply(self, request: MechanismRunRequest) -> MechanismOutputBundle:
            return MechanismOutputBundle(
                request_id=request.request_id,
                model_id=request.model_id,
            )

    stub = _Stub(spec)
    assert isinstance(stub, MechanismAdapter)


def test_class_without_apply_does_not_satisfy_protocol():
    class _MissingApply:
        spec = _spec()

    assert not isinstance(_MissingApply(), MechanismAdapter)


def test_adapter_does_not_require_kernel_to_apply():
    """The contract: an adapter must not read the kernel or any
    book. We prove the input-side invariant by passing the
    adapter a request constructed without any kernel reference,
    and checking the adapter returns a bundle from `request.evidence`
    alone."""
    spec = _spec()

    class _CountingAdapter:
        def __init__(self, s: MechanismSpec) -> None:
            self.spec = s

        def apply(self, request: MechanismRunRequest) -> MechanismOutputBundle:
            count = sum(
                len(v) if isinstance(v, tuple) else 1
                for v in request.evidence.values()
            )
            return MechanismOutputBundle(
                request_id=request.request_id,
                model_id=request.model_id,
                output_summary={"evidence_record_count": count},
            )

    adapter = _CountingAdapter(spec)
    request = MechanismRunRequest(
        request_id="req:1",
        model_id=spec.model_id,
        actor_id="firm:reference_a",
        as_of_date="2026-04-30",
        evidence={
            "VariableObservation": [{"observation_id": "o:1"}, {"observation_id": "o:2"}],
        },
    )
    output = adapter.apply(request)
    assert output.request_id == "req:1"
    assert output.output_summary["evidence_record_count"] == 2


# ---------------------------------------------------------------------------
# Vocabulary constants
# ---------------------------------------------------------------------------


def test_mechanism_families_includes_recommended_set():
    expected = {
        "firm_financial_mechanism",
        "valuation_mechanism",
        "credit_review_mechanism",
        "investor_intent_mechanism",
        "market_mechanism",
    }
    assert expected.issubset(set(MECHANISM_FAMILIES))


def test_calibration_statuses_covers_three_canonical_levels():
    assert set(CALIBRATION_STATUSES) == {
        "synthetic",
        "public_data_calibrated",
        "proprietary_calibrated",
    }


def test_stochasticity_labels_covers_three_canonical_levels():
    assert set(STOCHASTICITY_LABELS) == {
        "deterministic",
        "pinned_seed",
        "open_seed",
    }


# ---------------------------------------------------------------------------
# v1.9.3.1 freeze helpers — direct unit tests
# ---------------------------------------------------------------------------


def test_freeze_helper_converts_mapping_to_proxy():
    frozen = _freeze_json_like({"a": 1, "nested": {"b": 2}})
    with pytest.raises(TypeError):
        frozen["a"] = 99  # type: ignore[index]
    with pytest.raises(TypeError):
        frozen["nested"]["b"] = 99  # type: ignore[index]


def test_freeze_helper_converts_list_to_tuple():
    frozen = _freeze_json_like([1, 2, 3])
    assert frozen == (1, 2, 3)
    assert isinstance(frozen, tuple)


def test_freeze_helper_converts_set_to_sorted_tuple():
    frozen = _freeze_json_like({3, 1, 2})
    assert frozen == (1, 2, 3)


def test_freeze_helper_passes_scalars_through():
    for v in (None, True, 1, 1.5, "string"):
        assert _freeze_json_like(v) == v


def test_thaw_helper_round_trips():
    original = {"a": 1, "nested": {"b": [1, 2, 3]}}
    thawed = _thaw_json_like(_freeze_json_like(original))
    assert thawed == {"a": 1, "nested": {"b": [1, 2, 3]}}
    # And the result is a normal dict the caller can mutate.
    thawed["nested"]["b"].append(4)


# ---------------------------------------------------------------------------
# Anti-behavior: instantiating these types does not touch a kernel
# ---------------------------------------------------------------------------


def test_constructing_interface_records_does_not_require_a_kernel():
    """v1.9.3 anti-behavior invariant carried forward: every
    interface dataclass is pure data and constructs without
    needing any v0/v1 book or kernel."""
    _ = MechanismSpec(
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
    )
    _ = MechanismRunRequest(
        request_id="req:1",
        model_id="m:1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
    )
    _ = MechanismOutputBundle(request_id="req:1", model_id="m:1")
    _ = MechanismRunRecord(
        run_id="mr:1",
        request_id="req:1",
        model_id="m:1",
        model_family="firm_financial_mechanism",
        version="0.1",
        actor_id="firm:a",
        as_of_date="2026-04-30",
    )
