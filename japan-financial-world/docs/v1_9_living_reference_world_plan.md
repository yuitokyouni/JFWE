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

## v1.9.4 — what shipped

The **first concrete mechanism** built on the v1.9.3.1 hardened
interface contract. The framing was corrected during pre-v1.9.4
review: the milestone is **not** "Firm Financial Update" — a firm
does not update its financial statements simply because it
receives operating or financing pressure. The shipped name is
**Reference Firm Operating Pressure Assessment Mechanism**.

- `world/reference_firm_pressure.py` exports
  `FIRM_PRESSURE_MODEL_ID`,
  `FIRM_PRESSURE_MODEL_FAMILY = "firm_financial_mechanism"`,
  `FIRM_PRESSURE_SIGNAL_TYPE = "firm_operating_pressure_assessment"`,
  `FIRM_PRESSURE_MECHANISM_VERSION = "0.1"`,
  `FirmPressureMechanismAdapter` (frozen dataclass implementing
  the v1.9.3 / v1.9.3.1 `MechanismAdapter` Protocol), and
  `run_reference_firm_pressure_mechanism(kernel, *, firm_id,
  as_of_date=None, evidence_refs=None,
  variable_observation_ids=None, exposure_ids=None,
  corporate_signal_ids=None, ...)` as the caller-side helper.
- The adapter computes five synthetic pressure dimensions in
  `[0, 1]` (input-cost / energy-power / debt-service /
  fx-translation / logistics) plus the mean `overall_pressure`,
  and proposes one signal. The adapter is read-only against the
  kernel (it doesn't accept a kernel argument; it reads
  `request.evidence` only) and never mutates the request (the
  v1.9.3.1 deep-freeze property carries; tests re-pin it).
- The caller helper resolves observations from
  `WorldVariableBook` (hydrating each with `variable_group`),
  exposures from `ExposureBook`, and optional corporate signals
  from `SignalBook`; commits the one proposed signal through
  `kernel.signals.add_signal`; returns the
  `FirmPressureMechanismResult` (request + output + run_record
  + signal_id + pressure_summary) for audit.

