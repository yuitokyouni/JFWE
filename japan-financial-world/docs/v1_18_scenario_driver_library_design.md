# v1.18.0 Scenario Driver Library — Design Note

> **Status: docs-only.** v1.18.0 ships **no executable code, no
> new tests, no new ledger event types, no new behavior**. The
> living reference world's `living_world_digest`, per-period
> record count (`108 / 110`), per-run window (`[432, 480]`),
> default 4-period sweep total (`460 records`), and pytest count
> (`4165 / 4165`) are **unchanged from v1.17.last**. v1.18.0 is
> the design pointer for the v1.18 sequence; subsequent
> milestones (v1.18.1 → v1.18.last) will land code under this
> design.

## Purpose

v1.16.last froze the closed deterministic endogenous-market-
intent feedback loop (attention → market intent → aggregated
interest → indicative pressure → financing review → next-period
attention). v1.17.last froze the inspection layer (display
timelines, regime comparison, causal annotations, static
analyst workbench). The system is now **inspectable**.

The v1.18 sequence adds **synthetic scenario-driver templates**
that feed existing FWE evidence / context surfaces. A scenario
driver names a synthetic exogenous condition — `rate_repricing`,
`liquidity_stress`, `customer_churn`, `index_inclusion_exclusion`,
etc. — and projects it onto pre-existing context records (e.g.
`MarketEnvironmentStateRecord`, `IndustryConditionRecord`,
`ExposureRecord`, `MarketConditionRecord`) via deterministic
label / metadata changes. The downstream actor responses still
flow through the existing v1.12 / v1.14 / v1.15 / v1.16
mechanisms; the scenario driver does not decide what an actor
does. The v1.17 inspection layer then renders the resulting
behaviour.

A scenario driver is therefore a **context-shifting template**,
not a behaviour rule. It is the **stimulus**, never the
**response**.

This is **not** a market simulator, **not** a forecast layer,
**not** a trading dashboard, **not** a recommendation surface,
**not** a real-data view, **not** a Japan calibration, **not**
an LLM execution path. The v1.16 / v1.17 hard boundary applies
bit-for-bit at every v1.18 milestone.

## Design constraint pinned at v1.18.0

The user pinned the binding intent for v1.18 explicitly:
**do not overfit corporate / investor / bank judgment**. Future
versions may introduce LLM-based reasoning over actor context
frames, evidence refs, scenario drivers, and ledger history.
Therefore v1.18 must keep decision criteria **modular and
replaceable**.

This translates to five concrete design rules pinned at v1.18.0
and enforced for every v1.18.x milestone:

1. **Scenario drivers shift evidence / context only.** They
   never write to a record whose semantics is "an actor decided
   X". The downstream actor response is always mediated through
   an existing mechanism (v1.12.4 investor intent, v1.12.5
   valuation lite, v1.12.6 watch-label classifier, v1.14.5
   financing-path helper, v1.16.1 market-intent classifier,
   v1.16.3 attention focus widening) or, in the future, a
   `ReasoningPolicySlot`.
2. **All v1.18 classifier / mapping rules are deterministic,
   minimal, and explicitly labelled `reasoning_mode =
   "rule_based_fallback"`.** They are *fallbacks* — replaceable
   by a future audited reasoning policy. They are not canonical
   business judgment.
3. **Six concerns are kept structurally separate**:
   - evidence collection
   - driver classification (`DriverImpactLabel` /
     `EvidenceConditionLabel`)
   - actor context frame (`ActorReasoningInputFrame`, the
     v1.12.3 `EvidenceResolver` shape extended)
   - reasoning policy (`ReasoningPolicySlot`)
   - output label
   - audit metadata
4. **No LLM execution in v1.18.** The "LLM-compatible" suffix
   on slot names is a *future-affordance*, not a runtime
   capability. v1.18 ships only the rule-based fallback.
5. **Naming discipline.** Use the safe names below; avoid the
   forbidden ones, which read as canonical business judgment:

| Safe                              | Forbidden                          |
| --------------------------------- | ---------------------------------- |
| `ScenarioDriverTemplate`          | `FirmDecisionRule`                 |
| `ActorReasoningInputFrame`        | `InvestorActionRule`               |
| `ReasoningPolicySlot`             | `BankApprovalLogic`                |
| `DriverImpactLabel`               | `TradingDecisionModel`             |
| `EvidenceConditionLabel`          | `OptimalCapitalStructureRule`      |
| `InspectionAnnotation`            | (any `*Decision*Rule` / `*Optimal*Logic` form) |

## Two-line success condition

> A reviewer who has not read this codebase can pick a synthetic
> scenario driver from the v1.18 library, project it onto the
> default v1.16 fixture, and explain — by following plain-id
> citations from the v1.17 inspection layer — what evidence
> shifted, which existing mechanism processed the shift, what
> label changed, and what audit metadata records the chain.
> No actor decision is asserted by the scenario driver itself;
> every downstream label is produced by an existing mechanism
> or by a future `ReasoningPolicySlot`. The integration-test
> `living_world_digest` for the **default** fixture is unchanged
> at `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`;
> scenario-driven runs produce *different* digests by design,
> but the default sweep without any scenario applied stays
> byte-identical.

If a reviewer concludes that a scenario template "decides what
the firm should do" or "tells the investor to buy / sell", v1.18
has failed — the template is, by construction, only allowed to
shift evidence labels, not to write a decision.

## 1. Preferred flow (binding)

```
ScenarioDriverTemplate
   │  cited via plain-id citations — never mutates an existing
   │  context record
   ▼
EvidenceCondition / ContextShift
   │  a NEW append-only record (or a new metadata-bearing
   │  annotation alongside an existing record) that *cites* the
   │  pre-existing context record (env / industry / exposure /
   │  firm-state / market-condition) — the cited record itself
   │  is byte-identical pre / post application. The shift carries
   │  closed-set labels + the v1.18.0 audit-metadata block and is
   │  read by ActorReasoningInputFrame downstream.
   ▼
ActorReasoningInputFrame
   │  the v1.12.3 EvidenceResolver shape, extended with the
   │  scenario citation slot. Read-only against the kernel.
   ▼
existing mechanism  ── OR ──  ReasoningPolicySlot (future)
   │  v1.12.4 investor intent / v1.12.6 watch-label classifier /
   │  v1.14.5 financing-path helper / v1.16.1 market-intent
   │  classifier / v1.16.3 attention widening — every one of
   │  them deterministic and replaceable.
   ▼
output label                  (closed-set, audit-grade)
   │
   ▼
audit metadata                (reasoning_mode, reasoning_policy_id,
                                reasoning_slot, evidence_ref_ids,
                                unresolved_ref_count, boundary_flags)
   │
   ▼
v1.17 timeline / causal annotation
```

## 2. Forbidden flow (binding)

```
ScenarioDriverTemplate
   │
   ▼  ❌ never
"firm:reference_manufacturer_a decides to issue a bond"
"investor:reference_pension_a reduces position in firm X"
"bank:reference_commercial_a restricts credit to firm Y"
```

A scenario template **never** carries a sentence of the form
"actor decides X". The closest a template gets to actor
behaviour is a `DriverImpactLabel` ∈ a closed-set vocabulary
that names the *category* of impact a downstream mechanism may
detect — never the response itself.

## 3. Closed-set scenario driver families (v1.18.0 pin)

20 family labels, 9 group labels. Both are closed-set frozensets
that v1.18.1 will pin in code. v1.18+ may extend them via a
single coordinated change; the closed-set discipline is
binding.

### 3.1 `scenario_family_label`

