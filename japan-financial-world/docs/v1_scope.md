# v1 Scope

This document is the **explicit in/out boundary for the v1 milestone** of
the Japan Financial World Engine. It is the v1 freeze contract, analogous
to `v0_scope.md` for v0.

v1 is the **jurisdiction-neutral reference financial system**. It defines
reference content (record types, books, orchestrator) on top of the v0
kernel. It does **not** add autonomous behavior, decision logic, or
calibration. Japan-specific work begins in v2 (public data) and v3
(proprietary data).

## In scope for v1

The following are implemented and tested at the v1 freeze. Every item
below preserves the v0 invariants in [`v0_scope.md`](v0_scope.md).

### Valuation / fundamentals (v1.1)

- `ValuationRecord` — model-based valuation by a valuer of a subject
  (firm / asset / contract / any registered id) at a point in time,
  with `currency` (display unit), `numeraire` (perspective),
  `confidence`, `assumptions`, `inputs`, `related_ids`, `evidence_refs`.
- `ValuationBook` — append-only storage with `add_valuation`,
  `get_valuation`, `list_by_subject`, snapshot. Emits `valuation_added`
  on insert.
- `ValuationGap` — comparator output (`absolute_gap`, `relative_gap`)
  computed against the latest `PriceRecord` for the subject.
- `ValuationComparator.compare_to_latest_price(valuation_id)` — reads
  the originating valuation + latest price; returns a `ValuationGap`;
  emits `valuation_compared` with `parent_record_ids` pointing at the
  `valuation_added` record.
- Currency vs numeraire stored as data; v1 does not convert between
  them.

### Intraday phases (v1.2)

- `IntradayPhaseSpec` and `PhaseSequence` declaring an ordered list
  of intraday phases. The reference sequence is overnight → pre_open →
  opening_auction → continuous_session → closing_auction → post_close.
- `Phase` enum extended with `MAIN` + the six intraday phases. Tasks
  default to `MAIN`, so v0-era tasks fire under both v0 and v1.2 paths.
- `Scheduler.run_day_with_phases(date, sequence)` — dispatches due
  tasks through the declared phase order on a single date.
- Per-date **run-mode guard** that prevents mixing `date_tick` and
  `intraday_phase` advancement on the same simulation date. Scope
  resets naturally on the next date.
- Intraday phase ids are recordable on every v1 record that has a
  `phase_id` field (`InstitutionalActionRecord`,
  `ExternalFactorObservation`).

### Institutional decomposition (v1.3)

- `InstitutionProfile` — institution identity record with
  `institution_id`, `institution_type`, `jurisdiction_code`, `metadata`.
- `MandateRecord` — mandate held by an institution with
  `effective_from`, optional `effective_until`, `policy_targets`,
  `metadata`. Cross-references are stored as data; the book does not
  validate target resolution.
- `PolicyInstrumentProfile` — policy instrument operated by an
  institution with `instrument_id`, `institution_id`, `instrument_type`,
  `metadata`. Distinct from `PolicyInstrumentState` in
  `spaces/policy/state.py`.
- `InstitutionalActionRecord` — central v1.3 record: `action_id`,
  `institution_id`, `action_type`, `as_of_date`, `phase_id`,
  `input_refs`, `output_refs`, `target_ids`, `instrument_ids`,
  `payload`, `parent_record_ids`. Obeys the **four-property action
  contract**: explicit inputs, explicit outputs, ledger record on
  mutation, no cross-space mutation.
- `InstitutionBook` — append-only storage with separate add methods per
  record type, snapshot, and per-record ledger emission
  (`institution_profile_added`, `institution_mandate_added`,
  `institution_instrument_added`, `institution_action_recorded`).

### External world process (v1.4)

- `ExternalFactorProcess` — process *spec* (`process_id`, `factor_id`,
  `process_type`, `parameters`, `frequency`, `phase_id`, `metadata`).
  v1 stores the spec; it does not run the process.
- `ExternalFactorObservation` — single observation of a factor at a
  date (and optional intraday phase) with `value`, `source_id`,
  `process_id`, `metadata`.
- `ExternalScenarioPoint` / `ExternalScenarioPath` — forward path of
  scenario points, stored as data. v1 does not branch or replay.
- `ExternalProcessBook` — append-only storage with snapshot,
  duplicate detection, and per-record ledger emission
  (`external_process_added`, `external_observation_added`,
  `external_scenario_path_added`).
- Constant-process convenience helper:
  `create_constant_observation(process_id, as_of_date, phase_id, …)`.

### Relationship capital (v1.5)

- `RelationshipRecord` — directed relationship between agents:
  `relationship_id`, `from_id`, `to_id`, `relationship_type`,
  `strength`, `as_of_date`, `decay_spec`, `metadata`.
- `RelationshipView` — read-only join helper for "latest strength as
  of date" queries.
- `RelationshipCapitalBook` — append-only storage with strength
  updates emitting `relationship_strength_updated`, new records
  emitting `relationship_added`, snapshot, duplicate detection.
- Decay parameters stored but **not applied** automatically — reads
  return the last-recorded strength deterministically.

### First closed-loop reference economy (v1.6)

- `ReferenceLoopRunner` — thin orchestrator with seven step methods
  that wire existing v1 records into a single causal chain.
- End-to-end ledger trace: `external_observation_added` → `signal_added`
  → `valuation_added` → `valuation_compared` → `institution_action_recorded`
  → `signal_added` → `event_published` → `event_delivered` (D+1).
- The runner does not decide anything. Each step takes explicit
  inputs and delegates the write to the book that owns the record
  type.
- Direct-bus and space-driven publication produce equivalent ledger
  audit trails (the runner explicitly emits `event_published` to
  match what `BaseSpace.emit()` records).

