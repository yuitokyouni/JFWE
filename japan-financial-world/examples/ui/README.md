# FWE Analyst Workbench — static UI prototype

A single-file static HTML mockup that arranges FWE outputs as an
Excel-like analyst workbench. Open the file directly in a browser
— no backend, no build tools, no external runtime.

## Files

- `fwe_workbench_mockup.html` — the polished mockup (10 sheet
  tabs: Cover, Settings, Market State, Attention, Firms,
  Investors, Banks, Outputs, Ledger, Appendix).
- `preview.html` — earlier 7-tab draft kept for reference.

## How to open

From a clone of the repo, just double-click the file or open it
in your browser:

```
japan-financial-world/examples/ui/fwe_workbench_mockup.html
```

No web server is needed. No external CSS, JS, or font CDN is
fetched. Tab switching is plain vanilla JavaScript.

## What it shows

Each tab is a *visual placeholder* for one analyst-facing surface
of the engine:

| Sheet         | Content                                                                                                  |
| ------------- | -------------------------------------------------------------------------------------------------------- |
| Cover         | title, author, build line, hard-boundary footer                                                          |
| Settings      | run digest / seed / periods / firms / investors / banks; market regime selector mock; strategy modules    |
| Market State  | period-by-period regime labels, state lineage                                                             |
| Attention     | per-actor `ActorAttentionState`, selected evidence, memory selection, budget / decay / crowding / saturation |
| Firms         | firm latent state, corporate financing need (v1.14.1) placeholder, strategic response candidates          |
| Investors     | valuation refresh lite, intent signal, stewardship themes, dialogue / escalation candidates               |
| Banks         | bank credit review lite, interbank liquidity state (v1.13.5), v1.13 substrate map                         |
| Outputs       | wide hero index/event timeline, KPI strip, LLM-readable causal summary table, stylized facts (secondary)  |
| Ledger        | record stream, selected record, parent evidence, downstream records, digest / manifest area              |
| Appendix      | version boundary, hard-boundary statement, status of this UI                                              |

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