| Family                                  | Group                              | One-line synthetic semantics                                                                       |
| --------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------- |
| `rate_repricing_driver`                 | `macro_rates`                      | Synthetic rising-rate context shifts on `MarketEnvironmentStateRecord.rate_environment`.           |
| `credit_tightening_driver`              | `credit_liquidity`                 | Synthetic spread-environment shift to `tightening` / `stressed` on `credit_regime`.                |
| `funding_window_closure_driver`         | `credit_liquidity`                 | Synthetic primary-market access narrowing on `funding_regime`.                                     |
| `liquidity_stress_driver`               | `credit_liquidity`                 | Synthetic interbank / market-liquidity tightening on `liquidity_regime`.                           |
| `risk_off_driver`                       | `credit_liquidity`                 | Synthetic risk-appetite swing to `risk_off` on `risk_appetite_regime`.                             |
| `sector_demand_deterioration_driver`    | `demand_earnings`                  | Synthetic industry-condition shift via `IndustryConditionRecord`.                                  |
| `market_access_reopening_driver`        | `capital_structure_refinancing`    | Synthetic relief — `funding_regime` widens; financing-path coherence relaxes.                      |
| `refinancing_wall_driver`               | `capital_structure_refinancing`    | Synthetic refinancing-window narrowing on `refinancing_window`.                                    |
| `input_cost_pressure_driver`            | `cost_supply`                      | Synthetic cost-side pressure via firm-pressure / industry-condition surfaces.                      |
| `information_gap_driver`                | `information_attention`            | Synthetic evidence-deficient situation; v1.16.3 `information_gap` focus + v1.16.1 priority-1 path. |
| `regulatory_risk_driver`                | `regulation_legal`                 | Synthetic compliance / regulatory observation; surfaces as escalation-candidate evidence only.     |
| `litigation_risk_driver`                | `regulation_legal`                 | Synthetic litigation-event observation; surfaces as escalation-candidate evidence only.            |
| `supply_constraint_driver`              | `cost_supply`                      | Synthetic supply-side constraint via industry-condition + firm-pressure surfaces.                  |
| `customer_churn_driver`                 | `demand_earnings`                  | Synthetic customer-base deterioration; surfaces via firm-pressure / industry-condition.            |
| `technology_substitution_driver`        | `technology_competition`           | Synthetic technology / substitute observation; surfaces via industry-condition.                    |
| `policy_subsidy_driver`                 | `regulation_legal`                 | Synthetic policy-action observation (positive or negative).                                         |
| `thematic_attention_driver`             | `information_attention`            | Synthetic theme / narrative observation; surfaces via attention focus only.                         |
| `short_squeeze_attention_driver`        | `ownership_market_structure`       | Synthetic ownership-distribution attention shift.                                                   |
| `index_inclusion_exclusion_driver`      | `ownership_market_structure`       | Synthetic index-membership change; surfaces via attention + market-interest only.                   |
| `capital_policy_uncertainty_driver`     | `capital_structure_refinancing`    | Synthetic firm-level capital-policy uncertainty; surfaces via firm-state pressure / dialogue refs. |
| `unknown`                                | `unknown`                           | The catch-all for unrecognised templates.                                                           |

### 3.2 `driver_group_label`

| Group                              | Family members                                                                                                        |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `macro_rates`                      | `rate_repricing_driver`                                                                                                |
| `credit_liquidity`                 | `credit_tightening_driver` · `funding_window_closure_driver` · `liquidity_stress_driver` · `risk_off_driver`            |
| `demand_earnings`                  | `sector_demand_deterioration_driver` · `customer_churn_driver`                                                         |
| `cost_supply`                      | `input_cost_pressure_driver` · `supply_constraint_driver`                                                              |
| `regulation_legal`                 | `regulatory_risk_driver` · `litigation_risk_driver` · `policy_subsidy_driver`                                          |
| `ownership_market_structure`       | `short_squeeze_attention_driver` · `index_inclusion_exclusion_driver`                                                  |
| `technology_competition`           | `technology_substitution_driver`                                                                                       |
| `capital_structure_refinancing`    | `market_access_reopening_driver` · `refinancing_wall_driver` · `capital_policy_uncertainty_driver`                     |
| `information_attention`            | `information_gap_driver` · `thematic_attention_driver`                                                                  |
| `unknown`                          | (catch-all)                                                                                                            |

