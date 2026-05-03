# v1.16.0 Endogenous Market Intent Direction — Design Note

**Status:** Docs-only design. No code, no tests, no
`living_world_digest` change. v1.15.last is the most recent
shipped freeze; v1.16.0 begins the next sequence by **describing
how to replace the v1.15.5 deterministic four-cycle rotation for
`InvestorMarketIntentRecord.intent_direction_label` with an
evidence-conditioned classifier** without implementing any of
it.

## Purpose

v1.15.5's living-world integration sets each
`InvestorMarketIntentRecord.intent_direction_label` via:

```python
intent_direction = SAFE_INTENT_LABELS_BY_ROTATION[
    (period_idx + investor_idx + firm_idx) % 4
]
```

This is **acceptable for bounded demo diversity** (the per-period
histogram is non-trivial, the rotation is deterministic, and the
safe-label vocabulary is preserved) but it is **not yet
endogenous in the v1.12 sense**. The rotation cycles through four
values regardless of what the upstream evidence actually says —
two investors looking at the same security under wildly different
market conditions can end up with the *same* `intent_direction`
just because their `(period_idx + investor_idx + firm_idx)`
modulus collides.

v1.16 ships, *as a deterministic, label-only, replayable
classifier*, the missing endogeneity:

```
investor intent direction (v1.12.1)
valuation confidence (v1.9.5 / v1.12.5)
firm market_access_pressure (v1.12.0)
market environment overall_market_access_regime_label (v1.12.2)
actor attention focus_labels (v1.12.8)
        |
        v
intent_direction_label  ∈  SAFE_INTENT_LABELS ∪ {"unknown"}
intensity_label         ∈  {low, moderate, elevated, high, unknown}
```

The motivation is the same as the v1.12 endogenous attention loop,
the v1.14 corporate-financing chain, and the v1.15 securities
aggregation chain: **make a previously rotation-driven label a
function of the cited evidence**, without introducing
probabilistic behavior, calibrated decisions, or any execution
path. v1.16 replaces a *position* with a *cause*.

## Two-line success condition

> The same `(investor, security)` pair can produce **different**
> safe market-interest labels because the evidence context
> differs, **not** because of index rotation.

Stated negatively: if you change `period_idx` while holding all
upstream evidence fixed, the classifier must return the **same**
label. If you change the upstream evidence while holding
`period_idx` fixed, the classifier may return a different label.
This invariant is the v1.16 acceptance test.

## Five evidence sources

v1.16 introduces no new record types — every evidence input is
already on the kernel. The classifier reads only the **cited**
ids (no global scan), in the v1.12.3 `EvidenceResolver` /
v1.14.4 / v1.15.3 / v1.15.4 helper-discipline tradition.

### 1. `InvestorIntentRecord.intent_direction` (v1.12.1)

Per-investor / per-firm review-posture direction. Closed-set
values:

```
routine
request_dialogue
deepen_due_diligence
risk_flag_watch
engagement_watch
escalation_pending
unknown
```

This is the strongest single signal — it is *the same actor's*
firm-level review posture, and the v1.16 classifier produces a
*security-level* version of essentially the same posture for the
firm's listed equity. The classifier should treat
`investor_intent_direction` as the dominant axis and let the
other four sources adjust it.

### 2. `ValuationRecord.confidence` (v1.9.5 / v1.12.5)

`[0.0, 1.0]` synthetic ordering on how strongly the cited
valuation evidence supports the implied estimate. Low
confidence (e.g., `< 0.4`) under stressed market environment
should tilt market intent defensive (`reduce_interest` /
`risk_reduction_review`); high confidence (e.g., `>= 0.6`) under
constructive environment should tilt it constructive
(`increase_interest`). When multiple `(investor, firm)`
valuations are cited, the classifier should aggregate
deterministically (e.g., minimum confidence, or pessimistic
average — this design proposes **minimum** for clarity; the
classifier module will pin the choice in tests).

### 3. `FirmFinancialStateRecord.market_access_pressure` (v1.12.0)

`[0.0, 1.0]` synthetic latent scalar describing the firm's
operating-pressure on the market-access axis. High pressure
(e.g., `>= 0.7`) tilts the classifier defensive even when the
investor's own intent is routine.

