# Test Inventory

Snapshot of the test suite at **v1.8.12** (`Attention Variable
Hooks + Investor / Bank Attention Demo`): `1257 / 1257 passing`
(444 v0 + 188 v1.0-v1.7 frozen reference + 625 post-v1.7
additions covering reference demo, replay, manifest,
catalog-shape, experiment harness, renamed WorldID tests,
interactions, routines, attention, routine engine, the first
concrete routine, the world-variable storage layer, the exposure
/ dependency storage layer, the observation-menu builder join
service, and the heterogeneous-attention investor / bank
demo).

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

## Reference demo + replay + manifest (v1.7-public-rc1+)

- `test_reference_demo.py` (10) — the FWE Reference Demo runs
  end-to-end, populates eight spaces, emits all seven loop
  record types, links `parent_record_ids` correctly, does not
  mutate seeded prices / ownership, and uses only neutral
  identifiers.
- `test_reference_demo_replay.py` (6) — replay-determinism gate:
  two runs of the demo produce equal canonical ledger traces and
  equal SHA-256 digests.
- `test_reference_demo_manifest.py` (14) — manifest contract:
  required fields, ledger digest matches `replay_utils`, sha256
  hex shape, deterministic write, atomic parent-dir creation,
  graceful git-unavailable / not-a-repo paths, no ledger
  mutation.
- `test_reference_demo_catalog_shape.py` (8) — catalog-shape
  regression: `catalog["loop"]` is a Mapping with all 18 keys
  the runner reads; fails loudly if a degraded YAML parser is in
  use (PyYAML missing).

## Experiment harness (v1.8)

- `test_experiment_config.py` (43) — config schema (load,
  required-field validation, type / value validation, optional-
  section defaults), synthetic-only guard, code-built-config
  validation, base-config digest equivalence with the demo,
  manifest + digest write / skip, unimplemented-override
  boundaries, and a no-side-effects-on-the-demo regression.
- `test_ids.py` (12) — `WorldID` parsing, `build_world_id`,
  invalid-id rejection, `category_for_kind`. (Renamed from
  `tests.py` at v1.7-public-rc1+.)

## Interaction topology (v1.8.3)

- `test_interactions.py` (50) — `InteractionSpec` field
  validation; `InteractionBook` CRUD + duplicate rejection; every
  filter listing (by source space / target space / between
  spaces / interaction type / channel type / routine type);
  disabled-by-default + `include_disabled=True`; self-loops on
  the diagonal (`corporate → corporate`, `investors → investors`,
  `information → information`); channel multiplicity in one cell;
  tensor view shape `S × S × C` and determinism; matrix view
  count / enabled-count / channel-types / interaction-ids and
  determinism; snapshot determinism; ledger emission of
  `RecordType.INTERACTION_ADDED`; kernel wiring; no-mutation
  guarantee against every other v0 / v1 source-of-truth book.

## Reference attention demo + variable hooks (v1.8.12)

- `test_reference_attention_demo.py` (23) — end-to-end shape of
  `run_investor_bank_attention_demo`: result is immutable,
  exactly one `ObservationMenu` per actor is persisted through
  `AttentionBook.add_menu`, exactly one
  `SelectedObservationSet` per actor is persisted through
  `AttentionBook.add_selection`, the canonical investor / bank
  profiles register idempotently; heterogeneous selection
  semantics (the corporate-reporting signal is shared, investor
  picks fx + investor exposures, bank picks real-estate /
  energy + bank exposures, neither picks the other's axes,
  `shared_refs` / `investor_only_refs` / `bank_only_refs`
  agree with set membership); determinism across two fresh
  kernels (same selected refs, same set differences, same menu
  ids); ledger evidence using existing record types only
  (`OBSERVATION_MENU_CREATED` × 2 +
  `OBSERVATION_SET_SELECTED` × 2 per call, no new types); strict
  no-mutation guarantees against `valuations`, `prices`,
  `ownership`, `contracts`, `constraints`, `external_processes`,
  `institutions`, `relationships`; the demo runs no routine and
  emits no signal beyond optional setup; `kernel.tick()` and
  `kernel.run(days=N)` do NOT auto-fire the demo; defensive
  validation on empty `firm_id` / `investor_id` / `bank_id`;
  `as_of_date` defaults to `kernel.clock.current_date` when
  omitted.
