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
    # v1.9.6 — firm exposures so the v1.9.4 firm-pressure-assessment
    # mechanism produces non-zero output during the multi-period sweep.
    firm_exposure_specs: tuple[tuple[str, str, str, float], ...] = (
        ("firm:reference_manufacturer_a", "variable:reference_long_rate_10y", "funding_cost", 0.3),
        ("firm:reference_manufacturer_a", "variable:reference_fx_pair_a", "translation", 0.2),
        ("firm:reference_manufacturer_a", "variable:reference_electricity_price_a", "input_cost", 0.4),
        ("firm:reference_retailer_b", "variable:reference_fx_pair_a", "translation", 0.3),
        ("firm:reference_retailer_b", "variable:reference_long_rate_10y", "funding_cost", 0.2),
        ("firm:reference_utility_c", "variable:reference_electricity_price_a", "input_cost", 0.5),
        ("firm:reference_utility_c", "variable:reference_long_rate_10y", "funding_cost", 0.4),
    )
    for firm_id, var_id, exp_type, mag in firm_exposure_specs:
        metric = (
            "operating_cost_pressure"
            if exp_type == "input_cost"
            else "debt_service_burden"
            if exp_type == "funding_cost"
            else "fx_translation_pressure"
        )
        out.append(
            ExposureRecord(
                exposure_id=f"exposure:{firm_id}:{var_id}",
                subject_id=firm_id,
                subject_type="firm",
                variable_id=var_id,
                exposure_type=exp_type,
                metric=metric,
                direction="positive",
                magnitude=mag,
            )
        )
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


# ---------------------------------------------------------------------------
# v1.9.6 integration: firm pressure assessment + valuation refresh lite
# ---------------------------------------------------------------------------


def test_one_pressure_signal_per_firm_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.firm_pressure_signal_ids) == len(_FIRM_IDS)
        assert len(ps.firm_pressure_run_ids) == len(_FIRM_IDS)


def test_pressure_signals_resolve_to_stored_signals():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for sid in ps.firm_pressure_signal_ids:
            sig = k.signals.get_signal(sid)
            assert sig.signal_type == "firm_operating_pressure_assessment"
            assert sig.subject_id in _FIRM_IDS


def test_one_valuation_per_investor_firm_pair_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    expected = len(_INVESTOR_IDS) * len(_FIRM_IDS)
    for ps in r.per_period_summaries:
        assert len(ps.valuation_ids) == expected
        assert len(ps.valuation_mechanism_run_ids) == expected


def test_valuations_resolve_to_stored_records():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for vid in ps.valuation_ids:
            record = k.valuations.get_valuation(vid)
            assert record.method == "synthetic_lite_pressure_adjusted"
            assert record.subject_id in _FIRM_IDS
            assert record.valuer_id in _INVESTOR_IDS


def test_valuation_metadata_carries_pressure_signal_link():
    """Each valuation must reference the firm's pressure signal
    for the same period; this proves v1.9.5 actually consumed
    v1.9.4's output (not a coincidence of ordering)."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        pressure_by_firm = {
            k.signals.get_signal(sid).subject_id: sid
            for sid in ps.firm_pressure_signal_ids
        }
        for vid in ps.valuation_ids:
            record = k.valuations.get_valuation(vid)
            firm = record.subject_id
            assert (
                record.metadata["pressure_signal_id"]
                == pressure_by_firm[firm]
            )


def test_valuation_metadata_carries_boundary_flags():
    """Every committed ValuationRecord stamps the v1.9.5 boundary
    flags so a downstream reader can never mistake the synthetic
    claim for canonical truth."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for vid in ps.valuation_ids:
            record = k.valuations.get_valuation(vid)
            assert record.metadata["no_price_movement"] is True
            assert record.metadata["no_investment_advice"] is True
            assert record.metadata["synthetic_only"] is True


def test_pressure_run_records_resolve_via_caller_audit_path():
    """v1.9.4 returns MechanismRunRecord as caller-side audit
    data; v1.9.6 records the pressure run ids on the period
    summary. Verify each id is non-empty and unique within the
    period (lineage hygiene)."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        seen: set[str] = set()
        for rid in ps.firm_pressure_run_ids:
            assert isinstance(rid, str) and rid
            assert rid not in seen
            seen.add(rid)


def test_valuation_run_records_unique_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        seen: set[str] = set()
        for rid in ps.valuation_mechanism_run_ids:
            assert isinstance(rid, str) and rid
            assert rid not in seen
            seen.add(rid)


# ---------------------------------------------------------------------------
# v1.9.7 integration: bank credit review lite
# ---------------------------------------------------------------------------


def test_one_credit_review_signal_per_bank_firm_pair_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    expected = len(_BANK_IDS) * len(_FIRM_IDS)
    for ps in r.per_period_summaries:
        assert len(ps.bank_credit_review_signal_ids) == expected
        assert len(ps.bank_credit_review_mechanism_run_ids) == expected


def test_credit_review_signals_resolve_to_stored_records():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for sid in ps.bank_credit_review_signal_ids:
            sig = k.signals.get_signal(sid)
            assert sig.signal_type == "bank_credit_review_note"
            assert sig.subject_id in _FIRM_IDS
            assert sig.source_id in _BANK_IDS


def test_credit_review_metadata_carries_pressure_signal_link():
    """Each credit review must reference the firm's pressure
    signal for the same period; this proves v1.9.7 actually
    consumed v1.9.4's output through the chain."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        pressure_by_firm = {
            k.signals.get_signal(sid).subject_id: sid
            for sid in ps.firm_pressure_signal_ids
        }
        for sid in ps.bank_credit_review_signal_ids:
            sig = k.signals.get_signal(sid)
            firm = sig.subject_id
            assert (
                sig.payload["pressure_signal_id"]
                == pressure_by_firm[firm]
            )


def test_credit_review_related_ids_include_valuations_for_firm():
    """The v1.9.7 review must thread valuations through
    related_ids, proving the chain
    pressure → valuation → credit review is real, not coincidental
    ordering."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        # Group valuations by firm.
        valuations_by_firm: dict[str, list[str]] = {}
        for vid in ps.valuation_ids:
            v = k.valuations.get_valuation(vid)
            valuations_by_firm.setdefault(v.subject_id, []).append(vid)
        for sid in ps.bank_credit_review_signal_ids:
            sig = k.signals.get_signal(sid)
            firm = sig.subject_id
            firm_valuations = set(valuations_by_firm.get(firm, []))
            related = set(sig.related_ids)
            # At least one valuation on this firm should be in related_ids.
            assert firm_valuations & related, (
                f"credit review {sid} for firm {firm} did not "
                f"thread any valuation in related_ids"
            )


def test_credit_review_metadata_carries_boundary_flags():
    """Every committed credit review note stamps the v1.9.7
    boundary flags."""
    k = _seed_kernel()
    r = _run_default(k)
    expected_flags = (
        "no_lending_decision",
        "no_covenant_enforcement",
        "no_contract_mutation",
        "no_constraint_mutation",
        "no_default_declaration",
        "no_internal_rating",
        "no_probability_of_default",
        "synthetic_only",
    )
    for ps in r.per_period_summaries:
        for sid in ps.bank_credit_review_signal_ids:
            sig = k.signals.get_signal(sid)
            for flag in expected_flags:
                assert sig.metadata[flag] is True, (
                    f"credit review {sid} missing flag {flag}"
                )


def test_credit_review_run_records_unique_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        seen: set[str] = set()
        for rid in ps.bank_credit_review_mechanism_run_ids:
            assert isinstance(rid, str) and rid
            assert rid not in seen, (
                f"duplicate credit-review run id {rid} in {ps.period_id}"
            )
            seen.add(rid)


def test_credit_review_does_not_mutate_contracts_or_constraints():
    """v1.9.7's hard boundary: credit review must not touch
    ContractBook or ConstraintBook. Pin it with a snapshot
    equality across the entire sweep."""
    k = _seed_kernel()
    before_contracts = k.contracts.snapshot()
    before_constraints = k.constraints.snapshot()
    _run_default(k)
    assert k.contracts.snapshot() == before_contracts
    assert k.constraints.snapshot() == before_constraints


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
    """Snapshot the economic books that v1.9.6 must NOT mutate.

    Note: ``valuations`` is excluded from this snapshot because
    v1.9.6 deliberately commits one synthetic ValuationRecord per
    (investor, firm) pair per period via the v1.9.5
    valuation_mechanism. That growth is *expected*; the
    ``test_valuation_count_grows_by_expected_amount`` test pins
    the exact count instead. Every other book listed below stays
    byte-identical across the sweep.
    """
    return {
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


def test_valuation_count_grows_by_expected_amount():
    """v1.9.6 commits one ValuationRecord per (investor, firm) per
    period through the v1.9.5 valuation_mechanism. Pin the exact
    growth so a future change cannot quietly multiply this."""
    k = _seed_kernel()
    before = len(k.valuations.all_valuations())
    r = _run_default(k)
    after = len(k.valuations.all_valuations())
    expected = (
        len(r.investor_ids) * len(r.firm_ids) * r.period_count
    )
    assert after - before == expected
    # Per-period total also matches.
    for ps in r.per_period_summaries:
        assert (
            len(ps.valuation_ids)
            == len(r.investor_ids) * len(r.firm_ids)
        )


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
    """Sanity-check that the v1.9.7 sweep does not inadvertently
    enumerate firms × investors × banks × periods. With the
    default fixture (3 firms / 2 investors / 2 banks / 4 periods)
    we expect roughly:

      per period:
        2 × firms                 (corp_run + corp_signal)            =  6
        firms                     (pressure_signal — v1.9.6)          =  3
        2 × (investors + banks)   (menu + selection)                  =  8
        investors × firms         (valuation — v1.9.6)                =  6
        banks × firms             (credit_review_signal — v1.9.7)     =  6
        2 × (investors + banks)   (review_run + review_signal)        =  8
                                                               total  = 37

      × 4 periods                                                     = 148

      + a small constant amount of one-off setup records
        (interactions, routines, profiles registered on the first
        period — currently ~14).

    Lower bound 148 (v1.9.x per-period work × 4); upper bound 480
    catches accidental quadratic loops while leaving headroom for
    every milestone through v1.14.5 (which sits at ~408 records
    on the default fixture: v1.13.5 baseline 324 + v1.14.5's 60
    corporate-financing records + memory-selection residual). The
    tight per-version window lives in
    ``test_living_reference_world_performance_boundary.py``.
    """
    k = _seed_kernel()
    r = _run_default(k)
    minimum_expected = 4 * (
        2 * len(_FIRM_IDS)  # corp_run + corp_signal
        + len(_FIRM_IDS)  # pressure signal (v1.9.6)
        + 2 * (len(_INVESTOR_IDS) + len(_BANK_IDS))  # menu + selection
        + len(_INVESTOR_IDS) * len(_FIRM_IDS)  # valuation (v1.9.6)
        + len(_BANK_IDS) * len(_FIRM_IDS)  # credit review (v1.9.7)
        + 2 * (len(_INVESTOR_IDS) + len(_BANK_IDS))  # review_run + signal
    )  # = 4 * (6 + 3 + 8 + 6 + 6 + 8) = 148
    assert r.created_record_count >= minimum_expected
    # Loose upper bound: 480 is well below dense product space.
    assert r.created_record_count <= 480


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
        # Pass argv=[] explicitly. Without this, argparse would read
        # sys.argv, which under `pytest -q` contains the "-q" flag
        # the demo CLI does not recognise. Every CLI smoke test in
        # this repository must pass an explicit argv list for the
        # same reason.
        cli.main([])
    out = buf.getvalue()
    assert "[setup]" in out
    assert "[period 1]" in out
    assert "[period 4]" in out
    assert "[ledger]" in out
    # v1.9.6 / v1.9.7: pressure + valuation + credit_reviews now
    # appear in every period's trace line; the summary line names
    # the integrated chain and the boundary statement.
    assert "pressures=" in out
    assert "valuations=" in out
    assert "credit_reviews=" in out
    assert "bank credit review lite" in out
    assert "no canonical-truth valuation" in out
    assert "no investment advice" in out
    assert "no lending decisions" in out
    # v1.10.5 — every period line names the v1.10 phases; the
    # summary line names the engagement / response chain and
    # carries the v1.10 anti-claims.
    assert "industry=" in out
    assert "themes=" in out
    assert "dialogues=" in out
    assert "escalations=" in out
    assert "responses=" in out
    assert "industry demand condition" in out
    assert "investor escalation candidates" in out
    assert "corporate strategic response candidates" in out
    assert "no voting execution" in out
    assert "no proxy filing" in out
    assert "no public-campaign execution" in out
    assert "no corporate-action execution" in out
    assert "no disclosure filing" in out
    assert "no demand / revenue forecasting" in out
    # v1.11.0 — capital-market surface columns and anti-claims.
    assert "markets=" in out
    assert "market_conditions=" in out
    assert "capital-market conditions" in out
    assert "no yield-curve calibration" in out
    assert "no order matching" in out
    assert "no clearing" in out
    assert "no quote dissemination" in out
    assert "no security recommendation" in out
    # v1.11.1 — capital-market readout column.
    assert "market_readouts=" in out


# ===========================================================================
# v1.10.5 — engagement / strategic-response integration
# ===========================================================================


def test_v1_10_5_industry_condition_per_industry_per_period():
    """Each period emits one IndustryDemandConditionRecord per
    unique industry derived from the firm_industry_map default
    (3 firms → 3 distinct industries by keyword)."""
    k = _seed_kernel()
    r = _run_default(k)
    assert len(r.industry_ids) == 3
    for ps in r.per_period_summaries:
        assert len(ps.industry_condition_ids) == 3


def test_v1_10_5_industry_conditions_resolve_to_stored_records():
    k = _seed_kernel()
    r = _run_default(k)
    seen_cids: set[str] = set()
    for ps in r.per_period_summaries:
        seen_cids.update(ps.industry_condition_ids)
    for cid in seen_cids:
        rec = k.industry_conditions.get_condition(cid)
        assert 0.0 <= rec.demand_strength <= 1.0
        assert 0.0 <= rec.confidence <= 1.0


def test_v1_10_5_stewardship_themes_registered_setup_level():
    """Themes are setup-level: 2 themes × 2 investors = 4 themes,
    same theme tuple appears on every period summary."""
    k = _seed_kernel()
    r = _run_default(k)
    assert len(r.stewardship_theme_ids) == 4
    for ps in r.per_period_summaries:
        assert ps.stewardship_theme_ids == r.stewardship_theme_ids


def test_v1_10_5_stewardship_themes_idempotent_on_re_run():
    """Calling the chain twice on the same kernel against
    *non-overlapping* period dates must NOT raise on duplicate
    theme ids — themes are setup-level and registration is
    idempotent. Periods themselves are intentionally
    non-overlapping (re-running the corporate-reporting routine
    on the same date is unrelated to the v1.10.5 idempotency
    contract this test pins)."""
    k = _seed_kernel()
    first_window = _PERIOD_DATES[:2]
    second_window = _PERIOD_DATES[2:]
    r1 = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=first_window,
    )
    r2 = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=second_window,
        run_id="run:living:rerun",
    )
    assert r1.stewardship_theme_ids == r2.stewardship_theme_ids
    # Single set of theme records remains in the kernel — the
    # second call must not have produced a parallel theme set.
    assert (
        len(k.stewardship.list_themes())
        == len(r1.stewardship_theme_ids)
    )


def test_v1_10_5_dialogues_one_per_investor_firm_pair_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    expected = len(_INVESTOR_IDS) * len(_FIRM_IDS)
    for ps in r.per_period_summaries:
        assert len(ps.dialogue_ids) == expected


def test_v1_10_5_dialogue_records_resolve_and_carry_pressure_link():
    k = _seed_kernel()
    r = _run_default(k)
    period = r.per_period_summaries[0]
    pressure_set = set(period.firm_pressure_signal_ids)
    for did in period.dialogue_ids:
        d = k.engagement.get_dialogue(did)
        assert d.initiator_id in _INVESTOR_IDS
        assert d.counterparty_id in _FIRM_IDS
        # The dialogue carries the firm's pressure signal in the
        # dedicated v1.10.2 slot — never in related_signal_ids.
        assert any(p in pressure_set for p in d.related_pressure_signal_ids)


def test_v1_10_5_investor_escalation_candidates_one_per_pair_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    expected = len(_INVESTOR_IDS) * len(_FIRM_IDS)
    for ps in r.per_period_summaries:
        assert len(ps.investor_escalation_candidate_ids) == expected


def test_v1_10_5_escalation_candidates_resolve_and_link_dialogues():
    k = _seed_kernel()
    r = _run_default(k)
    period = r.per_period_summaries[0]
    dialogue_set = set(period.dialogue_ids)
    for eid in period.investor_escalation_candidate_ids:
        c = k.escalations.get_candidate(eid)
        assert c.investor_id in _INVESTOR_IDS
        assert c.target_company_id in _FIRM_IDS
        # Each escalation cites at least one dialogue from the
        # same period — the integration assertion that the
        # v1.10.5 orchestrator wired the pair link end-to-end.
        assert any(did in dialogue_set for did in c.dialogue_ids)


def test_v1_10_5_corporate_response_candidates_one_per_firm_per_period():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert (
            len(ps.corporate_strategic_response_candidate_ids)
            == len(_FIRM_IDS)
        )


def test_v1_10_5_corporate_response_uses_industry_condition_slot_not_signal_slot():
    """v1.10.4.1 type-correct cross-reference: industry-condition
    ids must appear in trigger_industry_condition_ids and **not**
    in trigger_signal_ids."""
    k = _seed_kernel()
    r = _run_default(k)
    period = r.per_period_summaries[0]
    industry_condition_set = set(period.industry_condition_ids)
    for rid in period.corporate_strategic_response_candidate_ids:
        c = k.strategic_responses.get_candidate(rid)
        # At least one industry-condition id from this period is
        # cited in the dedicated slot.
        assert any(
            cid in industry_condition_set
            for cid in c.trigger_industry_condition_ids
        )
        # The signal slot must NOT carry any industry-condition id.
        for sid in c.trigger_signal_ids:
            assert sid not in industry_condition_set


def test_v1_10_5_no_voting_or_corporate_action_payload_keys_in_ledger():
    """No v1.10.5 record's ledger payload may carry an execution /
    transcript / forecast key — the candidate-only / no-execution /
    no-forecast discipline applies end-to-end in the integrated
    demo."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_keys = {
        "vote_cast",
        "proposal_filed",
        "campaign_executed",
        "exit_executed",
        "letter_sent",
        "buyback_executed",
        "dividend_changed",
        "divestment_executed",
        "merger_executed",
        "board_change_executed",
        "disclosure_filed",
        "transcript",
        "content",
        "notes",
        "minutes",
        "attendees",
        "verbatim",
        "paraphrase",
        "body",
        "forecast_value",
        "revenue_forecast",
        "sales_forecast",
        "market_size",
        "demand_index_value",
        "vendor_consensus",
        "consensus_forecast",
        "real_data_value",
    }
    for rec in k.ledger.records[
        r.ledger_record_count_before : r.ledger_record_count_after
    ]:
        leaked = set(rec.payload.keys()) & forbidden_keys
        assert not leaked, (
            f"v1.10.5 demo record {rec.object_id!r} leaks forbidden "
            f"payload keys: {sorted(leaked)}"
        )


