"""
v1.9.3 Mechanism interface + v1.9.3.1 hardening (contract only — no
behavior).

This module ships the **contract** that v1.9.4+ economic-behavior
mechanisms will plug into. v1.9.3 introduced the five interface
types; v1.9.3.1 hardened them in three small ways:

1. **Deep-ish freeze for JSON-like data.** The four immutable
   dataclasses store nested mappings as ``MappingProxyType`` and
   nested lists / tuples as ``tuple``, recursively. A frozen
   dataclass alone is *shallow* — it prevents reassignment of a
   top-level attribute but does nothing to stop an outsider
   mutating a nested ``dict`` via subscript-assign. v1.9.3.1
   pushes the immutability one level deeper so audit / replay
   downstream of a mechanism's output cannot quietly observe a
   different snapshot than the mechanism saw.
2. **Rename** ``MechanismInputBundle`` → :class:`MechanismRunRequest`
   with a clearer field set. The new shape splits *evidence
   refs* (the deterministic lineage of record ids the caller
   resolved) from *evidence* (the resolved data, grouped by
   record type or logical key). Adapters read ``evidence``;
   they do **not** reach into the kernel or any book. The
   caller is responsible for resolving refs into evidence
   before invoking ``apply``. ``MechanismInputBundle`` is kept
   as a one-line backwards-compat alias.
3. **Clarify input-refs ordering.** :class:`MechanismRunRecord`
   preserves caller-provided ``input_refs`` order verbatim. It
   does **not** auto-dedupe or sort. Callers that need
   deterministic replay must order / dedupe their input_refs
   themselves; some mechanisms may carry meaningful order
   (e.g., a sequence of trades or a series of revisions) and
   v1.9.3.1 declines to second-guess them.

v1.9.3.1 still ships **no economic behavior**. The four dataclasses
plus the Protocol are pure data; the only code change is in the
deep-freeze helpers and the field rename.

Why this matters before v1.9.4
-------------------------------

The v1.9.3 audit
(``docs/model_mechanism_inventory.md`` +
``docs/behavioral_gap_audit.md``) records that the project so
far is a routine-driven information-flow substrate. v1.9.4 will
introduce the first concrete mechanism (firm financial update /
margin pressure). Hardening the interface *before* v1.9.4 lands
means:

- the first concrete mechanism cannot accidentally rely on
  shallow immutability;
- adapter code never receives a kernel reference (the contract
  forbids it; tests pin it);
- ``input_refs`` ordering responsibility is the caller's, by
  contract — so the mechanism cannot blame the substrate for
  replay drift on a misordered list.

Principles (also documented in ``docs/model_mechanism_inventory.md``)
---------------------------------------------------------------------

1. **Mechanisms do not directly mutate books.** They *propose*
   outputs; the caller decides what is committed.
2. **Mechanisms consume typed refs / resolved evidence / state
   views.** Inputs are explicit; no hidden globals; **no kernel
   or book access**.
3. **Mechanisms return proposed records or output bundles.**
4. **The caller decides which outputs are committed.**
5. **Every mechanism run is ledger-auditable** — through a
   :class:`MechanismRunRecord` the caller writes.
6. **Each mechanism declares**: ``model_id``, ``model_family``,
   ``version``, ``assumptions``, ``calibration_status``,
   ``stochasticity``, ``required_inputs``, ``output_types``.
7. **Reference mechanisms are simple and synthetic.**
8. **Advanced mechanisms attach as adapters.** FCN, herding,
   minority game, speculation game, LOB-style market
   microstructure are v2+ candidates.

Calibration vocabulary
----------------------

``MechanismSpec.calibration_status`` follows
:data:`CALIBRATION_STATUSES`:

- ``"synthetic"`` — illustrative round numbers, not calibrated.
- ``"public_data_calibrated"`` — driven by openly available data
  (v2 territory).
- ``"proprietary_calibrated"`` — driven by paid / expert data
  (v3 territory; private repo only).

Stochasticity vocabulary
------------------------

``MechanismSpec.stochasticity`` follows
:data:`STOCHASTICITY_LABELS`:

- ``"deterministic"`` — given the same input, same output.
- ``"pinned_seed"`` — randomness derived from a declared seed,
  reproducible byte-for-byte.
- ``"open_seed"`` — non-reproducible randomness. Forbidden in
  v1.x deterministic-replay milestones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable


# Canonical labels reserved by v1.9.3 / v1.9.3.1. Concrete
# mechanisms in v1.9.4+ are encouraged to use these strings so the
# inventory tooling can group them; free-form values are still
# permitted.
MECHANISM_FAMILIES: tuple[str, ...] = (
    "firm_financial_mechanism",
    "valuation_mechanism",
    "credit_review_mechanism",
    "investor_intent_mechanism",
    "market_mechanism",
    "macro_process_mechanism",
)

CALIBRATION_STATUSES: tuple[str, ...] = (
    "synthetic",
    "public_data_calibrated",
    "proprietary_calibrated",
)

STOCHASTICITY_LABELS: tuple[str, ...] = (
    "deterministic",
    "pinned_seed",
    "open_seed",
)


# ---------------------------------------------------------------------------
# v1.9.3.1 Deep-ish freeze for JSON-like data
# ---------------------------------------------------------------------------


def _freeze_json_like(value: Any) -> Any:
    """Recursively freeze a JSON-like value so audit / replay
    downstream of a mechanism's input or output cannot mutate it
    in place.

    - ``Mapping`` → ``MappingProxyType`` (read-only view)
    - ``list`` / ``tuple`` → ``tuple``
    - ``set`` / ``frozenset`` → ``tuple`` (sorted by stable str
      repr when items are heterogeneous so ordering is
      deterministic across processes)
    - scalar (``None`` / ``bool`` / ``int`` / ``float`` / ``str``)
      → returned as-is

    Anything not in those categories (e.g., a custom object) is
    returned unchanged. Mechanisms that want strict JSON-only
    inputs should validate at the call site; the helper is
    permissive on purpose so v1.9.4+ adapters can carry small
    typed sub-records.
    """
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(k): _freeze_json_like(v) for k, v in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_like(v) for v in value)
    if isinstance(value, (set, frozenset)):
        try:
            ordered = sorted(value, key=lambda item: (type(item).__name__, str(item)))
        except TypeError:
            ordered = list(value)
        return tuple(_freeze_json_like(v) for v in ordered)
    return value


def _thaw_json_like(value: Any) -> Any:
    """Recursively undo :func:`_freeze_json_like`. Returns regular
    mutable ``dict`` / ``list`` copies suitable for JSON
    serialization or caller-side mutation.

    A mechanism's ``to_dict`` always returns thawed copies — the
    frozen views are an *internal storage* property, not a
    serialization shape.
    """
    if isinstance(value, Mapping):
        return {str(k): _thaw_json_like(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_json_like(v) for v in value]
    if isinstance(value, (set, frozenset)):
        try:
            ordered = sorted(value, key=lambda item: (type(item).__name__, str(item)))
        except TypeError:
            ordered = list(value)
        return [_thaw_json_like(v) for v in ordered]
    return value


# ---------------------------------------------------------------------------
# MechanismSpec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MechanismSpec:
    """
    Declarative description of a mechanism.

    A spec is **data**: it carries no behavior. Concrete
    mechanisms ship a spec instance plus an
    :class:`MechanismAdapter` that interprets inputs against the
    spec. Two adapters with byte-identical specs must produce
    byte-identical outputs on byte-identical inputs (the
    deterministic-replay invariant).

    v1.9.3.1: ``metadata`` is now stored deeply frozen; nested
    dicts inside ``metadata`` are read-only.

    Field semantics
    ---------------
    - ``model_id`` is a stable, unique id for this mechanism.
      Suggested format: ``"mechanism:<family>:<short_label>"``.
    - ``model_family`` names the broad mechanism family
      (suggested values in :data:`MECHANISM_FAMILIES`).
    - ``version`` is a free-form version string.
    - ``assumptions`` is a tuple of free-form strings.
    - ``calibration_status`` follows :data:`CALIBRATION_STATUSES`.
    - ``stochasticity`` follows :data:`STOCHASTICITY_LABELS`.
    - ``required_inputs`` is a tuple naming the input record
      types the adapter expects.
    - ``output_types`` is a tuple naming the proposed-record
      types the adapter emits.
    - ``metadata`` is free-form, deeply frozen.
    """

    model_id: str
    model_family: str
    version: str
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    calibration_status: str = "synthetic"
    stochasticity: str = "deterministic"
    required_inputs: tuple[str, ...] = field(default_factory=tuple)
    output_types: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("model_id", "model_family", "version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{name} is required and must be a non-empty string"
                )
        if not isinstance(self.calibration_status, str) or not self.calibration_status:
            raise ValueError("calibration_status is required")
        if not isinstance(self.stochasticity, str) or not self.stochasticity:
            raise ValueError("stochasticity is required")

        for tuple_field_name in (
            "assumptions",
            "required_inputs",
            "output_types",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)

        object.__setattr__(self, "metadata", _freeze_json_like(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_family": self.model_family,
            "version": self.version,
            "assumptions": list(self.assumptions),
            "calibration_status": self.calibration_status,
            "stochasticity": self.stochasticity,
            "required_inputs": list(self.required_inputs),
            "output_types": list(self.output_types),
            "metadata": _thaw_json_like(self.metadata),
        }


# ---------------------------------------------------------------------------
# MechanismRunRequest (v1.9.3.1; replaces MechanismInputBundle)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MechanismRunRequest:
    """
    One resolved mechanism invocation prepared by the caller.

    v1.9.3.1 introduces this type to make the contract between
    caller and adapter explicit:

    - The **caller** resolves refs from kernel books into
      ``evidence_refs`` (the lineage / id list) and ``evidence``
      (the resolved data, grouped by record type or logical key)
      *before* calling ``apply``.
    - The **adapter** reads ``evidence``; it does **not** access
      the kernel, any book, or the ledger. v1.9.4+ tests pin
      this property by passing adapters a request constructed
      without a kernel.

    ``evidence_refs`` is a *deterministic lineage* tuple — the
    caller may dedupe / order it however it wants, but the
    request stores it verbatim. ``evidence`` is the resolved
    data the adapter reads; its keys are usually record-type
    names (``"InformationSignal"``, ``"VariableObservation"``,
    ``"ExposureRecord"``) but free-form logical keys are allowed.

    Field semantics
    ---------------
    - ``request_id`` is a stable id for this invocation.
    - ``model_id`` echoes the spec.
    - ``actor_id`` is the actor on whose behalf the mechanism is
      running.
    - ``as_of_date`` is ISO ``YYYY-MM-DD``.
    - ``selected_observation_set_ids`` is a tuple of
      :class:`SelectedObservationSet` ids the mechanism may
      consume (resolved separately from ``evidence_refs`` so the
      adapter can correlate selections with their refs).
    - ``evidence_refs`` is the caller-resolved tuple of record
      ids that flow through this run. Stored verbatim; no
      auto-dedup, no auto-sort.
    - ``evidence`` is a deeply-frozen mapping of resolved input
      data (record type / logical key → list of records or
      sub-dicts).
    - ``state_views`` is a mapping from a logical name to a
      deterministic state snapshot (e.g., a balance-sheet view).
      Deeply frozen.
    - ``parameters`` is a free-form deeply-frozen mapping.
    - ``metadata`` is a free-form deeply-frozen mapping.

    Backwards-compat: ``MechanismInputBundle`` is aliased to
    ``MechanismRunRequest`` for one milestone so code that imported
    the old name still loads. The alias does **not** restore the
    old field set — code using ``input_refs=...`` must update to
    ``evidence_refs=...``.
    """

    request_id: str
    model_id: str
    actor_id: str
    as_of_date: str
    selected_observation_set_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    evidence: Mapping[str, Any] = field(default_factory=dict)
    state_views: Mapping[str, Any] = field(default_factory=dict)
    parameters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("request_id", "model_id", "actor_id", "as_of_date"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{name} is required and must be a non-empty string"
                )

        for tuple_field_name in (
            "selected_observation_set_ids",
            "evidence_refs",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)

        # `evidence` keys must be non-empty strings. Values are
        # deeply frozen but otherwise free-form.
        if not isinstance(self.evidence, Mapping):
            raise ValueError(
                f"evidence must be a Mapping; got {type(self.evidence).__name__}"
            )
        for k in dict(self.evidence).keys():
            if not isinstance(k, str) or not k:
                raise ValueError("evidence keys must be non-empty strings")

        object.__setattr__(self, "evidence", _freeze_json_like(self.evidence))
        object.__setattr__(self, "state_views", _freeze_json_like(self.state_views))
        object.__setattr__(self, "parameters", _freeze_json_like(self.parameters))
        object.__setattr__(self, "metadata", _freeze_json_like(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "actor_id": self.actor_id,
            "as_of_date": self.as_of_date,
            "selected_observation_set_ids": list(
                self.selected_observation_set_ids
            ),
            "evidence_refs": list(self.evidence_refs),
            "evidence": _thaw_json_like(self.evidence),
            "state_views": _thaw_json_like(self.state_views),
            "parameters": _thaw_json_like(self.parameters),
            "metadata": _thaw_json_like(self.metadata),
        }


# Backwards-compat alias (kept for one milestone). The alias does
# not restore the old field set; code using ``input_refs=...``
# must rename to ``evidence_refs=...``.
MechanismInputBundle = MechanismRunRequest


# ---------------------------------------------------------------------------
# MechanismOutputBundle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MechanismOutputBundle:
    """
    Typed output bundle from one mechanism call.

    The bundle carries **proposals**, not commits. The caller
    chooses which proposals (if any) to write through to a book.

    v1.9.3.1: every nested mapping in the proposal tuples plus
    ``output_summary`` and ``metadata`` is deeply frozen.

    Status vocabulary (suggested):

    - ``"completed"`` — inputs flowed through cleanly.
    - ``"degraded"`` — some inputs were missing or empty (the
      v1.8.1 anti-scenario rule).
    - ``"skipped"`` — adapter chose not to run.
    - ``"failed"`` — hard error (mechanisms should prefer
      ``"degraded"``).
    """

    request_id: str
    model_id: str
    status: str = "completed"
    proposed_signals: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    proposed_valuation_records: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )
    proposed_constraint_pressure_deltas: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )
    proposed_intent_records: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )
    proposed_run_records: tuple[Mapping[str, Any], ...] = field(
        default_factory=tuple
    )
    output_summary: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("request_id", "model_id", "status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{name} is required and must be a non-empty string"
                )

        for tuple_field_name in (
            "proposed_signals",
            "proposed_valuation_records",
            "proposed_constraint_pressure_deltas",
            "proposed_intent_records",
            "proposed_run_records",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, Mapping):
                    raise ValueError(
                        f"{tuple_field_name} entries must be Mapping[str, Any]"
                    )
            # Each proposal is deeply frozen so audit / replay
            # downstream cannot mutate the proposed record by
            # subscript-assign on a nested dict.
            normalised = tuple(_freeze_json_like(entry) for entry in value)
            object.__setattr__(self, tuple_field_name, normalised)

        warnings_value = tuple(self.warnings)
        for entry in warnings_value:
            if not isinstance(entry, str) or not entry:
                raise ValueError("warnings entries must be non-empty strings")
        object.__setattr__(self, "warnings", warnings_value)

        object.__setattr__(self, "output_summary", _freeze_json_like(self.output_summary))
        object.__setattr__(self, "metadata", _freeze_json_like(self.metadata))

    @property
    def total_proposed_count(self) -> int:
        return (
            len(self.proposed_signals)
            + len(self.proposed_valuation_records)
            + len(self.proposed_constraint_pressure_deltas)
            + len(self.proposed_intent_records)
            + len(self.proposed_run_records)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "status": self.status,
            "proposed_signals": [_thaw_json_like(e) for e in self.proposed_signals],
            "proposed_valuation_records": [
                _thaw_json_like(e) for e in self.proposed_valuation_records
            ],
            "proposed_constraint_pressure_deltas": [
                _thaw_json_like(e) for e in self.proposed_constraint_pressure_deltas
            ],
            "proposed_intent_records": [
                _thaw_json_like(e) for e in self.proposed_intent_records
            ],
            "proposed_run_records": [
                _thaw_json_like(e) for e in self.proposed_run_records
            ],
            "output_summary": _thaw_json_like(self.output_summary),
            "warnings": list(self.warnings),
            "metadata": _thaw_json_like(self.metadata),
        }


# ---------------------------------------------------------------------------
# MechanismRunRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MechanismRunRecord:
    """
    Append-only audit record of one mechanism invocation.

    v1.9.3.1: ``metadata`` is deeply frozen.

    Ordering responsibility
    -----------------------

    ``input_refs`` and ``committed_output_refs`` are stored
    **verbatim** in caller-supplied order. v1.9.3.1 does **not**:

    - dedupe entries;
    - sort entries;
    - reject duplicates.

    Callers that need deterministic replay must order / dedupe
    their tuples themselves before constructing the record. Some
    mechanisms intentionally carry meaningful order (a sequence
    of revisions, a temporal trail of inputs); v1.9.3.1 declines
    to second-guess them. The contract test in
    ``tests/test_mechanism_interface.py`` pins the
    "preserve verbatim" property.

    Field semantics
    ---------------
    - ``run_id`` is the stable id of the run. Suggested formula:
      ``"mechanism_run:" + request_id``.
    - ``request_id`` mirrors the request.
    - ``model_id`` / ``model_family`` / ``version`` echo the
      spec.
    - ``actor_id`` echoes the request.
    - ``as_of_date`` echoes the request.
    - ``input_summary_hash`` and ``output_summary_hash`` are
      free-form opaque digest strings if the caller computed
      them.
    - ``input_refs`` is the caller-resolved tuple of input
      record ids the mechanism actually consumed (verbatim
      order).
    - ``committed_output_refs`` is the tuple of record ids the
      caller wrote to its books after consuming
      :class:`MechanismOutputBundle` (verbatim order).
    - ``status`` mirrors the output bundle.
    - ``parent_record_ids`` lets the run point back to upstream
      records.
    - ``metadata`` is free-form, deeply frozen.
    """

    run_id: str
    request_id: str
    model_id: str
    model_family: str
    version: str
    actor_id: str
    as_of_date: str
    status: str = "completed"
    input_refs: tuple[str, ...] = field(default_factory=tuple)
    committed_output_refs: tuple[str, ...] = field(default_factory=tuple)
    parent_record_ids: tuple[str, ...] = field(default_factory=tuple)
    input_summary_hash: str | None = None
    output_summary_hash: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "run_id",
            "request_id",
            "model_id",
            "model_family",
            "version",
            "actor_id",
            "as_of_date",
            "status",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{name} is required and must be a non-empty string"
                )

        for tuple_field_name in (
            "input_refs",
            "committed_output_refs",
            "parent_record_ids",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            # Preserve verbatim caller-supplied order. No dedupe,
            # no sort — see the docstring's "Ordering
            # responsibility" section.
            object.__setattr__(self, tuple_field_name, value)

        for hash_field_name in ("input_summary_hash", "output_summary_hash"):
            value = getattr(self, hash_field_name)
            if value is not None and not (isinstance(value, str) and value):
                raise ValueError(
                    f"{hash_field_name} must be a non-empty string or None"
                )

        object.__setattr__(self, "metadata", _freeze_json_like(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "model_id": self.model_id,
            "model_family": self.model_family,
            "version": self.version,
            "actor_id": self.actor_id,
            "as_of_date": self.as_of_date,
            "status": self.status,
            "input_refs": list(self.input_refs),
            "committed_output_refs": list(self.committed_output_refs),
            "parent_record_ids": list(self.parent_record_ids),
            "input_summary_hash": self.input_summary_hash,
            "output_summary_hash": self.output_summary_hash,
            "metadata": _thaw_json_like(self.metadata),
        }


# ---------------------------------------------------------------------------
# MechanismAdapter Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class MechanismAdapter(Protocol):
    """
    The Protocol that v1.9.4+ concrete mechanisms implement.

    An adapter is an object exposing a :class:`MechanismSpec`
    and an ``apply`` method that takes a
    :class:`MechanismRunRequest` and returns a
    :class:`MechanismOutputBundle` of proposals.

    Adapter contract (v1.9.3.1):

    - The adapter must **not** mutate the request. The request's
      nested mappings / sequences are deeply frozen;
      subscript-assign on any nested dict raises ``TypeError``.
    - The adapter must **not** read the kernel, any book, or the
      ledger. The caller resolves refs into ``request.evidence``
      *before* invocation; the adapter computes proposals from
      ``request.evidence`` alone.
    - The adapter must **not** commit any proposal. The caller
      decides which (if any) of the returned proposals to write
      through to a book.
    - The adapter must return proposals only.

    The Protocol is ``runtime_checkable`` so tests can assert
    ``isinstance(adapter, MechanismAdapter)``. The check is
    structural — any class with a ``spec`` attribute and an
    ``apply`` method satisfies it.
    """

    spec: MechanismSpec

    def apply(
        self, request: MechanismRunRequest
    ) -> MechanismOutputBundle: ...