**Hard boundary** (embedded verbatim in the signal's metadata):
*"pressure_assessment_signal_only; no financial-statement
update; no decision; no auto-trigger"*.

`tests/test_reference_firm_pressure.py` (28 tests) pins the
contract: adapter satisfies `MechanismAdapter`; spec is valid;
adapter doesn't accept a kernel; can run without a kernel;
missing evidence → degraded (not crash); pressure scores in
`[0, 1]`; `overall_pressure` = mean of five; clamping at 1.0;
deterministic across two fresh kernels seeded identically;
request not mutated; signal mapping has every required field;
caller helper commits exactly one signal; `evidence_refs`
preserved verbatim on the `MechanismRunRecord`; full no-mutation
guarantee against valuations / prices / ownership / contracts /
constraints / variables / exposures / institutions /
external_processes / relationships / routines / attention /
interactions; only one new ledger record per call (the
`signal_added` from `SignalBook.add_signal`); synthetic-only
identifiers (word-boundary forbidden-token check).

The full suite passes 1543 tests (1515 prior + 28 firm-pressure).

## v1.9.5 — what shipped

The **second concrete mechanism** on the v1.9.3.1 hardened
interface. Consumes the v1.9.4 firm-pressure-assessment signal
and proposes one **opinionated synthetic** `ValuationRecord`.
This is not a true valuation model — it is a synthetic reference
mechanism showing how diagnostic pressure and selected evidence
can produce an auditable valuation claim.

- `world/reference_valuation_refresh_lite.py` exports
  `VALUATION_REFRESH_MODEL_ID`,
  `VALUATION_REFRESH_MODEL_FAMILY = "valuation_mechanism"`,
  `VALUATION_REFRESH_MECHANISM_VERSION = "0.1"`,
  `VALUATION_REFRESH_METHOD_LABEL = "synthetic_lite_pressure_adjusted"`,
  `ValuationRefreshLiteAdapter` (frozen dataclass implementing
  the v1.9.3 / v1.9.3.1 `MechanismAdapter` Protocol),
  `ValuationRefreshLiteResult`, and
  `run_reference_valuation_refresh_lite(kernel, *, firm_id,
  valuer_id, as_of_date=None, pressure_signal_ids=...,
  corporate_signal_ids=..., selected_observation_set_ids=...,
  variable_observation_ids=..., exposure_ids=...,
  baseline_value=..., currency="unspecified",
  numeraire="unspecified",
  pressure_haircut_per_unit_pressure=None,
  confidence_decay_per_unit_pressure=None, ...)` as the
  caller-side helper.

- The adapter applies a synthetic linear pressure-haircut to a
  caller-supplied baseline value (default coefficients: 0.30
  haircut per unit pressure; 0.40 confidence decay per unit
  pressure). At pressure 1.0 the baseline is trimmed by 30% and
  confidence drops to 0.6. The adapter is read-only against the
  kernel (no kernel argument; reads `request.evidence` and
  `request.parameters` only) and never mutates the request.

- The caller helper resolves the v1.9.4 pressure signal +
  optional auxiliary evidence from the kernel books, calls the
  adapter, commits the one proposed `ValuationRecord` through
  `kernel.valuations.add_valuation`, and returns the
  `ValuationRefreshLiteResult` (request + output + run_record +
  valuation_id + valuation_summary) for audit.

**Hard boundary** (embedded verbatim in the valuation's metadata
as four flags + one boundary string): `no_price_movement`,
`no_investment_advice`, `synthetic_only`, `model_id`,
`pressure_signal_id`, plus *"valuation_claim_only;
no_price_movement; no_investment_advice; synthetic_only;
no_canonical_truth_claim"*.

`tests/test_reference_valuation_refresh_lite.py` (28 tests)
pins the contract: adapter satisfies `MechanismAdapter`; spec
valid; doesn't accept a kernel; can run without a kernel;
missing pressure evidence yields `status="degraded"` with
conservative output (baseline-only or `None`); algorithm
correctness (zero-pressure, full-pressure, custom-coefficient
paths); deterministic across two byte-identical requests;
request not mutated; valuation proposal carries every required
field including the method label; metadata carries the four
boundary flags and the `pressure_signal_id` link;
`related_ids` includes the pressure signal id; caller helper
commits exactly one `ValuationRecord`; `evidence_refs`
preserved verbatim on the `MechanismRunRecord`; full
no-mutation guarantee against prices / ownership / contracts /
constraints / variables / exposures / institutions /
external_processes / relationships / routines / attention /
interactions; only one new ledger record per call (the
`valuation_added` from `ValuationBook.add_valuation`);
synthetic-only identifiers (word-boundary forbidden-token
check).

The full suite passes 1571 tests (1543 prior + 28 valuation).

## v1.9.6 — what shipped

The **integration milestone** that wires v1.9.4 firm-pressure-
assessment and v1.9.5 valuation-refresh-lite into the multi-period
sweep. Until v1.9.6, both mechanisms were standalone caller helpers
tested in isolation; `run_living_reference_world` did not exercise
them per period. v1.9.6 closes that gap.

The integrated per-period flow:

```
corporate quarterly reporting       (per firm)
    -> firm operating pressure assessment   (per firm)
    -> heterogeneous attention              (per actor)
    -> valuation refresh lite               (per investor × firm)
    -> investor / bank review               (per actor)
```

Changes:

- `world/reference_living_world.py`: `LivingReferencePeriodSummary`
  extended additively with `firm_pressure_signal_ids`,
  `firm_pressure_run_ids`, `valuation_ids`,
  `valuation_mechanism_run_ids`. New phases inserted in
  `run_living_reference_world`. New parameters
  `firm_baseline_values` and `valuation_baseline_default`.
- `examples/reference_world/run_living_reference_world.py`: firm
  exposures added to the seed fixture so the v1.9.4 mechanism
  produces non-zero output. The `[period N]` trace line now
  includes `pressures=...` and `valuations=...` columns.
- `world/living_world_report.py`: per-period table extended with
  `pressures` and `valuations` columns; `LivingWorldPeriodReport`
  gains `pressure_signal_count` and `valuation_count` fields.
- `examples/reference_world/living_world_replay.py`: the v1.9.2
  canonical view includes the four new id tuples so the
  deterministic SHA-256 digest reflects pressure / valuation
  activity.
- `tests/test_living_reference_world.py`: fixture extended with
  firm exposures; record-count budget updated (per period now
  ~31 records; lower bound 124, upper bound 250); 9 new tests
  pinning per-period pressure / valuation counts, the
  `valuation.metadata["pressure_signal_id"]` link to the same
  firm's pressure signal (proves v1.9.5 actually consumed v1.9.4's
  output), and the boundary flags on every committed valuation.
  No-mutation test narrowed: `valuations` now expected to grow,
  pinned by a separate exact-count test.

