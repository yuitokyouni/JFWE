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
freeze is **v1.15.last** — the first FWE milestone where the
living reference world carries a bounded **securities-market-
interest aggregation** chain (investor market intent → aggregated
market interest → indicative market pressure) layered on top of
the v1.14 corporate financing chain, with a deterministic
feedback loop where indicative market pressure is cited by the
capital-structure review and the financing path. Pinned at digest
`bd7abdb9a62fb93a1001d3f760b76b3ab4a361313c3af936c8b860f5ab58baf8`
on the default 4-period fixture. This UI prototype is
intentionally lower-frequency than the engine and is bumped
opportunistically; for the engine narrative see
[`../../docs/v1_15_securities_market_intent_summary.md`](../../docs/v1_15_securities_market_intent_summary.md)
(v1.15) and
[`../../docs/v1_14_corporate_financing_intent_summary.md`](../../docs/v1_14_corporate_financing_intent_summary.md)
(v1.14).

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
