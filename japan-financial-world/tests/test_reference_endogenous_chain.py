"""
Tests for v1.8.14 endogenous chain harness.

Pins the v1.8.14 contract end-to-end:

- One ``RoutineRunRecord`` + one ``InformationSignal`` for the
  corporate report; two ``ObservationMenu`` records and two
  ``SelectedObservationSet`` records for heterogeneous attention;
  one ``RoutineRunRecord`` + one ``InformationSignal`` per review
  (so two of each). Bidirectional run↔signal links inherited from
  v1.8.7 / v1.8.13.
- The result fields all resolve back to *actually-stored* records
  in the kernel — the harness's summary is convenience, not the
  source of truth.
- Ledger order respects the chain (corporate → attention →
  investor review → bank review). Each component continues to
  use its existing ledger paths; v1.8.14 does not introduce new
  record types.
- Heterogeneous attention propagates: investor and bank selected
  refs differ; ``shared`` / ``investor_only`` / ``bank_only`` sets
  agree with set membership.
- No economic mutation. The harness writes only what the
  components write; every other v0/v1 source-of-truth book stays
  byte-identical.
- ``kernel.tick()`` and ``kernel.run(days=N)`` never fire the
  chain.
- Determinism: two fresh kernels seeded identically produce
  identical structural summaries (ids, statuses, set
  differences, ledger counts).
- Synthetic-only identifiers; no v1 forbidden tokens leak
  through.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from world.clock import Clock
from world.exposures import ExposureRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.reference_chain import (
    EndogenousChainResult,
    run_reference_endogenous_chain,
)
from world.reference_reviews import (
    BANK_REVIEW_ROUTINE_TYPE,
    INVESTOR_REVIEW_ROUTINE_TYPE,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.variables import ReferenceVariableSpec, VariableObservation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_FIRM = "firm:reference_manufacturer_a"
_INVESTOR = "investor:reference_pension_a"
_BANK = "bank:reference_megabank_a"
_AS_OF = "2026-04-30"


_REFERENCE_VARIABLES: tuple[tuple[str, str], ...] = (
    ("variable:reference_fx_pair_a", "fx"),
    ("variable:reference_long_rate_10y", "rates"),
    ("variable:reference_land_index_a", "real_estate"),
)


_REFERENCE_EXPOSURES: tuple[ExposureRecord, ...] = (
    ExposureRecord(
        exposure_id="exposure:investor_a:fx",
        subject_id=_INVESTOR,
        subject_type="investor",
        variable_id="variable:reference_fx_pair_a",
        exposure_type="translation",
        metric="portfolio_translation_exposure",
        direction="mixed",
        magnitude=0.4,
    ),
    ExposureRecord(
        exposure_id="exposure:bank_a:funding",
        subject_id=_BANK,
        subject_type="bank",
        variable_id="variable:reference_long_rate_10y",
        exposure_type="funding_cost",
        metric="debt_service_burden",
        direction="positive",
        magnitude=0.5,
    ),
    ExposureRecord(
        exposure_id="exposure:bank_a:collateral",
        subject_id=_BANK,
        subject_type="bank",
        variable_id="variable:reference_land_index_a",
        exposure_type="collateral",
        metric="collateral_value",
        direction="positive",
        magnitude=0.4,
    ),
)


def _seed_kernel() -> WorldKernel:
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
            )
        )
    for record in _REFERENCE_EXPOSURES:
        k.exposures.add_exposure(record)
    return k


def _run_default(k: WorldKernel) -> EndogenousChainResult:
    return run_reference_endogenous_chain(
        k,
        firm_id=_FIRM,
        investor_id=_INVESTOR,
        bank_id=_BANK,
        as_of_date=_AS_OF,
    )


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------


def test_result_is_immutable_and_well_formed():
    k = _seed_kernel()
    r = _run_default(k)
    assert isinstance(r, EndogenousChainResult)
    with pytest.raises(Exception):
        r.firm_id = "tampered"  # type: ignore[misc]


def test_result_records_each_chain_phase_id():
    k = _seed_kernel()
    r = _run_default(k)
    assert r.corporate_routine_run_id.startswith("run:")
    assert r.corporate_signal_id.startswith("signal:corporate_quarterly_report")
    assert r.investor_menu_id.startswith("menu:")
    assert r.bank_menu_id.startswith("menu:")
    assert r.investor_selection_id.startswith("selection:")
    assert r.bank_selection_id.startswith("selection:")
    assert r.investor_review_run_id.startswith("run:")
    assert r.bank_review_run_id.startswith("run:")
    assert r.investor_review_signal_id.startswith(
        "signal:investor_review:"
    )
    assert r.bank_review_signal_id.startswith("signal:bank_review:")


def test_result_ids_resolve_to_stored_records():
    """The summary's claims must be reconstructable against the kernel."""
    k = _seed_kernel()
    r = _run_default(k)
    # Routine run records.
    assert k.routines.get_run_record(r.corporate_routine_run_id) is not None
    assert k.routines.get_run_record(r.investor_review_run_id) is not None
    assert k.routines.get_run_record(r.bank_review_run_id) is not None
    # Signals.
    assert k.signals.get_signal(r.corporate_signal_id) is not None
    assert k.signals.get_signal(r.investor_review_signal_id) is not None
    assert k.signals.get_signal(r.bank_review_signal_id) is not None
    # Attention.
    assert k.attention.get_profile(r.investor_profile_id) is not None
    assert k.attention.get_profile(r.bank_profile_id) is not None
    assert k.attention.get_menu(r.investor_menu_id) is not None
    assert k.attention.get_menu(r.bank_menu_id) is not None
    assert k.attention.get_selection(r.investor_selection_id) is not None
    assert k.attention.get_selection(r.bank_selection_id) is not None


