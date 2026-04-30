# v1 Roadmap

This document describes the v1 line of the Japan Financial World Engine.
v1 is **not** the place where Japan-specific calibration lives — that is
v2 (public calibration) and v3 (proprietary / commercial calibration).

v1 is the **jurisdiction-neutral reference financial system** built on
top of the v0 world kernel.

## Version boundary recap

| Version | Purpose                                                       |
| ------- | ------------------------------------------------------------- |
| v0.xx   | Jurisdiction-neutral world kernel (current freeze)            |
| v1.xx   | **Jurisdiction-neutral reference financial system** (planned) |
| v2.xx   | Japan public calibration (later)                              |
| v3.xx   | Japan proprietary / commercial calibration (later)            |

Two rules apply to everything below:

1. v1 stays neutral. v1 does not import the name BOJ, MUFG, Toyota,
   Marunouchi, USD/JPY, GPIF, or any other jurisdiction-specific
   identifier. Reference behavior must be expressible against any
   plausible financial economy.
2. v1 may not weaken any v0 invariant from
   [`v0_release_summary.md`](v0_release_summary.md) without an explicit
   documented decision.

## v1 themes

The v1 line introduces **behavior** in seven layered themes. Each theme
is one or more milestones; the order below is the expected order of
implementation, not a hard sequence.

### v1.1 Valuation / Fundamentals layer

What it adds: a way for the world to carry a more-than-face-value notion
of asset and firm worth.

- A `FundamentalsBook` (or analog) keyed by agent or asset, holding
  domain-neutral fields like `revenue_run_rate`, `operating_margin`,
  `book_value`, `cap_rate`, etc. Field set is jurisdiction-neutral; v2
  decides how to populate from Japan public data.
- A reference valuation projector that joins fundamentals × prices ×
  ownership, e.g. P/E, P/B, EV/EBITDA, DCF-style estimates, model marks
  for illiquid assets. v1 implements *one reference method per asset
  class*, not a Japan-tuned ensemble.
- `BalanceSheetView` may incorporate model-based valuations alongside
  market prices, with `valuation_basis` recorded so callers can choose.

### v1.2 Intraday Phase Scheduler

What it adds: phases inside a trading day so that "daily" stops being
the smallest time unit.

- Extend `Scheduler` so a single calendar day can dispatch through
  ordered phases (e.g., `pre_market`, `market`, `post_market`,
  `settlement`). v0 already reserves a `Phase` enum for this — v1
  populates it.
- Each space declares which phases its tasks fire in. Default remains
  `MAIN` so v0 spaces continue to work unchanged.
- Reference behavior in v1 only needs phases for spaces whose actions
  must be ordered *within* a day (e.g., orders submitted in pre-market,
  cleared in market phase, settled in post-market). v2 / v3 may extend
  to specific exchange phase calendars.

### v1.3 Institutional decomposition

What it adds: reference behavior for each domain space, in the same
"classify-don't-act" → "classify-and-decide" transition that v0 set up.

- **CorporateSpace v1**: revenue / expense / earnings update rule
  (reference closed form, not Japan-specific), corporate-action
  vocabulary (dividend, buyback, issuance), simple capex /
  delever / borrow heuristics gated by `BalanceSheetView` and
  `ConstraintEvaluation`.
- **BankSpace v1**: a reference credit decision rule that reads
  `LendingExposure` and `ConstraintEvaluation`s, and returns a
  decision — extend, tighten, default-trigger — without writing
  back to `ContractBook`. The contract update is mediated by an
  explicit transition record, so the audit trail is preserved.
- **InvestorSpace v1**: a reference allocation rule that reads
  `PortfolioExposure` and `BalanceSheetView` and emits *intent*
  events. Order generation lives in ExchangeSpace v1, not here.
- **ExchangeSpace v1**: a reference order matching mechanism (e.g.,
  continuous double auction) that consumes investor intent events
  and produces `price_updated` records. v1 matches against a
  reference simple book, not a high-fidelity LOB.
- **RealEstateSpace v1**: a reference cap-rate / rent / vacancy
  update rule, again jurisdiction-neutral.
- **InformationSpace v1**: a reference signal-emission rule for
  scheduled events (earnings dates, rating reviews) and a reference
  visibility-decay model for rumor-style signals.