- `test_attention.py` (9 new; 102 → 111) — v1.8.12 `AttentionProfile`
  extension acceptance: the four new fields
  (`watched_variable_ids`, `watched_variable_groups`,
  `watched_exposure_types`, `watched_exposure_metrics`) default
  to empty tuples, normalize lists to tuples, reject empty
  strings, round-trip through `to_dict`, appear in the
  `ATTENTION_PROFILE_ADDED` ledger payload, and extend
  `profile_matches_menu` so structural overlap is reported on
  the new dimensions.

## Observation menu builder (v1.8.11)

- `test_observation_menu_builder.py` (50) — `ObservationMenu`
  extension acceptance for the two new fields
  (`available_variable_observation_ids` and
  `available_exposure_ids`), their participation in
  `total_available_count()` and `to_dict()`, rejection of empty
  strings inside the new tuples, and the two new counts
  (`available_variable_observation_count`,
  `available_exposure_count`) in the existing
  `OBSERVATION_MENU_CREATED` ledger payload;
  `ObservationMenuBuildRequest` field validation (parametrized
  rejection of empty required strings, non-bool include flags),
  frozen dataclass, `to_dict` round-trip; `build_menu` end-to-end
  flow writing exactly one `ObservationMenu` through
  `AttentionBook.add_menu` (and exactly one ledger record),
  result-mirrors-stored-menu, default `menu_id` formula
  (`menu:` + `request_id`), `metadata["menu_id"]` override,
  `metadata["status"]` override; date semantics
  (`request.as_of_date` overrides clock; clock default; missing
  date raises `ObservationMenuBuildMissingDateError`);
  exposure→variable join semantics (only variables the actor is
  exposed to surface; no-exposure ⇒ empty
  `available_variable_observation_ids` by default; visibility
  filter (`visible_from_date <= as_of_date`) admits and rejects
  correctly); inactive exposures (effective_to in past) excluded
  from both `available_exposure_ids` and the variable join;
  exposure scoping by `subject_id`; signal collection through
  `SignalBook.list_visible_to` (private signals excluded);
  `available_interaction_ids` union from
  `carried_by_interaction_id` + signal `metadata["interaction_id"]`,
  with deduplication; status auto-derivation
  (`completed` / `empty`) and caller override; include flags
  (`include_signals` / `include_variables` / `include_exposures`)
  skip the corresponding collector; preview path produces no
  persisted menu and no ledger record, returns same content as
  build, prefixes id with `menu:preview:`; read-only collectors
  (`collect_visible_signals`, `collect_active_exposures`,
  `collect_visible_variable_observations`); kernel wiring
  (`kernel.observation_menu_builder` exposed, books and clock
  shared); `kernel.tick()` and `kernel.run(days=N)` do NOT
  auto-build menus; no-mutation guarantee against `SignalBook`,
  `WorldVariableBook`, and `ExposureBook`;
  `DuplicateObservationMenuError` raised when the same
  `menu_id` is built twice.

## Exposure / dependency layer (v1.8.10)

- `test_exposures.py` (59) — `ExposureRecord` field validation
  (parametrized rejection of empty required strings, magnitude /
  confidence bounds in `[0.0, 1.0]`, bool rejection on numeric
  fields, inverted validity windows, empty entries in
  `source_ref_ids`); `is_active_as_of` semantics covering inside
  / before / after / inclusive at bounds / open-ended on each
  side / both bounds open cases; date coercion on optional date
  fields; tuple normalization for `source_ref_ids`; frozen
  dataclass; `to_dict` round-trip; CRUD with
  `DuplicateExposureError` / `UnknownExposureError`;
  cross-reference rule (`variable_id` NOT validated against
  `WorldVariableBook`); every filter listing using a
  six-record realistic synthetic seed (food processor /
  property operator / bank / macro fund / electricity-intensive
  manufacturer / AI-exposed labor sector — exactly the
  examples called out in the v1.8.10 task);
  `list_active_as_of` filtering with both ISO date strings and
  `date` objects; snapshot determinism with `exposure_count`
  and sorted-by-id record list; ledger emission of
  `RecordType.EXPOSURE_ADDED` (`source = subject_id`,
  `target = variable_id`); kernel wiring (`exposures` field +
  shared ledger / clock); no-mutation guarantee against every
  other v0 / v1 source-of-truth book including
  `InteractionBook`, `RoutineBook`, `AttentionBook`, and
  `WorldVariableBook`; `kernel.tick()` and `kernel.run(days=N)`
  do NOT auto-create exposures.

