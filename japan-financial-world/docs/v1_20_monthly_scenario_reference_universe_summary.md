# v1.20 Monthly Scenario Reference Universe — Summary

This document closes the v1.20 sequence of FWE. The sequence
ships the **first FWE milestone where the engine feels closer
to a synthetic financial world** — a 12-month, generic
11-sector, 11-firm reference universe with 4 investor and 3
bank archetypes, monthly information arrivals, one scheduled
scenario application, scenario context shifts, a CLI export
bundle, and static UI universe inspection.

v1.20.last itself is **docs-only** on top of the v1.20.0 →
v1.20.5 code freezes. No new module, no new test, no new
ledger event, no new label vocabulary, no new run profile.

This is **not** a market simulator, **not** a price-formation
layer, **not** a forecast layer, **not** a daily-frequency
economic simulation, **not** a recommendation surface, **not**
a real-data view, **not** a Japan calibration, **not** an LLM
execution path, **not** a backend server, **not** Ruby on
Rails, **not** FastAPI, **not** Flask, **not** browser-to-
Python execution, **not** a real-issuer mapping, **not** a
licensed-taxonomy dependency. It is **two new Python modules**
(`world/reference_universe.py`, `world/scenario_schedule.py`),
**one new keyword-argument value** on the existing
`run_living_reference_world` orchestrator
(`profile="scenario_monthly_reference_universe"`), **a new
CLI builder** (`_build_bundle_for_scenario_monthly_reference_universe`
in `examples/reference_world/export_run_bundle.py`), and **a
new Universe tab** in the existing static-HTML workbench
mockup. The chain executes the engine **only** from the
command line; the browser only reads JSON.

## Sequence map

