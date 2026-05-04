# v1.19 Local Run Bundle and Monthly Reference — Summary

This document closes the v1.19 sequence of FWE. The sequence
ships a **local-run-bridge / temporal-profile / read-only UI
loader** layer on top of the v1.18 scenario-driver inspection
layer, the v1.17 inspection layer, and the v1.16 closed loop.
It resolves two limitations the v1.18.last freeze left in
place: the static UI could not load a freshly-produced engine
run, and the default sweep was quarterly-only.

v1.19.last itself is **docs-only** on top of the v1.19.0 →
v1.19.4 code freezes (plus the v1.19.3.1 reconciliation
follow-up). No new module, no new test, no new ledger event,
no new label vocabulary.

This is **not** a market simulator, **not** a price-formation
layer, **not** a forecast layer, **not** a daily-frequency
economic simulation, **not** a recommendation surface, **not**
a real-data view, **not** a Japan calibration, **not** an LLM
execution path, **not** a backend server, **not** Ruby on
Rails, **not** FastAPI, **not** Flask, **not** browser-to-
Python execution. It is **two new Python modules**
(`world/run_export.py`, `world/information_release.py`), **a
CLI exporter** (`examples/reference_world/export_run_bundle.py`),
**an `examples/reference_world/scenario_report.py` extension**
that already existed at v1.18.3, **a static-HTML loader** in
the existing workbench, and **one new keyword argument**
(`profile=...`) on the existing `run_living_reference_world`
orchestrator. The chain executes the engine **only** from the
command line; the browser only reads JSON.

## Sequence map

| Milestone     | Module / surface                                                                                                                                                | Adds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| v1.19.0       | docs only                                                                                                                                                       | Local Run Bridge / Report Export / Temporal Run Profile design — four-layer separation (engine run profile / report export bundle / UI loading mode / local run bridge); five named run profiles (`quarterly_default` / `monthly_reference` / `scenario_monthly` / `daily_display_only` / `future_daily_full_simulation`); `RunExportBundle` data shape; `InformationReleaseCalendar` + `ScheduledIndicatorRelease` + `InformationArrivalRecord` design; CLI-first local bridge (no Rails, no backend); read-only UI loading. |
| v1.19.1       | `world/run_export.py`                                                                                                                                           | `RunExportBundle` immutable frozen dataclass + four module-level helpers (`build_run_export_bundle` / `bundle_to_dict` / `bundle_to_json` / `write_run_export_bundle` / `read_run_export_bundle`); deterministic JSON via `sort_keys=True`; `stable_for_replay` declarative default; four closed-set frozensets (`RUN_PROFILE_LABELS` / `GENERATED_AT_POLICY_LABELS` / `STATUS_LABELS` / `VISIBILITY_LABELS`); the v1.19.0 hard-naming-boundary `FORBIDDEN_RUN_EXPORT_FIELD_NAMES` frozenset (35+ entries) scanned recursively at any depth across every payload + boundary-flag + metadata mapping; the v1.19.0 default 8-flag boundary set carried on every bundle. +56 unit tests. |
| v1.19.2       | `examples/reference_world/export_run_bundle.py`                                                                                                                  | CLI exporter runnable as `python -m examples.reference_world.export_run_bundle …` (and as a script); composes the v1.17.2 regime-comparison driver (read-only path) with the v1.19.1 export infrastructure; writes a deterministic `RunExportBundle` JSON file. v1.19.2 ship: `--profile quarterly_default` only; `monthly_reference` / `scenario_monthly` / `daily_display_only` / `future_daily_full_simulation` exit non-zero with `"designed but not executable in v1.19.2"`. +20 tests. |
| v1.19.3       | `world/information_release.py` + `world/reference_living_world.py` (extended) + `world/kernel.py` + `world/ledger.py` (extended)                                  | `InformationReleaseCalendar` + `ScheduledIndicatorRelease` + `InformationArrivalRecord` immutable frozen dataclasses; one append-only `InformationReleaseBook`; nine closed-set frozensets (`RELEASE_CADENCE_LABELS` 8 / `INDICATOR_FAMILY_LABELS` 12 / `RELEASE_IMPORTANCE_LABELS` 5 / `JURISDICTION_SCOPE_LABELS` 4 / `ARRIVAL_STATUS_LABELS` 5 / `REASONING_MODE_LABELS` 4 / `REASONING_SLOT_LABELS` 4 / `STATUS_LABELS` 6 / `VISIBILITY_LABELS` 3); v1.19.3 hard-naming-boundary `FORBIDDEN_INFORMATION_RELEASE_FIELD_NAMES` frozenset composes the v1.18.0 actor-decision tokens with the v1.19.3 Japan-real-data tokens (`real_indicator_value` / `cpi_value` / `gdp_value` / `policy_rate` / `real_release_date` and the boundary identifiers); three new `RecordType` enum values; kernel wired with `WorldKernel.information_releases: InformationReleaseBook` empty by default; `run_living_reference_world(..., profile=...)` accepts `quarterly_default` (byte-identical to v1.19.1) and `monthly_reference` (12 months on a synthetic month-end ISO schedule, 7 indicator families, 51 arrivals — within the [36, 60] design budget). +88 unit tests + 13 living-world tests + 3 perf-boundary tests. |
| v1.19.3.1     | `examples/reference_world/export_run_bundle.py` (extended) + `tests/test_run_export_cli.py` (extended)                                                          | Reconciliation follow-up that promotes `monthly_reference` from designed-but-not-executable to executable in the CLI. New `EXECUTABLE_PROFILES = ("quarterly_default", "monthly_reference")` constant; new `_build_bundle_for_monthly_reference(...)` helper that calls `run_living_reference_world(profile="monthly_reference")` and adds an `information_arrival_summary` section under `metadata`. The three remaining deferred profile labels (`scenario_monthly` / `daily_display_only` / `future_daily_full_simulation`) continue to exit non-zero. +8 tests. |
| v1.19.4       | `examples/ui/fwe_workbench_mockup.html` (extended) + `examples/ui/README.md`                                                                                     | Static HTML / CSS / JS only — adds a top-ribbon **Load local bundle** button, hidden `<input type="file" accept="application/json,.json">`, FileReader + JSON.parse + schema validator + per-section renderers (Inputs / Overview / Timeline / Attention / Ledger). New **Local run bundle** card on the Inputs tab; for `monthly_reference` bundles renders the v1.19.3 `metadata.information_arrival_summary` histograms. New `current_data_source` label tracks `inline_fixture` / `sample_manifest` / `local_bundle`. Validate gains six new audit checks. **No fetch, no XHR, no backend, no engine execution from the browser, no file-system write.** No pytest delta — UI / JS only. |
| v1.19.last    | docs only                                                                                                                                                       | This summary, §128.20 in `docs/world_model.md`, the v1.19.last `RELEASE_CHECKLIST.md` snapshot, the v1.19.last `performance_boundary.md` update, the v1.19.last `test_inventory.md` header note, the v1.19.last `examples/reference_world/README.md` addendum, the v1.19.last `examples/ui/README.md` cross-link, and the v1.19.last `docs/fwe_reference_demo_design.md` headline note.                                                                                                                                       |

