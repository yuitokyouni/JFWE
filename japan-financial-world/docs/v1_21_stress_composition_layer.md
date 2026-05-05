# v1.21.0 Stress Composition Layer — Design Note

> **Status: docs-only.** v1.21.0 ships **no executable code, no
> new tests, no new ledger event types, no new behavior**. The
> living reference world's pinned digests (`quarterly_default`
> = `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`,
> `monthly_reference` = `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`,
> `scenario_monthly_reference_universe` test-fixture digest =
> `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`),
> per-period record counts, per-run windows, and pytest count
> (`4764 / 4764`) are **unchanged from v1.20.last**. v1.21.0 is
> the design pointer for the v1.21 sequence; subsequent
> milestones (v1.21.1 → v1.21.last) will land code under this
> design.

## Purpose

v1.20.last froze the **monthly scenario reference universe**:
12 monthly periods × 11 generic sectors × 11 representative
synthetic firm profiles × 4 investor archetypes × 3 bank
archetypes × 51 information arrivals × **one** scheduled
scenario application (`credit_tightening_driver` at
`month_04`). A reviewer can already export a deterministic
bundle and inspect the universe / sector / monthly scenario
surface in a `file://` browser session.

The next FWE realism step is **not** to add a second
scenario. v1.21 explicitly does **not** ship a "scenario-path
comparison toy" — running scenario A vs scenario B and
asking which one was "right" is exactly the kind of
forecast-shaped framing FWE refuses.

What v1.21 ships instead is a **stress composition layer**:

> A scenario is **not** a deterministic causal route.
> It is a **set of append-only stress stimuli** applied to
> context surfaces over time. The engine should record
> *which stresses are active*, *how overlapping stresses
> compose on a context surface*, and *which downstream
> records cite the composed field* — and then stop. It must
> never claim any of those stresses caused any specific
> outcome.

The layer answers four inspection questions:

1. **Which stress stimuli are active in this run?** —
   `StressProgramTemplate` + `StressStep` (the static plan).
2. **When was each stress fired?** —
   `StressFieldApplicationRecord` (the per-month receipt).
3. **What happens when stresses overlap on the same
   context surface?** — `StressInteractionRule` (the
   pairwise composition rule, label-only).
4. **What does the composed stress field look like at
   each (period, context surface)?** —
   `StressFieldReadout` (the aggregation surface).

## Sequence map

| Milestone     | Module / surface                                                                     | Adds                                                                                                                                                                                                                                                                                                                |
| ------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **v1.21.0**   | docs only (this document)                                                            | Stress composition design — six dataclass shapes (`StressProgramTemplate` / `StressStep` / `StressFieldApplicationRecord` / `StressInteractionRule` / `StressFieldReadout` / optional `StressFieldSummaryProjection`); closed-set composition / interaction / decay vocabularies; record-count budget; per-milestone roadmap; hard boundary. |
| v1.21.1       | `world/stress_composition.py`                                                        | `StressProgramTemplate` + `StressStep` + `StressFieldApplicationRecord` immutable frozen dataclasses + one append-only `StressCompositionBook`; closed-set frozensets; `FORBIDDEN_STRESS_FIELD_NAMES` frozenset (composes the v1.18.0 actor-decision tokens, the v1.20.0 real-issuer / licensed-taxonomy tokens, and the v1.21.0 forecast-shaped tokens). **Storage only** — no run profile, no interaction classifier, no readout, no CLI extension, no UI extension.                                                              |
| v1.21.2       | `world/stress_interactions.py`                                                       | `StressInteractionRule` + `StressInteractionBook` (append-only); pairwise classifier helper that maps (active stress steps × context surface × month) → `interaction_label` from the v1.21.0 closed set (`amplify` / `dampen` / `offset` / `coexist` / `unknown`). Storage + helper only — no numeric magnitude, no formula, no run profile.                                                                                                              |
| v1.21.3       | `world/stress_readout.py`                                                            | `StressFieldReadout` + `StressFieldReadoutBook` (append-only); aggregation helper that builds one readout per (period, context_surface) from the cited application + interaction records. Storage + helper only — no run profile.                                                                                                                                                              |
| v1.21.4       | `world/reference_living_world.py` (extended) — new `scenario_monthly_stress_composition` opt-in profile | Wires the v1.21.1–v1.21.3 layer into a new opt-in run profile **stacked on top of** v1.20.3's `scenario_monthly_reference_universe`. Reuses the v1.20.1 universe + v1.20.2 schedule + v1.18.2 `apply_scenario_driver` helper; adds 1+ stress programs and the per-period readout sweep. The default fixture pins **3** stress programs (e.g., one credit-tightening, one funding-window-closure, one information-gap), each with 1 step. The existing `quarterly_default` / `monthly_reference` / `scenario_monthly_reference_universe` digests stay byte-identical (v1.21 is opt-in).                                                                                                              |
| v1.21.5       | `examples/reference_world/export_run_bundle.py` (extended)                            | CLI export for the new profile — adds three new bundle sections (`stress_composition` / `stress_interactions` / `stress_field_readouts`) under `metadata`, mirroring the v1.20.4 shape.                                                                                                                                |
| v1.21.6       | `examples/ui/fwe_workbench_mockup.html` (extended)                                    | Adds a **Stress** tab (or extends the v1.20.5 Universe tab) with: per-month active-stress timeline; overlap clusters; affected-context-surface list; composition histogram; downstream-citation table.                                                                                                                |
| v1.21.last    | docs only                                                                            | Single-page reader-facing summary, freeze pin, release-readiness snapshot, cross-links.                                                                                                                                                                                                                              |

