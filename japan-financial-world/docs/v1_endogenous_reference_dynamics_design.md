# v1.8.1 Endogenous Reference Dynamics — Design

> **Status:** design-only milestone. No runtime code in v1.8.1.
> **Layer:** FWE Core (public, jurisdiction-neutral).
> **Depends on:** v1.7 frozen reference financial system, v1.8
> experiment harness.
> **Blocks:** v1.8.2 (Routine Engine) and every routine milestone
> after it. Until v1.8.1 lands, the project lacks a written
> direction-of-travel for endogenous activity.

## TL;DR — the core principle

> **External shocks are not the engine of the world. They are
> optional inputs to an already-running endogenous system.**

The v1.7 reference demo and the v1.8 experiment harness, taken
together, are *structurally* clean but *economically* thin: the
seven-step causal chain only fires when an `ExternalFactorObservation`
is recorded. If no observation arrives, the ledger is silent. That
makes the demo look scenario-driven by construction.

The v1.8.1 design correction is: a financial world that only moves
when poked is the wrong abstraction. Real economies post earnings,
mark portfolios, age debt, refresh research views, update
counterparty trust, and decay information freshness **continuously**,
regardless of whether a macro shock arrived this week. v1.8.1 names
this missing layer and gives it a vocabulary — *Routines* — so the
v1.8.2+ milestones can implement it without re-litigating the
direction.

This document is **design-only**. No `world/` or `spaces/` code
changes, no new tests, no new examples are committed here. The
deliverable is a vocabulary, a record-shape proposal, a list of
seven candidate routines, the boundaries those routines must
respect, and a milestone sequence.

## Why scenario-driven is the wrong direction

The v1.7-public-rc1 reference demo wires a single end-to-end chain:

```
ExternalFactorObservation
  → InformationSignal
  → ValuationRecord
  → ValuationGap
  → InstitutionalActionRecord
  → InformationSignal
  → WorldEvent
  → event_delivered
```

If you remove the leading observation, the chain produces nothing.
The v1.8 experiment harness wraps that demo in a config and a
manifest, but the trigger / driver structure is unchanged: every
trace begins with an external observation.

This shape is correct for v1.7's "structural completeness" goal —
proving every record type is wired together. It is **wrong** as a
template for what FWE simulates over time. Two failure modes
follow if v1.8.x copies it without correction:

1. **The world appears dead between shocks.** A run with no
   `ExternalFactorObservation` writes only setup records and dies.
   That is not a financial world; it is a stopwatch waiting for a
   button press.
2. **All endogenous structure migrates into the
   "external_observations" config section.** v1.8.x configs end up
   listing every reporting period, every relationship review, every
   debt-maturity check as a synthetic external "observation," even
   though none of those events is external in nature.

Both failure modes hide the real domain ontology — that financial
worlds run on internal cycles (calendar-driven reporting, periodic
review meetings, contract aging) that exist whether or not the
world is being shocked.

v1.8.1 fixes this by introducing the **Routine** as a first-class
concept distinct from `ExternalFactorObservation`.

## The Routine concept

> A **Routine** is a scheduled, bounded, auditable process that
> the world runs on its own schedule, independent of external
> observations.

Concrete properties:

- **Scheduled.** Bound to a `Frequency` (the v0 enum already
  defines DAILY / MONTHLY / QUARTERLY / YEARLY) and optionally a
  v1.2 `Phase`. The world's clock + scheduler decide *when* it
  runs; the routine itself does not.
- **Bounded.** Reads explicit input refs; writes explicit output
  refs. The reads are declared, not discovered. A routine that
  reads "everything" is over-broad and should be split.
- **Auditable.** Every execution emits a `RoutineRunRecord` to the
  ledger. The record's `parent_record_ids` link back to the inputs
  the routine actually used and forward to the records the routine
  produced.
- **Side-effect-disciplined.** A routine may write to the books it
  *owns* (declared via `owner_space_id`) plus emit signals /
  valuations / institutional actions through the existing v1
  APIs. It must not directly mutate any other space's identity-
  level state or any other book it does not own.
- **Endogenously valid.** A routine can run productively even when
  no `ExternalFactorObservation` exists for that date. If a
  routine genuinely requires an observation, it should be modeled
  as an event handler on the existing observation chain, not as a
  routine.

