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

### Top-ribbon buttons (v1.17.4 + post-v1.17.last UX pass)

- **Load sample run** — parses the inline JSON manifest and fills
  the data-bound tables.
- **Run mock** — reads the regime pill currently selected on the
  Inputs sheet (`constructive` / `mixed` / `constrained` /
  `tightening`) and updates the Overview executive summary, the
  Timeline KPIs, the Attention diff strip, the top-ribbon digest,
  and the Settings active-regime cell from a deterministic in-page
  `SAMPLE_RUNS` fixture. **The Python engine is not invoked.** The
  status strip updates to `mock UI run · <regime> · static fixture
  · no engine execution`. Same regime → same UI state across two
  clicks.
  - **No-jump discipline.** Run mock captures
    `(scrollX, scrollY, activeSheetId)` before mutating any slot
    and asserts they are unchanged afterward. Run mock never
    calls `scrollIntoView()`, never calls `.focus()`, never
    mutates `location.hash`, never toggles classes outside
    well-scoped slots, and never changes root font-size /
    transform / zoom. Card heights have stable `min-height` so
    longer fixture strings cannot reflow the page.
- **Validate** — runs strict client-side checks: inline JSON
  parses; tab/sheet count match; every tab points to a real sheet;
  every sheet has a tab; no duplicates; all 10 required sheet
  ids present; ledger records table present; regime-compare card
  present; **all Overview executive-summary slots present**
  (`ov-main-message` / `ov-active-regime` / `ov-digest` /
  `ov-drivers` / `ov-responses` / `ov-what-changed` /
  `ov-endpoint-bullet`); **evidence-trail CTA present**;
  **Run-mock-no-jump invariant** (dry-runs `runMock()` and
  asserts active sheet id + scroll position are unchanged).
  Status strip updates to `validation passed · static UI` or
  names the first failure.
- **Compare Regimes** — activates the dedicated Regime Compare
  tab and flashes the comparison card. (No scroll behavior on
  the home tab; the tab switch handles its own activation.)
- **Export HTML** — non-destructive. Updates the status strip to
  `export not implemented in static prototype · use browser Save
  Page / Print`. There is no file-system API.

### Overview = executive summary first, evidence second

The Overview sheet leads with five reader-facing blocks before
the closed-loop diagram is even in view:

1. **Main message** — one-sentence summary of the regime's
   dominant implication.
2. **Top 3 drivers · why it happened** — three driver cards
   (label · source type · affected actors · downstream effect).
3. **Top 3 actor responses · who reacted** — Investors / Banks
   / Firms response cards.
4. **What changed next** — three-to-four bullets describing
   period-N+1 consequences.
5. **Evidence trail CTA** — `See Ledger` button that drills into
   the audit surface; the Overview is summary-first, evidence-
   second by design.

The closed-loop SVG diagram and the compact KPI cards are
still rendered, but **demoted below** the executive summary so
the first thing a reader sees is the "so what", not the
implementation map.

The status strip below the load-status line always reads
`static fixture only · no backend execution` so the
no-engine-execution discipline is visible at a glance.

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

### v1.17.last freeze