## Design constraints (binding)

- **Reuse existing `ScenarioDriverTemplate` ids.** Every
  `StressStep` cites a v1.18.1 `scenario_driver_template_id`
  via plain id. v1.21 does **not** introduce a parallel
  scenario-family taxonomy.
- **No new scenario-family vocabulary.** The
  `SCENARIO_FAMILY_LABELS` frozenset in
  `world/scenario_drivers.py` stays the source of truth.
  v1.21 introduces **composition / interaction / decay**
  vocabularies, never family vocabularies.
- **No price, no forecast, no expected return, no target
  price, no buy / sell, no order, no trade, no execution,
  no lending decision, no firm decision, no investor
  action, no bank approval, no real data, no Japan
  calibration, no LLM output.** v1.21 explicitly extends
  the v1.18.0 / v1.19.3 / v1.20.0
  `FORBIDDEN_*_FIELD_NAMES` frozensets with
  forecast-shaped composition tokens (e.g.,
  `stress_magnitude_in_basis_points`,
  `stress_probability_weight`,
  `expected_field_response`, `stress_forecast_path`,
  `stress_buy_signal`, `stress_sell_signal`).
- **Stress steps may overlap.** Two stress steps can
  schedule the same `(period, context_surface)`. Overlap
  handling is **explicit** (see §`StressInteractionRule`).
- **Interaction output is labels, not numbers.** The
  closed set is `{amplify, dampen, offset, coexist,
  unknown}`. No real shock magnitude, no numeric decay
  coefficient, no expected impact in basis points, no
  probability weight.
- **All records append-only.** Existing source-of-truth
  records are byte-identical pre / post the v1.21 sweep.
- **Reporting is read-only.** The aggregation helper walks
  the cited records once and emits readouts; it never
  mutates any input.
- **Cardinality bounded.** See §`Cardinality / record-count
  risk analysis` below — interaction is **pairwise** by
  design, the soft cap on stress programs per run is **5**,
  and no loop shape that scales as `O(P × I × F × stress)`
  or `O(P × stress × stress × stress × ...)` is allowed.

## Six dataclass shapes (sketch only — no implementation)

The shapes below are **interface sketches**, not
implementations. v1.21.1 / v1.21.2 / v1.21.3 will land the
actual `@dataclass(frozen=True)` definitions with closed-set
validation, `__post_init__` guards, and `to_dict` methods
mirroring the v1.18 / v1.20 patterns.

### 1. `StressProgramTemplate`

A *named bundle* of stress steps. The composition unit. A
program may be re-used across runs / fixtures.

```
StressProgramTemplate
    stress_program_template_id      str
    program_label                   str (closed-set: see §closed sets)
    program_purpose_label           str (closed-set: e.g.
                                          "twin_credit_funding_stress",
                                          "single_credit_tightening_stress",
                                          "information_gap_stress",
                                          "custom_synthetic", "unknown")
    horizon_label                   str (closed-set:
                                          "monthly_12_period",
                                          "quarterly_4_period",
                                          "custom_synthetic", "unknown")
    step_count                      int
    stress_step_ids                 tuple[str, ...]  # plain-id citations
    severity_label                  str (closed-set:
                                          "low" / "moderate" / "high" /
                                          "very_high" / "unknown")
    affected_actor_scope_label      str (mirrors v1.18.1
                                          AFFECTED_ACTOR_SCOPE_LABELS)
    reasoning_mode                  str (v1.18.0 audit shape;
                                          binding default
                                          "rule_based_fallback")
    reasoning_policy_id             str
    reasoning_slot                  str (binding default
                                          "future_llm_compatible")
    status                          str (closed-set)
    visibility                      str (closed-set)
    metadata                        Mapping[str, Any]
                                      # opaque; scanned for
                                      # FORBIDDEN_STRESS_FIELD_NAMES
```