A routine is the **engine of endogenous activity**. An external
observation, when present, is *optional fuel* that lets specific
routines compute richer outputs — never the trigger that makes the
routine fire at all.

## Proposed record shapes

These shapes are **proposed for v1.8.2** (the Routine Engine
milestone). v1.8.1 commits no record types; the goal here is to
make the v1.8.2 review easier.

### `RoutineSpec`

The static declaration of a routine. Lives in a kernel-level book
analogous to `ExternalProcessBook` but for internal cycles.

| Field | Type | Notes |
| --- | --- | --- |
| `routine_id` | `str` | stable id, e.g. `"routine:corporate_quarterly_reporting:firm:reference_manufacturer_a"` |
| `routine_type` | `str` | controlled vocabulary; see the seven reference routines below |
| `owner_space_id` | `str` | which v0/v1 space owns the side effects; routines may not mutate other spaces' state |
| `frequency` | `Frequency` | DAILY / MONTHLY / QUARTERLY / YEARLY (existing v0 enum) |
| `phase_id` | `str \| None` | optional intraday phase (v1.2) |
| `input_refs` | `tuple[str, ...]` | declared input ids the routine reads each run |
| `output_schema` | `str` | controlled descriptor of what the routine produces (e.g., `"FundamentalsRecord"`, `"ValuationRecord"`, `"RelationshipRecord"`) |
| `enabled` | `bool` | flag to disable a routine without removing it; honors v1's "stored as data" rule |
| `metadata` | `Mapping[str, Any]` | free-form; provenance, parameters, owner notes |

`RoutineSpec` is **immutable per v1 conventions**. Updates produce
a new spec record, not in-place edits.

### `RoutineRunRecord`

The per-execution audit record. Emitted to the ledger every time
the engine executes a routine.

| Field | Type | Notes |
| --- | --- | --- |
| `run_id` | `str` | stable id, e.g. `"run:routine:corporate_quarterly_reporting:firm:reference_manufacturer_a:2026-03-31"` |
| `routine_id` | `str` | reference back to the spec |
| `as_of_date` | `str` | ISO date of the run |
| `phase_id` | `str \| None` | optional intraday phase |
| `input_refs` | `tuple[str, ...]` | the actual inputs read this run; may be a strict subset of the spec's declared inputs (e.g., a missing `ExternalFactorObservation`) |
| `output_refs` | `tuple[str, ...]` | the records this run produced |
| `parent_record_ids` | `tuple[str, ...]` | ledger lineage; links back to records that informed the run |
| `status` | `str` | `"completed"` / `"skipped"` / `"degraded"` / `"errored"` |
| `metadata` | `Mapping[str, Any]` | free-form; counts, warnings, performance hints |

`status` is the key field that makes routines *endogenously valid*:

- `"completed"` — routine ran; all declared inputs were available.
- `"skipped"` — routine intentionally produced nothing this run
  (e.g., not at quarter-end).
- `"degraded"` — routine ran with a subset of inputs (e.g., no
  external observation for the date); the output is meaningful but
  notes the missing input in `metadata`. **A degraded run is a
  valid run, not an error.**
- `"errored"` — routine raised; the engine still emits the record
  so the failure is auditable.

Per the v1 four-property action contract, the routine's
side-effect records (signals, valuations, fundamentals, etc.) are
*referenced* by the run record but are written by the existing v1
APIs that own them.

### Ledger event-type proposal

`routine_spec_added`, `routine_spec_updated`,
`routine_run_started`, `routine_run_completed`,
`routine_run_skipped`, `routine_run_degraded`,
`routine_run_errored`. The exact split between
`routine_run_*` types is a v1.8.2 decision; v1.8.1 only proposes
that *some* split exists so consumers can filter without inspecting
`status`.

## Seven reference routines

Conceptual sketches. None of these are implemented in v1.8.1.

### 1. `corporate_quarterly_reporting`

Models the calendar-driven act of a firm publishing financial
results.

- **Reads:** the firm's existing `FirmState`, the latest known
  fundamentals (if any), the date.
