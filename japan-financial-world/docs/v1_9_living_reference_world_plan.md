# v1.9 Living Reference World Demo — Plan

> **Status:** v1.9.0 shipped (see `world_model.md` §59 and
> `world/reference_living_world.py`). v1.9.x and v1.9.last remain
> in plan form. This document continues to define the v1.9 line's
> goal, scope, complexity discipline, and boundaries; the v1.9.0
> "Shipped" call-out below records what landed in the first
> sub-release.

## v1.9.0 — what shipped

The v1.9.0 sub-release lands the multi-period sweep:

- `world/reference_living_world.py` exports
  `run_living_reference_world(kernel, *, firm_ids, investor_ids,
  bank_ids, period_dates=None, ...)`,
  `LivingReferenceWorldResult`, and
  `LivingReferencePeriodSummary`. The harness is **pure
  orchestration** over existing v1.8 helpers — no new economic
  behavior.
- `world/reference_attention.py` re-exposes the v1.8.12 selection
  rule publicly as `select_observations_for_profile(kernel,
  profile, menu)`. The private alias is preserved.
- `examples/reference_world/run_living_reference_world.py` runs a
  small synthetic seed kernel (3 firms / 2 investors / 2 banks /
  6 variables / 10 exposures / 4 quarterly periods) and prints a
  compact `[setup]` / `[period N]` / `[ledger]` / `[summary]`
  trace.
- `tests/test_living_reference_world.py` (27 tests) pins shape,
  per-period counts, persistence, ledger-slice equality,
  determinism, complexity budget, no-mutation guarantees,
  no-auto-fire from `tick()` / `run()`, and synthetic-only
  identifiers.

The full suite passes 1368 tests (1341 prior + 27 living-world).
Markdown report wiring is intentionally not yet in v1.9.0 — that
is a v1.9.x polishing step.

## v1.9.1-prep — what shipped

A docs / contract-only sub-release that audits whether v1.9.0's
result + period summary schemas can carry a future
**Living World Trace Report**. Outcome: **no code change
required**. The audit doc and a regression-gate contract test
ship; v1.9.0's `world/reference_living_world.py` is byte-identical
before / after. Documents:

- [`v1_9_living_world_report_contract.md`](v1_9_living_world_report_contract.md)
  — schema cross-check, input policy, output contract,
  Markdown section layout, determinism rules, warning
  vocabulary, mandatory boundary statement, and the **infra
  prelude** finding (the v1.9.0 helper does idempotent
  registration before the period loop, so per-period
  `record_count_created` plus `infra_record_count` equals the
  total chain delta).
- `tests/test_living_reference_world_report_contract.py` (12
  tests) pins the report-critical invariants the v1.9.1 reporter
  will rely on, including the infra-prelude algebra.

The full suite passes 1380 tests (1368 prior + 12 contract).

## v1.9.1 — what shipped

The v1.9.1 sub-release implements the v1.9.1-prep contract:

- `world/living_world_report.py` exports
  `LivingWorldPeriodReport`, `LivingWorldTraceReport`,
  `build_living_world_trace_report`, and
  `render_living_world_markdown`. **Read-only explainability —
  no new economic behavior, no new ledger record types, no new
  kernel state, no scheduler hooks.**
- The reporter takes a `LivingReferenceWorldResult` plus the
  kernel and produces a deterministic immutable report whose
  `infra_record_count + per_period_record_count_total ==
  created_record_count` (the v1.9.1-prep algebra, now enforced
  in `__post_init__`).
- The CLI `examples/reference_world/run_living_reference_world.py`
  gains a `--markdown` flag mirroring v1.8.15's CLI. Default mode
  prints only the operational trace; `--markdown` appends the
  rendered report. Both modes are byte-identical across runs.
- `tests/test_living_world_report.py` (27 tests) pins shape,
  algebra, sorting, byte-identical determinism, every required
  Markdown section heading, the verbatim hard-boundary
  statement, warning emission on tampered chain results, and
  the read-only guarantee against every kernel book and the
  ledger length.