## What v1.19 ships — the local-run-bundle surface

```
   user (terminal)
        │  python -m examples.reference_world.export_run_bundle \
        │      --profile <quarterly_default | monthly_reference> \
        │      --regime <constructive | mixed | constrained | tightening> \
        │      --scenario none_baseline \
        │      --out /tmp/fwe_run_bundle.json
        ▼
   engine run profile (Layer A)              v1.19.3 / v1.19.3.1
        │  reuses the v1.16 closed loop on the chosen
        │  cadence; monthly_reference reads the default
        │  jurisdiction-neutral InformationReleaseCalendar
        │  and emits 51 InformationArrivalRecord objects
        │  across 12 months
        ▼
   RunExportBundle (Layer B)                  v1.19.1
        │  immutable frozen dataclass; bundle_to_json
        │  with sort_keys=True; default boundary_flags;
        │  deterministic across two runs
        ▼
   write_run_export_bundle → JSON file        v1.19.2 / v1.19.3.1
        │  no absolute path embedded; no wall-clock
        │  timestamp; no $USER / $HOSTNAME; same args →
        │  byte-identical bytes
        ▼
   user (browser, file://)
        │  click "Load local bundle"
        ▼
   <input type="file"> + FileReader.readAsText  v1.19.4
        │  no fetch; no XHR; no network; no engine
        ▼
   JSON.parse + validateBundleSchema           v1.19.4
        │  required top-level keys + 7 boundary flags;
        │  EXECUTABLE_PROFILES vs DEFERRED_PROFILES
        │  closed-set check
        ▼
   render via textContent only                 v1.19.4
        │  Inputs (Local run bundle card) /
        │  Overview / Timeline / Attention diff /
        │  Ledger (≤20 rows)
        ▼
   current_data_source = "local_bundle"
```

A reader can answer four inspection questions by following
plain-id citations from the rendered output:

1. **Which run produced this bundle?** — the Inputs *Local run
   bundle* card's `Active profile` / `Active regime` /
   `Selected scenario` / `Period count` / `Digest` /
   `Generated-at policy` rows.
2. **What did the engine see this period?** — the Overview /
   Timeline / Attention surfaces, populated from the bundle's
   `overview` / `timeline` / `attention_diff` sections.
3. **Where did information arrive?** (monthly only) — the
   *Information arrival summary* sub-card's calendar count /
   scheduled-release count / arrival count + per-
   `indicator_family_label` / per-`release_importance_label` /
   per-`arrival_status_label` histograms.
4. **What was actually emitted to the ledger?** — the Ledger
   tab's bounded excerpt (≤ 20 rows) with `record_id` /
   `timestamp` stripped per the v1.9.2 canonical-form rule
   (deterministic `simulation_date` preserved).

### v1.19.0 — Local Run Bridge / Report Export / Temporal Run Profile design

- The **stimulus / not response** discipline (carried forward
  from v1.18.0): a run profile is a label over the existing
  closed loop, never a new mechanism, never a new actor
  decision rule.
- The **four-layer separation** (binding): engine run profile
  / report export bundle / UI loading mode / local run bridge
  are kept structurally separate so each can evolve
  independently. Adding a new profile does not change the
  bundle schema; adding a new bundle field does not change the
  CLI; adding a UI loader option does not change the runtime.
- The **five named run profiles**: `quarterly_default`
  (current stable; preserves the canonical digest);
  `monthly_reference` (12 monthly periods on the existing
  closed loop; bounded — no daily fan-out, no price records);
  `scenario_monthly` (opt-in monthly + explicit scenario
  application; deferred); `daily_display_only` (display only;
  no daily economic records); `future_daily_full_simulation`
  (**explicitly out of scope for v1.19**, gated on the future
  market-mechanism / price-formation design).
- The **`InformationReleaseCalendar` layer**: monthly profiles
  are *not* naive 12× quarterly loops — the calendar layer
  announces *which categories of public information become
  available in which month* so two adjacent months become
  visibly different. Vocabulary: `InformationReleaseCalendar`
  storage book + `ScheduledIndicatorRelease` + `InformationArrivalRecord`
  + closed-set `ReleaseCadenceLabel` (8) / `IndicatorFamilyLabel`
  (12) / `ReleaseImportanceLabel` (5) / `JurisdictionScopeLabel`
  (4) / `ArrivalStatusLabel` (5).
- The **CLI-first local bridge**: the headline command is
  `python -m examples.reference_world.export_run_bundle …`
  writing a JSON file the static UI loads via `<input
  type="file">`. **Rails is forbidden by name** — the v1.x
  architecture has no Ruby dependency and will never acquire
  one.
- The **read-only UI loading** discipline: the static
  workbench may load JSON via `<input type="file">` +
  `JSON.parse`; **no `fetch()`, no XHR, no backend, no engine
  execution from the browser, no file-system write.**

### v1.19.1 — `RunExportBundle` data shape + JSON writer

- One immutable frozen dataclass `RunExportBundle` with
  twenty fields (`bundle_id` / `run_profile_label` /
  `regime_label` / `selected_scenario_label` / `period_count`
  / `digest` / `generated_at_policy_label` / `manifest` /
  `overview` / `timeline` / `regime_compare` /
  `scenario_trace` / `attention_diff` / `market_intent` /
  `financing` / `ledger_excerpt` / `boundary_flags` / `status`
  / `visibility` / `metadata`).
- Four module-level helpers — `build_run_export_bundle(...)`,
  `bundle_to_dict(bundle)`, `bundle_to_json(bundle, *, indent=2)`
  (deterministic via `sort_keys=True` + `ensure_ascii=False`),
  `write_run_export_bundle(bundle, path)` (UTF-8), and
  `read_run_export_bundle(path)` (returns a plain `dict` —
  full dataclass restoration is **deferred**; the v1.19.4
  read-only UI loader walks the dict).
- `stable_for_replay` is **declarative**: the dataclass
  carries no wall-clock timestamp field, so the rendered JSON
  contains no ISO-style timestamp inserted by the export
  module itself.
- Same arguments → byte-identical `to_dict()`, byte-identical
  `bundle_to_json` output, byte-identical written files
  (pinned by `test_bundle_to_json_byte_deterministic` +
  `test_write_twice_produces_byte_identical_files`).
- `period_count` validation rejects `bool` (which is otherwise
  a subclass of `int`) and negative ints.
