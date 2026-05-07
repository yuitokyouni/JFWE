"""
v1.28.4 — Merkle digest core for event-log partitions.

Implements the inner and root Merkle digest construction
on top of v1.28.1's :func:`compute_leaf_digest` boundary
and v1.28.2's JSONL reader. v1.28.4 is the **only** module
permitted to compose leaf digests into a tree; the leaf-
digest construction itself remains in
:mod:`world.event_log_schema` so there is exactly one
leaf-hash implementation in the project.

v1.28.4 ships:

- :func:`compute_manifest_digest` — SHA-256 over the
  canonical-JSON manifest bytes.
- :func:`compute_partition_leaf_digest` — reads a
  partition's JSONL part files in lex-ascending order,
  parses canonical records, reconstructs
  :class:`EventLogRecord` instances, and routes through
  :func:`compute_leaf_digest`.
- :func:`compute_inner_digest` — SHA-256 over
  canonically-serialised
  ``(child_key_str, child_digest_hex)`` tuples sorted by
  ``child_key_str``. Filesystem listing order, dict
  iteration order, and insertion order all have no
  effect on the inner digest.
- :func:`compute_event_log_root_digest` — walks every
  partition under an event-log root, computes the per-
  partition leaf digest, then composes the root digest
  with :func:`compute_inner_digest` over the sorted
  child set. The root also incorporates the manifest
  digest so manifest changes propagate.
- :class:`EventLogDigestTree` — frozen dataclass
  capturing the manifest digest, the per-partition
  leaf digests in canonical order, and the root.
- :func:`build_event_log_digest_tree` — convenience
  builder returning the dataclass.

v1.28.4 explicitly does NOT ship:

- Polars / DuckDB / PyArrow / xxhash / Rust / PyO3.
- Any independent leaf-hash implementation.
- Legacy ``living_world_digest`` — that surface is
  unchanged at v1.28.x; the Merkle digest is a new
  separate surface (per design pin §L).
- Materialised view (v1.28.8).

Empty event log:

- An event-log root with **no** partitions and **only**
  the manifest sidecar still produces a deterministic
  root digest (SHA-256 of the canonical leaf-material
  ``{"manifest_digest": …, "partitions": []}``).
- A partition with no part files (just an empty
  directory) is treated as having **zero** records —
  its leaf digest equals ``compute_leaf_digest((),
  manifest)`` and is included in the tree.
- A partition without even a directory is **not**
  included in the tree (only physically-present
  partitions are walked).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from world.event_log_schema import (
    EventLogManifest,
    EventLogRecord,
    compute_leaf_digest,
    manifest_to_canonical_dict,
    serialize_canonical_json,
)
from world.event_log_writer import (
    EventLogPartitionKey,
    _list_part_files_sorted,
    read_manifest_sidecar,
    read_partition_part_file,
)


# ---------------------------------------------------------------------------
# Manifest digest
# ---------------------------------------------------------------------------


def compute_manifest_digest(
    manifest: EventLogManifest,
) -> str:
    """SHA-256 over the canonical-JSON manifest bytes
    (sort_keys=True). Returns lowercase hex."""
    if not isinstance(manifest, EventLogManifest):
        raise TypeError(
            "compute_manifest_digest expects an "
            "EventLogManifest instance"
        )
    body = serialize_canonical_json(
        manifest_to_canonical_dict(manifest),
        sort_keys=True,
    )
    return hashlib.sha256(body).hexdigest()


# ---------------------------------------------------------------------------
# Partition leaf digest
# ---------------------------------------------------------------------------


def _record_dict_to_record(
    d: Mapping[str, Any],
) -> EventLogRecord:
    """Reconstruct an EventLogRecord from a parsed
    canonical-JSON dict. Tuples in the canonical
    representation are JSON arrays; the dataclass
    constructor normalises them back to tuples."""
    return EventLogRecord(
        event_id=d["event_id"],
        run_id=d["run_id"],
        period_id=d["period_id"],
        year_month=d["year_month"],
        sector_id=d["sector_id"],
        record_type=d["record_type"],
        source_space=d["source_space"],
        target_entity_type=d["target_entity_type"],
        target_entity_id=d["target_entity_id"],
        event_index=d["event_index"],
        payload_schema_version=d[
            "payload_schema_version"
        ],
        payload_ref_or_json=d["payload_ref_or_json"],
        parent_event_ids=tuple(d["parent_event_ids"]),
        provenance_kind=d["provenance_kind"],
        synthetic_seed=d["synthetic_seed"],
        created_at_logical=d["created_at_logical"],
        partition_key=d["partition_key"],
        canonical_sort_key=d["canonical_sort_key"],
    )


def compute_partition_leaf_digest(
    root: Path,
    partition_key: EventLogPartitionKey,
    manifest: EventLogManifest,
) -> str:
    """Compute the SHA-256 leaf digest for one partition
    cell.

    Reads part files in lex-ascending order (the canonical
    file sort), parses each line as canonical JSON,
    reconstructs :class:`EventLogRecord` instances, and
    routes through :func:`compute_leaf_digest`.

    Routing through `compute_leaf_digest` is **binding**:
    it is the single leaf-hash implementation per design
    pin §F.1.
    """
    if not isinstance(
        partition_key, EventLogPartitionKey
    ):
        raise TypeError(
            "partition_key must be an "
            "EventLogPartitionKey"
        )
    if not isinstance(manifest, EventLogManifest):
        raise TypeError(
            "manifest must be an EventLogManifest"
        )
    partition_dir = partition_key.to_partition_dir(
        Path(root)
    )
    part_files = _list_part_files_sorted(partition_dir)
    records: list[EventLogRecord] = []
    for pf in part_files:
        for d in read_partition_part_file(pf):
            records.append(_record_dict_to_record(d))
    # compute_leaf_digest re-sorts by canonical_sort_key,
    # so insertion order from the file walk is
    # irrelevant.
    return compute_leaf_digest(records, manifest)


# ---------------------------------------------------------------------------
# Inner digest
# ---------------------------------------------------------------------------


def compute_inner_digest(
    children: Mapping[str, str] | tuple[tuple[str, str], ...],
) -> str:
    """SHA-256 over canonically-serialised
    ``[[child_key, child_digest], ...]`` sorted by
    ``child_key``.

    Filesystem listing order, dict iteration order, and
    insertion order all have no effect on the result.
    """
    if isinstance(children, Mapping):
        items = list(children.items())
    else:
        items = list(children)
    for entry in items:
        if (
            not isinstance(entry, tuple)
            or len(entry) != 2
        ):
            raise ValueError(
                "compute_inner_digest entries must be "
                "(child_key, child_digest_hex) pairs"
            )
        k, d = entry
        if not isinstance(k, str) or not k:
            raise ValueError(
                "child_key must be a non-empty string"
            )
        if not isinstance(d, str) or not d:
            raise ValueError(
                "child_digest_hex must be a non-empty "
                "string"
            )
    items.sort(key=lambda kv: kv[0])
    body = serialize_canonical_json(
        [[k, d] for k, d in items], sort_keys=False
    )
    return hashlib.sha256(body).hexdigest()


# ---------------------------------------------------------------------------
# Partition discovery
# ---------------------------------------------------------------------------


def discover_partitions(
    root: Path,
) -> tuple[EventLogPartitionKey, ...]:
    """Walk an event-log root and return the partition
    keys for every physically-present partition
    directory.

    The path shape (binding) is

        <root>/year_month=<…>/sector_id=<…>/record_type=<…>/

    Directories that do not match this three-level shape
    are skipped silently. The result is sorted by
    ``(year_month, sector_id, record_type)``.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        return ()
    out: list[EventLogPartitionKey] = []
    ym_dirs = sorted(
        d for d in root_path.iterdir() if d.is_dir()
    )
    for ym in ym_dirs:
        if not ym.name.startswith("year_month="):
            continue
        ym_value = ym.name[len("year_month="):]
        if not ym_value:
            continue
        sector_dirs = sorted(
            d for d in ym.iterdir() if d.is_dir()
        )
        for sec in sector_dirs:
            if not sec.name.startswith("sector_id="):
                continue
            sec_value = sec.name[len("sector_id="):]
            if not sec_value:
                continue
            rt_dirs = sorted(
                d for d in sec.iterdir() if d.is_dir()
            )
            for rt in rt_dirs:
                if not rt.name.startswith("record_type="):
                    continue
                rt_value = rt.name[len("record_type="):]
                if not rt_value:
                    continue
                out.append(
                    EventLogPartitionKey(
                        year_month=ym_value,
                        sector_id=sec_value,
                        record_type=rt_value,
                    )
                )
    return tuple(out)


