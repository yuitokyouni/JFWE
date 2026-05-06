# v1.25 Institutional Investor Mandate / Benchmark Pressure — Design Note

*v1.25 is the **institutional investor mandate /
benchmark pressure** candidate. It adds a bounded
synthetic mandate / benchmark / liquidity-need /
stewardship-priority surface that conditions **what an
investor reviews or pays attention to** — without ever
deciding what the investor **does**, generating a trade,
producing an allocation, computing an expected return,
emitting a recommendation, or claiming any market
outcome.*

This document is **docs-only at v1.25.0**. It introduces
no runtime module, no new dataclass, no new ledger
event, no new test, no new label vocabulary, no new
behavior. It is the binding scope pin for v1.25.x;
v1.25.1 / v1.25.2 / v1.25.3 / v1.25.4 / v1.25.last must
implement exactly to this design or the design must be
re-pinned.

The companion documents are:

- [`v1_24_manual_annotation_layer.md`](v1_24_manual_annotation_layer.md)
  §24 — the v1.24.last freeze v1.25 sits alongside (the
  two layers are decoupled; v1.25 does not consume,
  modify, or extend the v1.24 annotation surface).
- [`v1_22_static_ui_stress_readout_reflection.md`](v1_22_static_ui_stress_readout_reflection.md)
  — the v1.22 export-side payload section v1.25.3 may
  extend with an optional descriptive-only mandate
  section (omitted when empty so v1.21.last digests
  stay byte-identical).
- [`v1_15_securities_market_intent_aggregation_design.md`](v1_15_securities_market_intent_aggregation_design.md)
  — the v1.15.5 investor-intent layer v1.25 conditions
  attention / review context over.
- [`v1_16_endogenous_market_intent_direction_design.md`](v1_16_endogenous_market_intent_direction_design.md)
  — the v1.16.2 closed-loop attention path v1.25 may
  surface mandate context to (read-only).
- [`world_model.md`](world_model.md) §134 — the
  constitutional position of v1.25.

---

## 1. Scope statement (binding)

v1.25's single goal is narrow: **let an investor carry a
mandate / benchmark / liquidity / stewardship profile
that biases what they review, without changing what
they do.**

Concretely:

- An **investor mandate profile** is a small, append-
  only, closed-set-label record cited by an investor
  via plain id. It carries a mandate type, a benchmark
  pressure label, a liquidity need label, a liability
  horizon label, a small set of stewardship priority
  labels, a review frequency label, a concentration
  tolerance label, plus the standard
  `visibility` / `metadata` carriers.
- The profile **conditions** the v1.16.x attention path
  and the v1.15.5 investor-intent review surface by
  surfacing additional descriptive labels: which
  evidence dimensions are salient, which review
  contexts are highlighted, which stewardship priorities
  inform the review. It **does not** change what the
  investor records as intent, does not generate a
  market intent, does not produce an order, and does
  not allocate capital.
- The profile is **append-only** with respect to its
  storage book; an investor revises a mandate by
  adding a new profile (the prior profile remains in
  the book). No mandate ever mutates a prior mandate.
- The profile is **read-only with respect to the
  world**. No source-of-truth book mutation, no
  trading, no settlement, no actor decision; the only
  ledger mutation is the storage event itself, fired
  exactly once per `add_profile(...)` call.
- The profile is **decoupled from v1.24**. Manual
  annotations and investor mandates do not consume
  each other; a v1.25 mandate readout makes no
  reference to manual annotations, and a v1.24
  manual annotation makes no reference to mandates.
  Both layers cite the same v1.21.x audit surface
  independently.

What v1.25 is (binding):

- **Attention / review context conditioning only.**
  v1.25.2 reads investor mandate profiles and emits
  a read-only mandate-attention-context projection
  carrying selected attention bias labels, review
  context labels, cited mandate fields, and warnings.
  No actor behavior emerges.
- **Bounded synthetic.** Six mandate-type labels (plus
  `unknown`); five benchmark-pressure / liquidity-
  need labels; three liability-horizon labels (plus
  `unknown`); five stewardship-priority labels; three
  review-frequency labels; small concentration-
  tolerance set. Every closed set is finalised at
  v1.25.0 design and pinned at v1.25.1 implementation;
  expanding any closed set requires a fresh design pin.
- **Sequence is strictly serial.** v1.25.0 ships docs;
  v1.25.1 ships storage; v1.25.2 ships the read-only
  mandate-attention-context readout; v1.25.3 ships
  optional export + minimal UI; v1.25.4 ships a
  read-only case study; v1.25.last ships the docs-
  only freeze.

What v1.25 is **NOT** (binding):

- v1.25 is **NOT** a portfolio. No `portfolio_allocation`,
  `target_weight`, `overweight`, `underweight`,
  `rebalance`, or any allocation field, label, or value.
- v1.25 is **NOT** a trade. No `buy`, `sell`, `order`,
  `trade`, `execution`, or any trading-verb field,
  label, or value.
- v1.25 is **NOT** a recommendation. No `recommendation`
  / `investment_advice` / `expected_return` /
  `target_price` field, label, or value.
- v1.25 is **NOT** a benchmark / tracking-error
  number. No `tracking_error_value`, `alpha`,
  `performance`, `price`, `forecast`, `prediction`
  field, label, or value. The `benchmark_pressure_label`
  is a closed-set string (`"none"` / `"low"` /
  `"moderate"` / `"high"` / `"unknown"`); it is **not**
  a numeric tracking-error budget.
- v1.25 is **NOT** an actor decision. No
  `actor_decision` / `firm_decision` / `investor_action`
  / `bank_approval` / `trading_decision` field, label,
  or value emerges from the v1.25 surface.
- v1.25 is **NOT** real-data-driven. No
  `real_data` / `japan_calibration` / real-issuer /
  licensed-taxonomy field, label, or value. Public
  v1.x stays jurisdiction-neutral and synthetic; v1.25
  inherits that boundary verbatim.
- v1.25 is **NOT** LLM-authored. v1.25.x does not
  invoke any LLM at runtime. No `llm_output` /
  `llm_prose` / `prompt_text` field, label, or value.