The v1.17 sequence is now frozen — the inspection layer is
complete. v1.17.last is **docs-only** on top of the v1.17.0 →
v1.17.4 code freezes. The single-page reader-facing summary is
[`../../docs/v1_17_inspection_layer_summary.md`](../../docs/v1_17_inspection_layer_summary.md).
The integration-test `living_world_digest` is unchanged from
v1.16.last at
**`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
across the entire v1.17 sequence; pytest count is **4165 / 4165**.

What this means for the static workbench specifically:

- The bottom-tab ↔ sheet article mapping is a **strict 1:1
  bijection** — 10 ↔ 10, no orphans, no duplicates. The in-page
  `Validate` button enforces the bijection at runtime.
- `Run mock` is **fixture switching**, not engine execution.
  Same regime selection → byte-identical UI state.
- `Compare Regimes` is **static / display-report navigation** —
  it activates the Regime Compare tab and flashes the comparison
  card; the displayed digests / histograms / causal arrows come
  from the inline `SAMPLE_RUNS` fixture and the inline JSON
  manifest, never from a live engine run.
- The sample manifest is explicitly tagged `digest_kind:
  sample_fixture` / `fixture_kind: sample_fixture` / `fixture_note:
  …`. The displayed digest, per-period count, and per-run
  window are sample fixture, not live output. The live v1.16.last
  runtime emits 108 / 110 records per period and a `[432, 480]`
  per-run window.
- A constant `static fixture only · no backend execution`
  sub-status is permanently visible in the top-ribbon so the
  no-engine-execution discipline is on screen at a glance.

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

## What each tab shows (v1.17.4 redesign)

The bottom-tab strip reorganises the workbench around the v1.16
closed loop so a first-time reader can inspect *what happened*,
*why*, *who reacted*, and *what changed next* without reading the
ledger line by line. Ten tabs, none of which executes the engine:

| Sheet           | Purpose                                                                                                                                  |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Cover           | title, author, build line, hard-boundary footer.                                                                                         |
| Inputs          | run configuration: regime selector, sample-fixture status, periods, reporting calendar, display frequency, actors, digest. *Strategy / behavior modules* live in a default-collapsed `<details>`. |
| Overview        | one-screen closed-loop view — small SVG diagram (attention → market intent → aggregated interest → indicative pressure → financing path → next-period attention) plus six compact KPI cards (active regime / top event / top market pressure / top financing constraint / top attention shift / display path endpoint) and a digest + fixture-status pair. |
| Timeline        | renamed from Outputs. Wide synthetic display path on a one-year window, event-annotation ticks, KPI row, LLM-readable causal summary table, and the secondary stylized-facts diagnostic table. The chart now carries a *Display-only. Not a price. Not a forecast. Not real market data.* banner under the SVG. |
| Regime Compare  | side-by-side panel of v1.11.2 regime presets (constructive / mixed / constrained / tightening) with the v1.17.3 **market environment subfields** row that surfaces the difference between regimes whose top-level histograms collide. |
| Attention       | starts with a v1.17.4 **diff strip** (Previous focus / Trigger / New focus / Dropped / Reinforced / Why) at the top so a reader sees *what changed* before scrolling into the per-actor cards and the v1.12.9 budget / decay / crowding / saturation table. |
| Market Intent   | the v1.15 / v1.16 chain — three tables: Investor market intent (per investor × security, with v1.16.1 classifier rule_id and confidence), Aggregated market interest (per venue × security, v1.15.3), Indicative market pressure (per security, v1.15.4). Boundary callout pinned at top. |
| Financing       | the v1.14 / v1.15.6 chain — three tables: Financing path summary (per firm), Funding option candidates (candidate language only — bank / bond / internal cash / asset sale), Capital structure review (with v1.15.6 `source_indicative_market_pressure_ids` citation). Boundary callout pinned at top. |
| Ledger          | record stream + selected record + parent evidence + downstream records inspector. Click any row to update the three inspector panels.                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Appendix        | version boundary, hard-boundary anti-claim list, **v1.16 / v1.17 milestone trail** (v1.16.last → v1.17.4), and the status-of-this-UI table.                                                                                                                                                                                                                                                                                                                                                                                                                                          |

The folded-out tabs (Market State, Firms, Investors, Banks, raw
Outputs) are no longer reachable from the bottom strip but their
underlying sample fixture survives as JSON (`market_state` /
`firms` / `investors` / `banks` / `outputs` keys) — the new tabs
re-render the same data from a closed-loop perspective. None of
the v1.17.4 redesign touches engine code, the `living_world_digest`,
or the test count.

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

## v1.20.4 forward pointer — `scenario_monthly_reference_universe` CLI export (shipped, UI rendering deferred)

v1.20.4 ships the CLI exporter for the v1.20.3 opt-in profile
`scenario_monthly_reference_universe` (see
[`../reference_world/README.md`](../reference_world/README.md)
and the v1.20.4 section there for the full bundle layout).
The new bundle carries three v1.20.x-specific sections:

- **`metadata.reference_universe`** — universe profile id, 11
  sector ids / labels (all carrying the `_like` suffix), 11
  firm profile ids / firm ids, and a per-sector sensitivity
  summary on the v1.20.0 six-dimension five-rung closed set.
- **`scenario_trace`** — scheduled-application + applied-
  application + emitted context-shift ids; merged context-
  surface labels (`market_environment` +
  `financing_review_surface`) and shift-direction labels
  (`tighten`); per-application **`affected_sector_ids` (11)**
  and **`affected_firm_profile_ids` (11)** so a downstream
  consumer can render per-sector / per-firm impact without
  recomputing the universe.
- **`market_intent`** + **`financing`** — compact label-only
  histograms with closed-loop cardinality counts.

The static workbench (this folder) **does not yet render** the
new bundle. v1.20.4 is **CLI-only**: the v1.19.4 file-input
loader does not list `scenario_monthly_reference_universe` in
`BUNDLE_EXECUTABLE_PROFILES` yet, so loading a v1.20.4 bundle
into this UI surfaces a generic "is not a recognised v1.19.x
run profile" status. The v1.20.5 milestone will:

- add `scenario_monthly_reference_universe` to
  `BUNDLE_EXECUTABLE_PROFILES`;
- render the universe view / sector heatmap / monthly
  timeline / sector comparison surfaces described in the
  v1.20.0 forward pointer below;
- extend the in-page `Validate` audit checks to pin the new
  surfaces.

Until v1.20.5 lands, the canonical inspection path for
`scenario_monthly_reference_universe` bundles is **CLI ->
local JSON file -> manual inspection** (e.g. `jq` /
`python -c 'import json; …'`). The `quarterly_default` and
`monthly_reference` browser-side rendering paths are unchanged.

## v1.20.0 forward pointer — Monthly Scenario Reference Universe design

The next planned milestone, **v1.20.0** (docs-only — see
[`../../docs/v1_20_monthly_scenario_reference_universe_design.md`](../../docs/v1_20_monthly_scenario_reference_universe_design.md)),
is a **realism / granularity** layer that introduces a new
opt-in profile **`scenario_monthly_reference_universe`** —
combining the v1.19.3 12-month cadence with a generic 11-sector
/ 11-firm synthetic universe and the v1.18.2 scenario chain.

By the end of the v1.20 sequence the static workbench (this
folder) will gain four new surfaces (v1.20.5):

- a **universe view** — 11-sector grid, 11-firm grid, sector
  sensitivity heatmap, selected-scenario impact by sector;
- a **monthly timeline** — 12 months, information arrivals,
  scenario application month callout, context shifts,
  attention / pressure / financing deltas;
- a **sector comparison** — impacted-sector ranking,
  financing-pressure firm ranking, market-intent histogram,
  bank-watch-label histogram;
- an always-visible **boundary statement** — *synthetic
  reference universe; not real companies; not real data; not
  investment advice; not Japan calibration*.

The v1.19.4 file-input loader carries forward verbatim. The
new bundle profile (`scenario_monthly_reference_universe`)
will be added to `BUNDLE_EXECUTABLE_PROFILES`. **Read-only
static viewer** — no engine execution from the browser, no
backend, no fetch / XHR, no file-system write. The `_like`
suffix on every sector label means the rendered view contains
**no real company names, no real sector index membership, no
licensed taxonomy dependency** — and the v1.19.4 boundary
checks already in `Validate` will be extended to pin the
absence of bare `GICS` / `MSCI` / `S&P` / `FactSet` /
`Bloomberg` / `Refinitiv` / `TOPIX` / `Nikkei` / `JPX` tokens
in the rendered text.

The canonical `quarterly_default` and `monthly_reference`
digests stay byte-identical unless the new profile is
explicitly invoked.

## v1.19.last — Local Run Bundle and Monthly Reference freeze (shipped, docs-only)

v1.19.last closes the v1.19 sequence as the **first FWE
milestone where a user can generate deterministic local run
bundles from CLI and inspect them in the static workbench,
including monthly_reference runs**. The static UI loader
shipped at v1.19.4 (described below) is the v1.19 contribution
to that surface; the v1.19.last freeze is docs-only and ships
no UI changes beyond cross-links into the single-page summary
at
[`../../docs/v1_19_local_run_bundle_and_monthly_reference_summary.md`](../../docs/v1_19_local_run_bundle_and_monthly_reference_summary.md).

Test count: **4522 / 4522**. The default-fixture
`living_world_digest` (`quarterly_default`) is unchanged at
`f93bdf3f…b705897c`; the `monthly_reference` digest is pinned
at `75a91cfa…91879d`. The browser remains a **read-only viewer**
— no `fetch()`, no XHR, no backend, no engine execution from
the browser, no file-system write.

## v1.19.4 — Local run bundle loader (shipped, read-only)

The static workbench now loads a `RunExportBundle` JSON
artifact produced by the v1.19.2 / v1.19.3.1 CLI exporter.
**Read-only** — the browser never executes Python, never calls a
backend, never writes files.

### Workflow

```bash
cd japan-financial-world

