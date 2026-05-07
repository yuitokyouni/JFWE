"""
v1.28.6 — Optional Polars scan boundary + digest-order
guard.

Defines the future Polars-based scanning surface as a
soft-import boundary. v1.28.6 ships **no** hard
dependency on Polars. The module imports successfully
on a stock Python install; Polars is loaded lazily via
`importlib.import_module` only when a function that
actually requires it is called.

Any future Polars-based leaf-digest path **must route
through** :func:`world.event_log_schema.compute_leaf_digest`
(per design pin §F.1 — single leaf-hash implementation
in the project). The module text below contains no
independent hash construction. The single approved
helper is :func:`polars_records_to_event_log_leaf_digest`,
which uses Polars only as an ordered scan surface and
hands the records back to `compute_leaf_digest`.

Future surface:

- :func:`scan_partition_with_polars` — scan one
  partition's part files via `polars.scan_*` (when
  Polars is available). Future.
- :func:`polars_records_to_event_log_leaf_digest` —
  reconstruct EventLogRecord instances from a Polars
  DataFrame and route through `compute_leaf_digest`.
  The helper is the **only** approved Polars → digest
  bridge. Future.

Both raise :class:`OptionalDependencyUnavailable` when
Polars is absent. When Polars is present, both raise
:class:`PolarsBackendNotImplementedError` at v1.28.6 —
the actual scan implementation is deferred to a future
sub-milestone behind its own design pin.
"""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any

from world.event_log_columnar import (
    OptionalDependencyUnavailable,
)
from world.event_log_schema import (
    compute_leaf_digest as _compute_leaf_digest_boundary,
)


# ---------------------------------------------------------------------------
# Boundary errors
# ---------------------------------------------------------------------------


class PolarsBackendNotImplementedError(NotImplementedError):
    """Raised when a v1.28.6 Polars-based entry point is
    called: the boundary is **declared** at v1.28.6 but
    **not implemented**."""


# ---------------------------------------------------------------------------
# Availability + lazy load
# ---------------------------------------------------------------------------


def is_polars_available() -> bool:
    return importlib.util.find_spec("polars") is not None


def _require_polars() -> Any:
    """Lazy-import polars; raise a clear unavailable
    error if the package is not installed."""
    if not is_polars_available():
        raise OptionalDependencyUnavailable(
            "polars is not installed; install the "
            "optional 'scale' extra to enable the "
            "Polars boundary at a future v1.28.x "
            "sub-milestone."
        )
    return importlib.import_module("polars")


# ---------------------------------------------------------------------------
# Boundary entry points (declared; not implemented at v1.28.6)
# ---------------------------------------------------------------------------


def scan_partition_with_polars(
    partition_dir: Any,
    *,
    manifest: Any = None,
) -> Any:
    """**Future** — lazy-scan a partition's part files
    via Polars.

    A real implementation must:

    1. Use `polars.scan_*` lazy mode (no eager
       hydration of all rows into Python).
    2. Apply an explicit ``ORDER BY canonical_sort_key``
       (or equivalent sort) so the row order is the
       canonical sort order.
    3. Project columns in the manifest's
       ``schema_column_order``.
    4. Round-trip through
       :func:`polars_records_to_event_log_leaf_digest`
       to verify equivalence with the v1.28.4 JSONL
       leaf-digest baseline.
    """
    _require_polars()
    raise PolarsBackendNotImplementedError(
        "scan_partition_with_polars is the v1.28.6 "
        "Polars boundary; the scanner is not "
        "implemented at v1.28.6."
    )


def polars_records_to_event_log_leaf_digest(
    polars_dataframe: Any,
    *,
    manifest: Any,
) -> str:
    """**Future** — convert a Polars DataFrame of
    records to a leaf digest by routing through
    :func:`compute_leaf_digest`.

    This is the **only** approved Polars → digest
    bridge. A real implementation must:

    1. Iterate the DataFrame rows in the
       canonical-sort order.
    2. Reconstruct :class:`EventLogRecord` instances
       (per-row dataclass construction).
    3. Pass the records and the manifest to
       :func:`compute_leaf_digest`.
    4. Return its lowercase hex digest unchanged.

    The reference to ``_compute_leaf_digest_boundary``
    is module-level so a static check can detect that
    the digest path is **declared** to route through
    the v1.28.1 boundary even before the
    implementation is written.
    """
    _require_polars()
    # No-op reference to the boundary import so a
    # static reader / linter confirms the dependency
    # is declared.
    _ = _compute_leaf_digest_boundary
    raise PolarsBackendNotImplementedError(
        "polars_records_to_event_log_leaf_digest is "
        "the v1.28.6 Polars-to-digest bridge; not "
        "implemented at v1.28.6. When implemented, it "
        "must route through "
        "world.event_log_schema.compute_leaf_digest."
    )


__all__ = [
    "OptionalDependencyUnavailable",
    "PolarsBackendNotImplementedError",
    "is_polars_available",
    "polars_records_to_event_log_leaf_digest",
    "scan_partition_with_polars",
]
