"""
Tests for v1.9.8 Performance Boundary / Sparse Traversal Discipline.

These tests pin the *traversal shape* of the v1.9 living
reference world. The demo is deliberately tiny (3 firms,
2 investors, 2 banks, 4 periods) and uses bounded all-pairs
loops only for valuation refresh and bank credit review.
Anything that quietly turns those bounded loops into
production-scale dense sweeps — or introduces a brand-new
quadratic loop, or starts emitting price / trade / contract
mutation records — must fail one of these tests loudly.

These tests **do not**:

- benchmark wall-clock time,
- profile any function,
- exercise any new economic behaviour, or
- run against any non-default fixture size.

They are a written contract against the small synthetic
fixture, and they are deliberately tight.

See ``docs/performance_boundary.md`` for the full discipline
this file pins.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from world.clock import Clock
from world.exposures import ExposureRecord
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.reference_living_world import run_living_reference_world
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.variables import ReferenceVariableSpec, VariableObservation


# Demo fixture. Mirrors ``tests/test_living_reference_world.py``
# deliberately so that any drift between the integration tests
# and this performance-boundary file shows up here too.

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
_PERIOD_DATES: tuple[str, ...] = (
    "2026-03-31",
    "2026-06-30",
    "2026-09-30",
    "2026-12-31",
)
_OBS_DATES: tuple[str, ...] = (
    "2026-01-15",
    "2026-04-15",
    "2026-07-15",
    "2026-10-15",
)
_REFERENCE_VARIABLES: tuple[tuple[str, str], ...] = (
    ("variable:reference_long_rate_10y", "rates"),
    ("variable:reference_fx_pair_a", "fx"),
    ("variable:reference_electricity_price_a", "energy"),
    ("variable:reference_land_index_a", "real_estate"),
)


def _seed_exposures() -> tuple[ExposureRecord, ...]:
    out: list[ExposureRecord] = []
    firm_specs: tuple[tuple[str, str, str, float], ...] = (
        ("firm:reference_manufacturer_a", "variable:reference_long_rate_10y",     "funding_cost", 0.3),
        ("firm:reference_manufacturer_a", "variable:reference_fx_pair_a",         "translation",  0.2),
        ("firm:reference_manufacturer_a", "variable:reference_electricity_price_a", "input_cost", 0.4),
        ("firm:reference_retailer_b",     "variable:reference_fx_pair_a",         "translation",  0.3),
        ("firm:reference_retailer_b",     "variable:reference_long_rate_10y",     "funding_cost", 0.2),
        ("firm:reference_utility_c",      "variable:reference_electricity_price_a", "input_cost", 0.5),
        ("firm:reference_utility_c",      "variable:reference_long_rate_10y",     "funding_cost", 0.4),
    )
    for firm_id, var_id, exp_type, mag in firm_specs:
        metric = (
            "operating_cost_pressure" if exp_type == "input_cost"
            else "debt_service_burden" if exp_type == "funding_cost"
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


def count_expected_living_world_records(
    *,
    firms: int,
    investors: int,
    banks: int,
    periods: int,
    industries: int = 3,
    markets: int = 5,
    capital_market_readouts_per_period: int = 1,
    market_environment_states_per_period: int = 1,
) -> int:
    """Returns the **total** record count across the entire
    multi-period run — i.e. the per-period formula multiplied
    by ``periods``. This is **not** a per-period count.

    Excludes the one-off setup records (interactions, routines,
    profiles, stewardship themes) that the helper registers on
    first invocation; those are bounded by the upper budget in the
    test that consumes this helper.

    Per period (multiplied by ``periods`` to obtain the run total):
        2 * firms                              corporate run + corporate signal
        firms                                  firm pressure signal (v1.9.4)
        industries                             industry demand condition (v1.10.4)
        markets                                capital-market condition (v1.11.0)
        capital_market_readouts_per_period     capital-market readout (v1.11.1)
        market_environment_states_per_period   market environment state (v1.12.2)
        firms                                  firm financial latent state (v1.12.0)
        2 * (investors + banks)                menu + selection
        investors * firms                      valuation (v1.9.5)
        banks                                  interbank liquidity state (v1.13.5)
        banks * firms                          bank credit review note (v1.9.7)
        investors * firms                      portfolio-company dialogue (v1.10.2)
        investors * firms                      investor escalation candidate (v1.10.3)
        investors * firms                      investor intent signal (v1.12.1)
        firms                                  corporate strategic response candidate (v1.10.3)
        2 * (investors + banks)                review_run + review_signal
        2 * investors                          attention state + feedback per investor (v1.12.8)
        2 * banks                              attention state + feedback per bank (v1.12.8)
        firms                                  corporate financing need (v1.14.5)
        2 * firms                              funding option candidate (v1.14.5)
        firms                                  capital structure review candidate (v1.14.5)
        firms                                  corporate financing path (v1.14.5)
        investors * firms                      investor market intent (v1.15.5)
        firms                                  aggregated market interest (v1.15.5)
        firms                                  indicative market pressure (v1.15.5)

    For the default fixture (3 firms, 2 investors, 2 banks,
    3 industries, 5 markets, 1 readout/period, 1 environment
    state/period, 4 periods) this is 108 records per period × 4
    periods = 432 (v1.15.5 adds investors × firms + 2 × firms = 12
    records per period on top of the v1.14.5 baseline of 96).

    v1.12.8 also creates a *memory* SelectedObservationSet per
    actor from period 1 onwards (when the actor has a
    prior-period attention state with focus_labels that point at
    concrete source ids). Memory selections are
    period-dependent (zero in period 0; up to ``investors +
    banks`` per subsequent period) — they are NOT in this
    formula because they are a residual the test's upper-bound
    allowance covers.
    """
    actors = investors + banks
    per_period = (
        2 * firms                              # corp run + corp signal
        + firms                                # pressure signal
        + industries                           # industry demand condition (v1.10.4)
        + markets                              # capital-market condition (v1.11.0)
        + capital_market_readouts_per_period   # capital-market readout (v1.11.1)
        + market_environment_states_per_period # market environment state (v1.12.2)
        + firms                                # firm financial latent state (v1.12.0)
        + 2 * actors                           # menu + selection
        + investors * firms                    # valuation
        + banks                                # interbank liquidity state (v1.13.5)
        + banks * firms                        # credit review
        + investors * firms                    # dialogue (v1.10.2)
        + investors * firms                    # escalation candidate (v1.10.3, investor)
        + investors * firms                    # investor intent signal (v1.12.1)
        + firms                                # response candidate (v1.10.3, corporate)
        + 2 * actors                           # review_run + review_signal
        + 2 * investors                        # attention state + feedback / investor (v1.12.8)
        + 2 * banks                            # attention state + feedback / bank (v1.12.8)
        + firms                                # corporate financing need (v1.14.5)
        + 2 * firms                            # funding option candidate (v1.14.5)
        + firms                                # capital structure review candidate (v1.14.5)
        + firms                                # corporate financing path (v1.14.5)
        + investors * firms                    # investor market intent (v1.15.5)
        + firms                                # aggregated market interest (v1.15.5)
        + firms                                # indicative market pressure (v1.15.5)
    )
    return per_period * periods


# ---------------------------------------------------------------------------
# Doc presence
# ---------------------------------------------------------------------------


def test_performance_boundary_doc_exists():
    """The performance-boundary discipline must be documented."""
    doc = (
        Path(__file__).resolve().parent.parent
        / "docs"
        / "performance_boundary.md"
    )
    assert doc.is_file(), f"missing {doc}"
    text = doc.read_text(encoding="utf-8")
    # Spot-check the doc covers each of the disciplines this
    # file pins. If a future edit removes one of these sections,
    # the test fails — keeping the doc and the tests in sync.
    for needle in (
        "Performance Boundary",
        "Current loop shapes",
        "Sparse gating principles",
        "Future acceleration",
        "Semantic caveat",
        "review is not origination",
        "demo-bounded",
    ):
        assert needle in text, f"perf doc missing section: {needle!r}"


# ---------------------------------------------------------------------------
# Per-run record budget (total across all periods, not per-period)
# ---------------------------------------------------------------------------


def test_default_living_world_total_run_record_count_matches_formula():
    """Total record count for a full default *run* (4 periods)
    equals the per-period formula × 4 plus a small
    infrastructure allowance for one-off setup (interactions,
    routines, profiles, attention configs, stewardship themes).

    Note on units: the budget pinned here is a **per-run total
    across all four periods**, NOT a per-period count. At v1.12.2
    the per-period count is 71 records; v1.12.8 adds 8 attention-
    feedback records; v1.13.5 adds ``banks`` interbank-liquidity
    records; v1.14.5 adds the corporate financing chain
    (5 × firms per period); v1.15.5 adds the securities market
    intent chain (``investors × firms`` market intents +
    ``2 × firms`` aggregated-interest + indicative-pressure
    records per period — 12 records per period in the default
    fixture). The per-run minimum from the v1.15.5 formula is
    432; the tight upper window accommodates the residual +
    setup overhead (now including 1 venue + ``firms`` listed
    securities = 4 setup records) and lands at [432, 480].
    """
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    expected_run_total = count_expected_living_world_records(
        firms=len(_FIRM_IDS),
        investors=len(_INVESTOR_IDS),
        banks=len(_BANK_IDS),
        periods=len(_PERIOD_DATES),
    )
    # Lower bound: at minimum the formula × periods must be
    # met. Anything less means a phase silently dropped output.
    assert r.created_record_count >= expected_run_total, (
        f"living world produced {r.created_record_count} records "
        f"across the full run, below per-run formula minimum "
        f"of {expected_run_total} (= per-period formula × "
        f"{len(_PERIOD_DATES)} periods)"
    )
    # Tight per-run upper bound: no more than 48 records on top
    # of the per-period formula minimum. v1.9.7 sits at ~14
    # setup records; v1.10.5 adds 4 stewardship-theme records;
    # v1.12.8 adds up to (investors+banks) × (periods-1) memory
    # selections (period 0 has none); 48 leaves headroom for
    # harmless infra adjustments but is far below any quadratic
    # explosion (which would push the count to triple-digit
    # growth per period).
    upper_bound = expected_run_total + 48
    assert r.created_record_count <= upper_bound, (
        f"living world produced {r.created_record_count} records "
        f"across the full run, above tight per-run upper bound "
        f"of {upper_bound}. A new mechanism or a hidden "
        "quadratic loop has crept in. Update "
        "count_expected_living_world_records and "
        "docs/performance_boundary.md if intentional."
    )


def test_per_period_record_count_is_constant_across_periods():
    """Each period's contribution to the ledger should be
    identical in shape: same number of corporate signals,
    same number of pressure signals, valuations, credit
    reviews, etc. If a phase becomes period-dependent that's
    an architectural change worth noticing."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    shapes: list[tuple[int, ...]] = []
    for ps in r.per_period_summaries:
        shapes.append(
            (
                len(ps.corporate_signal_ids),
                len(ps.corporate_run_ids),
                len(ps.firm_pressure_signal_ids),
                len(ps.firm_pressure_run_ids),
                len(ps.investor_menu_ids),
                len(ps.bank_menu_ids),
                len(ps.investor_selection_ids),
                len(ps.bank_selection_ids),
                len(ps.valuation_ids),
                len(ps.valuation_mechanism_run_ids),
                len(ps.bank_credit_review_signal_ids),
                len(ps.bank_credit_review_mechanism_run_ids),
                len(ps.investor_review_run_ids),
                len(ps.bank_review_run_ids),
                len(ps.investor_review_signal_ids),
                len(ps.bank_review_signal_ids),
            )
        )
    assert len(set(shapes)) == 1, (
        f"per-period shape not constant across periods: {shapes}"
    )