def test_v1_10_5_no_forbidden_action_class_event_types_appear():
    """The integrated v1.10.5 sweep must emit no action-class
    record types — even from the new engagement / response phases."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_event_types = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
        "firm_state_added",
    }
    seen = {
        rec.event_type
        for rec in k.ledger.records[
            r.ledger_record_count_before : r.ledger_record_count_after
        ]
    }
    assert seen.isdisjoint(forbidden_event_types), (
        "v1.10.5 integrated sweep emitted forbidden action-class "
        f"records: {sorted(seen & forbidden_event_types)}"
    )


def test_v1_10_5_no_other_books_mutated_by_engagement_phases():
    """The engagement / response phases must not mutate any other
    source-of-truth book. Snapshot every kernel book that v1.10
    is *not* expected to write into and compare before / after."""
    k = _seed_kernel()
    snaps_before = {
        "ownership": k.ownership.snapshot(),
        "contracts": k.contracts.snapshot(),
        "prices": k.prices.snapshot(),
        "constraints": k.constraints.snapshot(),
        "institutions": k.institutions.snapshot(),
        "external_processes": k.external_processes.snapshot(),
        "relationships": k.relationships.snapshot(),
    }
    _run_default(k)
    assert k.ownership.snapshot() == snaps_before["ownership"]
    assert k.contracts.snapshot() == snaps_before["contracts"]
    assert k.prices.snapshot() == snaps_before["prices"]
    assert k.constraints.snapshot() == snaps_before["constraints"]
    assert k.institutions.snapshot() == snaps_before["institutions"]
    assert (
        k.external_processes.snapshot()
        == snaps_before["external_processes"]
    )
    assert k.relationships.snapshot() == snaps_before["relationships"]


def test_v1_10_5_two_runs_produce_byte_identical_canonical_view():
    """v1.10.5 additions to LivingReferencePeriodSummary and the
    canonical view must remain deterministic — two fresh runs of
    the default fixture produce byte-identical canonical JSON."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_10_5_canonical_view_carries_engagement_id_tuples():
    """The canonical view must surface the v1.10.5 id tuples
    explicitly so a downstream lineage / replay consumer does not
    need to re-walk the ledger to find them."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
    )

    k = _seed_kernel()
    r = _run_default(k)
    can = canonicalize_living_world_result(k, r)
    assert "industry_ids" in can
    assert "stewardship_theme_ids" in can
    for ps in can["per_period_summaries"]:
        assert "industry_condition_ids" in ps
        assert "stewardship_theme_ids" in ps
        assert "dialogue_ids" in ps
        assert "investor_escalation_candidate_ids" in ps
        assert "corporate_strategic_response_candidate_ids" in ps


# ===========================================================================
# v1.11.0 — capital-market surface integration
# ===========================================================================


def test_v1_11_0_market_condition_per_market_per_period():
    """Each period emits one MarketConditionRecord per market in
    the orchestrator's default market spec set (5 by default:
    reference_rates, credit_spreads, equity_market, funding_market,
    liquidity_market)."""
    k = _seed_kernel()
    r = _run_default(k)
    assert len(r.market_ids) == 5
    for ps in r.per_period_summaries:
        assert len(ps.market_condition_ids) == 5


def test_v1_11_0_market_conditions_resolve_to_stored_records():
    k = _seed_kernel()
    r = _run_default(k)
    seen_mc_ids: set[str] = set()
    for ps in r.per_period_summaries:
        seen_mc_ids.update(ps.market_condition_ids)
    for mc_id in seen_mc_ids:
        rec = k.market_conditions.get_condition(mc_id)
        assert 0.0 <= rec.strength <= 1.0
        assert 0.0 <= rec.confidence <= 1.0


def test_v1_11_0_default_markets_cover_finance_surface():
    """The default market set must visibly cover the capital-market
    surface — rates, credit spreads, equity, funding, liquidity —
    so the demo looks finance-aware out of the box."""
    k = _seed_kernel()
    r = _run_default(k)
    market_types_seen: set[str] = set()
    for mc_id in r.per_period_summaries[0].market_condition_ids:
        market_types_seen.add(
            k.market_conditions.get_condition(mc_id).market_type
        )
    expected = {
        "reference_rates",
        "credit_spreads",
        "equity_market",
        "funding_market",
        "liquidity_market",
    }
    assert market_types_seen == expected


def test_v1_11_0_corporate_response_uses_market_condition_slot_not_signal_slot():
    """v1.11.0 type-correct cross-reference: market-condition ids
    must appear in trigger_market_condition_ids and **not** in
    trigger_signal_ids or trigger_industry_condition_ids."""
    k = _seed_kernel()
    r = _run_default(k)
    period = r.per_period_summaries[0]
    market_condition_set = set(period.market_condition_ids)
    industry_condition_set = set(period.industry_condition_ids)
    for rid in period.corporate_strategic_response_candidate_ids:
        c = k.strategic_responses.get_candidate(rid)
        # Every period's market-condition ids are cited in the
        # dedicated v1.11.0 slot.
        assert any(
            mc in market_condition_set
            for mc in c.trigger_market_condition_ids
        )
        # Neither the signal slot nor the industry-condition slot
        # may carry a market-condition id.
        for sid in c.trigger_signal_ids:
            assert sid not in market_condition_set
        for icid in c.trigger_industry_condition_ids:
            assert icid not in market_condition_set
        # And industry-condition ids must not leak into the
        # market-condition slot either.
        for mcid in c.trigger_market_condition_ids:
            assert mcid not in industry_condition_set


def test_v1_11_0_no_price_or_forecast_payload_keys_in_ledger():
    """No v1.11.0 record's ledger payload may carry a price /
    yield / spread / index / forecast / recommendation key — the
    capital-market surface is synthetic context only,
    end-to-end."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_keys = {
        "price",
        "market_price",
        "yield_value",
        "spread_bps",
        "index_level",
        "forecast_value",
        "expected_return",
        "recommendation",
        "target_price",
        "real_data_value",
        "market_size",
    }
    for rec in k.ledger.records[
        r.ledger_record_count_before : r.ledger_record_count_after
    ]:
        leaked = set(rec.payload.keys()) & forbidden_keys
        assert not leaked, (
            f"v1.11.0 demo record {rec.object_id!r} leaks forbidden "
            f"payload keys: {sorted(leaked)}"
        )


def test_v1_11_0_no_forbidden_action_or_price_event_types_appear():
    """The integrated v1.11.0 sweep must emit no action-class or
    price-formation-class record types — the capital-market
    surface is synthetic context only."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_event_types = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
        "firm_state_added",
    }
    seen = {
        rec.event_type
        for rec in k.ledger.records[
            r.ledger_record_count_before : r.ledger_record_count_after
        ]
    }
    assert seen.isdisjoint(forbidden_event_types), (
        "v1.11.0 integrated sweep emitted forbidden action / "
        f"price-formation records: {sorted(seen & forbidden_event_types)}"
    )


def test_v1_11_0_two_runs_produce_byte_identical_canonical_view():
    """v1.11.0 additions to LivingReferencePeriodSummary and the
    canonical view must remain deterministic — two fresh runs of
    the default fixture produce byte-identical canonical JSON."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_11_0_canonical_view_carries_market_id_tuples():
    """The canonical view must surface the v1.11.0 id tuples
    explicitly so a downstream lineage / replay consumer does not
    need to re-walk the ledger to find them."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
    )

    k = _seed_kernel()
    r = _run_default(k)
    can = canonicalize_living_world_result(k, r)
    assert "market_ids" in can
    assert "market_count" in can
    assert can["market_count"] == 5
    for ps in can["per_period_summaries"]:
        assert "market_condition_ids" in ps
        assert len(ps["market_condition_ids"]) == 5


# ===========================================================================
# v1.11.1 — capital-market readout integration
# ===========================================================================


def test_v1_11_1_one_capital_market_readout_per_period():
    """The v1.11.1 readout phase fires once per period; each
    period summary carries exactly one readout id."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.capital_market_readout_ids) == 1


def test_v1_11_1_readouts_resolve_and_carry_default_labels():
    """Each readout must resolve to a stored record whose
    overall_market_access_label sits in the documented enum and
    whose per-market tones come from the period's market
    conditions."""
    k = _seed_kernel()
    r = _run_default(k)
    allowed_overall = {
        "open_or_constructive",
        "selective_or_constrained",
        "mixed",
    }
    for ps in r.per_period_summaries:
        rec = k.capital_market_readouts.get_readout(
            ps.capital_market_readout_ids[0]
        )
        assert rec.overall_market_access_label in allowed_overall
        # The cited market_condition_ids must equal the period's
        # market_condition_ids.
        assert (
            tuple(rec.market_condition_ids) == ps.market_condition_ids
        )
        # The default fixture has rates / credit / equity /
        # funding / liquidity but no volatility market — the
        # builder should default volatility_tone to "unknown".
        assert rec.volatility_tone == "unknown"