- `FORBIDDEN_RUN_EXPORT_FIELD_NAMES` (35+ entries) scanned
  **recursively** at any depth across every payload +
  boundary-flag + metadata mapping at construction.
- The module imports no kernel / source-of-truth book /
  scenario-storage module — pinned by a module-text scan that
  forbids `from world.kernel`, `from world.prices`, `from
  world.scenario_drivers`, `from world.scenario_applications`,
  and twelve other patterns.

### v1.19.2 — CLI run exporter

- `python -m examples.reference_world.export_run_bundle …` (or
  the bare-script form). Composes the v1.17.2 regime-
  comparison driver with the v1.19.1 export infrastructure.
  Builds its own *fresh* kernel per invocation.
- v1.19.2 executable set: `--profile quarterly_default` only.
  Designed-but-not-executable: `monthly_reference` /
  `scenario_monthly` / `daily_display_only` /
  `future_daily_full_simulation`.
- `--regime` ∈ v1.11.2 presets (`constructive` / `mixed` /
  `constrained` / `tightening`).
- `--scenario` defaults to `none_baseline`. Other v1.18.4
  scenario selector labels exit non-zero.
- `--out` required. The path is **not** embedded in the
  bundle.
- Bundle sections populated by v1.19.2: `manifest`,
  `overview`, `timeline`, `scenario_trace` (`none_baseline`
  only), `ledger_excerpt` (≤ 20 records, `kernel.ledger.records[:20]`,
  with `record_id` / `timestamp` stripped per the v1.9.2
  canonical-form rule), `boundary_flags` (the v1.19.0 default
  8-flag set carries through), `metadata`. The other sections
  are reserved for v1.19.3+ / future milestones.

### v1.19.3 — `monthly_reference` profile + `InformationReleaseCalendar` layer

- One immutable frozen `InformationReleaseCalendar` dataclass
  + one immutable frozen `ScheduledIndicatorRelease` dataclass
  + one immutable frozen `InformationArrivalRecord` dataclass
  + one append-only `InformationReleaseBook`.
- Nine closed-set frozensets — the v1.19.0 design vocabulary
  pinned in code.
- Three new `RecordType` enum values:
  `INFORMATION_RELEASE_CALENDAR_RECORDED` /
  `SCHEDULED_INDICATOR_RELEASE_RECORDED` /
  `INFORMATION_ARRIVAL_RECORDED`.
- Kernel wired with `WorldKernel.information_releases:
  InformationReleaseBook` — **empty by default**, so the
  canonical view of an unmodified default sweep is byte-
  identical to v1.19.1 (pinned by
  `test_empty_information_releases_does_not_move_default_living_world_digest`).
- `run_living_reference_world(..., profile=...)` accepts
  `quarterly_default` (default, byte-identical to v1.19.1)
  and `monthly_reference`.
- Default `monthly_reference` fixture: 12 month-end ISO dates
  (`2026-01-31` → `2026-12-31`), 7 indicator families
  (`central_bank_policy` at meeting months 4/8/12; `inflation`
  + `market_liquidity` every month; `labor_market` +
  `production_supply` on non-quarterly-closing months;
  `consumption_demand` + `gdp_national_accounts` on
  quarterly-closing months 3/6/9/12), **51** total arrivals
  across 12 months — within the [36, 60] design budget.
- Arrivals carry the v1.18.0 reasoning-mode audit shape
  (`reasoning_mode = "rule_based_fallback"`,
  `reasoning_slot = "future_llm_compatible"`,
  `reasoning_policy_id = "v1.19.3:information_release:rule_based_fallback"`)
  and the v1.19.0 default 8-flag boundary-flag set verbatim.
- `LivingReferencePeriodSummary` extended with
  `scheduled_release_ids` and `information_arrival_ids`
  tuples — empty for `quarterly_default`.
- The `monthly_reference` `living_world_digest` is pinned at
  **`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`**.
  The `quarterly_default` digest stays byte-identical at
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**.
- **Information arrival is not data ingestion.** No real
  indicator values, no real release dates, no real
  institutional identifiers. Japan release cadence is a
  **design reference only**, never encoded as canonical data.

### v1.19.3.1 — monthly_reference enabled in the CLI exporter

- Reconciliation follow-up between the v1.19.2 CLI exporter
  and the v1.19.3 monthly profile. `monthly_reference` moves
  from `DESIGNED_BUT_NOT_EXECUTABLE_PROFILES` to a new
  `EXECUTABLE_PROFILES = ("quarterly_default", "monthly_reference")`
  constant.
