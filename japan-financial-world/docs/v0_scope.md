# v0 Scope

This document is the **explicit in/out boundary for the v0 milestone** of the
Japan Financial World Engine. It supersedes the earlier [`scope.md`](scope.md)
for the purpose of describing what v0 actually delivered. `scope.md` is kept
as the long-term ambition document; this file is the v0 freeze contract.

v0 is a **jurisdiction-neutral world kernel**. It defines structure, not
behavior. None of the items below are implemented as Japan-specific logic.
Japan-specific work begins in v2.

## In scope for v0

The following are implemented and tested at the v0 freeze:

### Identity and time

- `WorldID` typed identifiers with `kind:key` form and a fixed allowlist of
  kinds (`agent`, `firm`, `bank`, `investor`, `asset`, `contract`, `market`,
  `signal`, `price`, `space`)
- `Registry` for stable identity, lookup by id / type / category
- `Clock` advancing by one calendar day at a time, with month / quarter /
  year-end detection
- `Scheduler` registering tasks by frequency (DAILY / MONTHLY / QUARTERLY /
  YEARLY) and phase, returning due tasks in deterministic order

### Audit trail and state

- `Ledger` as an append-only immutable record of every state-changing event,
  with `parent_record_ids` / `correlation_id` / `causation_id` fields for
  causal reconstruction
- `State` and `StateSnapshot` for mutable state with immutable monthly
  snapshots
- A defined record-type taxonomy (`object_registered`, `task_executed`,
  `event_published`, `event_delivered`, `ownership_position_added`,
  `ownership_transferred`, `contract_created`, `contract_status_updated`,
  `price_updated`, `constraint_added`, `constraint_evaluated`,
  `signal_added`, `signal_observed`, `state_snapshot_created`, plus one
  `*_state_added` per domain space)

### Inter-space transport

- `WorldEvent` immutable transport message with addressing, delay, and
  optional `signal_id` payload reference
- `EventBus` with a strict same-tick-delivery-forbidden rule, broadcast
  source-exclusion, and at-most-once delivery per `(event_id, space_id)`
  pair

### Network books (mutable canonical stores)

- `OwnershipBook` — positions and transfers
- `ContractBook` — explicit obligations between parties
- `PriceBook` — chronological per-asset observations (append-only)
- `ConstraintBook` — declarative financial-constraint records
- `SignalBook` — signal storage with visibility filtering

### Projections (read-only views)

- `BalanceSheetView` — per-agent asset / liability / NAV view derived from
  ownership × prices × contracts (plus optional registry for cash-like
  detection)
- `ConstraintEvaluator` — produces `ConstraintEvaluation` (ok / warning /
  breached / unknown) against a `BalanceSheetView`
- `LendingExposure` (BankSpace) — bank-side view of lending contracts
- `PortfolioExposure` (InvestorSpace) — investor-side view of holdings

### Eight domain spaces

Identity-level state for each, with read-only access to kernel projections
and signals:

- Corporate (`FirmState`)
- Banking (`BankState` + `LendingExposure`)
- Investors (`InvestorState` + `PortfolioExposure`)
- Exchange (`MarketState` + `ListingState`, composite-key relation)
- Real Estate (`PropertyMarketState` + `PropertyAssetState`, foreign-key
  relation)
- Information (`InformationSourceState` + `InformationChannelState`)
- Policy (`PolicyAuthorityState` + `PolicyInstrumentState`,
  foreign-key relation)
- External (`ExternalFactorState` + `ExternalSourceState`)

### DomainSpace abstraction

- `BaseSpace` with `bind()` hook + `observe` / `step` / `emit` / `snapshot`
  contract
- `DomainSpace` with the four-property `bind()` contract (idempotent /
  fill-only / explicit refs win / no hot-swap) and the three shared
  read-only accessors (`get_balance_sheet_view`, `get_constraint_evaluations`,
  `get_visible_signals`)

### Cross-space integration

- All eight spaces coexist in one `WorldKernel` and run for 365 days
- Per-space task counts match declared frequencies
- EventBus delivers cross-space events with the next-tick rule
- Read operations across all spaces leave every kernel-level book unchanged
- Ledger contains every expected event type after a one-year run

## Out of scope for v0

The following are **not** implemented in v0. They are deliberate omissions
and belong to v1 (reference behavior), v2 (Japan public calibration), or
v3 (Japan proprietary calibration).

### Economic behavior

- Agent decisions of any kind (no firm acts, no bank lends, no investor
  trades)
- Reaction functions (Taylor, Brainard, inflation-targeting, etc.)
- Allocation rules, mandate enforcement, or strategy selection
- Bank credit underwriting, origination, tightening, or covenant trips
- Default detection or non-performing classification
- Collateral haircuts, LTV-breach reactions, or fire-sale logic
- Corporate actions, earnings updates, or revenue dynamics

### Markets and prices

- Order matching, order books, or limit-order semantics
- Price formation, last-trade vs mid vs VWAP, or quote logic
- Price impact or market impact estimation
- Trading sessions, opens, closes, halts, or auctions
- Circuit breakers, kill switches, or volatility brakes
- Index construction or rebalancing
- Trade reporting, fees, or settlement

### Real estate

- Real-estate price formation or appraisal logic
- Cap rate updates, rent updates, or vacancy dynamics
- Transaction matching, property auctions, or distressed-sale dynamics
- REIT NAV computation or fund-level valuation

### Information dynamics

- News generation, signal interpretation, or content authoring
- Source credibility dynamics or accuracy tracking
- Rumor propagation, leak diffusion, or audience targeting
- Narrative formation or theme aggregation

### Policy and external

- Policy rate decisions or rate setting
- Liquidity operations or balance-sheet expansion / contraction
- Regulatory rule changes (capital ratios, leverage caps, etc.)
- External shock generation (oil, FX, war, natural disaster, pandemic)
- Random walks, AR/ARMA processes, or any stochastic process
- Regime switching or regime detection
- Historical replay of past data

### Cross-cutting concerns

- Intraday market phases (open / continuous / close / auction)
- Relationship capital or interpersonal trust modeling
- Valuation models or fundamentals layers
- Country-specific calibration of any kind (including Japan)
- Scenarios

## Why these omissions

v0's success condition is structural, not behavioral. Adding any of the items
above would require either:

1. mutating kernel-level books outside their explicit contract, or
2. coupling spaces to each other via something other than EventBus and the
   network books

Both are forbidden by §14 of `world_model.md`. The whole point of v0 is to
prove that the structural contract holds before any behavior is layered on
top — so v1 can introduce reactions, decisions, and dynamics as additive
work rather than structural rewrites.

If a future task requests one of the items above, it is a v1+ request, not
a v0 request, and the corresponding milestone document (e.g., a future
`v1_release_summary.md`) should record the decision to add it.

## Population tiers, time scales, feedback loops

The original [`scope.md`](scope.md) discusses population tiers, multi-scale
time, and a core feedback loop (firm state → disclosure → investor signal
interpretation → market price → credit → firm funding → real economy). Those
are the long-term targets that v1 (reference behavior) and v2 (Japan
calibration) are supposed to make real. v0 contains only the kernel that
makes those targets implementable.