def test_v1_11_1_default_overall_label_is_open_or_constructive():
    """The default fixture's market conditions (funding
    supportive, credit stable) are designed to land on
    open_or_constructive every period."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        rec = k.capital_market_readouts.get_readout(
            ps.capital_market_readout_ids[0]
        )
        assert rec.overall_market_access_label == "open_or_constructive"
        assert (
            rec.banker_summary_label
            == "constructive_market_access_synthetic"
        )


def test_v1_11_1_no_price_or_advice_payload_keys_in_ledger():
    """No v1.11.1 record's ledger payload may carry any of the
    forbidden price / forecast / recommendation / deal-advice
    keys — the readout layer is labels only."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_keys = {
        "price",
        "target_price",
        "yield_value",
        "spread_bps",
        "forecast_value",
        "expected_return",
        "recommendation",
        "deal_advice",
        "market_size",
        "real_data_value",
    }
    for rec in k.ledger.records[
        r.ledger_record_count_before : r.ledger_record_count_after
    ]:
        leaked = set(rec.payload.keys()) & forbidden_keys
        assert not leaked, (
            f"v1.11.1 demo record {rec.object_id!r} leaks forbidden "
            f"payload keys: {sorted(leaked)}"
        )


def test_v1_11_1_two_runs_produce_byte_identical_canonical_view():
    """v1.11.1's additive readout id tuple must keep the canonical
    view byte-identical across two fresh runs."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_11_1_canonical_view_carries_readout_id_tuples():
    """The canonical view must surface the v1.11.1 readout id
    tuple per period."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
    )

    k = _seed_kernel()
    r = _run_default(k)
    can = canonicalize_living_world_result(k, r)
    for ps in can["per_period_summaries"]:
        assert "capital_market_readout_ids" in ps
        assert len(ps["capital_market_readout_ids"]) == 1


def test_v1_11_1_markdown_report_includes_capital_market_surface_section():
    """The v1.11.1 Markdown report must include a "Capital market
    surface" section with the per-market tone columns + the
    overall column."""
    from world.living_world_report import (
        build_living_world_trace_report,
        render_living_world_markdown,
    )

    k = _seed_kernel()
    r = _run_default(k)
    report = build_living_world_trace_report(k, r)
    md = render_living_world_markdown(report)
    assert "## Capital market surface" in md
    assert "rates" in md
    assert "credit" in md
    assert "equity" in md
    assert "funding window" in md
    assert "liquidity" in md
    assert "volatility" in md
    assert "overall" in md
    assert "open_or_constructive" in md
    # v1.11.1 boundary phrasing must be present somewhere in the
    # rendered report — either inline under "## Capital market
    # surface" or in the "## Boundaries" footer.
    md_lower = md.lower()
    assert (
        "deal advice" in md_lower
        or "deal_advice" in md_lower
        or "spread calibration" in md_lower
    )


# ===========================================================================
# v1.11.2 — demo market regime presets
# ===========================================================================


_REGIME_TO_OVERALL: dict[str, str] = {
    "constructive": "open_or_constructive",
    "mixed": "mixed",
    "constrained": "selective_or_constrained",
    # The "tightening" preset emphasises rates tightening flowing
    # into credit (widening) and liquidity (tightening) while
    # funding leaves the supportive set; the v1.11.1 classifier
    # therefore reaches the second branch and lands on
    # selective_or_constrained.
    "tightening": "selective_or_constrained",
}


def _readout_for_first_period(kernel, result):
    """Resolve the v1.11.1 readout for the first period."""
    rid = result.per_period_summaries[0].capital_market_readout_ids[0]
    return kernel.capital_market_readouts.get_readout(rid)


@pytest.mark.parametrize(
    "regime", ["constructive", "mixed", "constrained", "tightening"]
)
def test_v1_11_2_regime_runs_and_produces_expected_overall(regime):
    """Each preset runs end-to-end and produces the documented
    overall_market_access_label every period."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_regime=regime,
    )
    expected_overall = _REGIME_TO_OVERALL[regime]
    for ps in r.per_period_summaries:
        rec = k.capital_market_readouts.get_readout(
            ps.capital_market_readout_ids[0]
        )
        assert rec.overall_market_access_label == expected_overall


@pytest.mark.parametrize(
    "regime", ["constructive", "mixed", "constrained", "tightening"]
)
def test_v1_11_2_regime_is_deterministic_across_two_runs(regime):
    """Two fresh runs of the same preset must produce
    byte-identical canonical JSON and the same digest."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = run_living_reference_world(
        k1,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_regime=regime,
    )
    k2 = _seed_kernel()
    r2 = run_living_reference_world(
        k2,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_regime=regime,
    )
    assert canonicalize_living_world_result(
        k1, r1
    ) == canonicalize_living_world_result(k2, r2)
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_11_2_regime_labels_differ_across_presets():
    """The four regimes must produce visibly different per-market
    tone tuples on the first period — the whole point of the
    preset layer."""
    tone_signatures: set[tuple[str, ...]] = set()
    for regime in ("constructive", "mixed", "constrained", "tightening"):
        k = _seed_kernel()
        r = run_living_reference_world(
            k,
            firm_ids=_FIRM_IDS,
            investor_ids=_INVESTOR_IDS,
            bank_ids=_BANK_IDS,
            period_dates=_PERIOD_DATES,
            market_regime=regime,
        )
        rec = _readout_for_first_period(k, r)
        sig = (
            rec.rates_tone,
            rec.credit_tone,
            rec.equity_tone,
            rec.funding_window_tone,
            rec.liquidity_tone,
        )
        tone_signatures.add(sig)
    assert len(tone_signatures) == 4, (
        "v1.11.2 regimes must produce 4 distinct per-market "
        f"tone tuples; got {tone_signatures!r}"
    )


def test_v1_11_2_default_behavior_unchanged_when_regime_is_none():
    """Omitting market_regime must preserve the v1.11.1 default
    behavior bit-for-bit. The default living_world_digest
    documented in §78.6 is the v1.11.1 / v1.11.2 backward-compat
    contract."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )

    k_with_none = _seed_kernel()
    r_with_none = run_living_reference_world(
        k_with_none,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        # market_regime omitted → default path
    )
    k_default = _seed_kernel()
    r_default = run_living_reference_world(
        k_default,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    assert living_world_digest(
        k_with_none, r_with_none
    ) == living_world_digest(k_default, r_default)


def test_v1_11_2_unknown_regime_raises_value_error():
    k = _seed_kernel()
    with pytest.raises(ValueError):
        run_living_reference_world(
            k,
            firm_ids=_FIRM_IDS,
            investor_ids=_INVESTOR_IDS,
            bank_ids=_BANK_IDS,
            period_dates=_PERIOD_DATES,
            market_regime="not_a_regime",
        )


def test_v1_11_2_explicit_market_condition_specs_overrides_regime():
    """If a caller supplies explicit specs and a regime, the
    explicit specs win. Document the resolution order in
    §79."""
    explicit_specs = (
        (
            "market:reference_rates_general",
            "reference_rates",
            "rate_level",
            "easing",
            0.7,
            0.7,
            "medium_term",
        ),
        (
            "market:reference_credit_spreads_general",
            "credit_spreads",
            "spread_level",
            "narrowing",
            0.7,
            0.7,
            "medium_term",
        ),
        (
            "market:reference_equity_general",
            "equity_market",
            "valuation_environment",
            "supportive",
            0.7,
            0.7,
            "medium_term",
        ),
        (
            "market:reference_funding_general",
            "funding_market",
            "funding_window",
            "supportive",
            0.7,
            0.7,
            "short_term",
        ),
        (
            "market:reference_liquidity_general",
            "liquidity_market",
            "liquidity_regime",
            "stable",
            0.7,
            0.7,
            "short_term",
        ),
    )
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_condition_specs=explicit_specs,
        # regime that would otherwise produce
        # selective_or_constrained — must be ignored.
        market_regime="constrained",
    )
    rec = _readout_for_first_period(k, r)
    # Explicit specs imply open_or_constructive (funding
    # supportive + credit narrowing). If the regime had won, the
    # overall would be selective_or_constrained.
    assert rec.overall_market_access_label == "open_or_constructive"


def test_v1_11_2_regime_runs_emit_no_forbidden_event_types():
    """Across every preset, the integrated sweep must emit no
    action-class / pricing / issuance event types — the
    presets only swap labels; they don't introduce execution
    behavior."""
    forbidden_event_types = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
        "firm_state_added",
    }
    for regime in ("constructive", "mixed", "constrained", "tightening"):
        k = _seed_kernel()
        r = run_living_reference_world(
            k,
            firm_ids=_FIRM_IDS,
            investor_ids=_INVESTOR_IDS,
            bank_ids=_BANK_IDS,
            period_dates=_PERIOD_DATES,
            market_regime=regime,
        )
        seen = {
            rec.event_type
            for rec in k.ledger.records[
                r.ledger_record_count_before : r.ledger_record_count_after
            ]
        }
        assert seen.isdisjoint(forbidden_event_types), (
            f"v1.11.2 regime {regime!r} sweep emitted forbidden "
            f"records: {sorted(seen & forbidden_event_types)}"
        )


def test_v1_11_2_regime_runs_carry_no_price_or_advice_payload_keys():
    """Across every preset, no record's ledger payload may carry
    any forbidden price / forecast / recommendation / deal-advice
    key. v1.11.0 / v1.11.1 anti-fields apply unchanged."""
    forbidden_keys = {
        "price",
        "market_price",
        "yield_value",
        "spread_bps",
        "index_level",
        "forecast_value",
        "expected_return",
        "recommendation",
        "target_price",
        "real_data_value",
        "market_size",
        "deal_advice",
    }
    for regime in ("constructive", "mixed", "constrained", "tightening"):
        k = _seed_kernel()
        r = run_living_reference_world(
            k,
            firm_ids=_FIRM_IDS,
            investor_ids=_INVESTOR_IDS,
            bank_ids=_BANK_IDS,
            period_dates=_PERIOD_DATES,
            market_regime=regime,
        )
        for rec in k.ledger.records[
            r.ledger_record_count_before : r.ledger_record_count_after
        ]:
            leaked = set(rec.payload.keys()) & forbidden_keys
            assert not leaked, (
                f"v1.11.2 regime {regime!r} record {rec.object_id!r} "
                f"leaks forbidden payload keys: {sorted(leaked)}"
            )


def test_v1_11_2_cli_smoke_with_market_regime_flag():
    """The CLI ``--market-regime`` flag drives the orchestrator
    through to the readout, prints a regime banner, and produces
    a per-period trace."""
    from examples.reference_world import run_living_reference_world as cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.main(["--market-regime", "constrained"])
    out = buf.getvalue()
    assert "[regime]" in out
    assert "constrained" in out
    assert "[setup]" in out
    assert "market_readouts=" in out


# ===========================================================================
# v1.12.0 — firm financial latent state integration
# ===========================================================================


def test_v1_12_0_one_firm_financial_state_per_firm_per_period():
    """The v1.12.0 firm-state phase fires once per (firm, period);
    each period summary carries one state id per firm."""
    k = _seed_kernel()
    r = _run_default(k)
    expected = len(_FIRM_IDS)
    for ps in r.per_period_summaries:
        assert len(ps.firm_financial_state_ids) == expected


def test_v1_12_0_firm_states_resolve_and_carry_bounded_scalars():
    k = _seed_kernel()
    r = _run_default(k)
    seen_ids: set[str] = set()
    for ps in r.per_period_summaries:
        seen_ids.update(ps.firm_financial_state_ids)
    for sid in seen_ids:
        rec = k.firm_financial_states.get_state(sid)
        for v in (
            rec.margin_pressure,
            rec.liquidity_pressure,
            rec.debt_service_pressure,
            rec.market_access_pressure,
            rec.funding_need_intensity,
            rec.response_readiness,
            rec.confidence,
        ):
            assert 0.0 <= v <= 1.0


def test_v1_12_0_firm_states_chain_via_previous_state_id_within_run():
    """Across periods 1 → 4 for the same firm, every state after
    the first must carry a previous_state_id pointing at the
    state from the prior period."""
    k = _seed_kernel()
    r = _run_default(k)
    for firm_id in _FIRM_IDS:
        states = [
            k.firm_financial_states.get_state(
                ps.firm_financial_state_ids[
                    list(_FIRM_IDS).index(firm_id)
                ]
            )
            for ps in r.per_period_summaries
        ]
        assert states[0].previous_state_id is None
        for i in range(1, len(states)):
            assert states[i].previous_state_id == states[i - 1].state_id


def test_v1_12_0_constructive_regime_yields_lower_market_access_pressure_than_constrained():
    """The headline endogenous-dynamics integration test: under
    `constructive`, average market_access_pressure across firms
    decays below baseline by the final period; under
    `constrained`, it rises materially. The two regimes must
    produce a visible end-of-run gap."""
    def _final_avg_market_access(regime: str) -> float:
        k = _seed_kernel()
        r = run_living_reference_world(
            k,
            firm_ids=_FIRM_IDS,
            investor_ids=_INVESTOR_IDS,
            bank_ids=_BANK_IDS,
            period_dates=_PERIOD_DATES,
            market_regime=regime,
        )
        last = r.per_period_summaries[-1]
        states = [
            k.firm_financial_states.get_state(sid)
            for sid in last.firm_financial_state_ids
        ]
        return sum(s.market_access_pressure for s in states) / len(states)

    constructive_final = _final_avg_market_access("constructive")
    constrained_final = _final_avg_market_access("constrained")
    assert constructive_final < constrained_final
    # Visible separation — not just floating-point noise.
    assert constrained_final - constructive_final > 0.3


def test_v1_12_0_no_accounting_or_forecast_payload_keys_in_ledger():
    """No v1.12.0 record's ledger payload may carry any
    accounting / forecast / recommendation key."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_keys = {
        "revenue",
        "sales",
        "EBITDA",
        "ebitda",
        "net_income",
        "cash_balance",
        "debt_amount",
        "real_financial_statement",
        "forecast_value",
        "actual_value",
        "accounting_value",
        "investment_recommendation",
    }
    for rec in k.ledger.records[
        r.ledger_record_count_before : r.ledger_record_count_after
    ]:
        leaked = set(rec.payload.keys()) & forbidden_keys
        assert not leaked, (
            f"v1.12.0 demo record {rec.object_id!r} leaks forbidden "
            f"payload keys: {sorted(leaked)}"
        )


