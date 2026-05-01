# Roadmap: To-C demo (LATER)

> **Status:** **deliberately later.** Not v1, not v2, not v3.
> Optional, downstream of everything else.
> **Layer:** FWE Public Demo (synthetic, public, illustrative).
> **Depends on:** FWE Core public release roadmap. Optionally also
> on JFWE Public if a Japan-flavored synthetic demo is wanted —
> but **never on real data** for the to-C surface.
> **Blocks:** nothing. The to-C surface is intentionally peripheral.

## Goal

If — and only if — the project decides it wants a public-facing
**demo / lead-gen surface** (a hosted page, a small web UI, a
shareable scenario) on top of FWE, this roadmap is the scope.

The to-C surface is **not the main business**. It is a way for
external readers to *see* what FWE does without reading code. The
main work is in FWE Core (engine), JFWE Public (calibration), and
JFWE Proprietary (commercial calibration). To-C demo work that
distracts from those is a mistake.

## Why "later"

Three reasons:

1. **Credibility risk.** A polished web UI on top of an
   uncalibrated reference engine is the easiest way for a casual
   visitor to mistake the project for a market predictor. Until
   the public framing (disclaimer, product layers, naming policy)
   is rock-solid in the README and docs, a UI amplifies the wrong
   message.
2. **Maintenance cost.** Web UIs rot faster than code. Hosting,
   browser compat, dependency churn, security patches all need
   ongoing attention that does not advance the core engine.
3. **Wrong forcing function.** A to-C demo's design pressure pulls
   toward "show flashy results" — exactly the opposite of FWE's
   value proposition (causal traceability, not flash).

## In scope (when this milestone is started)

### Web UI

- [ ] Single-page, server-side-rendered or static UI. Default:
  static HTML + minimal JS over a precomputed demo bundle.
- [ ] No real-time backend simulation. The demo shows a fixed
  causal trace from a precomputed run; users explore by clicking
  through the trace, not by parameterizing live runs.
- [ ] Visible disclaimer on every page header — same wording as
  the repo-root `README.md` Disclaimer.
- [ ] Hard cap on scope: one demo world, one trace, one ledger
  view. If a second demo is wanted, it is a *separate* page, not
  a parameter on the first.

### Project save / load

- [ ] If the UI ever lets users edit the demo (parameter sliders,
  alternative entities), it must save / load **synthetic
  projects only**. No upload of real data, ever.
- [ ] Saved projects are JSON / YAML files the user downloads;
  no server-side state required for v1 of the surface.
- [ ] Loaded projects are validated against the existing v0 / v1
  schemas before any rendering.

### Scenario templates

- [ ] A small library of **synthetic** scenario templates
  (e.g., "macro-index up by N", "sector-wide valuation cut").
- [ ] Every template uses the FWE Reference Demo's
  `*_reference_*` entities; no real names.
- [ ] Templates do not claim to predict real-world outcomes; the
  template description names the synthetic chain it produces.
- [ ] No more than ~10 templates total. If the library grows
  bigger, scope creep has happened.

### Explanatory report

- [ ] After a run, the UI generates a **plain-language report**
  describing the causal chain that was produced — drawing
  directly from the ledger and the cross-references, not from
  invented narrative.
- [ ] The report is exportable as Markdown / PDF.
- [ ] The report's tone is "here is what the simulation
  produced," not "here is what will happen in markets."

### Usage analytics

- [ ] Page-level analytics only (page views, time on page, demo
  starts, scenario template clicks).
- [ ] **No** PII collection.
- [ ] **No** session-level user-input recording.
- [ ] Analytics provider chosen for privacy (no third-party that
  cross-tracks across the public web).
- [ ] A `/privacy` page documents what is collected and why, and
  honors browser do-not-track signals.

### Branding

- [ ] To-C surface stays under the FWE / Financial World Engine
  name. No market-predictor branding, no investment-advice
  branding, no "Japan market simulator" branding.
- [ ] Cross-link clearly to the GitHub repo, the disclaimer, and
  the design docs.

## Out of scope

- Real-time market data integration (paid or free).
- Login / accounts beyond what is needed for save/load.
- Paid tiers as the primary monetization. (See "pricing warning"
  below.)
- Mobile app, native client, or browser extension.
- Multi-user collaboration features.
- AI-generated narrative reports that hallucinate beyond the
  ledger.
- Email capture as the gate to running the demo.
- A "model marketplace" or third-party-template ecosystem.
- Any feature that would require ingesting user-supplied real
  market data.

## Pricing warning

If, much later, this surface becomes a paid product, the
following discipline applies:

> **Do not price by N alone.**
>
> "N" here means an internal resource limit — number of scenarios
> a user can run, number of saved projects, number of API calls
> per day. Pricing on `N` only is an anti-pattern: it conflates
> user-facing value with internal cost, frustrates users who hit
> the limit on legitimate use, and signals that the project does
> not understand what it is selling.
>
> User-facing value should be priced on what the user actually
> *gets*: scenarios (custom, advanced templates), reports
> (deeper, exportable, branded), saved projects (sharable,
> versioned), export (data formats, integrations), advanced
> templates (proprietary scenario libraries — strictly within
> the bounds of what JFWE Proprietary allows externally), and
> explanation depth (causal-graph drill-down, expert
> annotations).
>
> A pure rate limit on a free tier is fine as a fairness
> mechanism; it should never be the headline line item of a paid
> tier.

This warning lives here so that any future "pricing for the to-C
demo" conversation starts from the right place.

## Reminder: to-C is demo / lead-gen, not main business

The to-C surface exists, **if at all**, to:

- Help a researcher understand what FWE does without reading
  code.
- Help a potential collaborator (academic, engineer, or
  commercial counterparty) decide whether to engage further.
- Make the project's framing — "causal, auditable simulation;
  not a market predictor" — visible to a non-technical reader.

It does **not** exist to:

- Compete in the retail / hobbyist market-prediction tools
  category.
- Ship trading signals, allocations, or any output that resembles
  investment advice.
- Replace direct conversation with serious counterparties.
- Become the project's primary revenue source. The economic
  basis of the project is in JFWE Proprietary (commercial
  engagements built on calibrated content) — not in retail
  subscriptions to a demo page.

If at any point the to-C demo's roadmap pulls more attention than
JFWE Public or Proprietary, the priorities are wrong and the
to-C surface should be scaled back or paused.

## Acceptance criteria (when started)

A to-C demo milestone is acceptable when **all** hold:

1. The disclaimer is visible on every page.
2. Every entity / scenario / template is synthetic; no real
   names anywhere.
3. No claim of market prediction, investment advice, or
   real-world calibration appears in any UI text.
4. The maintenance cost (hosting, deps, browser compat) is
   bounded and budgeted; if it would exceed budget, the surface
   is paused.
5. Analytics are privacy-respecting and documented.
6. The pricing warning above is followed if any paid tier is
   considered.

## Dependencies

- FWE Core public release roadmap (a public repo that can be
  linked).
- (Optional) JFWE Public roadmap, only if a Japan-flavored
  synthetic narrative is desired — and even then, the to-C
  surface uses **synthetic data with Japan-flavored entity
  names**, not real Japan data. Real Japan data does not appear
  in to-C for license / public-confusion reasons.

## Notes

- This file exists so that "let's build a web UI" becomes a
  concrete, scope-disciplined milestone instead of an open-ended
  product pivot.
- If the project never builds a to-C demo, that is a fine
  outcome. FWE's value is in the engine and the calibration
  layers, not in retail UI.
