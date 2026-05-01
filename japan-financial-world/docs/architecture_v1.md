# v1 Architecture Overview

This document describes the architecture of the Japan Financial World Engine
**as implemented at the v1.7 freeze**. It builds on
[`architecture_v0.md`](architecture_v0.md), which captured the kernel shape
at the v0.16 freeze. v1 adds books, an extended scheduler, and a reference-
loop orchestrator on top of v0 — without replacing any v0 component.

v1 is jurisdiction-neutral and autonomous-behavior-free. The architecture
below is what v2 (Japan public calibration) and v3 (Japan proprietary
calibration) will populate, not replace.

## Layered text diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              WorldKernel                                     │
│                                                                              │
│  ┌─ v0 kernel (frozen) ─────────────────────────────────────────────────┐    │
│  │  Registry    Clock    Scheduler*   Ledger    State / Snapshot         │    │
│  │                                                                       │    │
│  │  EventBus    OwnershipBook   ContractBook   PriceBook                 │    │
│  │              ConstraintBook  SignalBook                               │    │
│  │                                                                       │    │
│  │  BalanceSheetProjector → BalanceSheetView                             │    │
│  │  ConstraintEvaluator   → ConstraintEvaluation                         │    │
│  │  (LendingExposure, PortfolioExposure inside spaces)                   │    │
│  │                                                                       │    │
│  │  * Scheduler extended in v1.2: Phase enum gains 6 intraday phases,    │    │
│  │    per-date run-mode guard added; v0 MAIN-only behavior preserved.    │    │
│  └───────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─ v1 books (additive) ────────────────────────────────────────────────┐    │
│  │                                                                       │    │
│  │  v1.1  ValuationBook ────────────► ValuationComparator                │    │
│  │            ValuationRecord                 reads PriceBook,           │    │
│  │            (with currency vs                writes ValuationGap +     │    │
│  │             numeraire)                       valuation_compared       │    │
│  │                                                                       │    │
│  │  v1.2  PhaseSequence (overnight → pre_open → opening_auction          │    │
│  │            → continuous_session → closing_auction → post_close)       │    │
│  │            consumed by Scheduler.run_day_with_phases                  │    │
│  │                                                                       │    │
│  │  v1.3  InstitutionBook                                                │    │
│  │            InstitutionProfile, MandateRecord,                         │    │
│  │            PolicyInstrumentProfile, InstitutionalActionRecord         │    │
│  │            (4-property action contract: explicit input_refs /         │    │
│  │             output_refs / ledger record / no cross-space mutation)    │    │
│  │                                                                       │    │
│  │  v1.4  ExternalProcessBook                                            │    │
│  │            ExternalFactorProcess (spec, not runtime)                  │    │
│  │            ExternalFactorObservation (point + scenario point)         │    │
│  │            ExternalScenarioPath                                       │    │
│  │                                                                       │    │
│  │  v1.5  RelationshipCapitalBook                                        │    │
│  │            RelationshipRecord (directed pairs, decay spec stored      │    │
│  │             but not applied)                                          │    │
│  │            RelationshipView (read-only join helper)                   │    │
│  │                                                                       │    │
│  │  v1.6  ReferenceLoopRunner (orchestrator, no book of its own)         │    │
│  │            chains every v1 record type through cross-references       │    │
│  └───────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ via DomainSpace.bind(kernel)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              DomainSpace                                     │
│  Common kernel refs (registry, balance_sheets, constraint_evaluator,         │
│  signals, ledger, clock) + bind() + 3 read-only accessors                    │
│  (unchanged from v0.10.1 — every v1 book is a kernel ref, not a              │
│   space-owned ref; spaces continue to read through the kernel)               │
└──────────────────────────────────────────────────────────────────────────────┘
        │           │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
   │Corporate│ │Banking  │ │Investor │ │Exchange │ │RealEst. │ │Inform./  │
   │         │ │         │ │         │ │         │ │         │ │Policy/   │
   │FirmState│ │BankState│ │Investor │ │Market+  │ │Property │ │External  │
   │         │ │+Lending │ │+Portfo- │ │Listing  │ │Market+  │ │(unchanged│
   │         │ │Exposure │ │lioExpo- │ │         │ │Asset    │ │ from v0) │
   │         │ │         │ │sure     │ │         │ │         │ │          │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘
```

The eight v0 spaces are unchanged in v1. v1 adds **books**, an **extended
scheduler**, and an **orchestrator**, but no new domain space — and no v1
module mutates any space's identity-level state.

## Components added in v1

### ValuationBook (v1.1)

`ValuationBook` stores `ValuationRecord`s — a model-based valuation of a
subject (firm, asset, contract, or any registered id) by a valuer at a
point in time. Fields include `valuation_id`, `subject_id`, `valuer_id`,
`valuation_type`, `purpose`, `method`, `as_of_date`, `estimated_value`,
`currency` (display unit), `numeraire` (perspective), `confidence`,
`assumptions`, `inputs`, `related_ids`, `evidence_refs`. Currency and
numeraire are stored as data; v1 does **not** convert between them.

`ValuationGap` is the comparator output. It is computed by
`ValuationComparator.compare_to_latest_price(valuation_id)`, which reads
the latest `PriceRecord` for the subject from `PriceBook`, computes
`absolute_gap` and `relative_gap`, and writes a `valuation_compared`
ledger record with `parent_record_ids` pointing at the originating
`valuation_added` record. Gaps are not stored; they are derived on read.

The book emits `valuation_added` on insert and `valuation_compared` on
comparison. It does not emit gap-driven records of its own — a gap does
not trigger any decision in v1.

### PhaseSequence + extended Scheduler (v1.2)

The v0 `Phase` enum had a single `MAIN` member as a placeholder. v1.2
populates it with six intraday phases:

```
overnight → pre_open → opening_auction → continuous_session
         → closing_auction → post_close
```

`IntradayPhaseSpec` declares one phase (id, label, order, optional
metadata). `PhaseSequence` is the ordered tuple of phase specs that a
trading day passes through.

The scheduler is extended with `run_day_with_phases(date, sequence)`,
which dispatches due tasks for the date through the declared phases in
order. Tasks declare `phase=Phase.MAIN` by default, so v0-era tasks
continue to fire under both `tick()` (date-only) and
`run_day_with_phases` (phase-aware). A per-date **run-mode guard**
prevents mixing `date_tick` and `intraday_phase` advancement on the
same simulation date — once a date has been advanced one way, the other
path is rejected for that date. The guard scope resets on the next
date.

Intraday phase ids are also recorded on every v1 record that has a
`phase_id` field (`InstitutionalActionRecord`,
`ExternalFactorObservation`), so causal-graph reconstruction can include
intra-day ordering.

### InstitutionBook (v1.3)

`InstitutionBook` is the institutional-decomposition layer. It holds:

- `InstitutionProfile` — identity-level metadata about an institution
  (`institution_id`, `institution_type`, `jurisdiction_code`,
  `metadata`). v1 does not enumerate institution types; the field is
  free-form.
- `MandateRecord` — a mandate held by an institution (`mandate_id`,
  `institution_id`, `mandate_type`, `effective_from`, optional
  `effective_until`, `policy_targets`, `metadata`). Cross-references to
  policy targets are stored as data.
- `PolicyInstrumentProfile` — a policy instrument operated by an
  institution (`instrument_id`, `institution_id`, `instrument_type`,
  optional `metadata`). Distinct from `PolicyInstrumentState` in
  `spaces/policy/state.py`, which tracks identity-level state; this is
  the institutional-side profile.
- `InstitutionalActionRecord` — the central v1.3 record. Carries
  `action_id`, `institution_id`, `action_type`, `as_of_date`,
  `phase_id`, `input_refs`, `output_refs`, `target_ids`,
  `instrument_ids`, `payload`, `parent_record_ids`. Per the
  **four-property action contract**: explicit `input_refs` declare
  what the action read; explicit `output_refs` declare what records
  the action's writer creates; the record itself is the ledger entry;
  no other book is mutated.

Ledger types: `institution_profile_added`, `institution_mandate_added`,
`institution_instrument_added`, `institution_action_recorded`.

### ExternalProcessBook (v1.4)

`ExternalProcessBook` holds the external-process layer:

- `ExternalFactorProcess` — a *spec* for how a factor evolves
  (`process_id`, `factor_id`, `process_type` ∈ {`constant`,
  `random_walk`, `ar1`, `regime_switch`, …}, `parameters`,
  `frequency`, optional `phase_id`, `metadata`). v1 stores the spec
  as data; it does **not** run the process.
- `ExternalFactorObservation` — a single observation of a factor at a
  date (and optional intraday phase): `observation_id`, `factor_id`,
  `value`, `as_of_date`, `phase_id`, `source_id`, `process_id`,
  `metadata`. Convenience helper `create_constant_observation` writes
  a constant-process observation and emits the matching ledger entry.
- `ExternalScenarioPoint` / `ExternalScenarioPath` — a forward path of
  scenario points (`path_id`, `process_id`, `points`, `metadata`).
  Stored as data; v1 does not branch or replay scenarios.

Ledger types: `external_process_added`, `external_observation_added`,
`external_scenario_path_added`.

### RelationshipCapitalBook (v1.5)

`RelationshipCapitalBook` records directed relationships between
agents:

- `RelationshipRecord` — `relationship_id`, `from_id`, `to_id`,
  `relationship_type`, `strength`, `as_of_date`, `decay_spec`
  (parameters such as half-life), `metadata`. Strength updates emit
  `relationship_strength_updated`; new records emit `relationship_added`.
- `RelationshipView` — read-only join helper that returns the latest
  strength for a (from_id, to_id, type) tuple as of a query date.

`decay_spec` is stored as data. v1 does **not** apply decay
automatically — reads return the last-recorded strength deterministically.
Decay application is reserved for v2+ behavioral milestones, where it
becomes part of a behavioral rule (credit reaction, allocation
weighting) rather than an automatic background process.

### ReferenceLoopRunner (v1.6)

`ReferenceLoopRunner` is a thin orchestrator. It owns no book; it holds
a reference to the kernel and exposes seven step methods that *wire*
existing v1 records into a single causal chain:

```
Step 1: record_external_observation
        → ExternalProcessBook.create_constant_observation
        → external_observation_added (ledger)