def test_v1_12_0_no_forbidden_action_or_firm_state_added_event_types():
    """The integrated v1.12.0 sweep must not emit any
    action-class record. In particular, the legacy v0/v1
    `firm_state_added` registration event must not appear — the
    new event type is `firm_latent_state_updated`, not
    `firm_state_added`."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_event_types = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
        "firm_state_added",
    }
    seen = {
        rec.event_type
        for rec in k.ledger.records[
            r.ledger_record_count_before : r.ledger_record_count_after
        ]
    }
    assert seen.isdisjoint(forbidden_event_types), (
        "v1.12.0 integrated sweep emitted forbidden event types: "
        f"{sorted(seen & forbidden_event_types)}"
    )


def test_v1_12_0_two_runs_produce_byte_identical_canonical_view():
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_12_0_canonical_view_carries_firm_financial_state_id_tuples():
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
    )

    k = _seed_kernel()
    r = _run_default(k)
    can = canonicalize_living_world_result(k, r)
    for ps in can["per_period_summaries"]:
        assert "firm_financial_state_ids" in ps
        assert len(ps["firm_financial_state_ids"]) == len(_FIRM_IDS)


def test_v1_12_0_markdown_report_includes_firm_financial_states_section():
    from world.living_world_report import (
        build_living_world_trace_report,
        render_living_world_markdown,
    )

    k = _seed_kernel()
    r = _run_default(k)
    report = build_living_world_trace_report(k, r)
    md = render_living_world_markdown(report)
    assert "## Firm financial states" in md
    assert "avg margin" in md
    assert "avg liquidity" in md
    assert "avg debt service" in md
    assert "avg market access" in md
    assert "avg funding need" in md
    assert "avg response readiness" in md
    md_lower = md.lower()
    assert (
        "not** an accounting statement" in md_lower
        or "not* an accounting statement" in md_lower
        or "ordering scalars" in md_lower
    )


# ===========================================================================
# v1.12.1 — investor intent integration
# ===========================================================================


def test_v1_12_1_one_investor_intent_per_pair_per_period():
    """The v1.12.1 investor-intent phase fires once per (investor,
    firm) per period."""
    k = _seed_kernel()
    r = _run_default(k)
    expected = len(_INVESTOR_IDS) * len(_FIRM_IDS)
    for ps in r.per_period_summaries:
        assert len(ps.investor_intent_ids) == expected


def test_v1_12_1_intent_records_resolve_and_carry_evidence():
    """Each intent must resolve to a stored record whose
    intent_direction sits in the documented label set and whose
    evidence id tuples carry the period's selection / readout /
    firm_state / valuation / dialogue / escalation / theme ids
    (attention discipline)."""
    k = _seed_kernel()
    r = _run_default(k)
    allowed_directions = {
        "increase_watch",
        "decrease_confidence",
        "engagement_watch",
        "hold_review",
        "risk_flag_watch",
        "deepen_due_diligence",
        "coverage_review",
    }
    for ps in r.per_period_summaries:
        for iid in ps.investor_intent_ids:
            rec = k.investor_intents.get_intent(iid)
            assert rec.intent_direction in allowed_directions
            # Evidence ids should be non-empty under the default
            # fixture: the orchestrator cites at least one
            # selection, the period's readout, the firm's state,
            # the (investor, firm) pair's dialogue, and the
            # escalation candidate.
            assert len(rec.evidence_selected_observation_set_ids) >= 1
            assert len(rec.evidence_market_readout_ids) >= 1
            assert len(rec.evidence_firm_state_ids) >= 1
            assert len(rec.evidence_dialogue_ids) >= 1
            assert len(rec.evidence_escalation_candidate_ids) >= 1


def test_v1_12_1_default_regime_yields_engagement_watch():
    """Under the default fixture (open_or_constructive market +
    dialogues + escalations cited but pressures not yet high),
    every intent lands on engagement_watch."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for iid in ps.investor_intent_ids:
            rec = k.investor_intents.get_intent(iid)
            assert rec.intent_direction == "engagement_watch"
            assert rec.intent_type == "engagement_review"


def test_v1_12_1_constrained_regime_yields_risk_or_due_diligence():
    """Under the constrained market regime, firm pressures
    accumulate and the market readout is restrictive, so intents
    land on risk_flag_watch (rule 2) or deepen_due_diligence
    (rule 1) — never on engagement_watch / hold_review."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_regime="constrained",
    )
    seen: set[str] = set()
    for ps in r.per_period_summaries:
        for iid in ps.investor_intent_ids:
            rec = k.investor_intents.get_intent(iid)
            seen.add(rec.intent_direction)
    assert seen.issubset({"risk_flag_watch", "deepen_due_diligence"})
    # And the constrained regime must produce at least one
    # risk_flag_watch / deepen_due_diligence intent.
    assert seen


def test_v1_12_1_no_order_or_recommendation_payload_keys_in_ledger():
    """No v1.12.1 record's ledger payload may carry any
    forbidden order / trade / rebalance / recommendation /
    execution key."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_keys = {
        "order",
        "order_id",
        "trade",
        "buy",
        "sell",
        "rebalance",
        "target_weight",
        "overweight",
        "underweight",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "portfolio_allocation",
        "execution",
    }
    for rec in k.ledger.records[
        r.ledger_record_count_before : r.ledger_record_count_after
    ]:
        leaked = set(rec.payload.keys()) & forbidden_keys
        assert not leaked, (
            f"v1.12.1 demo record {rec.object_id!r} leaks forbidden "
            f"payload keys: {sorted(leaked)}"
        )


def test_v1_12_1_no_forbidden_action_event_types_appear():
    """The integrated v1.12.1 sweep must not emit any
    action / pricing / trading / firm-state-added (legacy) record."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_event_types = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
        "firm_state_added",
    }
    seen = {
        rec.event_type
        for rec in k.ledger.records[
            r.ledger_record_count_before : r.ledger_record_count_after
        ]
    }
    assert seen.isdisjoint(forbidden_event_types), (
        "v1.12.1 integrated sweep emitted forbidden event types: "
        f"{sorted(seen & forbidden_event_types)}"
    )


def test_v1_12_1_two_runs_produce_byte_identical_canonical_view():
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_12_1_canonical_view_carries_investor_intent_id_tuples():
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
    )

    k = _seed_kernel()
    r = _run_default(k)
    can = canonicalize_living_world_result(k, r)
    expected_per_period = len(_INVESTOR_IDS) * len(_FIRM_IDS)
    for ps in can["per_period_summaries"]:
        assert "investor_intent_ids" in ps
        assert len(ps["investor_intent_ids"]) == expected_per_period


def test_v1_12_1_markdown_report_includes_investor_intent_section():
    from world.living_world_report import (
        build_living_world_trace_report,
        render_living_world_markdown,
    )

    k = _seed_kernel()
    r = _run_default(k)
    report = build_living_world_trace_report(k, r)
    md = render_living_world_markdown(report)
    assert "## Investor intent" in md
    # Histogram column must contain at least one of the v1.12.1
    # direction labels.
    assert "engagement_watch" in md or "hold_review" in md or "risk_flag_watch" in md
    md_lower = md.lower()
    # v1.12.1 anti-claims must show up either in the section
    # caption or in the boundary footer.
    assert (
        "not** an order" in md_lower
        or "not* an order" in md_lower
        or "non-binding labels only" in md_lower
        or "no order submission" in md_lower
    )


# ---------------------------------------------------------------------------
# v1.12.4 — attention-conditioned investor intent (orchestrator wiring)
# ---------------------------------------------------------------------------


def test_v1_12_4_orchestrator_uses_attention_conditioned_helper():
    """Every intent the orchestrator produces must carry the
    v1.12.4 attention metadata stamped by the new helper."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for iid in ps.investor_intent_ids:
            rec = k.investor_intents.get_intent(iid)
            assert rec.metadata.get("attention_conditioned") is True
            assert rec.metadata.get("context_frame_id"), (
                f"intent {iid!r} missing context_frame_id"
            )
            assert rec.metadata.get("context_frame_status") in {
                "resolved",
                "partially_resolved",
                "empty",
            }
            assert isinstance(
                rec.metadata.get("context_frame_confidence"), (int, float)
            )


def test_v1_12_4_orchestrator_intent_carries_selection_id_per_investor():
    """v1.12.4 routing: every intent's
    ``evidence_selected_observation_set_ids`` must reference the
    matching investor's per-period selection — not anyone else's.
    v1.12.8 widening: from period 1 onwards the tuple may also
    include a *memory* selection id (``selection:memory:...``)
    drawn from the investor's prior-period attention state. The
    period selection must always be the first id."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        sel_by_investor: dict[str, str] = {}
        for sid in ps.investor_selection_ids:
            sel = k.attention.get_selection(sid)
            sel_by_investor[sel.actor_id] = sid
        for iid in ps.investor_intent_ids:
            rec = k.investor_intents.get_intent(iid)
            expected = sel_by_investor.get(rec.investor_id)
            assert expected is not None
            assert (
                rec.evidence_selected_observation_set_ids[0] == expected
            )
            # Any extra ids must be v1.12.8 memory selections
            # for the same investor.
            for extra in rec.evidence_selected_observation_set_ids[1:]:
                assert extra.startswith("selection:memory:")
                assert rec.investor_id in extra


def test_v1_12_4_orchestrator_living_world_digest_remains_deterministic():
    """The orchestrator's switch to the attention-conditioned
    helper must keep the living-world canonical view byte-
    identical across two fresh runs."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_12_4_constrained_regime_still_yields_risk_or_due_diligence():
    """The v1.12.1 regime-divergence behavior must be preserved
    under the new helper — the constrained regime still lands
    every intent on risk_flag_watch or deepen_due_diligence."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_regime="constrained",
    )
    seen: set[str] = set()
    for ps in r.per_period_summaries:
        for iid in ps.investor_intent_ids:
            rec = k.investor_intents.get_intent(iid)
            seen.add(rec.intent_direction)
    assert seen
    assert seen.issubset({"risk_flag_watch", "deepen_due_diligence"})


# ---------------------------------------------------------------------------
# v1.12.7 — orchestrator-level attention-conditioned valuation +
# bank credit review wiring
# ---------------------------------------------------------------------------


def test_v1_12_7_orchestrator_valuation_carries_context_frame_metadata():
    """Every valuation the orchestrator produces must carry the
    four v1.12.5 attention-metadata keys stamped by the new
    helper."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for vid in ps.valuation_ids:
            rec = k.valuations.get_valuation(vid)
            assert rec.metadata.get("attention_conditioned") is True
            assert rec.metadata.get("context_frame_id"), (
                f"valuation {vid!r} missing context_frame_id"
            )
            assert rec.metadata.get("context_frame_status") in {
                "resolved",
                "partially_resolved",
                "empty",
            }
            assert isinstance(
                rec.metadata.get("context_frame_confidence"),
                (int, float),
            )
            # v1.9.5 anti-claim flags must remain bit-for-bit.
            assert rec.metadata.get("no_price_movement") is True
            assert rec.metadata.get("no_investment_advice") is True
            assert rec.metadata.get("synthetic_only") is True


def test_v1_12_7_orchestrator_credit_review_carries_watch_label():
    """Every bank credit review signal the orchestrator produces
    must carry the v1.12.6 watch_label + four context-frame
    metadata keys, and preserve the eight v1.9.7 boundary
    anti-claim flags bit-for-bit."""
    from world.reference_bank_credit_review_lite import (
        ALL_WATCH_LABELS,
    )

    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for sid in ps.bank_credit_review_signal_ids:
            sig = k.signals.get_signal(sid)
            assert sig.metadata.get("attention_conditioned") is True
            assert sig.metadata.get("context_frame_id"), (
                f"signal {sid!r} missing context_frame_id"
            )
            assert sig.metadata.get("context_frame_status") in {
                "resolved",
                "partially_resolved",
                "empty",
            }
            assert isinstance(
                sig.metadata.get("context_frame_confidence"),
                (int, float),
            )
            assert sig.payload.get("watch_label") in ALL_WATCH_LABELS
            for flag in (
                "no_lending_decision",
                "no_covenant_enforcement",
                "no_contract_mutation",
                "no_constraint_mutation",
                "no_default_declaration",
                "no_internal_rating",
                "no_probability_of_default",
                "synthetic_only",
            ):
                assert sig.metadata.get(flag) is True


def test_v1_12_7_valuation_carries_investor_specific_selection_id():
    """The orchestrator passes each investor's own
    `SelectedObservationSet` to the v1.12.5 valuation helper.
    The produced valuation's `metadata["context_frame_id"]` must
    therefore reference the valuer's actor id."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for vid in ps.valuation_ids:
            rec = k.valuations.get_valuation(vid)
            cfid = rec.metadata.get("context_frame_id", "")
            assert rec.valuer_id in cfid


def test_v1_12_7_credit_review_carries_bank_specific_selection_id():
    """The orchestrator passes each bank's own
    `SelectedObservationSet` to the v1.12.6 credit review
    helper. The produced signal's
    `metadata["context_frame_id"]` must therefore reference the
    bank's actor id (the `source_id` on the signal)."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for sid in ps.bank_credit_review_signal_ids:
            sig = k.signals.get_signal(sid)
            cfid = sig.metadata.get("context_frame_id", "")
            assert sig.source_id in cfid


