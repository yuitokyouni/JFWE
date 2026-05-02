"""
v1.9.1 Living World Trace Report.

A read-only reporting layer over the v1.9.0 multi-period living
reference world. Turns a ``LivingReferenceWorldResult`` plus the
matching slice of ``kernel.ledger.records`` into:

- a deterministic, immutable :class:`LivingWorldTraceReport`,
- a deterministic dict via :meth:`LivingWorldTraceReport.to_dict`,
  and
- a deterministic compact Markdown rendering via
  :func:`render_living_world_markdown`.

The reporter exists for **explainability**, not modeling. It
introduces no new ledger types, no new economic behavior, no new
routines, no scheduler hooks, no kernel mutation. Every walk over
``kernel.ledger.records`` and every read on
``kernel.attention.get_selection(...)`` is read-only.

Relationship to v1.8.15
-----------------------

This module mirrors `world/ledger_trace_report.py` (the v1.8.15
single-chain reporter) for the v1.9.0 multi-period sweep. The
design contract was audited in v1.9.1-prep and lives in
``docs/v1_9_living_world_report_contract.md``; v1.9.1 implements
that contract.

The infra prelude
-----------------

v1.9.0's ``run_living_reference_world`` does idempotent
registration (interactions + per-firm corporate routines + per-
actor profiles + review interactions + review routines)
**before** entering the period loop. Those writes form an
**infra prelude** between
``result.ledger_record_count_before`` and
``per_period_summaries[0].metadata["ledger_record_count_before"]``.
The reporter computes ``infra_record_count`` from the algebraic
relationship pinned in v1.9.1-prep:

    infra_record_count
        = result.created_record_count
            - sum(p.record_count_created for p in per_period_summaries)

and surfaces it separately in the Setup section so the per-period
table's totals add up honestly.

Determinism
-----------

For a given (kernel, living_world_result) pair, the report and
its ``to_dict`` / Markdown projections are byte-identical across
fresh process invocations. The reporter:

- sorts `record_type_counts` by event type;
- preserves ledger order in `ordered_record_ids` and the
  per-period `corporate_signal_ids` / review-signal id tuples;
- sorts `shared_selected_refs` / `investor_only_refs` /
  `bank_only_refs` alphabetically (set differences have no
  natural order, so we pick a stable one);
- sorts `investor_selected_ref_counts` and
  `bank_selected_ref_counts` by `(period_id, actor_id)`.

No timestamps, no wall-clock dependencies, no floating-point
accumulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from world.ledger import RecordType
from world.reference_living_world import (
    LivingReferencePeriodSummary,
    LivingReferenceWorldResult,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


_DEFAULT_CHAIN_NAME: str = "living_reference_world"


# The seven event types the v1.9.0 sweep emits across the infra
# prelude and the period loop. Used by the validation pass to flag
# missing components without crashing.
_EXPECTED_LIVING_WORLD_EVENT_TYPES: tuple[str, ...] = (
    RecordType.INTERACTION_ADDED.value,
    RecordType.ROUTINE_ADDED.value,
    RecordType.ROUTINE_RUN_RECORDED.value,
    RecordType.SIGNAL_ADDED.value,
    RecordType.ATTENTION_PROFILE_ADDED.value,
    RecordType.OBSERVATION_MENU_CREATED.value,
    RecordType.OBSERVATION_SET_SELECTED.value,
)


# Hard-boundary statement. Emitted verbatim under the
# `## Boundaries` section of the Markdown report. Per the v1.9.1
# task spec; expanded from the v1.9.1-prep draft to include
# "no investment advice".
_BOUNDARY_STATEMENT: str = (
    "No price formation, no trading, no lending decisions, "
    "no valuation behavior, no Japan calibration, no real data, "
    "no investment advice."
)


# ---------------------------------------------------------------------------
# Per-period report record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LivingWorldPeriodReport:
    """
    Immutable summary of one living-world period as projected into
    the report.

    Mirrors ``LivingReferencePeriodSummary`` plus per-period event-
    type counts and any per-period warnings the reporter detected.
    Counts derived from collections (``record_type_counts``) are
    sorted for determinism; ledger-order tuples
    (``corporate_signal_ids`` / review-signal id tuples) preserve
    the order each component helper wrote them in.
    """

    period_id: str
    as_of_date: str
    record_count_created: int
    corporate_report_count: int
    corporate_signal_ids: tuple[str, ...]
    investor_menu_count: int
    bank_menu_count: int
    investor_selection_count: int
    bank_selection_count: int
    investor_review_count: int
    bank_review_count: int
    investor_review_signal_ids: tuple[str, ...]
    bank_review_signal_ids: tuple[str, ...]
    record_type_counts: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.period_id, str) or not self.period_id:
            raise ValueError("period_id must be a non-empty string")
        if not isinstance(self.as_of_date, str) or not self.as_of_date:
            raise ValueError("as_of_date must be a non-empty string")
        for name in (
            "record_count_created",
            "corporate_report_count",
            "investor_menu_count",
            "bank_menu_count",
            "investor_selection_count",
            "bank_selection_count",
            "investor_review_count",
            "bank_review_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"{name} must be a non-negative int; got {value!r}"
                )

        for tuple_field_name in (
            "corporate_signal_ids",
            "investor_review_signal_ids",
            "bank_review_signal_ids",
            "warnings",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)

        normalized_counts: list[tuple[str, int]] = []
        for entry in self.record_type_counts:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or not entry[0]
                or not isinstance(entry[1], int)
                or entry[1] < 0
            ):
                raise ValueError(
                    "record_type_counts entries must be (non-empty str, "
                    f"non-negative int); got {entry!r}"
                )
            normalized_counts.append((entry[0], entry[1]))
        object.__setattr__(
            self,
            "record_type_counts",
            tuple(sorted(normalized_counts)),
        )

        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_id": self.period_id,
            "as_of_date": self.as_of_date,
            "record_count_created": self.record_count_created,
            "corporate_report_count": self.corporate_report_count,
            "corporate_signal_ids": list(self.corporate_signal_ids),
            "investor_menu_count": self.investor_menu_count,
            "bank_menu_count": self.bank_menu_count,
            "investor_selection_count": self.investor_selection_count,
            "bank_selection_count": self.bank_selection_count,
            "investor_review_count": self.investor_review_count,
            "bank_review_count": self.bank_review_count,
            "investor_review_signal_ids": list(self.investor_review_signal_ids),
            "bank_review_signal_ids": list(self.bank_review_signal_ids),
            "record_type_counts": [
                [event_type, count]
                for event_type, count in self.record_type_counts
            ],
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Aggregate report record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LivingWorldTraceReport:
    """
    Immutable aggregate report over one ``LivingReferenceWorldResult``.

    Field semantics
    ---------------
    - ``report_id`` is a stable id derived from the chain. Default
      is ``"report:living_reference_world:" + run_id``; the caller
      may override.
    - ``run_id`` mirrors the result.
    - ``period_count``, ``firm_count``, ``investor_count``,
      ``bank_count`` are setup-summary integers.
    - ``ledger_record_count_before`` / ``ledger_record_count_after``
      mirror the result so the slice can be re-walked from the
      report alone.
    - ``created_record_count`` is the total ledger delta.
    - ``infra_record_count`` is computed from the v1.9.1-prep
      algebraic relationship.
    - ``per_period_record_count_total`` is
      ``sum(p.record_count_created)`` and is provided so the
      Markdown's per-period totals row is reachable from the
      report alone.
    - ``record_type_counts`` is the **overall** ledger-slice
      event-type breakdown, sorted by event type.
    - ``period_summaries`` carries one
      :class:`LivingWorldPeriodReport` per period, in input order.
    - ``investor_selected_ref_counts`` and
      ``bank_selected_ref_counts`` are tuples of
      ``(actor_id, period_id, selected_ref_count)`` triples sorted
      by ``(period_id, actor_id)``.
    - ``shared_selected_refs`` / ``investor_only_refs`` /
      ``bank_only_refs`` are aggregated set differences over the
      union of investor selections and the union of bank selections
      across all periods. Sorted alphabetically for determinism.
    - ``ordered_record_ids`` is the ledger slice's ``object_id``
      tuple in ledger order (matches
      ``LivingReferenceWorldResult.created_record_ids`` when the
      ledger has not been touched).
    - ``warnings`` is a tuple of free-form strings for
      non-fatal validation issues.
    - ``metadata`` carries audit fields (renderer version, format
      version, the boundary statement, echoed counts).
    """

    report_id: str
    run_id: str
    period_count: int
    firm_count: int
    investor_count: int
    bank_count: int
    ledger_record_count_before: int
    ledger_record_count_after: int
    created_record_count: int
    infra_record_count: int
    per_period_record_count_total: int
    record_type_counts: tuple[tuple[str, int], ...]
    period_summaries: tuple[LivingWorldPeriodReport, ...]
    investor_selected_ref_counts: tuple[tuple[str, str, int], ...] = field(
        default_factory=tuple
    )
    bank_selected_ref_counts: tuple[tuple[str, str, int], ...] = field(
        default_factory=tuple
    )
    shared_selected_refs: tuple[str, ...] = field(default_factory=tuple)
    investor_only_refs: tuple[str, ...] = field(default_factory=tuple)
    bank_only_refs: tuple[str, ...] = field(default_factory=tuple)
    ordered_record_ids: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.report_id, str) or not self.report_id:
            raise ValueError("report_id must be a non-empty string")
        if not isinstance(self.run_id, str) or not self.run_id:
            raise ValueError("run_id must be a non-empty string")
        for name in (
            "period_count",
            "firm_count",
            "investor_count",
            "bank_count",
            "ledger_record_count_before",
            "ledger_record_count_after",
            "created_record_count",
            "infra_record_count",
            "per_period_record_count_total",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"{name} must be a non-negative int; got {value!r}"
                )

        if (
            self.ledger_record_count_after - self.ledger_record_count_before
            != self.created_record_count
        ):
            raise ValueError(
                "ledger_record_count_after - ledger_record_count_before must "
                "equal created_record_count"
            )
        if (
            self.infra_record_count + self.per_period_record_count_total
            != self.created_record_count
        ):
            raise ValueError(
                "infra_record_count + per_period_record_count_total must "
                "equal created_record_count"
            )
        if len(self.period_summaries) != self.period_count:
            raise ValueError(
                "period_summaries length must equal period_count"
            )

        for tuple_field_name in (
            "shared_selected_refs",
            "investor_only_refs",
            "bank_only_refs",
            "ordered_record_ids",
            "warnings",
        ):
            value = tuple(getattr(self, tuple_field_name))
            for entry in value:
                if not isinstance(entry, str) or not entry:
                    raise ValueError(
                        f"{tuple_field_name} entries must be non-empty strings"
                    )
            object.__setattr__(self, tuple_field_name, value)

        normalized_overall_counts: list[tuple[str, int]] = []
        for entry in self.record_type_counts:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or not entry[0]
                or not isinstance(entry[1], int)
                or entry[1] < 0
            ):
                raise ValueError(
                    "record_type_counts entries must be (non-empty str, "
                    f"non-negative int); got {entry!r}"
                )
            normalized_overall_counts.append((entry[0], entry[1]))
        object.__setattr__(
            self,
            "record_type_counts",
            tuple(sorted(normalized_overall_counts)),
        )

        for triple_field_name in (
            "investor_selected_ref_counts",
            "bank_selected_ref_counts",
        ):
            value = tuple(getattr(self, triple_field_name))
            for entry in value:
                if (
                    not isinstance(entry, tuple)
                    or len(entry) != 3
                    or not isinstance(entry[0], str)
                    or not entry[0]
                    or not isinstance(entry[1], int)
                    or entry[1] < 0
                ):
                    # entry[1] is the period_id (str), entry[2] is the count.
                    pass  # will re-check below with correct indices.
            normalized_triples: list[tuple[str, str, int]] = []
            for entry in value:
                if (
                    not isinstance(entry, tuple)
                    or len(entry) != 3
                    or not isinstance(entry[0], str)
                    or not entry[0]
                    or not isinstance(entry[1], str)
                    or not entry[1]
                    or not isinstance(entry[2], int)
                    or entry[2] < 0
                ):
                    raise ValueError(
                        f"{triple_field_name} entries must be "
                        "(actor_id, period_id, non-negative int); "
                        f"got {entry!r}"
                    )
                normalized_triples.append((entry[0], entry[1], entry[2]))
            object.__setattr__(
                self,
                triple_field_name,
                tuple(sorted(normalized_triples, key=lambda t: (t[1], t[0]))),
            )

        object.__setattr__(
            self,
            "period_summaries",
            tuple(self.period_summaries),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "run_id": self.run_id,
            "period_count": self.period_count,
            "firm_count": self.firm_count,
            "investor_count": self.investor_count,
            "bank_count": self.bank_count,
            "ledger_record_count_before": self.ledger_record_count_before,
            "ledger_record_count_after": self.ledger_record_count_after,
            "created_record_count": self.created_record_count,
            "infra_record_count": self.infra_record_count,
            "per_period_record_count_total": self.per_period_record_count_total,
            "record_type_counts": [
                [event_type, count]
                for event_type, count in self.record_type_counts
            ],
            "period_summaries": [ps.to_dict() for ps in self.period_summaries],
            "investor_selected_ref_counts": [
                [actor_id, period_id, count]
                for actor_id, period_id, count in self.investor_selected_ref_counts
            ],
            "bank_selected_ref_counts": [
                [actor_id, period_id, count]
                for actor_id, period_id, count in self.bank_selected_ref_counts
            ],
            "shared_selected_refs": list(self.shared_selected_refs),
            "investor_only_refs": list(self.investor_only_refs),
            "bank_only_refs": list(self.bank_only_refs),
            "ordered_record_ids": list(self.ordered_record_ids),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_living_world_trace_report(
    kernel: Any,
    living_world_result: LivingReferenceWorldResult,
    *,
    report_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> LivingWorldTraceReport:
    """
    Build a :class:`LivingWorldTraceReport` for ``living_world_result``
    by re-walking the kernel's ledger between
    ``ledger_record_count_before`` and
    ``ledger_record_count_after`` and reading the per-period
    selections through ``kernel.attention.get_selection``.

    Read-only: ``kernel`` is consulted but never mutated; no new
    ledger record is appended.

    Validation is permissive — slice / chain mismatches and missing
    expected event types yield non-fatal :attr:`warnings` strings
    rather than raising. v1.9.1 prefers "show what is there with
    warnings attached" over "refuse to render."
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(living_world_result, LivingReferenceWorldResult):
        raise TypeError(
            "living_world_result must be a LivingReferenceWorldResult; "
            f"got {type(living_world_result).__name__}"
        )
    if report_id is not None and not (
        isinstance(report_id, str) and report_id
    ):
        raise ValueError("report_id must be a non-empty string or None")

    start_idx = living_world_result.ledger_record_count_before
    end_idx = living_world_result.ledger_record_count_after
    if start_idx < 0 or end_idx < start_idx:
        raise ValueError(
            "living_world_result has invalid ledger indices "
            f"(start={start_idx}, end={end_idx})"
        )

    ledger_records = kernel.ledger.records
    safe_end = min(end_idx, len(ledger_records))
    slice_records = list(ledger_records[start_idx:safe_end])
    record_count = len(slice_records)

    warnings: list[str] = []
    if safe_end != end_idx:
        warnings.append(
            f"living_world_result claims end_record_index={end_idx} but "
            f"kernel.ledger.records has length {len(ledger_records)}; "
            f"slice truncated to {safe_end}"
        )

    # Overall ordered_record_ids + record_type_counts.
    ordered_record_ids: list[str] = []
    overall_counts: dict[str, int] = {}
    for record in slice_records:
        oid = record.object_id
        event_type = record.record_type.value
        overall_counts[event_type] = overall_counts.get(event_type, 0) + 1
        if isinstance(oid, str) and oid:
            ordered_record_ids.append(oid)

    expected_count = living_world_result.created_record_count
    if record_count != expected_count:
        warnings.append(
            f"ledger slice length ({record_count}) does not match "
            f"living_world_result.created_record_count ({expected_count})"
        )
    if (
        tuple(r.object_id for r in slice_records)
        != living_world_result.created_record_ids
    ):
        warnings.append(
            "ledger slice object_ids do not match "
            "living_world_result.created_record_ids"
        )

    seen_event_types = set(overall_counts.keys())
    for expected in _EXPECTED_LIVING_WORLD_EVENT_TYPES:
        if expected not in seen_event_types:
            warnings.append(f"expected event type missing: {expected}")

    # Sum to record_count cross-check.
    counts_sum = sum(overall_counts.values())
    if counts_sum != record_count:
        warnings.append(
            f"record_type_counts sum ({counts_sum}) does not match "
            f"slice length ({record_count})"
        )

    # Per-period reports.
    period_summaries: list[LivingWorldPeriodReport] = []
    for period in living_world_result.per_period_summaries:
        period_summary, period_warnings = _build_period_report(
            kernel, period, ledger_records=ledger_records
        )
        period_summaries.append(period_summary)
        for w in period_warnings:
            warnings.append(w)

    # Per-period record-count-created total + infra algebra.
    per_period_total = sum(
        period.record_count_created
        for period in living_world_result.per_period_summaries
    )
    infra_record_count = living_world_result.created_record_count - per_period_total
    if infra_record_count < 0:
        warnings.append(
            "infra_record_count is negative — per-period totals "
            f"({per_period_total}) exceed chain delta "
            f"({living_world_result.created_record_count})"
        )
        infra_record_count = 0

    # Attention divergence aggregated across all periods.
    investor_union: set[str] = set()
    bank_union: set[str] = set()
    investor_counts: list[tuple[str, str, int]] = []
    bank_counts: list[tuple[str, str, int]] = []

    for period in living_world_result.per_period_summaries:
        for sel_id in period.investor_selection_ids:
            actor_id, refs = _read_selection_refs(kernel, sel_id)
            if actor_id is None:
                warnings.append(
                    f"period {period.period_id}: investor selection "
                    f"{sel_id} does not resolve to a stored selection"
                )
                continue
            investor_union.update(refs)
            investor_counts.append((actor_id, period.period_id, len(refs)))
            if not refs:
                warnings.append(
                    f"period {period.period_id}: investor selection "
                    f"{sel_id} has zero refs"
                )
        for sel_id in period.bank_selection_ids:
            actor_id, refs = _read_selection_refs(kernel, sel_id)
            if actor_id is None:
                warnings.append(
                    f"period {period.period_id}: bank selection "
                    f"{sel_id} does not resolve to a stored selection"
                )
                continue
            bank_union.update(refs)
            bank_counts.append((actor_id, period.period_id, len(refs)))
            if not refs:
                warnings.append(
                    f"period {period.period_id}: bank selection "
                    f"{sel_id} has zero refs"
                )

    shared = sorted(investor_union & bank_union)
    investor_only = sorted(investor_union - bank_union)
    bank_only = sorted(bank_union - investor_union)

    rid = report_id or f"report:living_reference_world:{living_world_result.run_id}"

    final_metadata = {
        "renderer": "v1.9.1",
        "format_version": "1",
        "boundary_statement": _BOUNDARY_STATEMENT,
        "run_id": living_world_result.run_id,
        "firm_ids": list(living_world_result.firm_ids),
        "investor_ids": list(living_world_result.investor_ids),
        "bank_ids": list(living_world_result.bank_ids),
        "claimed_end_record_index": end_idx,
    }
    if metadata:
        final_metadata.update(dict(metadata))

    return LivingWorldTraceReport(
        report_id=rid,
        run_id=living_world_result.run_id,
        period_count=living_world_result.period_count,
        firm_count=len(living_world_result.firm_ids),
        investor_count=len(living_world_result.investor_ids),
        bank_count=len(living_world_result.bank_ids),
        ledger_record_count_before=start_idx,
        # Bound end_record_index to the actual slice we read.
        ledger_record_count_after=start_idx + record_count,
        created_record_count=record_count,
        # Recompute infra from the slice we actually read; if the
        # slice was truncated this stays internally consistent.
        infra_record_count=max(record_count - per_period_total, 0),
        per_period_record_count_total=per_period_total,
        record_type_counts=tuple(sorted(overall_counts.items())),
        period_summaries=tuple(period_summaries),
        investor_selected_ref_counts=tuple(investor_counts),
        bank_selected_ref_counts=tuple(bank_counts),
        shared_selected_refs=tuple(shared),
        investor_only_refs=tuple(investor_only),
        bank_only_refs=tuple(bank_only),
        ordered_record_ids=tuple(ordered_record_ids),
        warnings=tuple(warnings),
        metadata=final_metadata,
    )