- v1.25 is **NOT** a UI rebuild. v1.25.3 may add a
  small read-only "Investor mandate context" panel
  inside an existing sheet; it adds no tab, no
  backend, no scrollable free-text input.

---

## 2. What an investor mandate profile is (binding)

An **investor mandate profile** is one immutable,
append-only, closed-set-label record cited by an
investor via plain id. It carries:

- a **mandate type** label — what kind of investor
  archetype this profile describes
  (`pension_like` / `insurance_like` /
  `active_manager_like` / `passive_manager_like` /
  `sovereign_like` / `endowment_like` / `unknown`);
- a **benchmark pressure** label — how much the
  investor reviews against an unspecified synthetic
  benchmark (`none` / `low` / `moderate` / `high` /
  `unknown`). The label is descriptive; **no numeric
  tracking-error budget is encoded**;
- a **liquidity need** label — how much of the
  reviewed portfolio is expected to need liquidity
  on a short horizon (`low` / `moderate` / `high` /
  `unknown`);
- a **liability horizon** label — the time horizon
  of the investor's liabilities or commitments
  (`short` / `medium` / `long` / `unknown`);
- a small set of **stewardship priority** labels —
  what governance / disclosure / capital-discipline
  themes the investor flags for review
  (subset of `capital_discipline` /
  `governance_review` / `climate_disclosure` /
  `liquidity_resilience` / `funding_access` /
  `unknown`);
- a **review frequency** label — how often the
  investor reviews the mandate's covered surface
  (`monthly` / `quarterly` / `event_driven` /
  `unknown`);
- a **concentration tolerance** label — how much
  single-issuer / single-sector concentration the
  investor's review treats as in-scope (`low` /
  `moderate` / `high` / `unknown`);
- the standard `visibility` carrier (closed set) and
  an opaque `metadata` mapping scanned for forbidden
  keys.

The profile is **descriptive**, not interpretive. It
says "this investor reviews under a mandate that
emphasises X / Y / Z"; it does **not** say "this
investor will buy / sell / hold X / Y / Z."

A profile is **cited** by an investor via the
investor's existing plain id. The storage book does
not dereference the citation against any other book —
the v1.16.x investor layer remains the canonical
investor-id authority. The v1.25.2 mandate-attention-
context readout is the only layer that combines a
mandate profile with v1.16.x investor state, and it
does so **read-only**.

---

## 3. What benchmark pressure means in public v1.x (binding)

The `benchmark_pressure_label` field uses one of five
closed-set strings — `"none"` / `"low"` / `"moderate"` /
`"high"` / `"unknown"` — and **nothing else**.

- The label is a **descriptive string**, not a number.
  No `tracking_error_value`, `tracking_error_basis_points`,
  `benchmark_weight`, `index_weight`, `active_share`,
  `alpha`, `performance`, or any numeric benchmark
  metric is allowed in the dataclass, the payload, or
  the metadata.
- The label describes **how much the investor's
  review process emphasises a benchmark frame** —
  which evidence the investor highlights, not which
  trades they place. A `"high"` label means the
  investor's review tends to highlight benchmark-
  framed evidence (concentration deltas, sector-
  weight deltas, index-event timelines); a `"none"`
  label means the investor's review does not surface
  benchmark-framed evidence at all.
- The label is **not paired with a benchmark
  identifier**. v1.25.x does not name any
  benchmark — no real index, no synthetic index id,
  no licensed taxonomy. A future milestone could
  add a synthetic-benchmark-id field under a fresh
  design pin; v1.25 deliberately does not.
- The label is **not** a probability, a confidence,
  a magnitude, or a quantified intensity. The
  v1.21.0a "labels-not-numbers" discipline applies
  verbatim.
- The label is **not** a backtested / historically-
  calibrated category. Public v1.x stays
  jurisdiction-neutral and synthetic; v1.25.x carries
  no calibration evidence and makes no claim about
  real-world investor archetypes.

The reader of the audit object sees, for each
investor profile, a single closed-set label. The
reader **cannot** read off "how much tracking error
this investor tolerates"; that frame is forbidden.

---

## 4. Why v1.25 follows v1.24 (sequence rationale)

The v1.24 manual-annotation layer materialised the
v1.23.2 Cat 5 inter-reviewer reproducibility
placeholder's runtime surface as a **human-authored
audit overlay** on existing citation-graph records. It
gave reviewers a way to mark the audit object;
v1.24.x adds storage, readout, export, and a small UI
panel. The v1.24.x discipline was: human-authored
only, append-only, read-only with respect to the
world.

v1.25 sits **alongside** v1.24, not on top of it. The
two layers are decoupled:

- v1.24 manual annotations describe the **reviewer's
  observations** about the citation graph; v1.25
  mandate profiles describe the **investor's review
  posture**. Different audit surfaces; different
  closed sets; different read-only consumers.
- A v1.24 annotation may cite v1.25.2 mandate-attention-
  context readout ids in a future milestone, but
  v1.24 already supports that via its
  `validation_report:` / generic-prefix citation
  surface; no v1.25 change is required to make
  cross-citation possible.
- A v1.25 mandate-attention-context readout makes
  **no** reference to v1.24 manual annotations. The
  two surfaces are produced independently.

v1.25 inherits the v1.24 discipline pattern but does
not depend on v1.24 runtime behaviour. The reasons
v1.25 follows v1.24 are sequencing reasons (v1.24 was
the candidate the autopilot scheduled first;
v1.25 was queued behind it) and not coupling reasons.

The v1.25 layer **adds** to the v1.16.x investor-intent
audit surface: a v1.16.2 `InvestorMarketIntentRecord`
already carries a plain-id citation to its emitting
investor; the v1.25 mandate-attention-context readout
joins those records to a mandate profile descriptively,
without changing what the v1.16.x records contain or
when they fire.

---

## 5. What mandate **can** condition (binding, descriptive-only)

The v1.25.2 mandate-attention-context readout exposes
**four read-only surfaces** that downstream consumers
(future review-routine helpers, the optional v1.25.3
export, the optional v1.25.3 UI panel, the v1.25.4 case
study) can read. None of these surfaces emit a market
intent, a market order, an actor decision, or any new
ledger record beyond the v1.25.1 storage event.

