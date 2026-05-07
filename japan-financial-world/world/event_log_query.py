"""
v1.28.7 — Optional DuckDB validation query boundary.

Defines the future DuckDB-based validation query
surface as a soft-import boundary. v1.28.7 ships **no**
hard dependency on DuckDB. The module imports
successfully on a stock Python install; DuckDB is
loaded lazily via `importlib.import_module` only when a
function that actually requires it is called.

Local-first only: no Postgres, no Redis, no Kafka, no
external service. DuckDB (when available) is used as an
in-process embedded query engine over local Parquet /
JSONL artifacts.

The v1.28.7 boundary surface is descriptive and tiny:

- :func:`count_records_by_partition` — count records in
  each partition (synthetic). Future.
- :func:`count_records_by_record_type` — count records
  grouped by record_type. Future.
- :func:`validate_no_duplicate_event_id` — assert no
  duplicate event_id across a tiny file set. Future.

All three raise :class:`OptionalDependencyUnavailable`
when DuckDB is absent and
:class:`DuckDBBackendNotImplementedError` when DuckDB
is present (the boundary is **declared** at v1.28.7 but
**not implemented**).

DuckDB is **never** routed through the canonical
digest path. Digest computation continues to flow
through :func:`world.event_log_schema.compute_leaf_digest`
exclusively (per design pin §F.1).
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any

from world.event_log_columnar import (
    OptionalDependencyUnavailable,
)


# ---------------------------------------------------------------------------
# Boundary errors
# ---------------------------------------------------------------------------


class DuckDBBackendNotImplementedError(NotImplementedError):
    """Raised when a v1.28.7 DuckDB-based entry point
    is called: the boundary is **declared** at
    v1.28.7 but **not implemented**."""


# ---------------------------------------------------------------------------
# Availability + lazy load
# ---------------------------------------------------------------------------


def is_duckdb_available() -> bool:
    return importlib.util.find_spec("duckdb") is not None


def _require_duckdb() -> Any:
    """Lazy-import duckdb; raise a clear unavailable
    error if the package is not installed."""
    if not is_duckdb_available():
        raise OptionalDependencyUnavailable(
            "duckdb is not installed; install the "
            "optional 'scale' extra to enable the "
            "DuckDB validation query boundary at a "
            "future v1.28.x sub-milestone."
        )
    return importlib.import_module("duckdb")


# ---------------------------------------------------------------------------
# Boundary entry points (declared; not implemented at v1.28.7)
# ---------------------------------------------------------------------------


def count_records_by_partition(
    root: Path,
    *,
    manifest: Any = None,
) -> Any:
    """**Future** — count records in each partition
    under ``root``. Returns a mapping
    ``{(year_month, sector_id, record_type): count}``
    when implemented.

    The implementation must run entirely locally; no
    external service may be contacted.
    """
    _require_duckdb()
    raise DuckDBBackendNotImplementedError(
        "count_records_by_partition is the v1.28.7 "
        "DuckDB validation boundary; not implemented "
        "at v1.28.7."
    )


def count_records_by_record_type(
    root: Path,
    *,
    manifest: Any = None,
) -> Any:
    """**Future** — count records grouped by
    `record_type` under ``root``. Returns a mapping
    ``{record_type: count}`` when implemented."""
    _require_duckdb()
    raise DuckDBBackendNotImplementedError(
        "count_records_by_record_type is the v1.28.7 "
        "DuckDB validation boundary; not implemented "
        "at v1.28.7."
    )


def validate_no_duplicate_event_id(
    root: Path,
    *,
    manifest: Any = None,
) -> Any:
    """**Future** — assert that no two records share
    the same `event_id` across the entire event log.
    Raises :class:`ValueError` (or a domain-specific
    subclass) if duplicates are found; returns
    ``None`` when implemented and clean."""
    _require_duckdb()
    raise DuckDBBackendNotImplementedError(
        "validate_no_duplicate_event_id is the "
        "v1.28.7 DuckDB validation boundary; not "
        "implemented at v1.28.7."
    )


__all__ = [
    "DuckDBBackendNotImplementedError",
    "OptionalDependencyUnavailable",
    "count_records_by_partition",
    "count_records_by_record_type",
    "is_duckdb_available",
    "validate_no_duplicate_event_id",
]
