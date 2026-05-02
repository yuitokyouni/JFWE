"""
v1.9.7 Reference Bank Credit Review Lite Mechanism.

This module ships the project's **third concrete mechanism** on the
v1.9.3 / v1.9.3.1 hardened interface. It consumes resolved
evidence — firm pressure assessment signals, opinionated valuation
claims, the bank's own selected observation set, corporate
reporting signals, and exposure records — and proposes one
synthetic ``bank_credit_review_note`` signal that is committed
through the existing ``SignalBook.add_signal`` ledger path.

Hard boundary
-------------

This is **not a lending decision model.** It is a synthetic
reference mechanism showing how a bank could review credit-relevant
evidence without changing contracts, rates, covenants, or lending
status. The mechanism explicitly does **not**:

- approve / reject any loan;
- enforce or trip any covenant;
- mutate ``ContractBook``, ``ConstraintBook``, or any other
  source-of-truth book beyond a single ``SignalBook.add_signal``;
- change interest rates or any other contract field;
- detect or declare default;
- form, observe, or move any market price;
- imply that any score is a *probability of default*, an
  *internal rating*, or any other regulator-recognised credit
  measure;
- imply investment advice;
- ingest real data, calibrate to any real economy, or run a
  scenario engine.

The produced signal is a **diagnostic note**, not a decision. The
hard-boundary statement is embedded verbatim in the signal's
metadata so any downstream reader can immediately see what the
note isn't.

Conceptual distinction
----------------------

- **Bank credit review note** (this mechanism) — a synthetic
  diagnostic signal a bank issues *about its own attention to
  credit-relevant evidence on a firm*. It is a record of *what
  the bank looked at* and *how that evidence aggregated as a
  pressure score*; it is not a record of *what the bank decided
  to do*.
- **Lending decision** (NOT in v1.9.7) — credit approval,
  covenant enforcement, rate changes, default declaration. Those
  belong to a separate ``credit_decision_mechanism`` family that
  v1.9.7 deliberately does not ship.
- **Pressure assessment** (v1.9.4) and **valuation refresh lite**
  (v1.9.5) — produce *firm-level* diagnostics. v1.9.7 consumes
  them but does *not* re-derive them.

Mechanism interface contract
----------------------------

The adapter implements the v1.9.3 / v1.9.3.1
:class:`MechanismAdapter` Protocol:

- ``apply(request: MechanismRunRequest) -> MechanismOutputBundle``
  reads ``request.evidence`` + ``request.parameters`` only;
- the adapter does **not** accept a kernel parameter;
- the adapter does **not** read any book or the ledger;
- the adapter does **not** mutate ``request``;
- the adapter does **not** commit any proposal — that is the
  caller's job in :func:`run_reference_bank_credit_review_lite`.

Credit review dimensions
------------------------

Five synthetic dimensions, each a deterministic float in
``[0, 1]``:

- ``operating_pressure_score`` — the firm's overall operating /
  financing pressure (consumed verbatim from the v1.9.4 firm
  pressure assessment signal's ``payload.overall_pressure``).
- ``valuation_pressure_score`` — ``1 - mean(valuation.confidence)``
  across all supplied valuations on the firm. High-confidence
  valuations imply low pressure; low-confidence valuations
  imply more pressure (the bank should look harder).
- ``debt_service_attention_score`` — the firm's
  ``debt_service_pressure`` dimension from the pressure signal.
- ``collateral_attention_score`` — the firm's
  ``fx_translation_pressure`` (a synthetic stand-in; in a real
  model this would consume the bank's own collateral exposures
  and the relevant variable observations, but v1.9.7 keeps the
  formula simple and synthetic).
- ``information_quality_score`` — a synthetic completeness score
  in ``[0, 1]`` that measures how much of the expected evidence
  the caller actually supplied. Maxes at 1.0 when pressure +
  valuation + corporate-reporting + selection evidence is all
  present.

Plus one summary:

- ``overall_credit_review_pressure`` — deterministic mean of the
  four pressure-side scores (operating + valuation +
  debt_service + collateral). Note that ``information_quality_score``
  is a *coverage* metric, not a *pressure* metric, so it does not
  enter the mean.

Calibration status: ``"synthetic"``. Algorithm is a small
weighted recombination of upstream pressure / confidence values.
**This is not a probability of default**, **not an internal
rating**, **not a lending decision**.

Caller responsibilities
-----------------------

The caller:

1. resolves ``pressure_signal_ids`` from ``SignalBook`` (the
   v1.9.4 firm pressure assessment signals);
2. resolves ``valuation_ids`` from ``ValuationBook`` (the v1.9.5
   valuation refresh lite records);
3. optionally resolves ``selected_observation_set_ids`` from
   ``AttentionBook`` (the bank's own per-period selection);
4. optionally resolves ``corporate_signal_ids`` from
   ``SignalBook`` and ``exposure_ids`` from ``ExposureBook``;
5. builds a :class:`MechanismRunRequest` with deterministic
   ``evidence_refs`` ordering;
6. calls ``adapter.apply(request)``;
7. commits the one proposed signal through
   ``kernel.signals.add_signal``;
8. constructs a :class:`MechanismRunRecord` for audit and returns
   it on the result.

v1.9.7 deliberately does not introduce a new kernel-level
mechanism book; the run record is returned as audit data on the
result, mirroring the v1.9.4 / v1.9.5 pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

from world.mechanisms import (
    MechanismOutputBundle,
    MechanismRunRecord,
    MechanismRunRequest,
    MechanismSpec,
)
from world.signals import InformationSignal


# ---------------------------------------------------------------------------
# Controlled vocabulary
# ---------------------------------------------------------------------------


BANK_CREDIT_REVIEW_MODEL_ID: str = (
    "mechanism:credit_review_mechanism:reference_bank_credit_review_lite_v0"
)
BANK_CREDIT_REVIEW_MODEL_FAMILY: str = "credit_review_mechanism"
BANK_CREDIT_REVIEW_MECHANISM_VERSION: str = "0.1"
BANK_CREDIT_REVIEW_SIGNAL_TYPE: str = "bank_credit_review_note"

# Upstream signal type constants. Kept as strings here so the
# import graph stays one-way: v1.9.7 consumes v1.9.4's *output*,
# not its module surface.
_FIRM_PRESSURE_SIGNAL_TYPE: str = "firm_operating_pressure_assessment"


# ---------------------------------------------------------------------------
# Spec singleton
# ---------------------------------------------------------------------------


_DEFAULT_SPEC: MechanismSpec = MechanismSpec(
    model_id=BANK_CREDIT_REVIEW_MODEL_ID,
    model_family=BANK_CREDIT_REVIEW_MODEL_FAMILY,
    version=BANK_CREDIT_REVIEW_MECHANISM_VERSION,
    assumptions=(
        "operating_pressure_score_consumed_verbatim_from_v194",
        "valuation_pressure_score_is_one_minus_mean_confidence",
        "collateral_attention_uses_fx_translation_proxy",
        "information_quality_is_evidence_coverage_count",
        "overall_pressure_is_mean_of_four_pressure_scores",
        "no_lending_decision",
        "no_covenant_enforcement",
        "no_contract_mutation",
        "no_constraint_mutation",
        "no_default_declaration",
        "no_real_data",
        "no_calibration",
        "diagnostic_note_only",
    ),
    calibration_status="synthetic",
    stochasticity="deterministic",
    required_inputs=(
        "InformationSignal",
        "ValuationRecord",
        "SelectedObservationSet",
        "ExposureRecord",
        "VariableObservation",
    ),
    output_types=("InformationSignal",),
    metadata={
        "method": "synthetic_lite_credit_review",
        "boundary": (
            "credit_review_note_only; no_lending_decision; "
            "no_covenant_enforcement; no_contract_mutation; "
            "no_constraint_mutation; no_default_declaration"
        ),
    },
)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BankCreditReviewLiteAdapter:
    """
    The v1.9.7 adapter. Pure function over
    :class:`MechanismRunRequest`; produces one
    :class:`MechanismOutputBundle` carrying a single proposed
    bank-credit-review-note signal.

    The adapter is **immutable** (frozen dataclass) and **does
    not** carry kernel state. Two adapters with the same spec
    produce byte-identical outputs on byte-identical requests.
    """

    spec: MechanismSpec = _DEFAULT_SPEC

    def apply(
        self, request: MechanismRunRequest
    ) -> MechanismOutputBundle:
        if not isinstance(request, MechanismRunRequest):
            raise TypeError(
                "request must be a MechanismRunRequest; "
                f"got {type(request).__name__}"
            )

        signals = list(_iter_records(request.evidence, "InformationSignal"))
        valuations = list(_iter_records(request.evidence, "ValuationRecord"))
        observations = list(_iter_records(request.evidence, "VariableObservation"))
        exposures = list(_iter_records(request.evidence, "ExposureRecord"))
        selections = list(
            _iter_records(request.evidence, "SelectedObservationSet")
        )

        params = request.parameters
        bank_id = (
            params.get("bank_id")
            if isinstance(params.get("bank_id"), str) and params.get("bank_id")
            else f"bank:{request.actor_id}"
        )

        # The actor_id of the request is the firm being reviewed
        # (the *subject* of the credit review). The bank_id is
        # carried in parameters so we can route it onto the signal
        # without requiring it on the request schema.

        firm_id = request.actor_id

        # --- operating pressure score: the firm's pressure signal -------
        pressure_signal = _find_pressure_signal_for_firm(signals, firm_id)
        if pressure_signal is not None:
            operating_pressure_score = _safe_float(
                pressure_signal.get("payload", {}).get("overall_pressure"),
                default=0.0,
            )
            debt_service_attention_score = _safe_float(
                pressure_signal.get("payload", {}).get("debt_service_pressure"),
                default=0.0,
            )
            collateral_attention_score = _safe_float(
                pressure_signal.get("payload", {}).get("fx_translation_pressure"),
                default=0.0,
            )
        else:
            operating_pressure_score = 0.0
            debt_service_attention_score = 0.0
            collateral_attention_score = 0.0

        # --- valuation pressure: 1 - mean(confidence) across this firm -
        firm_valuations = [
            v for v in valuations if v.get("subject_id") == firm_id
        ]
        if firm_valuations:
            confidences = [
                _safe_float(v.get("confidence"), default=1.0)
                for v in firm_valuations
            ]
            valuation_pressure_score = max(
                0.0, min(1.0, 1.0 - (sum(confidences) / len(confidences)))
            )
        else:
            valuation_pressure_score = 0.0

        # --- information quality score: evidence-coverage metric -------
        # Four expected channels: pressure / valuation / corporate
        # report / selection. Each present channel contributes 0.25.
        coverage = 0.0
        if pressure_signal is not None:
            coverage += 0.25
        if firm_valuations:
            coverage += 0.25
        if any(
            s.get("signal_type") == "corporate_quarterly_report"
            and s.get("subject_id") == firm_id
            for s in signals
        ):
            coverage += 0.25
        if selections:
            coverage += 0.25
        information_quality_score = coverage

        # --- overall: mean of the four pressure scores ----------------
        overall_credit_review_pressure = (
            operating_pressure_score
            + valuation_pressure_score
            + debt_service_attention_score
            + collateral_attention_score
        ) / 4.0

        # --- status: degraded when neither pressure nor valuation
        # evidence was supplied (the v1.8.1 anti-scenario rule). A
        # bank with only corporate-reporting evidence still yields
        # a recordable note, but it'll be all-zeros and the
        # information-quality score reports the gap.
        status = (
            "completed"
            if (pressure_signal is not None or firm_valuations)
            else "degraded"
        )

        # --- audit lineage --------------------------------------------
        related_ids: list[str] = []
        if pressure_signal is not None:
            sid = pressure_signal.get("signal_id")
            if isinstance(sid, str) and sid:
                related_ids.append(sid)
        for v in firm_valuations:
            vid = v.get("valuation_id")
            if isinstance(vid, str) and vid and vid not in related_ids:
                related_ids.append(vid)
        for s in signals:
            sid = s.get("signal_id")
            if (
                isinstance(sid, str)
                and sid
                and sid not in related_ids
                and s.get("signal_type") != _FIRM_PRESSURE_SIGNAL_TYPE
            ):
                related_ids.append(sid)
        for sel in selections:
            sel_id = sel.get("selection_id")
            if isinstance(sel_id, str) and sel_id and sel_id not in related_ids:
                related_ids.append(sel_id)

        evidence_counts = {
            "information_signals": len(signals),
            "valuation_records": len(firm_valuations),
            "variable_observations": len(observations),
            "exposure_records": len(exposures),
            "selected_observation_sets": len(selections),
        }

        signal_id = _default_signal_id(bank_id, firm_id, request.as_of_date)

        proposed_signal: dict[str, Any] = {
            "signal_id": signal_id,
            "signal_type": BANK_CREDIT_REVIEW_SIGNAL_TYPE,
            "subject_id": firm_id,
            "source_id": bank_id,
            "published_date": request.as_of_date,
            "effective_date": request.as_of_date,
            "visibility": "public",
            "confidence": 1.0,
            "payload": {
                "bank_id": bank_id,
                "firm_id": firm_id,
                "as_of_date": request.as_of_date,
                "operating_pressure_score": operating_pressure_score,
                "valuation_pressure_score": valuation_pressure_score,
                "debt_service_attention_score": debt_service_attention_score,
                "collateral_attention_score": collateral_attention_score,
                "information_quality_score": information_quality_score,
                "overall_credit_review_pressure": (
                    overall_credit_review_pressure
                ),
                "evidence_counts": evidence_counts,
                "calibration_status": "synthetic",
                "status": status,
                "pressure_signal_id": (
                    pressure_signal.get("signal_id")
                    if pressure_signal is not None
                    else None
                ),
            },
            "related_ids": related_ids,
            "metadata": {
                "model_id": self.spec.model_id,
                "model_family": self.spec.model_family,
                "version": self.spec.version,
                "calibration_status": self.spec.calibration_status,
                "method": "synthetic_lite_credit_review",
                "no_lending_decision": True,
                "no_covenant_enforcement": True,
                "no_contract_mutation": True,
                "no_constraint_mutation": True,
                "no_default_declaration": True,
                "synthetic_only": True,
                "no_internal_rating": True,
                "no_probability_of_default": True,
                "boundary": (
                    "credit_review_note_only; no_lending_decision; "
                    "no_covenant_enforcement; no_contract_mutation; "
                    "no_constraint_mutation; no_default_declaration"
                ),
            },
        }

        return MechanismOutputBundle(
            request_id=request.request_id,
            model_id=self.spec.model_id,
            status=status,
            proposed_signals=(proposed_signal,),
            output_summary={
                "operating_pressure_score": operating_pressure_score,
                "valuation_pressure_score": valuation_pressure_score,
                "debt_service_attention_score": debt_service_attention_score,
                "collateral_attention_score": collateral_attention_score,
                "information_quality_score": information_quality_score,
                "overall_credit_review_pressure": (
                    overall_credit_review_pressure
                ),
                "bank_id": bank_id,
                "firm_id": firm_id,
                "evidence_counts": evidence_counts,
            },
            metadata={
                "model_id": self.spec.model_id,
                "calibration_status": self.spec.calibration_status,
            },
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iter_records(evidence: Mapping[str, Any], key: str):
    """Yield record-dicts under ``evidence[key]`` if present."""
    bundle = evidence.get(key)
    if bundle is None:
        return
    if isinstance(bundle, Mapping):
        yield bundle
        return
    for entry in bundle:
        if isinstance(entry, Mapping):
            yield entry


def _find_pressure_signal_for_firm(
    signals: list[Mapping[str, Any]], firm_id: str
) -> Mapping[str, Any] | None:
    """Pick the v1.9.4 pressure assessment signal whose
    ``subject_id`` matches the firm being reviewed."""
    for sig in signals:
        if (
            sig.get("signal_type") == _FIRM_PRESSURE_SIGNAL_TYPE
            and sig.get("subject_id") == firm_id
        ):
            return sig
    return None


def _safe_float(value: Any, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _coerce_iso_date(value: date | str | None, *, kernel: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    if value is None:
        if (
            kernel.clock is not None
            and kernel.clock.current_date is not None
        ):
            return kernel.clock.current_date.isoformat()
        raise ValueError(
            "as_of_date is None and the kernel clock has no current_date; "
            "supply as_of_date explicitly."
        )
    raise TypeError(
        f"as_of_date must be a date / ISO string / None; got {value!r}"
    )


def _default_signal_id(bank_id: str, firm_id: str, as_of_date: str) -> str:
    return (
        f"signal:{BANK_CREDIT_REVIEW_SIGNAL_TYPE}:"
        f"{bank_id}:{firm_id}:{as_of_date}"
    )


def _default_request_id(bank_id: str, firm_id: str, as_of_date: str) -> str:
    # Includes bank_id AND firm_id from the start so multi-bank
    # reviews on the same firm don't alias on the
    # ``mechanism_run:`` audit id (the v1.9.5 default formula
    # had this collision; v1.9.6 worked around it; v1.9.7 makes
    # it impossible by construction).
    return (
        f"req:bank_credit_review_lite:{bank_id}:{firm_id}:{as_of_date}"
    )


# ---------------------------------------------------------------------------
# Result + caller helper
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BankCreditReviewLiteResult:
    """Aggregate result of one
    :func:`run_reference_bank_credit_review_lite` call."""

    request: MechanismRunRequest
    output: MechanismOutputBundle
    run_record: MechanismRunRecord
    signal_id: str
    review_summary: Mapping[str, Any]

    @property
    def status(self) -> str:
        return self.output.status

    @property
    def overall_credit_review_pressure(self) -> float:
        return float(
            self.review_summary.get("overall_credit_review_pressure", 0.0)
        )


def run_reference_bank_credit_review_lite(
    kernel: Any,
    *,
    bank_id: str,
    firm_id: str,
    as_of_date: date | str | None = None,
    pressure_signal_ids: Sequence[str] | None = None,
    valuation_ids: Sequence[str] | None = None,
    selected_observation_set_ids: Sequence[str] | None = None,
    corporate_signal_ids: Sequence[str] | None = None,
    exposure_ids: Sequence[str] | None = None,
    variable_observation_ids: Sequence[str] | None = None,
    evidence_refs: Sequence[str] | None = None,
    request_id: str | None = None,
    signal_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BankCreditReviewLiteResult:
    """
    Caller-side helper that resolves evidence from the kernel,
    invokes the v1.9.7 :class:`BankCreditReviewLiteAdapter`, and
    commits the one proposed signal through
    ``kernel.signals.add_signal``.

    The adapter never sees ``kernel``. The contract:

    - **Caller** resolves all evidence ids into their record dicts.
    - **Adapter** reads ``request.evidence`` only.
    - **Caller** commits the adapter's proposed signal.

    Side effects (the only writes v1.9.7 performs):

    - One ``InformationSignal`` (the bank credit review note) in
      ``SignalBook`` (via ``add_signal``, which emits the
      existing ``signal_added`` ledger entry).

    No ``ContractBook``, ``ConstraintBook``, ``PriceBook``,
    ``OwnershipBook``, ``ValuationBook`` (after the v1.9.5
    valuation phase), or any other source-of-truth book is
    mutated. Tests pin every one of these.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(bank_id, str) or not bank_id:
        raise ValueError("bank_id is required and must be a non-empty string")
    if not isinstance(firm_id, str) or not firm_id:
        raise ValueError("firm_id is required and must be a non-empty string")

    iso_date = _coerce_iso_date(as_of_date, kernel=kernel)
    rid = request_id or _default_request_id(bank_id, firm_id, iso_date)

    # ------------------------------------------------------------------
    # 1. Resolve evidence from books.
    # ------------------------------------------------------------------
    evidence: dict[str, list[dict[str, Any]]] = {
        "InformationSignal": [],
        "ValuationRecord": [],
        "SelectedObservationSet": [],
        "VariableObservation": [],
        "ExposureRecord": [],
    }

    for sid in tuple(pressure_signal_ids or ()) + tuple(corporate_signal_ids or ()):
        sig = kernel.signals.get_signal(sid)
        evidence["InformationSignal"].append(
            {
                "signal_id": sig.signal_id,
                "signal_type": sig.signal_type,
                "subject_id": sig.subject_id,
                "source_id": sig.source_id,
                "published_date": sig.published_date,
                "payload": dict(sig.payload),
                "metadata": dict(sig.metadata),
            }
        )

    for vid in tuple(valuation_ids or ()):
        record = kernel.valuations.get_valuation(vid)
        evidence["ValuationRecord"].append(
            {
                "valuation_id": record.valuation_id,
                "subject_id": record.subject_id,
                "valuer_id": record.valuer_id,
                "valuation_type": record.valuation_type,
                "method": record.method,
                "as_of_date": record.as_of_date,
                "estimated_value": record.estimated_value,
                "currency": record.currency,
                "numeraire": record.numeraire,
                "confidence": record.confidence,
                "metadata": dict(record.metadata),
            }
        )

    for sel_id in tuple(selected_observation_set_ids or ()):
        sel = kernel.attention.get_selection(sel_id)
        evidence["SelectedObservationSet"].append(
            {
                "selection_id": sel.selection_id,
                "actor_id": sel.actor_id,
                "menu_id": sel.menu_id,
                "selected_refs": list(sel.selected_refs),
                "as_of_date": sel.as_of_date,
            }
        )

    for oid in tuple(variable_observation_ids or ()):
        obs = kernel.variables.get_observation(oid)
        try:
            spec = kernel.variables.get_variable(obs.variable_id)
            variable_group = spec.variable_group
        except Exception:
            variable_group = None
        evidence["VariableObservation"].append(
            {
                "observation_id": obs.observation_id,
                "variable_id": obs.variable_id,
                "variable_group": variable_group,
                "as_of_date": obs.as_of_date,
                "value": obs.value,
                "unit": obs.unit,
            }
        )

    for eid in tuple(exposure_ids or ()):
        exp = kernel.exposures.get_exposure(eid)
        evidence["ExposureRecord"].append(
            {
                "exposure_id": exp.exposure_id,
                "subject_id": exp.subject_id,
                "subject_type": exp.subject_type,
                "variable_id": exp.variable_id,
                "exposure_type": exp.exposure_type,
                "metric": exp.metric,
                "magnitude": float(exp.magnitude),
                "direction": exp.direction,
            }
        )

    # ------------------------------------------------------------------
    # 2. Build evidence_refs (caller-preserved order).
    # ------------------------------------------------------------------
    if evidence_refs is None:
        resolved_refs: tuple[str, ...] = (
            tuple(pressure_signal_ids or ())
            + tuple(valuation_ids or ())
            + tuple(corporate_signal_ids or ())
            + tuple(selected_observation_set_ids or ())
            + tuple(variable_observation_ids or ())
            + tuple(exposure_ids or ())
        )
    else:
        resolved_refs = tuple(evidence_refs)

    # ------------------------------------------------------------------
    # 3. Build adapter parameters.
    # ------------------------------------------------------------------
    parameters: dict[str, Any] = {"bank_id": bank_id}
    if signal_id is not None:
        parameters["signal_id"] = signal_id

    # ------------------------------------------------------------------
    # 4. Build the request.
    # ------------------------------------------------------------------
    request = MechanismRunRequest(
        request_id=rid,
        model_id=BANK_CREDIT_REVIEW_MODEL_ID,
        actor_id=firm_id,  # the firm being reviewed
        as_of_date=iso_date,
        selected_observation_set_ids=tuple(selected_observation_set_ids or ()),
        evidence_refs=resolved_refs,
        evidence=evidence,
        parameters=parameters,
        metadata=dict(metadata or {}),
    )

    # ------------------------------------------------------------------
    # 5. Apply the adapter (read-only; no kernel access).
    # ------------------------------------------------------------------
    adapter = BankCreditReviewLiteAdapter()
    output = adapter.apply(request)

    # ------------------------------------------------------------------
    # 6. Commit the one proposed signal through SignalBook.
    # ------------------------------------------------------------------
    if not output.proposed_signals:
        raise RuntimeError(
            "BankCreditReviewLiteAdapter returned no proposed signal; "
            "the v1.9.7 contract requires exactly one"
        )
    proposed = output.proposed_signals[0]

    # Caller may override the signal id if they want a custom
    # naming scheme; otherwise the adapter's default applies.
    final_signal_id = signal_id or proposed["signal_id"]

    signal = InformationSignal(
        signal_id=final_signal_id,
        signal_type=proposed["signal_type"],
        subject_id=proposed["subject_id"],
        source_id=proposed["source_id"],
        published_date=proposed["published_date"],
        effective_date=proposed.get("effective_date", proposed["published_date"]),
        visibility=proposed.get("visibility", "public"),
        confidence=float(proposed.get("confidence", 1.0)),
        payload=dict(proposed.get("payload", {})),
        related_ids=tuple(proposed.get("related_ids", ())),
        metadata=dict(proposed.get("metadata", {})),
    )
    kernel.signals.add_signal(signal)

    # ------------------------------------------------------------------
    # 7. Audit run record.
    # ------------------------------------------------------------------
    summary: dict[str, Any] = {
        "operating_pressure_score": float(
            output.output_summary.get("operating_pressure_score", 0.0)
        ),
        "valuation_pressure_score": float(
            output.output_summary.get("valuation_pressure_score", 0.0)
        ),
        "debt_service_attention_score": float(
            output.output_summary.get("debt_service_attention_score", 0.0)
        ),
        "collateral_attention_score": float(
            output.output_summary.get("collateral_attention_score", 0.0)
        ),
        "information_quality_score": float(
            output.output_summary.get("information_quality_score", 0.0)
        ),
        "overall_credit_review_pressure": float(
            output.output_summary.get("overall_credit_review_pressure", 0.0)
        ),
        "bank_id": bank_id,
        "firm_id": firm_id,
    }

    run_record = MechanismRunRecord(
        run_id=f"mechanism_run:{request.request_id}",
        request_id=request.request_id,
        model_id=adapter.spec.model_id,
        model_family=adapter.spec.model_family,
        version=adapter.spec.version,
        actor_id=request.actor_id,
        as_of_date=request.as_of_date,
        status=output.status,
        input_refs=request.evidence_refs,
        committed_output_refs=(signal.signal_id,),
        metadata={
            "calibration_status": adapter.spec.calibration_status,
            "review_summary": summary,
        },
    )

    return BankCreditReviewLiteResult(
        request=request,
        output=output,
        run_record=run_record,
        signal_id=signal.signal_id,
        review_summary=summary,
    )


