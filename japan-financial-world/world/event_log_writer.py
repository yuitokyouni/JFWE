"""
v1.28.2 — Append-only local event-log writer (JSONL).

Standard-library-only, filesystem-backed prototype writer
for the future scale substrate per
[`docs/v1_28_scale_substrate_event_log_columnar_merkle.md`](../docs/v1_28_scale_substrate_event_log_columnar_merkle.md)
§I (append-only physical enforcement).

v1.28.2 ships:

- :class:`EventLogPartitionKey` — three-field partition key
  with deterministic path projection.
- :class:`EventLogPartitionWriter` — per-partition append-
  only writer with monotonic zero-padded part-file index
  and per-partition seal marker.
- :class:`EventLogWriteResult` — frozen dataclass returned
  from each successful append.
- Reader helper :func:`read_partition_part_file` for
  v1.28.4 Merkle leaf digest reuse.

v1.28.2 explicitly does NOT ship:

- Parquet / Polars / DuckDB / PyArrow / xxhash / Rust /
  PyO3 — none imported, none referenced.
- Manifest sidecar — that is v1.28.3.
- Inner / root Merkle digest — that is v1.28.4.
- Materialised view — that is v1.28.8.
- WorldKernel binding — the writer is not exposed on the
  kernel; every existing v1.21.last canonical
  `living_world_digest` value remains byte-identical.

Path layout (binding, per design pin §D.1):

    <root>/
      year_month=<YYYY_MM>/
        sector_id=<synthetic_sector_id>/
          record_type=<record_type>/
            part-000001.jsonl
            part-000002.jsonl
            _SEALED   (optional, per-partition marker)

The seal marker is an empty file. Once present in a
partition directory, that partition refuses further
appends.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Iterable

from world.event_log_schema import (
    EventLogManifest,
    EventLogRecord,
    event_log_record_to_canonical_dict,
    serialize_canonical_json,
)


# ---------------------------------------------------------------------------
# Constants (binding for v1.28.2)
# ---------------------------------------------------------------------------


SEALED_MARKER_FILE_NAME: str = "_SEALED"
PART_FILE_NAME_PREFIX: str = "part-"
PART_FILE_INDEX_DIGITS: int = 6
PART_FILE_NAME_SUFFIX: str = ".jsonl"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class EventLogWriteError(Exception):
    """Base class for v1.28.2 writer errors."""


class SealedPartitionWriteError(EventLogWriteError):
    """Raised when an append is attempted on a sealed
    partition."""


class AlreadySealedError(EventLogWriteError):
    """Raised when ``seal()`` is called on a partition that
    has already been sealed (idempotent re-seal is
    forbidden; explicit re-seal is a likely caller bug)."""


class EventLogValidationError(EventLogWriteError):
    """Raised when an append's records do not match the
    writer's partition key."""


# ---------------------------------------------------------------------------
# EventLogPartitionKey
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventLogPartitionKey:
    """Three-field partition key.

    Mirrors the v1.28.0 §D.1 partition shape:

        year_month=<YYYY_MM>/sector_id=<…>/record_type=<…>

    The path projection is deterministic and is the only
    sanctioned way to derive the partition directory under
    a given event-log root.
    """

    year_month: str
    sector_id: str
    record_type: str

    REQUIRED_FIELDS: ClassVar[tuple[str, ...]] = (
        "year_month",
        "sector_id",
        "record_type",
    )

    def __post_init__(self) -> None:
        for fname in self.REQUIRED_FIELDS:
            value = getattr(self, fname)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{fname} must be a non-empty string"
                )

    @classmethod
    def from_record(
        cls, record: EventLogRecord
    ) -> EventLogPartitionKey:
        return cls(
            year_month=record.year_month,
            sector_id=record.sector_id,
            record_type=record.record_type,
        )

    def to_path_segments(self) -> tuple[str, str, str]:
        return (
            f"year_month={self.year_month}",
            f"sector_id={self.sector_id}",
            f"record_type={self.record_type}",
        )

    def to_partition_dir(self, root: Path) -> Path:
        return Path(root).joinpath(*self.to_path_segments())


