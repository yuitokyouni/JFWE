# FWE Reference Demo — Design

This document describes the **FWE Reference Demo**: a single, synthetic,
jurisdiction-neutral demo world that exercises every v0 + v1 record
type through the existing v1.6 reference loop and produces a complete
causal ledger trace.

The demo lives under `examples/reference_world/` (entry point + entity
catalog + expected-story narrative + runnable script). A test in
`tests/test_reference_demo.py` verifies that the script runs and the
expected ledger record types appear.

The demo is part of the **FWE Reference** product layer (see
[`product_architecture.md`](product_architecture.md)). It uses
synthetic entities only and makes no Japan calibration claim.

## Why a reference demo

After v1.7, FWE Core ships as a kernel + reference layer, and the
unit-and-integration tests verify every individual invariant. A new
reader who has *not* read the test suite still does not have a
single, runnable artifact that:

1. Builds a small but populated world (more than the minimal CLI
   smoke world; less than the kernel integration test).
2. Drives that world through the v1.6 reference loop.
3. Produces a ledger trace whose story can be read top-to-bottom
   without having to know the test fixtures.

The reference demo fills that gap. It is the answer to *"what does
FWE actually do?"* — runnable, narrated, synthetic, and small enough
to inspect by hand.

## What the demo represents

The demo represents a **single snapshot of one causal chain** in a
financial world:

- An external macro factor is observed.
- An information source emits a signal that references the
  observation.
- A valuer (e.g., a research desk) issues a valuation of one firm
  based on that signal.
- The valuation is compared to the latest market price; a
  `ValuationGap` is computed.
- An institutional authority (e.g., a reference central bank or
  regulator) records an institutional action that references the
  valuation and the gap.
- A follow-up signal is emitted that references the action.
- A `WorldEvent` is published on the event bus; on the next tick it
  is delivered to two target spaces (banking + investors), producing
  `event_delivered` ledger records.

The result is a ledger that contains every step of the chain and
preserves the cross-references (`related_ids`, `input_refs`,
`output_refs`, `parent_record_ids`, `evidence_refs`) that turn the
trace into a causal graph.

## What the demo does NOT represent

The demo is **not**:

- An economic prediction. No future price, return, default, or
  market outcome is forecast.
- A market impact model. The `WorldEvent` does not propagate into
  trades, quotes, or balance-sheet changes. v1 has no behavior that
  would do so; v2+ will.
- A trading simulation. No agent buys, sells, rebalances, or
  hedges. The portfolios in the demo are static.
- A Japan-calibrated model. Every entity name uses the
  `*_reference_*` naming convention and stays jurisdiction-neutral.
- A scenario or scenario branching. There is one demo run; the
  outcome is deterministic.
- A stress test. The demo does not stress balance sheets, capital
  ratios, liquidity, or constraints. It records one institutional
  action and walks away.
- An information-dynamics model. Signals are emitted, but no
  rumor propagation, narrative aggregation, or credibility decay
  happens.

The demo's value is in **causal traceability** — proving that v1's
record types, books, and orchestrator can be wired into a single
end-to-end audit trail. It is not a prediction tool of any kind.

> **Direction note (v1.8.1):** the v1.7 reference demo is
> *structurally* complete but *economically* thin. Every record in
> its trace is downstream of one `ExternalFactorObservation`; if
> no observation arrives, the demo writes only setup records. That
> is correct for v1.7's "structural completeness" goal but is the
> wrong default for what FWE simulates over time. The v1.8.1
> Endogenous Reference Dynamics design
> ([`v1_endogenous_reference_dynamics_design.md`](v1_endogenous_reference_dynamics_design.md))
> introduces the **Routine** as the primitive of endogenous
> activity and explicitly demotes external observations from
> "trigger" to "optional input." A v1.9 successor demo (the
> Living Reference World Demo) will produce a meaningful ledger
> for a full year *without* any external observation. This
> v1.7-era demo is preserved unchanged as the structural-baseline
> artifact.

## Demo composition

The demo populates a kernel with:

| Category               | Count | IDs                                                                                                                 |
| ---------------------- | ----- | ------------------------------------------------------------------------------------------------------------------- |
| Firms                  | 5     | `firm:reference_manufacturer_a`, `firm:reference_manufacturer_b`, `firm:reference_retailer_a`, `firm:reference_property_a`, `firm:reference_utility_a` |
| Banks                  | 2     | `bank:reference_bank_a`, `bank:reference_bank_b`                                                                    |
| Investor types         | 3     | `investor:reference_pension_a`, `investor:reference_passive_a`, `investor:reference_macro_a`                        |
| Exchange (1 market)    | 1     | `market:reference_equity_market`                                                                                    |
| Real-estate market     | 1     | `market:reference_real_estate_central`                                                                              |
| Information source     | 1     | `source:reference_news_outlet`                                                                                      |
| Policy authority       | 1     | `authority:reference_central_bank` (also exposed as institution `institution:reference_central_bank`)               |
| External factors       | 2     | `factor:reference_macro_index`, `factor:reference_fx_pair`                                                          |

All eight v0 spaces (Corporate, Banking, Investors, Exchange, Real
Estate, Information, Policy, External) are registered. Banking and
Investors are the event-bus delivery targets in step 7. The other
six are populated to demonstrate that the demo world is genuinely
multi-space — not just a runner with two stub spaces.

The `examples/reference_world/entities.yaml` file is the canonical
entity catalog; the runnable `run_reference_loop.py` consumes it.

## How to run the demo

From the `japan-financial-world/` directory:

```bash
python examples/reference_world/run_reference_loop.py
```

The script:

1. Builds a `WorldKernel` and registers all eight spaces.
2. Loads the entity catalog from
   `examples/reference_world/entities.yaml`.
3. Seeds one external process (`process:reference_macro_index`)
   and one priced subject (`firm:reference_manufacturer_a`) so the
   reference loop has the inputs it needs.
4. Walks the seven-step `ReferenceLoopRunner` chain.
5. Advances the clock by two days so the next-tick `WorldEvent`
   delivery completes.
6. Prints a summary: ledger record count, breakdown by event type,
   the seven causal-chain record IDs, and which target spaces
   received the event delivery.

The script returns the populated kernel for further interactive
inspection if imported as a module.

## Ledger records to inspect

After a demo run, the ledger contains (at minimum) these event
types — in this order:

| Step | Ledger event type            | Source / cause                                            |
| ---- | ---------------------------- | --------------------------------------------------------- |
| —    | `object_registered` (×N)     | Registry registrations for every entity in `entities.yaml` |
| —    | `*_state_added` (×N)         | One per identity-level state record in each space         |
| —    | `external_process_added`     | Macro process spec                                        |
| —    | `price_updated`              | Seed price for the valued firm                            |
| —    | `institution_profile_added`  | Central-bank institution profile                          |
| 1    | `external_observation_added` | Step 1 — observe macro index                              |
| 2    | `signal_added`               | Step 2 — signal references observation                    |
| 3    | `valuation_added`            | Step 3 — valuation references signal                      |
| 4    | `valuation_compared`         | Step 4 — comparator emits gap; parent = step-3 record id  |
| 5    | `institution_action_recorded`| Step 5 — action; parents = step-3 + step-4 record ids     |
| 6    | `signal_added`               | Step 6 — follow-up signal references action               |
| 7    | `event_published`            | Step 7 — `WorldEvent` published                           |
| 7+1  | `event_delivered` (×2)       | After day-2 tick, banking + investors each receive one    |

The full chain is reconstructable from `record.parent_record_ids` and
domain `related_ids` / `input_refs` / `output_refs` fields. See
[`expected_story.md`](../examples/reference_world/expected_story.md)
for the per-record narrative.

## Why this is useful for future stress testing

v1 does **not** implement stress testing. The demo is not a stress
test. But v2+ stress-testing milestones will rely on the same
properties the demo exercises:

- **Deterministic causal graph.** A stress test that follows "shock
  → action → signal → consequence" needs every step to be a record,
  every record to be discoverable from the ledger, and every cross-
  reference to hold. The demo proves the v1 record set + orchestrator
  can do this end-to-end.
- **Append-only audit trail.** A stress test cannot rewrite history.
  The v0 / v1 ledger contract makes that impossible by construction.