- New `_build_bundle_for_monthly_reference(...)` helper calls
  `run_living_reference_world(profile="monthly_reference")` on
  a fresh kernel, computes the digest via
  `examples.reference_world.living_world_replay.living_world_digest`,
  and adds an `information_arrival_summary` section under
  `metadata` (calendar / scheduled-release / arrival counts +
  per-`indicator_family_label` / per-`release_importance_label`
  / per-`arrival_status_label` histograms — all sorted at
  construction so insertion-order drift cannot leak into
  rendered JSON).
- The three remaining deferred profile labels
  (`scenario_monthly` / `daily_display_only` /
  `future_daily_full_simulation`) continue to exit non-zero.

### v1.19.4 — Static UI local run bundle loader (read-only)

- Top-ribbon **Load local bundle** button + hidden
  `<input type="file" accept="application/json,.json">`.
- `FileReader.readAsText` + `JSON.parse` (never `eval`).
- `validateBundleSchema(bundle)` checks the v1.19.1 top-level
  key set + the v1.19.0 default 8-flag boundary-flag block.
- `BUNDLE_EXECUTABLE_PROFILES = ['quarterly_default',
  'monthly_reference']`. `BUNDLE_DEFERRED_PROFILES =
  ['scenario_monthly', 'daily_display_only',
  'future_daily_full_simulation']` exit with `bundle profile
  '<profile>' is not loadable in v1.19.4 static UI`.
- Renders user-loaded values via `textContent` only — never
  `innerHTML`.
- Caps the rendered ledger excerpt at **20** rows.
- New `current_data_source` label tracks `inline_fixture` /
  `sample_manifest` / `local_bundle`.
- New **Local run bundle** card on the Inputs tab surfaces
  the loaded bundle's labels + a profile badge. For
  `monthly_reference` bundles a sub-card renders the v1.19.3
  `metadata.information_arrival_summary` histograms.
- Preserves the v1.17.4 / v1.18.4 no-jump discipline (no
  `scrollIntoView`, no `location.hash` mutation, no active-
  sheet shift; capture-and-restore protocol on scroll
  position).
- In-page **Validate** gains six new audit checks for the
  v1.19.4 surfaces.

## Final user workflow (the headline)

```bash
cd japan-financial-world

# 1. Generate a quarterly_default bundle (4 periods, canonical digest)
python -m examples.reference_world.export_run_bundle \
    --profile quarterly_default \
    --regime constrained \
    --scenario none_baseline \
    --out /tmp/fwe_quarterly_bundle.json

# 2. Generate a monthly_reference bundle (12 periods, 51 information arrivals)
python -m examples.reference_world.export_run_bundle \
    --profile monthly_reference \
    --regime constrained \
    --scenario none_baseline \
    --out /tmp/fwe_monthly_bundle.json

# 3. Open the static workbench under file://
open examples/ui/fwe_workbench_mockup.html

# 4. In the workbench:
#    - click "Load local bundle"
#    - pick /tmp/fwe_monthly_bundle.json
#    - inspect Overview / Timeline / Attention / Market Intent / Financing / Ledger
#    - the monthly_reference badge appears
#    - the Information arrival summary sub-card renders the v1.19.3 histograms
#    - the current_data_source label flips to "local_bundle"
```

The CLI executes the engine. The browser **never** does. The
JSON file in between is the contract.

## What v1.19 explicitly is not

- **Not a daily economic simulator.** `monthly_reference` is
  the finest granularity on which the engine emits records;
  `daily_display_only` is display-only; `future_daily_full_simulation`
  is gated on the future market-mechanism / price-formation
  design.
- **Not a backend / SaaS / network service.** The CLI is
  pure-Python; the static workbench runs under `file://`. The
  optional v1.19.0-mentioned `127.0.0.1` stub local server
  bridge stays **deferred** — the CLI + read-only UI loader
  cover the headline workflow already.
- **Not Rails.** The v1.x architecture has no Ruby dependency
  and will never acquire one.
- **Not data ingestion.** `InformationArrivalRecord` records
  *that a class of public information became available* — by
  `IndicatorFamilyLabel` ∈ a closed-set vocabulary — at a
  synthetic month. It stores no real value, no real date, no
  real institutional identifier.
- **Not Japan calibration.** Japan release cadence is a
  **design reference only**. Real-institution / real-cadence /
  real-value calibration remains private JFWE territory (v2 /
  v3 only).