# ---------------------------------------------------------------------------
# Run / signal counts
# ---------------------------------------------------------------------------


def test_one_corporate_routine_run_recorded():
    k = _seed_kernel()
    r = _run_default(k)
    runs = k.routines.list_runs_by_routine(
        f"routine:corporate_quarterly_reporting:{_FIRM}"
    )
    assert len(runs) == 1
    assert runs[0].run_id == r.corporate_routine_run_id


def test_two_observation_menus_persisted():
    k = _seed_kernel()
    _run_default(k)
    assert len(k.attention.list_menus_by_actor(_INVESTOR)) == 1
    assert len(k.attention.list_menus_by_actor(_BANK)) == 1


def test_two_selected_observation_sets_persisted():
    k = _seed_kernel()
    _run_default(k)
    assert len(k.attention.list_selections_by_actor(_INVESTOR)) == 1
    assert len(k.attention.list_selections_by_actor(_BANK)) == 1


def test_two_review_run_records_recorded():
    k = _seed_kernel()
    _run_default(k)
    inv_routine = f"routine:{INVESTOR_REVIEW_ROUTINE_TYPE}:{_INVESTOR}"
    bnk_routine = f"routine:{BANK_REVIEW_ROUTINE_TYPE}:{_BANK}"
    assert len(k.routines.list_runs_by_routine(inv_routine)) == 1
    assert len(k.routines.list_runs_by_routine(bnk_routine)) == 1


def test_three_signals_correspond_to_chain_writes():
    """Corporate report + investor review note + bank review note —
    three signals appear in the kernel after the chain."""
    k = _seed_kernel()
    before = len(k.signals.all_signals())
    _run_default(k)
    after = len(k.signals.all_signals())
    assert after - before == 3


# ---------------------------------------------------------------------------
# Ledger trace
# ---------------------------------------------------------------------------


def test_ledger_count_matches_created_record_ids():
    k = _seed_kernel()
    r = _run_default(k)
    assert (
        r.ledger_record_count_after - r.ledger_record_count_before
        == r.created_record_count
    )
    # The ids in created_record_ids match the ledger slice exactly,
    # in the same order.
    actual = tuple(
        rec.object_id
        for rec in k.ledger.records[
            r.ledger_record_count_before : r.ledger_record_count_after
        ]
    )
    assert actual == r.created_record_ids


def test_ledger_order_corporate_before_attention_before_reviews():
    k = _seed_kernel()
    r = _run_default(k)
    ids = list(r.created_record_ids)
    # The corporate routine run record must appear before any
    # attention profile / menu / selection.
    corp_run_idx = ids.index(r.corporate_routine_run_id)
    investor_menu_idx = ids.index(r.investor_menu_id)
    investor_review_run_idx = ids.index(r.investor_review_run_id)
    bank_review_run_idx = ids.index(r.bank_review_run_id)
    assert corp_run_idx < investor_menu_idx
    assert investor_menu_idx < investor_review_run_idx
    assert investor_review_run_idx < bank_review_run_idx