The full suite passes 1407 tests (1380 prior + 27 reporter).

## v1.9.2 — what shipped

The v1.9.2 sub-release adds reproducibility infrastructure for
the living-world demo, mirroring the v1.7-era reference-demo
`replay_utils.py` + `manifest.py` pair:

- `examples/reference_world/living_world_replay.py` exports
  `canonicalize_living_world_result(kernel, result, report=None)`
  and `living_world_digest(kernel, result, report=None)`.
  Canonical view excludes volatile `record_id` / `timestamp` and
  rewrites `parent_record_ids` as slice-relative
  `parent_sequences`. The digest is a 64-char lowercase hex
  SHA-256 over `json.dumps(canonical, sort_keys=True,
  separators=(",", ":"), ensure_ascii=False)`.
- `examples/reference_world/living_world_manifest.py` exports
  `build_living_world_manifest(...)` and
  `write_living_world_manifest(...)`. The manifest carries a
  best-effort git probe (never crashes on missing git), the
  Python version, platform, structural counts, the
  `living_world_digest`, and the v1.9.1 hard-boundary statement.
  Writer is deterministic (`sort_keys=True`, `indent=2`,
  `ensure_ascii=False`, trailing newline), atomic (temp sibling +
  rename), and creates parent directories.
- The CLI gains a `--manifest path/to/m.json` flag.
  `examples/reference_world/run_living_reference_world.py`
  default mode is unchanged; `--markdown` still works;
  `--manifest` writes a deterministic JSON manifest.
- `tests/test_living_world_replay.py` (16) +
  `tests/test_living_world_manifest.py` (19) pin shape, digest,
  determinism, atomic writer, missing-git resilience, and the
  read-only guarantee.

The full suite passes 1442 tests (1407 prior + 35 reproducibility).

## v1.9.3 — what shipped

A **substance-audit milestone**, not a code milestone. v1.9.3
ships:

- `docs/model_mechanism_inventory.md` — per-component
  classification (infrastructure / source-of-truth storage /
  structural model / observation-attention model / routine-process
  model / deterministic demo rule / economic behavior model /
  not yet modeled).
- `docs/behavioral_gap_audit.md` — gap analysis, missing
  mechanism ranking, recommended next path, anti-overclaiming
  language for the public prototype.
- `world/mechanisms.py` — interface contract (`MechanismSpec`,
  `MechanismInputBundle`, `MechanismOutputBundle`,
  `MechanismRunRecord`, `MechanismAdapter` Protocol). No
  behavior. Eight ship-or-die principles documented in the
  module docstring and pinned in the contract test.
- `tests/test_mechanism_interface.py` (39 tests) — required-field
  shape, immutability, validation, JSON round-trip,
  `runtime_checkable` Protocol semantics, vocabulary
  invariants.
- `README.md` opening paragraph and roadmap renumbered to
  reflect the v1.9.3 audit and the recommended next path.

**Numbering note.** The user task that prompted this work was
titled "v1.9.2 …" but v1.9.2 had already shipped as Living World
Replay / Manifest / Digest one milestone earlier. The audit
therefore lands as v1.9.3; downstream milestones shift by one.

**Recommended next path** (from the gap audit):

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.0 Living Reference World Demo | Code. | Shipped |
| v1.9.1-prep Report Contract Audit | Docs + contract test. | Shipped |
| v1.9.1 Living World Trace Report | Code. | Shipped |
| v1.9.2 Living World Replay / Manifest / Digest | Code. | Shipped |
| **v1.9.3** Model Mechanism Inventory + Gap Audit + Mechanism Interface | **Docs + contract.** | **Shipped** |
| v1.9.4 Synthetic Firm Financial Update / Margin Pressure | First `MechanismAdapter`. | Next |
| v1.9.5 Valuation Refresh Lite | `valuation_mechanism` adapter. | Planned |
| v1.9.6 Bank Credit Review Lite | `credit_review_mechanism` adapter. | Planned |
| v1.9.7 Performance Boundary | Sparse-iteration hardening. | Planned |
| v1.9.last | First lightweight public prototype. | Planned |