- **Writes:** a new fundamentals-style record (likely
  `ValuationRecord` with `purpose="reporting"` until v2 adds a
  dedicated `FundamentalsBook`), plus an `InformationSignal` of
  type `"earnings_disclosure"`.
- **Must not yet:** project earnings, choose accounting
  treatments, compute peer-relative metrics, react to public
  reactions, or apply jurisdiction-specific accounting standards.
- **Ledger appearance:** `routine_run_completed` →
  `valuation_added` (or future `fundamentals_added`) →
  `signal_added`.
- **Why endogenous:** quarter-ends arrive on the calendar. No
  external shock is required for a firm to file results.

### 2. `valuation_refresh`

A reference research desk re-computes its valuation of a subject.

- **Reads:** the subject's latest fundamentals (from routine 1 if
  available), the latest priced observation (`PriceBook`), any
  recent `InformationSignal`s tagged for the subject, optionally
  the latest `ExternalFactorObservation` for a relevant factor.
- **Writes:** a new `ValuationRecord`. Optionally invokes
  `ValuationComparator.compare_to_latest_price` to emit a
  `ValuationGap` via the existing v1.1 path.
- **Must not yet:** trigger trading on the gap, propagate the gap
  to other valuers, or imply that the gap is "right".
- **Ledger appearance:** `routine_run_completed` →
  `valuation_added` → optionally `valuation_compared`.
- **Why endogenous:** research desks update their views on a
  cadence (monthly DCF refresh, quarterly post-earnings update)
  whether or not anything else moved.

### 3. `debt_maturity_aging`

Walks active contracts in `ContractBook` and updates their
"days-to-maturity" view (a projection, not a stored field).

- **Reads:** the date, the contract's `maturity_date`.
- **Writes:** *no book mutation*. Emits a derived
  `DebtMaturityView` (a projection, in the spirit of
  `BalanceSheetView`) plus, optionally, an `InformationSignal` of
  type `"debt_maturity_imminent"` when a configured threshold is
  crossed.
- **Must not yet:** roll over the debt, refinance, default-trigger,
  change the contract's status, or reprice it.
- **Ledger appearance:** `routine_run_completed`. If a
  threshold-crossing signal is emitted: `signal_added`.
- **Why endogenous:** time passes. Days-to-maturity decrements
  whether or not external macro arrived.

### 4. `bank_review`

A bank periodically reviews its lending exposures and capital
position.

- **Reads:** the bank's `BankState`, `LendingExposure` projections,
  any active `ConstraintEvaluation`s on the bank.
- **Writes:** an `InformationSignal` summarizing the review (a
  `signal_type="bank_periodic_review"`). Optionally an
  `InstitutionalActionRecord` of type `"review_completed"` so the
  v1.3 action vocabulary captures the event without changing
  lending terms.
- **Must not yet:** tighten or loosen lending standards, trigger
  loan calls, decide rate changes, or otherwise re-write
  `ContractBook`.
- **Ledger appearance:** `routine_run_completed` → `signal_added`
  → optionally `institution_action_recorded`.
- **Why endogenous:** scheduled review meetings exist on every
  bank's calendar, with or without a macro event.

### 5. `investor_review`

An investor refreshes its portfolio view and mandate alignment.

- **Reads:** the investor's `InvestorState`, `PortfolioExposure`,
  current `BalanceSheetView`, any subject-relevant valuations from
  routine 2.
- **Writes:** an `InformationSignal` of type
  `"investor_periodic_review"`. Optionally an
  `InstitutionalActionRecord` of type `"review_completed"`.
- **Must not yet:** rebalance, place orders, change allocations,
  exit positions.
- **Ledger appearance:** `routine_run_completed` → `signal_added`
  → optionally `institution_action_recorded`.
- **Why endogenous:** mandate / IPS reviews are calendar-driven.

### 6. `relationship_refresh`

Walks `RelationshipCapitalBook` and emits a refreshed
`RelationshipView` snapshot.

- **Reads:** the latest `RelationshipRecord`s for each tracked
  pair, the date, the `decay_spec` parameters (stored in v1.5 but
  not yet applied).
- **Writes:** a refreshed `RelationshipView` (projection, not a
  new book entry). Optionally a `RelationshipRecord` with an
  updated `strength` if the routine is configured to apply decay.
