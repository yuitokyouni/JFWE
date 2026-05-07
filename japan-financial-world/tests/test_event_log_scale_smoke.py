"""
v1.28.9 — Opt-in synthetic scale smoke run pin tests.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

# Importing the example tool module via the file path
# requires sys.path to include the source root, which
# the project's pyproject.toml already arranges.
from examples.tools.run_v1_28_scale_smoke import (
    ScaleSmokeRunSummary,
    main,
    run_scale_smoke,
)


# ---------------------------------------------------------------------------
# Tiny default smoke (runs in default pytest)
# ---------------------------------------------------------------------------


def test_tiny_smoke_run_completes(tmp_path: Path) -> None:
    summary = run_scale_smoke(
        firms=4,
        periods=3,
        seed="synthetic_test_001",
        output_dir=tmp_path / "smoke",
    )
    assert isinstance(summary, ScaleSmokeRunSummary)
    assert summary.records_written == 12
    # Each firm × period maps to one partition cell
    # (sector_id=industry:synthetic_NN where NN =
    # firm_idx % 6, year_month = quarter-end month).
    # With 4 firms × 3 periods, partitions = 4 * 3 = 12.
    assert summary.partitions_written == 12
    assert len(summary.root_digest) == 64
    assert summary.elapsed_seconds >= 0.0
    assert summary.on_disk_bytes > 0


def test_tiny_smoke_is_deterministic_for_same_seed(
    tmp_path: Path,
) -> None:
    a = run_scale_smoke(
        firms=4,
        periods=3,
        seed="synthetic_test_002",
        output_dir=tmp_path / "a",
    )
    b = run_scale_smoke(
        firms=4,
        periods=3,
        seed="synthetic_test_002",
        output_dir=tmp_path / "b",
    )
    assert a.root_digest == b.root_digest
    assert a.records_written == b.records_written
    assert (
        a.partitions_written == b.partitions_written
    )


def test_tiny_smoke_changed_seed_changes_root_digest(
    tmp_path: Path,
) -> None:
    a = run_scale_smoke(
        firms=4,
        periods=3,
        seed="seed_alpha",
        output_dir=tmp_path / "a",
    )
    b = run_scale_smoke(
        firms=4,
        periods=3,
        seed="seed_beta",
        output_dir=tmp_path / "b",
    )
    assert a.root_digest != b.root_digest


def test_tiny_smoke_changed_firms_changes_root_digest(
    tmp_path: Path,
) -> None:
    a = run_scale_smoke(
        firms=4,
        periods=3,
        seed="seed",
        output_dir=tmp_path / "a",
    )
    b = run_scale_smoke(
        firms=5,
        periods=3,
        seed="seed",
        output_dir=tmp_path / "b",
    )
    assert a.root_digest != b.root_digest


def test_tiny_smoke_optional_investors_and_banks(
    tmp_path: Path,
) -> None:
    summary = run_scale_smoke(
        firms=2,
        periods=2,
        investors=3,
        banks=1,
        seed="seed",
        output_dir=tmp_path / "smoke",
    )
    # 2*2 firm records + 3*2 investor records + 1*2 bank
    # records = 4 + 6 + 2 = 12.
    assert summary.records_written == 12


def test_tiny_smoke_invalid_firms_or_periods_raises(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError):
        run_scale_smoke(
            firms=0,
            periods=4,
            seed="s",
            output_dir=tmp_path / "x",
        )
    with pytest.raises(ValueError):
        run_scale_smoke(
            firms=4,
            periods=0,
            seed="s",
            output_dir=tmp_path / "x",
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_main_runs_with_tiny_args(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(
        [
            "--firms",
            "3",
            "--periods",
            "2",
            "--seed",
            "synthetic_cli_001",
            "--output",
            str(tmp_path / "cli_smoke"),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "v1.28.9 synthetic scale smoke run summary" in (
        captured.out
    )
    assert "root_digest" in captured.out


# ---------------------------------------------------------------------------
# Forbidden-scope: no real identifier / adapter / advice content
# ---------------------------------------------------------------------------


def test_smoke_module_no_real_identifiers_or_adapters() -> None:
    """The synthetic smoke module text must not import
    or reference any real-data adapter, real Japanese
    company name, or investment-advice term."""
    from examples.tools import run_v1_28_scale_smoke as mod

    src = inspect.getsource(mod).lower()
    for adapter in (
        "edinet",
        "tdnet",
        "j_quants",
        "jquants",
        "fsa_filing",
        "topix",
        "nikkei",
        "jpx",
        "edgar",
        "bloomberg",
        "refinitiv",
        "factset",
    ):
        assert f"import {adapter}" not in src
        assert f"from {adapter}" not in src
    for forbidden_term in (
        "buy_signal",
        "sell_signal",
        "target_price",
        "alpha_claim",
        "backtest_claim",
        "investment_advice",
        "ownership_percentage",
        "voting_power",
    ):
        # These must not appear as identifiers at all
        # (the v1.x forbidden-token sets cover field
        # names; this is a belt-and-braces check on
        # the smoke module itself).
        assert forbidden_term not in src


def test_smoke_module_uses_synthetic_archetype_suffix() -> None:
    """All sector ids start with ``industry:synthetic_``
    and all firm ids start with ``firm:synthetic_`` so
    no real identifier ever leaks into a generated
    record."""
    from examples.tools import run_v1_28_scale_smoke as mod

    src = inspect.getsource(mod)
    assert "industry:synthetic_" in src
    assert "firm:synthetic_" in src


def test_smoke_module_routes_through_v1_28_writer_and_merkle() -> None:
    """The smoke module must compose existing
    primitives rather than reimplement any. Imports
    from world.event_log_writer + world.event_log_merkle
    are the binding contract."""
    from examples.tools import run_v1_28_scale_smoke as mod

    src = inspect.getsource(mod)
    assert (
        "from world.event_log_writer import" in src
    )
    assert (
        "from world.event_log_merkle import" in src
    )
    assert (
        "from world.event_log_schema import" in src
    )


# ---------------------------------------------------------------------------
# Default test suite does not run heavy benchmark
# ---------------------------------------------------------------------------


def test_default_test_suite_does_not_run_3000_x_60_smoke() -> None:
    """Sanity: this file's @pytest.mark.scale below is
    excluded by the default ``addopts``. The default
    pytest run reaches this assert without running
    the heavy smoke. We verify the heavy-smoke
    function exists in this module (so CI definitely
    knows where to opt in) without invoking it."""
    # The heavy-smoke function is defined below in
    # this same module; its presence is what we check
    # — i.e. the opt-in entry point exists.
    g = globals()
    assert "test_3000x60_smoke_run_opt_in" in g
    target = g["test_3000x60_smoke_run_opt_in"]
    # Verify it carries the expected pytest markers
    # (scale / slow / benchmark).
    marks = {
        m.name
        for m in getattr(target, "pytestmark", [])
    }
    assert {"scale", "slow", "benchmark"} <= marks


# ---------------------------------------------------------------------------
# Opt-in heavy smoke (default-skipped via the `scale` marker)
# ---------------------------------------------------------------------------


@pytest.mark.scale
@pytest.mark.slow
@pytest.mark.benchmark
def test_3000x60_smoke_run_opt_in(tmp_path: Path) -> None:
    """Opt-in heavy smoke. Runs only under
    ``pytest -m scale`` (or equivalent). The default
    invocation excludes scale / slow / benchmark
    markers via the project's ``addopts``."""
    summary = run_scale_smoke(
        firms=3000,
        periods=60,
        seed="synthetic_opt_in_001",
        output_dir=tmp_path / "scale_3000x60",
    )
    assert summary.firms == 3000
    assert summary.periods == 60
    assert summary.records_written == 3000 * 60
    assert len(summary.root_digest) == 64
    # Performance is intentionally NOT asserted here —
    # see design pin §R: budgets are configurable per
    # hardware profile, never hard-coded.
