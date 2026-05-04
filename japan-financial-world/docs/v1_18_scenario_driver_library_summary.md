# v1.18 Scenario Driver Library — Summary

This document closes the v1.18 sequence of FWE. The sequence
ships a **scenario-driver inspection layer** on top of the v1.17
inspection surface and the v1.16 closed endogenous-market-intent
feedback loop: a closed-set vocabulary of synthetic scenario
templates, an append-only application helper, append-only
context-shift records, deterministic event / causal annotations
rendered through the v1.17.1 display surface, a markdown
scenario report driver, and a static UI scenario selector mock.
v1.18.last itself is **docs-only** on top of the v1.18.0 →
v1.18.4 code freezes.

This is **not** a market simulator, **not** a price-formation
layer, **not** a forecast layer, **not** a trading dashboard,
**not** an investment-recommendation surface, **not** a
real-data view, **not** a Japan calibration, **not** an LLM
execution path. It is two storage modules, one append-only
helper, three pure-function display helpers, one markdown
driver, and one HTML selector mock. The scenario layer
**executes nothing** — every emitted record is append-only, and
every pre-existing context record is byte-identical pre / post
application.

## Sequence map

| Milestone   | Module / surface                                                                                                                                                | Adds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| v1.18.0     | docs only                                                                                                                                                       | Scenario Driver Library design — the binding `ScenarioDriverTemplate → EvidenceCondition / ContextShift → ActorReasoningInputFrame → existing mechanism OR ReasoningPolicySlot → output label → audit metadata → v1.17 timeline / causal annotation` flow; the forbidden flow (`scenario template → "actor decides X"`); 20 closed-set scenario family labels grouped under 9 driver-group labels; the future-LLM-compatibility audit shape (`reasoning_mode` / `reasoning_policy_id` / `reasoning_slot` / `evidence_ref_ids` / `unresolved_ref_count` / `boundary_flags`); the naming discipline with the v1.18.0 forbidden binding list. |
| v1.18.1     | `world/scenario_drivers.py`                                                                                                                                     | Storage-only foundation — one immutable frozen `ScenarioDriverTemplate` dataclass + one append-only `ScenarioDriverTemplateBook` + ten closed-set vocabularies + the v1.18.0 hard-naming-boundary `FORBIDDEN_SCENARIO_FIELD_NAMES` frozenset; new ledger event type `RecordType.SCENARIO_DRIVER_TEMPLATE_RECORDED`; `WorldKernel.scenario_drivers` wired (empty by default → no canonical-view drift). +56 unit tests.                                                                                                       |
| v1.18.2     | `world/scenario_applications.py`                                                                                                                                | Append-only application helper — two immutable frozen dataclasses (`ScenarioDriverApplicationRecord`, `ScenarioContextShiftRecord`) + one append-only `ScenarioApplicationBook` + three new closed-set vocabularies (`APPLICATION_STATUS_LABELS` 6 / `CONTEXT_SURFACE_LABELS` 9 / `SHIFT_DIRECTION_LABELS` 10) + two new ledger event types + the deterministic `apply_scenario_driver(...)` helper with five minimal family→shift mappings + a `no_direct_shift` fallback for unmapped families. The helper **never mutates** a pre-existing context record; the cited `MarketEnvironmentBook` / `FirmFinancialStateBook` / `PriceBook` / `InterbankLiquidityStateBook` / `CorporateFinancingPathBook` / `InvestorMarketIntentBook` / `ScenarioDriverTemplateBook` snapshots are byte-identical pre / post call (pinned per-book by trip-wire tests). +72 tests.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| v1.18.3     | `world/display_timeline.py` (extended) + `examples/reference_world/scenario_report.py`                                                                          | Scenario report / causal timeline integration — three pure-function display helpers (`build_event_annotations_from_scenario_shifts`, `build_causal_timeline_annotations_from_scenario_shifts`, `render_scenario_application_markdown`) + a kernel-reading driver with a deterministic six-template default fixture exercising all five v1.18.2 mappings plus the `no_direct_shift` fallback; surface-to-annotation-type map (`market_environment` / `interbank_liquidity` / `industry_condition` / `firm_financial_state` → `market_environment_change`; `market_pressure_surface` → `market_pressure_change`; `financing_review_surface` → `financing_constraint`; `attention_surface` → `attention_shift`; `display_annotation_surface` / `unknown` / `no_direct_shift` → `synthetic_event`); causal annotation shape `(template_id, application_id) → shift_id` carrying the v1.18.0 audit-metadata block verbatim; severity coercion `stress` → `high` (preserves the higher rung within the v1.17.1 `SEVERITY_LABELS = {low, medium, high, unknown}` vocabulary). +23 tests in `tests/test_display_timeline.py`, +18 tests in `tests/test_scenario_report.py`. |
| v1.18.4     | `examples/ui/fwe_workbench_mockup.html` + `examples/ui/sample_living_world_manifest.json` + `examples/ui/README.md`                                              | Static UI scenario selector mock — seven-option scenario driver selector on the Inputs tab (`Baseline` / `Rate repricing` / `Credit tightening` / `Funding window closure` / `Liquidity stress` / `Information gap` / `Unmapped fallback`); scenario summary + scenario trace cards on the Overview tab; scenario event annotation card + scenario trace table on the Timeline tab; deterministic seven-entry `SCENARIO_FIXTURES` data structure mirrored in inline + standalone JSON; long-id wrapping fix (`table-layout: fixed` + `overflow-wrap: anywhere`) so plain-id citations cannot push the page wider than the viewport. The scenario selector is **fixture switching only — the Python engine is not invoked from the UI**. Same `(regime, scenario)` pair → same visible state. The no-jump discipline pinned at v1.17.4 is preserved verbatim.       |
| v1.18.last  | docs only                                                                                                                                                       | This summary, §127 in `docs/world_model.md`, the v1.18.last `RELEASE_CHECKLIST.md` snapshot, the v1.18.last `performance_boundary.md` update, the v1.18.last `test_inventory.md` header note, the v1.18.last `examples/reference_world/README.md` addendum, the v1.18.last `examples/ui/README.md` cross-link, and the v1.18.last `docs/fwe_reference_demo_design.md` headline note.                                                                                                                                       |