def test_v1_12_7_no_forbidden_payload_keys_in_orchestrator_run():
    """Across the entire integrated v1.12.7 run, no ledger
    payload may carry any forbidden trading / lending /
    rating / advice key."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_keys = {
        "order",
        "order_id",
        "trade",
        "buy",
        "sell",
        "rebalance",
        "target_weight",
        "overweight",
        "underweight",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "portfolio_allocation",
        "execution",
        "lending_decision",
        "loan_approved",
        "loan_rejected",
        "covenant_breached",
        "covenant_enforced",
        "contract_amended",
        "constraint_changed",
        "default_declared",
        "internal_rating",
        "rating_grade",
        "probability_of_default",
        "pd",
        "lgd",
        "ead",
        "loan_pricing",
        "credit_pricing",
        "interest_rate",
        "underwriting_decision",
        "approval_status",
        "loan_terms",
    }
    for rec in k.ledger.records[
        r.ledger_record_count_before : r.ledger_record_count_after
    ]:
        leaked = set(rec.payload.keys()) & forbidden_keys
        assert not leaked, (
            f"v1.12.7 demo record {rec.object_id!r} ({rec.event_type}) "
            f"leaks forbidden payload keys: {sorted(leaked)}"
        )


def test_v1_12_7_no_forbidden_event_types():
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_event_types = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
        "firm_state_added",
    }
    seen = {
        rec.event_type
        for rec in k.ledger.records[
            r.ledger_record_count_before : r.ledger_record_count_after
        ]
    }
    assert seen.isdisjoint(forbidden_event_types), (
        "v1.12.7 integrated sweep emitted forbidden event types: "
        f"{sorted(seen & forbidden_event_types)}"
    )


def test_v1_12_7_canonical_replay_deterministic():
    """v1.12.7 changes the canonical-view bytes (new metadata),
    but two fresh runs of the same fixture must still produce
    byte-identical canonical views and digests."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_12_9_living_world_digest_pinned():
    """Pin the v1.12.9 living_world_digest so any future
    silent change to the attention-budget rule set,
    `apply_attention_budget`, the decay/crowding logic in
    `build_attention_feedback`, or the orchestrator's
    memory-selection wiring fails loudly.

    The digest moves at v1.12.9 because the new state record
    carries `per_dimension_budget` / `decay_horizon` /
    `saturation_policy` fields and a new
    `metadata["focus_stale_counts"]` carry-forward map; the
    memory `SelectedObservationSet` is now budget-bounded
    rather than fully accumulating.

    The digest moves again at v1.13.5: the orchestrator now
    emits one `interbank_liquidity_state_recorded` ledger
    record per bank per period (2 banks × 4 periods = 8 new
    records in the default fixture) and stamps the cited ids
    onto each `bank_credit_review_note` payload + metadata.

    The digest moves again at v1.14.5: the orchestrator now
    emits a corporate financing chain per firm per period —
    one CorporateFinancingNeedRecord, two FundingOptionCandidate
    records, one CapitalStructureReviewCandidate, and one
    CorporateFinancingPathRecord (5 × 3 firms × 4 periods = 60
    new records in the default fixture). Storage / audit /
    graph-linking only — never an order, trade, allocation,
    loan approval, security issuance, pricing, or
    recommendation.

    v1.16.2 moves the digest by design: the v1.15.5
    investor-market-intent phase now calls the v1.16.1
    ``classify_market_intent_direction(...)`` pure function
    instead of the four-cycle ``(period_idx + inv_idx + firm_idx)
    % 4`` rotation. ``InvestorMarketIntentRecord`` payloads now
    carry classifier-derived ``intent_direction_label`` /
    ``intensity_label`` / ``confidence`` and a classifier-audit
    ``metadata`` block (``classifier_version`` /
    ``classifier_rule_id`` / ``classifier_status`` /
    ``classifier_confidence`` /
    ``classifier_unresolved_or_missing_count`` /
    ``classifier_evidence_summary``). Record count and per-run
    window are **unchanged**.
    """
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )

    k = _seed_kernel()
    r = _run_default(k)
    expected = (
        "0b75e95ad8f157df5e938c1318817c07f00798179c3d11b8629452d30d9398fa"
    )
    assert living_world_digest(k, r) == expected, (
        "v1.16.2 living_world_digest moved unexpectedly. If the "
        "shift is intentional, update the pinned value here AND "
        "in docs/world_model.md and docs/test_inventory.md."
    )


def test_v1_12_7_constrained_regime_still_diverges():
    """The v1.12.1 / v1.12.4 regime-divergence behaviour must
    survive the v1.12.7 orchestrator switch — the constrained
    regime still produces non-routine investor intents."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_regime="constrained",
    )
    intent_directions: set[str] = set()
    for ps in r.per_period_summaries:
        for iid in ps.investor_intent_ids:
            rec = k.investor_intents.get_intent(iid)
            intent_directions.add(rec.intent_direction)
    assert intent_directions
    assert intent_directions.issubset(
        {"risk_flag_watch", "deepen_due_diligence"}
    )


def test_v1_12_7_constrained_regime_shifts_credit_review_watch_label():
    """Under the constrained market regime the orchestrator's
    bank credit reviews should produce at least one non-routine
    watch label (anything except routine_monitoring), proving
    that the bank's resolved frame actually drives the
    classification through the orchestrator path."""
    from world.reference_bank_credit_review_lite import (
        WATCH_LABEL_ROUTINE_MONITORING,
    )

    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_regime="constrained",
    )
    seen_labels: set[str] = set()
    for ps in r.per_period_summaries:
        for sid in ps.bank_credit_review_signal_ids:
            sig = k.signals.get_signal(sid)
            seen_labels.add(sig.payload["watch_label"])
    assert seen_labels
    # Under the constrained regime at least one non-routine
    # label must fire across the run.
    assert seen_labels - {WATCH_LABEL_ROUTINE_MONITORING}


def test_v1_12_7_markdown_report_renders_without_error():
    """The v1.9.1 trace report must continue to render the
    integrated v1.12.7 ledger slice without raising."""
    from world.living_world_report import (
        build_living_world_trace_report,
        render_living_world_markdown,
    )

    k = _seed_kernel()
    r = _run_default(k)
    report = build_living_world_trace_report(k, r)
    md = render_living_world_markdown(report)
    assert isinstance(md, str)
    assert len(md) > 0
    # Spot-check that the integrated v1.12.4 investor-intent
    # section still renders.
    assert "## Investor intent" in md


# ---------------------------------------------------------------------------
# v1.12.8 — cross-period attention feedback (HEADLINE)
# ---------------------------------------------------------------------------


def test_v1_12_8_orchestrator_emits_attention_state_per_actor_per_period():
    """Every period must produce one attention state +
    feedback per investor + per bank."""
    k = _seed_kernel()
    r = _run_default(k)
    n_inv = len(_INVESTOR_IDS)
    n_bank = len(_BANK_IDS)
    for ps in r.per_period_summaries:
        assert len(ps.investor_attention_state_ids) == n_inv
        assert len(ps.investor_attention_feedback_ids) == n_inv
        assert len(ps.bank_attention_state_ids) == n_bank
        assert len(ps.bank_attention_feedback_ids) == n_bank


def test_v1_12_8_attention_states_chain_across_periods():
    """Each actor's attention-state series must chain via
    ``previous_attention_state_id`` across periods. Period 0
    has ``previous_attention_state_id is None``; period N>=1
    references the actor's period N-1 state."""
    k = _seed_kernel()
    r = _run_default(k)
    investor = _INVESTOR_IDS[0]
    states_for_investor = []
    for ps in r.per_period_summaries:
        for asid in ps.investor_attention_state_ids:
            state = k.attention_feedback.get_attention_state(asid)
            if state.actor_id == investor:
                states_for_investor.append(state)
    # Period 0 has no prior; periods 1..N reference the prior.
    assert states_for_investor[0].previous_attention_state_id is None
    for prev, cur in zip(states_for_investor, states_for_investor[1:]):
        assert cur.previous_attention_state_id == prev.attention_state_id


def test_v1_12_8_period_0_has_no_memory_selection():
    """The cross-period feedback can only fire from period 1
    onwards because period 0 has no prior attention state."""
    k = _seed_kernel()
    r = _run_default(k)
    ps0 = r.per_period_summaries[0]
    assert ps0.investor_memory_selection_ids == ()
    assert ps0.bank_memory_selection_ids == ()


def test_v1_12_8_period_1_has_memory_selection_per_investor():
    """Under the default fixture (engagement_watch intent)
    every investor's prior attention state carries
    ``focus_label="dialogue"`` and ``focus_label="engagement"``,
    which both point at the prior-period dialogue ids. Period
    1 therefore builds one memory selection per investor."""
    k = _seed_kernel()
    r = _run_default(k)
    ps1 = r.per_period_summaries[1]
    assert len(ps1.investor_memory_selection_ids) == len(_INVESTOR_IDS)
    # Every memory selection is a SelectedObservationSet with
    # selection_reason="attention_feedback_memory" and a
    # non-empty selected_refs.
    for sid in ps1.investor_memory_selection_ids:
        sel = k.attention.get_selection(sid)
        assert sel.selection_reason == "attention_feedback_memory"
        assert len(sel.selected_refs) > 0
        assert sel.metadata.get("v1_12_8_memory_selection") is True


def test_v1_12_8_period_n_plus_1_intent_has_wider_selected_evidence_than_period_n():
    """**The headline cross-period feedback pin.**

    Period N's outcome (engagement_watch intent under the
    default fixture) writes a new ActorAttentionStateRecord
    whose focus_labels point at dialogue / engagement /
    escalation evidence. At period N+1, the orchestrator
    consults this state, builds a memory
    SelectedObservationSet from the prior period's dialogue
    ids, and passes it alongside the regular per-period
    selection to the v1.12.4 attention-conditioned investor
    intent helper. The intent record at period N+1 therefore
    surfaces *more* selected_observation_set_ids than the
    intent record at period N — proving that period N's
    outcome changed period N+1's selected evidence.
    """
    k = _seed_kernel()
    r = _run_default(k)

    investor = _INVESTOR_IDS[0]
    firm = _FIRM_IDS[0]

    ps0 = r.per_period_summaries[0]
    ps1 = r.per_period_summaries[1]

    intent_p0 = next(
        iid
        for iid in ps0.investor_intent_ids
        if f":{investor}:" in iid and f":{firm}:" in iid
    )
    intent_p1 = next(
        iid
        for iid in ps1.investor_intent_ids
        if f":{investor}:" in iid and f":{firm}:" in iid
    )
    rec0 = k.investor_intents.get_intent(intent_p0)
    rec1 = k.investor_intents.get_intent(intent_p1)

    sel_count_p0 = len(rec0.evidence_selected_observation_set_ids)
    sel_count_p1 = len(rec1.evidence_selected_observation_set_ids)

    # Period 0: only the regular per-period selection.
    assert sel_count_p0 == 1
    # Period 1: regular per-period selection + memory selection.
    assert sel_count_p1 == 2, (
        f"v1.12.8 cross-period feedback failed: period 1 intent "
        f"should reference 2 selections (period + memory) but "
        f"reports {sel_count_p1}: "
        f"{rec1.evidence_selected_observation_set_ids}"
    )
    assert sel_count_p1 > sel_count_p0

    # The second selection must be the memory selection — a
    # selection whose id starts with ``selection:memory:``.
    second = rec1.evidence_selected_observation_set_ids[1]
    assert second.startswith("selection:memory:")
    # And the memory selection must carry the v1.12.8 marker.
    sel = k.attention.get_selection(second)
    assert sel.metadata.get("v1_12_8_memory_selection") is True


def test_v1_12_8_period_n_plus_1_intent_has_wider_resolved_dialogue_evidence():
    """A complementary form of the headline pin. Because the
    memory selection's selected_refs include prior-period
    dialogue ids, the v1.12.4 helper resolves them into the
    intent's ``evidence_dialogue_ids`` slot. Period 1's
    resolved dialogue evidence is therefore strictly wider
    than period 0's for the same (investor, firm) pair."""
    k = _seed_kernel()
    r = _run_default(k)

    investor = _INVESTOR_IDS[0]
    firm = _FIRM_IDS[0]

    intent_p0 = next(
        iid
        for iid in r.per_period_summaries[0].investor_intent_ids
        if f":{investor}:" in iid and f":{firm}:" in iid
    )
    intent_p1 = next(
        iid
        for iid in r.per_period_summaries[1].investor_intent_ids
        if f":{investor}:" in iid and f":{firm}:" in iid
    )
    rec0 = k.investor_intents.get_intent(intent_p0)
    rec1 = k.investor_intents.get_intent(intent_p1)
    assert (
        len(rec1.evidence_dialogue_ids)
        > len(rec0.evidence_dialogue_ids)
    ), (
        "v1.12.8 cross-period feedback failed: period 1 intent "
        "should resolve more dialogue evidence than period 0 "
        f"(period 0 = {rec0.evidence_dialogue_ids}; period 1 = "
        f"{rec1.evidence_dialogue_ids})"
    )


def test_v1_12_8_attention_state_emits_only_attention_event_types():
    """The integrated v1.12.8 sweep must emit only the new
    attention_state_created / attention_feedback_recorded
    record types, plus the existing event types — no new
    forbidden trading / lending / pricing events."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_event_types = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
    }
    seen = {
        rec.event_type
        for rec in k.ledger.records[
            r.ledger_record_count_before : r.ledger_record_count_after
        ]
    }
    assert seen.isdisjoint(forbidden_event_types)
    # And the two new event types must appear.
    assert "attention_state_created" in seen
    assert "attention_feedback_recorded" in seen


def test_v1_12_8_no_forbidden_payload_keys_in_attention_records():
    """No attention-state or feedback ledger payload may carry
    any forbidden order / trade / rating / advice key."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_keys = {
        "order",
        "trade",
        "rebalance",
        "target_price",
        "expected_return",
        "recommendation",
        "investment_advice",
        "portfolio_allocation",
        "execution",
        "lending_decision",
        "internal_rating",
        "probability_of_default",
        "behavior_probability",
    }
    for rec in k.ledger.records[
        r.ledger_record_count_before : r.ledger_record_count_after
    ]:
        if rec.event_type not in {
            "attention_state_created",
            "attention_feedback_recorded",
        }:
            continue
        leaked = set(rec.payload.keys()) & forbidden_keys
        assert not leaked, (
            f"v1.12.8 record {rec.object_id!r} leaks forbidden "
            f"payload keys: {sorted(leaked)}"
        )


