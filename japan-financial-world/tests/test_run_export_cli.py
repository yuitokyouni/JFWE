"""
Tests for v1.19.2 CLI run exporter — ``examples/reference_world/
export_run_bundle.py``.

Pinned invariants:

- the CLI writes a JSON file whose top-level keys match the
  v1.19.1 ``RunExportBundle.to_dict()`` key set;
- two consecutive runs to two different output paths produce
  byte-identical JSON files (determinism);
- the four designed-but-not-executable profile labels
  (``monthly_reference`` / ``scenario_monthly`` /
  ``daily_display_only`` / ``future_daily_full_simulation``)
  exit non-zero with a stderr message containing ``"designed
  but not executable in v1.19.2"``;
- the v1.18.4 scenario selector labels other than
  ``none_baseline`` exit non-zero with a stderr message
  containing ``"not yet wired"``;
- the bundle JSON contains no ISO-style wall-clock timestamp
  pattern (``YYYY-MM-DDTHH:MM:SS``) — only deterministic
  ``simulation_date`` / quarter-end ``YYYY-MM-DD`` strings are
  permitted;
- the bundle JSON contains no absolute path (no ``/tmp/``,
  ``/Users/``, ``/home/``, no the ``--out`` path);
- ``ledger_excerpt`` length is at most 20 entries (the
  v1.19.2 cap);
- ``boundary_flags`` carries the v1.19.0 default 8-flag set;
- ``world.run_export.FORBIDDEN_RUN_EXPORT_FIELD_NAMES`` are
  absent at every depth in the JSON;
- the CLI module imports no FastAPI / Flask / Rails / aiohttp
  / tornado / browser names — pinned by a module-text scan;
- the CLI module does not mutate ``PriceBook`` — pinned by
  snapshotting prices on a separately seeded kernel before /
  after a CLI invocation;
- the default-fixture ``living_world_digest`` (per
  ``tests/test_living_reference_world.py::_seed_kernel`` /
  ``_run_default``) stays at the v1.18.last-pinned value after
  a CLI invocation;
- jurisdiction-neutral identifier scan over module + test text.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from world.run_export import FORBIDDEN_RUN_EXPORT_FIELD_NAMES, RunExportBundle


# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------


# ``japan-financial-world/`` (so ``python -m
# examples.reference_world.export_run_bundle`` resolves).
_REPO_DIR = Path(__file__).resolve().parent.parent

_CLI_MODULE_PATH = (
    _REPO_DIR
    / "examples"
    / "reference_world"
    / "export_run_bundle.py"
)


_DEFAULT_FIXTURE_LIVING_WORLD_DIGEST: str = (
    "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf"
    "0648a92cc961401b705897c"
)


# ---------------------------------------------------------------------------
# CLI invocation helper
# ---------------------------------------------------------------------------


def _run_cli(
    *args: str,
    expect_success: bool = True,
) -> subprocess.CompletedProcess:
    cp = subprocess.run(
        [
            sys.executable,
            "-m",
            "examples.reference_world.export_run_bundle",
            *args,
        ],
        cwd=str(_REPO_DIR),
        capture_output=True,
        text=True,
    )
    if expect_success and cp.returncode != 0:
        raise AssertionError(
            "CLI exited non-zero unexpectedly: "
            f"rc={cp.returncode} stdout={cp.stdout!r} "
            f"stderr={cp.stderr!r}"
        )
    return cp


def _default_invocation(out_path: Path) -> subprocess.CompletedProcess:
    return _run_cli(
        "--profile",
        "quarterly_default",
        "--regime",
        "constrained",
        "--scenario",
        "none_baseline",
        "--out",
        str(out_path),
        "--quiet",
    )


# ---------------------------------------------------------------------------
# Behavior tests
# ---------------------------------------------------------------------------


def _expected_bundle_to_dict_keys() -> set[str]:
    """Reference key set, derived from the v1.19.1
    :meth:`RunExportBundle.to_dict` output on a minimal sample
    bundle. We avoid ``__dataclass_fields__`` because the
    v1.19.1 dataclass also declares ``ClassVar`` schema-meta
    fields (``REQUIRED_STRING_FIELDS`` / ``LABEL_FIELDS`` /
    ``PAYLOAD_FIELDS``) which Python's ``from __future__ import
    annotations`` mode keeps in the dataclass-field map even
    though they are not data fields."""
    sample = RunExportBundle(
        bundle_id="run_bundle:test:1",
        run_profile_label="quarterly_default",
        regime_label="constrained",
        selected_scenario_label="none_baseline",
        period_count=0,
        digest="x" * 64,
    )
    return set(sample.to_dict().keys())


def test_quarterly_default_constrained_writes_parsable_json(
    tmp_path: Path,
) -> None:
    out = tmp_path / "fwe_run_bundle.json"
    _default_invocation(out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # Top-level keys match the v1.19.1 ``RunExportBundle.to_dict()``
    # key set.
    assert set(data.keys()) == _expected_bundle_to_dict_keys()


def test_two_runs_to_two_paths_are_byte_identical(
    tmp_path: Path,
) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _default_invocation(a)
    _default_invocation(b)
    bytes_a = a.read_bytes()
    bytes_b = b.read_bytes()
    assert bytes_a == bytes_b
    # Sanity: payload is non-trivial.
    assert len(bytes_a) > 100


@pytest.mark.parametrize(
    "deferred_profile",
    [
        "monthly_reference",
        "scenario_monthly",
        "daily_display_only",
        "future_daily_full_simulation",
    ],
)
def test_designed_but_not_executable_profiles_exit_non_zero(
    tmp_path: Path, deferred_profile: str
) -> None:
    out = tmp_path / "fwe_run_bundle.json"
    cp = _run_cli(
        "--profile",
        deferred_profile,
        "--regime",
        "constrained",
        "--scenario",
        "none_baseline",
        "--out",
        str(out),
        expect_success=False,
    )
    assert cp.returncode != 0
    assert "designed but not executable in v1.19.2" in cp.stderr
    assert not out.exists()


def test_unsupported_scenario_exits_non_zero(tmp_path: Path) -> None:
    out = tmp_path / "fwe_run_bundle.json"
    cp = _run_cli(
        "--profile",
        "quarterly_default",
        "--regime",
        "constrained",
        "--scenario",
        "rate_repricing_driver",
        "--out",
        str(out),
        expect_success=False,
    )
    assert cp.returncode != 0
    assert "not yet wired" in cp.stderr
    assert not out.exists()


def test_unsupported_regime_exits_non_zero(tmp_path: Path) -> None:
    out = tmp_path / "fwe_run_bundle.json"
    cp = _run_cli(
        "--profile",
        "quarterly_default",
        "--regime",
        "neutral_drift",
        "--scenario",
        "none_baseline",
        "--out",
        str(out),
        expect_success=False,
    )
    assert cp.returncode != 0
    assert "regime" in cp.stderr.lower()
    assert not out.exists()


def test_bundle_json_has_no_iso_wall_clock_timestamp(
    tmp_path: Path,
) -> None:
    """The v1.19.0 stable_for_replay default has no wall-clock
    field, and the v1.19.2 CLI strips ``timestamp`` /
    ``record_id`` from every ledger excerpt entry."""
    out = tmp_path / "fwe_run_bundle.json"
    _default_invocation(out)
    text = out.read_text(encoding="utf-8")
    match = re.search(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", text
    )
    assert match is None, (
        "v1.19.2 bundle JSON must not contain an ISO wall-clock "
        f"timestamp; first match: {match.group() if match else ''!r}"
    )


def test_bundle_json_contains_no_absolute_paths(
    tmp_path: Path,
) -> None:
    """The bundle must not embed ``--out`` or any local absolute
    path. Keep this check loose: only validate against the
    common roots and against the actual output path."""
    out = tmp_path / "fwe_run_bundle.json"
    _default_invocation(out)
    text = out.read_text(encoding="utf-8")
    assert "/tmp/" not in text
    assert "/Users/" not in text
    assert "/home/" not in text
    assert str(out) not in text
    assert str(tmp_path) not in text


def test_ledger_excerpt_at_most_twenty_records(tmp_path: Path) -> None:
    out = tmp_path / "fwe_run_bundle.json"
    _default_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    excerpt = data["ledger_excerpt"]
    assert isinstance(excerpt, dict)
    records = excerpt.get("records", [])
    assert isinstance(records, list)
    assert len(records) <= 20


def test_boundary_flags_carry_v1_19_0_default_eight(
    tmp_path: Path,
) -> None:
    out = tmp_path / "fwe_run_bundle.json"
    _default_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    flags = data["boundary_flags"]
    expected_flags = {
        "synthetic_only",
        "no_price_formation",
        "no_trading",
        "no_investment_advice",
        "no_real_data",
        "no_japan_calibration",
        "no_llm_execution",
        "display_or_export_only",
    }
    assert expected_flags <= set(flags.keys())
    for k in expected_flags:
        assert flags[k] is True


def _walk_for_forbidden_keys(payload: object) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        for k, v in payload.items():
            if (
                isinstance(k, str)
                and k in FORBIDDEN_RUN_EXPORT_FIELD_NAMES
            ):
                found.add(k)
            found |= _walk_for_forbidden_keys(v)
    elif isinstance(payload, list):
        for entry in payload:
            found |= _walk_for_forbidden_keys(entry)
    return found


def test_bundle_json_contains_no_forbidden_field_names_at_any_depth(
    tmp_path: Path,
) -> None:
    out = tmp_path / "fwe_run_bundle.json"
    _default_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    found = _walk_for_forbidden_keys(data)
    assert not found, (
        "v1.19.0 forbidden field names appeared in the v1.19.2 "
        f"bundle JSON: {sorted(found)!r}"
    )


# ---------------------------------------------------------------------------
# Module-text discipline
# ---------------------------------------------------------------------------


_FORBIDDEN_BACKEND_TOKENS: tuple[str, ...] = (
    "fastapi",
    "flask",
    "rails",
    "aiohttp",
    "tornado",
    "starlette",
    "uvicorn",
    "gunicorn",
    "django",
    "selenium",
    "playwright",
)


def test_module_imports_no_backend_or_browser_names() -> None:
    text = _CLI_MODULE_PATH.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_BACKEND_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden backend / browser token {token!r} appears "
            f"in {_CLI_MODULE_PATH.name}"
        )


# ---------------------------------------------------------------------------
# No PriceBook mutation
# ---------------------------------------------------------------------------


def test_cli_does_not_mutate_price_book_of_separately_seeded_kernel(
    tmp_path: Path,
) -> None:
    """Snapshot a separately seeded kernel's prices, run the CLI
    (which builds its OWN fresh kernel), then re-check the
    separately seeded kernel's prices. The CLI must not move
    any source-of-truth book belonging to a kernel it does not
    own."""
    from datetime import date

    from world.clock import Clock
    from world.kernel import WorldKernel
    from world.ledger import Ledger
    from world.registry import Registry
    from world.scheduler import Scheduler
    from world.state import State

    kernel = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )
    snapshot_before = kernel.prices.snapshot()

    out = tmp_path / "fwe_run_bundle.json"
    _default_invocation(out)

    snapshot_after = kernel.prices.snapshot()
    assert snapshot_after == snapshot_before


# ---------------------------------------------------------------------------
# Default-fixture digest trip wire
# ---------------------------------------------------------------------------


def test_default_fixture_living_world_digest_unchanged_after_cli(
    tmp_path: Path,
) -> None:
    """The v1.18.last-pinned default-fixture digest must not move
    after a CLI invocation. The CLI builds its own fresh kernel
    via the v1.17.2 regime driver — it must never influence a
    separately seeded default sweep."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (  # type: ignore[import-not-found]
        _run_default,
        _seed_kernel,
    )

    out = tmp_path / "fwe_run_bundle.json"
    _default_invocation(out)

    k = _seed_kernel()
    r = _run_default(k)
    assert (
        living_world_digest(k, r)
        == _DEFAULT_FIXTURE_LIVING_WORLD_DIGEST
    )


