"""
Tests for v1.9.1 Living World Trace Report.

Pins the v1.9.1 contract end-to-end:

- ``build_living_world_trace_report`` produces an immutable
  ``LivingWorldTraceReport`` whose ledger-slice metadata matches
  the v1.9.0 result.
- ``infra_record_count + per_period_record_count_total ==
  created_record_count`` (the v1.9.1-prep algebra).
- ``record_type_counts`` sums to ``created_record_count`` and is
  sorted for determinism.
- ``ordered_record_ids`` matches
  ``LivingReferenceWorldResult.created_record_ids`` byte-identically.
- Per-period reports preserve `period_id` / `as_of_date` / signal
  ids and carry their own per-period `record_type_counts`.
- Aggregated attention divergence (`shared_selected_refs`,
  `investor_only_refs`, `bank_only_refs`) matches the unions of
  stored selections and is sorted alphabetically.
- `to_dict` and `render_living_world_markdown` are deterministic
  across two fresh kernels seeded identically.
- Markdown contains every required section heading and emits the
  hard-boundary statement verbatim.
- Tampered chain results trigger `warnings` strings without
  crashing.
- The reporter is **read-only** — every kernel book and the ledger
  length stay byte-identical.
- The CLI prints both the operational trace and the Markdown
  report when `--markdown` is supplied; default mode prints only
  the trace.
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
from world.living_world_report import (
    LivingWorldPeriodReport,
    LivingWorldTraceReport,
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_FIRMS: tuple[str, ...] = (
    "firm:reference_manufacturer_a",
    "firm:reference_retailer_b",
    "firm:reference_utility_c",
)

_INVESTORS: tuple[str, ...] = (
    "investor:reference_pension_a",
    "investor:reference_growth_fund_a",
)

_BANKS: tuple[str, ...] = (
    "bank:reference_megabank_a",
    "bank:reference_regional_b",
)


_VARIABLES: tuple[tuple[str, str], ...] = (
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


def _seed_kernel() -> WorldKernel:
    k = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )
    for vid, vgroup in _VARIABLES:
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
        for q in _OBS_DATES:
            k.variables.add_observation(
                VariableObservation(
                    observation_id=f"obs:{vid}:{q}",
                    variable_id=vid,
                    as_of_date=q,
                    value=100.0,
                    unit="index",
                    vintage_id=f"{q}_initial",
                )
            )

    for inv in _INVESTORS:
        k.exposures.add_exposure(
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
        k.exposures.add_exposure(
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
    for bnk in _BANKS:
        k.exposures.add_exposure(
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
        k.exposures.add_exposure(
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

    return k


def _seeded_run() -> tuple[WorldKernel, LivingReferenceWorldResult]:
    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRMS,
        investor_ids=_INVESTORS,
        bank_ids=_BANKS,
    )
    return k, r


# ---------------------------------------------------------------------------
# Build / shape
# ---------------------------------------------------------------------------


def test_build_returns_immutable_report():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    assert isinstance(report, LivingWorldTraceReport)
    with pytest.raises(Exception):
        report.report_id = "tampered"  # type: ignore[misc]


def test_report_carries_all_setup_counts():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    assert report.run_id == r.run_id
    assert report.period_count == r.period_count
    assert report.firm_count == len(r.firm_ids)
    assert report.investor_count == len(r.investor_ids)
    assert report.bank_count == len(r.bank_ids)


def test_report_carries_one_period_summary_per_period():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    assert len(report.period_summaries) == r.period_count
    for ps in report.period_summaries:
        assert isinstance(ps, LivingWorldPeriodReport)


def test_period_reports_preserve_ids_and_dates():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    for source, projected in zip(r.per_period_summaries, report.period_summaries):
        assert projected.period_id == source.period_id
        assert projected.as_of_date == source.as_of_date
        assert projected.record_count_created == source.record_count_created
        assert projected.corporate_signal_ids == source.corporate_signal_ids
        assert (
            projected.investor_review_signal_ids
            == source.investor_review_signal_ids
        )
        assert (
            projected.bank_review_signal_ids == source.bank_review_signal_ids
        )


# ---------------------------------------------------------------------------
# Infra prelude algebra (the v1.9.1-prep finding)
# ---------------------------------------------------------------------------


def test_infra_plus_per_period_total_equals_created_record_count():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    assert (
        report.infra_record_count
        + report.per_period_record_count_total
        == report.created_record_count
    )
    assert report.created_record_count == r.created_record_count


def test_infra_record_count_is_strictly_positive_on_canonical_seed():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    # The canonical fixture registers interactions + per-firm
    # routines + per-actor profiles + review routines before the
    # period loop, so the prelude is always > 0 on this seed.
    assert report.infra_record_count > 0


# ---------------------------------------------------------------------------
# Record type counts
# ---------------------------------------------------------------------------


def test_record_type_counts_sum_to_created_record_count():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    total = sum(count for _, count in report.record_type_counts)
    assert total == report.created_record_count


def test_record_type_counts_are_sorted_for_determinism():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    keys = [event_type for event_type, _ in report.record_type_counts]
    assert keys == sorted(keys)


def test_per_period_record_type_counts_sum_to_period_record_count():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    for ps in report.period_summaries:
        total = sum(count for _, count in ps.record_type_counts)
        assert total == ps.record_count_created


# ---------------------------------------------------------------------------
# Ordered record ids
# ---------------------------------------------------------------------------


def test_ordered_record_ids_match_living_world_result():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    assert report.ordered_record_ids == r.created_record_ids


# ---------------------------------------------------------------------------
# Attention divergence
# ---------------------------------------------------------------------------


def test_aggregated_set_differences_match_stored_selections():
    """The aggregated investor / bank ref unions must equal the
    actual unions of stored selections; the set differences
    follow."""
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)

    investor_union: set[str] = set()
    bank_union: set[str] = set()
    for period in r.per_period_summaries:
        for sel_id in period.investor_selection_ids:
            investor_union.update(
                k.attention.get_selection(sel_id).selected_refs
            )
        for sel_id in period.bank_selection_ids:
            bank_union.update(
                k.attention.get_selection(sel_id).selected_refs
            )

    assert set(report.shared_selected_refs) == investor_union & bank_union
    assert set(report.investor_only_refs) == investor_union - bank_union
    assert set(report.bank_only_refs) == bank_union - investor_union


def test_set_difference_tuples_are_sorted_alphabetically():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    assert list(report.shared_selected_refs) == sorted(report.shared_selected_refs)
    assert list(report.investor_only_refs) == sorted(report.investor_only_refs)
    assert list(report.bank_only_refs) == sorted(report.bank_only_refs)


def test_per_actor_ref_counts_cover_every_period_and_actor():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    assert len(report.investor_selected_ref_counts) == r.period_count * len(
        _INVESTORS
    )
    assert len(report.bank_selected_ref_counts) == r.period_count * len(
        _BANKS
    )
    # Triples sorted by (period_id, actor_id).
    for triples in (
        report.investor_selected_ref_counts,
        report.bank_selected_ref_counts,
    ):
        keys = [(period_id, actor_id) for actor_id, period_id, _ in triples]
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_to_dict_is_deterministic_across_fresh_kernels():
    a_kernel, a_result = _seeded_run()
    b_kernel, b_result = _seeded_run()
    a = build_living_world_trace_report(a_kernel, a_result).to_dict()
    b = build_living_world_trace_report(b_kernel, b_result).to_dict()
    assert a == b


def test_markdown_is_deterministic_across_fresh_kernels():
    a_kernel, a_result = _seeded_run()
    b_kernel, b_result = _seeded_run()
    a = render_living_world_markdown(
        build_living_world_trace_report(a_kernel, a_result)
    )
    b = render_living_world_markdown(
        build_living_world_trace_report(b_kernel, b_result)
    )
    assert a == b


# ---------------------------------------------------------------------------
# Markdown content
# ---------------------------------------------------------------------------


def test_markdown_contains_required_sections():
    k, r = _seeded_run()
    md = render_living_world_markdown(build_living_world_trace_report(k, r))
    for heading in (
        "# living_reference_world",
        "## Setup",
        "## Infra prelude",
        "## Per-period summary",
        "## Attention divergence",
        "## Ledger event-type counts",
        "## Warnings",
        "## Boundaries",
    ):
        assert heading in md


def test_markdown_emits_hard_boundary_statement_verbatim():
    k, r = _seeded_run()
    md = render_living_world_markdown(build_living_world_trace_report(k, r))
    assert (
        "No price formation, no trading, no lending decisions, "
        "no valuation behavior, no Japan calibration, no real data, "
        "no investment advice."
    ) in md


def test_markdown_per_period_table_lists_every_period():
    k, r = _seeded_run()
    md = render_living_world_markdown(build_living_world_trace_report(k, r))
    for period in r.per_period_summaries:
        assert period.as_of_date in md


# ---------------------------------------------------------------------------
# Warnings on tampered results
# ---------------------------------------------------------------------------


def test_warning_when_chain_count_does_not_match_slice():
    k, r = _seeded_run()
    object.__setattr__(r, "created_record_ids", r.created_record_ids[:-1])
    report = build_living_world_trace_report(k, r)
    # The slice the reporter walks (using ledger_record_count_*)
    # is the truth; mismatch triggers the warning.
    assert any(
        "do not match" in w or "ledger slice length" in w
        for w in report.warnings
    )


def test_warning_when_end_index_extends_past_ledger():
    k, r = _seeded_run()
    object.__setattr__(
        r, "ledger_record_count_after", r.ledger_record_count_after + 5
    )
    report = build_living_world_trace_report(k, r)
    assert any(
        "ledger.records has length" in w or "slice truncated" in w
        for w in report.warnings
    )


def test_canonical_run_produces_no_warnings():
    k, r = _seeded_run()
    report = build_living_world_trace_report(k, r)
    assert report.warnings == ()


def test_report_rejects_kernel_none():
    _, r = _seeded_run()
    with pytest.raises(ValueError):
        build_living_world_trace_report(None, r)


def test_report_rejects_non_result():
    k = _seed_kernel()
    with pytest.raises(TypeError):
        build_living_world_trace_report(k, {"not": "a result"})


# ---------------------------------------------------------------------------
# Schema-level __post_init__ validation
# ---------------------------------------------------------------------------


def test_report_post_init_rejects_inconsistent_algebra():
    with pytest.raises(ValueError):
        LivingWorldTraceReport(
            report_id="r:1",
            run_id="run:1",
            period_count=0,
            firm_count=0,
            investor_count=0,
            bank_count=0,
            ledger_record_count_before=0,
            ledger_record_count_after=10,
            created_record_count=10,
            infra_record_count=3,
            per_period_record_count_total=4,  # 3 + 4 != 10
            record_type_counts=(),
            period_summaries=(),
        )


# ---------------------------------------------------------------------------
# Read-only guarantee
# ---------------------------------------------------------------------------


def _capture_state(k: WorldKernel) -> dict[str, Any]:
    return {
        "ledger_length": len(k.ledger.records),
        "valuations": k.valuations.snapshot(),
        "prices": k.prices.snapshot(),
        "ownership": k.ownership.snapshot(),
        "contracts": k.contracts.snapshot(),
        "constraints": k.constraints.snapshot(),
        "exposures": k.exposures.snapshot(),
        "variables": k.variables.snapshot(),
        "institutions": k.institutions.snapshot(),
        "external_processes": k.external_processes.snapshot(),
        "relationships": k.relationships.snapshot(),
        "attention": k.attention.snapshot(),
        "routines": k.routines.snapshot(),
        "interactions": k.interactions.snapshot(),
        "signal_count": len(k.signals.all_signals()),
    }


def test_build_does_not_mutate_kernel():
    k, r = _seeded_run()
    before = _capture_state(k)
    report = build_living_world_trace_report(k, r)
    render_living_world_markdown(report)
    report.to_dict()
    after = _capture_state(k)
    assert before == after


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


def test_cli_smoke_prints_trace_only_by_default():
    from examples.reference_world import run_living_reference_world as cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.main([])
    out = buf.getvalue()
    assert "[setup]" in out
    assert "[period 1]" in out
    assert "[period 4]" in out
    assert "[ledger]" in out
    # Without --markdown, the report headings must not appear.
    assert "## Setup" not in out
    assert "## Infra prelude" not in out


def test_cli_smoke_appends_markdown_when_flag_supplied():
    from examples.reference_world import run_living_reference_world as cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.main(["--markdown"])
    out = buf.getvalue()
    # Operational trace still printed.
    assert "[setup]" in out
    # Plus the report.
    assert "# living_reference_world" in out
    assert "## Infra prelude" in out
    assert "## Boundaries" in out
    assert "no investment advice" in out