def _build_period_report(
    kernel: Any,
    period: LivingReferencePeriodSummary,
    *,
    ledger_records,
) -> tuple[LivingWorldPeriodReport, list[str]]:
    """Build the per-period report. Returns the immutable record
    plus any warning strings detected for this period."""
    period_warnings: list[str] = []

    period_before = period.metadata.get("ledger_record_count_before")
    period_after = period.metadata.get("ledger_record_count_after")
    period_record_type_counts: tuple[tuple[str, int], ...] = ()

    if isinstance(period_before, int) and isinstance(period_after, int):
        safe_period_after = min(period_after, len(ledger_records))
        period_slice = list(ledger_records[period_before:safe_period_after])
        per_period_counts: dict[str, int] = {}
        for record in period_slice:
            event_type = record.record_type.value
            per_period_counts[event_type] = (
                per_period_counts.get(event_type, 0) + 1
            )
        period_record_type_counts = tuple(sorted(per_period_counts.items()))
        if len(period_slice) != period.record_count_created:
            period_warnings.append(
                f"period {period.period_id}: ledger slice length "
                f"({len(period_slice)}) does not match "
                f"record_count_created ({period.record_count_created})"
            )
    else:
        period_warnings.append(
            f"period {period.period_id}: metadata is missing "
            "ledger_record_count_before / ledger_record_count_after"
        )

    return (
        LivingWorldPeriodReport(
            period_id=period.period_id,
            as_of_date=period.as_of_date,
            record_count_created=period.record_count_created,
            corporate_report_count=len(period.corporate_signal_ids),
            corporate_signal_ids=period.corporate_signal_ids,
            investor_menu_count=len(period.investor_menu_ids),
            bank_menu_count=len(period.bank_menu_ids),
            investor_selection_count=len(period.investor_selection_ids),
            bank_selection_count=len(period.bank_selection_ids),
            investor_review_count=len(period.investor_review_run_ids),
            bank_review_count=len(period.bank_review_run_ids),
            investor_review_signal_ids=period.investor_review_signal_ids,
            bank_review_signal_ids=period.bank_review_signal_ids,
            record_type_counts=period_record_type_counts,
            warnings=tuple(period_warnings),
            metadata={
                "ledger_record_count_before": (
                    period_before if isinstance(period_before, int) else None
                ),
                "ledger_record_count_after": (
                    period_after if isinstance(period_after, int) else None
                ),
            },
        ),
        period_warnings,
    )


