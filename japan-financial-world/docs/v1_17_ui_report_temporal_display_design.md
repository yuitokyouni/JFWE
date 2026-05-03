# v1.17.0 UI / Report / Temporal Display — Design Note

> **Status: docs-only.** v1.17.0 ships **no executable code, no
> new tests, no new ledger event types, no new behavior**. The
> living reference world's `living_world_digest`, per-period
> record count (`108 / 110`), per-run window (`[432, 480]`),
> default 4-period sweep total (`460 records`), and pytest count
> (`4033 / 4033`) are **unchanged from v1.16.last**. v1.17.0 is
> the design pointer for the v1.17 sequence; subsequent
> milestones (v1.17.1 → v1.17.last) will land code under this
> design.

## Purpose

v1.16.last froze the **first closed endogenous-market-intent
feedback loop** in public FWE: attention → market intent →
aggregated interest → indicative pressure → financing review →
next-period attention. The loop is deterministic, replayable,
and bounded, but — by the user's own audit — **hard to
inspect**. The current UI prototype
([`examples/ui/fwe_workbench_mockup.html`](../examples/ui/fwe_workbench_mockup.html))
is visually decent but does not yet clearly answer:

1. **What happened?** — at this period, in this regime.
2. **Which actor saw what?** — what evidence reached which
   attention state.
3. **Which evidence changed?** — across periods, across
   regimes.
4. **Which intent / review / pressure changed?** — and why,
   citing which prior-period record.
5. **What changed in the next period?** — closing the loop's
   visual representation back onto the next-period attention
   widening.

v1.17 is a **presentation and inspection layer**. It does not
add new economic behavior. It does not change the v1.16 loop's
output bytes; the integration-test `living_world_digest` stays
**`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
across the v1.17.0 → v1.17.last sequence as long as no v1.17.x
milestone introduces a new record on the per-period sweep.

This is **not** a price-formation layer. It is **not** a
forecast layer. It is **not** a trading dashboard. It is **not**
an investment-recommendation surface. It is **not** a real-data
view. It is **not** a Japan calibration. The v1.16 hard
boundary applies bit-for-bit at every v1.17 milestone.

## Two-line success condition

> A reviewer who has not read this codebase can open the v1.17
> workbench, click through three regimes, and explain — in
> their own words — *what happened*, *which actor saw what*,
> *which evidence changed*, and *what changed in the next
> period* by following plain-id citations from the rendered
> UI. The integration-test `living_world_digest` is unchanged.

If a reviewer cannot do this in under fifteen minutes per
regime, v1.17 has failed. If a reviewer concludes that FWE
"predicts the market", "recommends investments", "produces
prices", or "is calibrated to Japan", v1.17 has also failed —
the layer's hard naming boundary (§5) is the binding control on
that risk.

## 1. Three concepts kept strictly separate

v1.17 introduces **three time concepts** that must not be
collapsed:

| Concept                | Frequency                | What it represents                                                                                                  |
| ---------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `simulation_period`    | Quarterly (default)      | The actual living-world update tick. Each period emits one full pass through the v1.16 loop. **Economic state.**     |
| `reporting_calendar`   | Monthly / daily-like     | A display-only axis used for inspection. **No new records, no new decisions, no new evidence.**                      |
| `display_series`       | Same axis as `reporting_calendar` | A synthetic UI series derived deterministically from existing labels and records — never a real price or forecast. |

The **simulation_period is the only economic clock**. The
`reporting_calendar` exists purely so a user can scrub a
finer-grained slider and see the same simulation-period output
spread out visually. The `display_series` is a deterministic
function of cited records — it is a **rendering**, not a
measurement.

A reviewer should be able to answer "is this a real-time
simulation?" with: *"No. The system runs quarterly. The monthly
/ daily-like axis is a display-only reading aid."*

## 2. Display-layer object vocabulary

v1.17.x will introduce the following **display-only** objects.
None of them is a kernel record; none of them is registered with
the ledger; none of them participates in evidence resolution.

### 2.1 `ReferenceTimelineSeries`

A small immutable dataclass naming a **synthetic display series**
on a `reporting_calendar` axis:

```
ReferenceTimelineSeries
  series_id: str                               # e.g. "indicative_pressure_path:firm:reference_manufacturer_a"
  series_kind: str                             # closed-set: "indicative_pressure_path" | "reference_index_proxy" | "attention_focus_density" | ...
  reporting_calendar_id: str                   # which calendar / axis
  source_record_ids: tuple[str, ...]           # plain-id cross-references to v1.x records
  values: tuple[ReferenceTimelinePoint, ...]   # each point names a date label and a synthetic scalar in [0, 1]
  visibility: str                              # "internal_only" by default
  metadata: Mapping[str, Any]                  # synthetic, never real prices / returns