### 5.1 Attention selection conditioning (read-only)

A profile's `mandate_type_label` and
`benchmark_pressure_label` may **bias the salience of
existing v1.12.x attention dimensions** — which
evidence dimensions an investor's review highlights
under that mandate. Concretely, the v1.25.2 readout
exposes a `selected_attention_bias_labels` tuple of
closed-set strings drawn from a small bias vocabulary
(e.g. `benchmark_drift_review`,
`liquidity_horizon_review`,
`stewardship_disclosure_review`,
`concentration_review`,
`refinancing_window_review`, `unknown`). The bias
vocabulary is finalised at v1.25.1 design and is not
expanded later.

The bias labels are **read-only descriptive
projections**: they say what an investor's review
tends to highlight under this mandate, not what the
investor decides. The v1.16.x `ActorAttentionStateRecord`
emission is **not** changed by v1.25; v1.25.2's
projection is a separate read-only object.

### 5.2 Review context conditioning (read-only)

A profile's `liquidity_need_label` and
`liability_horizon_label` may bias which **review
context labels** the readout highlights. The closed-
set review-context vocabulary is small (e.g.
`short_horizon_review`,
`long_horizon_review`,
`liquidity_resilience_review`,
`benchmark_relative_review`, `unknown`).

Again, **no review actually fires** because of v1.25;
the existing v1.x reference-routine layer (v1.10 /
v1.11) emits reviews on its own schedule. v1.25.2
exposes only the descriptive projection of "what
review context labels apply to this investor under
this mandate."

### 5.3 Evidence salience conditioning (read-only)

A profile's `concentration_tolerance_label` and
`stewardship_priority_labels` may bias which existing
v1.12.x evidence dimensions the readout flags as
salient (e.g. `concentration_delta_evidence`,
`governance_disclosure_evidence`,
`climate_disclosure_evidence`,
`funding_access_evidence`,
`refinancing_window_evidence`,
`unknown`).

Salience is **descriptive**; it does **not** weight
the v1.12.x attention budget mechanically. The
v1.12.last finite-attention-budget discipline is
preserved verbatim.

### 5.4 Stewardship priority conditioning (read-only)

A profile's `stewardship_priority_labels` (a small
multiset drawn from the closed set in §6.5) may
surface in the v1.25.2 readout's
`review_context_labels` field — the readout cites
which stewardship priorities the investor's review
tends to flag for follow-up. The v1.x existing
stewardship engagement layer (v1.10 / v1.11) is
**not** modified; v1.25 adds only a descriptive
projection.

---

## 6. What mandate **cannot** condition (binding)

This list is itself part of the boundary. v1.25.x
rejects each item at construction time (forbidden-
name scan, closed-set membership check, source-kind
allowlist):

- **NOT a trade.** No `buy` / `sell` / `order` /
  `trade` / `execution` field, label, or value
  appears in any v1.25.x record, payload, metadata
  key, export entry, or UI surface.
- **NOT an allocation.** No `portfolio_allocation`
  / `target_weight` / `overweight` / `underweight`
  / `rebalance` / `weight_change` / `allocation_band`
  field, label, or value.
- **NOT an expected return.** No `expected_return`
  / `expected_alpha` / `expected_path` /
  `expected_response` / `forecast` / `prediction`
  / `predicted_path` field, label, or value.
- **NOT a target price.** No `target_price` /
  `target_index` / `price_target` / `nav_target`
  / `valuation_target` field, label, or value.
- **NOT a recommendation.** No `recommendation` /
  `investment_advice` / `investment_recommendation`
  field, label, or value.
- **NOT an actor decision.** No `actor_decision` /
  `firm_decision` / `investor_action` /
  `bank_approval` / `trading_decision` /
  `optimal_capital_structure` field, label, or
  value.
- **NOT a benchmark number.** No
  `tracking_error_value` / `tracking_error_basis_points`
  / `benchmark_weight` / `active_share` / `alpha` /
  `performance` field, label, or value.
- **NOT a price.** No `price` / `market_price` /
  `predicted_index` / `predicted_path` / `nav` /
  `index_value` / `benchmark_value` field, label,
  or value.
- **NOT a real-data ingest.** No `real_data` /
  `real_data_value` / `real_indicator_value` /
  `cpi_value` / `gdp_value` / real-issuer /
  licensed-taxonomy field, label, or value.
- **NOT a Japan calibration.** No
  `japan_calibration` field, label, or value.
- **NOT an LLM execution path.** No `llm_output`
  / `llm_prose` / `prompt_text` field, label, or
  value. v1.25.x does not invoke any LLM.
- **NOT a stress interaction inference.** v1.25
  inherits the v1.21.0a *Deferred:
  StressInteractionRule* boundary verbatim. No
  `amplify` / `dampen` / `offset` / `coexist`
  / `aggregate_*` / `combined_*` / `net_*` /
  `dominant_*` / `composite_*` / `interaction_label`
  / `composition_label` field, label, or value.
- **NOT an auto-annotation.** v1.25 inherits the
  v1.24.0 manual-annotation boundary: no
  `auto_annotation` / `auto_inference` /
  `automatic_review` / `inferred_interaction` /
  `causal_effect` / `causal_proof` / `impact_score`
  field, label, or value (v1.25 does not produce
  manual annotations; the v1.24 surface stays as the
  exclusive home for human-authored annotation).

Mechanically, the v1.25.1 storage layer reuses the
v1.23.1 canonical
:data:`world.forbidden_tokens.FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES`
+ a v1.25.0 mandate delta (the §6 list above). The
dataclass field-name guard runs at construction time;
payload-key + metadata-key + label-value scans run at
construction time.

Because the storage layer rejects every forbidden
token at construction, no profile can ever propagate
a forbidden token into a downstream consumer (the
v1.25.2 readout, the v1.25.3 export, the v1.25.3 UI
panel, the v1.25.4 case study).

---

## 7. Proposed `InvestorMandateProfile` shape (design level)

The dataclass shape below is the v1.25.0 design pin.
v1.25.1 implementation must match this shape exactly;
any field rename, addition, or removal requires a
fresh design pin (a v1.25.0a or later correction).

