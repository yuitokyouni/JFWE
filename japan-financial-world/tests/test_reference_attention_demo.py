"""
Tests for v1.8.12 reference attention demo.

Covers ``run_investor_bank_attention_demo`` end-to-end:
heterogeneous attention is recorded as data; investor and bank,
looking at the same reference world, build distinct
``SelectedObservationSet`` records. The tests pin:

- one ``ObservationMenu`` per actor is created (and persisted
  through ``AttentionBook.add_menu``);
- one ``SelectedObservationSet`` per actor is created (and
  persisted through ``AttentionBook.add_selection``);
- both selections may share the same corporate-reporting signal
  but otherwise diverge along investor- vs bank-relevant axes;
- the demo never executes a review routine, never mutates a
  valuation / price / ownership / contract / constraint /
  external-process / institution book, and never auto-fires from
  ``tick()`` / ``run()``;
- determinism: identical inputs produce identical outputs across
  fresh kernels.

The "no economic behavior" prohibitions are enforced by direct
no-mutation checks on every other v0 / v1 source-of-truth book.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from world.clock import Clock
from world.exposures import ExposureRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.reference_attention import (
    InvestorBankAttentionDemoResult,
    register_bank_attention_profile,
    register_investor_attention_profile,
    run_investor_bank_attention_demo,
)
from world.reference_routines import (
    register_corporate_quarterly_reporting_routine,
    register_corporate_reporting_interaction,
    run_corporate_quarterly_reporting,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.variables import ReferenceVariableSpec, VariableObservation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


FIRM = "firm:reference_manufacturer_a"
INVESTOR = "investor:reference_pension_a"
BANK = "bank:reference_megabank_a"
AS_OF = "2026-04-30"


_REFERENCE_VARIABLES: tuple[tuple[str, str], ...] = (
    ("variable:cpi_yoy", "inflation"),
    ("variable:jpy_usd", "fx"),
    ("variable:jgb_10y", "rates"),
    ("variable:credit_spread_reference", "credit"),
    ("variable:land_index_tokyo", "real_estate"),
    ("variable:electricity_industrial", "energy_power"),
)


_REFERENCE_EXPOSURES: tuple[ExposureRecord, ...] = (
    ExposureRecord(
        exposure_id="exposure:investor_a:fx",
        subject_id=INVESTOR,
        subject_type="investor",
        variable_id="variable:jpy_usd",
        exposure_type="translation",
        metric="portfolio_translation_exposure",
        direction="mixed",
        magnitude=0.4,
    ),
    ExposureRecord(
        exposure_id="exposure:investor_a:rates",
        subject_id=INVESTOR,
        subject_type="investor",
        variable_id="variable:jgb_10y",
        exposure_type="discount_rate",
        metric="valuation_discount_rate",
        direction="negative",
        magnitude=0.3,
    ),
    ExposureRecord(
        exposure_id="exposure:bank_a:funding",
        subject_id=BANK,
        subject_type="bank",
        variable_id="variable:jgb_10y",
        exposure_type="funding_cost",
        metric="debt_service_burden",
        direction="positive",
        magnitude=0.5,
    ),
    ExposureRecord(
        exposure_id="exposure:bank_a:collateral",
        subject_id=BANK,
        subject_type="bank",
        variable_id="variable:land_index_tokyo",
        exposure_type="collateral",
        metric="collateral_value",
        direction="positive",
        magnitude=0.4,
    ),
    ExposureRecord(
        exposure_id="exposure:bank_a:operating_cost",
        subject_id=BANK,
        subject_type="bank",
        variable_id="variable:electricity_industrial",
        exposure_type="input_cost",
        metric="operating_cost_pressure",
        direction="negative",
        magnitude=0.2,
    ),
)


def _seed_kernel(*, with_corporate_signal: bool = True) -> WorldKernel:
    k = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
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
        k.variables.add_observation(
            VariableObservation(
                observation_id=f"obs:{vid}:2026Q1",
                variable_id=vid,
                as_of_date="2026-04-15",
                value=100.0,
                unit="index",
                vintage_id="2026Q1_initial",
                carried_by_interaction_id=(
                    "interaction:macro_data_release"
                ),
            )
        )

    for exposure in _REFERENCE_EXPOSURES:
        k.exposures.add_exposure(exposure)

    if with_corporate_signal:
        register_corporate_reporting_interaction(k)
        register_corporate_quarterly_reporting_routine(k, firm_id=FIRM)
        run_corporate_quarterly_reporting(k, firm_id=FIRM, as_of_date=AS_OF)

    return k


def _run_default_demo(k: WorldKernel) -> InvestorBankAttentionDemoResult:
    return run_investor_bank_attention_demo(
        k,
        firm_id=FIRM,
        investor_id=INVESTOR,
        bank_id=BANK,
        as_of_date=AS_OF,
    )


# ---------------------------------------------------------------------------
# Result shape + persistence
# ---------------------------------------------------------------------------


def test_result_is_immutable_and_well_formed():
    k = _seed_kernel()
    result = _run_default_demo(k)
    assert isinstance(result, InvestorBankAttentionDemoResult)
    assert result.as_of_date == AS_OF
    with pytest.raises(Exception):
        result.investor_selection_id = "tampered"  # type: ignore[misc]


def test_one_menu_per_actor_persisted():
    k = _seed_kernel()
    result = _run_default_demo(k)
    investor_menus = k.attention.list_menus_by_actor(INVESTOR)
    bank_menus = k.attention.list_menus_by_actor(BANK)
    assert len(investor_menus) == 1
    assert len(bank_menus) == 1
    assert investor_menus[0].menu_id == result.investor_menu_id
    assert bank_menus[0].menu_id == result.bank_menu_id


def test_one_selection_per_actor_persisted():
    k = _seed_kernel()
    result = _run_default_demo(k)
    investor_selections = k.attention.list_selections_by_actor(INVESTOR)
    bank_selections = k.attention.list_selections_by_actor(BANK)
    assert len(investor_selections) == 1
    assert len(bank_selections) == 1
    assert investor_selections[0].selection_id == result.investor_selection_id
    assert bank_selections[0].selection_id == result.bank_selection_id


def test_one_attention_profile_per_actor_registered():
    k = _seed_kernel()
    result = _run_default_demo(k)
    assert (
        k.attention.get_profile(result.investor_profile_id).actor_id
        == INVESTOR
    )
    assert k.attention.get_profile(result.bank_profile_id).actor_id == BANK


# ---------------------------------------------------------------------------
# Heterogeneous selection
# ---------------------------------------------------------------------------


def test_corporate_signal_is_shared_when_published():
    k = _seed_kernel(with_corporate_signal=True)
    result = _run_default_demo(k)
    expected_signal = (
        f"signal:corporate_quarterly_report:{FIRM}:{AS_OF}"
    )
    assert expected_signal in result.investor_selected_refs
    assert expected_signal in result.bank_selected_refs
    assert expected_signal in result.shared_refs


def test_investor_and_bank_selected_refs_differ():
    k = _seed_kernel()
    result = _run_default_demo(k)
    assert result.investor_selected_refs != result.bank_selected_refs
    # Each actor has at least one ref the other does not.
    assert len(result.investor_only_refs) > 0
    assert len(result.bank_only_refs) > 0


def test_investor_selects_investor_relevant_refs():
    k = _seed_kernel()
    result = _run_default_demo(k)
    # FX observation + at least one investor exposure should be selected.
    assert "obs:variable:jpy_usd:2026Q1" in result.investor_selected_refs
    assert any(
        ref.startswith("exposure:investor_a:")
        for ref in result.investor_selected_refs
    )


def test_bank_selects_bank_relevant_refs():
    k = _seed_kernel()
    result = _run_default_demo(k)
    # Real-estate / energy observations + at least one bank exposure.
    assert "obs:variable:land_index_tokyo:2026Q1" in result.bank_selected_refs
    assert (
        "obs:variable:electricity_industrial:2026Q1"
        in result.bank_selected_refs
    )
    assert any(
        ref.startswith("exposure:bank_a:")
        for ref in result.bank_selected_refs
    )


def test_investor_does_not_select_bank_only_axes():
    k = _seed_kernel()
    result = _run_default_demo(k)
    assert (
        "obs:variable:land_index_tokyo:2026Q1"
        not in result.investor_selected_refs
    )
    assert (
        "obs:variable:electricity_industrial:2026Q1"
        not in result.investor_selected_refs
    )
    assert all(
        not ref.startswith("exposure:bank_a:")
        for ref in result.investor_selected_refs
    )


def test_bank_does_not_select_investor_only_axes():
    k = _seed_kernel()
    result = _run_default_demo(k)
    assert "obs:variable:jpy_usd:2026Q1" not in result.bank_selected_refs
    assert all(
        not ref.startswith("exposure:investor_a:")
        for ref in result.bank_selected_refs
    )


def test_set_differences_match_membership():
    k = _seed_kernel()
    result = _run_default_demo(k)
    inv = set(result.investor_selected_refs)
    bnk = set(result.bank_selected_refs)
    assert set(result.shared_refs) == inv & bnk
    assert set(result.investor_only_refs) == inv - bnk
    assert set(result.bank_only_refs) == bnk - inv


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_demo_is_deterministic_across_fresh_kernels():
    a = _run_default_demo(_seed_kernel())
    b = _run_default_demo(_seed_kernel())
    assert a.investor_selected_refs == b.investor_selected_refs
    assert a.bank_selected_refs == b.bank_selected_refs
    assert a.shared_refs == b.shared_refs
    assert a.investor_only_refs == b.investor_only_refs
    assert a.bank_only_refs == b.bank_only_refs
    assert a.investor_menu_id == b.investor_menu_id
    assert a.bank_menu_id == b.bank_menu_id


# ---------------------------------------------------------------------------
# Idempotent profile registration
# ---------------------------------------------------------------------------


def test_register_investor_profile_is_idempotent():
    k = _seed_kernel(with_corporate_signal=False)
    p1 = register_investor_attention_profile(
        k, investor_id=INVESTOR, firm_id=FIRM
    )
    p2 = register_investor_attention_profile(
        k, investor_id=INVESTOR, firm_id=FIRM
    )
    assert p1.profile_id == p2.profile_id
    assert k.attention.list_profiles_by_actor(INVESTOR) == (p1,)


def test_register_bank_profile_is_idempotent():
    k = _seed_kernel(with_corporate_signal=False)
    p1 = register_bank_attention_profile(k, bank_id=BANK, firm_id=FIRM)
    p2 = register_bank_attention_profile(k, bank_id=BANK, firm_id=FIRM)
    assert p1.profile_id == p2.profile_id
    assert k.attention.list_profiles_by_actor(BANK) == (p1,)


# ---------------------------------------------------------------------------
# Ledger evidence (existing record types only — no new types)
# ---------------------------------------------------------------------------


def test_demo_uses_existing_ledger_record_types_only():
    k = _seed_kernel()
    pre_selected_count = len(
        k.ledger.filter(event_type="observation_set_selected")
    )
    pre_menu_count = len(
        k.ledger.filter(event_type="observation_menu_created")
    )
    _run_default_demo(k)
    selections = k.ledger.filter(event_type="observation_set_selected")
    menus = k.ledger.filter(event_type="observation_menu_created")
    assert len(selections) - pre_selected_count == 2
    assert len(menus) - pre_menu_count == 2


# ---------------------------------------------------------------------------
# No economic mutation
# ---------------------------------------------------------------------------


def _capture_state(k: WorldKernel) -> dict[str, Any]:
    """Snapshot every economic / structural book the demo must NOT touch."""
    return {
        "valuations": k.valuations.snapshot(),
        "prices": k.prices.snapshot(),
        "ownership": k.ownership.snapshot(),
        "contracts": k.contracts.snapshot(),
        "constraints": k.constraints.snapshot(),
        "external_processes": k.external_processes.snapshot(),
        "institutions": k.institutions.snapshot(),
        "relationships": k.relationships.snapshot(),
    }


def test_demo_does_not_mutate_economic_books():
    k = _seed_kernel()
    before = _capture_state(k)
    _run_default_demo(k)
    after = _capture_state(k)
    assert before == after


def test_demo_does_not_run_routines():
    k = _seed_kernel(with_corporate_signal=False)
    before_runs = len(k.routines.snapshot()["runs"])
    _run_default_demo(k)
    after_runs = len(k.routines.snapshot()["runs"])
    assert after_runs == before_runs


def test_demo_does_not_emit_signals_beyond_setup():
    k = _seed_kernel(with_corporate_signal=False)
    before_signals = len(k.signals.all_signals())
    _run_default_demo(k)
    after_signals = len(k.signals.all_signals())
    assert after_signals == before_signals


def test_kernel_tick_does_not_run_demo():
    k = _seed_kernel()
    before_selections = len(k.attention.list_selections_by_actor(INVESTOR))
    k.tick()
    k.run(days=3)
    after_selections = len(k.attention.list_selections_by_actor(INVESTOR))
    assert after_selections == before_selections


# ---------------------------------------------------------------------------
# Defensive errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"firm_id": ""},
        {"investor_id": ""},
        {"bank_id": ""},
    ],
)
def test_run_demo_rejects_empty_required_strings(kwargs):
    k = _seed_kernel()
    base = {
        "firm_id": FIRM,
        "investor_id": INVESTOR,
        "bank_id": BANK,
        "as_of_date": AS_OF,
    }
    base.update(kwargs)
    with pytest.raises(ValueError):
        run_investor_bank_attention_demo(k, **base)


def test_run_demo_uses_kernel_clock_when_date_omitted():
    k = _seed_kernel()
    result = run_investor_bank_attention_demo(
        k, firm_id=FIRM, investor_id=INVESTOR, bank_id=BANK
    )
    assert result.as_of_date == AS_OF
