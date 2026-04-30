# v0 Architecture Overview

This document describes the architecture of the Japan Financial World Engine
**as implemented at the v0 freeze**. The earlier [`architecture.md`](
architecture.md) describes the long-term ambition and is kept for reference;
this document describes what the v0 kernel actually contains.

v0 is jurisdiction-neutral and behavior-free. The architecture below is what
v1 / v2 / v3 will build on top of, not replace.

## Layered text diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WorldKernel                                    │
│                                                                             │
│   ┌─────────┐  ┌────────┐  ┌───────────┐  ┌────────┐  ┌──────────────┐     │
│   │Registry │  │Clock   │  │Scheduler  │  │Ledger  │  │State /       │     │
│   │         │  │        │  │           │  │(append │  │ Snapshot     │     │
│   │WorldID  │  │current │  │tasks by   │  │ only)  │  │              │     │
│   │+ kinds  │  │date,   │  │frequency  │  │        │  │              │     │
│   │         │  │month/  │  │+ phase    │  │        │  │              │     │
│   │         │  │quarter │  │+ order    │  │        │  │              │     │
│   │         │  │/year   │  │           │  │        │  │              │     │
│   │         │  │ends    │  │           │  │        │  │              │     │
│   └─────────┘  └────────┘  └───────────┘  └────────┘  └──────────────┘     │
│                                                                             │
│   ┌─────────┐  ┌────────────────────────────────────────────────────────┐  │
│   │EventBus │  │ Network Books (canonical mutable stores)               │  │
│   │         │  │   OwnershipBook    ContractBook    PriceBook           │  │
│   │next-tick│  │                                                        │  │
│   │delivery │  │ ConstraintBook              SignalBook                 │  │
│   │+ broad- │  │                                                        │  │
│   │cast w/  │  └────────────────────────────────────────────────────────┘  │
│   │source   │                                                               │
│   │exclusion│  ┌────────────────────────────────────────────────────────┐  │
│   └─────────┘  │ Projections (derived, never canonical)                 │  │
│                │   BalanceSheetProjector → BalanceSheetView             │  │
│                │   ConstraintEvaluator   → ConstraintEvaluation         │  │
│                │   (LendingExposure, PortfolioExposure live in spaces)  │  │
│                └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ via DomainSpace.bind(kernel)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DomainSpace                                    │
│  Common kernel refs (registry, balance_sheets, constraint_evaluator,        │
│  signals, ledger, clock) + bind() + 3 read-only accessors                   │
└─────────────────────────────────────────────────────────────────────────────┘
        │           │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
   │Corporate│ │Banking  │ │Investor │ │Exchange │ │RealEst. │ │Inform./  │
   │         │ │         │ │         │ │         │ │         │ │Policy/   │
   │FirmState│ │BankState│ │Investor │ │Market+  │ │Property │ │External  │
   │         │ │+Lending │ │+Portfo- │ │Listing  │ │Market+  │ │(Source/  │
   │         │ │Exposure │ │lioExpo- │ │         │ │Asset    │ │Channel/  │
   │         │ │         │ │sure     │ │         │ │         │ │Auth/     │
   │         │ │         │ │         │ │         │ │         │ │Inst/     │
   │         │ │         │ │         │ │         │ │         │ │Factor/   │
   │         │ │         │ │         │ │         │ │         │ │Source)   │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘
```

## Components

### WorldKernel

`WorldKernel` is a dataclass that holds and wires everything else. It
provides:

- `register_object(obj)` — register an entity in the Registry; emits
  `object_registered` to the ledger
- `register_space(space)` — register a `BaseSpace` instance; calls
  `space.bind(kernel)`; schedules every task the space declares
- `register_task(task)` — explicit task registration
- `tick()` — run all due tasks for the current clock date, optionally
  emit a state snapshot on month-ends, advance the clock by one day
- `run(days)` — call `tick()` `days` times

In `__post_init__` the kernel propagates its `ledger` and `clock`
references into every book (Ownership, Contracts, Prices, Constraints,
Signals) that does not already have them set, then constructs the
`BalanceSheetProjector` and `ConstraintEvaluator` with those shared
refs.

### Registry

Identity layer. `WorldID` strings have the form `"kind:key"` where
`kind` is one of: `agent`, `firm`, `bank`, `investor`, `asset`,
`contract`, `market`, `signal`, `price`, `space`. `Registry` provides
`register`, `get`, `__contains__`, `list_by_type`, plus dedicated
register methods per kind.

### Clock + Scheduler

`Clock` advances by one calendar day at a time and reports
`is_month_end / is_quarter_end / is_year_end`. `Scheduler` registers
tasks by frequency (DAILY / MONTHLY / QUARTERLY / YEARLY) and phase,
and returns the tasks due on the current clock date in deterministic
order.

### Ledger

`Ledger` is an append-only list of immutable `LedgerRecord`s. Every
record carries: `record_id`, `sequence`, timestamp, simulation date,
record type, source / target / object_id, payload, metadata,
parent_record_ids, optional `correlation_id` and `causation_id`,
optional reproducibility fields (`scenario_id`, `run_id`, `seed`,
`space_id`, `agent_id`, `snapshot_id`, `state_hash`, `visibility`,
`confidence`).

The ledger is the canonical audit trail. v0 emits it on every state-
changing operation. v1 reaction functions are expected to read it
without being affected by it.

### State + Snapshot

`State` is the kernel's mutable state store with `initialize_object`
and `snapshot(simulation_date)` returning an immutable
`StateSnapshot`. Snapshots are emitted by the kernel on month-ends and
referenced by ledger `state_snapshot_created` records. v0's State is
deliberately small — most state lives in the network books; State
holds only what the registry initializes via `initialize_object`.

### EventBus + WorldEvent

`EventBus` is the inter-space transport channel. `WorldEvent` carries
`event_id`, `simulation_date`, `source_space`, `target_spaces`,
`event_type`, `payload`, `visibility`, `delay_days`, `confidence`,
`related_ids`. The bus enforces:

- delivery only after `current_date > publication_date` (next-tick rule)
- delivery only after `current_date >= delivery_date` (delay_days)
- delivery only to addressed targets (or every space except source for
  broadcasts)
- at-most-once delivery per `(event_id, space_id)` pair

The kernel records `event_published` and `event_delivered` to the
ledger.

### Network books

Three canonical mutable stores plus two more that v0 added later:

- `OwnershipBook` — `(owner_id, asset_id) → quantity` with
  `add_position` / `transfer` / per-(owner|asset) listing / snapshot
- `ContractBook` — `contract_id → ContractRecord` with explicit
  `parties`, optional `principal` / `rate` / `maturity_date` /
  `collateral_asset_ids` / `status`, lookup by party / type, status
  update
- `PriceBook` — `asset_id → list[PriceRecord]` append-only history
- `ConstraintBook` — `constraint_id → ConstraintRecord`, declarative
  financial constraints
- `SignalBook` — `signal_id → InformationSignal`, with visibility
  filtering

All books emit ledger records on mutation. v0 contains no logic that
mutates these books on its own — every mutation is the result of an
explicit caller invocation.

### Projections

Derived views, never canonical:

- `BalanceSheetProjector.build_view(agent_id)` — joins ownership ×
  prices × contracts to produce a per-agent `BalanceSheetView` with
  `asset_value`, `liabilities`, `net_asset_value`, plus optional
  `cash_like_assets` / `debt_principal` / `collateral_value`. Missing
  prices flagged in `metadata`.
- `ConstraintEvaluator.evaluate_owner(agent_id)` — runs every
  constraint owned by the agent against a freshly built
  `BalanceSheetView` and returns `ConstraintEvaluation`s with
  status ∈ {ok, warning, breached, unknown}.

Projections are pure reads of the books. They never mutate.

### DomainSpace

`DomainSpace` is the v0.10.1 extraction shared by every concrete
space. It owns six common ref fields (`registry`, `balance_sheets`,
`constraint_evaluator`, `signals`, `ledger`, `clock`), a `bind()`
implementing the four-property contract (idempotent / fill-only /
explicit refs win / no hot-swap), and three read-only accessors
(`get_balance_sheet_view`, `get_constraint_evaluations`,
`get_visible_signals`).

Concrete spaces extend it by adding domain-specific fields (e.g.,
`contracts` for Banking, `ownership` and `prices` for Investors,
`prices` for Exchange / Real Estate) and overriding `bind()` to
capture them.

### Eight concrete spaces

Each space has identity-level state for its domain plus optional
domain-specific projections. None of them implement behavior.

| Space          | Identity state(s)                          | Domain projection      |
| -------------- | ------------------------------------------ | ---------------------- |
| Corporate      | FirmState                                  | (none)                 |
| Banking        | BankState                                  | LendingExposure        |
| Investors      | InvestorState                              | PortfolioExposure      |
| Exchange       | MarketState + ListingState                 | (uses ListingState)    |
| Real Estate    | PropertyMarketState + PropertyAssetState   | (FK from asset→market) |
| Information    | InformationSourceState + InformationChannelState | (uses SignalBook) |
| Policy         | PolicyAuthorityState + PolicyInstrumentState     | (FK from instrument→authority) |
| External       | ExternalFactorState + ExternalSourceState  | (independent maps)     |

## What v0 architecture does not contain

These items appear in the long-term [`architecture.md`](architecture.md)
but are not implemented at v0:

- Real Economy / Capital Market / Asset Market / Information / Policy /
  External *layer* abstractions as separate runtime objects (v0 has eight
  spaces, not seven layers; layers are conceptual)
- Index / Passive Flow, Derivatives, REIT, Shadow Banking subspaces
- BOJ-specific reaction logic, Government / Ministries decisions,
  exchange rules engine
- Geopolitics or Overseas Markets stochastic processes

These belong to later versions or remain conceptual sketches in
`architecture.md`.

## Why this layout

The v0 layout is dictated by §14 of `world_model.md`: spaces must not
directly mutate each other. Every cross-space effect must pass through
an explicit world object — ownership, contract, market price,
information signal, or constraint. The kernel-level books *are* those
explicit objects. The projections derive from them but never own them.
The event bus carries messages but never mutates books. The domain
spaces classify locally but cannot mutate kernel books directly (their
`bind()` only captures references; the books themselves are owned by
the kernel).

This is the reason v0 took fifteen incremental milestones to build —
each layer's invariants had to land before the next one could rely on
them. v1 behavior can now be added without re-litigating the kernel
shape.