```python
@dataclass(frozen=True)
class InvestorMandateProfile:
    """Immutable, append-only investor mandate /
    benchmark pressure / liquidity / stewardship
    profile cited by an investor via plain id."""

    mandate_profile_id: str
    investor_id: str
    mandate_type_label: str
    benchmark_pressure_label: str
    liquidity_need_label: str
    liability_horizon_label: str
    stewardship_priority_labels: tuple[str, ...]
    review_frequency_label: str
    concentration_tolerance_label: str
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

Field semantics (binding):

- `mandate_profile_id` — stable id, unique within the
  `InvestorMandateProfileBook`.
- `investor_id` — plain-id citation to a v1.16.x
  investor. The storage book does not dereference
  the citation against any other book.
- `mandate_type_label` — closed-set string, member of
  `MANDATE_TYPE_LABELS` (§8.1).
- `benchmark_pressure_label` — closed-set string,
  member of `BENCHMARK_PRESSURE_LABELS` (§8.2). **A
  closed-set descriptive label, not a numeric
  tracking-error budget.**
- `liquidity_need_label` — closed-set string, member
  of `LIQUIDITY_NEED_LABELS` (§8.3).
- `liability_horizon_label` — closed-set string,
  member of `LIABILITY_HORIZON_LABELS` (§8.4).
- `stewardship_priority_labels` — a tuple of closed-
  set strings drawn from `STEWARDSHIP_PRIORITY_LABELS`
  (§8.5). The tuple may be empty (a profile can
  decline to flag any stewardship priority) or carry
  up to N entries (N pinned at v1.25.1; the design
  intent is "small, ≤ 5"). Duplicate labels in the
  tuple are rejected at construction.
- `review_frequency_label` — closed-set string,
  member of `REVIEW_FREQUENCY_LABELS` (§8.6).
- `concentration_tolerance_label` — closed-set
  string, member of `CONCENTRATION_TOLERANCE_LABELS`
  (§8.7).
- `status` — small closed-set string
  (`"draft"` / `"active"` / `"superseded"` /
  `"archived"` / `"unknown"`). Status changes are
  recorded by adding a new profile (append-only
  discipline).
- `visibility` — small closed-set string
  (`"public"` / `"restricted"` / `"internal"` /
  `"private"` / `"unknown"`).
- `boundary_flags` — small mapping defaulted to the
  v1.25 anti-claim set (§9). Caller-set additional
  `True` flags allowed; default flags non-removable.
- `metadata` — opaque mapping scanned for forbidden
  keys.

### 7.1 Required-field discipline

- `mandate_profile_id`, `investor_id`,
  `mandate_type_label`, `benchmark_pressure_label`,
  `liquidity_need_label`, `liability_horizon_label`,
  `review_frequency_label`,
  `concentration_tolerance_label` are required (must
  be non-empty).
- `stewardship_priority_labels` may be the empty
  tuple but, when non-empty, every entry is a non-
  empty member of the closed set (no duplicates).
- All optional fields default per the dataclass
  signature.

### 7.2 Anti-fields (forbidden field names — binding)

The dataclass field set must NOT contain any of the
v1.18.0 / v1.19.0 / v1.21.0a / v1.22.0 / v1.24.0
forbidden tokens, nor the v1.25.0 mandate delta
(§10):

- v1.18.0 actor-decision tokens (`firm_decision`,
  `investor_action`, `bank_approval`, etc.);
- v1.19.0 run-export tokens (`predicted_path`,
  `forecast_index`, `target_price`, etc.);
- v1.19.3 / v1.20.0 real-indicator + real-issuer +
  licensed-taxonomy tokens;
- v1.21.0a stress / aggregate / interaction tokens;
- v1.22.0 export-side outcome / impact tokens;
- v1.24.0 manual-annotation tokens
  (`auto_annotation`, `causal_proof`, `impact_score`,
  etc.);
- the v1.25.0 mandate delta (§10):
  `portfolio_allocation`, `target_weight`,
  `overweight`, `underweight`, `rebalance`,
  `tracking_error_value`, `alpha`, `performance`,
  `expected_alpha`, `weight_change`,
  `allocation_band`.

The runtime
`world.forbidden_tokens.FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES`
composed set lands at v1.25.1 (per the v1.23.1 BASE
+ delta + composed convention).

---

## 8. Closed-set vocabularies (binding for v1.25.0 design)

### 8.1 `MANDATE_TYPE_LABELS`

Closed set; v1.25.1 implementation must match
exactly:

```python
MANDATE_TYPE_LABELS: frozenset[str] = frozenset({
    "pension_like",
    "insurance_like",
    "active_manager_like",
    "passive_manager_like",
    "sovereign_like",
    "endowment_like",
    "unknown",
})
```

The `_like` suffix is binding: the labels describe
**archetypes**, not real institutional categories.
v1.25.x carries no claim that any specific
real-world investor matches any specific archetype.

### 8.2 `BENCHMARK_PRESSURE_LABELS`

Closed set; v1.25.1 implementation must match
exactly:

```python
BENCHMARK_PRESSURE_LABELS: frozenset[str] = frozenset({
    "none",
    "low",
    "moderate",
    "high",
    "unknown",
})
```

Five descriptive bands. **No numeric mapping**; the
labels are not "0% / 25% / 50% / 75%" tracking-error
buckets in disguise.

### 8.3 `LIQUIDITY_NEED_LABELS`

Closed set; v1.25.1 implementation must match
exactly:

```python
LIQUIDITY_NEED_LABELS: frozenset[str] = frozenset({
    "low",
    "moderate",
    "high",
    "unknown",
})
```

### 8.4 `LIABILITY_HORIZON_LABELS`

Closed set; v1.25.1 implementation must match
exactly:

```python
LIABILITY_HORIZON_LABELS: frozenset[str] = frozenset({
    "short",
    "medium",
    "long",
    "unknown",
})
```

### 8.5 `STEWARDSHIP_PRIORITY_LABELS`

Closed set; v1.25.1 implementation must match
exactly:

```python
STEWARDSHIP_PRIORITY_LABELS: frozenset[str] = frozenset({
    "capital_discipline",
    "governance_review",
    "climate_disclosure",
    "liquidity_resilience",
    "funding_access",
    "unknown",
})
```

Carried in `stewardship_priority_labels` as a tuple;
duplicates rejected at construction.

### 8.6 `REVIEW_FREQUENCY_LABELS`

Closed set; v1.25.1 implementation must match
exactly:

```python
REVIEW_FREQUENCY_LABELS: frozenset[str] = frozenset({
    "monthly",
    "quarterly",
    "event_driven",
    "unknown",
})
```

### 8.7 `CONCENTRATION_TOLERANCE_LABELS`

Closed set; v1.25.1 implementation must match
exactly:

```python
CONCENTRATION_TOLERANCE_LABELS: frozenset[str] = frozenset({
    "low",
    "moderate",
    "high",
    "unknown",
})
```

### 8.8 `STATUS_LABELS` / `VISIBILITY_LABELS`

Closed sets; v1.25.1 implementation must match
exactly:

```python
STATUS_LABELS: frozenset[str] = frozenset({
    "draft",
    "active",
    "superseded",
    "archived",
    "unknown",
})