# v1.19.2 — quarterly_default
python -m examples.reference_world.export_run_bundle \
    --profile quarterly_default \
    --regime constrained \
    --scenario none_baseline \
    --out /tmp/fwe_quarterly_bundle.json

# v1.19.3.1 — monthly_reference
python -m examples.reference_world.export_run_bundle \
    --profile monthly_reference \
    --regime constrained \
    --scenario none_baseline \
    --out /tmp/fwe_monthly_bundle.json

open examples/ui/fwe_workbench_mockup.html
```

In the workbench:

1. Click **Load local bundle** in the top ribbon.
2. Pick the JSON file from your file picker.
3. Inspect the rendered result in Inputs (Local run bundle
   card) / Overview / Timeline / Attention / Market Intent /
   Financing / Ledger.

### Behavior

- Reads the file via the browser `FileReader` API; **no
  network**.
- Parses with `JSON.parse` — never `eval`, never script
  injection.
- Validates the v1.19.1 `RunExportBundle` top-level key set
  and the v1.19.0 default 8-flag boundary-flag block.
- Renders user-loaded values via `textContent` only — never
  `innerHTML`.
- Updates the top-ribbon status to:
  `loaded local bundle · <profile> · <regime> · digest=<prefix> · read-only`.
- Updates the **`current_data_source`** label to
  `local_bundle`. Subsequently clicking **Run mock** flips
  the label back to `inline_fixture`; clicking **Load sample
  run** flips it to `sample_manifest`.
- Caps the rendered `ledger_excerpt` at 20 rows.
- Preserves the v1.17.4 no-jump discipline — does not call
  `scrollIntoView`, change `location.hash`, or change the
  active sheet.

### Accepted profiles

- ✅ `quarterly_default` — 4-period canonical default.
- ✅ `monthly_reference` — 12-period synthetic monthly profile;
  the bundle's `metadata.information_arrival_summary` is
  rendered into the *Information arrival summary* sub-card
  (calendar count / scheduled releases / arrivals + per-
  indicator-family / per-importance / per-arrival-status
  histograms). **Information arrival is not data ingestion** —
  no real values, no real release dates, no real
  institutional identifiers.

### Rejected profiles (clear status message)

- ❌ `scenario_monthly` — deferred (v1.19.x).
- ❌ `daily_display_only` — display-only; not loadable as a
  run bundle in v1.19.4.
- ❌ `future_daily_full_simulation` — explicitly out of scope
  for v1.19.

For any of the above the loader prints
`bundle profile '<profile>' is not loadable in v1.19.4 static UI`.

### Hard boundary

No engine execution from the browser. No backend. No
file-system write. No network. No daily simulation. No price
formation. No trading. No financing execution. No investment
advice. No real data ingestion. No Japan calibration. No LLM
execution. The workbench remains a single-file static HTML
prototype runnable directly under `file://`.