### 2. `StressStep`

One stress step inside a program. Wraps a v1.18.1
`scenario_driver_template_id` with timing + scope + decay
labels. A stress step is the **plan**; the runtime
application is `StressFieldApplicationRecord`.

```
StressStep
    stress_step_id                  str
    stress_program_template_id      str  # plain-id, parent program
    scenario_driver_template_id     str  # plain-id, REUSE v1.18.1
    scheduled_period_indices        tuple[int, ...]  # 0-based, 0..11
    scheduled_month_labels          tuple[str, ...]  # mirrors v1.20.2
                                       # SCHEDULED_MONTH_LABELS
    step_severity_label             str (closed-set; see §closed sets)
    step_horizon_label              str (closed-set:
                                          "immediate" / "persistent" /
                                          "decaying" / "unknown")
    decay_label                     str (closed-set; see §closed sets)
    affected_sector_id_scope_label  str (closed-set:
                                          "universe_wide" /
                                          "sector_group_filtered" /
                                          "firm_profile_filtered" /
                                          "explicit_id_set" / "unknown")
    explicit_affected_sector_ids    tuple[str, ...]  # opt-in narrowing
                                                     # (plain-id citations)
    explicit_affected_firm_profile_ids
                                    tuple[str, ...]  # opt-in narrowing
    expected_context_surface_labels tuple[str, ...]  # mirrors v1.18.2
                                       # CONTEXT_SURFACE_LABELS
    expected_shift_direction_labels tuple[str, ...]  # mirrors v1.18.2
                                       # SHIFT_DIRECTION_LABELS
    status                          str
    visibility                      str
    metadata                        Mapping[str, Any]
```

### 3. `StressFieldApplicationRecord`

Append-only record emitted when a stress step is fired in a
month. The v1.21 analogue of the v1.18.2
`ScenarioDriverApplicationRecord`. Cites the v1.18.2
`ScenarioContextShiftRecord` ids it emitted via the
existing `apply_scenario_driver(...)` helper.

```
StressFieldApplicationRecord
    stress_field_application_id     str
    stress_step_id                  str  # plain-id
    stress_program_template_id      str  # plain-id
    scenario_driver_template_id     str  # plain-id, REUSE v1.18.1
    as_of_date                      str  # ISO YYYY-MM-DD
    application_status_label        str (closed-set; mirrors
                                          v1.18.2
                                          APPLICATION_STATUS_LABELS:
                                          "prepared" /
                                          "applied_as_field_shift" /
                                          "degraded_unresolved_refs" /
                                          "rejected" / "unknown")
    emitted_context_shift_ids       tuple[str, ...]  # cites v1.18.2
                                                     # ScenarioContextShiftRecord ids
    affected_sector_ids             tuple[str, ...]
    affected_firm_profile_ids       tuple[str, ...]
    source_information_arrival_ids  tuple[str, ...]  # cites v1.19.3
                                                     # InformationArrivalRecord ids
    reasoning_mode                  str (binding "rule_based_fallback")
    reasoning_policy_id             str
    reasoning_slot                  str (binding "future_llm_compatible")
    evidence_ref_ids                tuple[str, ...]
    unresolved_ref_count            int
    boundary_flags                  Mapping[str, bool]
                                      # default 8-flag set + new flags:
                                      #   no_actor_decision (binding True)
                                      #   no_field_value_claim (binding True)
                                      #   no_field_magnitude_claim (binding True)
    status                          str
    visibility                      str
    metadata                        Mapping[str, Any]
```

### 4. `StressInteractionRule`

Append-only record emitted when **two or more** stress
steps overlap on the same `(period, context_surface)` pair.
Maps the active stress-step ids and the surface to a
**label**, never a number.

```
StressInteractionRule
    stress_interaction_rule_id      str
    triggering_stress_step_ids      tuple[str, ...]  # plain-id
                                                     # (≥ 2; pairwise
                                                     # is the default;
                                                     # 3-way is opt-in
                                                     # gated)
    triggering_stress_field_application_ids
                                    tuple[str, ...]  # plain-id, the
                                                     # specific application
                                                     # records that
                                                     # collided
    shared_context_surface_label    str (closed-set; mirrors v1.18.2
                                          CONTEXT_SURFACE_LABELS)
    shared_month_label              str (mirrors v1.20.2
                                          SCHEDULED_MONTH_LABELS)
    interaction_label               str (closed-set:
                                          "amplify" / "dampen" /
                                          "offset" / "coexist" /
                                          "unknown")
    output_context_label            str (closed-set; mirrors v1.18.2
                                          SHIFT_DIRECTION_LABELS plus
                                          "mixed" / "neutral")
    classifier_rule_id              str  # plain-id of the
                                          # deterministic
                                          # classifier rule that
                                          # produced this label
    reasoning_mode                  str (binding "rule_based_fallback")
    reasoning_policy_id             str
    reasoning_slot                  str (binding "future_llm_compatible")
    evidence_ref_ids                tuple[str, ...]
    unresolved_ref_count            int
    boundary_flags                  Mapping[str, bool]
    status                          str
    visibility                      str
    metadata                        Mapping[str, Any]
```