def _partition_key_to_child_key(
    pk: EventLogPartitionKey,
) -> str:
    """Stable child-key string for inner-digest sort.

    Uses ``"|"`` as the delimiter so the three field
    values are unambiguously reconstructable in test
    harnesses if needed.
    """
    return f"{pk.year_month}|{pk.sector_id}|{pk.record_type}"


# ---------------------------------------------------------------------------
# Root digest + tree
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventLogDigestTree:
    """Frozen Merkle-style digest tree for one event-log
    artifact."""

    root_digest: str
    manifest_digest: str
    partition_digests: tuple[
        tuple[str, str], ...
    ] = field(default_factory=tuple)


def compute_event_log_root_digest(
    root: Path,
    manifest: EventLogManifest | None = None,
) -> str:
    """Compute the Merkle root digest for an event-log
    artifact at ``root``.

    If ``manifest`` is omitted, it is read from the
    ``_MANIFEST.json`` sidecar via
    :func:`read_manifest_sidecar` (raises
    ``FileNotFoundError`` if absent).

    Procedure:

    1. Read or accept the manifest. Compute
       ``manifest_digest = compute_manifest_digest(manifest)``.
    2. Discover partitions via
       :func:`discover_partitions` (sorted, deterministic).
    3. For each partition, compute the partition leaf
       digest via :func:`compute_partition_leaf_digest`
       (which routes through
       :func:`compute_leaf_digest`).
    4. Build the inner-digest input as
       ``[(partition_child_key, partition_leaf_digest),
       ("__manifest__", manifest_digest)]`` and call
       :func:`compute_inner_digest`. Including
       ``__manifest__`` in the inner input makes the
       root react to manifest changes even when the
       partition set is empty.
    """
    if manifest is None:
        manifest = read_manifest_sidecar(root)
    manifest_digest = compute_manifest_digest(manifest)
    partitions = discover_partitions(root)
    children: list[tuple[str, str]] = [
        ("__manifest__", manifest_digest),
    ]
    for pk in partitions:
        leaf = compute_partition_leaf_digest(
            root, pk, manifest
        )
        children.append(
            (_partition_key_to_child_key(pk), leaf)
        )
    return compute_inner_digest(children)