Step 2: emit_signal_from_observation
        → SignalBook.add_signal (v0)
        → InformationSignal with related_ids = (observation_id,)
        → signal_added (ledger)

Step 3: record_valuation_from_signal
        → ValuationBook.add_valuation
        → ValuationRecord with related_ids = (signal_id,)
                              inputs       = {"signal_id": ...}
        → valuation_added (ledger)

Step 4: compare_valuation_to_price
        → ValuationComparator.compare_to_latest_price
        → ValuationGap (computed, not stored)
        → valuation_compared (ledger, parent_record_ids -> valuation_added)

Step 5: record_institutional_action
        → InstitutionBook.add_action_record
        → InstitutionalActionRecord with
               input_refs        = (valuation_id, …)
               output_refs       = (planned_signal_id,)
               target_ids        = (subject_id, …)
               parent_record_ids = (valuation_added, valuation_compared)
        → institution_action_recorded (ledger)

Step 6: emit_signal_from_action
        → SignalBook.add_signal
        → InformationSignal with related_ids = (action_id,)
        → signal_added (ledger)

Step 7: publish_signal_event
        → EventBus.publish (v0 next-tick rule)
        → ledger.append("event_published") explicitly
                 (mirrors what BaseSpace.emit() records, so direct-
                  bus and space-driven publication produce equivalent
                  audit trails)
        → on date D+1: per-target event_delivered (ledger)
```

The runner does not decide anything. Each step takes explicit inputs,
builds the next record with appropriate cross-references, and delegates
the write to the book that owns the record type. The closed loop is
structural, not behavioral: it demonstrates that all the v1 record
types can be linked into a single end-to-end trace without any module
mutating state outside its own book.

## The end-to-end ledger causal trace

Reading from the ledger after a single reference-loop pass, the causal
graph (via `parent_record_ids` and `related_ids` references) looks like:

```
  external_process_added
        │
        ▼
  external_observation_added            (Step 1)
        │
        ▼ (related_ids)
  signal_added (observation-driven)     (Step 2)
        │
        ▼ (inputs.signal_id, related_ids)
  valuation_added                       (Step 3)
        │
        ▼ (parent_record_ids)
  valuation_compared                    (Step 4)
        │
        ▼ (parent_record_ids: valuation_added + valuation_compared)
  institution_action_recorded           (Step 5)
        │
        ▼ (related_ids = action_id)
  signal_added (action-driven)          (Step 6)
        │
        ▼ (related_ids = signal_id, payload.signal_id)
  event_published                       (Step 7, publish_date = D)
        │
        ▼ (next-tick rule, delivery_date = D+1)
  event_delivered (per target_space)    (Step 7, on D+1)