def test_ledger_uses_existing_record_types_only():
    k = _seed_kernel()
    r = _run_default(k)
    expected_event_types = {
        "interaction_added",
        "routine_added",
        "routine_run_recorded",
        "signal_added",
        "attention_profile_added",
        "observation_menu_created",
        "observation_set_selected",
    }
    new_records = k.ledger.records[
        r.ledger_record_count_before : r.ledger_record_count_after
    ]
    for record in new_records:
        assert record.event_type in expected_event_types


def test_review_phase_runs_after_attention_phase():
    """Investor review's input_refs must include refs from the
    investor selection — proving the attention phase ran first."""
    k = _seed_kernel()
    r = _run_default(k)
    inv_run = k.routines.get_run_record(r.investor_review_run_id)
    inv_selection = k.attention.get_selection(r.investor_selection_id)
    for ref in inv_selection.selected_refs:
        assert ref in inv_run.input_refs


# ---------------------------------------------------------------------------
# Heterogeneous attention propagation
# ---------------------------------------------------------------------------


def test_investor_and_bank_selected_refs_differ():
    k = _seed_kernel()
    r = _run_default(k)
    assert r.investor_selected_refs != r.bank_selected_refs


def test_set_differences_match_membership():
    k = _seed_kernel()
    r = _run_default(k)
    inv = set(r.investor_selected_refs)
    bnk = set(r.bank_selected_refs)
    assert set(r.shared_selected_refs) == inv & bnk
    assert set(r.investor_only_selected_refs) == inv - bnk
    assert set(r.bank_only_selected_refs) == bnk - inv


def test_corporate_signal_appears_in_shared_refs_when_both_pick_it():
    """The corporate report appears in both selections by design,
    so it must show up in shared_selected_refs."""
    k = _seed_kernel()
    r = _run_default(k)
    assert r.corporate_signal_id in r.shared_selected_refs


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def _structural_summary(r: EndogenousChainResult) -> dict[str, Any]:
    return {
        "corporate_routine_run_id": r.corporate_routine_run_id,
        "corporate_signal_id": r.corporate_signal_id,
        "investor_profile_id": r.investor_profile_id,
        "bank_profile_id": r.bank_profile_id,
        "investor_menu_id": r.investor_menu_id,
        "bank_menu_id": r.bank_menu_id,
        "investor_selection_id": r.investor_selection_id,
        "bank_selection_id": r.bank_selection_id,
        "investor_review_run_id": r.investor_review_run_id,
        "bank_review_run_id": r.bank_review_run_id,
        "investor_review_signal_id": r.investor_review_signal_id,
        "bank_review_signal_id": r.bank_review_signal_id,
        "investor_selected_refs": r.investor_selected_refs,
        "bank_selected_refs": r.bank_selected_refs,
        "shared_selected_refs": r.shared_selected_refs,
        "investor_only_selected_refs": r.investor_only_selected_refs,
        "bank_only_selected_refs": r.bank_only_selected_refs,
        "corporate_status": r.corporate_status,
        "investor_review_status": r.investor_review_status,
        "bank_review_status": r.bank_review_status,
        "created_record_count": r.created_record_count,
        "created_record_ids": r.created_record_ids,
    }


def test_chain_is_deterministic_across_fresh_kernels():
    a = _structural_summary(_run_default(_seed_kernel()))
    b = _structural_summary(_run_default(_seed_kernel()))
    assert a == b


# ---------------------------------------------------------------------------
# Status semantics
# ---------------------------------------------------------------------------


def test_default_chain_completes_all_three_phases():
    k = _seed_kernel()
    r = _run_default(k)
    assert r.corporate_status == "completed"
    assert r.investor_review_status == "completed"
    assert r.bank_review_status == "completed"


def test_chain_with_no_exposures_yields_degraded_reviews():
    """When the actors have no exposures, their selections carry
    only the corporate signal; selections still resolve and the
    reviews still run, but the review status remains 'completed'
    because the corporate signal *is* a ref. The chain still
    completes — this is the v1.8.1 anti-scenario rule in action."""
    k = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 4, 30)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )
    # No variables, no exposures — but the corporate report still
    # publishes a signal that lands in everyone's menu.
    r = _run_default(k)
    assert r.corporate_status == "completed"
    # Both reviews should still record the corporate signal.
    assert r.investor_review_status == "completed"
    assert r.bank_review_status == "completed"
    assert r.corporate_signal_id in r.investor_selected_refs
    assert r.corporate_signal_id in r.bank_selected_refs