# ---------------------------------------------------------------------------
# v1.12.6 — attention-conditioned helper
# ---------------------------------------------------------------------------


# v1.12.6 watch-label vocabulary (binding).
#
# A *watch label* is a small free-form non-binding tag that names
# what the bank's review attention surfaced in the resolved frame.
# It is not a rating, not a probability of default, not a lending
# decision, not a covenant view, not a price. The vocabulary is
# illustrative; tests pin the priority-order classifier below.
WATCH_LABEL_INFORMATION_GAP_REVIEW: str = "information_gap_review"
WATCH_LABEL_LIQUIDITY_WATCH: str = "liquidity_watch"
WATCH_LABEL_REFINANCING_WATCH: str = "refinancing_watch"
WATCH_LABEL_MARKET_ACCESS_WATCH: str = "market_access_watch"
WATCH_LABEL_COLLATERAL_WATCH: str = "collateral_watch"
WATCH_LABEL_HEIGHTENED_REVIEW: str = "heightened_review"
WATCH_LABEL_ROUTINE_MONITORING: str = "routine_monitoring"

ALL_WATCH_LABELS: tuple[str, ...] = (
    WATCH_LABEL_INFORMATION_GAP_REVIEW,
    WATCH_LABEL_LIQUIDITY_WATCH,
    WATCH_LABEL_REFINANCING_WATCH,
    WATCH_LABEL_MARKET_ACCESS_WATCH,
    WATCH_LABEL_COLLATERAL_WATCH,
    WATCH_LABEL_HEIGHTENED_REVIEW,
    WATCH_LABEL_ROUTINE_MONITORING,
)


