# FWE Reference Demo — Design

This document describes the **FWE Reference Demo**: a single, synthetic,
jurisdiction-neutral demo world that exercises every v0 + v1 record
type through the existing v1.6 reference loop and produces a complete
causal ledger trace.

> **Note (v1.19.last freeze).** v1.19 froze the public-FWE
> **local-run-bundle / monthly-reference inspection layer** on
> top of the v1.18 scenario-driver inspection layer, the v1.17
> inspection layer, and the v1.16 closed loop. The chain is
> CLI-first: a user runs
> `python -m examples.reference_world.export_run_bundle
> --profile <quarterly_default | monthly_reference>
> --regime <regime> --scenario none_baseline
> --out /tmp/fwe_run_bundle.json` in a terminal to produce a
> deterministic `RunExportBundle` JSON file
> ([`world/run_export.py`](../world/run_export.py),
> [`examples/reference_world/export_run_bundle.py`](../examples/reference_world/export_run_bundle.py));
> the static workbench
> ([`examples/ui/fwe_workbench_mockup.html`](../examples/ui/fwe_workbench_mockup.html))
> then loads that file via `<input type="file">` +
> `FileReader.readAsText` + `JSON.parse` — **no `fetch()`, no
> XHR, no backend, no engine execution from the browser, no
> file-system write**. The `monthly_reference` profile reuses
> the existing v1.16 closed loop on a 12-month synthetic
> schedule and emits 3-5 information arrivals per month
> (51 total) from a jurisdiction-neutral synthetic
> `InformationReleaseCalendar`
> ([`world/information_release.py`](../world/information_release.py)).
> **Information arrival is not data ingestion** — no real
> indicator values, no real release dates, no real
> institutional identifiers; Japan release cadence is a
> design reference only. The `quarterly_default`
> `living_world_digest` stays byte-identical at
> `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
> across the entire v1.19 sequence; the `monthly_reference`
> digest is pinned at
> `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`.
> See
> [`v1_19_local_run_bundle_and_monthly_reference_summary.md`](v1_19_local_run_bundle_and_monthly_reference_summary.md)
> for the v1.19 single-page summary.
>
> **Note (v1.18.last freeze).** v1.18 froze the public-FWE
> **scenario-driver inspection layer** on top of the v1.17
> inspection surface and the v1.16 closed loop — synthetic
> scenario templates ([`world/scenario_drivers.py`](../world/scenario_drivers.py)),
> append-only application + context-shift records
> ([`world/scenario_applications.py`](../world/scenario_applications.py)),
> deterministic event / causal annotations rendered through
> the v1.17.1 display surface plus a markdown scenario report
> ([`examples/reference_world/scenario_report.py`](../examples/reference_world/scenario_report.py)),
> and a static UI scenario selector mock on the v1.17.4
> workbench. The headline runnable surface remains the
> v1.16.last living reference world; v1.18 adds *scenario
> inspectability*, not new economic behaviour. Scenario driver
> is the stimulus, never the response — context shifts are
> append-only and the cited pre-existing context records are
> byte-identical pre / post call. The static workbench scenario
> selector is fixture-switching only — the Python engine is
> invoked from the command line, never from the UI. See
> [`v1_18_scenario_driver_library_summary.md`](v1_18_scenario_driver_library_summary.md)
> for the v1.18 single-page summary.
>
> **Note (v1.17.last freeze).** v1.17 froze the public-FWE
> **inspection layer** on top of the v1.16 closed loop —
> reporting calendar, synthetic display path, event
> annotations, causal timeline, regime comparison report, and a
> single-file static analyst workbench
> ([`examples/ui/fwe_workbench_mockup.html`](../examples/ui/fwe_workbench_mockup.html)).
> The headline runnable surface remains the v1.16.last living
> reference world; v1.17 adds *inspectability*, not new
> economic behavior. The static workbench is fixture-switching
> only — the Python engine is invoked from the command line,
> never from the UI. See
> [`v1_17_inspection_layer_summary.md`](v1_17_inspection_layer_summary.md)
> for the v1.17 single-page summary.
>
> **Note (v1.16.last freeze).** The headline runnable surface is
> now the **v1.9.last living reference world** plus the **v1.12
> endogenous attention-feedback loop** plus the **v1.14 corporate
> financing reasoning chain** (need → funding options → capital
> structure review → financing path) plus the **v1.15 securities
> market intent aggregation** (investor market intent → aggregated
> market interest → indicative market pressure) **with v1.15.6
> feedback** to the v1.14 review and path layers, **closed at
> v1.16** by an evidence-conditioned market-intent classifier
> (v1.16.1 / v1.16.2) and securities-market-pressure → next-period
> attention feedback (v1.16.3). The full loop now reads
> `attention → market intent → aggregated interest → indicative
> pressure → financing review / path → next-period attention`,
> closed deterministically and replayably. The original v1.6
> reference loop demo described below is preserved as the
> single-shot explainer / replay-determinism baseline; the
> multi-period, attention-conditioned, feedback-bounded,
> financing-aware, market-interest-aggregating, **endogenous-
> market-intent-feeding-back-into-attention** living world is the
> demo a v1.16.last reader should run first. See
> [`v1_16_endogenous_market_intent_feedback_summary.md`](v1_16_endogenous_market_intent_feedback_summary.md)
> for the v1.16 single-page summary,
> [`v1_15_securities_market_intent_summary.md`](v1_15_securities_market_intent_summary.md)
> for the v1.15 single-page summary,
> [`v1_14_corporate_financing_intent_summary.md`](v1_14_corporate_financing_intent_summary.md)
> for the v1.14 single-page summary, and
> [`v1_12_endogenous_attention_loop_summary.md`](v1_12_endogenous_attention_loop_summary.md)
> for the v1.12 attention-loop single-page summary.

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

> **v1.8.7 update — first endogenous routine available.** As of
> v1.8.7, the project ships its first concrete routine:
> `world.reference_routines.run_corporate_quarterly_reporting(...)`.
> The routine runs Corporate → Corporate as a self-loop, persists
> one `RoutineRunRecord` through `RoutineEngine`, and publishes one
> synthetic `corporate_quarterly_report` `InformationSignal`. The
> v1.7-era reference demo described in this document is unchanged;
> the v1.8.7 routine is a separate helper that callers may invoke
> for endogenous traces (no external observation required). The
> v1.9 Living Reference World Demo will compose multiple routines
> across firms / banks / investors into a single year-long trace
> that the v1.7-era one-shot demo here cannot produce on its own.

### Update — v1.8.14 endogenous chain harness

> v1.8.14 ships `world/reference_chain.py::run_reference_endogenous_chain`,
> a single orchestration helper that sequences the v1.8.7 corporate
> reporting routine, the v1.8.12 investor / bank attention demo, and
> the v1.8.13 investor / bank review routines into one chain. The
> harness writes nothing itself; every write goes through the existing
> component helpers, which means the chain reuses the same ledger
> record types the v1.7-era reference demo already inspects
> (`routine_added`, `routine_run_recorded`, `signal_added`,
> `attention_profile_added`, `observation_menu_created`,
> `observation_set_selected`, `interaction_added`).
>
> `EndogenousChainResult` names every primary record id and reports the
> ledger slice that contains the chain's writes
> (`ledger_record_count_before`, `ledger_record_count_after`,
> `created_record_ids`). The summary is convenience; the same chain is
> fully reconstructable from
> `kernel.ledger.records[before:after]` — tests pin that the slice's
> `object_id`s match `created_record_ids` exactly, in order. If the
> two ever disagree, **trust the ledger**.
>
> A small CLI lives at
> `examples/reference_world/run_endogenous_chain.py`; running it prints
> a compact human-readable trace and is byte-identical across runs.
> The v1.7-era reference demo described in this document is unchanged
> by v1.8.14 — it remains the *one-shot* baseline. v1.8.14 is its
> compact endogenous companion; v1.9 will sweep this harness over a
> full calendar year.

### Update — v1.8.15 ledger trace report

> v1.8.15 ships `world/ledger_trace_report.py` — a read-only reporter
> that turns the v1.8.14 chain's ledger slice into a deterministic
> `LedgerTraceReport` plus `to_dict` / Markdown projections. It adds
> no new ledger record types, no new economic behavior, and no new
> kernel state; the same record-by-record truth still lives at
> `kernel.ledger.records[start:end]` and the report is reconstructable
> from that slice plus the chain result.
>
> The CLI now accepts `--markdown` to render the report after the
> operational trace. Both modes are byte-identical across runs. The
> v1.7-era reference demo described in this document is unaffected;
> the v1.7 manifest catalog and replay-determinism gates do not
> include the v1.8.15 Markdown, which is presentation rather than a
> reproducibility artifact.

### Update — v1.9.0 Living Reference World Demo

> v1.9.0 ships `world/reference_living_world.py::run_living_reference_world`,
> a sweep helper that runs the v1.8.14 endogenous chain across
> multiple firms and multiple periods on a single kernel. With the
> CLI fixture (3 firms, 2 investors, 2 banks, 6 variables, 10
> exposures, 4 quarterly periods), the demo produces ~100 ledger
> records and finishes in well under a second. Heterogeneous
> attention persists across periods: investor and bank selections
> diverge in every quarter.
>
> v1.9.0 does **not** add a new public-release artifact. The v1.7-era
> reference demo described in this document and the v1.8.0 public
> release tag remain unaffected. v1.9.0's CLI lives at
> `examples/reference_world/run_living_reference_world.py` and is a
> peer of `run_endogenous_chain.py` — neither replaces the v1.7-era
> one-shot demo, which keeps its role as the manifest +
> replay-determinism baseline. The Markdown ledger-trace report
> from v1.8.15 is intentionally not yet wired into v1.9.0; that is
> a v1.9.x polishing step.

### Update — v1.9.1 Living World Trace Report

> v1.9.1 ships `world/living_world_report.py`, the symmetric counterpart
> to v1.8.15's `ledger_trace_report` for the multi-period v1.9.0
> sweep. `build_living_world_trace_report(kernel, living_world_result)`
> produces a deterministic immutable `LivingWorldTraceReport` plus
> `to_dict()` and a Markdown rendering. The Markdown layout is fixed
> (Setup → Infra prelude → Per-period summary → Attention divergence
> → Ledger event-type counts → Warnings → Boundaries) and includes
> the mandatory hard-boundary statement verbatim. The reporter is
> read-only and adds no new ledger record types, no new economic
> behavior, no scheduler hooks. The CLI now accepts `--markdown` —
> two consecutive runs produce byte-identical output. v1.7-era
> reference demo and v1.7 manifest / replay-determinism gates remain
> unaffected.

### Update — v1.9.2 living-world replay / manifest / digest

> v1.9.2 ships
> `examples/reference_world/living_world_replay.py` and
> `examples/reference_world/living_world_manifest.py`, the
> symmetric pair to the v1.7-era `replay_utils.py` /
> `manifest.py` for the v1.9.0 multi-period sweep. Two helpers:
>
> - `canonicalize_living_world_result(kernel, result, report=None)` +
>   `living_world_digest(kernel, result, report=None)` produce a
>   deterministic JSON-friendly canonical view (volatile
>   `record_id` / `timestamp` excluded; `parent_record_ids`
>   rewritten as slice-relative `parent_sequences`) and a
>   64-char lowercase hex SHA-256.
> - `build_living_world_manifest(...)` +
>   `write_living_world_manifest(...)` produce a deterministic
>   JSON manifest (sort_keys=True, indent=2, atomic write) with
>   the `living_world_digest`, structural counts, the v1.9.1
>   hard-boundary statement, a best-effort git probe (never
>   crashes), Python version, and platform.
>
> The CLI gains a `--manifest path/to/m.json` flag. The v1.7-era
> reference demo described in this document and the v1.7
> manifest / replay-determinism gates remain unaffected; v1.9.2 is
> a parallel manifest schema (`living_world_manifest.v1`) for the
> multi-period sweep, not a replacement for the v1.7-era one.

### Update — v1.8.16 freeze / readiness

> v1.8.16 is documentation only — no new code, no test surface
> change. It consolidates v1.8 (v1.8.0 – v1.8.15) into a coherent
> milestone: see [`v1_8_release_summary.md`](v1_8_release_summary.md).
> It also names the v1.9 successor and the v1.9.last public-prototype
> target: [`v1_9_living_reference_world_plan.md`](v1_9_living_reference_world_plan.md)
> and [`public_prototype_plan.md`](public_prototype_plan.md).
> The v1.7-era reference demo described in this document is again
> unaffected; v1.8.16 only adds cross-references and reaffirms the
> separation of "demo as reproducibility artifact" (this document)
> from "demo as explainability artifact" (the v1.8.14 / v1.8.15
> chain + report).

No file under `world/`, `spaces/`, or any existing test file is
modified. The 632 / 632 v0 + v1 test count grows by the number of
new demo tests; no existing test is changed.

### Update — v1.9.last public prototype freeze

> v1.9.last is the **public prototype freeze** of the v1.9 living
> reference world. It is a docs-only milestone: no `world/`,
> `spaces/`, or test file is modified. What lands at v1.9.last is
> a reader-facing freeze of what the public prototype is and what
> it does not claim to be. The headline runnable artifact for
> v1.9.last is `run_living_reference_world.py` (the multi-period
> sweep), not the v1.7-era one-shot demo described in this
> document. The v1.7-era reference demo, the manifest, and the
> replay-determinism gate remain unchanged; v1.9.last is layered
> on top.
>
> See [`v1_9_public_prototype_summary.md`](v1_9_public_prototype_summary.md)
> for the single-page reader summary, [`public_prototype_plan.md`](public_prototype_plan.md)
> for the gate definitions, [`performance_boundary.md`](performance_boundary.md)
> for the loop-shape discipline, and `RELEASE_CHECKLIST.md`'s
> "Public prototype gate (v1.9.last)" section for the local
> verification commands.

## v1.11.2 — demo market regime presets

v1.11.2 adds a `--market-regime` CLI flag to
`run_living_reference_world.py` so the demo can be run under one
of four named synthetic presets without changing any other input:

```bash
python -m examples.reference_world.run_living_reference_world --market-regime constructive
python -m examples.reference_world.run_living_reference_world --market-regime mixed
python -m examples.reference_world.run_living_reference_world --market-regime constrained
python -m examples.reference_world.run_living_reference_world --market-regime tightening
```

When the flag is set, the orchestrator prints a regime banner
before the per-period trace:

```
[regime]  market_regime=<name> (v1.11.2 synthetic preset; no real data, no forecasts)
```

Each preset deterministically alters only the synthetic
`(direction, strength, confidence, time_horizon)` tuples on the
v1.11.0 default 5-market spec set. The v1.11.1 capital-market
readout's overall_market_access_label classifier reaches a
different branch per preset:

| Regime | overall label |
| --- | --- |
| `constructive` | `open_or_constructive` |
| `mixed` | `mixed` |
| `constrained` | `selective_or_constrained` |
| `tightening` | `selective_or_constrained` |

The `tightening` and `constrained` presets share the
`selective_or_constrained` overall label but produce visibly
different per-market tone signatures (rates / credit / equity /
funding direction differ), so a banker viewer can tell them
apart in the rendered Markdown's `## Capital market surface`
table.

**No real data, no calibrated yields, no calibrated spreads, no
forecasts, no recommendations, no transaction execution.** v1.11.2
is a demo-configuration layer — see `world_model.md` §79 for the
binding contract.

Omitting the flag preserves the v1.11.1 default behavior
bit-for-bit. The default-fixture `living_world_digest`
(`209ff81682d331a9700e5c3c8dfac9aa9ecfa028757db6b060f75590249833ea`)
is unchanged when no regime is specified; a test pins this
backward-compatibility contract.