The valuation `request_id` is built per (investor, firm, period)
in the v1.9.6 helper (the v1.9.5 default formula didn't include
the valuer, which would have aliased multi-investor mechanism run
ids on the same firm/date).

**Hard boundary carried forward.** Every committed pressure
signal still stamps `pressure_assessment_signal_only` in
metadata; every committed valuation still stamps
`no_price_movement` / `no_investment_advice` / `synthetic_only`.
No price formation, no trading, no lending decisions, no firm
financial statement updates, no canonical-truth valuation, no
investment advice.

The full suite passes 1580 tests (1571 prior + 9 integration).

**Recommended next path (renumbered).** Bank Credit Review Lite
shifts to v1.9.7; Performance Boundary to v1.9.8; v1.9.last
remains the public prototype freeze.

## v1.9.7 — what shipped

The **third concrete mechanism** + its integration into the
multi-period sweep. Bank Credit Review Lite is a synthetic
diagnostic note generator — **not a lending decision model**, not
a default detector, not a covenant enforcer. Every produced
signal is a recordable note about *what the bank looked at* and
*how that evidence aggregated as a pressure score*; it is not a
record of *what the bank decided to do*.

- `world/reference_bank_credit_review_lite.py` exports
  `BANK_CREDIT_REVIEW_MODEL_ID`,
  `BANK_CREDIT_REVIEW_MODEL_FAMILY = "credit_review_mechanism"`,
  `BANK_CREDIT_REVIEW_MECHANISM_VERSION = "0.1"`,
  `BANK_CREDIT_REVIEW_SIGNAL_TYPE = "bank_credit_review_note"`,
  `BankCreditReviewLiteAdapter` (frozen dataclass implementing
  `MechanismAdapter`), `BankCreditReviewLiteResult`, and
  `run_reference_bank_credit_review_lite(kernel, *, bank_id,
  firm_id, ...)`. Default request_id formula includes both
  bank_id AND firm_id from the start so multi-bank reviews on
  the same firm don't alias on the audit lineage.

- Five synthetic [0,1] scores: operating_pressure_score (=
  pressure.overall_pressure), valuation_pressure_score (=
  1 - mean(valuation.confidence)), debt_service_attention_score,
  collateral_attention_score, information_quality_score (a
  coverage metric). Plus overall_credit_review_pressure (mean
  of the four pressure-side scores; information_quality is
  coverage, not pressure, and does not enter the mean).

- `world/reference_living_world.py`:
  `LivingReferencePeriodSummary` extended additively with
  `bank_credit_review_signal_ids` and
  `bank_credit_review_mechanism_run_ids` (one entry per (bank,
  firm) pair). New phase per period between valuation and
  reviews.

- CLI / report / replay: `[period N]` trace adds `credit_reviews=`;
  Markdown table adds `credit_reviews` column;
  `LivingWorldPeriodReport` adds `credit_review_signal_count`;
  v1.9.2 canonical view includes the new id tuples.