- **Must not yet:** propagate trust effects into credit decisions
  or allocations, decide which counterparties to escalate /
  de-escalate, or apply jurisdiction-specific keiretsu / main-bank
  rules.
- **Ledger appearance:** `routine_run_completed` → optionally
  `relationship_strength_updated`.
- **Why endogenous:** trust ages whether or not anything happens.

### 7. `information_staleness_update`

Walks the `SignalBook` and tags signals whose `effective_date` is
old relative to the clock.

- **Reads:** the date, every visible signal's `effective_date` and
  `signal_type`.
- **Writes:** a derived `StaleSignalsView` (projection). Optionally
  emits a `signal_freshness_summary` signal so consumers can read
  it through the existing `SignalBook` API.
- **Must not yet:** delete stale signals, adjust their
  `confidence`, reprioritize them in any consumer's view, or apply
  source-specific credibility rules.
- **Ledger appearance:** `routine_run_completed` → optionally
  `signal_added`.
- **Why endogenous:** information ages with the clock.

## Boundaries — what routines may NOT do (yet)

Routines are an *additive* layer. They write records, signals, and
projections through existing v1 APIs. They do not yet:

- **Move prices.** No routine writes to `PriceBook`. Price
  formation is a separate v1+ behavioral milestone.
- **Execute trades.** No routine writes to `OwnershipBook` to
  represent a buy / sell decision. Trading is a separate
  milestone.
- **Change lending terms.** No routine modifies `ContractBook`
  fields (rate, maturity, principal, status). The
  `bank_review` routine emits a *signal* about the review,
  not a contract change.
- **Trigger corporate asset sales / buybacks / issuances.** No
  routine writes new contracts or transfers ownership in the name
  of a corporate action. Corporate actions are a separate
  milestone.
- **Implement discretionary policy.** No routine encodes a Taylor
  rule, a Brainard rule, or any reaction function. The
  `bank_review` and `investor_review` routines stop at "the
  review happened"; the *decisions* downstream of a review are
  separate milestones.
- **Apply Japan-specific calibration.** No routine reads or writes
  any real-institution identifier or jurisdiction-specific
  parameter. v2 will calibrate these routines against Japan
  public data; v1.8.x stays jurisdiction-neutral.

The first four boundaries are **load-bearing**. If v1.8.x violates
any of them, the project has accidentally implemented a behavioral
milestone under a "routine" label, and the four-property action
contract from v1.3 is being routed around. A future code review
should reject any routine PR that touches `PriceBook`,
`OwnershipBook`, or rewrites `ContractBook` fields.

## Sensitivity matrices — not the engine

