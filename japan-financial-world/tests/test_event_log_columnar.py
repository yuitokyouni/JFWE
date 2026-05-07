"""
v1.28.5 — Columnar backend boundary pin tests.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from world.event_log_columnar import (
    ColumnarBackendNotImplementedError,
    ColumnarBackendStatus,
    OptionalDependencyUnavailable,
    columnar_backend_status,
    is_duckdb_available,
    is_fastparquet_available,
    is_polars_available,
    is_pyarrow_available,
    read_partition_records,
    scan_partition_parquet,
    write_partition_parquet,
)


# ---------------------------------------------------------------------------
# Default-import safety
# ---------------------------------------------------------------------------


def test_module_imports_without_pyarrow_polars_duckdb() -> None:
    """v1.28.5 module must be import-safe regardless of
    optional-dependency availability. The check above
    (top-of-file imports) already passes; this test is
    a deliberate documentation of the contract."""
    from world import event_log_columnar  # noqa: F401


def test_module_text_contains_no_top_level_optional_imports() -> None:
    from world import event_log_columnar

    src = inspect.getsource(event_log_columnar)
    # No `import pyarrow` / `from pyarrow ...` lines.
    for tok in (
        "\nimport pyarrow",
        "\nfrom pyarrow",
        "\nimport polars",
        "\nfrom polars",
        "\nimport duckdb",
        "\nfrom duckdb",
        "\nimport fastparquet",
        "\nfrom fastparquet",
    ):
        assert tok not in src


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------


def test_availability_helpers_return_bool() -> None:
    for fn in (
        is_pyarrow_available,
        is_polars_available,
        is_duckdb_available,
        is_fastparquet_available,
    ):
        assert isinstance(fn(), bool)


def test_availability_helpers_use_find_spec_only() -> None:
    """The implementation must check via
    importlib.util.find_spec rather than `import` —
    otherwise an availability call could surface a
    user-visible ImportError stack."""
    from world import event_log_columnar

    src = inspect.getsource(event_log_columnar)
    assert "importlib.util.find_spec" in src or (
        "find_spec" in src
        and "from importlib.util import find_spec" in src
    )


def test_columnar_backend_status_dataclass() -> None:
    s = columnar_backend_status()
    assert isinstance(s, ColumnarBackendStatus)
    assert s.columnar_implementation_state == (
        "boundary-only-v1.28.5"
    )
    for f in (
        "pyarrow_available",
        "polars_available",
        "duckdb_available",
        "fastparquet_available",
    ):
        assert isinstance(getattr(s, f), bool)


# ---------------------------------------------------------------------------
# Future entry points raise the boundary error
# ---------------------------------------------------------------------------


def test_write_partition_parquet_raises_boundary_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(ColumnarBackendNotImplementedError):
        write_partition_parquet(tmp_path, [])


def test_scan_partition_parquet_raises_boundary_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(ColumnarBackendNotImplementedError):
        scan_partition_parquet(tmp_path)


def test_read_partition_records_raises_boundary_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(ColumnarBackendNotImplementedError):
        read_partition_records(tmp_path / "part.parquet")


def test_boundary_error_is_a_not_implemented_error() -> None:
    """Callers should be able to catch the boundary
    error generically via NotImplementedError too."""
    assert issubclass(
        ColumnarBackendNotImplementedError,
        NotImplementedError,
    )


# ---------------------------------------------------------------------------
# Optional-dependency-unavailable error class
# ---------------------------------------------------------------------------


def test_optional_dependency_unavailable_is_exception() -> None:
    assert issubclass(
        OptionalDependencyUnavailable, Exception
    )


# ---------------------------------------------------------------------------
# Module exports + boundary content
# ---------------------------------------------------------------------------


def test_module_exports_match_design_pin() -> None:
    from world import event_log_columnar

    expected = {
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
    }
    assert set(event_log_columnar.__all__) == expected


def test_module_does_not_create_any_parquet_artifact(
    tmp_path: Path,
) -> None:
    """v1.28.5 must not write any file to disk under
    its boundary entry points (they all raise)."""
    try:
        write_partition_parquet(tmp_path, [])
    except ColumnarBackendNotImplementedError:
        pass
    assert list(tmp_path.iterdir()) == []


def test_module_does_not_introduce_pyproject_optional_dependencies() -> None:
    """v1.28.5 must NOT add any optional extra to
    pyproject.toml. The columnar backend is a docs +
    test-gated boundary at this milestone."""
    pyproject = (
        Path(__file__).resolve().parent.parent.parent
        / "pyproject.toml"
    )
    src = pyproject.read_text(encoding="utf-8")
    # No `scale = [` extra introduced; no `pyarrow` /
    # `polars` / `duckdb` mention as a dependency.
    lower = src.lower()
    for tok in (
        "pyarrow",
        "polars",
        "duckdb",
        "fastparquet",
    ):
        assert tok not in lower
