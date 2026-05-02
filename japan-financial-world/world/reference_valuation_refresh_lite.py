"""
v1.9.5 Reference Valuation Refresh Lite Mechanism.

This module ships the project's **second concrete mechanism** on
top of the v1.9.3 / v1.9.3.1 mechanism interface. It consumes
the v1.9.4 firm-pressure-assessment signal (plus optional
corporate reporting signals, selected observation sets, variable
observations, and exposures), and proposes one **opinionated
synthetic** :class:`ValuationRecord` that is committed through
the existing v1.1 ``ValuationBook.add_valuation`` ledger path.

Hard boundary
-------------

This is **not a true valuation model.** It is a synthetic
reference mechanism showing how diagnostic pressure and selected
evidence can produce an auditable valuation claim. The mechanism
explicitly does **not**:

- form, observe, or move any market price;
- trade, allocate, or rebalance any portfolio;
- make a buy / sell / hold recommendation;
- make a lending decision;
- enforce or trip a covenant;
- update any firm financial statement, balance-sheet line item,
  cash, leverage, revenue, margin, or DSCR / LTV measure;
- imply that the produced ``estimated_value`` is the canonical
  truth — it is **one valuer's opinionated claim** under the
  synthetic, jurisdiction-neutral assumptions documented below;
- imply investment advice of any kind;
- ingest real data, calibrate to any real economy, or run a
  scenario engine.

What the mechanism *is*: an auditable transformation of
*pressure + evidence → opinionated valuation claim*. The claim is
data; what (if anything) any consumer of that claim does with it
is a v1.9.6+ / caller-side concern.

Method label
------------

The mechanism stamps every produced ``ValuationRecord`` with
``method = "synthetic_lite_pressure_adjusted"`` so a reader can
unambiguously identify the modelling style and reject any reading
that treats the claim as canonical.

Calibration vocabulary
----------------------

``calibration_status = "synthetic"``. The valuation arithmetic is
a small linear pressure-adjustment formula on a baseline value
the caller supplies. Magnitudes are illustrative round numbers,
not calibrated sensitivities (per the v1.8.10 ``ExposureRecord``
contract).

Algorithm (deterministic; documented inline in
:func:`_compute_valuation_payload`)
------------------------------------------------------------

Given a pressure assessment with ``overall_pressure ∈ [0, 1]``
and a caller-supplied ``baseline_value``:

    pressure_haircut_fraction
        = pressure_haircut_per_unit_pressure * overall_pressure
    estimated_value
        = baseline_value * (1 - clamp(pressure_haircut_fraction, 0, 1))
    confidence
        = clamp(
            1 - confidence_decay_per_unit_pressure * overall_pressure,
            0,
            1,
        )

Default coefficients are deliberately conservative
(``pressure_haircut_per_unit_pressure = 0.30``,
``confidence_decay_per_unit_pressure = 0.40``) — pressure of 1.0
on the canonical fixture trims the baseline value by 30% and
drops confidence to 0.6. Coefficients are caller-overridable
through ``parameters`` on the request, but the defaults are
recorded in ``MechanismSpec.assumptions`` so an auditor can read
them off the spec.

Degraded path
-------------

If no pressure assessment signal is present in the evidence, the
mechanism returns ``status = "degraded"`` and proposes a
**baseline-only** valuation: ``estimated_value = baseline_value``,
``confidence = 1.0`` (when a baseline is supplied) or
``estimated_value = None`` (when no baseline is supplied either).
The mechanism never crashes on missing optional evidence.

Mechanism interface contract
----------------------------

The adapter implements the v1.9.3 / v1.9.3.1
:class:`MechanismAdapter` Protocol:

- ``apply(request: MechanismRunRequest) -> MechanismOutputBundle``
  reads ``request.evidence`` and ``request.parameters`` only;
- the adapter does **not** accept a kernel parameter;
- the adapter does **not** read any book or the ledger;
- the adapter does **not** mutate ``request``;
- the adapter does **not** commit any proposal — that is the
  caller's job in :func:`run_reference_valuation_refresh_lite`.
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
from world.valuations import ValuationRecord


# ---------------------------------------------------------------------------
# Controlled vocabulary
# ---------------------------------------------------------------------------


VALUATION_REFRESH_MODEL_ID: str = (
    "mechanism:valuation_mechanism:reference_valuation_refresh_lite_v0"
)
VALUATION_REFRESH_MODEL_FAMILY: str = "valuation_mechanism"
VALUATION_REFRESH_MECHANISM_VERSION: str = "0.1"
VALUATION_REFRESH_METHOD_LABEL: str = "synthetic_lite_pressure_adjusted"
VALUATION_REFRESH_VALUATION_TYPE: str = "synthetic_firm_equity_estimate"
VALUATION_REFRESH_PURPOSE: str = "reference_pressure_aware_valuation"

# Pressure-signal type the v1.9.4 mechanism emits (kept as a
# string here so the import graph stays one-way: v1.9.5 consumes
# v1.9.4's *output*, not v1.9.4's module surface).
_FIRM_PRESSURE_SIGNAL_TYPE: str = "firm_operating_pressure_assessment"

# Default coefficients (caller-overridable through
# request.parameters). Synthetic; not calibrated.
_DEFAULT_PRESSURE_HAIRCUT_PER_UNIT_PRESSURE: float = 0.30
_DEFAULT_CONFIDENCE_DECAY_PER_UNIT_PRESSURE: float = 0.40


# ---------------------------------------------------------------------------
# Spec singleton
# ---------------------------------------------------------------------------


_DEFAULT_SPEC: MechanismSpec = MechanismSpec(
    model_id=VALUATION_REFRESH_MODEL_ID,
    model_family=VALUATION_REFRESH_MODEL_FAMILY,
    version=VALUATION_REFRESH_MECHANISM_VERSION,
    assumptions=(
        "linear_pressure_haircut_on_baseline_value",
        f"default_pressure_haircut_per_unit_pressure={_DEFAULT_PRESSURE_HAIRCUT_PER_UNIT_PRESSURE}",
        f"default_confidence_decay_per_unit_pressure={_DEFAULT_CONFIDENCE_DECAY_PER_UNIT_PRESSURE}",
        "baseline_value_supplied_by_caller_not_observed",
        "no_real_data",
        "no_calibration",
        "opinionated_claim_not_canonical_truth",
        "no_price_movement",
        "no_decision",
    ),
    calibration_status="synthetic",
    stochasticity="deterministic",
    required_inputs=(
        # The pressure signal is the primary input; the others are
        # optional and used only to populate `inputs` / `related_ids`
        # for audit lineage.
        "InformationSignal",
        "VariableObservation",
        "ExposureRecord",
        "SelectedObservationSet",
    ),
    output_types=("ValuationRecord",),
    metadata={
        "method": VALUATION_REFRESH_METHOD_LABEL,
        "valuation_type": VALUATION_REFRESH_VALUATION_TYPE,
        "purpose": VALUATION_REFRESH_PURPOSE,
        "boundary": (
            "valuation_claim_only; no_price_movement; "
            "no_investment_advice; synthetic_only; "
            "no_canonical_truth_claim"
        ),
    },
)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValuationRefreshLiteAdapter:
    """
    The v1.9.5 adapter. Pure function over
    :class:`MechanismRunRequest`; produces one
    :class:`MechanismOutputBundle` carrying a single proposed
    :class:`ValuationRecord` mapping.

    The adapter is **immutable** (frozen dataclass) and **does
    not** carry kernel state. Two adapters with the same spec
    produce byte-identical outputs on byte-identical requests
    (the deterministic-replay invariant).
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
        observations = list(_iter_records(request.evidence, "VariableObservation"))
        exposures = list(_iter_records(request.evidence, "ExposureRecord"))
        selections = list(
            _iter_records(request.evidence, "SelectedObservationSet")
        )

        # Pull the firm pressure signal (the primary input).
        pressure_signal = _find_pressure_signal(signals, request.actor_id)
        overall_pressure = _safe_float(
            (pressure_signal or {}).get("payload", {}).get("overall_pressure"),
            default=0.0,
        )
        pressure_signal_id = (
            pressure_signal.get("signal_id") if pressure_signal else None
        )
        pressure_status = (
            (pressure_signal or {}).get("payload", {}).get("status")
        )

        # Caller-supplied parameters: baseline_value (optional),
        # plus the two coefficient overrides.
        params = request.parameters
        baseline_value = _safe_float(params.get("baseline_value"), default=None)
        haircut_coef = _safe_float(
            params.get("pressure_haircut_per_unit_pressure"),
            default=_DEFAULT_PRESSURE_HAIRCUT_PER_UNIT_PRESSURE,
        )
        confidence_decay = _safe_float(
            params.get("confidence_decay_per_unit_pressure"),
            default=_DEFAULT_CONFIDENCE_DECAY_PER_UNIT_PRESSURE,
        )
        currency = (
            params.get("currency") if isinstance(params.get("currency"), str)
            else "unspecified"
        ) or "unspecified"
        numeraire = (
            params.get("numeraire")
            if isinstance(params.get("numeraire"), str)
            else "unspecified"
        ) or "unspecified"
        valuation_id_override = params.get("valuation_id")

        # Compute estimated_value + confidence.
        if pressure_signal is None:
            # Degraded: no pressure evidence. Conservative output.
            status = "degraded"
            if baseline_value is not None:
                estimated_value: float | None = baseline_value
                confidence = 1.0
            else:
                estimated_value = None
                confidence = 0.0
        else:
            status = "completed"
            haircut_fraction = max(
                0.0, min(1.0, haircut_coef * overall_pressure)
            )
            if baseline_value is None:
                estimated_value = None
                confidence = max(
                    0.0, min(1.0, 1.0 - confidence_decay * overall_pressure)
                )
            else:
                estimated_value = baseline_value * (1.0 - haircut_fraction)
                confidence = max(
                    0.0, min(1.0, 1.0 - confidence_decay * overall_pressure)
                )

        # Build provenance.
        related_ids: list[str] = []
        if pressure_signal_id:
            related_ids.append(pressure_signal_id)
        for sig in signals:
            sid = sig.get("signal_id")
            if (
                isinstance(sid, str)
                and sid
                and sid not in related_ids
                and sig.get("signal_type") != _FIRM_PRESSURE_SIGNAL_TYPE
            ):
                related_ids.append(sid)
        for sel in selections:
            sid = sel.get("selection_id")
            if isinstance(sid, str) and sid and sid not in related_ids:
                related_ids.append(sid)

        # Build inputs (audit-friendly summary; keep it small so
        # the ledger payload doesn't bloat).
        inputs_summary: dict[str, Any] = {
            "overall_pressure": overall_pressure,
            "baseline_value": baseline_value,
            "pressure_signal_id": pressure_signal_id,
            "evidence_counts": {
                "information_signals": len(signals),
                "variable_observations": len(observations),
                "exposure_records": len(exposures),
                "selected_observation_sets": len(selections),
            },
            "pressure_signal_status": pressure_status,
        }

        valuation_id = (
            valuation_id_override
            if isinstance(valuation_id_override, str) and valuation_id_override
            else _default_valuation_id(request.actor_id, request.as_of_date)
        )

        proposed_valuation: dict[str, Any] = {
            "valuation_id": valuation_id,
            "subject_id": request.actor_id,
            # The valuer is supplied via metadata so the adapter
            # need not look it up; the caller helper can override
            # via parameters["valuer_id"] (see below).
            "valuer_id": (
                params.get("valuer_id")
                if isinstance(params.get("valuer_id"), str)
                and params.get("valuer_id")
                else f"valuer:{self.spec.model_id}"
            ),
            "valuation_type": VALUATION_REFRESH_VALUATION_TYPE,
            "purpose": VALUATION_REFRESH_PURPOSE,
            "method": VALUATION_REFRESH_METHOD_LABEL,
            "as_of_date": request.as_of_date,
            "estimated_value": estimated_value,
            "currency": currency,
            "numeraire": numeraire,
            "confidence": confidence,
            "assumptions": {
                "pressure_haircut_per_unit_pressure": haircut_coef,
                "confidence_decay_per_unit_pressure": confidence_decay,
                "linear_pressure_haircut_on_baseline_value": True,
                "baseline_value_supplied_by_caller": baseline_value is not None,
            },
            "inputs": inputs_summary,
            "related_ids": related_ids,
            "metadata": {
                "model_id": self.spec.model_id,
                "model_family": self.spec.model_family,
                "version": self.spec.version,
                "calibration_status": self.spec.calibration_status,
                "method": VALUATION_REFRESH_METHOD_LABEL,
                "no_price_movement": True,
                "no_investment_advice": True,
                "synthetic_only": True,
                "pressure_signal_id": pressure_signal_id,
                "boundary": (
                    "valuation_claim_only; "
                    "no_price_movement; "
                    "no_investment_advice; "
                    "synthetic_only; "
                    "no_canonical_truth_claim"
                ),
            },
        }

        return MechanismOutputBundle(
            request_id=request.request_id,
            model_id=self.spec.model_id,
            status=status,
            proposed_valuation_records=(proposed_valuation,),
            output_summary={
                "estimated_value": estimated_value,
                "confidence": confidence,
                "overall_pressure": overall_pressure,
                "baseline_value": baseline_value,
                "pressure_signal_id": pressure_signal_id,
                "method": VALUATION_REFRESH_METHOD_LABEL,
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
    """Yield record-dicts under ``evidence[key]`` if present.

    Returns an empty iterator for missing keys so the adapter
    tolerates incomplete evidence (the v1.8.1 anti-scenario
    rule).
    """
    bundle = evidence.get(key)
    if bundle is None:
        return
    if isinstance(bundle, Mapping):
        yield bundle
        return
    for entry in bundle:
        if isinstance(entry, Mapping):
            yield entry


def _find_pressure_signal(
    signals: list[Mapping[str, Any]], actor_id: str
) -> Mapping[str, Any] | None:
    """Pick the one v1.9.4 firm-pressure-assessment signal that
    matches ``actor_id``. Returns the first match in
    declaration order; returns ``None`` if none.
    """
    for sig in signals:
        if (
            sig.get("signal_type") == _FIRM_PRESSURE_SIGNAL_TYPE
            and sig.get("subject_id") == actor_id
        ):
            return sig
    return None


def _safe_float(value: Any, *, default: float | None) -> float | None:
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


def _default_valuation_id(firm_id: str, as_of_date: str) -> str:
    return f"valuation:reference_lite:{firm_id}:{as_of_date}"


def _default_request_id(firm_id: str, as_of_date: str) -> str:
    return f"req:valuation_refresh_lite:{firm_id}:{as_of_date}"


# ---------------------------------------------------------------------------
# Caller-side helper + result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValuationRefreshLiteResult:
    """Aggregate result of one
    :func:`run_reference_valuation_refresh_lite` call.

    Carries the request, the adapter's output bundle, the audit
    :class:`MechanismRunRecord`, and the resulting
    ``valuation_id`` once the caller committed the proposed
    record.
    """

    request: MechanismRunRequest
    output: MechanismOutputBundle
    run_record: MechanismRunRecord
    valuation_id: str
    valuation_summary: Mapping[str, Any]

    @property
    def status(self) -> str:
        return self.output.status

    @property
    def estimated_value(self) -> float | None:
        return self.valuation_summary.get("estimated_value")

    @property
    def confidence(self) -> float:
        return float(self.valuation_summary.get("confidence", 0.0))


def run_reference_valuation_refresh_lite(
    kernel: Any,
    *,
    firm_id: str,
    valuer_id: str,
    as_of_date: date | str | None = None,
    pressure_signal_ids: Sequence[str] | None = None,
    corporate_signal_ids: Sequence[str] | None = None,
    selected_observation_set_ids: Sequence[str] | None = None,
    variable_observation_ids: Sequence[str] | None = None,
    exposure_ids: Sequence[str] | None = None,
    baseline_value: float | None = None,
    currency: str = "unspecified",
    numeraire: str = "unspecified",
    pressure_haircut_per_unit_pressure: float | None = None,
    confidence_decay_per_unit_pressure: float | None = None,
    evidence_refs: Sequence[str] | None = None,
    request_id: str | None = None,
    valuation_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ValuationRefreshLiteResult:
    """
    Caller-side helper that resolves evidence from the kernel,
    invokes the v1.9.5 :class:`ValuationRefreshLiteAdapter`, and
    commits the one proposed :class:`ValuationRecord` through
    ``kernel.valuations.add_valuation``.

    The adapter never sees ``kernel``. The contract:

    - **Caller** resolves ``pressure_signal_ids`` (the v1.9.4
      firm-pressure-assessment signals), ``corporate_signal_ids``,
      ``selected_observation_set_ids``,
      ``variable_observation_ids``, and ``exposure_ids`` from the
      respective books. Each resolved record becomes a
      JSON-friendly dict in ``request.evidence``.
    - **Adapter** reads ``request.evidence`` +
      ``request.parameters`` only.
    - **Caller** commits the adapter's proposed valuation.

    Side effects (the only writes v1.9.5 performs):

    - One :class:`ValuationRecord` in
      :class:`world.valuations.ValuationBook` (via
      ``add_valuation``, which emits the existing
      ``valuation_added`` ledger entry).

    No price, ownership, contract, constraint, exposure, variable,
    institution, external-process, relationship, routine,
    attention, or interaction state is mutated. Tests pin every
    one of these.

    Parameters of note
    ------------------
    - ``valuer_id``: required; identifies the entity whose opinion
      is being recorded (an investor, an analyst desk, etc.).
      Free-form string; not validated against the registry.
    - ``baseline_value``: optional float. The pressure-haircut
      formula uses this as the starting point; without a baseline
      the mechanism still produces a record (with
      ``estimated_value=None``) but the claim is degraded.
    - ``currency`` / ``numeraire``: passed through to the
      :class:`ValuationRecord`. Default ``"unspecified"`` (the
      v1.1 neutral label).
    - ``pressure_haircut_per_unit_pressure`` /
      ``confidence_decay_per_unit_pressure``: optional
      coefficient overrides. Defaults are documented in the
      module docstring and embedded in
      ``MechanismSpec.assumptions``.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(firm_id, str) or not firm_id:
        raise ValueError("firm_id is required and must be a non-empty string")
    if not isinstance(valuer_id, str) or not valuer_id:
        raise ValueError("valuer_id is required and must be a non-empty string")

    iso_date = _coerce_iso_date(as_of_date, kernel=kernel)
    rid = request_id or _default_request_id(firm_id, iso_date)

    # ------------------------------------------------------------------
    # 1. Resolve evidence from books.
    # ------------------------------------------------------------------
    evidence: dict[str, list[dict[str, Any]]] = {
        "InformationSignal": [],
        "VariableObservation": [],
        "ExposureRecord": [],
        "SelectedObservationSet": [],
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

    # ------------------------------------------------------------------
    # 2. Build evidence_refs (caller-preserved order).
    # ------------------------------------------------------------------
    if evidence_refs is None:
        resolved_refs: tuple[str, ...] = (
            tuple(pressure_signal_ids or ())
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
    parameters: dict[str, Any] = {
        "valuer_id": valuer_id,
        "currency": currency,
        "numeraire": numeraire,
    }
    if baseline_value is not None:
        parameters["baseline_value"] = float(baseline_value)
    if pressure_haircut_per_unit_pressure is not None:
        parameters["pressure_haircut_per_unit_pressure"] = float(
            pressure_haircut_per_unit_pressure
        )
    if confidence_decay_per_unit_pressure is not None:
        parameters["confidence_decay_per_unit_pressure"] = float(
            confidence_decay_per_unit_pressure
        )
    if valuation_id is not None:
        parameters["valuation_id"] = valuation_id

    # ------------------------------------------------------------------
    # 4. Build the request.
    # ------------------------------------------------------------------
    request = MechanismRunRequest(
        request_id=rid,
        model_id=VALUATION_REFRESH_MODEL_ID,
        actor_id=firm_id,
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
    adapter = ValuationRefreshLiteAdapter()
    output = adapter.apply(request)

    # ------------------------------------------------------------------
    # 6. Commit the one proposed valuation through ValuationBook.
    # ------------------------------------------------------------------
    if not output.proposed_valuation_records:
        raise RuntimeError(
            "ValuationRefreshLiteAdapter returned no proposed valuation; "
            "the v1.9.5 contract requires exactly one"
        )
    proposed = output.proposed_valuation_records[0]

    record = ValuationRecord(
        valuation_id=proposed["valuation_id"],
        subject_id=proposed["subject_id"],
        valuer_id=proposed["valuer_id"],
        valuation_type=proposed["valuation_type"],
        purpose=proposed["purpose"],
        method=proposed["method"],
        as_of_date=proposed["as_of_date"],
        estimated_value=proposed.get("estimated_value"),
        currency=proposed.get("currency", "unspecified"),
        numeraire=proposed.get("numeraire", "unspecified"),
        confidence=float(proposed.get("confidence", 1.0)),
        assumptions=dict(proposed.get("assumptions", {})),
        inputs=dict(proposed.get("inputs", {})),
        related_ids=tuple(proposed.get("related_ids", ())),
        metadata=dict(proposed.get("metadata", {})),
    )
    kernel.valuations.add_valuation(record)

    # ------------------------------------------------------------------
    # 7. Audit run record.
    # ------------------------------------------------------------------
    summary: dict[str, Any] = {
        "estimated_value": output.output_summary.get("estimated_value"),
        "confidence": float(output.output_summary.get("confidence", 0.0)),
        "overall_pressure": float(
            output.output_summary.get("overall_pressure", 0.0)
        ),
        "baseline_value": output.output_summary.get("baseline_value"),
        "pressure_signal_id": output.output_summary.get("pressure_signal_id"),
        "method": output.output_summary.get("method"),
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
        committed_output_refs=(record.valuation_id,),
        metadata={
            "calibration_status": adapter.spec.calibration_status,
            "valuation_summary": summary,
        },
    )

    return ValuationRefreshLiteResult(
        request=request,
        output=output,
        run_record=run_record,
        valuation_id=record.valuation_id,
        valuation_summary=summary,
    )