### 3.3 Auxiliary closed-set vocabularies

`severity_label`: `low` · `medium` · `high` · `stress` · `unknown`.

`affected_actor_scope_label`: `market_wide` · `all_actors` · `firms_only` · `investors_only` · `banks_only` · `selected_firms` · `selected_investors` · `selected_banks` · `selected_securities` · `unknown`.

`event_date_policy_label`: `quarter_start` · `quarter_end` · `nearest_reporting_date` · `explicit_date` · `display_only_date` · `unknown`.

`expected_annotation_type_label` (must lie in v1.17.1 `ANNOTATION_TYPE_LABELS`): `market_environment_change` · `attention_shift` · `market_pressure_change` · `financing_constraint` · `causal_checkpoint` · `synthetic_event` · `unknown`.

`affected_context_surface_labels` (small open-ended tuple, but every entry must lie in a closed set the v1.18.1 storage module pins): `market_environment_state` · `industry_condition` · `market_condition` · `capital_market_readout` · `firm_financial_state` · `attention_state` · `actor_attention_focus` · `dialogue_candidate` · `escalation_candidate` · `valuation` · `investor_intent` · `unknown`.

`affected_evidence_bucket_labels` (must lie in v1.12.3 `EvidenceResolver` bucket vocabulary or its v1.13.6 extension): `market_environment_state` · `firm_state` · `industry_condition` · `market_condition` · `capital_market_readout` · `interbank_liquidity_state` · `dialogue` · `escalation_candidate` · `valuation` · `investor_intent` · `unknown`.

## 4. `ScenarioDriverTemplate` — data model

Immutable frozen dataclass; v1.18.1 will land it in code under
`world/scenario_drivers.py`. Field set pinned at v1.18.0:

```
@dataclass(frozen=True)
class ScenarioDriverTemplate:
    scenario_driver_template_id: str            # plain id, jurisdiction-neutral
    scenario_family_label:        str            # closed-set
    driver_group_label:           str            # closed-set
    driver_label:                 str            # short human-readable
    event_date_policy_label:      str            # closed-set
    severity_label:               str            # closed-set
    affected_actor_scope_label:   str            # closed-set
    affected_context_surface_labels:  tuple[str, ...]  # closed-set entries
    affected_evidence_bucket_labels:  tuple[str, ...]  # closed-set entries
    expected_annotation_type_label:   str         # closed-set ∈ ANNOTATION_TYPE_LABELS
    reasoning_mode:               str            # default "rule_based_fallback"
    reasoning_policy_id:          str            # plain id (e.g. "v1.18.2:rule_based_fallback")
    reasoning_slot:               str            # default "future_llm_compatible"
    status:                       str            # closed-set
    visibility:                   str            # closed-set
    metadata:                     Mapping[str, Any]   # synthetic, no real data
```

The dataclass:

- has no `confidence` field; templates are not predictions.
- carries no `numeric magnitude` field; templates are
  *category* shifts, not magnitudes. The v1.18.2 helper may add
  bounded ordinal magnitudes via `metadata` (synthetic, never
  prices / rates / spreads).
- carries no `actor decision` field; templates do not decide.
- is **runtime-book-free** at construction — the v1.18.1
  storage module imports no source-of-truth book; the v1.18.2
  application helper takes the kernel as an argument and reads
  only via `get_*` / `list_*`.

## 5. `ActorReasoningInputFrame` and `ReasoningPolicySlot`

These two surfaces are pinned at v1.18.0 as **future-affordance
shapes**. They are not implemented at v1.18.0; v1.18.2 lands a
minimal rule-based fallback, and v1.18.last freezes the layer
without adding LLM execution.

### 5.1 `ActorReasoningInputFrame`

