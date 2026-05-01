# v1.6 First Closed-loop Reference System Design

This document is the design rationale for the v1.6 milestone — the
v1 line's climax. v1.6 connects the v1.1 valuation layer, v1.2
intraday phases, v1.3 institutional decomposition + action contract,
v1.4 ExternalWorld processes, and v1.5 relationship capital into a
single end-to-end causal trace through the kernel.

v1.6 ships **structure, not behavior**. The loop is a reference
loop: it demonstrates that all the v1 record types can be linked
into one chain through their existing books, with no module
mutating state outside its own book and no economic decision being
made. v1.6 is what every later behavioral milestone (and v2 / v3
calibrations) builds on.

For the v1 design statement, see
[`v1_reference_system_design.md`](v1_reference_system_design.md).
For the inherited invariants, see
[`v1_design_principles.md`](v1_design_principles.md). For the
behavior contract, see
[`v1_behavior_boundary.md`](v1_behavior_boundary.md). v1.6 ships the
first concrete chain that satisfies that contract end-to-end.

## Why this is a reference loop, not market behavior

A real closed loop in a financial economy has a specific causal
shape: external events arrive, get reported as information,
incorporated into valuations, compared to observed prices, drive
institutional decisions, and produce new information that flows
back through the system. The loop closes when the new information
re-enters the inputs of the next cycle.

v1.6 implements that *shape* without any of the decisions:

- The "external event" is a constant-process observation, not a
  shock.
- The "information report" is a signal stamped with the
  observation's ID, not an analyst's interpretation.
- The "valuation" is a record with arbitrary `estimated_value`, not
  a DCF computation calibrated to anything.
- The "comparison" uses the existing `ValuationComparator` against
  whatever price was set in the test, not a real market.
- The "institutional decision" is an `InstitutionalActionRecord`
  whose payload merely echoes the gap, not a reaction function
  output.
- The "follow-up information" is another signal whose payload
  carries the action ID, not a press release.
- The "delivery to other parts of the system" is a `WorldEvent`
  through `EventBus`, with the existing v0.3 next-tick rule.