A natural temptation in v1.8.x is to introduce a *sensitivity
matrix* — a parameterized table that maps observations to impact
estimates (e.g., "a 25 bp rate shock moves bank A's NIM by X
bp"). Such matrices have a place, but **they are not the driving
engine**.

v1.8.1 commits to two principles about sensitivity matrices:

1. **Sensitivity matrices parameterize routines; they do not
   replace them.** A routine's job is to compute "what to record
   on this date for this subject." A sensitivity matrix may
   inform *how* the routine translates an input observation into
   an output record (e.g., a `valuation_refresh` routine could
   look up a sensitivity matrix when an
   `ExternalFactorObservation` is present). The matrix is a
   *parameter*, not a trigger.
2. **A routine that runs without external input must still
   produce something meaningful.** If the only behavior of a
   routine is "look up sensitivity to today's external shock",
   then in the absence of a shock the routine has nothing to do —
   and the design has slipped back into scenario-driven mode.
   v1.8.x reviewers should reject any routine whose `degraded`
   status is "no external observation, so nothing to write." The
   minimum endogenous work (refresh a view, age a contract,
   emit a "review happened" signal, produce a fundamentals
   snapshot) must always be present.

If a future commercial v3 layer wants to ship richer sensitivity
content, it does so as parameter data — `RoutineSpec.metadata`,
calibration packs, or a separate v3 SensitivityBook — never as the
sole driver of routine output.

## Relation to the external world

`ExternalFactorObservation` (v1.4) remains a first-class record
type. It is **optional fuel** for routines, not a trigger.

Concrete rules:

- A routine's `input_refs` may include the latest
  `ExternalFactorObservation` for a factor (e.g., a macro index).
- If the observation is present, the routine uses it (informs
  valuation, parameterizes an impact estimate, etc.).
- If the observation is absent, the routine still runs, with
  `status="completed"` if its declared inputs do not require the
  observation, or `status="degraded"` if the observation was
  declared but missing. Either way, the routine writes its
  endogenous output.

This rule is the operational test for "is this milestone
scenario-driven?" — if an absent observation causes a routine to
emit nothing, the routine has been mis-modeled as an event handler
on the observation chain.

The v1.4 external-process layer continues to handle the cases
where the world *does* receive macro / FX / news inputs. v1.8.x
routines simply stop *requiring* those inputs to fire.

## Proposed milestone sequence

> **Note (revised by v1.8.2):** v1.8.1's original sequence
> committed v1.8.2 to the Routine Engine. The v1.8.2 Interaction
> Topology and Attention design
> ([`v1_interaction_topology_design.md`](v1_interaction_topology_design.md))
> reorders the v1.8.x line so the topology + attention substrate
> lands *before* concrete routines — routines should consume the
> substrate from their first commit rather than being retro-fitted
> later. The authoritative sequence is the table in v1.8.2's
> design doc, mirrored below for reference. The original
> alternative ordering is preserved in the git history of this
> file.

| Milestone | Scope | Code? |
| --- | --- | --- |
| **v1.8.1 Endogenous Reference Dynamics — Design** | This document. Establishes the Routine vocabulary, the seven candidate routines, the boundaries, the relation to sensitivity matrices and external observations. No code. | No |
| **v1.8.2 Interaction Topology and Attention — Design** | `v1_interaction_topology_design.md`. `InteractionSpec` / `InteractionBook` / `AttentionProfile` / `ObservationMenu` / `SelectedObservationSet` proposed shapes; heterogeneous-attention examples; boundaries. No code. | No |
| **v1.8.3 InteractionBook + Matrix / Tensor View** | `InteractionSpec` + `InteractionBook` + the corresponding ledger event types + `build_space_interaction_matrix()`. No routines wired yet. | Yes (kernel) |
| **v1.8.4 RoutineBook + RoutineRunRecord** (storage + audit) | `RoutineSpec` + `RoutineRunRecord` + `RoutineBook` + `routine_can_use_interaction(...)` predicate against `InteractionBook` + `ROUTINE_ADDED` / `ROUTINE_RUN_RECORDED` ledger types. **Storage only**: no execution, no scheduler integration, no concrete routines. **Shipped** (72 tests; 775 → 847 total). | Yes (kernel) |
| **v1.8.5 AttentionProfile / ObservationMenu / SelectedObservationSet** | The §44 attention layer split out from the original v1.8.4 draft. Storage + lookup only; `AttentionBook` plus three new ledger types and the `profile_matches_menu` structural-overlap predicate. **Shipped** (102 tests; 847 → 949 total). | Yes (kernel) |
| **v1.8.6 Routine engine (plumbing)** | Caller-initiated execution service: `RoutineEngine`, `RoutineExecutionRequest`, `RoutineExecutionResult`. Consumes routines + attention selections + interaction compatibility checks to produce `RoutineRunRecord` entries through `RoutineBook.add_run_record`'s existing ledger path. v1.8.6 is plumbing only — no scheduler integration, no automatic firing on `tick()` / `run()`, no concrete routines. **Shipped** (50 tests; 949 → 999 total). | Yes (kernel) |
| **v1.8.5 Corporate Reporting Routine** *(replaced)* | The original v1.8.5 plan was the corporate reporting routine. The realised v1.8.5 instead landed `AttentionProfile` / `ObservationMenu` / `SelectedObservationSet` storage (§47). The corporate reporting routine landed at **v1.8.7** instead, after the routine engine plumbing landed at v1.8.6. See the v1.8.7 row below. | (superseded) |
| **v1.8.7 Corporate Quarterly Reporting Routine** | First concrete routine: `corporate_quarterly_reporting`, on the diagonal `Corporate → Corporate` self-loop. Writes one synthetic `corporate_quarterly_report` `InformationSignal` per call through `RoutineEngine` + `SignalBook`. Synthetic only; no economic computation. **Shipped** (26 tests; 999 → 1025 total). | Yes (one routine) |
| **v1.8.8 Reference Variable Layer — Design** | Names the universe of observable world-context variables (macro / financial / material / energy / technology / real-estate / labor / logistics / expectations) so v1.8.12's investor + bank demo has *something to watch*. Anti-scenario discipline: variables are observable context, not shocks; absence is partial / degraded, not silent. Design only; sequence revised (see `v1_reference_variable_layer_design.md`). | No |
| **v1.8.9 `WorldVariableBook` / `IndicatorBook`** | Code: `ReferenceVariableSpec` + `VariableObservation` records, append-only revision history with `vintage_id` / `revision_of`, `list_released_as_of(...)` helper for look-ahead-bias-free reads. | Yes (kernel) |
| **v1.8.10 Exposure / Dependency Layer** | Code: per-actor declarations of which variables / groups the actor is *exposed to* (e.g., a refinery is exposed to `oil_price_reference`). Distinct from `AttentionProfile.watched_*` (what the actor *watches*); exposure is *what affects* the actor. v1.8.10 stores exposures only; transmission is later. | Yes (kernel) |
| **v1.8.11 `ObservationMenu` builder** | Code: helpers that build an `ObservationMenu` automatically by joining an `AttentionProfile` against `ReferenceVariableBook` (filtered for as-of look-ahead) + `SignalBook` + the other v0/v1 books. | Yes (kernel) |
| **v1.8.12 Investor and Bank Attention Demo** | Two more concrete routines: an investor-side review consuming a value-investor `AttentionProfile` over reference variables, and a bank-side review consuming the bank profile. First place where heterogeneous attention against a shared variable layer produces structurally different ledger traces for two actors looking at the same world. | Yes |
| **v1.9 Living Reference World Demo** | A new (or expanded) reference demo that runs for a full year on the routine + topology + attention + variable stack *without any external observation*. The ledger should contain meaningful records on every quarter-end, every month-end, every relationship review cycle. The replay-determinism gate must hold; the manifest must remain stable. | Yes (demo + tests) |

After v1.9, the next direction is either (a) v2 (Japan public
calibration, populating routine / attention / topology parameters
from public data) or (b) v1+ behavioral milestones that introduce
price formation / trading / credit decisions on top of the routine
+ topology + attention substrate. The v1.9 demo's success is
measured by whether the ledger is *economically thick* even when
no shock is present.

## Open questions / non-decisions

v1.8.1 deliberately does not decide:

- **Where `RoutineBook` lives.** Likely `world/routines.py`
  modeled on `world/external_processes.py`; v1.8.2 will commit.
- **Whether `RoutineSpec` and `RoutineRunRecord` share a
  registry book or live in separate books.** v1.8.2 will commit.
- **Whether the engine integrates with `Scheduler` directly or
  introduces a `RoutineScheduler` adjacent to it.** v1.8.2 will
  commit; preference is integration-over-adjacency to keep the
  scheduler the single source of "what fires on this date".
- **The exact `output_schema` controlled vocabulary.** A v1.8.2
  starter set will be drawn from the seven reference routines
  above; v1.8.5 may extend it.
- **How routines compose.** v1.8.x will NOT introduce
  routine-of-routines or chained-routine semantics. If a routine
  needs another routine's output, it reads via the ledger, the
  same way every other v1 caller does.
- **Sensitivity-matrix schema.** Reserved for a v1.8.6+ milestone
  if any. v1.8.x routines must work without sensitivity matrices.

## Files in this milestone

- `docs/v1_endogenous_reference_dynamics_design.md` — this
  document.
- `docs/fwe_reference_demo_design.md` — updated to cross-link
  this design and to flag that the v1.8 demo is structurally
  complete but not yet endogenous.
- `docs/world_model.md` — gains a short v1.8.1 section
  documenting the principle and the Routine vocabulary so the
  constitutional design log records the direction change.

No `world/`, `spaces/`, `examples/`, or `tests/` file is changed.
The 725-test baseline is unchanged at v1.8.1; v1.8.2+ milestones
will grow the suite.