VISIBILITY_LABELS: frozenset[str] = frozenset({
    "public",
    "restricted",
    "internal",
    "private",
    "unknown",
})
```

---

## 9. Default boundary flags (binding)

Every emitted `InvestorMandateProfile` carries the
following default `boundary_flags` mapping. v1.25.1
construction merges caller-supplied flags on top, but
the defaults below are non-removable:

```python
_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    # v1.18.0 boundary
    ("no_actor_decision", True),
    ("no_llm_execution", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_financing_execution", True),
    ("no_investment_advice", True),
    ("synthetic_only", True),
    # v1.21.0a additions (re-pinned at v1.25.0)
    ("no_aggregate_stress_result", True),
    ("no_interaction_inference", True),
    ("no_field_value_claim", True),
    ("no_field_magnitude_claim", True),
    # v1.25.0 additions (mandate-specific)
    ("descriptive_only", True),
    ("no_portfolio_allocation", True),
    ("no_target_weight", True),
    ("no_rebalancing", True),
    ("no_expected_return_claim", True),
    ("no_tracking_error_value", True),
    ("no_benchmark_identification", True),
    ("attention_review_context_only", True),
)
```

A caller can set additional flags to `True`; a caller
**cannot** set any of the defaults to `False`.
Construction rejects any `False` override.

---

## 10. Forbidden tokens (binding)

The v1.25.0 forbidden-token list extends the v1.23.1
canonical composition with v1.25-specific tokens.
The combined set is binding for v1.25.x.

**Inherited from v1.23.1 canonical composition**
(verbatim, by reference):

- v1.18.0 actor-decision tokens.
- v1.19.0 run-export tokens.
- v1.19.3 real-indicator tokens.
- v1.20.0 real-issuer / licensed-taxonomy tokens.
- v1.21.0a stress / aggregate / interaction tokens.
- v1.22.0 export-side outcome / impact tokens.

**Inherited from v1.24.0 manual-annotation
composition**:

- v1.24.0 manual-annotation delta
  (`auto_annotation`, `causal_proof`, `impact_score`,
  etc.).

**v1.25.0 mandate delta** (new at this design pin):

```python
FORBIDDEN_TOKENS_V1_25_0_MANDATE_DELTA: frozenset[str] = (
    frozenset({
        # v1.25.0 portfolio / allocation language
        "portfolio_allocation",
        "target_weight",
        "overweight",
        "underweight",
        "rebalance",
        "rebalancing",
        "weight_change",
        "allocation_band",
        # v1.25.0 benchmark-number / performance language
        "tracking_error_value",
        "tracking_error_basis_points",
        "benchmark_weight",
        "benchmark_value",
        "active_share",
        "alpha",
        "performance",
        "expected_alpha",
        # v1.25.0 explicit mandate-as-action prohibitions
        "mandate_action",
        "mandate_decision",
        "mandate_buy_signal",
        "mandate_sell_signal",
    })
)
```

The composed
`FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES` set will be:

```python
FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_19_3_REAL_INDICATOR_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_REAL_ISSUER_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_LICENSED_TAXONOMY_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
    | FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_24_0_MANUAL_ANNOTATION_DELTA
    | FORBIDDEN_TOKENS_V1_25_0_MANDATE_DELTA
)
```

Scan discipline (carried verbatim from v1.21.x /
v1.24.x storage):

- Dataclass field names checked against the composed
  set at construction time.
- Payload keys (the ledger payload mapping) checked
  at construction time.
- Metadata keys checked at construction time.
- Label values checked at construction time
  (closed-set membership + belt-and-braces forbidden
  scan).

---

## 11. `InvestorMandateProfileBook` shape (design level)

```python
@dataclass
class InvestorMandateProfileBook:
    """Append-only storage for InvestorMandateProfile."""

    ledger: Ledger | None = None
    clock: Clock | None = None
    _profiles: dict[str, InvestorMandateProfile] = field(
        default_factory=dict
    )

    def add_profile(
        self,
        profile: InvestorMandateProfile,
        *,
        simulation_date: Any = None,
    ) -> InvestorMandateProfile:
        ...

    def get_profile(
        self, mandate_profile_id: str
    ) -> InvestorMandateProfile:
        ...

    def list_profiles(
        self,
    ) -> tuple[InvestorMandateProfile, ...]:
        ...

    def list_by_investor(
        self, investor_id: str
    ) -> tuple[InvestorMandateProfile, ...]:
        ...

    def list_by_mandate_type(
        self, mandate_type_label: str
    ) -> tuple[InvestorMandateProfile, ...]:
        ...

    def list_by_status(
        self, status: str
    ) -> tuple[InvestorMandateProfile, ...]:
        ...

    def snapshot(self) -> dict[str, Any]:
        ...
