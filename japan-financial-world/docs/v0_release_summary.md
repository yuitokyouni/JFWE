# v0 Release Summary

This document summarizes what the v0 milestone of the Japan Financial World
Engine delivered. It is the canonical "what's in v0" reference; for milestone-
by-milestone design rationale see `world_model.md`.

## v0 purpose

v0 builds the **constitutional structure** of the simulation: the world
kernel, the network of state-bearing books, the projections that derive
information from those books, the inter-space transport channel, and the
identity-level state for each of eight domain spaces. v0 is jurisdiction-
neutral — it makes no assumptions about Japan, no economic decisions, and
no scenarios.

The v0 success condition is *not* realism. It is whether the kernel can run
for one year with eight spaces coexisting, share its books and signals
through well-defined read-only accessors, deliver events between spaces
with a strict next-tick rule, and produce a complete ledger audit trail —
all without any space mutating any other space's state and without any
business behavior implemented.

`tests/test_world_kernel_full_structure.py` verifies these invariants
end-to-end. Combined with all earlier-milestone tests, the suite is
**444/444 passing** at v0 freeze.

## Final v0 module stack

```
world/                      # kernel
  ids.py                    # WorldID type and registry kinds
  registry.py               # Registry — identity, lookup, categories
  clock.py                  # Clock — simulation date and calendar boundaries
  scheduler.py              # Scheduler — task registration and frequency dispatch
  ledger.py                 # Ledger — append-only audit trail, every event type
  state.py                  # State / StateSnapshot — mutable state + immutable snapshots
  event_bus.py              # EventBus — inter-space transport, next-tick delivery
  events.py                 # WorldEvent — immutable transport message
  ownership.py              # OwnershipBook — positions and transfers
  contracts.py              # ContractBook — explicit obligations
  prices.py                 # PriceBook — chronological observations per asset
  balance_sheet.py          # BalanceSheetProjector — derived per-agent view
  constraints.py            # ConstraintBook + ConstraintEvaluator
  signals.py                # SignalBook + InformationSignal
  loader.py                 # YAML loader for minimal-world bootstrap
  validation.py             # Schema validation helpers
  kernel.py                 # WorldKernel — wires everything together
  cli.py                    # Command-line empty-world runner

spaces/
  base.py                   # BaseSpace — observe/step/emit/snapshot + bind() hook
  domain.py                 # DomainSpace — common ref fields + accessors (v0.10.1)
  corporate/                # FirmState
  banking/                  # BankState + LendingExposure
  investors/                # InvestorState + PortfolioExposure
  exchange/                 # MarketState + ListingState
  real_estate/              # PropertyMarketState + PropertyAssetState
  information/              # InformationSourceState + InformationChannelState
  policy/                   # PolicyAuthorityState + PolicyInstrumentState
  external/                 # ExternalFactorState + ExternalSourceState
```

## The eight spaces

Every space inherits from `DomainSpace` and follows the same pattern:
identity-level state map(s), `bind()` to capture kernel refs, read-only
accessors, deterministic `snapshot()`, ledger-recorded mutations.

| Space          | Frequencies                  | bind() override | Domain-specific projection |
| -------------- | ---------------------------- | --------------- | -------------------------- |
| Corporate      | MONTHLY, QUARTERLY, YEARLY   | no              | (none)                     |
| Banking        | DAILY, QUARTERLY             | yes (contracts) | LendingExposure            |
| Investors      | DAILY, MONTHLY               | yes (ownership, prices) | PortfolioExposure  |
| Exchange       | DAILY                        | yes (prices)    | (uses ListingState)        |
| Real Estate    | MONTHLY, QUARTERLY           | yes (prices)    | (uses PropertyAssetState)  |
| Information    | DAILY                        | no              | (uses SignalBook directly) |
| Policy         | MONTHLY                      | no              | (none)                     |
| External       | DAILY                        | no              | (none)                     |

Four spaces declare a `bind()` override (Banking / Investors / Exchange /
Real Estate) because they need a domain-specific kernel ref beyond the
DomainSpace defaults. The other four (Corporate / Information / Policy /
External) inherit `DomainSpace.bind` unchanged.

## Books, views, signals, events

**Books** — canonical mutable stores in the kernel:

- `OwnershipBook`: positions and transfers
- `ContractBook`: explicit obligations between parties
- `PriceBook`: append-only chronological price observations per asset
- `ConstraintBook`: declarative financial-constraint records
- `SignalBook`: signal store with visibility filtering

