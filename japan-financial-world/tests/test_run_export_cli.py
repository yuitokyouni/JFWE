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
        # v1.19.3.1 reconciliation moved ``monthly_reference``
        # out of this list — it is now executable. The three
        # remaining labels stay designed-but-not-executable.
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


# v1.20.4 — licensed-taxonomy tokens scanned by the new
# scenario universe bundle test. Mirrors the v1.20.x test
# files' pattern so a downstream test-file scan can strip the
# literal table.
_LICENSED_TAXONOMY_TOKENS: tuple[str, ...] = (
    "gics",
    "msci",
    "factset",
    "bloomberg",
    "refinitiv",
)


def _strip_token_table(text: str, marker: str) -> str:
    """Return ``text`` with the first ``(...)`` literal block
    starting at ``marker`` removed. Used by
    :func:`test_test_file_jurisdiction_neutral_scan` to mask out
    its own token tables."""
    start = text.find(marker)
    if start == -1:
        return text
    end = text.find(")", start)
    if end == -1:
        return text
    return text[:start] + text[end + 1 :]


def test_module_jurisdiction_neutral_scan() -> None:
    text = _CLI_MODULE_PATH.read_text(encoding="utf-8").lower()
    for token in _JURISDICTION_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            f"{_CLI_MODULE_PATH.name}"
        )


def test_test_file_jurisdiction_neutral_scan() -> None:
    """The token lists themselves appear in this file; scan the
    file excluding the literal table tuples."""
    text = Path(__file__).read_text(encoding="utf-8").lower()
    text = _strip_token_table(
        text, "_jurisdiction_tokens: tuple[str, ...] = ("
    )
    text = _strip_token_table(
        text, "_licensed_taxonomy_tokens: tuple[str, ...] = ("
    )
    for token in _JURISDICTION_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in this test file"
        )


# ---------------------------------------------------------------------------
# v1.19.3.1 reconciliation — monthly_reference profile in the CLI
# ---------------------------------------------------------------------------


def _monthly_invocation(out_path: Path) -> subprocess.CompletedProcess:
    return _run_cli(
        "--profile",
        "monthly_reference",
        "--regime",
        "constrained",
        "--scenario",
        "none_baseline",
        "--out",
        str(out_path),
        "--quiet",
    )


def test_v1_19_3_1_monthly_reference_writes_parsable_json(
    tmp_path: Path,
) -> None:
    out = tmp_path / "fwe_run_bundle_monthly.json"
    _monthly_invocation(out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    # Top-level keys match the v1.19.1 RunExportBundle shape.
    assert set(data.keys()) == _expected_bundle_to_dict_keys()
    assert data["run_profile_label"] == "monthly_reference"
    assert data["regime_label"] == "constrained"
    assert data["selected_scenario_label"] == "none_baseline"
    # Default monthly fixture is 12 months.
    assert data["period_count"] == 12


def test_v1_19_3_1_monthly_reference_two_runs_byte_identical(
    tmp_path: Path,
) -> None:
    a = tmp_path / "monthly_a.json"
    b = tmp_path / "monthly_b.json"
    _monthly_invocation(a)
    _monthly_invocation(b)
    assert a.read_bytes() == b.read_bytes()
    # Sanity — payload non-trivial and larger than the
    # quarterly_default bundle.
    assert len(a.read_bytes()) > 100


def test_v1_19_3_1_monthly_reference_carries_information_arrival_summary(
    tmp_path: Path,
) -> None:
    out = tmp_path / "monthly.json"
    _monthly_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    summary = data["metadata"]["information_arrival_summary"]
    # Default fixture: 1 calendar, 51 scheduled releases / arrivals.
    assert summary["calendar_count"] == 1
    assert summary["scheduled_release_count"] == 51
    assert summary["arrival_count"] == 51
    # Per-family counts are sorted (deterministic dict order).
    family_keys = list(summary["per_indicator_family"].keys())
    assert family_keys == sorted(family_keys)
    # Coverage sanity: at least the seven default-fixture
    # indicator families are present.
    expected_families = {
        "central_bank_policy",
        "consumption_demand",
        "gdp_national_accounts",
        "inflation",
        "labor_market",
        "market_liquidity",
        "production_supply",
    }
    assert expected_families <= set(summary["per_indicator_family"].keys())


def test_v1_19_3_1_monthly_reference_carries_no_real_indicator_values(
    tmp_path: Path,
) -> None:
    """The information arrival summary records label counts only.
    No real indicator values, no real release dates, no LLM-prose
    fields may appear at any depth in the bundle.

    The v1.19.3 module-level test in
    ``tests/test_information_release.py`` already pins the
    absence of real institutional identifiers (the v1.19.0
    public-FWE jurisdiction-neutral list) in the underlying
    ``world/information_release.py`` module text; that invariant
    transitively holds for the bundle composed of those records'
    labels. This test verifies the value / LLM-field tokens for
    completeness, using word-boundary regex so the bundle's
    ``no_japan_calibration`` boundary flag (a *negation* flag,
    not a real-data field) is correctly excluded."""
    out = tmp_path / "monthly.json"
    _monthly_invocation(out)
    text = out.read_text(encoding="utf-8")
    forbidden_value_tokens = (
        "real_indicator_value",
        "cpi_value",
        "gdp_value",
        "policy_rate",
        "real_release_date",
        "llm_output",
        "llm_prose",
        "prompt_text",
    )
    for tok in forbidden_value_tokens:
        pattern = rf"\b{re.escape(tok)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden value token {tok!r} appears in monthly bundle"
        )
    # ``japan_calibration`` is forbidden as a bare field name but
    # appears as a SUBSTRING inside the v1.19.0 boundary flag
    # ``no_japan_calibration`` (a binding negation pin). Use
    # word-boundary regex so the substring match does not trip;
    # ``\b`` between word chars (``_`` and ``j``) does not match,
    # so ``\bjapan_calibration\b`` correctly rejects only a bare
    # field while allowing ``no_japan_calibration``.
    assert (
        re.search(r"\bjapan_calibration\b", text) is None
    ), "bare 'japan_calibration' field in monthly bundle"