The classifier (v1.21.2) is a **deterministic closed-set
table** that maps `(triggering_stress_step_ids ×
shared_context_surface_label)` to `interaction_label` +
`output_context_label`. It is **rule-based**, not a
formula, and never produces a numeric magnitude.

### 5. `StressFieldReadout`

Per-(period, context-surface) aggregation. The inspection
layer's view of the stress field.

```
StressFieldReadout
    stress_field_readout_id         str
    as_of_date                      str  # ISO YYYY-MM-DD
    period_index                    int  # 0-based, 0..11
    month_label                     str (mirrors v1.20.2
                                          SCHEDULED_MONTH_LABELS)
    context_surface_label           str (mirrors v1.18.2
                                          CONTEXT_SURFACE_LABELS)
    active_stress_step_ids          tuple[str, ...]  # plain-id
    active_stress_field_application_ids
                                    tuple[str, ...]  # plain-id
    active_stress_program_template_ids
                                    tuple[str, ...]  # plain-id
    composition_label               str (closed-set:
                                          "single_stress" /
                                          "overlapping_stresses" /
                                          "amplified" / "dampened" /
                                          "offset" / "coexisting" /
                                          "quiescent" / "unknown")
    dominant_shift_direction_label  str (closed-set; mirrors v1.18.2
                                          SHIFT_DIRECTION_LABELS plus
                                          "mixed" / "neutral")
    evidence_stress_interaction_rule_ids
                                    tuple[str, ...]  # plain-id
    evidence_information_arrival_ids
                                    tuple[str, ...]  # plain-id, v1.19.3
    affected_sector_id_count        int
    affected_firm_profile_id_count  int
    status                          str
    visibility                      str
    metadata                        Mapping[str, Any]
```

Per-period there is **at most one** readout per
`(period, context_surface)`. With ≤ 8 context surfaces and
12 periods, the readout count is bounded at **96 per run**.

### 6. `StressFieldSummaryProjection` (optional)

Run-wide summary projection for downstream consumers (the
v1.21.5 CLI bundle, the v1.21.6 UI). **Optional** because
consumers can derive the same view by walking the readouts.

```
StressFieldSummaryProjection
    stress_field_summary_projection_id  str
    run_id                              str
    active_stress_program_template_ids  tuple[str, ...]
    active_stress_step_ids              tuple[str, ...]
    per_month_readout_ids               Mapping[int, tuple[str, ...]]
                                          # period_index -> readout ids
    per_context_surface_readout_ids     Mapping[str, tuple[str, ...]]
                                          # surface_label -> readout ids
    composition_histogram               Mapping[str, int]
                                          # composition_label -> count
    interaction_histogram               Mapping[str, int]
                                          # interaction_label -> count
    downstream_citation_count           int  # how many v1.15.5 /
                                              # v1.16.2 / v1.14.5 records
                                              # cite a stress field
                                              # application
    status                              str
    visibility                          str
    metadata                            Mapping[str, Any]
```

The v1.21.4 orchestrator may emit this projection at the
end of a run; the v1.21.5 CLI may surface it under
`bundle.metadata.stress_field_summary`. It is **derived**,
not append-only — re-running the helper on the same input
produces a byte-identical projection.

## Closed sets (pinned at v1.21.0)

The v1.21 sequence introduces **only** the vocabularies
listed below. It does **not** introduce new
scenario-family or context-surface vocabularies — those
remain pinned by v1.18.1 / v1.18.2.

