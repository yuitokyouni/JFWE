# Test Inventory

Snapshot of the test suite at the **v1.7 freeze**: `632 / 632 passing`
(444 v0 + 188 v1).

This inventory is grouped by what each component verifies. The numbers in
parentheses are test counts per file. Run the full suite with:

```bash
python -m pytest -q
```

The v0 portion (`444 passed`) is unchanged from v0.16 freeze. The v1
portion (`188 passed`) was added across milestones v1.1 – v1.6; v1.7 is
documentation-only and adds no new tests.

## Identity, time, and registration

- `test_yaml_load.py` (5) — YAML world specs load into typed records;
  malformed inputs raise `ValueError`.
- `test_validation.py` (4) — basic registry-object validation rules.

## Registry, scheduler, clock, ledger, state

- `test_clock.py` (11) — calendar advance, `is_month_end /
  is_quarter_end / is_year_end` boundary detection, advance-by-day
  semantics.
- `test_scheduler.py` (10) — task registration, frequency dispatch,
  due-task ordering, phase placeholder, deterministic order across
  ties.
- `test_ledger.py` (3) — record append, query, JSONL round-trip.
- `test_state.py` (5) — initialize_object, snapshot creation,
  immutability of snapshots, state-hash determinism.

## Cross-cutting kernel smoke

- `test_world_kernel_smoke.py` (1) — empty kernel runs for one year
  with two no-op tasks; verifies expected `task_executed` counts and
  monthly snapshot count.
- `test_spaces_smoke.py` (2) — three empty spaces (Corporate / Investor
  / Bank) coexist and fire at their declared frequencies.

## Inter-space transport (v0.3)

- `test_event_bus.py` (10) — publish, collect_for_space, next-tick
  delivery rule, broadcast (with source exclusion), at-most-once
  per-target delivery, pending-vs-delivered split.
- `test_space_signal_flow.py` (5) — emitter and observer spaces
  exchange a `WorldEvent` through the kernel; ledger records
  `event_published / event_delivered`.

## Network books (v0.4)

- `test_ownership.py` (14) — add/get/list positions, per-(owner|asset)
  views, transfer with insufficient-balance / unknown-source / self-
  transfer rejection, snapshot determinism, ledger writes.
- `test_contract_network.py` (13) — add_contract / get_contract /
  list_by_party / list_by_type, status update, duplicate rejection,
  ledger writes.
- `test_price_book.py` (11) — append-only history, `get_latest_price`,
  per-asset history retrieval, snapshot, ledger writes.

## Projections

- `test_balance_sheet.py` (18) — quantity × latest_price valuation,
  borrower-vs-lender contract treatment via `metadata`, collateral
  summation, missing-price tolerance, NAV computation, snapshot, no-
  mutation guarantee, kernel wiring.
- `test_constraints.py` (23) — `ConstraintRecord` / `ConstraintEvaluation`
  CRUD, all five constraint types (max_leverage, min_net_asset_value,
  min_cash_like_assets, min_collateral_coverage,
  max_single_asset_concentration) with ok / warning / breached /
  unknown paths, ledger writes, no-mutation guarantee.

## Information layer (v0.7)

- `test_signals.py` (25) — `InformationSignal` validation, six
  visibility values, effective-date filter, `mark_observed`, snapshot,
  ledger writes, cross-book isolation.
- `test_signal_event_flow.py` (4) — `WorldEvent` payload references a
  `signal_id`; observer fetches the signal through `SignalBook`;
  transport / visibility independence.

## DomainSpace (v0.10.1)

- `test_domain_space.py` (10) — `bind()` contract (idempotent / fill-
  only / explicit refs win / no hot-swap), three read-only accessors,
  graceful unbound behavior, kernel wiring.

## Domain spaces — identity state and integration

Each domain space has two test files: a unit-style state file
covering CRUD / snapshot / ledger / unbound behavior, and an
integration file covering kernel wiring, projection reads, and
no-mutation guarantee.

### Corporate (v0.8)

- `test_corporate_state.py` (16) — `FirmState` dataclass, CRUD,
  snapshot, ledger.
- `test_corporate_space_integration.py` (9) — kernel wiring, balance-
  sheet / constraint / signal reads, no-mutation, scheduler
  compatibility.

### Banking (v0.9)

- `test_bank_state.py` (21) — `BankState`, `LendingExposure`, CRUD,
  metadata-only role inference rule.
- `test_bank_space_integration.py` (12) — kernel wiring, lending-
  exposure derivation, no-mutation, scheduler compatibility.

### Investors (v0.10)

- `test_investor_state.py` (21) — `InvestorState`, `PortfolioExposure`
  with missing-data tolerance.
- `test_investor_space_integration.py` (13) — kernel wiring, three-
  book join (ownership × prices × registry), no-mutation.

### Exchange (v0.11)

- `test_exchange_state.py` (27) — `MarketState`, `ListingState` with
  composite-key relation, cross-listing support, snapshot.
- `test_exchange_space_integration.py` (10) — kernel wiring, price /
  signal reads, price/listing independence, no-mutation.

### Real Estate (v0.12)

- `test_real_estate_state.py` (28) — `PropertyMarketState`,
  `PropertyAssetState` with foreign-key relation, unenforced FK rule.
- `test_real_estate_space_integration.py` (10) — kernel wiring, price
  / signal reads, no-mutation.

### Information (v0.13)

- `test_information_state.py` (27) — `InformationSourceState`,
  `InformationChannelState`, channel-vs-signal visibility independence.
- `test_information_space_integration.py` (9) — signal queries by
  source / type / visibility, registration-independence, no-mutation.

### Policy (v0.14)

- `test_policy_state.py` (20) — `PolicyAuthorityState`,
  `PolicyInstrumentState`, list_instruments_by_authority filter.
