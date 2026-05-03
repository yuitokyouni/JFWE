# FWE Analyst Workbench — static UI prototype

A single-file static HTML mockup that arranges FWE outputs as an
Excel-like analyst workbench. Open the file directly in a browser
— no backend, no build tools, no external runtime.

The prototype has two states:

1. **Visual** — open the file and the tabs render with embedded
   illustrative example values.
2. **Data-bound** — click **Load sample run** in the top ribbon
   and the Market State / Attention / Firms / Investors / Banks /
   Outputs / Ledger tabs are repopulated from a synthetic JSON
   sample. The Ledger inspector becomes interactive.

Both states are 100% synthetic, jurisdiction-neutral, and
non-binding.

## Files

- `fwe_workbench_mockup.html` — the polished mockup (10 sheet
  tabs: Cover, Settings, Market State, Attention, Firms,
  Investors, Banks, Outputs, Ledger, Appendix).
- `sample_living_world_manifest.json` — canonical synthetic
  sample run. Analysts edit this file when iterating on the
  shape of a fake run. The same JSON is also embedded inline in
  the HTML so the Load button works from `file://` (browsers
  block `fetch()` of local JSON without a server). **Keep the
  two copies in sync.**
- `preview.html` — earlier 7-tab draft kept for reference.

## How to open

From a clone of the repo, just double-click the file or open it
in your browser:

```
japan-financial-world/examples/ui/fwe_workbench_mockup.html
```

No web server is needed. No external CSS, JS, or font CDN is
fetched. Tab switching, sample loading, and the ledger inspector
are all plain vanilla JavaScript.

If you prefer to serve over HTTP (e.g. to test `fetch()` of the
JSON file directly), run `python3 -m http.server` from this
directory and point a browser at the printed URL. Either way,
the **Load sample run** button reads from the inline copy, so
neither path is required for the prototype to function.

## Top-ribbon strip

The status strip in the top ribbon reflects the four-way version
split that the engine actually maintains:

| Slot                    | Current value | Meaning                                                  |
| ----------------------- | ------------- | -------------------------------------------------------- |
| UI prototype            | `v0`          | this static workbench                                    |
| Runtime engine          | `v1.14.1`     | runtime version pinned in the bundled sample manifest    |
| Evidence substrate      | `v1.13.6`     | latest `EvidenceResolver` bucket set                     |
| Frozen attention loop   | `v1.12.last`  | the v1.12 attention-feedback loop pinned for replay      |