| Vocabulary                              | Closed set                                                                                                                                                                                                              |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `STRESS_PROGRAM_PURPOSE_LABELS`         | `single_credit_tightening_stress` / `single_funding_window_closure_stress` / `single_information_gap_stress` / `twin_credit_funding_stress` / `twin_credit_information_gap_stress` / `multi_stress_demonstration` / `custom_synthetic` / `unknown` |
| `STRESS_PROGRAM_HORIZON_LABELS`         | `monthly_12_period` / `quarterly_4_period` / `custom_synthetic` / `unknown`                                                                                                                                              |
| `STRESS_STEP_HORIZON_LABELS`            | `immediate` / `persistent` / `decaying` / `unknown`                                                                                                                                                                      |
| `STRESS_STEP_DECAY_LABELS`              | `none` / `decay_1month_label` / `decay_2month_label` / `decay_3month_label` / `persistent_through_horizon` / `unknown`                                                                                                  |
| `STRESS_STEP_AFFECTED_SCOPE_LABELS`     | `universe_wide` / `sector_group_filtered` / `firm_profile_filtered` / `explicit_id_set` / `unknown`                                                                                                                     |
| `STRESS_INTERACTION_LABELS`             | `amplify` / `dampen` / `offset` / `coexist` / `unknown`                                                                                                                                                                  |
| `STRESS_COMPOSITION_LABELS`             | `single_stress` / `overlapping_stresses` / `amplified` / `dampened` / `offset` / `coexisting` / `quiescent` / `unknown`                                                                                                  |
| `STRESS_OUTPUT_CONTEXT_LABELS`          | mirrors v1.18.2 `SHIFT_DIRECTION_LABELS` (`tighten` / `loosen` / `deteriorate` / `improve` / `increase_uncertainty` / `reduce_uncertainty` / `attention_amplify` / `information_gap` / `no_direct_shift` / `unknown`) **plus** `mixed` / `neutral` |
| `STRESS_STATUS_LABELS`                  | `prepared` / `active` / `applied_as_field_shift` / `degraded_unresolved_refs` / `rejected` / `inactive` / `unknown`                                                                                                     |
| `STRESS_VISIBILITY_LABELS`              | mirrors v1.18.1 `VISIBILITY_LABELS`                                                                                                                                                                                      |

Decay labels are **labels**, not coefficients. `decay_1month_label`
means "the stress is recorded as decaying over one month"; it
does **not** mean the magnitude halves over 30 days.

## `FORBIDDEN_STRESS_FIELD_NAMES` (binding)

The frozenset extends the v1.18.0 / v1.19.3 / v1.20.0
forbidden-field-name lists with **forecast-shaped composition
tokens**:

- v1.18.0 actor-decision tokens (carried forward verbatim):
  `firm_decision`, `investor_action`, `bank_approval`,
  `trading_decision`, `optimal_capital_structure`,
  `buy`, `sell`, `order`, `trade`, `execution`, `price`,
  `market_price`, `predicted_index`, `forecast_path`,
  `expected_return`, `target_price`, `recommendation`,
  `investment_advice`, `real_data_value`,
  `japan_calibration`, `llm_output`, `llm_prose`,
  `prompt_text`.
- v1.19.3 Japan-real-data tokens (carried forward):
  `real_indicator_value`, `cpi_value`, `gdp_value`,
  `policy_rate`, `real_release_date`.
- v1.20.0 real-issuer / licensed-taxonomy tokens (carried
  forward): `real_company_name`, `real_sector_weight`,
  `market_cap`, `leverage_ratio`, `revenue`, `ebitda`,
  `net_income`, `real_financial_value`, `gics`, `msci`,
  `sp_index`, `topix`, `nikkei`, `jpx`.
- **NEW at v1.21.0** (forecast-shaped composition):
  `stress_magnitude_in_basis_points`,
  `stress_magnitude_in_percent`,
  `stress_probability_weight`,
  `expected_field_response`,
  `expected_stress_path`,
  `stress_forecast_path`,
  `stress_buy_signal`,
  `stress_sell_signal`,
  `stress_target_price`,
  `stress_expected_return`,
  `stress_outcome_label`.

The frozenset is scanned recursively across every dataclass
field name, every payload key, every metadata key, and the
module text via the regression-test pattern carried from
v1.20.x.

## Cardinality / record-count risk analysis

The danger shape v1.21 must guard against:

```
O(P × I × F × stress_step)         FORBIDDEN
O(P × stress_step × stress_step × stress_step × ...)
                                    FORBIDDEN (factorial)
O(P × stress_step × scenario_family × surface × actor_id)
                                    FORBIDDEN
O(P × day × stress_step)            FORBIDDEN (daily inner loop)
```

**Allowed** loop shapes (binding):

- `O(stress_step_count)` for stress program / step storage
  (constant per run; soft cap 5 programs × 3 steps each =
  15 steps).
- `O(P × stress_step_count_active_in_period)` for
  application records (≤ 12 × 5 = 60).
- `O(P × pairwise_active_stress × surface)` for interaction
  rules — **pairwise** only (3-way is opt-in gated by the
  v1.21.2 `allow_three_way_interaction` flag, default
  `False`). Tight bound: ≤ 12 × `min(C(active, 2), 10)` × 8
  surfaces = ≤ ~960 in the worst case, but every
  realistic fixture is far smaller (the v1.21.4 default
  fixture pins ≤ 50).