def test_v1_19_3_1_monthly_reference_no_iso_wall_clock_timestamp(
    tmp_path: Path,
) -> None:
    """Same invariant as the quarterly_default test — the bundle
    must contain no ISO wall-clock timestamp inserted by the
    export module. Deterministic ``simulation_date``
    ``YYYY-MM-DD`` strings (e.g. ``2026-04-30``) are explicitly
    permitted."""
    out = tmp_path / "monthly.json"
    _monthly_invocation(out)
    text = out.read_text(encoding="utf-8")
    assert (
        re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", text)
        is None
    )


def test_v1_19_3_1_monthly_reference_contains_no_absolute_paths(
    tmp_path: Path,
) -> None:
    out = tmp_path / "monthly.json"
    _monthly_invocation(out)
    text = out.read_text(encoding="utf-8")
    # Filter out the test's own absolute path tokens — but assert
    # the bundle text contains no tokens that look like an
    # absolute path.
    assert "/tmp/" not in text
    assert "/Users/" not in text
    assert "/home/" not in text
    assert str(out) not in text


def test_v1_19_3_1_monthly_reference_does_not_move_quarterly_default_digest(
    tmp_path: Path,
) -> None:
    """Running the CLI on the monthly_reference profile builds
    its own fresh kernel; it must NOT move the canonical
    quarterly_default ``living_world_digest`` of a separately
    seeded default sweep."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _run_default,
        _seed_kernel,
    )

    _monthly_invocation(tmp_path / "monthly.json")
    k = _seed_kernel()
    r = _run_default(k)
    assert (
        living_world_digest(k, r)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )


def test_v1_19_3_1_monthly_reference_success_line_carries_profile_label(
    tmp_path: Path,
) -> None:
    out = tmp_path / "monthly.json"
    cp = _run_cli(
        "--profile",
        "monthly_reference",
        "--regime",
        "constrained",
        "--scenario",
        "none_baseline",
        "--out",
        str(out),
    )
    assert cp.returncode == 0
    assert "profile=monthly_reference" in cp.stdout
    assert "regime=constrained" in cp.stdout
    assert "exported run bundle:" in cp.stdout


def test_v1_19_3_1_executable_profiles_pin_includes_monthly_reference():
    """Pin the CLI module's executable-profile constant so a
    future drift back to the v1.19.2 single-profile shape fails
    loudly."""
    from examples.reference_world.export_run_bundle import (
        DESIGNED_BUT_NOT_EXECUTABLE_PROFILES,
        EXECUTABLE_PROFILES,
    )

    assert "quarterly_default" in EXECUTABLE_PROFILES
    assert "monthly_reference" in EXECUTABLE_PROFILES
    # v1.20.4 — scenario_monthly_reference_universe is now
    # executable.
    assert "scenario_monthly_reference_universe" in EXECUTABLE_PROFILES
    # The three remaining deferred labels.
    assert set(DESIGNED_BUT_NOT_EXECUTABLE_PROFILES) == {
        "scenario_monthly",
        "daily_display_only",
        "future_daily_full_simulation",
    }


# ---------------------------------------------------------------------------
# v1.20.4 — scenario_monthly_reference_universe profile in the CLI
# ---------------------------------------------------------------------------


_V1_20_4_PINNED_BUNDLE_DIGEST: str = (
    "ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf"
)


def _scenario_universe_invocation(
    out_path: Path,
    *,
    scenario: str = "credit_tightening_driver",
) -> subprocess.CompletedProcess:
    return _run_cli(
        "--profile",
        "scenario_monthly_reference_universe",
        "--regime",
        "constrained",
        "--scenario",
        scenario,
        "--out",
        str(out_path),
        "--quiet",
    )


def test_v1_20_4_scenario_universe_writes_parsable_json(
    tmp_path: Path,
) -> None:
    out = tmp_path / "fwe_scenario_universe_bundle.json"
    _scenario_universe_invocation(out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    # Top-level keys match the v1.19.1 RunExportBundle shape.
    assert set(data.keys()) == _expected_bundle_to_dict_keys()
    assert (
        data["run_profile_label"]
        == "scenario_monthly_reference_universe"
    )
    assert data["regime_label"] == "constrained"
    assert (
        data["selected_scenario_label"]
        == "credit_tightening_driver"
    )
    assert data["period_count"] == 12


def test_v1_20_4_scenario_universe_two_runs_byte_identical(
    tmp_path: Path,
) -> None:
    a = tmp_path / "scenario_a.json"
    b = tmp_path / "scenario_b.json"
    _scenario_universe_invocation(a)
    _scenario_universe_invocation(b)
    assert a.read_bytes() == b.read_bytes()
    assert len(a.read_bytes()) > 1000


def test_v1_20_4_scenario_universe_digest_pinned(
    tmp_path: Path,
) -> None:
    """Pin the CLI bundle digest so accidental drift in the
    canonical view, the orchestrator, or any of the v1.20.x
    storage books fails loudly."""
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["digest"] == _V1_20_4_PINNED_BUNDLE_DIGEST, (
        "v1.20.4 scenario universe bundle digest drifted; if "
        "intentional, update _V1_20_4_PINNED_BUNDLE_DIGEST and "
        "document the cause"
    )


def test_v1_20_4_scenario_universe_manifest_counts(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    m = data["manifest"]
    assert m["sector_count"] == 11
    assert m["firm_count"] == 11
    assert m["investor_count"] == 4
    assert m["bank_count"] == 3
    assert m["scheduled_scenario_application_count"] == 1
    assert m["scenario_application_count"] == 1
    assert m["scenario_context_shift_count"] == 2
    # 51 information arrivals across 12 months.
    assert m["information_arrival_count"] == 51
    # Hard guardrail: under 4000 records.
    assert m["record_count"] <= 4000
    # Boundary flags.
    assert m["synthetic_only"] is True
    assert m["no_backend"] is True
    assert m["no_ui_execution"] is True


def test_v1_20_4_scenario_universe_carries_reference_universe_section(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    ru = data["metadata"]["reference_universe"]
    assert (
        ru["reference_universe_id"]
        == "reference_universe:generic_11_sector"
    )
    assert ru["sector_count"] == 11
    assert ru["firm_count"] == 11
    assert ru["synthetic_only"] is True
    # 11 sector labels, all with the ``_like`` suffix.
    assert len(ru["sector_labels"]) == 11
    for sector_label in ru["sector_labels"]:
        assert sector_label.endswith("_like")
    # 11 firm profile ids and 11 firm ids.
    assert len(ru["firm_profile_ids"]) == 11
    assert len(ru["firm_ids"]) == 11
    # Sector sensitivity summary present and complete.
    assert len(ru["sector_sensitivity_summary"]) == 11


def test_v1_20_4_scenario_universe_carries_scenario_trace_section(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    st = data["scenario_trace"]
    # Ids and counts.
    assert (
        st["selected_scenario_label"]
        == "credit_tightening_driver"
    )
    assert len(st["scheduled_scenario_application_ids"]) == 1
    assert len(st["scenario_application_ids"]) == 1
    assert st["scenario_application_count"] == 1
    assert st["scenario_context_shift_count"] == 2
    # The credit_tightening family emits exactly two surfaces.
    assert set(st["context_surface_labels"]) == {
        "market_environment",
        "financing_review_surface",
    }
    assert set(st["shift_direction_labels"]) == {"tighten"}
    # Universe-wide affected sets — 11 sectors / 11 firms.
    assert len(st["affected_sector_ids"]) == 11
    assert len(st["affected_firm_profile_ids"]) == 11
    # v1.18.0 audit shape preserved.
    assert "rule_based_fallback" in st["reasoning_modes"]
    assert "future_llm_compatible" in st["reasoning_slots"]
    # Boundary flags merged AND view.
    bf = st["boundary_flags"]
    assert bf.get("no_actor_decision") is True
    assert bf.get("no_price_formation") is True
    assert bf.get("no_financing_execution") is True


def test_v1_20_4_scenario_universe_per_application_summary_includes_affected_ids(
    tmp_path: Path,
) -> None:
    """The per-application summary list inside scenario_trace
    must surface ``affected_sector_ids`` and
    ``affected_firm_profile_ids`` so a downstream UI consumer
    can render per-sector / per-firm impact."""
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    summaries = data["scenario_trace"][
        "scenario_application_summaries"
    ]
    assert len(summaries) == 1
    s = summaries[0]
    assert s["application_status_label"] == (
        "applied_as_context_shift"
    )
    assert s["scheduled_month_label"] == "month_04"
    assert s["scheduled_period_index"] == 3
    assert len(s["affected_sector_ids"]) == 11
    assert len(s["affected_firm_profile_ids"]) == 11
    assert s["emitted_context_shift_count"] == 2


def test_v1_20_4_scenario_universe_carries_information_arrival_summary(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    summary = data["metadata"]["information_arrival_summary"]
    assert summary["calendar_count"] == 1
    assert summary["scheduled_release_count"] == 51
    assert summary["arrival_count"] == 51
    # Mirrored on the timeline.
    assert (
        data["timeline"]["information_arrival_summary"][
            "arrival_count"
        ]
        == 51
    )


def test_v1_20_4_scenario_universe_carries_market_intent_and_financing_summaries(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    mi = data["market_intent"]
    # I × F × P = 4 × 11 × 12 = 528.
    assert mi["investor_market_intent_count"] == 528
    # F × P = 11 × 12 = 132 each.
    assert mi["aggregated_market_interest_count"] == 132
    assert mi["indicative_market_pressure_count"] == 132
    fin = data["financing"]
    # F × P = 132 each.
    assert fin["capital_structure_review_count"] == 132
    assert fin["financing_path_count"] == 132


def test_v1_20_4_scenario_universe_ledger_excerpt_capped_at_twenty(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    excerpt = data["ledger_excerpt"]
    assert len(excerpt["records"]) <= 20
    # The excerpt must include at least one scenario-related
    # record type so a reader can see the v1.20.x setup chain.
    types = {rec["record_type"] for rec in excerpt["records"]}
    scenario_types = {
        "reference_universe_profile_recorded",
        "generic_sector_reference_recorded",
        "synthetic_sector_firm_profile_recorded",
        "scenario_driver_template_recorded",
        "scenario_schedule_recorded",
        "scheduled_scenario_application_recorded",
    }
    assert types & scenario_types, (
        "ledger excerpt should include at least one v1.20.x "
        "setup record; got: " + ", ".join(sorted(types))
    )


def test_v1_20_4_scenario_universe_no_iso_wall_clock_timestamp(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    text = out.read_text(encoding="utf-8")
    assert (
        re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", text)
        is None
    )


def test_v1_20_4_scenario_universe_contains_no_absolute_paths(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    text = out.read_text(encoding="utf-8")
    assert "/tmp/" not in text
    assert "/Users/" not in text
    assert "/home/" not in text
    assert str(out) not in text


def test_v1_20_4_scenario_universe_carries_no_real_indicator_values(
    tmp_path: Path,
) -> None:
    """Same word-boundary scan as the monthly_reference test
    extended to the scenario universe bundle."""
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    text = out.read_text(encoding="utf-8")
    forbidden_value_tokens = (
        "real_indicator_value",
        "real_company_name",
        "real_sector_weight",
        "real_market_cap",
        "real_financial_value",
        "cpi_value",
        "gdp_value",
        "policy_rate",
        "real_release_date",
        "llm_output",
        "llm_prose",
        "prompt_text",
        "market_price",
        "predicted_index",
        "forecast_path",
        "expected_return",
        "target_price",
        "investment_advice",
    )
    for tok in forbidden_value_tokens:
        pattern = rf"\b{re.escape(tok)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {tok!r} appears in scenario universe bundle"
        )
    # Bare ``japan_calibration`` field rejected; the negation
    # flag ``no_japan_calibration`` is permitted.
    assert (
        re.search(r"\bjapan_calibration\b", text) is None
    )


def test_v1_20_4_scenario_universe_no_licensed_taxonomy_tokens(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scenario.json"
    _scenario_universe_invocation(out)
    text = out.read_text(encoding="utf-8").lower()
    # ``_LICENSED_TAXONOMY_TOKENS`` and ``_JURISDICTION_TOKENS``
    # are module-level tuples stripped from the test-file scan
    # by ``_strip_token_table``; the Japanese-jurisdiction
    # tokens live in ``_JURISDICTION_TOKENS`` and are checked
    # there too.
    for tok in _LICENSED_TAXONOMY_TOKENS:
        pattern = rf"\b{re.escape(tok)}\b"
        assert re.search(pattern, text) is None, (
            f"licensed-taxonomy token {tok!r} appears in scenario universe bundle"
        )
    for tok in _JURISDICTION_TOKENS:
        pattern = rf"\b{re.escape(tok)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction token {tok!r} appears in scenario universe bundle"
        )


def test_v1_20_4_scenario_universe_does_not_move_quarterly_default_digest(
    tmp_path: Path,
) -> None:
    """Running the CLI on the scenario universe profile builds
    its own fresh kernel; it must NOT move the canonical
    quarterly_default ``living_world_digest`` of a separately
    seeded default sweep."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _run_default,
        _seed_kernel,
    )

    _scenario_universe_invocation(tmp_path / "scenario.json")
    k = _seed_kernel()
    r = _run_default(k)
    assert (
        living_world_digest(k, r)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )


