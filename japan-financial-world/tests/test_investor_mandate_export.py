"""
v1.25.3 — Investor mandate readout export pin tests.

Pins ``world/investor_mandate_export.py`` and the
``RunExportBundle.investor_mandate_readout`` payload
section per the v1.25.0 design pin §13.1:

- the section is **omitted** from
  ``RunExportBundle.to_dict()`` when empty;
- the section is **present** when the kernel carries
  mandate profiles;
- the export keys are descriptive-only (whitelist
  matches the pinned set);
- forbidden tokens absent at any depth;
- the export helper does not emit a ledger record;
- the export helper does not mutate any kernel book.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES,
)
from world.investor_mandate_export import (
    INVESTOR_MANDATE_READOUT_EXPORT_REQUIRED_KEYS,
    build_investor_mandate_readout_export_section,
    investor_mandate_readout_to_export_entry,
)
from world.investor_mandate_readout import (
    build_investor_mandate_readout,
)
from world.investor_mandates import (
    InvestorMandateProfile,
)
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.registry import Registry
from world.run_export import (
    build_run_export_bundle,
    bundle_to_dict,
)
from world.scheduler import Scheduler
from world.state import State

from _canonical_digests import (
    QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
)


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _profile(
    mandate_profile_id: str = (
        "investor_mandate_profile:test:01"
    ),
) -> InvestorMandateProfile:
    return InvestorMandateProfile(
        mandate_profile_id=mandate_profile_id,
        investor_id="investor:test_pension_a",
        mandate_type_label="pension_like",
        benchmark_pressure_label="moderate",
        liquidity_need_label="low",
        liability_horizon_label="long",
        review_frequency_label="quarterly",
        concentration_tolerance_label="low",
        stewardship_priority_labels=(
            "capital_discipline",
            "governance_review",
        ),
    )


def _basic_bundle(**kwargs):
    return build_run_export_bundle(
        bundle_id="run_bundle:v1_25_3:test",
        run_profile_label="quarterly_default",
        regime_label="constrained",
        period_count=4,
        digest=QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. Empty by default — section omitted.
# ---------------------------------------------------------------------------


def test_export_omits_investor_mandate_readout_when_absent() -> None:
    """A bundle constructed without
    ``investor_mandate_readout`` defaults to an empty
    tuple; ``to_dict()`` omits the
    ``investor_mandate_readout`` key entirely."""
    b = _basic_bundle()
    d = bundle_to_dict(b)
    assert "investor_mandate_readout" not in d
    assert b.investor_mandate_readout == ()


# ---------------------------------------------------------------------------
# 2. Existing no-mandate bundle digests unchanged.
# ---------------------------------------------------------------------------


def test_no_mandate_bundle_digest_unchanged() -> None:
    """A bundle with the v1.21.last canonical digest as
    its ``digest`` field still serialises without an
    ``investor_mandate_readout`` key. The actual
    living-world digest preservation is pinned by v1.25.1
    ``test_existing_digests_unchanged_with_empty_mandate_book``;
    this re-asserts the export-side omission rule."""
    b = _basic_bundle()
    d = bundle_to_dict(b)
    assert d["digest"] == QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST
    assert "investor_mandate_readout" not in d


# ---------------------------------------------------------------------------
# 3. Section is present when profiles exist.
# ---------------------------------------------------------------------------


def test_export_includes_investor_mandate_readout_when_present() -> None:
    """When the kernel carries mandate profiles, the
    helper returns one entry per profile; the bundle
    serialises the entry list verbatim."""
    kernel = _bare_kernel()
    kernel.investor_mandates.add_profile(
        _profile("mp:test:a")
    )
    kernel.investor_mandates.add_profile(
        InvestorMandateProfile(
            mandate_profile_id="mp:test:b",
            investor_id="investor:test_active_b",
            mandate_type_label="active_manager_like",
            benchmark_pressure_label="high",
            liquidity_need_label="moderate",
            liability_horizon_label="short",
            review_frequency_label="monthly",
            concentration_tolerance_label="high",
            stewardship_priority_labels=(),
        )
    )
    section = build_investor_mandate_readout_export_section(
        kernel
    )
    assert len(section) == 2
    b = _basic_bundle(investor_mandate_readout=section)
    d = bundle_to_dict(b)
    assert "investor_mandate_readout" in d
    assert len(d["investor_mandate_readout"]) == 2
    profile_ids = {
        e["mandate_profile_id"]
        for e in d["investor_mandate_readout"]
    }
    assert profile_ids == {"mp:test:a", "mp:test:b"}


# ---------------------------------------------------------------------------
# 4. Export keys are descriptive-only (whitelist).
# ---------------------------------------------------------------------------


def test_export_keys_are_descriptive_only() -> None:
    """The export entry's top-level keys exactly match
    the v1.25.3 descriptive-only whitelist (no
    metadata / boundary_flags / free-form caller fields)."""
    kernel = _bare_kernel()
    kernel.investor_mandates.add_profile(_profile())
    readout = build_investor_mandate_readout(
        kernel,
        mandate_profile_id="investor_mandate_profile:test:01",
    )
    entry = investor_mandate_readout_to_export_entry(readout)
    assert (
        set(entry.keys())
        == INVESTOR_MANDATE_READOUT_EXPORT_REQUIRED_KEYS
    )


# ---------------------------------------------------------------------------
# 5. Forbidden wording absent from export at any depth.
# ---------------------------------------------------------------------------


def test_forbidden_wording_absent_from_export() -> None:
    """The export entry contains no v1.25.0 forbidden
    token at any key + any whole-string value at any
    depth. Construction rejects forbidden keys."""
    kernel = _bare_kernel()
    kernel.investor_mandates.add_profile(_profile())
    readout = build_investor_mandate_readout(
        kernel,
        mandate_profile_id="investor_mandate_profile:test:01",
    )
    entry = investor_mandate_readout_to_export_entry(readout)

    def walk(value, path="entry"):
        if isinstance(value, str):
            assert (
                value
                not in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES
            ), (
                f"forbidden whole-string value at "
                f"{path}: {value!r}"
            )
            return
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(k, str):
                    assert (
                        k
                        not in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES
                    ), (
                        f"forbidden key at {path}: {k!r}"
                    )
                walk(v, f"{path}.{k}")
            return
        if isinstance(value, (list, tuple)):
            for i, x in enumerate(value):
                walk(x, f"{path}[{i}]")
    walk(entry)
    # And construction rejects forbidden keys directly.
    with pytest.raises(ValueError):
        build_run_export_bundle(
            bundle_id="run_bundle:bad",
            run_profile_label="quarterly_default",
            regime_label="constrained",
            period_count=4,
            digest=QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST,
            investor_mandate_readout=[
                {
                    "investor_id": "investor:test",
                    "alpha": 0.0,
                }
            ],
        )


# ---------------------------------------------------------------------------
# 6. Export does not emit a ledger record.
# ---------------------------------------------------------------------------


def test_export_does_not_emit_ledger_records() -> None:
    """Building the export section must not emit any
    ledger record."""
    kernel = _bare_kernel()
    kernel.investor_mandates.add_profile(_profile())
    ledger_len_before = len(kernel.ledger.records)
    build_investor_mandate_readout_export_section(kernel)
    assert len(kernel.ledger.records) == ledger_len_before


# ---------------------------------------------------------------------------
# 7. Export does not mutate source-of-truth books.
# ---------------------------------------------------------------------------


def test_export_does_not_mutate_source_of_truth_books() -> None:
    """Snapshots of every relevant kernel book are byte-
    identical pre / post export-section build."""
    kernel = _bare_kernel()
    kernel.investor_mandates.add_profile(_profile())
    snap_before = {
        "investor_mandates": (
            kernel.investor_mandates.snapshot()
        ),
        "investor_intents": (
            kernel.investor_intents.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
        "ownership": kernel.ownership.snapshot(),
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "ledger_len": len(kernel.ledger.records),
    }
    build_investor_mandate_readout_export_section(kernel)
    snap_after = {
        "investor_mandates": (
            kernel.investor_mandates.snapshot()
        ),
        "investor_intents": (
            kernel.investor_intents.snapshot()
        ),
        "investor_market_intents": (
            kernel.investor_market_intents.snapshot()
        ),
        "ownership": kernel.ownership.snapshot(),
        "manual_annotations": (
            kernel.manual_annotations.snapshot()
        ),
        "stress_applications": (
            kernel.stress_applications.snapshot()
        ),
        "ledger_len": len(kernel.ledger.records),
    }
    assert snap_before == snap_after