# ---------------------------------------------------------------------------
# Exact mechanism counts — quadratic-explosion canaries
# ---------------------------------------------------------------------------


def test_pressure_signal_count_is_exactly_periods_times_firms():
    """v1.9.4 mechanism: one pressure signal per firm per
    period. ``len(P) * len(F)`` exactly, not more."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    total = sum(len(ps.firm_pressure_signal_ids) for ps in r.per_period_summaries)
    assert total == len(_PERIOD_DATES) * len(_FIRM_IDS)


def test_valuation_count_is_exactly_periods_times_investors_times_firms():
    """v1.9.5 mechanism: one valuation per (investor, firm)
    per period. ``len(P) * len(I) * len(F)`` exactly."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    total = sum(len(ps.valuation_ids) for ps in r.per_period_summaries)
    expected = len(_PERIOD_DATES) * len(_INVESTOR_IDS) * len(_FIRM_IDS)
    assert total == expected


def test_credit_review_count_is_exactly_periods_times_banks_times_firms():
    """v1.9.7 mechanism: one bank credit review note per
    (bank, firm) per period. ``len(P) * len(B) * len(F)``
    exactly. Anything more would mean the mechanism started
    enumerating something it should not."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    total = sum(
        len(ps.bank_credit_review_signal_ids)
        for ps in r.per_period_summaries
    )
    expected = len(_PERIOD_DATES) * len(_BANK_IDS) * len(_FIRM_IDS)
    assert total == expected


# ---------------------------------------------------------------------------
# Forbidden ledger record types — price / trade / lending mutation
# ---------------------------------------------------------------------------


# Record types that v1.9 must NOT emit. These are the
# trade-execution / price-formation / loan-origination /
# covenant-enforcement mutation events; v1.9 is review-only,
# so any of these appearing means the demo crossed a
# behaviour boundary.
_FORBIDDEN_RECORD_TYPES: frozenset[RecordType] = frozenset({
    RecordType.ORDER_SUBMITTED,
    RecordType.PRICE_UPDATED,
    RecordType.CONTRACT_CREATED,
    RecordType.CONTRACT_STATUS_UPDATED,
    RecordType.CONTRACT_COVENANT_BREACHED,
    RecordType.OWNERSHIP_TRANSFERRED,
})


def test_no_forbidden_mutation_records_appear():
    """v1.9 is review-only: no orders, no price updates, no
    contracts, no covenant breaches, no ownership transfers.
    If any of these record types appears, the demo has
    silently crossed into trade-execution / loan-origination
    / covenant-enforcement territory — which is explicitly
    out of scope for v1.9.x."""
    k = _seed_kernel()
    run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    seen_types = {record.record_type for record in k.ledger.records}
    leaked = seen_types & _FORBIDDEN_RECORD_TYPES
    assert not leaked, (
        f"v1.9 must not emit {sorted(t.value for t in leaked)} — "
        "those are trade / price / lending mutation events. "
        "If a new mechanism legitimately produces them, that's "
        "a milestone change, not a v1.9.x quiet drift."
    )


def test_no_warning_or_error_records_during_default_sweep():
    """The default fixture is healthy by construction; no
    WARNING / ERROR records should appear. If they do, a
    mechanism is silently degrading on input it should
    accept — worth noticing before claiming a green sweep."""
    k = _seed_kernel()
    run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        period_dates=_PERIOD_DATES,
    )
    bad = [
        r for r in k.ledger.records
        if r.record_type in (RecordType.WARNING, RecordType.ERROR)
    ]
    assert not bad, (
        f"unexpected warning/error records: "
        f"{[(r.record_type.value, r.payload) for r in bad]}"
    )


# ---------------------------------------------------------------------------
# Helper-function contract
# ---------------------------------------------------------------------------


def test_count_expected_living_world_records_matches_default_fixture():
    """The helper formula must reproduce the documented
    per-period × periods total for the default fixture."""
    total = count_expected_living_world_records(
        firms=len(_FIRM_IDS),
        investors=len(_INVESTOR_IDS),
        banks=len(_BANK_IDS),
        periods=len(_PERIOD_DATES),
    )
    # Per docs/performance_boundary.md (v1.15.5):
    # 4 × 108 = 432 records per run from the per-period formula
    # (v1.14.5 baseline 96 + v1.15.5's 12 securities-market-intent
    # records per period: investors × firms = 6 market intents +
    # firms = 3 aggregated-interest + firms = 3 indicative-pressure).
    # Memory selections are period-dependent and not in the
    # formula.
    assert total == 432


def test_count_expected_living_world_records_scales_linearly_in_periods():
    """If the formula were quadratic in any actor count, this
    linearity check would not hold."""
    one_period = count_expected_living_world_records(
        firms=3, investors=2, banks=2, periods=1,
    )
    four_periods = count_expected_living_world_records(
        firms=3, investors=2, banks=2, periods=4,
    )
    assert four_periods == 4 * one_period


# ---------------------------------------------------------------------------
# v1.19.3 monthly_reference profile pins
# ---------------------------------------------------------------------------


def test_v1_19_3_monthly_reference_total_arrival_count_in_36_to_60():
    """The v1.19.3 ``monthly_reference`` default fixture pins
    a 12-month synthetic schedule with 3-5 information-arrival
    records per month, total in [36, 60]. Anything outside this
    window means the default release fixture has drifted into a
    denser shape."""
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        profile="monthly_reference",
    )
    total_arrivals = sum(
        len(ps.information_arrival_ids) for ps in r.per_period_summaries
    )
    assert 36 <= total_arrivals <= 60, (
        f"monthly_reference default fixture produced "
        f"{total_arrivals} arrivals; expected [36, 60]"
    )


def test_v1_19_3_monthly_reference_per_period_arrival_count_in_3_to_5():
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        profile="monthly_reference",
    )
    for ps in r.per_period_summaries:
        n = len(ps.information_arrival_ids)
        assert 3 <= n <= 5, (
            f"period {ps.period_id} produced {n} arrivals; "
            f"expected per-month bound [3, 5]"
        )


def test_v1_19_3_monthly_reference_emits_no_forbidden_record_types():
    """``monthly_reference`` must remain review-only — no
    price / trade / contract / lending mutation events."""
    k = _seed_kernel()
    run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        profile="monthly_reference",
    )
    seen = {rec.record_type for rec in k.ledger.records}
    leaked = seen & _FORBIDDEN_RECORD_TYPES
    assert not leaked, (
        f"monthly_reference must not emit "
        f"{sorted(t.value for t in leaked)}"
    )


# ===========================================================================
# v1.20.3 — scenario_monthly_reference_universe performance boundary
#
# These tests pin the v1.20.0 cardinality budget *before* a
# contributor can ship a denser per-period flow. They run against
# the canonical 11-sector / 11-firm / 4-investor / 3-bank
# fixture and assert:
#
# - 12 monthly periods,
# - 11 sectors / 11 representative firm profiles,
# - 4 investor archetypes / 3 bank archetypes,
# - exactly 1 scheduled scenario application in the default
#   fixture, firing only at ``period_index == 3`` / ``month_04``,
# - total record count under the v1.20.0 hard guardrail of 4000,
# - per-period record count within the documented [200, 280]
#   window,
# - no dense forbidden loop shape ever fires
#   (``O(P x I x F x scenario)`` / ``O(P x F x order)`` /
#   ``O(P x day x ...)``).
# ===========================================================================


from world.reference_living_world import (  # noqa: E402
    LivingReferenceWorldResult,
    _DEFAULT_SCENARIO_DRIVER_TEMPLATE_ID,
    _DEFAULT_SCENARIO_SCHEDULED_MONTH_LABEL,
    _DEFAULT_SCENARIO_SCHEDULED_PERIOD_INDEX,
    _DEFAULT_SCENARIO_UNIVERSE_BANK_IDS,
    _DEFAULT_SCENARIO_UNIVERSE_FIRM_IDS,
    _DEFAULT_SCENARIO_UNIVERSE_INVESTOR_IDS,
)


# Per-period record-count window for the v1.20.3 default fixture.
# Target [200, 280]; actual ~257-261. Lower bound rejects an
# accidental phase removal; upper bound rejects a denser loop.
_V1_20_3_PER_PERIOD_LOWER_BOUND: int = 200
_V1_20_3_PER_PERIOD_UPPER_BOUND: int = 280


# Run-window cumulative budget. Soft target [2400, 3360];
# hard guardrail <= 4000.
_V1_20_3_RUN_WINDOW_HARD_GUARDRAIL: int = 4000
_V1_20_3_RUN_WINDOW_TARGET_MIN: int = 2400
_V1_20_3_RUN_WINDOW_TARGET_MAX: int = 3360


# v1.20.3 pinned digest. Updated when a v1.20.x storage book or
# the v1.20.3 orchestrator path meaningfully changes its
# canonical projection.
_V1_20_3_PINNED_DIGEST: str = (
    "5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6"
)


def _seed_v1_20_3_kernel() -> WorldKernel:
    """Deterministic seed kernel for the v1.20.3 default
    fixture. Variables + per-firm exposure mirror the v1.20.x
    /v1.19.x convention."""
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
    for firm_id in _DEFAULT_SCENARIO_UNIVERSE_FIRM_IDS:
        k.exposures.add_exposure(
            ExposureRecord(
                exposure_id=f"exposure:{firm_id}:rates",
                subject_id=firm_id,
                subject_type="firm",
                variable_id="variable:reference_long_rate_10y",
                exposure_type="funding_cost",
                metric="debt_service_burden",
                direction="positive",
                magnitude=0.3,
            )
        )
    return k


def _run_v1_20_3(k: WorldKernel) -> LivingReferenceWorldResult:
    return run_living_reference_world(
        k,
        firm_ids=_DEFAULT_SCENARIO_UNIVERSE_FIRM_IDS,
        investor_ids=_DEFAULT_SCENARIO_UNIVERSE_INVESTOR_IDS,
        bank_ids=_DEFAULT_SCENARIO_UNIVERSE_BANK_IDS,
        profile="scenario_monthly_reference_universe",
    )


# --- Default fixture topology ---


def test_v1_20_3_runs_twelve_periods():
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert r.period_count == 12
    assert len(r.per_period_summaries) == 12


def test_v1_20_3_default_firm_count_is_eleven():
    assert len(_DEFAULT_SCENARIO_UNIVERSE_FIRM_IDS) == 11
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert len(r.firm_ids) == 11


def test_v1_20_3_default_sector_count_is_eleven():
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert len(r.sector_ids) == 11


def test_v1_20_3_default_firm_profile_count_is_eleven():
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert len(r.firm_profile_ids) == 11


def test_v1_20_3_default_investor_count_is_four():
    assert len(_DEFAULT_SCENARIO_UNIVERSE_INVESTOR_IDS) == 4
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert len(r.investor_ids) == 4


def test_v1_20_3_default_bank_count_is_three():
    assert len(_DEFAULT_SCENARIO_UNIVERSE_BANK_IDS) == 3
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert len(r.bank_ids) == 3


# --- Scheduled scenario application ---


def test_v1_20_3_default_has_one_scheduled_scenario_application():
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert len(r.scenario_schedule_ids) == 1
    assert len(r.scheduled_scenario_application_ids) == 1


def test_v1_20_3_scenario_fires_only_in_scheduled_period():
    """The default scenario must fire exactly once and only at
    the pinned ``period_index == 3`` / ``month_04``. Any other
    period must emit zero scenario application records and zero
    context shifts. The scheduled-period shift count must stay
    bounded by ``scheduled_app_count x firm_count = 11``."""
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    total_apps = 0
    total_shifts = 0
    for idx, ps in enumerate(r.per_period_summaries):
        if idx == _DEFAULT_SCENARIO_SCHEDULED_PERIOD_INDEX:
            assert (
                len(ps.scenario_application_ids) == 1
            ), (
                f"scheduled period {idx} expected exactly 1 "
                f"scenario application; got "
                f"{len(ps.scenario_application_ids)}"
            )
            # ``credit_tightening_driver`` family emits exactly
            # 2 context shifts (market_environment +
            # financing_review_surface) per the v1.18.2
            # _build_shift_specs mapping.
            assert len(ps.scenario_context_shift_ids) == 2
        else:
            assert ps.scenario_application_ids == ()
            assert ps.scenario_context_shift_ids == ()
        total_apps += len(ps.scenario_application_ids)
        total_shifts += len(ps.scenario_context_shift_ids)
    assert total_apps == 1
    assert total_shifts <= 1 * len(r.firm_ids)


def test_v1_20_3_scheduled_application_carries_expected_template():
    """Pin the schedule's template id. Drift would mean the
    default fixture has been re-pointed at a different scenario
    family without an explicit task."""
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    sched = k.scenario_schedule.get_schedule(
        r.scenario_schedule_ids[0]
    )
    assert sched.scenario_driver_template_ids == (
        _DEFAULT_SCENARIO_DRIVER_TEMPLATE_ID,
    )
    app = k.scenario_schedule.get_scheduled_application(
        r.scheduled_scenario_application_ids[0]
    )
    assert (
        app.scheduled_period_index
        == _DEFAULT_SCENARIO_SCHEDULED_PERIOD_INDEX
    )
    assert (
        app.scheduled_month_label
        == _DEFAULT_SCENARIO_SCHEDULED_MONTH_LABEL
    )


# --- Cardinality budget (binding) ---


def test_v1_20_3_total_record_count_under_hard_guardrail():
    """Hard guardrail: the default fixture must stay under 4000
    records. If this assertion fires, a denser loop has crept
    in — investigate before relaxing the bound."""
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert (
        r.created_record_count
        <= _V1_20_3_RUN_WINDOW_HARD_GUARDRAIL
    ), (
        f"v1.20.3 default fixture produced "
        f"{r.created_record_count} records — exceeds the "
        f"v1.20.0 hard guardrail of "
        f"{_V1_20_3_RUN_WINDOW_HARD_GUARDRAIL}"
    )


def test_v1_20_3_per_period_record_count_within_bounded_window():
    """Each period must produce a record count inside the
    documented [200, 280] target window. The default fixture
    runs at ~258."""
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    for ps in r.per_period_summaries:
        assert (
            _V1_20_3_PER_PERIOD_LOWER_BOUND
            <= ps.record_count_created
            <= _V1_20_3_PER_PERIOD_UPPER_BOUND
        ), (
            f"period {ps.period_id} produced "
            f"{ps.record_count_created} records — outside "
            f"the v1.20.3 per-period window "
            f"[{_V1_20_3_PER_PERIOD_LOWER_BOUND}, "
            f"{_V1_20_3_PER_PERIOD_UPPER_BOUND}]"
        )


def test_v1_20_3_total_record_count_within_target_window():
    """Soft target: cumulative records in [2400, 3360]. The
    default fixture runs at ~3220."""
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert (
        _V1_20_3_RUN_WINDOW_TARGET_MIN
        <= r.created_record_count
        <= _V1_20_3_RUN_WINDOW_TARGET_MAX
    ), (
        f"v1.20.3 default fixture produced "
        f"{r.created_record_count} records — outside the "
        f"[{_V1_20_3_RUN_WINDOW_TARGET_MIN}, "
        f"{_V1_20_3_RUN_WINDOW_TARGET_MAX}] soft target window"
    )


def test_v1_20_3_no_forbidden_mutation_record_in_ledger_slice():
    """Forbidden loop shape detection: the presence of any
    order / price-update / contract / ownership-transfer
    record type would mean a price / order / trade / execution
    / settlement loop has crept in."""
    k = _seed_v1_20_3_kernel()
    _run_v1_20_3(k)
    seen = {rec.record_type for rec in k.ledger.records}
    leaked = seen & _FORBIDDEN_RECORD_TYPES
    assert not leaked, (
        f"scenario_monthly_reference_universe must not emit "
        f"{sorted(t.value for t in leaked)}"
    )


# --- Closed-loop allowed loop shapes ---


def test_v1_20_3_investor_market_intent_count_is_per_period_i_times_f():
    """The closed-loop allowed shape ``O(P x I x F)`` is
    pinned at exactly 4 x 11 = 44 per period. A higher count
    (e.g., x venue) would mean a forbidden
    ``O(P x I x F x venue)`` loop has crept in."""
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    expected_per_period = (
        len(r.investor_ids) * len(r.firm_ids)
    )
    for ps in r.per_period_summaries:
        assert (
            len(ps.investor_market_intent_ids)
            == expected_per_period
        ), (
            f"period {ps.period_id} has "
            f"{len(ps.investor_market_intent_ids)} market "
            f"intents; expected exactly "
            f"{expected_per_period} (I x F)"
        )


def test_v1_20_3_bank_credit_review_count_is_per_period_b_times_f():
    """Closed-loop shape ``O(P x B x F)`` is pinned at exactly
    3 x 11 = 33 per period."""
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    expected_per_period = len(r.bank_ids) * len(r.firm_ids)
    for ps in r.per_period_summaries:
        assert (
            len(ps.bank_credit_review_signal_ids)
            == expected_per_period
        )


def test_v1_20_3_firm_state_count_is_per_period_f():
    """Closed-loop shape ``O(P x F)`` is pinned at exactly
    11 per period for the firm-financial-state phase."""
    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    for ps in r.per_period_summaries:
        assert (
            len(ps.firm_financial_state_ids) == len(r.firm_ids)
        )


# --- Determinism + digest pins ---


def test_v1_20_3_living_world_digest_is_deterministic_across_kernels():
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )

    k1 = _seed_v1_20_3_kernel()
    r1 = _run_v1_20_3(k1)
    k2 = _seed_v1_20_3_kernel()
    r2 = _run_v1_20_3(k2)
    assert living_world_digest(k1, r1) == living_world_digest(
        k2, r2
    )


def test_v1_20_3_living_world_digest_is_pinned():
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )

    k = _seed_v1_20_3_kernel()
    r = _run_v1_20_3(k)
    assert (
        living_world_digest(k, r) == _V1_20_3_PINNED_DIGEST
    ), (
        "v1.20.3 living_world_digest drifted; if intentional, "
        "update _V1_20_3_PINNED_DIGEST and document the cause"
    )