## What v1.18 ships — the scenario inspection surface

The v1.18 surface lets a reader pick a synthetic scenario
template, project it onto FWE evidence / context surfaces by
*emitting new records that cite the template via plain-id
citations*, and walk the resulting append-only chain in finite
read steps:

```
ScenarioDriverTemplate                           (v1.18.1)
        │  storage-only — closed-set family / group / severity /
        │  actor-scope / expected-annotation-type labels +
        │  v1.18.0 audit fields. No magnitude. No confidence.
        │  No actor-decision field.
        ▼
ScenarioDriverApplicationRecord                  (v1.18.2)
        │  per-call receipt with `application_status_label`
        │  ∈ APPLICATION_STATUS_LABELS. Cites
        │  `source_template_ids` + `source_context_record_ids`
        │  + `emitted_context_shift_ids` via plain ids only.
        ▼
ScenarioContextShiftRecord                       (v1.18.2)
        │  one or more per application — depending on the
        │  family→shift mapping. Cites `affected_context_record_ids`
        │  via plain ids; the cited records are byte-identical
        │  pre / post call.
        ▼
EventAnnotationRecord / CausalTimelineAnnotation  (v1.18.3)
        │  rendered through the v1.17.1 display vocabulary;
        │  deterministic surface→annotation_type mapping;
        │  causal shape `(template_id, application_id) →
        │  shift_id`; audit-metadata block carried verbatim.
        ▼
Markdown report (v1.18.3) / static UI cards (v1.18.4)
   six markdown sections: Scenario templates / Scenario
   applications / Emitted context shifts / Event annotations /
   Causal timeline annotations / Boundary statement.
   UI: Inputs (selector) + Overview (summary + trace) +
   Timeline (event annotation + trace).
```

A reader can answer four scenario-inspection questions by
following plain-id citations from the rendered output:

1. **Which template is in play?** — the Overview *Scenario
   driver* card's family / group / template id row.
2. **What was emitted?** — the Overview *Scenario trace* card's
   application id / context shift id / context surface / shift
   direction / expected annotation type rows.
3. **Where does it land in the timeline?** — the Timeline
   *Scenario event annotation* card's date · type · severity ·
   `annotation_label` row.
