"""
v1.28.5 — Columnar backend boundary (no hard
dependencies).

Defines the future Parquet / columnar boundary as a
named-only interface. v1.28.5 ships **no** Parquet
writer, **no** Parquet reader, **no** PyArrow / Polars /
DuckDB / fastparquet code path. The module is import-
safe on a stock Python install: it relies only on
:mod:`importlib.util.find_spec` for availability checks
and never imports an optional third-party package at
module load time.

The canonical prototype backend at v1.28.x remains
JSONL (v1.28.2 writer + v1.28.3 manifest sidecar +
v1.28.4 Merkle digest). The columnar boundary is
designed first; an actual implementation requires a
fresh design pin per the v1.28.0 sub-milestone
sequence.

Future surface (declared but not implemented at
v1.28.5):

- :func:`write_partition_parquet` — write one
  partition's records to a Parquet part file. Future.
- :func:`scan_partition_parquet` — lazy-scan a
  partition's Parquet part files. Future.
- :func:`read_partition_records` — read one part file
  back into a sequence of records. Future.

All three raise :class:`OptionalDependencyUnavailable`
at v1.28.5 unless their backing dependency is
actually installed AND a future design pin enables
them.

The user-facing dependency-availability surface is:

- :func:`is_pyarrow_available`,
- :func:`is_polars_available`,
- :func:`is_duckdb_available`,
- :func:`is_fastparquet_available`.

These check via ``importlib.util.find_spec`` only;
they never import the package.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Optional-dependency exceptions
# ---------------------------------------------------------------------------


class OptionalDependencyUnavailable(Exception):
    """Raised when a v1.28.5+ columnar backend is
    requested but its dependency is absent."""


class ColumnarBackendNotImplementedError(NotImplementedError):
    """Raised when a v1.28.5 columnar boundary entry
    point is called: the backend is **declared** at
    v1.28.5 but **not implemented**. v1.28.6 / v1.28.7
    or later may light up specific paths behind a
    fresh design pin."""


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------


def _is_module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def is_pyarrow_available() -> bool:
    return _is_module_available("pyarrow")


def is_polars_available() -> bool:
    return _is_module_available("polars")


def is_duckdb_available() -> bool:
    return _is_module_available("duckdb")


def is_fastparquet_available() -> bool:
    return _is_module_available("fastparquet")


# ---------------------------------------------------------------------------
# Columnar boundary descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ColumnarBackendStatus:
    """Frozen, read-only summary of the columnar
    backend availability + implementation state at
    v1.28.5."""

    pyarrow_available: bool
    polars_available: bool
    duckdb_available: bool
    fastparquet_available: bool
    columnar_implementation_state: str = (
        "boundary-only-v1.28.5"
    )


def columnar_backend_status() -> ColumnarBackendStatus:
    return ColumnarBackendStatus(
        pyarrow_available=is_pyarrow_available(),
        polars_available=is_polars_available(),
        duckdb_available=is_duckdb_available(),
        fastparquet_available=is_fastparquet_available(),
    )


# ---------------------------------------------------------------------------
# Future entry points (declared; not implemented at v1.28.5)
# ---------------------------------------------------------------------------


def write_partition_parquet(
    partition_dir: Path,
    records: Any,
    *,
    manifest: Any = None,
) -> Path:
    """**Future** — write one partition's records to a
    Parquet part file.

    v1.28.5 does not implement this. Callers must check
    :func:`is_pyarrow_available` (or equivalent) and
    accept a :class:`ColumnarBackendNotImplementedError`
    for now.

    A real implementation requires a fresh design pin
    that addresses: schema column order, deterministic
    null handling, list-column encoding, partition
    compaction policy, sealed-file enforcement under
    Parquet, and round-trip equivalence with the JSONL
    backend.
    """
    raise ColumnarBackendNotImplementedError(
        "write_partition_parquet is the v1.28.5 "
        "columnar boundary; the Parquet writer is "
        "not implemented at v1.28.5. JSONL remains "
        "the canonical prototype backend."
    )


def scan_partition_parquet(
    partition_dir: Path,
    *,
    manifest: Any = None,
) -> Any:
    """**Future** — lazy-scan a partition's Parquet
    part files. v1.28.5 does not implement this."""
    raise ColumnarBackendNotImplementedError(
        "scan_partition_parquet is the v1.28.5 "
        "columnar boundary; the Parquet scanner is "
        "not implemented at v1.28.5."
    )


def read_partition_records(
    part_path: Path,
    *,
    manifest: Any = None,
) -> Any:
    """**Future** — read one Parquet part file back
    into a sequence of records. v1.28.5 does not
    implement this."""
    raise ColumnarBackendNotImplementedError(
        "read_partition_records is the v1.28.5 "
        "columnar boundary; the Parquet reader is "
        "not implemented at v1.28.5."
    )


__all__ = [
    "ColumnarBackendNotImplementedError",
    "ColumnarBackendStatus",
    "OptionalDependencyUnavailable",
    "columnar_backend_status",
    "is_duckdb_available",
    "is_fastparquet_available",
    "is_polars_available",
    "is_pyarrow_available",
    "read_partition_records",
    "scan_partition_parquet",
    "write_partition_parquet",
]
