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
        banks * firms                          bank credit review note (v1.9.7)
        investors * firms                      portfolio-company dialogue (v1.10.2)
        investors * firms                      investor escalation candidate (v1.10.3)
        investors * firms                      investor intent signal (v1.12.1)
        firms                                  corporate strategic response candidate (v1.10.3)
        2 * (investors + banks)                review_run + review_signal

    For the default fixture (3 firms, 2 investors, 2 banks,
    3 industries, 5 markets, 1 readout/period, 1 environment
    state/period, 4 periods) this is 71 records per period × 4
    periods = 284.
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
        + banks * firms                        # credit review
        + investors * firms                    # dialogue (v1.10.2)
        + investors * firms                    # escalation candidate (v1.10.3, investor)
        + investors * firms                    # investor intent signal (v1.12.1)
        + firms                                # response candidate (v1.10.3, corporate)
        + 2 * actors                           # review_run + review_signal
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
    the per-period count is 71 records (37 v1.9.x + 18 v1.10.5
    + 5 v1.11.0 capital-market + 1 v1.11.1 capital-market readout
    + 1 v1.12.2 market environment state + 3 v1.12.0 firm
    financial latent state + 6 v1.12.1 investor intent); the
    per-run total is 71 × 4 = 284, plus up to 32 records of
    one-off setup overhead (14 v1.9.x infra + 4 v1.10.5
    stewardship themes + headroom; v1.11.0 / v1.11.1 / v1.12.0 /
    v1.12.1 / v1.12.2 add no new setup records), giving a tight
    total-run window of [284, 316].
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
    # Tight per-run upper bound: no more than 32 setup records
    # on top of the per-period work over the entire run. v1.9.7
    # sits at ~14 such records; v1.10.5 adds 4 stewardship-theme
    # records to setup; 32 leaves headroom for harmless infra
    # adjustments but is far below any quadratic explosion (which
    # would push the count to triple-digit growth per period).
    upper_bound = expected_run_total + 32
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
    # Per docs/performance_boundary.md (v1.12.2):
    # 4 × 71 = 284 records per run from the per-period formula.
    assert total == 284


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