# v1.12.6 watch-label rule-set thresholds. Small, documented,
# deterministic. None is a calibrated probability; none is a
# regulator-recognised credit measure.
_LIQUIDITY_PRESSURE_THRESHOLD: float = 0.65
_FUNDING_NEED_THRESHOLD: float = 0.70
_DEBT_SERVICE_PRESSURE_THRESHOLD: float = 0.65
_MARKET_ACCESS_PRESSURE_THRESHOLD: float = 0.65
_OVERALL_HEIGHTENED_THRESHOLD: float = 0.60
_RESTRICTIVE_OVERALL_LABEL: str = "selective_or_constrained"


def _classify_watch_label(
    *,
    has_firm_state_evidence: bool,
    has_pressure_signal_evidence: bool,
    high_liquidity_pressure: bool,
    high_funding_need_or_debt_service: bool,
    restrictive_market: bool,
    high_market_access_pressure: bool,
    overall_credit_review_pressure: float,
) -> str:
    """v1.12.6 deterministic watch-label classifier.

    Priority order:

    1. ``information_gap_review`` — when the bank's resolved frame
       carries neither firm-state evidence nor a pressure signal.
       The bank is reviewing without latent state.
    2. ``liquidity_watch`` — high liquidity pressure on a resolved
       firm state.
    3. ``refinancing_watch`` — high funding-need or debt-service
       pressure on a resolved firm state.
    4. ``market_access_watch`` — restrictive overall market access
       label on a resolved environment / readout.
    5. ``collateral_watch`` — high market-access pressure on a
       resolved firm state.
    6. ``heightened_review`` — overall pressure (from the v1.9.7
       adapter) ≥ 0.6.
    7. ``routine_monitoring`` — default.

    None of these labels is a rating, PD, LGD, EAD, loan term, or
    pricing.
    """
    if not (has_firm_state_evidence or has_pressure_signal_evidence):
        return WATCH_LABEL_INFORMATION_GAP_REVIEW
    if high_liquidity_pressure:
        return WATCH_LABEL_LIQUIDITY_WATCH
    if high_funding_need_or_debt_service:
        return WATCH_LABEL_REFINANCING_WATCH
    if restrictive_market:
        return WATCH_LABEL_MARKET_ACCESS_WATCH
    if high_market_access_pressure:
        return WATCH_LABEL_COLLATERAL_WATCH
    if overall_credit_review_pressure >= _OVERALL_HEIGHTENED_THRESHOLD:
        return WATCH_LABEL_HEIGHTENED_REVIEW
    return WATCH_LABEL_ROUTINE_MONITORING