4. **What is the audit shape?** — every annotation's
   `metadata` block carries `reasoning_mode`,
   `reasoning_policy_id`, `reasoning_slot`, `evidence_ref_ids`,
   `unresolved_ref_count`, and `boundary_flags`.

### v1.18.0 — Scenario Driver Library Design

- The **stimulus / not response** discipline — a scenario
  template never carries a sentence of the form "actor decides
  X". The closest a template gets to actor behaviour is an
  `expected_annotation_type_label` ∈ a closed-set vocabulary
  that names the *category* of inspection annotation a
  downstream mechanism may emit, never the response itself.
- The **forbidden flow** — `scenario template → "firm decides
  X" / "investor reduces Y" / "bank restricts Z"` is rejected
  by construction. Forbidden field names: `firm_decision` /
  `investor_action` / `bank_approval` / `trading_decision` /
  `optimal_capital_structure` (and the v1.17.0 forbidden
  display-name set: `market_price` / `predicted_index` /
  `forecast_path` / `expected_return` / `target_price` /
  `recommendation` / `investment_advice` / `real_data_value` /
  `japan_calibration` / `llm_output` / `llm_prose` /
  `prompt_text`).
- 20 closed-set **scenario family labels** grouped under 9
  closed-set **driver-group labels**, plus auxiliary closed-set
  vocabularies for severity / actor scope / event-date policy /
  expected-annotation type. v1.18.x may extend a vocabulary via
  a single coordinated change; the closed-set discipline is
  binding.
- The future-LLM-compatibility **audit shape** pinned on every
  emitted record: `reasoning_mode = "rule_based_fallback"`
  (binding at v1.18.x), `reasoning_policy_id`, `reasoning_slot
  = "future_llm_compatible"`, `evidence_ref_ids`,
  `unresolved_ref_count`, `boundary_flags`. A future LLM-mode
  policy must populate the same fields under a different policy
  id; the audit surface is forward-compatible.

### v1.18.1 — ScenarioDriverTemplate Storage

- One immutable frozen `ScenarioDriverTemplate` dataclass +
  one append-only `ScenarioDriverTemplateBook` + ten closed-set
  vocabularies (`SCENARIO_FAMILY_LABELS` 21 / `DRIVER_GROUP_LABELS`
  10 / `EVENT_DATE_POLICY_LABELS` 6 / `SEVERITY_LABELS` 5 /
  `AFFECTED_ACTOR_SCOPE_LABELS` 10 / `EXPECTED_ANNOTATION_TYPE_LABELS`
  7 / `REASONING_MODE_LABELS` 4 / `REASONING_SLOT_LABELS` 4 /
  `STATUS_LABELS` 6 / `VISIBILITY_LABELS` 3) + the v1.18.0
  hard-naming-boundary `FORBIDDEN_SCENARIO_FIELD_NAMES`
  frozenset (23 entries) — disjoint from every closed-set
  vocabulary; scanned against dataclass field names + payload
  keys + metadata keys at construction.
- **No `confidence` field** (templates are not predictions).
  **No numeric magnitude field** (templates are *category*
  shifts, not magnitudes). **No actor-decision field**
  (templates do not decide).
- New ledger event type `RecordType.SCENARIO_DRIVER_TEMPLATE_RECORDED`.
  `WorldKernel.scenario_drivers: ScenarioDriverTemplateBook`
  wired — **empty by default**, so the canonical view of an
  unmodified default sweep is byte-identical to v1.17.last.
- `reasoning_mode` defaults to `rule_based_fallback`;
  `reasoning_slot` defaults to `future_llm_compatible`.

### v1.18.2 — Scenario Driver Application Helper

- Two immutable frozen dataclasses
  (`ScenarioDriverApplicationRecord`,
  `ScenarioContextShiftRecord`) + one append-only
  `ScenarioApplicationBook` with 14 read methods + three new
  closed-set vocabularies + two new ledger event types
  (`SCENARIO_DRIVER_APPLICATION_RECORDED`,
  `SCENARIO_CONTEXT_SHIFT_RECORDED`).