The full suite passes 1481 tests (1442 prior + 39 mechanism
contract).

## v1.9.3.1 — what shipped

A targeted hardening of the v1.9.3 mechanism interface, before
v1.9.4 introduces the first concrete mechanism. **No economic
behavior; no concrete mechanism; v1.9.0 / v1.9.1 / v1.9.2
modules byte-identical before / after.** Three changes:

- **Deep-ish freeze for JSON-like data.** Two private helpers
  in `world/mechanisms.py` — `_freeze_json_like` and
  `_thaw_json_like` — recursively convert nested mappings to
  `MappingProxyType` and lists / tuples to `tuple`. The four
  immutable dataclasses now apply this on construction, so
  subscript-assign on any nested dict raises `TypeError`.
  `to_dict()` thaws back to plain mutable `dict` / `list` for
  JSON friendliness.
- **Rename `MechanismInputBundle` → `MechanismRunRequest`.** The
  new type splits `evidence_refs` (caller-resolved lineage
  id tuple, verbatim) from `evidence` (resolved data the
  adapter reads, grouped by record-type or logical key).
  Adapters consume `evidence`; they do **not** access kernel /
  books. The caller resolves before invocation.
  `MechanismInputBundle = MechanismRunRequest` is kept as a
  one-line backwards-compat alias for one milestone.
- **Clarify `MechanismRunRecord` ordering responsibility.**
  `input_refs` and `committed_output_refs` are stored
  **verbatim** — no auto-dedupe, no auto-sort. Callers that
  need deterministic replay must order / dedupe their tuples
  themselves; mechanisms that intentionally carry meaningful
  order keep it.

The Protocol's `apply` signature changes accordingly:
`apply(self, request: MechanismRunRequest) -> MechanismOutputBundle`.

`tests/test_mechanism_interface.py` (39 → 65) gains 26 new tests
pinning the deep-freeze property on every nested mutation site,
the `to_dict` thaw round-trip, the `MechanismInputBundle` alias
equality, the rename / new field set, the `evidence` validation
(Mapping required; non-empty string keys; lists become tuples
on freeze), the verbatim `input_refs` order including
duplicates, the new Protocol signature, the freeze helpers
themselves, and the "adapter does not require kernel"
anti-behavior test.

The full suite passes 1507 tests (1481 prior + 26 hardening).

## v1.9 goal

Build a small **synthetic, multi-period, jurisdiction-neutral
"living reference world"** in which recurring reporting, attention,
and review cycles create ledger activity *without* any external
shock. v1.9 is the natural successor to v1.8.14's one-shot chain
harness: where v1.8.14 runs the chain once on a single `as_of_date`,
v1.9 runs it many times across a small calendar.

The point of v1.9 is to demonstrate that the v1.8 stack composes
**over time**, not just over actors. By the end of v1.9 a single
deterministic command should:

- run a 4-quarter (default) sweep over a small set of firms, banks,
  and investors,
- produce a complete ledger trace for every period,
- emit a single human-readable report summarising the year, and
- finish in well under a second on a developer laptop.

## What v1.9 does *not* introduce

v1.9 stays inside the same hard rails as v1.8:

- **No new economic behavior.** v1.9 does not add price formation,
  trading, lending decisions, valuation refresh, impact estimation,
  sensitivity calculation, DSCR / LTV updates, covenant enforcement,
  corporate actions, or policy reactions.
- **No new books or kernel fields.** v1.9 reuses the books v1.8
  shipped.
- **No scheduler auto-firing.** Each period's chain is invoked
  explicitly by the v1.9 demo helper. `tick()` and `run()` never
  fire chain steps.
