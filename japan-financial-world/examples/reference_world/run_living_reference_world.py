"""
v1.9.0 + v1.9.1 + v1.9.2 reference CLI — runs the Living Reference
World demo on a synthetic seed kernel, prints a compact per-period
operational trace, and optionally renders the v1.9.1
``LivingWorldTraceReport`` as deterministic Markdown and / or
emits the v1.9.2 reproducibility manifest.

Usage:

    cd japan-financial-world
    python -m examples.reference_world.run_living_reference_world
    python -m examples.reference_world.run_living_reference_world --markdown
    python -m examples.reference_world.run_living_reference_world --manifest path/to/manifest.json

The seed values are deterministic and synthetic (no Japan
calibration, no real data). Re-running the script produces the same
trace, the same Markdown report, and the same SHA-256 living-world
digest — byte-identically.

This is a thin wrapper around
``world.reference_living_world.run_living_reference_world`` (the
v1.9.0 sweep), ``world.living_world_report`` (the v1.9.1 reporter),
and ``examples.reference_world.living_world_replay`` /
``living_world_manifest`` (the v1.9.2 reproducibility helpers).
Tests exercise all of them directly; the CLI is for human eyeballs.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

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

from examples.reference_world.living_world_manifest import (
    build_living_world_manifest,
    write_living_world_manifest,
)


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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_living_reference_world",
        description=(
            "Run the v1.9.0 Living Reference World demo on a synthetic "
            "seed kernel; optionally render the v1.9.1 Markdown report "
            "and / or emit the v1.9.2 reproducibility manifest."
        ),
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help=(
            "After the operational trace, render the v1.9.1 living-world "
            "trace report as deterministic Markdown."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help=(
            "Path to write the v1.9.2 reproducibility manifest as "
            "deterministic JSON. Parent directories are created if "
            "missing. The manifest carries the SHA-256 living-world "
            "digest."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    kernel = _build_seed_kernel()
    result = run_living_reference_world(
        kernel,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
    )
    _print_trace(result)

    report = None
    if args.markdown:
        report = build_living_world_trace_report(kernel, result)
        print()
        print(render_living_world_markdown(report), end="")

    if args.manifest is not None:
        manifest = build_living_world_manifest(
            kernel,
            result,
            report=report,
            input_profile="reference_world_default",
            preset_name="cli_default",
            variable_count=len(_REFERENCE_VARIABLES),
            exposure_count=len(_seed_exposures()),
        )
        target = write_living_world_manifest(manifest, Path(args.manifest))
        print(
            f"\n[manifest] wrote {target} "
            f"(living_world_digest={manifest['living_world_digest']})"
        )


if __name__ == "__main__":
    main()