- Five minimal deterministic family→shift mappings:
  - `rate_repricing_driver` / `macro_rates` →
    `market_environment` × `tighten` (or
    `increase_uncertainty` if `severity_label = "low"`) ×
    `market_environment_change`;
  - `credit_tightening_driver` / `credit_liquidity` →
    `market_environment` × `tighten` × `market_environment_change`
    **and** `financing_review_surface` × `tighten` ×
    `financing_constraint`;
  - `funding_window_closure_driver` →
    `financing_review_surface` × `deteriorate` ×
    `financing_constraint`;
  - `liquidity_stress_driver` / `credit_liquidity` →
    `interbank_liquidity` × `deteriorate` **and**
    `market_environment` × `deteriorate` × `market_environment_change`;
  - `information_gap_driver` → `attention_surface` ×
    `information_gap` × `attention_shift`.
- Other families fall back to a single `unknown` ×
  `no_direct_shift` × `<template.expected_annotation_type_label>`
  annotation. Every application emits **at least one shift**.
- The helper reads only the named template via
  `kernel.scenario_drivers.get_template(...)` and the cited
  `source_context_record_ids` — pinned by a trip-wire test
  that patches every other book's `list_*` / `snapshot`
  methods to raise; the helper still succeeds.
- Every emitted record carries the v1.18.0 audit-metadata
  block + the seven boundary flags (`no_actor_decision` /
  `no_llm_execution` / `no_price_formation` / `no_trading` /
  `no_financing_execution` / `no_investment_advice` /
  `synthetic_only`).
- `apply_scenario_driver(...)` is **deterministic** —
  identical `(template_id, as_of_date, source_context_record_ids)`
  inputs produce identical `scenario_application_id` and
  byte-identical book snapshots.
- **Append-only invariant pinned per book**: `MarketEnvironmentBook`
  / `FirmFinancialStateBook` / `PriceBook` /
  `InterbankLiquidityStateBook` / `CorporateFinancingPathBook` /
  `InvestorMarketIntentBook` / `ScenarioDriverTemplateBook`
  snapshots are byte-equal pre / post call.

### v1.18.3 — Scenario Report and Causal Timeline Integration

- Three pure-function helpers in `world/display_timeline.py`
  (`build_event_annotations_from_scenario_shifts(...)`,
  `build_causal_timeline_annotations_from_scenario_shifts(...)`,
  `render_scenario_application_markdown(...)`). Inputs are
  anonymous record-like objects accessed via `getattr`; the
  module imports no source-of-truth book or kernel (pinned by
  the v1.17.0 standalone-display module-text scan extended at
  v1.18.3 to forbid `from world.scenario_drivers` and
  `from world.scenario_applications`).
- Surface-to-annotation-type mapping (deterministic, minimal):
  `market_environment` / `interbank_liquidity` /
  `industry_condition` / `firm_financial_state` →
  `market_environment_change`; `market_pressure_surface` →
  `market_pressure_change`; `financing_review_surface` →
  `financing_constraint`; `attention_surface` →
  `attention_shift`; `display_annotation_surface` / `unknown` →
  `synthetic_event`; `shift_direction_label = no_direct_shift`
  overrides the surface mapping to `synthetic_event` so the
  v1.18.2 fallback path is visibly tagged.
- Severity coercion `stress` → `high`. The v1.17.1
  `SEVERITY_LABELS = {low, medium, high, unknown}` vocabulary
  is unchanged; the higher rung is preserved.
- Causal annotation shape: `source_record_ids = (template_id,
  application_id)`; `downstream_record_ids = (shift_id,)`. The
  annotation does **not** invent an "actor decision" arrow.
- New kernel-reading driver at
  `examples/reference_world/scenario_report.py` with a
  deterministic six-template default fixture exercising all
  five v1.18.2 mappings plus the `no_direct_shift` fallback;
  builds its own *fresh* kernel (so running the driver does
  not move the default-fixture `living_world_digest` of a
  separately seeded default sweep); renders six markdown
  sections (Scenario templates / Scenario applications /
  Emitted context shifts / Event annotations / Causal timeline
  annotations / Boundary statement). Same fixture + same
  `as_of_date` → byte-identical markdown.

### v1.18.4 — Static UI Scenario Selector Mock

- The single-file static HTML workbench gains a **scenario
  driver selector** card on the Inputs tab with seven options:
  `Baseline` (`none_baseline`), `Rate repricing`, `Credit
  tightening`, `Funding window closure`, `Liquidity stress`,
  `Information gap`, `Unmapped fallback`
  (`no_direct_shift_fallback`). Selecting and clicking
  **Run mock** updates the top ribbon status to
  `mock UI run · <regime> · <scenario> · static fixture · no
  engine execution`.