- **No Japan calibration.** All ids remain synthetic. The forbidden
  token list at `world/experiment.py::_FORBIDDEN_TOKENS` stays
  authoritative.
- **No real data ingestion.** No public-data feeds, no license
  metadata, no external HTTP. v1.9's seed is a tiny inlined
  fixture or a YAML fragment under `examples/reference_world/`.
- **No scenario engine.** No "what if rates rise" branching, no
  shock paths, no stress tests. The v1.8.1 anti-scenario discipline
  stays — variables move only because someone published an
  observation, not because v1.9 invented one in response to a
  policy.

## Scope

v1.9 keeps the demo small enough to read in one sitting:

| Element             | Count | Notes |
| ------------------- | ----- | ----- |
| Firms               | 3 – 5 | Each runs `corporate_quarterly_reporting` once per period. |
| Investors           | 2     | Each builds a per-period menu and selects refs against its `AttentionProfile`. |
| Banks               | 2     | Same. |
| World variables     | 5 – 8 | Mix of fx / rates / credit / real_estate / energy_power groups; reused across periods. |
| Exposure records    | 10 – 20 | Per-actor declarations linking subjects to relevant variables. |
| Periods             | 4 (default), configurable | Each period is an `as_of_date`; a 4-quarter sweep covers one synthetic year. |

Identifiers follow the `*_reference_*` convention
(`firm:reference_manufacturer_a`,
`investor:reference_pension_a`,
`variable:reference_long_rate_10y`, etc.) so the synthetic-only
audit greps under
[`test_inventory.md` §"Auditing for jurisdiction-neutral identifiers"](test_inventory.md)
stay clean.

## Per-period flow

Each of the v1.9 periods walks the v1.8.14 chain end-to-end:

1. **Corporate reporting** — for each firm, call
   `run_corporate_quarterly_reporting(kernel, firm_id=..., as_of_date=...)`.
   One `RoutineRunRecord` + one `corporate_quarterly_report`
   `InformationSignal` per firm per period.
2. **Variable observation refresh** — optionally publish one new
   `VariableObservation` per relevant variable for the period
   (vintage `<year>Q<quarter>_initial`). Carries `as_of_date` /
   `visible_from_date` consistently with v1.8.9.
3. **Menu building + heterogeneous attention** — for each (investor,
   bank) pair, call `run_investor_bank_attention_demo(kernel,
   firm_id=..., investor_id=..., bank_id=..., as_of_date=...)`.
4. **Investor / bank review** — for each actor, call the matching
   `run_*_review` helper with the period's selection ids.
5. **Period trace summary** — call
   `build_endogenous_chain_report(kernel, chain_result)` once per
   period. The reports concatenate into a single year-long Markdown
   trace.

The expected per-period chain length is the v1.8.14 baseline (~18
ledger records on the canonical 1-firm / 1-investor / 1-bank seed)
multiplied roughly by the number of (firm, investor, bank) triples
the demo iterates. v1.9 does **not** explode combinatorially across
all triples — see complexity discipline below.

## Complexity discipline

v1.9 must remain *fast and bounded*. Concrete rules:

- **No dense all-to-all traversal.** Do not iterate `firms × banks
  × investors × variables × exposures` as a Cartesian product.
  Instead, iterate the **sparse edge lists** the v1.8 books already
  provide:
  - `kernel.exposures.list_by_subject(actor_id)` for the variables
    that matter to *this* actor.
  - `WorldVariableBook.list_observations_visible_as_of(as_of_date)`
    for the visible observations on *this* date.
  - `kernel.attention.list_selections_by_actor(actor_id)` for the
    refs *this* actor selected.
- **No path enumeration.** v1.9 does not walk the channel multigraph
  exhaustively; the v1.8.3 tensor view stays a sparse projection,
  not a path generator.