# ---------------------------------------------------------------------------
# Date semantics
# ---------------------------------------------------------------------------


def test_as_of_date_defaults_to_kernel_clock():
    k = _seed_kernel()
    r = run_reference_endogenous_chain(
        k, firm_id=_FIRM, investor_id=_INVESTOR, bank_id=_BANK
    )
    assert r.as_of_date == _AS_OF


def test_explicit_as_of_date_overrides_clock():
    k = _seed_kernel()
    r = run_reference_endogenous_chain(
        k,
        firm_id=_FIRM,
        investor_id=_INVESTOR,
        bank_id=_BANK,
        as_of_date="2026-09-30",
    )
    assert r.as_of_date == "2026-09-30"


# ---------------------------------------------------------------------------
# Defensive errors
# ---------------------------------------------------------------------------


def test_chain_rejects_kernel_none():
    with pytest.raises(ValueError):
        run_reference_endogenous_chain(
            None,
            firm_id=_FIRM,
            investor_id=_INVESTOR,
            bank_id=_BANK,
            as_of_date=_AS_OF,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"firm_id": ""},
        {"investor_id": ""},
        {"bank_id": ""},
    ],
)
def test_chain_rejects_empty_required_strings(kwargs):
    k = _seed_kernel()
    base = {
        "firm_id": _FIRM,
        "investor_id": _INVESTOR,
        "bank_id": _BANK,
        "as_of_date": _AS_OF,
    }
    base.update(kwargs)
    with pytest.raises(ValueError):
        run_reference_endogenous_chain(k, **base)


# ---------------------------------------------------------------------------
# No economic mutation
# ---------------------------------------------------------------------------


def _capture_state(k: WorldKernel) -> dict[str, Any]:
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
    before = _capture_state(k)
    _run_default(k)
    after = _capture_state(k)
    assert before == after


def test_chain_does_not_mutate_exposures_or_variables_after_setup():
    """Exposures and variables are seeded before the chain. The
    chain itself must not add, remove, or modify any record in
    ``ExposureBook`` / ``WorldVariableBook``."""
    k = _seed_kernel()
    before_exposures = k.exposures.snapshot()
    before_variables = k.variables.snapshot()
    _run_default(k)
    assert k.exposures.snapshot() == before_exposures
    assert k.variables.snapshot() == before_variables


# ---------------------------------------------------------------------------
# No auto-firing
# ---------------------------------------------------------------------------


def test_kernel_tick_does_not_run_chain():
    k = _seed_kernel()
    before_runs = len(k.routines.snapshot()["runs"])
    before_signals = len(k.signals.all_signals())
    k.tick()
    assert len(k.routines.snapshot()["runs"]) == before_runs
    assert len(k.signals.all_signals()) == before_signals


def test_kernel_run_does_not_run_chain():
    k = _seed_kernel()
    before_runs = len(k.routines.snapshot()["runs"])
    before_signals = len(k.signals.all_signals())
    k.run(days=5)
    assert len(k.routines.snapshot()["runs"]) == before_runs
    assert len(k.signals.all_signals()) == before_signals


# ---------------------------------------------------------------------------
# Synthetic-only identifiers
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "nyse",
)


def test_chain_ids_are_synthetic_only():
    k = _seed_kernel()
    r = _run_default(k)
    candidates = list(r.created_record_ids) + [
        r.corporate_routine_run_id,
        r.corporate_signal_id,
        r.investor_menu_id,
        r.bank_menu_id,
        r.investor_selection_id,
        r.bank_selection_id,
        r.investor_review_run_id,
        r.bank_review_run_id,
        r.investor_review_signal_id,
        r.bank_review_signal_id,
    ]
    for id_str in candidates:
        lower = id_str.lower()
        for token in _FORBIDDEN_TOKENS:
            # Word-boundary check (handles substring false positives
            # like 'tse' ⊂ 'itself' — though our ids never include
            # English prose, defense in depth).
            for sep in (" ", ":", "/", "-", "_", "(", ")", ",", ".", "'", '"'):
                if f"{sep}{token}{sep}" in f" {lower} ":
                    pytest.fail(
                        f"forbidden token {token!r} appears in id {id_str!r}"
                    )