- `O(P × surface_count)` for readouts (≤ 12 × 8 = **96**).
- `O(stress_program_count)` for the optional summary
  projection (≤ 5).

**Soft target per run**:

- 3 stress programs × 1 step each (the v1.21.4 default
  fixture) = 3 stress steps,
- ≤ 3 application records (one per scheduled month per
  active step),
- ≤ ~10 interaction rules (most months have 0 or 1 active
  stress on any given surface; only the deliberate-overlap
  test fixture exercises ≥ 2),
- ≤ 96 readouts,
- ≤ 1 optional summary projection,
- ≈ **~110 v1.21 records** added to a v1.20.3-style
  `scenario_monthly_reference_universe` run.

**Hard guardrail**: `manifest.record_count` for any v1.21
opt-in profile must stay **≤ 4000** (the v1.20.0 budget,
unchanged). The v1.20.4 CLI fixture currently sits at
**3241**; v1.21 is allotted up to ~700 additional records,
which the soft target stays well below.

The v1.20.0 forbidden loop shapes (`O(P × I × F × scenario)`,
`O(P × I × F × venue)`, `O(P × F × order)`, `O(P × day × ...)`)
remain forbidden at v1.21.

## Hard boundary statement

v1.21 increases realism by adding **stress composition
auditability**. It does **not**:

- **Claim causality.** The readout is an *audit* of which
  stresses were active and how they composed; never a
  claim that "stress X caused outcome Y".
- **Compute magnitudes.** `interaction_label` and
  `output_context_label` are closed-set strings; no
  numeric formula composes them.
- **Decide actor behavior.** Stress steps are stimuli;
  downstream mechanisms (v1.12 attention, v1.15.5 market
  intent, v1.14.5 financing path) may *cite* the
  application records as evidence, but never as a binding
  decision.
- **Mutate any source-of-truth book.** PriceBook,
  ContractBook, ConstraintBook, OwnershipBook,
  InstitutionsBook, MarketEnvironmentBook,
  FirmFinancialStateBook, InterbankLiquidityStateBook,
  IndustryConditionBook — all byte-identical pre / post
  the v1.21 sweep.
- **Add real data.** No real CPI / GDP / policy-rate
  values, no real release dates, no real institutional
  identifiers, no real sector-index membership, no real
  financial-statement values.
- **Add price formation, trading, orders, execution,
  clearing, settlement, financing execution, lending
  decisions, investment advice, or LLM execution.**
- **Unlock daily-frequency economic simulation.**

Re-pinned at v1.21:

- `reasoning_mode = "rule_based_fallback"` is binding on
  every emitted record. A future LLM-mode reasoning policy
  may replace the rule-based classifier under the same
  v1.18.0 audit shape (`reasoning_policy_id` /
  `reasoning_slot` / `evidence_ref_ids` /
  `unresolved_ref_count` / `boundary_flags`) without
  changing the audit surface.
- `reasoning_slot = "future_llm_compatible"` reserves room
  for the same future replacement.
- The static workbench remains read-only — `textContent`
  only, no `innerHTML` for user-loaded JSON, no `eval`,
  no `fetch` / XHR, no backend, no file-system write, no
  browser-to-Python execution.

## Suggested tests (v1.21.1 → v1.21.6)

These tests will land alongside the code milestones; v1.21.0
ships none.

### v1.21.1 storage tests (`tests/test_stress_composition.py`)

- Closed-set vocabulary tests (every label exhaustively
  enumerated; no implicit additions).
- `FORBIDDEN_STRESS_FIELD_NAMES` boundary tests (every
  forbidden token rejected as a dataclass field name, a
  `to_dict` key, a payload key, and a metadata key —
  scanned recursively at any depth).
- Per-dataclass field validation:
  - `StressProgramTemplate`: `step_count` rejects `bool`,
    negatives; `stress_step_ids` rejects empty strings;
    closed-set rejection paths for every label field.
  - `StressStep`: `scheduled_period_indices` rejects
    `bool`, negatives, `> 11` (mirrors v1.20.2);
    `decay_label` rejects unknown labels; closed-set
    rejection per label field.
  - `StressFieldApplicationRecord`: `unresolved_ref_count`
    rejects `bool` / negatives; closed-set rejection per
    label field.
- Append-only book invariants: duplicate id rejection (no
  extra ledger record), unknown id `KeyError`, every
  `list_*` filter method, `snapshot()` determinism, ledger
  one-record-per-add.
- Plain-id citations accepted **without** resolution at
  the storage layer (v0/v1 rule).
- Trip-wires: empty book does **not** move the
  `quarterly_default` / `monthly_reference` /
  `scenario_monthly_reference_universe` digests (binding
  pin — v1.21.1 is opt-in storage).