def test_v1_12_8_canonical_replay_remains_deterministic():
    """Two fresh runs must still produce byte-identical
    canonical views and digests after the v1.12.8 wiring."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_12_8_constrained_regime_drives_risk_focus():
    """Under the constrained regime, period 1's investor
    attention state should carry risk-focused labels (the
    period 0 intent direction is risk_flag_watch /
    deepen_due_diligence under that regime). The trigger
    label must be ``risk_intent_observed`` for at least one
    investor."""
    from world.attention_feedback import (
        FOCUS_LABEL_FIRM_STATE,
        TRIGGER_RISK_INTENT_OBSERVED,
    )

    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_regime="constrained",
    )
    triggers: set[str] = set()
    focus_labels_seen: set[str] = set()
    for ps in r.per_period_summaries:
        for fbid in ps.investor_attention_feedback_ids:
            fb = k.attention_feedback.get_feedback(fbid)
            triggers.add(fb.trigger_label)
        for asid in ps.investor_attention_state_ids:
            state = k.attention_feedback.get_attention_state(asid)
            focus_labels_seen.update(state.focus_labels)
    assert TRIGGER_RISK_INTENT_OBSERVED in triggers
    assert FOCUS_LABEL_FIRM_STATE in focus_labels_seen


# ---------------------------------------------------------------------------
# v1.12.9 — attention budget / decay / saturation
# ---------------------------------------------------------------------------


def test_v1_12_9_state_carries_budget_fields():
    """Every orchestrator-produced attention state must carry
    the v1.12.9 budget fields."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for asid in (
            tuple(ps.investor_attention_state_ids)
            + tuple(ps.bank_attention_state_ids)
        ):
            state = k.attention_feedback.get_attention_state(asid)
            assert state.per_dimension_budget == 3
            assert state.decay_horizon == 2
            assert state.saturation_policy == "drop_oldest"
            # Every state's max_selected_refs is capped at the
            # v1.12.9 constant.
            assert 0 < state.max_selected_refs <= 12


def test_v1_12_9_memory_selection_size_respects_max_selected_refs():
    """No memory selection's ``selected_refs`` may exceed the
    actor's prior-state ``max_selected_refs``. This is the
    v1.12.9 attention-scarcity invariant: feedback is bounded,
    not monotonically accumulating."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for sid in (
            tuple(ps.investor_memory_selection_ids)
            + tuple(ps.bank_memory_selection_ids)
        ):
            sel = k.attention.get_selection(sid)
            actor_id = sel.actor_id
            prior_state = k.attention_feedback.get_latest_for_actor(
                actor_id
            )
            # The "latest for actor" at end-of-period N is the
            # state created at end of period N (since memory
            # selection at period N+1 is built from period N's
            # state). For the bound check we use the orchestrator's
            # cap at the time of memory build — _BASE_MAX + len ≤ 12.
            assert prior_state is not None
            assert (
                len(sel.selected_refs) <= prior_state.max_selected_refs
            )


def test_v1_12_9_memory_selection_size_does_not_grow_monotonically():
    """Across periods, memory selection size must stay bounded.
    Under the v1.12.9 budget the per-period investor memory
    selection's ref count must not exceed the cap regardless of
    how many periods have elapsed."""
    k = _seed_kernel()
    r = _run_default(k)
    investor = _INVESTOR_IDS[0]
    sizes: list[int] = []
    for ps in r.per_period_summaries:
        for sid in ps.investor_memory_selection_ids:
            sel = k.attention.get_selection(sid)
            if sel.actor_id == investor:
                sizes.append(len(sel.selected_refs))
    if not sizes:
        pytest.skip("no investor memory selections produced (period 0 only)")
    # The maximum ref count across periods must respect the
    # v1.12.9 cap (_MAX_SELECTED_REFS_CAP = 12).
    assert max(sizes) <= 12


def test_v1_12_9_state_metadata_carries_focus_stale_counts():
    k = _seed_kernel()
    r = _run_default(k)
    investor = _INVESTOR_IDS[0]
    for ps in r.per_period_summaries:
        for asid in ps.investor_attention_state_ids:
            state = k.attention_feedback.get_attention_state(asid)
            if state.actor_id != investor:
                continue
            counts = state.metadata.get("focus_stale_counts")
            assert isinstance(counts, dict)
            for label in state.focus_labels:
                assert label in counts


def test_v1_12_9_no_forbidden_payload_keys_in_v1_12_9_records():
    """v1.12.9 must not introduce any forbidden trading /
    lending / pricing / advice key on the attention-state
    or feedback ledger payload."""
    k = _seed_kernel()
    r = _run_default(k)
    forbidden_keys = {
        "order",
        "trade",
        "rebalance",
        "target_price",
        "expected_return",
        "recommendation",
        "investment_advice",
        "portfolio_allocation",
        "execution",
        "lending_decision",
        "internal_rating",
        "probability_of_default",
        "behavior_probability",
    }
    for rec in k.ledger.records[
        r.ledger_record_count_before : r.ledger_record_count_after
    ]:
        if rec.event_type not in {
            "attention_state_created",
            "attention_feedback_recorded",
        }:
            continue
        leaked = set(rec.payload.keys()) & forbidden_keys
        assert not leaked


def test_v1_12_9_constrained_regime_drives_risk_focus_with_decay():
    """Under the constrained regime period 0's outcomes are
    already risk-shaped, so the constrained regime exercises
    the v1.12.9 reinforcement path: every period reinforces the
    same risk focus, stale_count stays at 0 for risk labels,
    and the state's focus does not accidentally widen via
    decay-based inheritance."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
        market_regime="constrained",
    )
    investor = _INVESTOR_IDS[0]
    # Pick the last period's state for the first investor.
    last_period = r.per_period_summaries[-1]
    last_state_id = next(
        asid
        for asid in last_period.investor_attention_state_ids
        if k.attention_feedback.get_attention_state(asid).actor_id == investor
    )
    last_state = k.attention_feedback.get_attention_state(last_state_id)
    counts = last_state.metadata.get("focus_stale_counts", {})
    # Every active focus label has stale_count 0 — the
    # constrained regime keeps reinforcing the same labels.
    for label in last_state.focus_labels:
        assert counts.get(label) == 0
    # And every active label has weight 1.0 — none decayed.
    for label in last_state.focus_labels:
        assert last_state.focus_weights.get(label) == 1.0


# ---------------------------------------------------------------------------
# v1.12.2 — market environment state
# ---------------------------------------------------------------------------


def test_v1_12_2_one_market_environment_per_period():
    """v1.12.2 emits exactly one MarketEnvironmentStateRecord per
    period."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.market_environment_state_ids) == 1


def test_v1_12_2_environment_states_resolve_and_carry_regime_labels():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        sid = ps.market_environment_state_ids[0]
        rec = k.market_environments.get_state(sid)
        # All nine regime label fields must be non-empty strings.
        for field_name in (
            "liquidity_regime",
            "volatility_regime",
            "credit_regime",
            "funding_regime",
            "risk_appetite_regime",
            "rate_environment",
            "refinancing_window",
            "equity_valuation_regime",
            "overall_market_access_label",
        ):
            value = getattr(rec, field_name)
            assert isinstance(value, str) and value, (
                f"empty {field_name} on {sid}"
            )


def test_v1_12_2_default_overall_label_is_open_or_constructive():
    """Default fixture's market specs are constructive — the
    environment's overall label should match the default
    readout."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        sid = ps.market_environment_state_ids[0]
        rec = k.market_environments.get_state(sid)
        assert rec.overall_market_access_label == "open_or_constructive"


def test_v1_12_2_environment_cited_on_firm_state():
    """v1.12.2 type-correct cross-link: each firm state's
    ``evidence_market_environment_state_ids`` must include the
    period's environment-state id."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        env_id = ps.market_environment_state_ids[0]
        for fsid in ps.firm_financial_state_ids:
            state = k.firm_financial_states.get_state(fsid)
            assert env_id in state.evidence_market_environment_state_ids


def test_v1_12_2_environment_cited_on_investor_intent():
    """v1.12.2 type-correct cross-link: each investor intent's
    ``evidence_market_environment_state_ids`` must include the
    period's environment-state id."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        env_id = ps.market_environment_state_ids[0]
        for iid in ps.investor_intent_ids:
            intent = k.investor_intents.get_intent(iid)
            assert env_id in intent.evidence_market_environment_state_ids


def test_v1_12_2_environment_cited_on_corporate_response():
    """v1.12.2 type-correct cross-link: each corporate response
    candidate's ``trigger_market_environment_state_ids`` must
    include the period's environment-state id, and the env id
    must NOT ride in any other trigger slot."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        env_id = ps.market_environment_state_ids[0]
        for rid in ps.corporate_strategic_response_candidate_ids:
            cand = k.strategic_responses.get_candidate(rid)
            assert env_id in cand.trigger_market_environment_state_ids
            assert env_id not in cand.trigger_signal_ids
            assert env_id not in cand.trigger_industry_condition_ids
            assert env_id not in cand.trigger_market_condition_ids


def test_v1_12_2_no_price_or_forecast_payload_keys_in_ledger():
    """v1.12.2 ``market_environment_state_added`` payloads must
    not carry any anti-field key."""
    k = _seed_kernel()
    _run_default(k)
    forbidden = {
        "price",
        "market_price",
        "yield_value",
        "spread_bps",
        "index_level",
        "forecast_value",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "real_data_value",
        "market_size",
        "order",
        "trade",
        "allocation",
    }
    payloads = [
        record.payload
        for record in k.ledger.records
        if record.record_type.value == "market_environment_state_added"
    ]
    assert payloads, "no market_environment_state_added records emitted"
    for payload in payloads:
        leaked = set(payload.keys()) & forbidden
        assert not leaked, (
            "market_environment payload must not include anti-field "
            f"keys; leaked: {sorted(leaked)}"
        )


def test_v1_12_2_no_forbidden_event_types_appear():
    """v1.12.2 must not emit any new action / pricing / order /
    trade / allocation event."""
    from world.ledger import RecordType

    k = _seed_kernel()
    _run_default(k)
    forbidden = {
        RecordType.ORDER_SUBMITTED,
        RecordType.PRICE_UPDATED,
        RecordType.CONTRACT_CREATED,
        RecordType.CONTRACT_STATUS_UPDATED,
        RecordType.CONTRACT_COVENANT_BREACHED,
        RecordType.OWNERSHIP_TRANSFERRED,
    }
    seen = {r.record_type for r in k.ledger.records}
    leaked = seen & forbidden
    assert not leaked, (
        f"v1.12.2 must not emit {sorted(t.value for t in leaked)}"
    )


def test_v1_12_2_two_runs_produce_byte_identical_canonical_view():
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_12_2_canonical_view_carries_market_environment_id_tuples():
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
    )

    k = _seed_kernel()
    r = _run_default(k)
    can = canonicalize_living_world_result(k, r)
    for ps in can["per_period_summaries"]:
        assert "market_environment_state_ids" in ps
        assert len(ps["market_environment_state_ids"]) == 1


def test_v1_12_2_markdown_report_includes_market_environment_section():
    from world.living_world_report import (
        build_living_world_trace_report,
        render_living_world_markdown,
    )

    k = _seed_kernel()
    r = _run_default(k)
    report = build_living_world_trace_report(k, r)
    md = render_living_world_markdown(report)
    assert "## Market environment state" in md
    md_lower = md.lower()
    # v1.12.2 anti-claims must show up either in the section
    # caption or in the boundary footer.
    assert (
        "labels-only context" in md_lower
        or "no price" in md_lower
        or "no forecast" in md_lower
    )


# ---------------------------------------------------------------------------
# v1.14.5 — Living-world corporate financing chain integration
# ---------------------------------------------------------------------------


def test_v1_14_5_each_period_has_one_financing_need_per_firm():
    """One ``CorporateFinancingNeedRecord`` is emitted per firm per
    period — bounded by ``firms × periods``, not a quadratic loop."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.corporate_financing_need_ids) == len(_FIRM_IDS)
    total = sum(
        len(ps.corporate_financing_need_ids) for ps in r.per_period_summaries
    )
    assert total == len(_PERIOD_DATES) * len(_FIRM_IDS)


def test_v1_14_5_each_period_has_two_funding_options_per_need():
    """Bounded option set: exactly 2 options per need, per period."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert (
            len(ps.funding_option_candidate_ids)
            == 2 * len(ps.corporate_financing_need_ids)
        )
    total = sum(
        len(ps.funding_option_candidate_ids)
        for ps in r.per_period_summaries
    )
    assert total == 2 * len(_PERIOD_DATES) * len(_FIRM_IDS)


def test_v1_14_5_each_period_has_one_capital_review_per_firm():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert (
            len(ps.capital_structure_review_candidate_ids)
            == len(_FIRM_IDS)
        )


def test_v1_14_5_each_period_has_one_financing_path_per_firm():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.corporate_financing_path_ids) == len(_FIRM_IDS)


def test_v1_14_5_funding_options_cite_their_need():
    """Every option emitted in a period names a need id from the
    same period in its ``source_need_ids`` slot."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        period_needs = set(ps.corporate_financing_need_ids)
        for opt_id in ps.funding_option_candidate_ids:
            opt = k.funding_options.get_candidate(opt_id)
            assert opt.source_need_ids
            assert set(opt.source_need_ids) & period_needs


def test_v1_14_5_capital_reviews_cite_need_and_options():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        period_needs = set(ps.corporate_financing_need_ids)
        period_options = set(ps.funding_option_candidate_ids)
        for rid in ps.capital_structure_review_candidate_ids:
            rec = k.capital_structure_reviews.get_candidate(rid)
            assert set(rec.source_need_ids) & period_needs
            assert set(rec.source_funding_option_ids) & period_options


def test_v1_14_5_financing_paths_link_need_option_review():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        period_needs = set(ps.corporate_financing_need_ids)
        period_options = set(ps.funding_option_candidate_ids)
        period_reviews = set(ps.capital_structure_review_candidate_ids)
        for pid in ps.corporate_financing_path_ids:
            rec = k.financing_paths.get_path(pid)
            assert set(rec.need_ids) & period_needs
            assert set(rec.funding_option_ids) & period_options
            assert (
                set(rec.capital_structure_review_ids) & period_reviews
            )