```

`ReferenceTimelinePoint.value` is a synthetic ordering scalar in
`[0.0, 1.0]` — **never a price, return, market value, NAV, or
benchmark level**. A test at v1.17.1 will scan series payloads
for forbidden keys.

### 2.2 `SyntheticDisplayPath`

A typed wrapper over `ReferenceTimelineSeries` whose
`series_kind` is one of the allowed display kinds (§4) and whose
`metadata["display_only"] = True`. The type tag is the binding
boundary against accidental promotion from "display" to
"economic state".

### 2.3 `EventAnnotationRecord`

An annotation rendered **below** a timeline:

```
EventAnnotationRecord
  annotation_id: str
  reporting_calendar_id: str
  date_label: str                              # ISO display label
  annotation_kind: str                         # closed-set: "regime_change" | "evidence_arrival" | "attention_widening" | "review_recorded" | "pressure_change" | ...
  cited_record_ids: tuple[str, ...]            # the v1.x records that caused the annotation
  display_text: str                            # short, synthetic, audit-grade
  visibility: str                              # "internal_only" by default
  metadata: Mapping[str, Any]
```

The annotation's `display_text` is **always** a description of
*what was recorded*, never *what was predicted* or *what should
happen*. Closed-set `annotation_kind` ensures a future v1.18+
scenario library can compose with v1.17 without needing to
extend the vocabulary unsafely.

### 2.4 `CausalTimelineAnnotation`

A pair of `EventAnnotationRecord`s linked by a plain-id arrow:

```
CausalTimelineAnnotation
  causal_id: str
  cause_annotation_id: str
  effect_annotation_id: str
  cited_record_ids: tuple[str, ...]            # the records that justify the link
  link_kind: str                               # closed-set: "evidence_to_intent" | "pressure_to_attention" | "review_to_path" | ...
  display_text: str                            # short rationale, no probability claim
  visibility: str                              # "internal_only" by default
  metadata: Mapping[str, Any]
```

`CausalTimelineAnnotation` is the **rendering** of a single
plain-id citation that already exists in the kernel — it does
not invent a new edge. A test at v1.17.3 will pin that every
emitted annotation cites at least one record id that is
reachable from the kernel by `get_*` lookup.

### 2.5 `RegimeComparisonPanel`

A side-by-side display object that snapshots **two or three
named regimes** for the same default fixture:

```
RegimeComparisonPanel
  panel_id: str
  reporting_calendar_id: str
  regime_panels: tuple[NamedRegimePanel, ...]  # each panel names regime_id, source manifest digest, and selected display series
  comparison_axes: tuple[str, ...]             # closed-set: "attention_focus" | "market_intent_direction" | "indicative_pressure" | "financing_constraint" | ...
  metadata: Mapping[str, Any]