- No actor-decision event types emitted by the storage
  book.
- No `PriceBook` mutation.
- Module text + test text scans: `_strip_module_docstring`
  + `_strip_forbidden_literal` discipline mirrors
  v1.20.x; jurisdiction-neutral identifier scan +
  licensed-taxonomy scan + v1.21.0 forecast-shaped-token
  scan.

### v1.21.2 interaction-classifier tests (`tests/test_stress_interactions.py`)

- Closed-set `STRESS_INTERACTION_LABELS` exhaustive.
- The pairwise classifier is **deterministic** —
  `(stress_step_a_id, stress_step_b_id, surface)` →
  always the same `interaction_label`.
- Two stresses pushing the same direction on the same
  surface → `amplify`.
- Two stresses pushing opposite directions on the same
  surface → `offset` or `dampen` per the v1.21.2 rule
  table (binding closed set).
- Two stresses on different surfaces → `coexist`.
- Three-way interactions are **rejected** unless the
  caller explicitly passes `allow_three_way=True`; even
  then the classifier reports `unknown` for any 3-tuple
  not in the v1.21.2 explicit 3-way rule table.
- The classifier never returns a numeric magnitude.
- The classifier never reads / writes `PriceBook` or any
  other source-of-truth book.

### v1.21.3 readout-aggregation tests (`tests/test_stress_field_readout.py`)

- The aggregation helper produces **at most one** readout
  per `(period, context_surface)`.
- `composition_label` is derived deterministically from
  the active stress steps + interactions.
- `quiescent` readouts are emitted for surfaces with **no**
  active stress (the readout count is therefore stable
  across runs even when stress activity differs).
- The helper is read-only against the v1.21.1 / v1.21.2
  books and the kernel ledger.
- `dominant_shift_direction_label` is derived from the
  v1.18.2 shift directions on the cited application
  records.
- Re-running the helper on the same input produces
  byte-identical readouts.

### v1.21.4 run-profile tests (`tests/test_living_reference_world.py` extended + `tests/test_living_reference_world_performance_boundary.py` extended)

- The new `scenario_monthly_stress_composition` profile
  is recognized; the three pre-existing profiles
  (`quarterly_default`, `monthly_reference`,
  `scenario_monthly_reference_universe`) keep their
  pinned digests.
- Default fixture: 3 stress programs × 1 step each = 3
  stress steps; pin the count.
- ≤ 3 application records emitted per run; pin the bound.
- ≤ ~50 interaction rules; pin the bound.
- ≤ 96 readouts; pin the bound.
- Total `created_record_count` ≤ 4000 (v1.20.0 hard
  guardrail); pin the bound.
- Forbidden record types absent: no `ORDER_SUBMITTED` /
  `PRICE_UPDATED` / `CONTRACT_*` / `OWNERSHIP_TRANSFERRED`.
- Append-only invariant: pre-existing `MarketEnvironmentBook`
  / `FirmFinancialStateBook` / `InterbankLiquidityStateBook`
  / `IndustryConditionBook` / `PriceBook` snapshots
  byte-identical pre / post run.
- New profile's `living_world_digest` is pinned and
  deterministic.

### v1.21.5 CLI tests (`tests/test_run_export_cli.py` extended)

- The CLI accepts
  `--profile scenario_monthly_stress_composition` and
  exits non-zero on any other (scenario, profile)
  combination not in the v1.21.5
  `SCENARIO_STRESS_COMPOSITION_SUPPORTED_SCENARIOS`
  closed set.
- Same args → byte-identical JSON.
- `bundle.metadata.stress_composition` carries the
  program / step ids; `bundle.metadata.stress_interactions`
  carries the interaction-rule ids; `bundle.metadata.stress_field_readouts`
  carries the readout ids.
- `manifest.stress_program_count` /
  `stress_step_count` / `stress_field_application_count` /
  `stress_interaction_rule_count` / `stress_field_readout_count`
  fields present and correct.
- No real indicator value, no licensed-taxonomy token, no
  forecast-shaped-token in the rendered bundle JSON
  (extends the v1.20.4 word-boundary scans with the
  v1.21.0 forecast-shaped-token list).
- Pinned bundle digest.
- `quarterly_default` / `monthly_reference` /
  `scenario_monthly_reference_universe` `living_world_digest`s
  unchanged.

### v1.21.6 UI tests (manual smoke)