A read-only bundle of evidence ids that an existing mechanism or
a future `ReasoningPolicySlot` consumes. Built on top of the
v1.12.3 `EvidenceResolver.ActorContextFrame`:

```
@dataclass(frozen=True)
class ActorReasoningInputFrame:
    actor_id:                str
    actor_type:              str            # closed-set ("investor"|"bank"|"firm")
    as_of_date:              str
    base_evidence_frame:     "ActorContextFrame"   # v1.12.3 frame, read-only
    scenario_driver_ids:     tuple[str, ...]       # plain-id citations
    driver_impact_labels:    tuple[str, ...]       # closed-set DriverImpactLabel
    evidence_condition_labels: tuple[str, ...]     # closed-set EvidenceConditionLabel
    unresolved_ref_count:    int                   # ≥ 0
    boundary_flags:          Mapping[str, bool]    # e.g. {"requires_audit": True}
    metadata:                Mapping[str, Any]
```

### 5.2 `ReasoningPolicySlot`

A typed slot a downstream caller passes the
`ActorReasoningInputFrame` to. v1.18.2 lands a **rule-based
fallback** policy only:

```
@dataclass(frozen=True)
class ReasoningPolicySlot:
    reasoning_policy_id:    str            # plain id
    reasoning_mode:         str            # "rule_based_fallback" only at v1.18.2
    reasoning_slot:         str            # "future_llm_compatible"
    description:            str            # short, jurisdiction-neutral
    metadata:               Mapping[str, Any]
```

The slot does **not** execute any LLM at v1.18 — `reasoning_mode`
is binding to `rule_based_fallback`. The `future_llm_compatible`
slot tag is an architectural commitment, not a runtime
capability.

### 5.3 Audit metadata recorded on every emitted record

Every record produced under v1.18.2 application carries:

| Field                  | Value at v1.18.2                                                                                    |
| ---------------------- | --------------------------------------------------------------------------------------------------- |
| `reasoning_mode`       | `"rule_based_fallback"` (binding)                                                                    |
| `reasoning_policy_id`  | e.g. `"v1.18.2:scenario_application:rule_based_fallback"`                                              |
| `reasoning_slot`       | `"future_llm_compatible"`                                                                            |
| `evidence_ref_ids`     | tuple of plain-id citations to the records the policy read                                            |
| `unresolved_ref_count` | `int ≥ 0`                                                                                             |
| `boundary_flags`       | mapping naming each binding-boundary check the policy ran (e.g. `{"no_price_formation": True, "no_actor_decision": True}`) |

A future LLM-mode policy must populate the same metadata
fields; the audit shape is forward-compatible.

## 6. Design rules (binding for v1.18.x)

1. Scenario drivers do **not** decide actor behaviour.
2. Scenario drivers do **not** create forecasts.
3. Scenario drivers do **not** create prices.
4. Scenario drivers do **not** create trades / orders /
   matches / executions / clearings / settlements / quotes /
   bid / ask.
5. Scenario drivers do **not** create financing execution / loan
   approval / bond or equity issuance / underwriting /
   syndication / pricing / interest rates / spreads / coupons
   / fees / offering prices.
6. Scenario drivers only **prepare synthetic evidence /
   context inputs** for existing mechanisms or future
   `ReasoningPolicySlot`. Application **emits new evidence /
   context records that cite the scenario driver via plain-id
   citations**; it **never mutates a pre-existing context
   record**. Every cited record is byte-identical pre / post
   application — pinned by a v1.18.2 trip-wire test.
7. Scenario application must be **deterministic** and
   **replay-stable** — same `(template_id, kernel state,
   as_of_date)` inputs → byte-identical record emissions.
8. Scenario templates must be **jurisdiction-neutral** in public
   FWE. No real exchange / regulator / issuer / venue / index
   identifier in any v1.18 module, fixture, test, or rendered
   view. Every numeric value is a synthetic ordinal in
   `[0.0, 1.0]` or a closed-set label.