- 29 standalone tests + 7 integration tests pinning the
  contract: protocol satisfaction; runs without kernel; missing
  evidence → degraded with conservative output; scores in [0,1];
  overall = mean of four; deterministic; request immutable;
  signal shape with eight boundary flags
  (`no_lending_decision` / `no_covenant_enforcement` /
  `no_contract_mutation` / `no_constraint_mutation` /
  `no_default_declaration` / `no_internal_rating` /
  `no_probability_of_default` / `synthetic_only`); caller helper
  commits exactly one signal; lineage preserved; full
  no-mutation against contracts / constraints / prices /
  ownership / valuations / etc.; per (bank, firm) per period
  in living-world; pressure_signal_id link in payload; valuations
  threaded in related_ids.

**Hard boundary carried forward.** Every committed credit
review note stamps the eight boundary flags. The mechanism
produces a *diagnostic note*, not a *decision*. No price
formation, no trading, no lending decisions, no covenant
enforcement, no contract or constraint mutation.

The full suite passes 1616 tests (1580 prior + 36 v1.9.7).

**Recommended next path.** Performance Boundary moves to v1.9.8;
v1.9.last remains the public prototype freeze.

## v1.9.8 — what shipped

A **discipline milestone**, not a behaviour milestone. v1.9.8
documents the computational boundaries of the v1.9 living
reference world and pins them with tests. Nothing about the
runtime or any mechanism changed; the goal is to prevent silent
drift from "bounded synthetic demo" into "dense all-to-all
simulator" before the public prototype freezes.

- `docs/performance_boundary.md` — new doc covering: current
  loop shapes per phase (`O(P × F)`, `O(P × F × n_exposures)`,
  `O(P × I × F)`, `O(P × B × F)`, etc.); per-period record-count
  breakdown (`2F + F + 2(I+B) + IF + BF + 2(I+B) = 37` for the
  default fixture); v1.9 demo discipline (all-pairs only inside
  fixed demo-size fixtures, no path enumeration, no hidden
  quadratic loops, tensor / matrix views are diagnostic, reporting
  cost is `O(R)`); sparse gating principles for future production
  scale (bank credit review gated by contracts / exposures /
  watchlists; investor valuation gated by holdings / mandates /
  coverage; menus from actor-specific indexes); future
  acceleration candidates with explicit "no native rewrite in
  v1.9.x" position; semantic caveat that **review is not
  origination** — v1.9.7 is review-note generation, not loan
  approval.

- `tests/test_living_reference_world_performance_boundary.py`
  (10 tests) — pins the discipline:
  * `test_performance_boundary_doc_exists` (with a section
    spot-check),
  * `test_default_living_world_record_count_is_exactly_per_formula`
    (lower bound = 148, tight upper bound = 148 + 32 = 180),
  * `test_per_period_record_count_is_constant_across_periods`,
  * `test_pressure_signal_count_is_exactly_periods_times_firms`,
  * `test_valuation_count_is_exactly_periods_times_investors_times_firms`,
  * `test_credit_review_count_is_exactly_periods_times_banks_times_firms`,
  * `test_no_forbidden_mutation_records_appear` — none of
    `ORDER_SUBMITTED`, `PRICE_UPDATED`, `CONTRACT_CREATED`,
    `CONTRACT_STATUS_UPDATED`, `CONTRACT_COVENANT_BREACHED`,
    `OWNERSHIP_TRANSFERRED` may appear in the v1.9 ledger,
  * `test_no_warning_or_error_records_during_default_sweep`,
  * `test_count_expected_living_world_records_matches_default_fixture`
    (= 148),
  * `test_count_expected_living_world_records_scales_linearly_in_periods`.

- A `count_expected_living_world_records(*, firms, investors,
  banks, periods)` helper sits in the new test module and is
  a written, reusable formula for the budget. It is intentionally
  in the test file rather than `world/`: it documents the
  bounded-fixture assumption and is the canary that fails when
  the bound is broken, not a runtime planning helper.

**What this milestone explicitly does *not* do.**

- No new economic behaviour. No new mechanism.
- No price formation. No trading. No lending decisions. No loan
  origination. No covenant enforcement. No contract mutation.
- No C++, Julia, Rust, or GPU rewrite.
- No Japan calibration. No public-data ingestion.

The full suite passes 1626 tests (1616 prior + 10 v1.9.8).

**Recommended next path.** v1.9.last — the first public
prototype freeze.

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