- **Not price formation.** No `market_price`, no
  `predicted_index`, no `forecast_path`, no `expected_return`,
  no `target_price`, no `recommendation`, no
  `investment_advice`. These names are pinned by the v1.19.0
  `FORBIDDEN_RUN_EXPORT_FIELD_NAMES` frozenset and the
  v1.19.3 `FORBIDDEN_INFORMATION_RELEASE_FIELD_NAMES`
  frozenset and scanned for absence by tests.
- **Not trading.** No order submission, no order book, no
  matching, no execution, no clearing, no settlement, no
  quote dissemination, no bid / ask, no `PriceBook` mutation.
- **Not investment advice.** No `recommendation`, no
  `investment_advice`. These appear in the workbench HTML and
  the markdown reports only inside negation / boundary /
  forbidden-list contexts.
- **Not real data.** No real exchange / broker / index /
  regulator / issuer / venue / institution identifier appears
  in any v1.19.x module, fixture, test, or rendered view.
- **Not LLM execution.** No model, no prompt, no API call, no
  generated content. `reasoning_mode = "rule_based_fallback"`
  remains binding at v1.19.x; the `future_llm_compatible`
  slot marker is an architectural commitment, not a runtime
  capability.

## Performance boundary at v1.19.last

- **Per-period record count (`quarterly_default` default
  fixture, no scenario applied):** **108** (period 0) /
  **110** (periods 1+). Unchanged from v1.18.last. v1.19
  added zero records to the per-period sweep on
  `quarterly_default` — the new books are empty by default,
  the new helpers are read-only or opt-in, the CLI builds its
  own *fresh* kernel per invocation, and the UI loader walks
  the JSON.
- **Per-run window (`quarterly_default`, default 4-period
  fixture):** **`[432, 480]`**. Unchanged.
- **Default 4-period sweep total (`quarterly_default`):**
  **460 records**. Unchanged.
- **Integration-test `living_world_digest` (`quarterly_default`,
  default fixture, no scenario applied):**
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**.
  Unchanged from v1.18.last across all v1.19 milestones,
  pinned by per-book trip-wire tests in
  `tests/test_run_export.py` (v1.19.1),
  `tests/test_run_export_cli.py` (v1.19.2 + v1.19.3.1),
  `tests/test_information_release.py` (v1.19.3),
  `tests/test_living_reference_world.py::test_v1_19_3_quarterly_default_digest_unchanged`
  (v1.19.3).
- **`monthly_reference` `living_world_digest`:**
  **`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`**.
  Pinned by
  `tests/test_living_reference_world.py::test_v1_19_3_monthly_reference_living_world_digest_is_pinned`
  and
  `test_v1_19_3_monthly_reference_is_deterministic_across_two_kernels`.
- **`monthly_reference` arrivals (default fixture):** **3-5
  per month, 51 across 12 months** — within the [36, 60]
  design budget.
- **Test count:** **4522 / 4522** passing. Up from 4334 /
  4334 at v1.18.last (+188 across the v1.19 sequence:
  v1.19.1 +56, v1.19.2 +20, v1.19.3 +88+13+3, v1.19.3.1 +8,
  v1.19.4 +0). v1.19.0 / v1.19.4 are docs / static-HTML only
  and add no pytest tests; the in-page Validate button
  enforces the workbench-side invariants instead.

## UI status at v1.19.last

- **Type:** single-file static HTML prototype.
- **File:** `examples/ui/fwe_workbench_mockup.html`.
- **Backend:** none.
- **Build tools:** none.
- **External runtime:** none.
- **Network I/O:** none. Inline JSON manifest, the
  `SAMPLE_RUNS` regime fixture, the `SCENARIO_FIXTURES`
  scenario fixture, and the v1.19.4 `<input type="file">`
  loader make every interaction work under `file://` without
  `fetch()`.
- **Top-ribbon buttons** (deterministic, no network, no
  kernel mutation): Load sample run / **Load local bundle**
  (v1.19.4) / Run mock (v1.17.4 / v1.18.4) / Validate /
  Compare Regimes / Export HTML.
- **Load local bundle** flow: pick a JSON via
  `<input type="file">` → `FileReader.readAsText` →
  `JSON.parse` → `validateBundleSchema` → render via
  `textContent` only. No engine execution. Sets
  `current_data_source = "local_bundle"`.
- **Accepted bundle profiles in the UI:** `quarterly_default`
  / `monthly_reference`.
- **Rejected bundle profiles in the UI:** `scenario_monthly`
  / `daily_display_only` / `future_daily_full_simulation`
  with `bundle profile '<profile>' is not loadable in v1.19.4
  static UI`.