- `test_policy_space_integration.py` (5) — kernel wiring, signal
  reads, no-mutation, scheduler compatibility.

### External (v0.14)

- `test_external_state.py` (21) — `ExternalFactorState` with `unit`
  field, `ExternalSourceState` (no tier — distinguished from
  InformationSourceState).
- `test_external_space_integration.py` (5) — kernel wiring, signal
  reads, no-mutation, scheduler compatibility.

## Cross-space integration (v0.15)

- `test_world_kernel_full_structure.py` (16) — the v0 closing test.
  Builds a populated `WorldKernel` with all eight spaces, runs for
  365 days, verifies per-frequency task counts, every space's read
  accessors, EventBus next-tick delivery to two target spaces,
  transport / visibility independence, no source-of-truth book
  mutation across all reads, and a complete ledger audit trail.

## Valuation / fundamentals layer (v1.1)

- `test_valuations.py` (34) — `ValuationRecord` validation,
  `ValuationBook` CRUD / snapshot / ledger, currency vs numeraire
  storage, `ValuationGap` computation, `ValuationComparator`
  comparing against the latest `PriceRecord`, `valuation_compared`
  ledger emission with `parent_record_ids` lineage, missing-price
  tolerance, no-mutation guarantee.

## Intraday phase scheduler (v1.2)

- `test_phases.py` (18) — `IntradayPhaseSpec` / `PhaseSequence`
  validation, ordered traversal, duplicate / unknown phase
  rejection, phase-id storage on records that carry `phase_id`.
- `test_phase_scheduler.py` (21) — `Scheduler.run_day_with_phases`
  dispatch through six intraday phases, MAIN-phase compatibility
  with v0 tasks, per-date run-mode guard rejecting mixed
  `date_tick` / `intraday_phase` advancement, scope reset on next
  date, deterministic order across phase ties.

## Institutional decomposition (v1.3)

- `test_institutions.py` (35) — `InstitutionProfile`,
  `MandateRecord`, `PolicyInstrumentProfile`,
  `InstitutionalActionRecord` validation; `InstitutionBook` CRUD /
  snapshot / ledger; the four-property action contract (explicit
  inputs / outputs / ledger record / no cross-space mutation);
  duplicate detection per record type; cross-references stored as
  data without resolution.

## External world process layer (v1.4)

- `test_external_processes.py` (44) — `ExternalFactorProcess` spec
  (constant / random_walk / ar1 / regime_switch),
  `ExternalFactorObservation` with `phase_id` field,
  `ExternalScenarioPoint` / `ExternalScenarioPath` storage,
  `ExternalProcessBook` CRUD / snapshot / ledger,
  `create_constant_observation` helper, duplicate detection,
  no-runtime-execution guarantee.

## Relationship capital (v1.5)

- `test_relationships.py` (31) — `RelationshipRecord` validation,
  directed-pair semantics, `RelationshipCapitalBook` CRUD /
  snapshot / ledger, `relationship_strength_updated` on update,
  `RelationshipView` latest-strength queries, `decay_spec` stored
  but not applied automatically, deterministic reads.

## First closed-loop reference economy (v1.6)

- `test_reference_loop.py` (5) — the v1 closing test.
  `ReferenceLoopRunner` chains `ExternalFactorObservation` →
  `InformationSignal` → `ValuationRecord` → `ValuationGap` →
  `InstitutionalActionRecord` → `InformationSignal` → `WorldEvent`
  → `event_delivered` (D+1). Verifies that every cross-reference
  field is wired correctly, that `parent_record_ids` form a complete
  causal graph reconstructable from the ledger alone, that
  direct-bus and space-driven publication produce equivalent ledger
  audit trails, and that the runner does not mutate any state
  outside the books that own each record type.

## Test count by component

### v0 components (frozen at v0.16)

| Component                        | Files | Tests |
| -------------------------------- | ----- | ----- |
| YAML load / validation           | 2     | 9     |
| Clock / scheduler / ledger / state | 4   | 29    |
| Kernel / spaces smoke            | 2     | 3     |
| Event bus + signal flow          | 2     | 15    |
| Network books                    | 3     | 38    |
| Projections (balance sheet, constraints) | 2 | 41 |
| Signals (signals + flow)         | 2     | 29    |
| DomainSpace                      | 1     | 10    |
| Domain spaces (state + integration) × 8 | 16 | 254 |
| Cross-space integration          | 1     | 16    |
| **v0 subtotal**                  | **35**| **444** |

### v1 components (frozen at v1.7)

| Component                        | Files | Tests |
| -------------------------------- | ----- | ----- |
| Valuation / fundamentals (v1.1)  | 1     | 34    |
| Intraday phase scheduler (v1.2)  | 2     | 39    |
| Institutional decomposition (v1.3) | 1   | 35    |
| External world process (v1.4)    | 1     | 44    |
| Relationship capital (v1.5)      | 1     | 31    |
| Reference loop (v1.6)            | 1     | 5     |
| **v1 subtotal**                  | **7** | **188** |

### v0 + v1 totals

| Layer                            | Files | Tests |
| -------------------------------- | ----- | ----- |
| v0                               | 35    | 444   |
| v1                               | 7     | 188   |
| **Total**                        | **42**| **632** |

## How to interpret a failing test

If a test fails after this freeze, one of three things is true:

1. The freeze invariants have been broken. This is a regression and
   should be the default suspicion — every test in this inventory
   passed at v1.7 freeze.
2. The test environment differs from the freeze environment (e.g., a
   Python version that changed dict ordering, a timezone issue
   affecting date conversions). Check the test name against the
   inventory above to determine which invariant is being tested.
3. New code intentionally relaxed an invariant. In that case the
   relaxing commit should have updated this inventory and a milestone
   document explaining the decision.
