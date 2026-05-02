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

    Lower bound 148 (per-period work × 4); upper bound 280
    catches accidental quadratic loops while leaving headroom
    for harmless infra adjustments.
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
    # Loose upper bound: 280 is well below dense product space.
    assert r.created_record_count <= 280


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