**Projections** — derived views, never canonical state:

- `BalanceSheetView`: per-agent asset/liability/NAV view, joins
  `OwnershipBook × PriceBook × ContractBook` (and optionally `Registry` for
  cash-like detection)
- `ConstraintEvaluation`: ok / warning / breached / unknown verdict against a
  `BalanceSheetView`
- `LendingExposure`: bank-side view of lending contracts
- `PortfolioExposure`: investor-side view of holdings (joins ownership,
  prices, and registry)

**Signals** — first-class information records:

- `InformationSignal`: who said what about whom, with effective date,
  visibility, credibility, confidence, and references to other world IDs

**Events** — inter-space transport:

- `WorldEvent`: addressable message with `target_spaces`, `delay_days`, and
  optional `signal_id` reference in payload
- `EventBus`: delivers events with a strict same-tick-delivery-forbidden rule

## Invariants verified by v0.15

The cross-space integration test (`test_world_kernel_full_structure.py`)
asserts these properties hold simultaneously:

1. All eight spaces coexist in one `WorldKernel` and run for 365 days
   without exception.
2. Each space's scheduled tasks fire the expected number of times
   (DAILY × 365, MONTHLY × 12, QUARTERLY × 4, YEARLY × 1).
3. Month-end snapshots are created automatically (12 over the year).
4. Every space's read accessors return correct data for the populated seed.
5. EventBus delivers a multi-target event on day 2 (next-tick rule), with
   exactly one ledger record per target.
6. Event delivery is independent of signal visibility — a restricted
   signal can still flow through the bus, but `SignalBook.list_visible_to`
   continues to hide it from non-allowed observers.
7. Read operations across all eight spaces leave every kernel-level book's
   snapshot byte-identical (no space mutates any source-of-truth book).
8. The ledger contains every expected event type after a full setup +
   one-year run.

These are the v0 invariants. Any future milestone that breaks them
without an explicit, documented decision is breaking v0's contract.

## What is intentionally out of scope for v0

v0 does **not** implement:

- economic decisions of any kind (no agent acts; spaces only classify and read)
- price formation, order matching, trading, or order books
- credit decisions, default detection, covenant trips, or collateral haircuts
- investor strategy, allocation, rebalancing, or activist behavior
- policy rate decisions, reaction functions, or liquidity operations
- regulatory rule changes (e.g., capital ratio adjustments)
- corporate actions, earnings updates, or revenue dynamics
- real-estate price formation, cap-rate updates, or rent dynamics
- external shock generation, random walks, regime switching, or historical
  replay
- narrative / rumor / credibility dynamics
- intraday market phases (open / close / auction / halt)
- relationship capital or interpersonal trust modeling
- valuation models or fundamentals layers
- any Japan-specific (or any other jurisdiction-specific) calibration
- scenarios

These omissions are not bugs. They are the v0 contract.

## How v0 prepares v1

v1 will introduce **jurisdiction-neutral reference behavior** on top of the
v0 kernel:

- Reference valuation / fundamentals layer (so balance sheets reflect
  more than face-value face value)
- Intraday phase scheduler (open / continuous / close phases inside a
  trading day)
- First reference institutional behavior (investor decisions, bank credit
  decisions, corporate actions, market clearing)
- ExternalWorld stochastic processes (random walks, regime switches as
  reference dynamics, not Japan calibration)
- Relationship capital layer (cross-agent reputation / trust signals)
- A first closed-loop reference economy: signal → decision → action → state
  change → new signal

v0's invariants make v1 implementable as additive behavior rather than
structural change. Specifically:

- The ledger is a complete causal trace, so v1 reaction functions can read
  it without being affected by it.
- Books are append-only or carefully versioned, so v1 mutations do not
  destroy v0 history.
- `bind()` lets v1 spaces capture additional refs without modifying the
  kernel.
- `WorldEvent` and `SignalBook` are decoupled, so v1 can add narrative
  dynamics without changing transport.
- `DomainSpace` makes adding new domain spaces (or rebuilding existing ones
  with v1 behavior) a localized change.

Japan-specific calibration belongs to v2; commercial/proprietary Japan
calibration belongs to v3. **v1 stays neutral**, just like v0.

## Test status at freeze

`pytest -q` reports `444 passed`. The breakdown by component is in
[`test_inventory.md`](test_inventory.md).