```

Storage discipline (binding):

- One ledger record per successful
  `add_profile(...)` call: a single
  `investor_mandate_profile_recorded` event with
  the profile's id as `object_id` and a payload
  carrying every dataclass field.
- No ledger record on duplicate id (raises
  `DuplicateInvestorMandateProfileError`).
- No mutation of any other source-of-truth book.
- No call to
  `world.stress_applications.apply_stress_program`,
  `world.scenario_applications.apply_scenario_driver`,
  `world.investor_intent.*`, or
  `world.market_intents.*`.
- No automatic profile helper. The book exposes
  `add_profile(profile)` only.

The kernel's `investor_mandate_profiles` field is
wired with
`field(default_factory=InvestorMandateProfileBook)`;
an empty book emits no ledger record, leaving every
existing `living_world_digest` byte-identical at
v1.25.x:

- `quarterly_default` —
  `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
- `monthly_reference` —
  `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
- `scenario_monthly_reference_universe` test-fixture
  — `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
- v1.20.4 CLI bundle —
  `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`

---

## 12. Read-only mandate-attention-context readout (binding shape for v1.25.2)

`world/investor_mandate_attention_context.py` (NEW at
v1.25.2) will ship:

```python
@dataclass(frozen=True)
class InvestorMandateAttentionContext:
    """Immutable, read-only attention-context
    projection over an investor + mandate pair."""

    readout_id: str
    investor_id: str
    mandate_profile_id: str
    selected_attention_bias_labels: tuple[str, ...]
    review_context_labels: tuple[str, ...]
    cited_mandate_fields: tuple[str, ...]
    warnings: tuple[str, ...]
    metadata: Mapping[str, Any]
```

Read-only discipline (binding):

- Re-running the helper on the same kernel state
  produces a byte-identical readout.
- The readout emits **no** ledger record; v1.25.2
  ships **no** new
  :class:`world.ledger.RecordType`.
- The readout does **not** mutate any kernel book.
- The readout does **not** call
  `apply_stress_program`,
  `apply_scenario_driver`,
  `add_profile`, or any v1.16.x investor-intent
  helper.
- No automatic interpretation. The readout never
  reduces multiple profiles into a "combined"
  profile, never infers an interaction, never
  produces an outcome / impact / forecast /
  recommendation, never emits a market intent.
- No portfolio allocation. No trade. No order. No
  expected return. No target weight.

### 12.1 Closed-set bias / review-context vocabularies

Two small closed sets pinned at v1.25.1:

```python
MANDATE_ATTENTION_BIAS_LABELS: frozenset[str] = frozenset({
    "benchmark_drift_review",
    "liquidity_horizon_review",
    "stewardship_disclosure_review",
    "concentration_review",
    "refinancing_window_review",
    "unknown",
})

MANDATE_REVIEW_CONTEXT_LABELS: frozenset[str] = frozenset({
    "short_horizon_review",
    "long_horizon_review",
    "liquidity_resilience_review",
    "benchmark_relative_review",
    "stewardship_followup_review",
    "unknown",
})
```

The mapping from mandate fields → bias / review-
context labels is **deterministic, rule-based, and
small**; it lands in v1.25.2 as a few short tables,
not as a classifier or LLM.

---

## 13. Optional export + minimal UI (design level for v1.25.3)

### 13.1 Export

v1.25.3 may add an optional descriptive-only
`investor_mandate_readout` payload section on
`RunExportBundle`. The section is omitted when empty
(no profile in the kernel) so every pre-v1.25
bundle digest stays byte-identical.

Allowed export keys (whitelist):

- `investor_id`
- `mandate_profile_id`
- `mandate_type_label`
- `benchmark_pressure_label`
- `liquidity_need_label`
- `liability_horizon_label`
- `stewardship_priority_labels`
- `review_frequency_label`
- `concentration_tolerance_label`
- `selected_attention_bias_labels`
- `review_context_labels`
- `warnings`

Forbidden export keys / values:

- `portfolio_allocation` / `target_weight` /
  `overweight` / `underweight` / `rebalance` /
  `weight_change`
- `tracking_error_value` / `alpha` /
  `performance` / `expected_alpha`
- `buy` / `sell` / `order` / `trade` /
  `execution`
- `recommendation` / `investment_advice`
- `expected_return` / `target_price` /
  `forecast` / `prediction`
- v1.18.0 / v1.19.0 / v1.21.0a / v1.22.0 / v1.24.0
  forbidden tokens.

### 13.2 UI

v1.25.3 may add a small read-only **"Investor
mandate context"** panel inside an existing sheet
(likely the existing investor-relevant area or
Universe). The v1.20.5 / v1.22.2 / v1.24.3 11-tab
↔ 11-sheet bijection is preserved at v1.25.last;
v1.25.3 introduces no new tab.

Candidate panel content:

- mandate type label;
- benchmark pressure label;
- liquidity need label;
- liability horizon label;
- stewardship priority label list;
- review frequency label;
- concentration tolerance label;
- selected attention bias label list (from
  v1.25.2 readout);
- review context label list (from v1.25.2
  readout);
- warnings count + first warning text.

The panel does **not** show: any allocation
percentage, any tracking-error number, any
expected-return value, any recommendation, any
buy / sell / trade / order / execution wording.

textContent only; no innerHTML for caller-supplied
values.

If v1.25.3 prefers export-only (no UI), the design
pin permits skipping the UI panel entirely.

---

## 14. Case study (binding shape for v1.25.4)

v1.25.4 ships a **read-only case study** showing
how two investor archetypes (e.g.
`pension_like` with `liability_horizon = "long"` /
`benchmark_pressure = "low"`, vs.
`active_manager_like` with `liability_horizon = "short"`
/ `benchmark_pressure = "high"`) review the **same**
v1.21.3 stress readout differently because the
v1.25.2 readout surfaces different attention bias /
review context labels for each.

Binding constraints (v1.25.4):

- The case study is **read-only**: it loads a
  pre-stress-applied kernel, attaches two
  `InvestorMandateProfile` records, builds two
  v1.25.2 readouts, and asserts that the two
  readouts surface different label sets.
- The case study **never** emits a market intent,
  market order, allocation, expected return, target
  price, recommendation, or any actor decision.
- The case study **never** claims one archetype is
  "right" and the other "wrong"; both are
  descriptive projections.
- The case study reuses existing v1.21.3 stress
  readout + v1.25.2 mandate-attention-context
  readout verbatim — no new ledger event types, no
  new label vocabularies.
