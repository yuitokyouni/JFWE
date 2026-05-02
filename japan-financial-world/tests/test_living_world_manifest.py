"""
Tests for v1.9.2 living-world reproducibility manifest.

Pins the v1.9.2 contract for ``build_living_world_manifest`` and
``write_living_world_manifest``:

- the manifest carries every required field and the right
  ``manifest_version`` / ``run_type`` constants;
- the manifest's ``living_world_digest`` matches the standalone
  ``living_world_digest(kernel, result)``;
- counts (period / firm / investor / bank / created / infra /
  per-period total) match the result;
- a missing-git environment doesn't crash the builder;
- the writer produces deterministic JSON byte-identically across
  consecutive writes;
- the writer creates parent directories;
- the writer is atomic (no partial file on disk if the encode
  step itself fails — checked via the temp-file pattern);
- building / writing the manifest does not mutate any kernel
  book or the ledger length;
- the CLI ``--manifest`` flag writes a valid manifest with the
  right digest.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from datetime import date
from typing import Any

import pytest

from world.clock import Clock
from world.exposures import ExposureRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.living_world_report import build_living_world_trace_report
from world.reference_living_world import (
    LivingReferenceWorldResult,
    run_living_reference_world,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.variables import ReferenceVariableSpec, VariableObservation

from examples.reference_world.living_world_manifest import (
    MANIFEST_VERSION,
    RUN_TYPE,
    _git_probe,
    build_living_world_manifest,
    write_living_world_manifest,
)
from examples.reference_world.living_world_replay import (
    LIVING_WORLD_BOUNDARY_STATEMENT,
    living_world_digest,
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


_FIRMS = (
    "firm:reference_manufacturer_a",
    "firm:reference_retailer_b",
)
_INVESTORS = ("investor:reference_pension_a",)
_BANKS = ("bank:reference_megabank_a",)
_PERIODS = ("2026-03-31", "2026-06-30")


def _seed_kernel() -> WorldKernel:
    k = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )
    for vid, vgroup in (
        ("variable:reference_fx_pair_a", "fx"),
        ("variable:reference_long_rate_10y", "rates"),
    ):
        k.variables.add_variable(
            ReferenceVariableSpec(
                variable_id=vid,
                variable_name=vid,
                variable_group=vgroup,
                variable_type="level",
                source_space_id="external",
                canonical_unit="index",
                frequency="QUARTERLY",
                observation_kind="released",
            )
        )
        for q in ("2026-01-15", "2026-04-15"):
            k.variables.add_observation(
                VariableObservation(
                    observation_id=f"obs:{vid}:{q}",
                    variable_id=vid,
                    as_of_date=q,
                    value=100.0,
                    unit="index",
                    vintage_id=f"{q}_initial",
                )
            )
    k.exposures.add_exposure(
        ExposureRecord(
            exposure_id="exposure:investor_a:fx",
            subject_id=_INVESTORS[0],
            subject_type="investor",
            variable_id="variable:reference_fx_pair_a",
            exposure_type="translation",
            metric="portfolio_translation_exposure",
            direction="mixed",
            magnitude=0.4,
        )
    )
    k.exposures.add_exposure(
        ExposureRecord(
            exposure_id="exposure:bank_a:funding",
            subject_id=_BANKS[0],
            subject_type="bank",
            variable_id="variable:reference_long_rate_10y",
            exposure_type="funding_cost",
            metric="debt_service_burden",
            direction="positive",
            magnitude=0.5,
        )
    )
    return k


def _seeded_run() -> tuple[WorldKernel, LivingReferenceWorldResult]:
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRMS,
        investor_ids=_INVESTORS,
        bank_ids=_BANKS,
        period_dates=_PERIODS,
    )
    return k, r


# ---------------------------------------------------------------------------
# Manifest shape + required fields
# ---------------------------------------------------------------------------


_REQUIRED_MANIFEST_FIELDS: frozenset[str] = frozenset(
    {
        "manifest_version",
        "run_type",
        "git_sha",
        "git_dirty",
        "git_status",
        "python_version",
        "platform",
        "input_profile",
        "preset_name",
        "period_count",
        "firm_count",
        "investor_count",
        "bank_count",
        "variable_count",
        "exposure_count",
        "ledger_record_count_before",
        "ledger_record_count_after",
        "created_record_count",
        "infra_record_count",
        "per_period_record_count_total",
        "living_world_digest",
        "boundary_statement",
        "summary",
    }
)


def test_manifest_carries_every_required_field():
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    missing = _REQUIRED_MANIFEST_FIELDS - set(manifest.keys())
    assert missing == set(), f"missing fields: {missing}"


def test_manifest_version_and_run_type_constants():
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    assert manifest["manifest_version"] == MANIFEST_VERSION
    assert manifest["manifest_version"] == "living_world_manifest.v1"
    assert manifest["run_type"] == RUN_TYPE
    assert manifest["run_type"] == "living_reference_world"


def test_manifest_digest_matches_standalone_helper():
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    assert manifest["living_world_digest"] == living_world_digest(k, r)


def test_manifest_counts_match_result():
    k, r = _seeded_run()
    manifest = build_living_world_manifest(
        k,
        r,
        variable_count=2,
        exposure_count=2,
    )
    assert manifest["period_count"] == r.period_count
    assert manifest["firm_count"] == len(r.firm_ids)
    assert manifest["investor_count"] == len(r.investor_ids)
    assert manifest["bank_count"] == len(r.bank_ids)
    assert manifest["created_record_count"] == r.created_record_count
    assert (
        manifest["infra_record_count"]
        + manifest["per_period_record_count_total"]
        == r.created_record_count
    )
    assert manifest["variable_count"] == 2
    assert manifest["exposure_count"] == 2


def test_manifest_boundary_statement_matches_replay_constant():
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    assert manifest["boundary_statement"] == LIVING_WORLD_BOUNDARY_STATEMENT


def test_manifest_includes_report_digest_when_report_supplied():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    manifest = build_living_world_manifest(k, r, report=report)
    assert "report_digest" in manifest
    assert isinstance(manifest["report_digest"], str)
    assert len(manifest["report_digest"]) == 64


def test_manifest_omits_report_digest_when_report_absent():
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    assert "report_digest" not in manifest


# ---------------------------------------------------------------------------
# Defensive errors
# ---------------------------------------------------------------------------


def test_build_rejects_kernel_none():
    _, r = _seeded_run()
    with pytest.raises(ValueError):
        build_living_world_manifest(None, r)


def test_build_rejects_non_result():
    k = _seed_kernel()
    with pytest.raises(TypeError):
        build_living_world_manifest(k, {"not": "a result"})


# ---------------------------------------------------------------------------
# Git probe is best-effort
# ---------------------------------------------------------------------------


def test_git_probe_returns_status_dict():
    info = _git_probe()
    assert "sha" in info
    assert "dirty" in info
    assert "status" in info
    assert info["status"] in {"ok", "git_unavailable", "not_a_repo", "error"}


def test_git_unavailable_does_not_crash_manifest_build(monkeypatch):
    """Simulate a missing git binary by monkey-patching subprocess.run
    inside the manifest module to raise FileNotFoundError."""
    import examples.reference_world.living_world_manifest as manifest_mod

    def _no_git(*args, **kwargs):
        raise FileNotFoundError("git not installed")

    monkeypatch.setattr(manifest_mod.subprocess, "run", _no_git)
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    assert manifest["git_status"] == "git_unavailable"
    assert manifest["git_sha"] is None
    assert manifest["git_dirty"] is None
    # The rest of the manifest is still well-formed.
    assert manifest["manifest_version"] == MANIFEST_VERSION
    assert manifest["living_world_digest"] == living_world_digest(k, r)


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


def test_writer_produces_deterministic_json_across_consecutive_writes(tmp_path):
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    p1 = tmp_path / "m1.json"
    p2 = tmp_path / "m2.json"
    write_living_world_manifest(manifest, p1)
    write_living_world_manifest(manifest, p2)
    assert p1.read_bytes() == p2.read_bytes()


def test_writer_produces_indent_2_sorted_keys(tmp_path):
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    p = tmp_path / "m.json"
    write_living_world_manifest(manifest, p)
    text = p.read_text(encoding="utf-8")
    # Trailing newline.
    assert text.endswith("\n")
    # sort_keys=True: alphabetical top-level ordering. Spot-check
    # one ordering pair we know.
    assert text.find('"manifest_version"') < text.find('"run_type"')
    # And the JSON parses back identically.
    decoded = json.loads(text)
    assert decoded == manifest


def test_writer_creates_parent_directories(tmp_path):
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    nested = tmp_path / "a" / "b" / "c" / "manifest.json"
    write_living_world_manifest(manifest, nested)
    assert nested.is_file()
    decoded = json.loads(nested.read_text(encoding="utf-8"))
    assert decoded["living_world_digest"] == manifest["living_world_digest"]


def test_writer_uses_temp_sibling_pattern(tmp_path):
    """The writer must write through a temp sibling and rename to
    avoid leaving a half-written manifest at the target path. We
    can't easily simulate a crash mid-write, but we can check that
    after a successful write no `.tmp` file lingers."""
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    target = tmp_path / "m.json"
    write_living_world_manifest(manifest, target)
    assert target.is_file()
    assert not (tmp_path / "m.json.tmp").exists()


def test_writer_returns_path(tmp_path):
    k, r = _seeded_run()
    manifest = build_living_world_manifest(k, r)
    target = tmp_path / "m.json"
    returned = write_living_world_manifest(manifest, target)
    assert returned == target


# ---------------------------------------------------------------------------
# Read-only guarantee
# ---------------------------------------------------------------------------


def _capture_state(k: WorldKernel) -> dict[str, Any]:
    return {
        "ledger_length": len(k.ledger.records),
        "valuations": k.valuations.snapshot(),
        "prices": k.prices.snapshot(),
        "ownership": k.ownership.snapshot(),
        "contracts": k.contracts.snapshot(),
        "constraints": k.constraints.snapshot(),
        "exposures": k.exposures.snapshot(),
        "variables": k.variables.snapshot(),
        "institutions": k.institutions.snapshot(),
        "external_processes": k.external_processes.snapshot(),
        "relationships": k.relationships.snapshot(),
        "attention": k.attention.snapshot(),
        "routines": k.routines.snapshot(),
        "interactions": k.interactions.snapshot(),
        "signal_count": len(k.signals.all_signals()),
    }


def test_manifest_build_and_write_does_not_mutate_kernel(tmp_path):
    k, r = _seeded_run()
    before = _capture_state(k)
    manifest = build_living_world_manifest(k, r)
    write_living_world_manifest(manifest, tmp_path / "m.json")
    after = _capture_state(k)
    assert before == after


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


def test_cli_smoke_writes_valid_manifest(tmp_path):
    from examples.reference_world import run_living_reference_world as cli

    target = tmp_path / "cli_manifest.json"
    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.main(["--manifest", str(target)])
    out = buf.getvalue()

    # Operational trace still printed.
    assert "[setup]" in out
    assert "[manifest]" in out
    assert str(target) in out

    # File is valid JSON with the v1.9.2 schema.
    assert target.is_file()
    decoded = json.loads(target.read_text(encoding="utf-8"))
    assert decoded["manifest_version"] == MANIFEST_VERSION
    assert decoded["run_type"] == RUN_TYPE
    assert isinstance(decoded["living_world_digest"], str)
    assert len(decoded["living_world_digest"]) == 64
    assert (
        decoded["infra_record_count"]
        + decoded["per_period_record_count_total"]
        == decoded["created_record_count"]
    )


def test_cli_smoke_default_does_not_write_manifest(tmp_path):
    """Without --manifest, no file should be written and the
    operational trace should not include a [manifest] line."""
    from examples.reference_world import run_living_reference_world as cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.main([])
    out = buf.getvalue()
    assert "[setup]" in out
    assert "[manifest]" not in out
