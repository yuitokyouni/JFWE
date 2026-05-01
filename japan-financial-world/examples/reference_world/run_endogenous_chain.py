"""
v1.8.14 reference CLI — runs the endogenous chain on a synthetic
seed kernel and prints a compact trace.

Usage:

    cd japan-financial-world
    python -m examples.reference_world.run_endogenous_chain

The seed values are deterministic and synthetic (no Japan
calibration, no real data). Re-running the script produces the
same trace.

This is a thin orchestration wrapper around
``world.reference_chain.run_reference_endogenous_chain``. Tests
exercise the harness directly; the CLI is for human eyeballs.
"""

from __future__ import annotations

from datetime import date

from world.clock import Clock
from world.exposures import ExposureRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.reference_chain import (
    EndogenousChainResult,
    run_reference_endogenous_chain,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.variables import ReferenceVariableSpec, VariableObservation


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


def _build_seed_kernel() -> WorldKernel:
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


def _print_trace(result: EndogenousChainResult) -> None:
    print("[setup]    kernel seeded with synthetic variables / exposures")
    print(f"[setup]    as_of_date = {result.as_of_date}")
    print(
        f"[corporate] reporting run {result.corporate_routine_run_id} "
        f"-> signal {result.corporate_signal_id} "
        f"({result.corporate_status})"
    )
    print(
        f"[attention] investor menu {result.investor_menu_id}"
    )
    print(
        f"[attention] bank menu     {result.bank_menu_id}"
    )
    print(
        f"[selection] investor selected {len(result.investor_selected_refs)} refs "
        f"({result.investor_selection_id})"
    )
    print(
        f"[selection] bank selected     {len(result.bank_selected_refs)} refs "
        f"({result.bank_selection_id})"
    )
    print(
        f"[selection] shared = {len(result.shared_selected_refs)}, "
        f"investor_only = {len(result.investor_only_selected_refs)}, "
        f"bank_only = {len(result.bank_only_selected_refs)}"
    )
    print(
        f"[review]    investor review run {result.investor_review_run_id} "
        f"-> signal {result.investor_review_signal_id} "
        f"({result.investor_review_status})"
    )
    print(
        f"[review]    bank review run     {result.bank_review_run_id} "
        f"-> signal {result.bank_review_signal_id} "
        f"({result.bank_review_status})"
    )
    print(
        f"[ledger]    {result.created_record_count} new records "
        f"({result.ledger_record_count_before} -> "
        f"{result.ledger_record_count_after})"
    )


def main() -> None:
    kernel = _build_seed_kernel()
    result = run_reference_endogenous_chain(
        kernel,
        firm_id=_FIRM,
        investor_id=_INVESTOR,
        bank_id=_BANK,
        as_of_date=_AS_OF,
    )
    _print_trace(result)


if __name__ == "__main__":
    main()