- The pinned output is byte-deterministic across
  runs (Cat 1 determinism pin extends verbatim).

Companion doc:
`docs/case_study_002_investor_mandate_attention_context.md`
(NEW at v1.25.4).

---

## 15. Sub-milestone sequence (binding for v1.25.x)

The sequence is **strictly serial**. v1.25.1 must
not start until v1.25.0 docs are merged and CI is
green. v1.25.2 must not start until v1.25.1 storage
is byte-stable. v1.25.3 must not start until
v1.25.2 readout is in place. v1.25.4 must not start
until v1.25.3 export ships. v1.25.last must not
start until v1.25.4 is shipped and CI is green.

| Sub-milestone | Surface | What it ships |
| ------------- | ------- | ------------- |
| **v1.25.0** | docs only | This design note. §134 in `world_model.md`. README §9 row. |
| v1.25.1 | runtime + tests | `InvestorMandateProfile` + `InvestorMandateProfileBook` storage in [`world/investor_mandate_profiles.py`](../world/investor_mandate_profiles.py) (NEW). Closed-set vocabularies per §8. Default boundary flags per §9. Forbidden-token composition per §10 (extending [`world/forbidden_tokens.py`](../world/forbidden_tokens.py) with the v1.25.0 delta + composed set). Optional `INVESTOR_MANDATE_PROFILE_RECORDED` `RecordType` if convention requires. **No no-mandate / no-profile behavior change.** **No digest movement.** ~ +14 tests. |
| v1.25.2 | runtime + tests | `InvestorMandateAttentionContext` + `build_investor_mandate_attention_context(...)` in [`world/investor_mandate_attention_context.py`](../world/investor_mandate_attention_context.py) (NEW). Closed-set bias / review-context vocabularies (§12.1). **No ledger emission.** **No mutation.** ~ +9 tests. |
| v1.25.3 | export + optional UI + tests | Optional `investor_mandate_readout` payload section on `RunExportBundle` (descriptive-only, empty-by-default, omitted from JSON when empty so v1.21.last digests stay byte-identical). Optional minimal "Investor mandate context" panel in an existing sheet of `examples/ui/fwe_workbench_mockup.html` (no new tab; `textContent` only). ~ +9 tests. |
| v1.25.4 | example + tests + docs | Read-only case study showing two archetypes reviewing the same stress readout differently. New companion doc `case_study_002_investor_mandate_attention_context.md`. ~ +8 tests. |
| **v1.25.last** | docs only | Final freeze. Sequence map, hard-boundary re-pin, future candidates. |

### 15.1 Cardinality (binding for v1.25.x)

- **0** new closed-set vocabularies *outside* those
  pinned in §8 (mandate type / benchmark pressure /
  liquidity need / liability horizon / stewardship
  priority / review frequency / concentration
  tolerance / status / visibility) and §12.1
  (mandate attention bias / mandate review
  context).
- **2** new dataclasses across the v1.25.x
  sequence: `InvestorMandateProfile` (v1.25.1) and
  `InvestorMandateAttentionContext` (v1.25.2).
- **0** or **1** new `RecordType` values:
  `INVESTOR_MANDATE_PROFILE_RECORDED` if convention
  requires (v1.25.1 only; v1.25.2 / .3 / .4 emit
  no new RecordType).
- **1** new ledger event type:
  `investor_mandate_profile_recorded` (only emitted
  when a profile is added; an empty book is
  silent).
- **0** new tabs in the static UI.
- v1.25.1 expected test delta: **+ ~ 14**.
- v1.25.2 expected test delta: **+ ~ 9**.
- v1.25.3 expected test delta: **+ ~ 9**.
- v1.25.4 expected test delta: **+ ~ 8**.
- v1.25.last final test count target: **~ 5031**
  (subject to exact pin at each sub-milestone).

### 15.2 Digest preservation (binding)

Every v1.25.x sub-milestone preserves every
v1.21.last canonical `living_world_digest` byte-
identical. Digest preservation is guaranteed by the
empty-by-default rule: every existing fixture seeds
an empty `InvestorMandateProfileBook`; the empty
book emits no ledger record; therefore no fixture's
record count changes.

---

## 16. Test plan summary (per sub-milestone)

### v1.25.1 — investor mandate storage tests
*(target: ~ 14 new tests)*

1. `test_investor_mandate_profile_validates_required_fields`
2. `test_investor_mandate_profile_rejects_invalid_mandate_type`
3. `test_investor_mandate_profile_rejects_invalid_benchmark_pressure`
4. `test_investor_mandate_profile_rejects_invalid_stewardship_priority_labels`
5. `test_investor_mandate_profile_rejects_duplicate_stewardship_labels`
6. `test_investor_mandate_profile_rejects_forbidden_field_names`
7. `test_investor_mandate_profile_rejects_forbidden_metadata_keys`
8. `test_investor_mandate_profile_book_add_get_list_snapshot`
9. `test_investor_mandate_profile_list_by_investor_and_mandate_type`
10. `test_duplicate_mandate_profile_emits_no_extra_ledger_record`
11. `test_mandate_storage_does_not_mutate_source_of_truth_books`
12. `test_mandate_storage_does_not_call_apply_or_intent_helpers`
13. `test_world_kernel_investor_mandate_profiles_empty_by_default`
14. `test_existing_digests_unchanged_with_empty_mandate_book`

### v1.25.2 — mandate-attention-context tests
*(target: ~ 9 new tests)*

1. `test_mandate_attention_context_is_read_only`
2. `test_mandate_attention_context_emits_no_ledger_record`
3. `test_mandate_attention_context_does_not_mutate_kernel`
4. `test_mandate_attention_context_does_not_call_intent_helpers`
5. `test_mandate_attention_context_bias_labels_in_closed_set`
6. `test_mandate_attention_context_review_context_labels_in_closed_set`
7. `test_mandate_attention_context_no_forbidden_wording`
8. `test_mandate_attention_context_deterministic_across_runs`
9. `test_existing_validation_tests_still_pass_without_mandate`

### v1.25.3 — mandate export + optional UI tests
*(target: ~ 9 new tests)*