```

Every arrow above is a typed cross-reference field on a record. A
consumer of the ledger can reconstruct this graph from the record
stream alone, without consulting any book — this is the "ledger as
canonical audit trail" property carried over from v0.

## Per-record-type cross-reference vocabulary

To keep the causal graph reconstructable, v1 records reuse a small
vocabulary of cross-reference fields. The shapes match v0's signal
conventions where possible.

| Field                | Shape                  | Semantics                                          |
| -------------------- | ---------------------- | -------------------------------------------------- |
| `related_ids`        | `tuple[str, ...]`      | Domain-level "this record talks about these ids."  |
| `input_refs`         | `tuple[str, ...]`      | "This action / write read these records."          |
| `output_refs`        | `tuple[str, ...]`      | "The writer of this action will create these records." |
| `target_ids`         | `tuple[str, ...]`      | "The action targets these subjects."               |
| `instrument_ids`     | `tuple[str, ...]`      | "The action uses these policy instruments."        |
| `parent_record_ids`  | `tuple[str, ...]`      | Ledger-level lineage. Parents are *ledger record_ids*, not domain ids. |
| `evidence_refs`      | `tuple[str, ...]`      | Auxiliary: external sources, attachments.          |
| `inputs`             | `Mapping[str, Any]`    | Domain-specific keyed inputs (e.g., `{"signal_id": ...}`). |
| `assumptions`        | `Mapping[str, Any]`    | Free-form modeling assumptions.                    |
| `payload`            | `Mapping[str, Any]`    | Free-form domain payload (e.g., gap fields).       |
| `metadata`           | `Mapping[str, Any]`    | Storage-layer metadata. Not part of identity.      |

Cross-references are stored as data. v1 books do **not** validate that
referenced ids exist. Resolver responsibility is on the caller.

## Run-mode guard (v1.2 detail)

`Scheduler` records the run mode used to advance each simulation date:

- `date_tick` — v0-style; `kernel.tick()` advances the clock by one
  date and dispatches all due tasks under `Phase.MAIN`.
- `intraday_phase` — v1.2-style; `scheduler.run_day_with_phases(date,
  sequence)` dispatches due tasks through the declared phase sequence.

The two cannot mix on the same date. Once a date has been advanced one
way, the other path raises. The guard scope is per-date and resets
naturally when the clock advances.

## Why v1 is layered this way

The v1 layout is dictated by three rules from `world_model.md`:

1. **§14 (carried over from v0):** spaces must not directly mutate
   each other. v1 books are kernel-level, so reads remain through
   `DomainSpace`'s shared accessors.
2. **§30+ (added in v1):** behavior is structural. v1 introduces
   record types, books, and orchestrators, but no module decides
   anything on its own. Every mutation is the result of an explicit
   caller invocation.
3. **§40+ (added in v1):** cross-references are data, not validation.
   v1 records may reference ids that do not yet exist; the resolver is
   the caller.

These three rules together explain why v1 took six behavior-adding
sub-milestones (v1.1 – v1.6) plus a freeze (v1.7) rather than a
single behavior-rewrite. Each milestone landed one record type, one
book, or one orchestrator, and verified its invariants before the next
one started. v2 inherits the same sequencing freedom: a v2 calibration
milestone can land Japan public data for one v1 book at a time.

## What v1 architecture does not contain

These items appear in the long-term [`architecture.md`](architecture.md)
or [`v1_roadmap.md`](v1_roadmap.md) but are **not** implemented at v1.7:

- price formation, order matching, last-trade vs mid vs VWAP
- bank credit decisions, default detection, covenant trips
- investor strategy, allocation, rebalancing
- corporate actions, earnings updates, revenue dynamics
- policy reaction functions, rate-setting rules
- regulatory rule changes
- runtime execution of `ExternalFactorProcess` specs (v1 stores them; v2+
  runs them)
- automatic relationship-strength decay
- iterative loops or year-long simulation drivers
- any Japan-specific calibration of any kind
- scenarios, scenario branching, or scenario replay

These belong to v2 / v3 or remain conceptual sketches.