- Open `examples/ui/fwe_workbench_mockup.html` under
  `file://`; click **Load local bundle**; pick the
  v1.21.5 JSON; switch to the new **Stress** tab (or the
  extended v1.20.5 Universe tab); confirm:
  - active-stress timeline renders all 12 months,
  - overlap clusters render the `interaction_label` per
    cluster,
  - composition histogram renders per
    `STRESS_COMPOSITION_LABELS`,
  - downstream-citation table renders the v1.15.5 /
    v1.16.2 / v1.14.5 records that cite the v1.21
    applications,
  - boundary footer reads
    *synthetic / append-only / no causality claim / no
    price / no recommendation / no real data / no Japan
    calibration / no LLM execution*.
- Tab ↔ sheet bijection holds (12 ↔ 12 if a new tab is
  added; otherwise 11 ↔ 11 if the Universe tab is
  extended).

## UI readout requirements (v1.21.6, sketch only)

The v1.21.6 milestone will extend the v1.20.5 static
workbench. The minimum surfaces:

1. **Active-stress timeline** — one row per month, one
   column per active `stress_step_id`. Cells render the
   stress step's `step_severity_label` via the same
   five-rung CSS heatmap classes (`sens-low` /
   `sens-moderate` / `sens-high` / `sens-very-high` /
   `sens-unknown`); cell text echoes the underlying label
   verbatim.
2. **Overlap clusters** — for each `(period, surface)`
   with ≥ 2 active stresses, render a card showing the
   triggering `stress_step_ids`, the
   `interaction_label`, and the resulting
   `output_context_label`. Wrap long ids
   (`word-break: break-word`).
3. **Affected context surfaces** — a per-month list of
   `context_surface_label`s touched by any active stress.
   Render as label chips, never as numeric weights.
4. **Composition histogram** — a bar chart (or compact
   horizontal stacked bar) over
   `STRESS_COMPOSITION_LABELS`. The bar height is the
   readout count per label across the 12 months.
5. **Downstream citations** — a table listing the
   v1.15.5 / v1.16.2 / v1.14.5 record types whose
   `evidence_*_ids` cite at least one
   `stress_field_application_id`. Counts only — no
   numeric pressure / intent values.
6. **Boundary footer** — `synthetic / append-only / no
   causality claim / no price formation / no
   recommendation / no real data / no Japan calibration /
   no LLM execution / no browser-to-Python execution`.

Required wording disciplines (binding):

- The UI must **never** render a phrase like "stress X
  caused outcome Y", "stress X has impact Z basis points",
  "stress X is more likely than stress Y", "stress X
  predicts …", or any equivalent. Use neutral phrasing —
  *"stress X is active in month M on surface S"*,
  *"stresses X and Y overlap on surface S; interaction =
  amplify"*, *"N records cite stress X"*.
- The UI must **never** render a numeric magnitude on a
  stress step or an interaction. Counts, label
  histograms, and citation tables only.
- The UI must **never** suggest a buy / sell / hold /
  allocation / rebalance action.

## Naming boundary (binding, carried forward)

- No real companies; no real sector weights; no real
  financial values; no real indicator values; no real
  release dates; no real institutional identifiers.
- Sector labels carry the `_like` suffix; firm ids follow
  the synthetic `firm:reference_<sector>_a` pattern; no
  public-FWE module text or test depends on bare `GICS`,
  `MSCI`, `S&P`, `FactSet`, `Bloomberg`, `Refinitiv`,
  `TOPIX`, `Nikkei`, or `JPX` tokens.
- Stress program and stress step ids follow the synthetic
  pattern `stress_program:<purpose_label>:<run_id>` and
  `stress_step:<program_id>:<step_index>` respectively.

## Read-in order (for a v1.21 reviewer)

1. [`v1_20_monthly_scenario_reference_universe_summary.md`](v1_20_monthly_scenario_reference_universe_summary.md)
   for the v1.20 frozen surface.
2. This document (the v1.21.0 design).
3. `world_model.md` §129 (v1.20) → §130 (v1.21, future)
   for the cross-position in the FWE module map.
4. The v1.21.last single-page summary (will be added at
   freeze time, mirroring
   `v1_20_monthly_scenario_reference_universe_summary.md`).

## Forward pointer

v1.21.1 will land
[`world/stress_composition.py`](../world/stress_composition.py)
(storage only). v1.21.2 will land the pairwise interaction
classifier. v1.21.3 will land the readout aggregation. v1.21.4
will wire the new opt-in profile
`scenario_monthly_stress_composition` into the v1.20.3
orchestrator. v1.21.5 will extend the v1.20.4 CLI exporter.
v1.21.6 will extend the v1.20.5 static workbench. v1.21.last
will freeze the v1.21 sequence (docs-only).

The `quarterly_default` / `monthly_reference` /
`scenario_monthly_reference_universe` digests must remain
**byte-identical** to v1.20.last across the entire v1.21
sequence.