- Overview gains a *Scenario driver* summary card +
  *Scenario trace* card showing template id → application id →
  context shift id → context surface → shift direction →
  expected annotation type → reasoning mode / slot / boundary
  flags.
- Timeline gains a *Scenario event annotation* card +
  scenario trace table; the **`no_direct_shift_fallback`**
  option surfaces the v1.18.2 fallback callout verbatim —
  *"No direct context shift emitted beyond
  fallback/no_direct_shift. This is not an error. The template
  is stored but not yet mapped to a concrete context surface."*
- Long plain-id citations cannot push the page wider than the
  viewport: the scenario tables use `table-layout: fixed` +
  `overflow-wrap: anywhere`. The no-jump discipline pinned at
  v1.17.4 is preserved verbatim — Run mock does not call
  `scrollIntoView`, change `location.hash`, change the active
  sheet, change browser zoom, or change scroll position.
- Inline JSON (`#fwe-sample-manifest`) and standalone
  `sample_living_world_manifest.json` both gain four top-level
  keys: `scenario_selector`, `scenario_fixtures` (7 entries),
  `scenario_trace`, `selected_scenario`. Both parse with
  `json.loads`. **Validate** checks every key, every required
  fixture field, the `no_direct_shift` callout text, the
  scenario selector / summary / trace / annotation card
  bijection, and the scenario pill option set.
- The selector is **fixture switching only — the Python engine
  is not invoked from the UI**. Same `(regime, scenario)`
  pair → same visible state.

## What v1.18 explicitly is not

- **Not a market simulator.** The scenario layer renders
  append-only records that *cite* the v1.16 closed-loop
  records; it invents no new economic edge.
- **Not price formation.** No `market_price`, no
  `predicted_index`, no `forecast_path`, no `expected_return`,
  no `target_price`. These names are pinned by the v1.18.0
  `FORBIDDEN_SCENARIO_FIELD_NAMES` frozenset and the v1.17.0
  `FORBIDDEN_DISPLAY_NAMES` frozenset and scanned for absence
  by tests.
- **Not actor decisions.** No `firm_decision`, no
  `investor_action`, no `bank_approval`, no `trading_decision`,
  no `optimal_capital_structure`. A v1.18.2 trip-wire test
  pins the disjoint set on dataclass field names, payload
  keys, metadata keys, and boundary-flag keys.
- **Not trading.** No order submission, no order book, no
  matching, no execution, no clearing, no settlement, no
  quote dissemination, no bid / ask, no `PriceBook` mutation.
- **Not investment advice.** No `recommendation`, no
  `investment_advice`. These appear in the workbench HTML and
  the markdown report only inside negation / boundary /
  forbidden-list contexts (e.g. the boundary statement that
  lists them as "deliberately absent").
- **Not real data.** No real exchange / broker / index /
  regulator / issuer identifier appears in any v1.18 module,
  fixture, test, or rendered view. Every numeric value is a
  synthetic ordinal in `[0.0, 1.0]` or a closed-set label.
- **Not a Japan calibration.** All venue ids, security ids,
  and labels are jurisdiction-neutral and synthetic. Real-
  venue calibration remains private JFWE territory (v2 / v3
  only).
- **Not LLM execution.** No model, no prompt, no API call, no
  generated content. `reasoning_mode = "rule_based_fallback"`
  is binding at v1.18.x; the `future_llm_compatible` slot
  marker is an architectural commitment, not a runtime
  capability. There is no `prompt_text` field, no `llm_output`
  field, no `llm_prose` field — pinned by the v1.18.0
  forbidden field-name set.
- **Not a learned model.** No training data, no gradient, no
  fitting, no cross-validation, no backtest. Every mapping
  rule is a Boolean combination of closed-set inputs.
- **Not a mutation of pre-existing context records.** The
  v1.18.2 helper writes only via `add_application(...)` /
  `add_context_shift(...)`. Every cited
  `MarketEnvironmentStateRecord` /
  `FirmFinancialStateRecord` /
  `InterbankLiquidityStateRecord` /
  `CorporateFinancingPathRecord` /
  `InvestorMarketIntentRecord` is byte-identical pre / post
  application.

