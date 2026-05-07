"""
v1.28.7 — Optional DuckDB validation query boundary
pin tests.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from world.event_log_query import (
    DuckDBBackendNotImplementedError,
    OptionalDependencyUnavailable,
    count_records_by_partition,
    count_records_by_record_type,
    is_duckdb_available,
    validate_no_duplicate_event_id,
)


# ---------------------------------------------------------------------------
# Default-import safety
# ---------------------------------------------------------------------------


def test_module_imports_without_duckdb() -> None:
    from world import event_log_query  # noqa: F401


def test_module_text_has_no_top_level_duckdb_import() -> None:
    from world import event_log_query

    src = inspect.getsource(event_log_query)
    for tok in (
        "\nimport duckdb",
        "\nfrom duckdb",
    ):
        assert tok not in src


def test_module_text_has_no_external_service_imports() -> None:
    """Local-first boundary: no Kafka / Postgres /
    Redis / cloud-SDK *imports* in module text. (The
    docstring is allowed to mention them in the
    "do NOT use" position.)"""
    from world import event_log_query

    src = inspect.getsource(event_log_query)
    for tok in (
        "import kafka",
        "from kafka",
        "import psycopg",
        "from psycopg",
        "import asyncpg",
        "from asyncpg",
        "import redis",
        "from redis",
        "import boto3",
        "from boto3",
        "from google.cloud",
        "from azure.storage",
    ):
        assert tok not in src


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------


def test_is_duckdb_available_returns_bool() -> None:
    assert isinstance(is_duckdb_available(), bool)


# ---------------------------------------------------------------------------
# Future entry points raise clear errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fn",
    [
        count_records_by_partition,
        count_records_by_record_type,
        validate_no_duplicate_event_id,
    ],
)
def test_query_boundary_unavailable_or_not_implemented(
    tmp_path: Path, fn
) -> None:
    if is_duckdb_available():
        with pytest.raises(
            DuckDBBackendNotImplementedError
        ):
            fn(tmp_path)
    else:
        with pytest.raises(
            OptionalDependencyUnavailable
        ):
            fn(tmp_path)


def test_duckdb_backend_not_implemented_is_not_implemented_error() -> None:
    assert issubclass(
        DuckDBBackendNotImplementedError,
        NotImplementedError,
    )


# ---------------------------------------------------------------------------
# DuckDB never routed through canonical digest path
# ---------------------------------------------------------------------------


def test_query_module_does_not_call_or_import_compute_leaf_digest() -> None:
    """Per design pin §K + §F.1, DuckDB is never used
    for the canonical digest path. The module text
    must not *import* or *call* `compute_leaf_digest`.
    Docstring mentions in the "never used here"
    position are allowed."""
    from world import event_log_query

    src = inspect.getsource(event_log_query)
    # No import line.
    assert "import compute_leaf_digest" not in src
    assert (
        "from world.event_log_schema import" not in src
    )
    # No callable invocation site `compute_leaf_digest(`.
    assert "compute_leaf_digest(" not in src


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


def test_module_exports_match_design_pin() -> None:
    from world import event_log_query

    expected = {
        "DuckDBBackendNotImplementedError",
        "OptionalDependencyUnavailable",
        "count_records_by_partition",
        "count_records_by_record_type",
        "is_duckdb_available",
        "validate_no_duplicate_event_id",
    }
    assert set(event_log_query.__all__) == expected


# ---------------------------------------------------------------------------
# Optional duckdb test
# ---------------------------------------------------------------------------


def test_duckdb_present_path_raises_not_implemented_error() -> None:
    if not is_duckdb_available():
        pytest.skip("duckdb is not installed")
    with pytest.raises(DuckDBBackendNotImplementedError):
        count_records_by_partition(Path("."))


# ---------------------------------------------------------------------------
# Default test suite must pass without duckdb
# ---------------------------------------------------------------------------


def test_default_test_suite_does_not_require_duckdb() -> None:
    """Sanity: this test runs in every environment.
    The module-level import already succeeded."""
    from world import event_log_query  # noqa: F401