- **No-mutation guarantee on unrelated books.** A stress chain that
  touches valuations and signals must not silently change ownership
  or contracts. The demo's ledger and snapshot diff show that the
  chain only writes where it claims to.
- **Cross-references as data, not validation.** A stress scenario
  may reference a hypothetical institution that has not yet been
  registered. v1's rule that resolution is the caller's job lets a
  v2+ stress run plug in scenarios incrementally without ordering
  constraints.

When a future v2 (or v1+ behavioral milestone) introduces real
stress-test logic, the *shape* of its chain — observation → signal →
valuation → action → consequence — is what the demo validates today.
The demo's job is to make sure that shape is concrete, runnable, and
inspectable before any specific stress logic is layered on top.

## Replay determinism gate

A second run of the same demo must produce the same canonical
ledger trace as the first run. This is enforced by
`tests/test_reference_demo_replay.py` and is a v0 / v1 invariant
("the ledger is a reproducible, byte-stable causal record for a
given input").

The helpers in `examples/reference_world/replay_utils.py` define
the canonical view:

- **`canonicalize_ledger(kernel) -> list[dict]`** — strips two
  fields that vary across runs by construction:
    - `record_id`: derived from a stable hash of a body that
      includes `timestamp.isoformat()`. Different timestamp →
      different record_id.
    - `timestamp`: defaults to `datetime.now(timezone.utc)` when a
      record is appended; wall-clock dependent.
  And rewrites one field that embeds the volatile `record_id`:
    - `parent_record_ids` (a tuple of `record_id` strings) becomes
      `parent_sequences` (a tuple of `int` sequence indices that
      point to the parent's position in the same ledger).
  Everything else — `record_type`, `simulation_date`, `source`,
  `target`, `object_id`, `payload`, `metadata`, `correlation_id`,
  `causation_id`, `space_id`, `agent_id`, `confidence`, etc. — is
  preserved verbatim.
- **`ledger_digest(kernel) -> str`** — SHA-256 hex digest of
  `json.dumps(canonical, sort_keys=True, separators=(",", ":"),
  ensure_ascii=False)`. Two runs of the same demo produce the
  same 64-char digest.

If a future change to v0 / v1 introduces non-determinism into a
field that the canonical view preserves, the replay tests will
fail and a milestone document must record either (a) a fix to
remove the non-determinism, or (b) an explicit decision to add
the new field to the volatility-allowlist with a justification.

The replay gate is strictly a *correctness* check, not a
*calibration* check. It does not assert that the trace contains
the right values — only that running twice produces the same
values. Calibration assertions (e.g., "the macro process value
should be X") live in dedicated tests under
`tests/test_reference_demo.py` and `tests/test_reference_loop.py`.

## Reproducibility manifest

A reference demo run can produce a small JSON **manifest** that
captures just enough metadata to identify the run later:

- `manifest_version` — schema version of the manifest itself.
- `run_type` — fixed string `"fwe_reference_demo"` so a manifest
  can be routed correctly without inspecting other fields.
- `git_sha` / `git_dirty` / `git_status` — best-effort probe of the
  current commit. If `git` is not on `PATH`, or the working
  directory is not a git repo, the values are `None` and
  `git_status` records `"git_unavailable"` / `"not_a_repo"` /
  `"error"`. The builder never crashes on git absence.
- `python_version` — `sys.version.split()[0]` (e.g. `"3.12.7"`).
- `platform` — `platform.platform()` (e.g.
  `"macOS-15.0-arm64-arm-64bit"`).
- `input_files` — mapping `path -> {"sha256": hex64, "status":
  "ok"|"missing"}`. The default input is the demo's
  `entities.yaml`. Missing files are recorded with
  `status="missing"` rather than crashing the build.
- `ledger_digest` — the SHA-256 hex digest produced by
  `replay_utils.ledger_digest(kernel)`. Identical to the value the
  replay-determinism gate checks.
- `ledger_record_count` — `len(kernel.ledger.records)`.
- `summary` — the `DemoSummary` returned by `run_reference_loop.run()`,
  serialized as a dict.

Two helpers live in
`examples/reference_world/manifest.py`:

- `build_reference_demo_manifest(kernel, summary, *, input_paths=None)
  -> dict` — assemble the manifest. Reads only; does not mutate the
  kernel or its ledger.
- `write_manifest(manifest, output_path) -> None` — write the
  manifest as deterministic JSON (`sort_keys=True`, `indent=2`,
  `ensure_ascii=False`, trailing newline). Two writes of the same
  manifest dict are byte-identical. Parent directories are created
  if missing; the write is atomic via a temporary sibling +
  rename.

Scope discipline:

- The manifest is for **reproducibility**, not for
  experiment-tracking, scenario archives, or proprietary
  provenance.
- The manifest contains **no private or proprietary content** —
  no expert notes, no paid-data identifiers, no client metadata.
  Per `docs/public_private_boundary.md`, those belong in JFWE
  Proprietary's separate, private manifest schema, not here.
- The manifest is **not** a substitute for the replay-determinism
  gate. The replay test verifies that two runs produce the same
  trace; the manifest records *which* trace was produced. Both
  matter.

If a future calibration milestone (v2 / v3) needs richer
provenance fields (license id, vendor product code, snapshot id,
NDA flags), that schema is a separate document — see
`docs/roadmap/jfwe_proprietary_calibration.md`. The fields in
this manifest do not change to accommodate v2 / v3 needs.

## Why the demo uses fictional entities

Three reasons:

1. **Public-release hygiene.** Per
   [`public_private_boundary.md`](public_private_boundary.md), the
   public repo must not contain real-institution names tied to
   simulation outcomes. A demo named after real banks, firms, or
   policy authorities would cross that line; a demo named with
   `*_reference_*` synthetic ids cannot.
2. **No calibration implied.** Real names imply calibrated
   parameters. The demo's parameters (the macro index base value,
   the seed price, the valuation, the gap) are illustrative round
   numbers chosen for traceability, not realism. Synthetic ids make
   the lack of calibration explicit.
3. **Reusable across jurisdictions.** v2 (Japan public) and v3
   (Japan proprietary) will *populate* the same record shapes with
   real data; v1's demo provides the structural template. A
   jurisdiction-neutral demo is the cleanest hand-off, because
   nothing in the demo presumes any specific market.

## Boundary with other parts of the repo

The reference demo is **layered on top of** the existing v0 + v1
code; it adds **no new behavior**. Specifically, the demo:

- imports only `WorldKernel`, the eight space classes, the v1 books
  (`ValuationBook`, `InstitutionBook`, `ExternalProcessBook`,
  `RelationshipCapitalBook`), and `ReferenceLoopRunner`;
- never extends, subclasses, or monkey-patches any of those;
- writes only through the public APIs already used by the v1.6
  closing test (`tests/test_reference_loop.py`);
- contains no decision logic, no reaction function, no matching
  engine, and no scenario branching.

If a future request would require any of the above, that request is
a v1+ behavioral milestone, not an extension of this demo.

## Files in this milestone

- `docs/fwe_reference_demo_design.md` — this document.
- `examples/reference_world/README.md` — short entry-point.
- `examples/reference_world/entities.yaml` — entity catalog.
- `examples/reference_world/expected_story.md` — per-step narrative
  of the ledger trace.
- `examples/reference_world/run_reference_loop.py` — runnable
  script using only existing v0 / v1 APIs.
- `examples/reference_world/replay_utils.py` —
  `canonicalize_ledger(kernel)` / `ledger_digest(kernel)` helpers
  used by the replay-determinism gate.
- `examples/reference_world/manifest.py` —
  `build_reference_demo_manifest(kernel, summary, ...)` /
  `write_manifest(manifest, output_path)` helpers for the
  reproducibility manifest.
- `tests/test_reference_demo.py` — verifies the script runs and
  produces the expected ledger event types.
- `tests/test_reference_demo_replay.py` — replay-determinism
  gate (two runs → same canonical trace + same SHA-256 digest).
- `tests/test_reference_demo_manifest.py` — manifest contract
  (required fields, hash format, deterministic write,
  git-unavailable handling, no ledger mutation).

No file under `world/`, `spaces/`, or any existing test file is
modified. The 632 / 632 v0 + v1 test count grows by the number of
new demo tests; no existing test is changed.