# ---------------------------------------------------------------------------
# EventLogWriteResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventLogWriteResult:
    """Frozen result of one successful append."""

    partition_key: EventLogPartitionKey
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
        f"{PART_FILE_NAME_PREFIX}"
        f"{index:0{PART_FILE_INDEX_DIGITS}d}"
        f"{PART_FILE_NAME_SUFFIX}"
    )


def _list_part_files_sorted(partition_dir: Path) -> tuple[Path, ...]:
    """List part files in lex-ascending order (the canonical
    sort for digest determinism per §F.2.2)."""
    if not partition_dir.is_dir():
        return ()
    candidates = [
        p
        for p in partition_dir.iterdir()
        if p.is_file()
        and p.name.startswith(PART_FILE_NAME_PREFIX)
        and p.name.endswith(PART_FILE_NAME_SUFFIX)
    ]
    return tuple(sorted(candidates, key=lambda p: p.name))


# ---------------------------------------------------------------------------
# EventLogPartitionWriter
# ---------------------------------------------------------------------------


@dataclass
class EventLogPartitionWriter:
    """Per-partition append-only JSONL writer.

    The writer enforces:

    - **Monotonic per-partition part-file index.** Each
      ``append(...)`` creates a new part file with an
      index strictly greater than every existing part
      file's index.
    - **Sealed partitions refuse further appends.** Once
      ``seal()`` has been called, any further
      ``append(...)`` raises
      :class:`SealedPartitionWriteError`.
    - **Existing part files are never rewritten.** A new
      append never opens an existing part file for write.
    - **Deterministic JSONL contents.** Records in a
      single append are sorted by ``canonical_sort_key``
      and serialised through the v1.28.1 canonical
      serializer (one record per line, ``"\\n"``-
      separated, terminated with a trailing newline).
    """

    root_path: Path
    partition_key: EventLogPartitionKey
    manifest: EventLogManifest
    _autocreate_dirs: bool = field(default=True)

    def __post_init__(self) -> None:
        if not isinstance(
            self.root_path, (str, Path)
        ) or not str(self.root_path):
            raise EventLogValidationError(
                "root_path must be a non-empty path"
            )
        self.root_path = Path(self.root_path)
        if not isinstance(
            self.partition_key, EventLogPartitionKey
        ):
            raise EventLogValidationError(
                "partition_key must be an "
                "EventLogPartitionKey"
            )
        if not isinstance(self.manifest, EventLogManifest):
            raise EventLogValidationError(
                "manifest must be an EventLogManifest"
            )

    # -- path helpers -----------------------------------------------

    @property
    def partition_dir(self) -> Path:
        return self.partition_key.to_partition_dir(
            self.root_path
        )

    @property
    def sealed_marker(self) -> Path:
        return self.partition_dir / SEALED_MARKER_FILE_NAME

    def is_sealed(self) -> bool:
        return self.sealed_marker.exists()

    def list_part_files(self) -> tuple[Path, ...]:
        return _list_part_files_sorted(self.partition_dir)

    def _next_part_file_path(self) -> Path:
        existing = self.list_part_files()
        if not existing:
            return self.partition_dir / _format_part_file_name(1)
        # Each filename is ``part-NNNNNN.jsonl``; parse the
        # numeric segment to find the maximum index.
        max_index = 0
        for p in existing:
            stem = p.name[len(PART_FILE_NAME_PREFIX):
                          -len(PART_FILE_NAME_SUFFIX)]
            try:
                idx = int(stem)
            except ValueError:
                continue
            if idx > max_index:
                max_index = idx
        return self.partition_dir / _format_part_file_name(
            max_index + 1
        )

    # -- append ----------------------------------------------------

    def append(
        self, records: Iterable[EventLogRecord]
    ) -> EventLogWriteResult:
        """Append ``records`` to a NEW part file in this
        partition.

        Refuses to write if the partition is sealed.
        Refuses records whose partition key does not match
        ``self.partition_key``.
        Sorts records by ``canonical_sort_key`` before
        serialising — the in-file order is canonical and
        deterministic.
        """
        if self.is_sealed():
            raise SealedPartitionWriteError(
                "Partition is sealed; cannot append: "
                f"{self.partition_dir}"
            )
        materialised = tuple(records)
        if not materialised:
            raise EventLogValidationError(
                "append() requires at least one record"
            )
        for r in materialised:
            if not isinstance(r, EventLogRecord):
                raise EventLogValidationError(
                    "append() expects EventLogRecord "
                    f"instances; got {type(r).__name__}"
                )
            rk = EventLogPartitionKey.from_record(r)
            if rk != self.partition_key:
                raise EventLogValidationError(
                    "record partition_key "
                    f"{rk!r} does not match writer's "
                    f"partition_key {self.partition_key!r}"
                )
        if self._autocreate_dirs:
            self.partition_dir.mkdir(
                parents=True, exist_ok=True
            )
        elif not self.partition_dir.is_dir():
            raise EventLogValidationError(
                "partition directory does not exist and "
                "autocreate is disabled: "
                f"{self.partition_dir}"
            )
        part_path = self._next_part_file_path()
        if part_path.exists():
            # Defensive: should be impossible because
            # the index is monotonic.
            raise EventLogWriteError(
                "next part-file path already exists; "
                "refusing to overwrite: "
                f"{part_path}"
            )
        sorted_records = sorted(
            materialised,
            key=lambda r: r.canonical_sort_key,
        )
        # Build the JSONL body in memory first, then write
        # atomically (open-write-close — no in-place edit
        # of existing files).
        lines: list[bytes] = []
        for r in sorted_records:
            d = event_log_record_to_canonical_dict(
                r,
                column_order=(
                    self.manifest.schema_column_order
                ),
            )
            lines.append(serialize_canonical_json(d))
            lines.append(b"\n")
        body = b"".join(lines)
        with part_path.open("xb") as fh:  # x = exclusive
            fh.write(body)
        # Recover the index for the result dataclass.
        stem = part_path.name[len(PART_FILE_NAME_PREFIX):
                              -len(PART_FILE_NAME_SUFFIX)]
        return EventLogWriteResult(
            partition_key=self.partition_key,
            part_file_path=part_path,
            part_file_index=int(stem),
            record_count=len(sorted_records),
            bytes_written=len(body),
        )

    # -- seal ------------------------------------------------------

    def seal(self) -> None:
        """Place the seal marker. Refuses to re-seal."""
        if self.is_sealed():
            raise AlreadySealedError(
                "partition already sealed: "
                f"{self.partition_dir}"
            )
        if not self.partition_dir.is_dir():
            # Sealing an empty/never-written partition is
            # allowed for symmetry, but we still need the
            # directory to hold the marker.
            self.partition_dir.mkdir(
                parents=True, exist_ok=True
            )
        # Touch the marker as an empty file. Use exclusive
        # open so a concurrent seal is detected.
        with self.sealed_marker.open("xb") as fh:
            fh.write(b"")