## v1.19.2 — CLI emits the JSON the v1.19.4 UI loader consumes (shipped)

The v1.19.2 CLI exporter at
[`../reference_world/export_run_bundle.py`](../reference_world/export_run_bundle.py)
now produces a deterministic `RunExportBundle` JSON artifact
on disk. v1.19.2 ships **CLI export only** — the static
workbench does not yet have a `Load local run bundle` button
(planned at v1.19.4).

When the v1.19.4 read-only loader ships, the file the static UI
will load is the byte-identical JSON produced by:

```bash
cd japan-financial-world

python examples/reference_world/export_run_bundle.py \
    --profile quarterly_default \
    --regime constrained \
    --scenario none_baseline \
    --out examples/ui/run_bundle.local.json
```

Two CLI runs with the same arguments produce byte-identical
JSON bytes regardless of the `--out` path. The bundle JSON
contains no ISO-style wall-clock timestamp, no absolute path,
and no `$USER` / `$HOSTNAME` — it is safe to drop into a
`file://`-runnable static workbench at v1.19.4 without any
local environment leakage.

## v1.19.1 — RunExportBundle data shape (shipped)

The static UI does not yet have a `Load local run bundle`
button (planned at v1.19.4). v1.19.1 lands the **data shape**
the future button will consume:
[`world/run_export.py`](../../world/run_export.py) now exports
a deterministic `RunExportBundle` dataclass and a JSON writer.