## World variable book (v1.8.9)

- `test_variables.py` (91) — `ReferenceVariableSpec` and
  `VariableObservation` field validation (parametrized rejection
  of empty required strings, empty entries in tuple fields,
  non-numeric / out-of-bounds / bool-typed `confidence`, non-int
  `expected_release_lag_days`); date coercion on every date
  field; numeric (int / float) and string and `None` `value`
  acceptance; frozen dataclasses; `to_dict` round-trip;
  `WorldVariableBook` CRUD with duplicate rejection
  (`DuplicateVariableError` /
  `DuplicateVariableObservationError`) for both records; every
  filter listing for variables (by group / source space /
  related space / consumer space) and observations (by variable
  / `as_of_date` / channel); the visibility-filter rule —
  `visible_from_date` overrides `as_of_date` when present, in
  *both* directions (earlier and later); `latest_observation`
  deterministic tiebreaker (`visibility_date` desc →
  `as_of_date` desc → `observation_id` desc); `latest_observation`
  returns `None` when nothing visible or variable unknown;
  vintage / revision storage and retrieval; cross-reference rule
  (`variable_id` on observation NOT validated against the
  variables store); snapshot determinism with separate counts;
  ledger emission of `VARIABLE_ADDED` and
  `VARIABLE_OBSERVATION_ADDED` (with `simulation_date` from the
  observation's `as_of_date` and `correlation_id` from
  `carried_by_interaction_id`); kernel wiring; no-mutation
  guarantee against every other v0 / v1 source-of-truth book
  including `InteractionBook`, `RoutineBook`, and
  `AttentionBook`; `kernel.tick()` and `kernel.run(days=N)` do
  NOT auto-mutate variables or observations.

## Corporate quarterly reporting routine (v1.8.7)

- `test_corporate_reporting_routine.py` (26) — registration
  helpers (`register_corporate_reporting_interaction` /
  `register_corporate_quarterly_reporting_routine`) are
  idempotent and produce a Corporate → Corporate self-loop
  channel locked to the `corporate_quarterly_reporting`
  routine type, plus per-firm `RoutineSpec`s with the right
  `frequency` / `phase_id` / `missing_input_policy` /
  `allowed_interaction_ids`. The
  `run_corporate_quarterly_reporting` helper produces exactly
  one `RoutineRunRecord` and exactly one
  `corporate_quarterly_report` `InformationSignal` per call,
  linked by id (`signal.related_ids` and
  `signal.metadata["routine_run_id"]` back-reference the run;
  `record.output_refs` forward-references the signal). Default
  `status="completed"` when inputs are present; `status="degraded"`
  when `explicit_input_refs=()` (v1.8.1 anti-scenario discipline);
  date defaults to clock and explicit override honored;
  missing interaction or missing routine spec raise the
  v1.8.6 controlled errors; ledger ordering pinned to
  `routine_run_recorded` then `signal_added`; no-mutation
  guarantee against every other v0/v1 source-of-truth book;
  `kernel.tick()` and `kernel.run(days=N)` do NOT auto-run;
  signal payload + module constants are scanned for the
  forbidden Japan-name token list and asserted clean;
  multiple firms each get their own routine; the same firm
  across two quarters produces two distinct run records and
  signals.

## Routine engine (v1.8.6)