Every step is a record. No step decides. Every link is preserved
through `parent_record_ids` (on the action's ledger record),
`related_ids` (on signals and events), `input_refs` and
`output_refs` (on the action), and `evidence_refs` (available where
relevant). A reviewer looking at the ledger after the run can walk
from any node to its parents and to its children without re-running
the simulation.

That is the v1.6 success condition: the chain is complete, the
chain is auditable, and nothing in the chain decides anything.

## How v1.1 through v1.5 are connected

The loop touches every v1 milestone introduced so far:

```
                         (v1.4)                        (v0.7)
    ExternalFactorObservation  ──► InformationSignal_1
        phase_id=overnight             related_ids=(observation,)
              │                                 │
              ▼                                 ▼
                                         (v1.1)
                                ValuationRecord
                                related_ids=(signal_1,)
                                inputs={signal_id: signal_1}
                                         │
                                         ▼
                                         (v1.1)
                                  ValuationGap
                                via ValuationComparator;
                                ledger valuation_compared
                                has parent_record_ids = (
                                  valuation_added.record_id,
                                )
                                         │
                                         ▼
                                         (v1.3)
                              InstitutionalActionRecord
                              phase_id=post_close
                              input_refs=(valuation,)
                              output_refs=(signal_2,)
                              parent_record_ids=(
                                  valuation_added.record_id,
                                  valuation_compared.record_id,
                              )
                                         │
                                         ▼
                                         (v0.7)
                              InformationSignal_2
                              related_ids=(action,)
                                         │
                                         ▼
                                         (v0.3)
                                  WorldEvent
                              payload={signal_id: signal_2}
                              related_ids=(signal_2,)
                                         │
                                         ▼
                                  EventBus next-tick rule
                                         │
                                         ▼
                              event_delivered records on day D+1
                              for each target space
```

The corresponding v1 modules:

- **v1.4 ExternalWorld Process** — supplies the constant-process
  helper used to record the observation.
- **v0.7 InformationSignal / SignalBook** — stores the two signals
  and lets the event bus reference them by id.
- **v1.1 Valuation Layer** — stores the `ValuationRecord` and
  produces the `ValuationGap` via the `ValuationComparator`. The
  comparator's ledger record carries
  `parent_record_ids = (valuation_added.record_id,)` so the
  comparison is causally linked to its source.
- **v1.3 Institutional Decomposition + Action Contract** — stores
  the `InstitutionalActionRecord`. The action's `input_refs`,
  `output_refs`, `target_ids`, and `parent_record_ids` carry the
  full upstream and downstream graph references.
- **v0.3 WorldEvent / EventBus** — transports the follow-up signal.
  The next-tick rule guarantees that delivery occurs on the day
  after publication, which is what closes the loop in calendar
  terms.

**v1.2 (Intraday Phase Scheduler)** is used through the `phase_id`
fields on the observation and the action. v1.6 stamps the
observation with `"overnight"` and the action with `"post_close"`,
matching the use cases documented in
[`v1_intraday_phase_design.md`](v1_intraday_phase_design.md). v1.6
itself does not run via `run_day_with_phases` — that is a v1.2
feature exercised separately. The phase_id is recorded on the
records as documentation of when conceptually each step happens.

**v1.5 (Relationship Capital)** is available but not used by the
v1.6 loop. The reference loop does not need a relationship to
demonstrate the chain. Relationship-driven loops belong to a
later milestone that introduces relationship-aware behavior.

## The causal chain

Every link in the chain is a backward reference from the new record
to its predecessor. The forward direction is also reachable on
records that explicitly claim authorship over downstream records
(the action's `output_refs`, the event's payload).

| From                                | To                          | Field carrying the link              |
| ----------------------------------- | --------------------------- | ------------------------------------ |
| `ExternalFactorObservation`         | (creates ledger entry)      | `observation_id`                     |
| `ExternalFactorObservation`         | `InformationSignal_1`       | `signal_1.related_ids` includes obs   |
| `InformationSignal_1`               | `ValuationRecord`           | `valuation.related_ids` and `valuation.inputs.signal_id` |
| `ValuationRecord`                   | `ValuationGap`              | `gap.valuation_id`                   |
| `valuation_added` (ledger)          | `valuation_compared` (ledger) | `parent_record_ids` on `valuation_compared` |
| `ValuationRecord`, `ValuationGap`   | `InstitutionalActionRecord` | `action.input_refs` (valuation_id), `action.parent_record_ids` (both ledger records), `action.payload` (gap fields) |
| `InstitutionalActionRecord`         | `InformationSignal_2`       | `signal_2.related_ids` includes action; `action.output_refs` includes signal_2 (forward reference; planned at action time) |
| `InformationSignal_2`               | `WorldEvent`                | `event.payload.signal_id`, `event.related_ids` |
| `WorldEvent`                        | `event_published` (ledger)  | runner records on publish             |
| `WorldEvent`                        | `event_delivered` (ledger)  | written by `BaseSpace` on day D+1     |

The `parent_record_ids` field in particular is what lets a future
audit walk the chain backward from any node. Action records use it
to link to the valuation_added and valuation_compared ledger
entries; the comparator already populated it from valuation_added
in v1.1.

## The 4-property action contract

v1.6 is the first concrete demonstration that the v1.3 4-property
action contract works in a multi-step chain. Restated for the
loop:

1. **Explicit inputs.** The action's `input_refs` lists
   `(valuation.valuation_id,)`. A reviewer can walk from the action
   to the valuation, from the valuation to its referenced signal
   via `related_ids`, from the signal to its referenced
   observation. Every input is named.
2. **Explicit outputs.** The action's `output_refs` lists
   `(planned_output_signal_id,)` — the follow-up signal the runner
   will create in the next step. The action claims authorship over
   that signal even though the action's storage code does not
   create it.
3. **Ledger record.** The action's `institution_action_recorded`
   ledger entry preserves `parent_record_ids` from the action
   record verbatim. A reviewer querying for "what produced this
   action?" finds the valuation_added and valuation_compared
   records and can read them directly.
4. **No direct cross-space mutation.** The action's storage writes
   only to `InstitutionBook` and the ledger. The follow-up signal
   is created by a separate runner step (calling
   `SignalBook.add_signal`); the WorldEvent is created by another
   runner step (calling `EventBus.publish`). The action *describes*
   the side effects via its references but does not perform them.

The v1.6 test
[`test_reference_loop_does_not_mutate_unrelated_books`](../tests/test_reference_loop.py)
enforces this for the other side of the boundary: snapshots of
ownership / contracts / prices / constraints / relationships are
byte-identical before and after the full loop runs. The loop only
writes to its own designated books.

## The ReferenceLoopRunner

`world/reference_loop.py` ships a thin orchestrator,
`ReferenceLoopRunner`, with one method per loop step:

- `record_external_observation`
- `emit_signal_from_observation`
- `record_valuation_from_signal`
- `compare_valuation_to_price`
- `record_institutional_action`
- `emit_signal_from_action`
- `publish_signal_event`

Each method takes explicit inputs (records or ids), builds the next
record with the appropriate cross-references, and delegates the
write to the existing kernel-level book. The runner does not
decide; it only chains the bookkeeping.

The runner is not the only way to drive the loop. A future
behavior module that consumes valuations and produces decisions can
call `add_action_record` directly with the same shape; the runner
exists so that v1.6's test (and any later reference example) can
construct the chain in a single readable script.

The runner's `publish_signal_event` step also records
`event_published` to the ledger so the runner-driven path produces
the same audit trail as the `BaseSpace`-driven path used in v0.3 /
v0.15. Both paths leave a complete `event_published` /
`event_delivered` pair.

## What remains out of scope

v1.6 is structural. It explicitly does not:

- Decide whether the gap should trigger a buy, sell, hold, lend,
  tighten, default, or any other action. The action's `action_type`
  is a free-form string in the test and carries no semantic meaning.
- Move any price. `PriceBook` is read by the comparator and never
  written by the loop.
- Place any order. The follow-up signal does not contain order
  fields; the event does not target an exchange's matching engine.
- Update any agent state. Banking, investors, corporate, real
  estate, and information spaces all receive event_delivered ledger
  records on day D+1 but their `step()` bodies remain v0 no-ops.
- Apply any decay to relationships or process parameters. v1.5
  decay is stored, not applied.
- Calibrate to any specific jurisdiction. The factors, processes,
  signals, valuations, and institutions in v1.6 tests use neutral
  identifiers (`institution:reference_authority`,
  `factor:reference_macro_index`, `firm:reference_a`).
- Use multiple loop iterations. A real closed loop iterates: the
  follow-up signal would feed back into the next valuation cycle.
  v1.6 demonstrates one cycle of the chain; iteration is a future
  behavior milestone that adds the cycling logic on top of this
  shape.

## How v1.6 prepares v2 / v3 calibration

The v1.6 chain is the substrate every later calibration layer plugs
into:

- **v2 (Japan public calibration)** can populate the same chain
  with real Japanese institutions and real public data. The
  `ExternalFactorProcess` becomes a public macro indicator (BoJ
  open-data overnight rate, JGB auction yields, MoF debt issuance
  schedule). The `InformationSignal` becomes a real disclosure
  (TDnet filing, EDINET XBRL, BoJ press release). The
  `ValuationRecord` becomes a real DCF tuned to public earnings
  data. The `InstitutionalActionRecord` becomes a real central-bank
  announcement attributed to the Bank of Japan. The
  `WorldEvent` delivers to the same eight v0 spaces.
- **v3 (Japan proprietary / commercial calibration)** can replace
  any v2 component with proprietary data: a vendor-marked
  fundamentals series, a paid news feed, an expert-curated regime
  classification.

In both cases the chain shape, the record types, and the audit
trail are unchanged. Calibration changes the data; v1.6 freezes
the structure.

## What v1.6 ships

In scope:

- `world/reference_loop.py` with `ReferenceLoopRunner` and its
  seven methods, each documenting which v1 module it touches.
- `tests/test_reference_loop.py` with five tests:
  * `test_reference_loop_creates_full_causal_chain` — walks the
    seven steps and asserts every forward and backward reference.
  * `test_reference_loop_ledger_has_all_expected_record_types` —
    verifies the seven ledger event types are all produced.
  * `test_reference_loop_causal_chain_reachable_from_every_link` —
    asserts each forward field carries the expected reference.
  * `test_reference_loop_does_not_mutate_unrelated_books` —
    snapshots unrelated books before and after, asserts equality.
  * `test_reference_loop_uses_phase_id_on_observation_and_action` —
    asserts `overnight` and `post_close` phase stamps are recorded.

Out of scope:

- Anything in the "What remains out of scope" section above.

## v1.6 success criteria

v1.6 is complete when **all** of the following hold:

1. `ReferenceLoopRunner` exists with the seven step methods, each
   delegating to the existing kernel-level book that owns the
   record type produced.
2. The end-to-end loop test runs without exceptions and produces
   all seven expected ledger event types
   (`external_observation_added`, `signal_added`, `valuation_added`,
   `valuation_compared`, `institution_action_recorded`,
   `event_published`, `event_delivered`).
3. Forward and backward references are preserved at every link:
   `signal_obs.related_ids` includes the observation;
   `valuation.related_ids` includes the signal; the action's
   `input_refs`, `output_refs`, `target_ids`, and
   `parent_record_ids` are populated; the follow-up signal's
   `related_ids` includes the action; the event's payload and
   `related_ids` include the follow-up signal.
4. The action's `parent_record_ids` includes both the
   `valuation_added` and `valuation_compared` ledger record_ids.
5. Event delivery follows the v0.3 next-tick rule: no
   `event_delivered` records on day 1; both targets receive on
   day 2.
6. Ownership, contracts, prices, constraints, and relationships
   are byte-identical before and after the loop runs.
7. The runner is jurisdiction-neutral. v1.6 tests use neutral
   identifiers; no Japan-specific institution, factor, firm, or
   data source appears.
8. All previous milestones (v0 through v1.5) continue to pass.
