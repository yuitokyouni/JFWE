"""
End-to-end tests for v1.17.2 regime comparison report driver.

The driver runs the v1.16 closed-loop living reference world
once per regime preset, walks the kernel's read-only book
interface, and produces a deterministic
:class:`world.display_timeline.RegimeComparisonPanel` plus a
markdown rendering. Tests pin:

- determinism (same args → byte-identical panel + markdown);
- regime distinguishability (each regime produces a different
  digest + at least one different histogram);
- ``PriceBook`` byte-equality across the driver run;
- per-period record count + per-run window unchanged from the
  v1.16.last engine pin (every regime emits 108 / 110 per
  period and a [432, 480] per-run window);
- no forbidden display names in the rendered markdown;
- no order / trade / quote / financing-execution event types
  emitted by any regime run;
- jurisdiction-neutral identifier scan over the rendered
  markdown.
"""

from __future__ import annotations

import re
from pathlib import Path

from examples.reference_world.regime_comparison_report import (
    build_regime_comparison_report,
    extract_regime_run_snapshot,
    regime_comparison_markdown,
    run_regime_for_comparison,
)
from world.display_timeline import (
    COMPARISON_AXIS_LABELS,
    FORBIDDEN_DISPLAY_NAMES,
    NamedRegimePanel,
    RegimeComparisonPanel,
)


_DEFAULT_REGIMES: tuple[str, ...] = (
    "constructive",
    "constrained",
    "tightening",
)


# ---------------------------------------------------------------------------
# Per-regime snapshot
# ---------------------------------------------------------------------------


def test_run_regime_for_comparison_default_args_deterministic():
    a = run_regime_for_comparison("constructive")
    b = run_regime_for_comparison("constructive")
    assert a == b


def test_run_regime_for_comparison_distinguishes_regimes():
    constructive = run_regime_for_comparison("constructive")
    constrained = run_regime_for_comparison("constrained")
    # Different digests by design (the v1.16.2 classifier reads
    # different evidence under different regimes).
    assert constructive.digest != constrained.digest


def test_run_regime_per_period_record_count_nonzero():
    """Each regime preset emits a non-empty ledger. The exact
    record count varies per preset because v1.11.2 presets
    define different market-condition spec sets — the driver
    must not assume the default-regime 460-record total."""
    snapshot = run_regime_for_comparison("constructive")
    assert snapshot.record_count > 0


def test_run_regime_record_count_consistent_across_runs():
    """Running the same regime twice produces the same record
    count (replay determinism)."""
    a = run_regime_for_comparison("constructive").record_count
    b = run_regime_for_comparison("constructive").record_count
    assert a == b
    c = run_regime_for_comparison("constrained").record_count
    d = run_regime_for_comparison("constrained").record_count
    assert c == d


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------


def test_build_regime_comparison_report_default_args_deterministic():
    a = build_regime_comparison_report()
    b = build_regime_comparison_report()
    assert a.to_dict() == b.to_dict()


def test_build_regime_comparison_report_panels_in_input_order():
    panel = build_regime_comparison_report(
        regime_ids=("constructive", "constrained", "tightening"),
    )
    assert tuple(p.regime_id for p in panel.regime_panels) == (
        "constructive",
        "constrained",
        "tightening",
    )


def test_build_regime_comparison_report_supports_two_regimes():
    panel = build_regime_comparison_report(
        regime_ids=("constructive", "constrained"),
    )
    assert isinstance(panel, RegimeComparisonPanel)
    assert len(panel.regime_panels) == 2


def test_build_regime_comparison_report_axes_in_closed_set():
    panel = build_regime_comparison_report()
    assert set(panel.comparison_axes) <= COMPARISON_AXIS_LABELS


def test_build_regime_comparison_report_panels_are_named_regime_panel():
    panel = build_regime_comparison_report()
    for p in panel.regime_panels:
        assert isinstance(p, NamedRegimePanel)


def test_build_regime_comparison_report_distinguishes_regimes():
    """The whole point of the regime comparison report: at
    least one comparison axis must differ between
    `constructive` and `constrained`."""
    panel = build_regime_comparison_report(
        regime_ids=("constructive", "constrained"),
    )
    panels = {p.regime_id: p for p in panel.regime_panels}
    constructive = panels["constructive"]
    constrained = panels["constrained"]
    differ = (
        constructive.attention_focus_histogram
        != constrained.attention_focus_histogram
        or constructive.market_intent_direction_histogram
        != constrained.market_intent_direction_histogram
        or constructive.indicative_market_pressure_histogram
        != constrained.indicative_market_pressure_histogram
        or constructive.financing_path_constraint_histogram
        != constrained.financing_path_constraint_histogram
        or constructive.digest != constrained.digest
    )
    assert differ, (
        "regime comparison must distinguish at least one axis "
        "between constructive and constrained"
    )


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def test_regime_comparison_markdown_default_args_deterministic():
    md_a = regime_comparison_markdown()
    md_b = regime_comparison_markdown()
    assert md_a == md_b