# ---------------------------------------------------------------------------
# Reader helper (used by v1.28.4 Merkle leaf digest)
# ---------------------------------------------------------------------------


def read_partition_part_file(
    part_path: Path,
) -> tuple[dict[str, Any], ...]:
    """Read one JSONL part file and return its records as a
    tuple of plain dicts.

    The dicts preserve the canonical column order written
    by the writer (Python's ``json.loads`` preserves dict
    insertion order; ``json.dumps`` with the v1.28.1
    canonical serializer's ``sort_keys=False`` writes in
    the manifest's ``schema_column_order``).

    Empty file → empty tuple. Trailing newline tolerated.
    """
    raw = Path(part_path).read_bytes()
    if not raw:
        return ()
    out: list[dict[str, Any]] = []
    for line in raw.split(b"\n"):
        if not line:
            continue
        out.append(json.loads(line))
    return tuple(out)


__all__ = [
    "AlreadySealedError",
    "EventLogPartitionKey",
    "EventLogPartitionWriter",
    "EventLogValidationError",
    "EventLogWriteError",
    "EventLogWriteResult",
    "PART_FILE_INDEX_DIGITS",
    "PART_FILE_NAME_PREFIX",
    "PART_FILE_NAME_SUFFIX",
    "SEALED_MARKER_FILE_NAME",
    "SealedPartitionWriteError",
    "read_partition_part_file",
]
