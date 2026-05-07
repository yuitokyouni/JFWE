"""
v1.28.1 — Event-log schema dataclasses + canonical
serializer + leaf digest function boundary.

Smallest possible runtime foundation for the future
scale substrate per
[`docs/v1_28_scale_substrate_event_log_columnar_merkle.md`](../docs/v1_28_scale_substrate_event_log_columnar_merkle.md).

v1.28.1 ships:

- one canonical event-log row representation
  (:class:`EventLogRecord`),
- one manifest representation
  (:class:`EventLogManifest`),
- one deterministic canonical-JSON serializer
  (:func:`serialize_canonical_json`),
- one SHA-256 leaf-digest function boundary
  (:func:`compute_leaf_digest`).

Critical scope constraints carried verbatim from the
v1.28.0 design pin (binding):

- **No Parquet writer / reader.** No PyArrow.
- **No Polars / DuckDB / xxhash / Rust / PyO3.**
- **No filesystem partition writer.** No file is read
  or written by anything in this module.
- **No sealed-partition enforcement.** Append-only
  physical semantics are deferred to v1.28.2+.
- **No full Merkle tree.** No inner / root digest;
  only the leaf-digest function boundary.
- **No materialized views.** No historical lazy
  loading.
- **No scale benchmark.** Tests run on tiny
  in-memory fixtures only.
- **No real data, no Japan calibration, no adapter,
  no investment output, no price-impact modeling.**

Empty-by-default rule preserved on the kernel: this
module does not register a kernel field. Every
existing v1.21.last canonical
``living_world_digest`` value remains byte-identical.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import (
    Any,
    ClassVar,
    Iterable,
    Mapping,
    Sequence,
)


# ---------------------------------------------------------------------------
# Canonical schema column order (binding for v1.28.1)
#
# This is the canonical field-name set for the
# :class:`EventLogRecord` serializer. Every
# :class:`EventLogManifest` must carry exactly this set
# of column names in its ``schema_column_order`` tuple
# (the *order* may differ — and a different order
# yields a different leaf digest, by design).
# ---------------------------------------------------------------------------


CANONICAL_SCHEMA_COLUMN_ORDER: tuple[str, ...] = (
    "event_id",
    "run_id",
    "period_id",
    "year_month",
    "sector_id",
    "record_type",
    "source_space",
    "target_entity_type",
    "target_entity_id",
    "event_index",
    "payload_schema_version",
    "payload_ref_or_json",
    "parent_event_ids",
    "provenance_kind",
    "synthetic_seed",
    "created_at_logical",
    "partition_key",
    "canonical_sort_key",
)


CANONICAL_SCHEMA_COLUMN_NAMES: frozenset[str] = frozenset(
    CANONICAL_SCHEMA_COLUMN_ORDER
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_required_string(
    value: Any, *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )
    return value


def _validate_string_tuple(
    value: Any,
    *,
    field_name: str,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    """Accept any iterable of non-empty strings; reject
    raw ``str`` (which is itself an iterable of single
    characters and almost certainly a caller mistake).
    """
    if isinstance(value, str):
        raise ValueError(
            f"{field_name} must be an iterable of "
            "non-empty strings, not a single string"
        )
    if not isinstance(value, (tuple, list)):
        raise ValueError(
            f"{field_name} must be a tuple or list of "
            "non-empty strings"
        )
    normalised = tuple(value)
    if not allow_empty and not normalised:
        raise ValueError(
            f"{field_name} must be non-empty"
        )
    for entry in normalised:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty "
                f"strings; got {entry!r}"
            )
    return normalised


def _validate_non_negative_int(
    value: Any, *, field_name: str
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"{field_name} must be a non-negative int"
        )
    if value < 0:
        raise ValueError(
            f"{field_name} must be >= 0; got {value!r}"
        )
    return value


# ---------------------------------------------------------------------------
# EventLogRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventLogRecord:
    """Immutable, append-only event-log row.

    The 18 fields below are the canonical event-log
    schema for v1.28.1. Every field's storage shape and
    validation rule is binding for v1.28.x; changing
    them requires a fresh design pin.

    Two fields admit deterministic defaults:

    - ``partition_key`` defaults to
      ``f"year_month={year_month}/sector_id={sector_id}/"
      f"record_type={record_type}"`` if omitted.
    - ``canonical_sort_key`` defaults to
      ``f"{partition_key}/event_index={event_index:012d}/"
      f"event_id={event_id}"`` if omitted.

    Callers may supply explicit values for these two
    fields; they are validated as non-empty strings but
    not checked against the default form. (A future
    v1.28.x sub-milestone may tighten this if a use
    case for non-default keys does not appear.)

    The record carries no wall-clock timestamp. The
    ``created_at_logical`` field is a logical-period
    string (e.g. ``"2026-Q2"`` / ``"2026_06"``); it
    must not be a real wall-clock time.

    The record carries no real-world identifier. The
    ``sector_id``, ``record_type``, and
    ``target_entity_id`` fields are not validated
    against any closed-set vocabulary at v1.28.1.
    Real-world meaning is intentionally not inferred:
    the schema is the canonical event-row shape, not a
    domain taxonomy.
    """

    event_id: str
    run_id: str
    period_id: str
    year_month: str
    sector_id: str
    record_type: str
    source_space: str
    target_entity_type: str
    target_entity_id: str
    event_index: int
    payload_schema_version: str
    payload_ref_or_json: str
    parent_event_ids: tuple[str, ...] = ()
    provenance_kind: str = "synthetic"
    synthetic_seed: str = ""
    created_at_logical: str = ""
    partition_key: str = ""
    canonical_sort_key: str = ""

    REQUIRED_NON_EMPTY_FIELDS: ClassVar[tuple[str, ...]] = (
        "event_id",
        "run_id",
        "period_id",
        "year_month",
        "sector_id",
        "record_type",
        "source_space",
        "target_entity_type",
        "target_entity_id",
        "payload_schema_version",
        "payload_ref_or_json",
        "provenance_kind",
    )

    def __post_init__(self) -> None:
        # Required non-empty string fields.
        for fname in self.REQUIRED_NON_EMPTY_FIELDS:
            _validate_required_string(
                getattr(self, fname), field_name=fname
            )
        # event_index — non-negative integer.
        object.__setattr__(
            self,
            "event_index",
            _validate_non_negative_int(
                self.event_index,
                field_name="event_index",
            ),
        )
        # parent_event_ids — tuple of non-empty strings;
        # may be empty.
        object.__setattr__(
            self,
            "parent_event_ids",
            _validate_string_tuple(
                self.parent_event_ids,
                field_name="parent_event_ids",
                allow_empty=True,
            ),
        )
        # synthetic_seed / created_at_logical — optional
        # strings; if non-empty must be valid strings.
        for fname in ("synthetic_seed", "created_at_logical"):
            value = getattr(self, fname)
            if not isinstance(value, str):
                raise ValueError(
                    f"{fname} must be a string (possibly empty)"
                )
        # partition_key — derive default if empty.
        if not self.partition_key:
            object.__setattr__(
                self,
                "partition_key",
                self._default_partition_key(),
            )
        else:
            _validate_required_string(
                self.partition_key,
                field_name="partition_key",
            )
        # canonical_sort_key — derive default if empty.
        if not self.canonical_sort_key:
            object.__setattr__(
                self,
                "canonical_sort_key",
                self._default_canonical_sort_key(),
            )
        else:
            _validate_required_string(
                self.canonical_sort_key,
                field_name="canonical_sort_key",
            )

    def _default_partition_key(self) -> str:
        return (
            f"year_month={self.year_month}"
            f"/sector_id={self.sector_id}"
            f"/record_type={self.record_type}"
        )

    def _default_canonical_sort_key(self) -> str:
        return (
            f"{self.partition_key}"
            f"/event_index={self.event_index:012d}"
            f"/event_id={self.event_id}"
        )


# ---------------------------------------------------------------------------
# EventLogManifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventLogManifest:
    """Immutable manifest pinning the partition shape,
    canonical sort-key fields, schema column order,
    digest algorithm, leaf serializer, and Merkle-tree
    version for one event-log artifact.

    The manifest is **part of the digest material** in
    :func:`compute_leaf_digest`. Changing any manifest
    field changes the leaf digest even when the
    underlying records are byte-identical. This is
    intentional: a partition schema change is a
    versioned digest change and must surface.
    """

    manifest_version: str
    partition_schema_version: str
    partition_key_fields: tuple[str, ...]
    event_schema_version: str
    canonical_sort_key_fields: tuple[str, ...]
    schema_column_order: tuple[str, ...]
    digest_algorithm: str = "sha256"
    leaf_serializer: str = "canonical-json-v1"
    merkle_tree_version: str = "merkle-v1-prototype"

    REQUIRED_NON_EMPTY_FIELDS: ClassVar[tuple[str, ...]] = (
        "manifest_version",
        "partition_schema_version",
        "event_schema_version",
        "digest_algorithm",
        "leaf_serializer",
        "merkle_tree_version",
    )

    REQUIRED_NON_EMPTY_TUPLE_FIELDS: ClassVar[
        tuple[str, ...]
    ] = (
        "partition_key_fields",
        "canonical_sort_key_fields",
        "schema_column_order",
    )

    REQUIRED_PARTITION_KEY_FIELDS: ClassVar[
        frozenset[str]
    ] = frozenset({"year_month", "sector_id", "record_type"})

    REQUIRED_CANONICAL_SORT_KEY_FIELDS: ClassVar[
        frozenset[str]
    ] = frozenset(
        {
            "canonical_sort_key",
        }
    )

    def __post_init__(self) -> None:
        for fname in self.REQUIRED_NON_EMPTY_FIELDS:
            _validate_required_string(
                getattr(self, fname), field_name=fname
            )
        for fname in self.REQUIRED_NON_EMPTY_TUPLE_FIELDS:
            object.__setattr__(
                self,
                fname,
                _validate_string_tuple(
                    getattr(self, fname),
                    field_name=fname,
                    allow_empty=False,
                ),
            )
        if self.digest_algorithm != "sha256":
            raise ValueError(
                "digest_algorithm must be 'sha256' at "
                "v1.28.1 (canonical hash boundary); "
                f"got {self.digest_algorithm!r}"
            )
        # partition_key_fields must include the binding
        # partition dimensions.
        partition_set = frozenset(self.partition_key_fields)
        missing_partition = (
            self.REQUIRED_PARTITION_KEY_FIELDS - partition_set
        )
        if missing_partition:
            raise ValueError(
                "partition_key_fields must include "
                f"{sorted(self.REQUIRED_PARTITION_KEY_FIELDS)!r}; "
                f"missing {sorted(missing_partition)!r}"
            )
        # canonical_sort_key_fields must include the
        # binding sort-key field.
        sort_set = frozenset(self.canonical_sort_key_fields)
        missing_sort = (
            self.REQUIRED_CANONICAL_SORT_KEY_FIELDS - sort_set
        )
        if missing_sort:
            raise ValueError(
                "canonical_sort_key_fields must include "
                f"{sorted(self.REQUIRED_CANONICAL_SORT_KEY_FIELDS)!r}; "
                f"missing {sorted(missing_sort)!r}"
            )
        # schema_column_order must equal the canonical
        # column NAME-SET (the order may differ — and a
        # different order yields a different leaf digest,
        # by design).
        column_set = frozenset(self.schema_column_order)
        if column_set != CANONICAL_SCHEMA_COLUMN_NAMES:
            extra = column_set - CANONICAL_SCHEMA_COLUMN_NAMES
            missing = (
                CANONICAL_SCHEMA_COLUMN_NAMES - column_set
            )
            raise ValueError(
                "schema_column_order must contain exactly "
                "the canonical EventLogRecord field set; "
                f"missing {sorted(missing)!r}, "
                f"extra {sorted(extra)!r}"
            )
        if len(self.schema_column_order) != len(column_set):
            raise ValueError(
                "schema_column_order must not contain "
                "duplicate field names"
            )


# ---------------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------------


def event_log_record_to_canonical_dict(
    record: EventLogRecord,
    *,
    column_order: Sequence[str] = (
        CANONICAL_SCHEMA_COLUMN_ORDER
    ),
) -> dict[str, Any]:
    """Project an :class:`EventLogRecord` into a
    canonical mapping ordered by ``column_order``.

    Tuples are converted to lists so the JSON
    serializer produces a stable representation.

    The returned dict's insertion order is the
    canonical column order; serializing it without
    ``sort_keys=True`` preserves that order.
    """

    if not isinstance(record, EventLogRecord):
        raise TypeError(
            "event_log_record_to_canonical_dict expects "
            "an EventLogRecord instance"
        )
    column_set = frozenset(column_order)
    if column_set != CANONICAL_SCHEMA_COLUMN_NAMES:
        extra = column_set - CANONICAL_SCHEMA_COLUMN_NAMES
        missing = (
            CANONICAL_SCHEMA_COLUMN_NAMES - column_set
        )
        raise ValueError(
            "column_order must contain exactly the "
            "canonical EventLogRecord field set; "
            f"missing {sorted(missing)!r}, "
            f"extra {sorted(extra)!r}"
        )
    out: dict[str, Any] = {}
    for col in column_order:
        value = getattr(record, col)
        if isinstance(value, tuple):
            out[col] = list(value)
        else:
            out[col] = value
    return out


def manifest_to_canonical_dict(
    manifest: EventLogManifest,
) -> dict[str, Any]:
    """Project an :class:`EventLogManifest` into a
    canonical mapping. Tuple fields are serialised as
    lists; other fields are passed through unchanged.

    The returned dict's keys are emitted in
    alphabetical order (sort_keys=True at serialize
    time) so the manifest's canonical JSON is
    insertion-order-independent.
    """

    if not isinstance(manifest, EventLogManifest):
        raise TypeError(
            "manifest_to_canonical_dict expects an "
            "EventLogManifest instance"
        )
    return {
        "canonical_sort_key_fields": list(
            manifest.canonical_sort_key_fields
        ),
        "digest_algorithm": manifest.digest_algorithm,
        "event_schema_version": (
            manifest.event_schema_version
        ),
        "leaf_serializer": manifest.leaf_serializer,
        "manifest_version": manifest.manifest_version,
        "merkle_tree_version": (
            manifest.merkle_tree_version
        ),
        "partition_key_fields": list(
            manifest.partition_key_fields
        ),
        "partition_schema_version": (
            manifest.partition_schema_version
        ),
        "schema_column_order": list(
            manifest.schema_column_order
        ),
    }


def serialize_canonical_json(
    value: Mapping[str, Any]
    | Sequence[Mapping[str, Any]]
    | Sequence[Any],
    *,
    sort_keys: bool = False,
) -> bytes:
    """Canonical JSON bytes.

    Uses ``separators=(",", ":")`` and
    ``ensure_ascii=False`` (UTF-8 bytes). Tuples
    serialise as JSON arrays. The caller controls
    ``sort_keys``:

    - For a record dict whose insertion order is the
      canonical column order, pass
      ``sort_keys=False`` (the default) so the column
      order is preserved.
    - For a manifest dict whose key set is fixed and
      whose canonical form is alphabetic, pass
      ``sort_keys=True``.

    No wall-clock timestamp, no Python repr, no memory
    address, no pandas / Polars / DuckDB / filesystem
    ordering reaches the canonical bytes.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=sort_keys,
        separators=(",", ":"),
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Leaf digest function boundary
# ---------------------------------------------------------------------------


