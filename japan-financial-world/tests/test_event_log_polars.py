"""
v1.28.6 — Optional Polars scan boundary pin tests.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from world.event_log_polars import (
    OptionalDependencyUnavailable,
    PolarsBackendNotImplementedError,
    is_polars_available,
    polars_records_to_event_log_leaf_digest,
    scan_partition_with_polars,
)


# ---------------------------------------------------------------------------
# Default-import safety
# ---------------------------------------------------------------------------


def test_module_imports_without_polars() -> None:
    """v1.28.6 module must import without polars."""
    from world import event_log_polars  # noqa: F401


def test_module_text_has_no_top_level_polars_import() -> None:
    from world import event_log_polars

    src = inspect.getsource(event_log_polars)
    for tok in (
        "\nimport polars",
        "\nfrom polars",
    ):
        assert tok not in src


def test_module_text_has_no_pandas_csv_hashing() -> None:
    """The v1.28.0 design pin §F.1 forbids hashing
    pandas CSV output. Verify the module text
    contains no such pattern."""
    from world import event_log_polars

    src = inspect.getsource(event_log_polars).lower()
    for tok in (
        "to_csv(",
        "read_csv(",
        "pandas.dataframe",
        "pd.dataframe",
    ):
        assert tok not in src


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------


def test_is_polars_available_returns_bool() -> None:
    assert isinstance(is_polars_available(), bool)


# ---------------------------------------------------------------------------
# Future entry points raise the right error class
# ---------------------------------------------------------------------------


def test_scan_partition_with_polars_unavailable_raises_clear_error(
    tmp_path: Path,
) -> None:
    """Whichever path runs, the caller gets a clear
    error. If polars is not installed →
    OptionalDependencyUnavailable. If polars is
    installed → PolarsBackendNotImplementedError."""
    if is_polars_available():
        with pytest.raises(
            PolarsBackendNotImplementedError
        ):
            scan_partition_with_polars(tmp_path)
    else:
        with pytest.raises(
            OptionalDependencyUnavailable
        ):
            scan_partition_with_polars(tmp_path)


def test_polars_records_bridge_unavailable_raises_clear_error() -> None:
    if is_polars_available():
        with pytest.raises(
            PolarsBackendNotImplementedError
        ):
            polars_records_to_event_log_leaf_digest(
                None, manifest=None
            )
    else:
        with pytest.raises(
            OptionalDependencyUnavailable
        ):
            polars_records_to_event_log_leaf_digest(
                None, manifest=None
            )


# ---------------------------------------------------------------------------
# Single leaf-hash implementation pin
# ---------------------------------------------------------------------------


def test_polars_module_routes_through_compute_leaf_digest_boundary() -> None:
    """The Polars module must declare its dependency on
    `compute_leaf_digest` at module load. A static
    grep confirms the import line, which is the
    v1.28.0 §F.1 single-leaf-hash-implementation
    contract: no Polars-side independent hash code
    path."""
    from world import event_log_polars

    src = inspect.getsource(event_log_polars)
    assert "compute_leaf_digest" in src
    assert "from world.event_log_schema" in src


def test_polars_module_does_not_define_a_separate_hash_function() -> None:
    """No `def hash_…` or `def compute_…leaf…` other
    than the documented bridge."""
    from world import event_log_polars

    src = inspect.getsource(event_log_polars)
    # The only approved bridge:
    # `polars_records_to_event_log_leaf_digest`. No
    # other digest-producing function.
    forbidden_defs = (
        "def hash_records",
        "def compute_partition_leaf",
        "def compute_leaf_digest",
        "def merkle_leaf",
        "def sha256_partition",
    )
    for tok in forbidden_defs:
        assert tok not in src


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


def test_module_exports_match_design_pin() -> None:
    from world import event_log_polars

    expected = {
        "OptionalDependencyUnavailable",
        "PolarsBackendNotImplementedError",
        "is_polars_available",
        "polars_records_to_event_log_leaf_digest",
        "scan_partition_with_polars",
    }
    assert set(event_log_polars.__all__) == expected


def test_polars_backend_not_implemented_error_is_not_implemented_error() -> None:
    assert issubclass(
        PolarsBackendNotImplementedError,
        NotImplementedError,
    )


# ---------------------------------------------------------------------------
# Optional polars test (skipped if polars not present)
# ---------------------------------------------------------------------------


def test_polars_present_path_does_not_skip_under_lazy_import() -> None:
    """If polars is actually installed, the
    `_require_polars` helper succeeds and the
    boundary entry point still raises the
    not-implemented error (rather than crashing on
    an import)."""
    if not is_polars_available():
        pytest.skip("polars is not installed")
    # If we got here, polars is present.
    with pytest.raises(PolarsBackendNotImplementedError):
        scan_partition_with_polars(Path("."))


# ---------------------------------------------------------------------------
# Default test suite must pass without optional deps
# ---------------------------------------------------------------------------


def test_default_test_suite_does_not_require_polars() -> None:
    """Conditional sanity: this test runs in every
    environment. If polars is absent, the module-level
    import of `event_log_polars` already succeeded
    (the whole file would have failed to load
    otherwise). If polars is present, the test still
    runs."""
    from world import event_log_polars  # noqa: F401