def test_v1_20_4_scenario_universe_does_not_move_monthly_reference_digest(
    tmp_path: Path,
) -> None:
    """Same invariant for monthly_reference."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _run_monthly_reference,
        _seed_kernel,
    )

    _scenario_universe_invocation(tmp_path / "scenario.json")
    k = _seed_kernel()
    r = _run_monthly_reference(k)
    assert (
        living_world_digest(k, r)
        == "75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d"
    )


def test_v1_20_4_scenario_universe_rejects_unrelated_scenario_label(
    tmp_path: Path,
) -> None:
    """``credit_tightening_driver`` is allowed only under the
    scenario universe profile. Pointing it at quarterly_default
    must still exit non-zero."""
    out = tmp_path / "scenario.json"
    cp = _run_cli(
        "--profile",
        "quarterly_default",
        "--regime",
        "constrained",
        "--scenario",
        "credit_tightening_driver",
        "--out",
        str(out),
        expect_success=False,
    )
    assert cp.returncode != 0
    assert not out.exists()


def test_v1_20_4_scenario_universe_rejects_unsupported_scenario(
    tmp_path: Path,
) -> None:
    """Any other scenario label must be rejected even under the
    universe profile."""
    out = tmp_path / "scenario.json"
    cp = _run_cli(
        "--profile",
        "scenario_monthly_reference_universe",
        "--regime",
        "constrained",
        "--scenario",
        "rate_repricing_driver",
        "--out",
        str(out),
        expect_success=False,
    )
    assert cp.returncode != 0
    assert (
        "is not supported under profile "
        "'scenario_monthly_reference_universe'"
    ) in cp.stderr
    assert not out.exists()


def test_v1_20_4_scenario_universe_accepts_none_baseline(
    tmp_path: Path,
) -> None:
    """The ``none_baseline`` scenario remains valid under the
    universe profile (returns a bundle with the same scenario
    application records, since the engine still fires the
    scheduled scenario regardless of the CLI selector label).
    The ``selected_scenario_label`` echoes the caller's
    selection."""
    out = tmp_path / "scenario_baseline.json"
    cp = _scenario_universe_invocation(
        out, scenario="none_baseline"
    )
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["selected_scenario_label"] == "none_baseline"
    # The engine still fires the scheduled scenario at month 4
    # (the v1.20.3 schedule is registered when the profile runs;
    # the CLI selector label is metadata only).
    assert data["scenario_trace"][
        "scenario_application_count"
    ] == 1


def test_v1_20_4_scenario_universe_designed_but_not_executable_unchanged(
    tmp_path: Path,
) -> None:
    """The three designed-but-not-executable labels stay
    designed-but-not-executable at v1.20.4."""
    for deferred_profile in (
        "scenario_monthly",
        "daily_display_only",
        "future_daily_full_simulation",
    ):
        out = tmp_path / f"deferred_{deferred_profile}.json"
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
        assert not out.exists()