- **PolicySpace v1**: a reference reaction function (e.g., a
  generic policy rule reading aggregate macro signals and
  publishing rate-change announcements as signals + WorldEvents).
  No Japan-specific BOJ logic.
- **ExternalSpace v1**: reference stochastic processes (random
  walk, AR(1), regime switch) wired to `factor_id`s, with explicit
  parameters that v2 calibrates to Japan public data.

### v1.4 ExternalWorld process

What it adds: a separate runtime layer that drives `ExternalFactorState`
values forward in time according to declared stochastic specs.

- Each external factor can declare a process spec in metadata
  (`{"process": "random_walk", "drift": ..., "vol": ...}`).
- A v1 ExternalWorld runner reads the specs and emits
  `factor_value_observed` records (a new ledger event type) on the
  declared frequency.
- v1 ships a small library of reference processes. v2 picks
  parameters using Japan public time series; v3 swaps in
  proprietary / paid-data calibration.

### v1.5 Relationship Capital layer

What it adds: the cross-agent reputation / trust dimension that
matters for credit, allocation, and information weighting but does
not belong inside any one space.

- A new kernel-level book (or layer) recording directed
  relationships between agents (e.g., `bank → firm` lending
  relationship strength, `investor → analyst` trust weight,
  `firm → press` historical disclosure quality).
- Read-only queries available to all spaces via the DomainSpace
  pattern.
- Reference v1 update rules are jurisdiction-neutral (e.g., trust
  decays slowly, breaches reset it, repeat-counterparty effects).
  Japan-specific relationship dynamics (keiretsu, main-bank
  relationships) belong to v2.

### v1.6 First closed-loop reference economy

What it adds: the first end-to-end loop where signals → decisions →
actions → state changes → new signals.

The test target is something like:
- ExternalSpace publishes a macro signal (e.g., reference rate up).
- PolicySpace reacts via reference reaction function.
- BankSpace tightens lending decision.
- CorporateSpace responds with reference borrow / capex behavior.
- ExchangeSpace clears equity prices via reference matching.
- InvestorSpace rebalances with reference allocation rule.
- The loop runs for a year and produces a coherent ledger trace.

This is the "v1 success condition" milestone. After it passes, v2 can
start replacing reference behavior with Japan-tuned behavior on a
per-space basis without breaking the loop.

## Out of scope for v1

Explicitly not in v1, even though they may be tempting:

- Any Japan-specific identifier or calibration (BOJ, MUFG, GPIF,
  USD/JPY, real listed firms, real macro data) — that is v2.
- Proprietary, expert-knowledge, or paid-data calibration — that is v3.
- High-fidelity limit order book or microstructure simulation —
  reference matching is enough for v1.
- Full natural-language news generation — v1 emits structured signals
  with reference content fields, not prose.
- Detailed accounting standard treatment (J-GAAP, IFRS) — reference
  fundamentals fields only.
- Detailed tax treatment.
- Endogenous global / multi-jurisdiction economy — v1 has one
  jurisdiction-neutral economy plus an ExternalWorld driver.

## Why this split

The reason v1 stays neutral is that calibration and reference behavior
have very different review cadences:

- Reference behavior changes when *the model* changes. It is reviewed
  by people who understand the math and the system architecture.
- Calibration changes when *the data* changes. It is reviewed by
  people who understand Japanese financial institutions and which
  data sources are credible.

If the two were entangled, every Japan-data update would be a model
change and every model change would be a Japan recalibration. v1
keeps them separate so that v2 / v3 can move on a faster cadence
without touching reference logic, and v1 can evolve without
invalidating prior calibration runs.

## Relationship to v2 and v3

| Layer | Owns                                                    | Examples                                       |
| ----- | ------------------------------------------------------- | ---------------------------------------------- |
| v0    | Structure, books, projections, transport                | `BalanceSheetView`, `EventBus`, `DomainSpace`  |
| v1    | Reference behavior, jurisdiction-neutral                | reference reaction function, reference matching, reference stochastic processes |
| v2    | Japan public calibration                                | BOJ in PolicySpace, listed equities, public macro time series |
| v3    | Japan proprietary / expert / paid-data calibration      | proprietary fund holdings, paid news feeds, expert override of structural breaks |

The further down the table, the higher the cadence of change. v0 is
frozen; v1 evolves with the model; v2 evolves with public data; v3
evolves with proprietary intelligence.