9. Any future LLM reasoning must be **auditable**:
   - input evidence ids
   - prompt / policy id
   - output label
   - confidence / status
   - rejected / unknown cases
   - **no hidden mutation of any source-of-truth book**.
10. Public v1.x boundary remains: no investment advice, no
    financing decision, no trading, no price formation, no
    real data, no Japan calibration, no LLM execution.

## 7. Per-milestone roadmap inside v1.18

| Milestone     | What                                                                                                                                                                              | Status                  |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| v1.18.0       | Scenario Driver Library design (this document) — closed-set vocabularies, `ScenarioDriverTemplate` data model, `ActorReasoningInputFrame` + `ReasoningPolicySlot` shapes, design rules, per-milestone roadmap, success condition | Shipped (docs-only)     |
| **v1.18.1**   | **`world/scenario_drivers.py`** — `ScenarioDriverTemplate` immutable dataclass + `ScenarioDriverTemplateBook` append-only store + 10 closed-set vocabularies + the v1.18.0 hard-naming-boundary `FORBIDDEN_SCENARIO_FIELD_NAMES` frozenset; new ledger event type `RecordType.SCENARIO_DRIVER_TEMPLATE_RECORDED`; `WorldKernel.scenario_drivers` wired (empty by default → no canonical-view drift); +56 unit tests | **Shipped**             |
| **v1.18.2**   | **`world/scenario_applications.py`** — `apply_scenario_driver(...)` deterministic helper that takes `(kernel, scenario_driver_template_id, as_of_date)` and **emits new evidence / context records that cite the scenario driver via plain-id citations** through the existing append-only `add_*` interface of the new `ScenarioApplicationBook`. The helper **never mutates a pre-existing context record**: every shift is a new `ScenarioContextShiftRecord` carrying the v1.18.0 audit-metadata block (`reasoning_mode = "rule_based_fallback"` / `reasoning_policy_id` / `reasoning_slot = "future_llm_compatible"` / `evidence_ref_ids` / `unresolved_ref_count` / `boundary_flags`). New ledger event types `RecordType.SCENARIO_DRIVER_APPLICATION_RECORDED` / `RecordType.SCENARIO_CONTEXT_SHIFT_RECORDED`; new closed-set vocabularies `APPLICATION_STATUS_LABELS` (6) / `CONTEXT_SURFACE_LABELS` (9) / `SHIFT_DIRECTION_LABELS` (10); five minimal deterministic family→shift mappings (`rate_repricing_driver` → `market_environment` × `tighten`/`increase_uncertainty`; `credit_tightening_driver` → `market_environment` + `financing_review_surface` × `tighten`; `funding_window_closure_driver` → `financing_review_surface` × `deteriorate`; `liquidity_stress_driver` → `interbank_liquidity` + `market_environment` × `deteriorate`; `information_gap_driver` → `attention_surface` × `information_gap`); other families fall back to a single `no_direct_shift` annotation. Rule-based-fallback only at v1.18.2; a future audited reasoning policy can replace the rule table without changing the audit shape. Trip-wire tests pin: (a) `kernel.<context_book>.snapshot()` for any *pre-existing* record id is byte-equal pre / post call (`PriceBook` / `MarketEnvironmentBook` / `FirmFinancialStateBook` / `InterbankLiquidityStateBook` / `CorporateFinancingPathBook` / `InvestorMarketIntentBook` / `ScenarioDriverTemplateBook`); (b) the helper writes only via `add_application` / `add_context_shift` and reads only the named template + cited `source_context_record_ids` (no global book scan); (c) every emitted record carries the v1.18.0 audit metadata and the seven boundary flags (`no_actor_decision` / `no_llm_execution` / `no_price_formation` / `no_trading` / `no_financing_execution` / `no_investment_advice` / `synthetic_only`); (d) the default-fixture `living_world_digest` is byte-identical to v1.17.last when no scenario is applied; +72 tests in `tests/test_scenario_applications.py` | **Shipped**             |
| **v1.18.3**   | **Scenario report / causal timeline integration** — adds three pure-function helpers to `world/display_timeline.py` (`build_event_annotations_from_scenario_shifts`, `build_causal_timeline_annotations_from_scenario_shifts`, `render_scenario_application_markdown`) that turn v1.18.2 `ScenarioDriverApplicationRecord` / `ScenarioContextShiftRecord` outputs into the v1.17.1 `EventAnnotationRecord` / `CausalTimelineAnnotation` shapes; surface-to-annotation-type map: `market_environment` / `interbank_liquidity` / `industry_condition` / `firm_financial_state` → `market_environment_change`; `market_pressure_surface` → `market_pressure_change`; `financing_review_surface` → `financing_constraint`; `attention_surface` → `attention_shift`; `display_annotation_surface` / `unknown` → `synthetic_event`; `no_direct_shift` → `synthetic_event`; severity coercion `stress` → `high` (preserves the higher rung without inventing a new severity label); causal annotation cites the template id + application id as `source_record_ids` and the shift id as `downstream_record_ids`; every emitted annotation carries the v1.18.0 audit-metadata block (`reasoning_mode` / `reasoning_policy_id` / `reasoning_slot` / `boundary_flags`) verbatim; new kernel-reading driver at `examples/reference_world/scenario_report.py` with a deterministic six-template default fixture exercising all five v1.18.2 mappings plus the `no_direct_shift` fallback path; the driver builds its own fresh kernel and does not move the default-fixture `living_world_digest` of a separately seeded default sweep; markdown report sections: `Scenario templates` / `Scenario applications` / `Emitted context shifts` / `Event annotations` / `Causal timeline annotations` / `Boundary statement` (boundary statement re-pins the v1.18.0 / v1.18.2 discipline and the no-mutation, no-actor-decision, no-price, no-trade, no-forecast invariants); `no_direct_shift` shifts are visibly tagged with a "this is not an error — the template is stored but not yet mapped to a concrete context surface" callout in the report; +23 tests in `tests/test_display_timeline.py` (mapping coverage for every v1.18.2 family + fallback; severity coercion; reporting-calendar snap; deterministic byte-identical output; metadata-block carriage; no-forbidden-display-name scan; no-kernel-import standalone-display discipline; no-ledger-emission; no-PriceBook-mutation; no-default-`living_world_digest`-move) and +18 tests in `tests/test_scenario_report.py` (default-fixture family coverage; deterministic byte-identical markdown; explicit `as_of_date` and ISO-string variants; required-section presence; no forbidden display names / scenario field names in the markdown; no-direct-shift callout visible; no-default-`living_world_digest`-move; no-actor-decision-event-types; audit-metadata block on every annotation; causal annotations cite template + application + shift ids; jurisdiction-neutral identifier scan over both module and test text); **report / display integration only — no living-world scenario execution by default, no mutation of pre-existing context records, no actor decisions, no price formation, no trading, no financing execution, no investment advice, no forecast, no real data, no Japan calibration, no LLM execution**; default-fixture `living_world_digest` unchanged at `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c` for a sweep on a *separately seeded* default kernel | **Shipped (4334 tests)** |
| v1.18.4       | UI scenario selector mock — adds a non-destructive scenario picker to `examples/ui/fwe_workbench_mockup.html` that swaps the active `ScenarioDriverTemplate` from a static fixture, updates Overview / Timeline / Regime Compare / Attention diff slots, and stays bound by the v1.17.4 no-jump discipline; **fixture switching only — the Python engine is not invoked from the UI** | Planned                 |
| **v1.18.last**| **Scenario Driver Library freeze** (docs-only) — single-page reader-facing summary in [`docs/v1_18_scenario_driver_library_summary.md`](v1_18_scenario_driver_library_summary.md); §127 in `docs/world_model.md`; v1.18.last release-readiness snapshot in `RELEASE_CHECKLIST.md`; v1.18.last freeze-pin section in `docs/performance_boundary.md`; v1.18.last `test_inventory.md` header note; v1.18.last addendum in `examples/reference_world/README.md`; v1.18.last cross-link in `docs/fwe_reference_demo_design.md` and `examples/ui/README.md`; no new code, no new tests, no new ledger event types; test count = **4334 / 4334**, per-period record count = **108 / 110**, per-run window = **`[432, 480]`**, `living_world_digest` = **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`** — all unchanged from v1.17.last by design across the entire v1.18 sequence when no scenario is applied | **Shipped (4334 tests)** |

## 8. Performance boundary at v1.18.0

v1.18.0 is docs-only. **Nothing changes**:

- per-period record count: **108 / 110** (unchanged from
  v1.17.last);
- per-run window: **`[432, 480]`** (unchanged);
- default 4-period sweep total: **460 records** (unchanged);
- integration-test `living_world_digest` **for the default
  fixture without any scenario applied**:
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
  (unchanged across the entire v1.17 sequence and the v1.18.0
  design pass);
- pytest count: **4165 / 4165** passing (unchanged).

v1.18.1 → v1.18.last will land code, but the **default-fixture
no-scenario** digest stays byte-identical by design — scenario
application is opt-in. Only when a scenario is explicitly
applied does the digest move, and that move is pinned per
scenario template.

## 9. Hard boundary recap (carried forward verbatim from v1.17.last)

This is **scenario inspection, not prediction**. This is
**stimulus templates, not response rules**. This is **synthetic
context shifts, not real data**.

No order submission. No buy / sell labels. No order book. No
matching. No execution. No clearing. No settlement. No quote
dissemination. No bid / ask. No price update. No `PriceBook`
mutation. No target price. No expected return. No
recommendation. No portfolio allocation. No real exchange
mechanics. No financing execution. No loan approval. No bond /
equity issuance. No underwriting. No syndication. No pricing.
No interest rate. No spread. No coupon. No fee. No offering
price. No investment advice. No real data. No Japan
calibration. No LLM execution. No stochastic behaviour
probabilities. No learned model. **No firm decision rule, no
investor action rule, no bank approval logic, no trading
decision model, no optimal capital structure rule.**

## 10. Forward pointer

v1.18.1 lands the storage module + 20 default templates
(**shipped**). v1.18.2 lands the application helper with
rule-based-fallback policy (**shipped**). v1.18.3 wires the
scenario surface into the v1.17.1 / v1.17.2 / v1.17.3
inspection layer through three pure-function display helpers + a
deterministic markdown driver (**shipped**). v1.18.4 adds a
non-destructive UI selector. v1.18.last freezes.

The next sequence (v1.19+) candidates:

- **v1.19 — local run bridge / report export (conditional).**
  If UI execution becomes necessary, a CLI-driven bridge that
  writes regime-comparison + scenario reports to disk for the
  static workbench to `Load sample run` against. Still no
  backend, no build, no network.
- **v2.0 — Japan public calibration in private JFWE only.**
  Public FWE remains jurisdiction-neutral and synthetic.
- **Future LLM-mode reasoning policies.** When introduced,
  must populate the same `ActorReasoningInputFrame` /
  `ReasoningPolicySlot` audit shape pinned at v1.18.0; must
  carry input evidence ids, prompt / policy id, output label,
  confidence / status, rejected / unknown cases, and must
  never hide a mutation of any source-of-truth book.
- **Future price formation remains gated** until the v1.16 /
  v1.17 / v1.18 surface is operationally legible to a reviewer
  who has not read this codebase.

The v1.18 chain stays scenario-template-only and label-only
forever. Future milestones may *cite* v1.18 templates (plain-id
cross-references, additional driver-impact rendering kinds), but
they may **never** mutate the v1.18.0 vocabulary, replace the
deterministic rule-based fallback with a runtime-active LLM
mode without the audit shape, or hard-code corporate / investor
/ bank judgment as canonical truth on top of the scenario
layer.