- **Ledger excerpt cap:** 20 rows.
- **No-jump discipline:** preserved verbatim from v1.17.4 /
  v1.18.4 — no `scrollIntoView`, no `location.hash` mutation,
  no active-sheet shift; capture-and-restore protocol on
  scroll position.
- **Validate** runs every prior audit check + six new ones
  for the v1.19.4 surfaces.

## Discipline preserved bit-for-bit

Every v1.9.x / v1.10.x / v1.11.x / v1.12.x / v1.13.x / v1.14.x
/ v1.15.x / v1.16.x / v1.17.x / v1.18.x boundary anti-claim is
preserved unchanged at v1.19.last:

- No real data, no Japan calibration, no LLM-agent execution,
  no behaviour probability, no learned model.
- No price formation, no trading, no portfolio allocation, no
  investment advice, no rating.
- No lending decision, no covenant enforcement, no contract
  mutation, no constraint mutation, no default declaration.
- No financing execution, no loan approval, no securities
  issuance, no underwriting, no syndication, no allocation,
  no pricing.
- The v1.16.1 classifier output stays in
  `INTENT_DIRECTION_LABELS`; the forbidden trade-instruction
  verbs are disjoint by construction.
- The v1.17 inspection layer is **standalone-display-only** —
  pinned by the v1.17.1 module-text scan extended at v1.18.3
  to forbid scenario-storage module imports and now extended
  conceptually at v1.19.1 to forbid kernel / source-of-truth
  book / scenario-storage / settlement / financing-paths
  imports inside `world/run_export.py`.
- The v1.18.x scenario chain remains append-only and stimulus-
  only.
- The `PriceBook` is byte-equal across the full default sweep
  — pinned by tests at v1.15.5, v1.15.6, v1.16.2, v1.16.3,
  v1.17.1, v1.17.2, v1.18.1, v1.18.2, v1.18.3, **v1.19.1,
  v1.19.2, v1.19.3, and v1.19.3.1**.
- The v1.9.last public-prototype freeze, the v1.12.last
  attention-loop freeze, the v1.13.last settlement-substrate
  freeze, the v1.14.last corporate-financing-intent freeze,
  the v1.15.last securities-market-intent freeze, the
  v1.16.last endogenous-market-intent feedback freeze, the
  v1.17.last inspection-layer freeze, the v1.18.last
  scenario-driver-library freeze, and the v1.8.0 public
  release remain untouched.

## Key architecture (carried verbatim from v1.19.0)

- **CLI generates** the local JSON bundle.
- **Browser reads** the JSON as data only.
- **Browser does not execute Python.**
- **No backend, no Rails, no FastAPI, no Flask** in the
  default workflow.
- **No browser-to-engine execution.**
- **No file-system write** from the browser.

The CLI is the trust boundary; the JSON file is the contract;
the browser is a read-only viewer.

## monthly_reference boundary (carried verbatim)

`monthly_reference` creates actual monthly synthetic records
and information arrivals. It is **opt-in**. It is **not real
data ingestion**. It stores **no real indicator values**. It
uses **no real institutional identifiers**. It is **not daily
simulation**. It creates **no price records**, **no orders**,
**no trades**, **no investment advice**.

## Daily boundary (carried verbatim)

`daily_display_only` remains **display / report only** — the
v1.17.1 `daily_like` `ReportingCalendar` + `SyntheticDisplayPath`
serves it as a display refinement on top of an underlying
quarterly / monthly run. **No daily economic records.**

`future_daily_full_simulation` remains **out of scope for the
v1.19 sequence**. It will ship in **v2+ at the earliest**,
gated on the future market-mechanism / price-formation design
that the v1.16 freeze deferred. Adding daily full simulation
on top of the current surface would defeat the auditability
goal of every prior freeze.

## Future LLM compatibility (forward-affordance only)

v1.19 does **not** ship LLM execution. The audit shape pinned
at v1.18.0 carries forward verbatim:

- `reasoning_mode = "rule_based_fallback"` is **binding** at
  v1.19.x.
- `reasoning_slot = "future_llm_compatible"` reserves room for
  a future audited reasoning policy without changing the audit
  surface.
- `reasoning_policy_id` is a plain id naming the rule table or
  policy that produced the output — at v1.19.x always one of
  `"v1.19.3:information_release:rule_based_fallback"` (v1.19.3
  arrivals) or the v1.18.2 / v1.18.x policy ids (carried
  through verbatim on scenario chains).
- `evidence_ref_ids`, `unresolved_ref_count`, and
  `boundary_flags` are present on every emitted record.
