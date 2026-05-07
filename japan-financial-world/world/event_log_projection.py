"""
v1.28.8 — Deterministic event-log projection prototype.

Read-only multiset projection over an on-disk event-log
artifact. The projection is a **materialised view**, not
a source of truth — dropping it and rebuilding from the
event log produces a byte-identical view (per design pin
§G + §H).

v1.28.8 ships:

- :class:`EventLogProjectionSummary` — frozen dataclass
  holding deterministic counts and the partition-key
  set.
- :func:`project_event_log` — walk the event-log root,
  read JSONL part files, and produce the summary
  deterministically.

v1.28.8 explicitly does NOT ship:

- No `WorldKernel` binding. No kernel field is added.
- No rebinding of any v1.x `Book.list_*(...)` method.
  The existing book APIs are unchanged.
- No historical lazy-load into production APIs.
- No domain semantics (no closed-set vocabulary
  validation; the projection is a generic count-and-
  group surface).
- No citation graph. No trace graph. No PROV-O
  mapping. No SPARQL / Cypher query layer. No
  counterfactual replay.
- No Polars / DuckDB / PyArrow / xxhash dependency.

The projection is **not** the audit-query layer (that
work, if undertaken, lives in a future v1.29+
milestone).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from world.event_log_merkle import discover_partitions
from world.event_log_writer import (
    EventLogPartitionKey,
    _list_part_files_sorted,
    read_partition_part_file,
)


# ---------------------------------------------------------------------------
# EventLogProjectionSummary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventLogProjectionSummary:
    """Frozen, read-only multiset projection over one
    event-log artifact.

    All count fields are non-negative integers. Tuple-
    of-pair fields are sorted deterministically (by key
    ascending) so two projections of the same event log
    are byte-identical.
    """

    total_records: int
    records_by_period: tuple[tuple[str, int], ...] = field(
        default_factory=tuple
    )
    records_by_entity: tuple[tuple[str, int], ...] = field(
        default_factory=tuple
    )
    records_by_record_type: tuple[
        tuple[str, int], ...
    ] = field(default_factory=tuple)
    partition_keys: tuple[
        tuple[str, str, str], ...
    ] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records": self.total_records,
            "records_by_period": [
                list(p) for p in self.records_by_period
            ],
            "records_by_entity": [
                list(p) for p in self.records_by_entity
            ],
            "records_by_record_type": [
                list(p)
                for p in self.records_by_record_type
            ],
            "partition_keys": [
                list(t) for t in self.partition_keys
            ],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ordered_count_pairs(
    items: list[str],
) -> tuple[tuple[str, int], ...]:
    """Return ``((label, count), ...)`` sorted by label
    ascending. Deterministic across reruns regardless
    of iteration order of the source ``items``."""
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return tuple(sorted(counts.items()))


def _record_in_period_window(
    record_dict: Mapping[str, Any],
    *,
    period_window: tuple[str, str] | None,
) -> bool:
    if period_window is None:
        return True
    lo, hi = period_window
    p = record_dict["period_id"]
    return lo <= p <= hi


# ---------------------------------------------------------------------------
# project_event_log
# ---------------------------------------------------------------------------


def project_event_log(
    root: Path,
    *,
    period_window: tuple[str, str] | None = None,
) -> EventLogProjectionSummary:
    """Build a deterministic projection summary over
    the event-log root.

    The projection:

    - walks every physically-present partition under
      ``root`` (via :func:`discover_partitions`,
      sorted);
    - for each partition, reads part files in lex-
      ascending order (via :func:`_list_part_files_sorted`)
      and parses canonical JSONL records;
    - counts records globally and groups them by
      `period_id`, `target_entity_id`, and
      `record_type`;
    - if ``period_window`` is supplied, restricts the
      projection to records whose `period_id` falls
      lexicographically within ``[lo, hi]`` (inclusive
      both ends).

    The summary's tuple-of-pair fields are sorted by
    key ascending; the partition_keys field is sorted
    by ``(year_month, sector_id, record_type)``.
    Identical event-log content produces byte-
    identical summaries.
    """
    root_path = Path(root)
    partitions: tuple[
        EventLogPartitionKey, ...
    ] = discover_partitions(root_path)

    period_ids: list[str] = []
    entity_ids: list[str] = []
    record_types: list[str] = []
    total = 0
    partition_keys: list[tuple[str, str, str]] = []
    seen_partitions: set[tuple[str, str, str]] = set()

    for pk in partitions:
        partition_dir = pk.to_partition_dir(root_path)
        part_files = _list_part_files_sorted(
            partition_dir
        )
        partition_has_record = False
        for pf in part_files:
            for d in read_partition_part_file(pf):
                if not _record_in_period_window(
                    d, period_window=period_window
                ):
                    continue
                total += 1
                period_ids.append(d["period_id"])
                entity_ids.append(d["target_entity_id"])
                record_types.append(d["record_type"])
                partition_has_record = True
        # Include the partition in the summary only if
        # it contains at least one record under the
        # current window. (This makes a window-
        # restricted summary equal to a full summary
        # filtered to the same window.)
        if partition_has_record:
            t = (pk.year_month, pk.sector_id, pk.record_type)
            if t not in seen_partitions:
                seen_partitions.add(t)
                partition_keys.append(t)

    return EventLogProjectionSummary(
        total_records=total,
        records_by_period=_ordered_count_pairs(
            period_ids
        ),
        records_by_entity=_ordered_count_pairs(
            entity_ids
        ),
        records_by_record_type=_ordered_count_pairs(
            record_types
        ),
        partition_keys=tuple(
            sorted(partition_keys)
        ),
    )


__all__ = [
    "EventLogProjectionSummary",
    "project_event_log",
]