- `test_routine_engine.py` (50) — `RoutineExecutionRequest` field
  validation (parametrized rejection of empty required strings,
  empty entries in tuple fields); frozen dataclass + `to_dict`
  round-trip; `execute_request` end-to-end happy path producing
  exactly one `RoutineRunRecord`; `RoutineExecutionResult`
  mirrors the stored record; default `run_id` format
  (`"run:" + request_id`) and metadata-`run_id` override; date
  semantics (request override > clock fallback > controlled
  `RoutineExecutionMissingDateError`); `collect_selected_refs`
  preserves declaration order across selections and raises
  `RoutineExecutionUnknownSelectionError` on missing ids;
  explicit + selected refs combine deterministically with
  first-occurrence dedup; status defaults
  (`"completed"` with inputs / `"degraded"` without; explicit
  override preserved); interaction compatibility (compatible
  passes; not-in-allowed-list raises; not-admitting-routine-type
  raises; unknown-interaction fails execution with
  `RoutineExecutionIncompatibleInteractionError`); attention
  compatibility (unknown selection raises;
  subset-of-menu NOT enforced per v1.8.5);
  `RoutineExecutionValidationError` on unknown / disabled
  routine; `parent_record_ids` flow from metadata to record;
  `selected_observation_set_ids` stored under run record's
  `metadata`; `validate_request` returns the same shape and
  raises the same controlled errors; `RoutineBook` ledger emits
  exactly one `routine_run_recorded` per request via the
  existing `add_run_record` path; kernel exposes
  `routine_engine`; `kernel.tick()` and `kernel.run(days=N)` do
  NOT auto-execute; no-mutation guarantee against every other
  v0 / v1 source-of-truth book including `InteractionBook`,
  `AttentionBook`, and `RoutineBook` snapshot before-and-after;
  the error hierarchy.

## Attention (v1.8.5)

- `test_attention.py` (102) — `AttentionProfile`,
  `ObservationMenu`, and `SelectedObservationSet` field validation
  (parametrized rejection of empty required strings, non-bool
  `enabled`, empty entries in tuple fields, non-numeric and
  bool-typed `priority_weights`, date coercion on `as_of_date`);
  tuple normalization; frozen dataclasses; `AttentionBook` CRUD +
  duplicate rejection (`DuplicateAttentionProfileError` /
  `DuplicateObservationMenuError` /
  `DuplicateSelectedObservationSetError`) for all three record
  types; every filter listing (`list_profiles_by_actor` /
  `list_profiles_by_actor_type` /
  `list_profiles_by_watched_space` / `list_profiles_by_channel`;
  `list_menus_by_actor` / `list_menus_by_date`;
  `list_selections_by_actor` / `list_selections_by_profile` /
  `list_selections_by_menu` / `list_selections_by_status`);
  multiple profiles per actor allowed; disabled-by-default with
  `include_disabled=True` opt-in; `priority_weights` preserved as
  numeric `dict[str, float]`; `missing_input_policy` defaults to
  `"degraded"`; empty / partial menus accepted; recommended
  selection status vocabulary (`"completed"` / `"partial"` /
  `"degraded"` / `"empty"`) round-trips cleanly;
  `selected_refs` not enforced as subset of menu (documented
  v1.8.5 behavior); `profile_matches_menu` shape, overlap-found,
  no-overlap, omits-unwatched-dimensions, unknown-profile raises,
  unknown-menu raises, no-mutation cases; snapshot determinism
  with separate enabled / disabled counts; ledger emission of
  all three new `RecordType` members (`attention_profile_added`,
  `observation_menu_created` with `simulation_date=as_of_date`,
  `observation_set_selected` with `correlation_id=routine_run_id`);
  kernel wiring; no-mutation guarantee against every other v0 /
  v1 source-of-truth book including `InteractionBook` and
  `RoutineBook`.

## Routines (v1.8.4)

- `test_routines.py` (72) — `RoutineSpec` and
  `RoutineRunRecord` field validation (parametrized rejection of
  empty required strings, non-bool `enabled`, empty entries in
  tuple fields); date coercion on `as_of_date`; tuple
  normalization; `RoutineBook` CRUD for both record types with
  duplicate rejection (`DuplicateRoutineError` /
  `DuplicateRoutineRunError`); every filter listing
  (`list_by_type` / `list_by_owner_space` / `list_by_frequency`
  / `list_for_interaction` for routines;
  `list_runs_by_routine` / `list_runs_by_date` /
  `list_runs_by_status` for runs); disabled-by-default + the
  `include_disabled=True` opt-in; the recommended status
  vocabulary (`"completed"` / `"partial"` / `"degraded"` /
  `"failed"`) round-trips cleanly; `missing_input_policy`
  defaults to `"degraded"` and stores any free-form label;
  `parent_record_ids` preserved on run records;
  `routine_can_use_interaction` predicate covering the positive
  case, the routine-type-not-allowed case, the
  not-in-allowed-interaction-ids case, the unknown-routine
  raises (`UnknownRoutineError`) case, the unknown-interaction
  returns False case, the empty-allowed-types-means-any case,
  and the no-mutation guarantee; snapshot determinism with
  separate enabled / disabled counts; ledger emission of
  `RecordType.ROUTINE_ADDED` and `RecordType.ROUTINE_RUN_RECORDED`;
  kernel wiring; no-mutation guarantee against every other v0 /
  v1 source-of-truth book including `InteractionBook`.

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