- No `prompt_text`, no `llm_output`, no `llm_prose` field —
  these are in `FORBIDDEN_RUN_EXPORT_FIELD_NAMES` and
  `FORBIDDEN_INFORMATION_RELEASE_FIELD_NAMES`.

A future LLM-mode policy must populate the **same fields**
under a different `reasoning_policy_id`. There is no hidden
mutation of any source-of-truth book — pinned per book by
v1.19.x trip-wire tests.

## Known limitations

The v1.19 layer is a **deterministic local-run-bundle inspection
layer**. Specific limitations a reader should know about:

1. **`monthly_reference` is still synthetic.** A 12-month run
   with 51 information arrivals is *richer* than a 4-quarter
   sweep, but every label is still a closed-set ordinal over a
   synthetic vocabulary. There is no real CPI value behind an
   `IndicatorFamilyLabel = inflation` arrival; there is no
   real BOJ / FOMC / ECB date behind a
   `release_cadence_label = meeting_based` slot. Public FWE
   remains jurisdiction-neutral.
2. **Information arrivals are categories, not values.** An
   `InformationArrivalRecord` records *that a class of public
   information became available*. It stores no number. Tests
   pin the absence of `real_indicator_value` / `cpi_value` /
   `gdp_value` / `policy_rate` / `real_release_date` at any
   depth.
3. **UI loading is read-only.** The static workbench renders
   the loaded JSON; it cannot mutate, write, or re-export. The
   v1.19.4 button loads; it does not save.
4. **`scenario_monthly` is not executable yet.** The CLI
   rejects it; the UI rejects it. Wiring the v1.18.2
   `apply_scenario_driver(...)` chain into the
   `monthly_reference` profile is a future milestone (a
   v1.20 candidate; see below).
5. **`daily_display_only` is not economic simulation.** The
   v1.17.1 `daily_like` `ReportingCalendar` exposes a finer
   display axis; no economic record is added.
6. **No live run button yet.** The static workbench has no
   "Run engine now" affordance. The user runs the CLI in a
   terminal, then loads the produced JSON. This is by design
   — the browser remains a read-only viewer.

## What v1.20+ does next

v1.19.last freezes the public-FWE local-run-bundle / monthly-
reference / read-only UI inspection layer. The next roadmap
candidates remain:

- **v1.20 — Institutional Investor Mandate / Benchmark
  Pressure design** (one option). Adds a synthetic mandate /
  benchmark layer (jurisdiction-neutral, label-only) that
  shapes investor reasoning under the existing closed loop.
  Each new label is a closed-set extension; no new mechanism;
  the v1.18.2 scenario application + v1.19.3 information
  arrivals remain unchanged.
- **v1.20 — `scenario_monthly` profile** (alternative). Wires
  the v1.18.2 `apply_scenario_driver(...)` chain into the
  `monthly_reference` profile so a reader can see scenario-
  driver applications interleaved with month-by-month
  information arrivals. Each scenario application stays
  append-only; the canonical `quarterly_default` /
  `monthly_reference` digests are unchanged.
- **v2.0 — Japan public calibration in private JFWE only.**
  Public FWE remains jurisdiction-neutral and synthetic. The
  v1.19.3 release-cadence vocabulary is jurisdiction-neutral
  by design and may be calibrated to BOJ / METI / MIC / MOF
  schedules in private JFWE without changing the public
  surface.
- **Future LLM-mode reasoning policies.** When introduced,
  must populate the same `ActorReasoningInputFrame` /
  `ReasoningPolicySlot` audit shape pinned at v1.18.0 — input
  evidence ids, prompt / policy id, output label, confidence /
  status, rejected / unknown cases — and must **never** hide a
  mutation of any source-of-truth book.
- **Future price formation remains gated** until the v1.16 /
  v1.17 / v1.18 / v1.19 surface is operationally legible to a
  reviewer who has not read this codebase. Adding price
  formation on top of an opaque profile / bundle / arrival
  layer would defeat the auditability goal of every prior
  freeze.

The v1.19 chain stays profile-only, calendar-only, bundle-only,
CLI-first, and read-only-loader forever. Future milestones may
*cite* v1.19 profiles / bundles / arrival records (plain-id
cross-references, additional rendering kinds), but they may
**never** mutate the v1.19.0 / v1.19.3 vocabulary, replace the
deterministic CLI export with a runtime-active server bridge as
the headline path, hard-code real institution names / real
release dates / real indicator values, or introduce daily full
economic simulation on top of the calendar layer.
