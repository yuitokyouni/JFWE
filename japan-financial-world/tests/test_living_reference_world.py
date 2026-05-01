"""
Tests for v1.9.0 Living Reference World Demo.

Pins the v1.9.0 contract end-to-end:

- ``run_living_reference_world`` runs for ``len(period_dates)``
  periods (default 4 quarters), and the kernel ledger grows in
  every period.
- Per-period record counts are exact: each firm emits one
  corporate report; each investor and bank gets one menu, one
  selection, and one review (plus the matching review-note
  signal).
- Investor and bank selected refs differ — the v1.8.12 attention
  rule continues to discriminate when the chain runs across
  multiple firms and multiple periods.
- Every result id resolves to an actually-stored record in the
  kernel.
- The result is deterministic across two fresh kernels seeded
  identically.
- No economic mutation — ``valuations`` / ``prices`` /
  ``ownership`` / ``contracts`` / ``constraints`` /
  ``institutions`` / ``external_processes`` / ``relationships``
  snapshots are byte-equal before and after the sweep.
- Exposures and variables are byte-equal before and after the
  sweep (the v1.9.0 helper does not mutate them after setup).
- ``kernel.tick()`` and ``kernel.run(days=N)`` never fire the
  chain.
- A loose **complexity budget** is enforced so a future change
  that introduces dense Cartesian-product loops fails the test
  loudly.
- Synthetic-only identifiers; no v1 forbidden tokens leak through.
- The CLI smoke runs and prints the expected substrings.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from datetime import date
from typing import Any

import pytest

from world.clock import Clock
from world.exposures import ExposureRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.reference_living_world import (
    LivingReferencePeriodSummary,
    LivingReferenceWorldResult,
    run_living_reference_world,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.variables import ReferenceVariableSpec, VariableObservation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_FIRM_IDS: tuple[str, ...] = (
    "firm:reference_manufacturer_a",
    "firm:reference_retailer_b",
    "firm:reference_utility_c",
)

_INVESTOR_IDS: tuple[str, ...] = (
    "investor:reference_pension_a",
    "investor:reference_growth_fund_a",
)

_BANK_IDS: tuple[str, ...] = (
    "bank:reference_megabank_a",
    "bank:reference_regional_b",
)

_REFERENCE_VARIABLES: tuple[tuple[str, str], ...] = (
    ("variable:reference_fx_pair_a", "fx"),
    ("variable:reference_long_rate_10y", "rates"),
    ("variable:reference_credit_spread_a", "credit"),
    ("variable:reference_land_index_a", "real_estate"),
    ("variable:reference_electricity_price_a", "energy_power"),
    ("variable:reference_cpi_yoy", "inflation"),
)

_OBS_DATES: tuple[str, ...] = (
    "2026-01-15",
    "2026-04-15",
    "2026-07-15",
    "2026-10-15",
)

_PERIOD_DATES: tuple[str, ...] = (
    "2026-03-31",
    "2026-06-30",
    "2026-09-30",
    "2026-12-31",
)


def _seed_exposures() -> tuple[ExposureRecord, ...]:
    out: list[ExposureRecord] = []
    for inv in _INVESTOR_IDS:
        out.append(
            ExposureRecord(
                exposure_id=f"exposure:{inv}:fx",
                subject_id=inv,
                subject_type="investor",
                variable_id="variable:reference_fx_pair_a",
                exposure_type="translation",
                metric="portfolio_translation_exposure",
                direction="mixed",
                magnitude=0.4,
            )
        )
        out.append(
            ExposureRecord(
                exposure_id=f"exposure:{inv}:rates",
                subject_id=inv,
                subject_type="investor",
                variable_id="variable:reference_long_rate_10y",
                exposure_type="discount_rate",
                metric="valuation_discount_rate",
                direction="negative",
                magnitude=0.3,
            )
        )
    for bnk in _BANK_IDS:
        out.append(
            ExposureRecord(
                exposure_id=f"exposure:{bnk}:funding",
                subject_id=bnk,
                subject_type="bank",
                variable_id="variable:reference_long_rate_10y",
                exposure_type="funding_cost",
                metric="debt_service_burden",
                direction="positive",
                magnitude=0.5,
            )
        )
        out.append(
            ExposureRecord(
                exposure_id=f"exposure:{bnk}:collateral",
                subject_id=bnk,
                subject_type="bank",
                variable_id="variable:reference_land_index_a",
                exposure_type="collateral",
                metric="collateral_value",
                direction="positive",
                magnitude=0.4,
            )
        )
        out.append(
            ExposureRecord(
                exposure_id=f"exposure:{bnk}:operating_cost",
                subject_id=bnk,
                subject_type="bank",
                variable_id="variable:reference_electricity_price_a",
                exposure_type="input_cost",
                metric="operating_cost_pressure",
                direction="negative",
                magnitude=0.2,
            )
        )
    return tuple(out)


def _seed_kernel() -> WorldKernel:
    k = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )
    for vid, vgroup in _REFERENCE_VARIABLES:
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
        for q_date in _OBS_DATES:
            k.variables.add_observation(
                VariableObservation(
                    observation_id=f"obs:{vid}:{q_date}",
                    variable_id=vid,
                    as_of_date=q_date,
                    value=100.0,
                    unit="index",
                    vintage_id=f"{q_date}_initial",
                )
            )
    for record in _seed_exposures():
        k.exposures.add_exposure(record)
    return k


def _run_default(k: WorldKernel) -> LivingReferenceWorldResult:
    return run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------


def test_result_is_immutable_and_well_formed():
    k = _seed_kernel()
    r = _run_default(k)
    assert isinstance(r, LivingReferenceWorldResult)
    assert r.period_count == 4
    assert r.firm_ids == _FIRM_IDS
    assert r.investor_ids == _INVESTOR_IDS
    assert r.bank_ids == _BANK_IDS
    with pytest.raises(Exception):
        r.run_id = "tampered"  # type: ignore[misc]


def test_per_period_summaries_have_period_count_entries():
    k = _seed_kernel()
    r = _run_default(k)
    assert len(r.per_period_summaries) == 4
    for ps in r.per_period_summaries:
        assert isinstance(ps, LivingReferencePeriodSummary)


# ---------------------------------------------------------------------------
# Per-period counts
# ---------------------------------------------------------------------------


def test_each_firm_emits_one_corporate_report_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.corporate_signal_ids) == len(_FIRM_IDS)
        assert len(ps.corporate_run_ids) == len(_FIRM_IDS)


def test_one_menu_and_selection_per_actor_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.investor_menu_ids) == len(_INVESTOR_IDS)
        assert len(ps.bank_menu_ids) == len(_BANK_IDS)
        assert len(ps.investor_selection_ids) == len(_INVESTOR_IDS)
        assert len(ps.bank_selection_ids) == len(_BANK_IDS)


def test_one_review_run_and_signal_per_actor_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.investor_review_run_ids) == len(_INVESTOR_IDS)
        assert len(ps.bank_review_run_ids) == len(_BANK_IDS)
        assert len(ps.investor_review_signal_ids) == len(_INVESTOR_IDS)
        assert len(ps.bank_review_signal_ids) == len(_BANK_IDS)


def test_period_record_counts_are_positive():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert ps.record_count_created > 0


def test_ledger_grows_in_every_period():
    """Each period's record_count_created must be > 0 — the chain
    actually advances per quarter."""
    k = _seed_kernel()
    r = _run_default(k)
    assert all(ps.record_count_created > 0 for ps in r.per_period_summaries)


# ---------------------------------------------------------------------------
# Persistence: every result id resolves to a stored record
# ---------------------------------------------------------------------------


def test_every_result_id_resolves_to_a_stored_record():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for rid in ps.corporate_run_ids + ps.investor_review_run_ids + ps.bank_review_run_ids:
            assert k.routines.get_run_record(rid) is not None
        for sid in (
            ps.corporate_signal_ids
            + ps.investor_review_signal_ids
            + ps.bank_review_signal_ids
        ):
            assert k.signals.get_signal(sid) is not None
        for mid in ps.investor_menu_ids + ps.bank_menu_ids:
            assert k.attention.get_menu(mid) is not None
        for sel in ps.investor_selection_ids + ps.bank_selection_ids:
            assert k.attention.get_selection(sel) is not None


def test_created_record_ids_match_ledger_slice():
    k = _seed_kernel()
    r = _run_default(k)
    actual = tuple(
        rec.object_id
        for rec in k.ledger.records[
            r.ledger_record_count_before : r.ledger_record_count_after
        ]
    )
    assert actual == r.created_record_ids


# ---------------------------------------------------------------------------
# Heterogeneous attention propagates across periods
# ---------------------------------------------------------------------------


def test_investor_and_bank_selected_refs_differ_in_every_period():
    k = _seed_kernel()
    _run_default(k)
    for inv in _INVESTOR_IDS:
        inv_selections = k.attention.list_selections_by_actor(inv)
        # Period 1 selection refs should differ from any bank's
        # period 1 selection refs.
        for bnk in _BANK_IDS:
            bnk_selections = k.attention.list_selections_by_actor(bnk)
            for inv_sel, bnk_sel in zip(inv_selections, bnk_selections):
                assert inv_sel.selected_refs != bnk_sel.selected_refs


def test_corporate_signals_appear_in_actor_selections():
    """All firms' corporate signals show up in every actor's
    selection because both default profiles watch the
    `corporate_quarterly_report` signal type."""
    k = _seed_kernel()
    r = _run_default(k)
    period_signals = r.per_period_summaries[0].corporate_signal_ids

    for inv in _INVESTOR_IDS:
        sel = k.attention.list_selections_by_actor(inv)[0]
        for sid in period_signals:
            assert sid in sel.selected_refs

    for bnk in _BANK_IDS:
        sel = k.attention.list_selections_by_actor(bnk)[0]
        for sid in period_signals:
            assert sid in sel.selected_refs


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def _structural_summary(r: LivingReferenceWorldResult) -> dict[str, Any]:
    return {
        "run_id": r.run_id,
        "period_count": r.period_count,
        "firm_ids": r.firm_ids,
        "investor_ids": r.investor_ids,
        "bank_ids": r.bank_ids,
        "created_record_count": r.created_record_count,
        "created_record_ids": r.created_record_ids,
        "per_periods": tuple(
            (
                ps.period_id,
                ps.as_of_date,
                ps.corporate_signal_ids,
                ps.corporate_run_ids,
                ps.investor_menu_ids,
                ps.bank_menu_ids,
                ps.investor_selection_ids,
                ps.bank_selection_ids,
                ps.investor_review_run_ids,
                ps.bank_review_run_ids,
                ps.investor_review_signal_ids,
                ps.bank_review_signal_ids,
                ps.record_count_created,
            )
            for ps in r.per_period_summaries
        ),
    }


def test_living_world_is_deterministic_across_fresh_kernels():
    a = _structural_summary(_run_default(_seed_kernel()))
    b = _structural_summary(_run_default(_seed_kernel()))
    assert a == b


# ---------------------------------------------------------------------------
# Date / arg semantics
# ---------------------------------------------------------------------------


def test_default_period_dates_are_four_quarter_ends():
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
    )
    assert r.period_count == 4
    iso_dates = tuple(ps.as_of_date for ps in r.per_period_summaries)
    assert iso_dates == (
        "2026-03-31",
        "2026-06-30",
        "2026-09-30",
        "2026-12-31",
    )


def test_explicit_period_dates_honored():
    k = _seed_kernel()
    custom = ("2027-03-31", "2027-06-30")
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=custom,
    )
    assert r.period_count == 2
    assert tuple(ps.as_of_date for ps in r.per_period_summaries) == custom


# ---------------------------------------------------------------------------
# Defensive errors
# ---------------------------------------------------------------------------


def test_chain_rejects_kernel_none():
    with pytest.raises(ValueError):
        run_living_reference_world(
            None,
            firm_ids=_FIRM_IDS,
            investor_ids=_INVESTOR_IDS,
            bank_ids=_BANK_IDS,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"firm_ids": ()},
        {"investor_ids": ()},
        {"bank_ids": ()},
        {"firm_ids": ("",)},
        {"period_dates": ()},
    ],
)
def test_chain_rejects_invalid_inputs(kwargs):
    k = _seed_kernel()
    base: dict[str, Any] = {
        "firm_ids": _FIRM_IDS,
        "investor_ids": _INVESTOR_IDS,
        "bank_ids": _BANK_IDS,
    }
    base.update(kwargs)
    with pytest.raises(ValueError):
        run_living_reference_world(k, **base)


# ---------------------------------------------------------------------------
# No economic mutation
# ---------------------------------------------------------------------------


def _capture_economic_state(k: WorldKernel) -> dict[str, Any]:
    return {
        "valuations": k.valuations.snapshot(),
        "prices": k.prices.snapshot(),
        "ownership": k.ownership.snapshot(),
        "contracts": k.contracts.snapshot(),
        "constraints": k.constraints.snapshot(),
        "institutions": k.institutions.snapshot(),
        "external_processes": k.external_processes.snapshot(),
        "relationships": k.relationships.snapshot(),
    }


def test_chain_does_not_mutate_economic_books():
    k = _seed_kernel()
    before = _capture_economic_state(k)
    _run_default(k)
    after = _capture_economic_state(k)
    assert before == after


def test_chain_does_not_mutate_exposures_or_variables_after_setup():
    k = _seed_kernel()
    before_exposures = k.exposures.snapshot()
    before_variables = k.variables.snapshot()
    _run_default(k)
    assert k.exposures.snapshot() == before_exposures
    assert k.variables.snapshot() == before_variables


# ---------------------------------------------------------------------------
# No auto-firing
# ---------------------------------------------------------------------------


def test_kernel_tick_does_not_run_living_world():
    k = _seed_kernel()
    before_runs = len(k.routines.snapshot()["runs"])
    before_signals = len(k.signals.all_signals())
    k.tick()
    assert len(k.routines.snapshot()["runs"]) == before_runs
    assert len(k.signals.all_signals()) == before_signals


def test_kernel_run_does_not_run_living_world():
    k = _seed_kernel()
    before_runs = len(k.routines.snapshot()["runs"])
    before_signals = len(k.signals.all_signals())
    k.run(days=10)
    assert len(k.routines.snapshot()["runs"]) == before_runs
    assert len(k.signals.all_signals()) == before_signals


# ---------------------------------------------------------------------------
# Complexity budget — flags accidental Cartesian-product loops
# ---------------------------------------------------------------------------


def test_living_world_stays_within_record_budget():
    """Sanity-check that the v1.9.0 sweep does not inadvertently
    enumerate firms × investors × banks × periods. With the
    default fixture (3 firms / 2 investors / 2 banks / 4 periods)
    we expect roughly:

      4 periods × (3 corp_run + 3 corp_signal
                   + 4 menus + 4 selections
                   + 4 review_run + 4 review_signal)
      = 88 records

      + a small constant amount of one-off setup records
        (interactions, routines, profiles registered on the first
        period).

    A budget of 200 catches accidental quadratic loops while
    leaving headroom for harmless infra adjustments.
    """
    k = _seed_kernel()
    r = _run_default(k)
    # Tight lower bound: the chain must produce at least the
    # per-period work multiplied by 4.
    minimum_expected = 4 * (
        2 * len(_FIRM_IDS)
        + 2 * (len(_INVESTOR_IDS) + len(_BANK_IDS))
        + 2 * (len(_INVESTOR_IDS) + len(_BANK_IDS))
    )  # = 4 * (6 + 8 + 8) = 88
    assert r.created_record_count >= minimum_expected
    # Loose upper bound: 200 is well below the 4×3×2×2×... product
    # space (180+ if the loop were dense), so it flags drift early.
    assert r.created_record_count <= 200


# ---------------------------------------------------------------------------
# Synthetic-only identifiers
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "nyse",
)


def test_living_world_ids_are_synthetic_only():
    k = _seed_kernel()
    r = _run_default(k)
    candidates: list[str] = list(r.created_record_ids)
    candidates.extend(r.firm_ids + r.investor_ids + r.bank_ids)
    for ps in r.per_period_summaries:
        candidates.extend(ps.corporate_signal_ids)
        candidates.extend(ps.investor_review_signal_ids)
        candidates.extend(ps.bank_review_signal_ids)
    for id_str in candidates:
        lower = id_str.lower()
        for token in _FORBIDDEN_TOKENS:
            for sep in (" ", ":", "/", "-", "_", "(", ")", ",", ".", "'", '"'):
                if f"{sep}{token}{sep}" in f" {lower} ":
                    pytest.fail(
                        f"forbidden token {token!r} appears in id {id_str!r}"
                    )


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


def test_cli_smoke_prints_per_period_trace():
    from examples.reference_world import run_living_reference_world as cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.main()
    out = buf.getvalue()
    assert "[setup]" in out
    assert "[period 1]" in out
    assert "[period 4]" in out
    assert "[ledger]" in out
    assert "no price / trading / lending" in out
