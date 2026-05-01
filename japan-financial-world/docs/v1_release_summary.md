# v1 Release Summary

This document summarizes what the v1 milestone of the Japan Financial World
Engine delivered. It is the canonical "what's in v1" reference; for milestone-
by-milestone design rationale see the per-milestone v1 design documents
listed under [v1 module stack](#final-v1-module-stack), and the running
constitutional design log in [`world_model.md`](world_model.md).

## v1 purpose

v1 builds the **jurisdiction-neutral reference financial system** on top of
the v0 world kernel. v0 froze the structural contract — books, projections,
transport, identity-level state, the four-property `bind()` contract, the
next-tick rule, the no-cross-mutation rule. v1 layers reference *behavior*
and reference *content* on that contract: model-based valuations, intraday
phases, an institutional decomposition vocabulary, an external-process
layer, a relationship-capital layer, and an end-to-end causal chain that
exercises every v1 record type in a single ledger trace.

v1 is **not** Japan-calibrated. v1 does not import the names BOJ, MUFG,
Toyota, GPIF, USD/JPY, J-GAAP, IFRS, or any other jurisdiction-specific
identifier. Reference behavior is expressible against any plausible
financial economy. Japan public calibration belongs to v2; Japan
proprietary / commercial calibration belongs to v3. v1 stays neutral.

The v1 success condition is **not** realism, parameter accuracy, or
loop-driven dynamics. It is whether every v1 module:

- preserves every v0 invariant (no cross-space mutation, append-only
  ledger, deterministic snapshot, next-tick delivery, etc.),
- adds new record types without weakening the existing taxonomy,
- can be linked to every other v1 module through cross-reference fields
  (`related_ids`, `input_refs`, `output_refs`, `parent_record_ids`,
  `evidence_refs`, `inputs`) so the resulting ledger forms a complete
  causal graph end-to-end,
- and stays jurisdiction-neutral and behavior-free in the sense that no
  v1 module decides anything on its own — every record is the result of
  an explicit caller invocation.

`tests/test_reference_loop.py` verifies the end-to-end causal chain.
Combined with all v0 + v1 milestone tests, the suite is **632 / 632
passing** at the v1 freeze.

## How v1 extends v0

v1 follows three additivity rules:

1. **Behavior is structural, not autonomous.** v1 introduces new record
   types (`ValuationRecord`, `MandateRecord`, `InstitutionalActionRecord`,
   `ExternalFactorObservation`, `RelationshipRecord`, etc.) and new books
   (`ValuationBook`, `InstitutionBook`, `ExternalProcessBook`,
   `RelationshipCapitalBook`), but every mutation is the result of an
   explicit caller invocation. v1 modules do not run reaction functions,
   matching engines, or reference dynamics on their own.
2. **Cross-references are data, not validation.** v1 records may reference
   other ids that have not yet been created or have been removed. The
   resolver is the caller's responsibility, not the book's. This rule is
   carried over verbatim from v0 (signals reference `subject_id`s without
   validating them).
3. **Storage is separated from behavior.** Every v1 module ships a book
   (storage, append-only, ledger-emitting) and, where relevant, an
   orchestrator that reads the book and writes back through it
   (e.g., `ValuationComparator`, `ReferenceLoopRunner`). The orchestrator
   never bypasses the book.

These rules let v1 add modules without re-litigating the v0 kernel shape.
v0 stays frozen; v1 is purely additive.

## Final v1 module stack

```
world/                             # v0 kernel (frozen, unchanged in v1)
  ids.py, registry.py, clock.py, scheduler.py, ledger.py, state.py,
  event_bus.py, events.py,
  ownership.py, contracts.py, prices.py,
  balance_sheet.py, constraints.py, signals.py,
  loader.py, validation.py, kernel.py, cli.py

world/                             # v1 additions
  valuations.py                    # v1.1  ValuationRecord, ValuationGap,
                                   #       ValuationBook, ValuationComparator
  phases.py                        # v1.2  IntradayPhaseSpec, PhaseSequence
  institutions.py                  # v1.3  InstitutionProfile, MandateRecord,
                                   #       PolicyInstrumentProfile,
                                   #       InstitutionalActionRecord,
                                   #       InstitutionBook
  external_processes.py            # v1.4  ExternalFactorProcess,
                                   #       ExternalFactorObservation,
                                   #       ExternalScenarioPoint,
                                   #       ExternalScenarioPath,
                                   #       ExternalProcessBook
  relationships.py                 # v1.5  RelationshipRecord,
                                   #       RelationshipView,
                                   #       RelationshipCapitalBook
  reference_loop.py                # v1.6  ReferenceLoopRunner

scheduler.py (extended)            # v1.2  Phase enum: MAIN + 6 intraday phases
                                   #       run-mode guard (date_tick vs
                                   #       intraday_phase, per-date scope)
ledger.py (extended)               # new RecordType members for every v1 book
kernel.py (extended)               # __post_init__ wiring for every v1 book
```

The v1 modules are listed in the order in which they were added. Each
sub-milestone has a design document under `docs/`:

| Milestone | Module(s)                       | Design document                                    |
| --------- | ------------------------------- | -------------------------------------------------- |
| v1.0-prep | (planning only)                 | `v1_reference_system_design.md`,                   |
|           |                                 | `v1_design_principles.md`,                         |
|           |                                 | `v1_module_plan.md`,                               |
|           |                                 | `v1_behavior_boundary.md`                          |
| v1.1      | `valuations.py`                 | `v1_valuation_fundamentals_design.md`              |
| v1.2      | `phases.py`, scheduler ext.     | `v1_intraday_phase_design.md`                      |
| v1.3      | `institutions.py`               | `v1_institutional_decomposition_design.md`         |
| v1.4      | `external_processes.py`         | `v1_external_world_process_design.md`              |
| v1.5      | `relationships.py`              | `v1_relationship_capital_design.md`                |
| v1.6      | `reference_loop.py`             | `v1_first_closed_loop_design.md`                   |
| v1.7      | (freeze; no Python changes)     | this document, `architecture_v1.md`,               |
|           |                                 | `v1_scope.md`, `v2_readiness_notes.md`             |

## What v1 proves

The v1 freeze is a structural-completeness statement. The following are
verified end-to-end at v1.7:

1. **All v0 invariants still hold.** Every v0 test (444 / 444) still
   passes after v1.1 — v1.6 land. No v1 module mutates a kernel-level
   book outside its own contract; no v1 module bypasses the ledger.
2. **The full v1 record-type taxonomy is wired.** `ValuationRecord`,
   `ValuationGap`, `MandateRecord`, `PolicyInstrumentProfile`,
   `InstitutionalActionRecord`, `ExternalFactorProcess`,
   `ExternalFactorObservation`, `ExternalScenarioPath`,
   `RelationshipRecord`, `IntradayPhaseSpec`, plus the corresponding new
   ledger record types (`valuation_added`, `valuation_compared`,
   `institution_profile_added`, `institution_mandate_added`,
   `institution_instrument_added`, `institution_action_recorded`,
   `external_process_added`, `external_observation_added`,
   `external_scenario_path_added`, `relationship_added`,
   `relationship_strength_updated`).
3. **Every v1 module obeys the four-property action contract.** As
   defined in v1.3 and reused throughout v1.4 / v1.5 / v1.6: explicit
   inputs, explicit outputs, ledger record on mutation, no cross-space
   mutation.
4. **Cross-references form a closed causal graph.** The v1.6 reference
   loop links: `ExternalFactorObservation` → `InformationSignal` →
   `ValuationRecord` → `ValuationGap` → `InstitutionalActionRecord` →
   `InformationSignal` → `WorldEvent` → `event_delivered` ledger record.
   `parent_record_ids` connect every step back to its predecessor; the
   audit trail is reconstructable as a graph from the ledger alone.
5. **Intraday phases coexist with daily / monthly tasks.** The v1.2
   scheduler extension dispatches a single calendar day through six
   ordered intraday phases (overnight, pre_open, opening_auction,
   continuous_session, closing_auction, post_close) while preserving
   v0 MAIN-phase semantics for spaces that have not opted in. The
   per-date run-mode guard prevents mixed-mode advancement on the same
   simulation date.
6. **The next-tick rule continues to hold.** v1 never publishes-and-
   delivers an event on the same simulation date. The reference loop
   runner publishes through `EventBus` exactly the same way `BaseSpace`
   does, including the `event_published` ledger record, so direct and
   space-driven publication produce equivalent audit trails.
7. **Snapshot determinism is preserved.** Every v1 book sorts its
   snapshot output by id keys, matching the v0 convention, so kernel
   snapshots remain byte-identical across read-only operations.
8. **Currency vs numeraire is recorded as data, not enforced as logic.**
   v1.1 separates display unit (`currency`) from valuation perspective
   (`numeraire`). v1 stores both; it does not perform conversions.

## What v1 does not do

v1 is structural; it is not behavioral in the autonomous sense. v1 does
**not** implement:

- price formation, order matching, last-trade vs mid vs VWAP, or any
  market microstructure
- bank credit decisions, default detection, collateral haircuts, or
  covenant trips
- investor strategy, allocation rules, rebalancing, or activist behavior
- corporate actions, earnings updates, or revenue dynamics
- policy reaction functions, rate-setting rules, or liquidity operations
- regulatory rule changes (capital ratios, leverage caps, etc.)
- external shock generation (random walks, AR(1), regime switches as
  *dynamics* — v1 stores process specs as data; v2+ runs them)
- valuation-driven trading (gap → order)
- relationship-driven decisions (trust → credit / allocation effect)
- relationship-strength decay applied automatically (decay parameters
  are stored; reads are deterministic)
- a matching engine, even a reference one
- iterative loops (the v1.6 closed-loop runner is a single-shot
  orchestrator, not a year-long simulation driver)
- any Japan-specific calibration of any kind (instrument names, listed
  firms, macro time series, accounting standards, tax rules) — that is
  v2 / v3
- scenarios, scenario branching, or scenario replay
- natural-language news generation (signals carry structured payloads,
  not prose)
- detailed accounting standard treatment (J-GAAP, IFRS) or detailed
  tax treatment

These omissions are not bugs. They are the v1 contract. See
[`v1_scope.md`](v1_scope.md) for the explicit boundary and
[`v1_behavior_boundary.md`](v1_behavior_boundary.md) for the per-module
behavior owner table.

## Test status at freeze

`pytest -q` reports `632 passed`. The breakdown by component is in
[`test_inventory.md`](test_inventory.md). v0's 444 tests are unchanged;
v1 added 188 tests across seven test files:

| v1 test file                  | Tests |
| ----------------------------- | ----- |
| `test_valuations.py`          | 34    |
| `test_phases.py`              | 18    |
| `test_phase_scheduler.py`     | 21    |
| `test_institutions.py`        | 35    |
| `test_external_processes.py`  | 44    |
| `test_relationships.py`       | 31    |
| `test_reference_loop.py`      | 5     |
| **v1 subtotal**               | **188** |
| **v0 + v1 total**             | **632** |

## Relationship to v2 and v3

v1 freezes the **reference behavior contract**. v2 and v3 layer
calibration on top of it without modifying v1 record shapes or v1 book
APIs.

| Layer | Owns                                                                                | Examples                                                              |
| ----- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| v0    | Structure: books, projections, transport, identity, scheduler                       | `BalanceSheetView`, `EventBus`, `DomainSpace`                         |
| v1    | Reference behavior, jurisdiction-neutral, autonomous-behavior-free                  | `ValuationBook`, `InstitutionBook`, `ExternalProcessBook`, `ReferenceLoopRunner` |
| v2    | Japan public calibration                                                            | BOJ as `InstitutionProfile`, listed equities as registry entries, public macro time series as `ExternalFactorObservation` populations |
| v3    | Japan proprietary / expert / paid-data calibration                                  | proprietary fund holdings, paid news feeds, expert override of structural breaks |

The further down the table, the higher the cadence of change. v0 is
frozen; v1 is now frozen as of v1.7; v2 will evolve with public data; v3
will evolve with proprietary intelligence.

For the v2 readiness picture (data-source inventory, entity mapping,
license review, v2 vs v3 boundary), see
[`v2_readiness_notes.md`](v2_readiness_notes.md).

## Why v1 took seven sub-milestones

Each v1 sub-milestone landed *one* piece of reference content and
verified its invariants before the next one started:

- v1.1 had to prove that valuation could be added without entangling
  with `PriceBook` (separate book, comparator joins on read).
- v1.2 had to prove that intraday phases could be added without breaking
  v0 daily tasks (MAIN preserved; run-mode guard per date).
- v1.3 had to prove that institutional behavior could be expressed as
  records-with-cross-references rather than as autonomous decisions
  (the four-property action contract).
- v1.4 had to prove that an external-process layer could store specs
  and observations without running them (no scheduling logic in the
  book).
- v1.5 had to prove that relationship capital could be tracked without
  affecting credit / allocation behavior (decay stored, not applied).
- v1.6 had to prove that all of v1 could be linked into a single
  causal chain through cross-references alone (reference loop runner
  as thin orchestrator).
- v1.7 freezes the result. No Python behavior changes; documentation
  only.

This sequencing is what made v1 implementable as additive layers rather
than an entangled rewrite. v2 inherits the same sequencing freedom: a
v2 calibration milestone can land Japan public data for one v1 book at
a time, without coupling to the rest.