def run_attention_conditioned_bank_credit_review_lite(
    kernel: Any,
    *,
    bank_id: str,
    firm_id: str,
    as_of_date: date | str | None = None,
    selected_observation_set_ids: Sequence[str] = (),
    explicit_pressure_signal_ids: Sequence[str] = (),
    explicit_corporate_signal_ids: Sequence[str] = (),
    explicit_valuation_ids: Sequence[str] = (),
    explicit_firm_state_ids: Sequence[str] = (),
    explicit_market_readout_ids: Sequence[str] = (),
    explicit_market_environment_state_ids: Sequence[str] = (),
    explicit_industry_condition_ids: Sequence[str] = (),
    explicit_exposure_ids: Sequence[str] = (),
    explicit_variable_observation_ids: Sequence[str] = (),
    request_id: str | None = None,
    signal_id: str | None = None,
    strict: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> BankCreditReviewLiteResult:
    """
    v1.12.6 — attention-conditioned bank credit review lite.

    Builds an :class:`world.evidence.ActorContextFrame` for the
    bank via :func:`world.evidence.resolve_actor_context` and
    runs the v1.9.7 :class:`BankCreditReviewLiteAdapter` on
    **only the resolver-surfaced evidence ids**. The bank's
    ``SelectedObservationSet`` is the attention surface;
    explicit-id kwargs cover evidence types not yet in the v1.8.x
    menu builder (firm states, market environment states, market
    readouts, valuations, industry conditions).

    The adapter's existing pressure-score formula is preserved
    bit-for-bit; v1.12.6 layers a deterministic synthetic
    **watch label** on top, derived from the resolved frame:

    - ``information_gap_review`` when the frame surfaces no firm
      state and no pressure signal;
    - ``liquidity_watch`` when a resolved firm state has
      ``liquidity_pressure ≥ 0.65``;
    - ``refinancing_watch`` when a resolved firm state has
      ``funding_need_intensity ≥ 0.7`` or
      ``debt_service_pressure ≥ 0.65``;
    - ``market_access_watch`` when a resolved capital-market
      readout or market environment carries
      ``overall_market_access_label == "selective_or_constrained"``;
    - ``collateral_watch`` when a resolved firm state has
      ``market_access_pressure ≥ 0.65``;
    - ``heightened_review`` when the v1.9.7 adapter's
      ``overall_credit_review_pressure ≥ 0.6``;
    - ``routine_monitoring`` otherwise.

    The watch label is a *recorded label*, not a decision. None
    of these is a rating, PD, LGD, EAD, loan term, pricing, or
    investment advice. Anti-claim metadata
    (``no_lending_decision`` / ``no_covenant_enforcement`` /
    ``no_contract_mutation`` / ``no_constraint_mutation`` /
    ``no_default_declaration`` / ``no_internal_rating`` /
    ``no_probability_of_default`` / ``synthetic_only``) is
    preserved bit-for-bit on the produced signal's metadata.

    Helper-level: the orchestrator continues to call
    :func:`run_reference_bank_credit_review_lite` for the
    living-world bank credit review phase. v1.12.6 is opt-in
    helper + tests; orchestrator wiring would shift the
    ``signal_added`` payload bytes (the new watch label and
    frame metadata) and is therefore deferred to a future
    v1.12.6.x sub-milestone, mirroring the v1.12.5 precedent.

    The helper does **not**:

    - approve, reject, or origin any loan;
    - enforce or trip any covenant;
    - mutate any source-of-truth book beyond the existing single
      ``SignalBook.add_signal`` write;
    - change interest rates or any other contract field;
    - detect or declare default;
    - form, observe, or move any market price;
    - imply that any score is a probability of default, an
      internal rating, an LGD, an EAD, or any
      regulator-recognised credit measure;
    - imply investment advice;
    - ingest real data, calibrate to any real economy, or apply
      Japan-specific calibration;
    - dispatch to an LLM agent or any external solver.

    Strict mode forwards to the resolver and raises
    :class:`world.evidence.StrictEvidenceResolutionError` on any
    unresolved id; the helper does not emit a signal in that
    case.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(bank_id, str) or not bank_id:
        raise ValueError(
            "bank_id is required and must be a non-empty string"
        )
    if not isinstance(firm_id, str) or not firm_id:
        raise ValueError(
            "firm_id is required and must be a non-empty string"
        )

    # Local import to keep the v1.9.7 import surface unchanged for
    # callers that don't use the v1.12.6 helper.
    from world.evidence import (  # noqa: PLC0415
        ActorContextFrame,
        resolve_actor_context,
    )

    iso_date = _coerce_iso_date(as_of_date, kernel=kernel)
    rid = request_id or _default_request_id(bank_id, firm_id, iso_date)

    # ------------------------------------------------------------------
    # Pass 1 — ask the resolver to build a context frame for this
    # bank on this date. Strict mode raises before any record is
    # emitted.
    # ------------------------------------------------------------------
    frame: ActorContextFrame = resolve_actor_context(
        kernel,
        actor_id=bank_id,
        actor_type="bank",
        as_of_date=iso_date,
        selected_observation_set_ids=tuple(selected_observation_set_ids),
        explicit_signal_ids=(
            tuple(explicit_pressure_signal_ids)
            + tuple(explicit_corporate_signal_ids)
        ),
        explicit_valuation_ids=tuple(explicit_valuation_ids),
        explicit_firm_state_ids=tuple(explicit_firm_state_ids),
        explicit_market_readout_ids=tuple(explicit_market_readout_ids),
        explicit_market_environment_state_ids=tuple(
            explicit_market_environment_state_ids
        ),
        explicit_industry_condition_ids=tuple(explicit_industry_condition_ids),
        explicit_exposure_ids=tuple(explicit_exposure_ids),
        explicit_variable_observation_ids=tuple(
            explicit_variable_observation_ids
        ),
        strict=strict,
    )

    # ------------------------------------------------------------------
    # Pass 2 — populate the adapter's evidence dict from resolved
    # frame ids only. The helper never scans the kernel's other
    # books for additional context.
    # ------------------------------------------------------------------
    evidence: dict[str, list[dict[str, Any]]] = {
        "InformationSignal": [],
        "ValuationRecord": [],
        "SelectedObservationSet": [],
        "VariableObservation": [],
        "ExposureRecord": [],
    }

    has_pressure_signal_evidence = False
    for sid in frame.resolved_signal_ids:
        sig = kernel.signals.get_signal(sid)
        evidence["InformationSignal"].append(
            {
                "signal_id": sig.signal_id,
                "signal_type": sig.signal_type,
                "subject_id": sig.subject_id,
                "source_id": sig.source_id,
                "published_date": sig.published_date,
                "payload": dict(sig.payload),
                "metadata": dict(sig.metadata),
            }
        )
        if (
            sig.signal_type == _FIRM_PRESSURE_SIGNAL_TYPE
            and sig.subject_id == firm_id
        ):
            has_pressure_signal_evidence = True

    for vid in frame.resolved_valuation_ids:
        record = kernel.valuations.get_valuation(vid)
        evidence["ValuationRecord"].append(
            {
                "valuation_id": record.valuation_id,
                "subject_id": record.subject_id,
                "valuer_id": record.valuer_id,
                "valuation_type": record.valuation_type,
                "method": record.method,
                "as_of_date": record.as_of_date,
                "estimated_value": record.estimated_value,
                "currency": record.currency,
                "numeraire": record.numeraire,
                "confidence": record.confidence,
                "metadata": dict(record.metadata),
            }
        )

    for sel_id in frame.selected_observation_set_ids:
        try:
            sel = kernel.attention.get_selection(sel_id)
        except Exception:
            continue
        evidence["SelectedObservationSet"].append(
            {
                "selection_id": sel.selection_id,
                "actor_id": sel.actor_id,
                "menu_id": sel.menu_id,
                "selected_refs": list(sel.selected_refs),
                "as_of_date": sel.as_of_date,
            }
        )

    for oid in frame.resolved_variable_observation_ids:
        obs = kernel.variables.get_observation(oid)
        try:
            spec = kernel.variables.get_variable(obs.variable_id)
            variable_group = spec.variable_group
        except Exception:
            variable_group = None
        evidence["VariableObservation"].append(
            {
                "observation_id": obs.observation_id,
                "variable_id": obs.variable_id,
                "variable_group": variable_group,
                "as_of_date": obs.as_of_date,
                "value": obs.value,
                "unit": obs.unit,
            }
        )

    for eid in frame.resolved_exposure_ids:
        exp = kernel.exposures.get_exposure(eid)
        evidence["ExposureRecord"].append(
            {
                "exposure_id": exp.exposure_id,
                "subject_id": exp.subject_id,
                "subject_type": exp.subject_type,
                "variable_id": exp.variable_id,
                "exposure_type": exp.exposure_type,
                "metric": exp.metric,
                "magnitude": float(exp.magnitude),
                "direction": exp.direction,
            }
        )

    # ------------------------------------------------------------------
    # Pass 3 — derive the watch-label classifier inputs from
    # additional resolved frame slots that the v1.9.7 adapter does
    # not consume directly (firm states, market readouts, market
    # environments).
    # ------------------------------------------------------------------
    has_firm_state_evidence = bool(frame.resolved_firm_state_ids)
    high_liquidity_pressure = False
    high_funding_need_or_debt_service = False
    high_market_access_pressure = False
    if has_firm_state_evidence:
        for fsid in frame.resolved_firm_state_ids:
            try:
                state = kernel.firm_financial_states.get_state(fsid)
            except Exception:
                continue
            if state.liquidity_pressure >= _LIQUIDITY_PRESSURE_THRESHOLD:
                high_liquidity_pressure = True
            if (
                state.funding_need_intensity >= _FUNDING_NEED_THRESHOLD
                or state.debt_service_pressure
                >= _DEBT_SERVICE_PRESSURE_THRESHOLD
            ):
                high_funding_need_or_debt_service = True
            if (
                state.market_access_pressure
                >= _MARKET_ACCESS_PRESSURE_THRESHOLD
            ):
                high_market_access_pressure = True

    restrictive_market = False
    for rid_x in frame.resolved_market_readout_ids:
        try:
            readout = kernel.capital_market_readouts.get_readout(rid_x)
        except Exception:
            continue
        if readout.overall_market_access_label == _RESTRICTIVE_OVERALL_LABEL:
            restrictive_market = True
    for eid in frame.resolved_market_environment_state_ids:
        try:
            env = kernel.market_environments.get_state(eid)
        except Exception:
            continue
        if env.overall_market_access_label == _RESTRICTIVE_OVERALL_LABEL:
            restrictive_market = True

    # ------------------------------------------------------------------
    # Pass 4 — build evidence_refs (deterministic, first-seen
    # order) and run the adapter.
    # ------------------------------------------------------------------
    resolved_refs: tuple[str, ...] = (
        tuple(frame.resolved_signal_ids)
        + tuple(frame.resolved_valuation_ids)
        + tuple(frame.selected_observation_set_ids)
        + tuple(frame.resolved_variable_observation_ids)
        + tuple(frame.resolved_exposure_ids)
        + tuple(frame.resolved_firm_state_ids)
        + tuple(frame.resolved_market_readout_ids)
        + tuple(frame.resolved_market_environment_state_ids)
        + tuple(frame.resolved_industry_condition_ids)
    )

    parameters: dict[str, Any] = {"bank_id": bank_id}
    if signal_id is not None:
        parameters["signal_id"] = signal_id

    request = MechanismRunRequest(
        request_id=rid,
        model_id=BANK_CREDIT_REVIEW_MODEL_ID,
        actor_id=firm_id,
        as_of_date=iso_date,
        selected_observation_set_ids=tuple(
            frame.selected_observation_set_ids
        ),
        evidence_refs=resolved_refs,
        evidence=evidence,
        parameters=parameters,
        metadata=dict(metadata or {}),
    )

    adapter = BankCreditReviewLiteAdapter()
    output = adapter.apply(request)
    if not output.proposed_signals:
        raise RuntimeError(
            "BankCreditReviewLiteAdapter returned no proposed signal; "
            "the v1.9.7 contract requires exactly one"
        )
    proposed = output.proposed_signals[0]
    overall_credit_review_pressure = float(
        proposed["payload"].get("overall_credit_review_pressure", 0.0)
    )

    # ------------------------------------------------------------------
    # Pass 5 — derive the watch label and stamp the v1.12.6 frame
    # audit onto the proposed signal's payload + metadata. We do
    # NOT introduce any new ledger event type; the adapter still
    # emits a single ``signal_added`` record per call.
    # ------------------------------------------------------------------
    watch_label = _classify_watch_label(
        has_firm_state_evidence=has_firm_state_evidence,
        has_pressure_signal_evidence=has_pressure_signal_evidence,
        high_liquidity_pressure=high_liquidity_pressure,
        high_funding_need_or_debt_service=high_funding_need_or_debt_service,
        restrictive_market=restrictive_market,
        high_market_access_pressure=high_market_access_pressure,
        overall_credit_review_pressure=overall_credit_review_pressure,
    )

    final_signal_id = signal_id or proposed["signal_id"]
    payload = dict(proposed.get("payload", {}))
    # v1.12.6 additive payload key: the synthetic non-binding
    # watch label, plus the frame's resolved bucket counts so an
    # audit reader can see which evidence shapes the bank actually
    # surfaced.
    payload["watch_label"] = watch_label
    payload["context_frame_id"] = frame.context_frame_id
    payload["context_frame_status"] = frame.status
    payload["resolved_evidence_buckets"] = {
        "signals": len(frame.resolved_signal_ids),
        "valuations": len(frame.resolved_valuation_ids),
        "exposures": len(frame.resolved_exposure_ids),
        "firm_states": len(frame.resolved_firm_state_ids),
        "market_readouts": len(frame.resolved_market_readout_ids),
        "market_environment_states": len(
            frame.resolved_market_environment_state_ids
        ),
        "industry_conditions": len(frame.resolved_industry_condition_ids),
        "variable_observations": len(
            frame.resolved_variable_observation_ids
        ),
    }

    extra_metadata = dict(proposed.get("metadata", {}))
    extra_metadata["attention_conditioned"] = True
    extra_metadata["context_frame_id"] = frame.context_frame_id
    extra_metadata["context_frame_status"] = frame.status
    extra_metadata["context_frame_confidence"] = frame.confidence
    extra_metadata["watch_label"] = watch_label
    if frame.unresolved_refs:
        extra_metadata["unresolved_refs"] = [
            r.to_dict() for r in frame.unresolved_refs
        ]

    signal = InformationSignal(
        signal_id=final_signal_id,
        signal_type=proposed["signal_type"],
        subject_id=proposed["subject_id"],
        source_id=proposed["source_id"],
        published_date=proposed["published_date"],
        effective_date=proposed.get(
            "effective_date", proposed["published_date"]
        ),
        visibility=proposed.get("visibility", "public"),
        confidence=float(proposed.get("confidence", 1.0)),
        payload=payload,
        related_ids=tuple(proposed.get("related_ids", ())),
        metadata=extra_metadata,
    )
    kernel.signals.add_signal(signal)

    # ------------------------------------------------------------------
    # Pass 6 — audit run record (mirrors v1.9.7 shape; adds the
    # attention-conditioning audit fields under metadata).
    # ------------------------------------------------------------------
    summary: dict[str, Any] = {
        "operating_pressure_score": float(
            output.output_summary.get("operating_pressure_score", 0.0)
        ),
        "valuation_pressure_score": float(
            output.output_summary.get("valuation_pressure_score", 0.0)
        ),
        "debt_service_attention_score": float(
            output.output_summary.get("debt_service_attention_score", 0.0)
        ),
        "collateral_attention_score": float(
            output.output_summary.get("collateral_attention_score", 0.0)
        ),
        "information_quality_score": float(
            output.output_summary.get("information_quality_score", 0.0)
        ),
        "overall_credit_review_pressure": overall_credit_review_pressure,
        "bank_id": bank_id,
        "firm_id": firm_id,
        "watch_label": watch_label,
        "attention_conditioned": True,
        "context_frame_id": frame.context_frame_id,
        "context_frame_status": frame.status,
        "context_frame_confidence": frame.confidence,
    }

    run_record = MechanismRunRecord(
        run_id=f"mechanism_run:{request.request_id}",
        request_id=request.request_id,
        model_id=adapter.spec.model_id,
        model_family=adapter.spec.model_family,
        version=adapter.spec.version,
        actor_id=request.actor_id,
        as_of_date=request.as_of_date,
        status=output.status,
        input_refs=request.evidence_refs,
        committed_output_refs=(signal.signal_id,),
        metadata={
            "calibration_status": adapter.spec.calibration_status,
            "review_summary": summary,
        },
    )

    return BankCreditReviewLiteResult(
        request=request,
        output=output,
        run_record=run_record,
        signal_id=signal.signal_id,
        review_summary=summary,
    )