The bundled sample manifest captures a snapshot of v1.14.1
(`CorporateFinancingNeedRecord` storage). The latest engine
freeze is **v1.16.last** — the first FWE milestone where the
living reference world has a **closed deterministic endogenous-
market-intent feedback loop**: attention →
`InvestorMarketIntent` (via the v1.16.1 evidence-conditioned
classifier rewired into the orchestrator at v1.16.2) →
`AggregatedMarketInterest` → `IndicativeMarketPressure` →
`CapitalStructureReview` / `CorporateFinancingPath` → next-period
`ActorAttentionState.focus_labels` (via the v1.16.3 deterministic
mapping). Pinned at digest
`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
on the default 4-period fixture. The v1.15.last freeze
(`bd7abdb9a62fb93a1001d3f760b76b3ab4a361313c3af936c8b860f5ab58baf8`)
remains the prior engine freeze and is preserved unchanged. This
UI prototype is intentionally lower-frequency than the engine and
is bumped opportunistically; for the engine narrative see
[`../../docs/v1_16_endogenous_market_intent_feedback_summary.md`](../../docs/v1_16_endogenous_market_intent_feedback_summary.md)
(v1.16),
[`../../docs/v1_15_securities_market_intent_summary.md`](../../docs/v1_15_securities_market_intent_summary.md)
(v1.15) and
[`../../docs/v1_14_corporate_financing_intent_summary.md`](../../docs/v1_14_corporate_financing_intent_summary.md)
(v1.14).

### What the workbench should expose for the v1.16.last loop

The Attention / Investors / Firms / Outputs / Ledger tabs
together carry the v1.16 loop. A v1.17+ workbench polish should
make each of the following first-class views (all of these are
already in the manifest payload — they just need a sheet-level
narrative):

| v1.16 layer                                                   | Surfaced via                                                                                  |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Per-period **`ActorAttentionState.focus_labels`** + weights   | Attention tab: focus-label chips (with v1.16.3 additions `risk` / `financing` / `dilution` / `market_interest` / `information_gap`), per-dimension stale-count heatmap |
| Per-`(investor, security)` **`InvestorMarketIntentRecord`** + classifier audit | Investors tab: market-intent table with `intent_direction_label`, `intensity_label`, `confidence`, and the metadata `classifier_rule_id` / `classifier_status` / `classifier_unresolved_or_missing_count` columns |
| Per-security **`AggregatedMarketInterestRecord`**             | Outputs tab (or new "Securities" tab): venue × security grid with net / liquidity / concentration labels and per-period histogram |
| Per-security **`IndicativeMarketPressureRecord`**             | Outputs tab: pressure card per security with five label fields (`demand_pressure_label` / `liquidity_pressure_label` / `volatility_pressure_label` / `market_access_label` / `financing_relevance_label`) |
| Per-firm **`CorporateFinancingPathRecord`** outcome           | Firms tab: financing-path card with `coherence_label`, `constraint_label`, `next_review_label`, plus citations to that period's pressure ids |
| **Next-period attention widening** (the closed loop)          | Attention tab: a small "what changed because of last period's pressure / path" sub-panel showing the v1.16.3 fresh focus labels and the prior pressure / path ids that triggered them (`source_indicative_market_pressure_ids` / `source_corporate_financing_path_ids`) |

The Ledger tab already supports plain-id click-through; v1.17
should add cross-sheet click-through so an analyst can trace
"why does this investor's focus include `dilution` at period 2"
back to "because period-1 pressure for security X had
`financing_relevance_label = caution_for_dilution`".

**Workbench scope reminder.** The workbench is a *post-hoc
inspector* of a deterministic synthetic run. It is **not** a
trading dashboard, **not** an order management interface, **not**
an investment-recommendation surface, **not** a Japan-specific
view. The v1.16 hard boundary applies bit-for-bit: no order
submission / matching / execution / clearing / settlement / quote
dissemination / bid / ask / price formation / `PriceBook`
mutation / target prices / expected returns / recommendations /
portfolio allocations / financing approvals / loan approvals /
real data / Japan calibration / LLM execution / stochastic
behaviour probabilities / learned models.

### v1.17.0 design pointer (forward look)

v1.17 is the **presentation and inspection layer** designed
on top of the v1.16 closed loop. The full design lives in
[`../../docs/v1_17_ui_report_temporal_display_design.md`](../../docs/v1_17_ui_report_temporal_display_design.md).
v1.17.0 is **docs-only** (no executable code, no tests, no
new ledger event types, no behavior change); the
`living_world_digest` and pytest count are unchanged from
v1.16.last.

The v1.17 sequence introduces three time concepts that must
be kept strictly separate:

| Concept                | Frequency                | What it represents                                    |
| ---------------------- | ------------------------ | ----------------------------------------------------- |
| `simulation_period`    | Quarterly (default)      | The actual living-world update tick (economic state). |
| `reporting_calendar`   | Monthly / daily-like     | A display-only axis used for inspection.              |
| `display_series`       | Same axis as `reporting_calendar` | Synthetic UI series derived from existing labels and records. |

The `simulation_period` is the **only** economic clock. The
monthly / daily-like axis is a **reading aid**, not a
higher-frequency simulation. A reviewer who asks *"does FWE
run daily?"* must be able to read off *"no — the daily-like
axis is a display rendering of the quarterly economic clock"*
from any v1.17.4 page footer.

The v1.17 sequence will land in this directory in five small
steps:

| Milestone   | What                                                                                                       |
| ----------- | ---------------------------------------------------------------------------------------------------------- |
| v1.17.0     | Design (this pointer + the design doc above). **Shipped (docs-only).**                                      |
| v1.17.1     | `ReferenceTimelineSeries` / `SyntheticDisplayPath` / `ReportingCalendar` + monthly / daily-like expansion helper. |
| v1.17.2     | `RegimeComparisonPanel` + side-by-side markdown panels for the v1.11.2 regime presets.                      |
| v1.17.3     | `EventAnnotationRecord` + `CausalTimelineAnnotation` walking the v1.16 closed-loop citations.               |
| v1.17.4     | UI workbench polish — wires v1.17.1 / v1.17.2 / v1.17.3 outputs into this mockup; adds Attention "what changed" diff, cross-tab click-through. |
| v1.17.last  | Inspection-layer freeze (docs-only).                                                                        |

The hard naming boundary is binding from v1.17.0. **Allowed**
display kinds: `synthetic_display_index` / `reference_timeline` /
`indicative_pressure_path` / `event_annotation` /
`causal_timeline` / `regime_comparison` / `attention_focus_density` /
`display_series` / `reporting_calendar`. **Forbidden** (will be
test-pinned at v1.17.1+): `market_price` / `predicted_index` /
`predicted_path` / `expected_return` / `target_price` /
`forecast_path` / `forecast_index` / `real_price_series` /
`actual_price` / `quoted_price` / `last_trade` / `nav` /
`index_value` / `benchmark_value` / `valuation_target`.

These advance independently. The prototype version is
intentionally lower than the runtime version because the
prototype shows engine behaviour at a snapshot — not a 1:1
mirror of every code milestone.

## What each tab shows

Each tab is a *visual placeholder* for one analyst-facing surface
of the engine:

| Sheet         | Static content                                                                                            | Data-bound after Load sample run                  |
| ------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| Cover         | title, author, build line, hard-boundary footer                                                          | unchanged                                         |
| Settings      | run digest / seed / periods / firms / investors / banks; market regime selector mock; strategy modules    | unchanged (regime selector is interactive)        |
| Market State  | period-by-period regime labels, state lineage                                                             | KPI cards + quarterly + lineage                   |
| Attention     | per-actor `ActorAttentionState`, selected evidence, memory selection, budget / decay / crowding / saturation | three actor cards + discipline table              |
| Firms         | firm latent state, corporate financing need (v1.14.1) placeholder, strategic response candidates          | latent + financing need + strategic response      |
| Investors     | valuation refresh lite, intent signal, stewardship themes, dialogue / escalation candidates               | all four tables                                   |
| Banks         | bank credit review lite, interbank liquidity state (v1.13.5), v1.13 substrate map                         | credit review + interbank liquidity + substrate    |
| Outputs       | wide hero index/event timeline, KPI strip, LLM-readable causal summary table, stylized facts (secondary)  | index path + baseline drawn from points; event annotations + chips; KPIs; causal summary |
| Ledger        | record stream, selected record, parent evidence, downstream records, digest / manifest area              | record stream is clickable — selecting a row updates the three inspector panels |
| Appendix      | version boundary, hard-boundary statement, status of this UI                                              | unchanged                                         |

## How the data binding works

The HTML embeds the sample JSON inline:

```html
<script type="application/json" id="fwe-sample-manifest">
  { ... }
