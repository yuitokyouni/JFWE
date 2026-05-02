"""
Tests for v1.9.2 living-world replay-determinism helpers.

Pins the v1.9.2 contract for ``canonicalize_living_world_result``
and ``living_world_digest``:

- canonical output is a JSON-friendly dict that round-trips through
  ``json.dumps`` / ``json.loads`` byte-identically;
- canonical output is **byte-equal** across two fresh kernels
  seeded identically;
- volatile ledger fields (``record_id`` / ``timestamp``) are
  excluded from the canonical view (``parent_record_ids`` is
  rewritten as ``parent_sequences``);
- the v1.9.1-prep infra-algebra
  (``infra_record_count + per_period_record_count_total ==
  created_record_count``) is preserved in the canonical view;
- digest is 64-char lowercase hex SHA-256 over
  ``json.dumps(canonical, sort_keys=True, separators=(",", ":"),
  ensure_ascii=False)``;
- digest is byte-equal across two fresh runs;
- digest changes when a canonical field changes;
- canonicalize / digest are read-only — every kernel book and the
  ledger length stay byte-identical;
- the ``LIVING_WORLD_BOUNDARY_STATEMENT`` constant matches the
  v1.9.1 reporter's verbatim string.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from world.clock import Clock
from world.exposures import ExposureRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.living_world_report import (
    build_living_world_trace_report,
    render_living_world_markdown,
)
from world.reference_living_world import (
    LivingReferenceWorldResult,
    run_living_reference_world,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.variables import ReferenceVariableSpec, VariableObservation

from examples.reference_world.living_world_replay import (
    CANONICAL_FORMAT_VERSION,
    LIVING_WORLD_BOUNDARY_STATEMENT,
    canonicalize_living_world_result,
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
# Canonical shape
# ---------------------------------------------------------------------------


def test_canonical_returns_dict_with_expected_keys():
    k, r = _seeded_run()
    canonical = canonicalize_living_world_result(k, r)
    expected_keys = {
        "format",
        "run_id",
        "period_count",
        "firm_ids",
        "investor_ids",
        "bank_ids",
        "firm_count",
        "investor_count",
        "bank_count",
        "ledger_record_count_before",
        "ledger_record_count_after",
        "created_record_count",
        "infra_record_count",
        "per_period_record_count_total",
        "created_record_ids",
        "record_type_counts",
        "per_period_summaries",
        "shared_selected_refs",
        "investor_only_refs",
        "bank_only_refs",
        "investor_selected_ref_counts",
        "bank_selected_ref_counts",
        "ledger_slice_canonical",
        "boundary_statement",
    }
    assert expected_keys.issubset(canonical.keys())
    assert canonical["format"] == CANONICAL_FORMAT_VERSION


def test_canonical_includes_boundary_statement():
    k, r = _seeded_run()
    canonical = canonicalize_living_world_result(k, r)
    assert canonical["boundary_statement"] == LIVING_WORLD_BOUNDARY_STATEMENT


def test_canonical_carries_infra_algebra():
    k, r = _seeded_run()
    canonical = canonicalize_living_world_result(k, r)
    assert (
        canonical["infra_record_count"]
        + canonical["per_period_record_count_total"]
        == canonical["created_record_count"]
    )


def test_canonical_record_type_counts_sum_to_created_record_count():
    k, r = _seeded_run()
    canonical = canonicalize_living_world_result(k, r)
    total = sum(count for _, count in canonical["record_type_counts"])
    assert total == canonical["created_record_count"]


# ---------------------------------------------------------------------------
# Volatile-field exclusion
# ---------------------------------------------------------------------------


def test_canonical_ledger_slice_excludes_volatile_fields():
    k, r = _seeded_run()
    canonical = canonicalize_living_world_result(k, r)
    for entry in canonical["ledger_slice_canonical"]:
        assert "record_id" not in entry
        assert "timestamp" not in entry
        # parent_record_ids must have been rewritten as parent_sequences.
        assert "parent_record_ids" not in entry
        assert "parent_sequences" in entry


def test_canonical_ledger_slice_uses_relative_sequence_indices():
    """parent_sequences should be 0-based positions within the
    chain's slice, not absolute ledger sequences. Two canonical
    runs whose kernels happened to start with different ledger
    lengths must produce the same parent_sequences."""
    k, r = _seeded_run()
    canonical = canonicalize_living_world_result(k, r)
    for entry in canonical["ledger_slice_canonical"]:
        for ps in entry["parent_sequences"]:
            if isinstance(ps, int):
                assert 0 <= ps < canonical["created_record_count"]


# ---------------------------------------------------------------------------
# Round-trip stability
# ---------------------------------------------------------------------------


def test_canonical_json_round_trips():
    k, r = _seeded_run()
    canonical = canonicalize_living_world_result(k, r)
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    decoded = json.loads(encoded)
    re_encoded = json.dumps(
        decoded,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert re_encoded == encoded


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_canonical_equal_across_two_fresh_runs():
    a_kernel, a_result = _seeded_run()
    b_kernel, b_result = _seeded_run()
    a_canonical = canonicalize_living_world_result(a_kernel, a_result)
    b_canonical = canonicalize_living_world_result(b_kernel, b_result)
    assert a_canonical == b_canonical


def test_digest_is_64_char_lowercase_hex():
    k, r = _seeded_run()
    digest = living_world_digest(k, r)
    assert isinstance(digest, str)
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_digest_equal_across_two_fresh_runs():
    a_kernel, a_result = _seeded_run()
    b_kernel, b_result = _seeded_run()
    assert living_world_digest(a_kernel, a_result) == living_world_digest(
        b_kernel, b_result
    )


def test_digest_matches_explicit_sha256_recipe():
    """Pin the digest recipe (SHA-256 over
    json.dumps(canonical, sort_keys=True, separators=(",", ":"),
    ensure_ascii=False)) so a future change cannot quietly switch
    to a different hash function or serialization preset."""
    k, r = _seeded_run()
    canonical = canonicalize_living_world_result(k, r)
    expected = hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert living_world_digest(k, r) == expected


def test_digest_changes_when_a_canonical_field_changes():
    """Sanity: tampering with a structural field should change the
    digest. We test by tampering the result's run_id (a canonical
    field) and re-running the canonicalizer."""
    k, r = _seeded_run()
    digest_before = living_world_digest(k, r)
    object.__setattr__(r, "run_id", "run:tampered")
    digest_after = living_world_digest(k, r)
    assert digest_before != digest_after


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


def test_canonicalize_does_not_mutate_kernel():
    k, r = _seeded_run()
    before = _capture_state(k)
    canonicalize_living_world_result(k, r)
    living_world_digest(k, r)
    after = _capture_state(k)
    assert before == after


# ---------------------------------------------------------------------------
# Boundary-statement consistency with v1.9.1 reporter
# ---------------------------------------------------------------------------


def test_boundary_statement_matches_v191_reporter_output():
    """The v1.9.2 helpers must use the same hard-boundary string the
    v1.9.1 reporter emits. Drift in either copy fails this test."""
    k, r = _seeded_run()
    md = render_living_world_markdown(
        build_living_world_trace_report(k, r)
    )
    assert LIVING_WORLD_BOUNDARY_STATEMENT in md


# ---------------------------------------------------------------------------
# Defensive errors
# ---------------------------------------------------------------------------


def test_canonicalize_rejects_kernel_none():
    _, r = _seeded_run()
    import pytest
    with pytest.raises(ValueError):
        canonicalize_living_world_result(None, r)


def test_canonicalize_rejects_non_result():
    k = _seed_kernel()
    import pytest
    with pytest.raises(TypeError):
        canonicalize_living_world_result(k, {"not": "a result"})