def _read_selection_refs(
    kernel: Any, selection_id: str
) -> tuple[str | None, tuple[str, ...]]:
    """Return (actor_id, selected_refs) for a stored selection,
    or (None, ()) if the id does not resolve."""
    try:
        sel = kernel.attention.get_selection(selection_id)
    except Exception:
        return None, ()
    return sel.actor_id, tuple(sel.selected_refs)


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def render_living_world_markdown(report: LivingWorldTraceReport) -> str:
    """
    Compact deterministic Markdown rendering of ``report``.

    Section layout is fixed: title → setup → infra prelude →
    per-period summary → attention divergence → ledger event-type
    counts → warnings → boundary statement. Two reports built from
    byte-identical living-world results render to byte-identical
    Markdown.
    """
    md = report.to_dict()
    lines: list[str] = []

    lines.append("# living_reference_world")
    lines.append("")

    # Setup summary.
    lines.append("## Setup")
    lines.append("")
    lines.append(f"- **report_id**: `{md['report_id']}`")
    lines.append(f"- **run_id**: `{md['run_id']}`")
    lines.append(f"- **period_count**: {md['period_count']}")
    lines.append(f"- **firms**: {md['firm_count']}")
    lines.append(f"- **investors**: {md['investor_count']}")
    lines.append(f"- **banks**: {md['bank_count']}")
    lines.append(
        f"- **ledger_slice**: `[{md['ledger_record_count_before']}, "
        f"{md['ledger_record_count_after']})` "
        f"({md['created_record_count']} records)"
    )
    lines.append("")

    # Infra prelude.
    lines.append("## Infra prelude")
    lines.append("")
    lines.append(
        f"- **infra_record_count**: {md['infra_record_count']} "
        "(idempotent registrations: interactions, per-firm corporate "
        "routines, per-actor profiles, review interactions, review routines)"
    )
    lines.append(
        f"- **per_period_record_count_total**: "
        f"{md['per_period_record_count_total']}"
    )
    lines.append(
        f"- **algebra check**: {md['infra_record_count']} + "
        f"{md['per_period_record_count_total']} = "
        f"{md['created_record_count']}"
    )
    lines.append("")

    # Per-period summary.
    lines.append("## Per-period summary")
    lines.append("")
    if md["period_summaries"]:
        lines.append(
            "| period | as_of_date | reports | inv_menus | bnk_menus | "
            "inv_sel | bnk_sel | inv_rev | bnk_rev | records |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        )
        for ps in md["period_summaries"]:
            lines.append(
                f"| `{ps['period_id']}` | `{ps['as_of_date']}` | "
                f"{ps['corporate_report_count']} | "
                f"{ps['investor_menu_count']} | "
                f"{ps['bank_menu_count']} | "
                f"{ps['investor_selection_count']} | "
                f"{ps['bank_selection_count']} | "
                f"{ps['investor_review_count']} | "
                f"{ps['bank_review_count']} | "
                f"{ps['record_count_created']} |"
            )
    else:
        lines.append("- _(none)_")
    lines.append("")

    # Attention divergence summary.
    lines.append("## Attention divergence")
    lines.append("")
    lines.append(
        f"- shared: {len(md['shared_selected_refs'])} | "
        f"investor_only: {len(md['investor_only_refs'])} | "
        f"bank_only: {len(md['bank_only_refs'])}"
    )
    lines.append("")
    lines.append("### Per-actor selected-ref counts")
    lines.append("")
    if md["investor_selected_ref_counts"]:
        for actor_id, period_id, count in md["investor_selected_ref_counts"]:
            lines.append(
                f"- investor `{actor_id}` @ `{period_id}`: "
                f"{count} ref(s)"
            )
    else:
        lines.append("- _(no investor selections)_")
    if md["bank_selected_ref_counts"]:
        for actor_id, period_id, count in md["bank_selected_ref_counts"]:
            lines.append(
                f"- bank `{actor_id}` @ `{period_id}`: {count} ref(s)"
            )
    else:
        lines.append("- _(no bank selections)_")
    lines.append("")
    if md["shared_selected_refs"]:
        lines.append("### Shared refs (across all periods)")
        lines.append("")
        for ref in md["shared_selected_refs"]:
            lines.append(f"- `{ref}`")
        lines.append("")
    if md["investor_only_refs"]:
        lines.append("### Investor-only refs (across all periods)")
        lines.append("")
        for ref in md["investor_only_refs"]:
            lines.append(f"- `{ref}`")
        lines.append("")
    if md["bank_only_refs"]:
        lines.append("### Bank-only refs (across all periods)")
        lines.append("")
        for ref in md["bank_only_refs"]:
            lines.append(f"- `{ref}`")
        lines.append("")

    # Ledger event-type counts.
    lines.append("## Ledger event-type counts")
    lines.append("")
    if md["record_type_counts"]:
        for event_type, count in md["record_type_counts"]:
            lines.append(f"- `{event_type}`: {count}")
    else:
        lines.append("- _(none)_")
    lines.append("")

    # Warnings.
    lines.append("## Warnings")
    lines.append("")
    if md["warnings"]:
        for warning in md["warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("- _(none)_")
    lines.append("")

    # Boundaries.
    lines.append("## Boundaries")
    lines.append("")
    lines.append(f"> {_BOUNDARY_STATEMENT}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