## Performance boundary at v1.18.last

- **Per-period record count (default fixture, no scenario
  applied):** **108** (period 0) / **110** (periods 1+).
  Unchanged from v1.17.last. v1.18.x adds zero records to the
  per-period sweep — the scenario books are empty by default,
  the application helper runs only when `apply_scenario_driver(...)`
  is explicitly invoked, and the regime-comparison driver is
  unchanged.
- **Per-run window (default fixture):** **`[432, 480]`**.
  Unchanged.
- **Default 4-period sweep total:** **460 records**. Unchanged.
- **Integration-test `living_world_digest` (default fixture,
  no scenario applied):**
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**.
  Unchanged from v1.17.last across all v1.18 milestones —
  v1.18.0 was docs-only; v1.18.1 added an empty
  `ScenarioDriverTemplateBook` to `WorldKernel` (pinned
  byte-identical by
  `tests/test_scenario_drivers.py::test_empty_scenario_drivers_does_not_move_default_living_world_digest`);
  v1.18.2 added an empty `ScenarioApplicationBook` (pinned by
  `tests/test_scenario_applications.py::test_empty_scenario_applications_does_not_move_default_living_world_digest`
  and `…::test_explicit_scenario_application_does_not_touch_default_run`);
  v1.18.3 helpers and the v1.18.3 driver build their own
  *fresh* kernel (pinned by
  `tests/test_display_timeline.py::test_scenario_helpers_do_not_move_default_living_world_digest`
  and
  `tests/test_scenario_report.py::test_run_scenario_report_does_not_move_default_living_world_digest`);
  v1.18.4 is a static-HTML edit only.
- **Test count:** **4334 / 4334** passing. Up from 4165 / 4165
  at v1.17.last (+169 across v1.18.1 / v1.18.2 / v1.18.3).
  v1.18.0 / v1.18.4 are docs / static-HTML only and add no
  pytest tests; the in-page Validate button enforces the
  scenario-selector / scenario-trace bijection invariants in
  v1.18.4.

## UI status at v1.18.last

- **Type:** single-file static HTML prototype.
- **File:** `examples/ui/fwe_workbench_mockup.html`.
- **Backend:** none.
- **Build tools:** none.
- **External runtime:** none.
- **Network I/O:** none. The inline JSON manifest, the
  `SAMPLE_RUNS` regime fixture, and the `SCENARIO_FIXTURES`
  scenario fixture make every interaction work under `file://`
  without `fetch()`.
- **Run mock:** fixture-switching only — the Python engine is
  **not** invoked. Same `(regime, scenario)` pair →
  byte-identical UI state. Status reads `mock UI run ·
  <regime> · <scenario> · static fixture · no engine execution`.
- **Scenario selector:** seven options on the Inputs tab —
  `Baseline` (`none_baseline`), `Rate repricing`
  (`rate_repricing_driver`), `Credit tightening`
  (`credit_tightening_driver`), `Funding window closure`
  (`funding_window_closure_driver`), `Liquidity stress`
  (`liquidity_stress_driver`), `Information gap`
  (`information_gap_driver`), `Unmapped fallback`
  (`no_direct_shift_fallback`). Picking a scenario and
  clicking Run mock updates the Overview *scenario summary* +
  *scenario trace* cards and the Timeline *scenario event
  annotation* card.
- **`no_direct_shift_fallback`** option surfaces the v1.18.2
  fallback callout verbatim — *"No direct context shift
  emitted beyond fallback/no_direct_shift. This is not an
  error. The template is stored but not yet mapped to a
  concrete context surface."*
- **Future-LLM-compatibility note** visible on every scenario
  card: *"Reasoning mode: `rule_based_fallback`. Reasoning
  slot: `future_llm_compatible`. No LLM execution in this
  prototype."*
- **Validate:** strict in-page sanity check on the bottom-tab
  ↔ sheet article bijection (10 of each, no orphans, no
  duplicates), the scenario selector / summary / trace /
  annotation card presence, the scenario pill option set, the
  `SCENARIO_FIXTURES` field set per option, the
  `no_direct_shift_fallback` flag and callout text, and the
  inline JSON `scenario_selector` / `scenario_fixtures` /
  `scenario_trace` / `selected_scenario` keys.