When the v1.19.4 loader ships, the file the UI will load is the
byte-identical JSON produced by:

```python
from world.run_export import build_run_export_bundle, write_run_export_bundle

bundle = build_run_export_bundle(
    bundle_id="run_bundle:demo:1",
    run_profile_label="quarterly_default",
    regime_label="constrained",
    period_count=4,
    digest="f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c",
    overview={"main_message": "..."},
    timeline={...},
    # ...
)
write_run_export_bundle(bundle, "examples/ui/run_bundle.local.json")
```

The bundle is **deterministic** (`sort_keys=True`); two writes
of the same `(profile, regime, scenario, payload)` triple
produce byte-identical files. The dataclass carries no
wall-clock timestamp field, so the rendered JSON contains no
ISO-style timestamp inserted by the export module itself.

Top-level keys the UI loader will consume:
`bundle_id` / `run_profile_label` / `regime_label` /
`selected_scenario_label` / `period_count` / `digest` /
`generated_at_policy_label` / `manifest` / `overview` /
`timeline` / `regime_compare` / `scenario_trace` /
`attention_diff` / `market_intent` / `financing` /
`ledger_excerpt` / `boundary_flags` / `status` / `visibility` /
`metadata`.

Default boundary flags: `synthetic_only` /
`no_price_formation` / `no_trading` / `no_investment_advice` /
`no_real_data` / `no_japan_calibration` / `no_llm_execution` /
`display_or_export_only`.

## v1.19.0 design pointer — local run bundle loader (delivered at v1.19.4)

The next planned UI milestone, **v1.19.0** (docs-only — see
[`../../docs/v1_19_local_run_bridge_and_temporal_profiles_design.md`](../../docs/v1_19_local_run_bridge_and_temporal_profiles_design.md)),
designs a **read-only `Load local run bundle`** affordance for
the static workbench:

- A fourth top-ribbon button (`Load local run bundle`) that
  reads a user-supplied `run_bundle.local.json` via `<input
  type="file">`, parses it with `JSON.parse` (no `eval`),
  validates the bundle shape via the existing `Validate`
  audit pass, and renders into the existing tabs (Overview /
  Timeline / Regime Compare / Scenario / Ledger / Attention /
  Market Intent / Financing).
- The JSON file is produced by a **CLI-first local run
  bridge** (`python -m examples.reference_world.export_run_bundle
  --profile <profile> --regime <regime> --scenario <scenario>
  --out examples/ui/run_bundle.local.json`).
- Optional v1.19.4+ tiny local server bridge: **127.0.0.1
  FastAPI / Flask / `http.server` only — never Rails**, never
  deployed SaaS. The static workbench remains
  `file://`-runnable; the bridge is optional and
  bypassable.
- **No browser file-system write. No engine execution from
  the UI. No daily full economic simulation. No backend
  server in v1.19.0.**