```

`NamedRegimePanel.regime_id` reuses the v1.11.2 regime preset
ids (`constructive` / `selective` / `constrained` /
`tightening`). The display layer never invents a regime —
every panel's data comes from a real
`run_living_reference_world(...)` call against a v1.11.2
preset.

## 3. Why these are not kernel records

- They are **renderings of existing records**, not new
  economic facts.
- They are **idempotent on inputs** — same kernel state →
  byte-identical display objects.
- They are **emitted only when the report / UI asks for them** —
  the per-period sweep does not create them.
- They live in a separate module (`world/display.py` or
  `world/reference_display.py` — to be decided at v1.17.1) that
  imports the **read-only** book interface (`get_*`, `list_*`,
  `snapshot`) and **never** the `add_*` methods.

A trip-wire test at v1.17.1 will pin that the display module
holds no reference to any `kernel.<book>.add_*`, `Ledger.add_*`,
or `WorldKernel`-mutating call.

## 4. Hard naming boundary

The display layer must use **only** the following safe names.
Tests at every v1.17.x milestone scan module text, payload
strings, and the example workbench mockup HTML for the forbidden
list.

### Allowed

- `synthetic_display_index`
- `reference_timeline`
- `indicative_pressure_path`
- `event_annotation`
- `causal_timeline`
- `regime_comparison`
- `attention_focus_density`
- `display_series`
- `reporting_calendar`

### Forbidden (binding boundary)

- `market_price`
- `predicted_index`
- `predicted_path`
- `expected_return`
- `target_price`
- `forecast_path`
- `forecast_index`
- `real_price_series`
- `actual_price`
- `quoted_price`
- `last_trade`
- `nav`
- `index_value`
- `benchmark_value`
- `valuation_target`

The naming boundary is closed-set. v1.17.0 pins it here;
v1.17.1 → v1.17.last enforces it via a test.

The forbidden list is **disjoint** from the v1.16 forbidden
trade-instruction verbs (`buy` / `sell` / `order` / etc.) by
construction — neither set leaks into the other.

## 5. Per-milestone roadmap inside v1.17

| Milestone   | What                                                                                                                                                                   | Status                  |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| **v1.17.0** | **UI / Report / Temporal Display design (this document)** — three-concept separation; safe object vocabulary; hard naming boundary; per-milestone roadmap; success condition | **Shipped (docs-only)** |
| v1.17.1     | `world/display.py` (or equivalent) — `ReferenceTimelineSeries`, `SyntheticDisplayPath`, `ReportingCalendar`; deterministic helper that expands a quarterly run onto a monthly / daily-like axis (display-only); unit tests for closed-set kinds, immutability, no-runtime-book-mutation, jurisdiction-neutral scan, forbidden-name scan | Planned                 |
| v1.17.2     | `RegimeComparisonPanel` and a small markdown-report extension that renders side-by-side panels for the v1.11.2 regime presets (`constructive` / `selective` / `constrained` / `tightening`); attention focus / market intent / pressure / financing constraint compared per period | Planned                 |
| v1.17.3     | `EventAnnotationRecord` + `CausalTimelineAnnotation`; deterministic helper that walks the v1.16 closed loop's plain-id citations and emits annotations + causal links; unit tests pin that every annotation cites a reachable record | Planned                 |
| v1.17.4     | UI workbench polish — wire the v1.17.1 / v1.17.2 / v1.17.3 outputs into [`examples/ui/fwe_workbench_mockup.html`](../examples/ui/fwe_workbench_mockup.html); add the §6 page-level views; cross-tab click-through; "what changed" diff strip on Attention; jurisdiction-neutral scan over the rendered HTML | Planned                 |
| v1.17.last  | Endogenous-market-intent feedback loop **inspection-layer freeze** (docs-only): single-page reader-facing summary, §119 in `world_model.md`, `RELEASE_CHECKLIST.md` snapshot, `performance_boundary.md` update, `test_inventory.md` header note, `examples/ui/README.md` v1.17 sub-section | Planned                 |

The v1.17 sequence preserves the v1.x storage-first / labels-only
discipline. Each milestone ships one small deterministic
addition, passes a closed-set + safe-label test, passes the
forbidden-name scan, and integrates into the workbench at
v1.17.4. The v1.17.0 design itself ships nothing executable —
`living_world_digest` is unchanged from v1.16.last
(`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`).

## 6. Page-level target — what every v1.17.4 page must answer

At v1.17.4 the workbench should answer the five inspection
questions (§Purpose) on dedicated pages.

### 6.1 Attention page

For each `(actor, period)` cell:

- **Previous focus** — the prior-period
  `ActorAttentionStateRecord.focus_labels` rendered as chips.
- **New focus** — the current-period focus chips.
- **Dropped focus** — labels in *previous* but not in *new*.
- **Reinforced focus** — labels in *both*, with the
  `focus_weights` reset to 1.0 in this period.
- **Source of change** — for every fresh focus label, the
  citation that introduced it: market pressure
  (`source_indicative_market_pressure_ids` from v1.16.3), or
  financing path (`source_corporate_financing_path_ids`), or
  credit review signal (v1.12.x).

A "what changed" diff strip across the period boundary is the
canonical view; the underlying data already lives in the
`AttentionFeedbackRecord` and the prior-period
`ActorAttentionStateRecord` — v1.17.4 only renders it.

### 6.2 Outputs page

- **Wide synthetic display index** — one
  `SyntheticDisplayPath` per security id, rendered as a wide
  hero chart with a small monthly / daily-like axis. The path
  is the v1.17.1 expansion of the per-period
  `IndicativeMarketPressureRecord` chain — deterministic, not
  a forecast, not a price.
- **Indicative pressure path** — one
  `SyntheticDisplayPath` per security id whose value at each
  display tick is a closed-set ordinal of the cited
  pressure's `market_access_label` /
  `liquidity_pressure_label` / `financing_relevance_label`.
- **Event annotations** — `EventAnnotationRecord`s rendered
  as ticks below the timeline. Click → highlight the
  underlying record.
- **Causal summary table** — for the selected period, a small
  table walking attention → intent → pressure →
  review / path → next-period attention with one cited record
  id per arrow.

### 6.3 Ledger page

- **Selected record** — payload of the chosen ledger row.
- **Parent evidence** — every plain-id reference reachable by
  `get_*` lookup on the kernel.
- **Downstream records** — every record whose
  `source_*_ids` / `evidence_*_ids` cites the selected one.
  Walks the v1.16.3 attention-feedback citations explicitly so
  a reviewer can trace pressure → next-period attention without
  reading the v1.16 design doc.
- **Digest / manifest** — pinned `living_world_digest`,
  `run_id`, `record_count`, `period_count`. Read from the
  v1.9.1 manifest only; never recomputed from a synthetic
  source.

### 6.4 Regime Comparison page (v1.17.2)

A `RegimeComparisonPanel` rendering two or three named regimes
side by side. Compared axes:

- **Attention focus** — overlapping chip-frequency histograms
  per regime per period.
- **Market intent direction** — per-regime histogram of
  `intent_direction_label` (the v1.16.1 classifier's output).
- **Indicative pressure** — per-regime histogram of
  `market_access_label` / `liquidity_pressure_label`.
- **Financing constraints** — per-regime distribution of
  `CapitalStructureReviewCandidate.constraint_label` and
  `CorporateFinancingPathRecord.constraint_label`.

Click → cross-tab navigate to the source records in the
selected regime's manifest.

## 7. Monthly / daily-like display expansion

The orchestrator runs **quarterly**. v1.17 must show the same
output on a **monthly** or **daily-like** axis without
introducing any new economic decision.

The expansion rule is **purely visual**:

1. Each `simulation_period` (quarter) is mapped to a contiguous
   block on the `reporting_calendar` (e.g. ~13 weeks for
   monthly, ~63 weekdays for daily-like, with an integer step
   per quarter that the helper exposes deterministically).
2. The display value at each tick inside the block is a
   **deterministic interpolation** of two adjacent quarterly
   values *that already exist in the kernel records*. The
   interpolation is pure (no randomness, no exponential
   smoothing fit to anything) and uses one of the closed-set
   methods documented at v1.17.1: `step` / `linear` /
   `cumulative_to_label_ordinal`.
3. The expansion **never creates new evidence**, **never opens
   a new ledger record type**, and **never mutates the
   `PriceBook`**.

A test at v1.17.1 will pin that running the expansion on the
default fixture leaves the kernel byte-identical
(`kernel.snapshot()` before == after) and that the
`living_world_digest` does not move.

The expansion is a **reading aid**, not a higher-frequency
simulation. A reviewer who asks "does FWE run daily?" must be
able to read off the answer "no — the daily-like axis is a
display rendering of the quarterly economic clock" from any
v1.17.4 page footer.

## 8. Boundary statement

v1.17 improves **inspectability**. It does not improve
**predictive validity**. It does not make FWE a market simulator.
It does not add trading or price formation.

Specifically, v1.17 does **not**:

- create any order, trade, quote, bid, ask, fill, match,
  execution, clearing, or settlement record;
- mutate the `PriceBook`;
- introduce any market price, predicted index, expected return,
  target price, forecast path, or real price series;
- introduce any new daily / monthly economic decision — the
  finer-grained axis is **display-only**;
- ingest any real-data feed (real exchange tape, real audit
  filings, real broker prints, real macro release stream);
- introduce any Japan-specific calibration, jurisdiction-bound
  identifier, or named real-world entity in any module,
  fixture, test, or rendered view;
- run any LLM, calibrated probability model, learned attention
  head, or stochastic behaviour rule;
- produce any investment recommendation, portfolio allocation,
  rating, or risk metric.

The v1.16 hard boundary anti-claims (no order submission, no
order book, no matching, no execution, no clearing, no
settlement, no quote dissemination, no price formation, no
target price, no expected return, no recommendation, no
portfolio allocation, no financing execution, no loan
approval, no underwriting, no real data, no Japan calibration,
no LLM execution, no stochastic behaviour probabilities, no
learned model) are preserved bit-for-bit through v1.17.0 →
v1.17.last.

## 9. Performance boundary at v1.17.0

v1.17.0 is docs-only. **Nothing changes**:

- per-period record count: **108 / 110** (unchanged from
  v1.16.last);
- per-run window: **`[432, 480]`** (unchanged);
- default 4-period sweep total: **460 records** (unchanged);
- integration-test `living_world_digest`:
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
  (unchanged);
- pytest count: **4033 / 4033** passing (unchanged).

v1.17.1 → v1.17.4 are display-layer additions; their tests will
**not** change `living_world_digest` because the display layer
runs *after* the per-period sweep and never writes to any kernel
book. v1.17.1 will pin this with a dedicated
`test_v1_17_1_display_helper_does_not_mutate_kernel`-shaped
trip-wire.

## 10. What v1.18+ does next

v1.17.last freezes the inspection layer. The expected next
roadmap candidates remain (from the v1.16.last summary):

- **v1.18** — scenario library / exogenous event templates.
  Adds named, deterministic, reproducible scenario templates
  (e.g. `tightening_credit`, `equity_correction`,
  `liquidity_event`, `dialogue_breakdown`) that compose with
  the existing `--regime` presets and the v1.17.2
  `RegimeComparisonPanel` — still no real-data, no calibration.
- **v2.0** — Japan public calibration in private JFWE only.
  Real-venue / real-issuer / real-regulator calibration moves
  to private JFWE only. Public FWE remains jurisdiction-neutral
  and synthetic.
- **Future price formation.** Out of scope until v1.17 / v1.18
  make the loop's causal structure operationally legible to a
  reviewer who has not read this codebase. Adding price
  formation on top of an opaque layer would defeat the
  auditability goal of the v1.16 freeze; v1.17 is the
  prerequisite for ever revisiting that gate.

The v1.17 chain stays display-only and label-only forever.
Future milestones may *cite* the v1.17 display objects
(plain-id cross-references, additional rendering kinds), but
they may **never** mutate the v1.17 vocabulary, replace the
deterministic expansion helpers with stochastic ones, or
introduce execution paths on top of the display layer.