| Milestone     | Module / surface                                                                                                                                                | Adds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| v1.20.0       | docs only                                                                                                                                                       | Monthly Scenario Reference Universe design — opens the v1.20 sequence as a **realism / granularity** layer combining temporal granularity (the v1.19.3 12-month `monthly_reference` cadence) with **cross-sectional breadth** (a generic 11-sector / 11-firm synthetic reference universe with 4 investor archetypes + 3 bank archetypes); pins the **new opt-in profile** `scenario_monthly_reference_universe`; pins three new immutable frozen dataclass shapes; pins the **closed-set 11-sector taxonomy** (every label carrying the `_like` suffix); pins the **default sensitivity matrix** (11 sectors × 6 dimensions × five-rung closed set); pins the **investor / bank archetype set**; pins the **bounded performance budget** (target 200-280 records / period, target [2400, 3360] records / run, **upper guardrail ≤ 4000 records**); pins the **`ScenarioSchedule` / `ScheduledScenarioApplication` storage** with default fixture; pins the **scenario-to-sector impact map**; pins the **per-milestone roadmap**. |
| v1.20.1       | `world/reference_universe.py`                                                                                                                                  | Three immutable frozen dataclasses (`ReferenceUniverseProfile`, `GenericSectorReference`, `SyntheticSectorFirmProfile`); one append-only `ReferenceUniverseBook` with 17 read methods; twelve closed-set frozensets; the v1.20.0 hard-naming-boundary `FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES` frozenset composing the v1.18.0 actor-decision tokens with the v1.20.0 real-issuer / real-financial / licensed-taxonomy tokens; three new `RecordType` enum values; kernel wired with `WorldKernel.reference_universe: ReferenceUniverseBook` empty by default; deterministic `build_generic_11_sector_reference_universe(...)` helper + explicit `register_generic_11_sector_reference_universe(...)` helper; +92 tests. **Storage only** — no run profile, no scenario schedule, no CLI extension, no UI extension. |
| v1.20.2       | `world/scenario_schedule.py`                                                                                                                                   | Two immutable frozen dataclasses (`ScenarioSchedule`, `ScheduledScenarioApplication`); one append-only `ScenarioScheduleBook` with 17 read methods; six closed-set frozensets; the v1.20.0 hard-naming-boundary `FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES` frozenset; two new `RecordType` enum values; `MONTHLY_PERIOD_INDEX_MIN` / `MONTHLY_PERIOD_INDEX_MAX` constants pinning the `[0, 11]` bound for monthly profile period indices; kernel wired with `WorldKernel.scenario_schedule: ScenarioScheduleBook` empty by default; deterministic `build_default_scenario_monthly_schedule(...)` helper; +90 tests. **Storage only** — no run profile, no scenario application execution, no CLI extension, no UI extension. |
| v1.20.3       | `world/reference_living_world.py` (extended)                                                                                                                    | The opt-in `scenario_monthly_reference_universe` run profile. `_SUPPORTED_RUN_PROFILE_LABELS` extended additively. When invoked, the orchestrator idempotently registers the v1.20.1 universe (1 + 11 + 11 = 23 setup records), the v1.18.1 credit-tightening scenario template (1 setup record), and the v1.20.2 default scenario schedule (1 + 1 = 2 setup records). Reuses the v1.19.3 `InformationReleaseCalendar` for monthly arrivals (3-5 / month, 51 total). Fires exactly one scheduled scenario application at `period_index == 3` / `month_04` via the v1.18.2 `apply_scenario_driver(...)` helper, emitting 1 `ScenarioDriverApplicationRecord` + 2 `ScenarioContextShiftRecord` (`market_environment` + `financing_review_surface`). The closed-loop chain (attention → investor market intent → aggregated market interest → indicative market pressure → capital structure review / financing path → next-period attention) runs unchanged on the larger 4-investor / 3-bank fixture. The heavyweight engagement / dialogue / escalation / strategic-response / valuation / investor-intent / stewardship-themes layer is skipped under the new profile to keep the per-period record count under the v1.20.0 budget. `LivingReferencePeriodSummary` and `LivingReferenceWorldResult` extended with seven v1.20.3 tuple fields. The canonical-form view in `examples/reference_world/living_world_replay.py` is extended additively (new keys appear only when non-empty so pre-existing digests stay byte-identical). Wall-clock leakage in v1.20.x book ledger entries is closed by adding `simulation_date` kwargs. +40 tests. |
| v1.20.4       | `examples/reference_world/export_run_bundle.py` (extended)                                                                                                      | CLI export for the new profile. `EXECUTABLE_PROFILES` extended additively. New `SCENARIO_UNIVERSE_PROFILE_SUPPORTED_SCENARIOS = ("none_baseline", "credit_tightening_driver")`. New `_build_bundle_for_scenario_monthly_reference_universe(...)` helper composes three v1.20.x-specific bundle sections: `metadata.reference_universe` (universe profile id + 11 sectors with the `_like` suffix + 11 firm profiles + per-sector sensitivity summary on the v1.20.0 six-dimension five-rung closed set); `scenario_trace` (scheduled-application + applied-application + emitted context-shift ids; merged context-surface labels + shift-direction labels; **per-application `affected_sector_ids` (11) + `affected_firm_profile_ids` (11)** read from the v1.20.4 orchestrator's application metadata; merged `boundary_flags` AND view; v1.18.0 `reasoning_modes` / `reasoning_slots` audit shape); `market_intent` + `financing` (compact label-only histograms with closed-loop cardinality counts). Reuses the v1.19.3.1 `information_arrival_summary`. `ledger_excerpt` bounded at 20 records with v1.20.x-setup-priority selection. Volatile fields stripped. The v1.20.3 orchestrator's scenario application metadata now stamps universe-wide `affected_sector_ids` + `affected_firm_profile_ids` so the per-sector / per-firm impact is visible to v1.20.4 / v1.20.5 without recomputing the universe. Bundle deterministic — same CLI args → byte-identical JSON. Pinned CLI bundle digest: `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`. +20 CLI tests. |
| v1.20.5       | `examples/ui/fwe_workbench_mockup.html` (extended)                                                                                                              | UI universe / sector / monthly scenario rendering. New **Universe** tab between Overview and Timeline; bottom-tabs nav now lists 11 tabs and 11 sheets; the tab ↔ sheet bijection is preserved. Empty-state card when no v1.20.4 bundle is loaded. Live-state card when a `scenario_monthly_reference_universe` bundle is loaded: profile-id header, eight-card counts row, **11-row × 9-column sector sensitivity heatmap** (CSS-class colour grid `sens-low` / `sens-moderate` / `sens-high` / `sens-very-high` / `sens-unknown` — colour decorative, cell text always echoes the closed-set label verbatim), **11-row × 6-column firm profile table** (`word-break: break-word` so long ids wrap), **scenario causal trace** five-step ordered list, boundary footer. `BUNDLE_EXECUTABLE_PROFILES` extended additively. `validateBundleSchema(...)` requires `metadata.reference_universe` + `scenario_trace.affected_*_ids` + manifest counts when the profile is `scenario_monthly_reference_universe`. Profile badge gains a distinct amber colour. Information arrival summary card now also visible for the new profile. In-page `Validate` audit gained 7 new checks. `textContent` only — no `innerHTML` for user-loaded JSON, no `eval`, no `fetch` / XHR, no backend, no file-system write, no `location.hash` mutation during bundle load. **No pytest delta** — UI / JS only. |
| v1.20.last    | docs only                                                                                                                                                       | This summary, the v1.20.last sections in `docs/world_model.md`, the v1.20.last freeze pin in `docs/performance_boundary.md`, the v1.20.last `test_inventory.md` header note, the v1.20.last `RELEASE_CHECKLIST.md` snapshot, the v1.20.last `examples/reference_world/README.md` addendum, the v1.20.last `examples/ui/README.md` addendum, and the v1.20.last `docs/fwe_reference_demo_design.md` cross-link. |

## What v1.20 ships — the monthly scenario reference universe

```
   user (terminal)
        │  python -m examples.reference_world.export_run_bundle \
        │      --profile scenario_monthly_reference_universe \
        │      --regime <constructive | mixed | constrained | tightening> \
        │      --scenario <none_baseline | credit_tightening_driver> \
        │      --out /tmp/fwe_scenario_universe_bundle.json
        ▼
   engine run profile (v1.20.3)
        │  reuses the v1.19.3 monthly cadence + v1.19.3
        │  InformationReleaseCalendar; idempotently registers
        │  the v1.20.1 generic 11-sector reference universe
        │  (1 universe profile + 11 sectors + 11 firm profiles
        │  = 23 setup records); registers the v1.18.1
        │  credit-tightening scenario template (1 setup record)
        │  and the v1.20.2 default scenario schedule (1 + 1
        │  setup records); fires exactly one scheduled scenario
        │  application at period_index == 3 / month_04
        │  emitting 1 ScenarioDriverApplicationRecord +
        │  2 ScenarioContextShiftRecord; runs the closed-loop
        │  chain on 12 months × 11 firms × 4 investors ×
        │  3 banks × 51 information arrivals
        ▼
   RunExportBundle (v1.20.4)
        │  three v1.20.x bundle sections —
        │  metadata.reference_universe (11 sectors with _like
        │  suffix + 11 firm profiles + sector sensitivity
        │  summary); scenario_trace (universe-wide
        │  affected_sector_ids = 11 + affected_firm_profile_ids
        │  = 11 + scenario template / scheduled application /
        │  applied application / context shift ids + reasoning
        │  audit shape + merged boundary_flags AND view);
        │  market_intent + financing (compact label-only
        │  histograms — 528 / 132 / 132 / 132 / 132 closed-loop
        │  cardinality)
        ▼
   write_run_export_bundle → JSON file (v1.20.4)
        │  no absolute path embedded; no wall-clock timestamp;
        │  no $USER / $HOSTNAME; same args → byte-identical
        │  bytes; CLI bundle digest pinned at
        │  ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf
        ▼
   user (browser, file://)
        │  click "Load local bundle"
        ▼
   <input type="file"> + FileReader.readAsText (v1.19.4 surface)
        │  no fetch; no XHR; no network; no engine
        ▼
   JSON.parse + validateBundleSchema (v1.20.5)
        │  required top-level keys + 7 boundary flags;
        │  EXECUTABLE_PROFILES (now includes
        │  scenario_monthly_reference_universe) vs
        │  DEFERRED_PROFILES closed-set check;
        │  profile-conditional checks for
        │  metadata.reference_universe + scenario_trace +
        │  manifest counts (sector_count == 11 / firm_count ==
        │  11 / investor_count == 4 / bank_count == 3)
        ▼
   render via textContent only (v1.20.5)
        │  new Universe tab between Overview and Timeline:
        │  empty-state card when no bundle is loaded; live-
        │  state card when a v1.20.4 bundle is loaded with the
        │  11-row × 9-column sector sensitivity heatmap, the
        │  11-row × 6-column firm profile table, the five-step
        │  scenario causal trace, and the affected-scope
        │  summary
        ▼
   current_data_source = "local_bundle"
```

A reader can answer five inspection questions by following
plain-id citations from the rendered output:

1. **Which universe is in scope?** — the Universe tab's
   profile-id header (`reference_universe_id` +
   `sector_taxonomy_label`) and the eight-card counts row.
2. **Which sectors and firms are in the universe?** — the
   sector sensitivity heatmap (11 rows × 6 sensitivity
   dimensions on the v1.20.0 five-rung closed set) and the
   11-row firm profile table.
3. **Which sectors and firms did the scheduled scenario
   touch?** — the sector heatmap's `Affected` column, the
   firm-table's `Affected` column, the counts row's
   *Affected sectors* / *Affected firms* cards, and the
   scenario-causal-trace `affected scope` step.
4. **What is the scenario causal lineage?** — the five-step
   trace block: scenario template → scheduled application →
   applied application → context shifts → affected scope.
5. **What did the engine see this period?** — the existing
   Overview / Timeline / Attention / Market Intent /
   Financing / Ledger surfaces, populated from the bundle's
   sections.

## Final user workflow

```sh
cd japan-financial-world
python -m examples.reference_world.export_run_bundle \
    --profile scenario_monthly_reference_universe \
    --regime constrained \
    --scenario credit_tightening_driver \
    --out /tmp/fwe_scenario_universe_bundle.json
```

```
open examples/ui/fwe_workbench_mockup.html       (or just double-click)
click "Load local bundle"                          (top ribbon)
select /tmp/fwe_scenario_universe_bundle.json
inspect the result on the new Universe tab — 11-sector
sensitivity heatmap, 11-firm profile table, scenario causal
trace, affected scope summary; cross-reference with Overview /
Timeline / Attention / Market Intent / Financing / Ledger
```

## Performance boundary

### Per-period record count (binding)

| Surface                                                       | Value (v1.20.3 / v1.20.4 default fixture)                                       |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Per-period record count, periods 0 / 1-2 / 4-11 (no scenario) | **257**                                                                          |
| Per-period record count, period 3 (scheduled scenario fires)  | **261**                                                                          |
| v1.20.0 per-period target window                              | `[200, 280]` — observed **257-261**, within target                                |
| Forbidden (would mean a denser inner loop)                    | per-period count outside `[200, 280]`                                            |

### Per-run record count (binding)

The v1.20 freeze pins **two** record counts. They are
deterministic, complementary, and **intentionally different**:

| Surface                                                                                            | Value      | What it counts                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| -------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Profile canonical record count** (v1.20.3)                                                       | **3220**   | `LivingReferenceWorldResult.created_record_count` after `run_living_reference_world(profile="scenario_monthly_reference_universe")` runs **on the v1.20.3 default test fixture** (no `market_regime` kwarg, so the v1.11.0 `_DEFAULT_MARKET_CONDITION_SPECS` apply). Pinned by `tests/test_living_reference_world_performance_boundary.py::test_v1_20_3_total_record_count_within_target_window`.                                                                                            |
| **CLI export bundle `manifest.record_count`** (v1.20.4)                                            | **3241**   | `bundle.manifest.record_count` written by the v1.20.4 CLI exporter when invoked with **`--regime constrained`** (the v1.11.2 `_REGIME_PRESETS["constrained"]` preset is selected, which surfaces a different market-condition spec set to the v1.8.x menu builder than the default). Pinned by `tests/test_run_export_cli.py::test_v1_20_4_scenario_universe_manifest_counts`.                                                                                                              |

The **+21 record delta** is fully explained by the v1.11.2
regime preset and lives entirely in the
`observation_set_selected` record type (the v1.8.x attention-
selection layer):

- `--regime constrained` (CLI) selects the v1.11.2
  `_REGIME_PRESETS["constrained"]` market-condition spec set.
- The v1.20.3 default test fixture does not pass a regime
  kwarg, so it uses the v1.11.0 `_DEFAULT_MARKET_CONDITION_SPECS`.
- The two specs sets surface a different number of market-
  condition records to the v1.8.x menu builder, which then
  emits a different number of `observation_set_selected`
  records over 12 periods × 7 actors. The delta is +21
  selections; every other record type is identical between
  the two paths.
- Pre-seeded variables / exposures (which the v1.20.3 test
  fixture seeds and the v1.20.4 CLI bare kernel does not) make
  **zero** difference to the count: with the default regime
  preset, both paths produce **3220**; with `--regime
  constrained`, both paths produce **3241**.

Both counts are deterministic on a given codebase + same
inputs. Both stay well under the v1.20.0 hard guardrail of
**≤ 4000 records**:

| Surface                                                       | Value        |
| ------------------------------------------------------------- | ------------ |
| v1.20.0 per-run target window                                 | `[2400, 3360]` — observed **3220** and **3241**, both within target |
| v1.20.0 hard guardrail                                        | **`≤ 4000`** — observed 3220 and 3241, both well under |

### Universe topology (binding)

| Surface                                                                   | Value                                                                       |
| ------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `manifest.sector_count`                                                   | **11**                                                                       |
| `manifest.firm_count`                                                     | **11**                                                                       |
| `manifest.investor_count`                                                 | **4**                                                                        |
| `manifest.bank_count`                                                     | **3**                                                                        |
| Period count                                                               | **12 (monthly)**                                                             |
| Information arrivals (per `metadata.information_arrival_summary`)         | **51** across **12** months (1 calendar / 51 scheduled releases)             |
| `manifest.scheduled_scenario_application_count`                           | **1**                                                                        |
| `manifest.scenario_application_count`                                     | **1**                                                                        |
| `manifest.scenario_context_shift_count`                                   | **2** (`market_environment` + `financing_review_surface`)                    |
| `scenario_trace.affected_sector_ids` count                                | **11** (universe-wide)                                                       |
| `scenario_trace.affected_firm_profile_ids` count                          | **11** (universe-wide)                                                       |

### Allowed loop shapes (binding)

| Loop shape                                                       | Cardinality                | Pinned by                                                                                                                                |
| ---------------------------------------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `O(P × F)` — firm states / market pressure / financing path     | 12 × 11 = **132** records  | `test_v1_20_3_firm_state_count_is_per_period_f`                                                                                         |
| `O(P × I × F)` — investor market intent                         | 12 × 4 × 11 = **528**      | `test_v1_20_3_investor_market_intent_count_is_per_period_i_times_f`                                                                     |
| `O(P × B × F)` — bank credit review                              | 12 × 3 × 11 = **396**      | `test_v1_20_3_bank_credit_review_count_is_per_period_b_times_f`                                                                         |
| `O(P × release_count)` — information arrivals                    | **51**                     | `test_v1_20_3_information_arrivals_emitted_each_month` and the v1.19.3 `[36, 60]` arrival-budget tests                                  |
| `O(scheduled_app_count × F)` — context shifts (scheduled month)  | ≤ 1 × 11 = 11 (actual: 2) | `test_v1_20_3_scenario_fires_only_in_scheduled_period`                                                                                  |

### Forbidden loop shapes (binding)

| Loop shape                              | Pinned out by                                                                                                              |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `O(P × I × F × scenario)`               | `test_v1_20_3_scenario_fires_only_in_scheduled_period` (scenario fires exactly once, not 4 × 11 = 44 per period)            |
| `O(P × I × F × venue)`                  | per-period investor-market-intent count assertion (exactly 528 per period, not 528 × V for V > 1)                          |
| `O(P × F × order)`                      | `test_v1_20_3_no_forbidden_mutation_record_in_ledger_slice` (no `ORDER_SUBMITTED` / `PRICE_UPDATED` / `CONTRACT_*` / `OWNERSHIP_TRANSFERRED` records in the ledger slice) |
| `O(P × day × ...)`                      | per-period record-count window (a daily inner loop would multiply each period's count by ~30, well past the 280 upper bound) |

## Pinned digests (binding)

| Surface                                                                                       | Value                                                                       |
| --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `scenario_monthly_reference_universe` `living_world_digest` (v1.20.3 default test fixture)     | **`5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`**       |
| `scenario_monthly_reference_universe` CLI export bundle digest (v1.20.4, `--regime constrained --scenario credit_tightening_driver`) | **`ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`**       |
| `quarterly_default` `living_world_digest` (unchanged across the entire v1.20 sequence)        | **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**       |
| `monthly_reference` `living_world_digest` (unchanged across the entire v1.20 sequence)        | **`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`**       |

The two `living_world_digest` values for `quarterly_default`
and `monthly_reference` are **byte-identical** to v1.19.last —
the v1.20 sequence is **opt-in**. Only when a caller picks
`scenario_monthly_reference_universe` does the engine emit
universe / sector / firm-profile / scenario-schedule records.

## Hard boundary statement

The v1.20 monthly scenario reference universe makes the FWE
engine feel closer to a synthetic financial world. It does
**not** turn FWE into one. Every boundary pinned at v1.18.last
/ v1.19.last carries forward verbatim, and v1.20 adds the
following:

- **No real companies.** Firm ids follow the synthetic
  `firm:reference_<sector>_a` pattern. No real company name,
  no real ticker, no real ISIN, no real LEI.
- **No real sector weights.** The sensitivity matrix uses
  `low` / `moderate` / `high` / `very_high` / `unknown`
  closed-set rungs; cells carry the label string verbatim.
  The Universe tab's heatmap colours are decorative only —
  the cell text always echoes the underlying label. No
  numeric weight, no real market-cap, no real index
  membership.
- **No licensed taxonomy dependency.** Every sector label
  carries the `_like` suffix to make the
  non-real-membership discipline visible. The public-FWE
  module text and tests pin the absence of bare `GICS`,
  `MSCI`, `S&P`, `FactSet`, `Bloomberg`, `Refinitiv`,
  `TOPIX`, `Nikkei`, and `JPX` tokens.
- **No real financial values.** No real revenue, EBITDA, net
  income, cash balance, debt amount, leverage ratio, or
  market cap. The v1.12.0 firm financial latent state is
  synthetic ordinal scalars in `[0, 1]`.
- **No real indicator values, no real release dates, no real
  institutional identifiers.** The v1.19.3 information-
  release calendar is jurisdiction-neutral and synthetic.
- **No price formation, no market price, no predicted index,
  no forecast path, no expected return, no target price, no
  trading, no orders, no execution, no clearing, no
  settlement, no financing execution.** The closed-loop
  chain ends with capital-structure review and financing
  path records — never with an order book, a trade, a loan
  approval, a bond / equity issuance, or an underwriting
  decision.
- **No direct firm decisions, no direct investor actions, no
  bank approval logic.** The scenario application stamps
  `affected_sector_ids` and `affected_firm_profile_ids` on
  the application metadata so a downstream consumer can see
  the *evidence / context* impact; it never decides on
  behalf of a firm, an investor, or a bank.
- **No investment advice.** No recommendation. No
  buy / sell / hold signal. No portfolio allocation.
- **No real data ingestion.** The CLI exporter reads only
  from a fresh kernel; the static UI reads only the bundle
  JSON. Neither calls the network.
- **No Japan calibration.** `japan_calibration` is in the
  v1.18.0 / v1.19.3 / v1.20.0 forbidden-field-name lists
  scanned across every payload, metadata mapping, and
  module text. The negation flag `no_japan_calibration` is
  the only place the substring appears.
- **No LLM execution, no LLM prose as source-of-truth.** The
  v1.18.0 audit shape (`reasoning_mode = "rule_based_fallback"`
  binding · `reasoning_policy_id` · `reasoning_slot =
  "future_llm_compatible"` · `evidence_ref_ids` ·
  `unresolved_ref_count` · `boundary_flags`) carries forward
  verbatim on every emitted scenario record. A future LLM-
  mode reasoning policy may replace the v1.18.x rule-based
  fallback without changing the audit surface.
- **No backend, no fetch / XHR, no file-system write, no
  browser-to-Python execution.** The CLI generates JSON; the
  browser reads JSON. The browser never calls Python and
  never writes files.

## UI status

- **Universe tab added** — between Overview and Timeline.
  The bottom-tabs nav now lists 11 tabs and 11 sheets:
  Cover · Inputs · Overview · **Universe** · Timeline ·
  Regime Compare · Attention · Market Intent · Financing ·
  Ledger · Appendix.
- **Tab ↔ sheet bijection** — preserved (11 ↔ 11).
- **Sector sensitivity heatmap** — 11-row × 9-column table
  with CSS rung classes (`sens-low` / `sens-moderate` /
  `sens-high` / `sens-very-high` / `sens-unknown`). Colour
  is decorative; the cell text always echoes the underlying
  closed-set label verbatim.
- **Firm profile table** — 11-row × 6-column table with
  `word-break: break-word` so long ids wrap without
  horizontal overflow.
- **Scenario causal trace** — five-step ordered list:
  scenario template → scheduled application → applied
  application → context shifts → affected scope.
- **Profile-conditional bundle validator** —
  `validateBundleSchema(...)` requires `metadata.reference_universe`
  + `scenario_trace.affected_*_ids` + `manifest.{sector,
  firm, investor, bank}_count` when the profile is
  `scenario_monthly_reference_universe`.
- **`textContent` only** — no `innerHTML` for user-loaded
  JSON, no `eval`, no script injection.
- **No `fetch` / XHR / network call** — no backend, no
  file-system write.
- **No `location.hash` mutation during bundle load** —
  capture-and-restore protocol mirrors the v1.19.4 loader.
- **Long ids wrap without overflow** — the universe-firm-
  table CSS uses `table-layout: fixed` and `word-break:
  break-word`.

## Known limitations

The v1.20 monthly scenario reference universe is **still
synthetic**. v1.20 increases realism along two axes (temporal
granularity + cross-sectional breadth) but explicitly does
**not**:

- **Replace the synthetic universe with a real investable
  one.** 11 firms is a *reference fixture*, not a real-
  issuer set. The synthetic firm ids
  (`firm:reference_<sector>_a`) carry no claim about any
  real company.
- **Replace the closed-set sensitivity labels with calibrated
  numeric parameters.** The five-rung sensitivity vocabulary
  (`low` / `moderate` / `high` / `very_high` / `unknown`) is
  an *ordering*, not a number.
- **Replace the bounded scenario context shifts with direct
  decisions.** The credit-tightening scenario emits 1
  application + 2 context shifts (`market_environment` +
  `financing_review_surface`); per-sector / per-firm impact
  lives on the application metadata as evidence, not as a
  firm decision, an investor action, or a bank approval.
- **Add real data.** No real indicator values, no real
  release dates, no real institutional identifiers, no real
  financial-statement values, no real market-cap values, no
  real leverage ratios.
- **Add Japan calibration.** No JP-specific data, no JP-
  specific timing, no JP-specific institution.
- **Add price formation or trading.** No price update, no
  market-price, no order book, no matching, no clearing, no
  settlement.
- **Add an investment recommendation surface.** The closed-
  loop chain ends at indicative pressure / capital-structure
  review / financing path — never at a buy / sell / hold
  signal or a portfolio allocation.
- **Unlock daily-frequency economic simulation.** The
  `daily_display_only` and `future_daily_full_simulation`
  profile labels remain designed-but-not-executable; the
  CLI exits non-zero on either.

## Next roadmap candidates (post-v1.20)

| Candidate                                                 | What it would add                                                                                                                                 | Status                                                                              |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **v1.21 Stress Composition Layer**                       | auditable composition of multiple synthetic stress stimuli on the same monthly reference universe. Reuses v1.18.1 `ScenarioDriverTemplate` ids verbatim; introduces six new dataclass shapes (`StressProgramTemplate` / `StressStep` / `StressFieldApplicationRecord` / `StressInteractionRule` / `StressFieldReadout` / optional `StressFieldSummaryProjection`); records *which stresses are active*, *how overlapping stresses compose on a context surface* (closed-set `amplify` / `dampen` / `offset` / `coexist` / `unknown`), and *which downstream records cite the composed field*. **Append-only / read-only / no causality claim / no magnitudes / no price / no recommendation.** | **Design scoped at v1.21.0** — see [`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md). |
| **v1.21 Institutional Investor Mandate / Benchmark Pressure** | benchmark / peer / mandate constraints on the v1.15.5 / v1.16.2 investor-intent layer; bounded synthetic mandate / benchmark id vocabulary. Decoupled from the stress composition layer; may ship in parallel. | Roadmap candidate.                                                                  |
| **v2.0 private JFWE Japan public calibration**           | bring in public Japanese data under licensing constraints; private repo only; would preserve every public-FWE boundary.                                                                                                                                                                                                                          | Gated. Not a public-FWE milestone.                                                  |
| **Future LLM reasoning policy**                          | a non-rule-based-fallback `reasoning_mode` that fills the same v1.18.0 audit shape (`reasoning_policy_id` / `reasoning_slot` / `evidence_ref_ids` / `unresolved_ref_count` / `boundary_flags`).                                                                                                                                                  | Gated by auditability + evidence-refs + source-book immutability + boundary flags. |
| **Future price formation**                               | a future milestone where indicative pressure can drive a synthetic price quote layer.                                                                                                                                                                                                                                                            | Gated until the v1.16 / v1.17 / v1.18 / v1.19 / v1.20 surface is operationally legible to a reviewer who has not read this codebase. |

## Reader-facing summary

v1.20 is the **first FWE milestone where the engine moves from
a small closed-loop demo to a richer synthetic market-like
reference universe**. With one CLI command a user can produce
a deterministic 12-month, 11-sector, 11-firm scenario universe
bundle, open the static workbench under `file://`, and inspect
the cross-sectional reach of the credit-tightening scenario
on the new Universe tab — all without a backend, without
browser-to-Python execution, without real data, without prices,
without trades, without actor decisions, and without Japan
calibration.

Test count: **4764 / 4764**. v1.20.last is docs-only on top
of the v1.20.0 → v1.20.5 code freezes.
