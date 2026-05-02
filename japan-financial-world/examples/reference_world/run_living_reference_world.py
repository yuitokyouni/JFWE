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
    # v1.9.6 — firm exposures so the v1.9.4 firm-pressure-assessment
    # mechanism produces non-zero output. Each firm has a distinct
    # exposure profile so per-period pressure assessments differ across
    # firms (input_cost / energy_power / debt_service / fx_translation
    # / logistics dimensions).
    firm_exposure_specs: tuple[tuple[str, str, str, float], ...] = (
        # firm a — diversified manufacturer-style: rates + fx + energy
        ("firm:reference_manufacturer_a", "variable:reference_long_rate_10y", "funding_cost", 0.3),
        ("firm:reference_manufacturer_a", "variable:reference_fx_pair_a", "translation", 0.2),
        ("firm:reference_manufacturer_a", "variable:reference_electricity_price_a", "input_cost", 0.4),
        # firm b — retailer-style: fx + logistics-leaning rates
        ("firm:reference_retailer_b", "variable:reference_fx_pair_a", "translation", 0.3),
        ("firm:reference_retailer_b", "variable:reference_long_rate_10y", "funding_cost", 0.2),
        # firm c — utility-style: energy heavy + rates
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
        f"exposures={len(_seed_exposures())}, "
        f"industries={len(result.industry_ids)}, "
        f"themes={len(result.stewardship_theme_ids)}, "
        f"markets={len(result.market_ids)}"
    )
    for idx, ps in enumerate(result.per_period_summaries, start=1):
        print(
            f"[period {idx}] as_of={ps.as_of_date} "
            f"reports={len(ps.corporate_signal_ids)} "
            f"pressures={len(ps.firm_pressure_signal_ids)} "
            f"industry={len(ps.industry_condition_ids)} "
            f"market_conditions={len(ps.market_condition_ids)} "
            f"market_readouts={len(ps.capital_market_readout_ids)} "
            f"market_environments={len(ps.market_environment_state_ids)} "
            f"firm_states={len(ps.firm_financial_state_ids)} "
            f"themes={len(ps.stewardship_theme_ids)} "
            f"dialogues={len(ps.dialogue_ids)} "
            f"escalations={len(ps.investor_escalation_candidate_ids)} "
            f"investor_intents={len(ps.investor_intent_ids)} "
            f"responses={len(ps.corporate_strategic_response_candidate_ids)} "
            f"valuations={len(ps.valuation_ids)} "
            f"credit_reviews={len(ps.bank_credit_review_signal_ids)} "
            f"reviews={len(ps.investor_review_run_ids) + len(ps.bank_review_run_ids)} "
            f"records={ps.record_count_created}"
        )
    print(
        f"[ledger]  total new records={result.created_record_count} "
        f"({result.ledger_record_count_before} -> "
        f"{result.ledger_record_count_after})"
    )
    print(
        "[summary] integrated chain: corporate reporting -> firm "
        "pressure assessment -> industry demand condition -> "
        "capital-market conditions -> capital-market readout -> "
        "firm financial latent state update -> heterogeneous "
        "attention -> valuation refresh lite -> bank credit "
        "review lite -> portfolio-company dialogue metadata -> "
        "investor escalation candidates -> investor intent "
        "signals -> corporate strategic response candidates -> "
        "review. No price formation, no trading, no lending "
        "decisions, no covenant enforcement, no contract or "
        "constraint mutation, no firm financial statement "
        "updates, no accounting values, no canonical-truth "
        "valuation, no investment advice, no voting execution, "
        "no proxy filing, no public-campaign execution, no "
        "corporate-action execution, no disclosure filing, no "
        "demand / revenue forecasting, no Japan calibration, no "
        "yield-curve calibration, no order matching, no "
        "clearing, no quote dissemination, no security "
        "recommendation, no order submission, no rebalancing, "
        "no portfolio allocation, no buy / sell / overweight / "
        "underweight execution."
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
    parser.add_argument(
        "--market-regime",
        type=str,
        default=None,
        choices=("constructive", "mixed", "constrained", "tightening"),
        help=(
            "v1.11.2: select a synthetic market-regime preset for "
            "the per-period capital-market conditions. Each preset "
            "deterministically alters only the synthetic "
            "(direction, strength, confidence, time_horizon) "
            "tuples; no real data, no calibrated yields, no "
            "spreads, no forecasts. Default (omit the flag): "
            "preserve the v1.11.0 / v1.11.1 default specs."
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
        market_regime=args.market_regime,
    )
    if args.market_regime is not None:
        print(
            f"[regime]  market_regime={args.market_regime} "
            "(v1.11.2 synthetic preset; no real data, no forecasts)"
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