### 4. `MarketEnvironmentStateRecord.overall_market_access_regime_label` (v1.12.2)

Closed-set environment label:

```
open_or_constructive
selective
constrained
closed
unknown
```

This is the *macro* axis. A `closed` environment should not
produce `increase_interest` even if the investor's micro
evidence is supportive. A `constrained` environment combined
with high firm pressure should escalate toward
`risk_reduction_review` or `liquidity_watch`. The labels are
identical to the v1.14.3 `CapitalStructureReviewCandidate` and
v1.15.4 `IndicativeMarketPressureRecord` `market_access_label`
vocabulary; the classifier reuses this set so the v1.16 layer
composes cleanly with the v1.14 and v1.15 chains.

### 5. `ActorAttentionStateRecord.focus_labels` (v1.12.8)

Tuple of closed-set focus labels the actor is attending to in
the current period. The v1.12.8 vocabulary includes (among
others):

- `dialogue` / `engagement` / `escalation` (engagement-themed)
- `firm_state` / `valuation` (firm-themed)
- `market_environment` / `market_condition` / `funding` /
  `liquidity` (market / macro-themed)

Focus labels modulate the classifier's tilt:

- `engagement` / `dialogue` / `stewardship` focus + investor
  intent `engagement_watch` → `engagement_linked_review`.
- `liquidity` / `funding` focus + constrained environment →
  `liquidity_watch`.
- `firm_state` / `valuation` focus + no strong directional
  signal → `rebalance_review`.

The `prior_attention_state_id` (v1.12.8 chain pointer) gives
the classifier optional access to the *previous* period's focus
labels — this lets the classifier preserve a defensive posture
across periods when the actor's focus stays on
`risk` / `escalation` axes.

## Output vocabulary

The classifier returns labels from the **existing v1.15
`SAFE_INTENT_LABELS` set ∪ `{"unknown"}`**. No new labels.

```
increase_interest
reduce_interest
hold_review
liquidity_watch
rebalance_review
risk_reduction_review
engagement_linked_review
unknown
```

The forbidden trading verbs (`buy`, `sell`, `order`,
`target_weight`, `overweight`, `underweight`, `execution`)
remain **rejected by closed-set membership** at the
`InvestorMarketIntentRecord` construction layer; the classifier
cannot return them because they are not in the closed set.

The classifier may also return an `intensity_label` value over
the existing v1.15.2 closed set (`low` / `moderate` / `elevated`
/ `high` / `unknown`); the rules below propose deterministic
intensity scoring from the same evidence.

The classifier does **not** modify the v1.15.2 record's
`horizon_label` — the v1.15.5 default `near_term` is preserved
in v1.16.1 (a future v1.16.x can extend if useful).

## Deterministic classification rules

The rule table is **priority-ordered** — first matching rule
wins. Each rule is a small deterministic predicate over the
cited evidence. The priority order encodes a defensible
hierarchy (severe risk and engagement signals dominate over
routine market-tilt signals).

Notation:

- `II.dir` = aggregated `InvestorIntent.intent_direction` for
  this `(investor, firm)` (defaults to `unknown` when no
  intent is cited).
- `Val.conf` = aggregated `Valuation.confidence` (default
  rule: minimum across cited; `None` when no valuation cited).
- `FS.access` = `FirmFinancialState.market_access_pressure`
  (`None` when no firm-state cited).
- `MES.access` = `MarketEnvironmentState.overall_market_access_regime_label`
  (`unknown` when no MES cited).
- `Foc` = set of `ActorAttentionState.focus_labels` for this
  actor (`set()` when no attention state cited).

### Priority 1 — evidence-deficient

If **all** of `II.dir`, `Val.conf`, `FS.access`, `MES.access`,
and `Foc` are absent or `unknown`:

```
intent_direction_label = "unknown"
intensity_label        = "unknown"
```

### Priority 2 — engagement-linked review

If `II.dir == "engagement_watch"` **and** `Foc` intersects
`{engagement, dialogue, stewardship_theme}`:

```
intent_direction_label = "engagement_linked_review"
intensity_label        = "moderate"
```

### Priority 3 — risk-reduction review