def compute_leaf_digest(
    records: Iterable[EventLogRecord],
    manifest: EventLogManifest,
) -> str:
    """Compute the SHA-256 leaf digest for a partition
    cell.

    All future Merkle leaf hashing must go through this
    single function boundary (per
    [`docs/v1_28_scale_substrate_event_log_columnar_merkle.md`](../docs/v1_28_scale_substrate_event_log_columnar_merkle.md)
    §F).

    Behavior (binding for v1.28.x):

    1. Materialise ``records`` into a tuple.
    2. Sort the tuple by ``canonical_sort_key`` (the
       record-level sort; insertion order is irrelevant).
    3. Project each record through
       :func:`event_log_record_to_canonical_dict` using
       the manifest's ``schema_column_order`` (changing
       that order changes the digest, by design).
    4. Build a leaf-material mapping
       ``{"manifest": manifest_canonical_dict,
          "records": [record_canonical_dict, ...]}``.
       The manifest dict is canonicalised with
       alphabetic key order; the records list preserves
       insertion order, which is the canonical sorted
       order from step 2.
    5. Serialise the leaf material with
       :func:`serialize_canonical_json`
       (``sort_keys=False`` so column order in records
       is preserved; the manifest dict is already
       alphabetic).
    6. Hash with SHA-256 and return the lowercase hex
       digest.

    Empty record list is allowed: the digest is the
    SHA-256 of the canonical JSON
    ``{"manifest": {...}, "records": []}``, which is
    deterministic and a function of the manifest only.
    """

    if not isinstance(manifest, EventLogManifest):
        raise TypeError(
            "compute_leaf_digest expects an "
            "EventLogManifest instance"
        )
    materialised = tuple(records)
    for r in materialised:
        if not isinstance(r, EventLogRecord):
            raise TypeError(
                "compute_leaf_digest expects an iterable "
                "of EventLogRecord instances; got "
                f"{type(r).__name__}"
            )
    sorted_records = sorted(
        materialised, key=lambda r: r.canonical_sort_key
    )
    record_dicts = [
        event_log_record_to_canonical_dict(
            r, column_order=manifest.schema_column_order
        )
        for r in sorted_records
    ]
    manifest_dict = manifest_to_canonical_dict(manifest)
    # The leaf material is itself a small mapping with
    # alphabetic top-level keys (``manifest`` <
    # ``records``); sort_keys=False preserves the
    # column order inside each record dict.
    leaf_material: dict[str, Any] = {
        "manifest": manifest_dict,
        "records": record_dicts,
    }
    leaf_bytes = serialize_canonical_json(
        leaf_material, sort_keys=False
    )
    return hashlib.sha256(leaf_bytes).hexdigest()


__all__ = [
    "CANONICAL_SCHEMA_COLUMN_NAMES",
    "CANONICAL_SCHEMA_COLUMN_ORDER",
    "EventLogManifest",
    "EventLogRecord",
    "compute_leaf_digest",
    "event_log_record_to_canonical_dict",
    "manifest_to_canonical_dict",
    "serialize_canonical_json",
]