- **No O(N^N) anything.** Constraints in the kernel layer (v0)
  already enforce sparse patterns; v1.9 must not introduce loops
  that violate them.
- **Expected complexity:** roughly **O(periods × actors × relevant_refs)**
  where `actors` ≤ ~8 and `relevant_refs` per actor is bounded by
  exposure count + visible signals. With v1.9's defaults the demo
  should run in well under a second on a developer laptop.
- **No floating-point accumulation across periods.** Counts are
  integers; refs are tuples; statuses are string labels. No drift,
  no rounding, no non-determinism.

Tests must pin the "fast and bounded" property: a budget assertion
on `len(kernel.ledger.records)` after the sweep, and a wall-time
budget loose enough to survive CI variance but tight enough to flag
accidental quadratic loops.

## Same boundaries as v1.8

The v1.8 forbidden behaviors carry over verbatim:

- No price formation, trading, lending decisions, portfolio
  optimization, valuation refresh, impact estimation, sensitivity
  calculation, DSCR / LTV update, covenant enforcement, corporate
  actions, policy reactions.
- No Japan calibration; all identifiers synthetic.
- No real data ingestion; no scenario engine.
- No autonomous execution; each period is caller-initiated.

Tests on the v1.9 demo must verify (at minimum) byte-equality on
`valuations` / `prices` / `ownership` / `contracts` / `constraints`
/ `institutions` / `external_processes` / `relationships` snapshots
across the entire sweep.

## v1.9.last — first public prototype

v1.9.last is the **first lightweight public prototype-quality
milestone** for the project. It is the v1.9 line crystallised into
something a researcher visiting the repo can run in 60 seconds and
walk away with a clear, accurate mental model.

Acceptance criteria for v1.9.last:

- **Runnable demo.** A single command produces a complete trace
  from a clean clone (after `pip install -e ".[dev]"`).
- **Clear README.** `README.md` accurately describes scope,
  capability, and explicit non-capabilities, with no marketing
  claims.
- **Compact CLI output.** The default trace is short and readable;
  `--markdown` produces the deterministic ledger-trace report.
- **Trace report.** Each period's
  [`LedgerTraceReport`](world_model.md) is reachable from the demo;
  for multi-period sweeps the year-long report is a concatenation
  with a single header row.
- **Synthetic-only data.** No real names, no public-data feeds, no
  Japan calibration. Word-boundary forbidden-token check passes.
- **CI green.** All tests, `compileall`, `ruff check .`, gitleaks.
- **No real data.** Examples and tests use the `*_reference_*`
  identifier pattern.
- **No investment-advice claims.** README, docs, and CLI output
  reaffirm the research-software framing.

The detailed public / private surface for v1.9.last lives in
[`public_prototype_plan.md`](public_prototype_plan.md).

## Open questions / non-decisions

v1.9's plan deliberately leaves the following unresolved; they
will be settled by the first sub-release that needs to commit:

- **Variable observation refresh cadence.** Does every variable
  refresh every period, or only the ones whose `frequency` matches?
  Default likely: refresh quarterly variables every period; daily
  variables once per period using the period boundary date.
- **Per-period selection determinism vs cross-period drift.** The
  v1.8.12 selection rule is structural; we expect each period's
  selection to depend only on what is visible on that period's
  `as_of_date`. Cross-period state (e.g., "the bank already
  reviewed this signal last quarter") is not tracked; if v1.9 needs
  it, that is a v1.10+ decision.
- **Reporting of degraded periods.** If a firm fails to publish
  in a quarter (e.g., the routine is registered but the helper
  is not invoked), the period's trace will show fewer records.
  v1.9 should treat this as the v1.8.1 anti-scenario rule
  intends: degraded, not failed.
- **CLI surface.** v1.9's CLI may extend
  `examples/reference_world/run_endogenous_chain.py` with a
  `--periods N` flag, or ship a separate
  `run_living_reference_world.py`. The choice is open and should
  be made when v1.9.0 lands.