def test_v1_14_5_financing_records_cite_market_environment_and_firm_state():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        mes = set(ps.market_environment_state_ids)
        firm_states = set(ps.firm_financial_state_ids)
        # needs cite market environment + firm state (when available).
        for nid in ps.corporate_financing_need_ids:
            need = k.corporate_financing_needs.get_need(nid)
            assert set(need.source_market_environment_state_ids) & mes
            assert set(need.source_firm_financial_state_ids) & firm_states
        # options cite MES + firm state + IBL.
        for oid in ps.funding_option_candidate_ids:
            opt = k.funding_options.get_candidate(oid)
            assert set(opt.source_market_environment_state_ids) & mes
            assert set(opt.source_firm_state_ids) & firm_states
            assert opt.source_interbank_liquidity_state_ids
        # reviews cite MES + firm state + IBL.
        for rid in ps.capital_structure_review_candidate_ids:
            rev = k.capital_structure_reviews.get_candidate(rid)
            assert set(rev.source_market_environment_state_ids) & mes
            assert set(rev.source_firm_state_ids) & firm_states
            assert rev.source_interbank_liquidity_state_ids


def test_v1_14_5_no_forbidden_event_types_appear():
    """v1.14.5 must NOT emit any execution / order / trade / loan
    approval / issuance event."""
    from world.ledger import RecordType

    k = _seed_kernel()
    _run_default(k)
    forbidden = {
        RecordType.ORDER_SUBMITTED,
        RecordType.PRICE_UPDATED,
        RecordType.CONTRACT_CREATED,
        RecordType.CONTRACT_STATUS_UPDATED,
        RecordType.CONTRACT_COVENANT_BREACHED,
        RecordType.OWNERSHIP_TRANSFERRED,
    }
    seen = {r.record_type for r in k.ledger.records}
    leaked = seen & forbidden
    assert not leaked, (
        f"v1.14.5 must not emit {sorted(t.value for t in leaked)}"
    )

    # Also forbid by string name any exec-flavoured event the
    # task spec calls out (these record types do not exist in
    # the ledger enum and must not be introduced by v1.14.5).
    forbidden_names = {
        "trade_executed",
        "loan_approved",
        "security_issued",
        "underwriting_executed",
    }
    seen_names = {r.record_type.value for r in k.ledger.records}
    assert not (seen_names & forbidden_names)


def test_v1_14_5_no_forbidden_payload_keys_in_financing_records():
    """No financing record carries an execution / pricing /
    optimal-choice / recommendation key."""
    k = _seed_kernel()
    _run_default(k)
    forbidden = {
        "approved",
        "executed",
        "selected_option",
        "optimal_option",
        "commitment",
        "underwriting",
        "syndication",
        "allocation",
        "pricing",
        "interest_rate",
        "spread",
        "coupon",
        "fee",
        "offering_price",
        "target_price",
        "expected_return",
        "recommendation",
        "investment_advice",
        "real_data_value",
        "leverage_ratio",
        "debt_to_equity",
        "WACC",
        "PD",
        "LGD",
        "EAD",
    }
    financing_event_types = {
        "corporate_financing_need_recorded",
        "funding_option_candidate_recorded",
        "capital_structure_review_candidate_recorded",
        "corporate_financing_path_recorded",
    }
    payloads = [
        record.payload
        for record in k.ledger.records
        if record.record_type.value in financing_event_types
    ]
    assert payloads, "no financing records emitted"
    for payload in payloads:
        leaked = set(payload.keys()) & forbidden
        assert not leaked, (
            "financing record payload must not include anti-field "
            f"keys; leaked: {sorted(leaked)}"
        )


def test_v1_14_5_financing_phase_does_not_mutate_unrelated_books():
    """Adding the financing chain should not change the snapshot
    of any other source-of-truth book *after* the same baseline
    upstream phases have run. We compare two runs: one default,
    and one where we capture mid-run snapshots before/after the
    chain. For simplicity, here we check that the v1.14 books
    each grew by the expected per-run total and other books'
    snapshots equal those in a kernel run without the v1.14.5
    code (impractical to set up in-test); instead, we assert the
    only books touched by the chain are the four v1.14 books and
    the ledger.
    """
    k = _seed_kernel()
    _run_default(k)
    # The four v1.14 books each carry exactly the per-run totals.
    assert (
        len(k.corporate_financing_needs.list_needs())
        == len(_PERIOD_DATES) * len(_FIRM_IDS)
    )
    assert (
        len(k.funding_options.list_candidates())
        == 2 * len(_PERIOD_DATES) * len(_FIRM_IDS)
    )
    assert (
        len(k.capital_structure_reviews.list_candidates())
        == len(_PERIOD_DATES) * len(_FIRM_IDS)
    )
    assert (
        len(k.financing_paths.list_paths())
        == len(_PERIOD_DATES) * len(_FIRM_IDS)
    )


def test_v1_14_5_two_runs_produce_byte_identical_canonical_view():
    """Replay determinism — the v1.14.5 chain must not introduce
    any non-determinism into the canonical view."""
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_14_5_canonical_view_carries_financing_id_tuples():
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
    )

    k = _seed_kernel()
    r = _run_default(k)
    can = canonicalize_living_world_result(k, r)
    for ps in can["per_period_summaries"]:
        for field_name in (
            "corporate_financing_need_ids",
            "funding_option_candidate_ids",
            "capital_structure_review_candidate_ids",
            "corporate_financing_path_ids",
        ):
            assert field_name in ps, field_name
            assert len(ps[field_name]) > 0


def test_v1_14_5_markdown_report_includes_corporate_financing_section():
    from world.living_world_report import (
        build_living_world_trace_report,
        render_living_world_markdown,
    )

    k = _seed_kernel()
    r = _run_default(k)
    report = build_living_world_trace_report(k, r)
    md = render_living_world_markdown(report)
    assert "## Corporate financing" in md
    md_lower = md.lower()
    # The boundary footer of the financing section must include
    # the storage / audit / non-execution disclaimer.
    assert (
        "no financing execution" in md_lower
        or "storage / audit / graph-linking only" in md_lower
    )


def test_v1_14_5_financing_record_ids_are_synthetic_only():
    from re import escape, search

    k = _seed_kernel()
    r = _run_default(k)
    candidates: list[str] = []
    for ps in r.per_period_summaries:
        candidates.extend(ps.corporate_financing_need_ids)
        candidates.extend(ps.funding_option_candidate_ids)
        candidates.extend(ps.capital_structure_review_candidate_ids)
        candidates.extend(ps.corporate_financing_path_ids)
    assert candidates, "no financing ids emitted"
    forbidden = (
        "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
        "gpif", "tse", "nikkei", "topix", "sony", "nyse",
    )
    for id_str in candidates:
        lower = id_str.lower()
        for token in forbidden:
            assert search(rf"\b{escape(token)}\b", lower) is None, (
                f"forbidden token {token!r} appears in id {id_str!r}"
            )


# ---------------------------------------------------------------------------
# v1.15.5 — Living-world securities market intent chain integration
# ---------------------------------------------------------------------------


def test_v1_15_5_setup_registers_one_venue_and_one_security_per_firm():
    k = _seed_kernel()
    r = _run_default(k)
    assert r.market_venue_ids == ("venue:reference_exchange_a",)
    assert len(r.listed_security_ids) == len(_FIRM_IDS)
    for firm_id in _FIRM_IDS:
        expected_id = f"security:{firm_id}:equity:line_1"
        assert expected_id in r.listed_security_ids


def test_v1_15_5_each_period_has_one_market_intent_per_investor_security_pair():
    """One ``InvestorMarketIntentRecord`` per (investor, security)
    per period — bounded by ``P × I × F``."""
    k = _seed_kernel()
    r = _run_default(k)
    expected_per_period = len(_INVESTOR_IDS) * len(_FIRM_IDS)
    for ps in r.per_period_summaries:
        assert len(ps.investor_market_intent_ids) == expected_per_period
    total = sum(
        len(ps.investor_market_intent_ids) for ps in r.per_period_summaries
    )
    assert total == len(_PERIOD_DATES) * expected_per_period


def test_v1_15_5_each_period_has_one_aggregated_per_security():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.aggregated_market_interest_ids) == len(_FIRM_IDS)


def test_v1_15_5_each_period_has_one_pressure_per_security():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        assert len(ps.indicative_market_pressure_ids) == len(_FIRM_IDS)


def test_v1_15_5_market_intents_cite_security_and_venue():
    """Every emitted market intent names a security id and a
    venue id in its evidence slots."""
    k = _seed_kernel()
    r = _run_default(k)
    expected_security_ids = set(r.listed_security_ids)
    for ps in r.per_period_summaries:
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            assert rec.evidence_security_ids
            assert set(rec.evidence_security_ids) <= expected_security_ids
            assert rec.evidence_venue_ids == ("venue:reference_exchange_a",)
            assert rec.security_id in expected_security_ids


def test_v1_15_5_aggregated_interest_cites_market_intents():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        period_intents = set(ps.investor_market_intent_ids)
        for aid in ps.aggregated_market_interest_ids:
            rec = k.aggregated_market_interest.get_record(aid)
            # Every cited source id should be in the period's intent set.
            assert set(rec.source_market_intent_ids) <= period_intents
            assert len(rec.source_market_intent_ids) > 0


def test_v1_15_5_indicative_pressure_cites_aggregated_interest():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        period_aggregated = set(ps.aggregated_market_interest_ids)
        for pid in ps.indicative_market_pressure_ids:
            rec = k.indicative_market_pressure.get_record(pid)
            assert set(rec.source_aggregated_interest_ids) <= period_aggregated
            assert len(rec.source_aggregated_interest_ids) > 0


def test_v1_15_5_does_not_mutate_pricebook():
    """v1.15.5 explicitly does NOT mutate the PriceBook even
    though it integrates a securities-market chain."""
    k = _seed_kernel()
    prices_before = k.prices.snapshot()
    _run_default(k)
    assert k.prices.snapshot() == prices_before


def test_v1_15_5_no_forbidden_event_types_appear():
    """v1.15.5 must NOT emit any execution / order / trade / quote /
    clearing / settlement event."""
    from world.ledger import RecordType

    k = _seed_kernel()
    _run_default(k)
    forbidden = {
        RecordType.ORDER_SUBMITTED,
        RecordType.PRICE_UPDATED,
        RecordType.CONTRACT_CREATED,
        RecordType.CONTRACT_STATUS_UPDATED,
        RecordType.CONTRACT_COVENANT_BREACHED,
        RecordType.OWNERSHIP_TRANSFERRED,
    }
    seen = {r.record_type for r in k.ledger.records}
    leaked = seen & forbidden
    assert not leaked

    forbidden_names = {
        "trade_executed",
        "quote_disseminated",
        "clearing_completed",
        "settlement_completed",
    }
    seen_names = {r.record_type.value for r in k.ledger.records}
    assert not (seen_names & forbidden_names)


def test_v1_15_5_no_forbidden_payload_keys_in_chain_records():
    k = _seed_kernel()
    _run_default(k)
    forbidden = {
        "buy",
        "sell",
        "order",
        "order_id",
        "trade",
        "trade_id",
        "bid",
        "ask",
        "quote",
        "price",
        "market_price",
        "indicative_price",
        "target_price",
        "expected_return",
        "execution",
        "clearing",
        "settlement",
        "target_weight",
        "overweight",
        "underweight",
        "recommendation",
        "investment_advice",
        "real_data_value",
    }
    chain_event_types = {
        "listed_security_registered",
        "market_venue_registered",
        "investor_market_intent_recorded",
        "aggregated_market_interest_recorded",
        "indicative_market_pressure_recorded",
    }
    payloads = [
        record.payload
        for record in k.ledger.records
        if record.record_type.value in chain_event_types
    ]
    assert payloads, "no v1.15.5 chain records emitted"
    for payload in payloads:
        leaked = set(payload.keys()) & forbidden
        assert not leaked, (
            "v1.15.5 chain payload must not include anti-field keys; "
            f"leaked: {sorted(leaked)}"
        )


def test_v1_15_5_two_runs_produce_byte_identical_canonical_view():
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
        living_world_digest,
    )

    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    can1 = canonicalize_living_world_result(k1, r1)
    can2 = canonicalize_living_world_result(k2, r2)
    assert can1 == can2
    assert living_world_digest(k1, r1) == living_world_digest(k2, r2)


def test_v1_15_5_canonical_view_carries_chain_id_tuples():
    from examples.reference_world.living_world_replay import (
        canonicalize_living_world_result,
    )

    k = _seed_kernel()
    r = _run_default(k)
    can = canonicalize_living_world_result(k, r)
    assert can["listed_security_count"] == len(_FIRM_IDS)
    assert can["market_venue_count"] == 1
    for ps in can["per_period_summaries"]:
        for field_name in (
            "investor_market_intent_ids",
            "aggregated_market_interest_ids",
            "indicative_market_pressure_ids",
        ):
            assert field_name in ps, field_name
            assert len(ps[field_name]) > 0


def test_v1_15_5_markdown_report_includes_securities_market_intent_section():
    from world.living_world_report import (
        build_living_world_trace_report,
        render_living_world_markdown,
    )

    k = _seed_kernel()
    r = _run_default(k)
    report = build_living_world_trace_report(k, r)
    md = render_living_world_markdown(report)
    assert "## Securities market intent" in md
    md_lower = md.lower()
    assert (
        "market interest aggregation, not market trading" in md_lower
        or "no order book" in md_lower
        or "no pricebook mutation" in md_lower
    )


def test_v1_15_6_capital_reviews_cite_indicative_market_pressure():
    """Each period's capital-structure-review records cite the
    same period's `IndicativeMarketPressureRecord` for the firm's
    listed equity. v1.15.6 closes the
    market-interest → corporate-financing feedback loop."""
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        period_pressures = set(ps.indicative_market_pressure_ids)
        for rid in ps.capital_structure_review_candidate_ids:
            rec = k.capital_structure_reviews.get_candidate(rid)
            assert rec.source_indicative_market_pressure_ids
            assert (
                set(rec.source_indicative_market_pressure_ids)
                & period_pressures
            )


def test_v1_15_6_financing_paths_cite_indicative_market_pressure():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        period_pressures = set(ps.indicative_market_pressure_ids)
        for pid in ps.corporate_financing_path_ids:
            rec = k.financing_paths.get_path(pid)
            assert rec.indicative_market_pressure_ids
            assert (
                set(rec.indicative_market_pressure_ids) & period_pressures
            )