- **Compare Regimes:** static / display-report navigation —
  unchanged from v1.17.4.
- **Export HTML:** non-destructive — unchanged.
- **Bottom-tab ↔ sheet article mapping:** 10 ↔ 10 bijection,
  enforced at runtime by Validate.
- **Long plain-id wrapping fix (v1.18.4):** the scenario
  trace tables use `table-layout: fixed` + `overflow-wrap:
  anywhere` so plain-id citations cannot push the page wider
  than the viewport when Run mock fills them.
- **Sample fixture status:** the embedded scenario fixtures
  carry `fixture_kind: sample_fixture` / `fixture_note:
  v1.18.4 selector mock — fixture switching only. Python
  engine NOT invoked from the UI.`

## Discipline preserved bit-for-bit

Every v1.9.x / v1.10.x / v1.11.x / v1.12.x / v1.13.x / v1.14.x /
v1.15.x / v1.16.x / v1.17.x boundary anti-claim is preserved
unchanged at v1.18.last:

- No real data, no Japan calibration, no LLM-agent execution,
  no behaviour probability, no learned model.
- No price formation, no trading, no portfolio allocation, no
  investment advice, no rating.
- No lending decision, no covenant enforcement, no contract
  mutation, no constraint mutation, no default declaration.
- No financing execution, no loan approval, no securities
  issuance, no underwriting, no syndication, no allocation, no
  pricing.
- The v1.12.6 watch-label classifier is unchanged.
- The v1.12.9 attention-budget discipline is preserved
  bit-for-bit; v1.16.3 fresh focus passes through the same
  decay / saturation pipeline.
- The v1.13.5 settlement / interbank-liquidity substrate is
  unchanged.
- The v1.14 corporate-financing record set is unchanged in
  vocabulary; v1.15.6 added two citation slots and v1.16.x /
  v1.17.x / v1.18.x added zero new vocabulary inside that
  record set.
- The v1.15 `SAFE_INTENT_LABELS` vocabulary is unchanged.
- The v1.16.1 classifier output is strictly in
  `INTENT_DIRECTION_LABELS`; the forbidden trade-instruction
  verbs are disjoint by construction.
- The v1.16.2 living-world `intent_direction_label` is
  produced by the v1.16.1 classifier — never by an index
  rotation.
- The v1.16.3 `ActorAttentionStateRecord.focus_labels` widening
  reads only cited prior-period pressure / path ids — never a
  global scan.
- The `PriceBook` is byte-equal across the full default sweep
  — pinned by tests at v1.15.5, v1.15.6, v1.16.2, v1.16.3,
  v1.17.1, v1.17.2, **v1.18.1, v1.18.2, and v1.18.3**.
- The v1.17 inspection layer is **standalone-display-only** —
  pinned by a v1.17.1 module-text scan extended at v1.18.3 to
  forbid `from world.scenario_drivers` and
  `from world.scenario_applications`.
- The v1.9.last public-prototype freeze, the v1.12.last
  attention-loop freeze, the v1.13.last settlement-substrate
  freeze, the v1.14.last corporate-financing-intent freeze,
  the v1.15.last securities-market-intent freeze, the
  v1.16.last endogenous-market-intent feedback freeze, the
  v1.17.last inspection-layer freeze, and the v1.8.0 public
  release remain untouched.

## Future LLM compatibility (forward-affordance only)

v1.18 does **not** ship LLM execution. The
`future_llm_compatible` slot marker on every record / template
is an architectural commitment, not a runtime capability:

- `reasoning_mode = "rule_based_fallback"` is **binding** at
  v1.18.x.
- `reasoning_slot = "future_llm_compatible"` reserves room for
  a future audited reasoning policy without changing the audit
  surface.
- `reasoning_policy_id` is a plain id naming the rule table or
  policy that produced the output — at v1.18.x always
  `"v1.18.2:scenario_application:rule_based_fallback"` (or
  `"v1.18.1:storage_only:rule_based_fallback"`).
- `evidence_ref_ids` is a plain-id citation tuple of the
  records the policy read.
- `unresolved_ref_count` is a non-negative integer.
- `boundary_flags` is a Boolean mapping that names each
  binding-boundary check the policy ran (the v1.18.2 default
  set: `no_actor_decision` / `no_llm_execution` /
  `no_price_formation` / `no_trading` /
  `no_financing_execution` / `no_investment_advice` /
  `synthetic_only`).