Run profiles the loader will surface (per `RunProfileLabel`
closed-set vocabulary): `quarterly_default` (current stable
default; preserves the canonical digest at
`f93bdf3f…b705897c`); `monthly_reference` (opt-in 12 monthly
periods); `scenario_monthly` (opt-in monthly + explicit
scenario application); `daily_display_only` (display-only
daily axis on top of a quarterly / monthly run, no daily
economic records); `future_daily_full_simulation` (**explicitly
out of scope for v1.19**).

## v1.18.last — scenario driver library freeze

v1.18.last closes the v1.18 sequence as the first FWE milestone
where **synthetic scenario drivers can be stored, applied as
append-only context shifts, rendered into scenario reports, and
selected in the static workbench UI** — without mutating any
source-of-truth record and without deciding actor behaviour.
The static workbench scenario selector (described below) is the
v1.18.4 contribution to that surface; the v1.18.last freeze is
docs-only and ships no UI changes beyond cross-links into the
single-page summary at
[`../../docs/v1_18_scenario_driver_library_summary.md`](../../docs/v1_18_scenario_driver_library_summary.md).

## v1.18.4 — scenario selector mock

The Inputs tab now carries a **scenario driver selector** card
with seven static fixture options:

- `none_baseline`              · Baseline (no scenario applied)
- `rate_repricing_driver`      · Rate repricing
- `credit_tightening_driver`   · Credit tightening
- `funding_window_closure_driver` · Funding window closure
- `liquidity_stress_driver`    · Liquidity stress
- `information_gap_driver`     · Information gap
- `no_direct_shift_fallback`   · Unmapped fallback

Selecting a scenario and clicking **Run mock** updates the top
ribbon status (`mock UI run · <regime> · <scenario> · static
fixture · no engine execution`), the Overview *scenario
summary* and *scenario trace* cards, and the Timeline *scenario
event annotation* card with a fixture-only rendering of the
v1.18.2 / v1.18.3 chain:

```
ScenarioDriverTemplate
  → ScenarioDriverApplicationRecord
  → ScenarioContextShiftRecord
  → EventAnnotationRecord
  → CausalTimelineAnnotation
```

Picking the **`no_direct_shift_fallback`** option surfaces the
v1.18.2 fallback callout verbatim — *"No direct context shift
emitted beyond fallback/no_direct_shift. This is not an error.
The template is stored but not yet mapped to a concrete context
surface."* — under the Timeline scenario card. This is the v1.18
design intent (rule-based-fallback only at v1.18.2; future
audited reasoning policies can replace the rule table) made
visible to a reader.

Every scenario card carries a small future-LLM-compatibility
note: **Reasoning mode: `rule_based_fallback`. Reasoning slot:
`future_llm_compatible`. No LLM execution in this prototype.**

The selector is **fixture switching only — the Python engine is
not invoked from the UI**. Same `(regime, scenario)` pair → same
visible state. The no-jump discipline pinned at v1.17.4 is
preserved verbatim: Run mock does not call `scrollIntoView`,
does not change `location.hash`, does not change the active
sheet, does not change browser zoom, and does not change scroll
position. The scenario tables use `table-layout: fixed` +
`overflow-wrap: anywhere` so long plain-id citations cannot
push the page wider than the viewport.

The inline JSON (`#fwe-sample-manifest`) and the standalone
[`sample_living_world_manifest.json`](sample_living_world_manifest.json)
both gain four top-level keys: `scenario_selector`,
`scenario_fixtures` (one entry per option), `scenario_trace`
(the chain pointer), and `selected_scenario`. **Validate**
checks every key, every required fixture field, the
`no_direct_shift` callout text, and the scenario selector
↔ trace card bijection.

## Hard boundary

No price prediction. No price formation. No trading. No order
matching. No lending decisions. No portfolio allocation. No
investment advice. No real data. No Japan calibration. No LLM
execution. No behavior probabilities. **Scenario selector is
the stimulus, never the response. Context shifts are
append-only; no pre-existing context record is mutated. No
actor decision is asserted by the scenario picker.**