If `II.dir == "risk_flag_watch"`:

```
intent_direction_label = "risk_reduction_review"
intensity_label        = "elevated"  if FS.access >= 0.7 else "moderate"
```

If `II.dir == "deepen_due_diligence"` **and** (`FS.access >= 0.7`
**or** `MES.access in {constrained, closed}`):

```
intent_direction_label = "risk_reduction_review"
intensity_label        = "high" if MES.access == "closed" else "elevated"
```

### Priority 4 — liquidity watch

If `Foc` intersects `{liquidity, funding}` **and** `MES.access`
∈ `{selective, constrained, closed}`:

```
intent_direction_label = "liquidity_watch"
intensity_label        = "high" if MES.access == "closed" else "elevated"
```

If `FS.access >= 0.7` **and** `Foc` intersects
`{liquidity, funding}`:

```
intent_direction_label = "liquidity_watch"
intensity_label        = "elevated"
```

### Priority 5 — reduce interest

If `Val.conf < 0.4` **and** `MES.access ∈ {constrained, closed}`:

```
intent_direction_label = "reduce_interest"
intensity_label        = "high" if MES.access == "closed" else "elevated"
```

If `II.dir == "deepen_due_diligence"` **and** `Val.conf < 0.5`
**and** `FS.access >= 0.5`:

```
intent_direction_label = "reduce_interest"
intensity_label        = "moderate"
```

### Priority 6 — increase interest

If `Val.conf >= 0.6` **and** `FS.access < 0.4` **and**
`MES.access == "open_or_constructive"` **and**
`II.dir ∈ {routine, engagement_watch}`:

```
intent_direction_label = "increase_interest"
intensity_label        = "moderate" if Val.conf < 0.8 else "elevated"
```

### Priority 7 — rebalance review

If `Foc` intersects `{firm_state, valuation, market_environment}`
**and** no rule above fires:

```
intent_direction_label = "rebalance_review"
intensity_label        = "moderate"
```

### Priority 8 — default

```
intent_direction_label = "hold_review"
intensity_label        = "low"
```

The eight priorities map exactly onto the eight values in
`SAFE_INTENT_LABELS ∪ {unknown}`, plus a default of `hold_review`
for "we have some evidence but no rule fires." Every rule is a
deterministic boolean over closed-set / bounded-numeric inputs;
no rule reads a calibrated probability or a stochastic shock.

## Evidence discipline

The classifier follows the v1.12.3 `EvidenceResolver` /
v1.14.4 / v1.15.3 / v1.15.4 helper discipline verbatim:

- **Cited-ids only.** The classifier reads only the explicitly
  cited ids via the kernel's `get_*` accessors. It never calls
  `list_*` or `snapshot` on any source-of-truth book. v1.16.1
  will pin this with a trip-wire test that monkey-patches every
  `list_*` and `snapshot` on the cited books.
- **Unresolved → degrade.** Any cited id that fails to resolve
  is silently skipped during evidence extraction; the count is
  recorded in the returned record's `metadata` under
  `unresolved_<bucket>_count`. If the evidence-deficient rule
  trips after unresolved drops, the classifier returns
  `unknown` (severe deficit) or `hold_review` (some evidence
  remained but no directional rule fires).
- **No mutation.** The classifier writes nothing. It returns
  a `(intent_direction_label, intensity_label)` tuple plus
  derived metadata. The v1.15.5 phase consumes the return
  value and constructs the `InvestorMarketIntentRecord` as
  before — no other source-of-truth book is touched.
- **Replay-stable.** Two consecutive runs over the same fixture
  must produce byte-identical classifier outputs. v1.16.1 will
  pin this with a determinism test on a fresh kernel pair.

The v1.12.3 `EvidenceResolver` may be reused as the *resolution
layer*: callers can pass an `ActorContextFrame` and the
classifier reads its already-resolved `resolved_*_ids` buckets.
v1.16.1 will decide whether to take an `ActorContextFrame`
directly or accept the cited-id tuples and wrap the resolver
internally — both are clean designs; the test surface is the
same.

## Per-milestone roadmap inside v1.16

