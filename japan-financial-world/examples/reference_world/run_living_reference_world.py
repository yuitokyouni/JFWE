"""
v1.9.0 reference CLI — runs the Living Reference World demo on a
synthetic seed kernel and prints a compact per-period trace.

Usage:

    cd japan-financial-world
    python -m examples.reference_world.run_living_reference_world

The seed values are deterministic and synthetic (no Japan
calibration, no real data). Re-running the script produces the same
trace.

This is a thin wrapper around
``world.reference_living_world.run_living_reference_world``. Tests
exercise the helper directly; the CLI is for human eyeballs. The
``--markdown`` flag is intentionally not yet wired — that is a
v1.9.1 polishing step. v1.9.0's brief is "first multi-period sweep,
nothing else."
"""

from __future__ import annotations

from datetime import date

from world.clock import Clock
from world.exposures import ExposureRecord
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.reference_living_world import (
    LivingReferenceWorldResult,
    run_living_reference_world,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.variables import ReferenceVariableSpec, VariableObservation


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


_QUARTER_OBSERVATION_DATES: tuple[str, ...] = (
    "2026-01-15",
    "2026-04-15",
    "2026-07-15",
    "2026-10-15",
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


def _build_seed_kernel() -> WorldKernel:
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
        for q_date in _QUARTER_OBSERVATION_DATES:
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


def _print_trace(result: LivingReferenceWorldResult) -> None:
    print(
        f"[setup]   firms={len(result.firm_ids)}, "
        f"investors={len(result.investor_ids)}, "
        f"banks={len(result.bank_ids)}, "
        f"variables={len(_REFERENCE_VARIABLES)}, "
        f"exposures={len(_seed_exposures())}"
    )
    for idx, ps in enumerate(result.per_period_summaries, start=1):
        print(
            f"[period {idx}] as_of={ps.as_of_date} "
            f"reports={len(ps.corporate_signal_ids)} "
            f"menus={len(ps.investor_menu_ids) + len(ps.bank_menu_ids)} "
            f"selections={len(ps.investor_selection_ids) + len(ps.bank_selection_ids)} "
            f"reviews={len(ps.investor_review_run_ids) + len(ps.bank_review_run_ids)} "
            f"records={ps.record_count_created}"
        )
    print(
        f"[ledger]  total new records={result.created_record_count} "
        f"({result.ledger_record_count_before} -> "
        f"{result.ledger_record_count_after})"
    )
    print(
        "[summary] no price / trading / lending / valuation behavior "
        "executed; chain is endogenous and routine-driven only."
    )


def main() -> None:
    kernel = _build_seed_kernel()
    result = run_living_reference_world(
        kernel,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
    )
    _print_trace(result)


if __name__ == "__main__":
    main()
