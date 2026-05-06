# v1.23 Substrate Hardening + Validation Foundation — Design Note

*v1.23 is the **substrate-hardening + validation-foundation**
milestone. It addresses concrete risks surfaced by the
post-v1.22.last review (round-1 reports
`/tmp/fwe_post_v1_22_2_analysis/01..04` and round-2 reports
`/tmp/fwe_post_v1_22_2_analysis_round2/A..D`) before any new
feature surface (mandate / interaction-annotation) is added.*

This document is **docs-only at v1.23.0**. It introduces no
new runtime module, no new dataclass, no new ledger event,
no new test, no new label vocabulary, no new behavior. It is
the binding scope pin for v1.23.x; v1.23.1 / v1.23.2 / v1.23.3
must implement exactly to this design or the design must be
re-pinned.

The companion documents are:

- [`v1_22_static_ui_stress_readout_reflection.md`](v1_22_static_ui_stress_readout_reflection.md)
  — the v1.22 layer v1.23 hardens.
- [`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md)
  — the v1.21 stress layer whose substrate v1.23 hardens.
- [`research_note_001_stress_composition_without_outcome_inference.md`](research_note_001_stress_composition_without_outcome_inference.md)
  — the research framing v1.23 inherits.
- `research_note_002_validating_stress_citation_graphs_without_price_prediction.md`
  — companion research note; **scoped for v1.23.2** (not
  shipped at v1.23.0).
- [`world_model.md`](world_model.md) §132 — the
  constitutional position of v1.23.

---

## 1. Scope statement (binding)

v1.23 has two parallel goals, both narrow:

1. **Substrate hardening.** The v1.21.x / v1.22.x layers now
   rely on five concrete contracts that are not pinned at the
   substrate level: canonical digests duplicated across tests,
   six non-composing forbidden-name frozensets, an unpinned
   cross-layer metadata stamp, an unenforced runtime
   cardinality cap, and a stale test inventory. v1.23 closes
   each gap **without changing existing behavior** (no
   digest movement; no test-count drift beyond additive new
   pin tests; no runtime side-effect under no-stress
   profiles).
2. **Validation foundation.** The v1.21.3 stress readout is
   currently audit-only — there is no framework for asking
   "is this readout trustworthy as an audit object?" beyond
   the boundary-scan / forbidden-name discipline. v1.23 lays
   the **minimum** scaffolding to ask six concrete questions
   about a readout (determinism / boundary preservation /
   citation completeness / partial-application visibility /
   inter-reviewer reproducibility placeholder / null-model
   comparison placeholder). Two of these are placeholders
   for v1.24+ work; four are pinnable now.

What v1.23 is (binding):

- Substrate-only. All five hardening sub-tasks (§3 below)
  preserve existing behavior; the only new runtime artifact
  is one frozen constant (`STRESS_PROGRAM_RUN_RECORD_CAP`)
  and one trip-wire check inside the existing
  `apply_stress_program(...)` helper.
- Read-only validation. Every validation pin reads existing
  records and asserts a property; nothing emits a ledger
  record, mutates a book, or invents a new label.
- Additive tests only. v1.23 adds tests; it does not
  rename, restructure, or remove any existing test.
- Digest-stable. All v1.21.last canonical digests
  (`f93bdf3f…b705897c` / `75a91cfa…91879d` /
  `5003fdfa…566eb6` / `ec37715b…0731aaf`) remain
  byte-identical at every v1.23.x sub-milestone.

What v1.23 is **NOT** (binding):

- v1.23 is **NOT** the institutional investor mandate /
  benchmark pressure layer. That candidate is deferred to
  **v1.25** (see §7).
- v1.23 is **NOT** the manual_annotation interaction
  layer. That candidate is deferred to **v1.24** (see §7).
- v1.23 is **NOT** an outcome / impact / risk-score view.
  No magnitude, no probability, no expected response.
- v1.23 is **NOT** a price / forecast / trading /
  recommendation surface.
- v1.23 does **NOT** introduce real data, Japan
  calibration, or LLM execution.
- v1.23 is **NOT** a refactor of the v1.21.x / v1.22.x
  surface. It pins the existing surface; it does not
  change it.

---

## 2. Sequence map

| Milestone     | Surface                                                                                                            | What it ships                                                                                                                                                                              |
| ------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **v1.23.0**   | docs only                                                                                                          | This design note. §132 in `world_model.md`. Roadmap-row refresh in `v1_20_monthly_scenario_reference_universe_summary.md` and `README.md`.                                                  |
| v1.23.1       | substrate-hardening code: `tests/_canonical_digests.py` (NEW) + `world/forbidden_tokens.py` (NEW) + extensions to `world/stress_applications.py` + `world/stress_programs.py` | Five concrete hardenings (§3.A–E below). Additive tests. **No digest movement.** **No no-stress behavior change.**                                                                          |
| v1.23.2       | validation fixtures: `tests/test_validation_*.py` (NEW) + `docs/research_note_002_validating_stress_citation_graphs_without_price_prediction.md` (NEW) | Four pinnable validation categories + two placeholder categories (§4 below). Research note 002 lands here, not at v1.23.0.                                                                  |
| v1.23.3       | demo case study: `examples/research/attention_crowding_case_study.py` (NEW) + `tests/test_attention_crowding_case_study.py` (NEW) | A read-only research-defensible demo: load a pre-stressed kernel, surface a case where one stress is emitted but no downstream actor cites it (attention saturation). **No new ledger event types. No new label vocabulary.** |
| **v1.23.last**| docs only                                                                                                          | Final freeze section. Sequence map, what-v1.23-is / what-v1.23-is-NOT, pinned test count, preserved digests, hard-boundary re-pin, future optional candidates (v1.24 manual_annotation, v1.25 mandate). |

The sequence is **strictly serial**. v1.23.2 must not start
until v1.23.1's hardening is byte-stable and tests are green.
v1.23.3 must not start until v1.23.2's validation pins are
in place.

Cardinality (binding for the v1.23 sequence):

- **0** new dataclasses (no new record type, no new book).
- **0** new ledger event types.
- **0** new label vocabularies (every constant added is a
  pinned id / digest / cap, not a label).
- **2** new runtime modules (`world/forbidden_tokens.py`
  + `tests/_canonical_digests.py`); both are
  consolidation modules that re-export existing values
  with no behavior change.
- **1** new runtime constant (`STRESS_PROGRAM_RUN_RECORD_CAP
  = 60`) plus one trip-wire check.
- **0** new UI regions. v1.23 does not touch
  `examples/ui/fwe_workbench_mockup.html`.
- **0** new tabs. v1.20.5 11-tab ↔ 11-sheet bijection
  preserved.
- v1.23.1 expected test delta: **+ ~ 15** (per §3 + §6).
- v1.23.2 expected test delta: **+ ~ 12** (per §4 + §6).
- v1.23.3 expected test delta: **+ ~ 8** (per §5 + §6).
- Final v1.23.last test count target: **~ 4928** (subject to
  exact pin at each sub-milestone).

---

## 3. Substrate hardening design (binding for v1.23.1)

Five concrete risks. For each: the symptom, the design, the
binding constraints, and the v1.23.1 deliverable.

### 3.A Canonical digest sprawl

**Symptom.** Round-2 Agent A counted 47 hex-digest literal
pins across `tests/*.py`. The four canonical digests are
duplicated by hand across:

- `quarterly_default` `f93bdf3f…b705897c`: ≥ 17 sites
- `monthly_reference` `75a91cfa…91879d`: ≥ 7 sites
- `scenario_monthly_reference_universe` test-fixture
  `5003fdfa…566eb6`: ≥ 4 sites
- v1.20.4 CLI bundle `ec37715b…0731aaf`: ≥ 4 sites

A future digest update would require updating each site by
hand. A typo in any single site silently breaks regression
detection at that site.

**Design.** A new module **`tests/_canonical_digests.py`**
that exports the four canonical constants verbatim:

```python
# tests/_canonical_digests.py — v1.23.1
"""Canonical living_world_digest constants. Single source of
truth for digest pins across the test suite. Importing from
this module is the discipline; pasting hex literals into
test files is a regression."""

from __future__ import annotations

# v1.18.last / v1.19.last / v1.20.last / v1.21.last canonical
# default-fixture digest. Pinned by:
#   tests/test_living_reference_world.py
#   tests/test_run_export_cli.py
#   tests/test_run_export_stress_readout.py
#   tests/test_ui_active_stresses_strip.py
#   ... (≥17 sites)
QUARTERLY_DEFAULT_LIVING_WORLD_DIGEST: str = (
    "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf"
    "0648a92cc961401b705897c"
)

# v1.19.3 monthly_reference profile digest.
MONTHLY_REFERENCE_LIVING_WORLD_DIGEST: str = (
    "75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc"
    "4514a009bb4e596c91879d"
)

# v1.20.3 scenario_monthly_reference_universe test-fixture
# digest (default regime, no --regime flag).
SCENARIO_MONTHLY_REFERENCE_UNIVERSE_FIXTURE_DIGEST: str = (
    "5003fdfaa45d5b5212130b1158729c692616cf2a8d"
    "f9b425b226baef15566eb6"
)

# v1.20.4 CLI bundle digest under
# --regime constrained --scenario credit_tightening_driver.
V1_20_4_CLI_BUNDLE_DIGEST: str = (
    "ec37715b8b5532841311bbf14d087cf4dcca731a9d"
    "c5de3b2868f32700731aaf"
)
```

**Binding constraints (v1.23.1):**

1. v1.23.1 imports the existing canonical constants from
   their current sites via a one-pass migration: every
   test that currently has a hex literal for one of these
   four digests is updated to `from tests._canonical_digests
   import <CONSTANT>` and reference the constant.
2. **No digest changes.** Every constant matches the
   current literal byte-for-byte.
3. The migration is a no-op semantically — running the test
   suite before and after the migration must produce
   identical pass / fail results.
4. v1.23.1 may NOT introduce a fifth digest constant. If
   v1.23.x detects the need for a new pinned digest, that
   addition lands in a separate v1.23.x.x sub-milestone
   under a fresh design pin.

### 3.B Forbidden-token set composition

**Symptom.** Six non-composing forbidden-name frozensets
exist:

- `FORBIDDEN_RUN_EXPORT_FIELD_NAMES` (`world/run_export.py:127`)
  — v1.19.0 base, **does not compose** with the v1.21.x
  stress sets. Round-1 Agent 01 confirmed: tokens like
  `interaction_label`, `composition_label`, `aggregate_*`,
  `combined_*`, `dominant_stress_label`,
  `stress_amplification_score`, `amplify` / `dampen` /
  `offset` / `coexist` can appear as keys inside the
  bundle's `metadata` / `overview` / `timeline` /
  `scenario_trace` payload sections today and pass scanning.
- `FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES` (`world/stress_programs.py:185`)
  — v1.21.0a stress base.
- `FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES`
  (`world/stress_applications.py:181`) — alias of above.
- `FORBIDDEN_STRESS_READOUT_FIELD_NAMES`
  (`world/stress_readout.py:135`) — alias of above.
- `FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS`
  (`world/run_export.py:175`, v1.22.1) — extends the base
  with v1.22.0 outcome / interaction tokens, but only
  scanned under the `stress_readout` payload section.
- (`docs/v1_22_*` text-only forbidden lists also exist as
  human-readable doctrine, but those are not runtime sets.)

**Design.** A new module **`world/forbidden_tokens.py`**
that decomposes the existing sets into a base + per-milestone
deltas, then re-composes them. The composed sets re-export
to the existing names; existing imports continue to work
without code change.

```python
# world/forbidden_tokens.py — v1.23.1
"""Composable forbidden-name vocabulary.

v1.23.1 consolidation: the v1.18.0 / v1.19.0 / v1.21.0a /
v1.22.0 forbidden-name sets are decomposed into
``BASE`` + per-milestone ``_DELTA`` frozensets and
re-composed. The re-composed sets are re-exported under
their existing public names; existing imports continue to
work unchanged. **No token is added or removed at v1.23.1.**

Composition discipline:
- ``BASE`` carries the v1.18.0 actor-decision / canonical-
  judgment / price / forecast / advice / real-data /
  Japan / LLM tokens that EVERY downstream layer forbids.
- Each ``*_DELTA`` carries the milestone-specific
  additions that should compose with BASE.
- The composed names are the existing public names so
  no caller is broken.

The discipline this module enforces (test-pinned):
- Every forbidden-name set must contain BASE.
- Every milestone delta must NOT remove a BASE token.
- A future v1.x milestone adding a forbidden token under
  one layer must add it to a delta, not in-place — so
  composition propagates automatically.
"""

# (frozenset definitions — verbatim copies of existing
# tokens, decomposed)
FORBIDDEN_TOKENS_BASE: frozenset[str] = ...
FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA: frozenset[str] = ...
FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA: frozenset[str] = ...
FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA: frozenset[str] = ...

# Re-exported composed sets (preserve existing names).
FORBIDDEN_RUN_EXPORT_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
    | FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA
)
FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
)
FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES = (
    FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
)
FORBIDDEN_STRESS_READOUT_FIELD_NAMES = (
    FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES
)
FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
)
```

**Binding constraints (v1.23.1):**

1. **No token is added or removed at v1.23.1.** The
   consolidation is a re-decomposition of existing
   tokens. v1.23.1's test
   `test_forbidden_token_consolidation_preserves_v1_22_x_byte_identity`
   asserts that each composed set equals the existing set
   (set-equality across all 6 frozensets).
2. The **closing-the-leak** intent — making
   `FORBIDDEN_RUN_EXPORT_FIELD_NAMES` *additionally*
   include the v1.21.0a stress tokens (so the bundle's
   non-stress payload sections cannot smuggle
   `interaction_label` / `aggregate_*` / etc.) — is
   binding via the composition above. This **does** add
   tokens to one set's effective membership; it must be
   accompanied by:
   - A migration sweep over the existing test corpus to
     confirm no current test relies on the previously-
     leaky behavior (i.e., no existing payload contains a
     v1.21.0a stress token).
   - A pin test that asserts every v1.21.0a stress token
     is rejected by every payload field's scanner.
3. The existing `world/run_export.py`,
   `world/stress_programs.py`,
   `world/stress_applications.py`,
   `world/stress_readout.py` modules import from
   `world/forbidden_tokens.py` instead of declaring the
   sets in-place. The decomposed module becomes the
   single source of truth.

**Critical caveat — digest stability.** If the existing
fixtures contain a payload value (under a non-stress section
like `metadata` or `overview`) that happens to equal a
v1.21.0a stress token, this consolidation would raise at
construction time, moving the digest. **The migration must
verify no such value exists** before merge. Specifically:
v1.23.1 runs a one-shot dry-run scanner that walks every
existing `RunExportBundle` constructed in the test suite
and reports any payload that would newly fail under the
composed forbidden set. If the dry-run is clean (zero
violations), the consolidation merges. If not, the
violations must be addressed first (by renaming the
offending payload key) under a separate sub-PR.

### 3.C Cross-layer metadata contract

**Symptom.** v1.21.2 `apply_stress_program(...)` writes
`metadata["stress_program_application_id"]` and
`metadata["stress_step_id"]` on every per-step
`apply_scenario_driver(...)` call (`world/stress_applications.py:786-789`).
v1.21.3 `build_stress_field_readout(...)` reads these keys to
filter v1.18.2 application records (`world/stress_readout.py:597-605`).
The contract is currently **unpinned** — no test asserts
that this glue is intact. Round-2 Agent A confirmed via
`grep`: zero hits for `metadata["stress_program_application_id"]`
in `tests/`.

**Design.** Add explicit pin tests in v1.23.1's
`tests/test_metadata_stamp_contract.py` (NEW):

1. **Forward direction.** After
   `apply_stress_program(...)`, assert that every emitted
   per-step v1.18.2 `ScenarioDriverApplicationRecord` has
   `metadata["stress_program_application_id"]` matching
   the program receipt id and
   `metadata["stress_step_id"]` matching the step id.
2. **Reverse direction.** Build a stress-applied kernel,
   call `build_stress_field_readout(...)`, and assert that
   the readout's `scenario_application_ids` correspond
   exactly to the v1.18.2 records carrying the matching
   metadata stamp. Adding an unrelated v1.18.2 record (not
   stamped) must NOT appear in the readout.
3. **Round-trip.** Apply stress program → build readout →
   serialize via
   `build_stress_readout_export_section(...)` → assert
   that every entry's `scenario_application_ids` match the
   forward direction's stamped records.
4. **Boundary scan on metadata.** The v1.21.0a forbidden
   set already scans metadata keys. Add a test that
   confirms a metadata stamp containing a forbidden value
   (e.g., `metadata["stress_program_application_id"] =
   "amplify"`) raises during readout construction or
   during export. (This is more about catching naming
   regressions than smuggling — the canonical id format
   is `stress_program_application:NNN`, far from any
   forbidden token.)

**Binding constraints (v1.23.1):**

1. The contract pin tests add no new behavior; they only
   assert what v1.21.2 / v1.21.3 already do.
2. The metadata-key names (`stress_program_application_id`,
   `stress_step_id`) are pinned **as string-literal
   constants** at the top of `world/stress_applications.py`
   so a future rename requires updating one place.

### 3.D Runtime cardinality constant

**Symptom.** The v1.21.0a binding "≤ 60 records added per
run" is currently a fixture assertion at
`tests/test_stress_applications.py:873-905` plus a docs
sentence — there is no runtime guard. A misuse pattern
(applying a stress program with a large number of steps
across multiple kernels, or future extensions that grow the
per-step record count) could silently exceed the cap.

**Design.** Add a **runtime constant** and a **trip-wire
check**:

```python
# world/stress_applications.py — v1.23.1 addition
"""...

v1.23.1 — runtime cardinality cap. v1.21.0a binding:
``apply_stress_program(...)`` MUST emit at most
:data:`STRESS_PROGRAM_RUN_RECORD_CAP` total records into
the kernel (counting program receipt + per-step v1.18.2
applications + per-shift v1.18.2 context-shift records).
Exceeding this cap is a regression. The check is performed
at the END of ``apply_stress_program`` and raises
:class:`StressProgramRecordCapExceededError`."""

STRESS_PROGRAM_RUN_RECORD_CAP: int = 60


class StressProgramRecordCapExceededError(StressApplicationError):
    """Raised when apply_stress_program emits more records
    than STRESS_PROGRAM_RUN_RECORD_CAP."""


# Inside apply_stress_program, after all per-step calls
# complete:
#   delta = (len(kernel.stress_applications.list_applications())
#          - app_count_before)
#         + (len(kernel.scenario_applications.list_applications())
#          - sce_app_count_before)
#         + (len(kernel.scenario_applications.list_context_shifts())
#          - shift_count_before)
#   if delta > STRESS_PROGRAM_RUN_RECORD_CAP:
#       raise StressProgramRecordCapExceededError(...)
```

**Binding constraints (v1.23.1):**

1. **No no-stress behavior change.** The check fires only
   inside `apply_stress_program(...)`. Kernels that never
   call this helper see no change.
2. **No existing-fixture digest movement.** Every current
   stress fixture emits well under 60 records (the
   fixture pin at `tests/test_stress_applications.py:873`
   already verifies this). The trip-wire fires only on
   regressions.
3. The constant is exported at module level so tests can
   import it: `from world.stress_applications import
   STRESS_PROGRAM_RUN_RECORD_CAP`. The trip-wire test
   (`tests/test_stress_program_record_cap.py`, NEW)
   constructs a kernel + program designed to exceed the
   cap and asserts the error is raised.
4. Future v1.x milestones that legitimately need a higher
   cap MUST update the constant under a fresh design pin
   (a v1.23.last-correction or later) — silent extension
   is forbidden.

### 3.E Test inventory freshness

**Symptom.** `docs/test_inventory.md` is pinned at
v1.20.last (4764 tests). The current test count is **4893**
(2 milestones behind). Round-2 Agent A confirmed staleness.

**Design.** Two thin pieces:

1. **A generator script:**
   `examples/tools/refresh_test_inventory.py` — reads
   `pytest --collect-only -q` output, parses test counts
   per file, regenerates the markdown table in
   `docs/test_inventory.md`. Idempotent: running it
   twice produces the same output.
2. **A freshness pin test:**
   `tests/test_test_inventory_currency.py` (NEW) — reads
   the pinned total in `docs/test_inventory.md` and
   asserts it matches the current `pytest --collect-only`
   total. If a new test is added without regenerating
   the inventory, this test fails.

**Binding constraints (v1.23.1):**

1. The freshness test must be cheap (it parses the
   inventory and counts files, not re-run the full
   suite). Target: < 1 second.
2. The generator must be deterministic — same test set
   → byte-identical inventory file. Future contributors
   regenerate the inventory as part of every milestone's
   freeze checklist.
3. The freshness test must be one of the tests counted —
   i.e., adding it bumps the inventory pin from N to
   N+1 by definition. No circular failure.

---

## 4. Validation foundation design (binding for v1.23.2)

The v1.21.3 stress readout is currently audit-only. v1.23.2
introduces a **minimum** validation framework — six
question categories, four pinnable now, two as
placeholders.

The validation object (per
`research_note_001_stress_composition_without_outcome_inference.md`
§3) is:

```
StressProgram
   ↓
ScenarioDriverApplication
   ↓
ScenarioContextShift
   ↓
StressFieldReadout
   ↓
UI / export citation trail
```

Validation must NOT claim:

- price prediction
- causal proof
- investment advice
- real-data calibration
- forecast / expected response / outcome metric
- magnitude / probability / target / risk score

### 4.1 Pinnable categories (v1.23.2)

**Category 1 — Determinism.**

- Pin: same kernel state + same arguments →
  byte-identical readout. The v1.21.3 layer already
  asserts this in `tests/test_stress_readout.py`. v1.23.2
  promotes this to a **named validation pin**:
  `tests/test_validation_determinism.py::test_validation_determinism_pin_v1_23_2`.
- The pin reads two consecutive readout builds and asserts
  byte-equality of the markdown summary, the
  `StressFieldReadout.to_dict()` output, and the v1.22.1
  export entry.

**Category 2 — Boundary preservation.**

- Pin: every readout's emission must satisfy the v1.21.0a
  + v1.22.0 forbidden-name boundary. v1.23.2 adds
  `tests/test_validation_boundary.py`:
  - The dataclass field-name scan (already enforced).
  - The metadata-key scan (already enforced).
  - The markdown-render scan (the rendered markdown must
    not contain any forbidden token from the composed
    forbidden set, scanned against
    `world.forbidden_tokens.FORBIDDEN_STRESS_READOUT_EXPORT_TOKENS`).
  - The export-section scan (already enforced at
    `world/run_export.py:_validate_stress_readout_entry`).
- The pin is named:
  `test_validation_boundary_preservation_pin_v1_23_2`.

**Category 3 — Citation completeness.**

- Pin: every `cited_source_context_record_id` in the
  readout must resolve to an actual record in the
  kernel's source-of-truth book. A "dangling citation" —
  an id that does not match any extant record — is a
  regression class the current tests do not catch.
- v1.23.2 adds
  `tests/test_validation_citation_completeness.py` with:
  - For a stress-applied kernel, build the readout, then
    walk `source_context_record_ids` and assert each
    resolves to a record in the corresponding book.
  - For `downstream_citation_ids` (when supplied), same
    walk against the downstream book.
- The pin is named:
  `test_validation_citation_completeness_pin_v1_23_2`.

**Category 4 — Partial-application visibility.**

- Pin: when `is_partial == True`, the readout MUST surface
  every required visibility field (already enforced at
  the dataclass level). v1.23.2 adds an end-to-end test
  that confirms the visibility propagates through the
  v1.22.1 export entry AND through the v1.21.3 markdown
  summary's "PARTIAL APPLICATION" banner.
- The pin is named:
  `test_validation_partial_application_visibility_pin_v1_23_2`.

### 4.2 Placeholder categories (v1.23.2 — design only, no pinning yet)

**Category 5 — Inter-reviewer reproducibility (placeholder).**

- The intent: two human reviewers reading the same readout
  + same fixture should reach the same audit conclusion.
  v1.23.2 cannot pin this with humans, so it pins a
  **format placeholder**: a `tests/fixtures/inter_reviewer/`
  directory with a stub format for reviewer notes, and a
  test that asserts the format is parseable.
- No actual reviewer panel exists. The placeholder is
  scaffolding for a future v1.x milestone (or for an
  external research collaboration) to populate.

**Category 6 — Null-model comparison (placeholder).**

- The intent: a readout from a kernel with **scenario
  drivers applied but no stress program** is the
  natural null model — what does adding the stress
  program *change* in the citation graph?
- v1.23.2 cannot fully pin this without designing the
  diff format. The placeholder: a fixture pair (kernel
  with-stress / without-stress) and a test that asserts
  the readout build succeeds for both AND that the
  `stress_readout` export section is empty for the
  without-stress kernel and non-empty for the
  with-stress kernel. The diff itself is deferred.

### 4.3 What v1.23.2 does NOT add

- No new dataclass.
- No new ledger event.
- No new label vocabulary.
- No outcome metric.
- No statistical test (no t-test, no goodness-of-fit, no
  hypothesis testing — those would imply the readout is
  a random variable, which it is not at v1.x).
- No comparison to a real-world series, real-world
  index, real-world institution, or real-world stress
  episode.

---

## 5. Demo case study — attention crowding (binding for v1.23.3)

The v1.12 finite attention budget plus the v1.18 / v1.20 /
v1.21 stimulus chain produces a graph in which a reviewer
can see **whether one stress's downstream citations crowd
out another's** in the same period (per
`research_note_001_*` §5). v1.23.3 ships a **read-only
demo case study** that surfaces this:

- A new example script:
  `examples/research/attention_crowding_case_study.py`
  that loads a deterministic synthetic universe, applies
  two overlapping stress programs (cardinality permitting
  — note v1.21.0a constraint of ≤ 1 per run; the case
  study uses two **sequential** runs with different
  programs, not concurrent), and surfaces the readout
  difference.
- A test:
  `tests/test_attention_crowding_case_study.py` that pins
  the case study's deterministic output (the citation
  graph for run A vs run B is byte-deterministic).
- The case study is **NOT** a claim about real-world
  attention. It is a research-defensible demonstration
  that the engine surfaces *crowding-shaped* citation
  differences when the v1.12 attention budget saturates.

**Binding constraints (v1.23.3):**

1. The script never executes Python from the browser, never
   ingests real data, never produces a forecast.
2. The script is **read-only** — its only side effect is
   writing two markdown audit summaries to a user-supplied
   `--out` directory.
3. The pinned output is byte-deterministic across runs.
4. **No new ledger event types. No new label vocabulary.**
   The case study reuses existing v1.21.3 readout +
   markdown summary verbatim.
5. The case study's documentation lives in
   `docs/research_note_002_*` (added at v1.23.2) and
   does not invent new audit semantics.

---

## 6. Test plan summary (per sub-milestone)

### v1.23.1 — substrate hardening tests
*(target: ~ 15 new tests across 3-5 files)*

1. `tests/test_canonical_digests_module.py` — 3 tests:
   constants exist; constants match the four expected
   hex values; constants are imported by ≥ 1 existing
   test (sanity).
2. `tests/test_forbidden_token_consolidation.py` — ~ 5
   tests: each composed set equals the pre-consolidation
   literal set (preservation); BASE is a subset of every
   composed set; v1.21.0a stress tokens are rejected by
   `FORBIDDEN_RUN_EXPORT_FIELD_NAMES` (the leak-fix); no
   token disappears.
3. `tests/test_metadata_stamp_contract.py` — ~ 4 tests:
   forward direction; reverse direction; round-trip;
   boundary scan on metadata.
4. `tests/test_stress_program_record_cap.py` — ~ 2 tests:
   cap is exposed; trip-wire raises when exceeded.
5. `tests/test_test_inventory_currency.py` — 1 test: the
   pinned total in `docs/test_inventory.md` matches the
   current `pytest --collect-only` total.

### v1.23.2 — validation foundation tests
*(target: ~ 12 new tests across 4 files)*

1. `tests/test_validation_determinism.py` — ~ 3 tests:
   markdown summary byte-identity; readout dict byte-
   identity; v1.22.1 export entry byte-identity.
2. `tests/test_validation_boundary.py` — ~ 4 tests:
   dataclass field scan; metadata key scan; markdown
   render scan; export entry scan.
3. `tests/test_validation_citation_completeness.py` — ~ 3
   tests: source_context_record_ids resolve;
   downstream_citation_ids resolve when supplied; dangling
   citation raises during readout construction.
4. `tests/test_validation_partial_application_visibility.py`
   — ~ 2 tests: visibility through export; visibility
   through markdown.

### v1.23.3 — demo case study tests
*(target: ~ 8 new tests in 1 file)*

1. `tests/test_attention_crowding_case_study.py` — ~ 8
   tests: case study script imports cleanly; case study
   produces deterministic output; output is byte-
   deterministic across two consecutive runs; output
   files contain the v1.21.3 markdown summary verbatim;
   no forbidden tokens in output; case study is
   read-only (no kernel mutation pre/post); script
   handles missing `--out` gracefully; script's
   case-study fixture preserves the v1.21.last canonical
   digests.

### v1.23.0 — what ships in tests

**Nothing.** v1.23.0 is docs-only. Test count holds at 4893.

---

## 7. Roadmap (binding for the v1.23 sequence)

| Sub-milestone | Surface     | Description                                                                                                                                | Status               |
| ------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------- |
| **v1.23.0**   | docs only   | This design note + §132 in `world_model.md` + roadmap-row refresh. Test count: 4893 / 4893 (unchanged).                                    | **Design scoped (this PR)** |
| v1.23.1       | runtime + tests | Substrate hardening: canonical digests module + forbidden-token consolidation + metadata stamp pin + record-cap trip-wire + test-inventory currency. **No digest movement.** **No no-stress behavior change.** | Not started.         |
| v1.23.2       | tests + docs | Validation foundation: 4 pinnable categories + 2 placeholder categories + research note 002.                                                | Not started.         |
| v1.23.3       | example + tests | Attention-crowding read-only demo case study.                                                                                              | Not started.         |
| v1.23.last    | docs only   | Final freeze. Sequence map, what-v1.23-is / what-v1.23-is-NOT, pinned test count, preserved digests, hard-boundary re-pin, future optional candidates. | Not started.         |

**Future optional candidates (NOT planned, NOT scoped at v1.23.0):**

| Future milestone | Description                                                                                                                                                                                                       | Status               |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| v1.24 candidate  | **Manual-annotation interaction layer** — `manual_annotation`-only annotation layer over the v1.21.3 multiset readout. Closed sets `source_kind = {"human"}` and `reasoning_mode = {"human_authored"}`. **MUST NEVER be inferred by a helper, classifier, closed-set rule table, LLM, or any other automated layer.** | Optional candidate.  |
| v1.25 candidate  | **Institutional Investor Mandate / Benchmark Pressure** — bounded synthetic mandate / benchmark / peer-pressure constraints on the v1.15.5 / v1.16.2 investor-intent layer. Decoupled from the v1.21 / v1.22 / v1.23 stress + audit surface. | Optional candidate.  |
| v2.x            | **Japan public calibration** — only after data / license boundaries are designed.                                                                                                                                | Gated.               |
| v3.x            | **Proprietary Japan calibration** — not public.                                                                                                                                                                  | Not public.          |

The sequence is **strictly serial**: v1.23.2 must not start
until v1.23.1 is byte-stable and tests are green; v1.23.3
must not start until v1.23.2 validation pins are in place;
v1.24 must not start until v1.23.last is frozen. Silent
extension of v1.23 is forbidden.

---

## 8. Hard boundary (re-pinned at v1.23.0)

v1.23 inherits and re-pins the v1.22.last hard boundary in
full. The boundary at v1.23.0 is therefore identical to
v1.22.last:

**No real-world output.**
- No price formation, no market price, no order, no trade,
  no execution, no clearing, no settlement, no financing
  execution.
- No forecast path, no expected return, no target price, no
  recommendation, no investment advice.
- No magnitude, no probability, no expected response.
- No firm decision, no investor action, no bank approval
  logic.

**No real-world input.**
- No real data ingestion.
- No real institutional identifiers.
- No licensed taxonomy dependency.
- No Japan calibration.

**No autonomous reasoning.**
- No LLM execution at runtime.
- No LLM prose accepted as source-of-truth.
- `reasoning_mode = "rule_based_fallback"` binding.
- No interaction auto-inference.
- No aggregate / combined / net / dominant / composite
  stress output.

**No source-of-truth book mutation.**
- v1.23.x adds substrate hardening + validation pins. It
  does not write to any kernel book. Pre-existing book
  snapshots remain byte-identical pre / post any v1.23
  helper call.

**No backend in the UI.**
- v1.23 does not touch the static UI mockup. The v1.20.5 /
  v1.22.2 loader discipline is preserved.

**No digest movement.**
- v1.23.1 substrate-hardening migration must produce
  byte-identical digests. The forbidden-token
  consolidation's "leak fix" (composing v1.21.0a stress
  tokens into the run-export forbidden set) must be
  validated by a dry-run scan over existing fixtures
  before merge — confirming that no current payload
  contains a previously-leaky token.

---

## 9. Read-in order (for a v1.23 reviewer)

1. [`v1_22_static_ui_stress_readout_reflection.md`](v1_22_static_ui_stress_readout_reflection.md)
   §"v1.22.last freeze" — the layer v1.23 hardens.
2. This document — the v1.23.0 design pin.
3. [`world_model.md`](world_model.md) §132 — the
   constitutional position.
4. [`research_note_001_stress_composition_without_outcome_inference.md`](research_note_001_stress_composition_without_outcome_inference.md)
   — the research framing v1.23 inherits.
5. [`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md)
   §"v1.21.last freeze" — the stress layer whose
   substrate v1.23 hardens.
6. The post-v1.22.2 review reports
   (`/tmp/fwe_post_v1_22_2_analysis/01..04` +
   `/tmp/fwe_post_v1_22_2_analysis_round2/A..D`) — the
   evidence base for the v1.23 risk list.

---

## 10. Deliverables for v1.23.0 (this PR)

- This design note: `docs/v1_23_substrate_hardening_validation_foundation.md`.
- New section §132 in `docs/world_model.md` —
  "v1.23 Substrate Hardening + Validation Foundation
  (design pointer, **v1.23.0 design-only**)".
- Roadmap-row refresh in
  `docs/v1_20_monthly_scenario_reference_universe_summary.md`
  — the v1.23 row updates from "Roadmap candidate" to
  "Design scoped at v1.23.0"; the v1.24 / v1.25 candidate
  rows are added.
- README anchor refresh in `README.md` §9 — the v1.22.last
  row demoted; v1.23 row added as "Design scoped"; v1.24
  candidate added (manual_annotation); v1.25 candidate
  added (mandate).

No runtime code change. No UI implementation. No new tests.
No new dataclass. No new ledger event. No new label
vocabulary. No digest movement. No record-count change. No
pytest-count change.

---

## 11. Cardinality summary (binding at v1.23.0)

- **0** new dataclasses (v1.23 sequence)
- **0** new ledger event types
- **0** new label vocabularies
- **2** new runtime modules at v1.23.1
  (`tests/_canonical_digests.py`, `world/forbidden_tokens.py`)
  — both consolidation modules; no behavior change
- **1** new runtime constant at v1.23.1
  (`STRESS_PROGRAM_RUN_RECORD_CAP = 60`)
- **0** new UI regions; **0** new tabs
- v1.23.1 expected test delta: **+ ~ 15**
- v1.23.2 expected test delta: **+ ~ 12**
- v1.23.3 expected test delta: **+ ~ 8**
- v1.23.last final test count target: **~ 4928**
- v1.21.last canonical digests: **byte-identical at every
  v1.23.x sub-milestone**

The v1.23 sequence is scoped. Subsequent work that touches
the substrate or validation layer must explicitly re-open
scope under a new design pin (a v1.23.0a or later
correction); silent extension is forbidden.