| Milestone     | What                                                                                                                                   | Status                  |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| v1.16.0       | Endogenous market intent direction design (this document)                                                                              | Shipped (docs-only)     |
| v1.16.1       | `world/market_intent_classifier.py` — `MarketIntentClassificationResult` + `classify_market_intent_direction(...)` pure function + 100 unit tests; runtime-book-free; signature rejects `period_idx` / `investor_idx` / `firm_idx` | Shipped                 |
| **v1.16.2**   | **Living-world classifier rewire** — replaces the v1.15.5 four-cycle `(period_idx + investor_idx + firm_idx) % 4` rotation in `world/reference_living_world.py` with a per-pair call into `classify_market_intent_direction(...)`; resolves classifier inputs from cited records (investor intent, valuation, firm financial state, market environment, actor attention); `InvestorMarketIntentRecord.metadata` now carries a classifier-audit block (`classifier_version` / `classifier_rule_id` / `classifier_status` / `classifier_confidence` / `classifier_unresolved_or_missing_count` / `classifier_evidence_summary`); `living_world_digest` moves to `0b75e95ad8f157df5e938c1318817c07f00798179c3d11b8629452d30d9398fa` by design (label / metadata bytes only — record count and per-run window unchanged); +16 tests | **Shipped**             |
| v1.16.3       | Wire the classifier into the v1.12.8 attention-feedback loop so the actor's prior-period focus labels feed the next period's classification (closes the v1.12 → v1.15 loop) | Planned                 |
| v1.16.last    | Endogenous market intent direction freeze (docs-only)                                                                                  | Planned                 |

The v1.16 sequence preserves the v1.x storage-first / labels-only
discipline. Each milestone ships one small deterministic
addition, passes a closed-set + safe-label test, passes the
forbidden-label / forbidden-payload-key scan, and integrates
into the living world only at v1.16.2. The v1.16.0 design itself
ships nothing executable — `living_world_digest` is unchanged
from v1.15.last (`bd7abdb9a62fb93a1001d3f760b76b3ab4a361313c3af936c8b860f5ab58baf8`).

## What v1.16 explicitly is not

- **Not a probabilistic classifier.** No softmax, no logistic
  regression, no random forest, no neural network, no LLM, no
  calibrated probability output. Every rule is a Boolean
  combination of closed-set / bounded-numeric inputs, and the
  classifier is a pure function from evidence to label.
- **Not a behaviour predictor.** The classifier produces a
  *review-posture label*, not a forecast of what the investor
  will do. The v1.15 `SAFE_INTENT_LABELS` vocabulary is
  deliberately phrased to make this distinction structural.
- **Not an order generator.** The forbidden trading verbs
  (`buy` / `sell` / `order` / `target_weight` / `overweight`
  / `underweight` / `execution`) cannot appear in the
  classifier's output by closed-set membership.
- **Not a price-formation layer.** The `PriceBook` is byte-
  equal across the full default sweep — pinned by tests at
  v1.15.5 / v1.15.6 and inherited by v1.16.x.
- **Not an investment-advice layer.** The classifier reads
  upstream evidence and returns a posture label; it does not
  make a recommendation on behalf of any actor.
- **Not a calibrated risk model.** No PD, LGD, EAD, default
  probability, behaviour probability, or stochastic decay.
- **Not a real-data layer.** Every numeric value is a synthetic
  illustrative scalar; every id uses the `*_reference_*`
  synthetic naming convention.
- **Not a Japan calibration.** All vocabularies, thresholds, and
  evidence sources are jurisdiction-neutral and synthetic.
  Real-jurisdiction calibration is private JFWE territory (v2 /
  v3 only).

## Boundary recap

This is **endogenous market-interest direction classification,
not market trading.** It produces audit-grade review-posture
labels from cited evidence, not orders or prices. Every v1.9.x /
v1.10.x / v1.11.x / v1.12.x / v1.13.x / v1.14.x / v1.15.x
anti-claim is preserved unchanged. The v1.9.last public-prototype
freeze, the v1.12.last attention-loop freeze, the v1.13.last
settlement-substrate freeze, the v1.14.last corporate-financing-
intent freeze, the v1.15.last securities-market-intent
aggregation freeze, and the v1.8.0 public release remain
untouched.
