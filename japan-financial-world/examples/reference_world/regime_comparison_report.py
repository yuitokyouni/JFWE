"""
v1.17.2 — Regime comparison report driver.

This is the kernel-reading bridge between
:mod:`world.display_timeline` (which is intentionally
runtime-book-free) and the v1.9.x living reference world. It
walks the kernel's existing v1.16 closed-loop records, extracts
deterministic label tuples, and produces a
:class:`world.display_timeline.RegimeComparisonPanel` plus a
markdown rendering.

The driver:

- runs ``run_living_reference_world`` once per regime preset
  passed in (each run isolated in a fresh
  :class:`world.kernel.WorldKernel`);
- reads only via the read-only book interface (``list_*`` /
  ``get_*``) — never writes, never mutates;
- never touches the ``PriceBook``;
- never prints, never logs (the caller may print the markdown
  string returned).

This is **display / report only**. It does **not** introduce
new economic state, **does not** mutate any source-of-truth
book, **does not** create prices, forecasts, target prices,
expected returns, or recommendations, **does not** ingest real
data, and **does not** make a Japan-specific calibration claim.
The v1.16 hard boundary applies bit-for-bit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Mapping, Sequence

from examples.reference_world.living_world_replay import (
    living_world_digest,
)
from world.clock import Clock
from world.display_timeline import (
    CausalTimelineAnnotation,
    EventAnnotationRecord,
    NamedRegimePanel,
    RegimeComparisonPanel,
    build_causal_timeline_annotations_from_closed_loop_data,
    build_event_annotations_from_closed_loop_data,
    build_named_regime_panel,
    build_regime_comparison_panel,
    render_regime_comparison_markdown,
)
from world.kernel import WorldKernel
from world.ledger import Ledger
from world.reference_living_world import (
    LivingReferenceWorldResult,
    run_living_reference_world,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


# ---------------------------------------------------------------------------
# Default fixture (mirrors tests/test_living_reference_world.py)
# ---------------------------------------------------------------------------


_DEFAULT_FIRM_IDS: tuple[str, ...] = (
    "firm:reference_manufacturer_a",
    "firm:reference_manufacturer_b",
    "firm:reference_manufacturer_c",
)
_DEFAULT_INVESTOR_IDS: tuple[str, ...] = (
    "investor:reference_pension_a",
    "investor:reference_asset_manager_a",
)
_DEFAULT_BANK_IDS: tuple[str, ...] = (
    "bank:reference_commercial_a",
    "bank:reference_commercial_b",
)
_DEFAULT_PERIOD_DATES: tuple[str, ...] = (
    "2026-03-31",
    "2026-06-30",
    "2026-09-30",
    "2026-12-31",
)


def _seed_kernel() -> WorldKernel:
    """Build a fresh kernel for one regime run. The fixture
    deliberately mirrors the default fixture used by the
    integration tests so the same regime-preset arguments
    reproduce the same byte-identical run."""
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


# ---------------------------------------------------------------------------
# Kernel → label-tuples extraction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _RegimeRunSnapshot:
    regime_id: str
    digest: str
    record_count: int
    unresolved_refs_count: int
    attention_focus_labels: tuple[str, ...]
    market_intent_direction_labels: tuple[str, ...]
    aggregated_market_interest_labels: tuple[str, ...]
    indicative_market_pressure_labels: tuple[str, ...]
    financing_path_constraint_labels: tuple[str, ...]
    financing_path_coherence_labels: tuple[str, ...]
    event_annotations: tuple[EventAnnotationRecord, ...]
    causal_annotations: tuple[CausalTimelineAnnotation, ...]


def _sum_unresolved_refs(kernel: WorldKernel) -> int:
    """Sum a small, deterministic set of unresolved-ref counts
    across the v1.16 closed-loop records.

    The v1.16.2 ``InvestorMarketIntentRecord`` carries
    ``classifier_unresolved_or_missing_count`` in metadata; the
    v1.15.3 / v1.15.4 helpers record
    ``unresolved_*_count`` / ``mismatched_*_count`` in their
    metadata. Summing these gives a single total. Read-only;
    no kernel mutation."""
    total = 0
    for intent in kernel.investor_market_intents.list_intents():
        md = intent.metadata or {}
        v = md.get("classifier_unresolved_or_missing_count", 0)
        if isinstance(v, int) and not isinstance(v, bool):
            total += v
    for agg in kernel.aggregated_market_interest.list_records():
        md = agg.metadata or {}
        for k, v in md.items():
            kl = str(k).lower()
            if (
                ("unresolved" in kl or "mismatched" in kl)
                and isinstance(v, int)
                and not isinstance(v, bool)
            ):
                total += v
    for pressure in kernel.indicative_market_pressure.list_records():
        md = pressure.metadata or {}
        for k, v in md.items():
            kl = str(k).lower()
            if (
                ("unresolved" in kl or "mismatched" in kl)
                and isinstance(v, int)
                and not isinstance(v, bool)
            ):
                total += v
    return total


def extract_regime_run_snapshot(
    *,
    regime_id: str,
    kernel: WorldKernel,
    result: LivingReferenceWorldResult,
) -> _RegimeRunSnapshot:
    """Read the kernel's v1.16 closed-loop records and produce
    the label tuples needed to build a
    :class:`NamedRegimePanel`. Read-only.
    """
    digest = living_world_digest(kernel, result)

    attention_focus: list[str] = []
    for state in kernel.attention_feedback.list_attention_states():
        attention_focus.extend(state.focus_labels)

    market_intent_direction: list[str] = []
    for intent in kernel.investor_market_intents.list_intents():
        market_intent_direction.append(intent.intent_direction_label)

    aggregated_market_interest: list[str] = []
    for agg in kernel.aggregated_market_interest.list_records():
        aggregated_market_interest.append(agg.net_interest_label)

    indicative_market_pressure: list[str] = []
    for pressure in kernel.indicative_market_pressure.list_records():
        indicative_market_pressure.append(pressure.market_access_label)

    financing_path_constraint: list[str] = []
    financing_path_coherence: list[str] = []
    for path in kernel.financing_paths.list_paths():
        financing_path_constraint.append(path.constraint_label)
        financing_path_coherence.append(path.coherence_label)

    record_count = len(kernel.ledger.records)
    unresolved_refs_count = _sum_unresolved_refs(kernel)

    # v1.17.3 — extract closed-loop records for the event /
    # causal annotation helpers. Read-only.
    env_states = tuple(kernel.market_environments.list_states())
    pressure_records = tuple(
        kernel.indicative_market_pressure.list_records()
    )
    path_records = tuple(kernel.financing_paths.list_paths())
    attention_records = tuple(
        kernel.attention_feedback.list_attention_states()
    )
    event_annotations = build_event_annotations_from_closed_loop_data(
        market_environment_states=env_states,
        indicative_market_pressures=pressure_records,
        financing_paths=path_records,
        attention_states=attention_records,
        annotation_id_prefix=f"event_annotation:{regime_id}",
    )
    causal_annotations = (
        build_causal_timeline_annotations_from_closed_loop_data(
            indicative_market_pressures=pressure_records,
            financing_paths=path_records,
            attention_states=attention_records,
            annotation_id_prefix=f"causal_timeline:{regime_id}",
        )
    )

    return _RegimeRunSnapshot(
        regime_id=regime_id,
        digest=digest,
        record_count=record_count,
        unresolved_refs_count=unresolved_refs_count,
        attention_focus_labels=tuple(attention_focus),
        market_intent_direction_labels=tuple(market_intent_direction),
        aggregated_market_interest_labels=tuple(aggregated_market_interest),
        indicative_market_pressure_labels=tuple(indicative_market_pressure),
        financing_path_constraint_labels=tuple(financing_path_constraint),
        financing_path_coherence_labels=tuple(financing_path_coherence),
        event_annotations=event_annotations,
        causal_annotations=causal_annotations,
    )


def named_regime_panel_from_snapshot(
    snapshot: _RegimeRunSnapshot,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> NamedRegimePanel:
    return build_named_regime_panel(
        regime_id=snapshot.regime_id,
        digest=snapshot.digest,
        record_count=snapshot.record_count,
        unresolved_refs_count=snapshot.unresolved_refs_count,
        attention_focus_labels=snapshot.attention_focus_labels,
        market_intent_direction_labels=(
            snapshot.market_intent_direction_labels
        ),
        aggregated_market_interest_labels=(
            snapshot.aggregated_market_interest_labels
        ),
        indicative_market_pressure_labels=(
            snapshot.indicative_market_pressure_labels
        ),
        financing_path_constraint_labels=(
            snapshot.financing_path_constraint_labels
        ),
        financing_path_coherence_labels=(
            snapshot.financing_path_coherence_labels
        ),
        event_annotations=snapshot.event_annotations,
        causal_annotations=snapshot.causal_annotations,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Top-level driver
# ---------------------------------------------------------------------------


def run_regime_for_comparison(
    regime_id: str,
    *,
    firm_ids: Sequence[str] = _DEFAULT_FIRM_IDS,
    investor_ids: Sequence[str] = _DEFAULT_INVESTOR_IDS,
    bank_ids: Sequence[str] = _DEFAULT_BANK_IDS,
    period_dates: Sequence[str] = _DEFAULT_PERIOD_DATES,
) -> _RegimeRunSnapshot:
    """Run one regime preset on a fresh kernel and extract the
    label snapshot. Read-only against the kernel after the run
    finishes."""
    kernel = _seed_kernel()
    result = run_living_reference_world(
        kernel,
        firm_ids=tuple(firm_ids),
        investor_ids=tuple(investor_ids),
        bank_ids=tuple(bank_ids),
        period_dates=tuple(period_dates),
        market_regime=regime_id,
    )
    return extract_regime_run_snapshot(
        regime_id=regime_id, kernel=kernel, result=result
    )


def build_regime_comparison_report(
    *,
    panel_id: str = "regime_comparison:reference_run:default",
    regime_ids: Iterable[str] = (
        "constructive",
        "constrained",
        "tightening",
    ),
    firm_ids: Sequence[str] = _DEFAULT_FIRM_IDS,
    investor_ids: Sequence[str] = _DEFAULT_INVESTOR_IDS,
    bank_ids: Sequence[str] = _DEFAULT_BANK_IDS,
    period_dates: Sequence[str] = _DEFAULT_PERIOD_DATES,
    metadata: Mapping[str, Any] | None = None,
) -> RegimeComparisonPanel:
    """Run each regime preset on a fresh kernel and build a
    :class:`RegimeComparisonPanel` summarising the v1.16 closed
    loop's behaviour under each preset.

    Same arguments → byte-identical panel.

    The driver does **not** mutate the input arguments,
    **does not** retain references to the per-regime kernels
    after the snapshot is extracted, and **does not** create any
    new economic state.
    """
    snapshots: list[_RegimeRunSnapshot] = []
    for regime_id in regime_ids:
        snapshot = run_regime_for_comparison(
            regime_id,
            firm_ids=firm_ids,
            investor_ids=investor_ids,
            bank_ids=bank_ids,
            period_dates=period_dates,
        )
        snapshots.append(snapshot)
    panels = [
        named_regime_panel_from_snapshot(s) for s in snapshots
    ]
    return build_regime_comparison_panel(
        panel_id=panel_id,
        regime_panels=panels,
        metadata=metadata or {},
    )


def regime_comparison_markdown(
    *,
    panel: RegimeComparisonPanel | None = None,
    panel_id: str = "regime_comparison:reference_run:default",
    regime_ids: Iterable[str] = (
        "constructive",
        "constrained",
        "tightening",
    ),
) -> str:
    """Convenience wrapper. If ``panel`` is supplied, render it;
    otherwise build a default regime comparison panel and render
    it. Returns the deterministic markdown string."""
    if panel is None:
        panel = build_regime_comparison_report(
            panel_id=panel_id,
            regime_ids=regime_ids,
        )
    return render_regime_comparison_markdown(panel)


__all__ = [
    "build_regime_comparison_report",
    "extract_regime_run_snapshot",
    "named_regime_panel_from_snapshot",
    "regime_comparison_markdown",
    "run_regime_for_comparison",
]


# ``timedelta`` is imported above so that callers can synthesise
# their own custom calendar windows; keep it referenced to silence
# linting if the import is otherwise unused.
_ = timedelta