### v1.7-public-rc1+ / v1.8 / v1.8.3 / v1.8.4 / v1.8.5 / v1.8.6 / v1.8.7 / v1.8.9 / v1.8.10 / v1.8.11 / v1.8.12 additions

| Component                               | Files | Tests |
| --------------------------------------- | ----- | ----- |
| Reference demo (v1.7-public-rc1)        | 1     | 10    |
| Replay determinism (v1.7-public-rc1+)   | 1     | 6     |
| Manifest (v1.7-public-rc1+)             | 1     | 14    |
| Catalog-shape regression (v1.7-public-rc1+) | 1 | 8     |
| Experiment harness config (v1.8)        | 1     | 43    |
| WorldID tests (renamed from tests.py)   | 1     | 12    |
| Interaction topology (v1.8.3)           | 1     | 50    |
| Routines (v1.8.4)                       | 1     | 72    |
| Attention (v1.8.5 + v1.8.12 schema)     | 1     | 111   |
| Routine engine (v1.8.6)                 | 1     | 50    |
| Corporate quarterly reporting (v1.8.7)  | 1     | 26    |
| World variable book (v1.8.9)            | 1     | 91    |
| Exposure / dependency layer (v1.8.10)   | 1     | 59    |
| Observation menu builder (v1.8.11)      | 1     | 50    |
| Reference attention demo (v1.8.12)      | 1     | 23    |
| **post-v1.7 subtotal**                  | **15**| **625** |

### v0 + v1 + post-v1.7 totals

| Layer                            | Files | Tests |
| -------------------------------- | ----- | ----- |
| v0                               | 35    | 444   |
| v1.0–v1.7 frozen reference       | 7     | 188   |
| post-v1.7 (v1.7-public-rc1+ / v1.8 / v1.8.3 / v1.8.4 / v1.8.5 / v1.8.6 / v1.8.7 / v1.8.9 / v1.8.10 / v1.8.11 / v1.8.12) | 15 | 625 |
| **Total**                        | **57**| **1257** |

## Auditing for jurisdiction-neutral identifiers

The v1 line is jurisdiction-neutral by design (see
`docs/v1_scope.md` and `docs/v1_release_summary.md`). When
auditing the tree for stray Japan-specific identifiers, prefer
the canonical token list maintained at
`world/experiment.py::_FORBIDDEN_TOKENS` (`toyota`, `mufg`,
`smbc`, `mizuho`, `boj`, `fsa`, `jpx`, `gpif`, `tse`, `nikkei`,
`topix`, `sony`, `jgb`, `nyse`) and use **word-boundary
matches**, not raw substring greps.

A naive `grep -RIn "tse\|jgb\|topix"` produces large numbers of
false positives because, e.g., `"tse"` is a substring of
`"itself"`. Use word boundaries instead:

```bash
grep -RInE "\b(toyota|mufg|smbc|mizuho|boj|fsa|jpx|gpif|tse|nikkei|topix|sony|jgb|nyse)\b" .
```

Some tokens (`JPY`, `USD/JPY`, `cash_jpy`, the v1.1 currency
display field) appear deliberately in v0 / v1 modules as
*examples* of free-form unit / currency labels — those are
**not** jurisdiction-specific behavior and are explicitly
allowed by `docs/v1_scope.md`. The forbidden-token list above
is the authoritative gate; new code that introduces any of
those tokens should fail review unless it is explicitly part
of the v2 calibration roadmap.

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
