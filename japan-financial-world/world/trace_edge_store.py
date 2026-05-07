"""
v1.29.2 — Append-only local trace-edge storage.

Standard-library-only filesystem-backed JSONL writer
for trace-edge records. Mirrors the v1.28.2 event-log
writer discipline (sealed marker, monotonic part-file
index, exclusive-open append, manifest sidecar with
write-or-verify-equal semantics).

v1.29.2 ships:

- :class:`TraceEdgeManifest` — frozen manifest pinning
  the trace-edge schema version, partition shape,
  canonical column order, leaf serializer, digest
  algorithm.
- :class:`TraceEdgePartitionKey` — three-field
  partition key
  ``(run_id, period_id_or_unknown,
  edge_category_label)``.
- :class:`TraceEdgePartitionWriter` — append-only
  per-partition JSONL writer.
- :class:`TraceEdgeWriteResult` — frozen result
  dataclass.
- Sidecar helpers
  :func:`write_trace_edges_manifest_sidecar`,
  :func:`read_trace_edges_manifest_sidecar`,
  :func:`ensure_trace_edges_manifest_sidecar`.
- Reader helper
  :func:`read_trace_edge_part_file` for use by
  v1.29.3+ projection / digest paths.

v1.29.2 explicitly does NOT ship:

- No Parquet / Polars / DuckDB / PyArrow / xxhash /
  Rust / PyO3.
- No graph database (Neo4j / TigerGraph / etc.).
- No PROV-O / RDF / SPARQL / Cypher.
- No `prev_hash` / `self_hash` chain on records or
  partitions. Tamper evidence is layered through
  :func:`world.trace_edges.compute_trace_edge_leaf_digest`
  (v1.29.1) — the same SHA-256 boundary.
- No `WorldKernel` field.
- No mutation of the v1.28 event-log files.

Path layout (binding):

    <root>/
      run_id=<run_id>/
        period_id=<period_id_or_unknown>/
          edge_category=<edge_category_label>/
            part-000001.jsonl
            part-000002.jsonl
            _SEALED   (optional, per-partition marker)
      _TRACE_EDGES_MANIFEST.json   (per-root manifest sidecar)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Iterable

from world.event_log_schema import (
    serialize_canonical_json,
)
from world.trace_edges import (
    CANONICAL_TRACE_EDGE_COLUMN_ORDER,
    TRACE_EDGE_CATEGORY_LABELS,
    TRACE_EDGE_SCHEMA_VERSION,
    TraceEdgeRecord,
    compute_trace_edge_leaf_digest,
    trace_edge_to_canonical_dict,
)


# ---------------------------------------------------------------------------
# Constants (binding for v1.29.2)
# ---------------------------------------------------------------------------


TRACE_EDGES_SEALED_MARKER_FILE_NAME: str = "_SEALED"
TRACE_EDGES_PART_FILE_NAME_PREFIX: str = "part-"
TRACE_EDGES_PART_FILE_INDEX_DIGITS: int = 6
TRACE_EDGES_PART_FILE_NAME_SUFFIX: str = ".jsonl"
TRACE_EDGES_MANIFEST_SIDECAR_FILE_NAME: str = (
    "_TRACE_EDGES_MANIFEST.json"
)

# Placeholder used in the partition path when
# ``period_id`` is empty on the source record.
PERIOD_ID_UNKNOWN_PATH_VALUE: str = "unknown"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TraceEdgeWriteError(Exception):
    """Base class for v1.29.2 trace-edge writer errors."""


class TraceEdgeSealedPartitionError(TraceEdgeWriteError):
    """Raised when an append is attempted on a sealed
    partition."""


class TraceEdgeAlreadySealedError(TraceEdgeWriteError):
    """Raised when ``seal()`` is called on a partition
    that has already been sealed."""


class TraceEdgeValidationError(TraceEdgeWriteError):
    """Raised when an append's records do not match the
    writer's partition key, or when constructor inputs
    are invalid."""


class TraceEdgeManifestMismatchError(TraceEdgeWriteError):
    """Raised when the existing trace-edge manifest
    sidecar does not match the supplied manifest."""


# ---------------------------------------------------------------------------
# TraceEdgeManifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceEdgeManifest:
    """Frozen manifest pinning the trace-edge
    partition shape, canonical column order, digest
    algorithm, and leaf serializer for one trace-edge
    artifact root.

    Mirrors the v1.28.3 :class:`EventLogManifest`
    discipline. Manifest changes propagate into
    :func:`compute_trace_edge_leaf_digest` indirectly
    via the bumped ``trace_edge_schema_version``;
    direct manifest fields are pinned here so the
    sidecar can be verified at writer construction.
    """

    manifest_version: str
    trace_edge_schema_version: str
    partition_key_fields: tuple[str, ...]
    canonical_sort_key_fields: tuple[str, ...]
    schema_column_order: tuple[str, ...]
    digest_algorithm: str = "sha256"
    leaf_serializer: str = "canonical-json-v1"

    REQUIRED_NON_EMPTY_FIELDS: ClassVar[tuple[str, ...]] = (
        "manifest_version",
        "trace_edge_schema_version",
        "digest_algorithm",
        "leaf_serializer",
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
    ] = frozenset(
        {"run_id", "period_id", "edge_category_label"}
    )

    def __post_init__(self) -> None:
        for fname in self.REQUIRED_NON_EMPTY_FIELDS:
            v = getattr(self, fname)
            if not isinstance(v, str) or not v:
                raise TraceEdgeValidationError(
                    f"{fname} must be a non-empty string"
                )
        for fname in self.REQUIRED_NON_EMPTY_TUPLE_FIELDS:
            v = getattr(self, fname)
            if not isinstance(v, (tuple, list)):
                raise TraceEdgeValidationError(
                    f"{fname} must be a tuple or list"
                )
            normalised = tuple(v)
            if not normalised:
                raise TraceEdgeValidationError(
                    f"{fname} must be non-empty"
                )
            for entry in normalised:
                if (
                    not isinstance(entry, str)
                    or not entry
                ):
                    raise TraceEdgeValidationError(
                        f"{fname} entries must be non-"
                        "empty strings"
                    )
            object.__setattr__(self, fname, normalised)
        if self.digest_algorithm != "sha256":
            raise TraceEdgeValidationError(
                "digest_algorithm must be 'sha256' at "
                f"v1.29.2; got {self.digest_algorithm!r}"
            )
        partition_set = frozenset(self.partition_key_fields)
        missing = (
            self.REQUIRED_PARTITION_KEY_FIELDS - partition_set
        )
        if missing:
            raise TraceEdgeValidationError(
                "partition_key_fields must include "
                f"{sorted(self.REQUIRED_PARTITION_KEY_FIELDS)!r};"
                f" missing {sorted(missing)!r}"
            )
        column_set = frozenset(self.schema_column_order)
        canonical_set = frozenset(
            CANONICAL_TRACE_EDGE_COLUMN_ORDER
        )
        if column_set != canonical_set:
            extra = column_set - canonical_set
            missing = canonical_set - column_set
            raise TraceEdgeValidationError(
                "schema_column_order must contain exactly "
                "the canonical TraceEdgeRecord field set; "
                f"missing {sorted(missing)!r}, "
                f"extra {sorted(extra)!r}"
            )
        if len(self.schema_column_order) != len(column_set):
            raise TraceEdgeValidationError(
                "schema_column_order must not contain "
                "duplicate field names"
            )


def default_trace_edge_manifest() -> TraceEdgeManifest:
    """Return the default v1.29.2 trace-edge manifest
    pinned at the v1.29.1 schema version."""
    return TraceEdgeManifest(
        manifest_version="v1.29.2-trace-store-v1",
        trace_edge_schema_version=TRACE_EDGE_SCHEMA_VERSION,
        partition_key_fields=(
            "run_id",
            "period_id",
            "edge_category_label",
        ),
        canonical_sort_key_fields=(
            "run_id",
            "source_event_id",
            "target_event_id",
            "edge_type_label",
            "edge_id",
            "canonical_sort_key",
        ),
        schema_column_order=(
            CANONICAL_TRACE_EDGE_COLUMN_ORDER
        ),
    )


# ---------------------------------------------------------------------------
# Manifest sidecar helpers
# ---------------------------------------------------------------------------


def trace_edges_manifest_sidecar_path(root: Path) -> Path:
    return Path(root) / TRACE_EDGES_MANIFEST_SIDECAR_FILE_NAME


def _manifest_to_canonical_dict(
    manifest: TraceEdgeManifest,
) -> dict[str, Any]:
    return {
        "canonical_sort_key_fields": list(
            manifest.canonical_sort_key_fields
        ),
        "digest_algorithm": manifest.digest_algorithm,
        "leaf_serializer": manifest.leaf_serializer,
        "manifest_version": manifest.manifest_version,
        "partition_key_fields": list(
            manifest.partition_key_fields
        ),
        "schema_column_order": list(
            manifest.schema_column_order
        ),
        "trace_edge_schema_version": (
            manifest.trace_edge_schema_version
        ),
    }


def write_trace_edges_manifest_sidecar(
    root: Path, manifest: TraceEdgeManifest
) -> Path:
    """Write the trace-edge manifest sidecar at
    ``root / _TRACE_EDGES_MANIFEST.json``.

    Refuses to overwrite an existing sidecar — that is
    the ManifestMismatchError path. Use
    :func:`ensure_trace_edges_manifest_sidecar` for
    idempotent write-or-verify semantics.
    """
    if not isinstance(manifest, TraceEdgeManifest):
        raise TraceEdgeValidationError(
            "manifest must be a TraceEdgeManifest"
        )
    p = trace_edges_manifest_sidecar_path(root)
    Path(root).mkdir(parents=True, exist_ok=True)
    body = serialize_canonical_json(
        _manifest_to_canonical_dict(manifest),
        sort_keys=True,
    )
    with p.open("xb") as fh:
        fh.write(body)
    return p


def read_trace_edges_manifest_sidecar(
    root: Path,
) -> TraceEdgeManifest:
    p = trace_edges_manifest_sidecar_path(root)
    raw = p.read_bytes()
    data = json.loads(raw)
    return TraceEdgeManifest(
        manifest_version=data["manifest_version"],
        trace_edge_schema_version=data[
            "trace_edge_schema_version"
        ],
        partition_key_fields=tuple(
            data["partition_key_fields"]
        ),
        canonical_sort_key_fields=tuple(
            data["canonical_sort_key_fields"]
        ),
        schema_column_order=tuple(
            data["schema_column_order"]
        ),
        digest_algorithm=data["digest_algorithm"],
        leaf_serializer=data["leaf_serializer"],
    )


def ensure_trace_edges_manifest_sidecar(
    root: Path, manifest: TraceEdgeManifest
) -> Path:
    if not isinstance(manifest, TraceEdgeManifest):
        raise TraceEdgeValidationError(
            "manifest must be a TraceEdgeManifest"
        )
    p = trace_edges_manifest_sidecar_path(root)
    if p.is_file():
        existing = read_trace_edges_manifest_sidecar(root)
        if existing != manifest:
            raise TraceEdgeManifestMismatchError(
                "existing trace-edge manifest sidecar at "
                f"{p} differs from supplied manifest"
            )
        return p
    return write_trace_edges_manifest_sidecar(root, manifest)


# ---------------------------------------------------------------------------
# TraceEdgePartitionKey
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceEdgePartitionKey:
    """Three-field trace-edge partition key.

    ``period_id`` may be empty on the source record;
    in that case the partition path uses the literal
    placeholder ``period_id=unknown``. Use
    :meth:`from_record` to materialise the placeholder
    deterministically.
    """

    run_id: str
    period_id_or_unknown: str
    edge_category_label: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.run_id, str)
            or not self.run_id
        ):
            raise TraceEdgeValidationError(
                "run_id must be a non-empty string"
            )
        if (
            not isinstance(self.period_id_or_unknown, str)
            or not self.period_id_or_unknown
        ):
            raise TraceEdgeValidationError(
                "period_id_or_unknown must be a non-empty "
                "string"
            )
        if (
            self.edge_category_label
            not in TRACE_EDGE_CATEGORY_LABELS
        ):
            raise TraceEdgeValidationError(
                "edge_category_label must be in "
                f"{sorted(TRACE_EDGE_CATEGORY_LABELS)!r}; "
                f"got {self.edge_category_label!r}"
            )

    @classmethod
    def from_record(
        cls, record: TraceEdgeRecord
    ) -> TraceEdgePartitionKey:
        return cls(
            run_id=record.run_id,
            period_id_or_unknown=(
                record.period_id
                if record.period_id
                else PERIOD_ID_UNKNOWN_PATH_VALUE
            ),
            edge_category_label=record.edge_category_label,
        )

    def to_path_segments(self) -> tuple[str, str, str]:
        return (
            f"run_id={self.run_id}",
            f"period_id={self.period_id_or_unknown}",
            f"edge_category={self.edge_category_label}",
        )

    def to_partition_dir(self, root: Path) -> Path:
        return Path(root).joinpath(
            *self.to_path_segments()
        )


# ---------------------------------------------------------------------------
# TraceEdgeWriteResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceEdgeWriteResult:
    partition_key: TraceEdgePartitionKey
    part_file_path: Path
    part_file_index: int
    record_count: int
    bytes_written: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_part_file_name(index: int) -> str:
    if index < 1:
        raise ValueError(
            "part-file index must be >= 1"
        )
    return (
        f"{TRACE_EDGES_PART_FILE_NAME_PREFIX}"
        f"{index:0{TRACE_EDGES_PART_FILE_INDEX_DIGITS}d}"
        f"{TRACE_EDGES_PART_FILE_NAME_SUFFIX}"
    )


def _list_part_files_sorted(
    partition_dir: Path,
) -> tuple[Path, ...]:
    if not partition_dir.is_dir():
        return ()
    candidates = [
        p
        for p in partition_dir.iterdir()
        if p.is_file()
        and p.name.startswith(
            TRACE_EDGES_PART_FILE_NAME_PREFIX
        )
        and p.name.endswith(
            TRACE_EDGES_PART_FILE_NAME_SUFFIX
        )
    ]
    return tuple(sorted(candidates, key=lambda p: p.name))


# ---------------------------------------------------------------------------
# TraceEdgePartitionWriter
# ---------------------------------------------------------------------------


@dataclass
class TraceEdgePartitionWriter:
    """Per-partition append-only JSONL writer for
    trace edges. Mirrors v1.28.2
    :class:`world.event_log_writer.EventLogPartitionWriter`.
    """

    root_path: Path
    partition_key: TraceEdgePartitionKey
    manifest: TraceEdgeManifest = field(
        default_factory=default_trace_edge_manifest
    )
    _autocreate_dirs: bool = field(default=True)

    def __post_init__(self) -> None:
        if not isinstance(
            self.root_path, (str, Path)
        ) or not str(self.root_path):
            raise TraceEdgeValidationError(
                "root_path must be a non-empty path"
            )
        self.root_path = Path(self.root_path)
        if not isinstance(
            self.partition_key, TraceEdgePartitionKey
        ):
            raise TraceEdgeValidationError(
                "partition_key must be a "
                "TraceEdgePartitionKey"
            )
        if not isinstance(
            self.manifest, TraceEdgeManifest
        ):
            raise TraceEdgeValidationError(
                "manifest must be a TraceEdgeManifest"
            )
        # Eager sidecar verification.
        if (
            self.root_path.is_dir()
            and trace_edges_manifest_sidecar_path(
                self.root_path
            ).is_file()
        ):
            existing = read_trace_edges_manifest_sidecar(
                self.root_path
            )
            if existing != self.manifest:
                raise TraceEdgeManifestMismatchError(
                    "existing trace-edge manifest sidecar "
                    f"at {trace_edges_manifest_sidecar_path(self.root_path)} "
                    "differs from supplied manifest"
                )

    @property
    def partition_dir(self) -> Path:
        return self.partition_key.to_partition_dir(
            self.root_path
        )

    @property
    def sealed_marker(self) -> Path:
        return (
            self.partition_dir
            / TRACE_EDGES_SEALED_MARKER_FILE_NAME
        )

    def is_sealed(self) -> bool:
        return self.sealed_marker.exists()

    def list_part_files(self) -> tuple[Path, ...]:
        return _list_part_files_sorted(self.partition_dir)

    def _next_part_file_path(self) -> Path:
        existing = self.list_part_files()
        if not existing:
            return (
                self.partition_dir
                / _format_part_file_name(1)
            )
        max_index = 0
        for p in existing:
            stem = p.name[
                len(
                    TRACE_EDGES_PART_FILE_NAME_PREFIX
                ):-len(TRACE_EDGES_PART_FILE_NAME_SUFFIX)
            ]
            try:
                idx = int(stem)
            except ValueError:
                continue
            if idx > max_index:
                max_index = idx
        return (
            self.partition_dir
            / _format_part_file_name(max_index + 1)
        )

    def append(
        self, records: Iterable[TraceEdgeRecord]
    ) -> TraceEdgeWriteResult:
        if self.is_sealed():
            raise TraceEdgeSealedPartitionError(
                "Partition is sealed; cannot append: "
                f"{self.partition_dir}"
            )
        materialised = tuple(records)
        if not materialised:
            raise TraceEdgeValidationError(
                "append() requires at least one record"
            )
        for r in materialised:
            if not isinstance(r, TraceEdgeRecord):
                raise TraceEdgeValidationError(
                    "append() expects TraceEdgeRecord "
                    f"instances; got {type(r).__name__}"
                )
            rk = TraceEdgePartitionKey.from_record(r)
            if rk != self.partition_key:
                raise TraceEdgeValidationError(
                    f"record partition_key {rk!r} does "
                    "not match writer's partition_key "
                    f"{self.partition_key!r}"
                )
        if self._autocreate_dirs:
            self.partition_dir.mkdir(
                parents=True, exist_ok=True
            )
        elif not self.partition_dir.is_dir():
            raise TraceEdgeValidationError(
                "partition directory does not exist and "
                "autocreate is disabled: "
                f"{self.partition_dir}"
            )
        ensure_trace_edges_manifest_sidecar(
            self.root_path, self.manifest
        )
        part_path = self._next_part_file_path()
        if part_path.exists():
            raise TraceEdgeWriteError(
                "next part-file path already exists; "
                "refusing to overwrite: "
                f"{part_path}"
            )
        sorted_records = sorted(
            materialised,
            key=lambda r: r.canonical_sort_key,
        )
        lines: list[bytes] = []
        for r in sorted_records:
            d = trace_edge_to_canonical_dict(r)
            lines.append(
                serialize_canonical_json(
                    d, sort_keys=False
                )
            )
            lines.append(b"\n")
        body = b"".join(lines)
        with part_path.open("xb") as fh:
            fh.write(body)
        stem = part_path.name[
            len(TRACE_EDGES_PART_FILE_NAME_PREFIX):
            -len(TRACE_EDGES_PART_FILE_NAME_SUFFIX)
        ]
        return TraceEdgeWriteResult(
            partition_key=self.partition_key,
            part_file_path=part_path,
            part_file_index=int(stem),
            record_count=len(sorted_records),
            bytes_written=len(body),
        )

    def seal(self) -> None:
        if self.is_sealed():
            raise TraceEdgeAlreadySealedError(
                "partition already sealed: "
                f"{self.partition_dir}"
            )
        if not self.partition_dir.is_dir():
            self.partition_dir.mkdir(
                parents=True, exist_ok=True
            )
        with self.sealed_marker.open("xb") as fh:
            fh.write(b"")


# ---------------------------------------------------------------------------
# Reader helper
# ---------------------------------------------------------------------------


def read_trace_edge_part_file(
    part_path: Path,
) -> tuple[dict[str, Any], ...]:
    """Read one trace-edge JSONL part file and return
    its records as a tuple of plain dicts. Used by
    v1.29.3 projection + v1.29.5 digest helpers."""
    raw = Path(part_path).read_bytes()
    if not raw:
        return ()
    out: list[dict[str, Any]] = []
    for line in raw.split(b"\n"):
        if not line:
            continue
        out.append(json.loads(line))
    return tuple(out)


# ---------------------------------------------------------------------------
# Tamper-evidence digest hook (delegates to v1.29.1 boundary)
# ---------------------------------------------------------------------------


def compute_partition_trace_edge_leaf_digest(
    root: Path,
    partition_key: TraceEdgePartitionKey,
    manifest: TraceEdgeManifest | None = None,
) -> str:
    """Walk a single trace-edge partition's part files
    in lex-ascending order, parse canonical JSONL,
    reconstruct :class:`TraceEdgeRecord` instances, and
    route through
    :func:`world.trace_edges.compute_trace_edge_leaf_digest`
    (the single trace-edge leaf-digest boundary).

    Returns lowercase hex SHA-256.
    """
    if not isinstance(
        partition_key, TraceEdgePartitionKey
    ):
        raise TypeError(
            "partition_key must be a TraceEdgePartitionKey"
        )
    if manifest is None:
        manifest = default_trace_edge_manifest()
    if not isinstance(manifest, TraceEdgeManifest):
        raise TypeError(
            "manifest must be a TraceEdgeManifest"
        )
    partition_dir = partition_key.to_partition_dir(
        Path(root)
    )
    part_files = _list_part_files_sorted(partition_dir)
    records: list[TraceEdgeRecord] = []
    for pf in part_files:
        for d in read_trace_edge_part_file(pf):
            records.append(_record_dict_to_record(d))
    return compute_trace_edge_leaf_digest(
        records,
        schema_version=manifest.trace_edge_schema_version,
    )


def _record_dict_to_record(
    d: dict[str, Any],
) -> TraceEdgeRecord:
    return TraceEdgeRecord(
        edge_id=d["edge_id"],
        run_id=d["run_id"],
        source_event_id=d["source_event_id"],
        target_event_id=d["target_event_id"],
        edge_type_label=d["edge_type_label"],
        edge_category_label=d["edge_category_label"],
        evidence_ref_ids=tuple(d["evidence_ref_ids"]),
        citation_ids=tuple(d["citation_ids"]),
        actor_id=d["actor_id"],
        period_id=d["period_id"],
        provenance_kind=d["provenance_kind"],
        confidence_label=d["confidence_label"],
        notes=d["notes"],
        canonical_sort_key=d["canonical_sort_key"],
    )


# ---------------------------------------------------------------------------
# File-byte stability helper (used in v1.29.5 tests)
# ---------------------------------------------------------------------------


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


__all__ = [
    "PERIOD_ID_UNKNOWN_PATH_VALUE",
    "TRACE_EDGES_MANIFEST_SIDECAR_FILE_NAME",
    "TRACE_EDGES_PART_FILE_INDEX_DIGITS",
    "TRACE_EDGES_PART_FILE_NAME_PREFIX",
    "TRACE_EDGES_PART_FILE_NAME_SUFFIX",
    "TRACE_EDGES_SEALED_MARKER_FILE_NAME",
    "TraceEdgeAlreadySealedError",
    "TraceEdgeManifest",
    "TraceEdgeManifestMismatchError",
    "TraceEdgePartitionKey",
    "TraceEdgePartitionWriter",
    "TraceEdgeSealedPartitionError",
    "TraceEdgeValidationError",
    "TraceEdgeWriteError",
    "TraceEdgeWriteResult",
    "compute_partition_trace_edge_leaf_digest",
    "default_trace_edge_manifest",
    "ensure_trace_edges_manifest_sidecar",
    "file_sha256",
    "read_trace_edge_part_file",
    "read_trace_edges_manifest_sidecar",
    "trace_edges_manifest_sidecar_path",
    "write_trace_edges_manifest_sidecar",
]