### Cross-cutting v1 contracts

- **Four-property action contract** (v1.3, reused by v1.4 / v1.5 /
  v1.6): every behavior-adjacent record declares explicit inputs,
  explicit outputs, a ledger record, and no cross-space mutation.
- **Cross-references as data** (v1.0-prep, reused throughout):
  records may reference ids that have not yet been created or have
  been removed; the resolver is the caller.
- **Storage separated from behavior**: every v1 module ships a book
  (storage) and, where relevant, an orchestrator (e.g.,
  `ValuationComparator`, `ReferenceLoopRunner`) that reads the book
  and writes back through it.
- **Ledger taxonomy extension**: every new record type has a
  corresponding ledger record type in `RecordType`; no v1 module
  bypasses the ledger.
- **Snapshot determinism**: every v1 book sorts snapshot output by
  id keys, matching the v0 convention.

### Test coverage

- 188 v1 tests across 7 files (`test_valuations.py`,
  `test_phases.py`, `test_phase_scheduler.py`, `test_institutions.py`,
  `test_external_processes.py`, `test_relationships.py`,
  `test_reference_loop.py`).
- v0's 444 tests unchanged.
- Combined `pytest -q` reports `632 passed` at the v1 freeze.

## Out of scope for v1

The following are **not** implemented in v1. They belong to v2 (Japan
public calibration), v3 (Japan proprietary calibration), or future v1+
behavioral milestones if explicitly chartered.

### Autonomous behavior

- price formation, order matching, last-trade vs mid vs VWAP, or any
  market microstructure
- limit order book (full or reference), order priority rules
- bank credit decisions, default detection, covenant trips, collateral
  haircuts, fire-sale logic
- investor strategy, allocation rules, rebalancing, activist behavior,
  mandate enforcement
- corporate actions, earnings updates, revenue dynamics, capex /
  delever / borrow heuristics
- policy reaction functions, rate-setting rules, liquidity operations,
  reserve-ratio adjustments
- regulatory rule changes (capital ratios, leverage caps, LCR,
  large-exposure rules)
- runtime execution of `ExternalFactorProcess` specs (v1 stores them;
  v2+ runs them)
- automatic relationship-strength decay (v1 stores `decay_spec`
  parameters; v2+ behavioral milestones apply them)
- iterative loops, year-long simulation drivers, scenario branching,
  scenario replay

### Reference matching engine

- A reference order matching engine, even a continuous double auction
- A reference price-formation rule, even a clearing-price-from-orders
  rule
- Trade reporting, fees, settlement
- Index construction or rebalancing

### Information dynamics

- News generation in natural language (signals carry structured
  payloads, not prose)
- Source credibility dynamics or accuracy tracking
- Rumor propagation, leak diffusion, audience targeting
- Narrative formation or theme aggregation
- Visibility decay for rumor-style signals

### Calibration

- Any Japan-specific identifier (BOJ, MUFG, Toyota, GPIF, USD/JPY,
  J-GAAP, IFRS, etc.) — that is v2 / v3
- Any Japan public macro time series, listed equities, public sector
  data — that is v2
- Proprietary, expert-knowledge, or paid-data calibration — that is v3
- Process parameter calibration (drift, vol, regime probabilities) —
  v1 stores parameters; v2 picks them
- Detailed accounting standard treatment (J-GAAP, IFRS) — reference
  fundamentals fields only
- Detailed tax treatment

### Cross-jurisdiction modeling

- Multi-jurisdiction economy — v1 has one jurisdiction-neutral economy
  plus an external-process layer
- FX dynamics, capital flows between jurisdictions
- Geopolitical events, sanctions, war shocks

## v1 vs v2 vs v3 boundary

The cleanest way to assign a feature to a milestone is to ask: *what
changes when this feature changes?*

| Trigger for change                              | Layer | Reviewer profile                         |
| ----------------------------------------------- | ----- | ---------------------------------------- |
| Kernel structure (books, projections, transport) | v0   | Frozen at v0.16; only re-opened with documented decision |
| Reference behavior (record shape, book API,     | v1   | Model architects; reviewed for           |
|  orchestrator semantics, action contract)       |       | jurisdiction-neutral correctness         |
| Public Japan data (BOJ rate, listed equities,   | v2   | Japan macro / market specialists;        |
|  publicly available macro time series)          |       | reviewed for source credibility          |
| Proprietary Japan intelligence (paid data,      | v3   | Domain experts; reviewed for licensing   |
|  expert overrides, fund holdings, news feeds)   |       | and proprietary-knowledge handling       |

If a request would require:

- changing a v1 record shape → it is a **v1+ behavioral milestone**, not
  a v2 task.
- adding Japan public data into an existing v1 book → it is a **v2 task**.
- adding paid data, fund holdings, or expert knowledge → it is a **v3
  task**.

## Why these omissions

v1's success condition is **structural completeness** — every reference
record type exists, every cross-reference field is wired, the four-property
action contract is enforced, the ledger remains a complete causal trace,
and the closed-loop runner can chain every record type into a single
end-to-end audit trail.

Adding any out-of-scope item above would require either:

1. mutating kernel-level books outside their explicit contract, or
2. coupling spaces to each other via something other than `EventBus`
   and the network books, or
3. coupling reference behavior to specific calibration inputs (so that
   a calibration change becomes a model change).

All three are forbidden by v0 §14 and v1 §30+. Calibration belongs to
v2 / v3; the model belongs to v1; the structure belongs to v0. Keeping
these layered means each layer can move at its own cadence — v0 frozen,
v1 frozen as of v1.7, v2 evolving with public data, v3 evolving with
proprietary intelligence.

If a future task requests one of the items above, it is a v1+ / v2 /
v3 request, not a v1 request, and the corresponding milestone document
should record the decision to add it.