def build_event_log_digest_tree(
    root: Path,
    manifest: EventLogManifest | None = None,
) -> EventLogDigestTree:
    """Convenience builder returning the full
    :class:`EventLogDigestTree` for inspection or
    persistence.

    The dataclass exposes the manifest digest, the
    per-partition leaf digests in canonical sorted
    order, and the root digest itself.
    """
    if manifest is None:
        manifest = read_manifest_sidecar(root)
    manifest_digest = compute_manifest_digest(manifest)
    partitions = discover_partitions(root)
    partition_digests: list[tuple[str, str]] = []
    for pk in partitions:
        leaf = compute_partition_leaf_digest(
            root, pk, manifest
        )
        partition_digests.append(
            (_partition_key_to_child_key(pk), leaf)
        )
    inner_input: list[tuple[str, str]] = [
        ("__manifest__", manifest_digest),
        *partition_digests,
    ]
    root_digest = compute_inner_digest(inner_input)
    return EventLogDigestTree(
        root_digest=root_digest,
        manifest_digest=manifest_digest,
        partition_digests=tuple(partition_digests),
    )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "EventLogDigestTree",
    "build_event_log_digest_tree",
    "compute_event_log_root_digest",
    "compute_inner_digest",
    "compute_manifest_digest",
    "compute_partition_leaf_digest",
    "discover_partitions",
]