</script>
```

The `Load sample run` button parses this with `JSON.parse(node.textContent)`
and rewrites table bodies, KPI cards, the index-path SVG, and
the ledger inspector. There is no `fetch()`, no XHR, and no
network I/O — deliberately, so the prototype works under
`file://` without the browser blocking it.

`sample_living_world_manifest.json` is the **canonical** copy.
When you edit it, copy the new JSON into the inline
`<script type="application/json">` block as well. (This
duplication is the price of zero-server, zero-build operation.)

### JSON shape (top-level keys)

```
manifest          – schema, version strip, digest, period, counts
market_state      – kpis[], quarterly[], lineage[]
attention         – actors[], discipline[]
firms             – latent_state[], financing_need[], strategic_response[]
investors         – valuation[], intent[], stewardship[], dialogue[]
banks             – credit_review[], interbank_liquidity[], v1_13_substrate[]
outputs           – index_path[], fundamental_baseline[], events[], kpis[], causal_summary[]
ledger            – stream_period, records[]
                       └─ each record has: record_id, seq, type, source, target, status,
                          selected[][], parent_evidence[], downstream[]
```

The shape is illustrative — not a stable contract. The real
engine emits a `living_world_manifest.v1` JSON; this file is
hand-shaped to be ergonomic for the workbench layout, not a 1:1
copy of that manifest.

## What it is **not**

This is a static HTML prototype. It is **not**:

- a backend or live demo (no fetch, no API, no server)
- a React / build-tool app (no node, no bundler, no transpile)
- production UI
- a price predictor, market simulator, or trading interface
- a calibrated probability or forecast tool
- a real-data viewer
- a Japan calibration

Every number, label, identifier, and digest in the file is
illustrative and deterministic. Real engine output is the source
of truth (see `examples/reference_world/run_living_reference_world.py`
and the `living_world_manifest.v1` JSON it emits).

## Strategy / module section

The Settings tab lists candidate strategy adapters
(Brock-Hommes, Lux-Marchesi, Minority Game, Speculation Game,
FCN / LOB) as **interchangeable experimental modules — not all
active at once**. None ships as live behavior in the current
public prototype. Selecting one would not enable trading,
ordering, or price formation.

## Hard boundary

No price prediction. No price formation. No trading. No order
matching. No lending decisions. No portfolio allocation. No
investment advice. No real data. No Japan calibration. No LLM
execution. No behavior probabilities.