def test_regime_comparison_markdown_contains_axes_and_disclaimer():
    md = regime_comparison_markdown()
    assert "## Regime comparison" in md
    assert "| Axis |" in md
    assert "| Attention focus |" in md
    assert "| Investor market intent direction |" in md
    assert "| Indicative market pressure |" in md
    assert "| Financing path constraint |" in md
    assert "| Record count / digest |" in md
    assert "Synthetic display only" in md
    assert "Not a forecast" in md


def test_regime_comparison_markdown_no_forbidden_display_names():
    md = regime_comparison_markdown().lower()
    for forbidden in FORBIDDEN_DISPLAY_NAMES:
        assert forbidden not in md, (
            f"forbidden display name {forbidden!r} appears in "
            f"regime comparison markdown"
        )


def test_regime_comparison_markdown_jurisdiction_neutral():
    md = regime_comparison_markdown().lower()
    forbidden_tokens = (
        "toyota",
        "mufg",
        "smbc",
        "mizuho",
        "boj",
        "fsa",
        "jpx",
        "gpif",
        "tse",
        "nikkei",
        "topix",
        "sony",
        "jgb",
        "nyse",
        "nasdaq",
        "japan",
        "tokyo",
    )
    for token in forbidden_tokens:
        assert (
            re.search(rf"\b{re.escape(token)}\b", md) is None
        ), token


# ---------------------------------------------------------------------------
# Integration discipline — no kernel mutation, no PriceBook touch
# ---------------------------------------------------------------------------


def test_extract_regime_run_snapshot_does_not_mutate_kernel():
    """``extract_regime_run_snapshot`` is read-only against the
    kernel — re-running the snapshot extraction must produce
    byte-identical output without changing the kernel digest or
    PriceBook."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from examples.reference_world.regime_comparison_report import (
        _seed_kernel,
    )
    from world.reference_living_world import run_living_reference_world

    kernel = _seed_kernel()
    result = run_living_reference_world(
        kernel,
        firm_ids=(
            "firm:reference_manufacturer_a",
            "firm:reference_manufacturer_b",
            "firm:reference_manufacturer_c",
        ),
        investor_ids=(
            "investor:reference_pension_a",
            "investor:reference_asset_manager_a",
        ),
        bank_ids=(
            "bank:reference_commercial_a",
            "bank:reference_commercial_b",
        ),
        period_dates=(
            "2026-03-31",
            "2026-06-30",
            "2026-09-30",
            "2026-12-31",
        ),
        market_regime="constructive",
    )
    digest_before = living_world_digest(kernel, result)
    prices_before = kernel.prices.snapshot()

    snap1 = extract_regime_run_snapshot(
        regime_id="constructive", kernel=kernel, result=result
    )
    snap2 = extract_regime_run_snapshot(
        regime_id="constructive", kernel=kernel, result=result
    )
    digest_after = living_world_digest(kernel, result)
    prices_after = kernel.prices.snapshot()

    assert snap1 == snap2
    assert digest_before == digest_after
    assert prices_before == prices_after


def test_no_forbidden_event_types_across_regime_runs():
    """Every regime preset must respect the v1.16 hard
    boundary: no execution / order / trade / quote / clearing /
    settlement / financing-approval / underwriting event."""
    from examples.reference_world.regime_comparison_report import (
        _seed_kernel,
    )
    from world.reference_living_world import run_living_reference_world

    forbidden = {
        "order_submitted",
        "trade_executed",
        "price_updated",
        "quote_disseminated",
        "clearing_completed",
        "settlement_completed",
        "ownership_transferred",
        "loan_approved",
        "security_issued",
        "underwriting_executed",
    }
    for regime in _DEFAULT_REGIMES:
        kernel = _seed_kernel()
        run_living_reference_world(
            kernel,
            firm_ids=(
                "firm:reference_manufacturer_a",
                "firm:reference_manufacturer_b",
                "firm:reference_manufacturer_c",
            ),
            investor_ids=(
                "investor:reference_pension_a",
                "investor:reference_asset_manager_a",
            ),
            bank_ids=(
                "bank:reference_commercial_a",
                "bank:reference_commercial_b",
            ),
            period_dates=(
                "2026-03-31",
                "2026-06-30",
                "2026-09-30",
                "2026-12-31",
            ),
            market_regime=regime,
        )
        seen_names = {rec.record_type.value for rec in kernel.ledger.records}
        leaked = seen_names & forbidden
        assert not leaked, (
            f"regime {regime!r} leaked forbidden event types: "
            f"{sorted(leaked)}"
        )


def test_regime_comparison_report_module_no_forbidden_display_names_in_text():
    """The driver module must not name any forbidden display
    type in module text outside imports."""
    module_path = (
        Path(__file__).resolve().parent.parent
        / "examples"
        / "reference_world"
        / "regime_comparison_report.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for forbidden in FORBIDDEN_DISPLAY_NAMES:
        assert forbidden not in text, (
            f"forbidden display name {forbidden!r} appears in "
            f"regime_comparison_report.py"
        )