1. `test_export_omits_investor_mandate_readout_when_absent`
2. `test_existing_no_mandate_bundle_digest_unchanged`
3. `test_export_includes_investor_mandate_readout_when_present`
4. `test_export_keys_are_descriptive_only`
5. `test_export_carries_no_forbidden_wording`
6. `test_export_does_not_emit_ledger_records`
7. `test_export_does_not_mutate_source_of_truth_books`
8. `test_ui_no_new_tab_added_at_v1_25_3` (if UI shipped)
9. `test_ui_uses_textcontent_only_for_loaded_values` (if UI shipped)

### v1.25.4 — case study tests
*(target: ~ 8 new tests)*

1. `test_mandate_case_study_report_is_deterministic`
2. `test_mandate_case_study_two_archetypes_surface_different_labels`
3. `test_mandate_case_study_does_not_emit_ledger_record`
4. `test_mandate_case_study_does_not_mutate_kernel`
5. `test_mandate_case_study_does_not_call_apply_helpers`
6. `test_mandate_case_study_no_forbidden_wording`
7. `test_mandate_case_study_no_actor_decision_emitted`
8. `test_mandate_case_study_uses_existing_stress_readout_verbatim`

### v1.25.0 / v1.25.last — what ships in tests

**Nothing.** v1.25.0 is docs-only. Test count holds
at 4991 / 4991 at v1.25.0 (and again at v1.25.last
after the v1.25.1-4 increments).

---

## 17. Hard boundary (re-pinned at v1.25.0)

v1.25.0 inherits and re-pins the v1.24.last hard
boundary in full. v1.25.x adds the mandate-specific
prohibitions (§6, §10, §11) on top:

**No real-world output.**
- No price formation. No market price. No order. No
  trade. No execution. No clearing. No settlement.
  No financing execution.
- No forecast / expected return / target price /
  recommendation / investment advice.
- No magnitude / probability / expected response.
- No firm decision / investor action / bank approval
  logic.

**No real-world input.**
- No real data ingestion. No real institutional
  identifiers. No licensed taxonomy dependency. No
  Japan calibration.

**No autonomous reasoning.**
- No LLM execution at runtime. No LLM prose accepted
  as source-of-truth.
- No interaction auto-inference. No aggregate /
  combined / net / dominant / composite stress
  output.
- No auto-annotation (v1.24.0 boundary applies
  verbatim).
- v1.25.x adds: **no portfolio allocation, no
  target weight, no rebalancing, no expected
  return, no tracking-error value, no benchmark
  identifier, no investor action emitted from the
  mandate surface.**

**No source-of-truth book mutation.**
- v1.25.x adds one storage book + one read-only
  readout + one optional export section + one
  optional UI panel + one read-only case study.
  No v1.25.x helper mutates any pre-existing
  kernel book; pre-existing book snapshots remain
  byte-identical pre / post any v1.25.x helper
  call (the only new mutation is the
  `investor_mandate_profile_recorded` ledger
  event, fired exactly once per
  `add_profile(...)` call).

**No backend in the UI.**
- v1.25.3 may touch the static UI mockup; the
  v1.20.5 / v1.22.2 / v1.23.2a / v1.23.2b /
  v1.24.3 loader discipline is preserved. No new
  tab. No new sheet. No backend / fetch / XHR /
  file-system write.

**No digest movement.**
- v1.25.x preserves every v1.21.last canonical
  living-world digest byte-identical at every
  sub-milestone.

---

## 18. Read-in order (for a v1.25 reviewer)

1. [`v1_24_manual_annotation_layer.md`](v1_24_manual_annotation_layer.md)
   §24 "v1.24.last freeze" — the v1.24.last hard
   boundary v1.25 inherits.
2. This document — the v1.25.0 design pin.
3. [`world_model.md`](world_model.md) §134 — the
   constitutional position.
4. [`v1_15_securities_market_intent_aggregation_design.md`](v1_15_securities_market_intent_aggregation_design.md)
   — the v1.15.5 investor-intent layer v1.25
   conditions attention / review context over.
5. [`v1_16_endogenous_market_intent_direction_design.md`](v1_16_endogenous_market_intent_direction_design.md)
   — the v1.16.2 closed-loop attention path v1.25
   may surface mandate context to.

---

## 19. Deliverables for v1.25.0 (this PR)

- This design note:
  `docs/v1_25_institutional_investor_mandate_benchmark_pressure.md`.
- New section §134 in `docs/world_model.md` — "v1.25
  Institutional Investor Mandate / Benchmark
  Pressure (design pointer, **v1.25.0
  design-only**)".
- README §9 roadmap-row refresh — the v1.25 row
  updates from "Optional candidate" to "Design
  scoped at v1.25.0".

No runtime code change. No UI implementation. No new
tests. No new dataclass. No new ledger event. No new
label vocabulary. No digest movement. No record-count
change. No pytest-count change.

---

## 20. Cardinality summary (binding at v1.25.0)

- **0** new dataclasses at v1.25.0 (the
  `InvestorMandateProfile` shape is *designed* here,
  not *implemented*; it lands at v1.25.1).
- **0** new ledger event types at v1.25.0.
- **0** new label vocabularies at v1.25.0 (the
  closed sets in §8 + §12.1 are *designed* here;
  they land at v1.25.1 / v1.25.2).
- **0** new runtime modules at v1.25.0.
- **0** new tests at v1.25.0.
- **0** new UI regions at v1.25.0; **0** new tabs
  at any v1.25.x milestone.
- v1.25.1 expected test delta: **+ ~ 14**.
- v1.25.2 expected test delta: **+ ~ 9**.
- v1.25.3 expected test delta: **+ ~ 9**.
- v1.25.4 expected test delta: **+ ~ 8**.
- v1.25.last final test count target: **~ 5031**.
- v1.21.last canonical digests: **byte-identical
  at every v1.25.x sub-milestone**.

The v1.25 sequence is scoped. Subsequent work that
touches the mandate / benchmark-pressure /
mandate-attention-context layer must explicitly
re-open scope under a new design pin (a v1.25.0a
or later correction); silent extension is forbidden.