A future LLM-mode policy must populate the **same fields**
under a different `reasoning_policy_id`. There is no
`prompt_text` field, no `llm_output` field, no `llm_prose`
field — these are in `FORBIDDEN_SCENARIO_FIELD_NAMES`. There
is no hidden mutation of any source-of-truth book — the
v1.18.2 trip-wire tests pin per-book byte-equality pre / post
helper call.

## Known limitations

The v1.18 layer is a **rendering / inspection / static UI
selector** for synthetic scenario templates. Specific
limitations a reader should know about:

1. **Scenario templates are synthetic, not forecasts.** A
   `ScenarioDriverTemplate` names a *category* of exogenous
   condition (rate repricing, credit tightening, …); it carries
   no probability, no magnitude in any economic unit, and no
   calibration. The label is the contract — there is no number
   behind it.
2. **Application is rule-based fallback.** v1.18.2 ships
   exactly five family→shift mappings + a `no_direct_shift`
   fallback. The mappings are the simplest deterministic table
   that satisfies the v1.18.0 design rules; future audited
   reasoning policies can replace the table without changing
   the audit surface.
3. **Actor response stays in existing / future mechanisms.**
   The scenario layer never asserts "actor X reacts with Y".
   Downstream actor responses still flow through the v1.12 /
   v1.14 / v1.15 / v1.16 mechanisms (or, in the future, a
   `ReasoningPolicySlot`) — the scenario driver is the
   *stimulus*, never the *response*.
4. **No scenario is calibrated to real data.** Every
   `scenario_driver_template_id`, every numeric value, and
   every label is jurisdiction-neutral and synthetic. Real-
   venue / real-issuer / real-regulator calibration is private
   JFWE territory (v2 / v3 only).
5. **The static UI scenario selector is a mock, not live
   execution.** Picking a scenario and clicking Run mock
   switches a fixture; running `apply_scenario_driver(...)` on
   a kernel still requires
   `python -m examples.reference_world.scenario_report` (or a
   custom Python entry point).
6. **`no_direct_shift` fallback is visible by design.** A
   `thematic_attention_driver` / `short_squeeze_attention_driver`
   / etc. template falls back to the `unknown` ×
   `no_direct_shift` annotation; the markdown report and the
   v1.18.4 UI tag this as "this is not an error — the template
   is stored but not yet mapped to a concrete context
   surface". A future v1.19+ milestone may add concrete
   mappings for additional families.

## What v1.19+ does next

v1.18.last freezes the public-FWE scenario-driver inspection
layer. The next roadmap candidates remain:

- **v1.19 — local run bridge / report export (conditional).**
  If interactive scenario execution becomes necessary, a
  CLI-driven bridge that writes a regime-comparison panel + a
  scenario-application markdown report to disk
  (markdown / JSON), which the static workbench can then
  `Load sample run` against. Still no backend, no build, no
  network.
- **v2.0 — Japan public calibration in private JFWE.** Real-
  venue / real-issuer / real-regulator calibration moves to
  private JFWE only. Public FWE remains jurisdiction-neutral
  and synthetic.
- **Future LLM-mode reasoning policies.** When introduced,
  must populate the same `ActorReasoningInputFrame` /
  `ReasoningPolicySlot` audit shape pinned at v1.18.0 — input
  evidence ids, prompt / policy id, output label, confidence /
  status, rejected / unknown cases — and must **never**
  hide a mutation of any source-of-truth book.
- **Future price formation remains gated.** Out of scope until
  the v1.16 / v1.17 / v1.18 surface is operationally legible
  to a reviewer who has not read this codebase. Adding price
  formation on top of an opaque scenario layer would defeat
  the auditability goal of the v1.16 freeze.

The v1.18 chain stays template-only, append-only, label-only,
and stimulus-only forever. Future milestones may *cite* v1.18
templates / applications / shifts (plain-id cross-references,
additional rendering kinds), but they may **never** mutate the
v1.18.0 vocabulary, replace the deterministic rule-based
fallback with a runtime-active LLM mode without the audit
shape, or hard-code corporate / investor / bank judgment as
canonical truth on top of the scenario layer.
