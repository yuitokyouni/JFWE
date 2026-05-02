"""
v1.9.2 Living-world replay-determinism helpers.

Mirrors v1.7-era ``examples/reference_world/replay_utils.py`` for
the multi-period v1.9.0 sweep:

- :func:`canonicalize_living_world_result` returns a JSON-friendly
  dict that captures every structural fact about the run while
  excluding wall-clock fields and hash-derived ledger ids.
- :func:`living_world_digest` returns the hex SHA-256 of the
  canonical-form JSON.

What "structural" means here
----------------------------

The canonical view captures:

- run identity (run_id, period_count, actor count tuples);
- ledger slice metadata (before / after / created counts) plus
  the v1.9.1-prep infra-prelude algebra (`infra_record_count`
  + `per_period_record_count_total` == `created_record_count`);
- per-period summaries from the v1.9.0 result (period_id,
  as_of_date, the six primary count fields, the corporate /
  review-signal / menu / selection id tuples in ledger order);
- the kernel ledger slice projected through the v1.7-era
  volatile-field-removal rule (drop ``record_id`` and
  ``timestamp``; rewrite ``parent_record_ids`` into stable
  sequence indices relative to the slice);
- aggregated event-type counts (sorted) summing to
  `created_record_count`;
- aggregated attention divergence (`shared_selected_refs`,
  `investor_only_refs`, `bank_only_refs`) sorted alphabetically;
- per-actor selected-ref count triples sorted by
  `(period_id, actor_id)`;
- the v1.9.1 hard-boundary statement, embedded so a downstream
  consumer can verify the boundary discipline from the manifest
  alone.

What is NOT in the canonical view
---------------------------------

- ``record_id`` (hash-derived; depends on timestamp)
- ``timestamp`` (wall-clock)
- absolute file system paths
- raw ``parent_record_ids`` (rewritten as ``parent_sequences``)
- the v1.9.1 report's ``warnings`` (intended for human review;
  stable across deterministic runs but not part of the digest)
- the v1.9.1 report's ``metadata.renderer`` / ``format_version``
  (not part of the run's structural identity)

Two runs of the canonical living-world demo on the same code
revision must produce ``canonicalize_living_world_result(...) ==
canonicalize_living_world_result(...)`` and identical
``living_world_digest(...)``.

Read-only
---------

Both helpers read from the kernel without mutating any book or
the ledger. Tests pin this in `tests/test_living_world_replay.py`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from world.reference_living_world import (
    LivingReferencePeriodSummary,
    LivingReferenceWorldResult,
)


# Must match the verbatim string emitted by the v1.9.1 reporter
# (`world/living_world_report.py::_BOUNDARY_STATEMENT`). A test
# in `tests/test_living_world_replay.py` pins the equality so a
# drift in either copy fails loudly.
LIVING_WORLD_BOUNDARY_STATEMENT: str = (
    "No price formation, no trading, no lending decisions, "
    "no valuation behavior, no Japan calibration, no real data, "
    "no investment advice."
)

CANONICAL_FORMAT_VERSION: str = "living_world_canonical.v1"


_VOLATILE_LEDGER_FIELDS: tuple[str, ...] = ("record_id", "timestamp")


# ---------------------------------------------------------------------------
# JSON normalisation
# ---------------------------------------------------------------------------


def _coerce_json_safe(value: Any) -> Any:
    """Convert arbitrary ledger-record values into JSON-serializable
    form so the resulting dict round-trips through
    ``json.dumps(..., sort_keys=True)`` and produces a stable byte
    string. Mirrors the v1.7-era helper exactly."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _coerce_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_coerce_json_safe(v) for v in value]
    if hasattr(value, "value") and not isinstance(value, type):
        # Enum members (RecordType): preserve the underlying value.
        try:
            return _coerce_json_safe(value.value)
        except AttributeError:
            pass
    return str(value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_infra_record_count(result: LivingReferenceWorldResult) -> int:
    per_period_total = sum(
        p.record_count_created for p in result.per_period_summaries
    )
    return max(result.created_record_count - per_period_total, 0)


def _canonicalize_period(period: LivingReferencePeriodSummary) -> dict[str, Any]:
    """Canonical form of one period summary. Excludes the volatile
    metadata fields (`ledger_record_count_before` / `_after` are
    not deterministic across kernels with different starting
    ledger sizes; those go on the aggregate result, not the
    period). Preserves every id tuple in ledger order."""
    return {
        "period_id": period.period_id,
        "as_of_date": period.as_of_date,
        "record_count_created": period.record_count_created,
        "corporate_signal_ids": list(period.corporate_signal_ids),
        "corporate_run_ids": list(period.corporate_run_ids),
        "investor_menu_ids": list(period.investor_menu_ids),
        "bank_menu_ids": list(period.bank_menu_ids),
        "investor_selection_ids": list(period.investor_selection_ids),
        "bank_selection_ids": list(period.bank_selection_ids),
        "investor_review_run_ids": list(period.investor_review_run_ids),
        "bank_review_run_ids": list(period.bank_review_run_ids),
        "investor_review_signal_ids": list(period.investor_review_signal_ids),
        "bank_review_signal_ids": list(period.bank_review_signal_ids),
    }


def _canonicalize_ledger_slice(
    kernel: Any, result: LivingReferenceWorldResult
) -> list[dict[str, Any]]:
    """Mirror of v1.7-era ``canonicalize_ledger`` restricted to the
    living-world chain's slice. Drops ``record_id`` / ``timestamp``
    and rewrites ``parent_record_ids`` into ``parent_sequences``
    — sequence indices *relative to the slice*, so the rewriting is
    insensitive to the kernel's pre-existing ledger length.
    """
    start = result.ledger_record_count_before
    end = min(result.ledger_record_count_after, len(kernel.ledger.records))
    slice_records = list(kernel.ledger.records[start:end])

    # Map record_id -> position-within-slice for the parent rewrite.
    id_to_slice_position: dict[str, int] = {
        getattr(r, "record_id", None): pos
        for pos, r in enumerate(slice_records)
        if getattr(r, "record_id", None)
    }

    canonical: list[dict[str, Any]] = []
    for slice_pos, record in enumerate(slice_records):
        parent_seqs: list[int | str] = []
        for parent_id in getattr(record, "parent_record_ids", ()) or ():
            if parent_id in id_to_slice_position:
                parent_seqs.append(id_to_slice_position[parent_id])
            else:
                parent_seqs.append(f"<external:{parent_id!s}>")

        canonical_record: dict[str, Any] = {
            "slice_position": slice_pos,
            "schema_version": getattr(record, "schema_version", None),
            "simulation_date": record.simulation_date,
            "record_type": _coerce_json_safe(record.record_type),
            "source": record.source,
            "target": record.target,
            "object_id": record.object_id,
            "payload": _coerce_json_safe(record.payload),
            "metadata": _coerce_json_safe(record.metadata),
            "parent_sequences": parent_seqs,
            "correlation_id": record.correlation_id,
            "causation_id": record.causation_id,
            "scenario_id": record.scenario_id,
            "run_id": record.run_id,
            "seed": record.seed,
            "space_id": record.space_id,
            "agent_id": record.agent_id,
            "snapshot_id": record.snapshot_id,
            "state_hash": record.state_hash,
            "visibility": record.visibility,
            "confidence": record.confidence,
        }

        for forbidden in _VOLATILE_LEDGER_FIELDS:
            assert forbidden not in canonical_record, (
                f"canonical_record must not include volatile field {forbidden!r}"
            )

        canonical.append(canonical_record)

    return canonical


def _aggregate_attention_divergence(
    kernel: Any, result: LivingReferenceWorldResult
) -> tuple[
    list[str], list[str], list[str], list[list[Any]], list[list[Any]]
]:
    """Recompute the attention divergence directly from stored
    selections so the canonical form is independent of whether the
    caller built a v1.9.1 report. Mirrors the
    union-of-unions semantics defined in §61."""
    investor_union: set[str] = set()
    bank_union: set[str] = set()
    investor_counts: list[tuple[str, str, int]] = []
    bank_counts: list[tuple[str, str, int]] = []

    for period in result.per_period_summaries:
        for sel_id in period.investor_selection_ids:
            try:
                sel = kernel.attention.get_selection(sel_id)
            except Exception:
                continue
            investor_union.update(sel.selected_refs)
            investor_counts.append(
                (sel.actor_id, period.period_id, len(sel.selected_refs))
            )
        for sel_id in period.bank_selection_ids:
            try:
                sel = kernel.attention.get_selection(sel_id)
            except Exception:
                continue
            bank_union.update(sel.selected_refs)
            bank_counts.append(
                (sel.actor_id, period.period_id, len(sel.selected_refs))
            )

    shared = sorted(investor_union & bank_union)
    investor_only = sorted(investor_union - bank_union)
    bank_only = sorted(bank_union - investor_union)
    investor_count_rows = [
        [actor_id, period_id, count]
        for actor_id, period_id, count in sorted(
            investor_counts, key=lambda t: (t[1], t[0])
        )
    ]
    bank_count_rows = [
        [actor_id, period_id, count]
        for actor_id, period_id, count in sorted(
            bank_counts, key=lambda t: (t[1], t[0])
        )
    ]
    return shared, investor_only, bank_only, investor_count_rows, bank_count_rows


def _aggregate_record_type_counts(
    kernel: Any, result: LivingReferenceWorldResult
) -> list[list[Any]]:
    """Walk the chain's ledger slice and return a sorted list of
    `[event_type, count]` pairs. The pairs sum to
    `result.created_record_count` when the ledger has not been
    mutated since the chain returned."""
    start = result.ledger_record_count_before
    end = min(result.ledger_record_count_after, len(kernel.ledger.records))
    counts: dict[str, int] = {}
    for record in kernel.ledger.records[start:end]:
        event_type = record.record_type.value
        counts[event_type] = counts.get(event_type, 0) + 1
    return [[event_type, count] for event_type, count in sorted(counts.items())]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def canonicalize_living_world_result(
    kernel: Any,
    result: LivingReferenceWorldResult,
    report: Any = None,
) -> dict[str, Any]:
    """
    Return a deterministic, JSON-friendly dict describing a single
    living-world run. See module docstring for what is and is not
    in the canonical view.

    Two runs of a deterministic living-world fixture must produce
    equal canonical dicts. The optional ``report`` argument is
    accepted for forward compatibility (a future v1.9.x manifest
    may include a `report_digest` cross-check) but is not currently
    used to compute any canonical field — every canonical field is
    derived directly from `kernel` + `result`, so the digest is
    well-defined regardless of whether the caller built a report.

    Read-only.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(result, LivingReferenceWorldResult):
        raise TypeError(
            "result must be a LivingReferenceWorldResult; "
            f"got {type(result).__name__}"
        )

    per_period_total = sum(
        p.record_count_created for p in result.per_period_summaries
    )
    infra_record_count = _compute_infra_record_count(result)

    (
        shared,
        investor_only,
        bank_only,
        investor_count_rows,
        bank_count_rows,
    ) = _aggregate_attention_divergence(kernel, result)

    record_type_counts = _aggregate_record_type_counts(kernel, result)
    ledger_slice_canonical = _canonicalize_ledger_slice(kernel, result)

    return {
        "format": CANONICAL_FORMAT_VERSION,
        "run_id": result.run_id,
        "period_count": result.period_count,
        "firm_ids": list(result.firm_ids),
        "investor_ids": list(result.investor_ids),
        "bank_ids": list(result.bank_ids),
        "firm_count": len(result.firm_ids),
        "investor_count": len(result.investor_ids),
        "bank_count": len(result.bank_ids),
        "ledger_record_count_before": result.ledger_record_count_before,
        "ledger_record_count_after": result.ledger_record_count_after,
        "created_record_count": result.created_record_count,
        "infra_record_count": infra_record_count,
        "per_period_record_count_total": per_period_total,
        "created_record_ids": list(result.created_record_ids),
        "record_type_counts": record_type_counts,
        "per_period_summaries": [
            _canonicalize_period(p) for p in result.per_period_summaries
        ],
        "shared_selected_refs": shared,
        "investor_only_refs": investor_only,
        "bank_only_refs": bank_only,
        "investor_selected_ref_counts": investor_count_rows,
        "bank_selected_ref_counts": bank_count_rows,
        "ledger_slice_canonical": ledger_slice_canonical,
        "boundary_statement": LIVING_WORLD_BOUNDARY_STATEMENT,
    }


def living_world_digest(
    kernel: Any,
    result: LivingReferenceWorldResult,
    report: Any = None,
) -> str:
    """
    SHA-256 hex digest (64-char lowercase) of the canonical-form
    JSON of the living-world run. Two runs of a deterministic
    fixture must produce the same digest.
    """
    canonical = canonicalize_living_world_result(kernel, result, report=report)
    payload = json.dumps(
        canonical,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