# ---------------------------------------------------------------------------
# Success-line shape
# ---------------------------------------------------------------------------


def test_success_line_includes_path_profile_regime_digest(
    tmp_path: Path,
) -> None:
    out = tmp_path / "fwe_run_bundle.json"
    cp = _run_cli(
        "--profile",
        "quarterly_default",
        "--regime",
        "constrained",
        "--scenario",
        "none_baseline",
        "--out",
        str(out),
    )
    line = cp.stdout.strip()
    assert line.startswith("exported run bundle: ")
    assert str(out) in line
    assert "profile=quarterly_default" in line
    assert "regime=constrained" in line
    # 12-char digest prefix.
    digest_match = re.search(r"digest=([0-9a-f]{12})\b", line)
    assert digest_match is not None


def test_quiet_flag_suppresses_success_line(tmp_path: Path) -> None:
    out = tmp_path / "fwe_run_bundle.json"
    cp = _default_invocation(out)
    assert cp.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Jurisdiction-neutral scan
# ---------------------------------------------------------------------------


_JURISDICTION_TOKENS: tuple[str, ...] = (
    "toyota",
    "mufg",
    "smbc",
    "mizuho",
    "boj",
    "fsa",
    "jpx",
    "gpif",
    "tse",
    "nikkei",
    "topix",
    "sony",
    "jgb",
    "nyse",
    "nasdaq",
)


def test_module_jurisdiction_neutral_scan() -> None:
    text = _CLI_MODULE_PATH.read_text(encoding="utf-8").lower()
    for token in _JURISDICTION_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            f"{_CLI_MODULE_PATH.name}"
        )


def test_test_file_jurisdiction_neutral_scan() -> None:
    """The token list itself appears in this file; scan the file
    excluding the literal table tuple."""
    text = Path(__file__).read_text(encoding="utf-8").lower()
    table_start = text.find("_jurisdiction_tokens: tuple[str, ...] = (")
    assert table_start != -1
    table_end = text.find(")", table_start)
    assert table_end != -1
    text_minus_table = text[:table_start] + text[table_end + 1 :]
    for token in _JURISDICTION_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text_minus_table) is None, (
            f"forbidden token {token!r} appears in this test file"
        )