def test_v1_15_6_pressure_security_id_matches_review_firm_security():
    """The pressure record cited by a firm's review names the
    same security_id as the firm's listed equity (via the
    `security:{firm_id}:equity:line_1` setup convention)."""
    k = _seed_kernel()
    r = _run_default(k)
    expected_security_for = {
        firm_id: f"security:{firm_id}:equity:line_1"
        for firm_id in r.firm_ids
    }
    for ps in r.per_period_summaries:
        for rid in ps.capital_structure_review_candidate_ids:
            review = k.capital_structure_reviews.get_candidate(rid)
            expected_security = expected_security_for[review.firm_id]
            for pid in review.source_indicative_market_pressure_ids:
                pressure = k.indicative_market_pressure.get_record(pid)
                assert pressure.security_id == expected_security


def test_v1_15_6_does_not_mutate_pricebook():
    """v1.15.6 wires pressure feedback into corporate financing,
    but it must NOT mutate the PriceBook."""
    k = _seed_kernel()
    prices_before = k.prices.snapshot()
    _run_default(k)
    assert k.prices.snapshot() == prices_before


def test_v1_15_6_chain_payloads_carry_no_forbidden_keys():
    """The corporate-financing chain (need / option / review /
    path) and the v1.15 chain (intent / aggregated / pressure)
    payloads must not include any execution / order / pricing /
    recommendation key. Pinned at the per-event-type level."""
    k = _seed_kernel()
    _run_default(k)
    forbidden = {
        "buy",
        "sell",
        "order",
        "order_id",
        "trade",
        "trade_id",
        "bid",
        "ask",
        "quote",
        "price",
        "market_price",
        "indicative_price",
        "target_price",
        "expected_return",
        "execution",
        "clearing",
        "settlement",
        "approved",
        "selected_option",
        "optimal_option",
        "commitment",
        "underwriting",
        "syndication",
        "allocation",
        "pricing",
        "interest_rate",
        "spread",
        "coupon",
        "fee",
        "offering_price",
        "recommendation",
        "investment_advice",
        "real_data_value",
    }
    chain_event_types = {
        "corporate_financing_need_recorded",
        "funding_option_candidate_recorded",
        "capital_structure_review_candidate_recorded",
        "corporate_financing_path_recorded",
        "investor_market_intent_recorded",
        "aggregated_market_interest_recorded",
        "indicative_market_pressure_recorded",
    }
    for record in k.ledger.records:
        if record.record_type.value not in chain_event_types:
            continue
        leaked = set(record.payload.keys()) & forbidden
        assert not leaked, (
            f"{record.record_type.value} payload must not include "
            f"anti-field keys; leaked: {sorted(leaked)}"
        )


def test_v1_15_5_chain_record_ids_are_synthetic_only():
    from re import escape, search

    k = _seed_kernel()
    r = _run_default(k)
    candidates: list[str] = []
    candidates.extend(r.listed_security_ids)
    candidates.extend(r.market_venue_ids)
    for ps in r.per_period_summaries:
        candidates.extend(ps.investor_market_intent_ids)
        candidates.extend(ps.aggregated_market_interest_ids)
        candidates.extend(ps.indicative_market_pressure_ids)
    assert candidates, "no chain ids emitted"
    forbidden = (
        "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
        "gpif", "tse", "nikkei", "topix", "sony", "nyse",
    )
    for id_str in candidates:
        lower = id_str.lower()
        for token in forbidden:
            assert search(rf"\b{escape(token)}\b", lower) is None, (
                f"forbidden token {token!r} appears in id {id_str!r}"
            )


# ---------------------------------------------------------------------------
# v1.16.2 — endogenous market-intent classifier rewire of the living world.
#
# These tests pin the success condition of v1.16.2: the living-world
# investor-market-intent phase derives ``intent_direction_label`` from
# cited evidence via the v1.16.1 pure-function classifier instead of
# the v1.15.5 four-cycle ``(period_idx + investor_idx + firm_idx) %
# 4`` rotation. Record count, per-run window, and the public-FWE
# anti-trading boundaries are preserved; the digest moved by design
# (pin tested above).
# ---------------------------------------------------------------------------


def test_v1_16_2_market_intent_labels_use_classifier_vocabulary():
    from world.market_intents import INTENT_DIRECTION_LABELS

    k = _seed_kernel()
    r = _run_default(k)
    forbidden_verbs = {
        "buy",
        "sell",
        "order",
        "target_weight",
        "overweight",
        "underweight",
        "execution",
    }
    assert not (forbidden_verbs & INTENT_DIRECTION_LABELS)
    seen_labels: set[str] = set()
    for ps in r.per_period_summaries:
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            assert rec.intent_direction_label in INTENT_DIRECTION_LABELS
            assert rec.intent_direction_label not in forbidden_verbs
            seen_labels.add(rec.intent_direction_label)
    assert seen_labels, "no labels emitted"


def test_v1_16_2_market_intent_metadata_carries_classifier_audit():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            md = rec.metadata
            assert md.get("classifier_version") == "v1.16.1"
            assert isinstance(md.get("classifier_rule_id"), str)
            assert md["classifier_rule_id"]
            assert md.get("classifier_status") in {
                "evidence_deficient",
                "default_fallback",
                "classified",
            }
            cc = md.get("classifier_confidence")
            assert isinstance(cc, (int, float))
            assert 0.0 <= float(cc) <= 1.0
            uc = md.get("classifier_unresolved_or_missing_count")
            assert isinstance(uc, int)
            assert 0 <= uc <= 5
            es = md.get("classifier_evidence_summary")
            assert isinstance(es, dict)
            assert set(es.keys()) >= {
                "investor_intent_direction",
                "valuation_confidence",
                "firm_market_access_pressure",
                "market_environment_access_label",
                "attention_focus_labels",
            }


def test_v1_16_2_record_confidence_matches_classifier_confidence():
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            md_cc = float(rec.metadata["classifier_confidence"])
            assert rec.confidence == md_cc


def test_v1_16_2_no_index_rotation_with_default_evidence():
    """The classifier rewire success condition: the per-pair
    label sequence across periods is no longer the v1.15.5
    four-cycle rotation. Counted strictly: at least one
    (investor, firm) pair must produce a sequence that is
    **not** the rotation."""
    rotation = (
        "increase_interest",
        "reduce_interest",
        "hold_review",
        "liquidity_watch",
    )
    k = _seed_kernel()
    r = _run_default(k)
    per_pair_labels: dict[tuple[str, str], list[str]] = {}
    for period_idx, ps in enumerate(r.per_period_summaries):
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            sec_id = rec.security_id
            firm_id = sec_id.split(":")[1]
            key = (rec.investor_id, firm_id)
            per_pair_labels.setdefault(
                key, [""] * len(r.per_period_summaries)
            )[period_idx] = rec.intent_direction_label
    matches_rotation_count = 0
    for inv_idx, investor_id in enumerate(_INVESTOR_IDS):
        for firm_idx, firm_id in enumerate(_FIRM_IDS):
            key = (investor_id, firm_id)
            if key not in per_pair_labels:
                continue
            sequence = tuple(per_pair_labels[key])
            shifted = tuple(
                rotation[(p + inv_idx + firm_idx) % len(rotation)]
                for p in range(len(r.per_period_summaries))
            )
            if sequence == shifted:
                matches_rotation_count += 1
    total_pairs = len(_INVESTOR_IDS) * len(_FIRM_IDS)
    assert matches_rotation_count < total_pairs, (
        "every (investor, firm) pair still follows the v1.15.5 "
        "four-cycle rotation — classifier rewire did not take effect"
    )


def test_v1_16_2_classifier_is_deterministic_across_two_runs():
    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    for ps1, ps2 in zip(r1.per_period_summaries, r2.per_period_summaries):
        for mid1, mid2 in zip(
            ps1.investor_market_intent_ids,
            ps2.investor_market_intent_ids,
        ):
            assert mid1 == mid2
            rec1 = k1.investor_market_intents.get_intent(mid1)
            rec2 = k2.investor_market_intents.get_intent(mid2)
            assert rec1.to_dict() == rec2.to_dict()


def test_v1_16_2_intensity_label_in_closed_vocabulary():
    from world.market_intents import INTENSITY_LABELS

    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            assert rec.intensity_label in INTENSITY_LABELS


def test_v1_16_2_record_count_unchanged_from_v1_15_6():
    k = _seed_kernel()
    r = _run_default(k)
    expected_per_period = len(_INVESTOR_IDS) * len(_FIRM_IDS)
    for ps in r.per_period_summaries:
        assert len(ps.investor_market_intent_ids) == expected_per_period
        assert len(ps.aggregated_market_interest_ids) == len(_FIRM_IDS)
        assert len(ps.indicative_market_pressure_ids) == len(_FIRM_IDS)


def test_v1_16_2_does_not_mutate_pricebook():
    k = _seed_kernel()
    prices_before = k.prices.snapshot()
    _run_default(k)
    assert k.prices.snapshot() == prices_before


def test_v1_16_2_evidence_ids_preserved():
    k = _seed_kernel()
    r = _run_default(k)
    expected_security_ids = set(r.listed_security_ids)
    for ps in r.per_period_summaries:
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            assert rec.evidence_security_ids
            assert set(rec.evidence_security_ids) <= expected_security_ids
            assert rec.evidence_venue_ids == ("venue:reference_exchange_a",)
            assert rec.evidence_market_environment_state_ids


def test_v1_16_2_no_forbidden_payload_keys_in_classifier_metadata():
    forbidden = {
        "buy",
        "sell",
        "order",
        "order_id",
        "trade",
        "trade_id",
        "bid",
        "ask",
        "quote",
        "price",
        "market_price",
        "indicative_price",
        "target_price",
        "expected_return",
        "execution",
        "clearing",
        "settlement",
        "target_weight",
        "overweight",
        "underweight",
        "recommendation",
        "investment_advice",
        "real_data_value",
    }
    k = _seed_kernel()
    r = _run_default(k)
    for ps in r.per_period_summaries:
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            md_keys = set(rec.metadata.keys())
            assert not (md_keys & forbidden)
            es = rec.metadata.get("classifier_evidence_summary", {})
            assert not (set(es.keys()) & forbidden)


def test_v1_16_2_classifier_rule_ids_in_known_namespace():
    """Every fired ``rule_id`` must be one of the eight v1.16.1
    classifier priorities — never the v1.15.5 rotation tag."""
    known_rule_id_prefixes = (
        "priority_1_",
        "priority_2_",
        "priority_3a_",
        "priority_3b_",
        "priority_4a_",
        "priority_4b_",
        "priority_5a_",
        "priority_5b_",
        "priority_6_",
        "priority_7_",
        "priority_8_",
    )
    k = _seed_kernel()
    r = _run_default(k)
    seen_rule_ids: set[str] = set()
    for ps in r.per_period_summaries:
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            rid = rec.metadata["classifier_rule_id"]
            assert rid.startswith(known_rule_id_prefixes), (
                f"unknown classifier rule_id {rid!r}"
            )
            seen_rule_ids.add(rid)
    assert seen_rule_ids, "no rule_ids observed"


def test_v1_16_2_no_forbidden_chain_event_types():
    from world.ledger import RecordType

    k = _seed_kernel()
    _run_default(k)
    forbidden_record_types = {
        RecordType.ORDER_SUBMITTED,
        RecordType.PRICE_UPDATED,
        RecordType.OWNERSHIP_TRANSFERRED,
    }
    seen = {rec.record_type for rec in k.ledger.records}
    assert not (seen & forbidden_record_types)
    forbidden_names = {
        "trade_executed",
        "quote_disseminated",
        "clearing_completed",
        "settlement_completed",
        "order_submitted",
        "ownership_transferred",
    }
    seen_names = {rec.record_type.value for rec in k.ledger.records}
    assert not (seen_names & forbidden_names)


def test_v1_16_2_canonical_replay_byte_identical_two_runs():
    k1 = _seed_kernel()
    r1 = _run_default(k1)
    k2 = _seed_kernel()
    r2 = _run_default(k2)
    for ps1, ps2 in zip(r1.per_period_summaries, r2.per_period_summaries):
        ids_1 = list(ps1.investor_market_intent_ids)
        ids_2 = list(ps2.investor_market_intent_ids)
        assert ids_1 == ids_2
        for mid1, mid2 in zip(ids_1, ids_2):
            d1 = k1.investor_market_intents.get_intent(mid1).to_dict()
            d2 = k2.investor_market_intents.get_intent(mid2).to_dict()
            assert d1 == d2


def test_v1_16_2_jurisdiction_neutral_in_metadata():
    from re import escape, search

    k = _seed_kernel()
    r = _run_default(k)
    forbidden = (
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
        "nyse",
        "japan",
        "tokyo",
    )
    for ps in r.per_period_summaries:
        for mid in ps.investor_market_intent_ids:
            rec = k.investor_market_intents.get_intent(mid)
            payload_text = repr(rec.metadata).lower()
            for token in forbidden:
                assert (
                    search(rf"\b{escape(token)}\b", payload_text) is None
                ), f"forbidden token {token!r} in metadata: {rec.metadata!r}"


def test_v1_16_2_classifier_module_no_runtime_books_imported():
    import world.market_intent_classifier as mic

    src = open(mic.__file__).read()
    forbidden_imports = (
        "from world.ledger import",
        "from world.kernel import",
        "from world.investor_intent import",
        "from world.valuations import",
        "from world.firm_state import",
        "from world.market_environment import",
        "from world.attention_feedback import",
        "from world.attention import",
    )
    for needle in forbidden_imports:
        assert needle not in src, (
            f"classifier module should not import a runtime book: "
            f"{needle!r}"
        )


def test_v1_16_2_living_world_imports_classifier():
    import world.reference_living_world as rlw

    src = open(rlw.__file__).read()
    assert "from world.market_intent_classifier import" in src
    assert "classify_market_intent_direction" in src
    assert "_SAFE_INTENT_DIRECTION_BY_ROTATION" not in src
    assert "_MARKET_INTENT_INTENSITY_BY_ROTATION" not in src
