# v1.16 Endogenous Market Intent Feedback — Summary

This document closes the v1.16 sequence of FWE. The sequence
ships the **first closed deterministic endogenous-market-intent
feedback loop** in public FWE: the actor's prior-period
attention focus shapes this period's evidence-conditioned market
intent, the resulting market intent flows through the v1.15
aggregation chain to indicative pressure and the v1.14 corporate
financing review, and the same period's pressure / financing
path then re-shape the *next* period's attention focus. v1.16.last
itself is **docs-only** on top of the v1.16.0 → v1.16.3 code
freezes.

This is **not** an order book, **not** a quote stream, **not** a
match engine, **not** a trade execution layer, **not** a price
formation layer, **not** a clearing or settlement layer, **not**
an issuance / underwriting / pricing layer, **not** a learned
behaviour model, **not** a Japan calibration. It is one new
pure-function classifier module, two new closed-set rule helpers
inside `world/attention_feedback.py`, two new source-id slots on
`ActorAttentionStateRecord`, two new kwargs on
`build_attention_feedback`, five new closed-set focus labels, two
new trigger labels, one classifier-audit metadata block on every
`InvestorMarketIntentRecord`, and the per-period orchestrator
threading that closes the loop. The chain executes nothing.

## Sequence map

| Milestone   | Module / surface                                                                                    | Adds                                                                                                                                                                                                                                                                                                                                                                |
| ----------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.16.0     | docs only                                                                                           | Endogenous market intent direction design (eight-priority rule table over `InvestorIntentRecord.intent_direction` / `ValuationRecord.confidence` / `FirmFinancialStateRecord.market_access_pressure` / `MarketEnvironmentStateRecord.overall_market_access_label` / `ActorAttentionStateRecord.focus_labels`); explicitly out of scope: trade execution, price formation. |
| v1.16.1     | `world/market_intent_classifier.py`                                                                  | `MarketIntentClassificationResult` (frozen dataclass) + `classify_market_intent_direction(...)` pure function. **Runtime-book-free**: imports no source-of-truth book; signature parameter-check rejects `period_idx` / `investor_idx` / `firm_idx`. Eight priority rules, output strictly in `INTENT_DIRECTION_LABELS`. **+100 unit tests.**                          |
| v1.16.2     | `world/reference_living_world.py` (rewire) + `InvestorMarketIntentRecord.metadata` audit block       | Replaces the v1.15.5 four-cycle `(period_idx + investor_idx + firm_idx) % 4` rotation with a per-pair classifier call; resolves classifier inputs from cited records (investor intent / valuation / firm state / market environment / actor attention); records `classifier_version` / `classifier_rule_id` / `classifier_status` / `classifier_confidence` / `classifier_unresolved_or_missing_count` / `classifier_evidence_summary` on every emitted record. **+16 living-world tests.** |
| v1.16.3     | `world/attention_feedback.py` (new labels / triggers / source slots / kwargs / two rule helpers) + `world/reference_living_world.py` (prev-period thread) | Closes the v1.12 → v1.15 attention loop. Five new closed-set focus labels (`risk` / `financing` / `dilution` / `market_interest` / `information_gap`), two new trigger labels, two new source-id slots on `ActorAttentionStateRecord`, two new `build_attention_feedback` kwargs, two pure-function rule helpers. v1.12.9 budget / decay / saturation discipline preserved bit-for-bit. **+34 tests.** |
| v1.16.last  | docs only                                                                                           | This summary, §118 in `docs/world_model.md`, the v1.16.last `RELEASE_CHECKLIST.md` snapshot, the v1.16.last `performance_boundary.md` update, the v1.16.last `test_inventory.md` header note, the v1.16.last addendum in `examples/reference_world/README.md`, and the v1.16.last cross-link in `docs/fwe_reference_demo_design.md`. |

## What v1.16 ships

The final living-world loop is:

```
period N
  ActorAttentionState.focus_labels                        (v1.12.8 + v1.16.3)
        │
        v
  InvestorMarketIntentRecord                              (v1.15.2 — directed by
                                                            v1.16.1 classifier
                                                            from v1.16.2)
        │
        v
  AggregatedMarketInterestRecord                          (v1.15.3)
        │
        v
  IndicativeMarketPressureRecord                          (v1.15.4)
        │
        v
  CapitalStructureReviewCandidate / CorporateFinancingPathRecord
                                                            (v1.14.3 / v1.14.4
                                                             + v1.15.6 citations)
        │
        v
period N+1
  ActorAttentionState.focus_labels widened by              (v1.16.3)
   _classify_market_pressure_focus(...) and
   _classify_financing_path_focus(...) over the
   period-N pressure / path records
        │
        v
  ... back into the v1.16.1 classifier at period N+1
```

The loop is **closed**, **deterministic**, and **replayable**.
The same default-fixture seed produces byte-identical canonical
view, byte-identical `living_world_digest`, and byte-identical
ledger payloads across two consecutive runs.

### v1.16.1 — classifier module

- `world/market_intent_classifier.py` is a **pure-function module**
  with no kernel argument and no runtime-book imports
  (regression-pinned by a text scan over the module source).
- `MarketIntentClassificationResult` (frozen dataclass) carries
  the chosen `intent_direction_label` (∈ `INTENT_DIRECTION_LABELS`,
  = v1.15 `SAFE_INTENT_LABELS ∪ {"unknown"}`), `rule_id`,
  `status` (`evidence_deficient` / `default_fallback` /
  `classified`), synthetic `confidence` ∈ `[0.0, 1.0]`, the
  abstract `evidence_summary` the classifier saw, and
  `unresolved_or_missing_count` ∈ `{0..5}`.
- `classify_market_intent_direction(...)` is the eight-priority
  rule table from the v1.16.0 design — closed-set inputs map
  deterministically to a closed-set output. The forbidden
  trade-instruction verbs (`buy` / `sell` / `order` /
  `target_weight` / `overweight` / `underweight` / `execution`)
  are disjoint from `INTENT_DIRECTION_LABELS` and additionally
  rejected by an explicit `FORBIDDEN_OUTPUT_LABELS` check.
- The signature parameter-check rejects positional indices
  (`period_idx` / `investor_idx` / `firm_idx` / etc.). The
  v1.15.5 four-cycle rotation those indices drove cannot be
  re-introduced through the classifier.

### v1.16.2 — living-world classifier rewire

- `world/reference_living_world.py` removed the v1.15.5
  module-level rotation tables (`_SAFE_INTENT_DIRECTION_BY_ROTATION`,
  `_MARKET_INTENT_INTENSITY_BY_ROTATION`); their absence is
  pinned by a regression test.
- The investor-market-intent phase calls
  `classify_market_intent_direction(...)` once per
  `(investor, firm)` pair per period, resolving the five
  classifier inputs from cited records:
  `kernel.investor_intents.get_intent(...).intent_direction`,
  `kernel.valuations.get_valuation(...).confidence`,
  `kernel.firm_financial_states.get_state(...).market_access_pressure`,
  `kernel.market_environments.get_state(...).overall_market_access_label`,
  `kernel.attention_feedback.get_attention_state(...).focus_labels`.
- The record's `intent_direction_label`, `intensity_label`, and
  `confidence` are now classifier-derived (no more hardcoded
  `0.5`); a deterministic helper
  `_intensity_label_for_classifier_confidence(...)` maps
  `(status, confidence)` → `INTENSITY_LABELS`.
- Every emitted `InvestorMarketIntentRecord.metadata` carries a
  compact classifier-audit block (`classifier_version` /
  `classifier_rule_id` / `classifier_status` /
  `classifier_confidence` / `classifier_unresolved_or_missing_count` /
  `classifier_evidence_summary`).

### v1.16.3 — securities-market pressure → next-period attention feedback

- `world/attention_feedback.py` adds five closed-set focus labels
  to `ALL_FOCUS_LABELS`: `risk`, `financing`, `dilution`,
  `market_interest`, `information_gap`. Two new trigger labels:
  `market_pressure_observed`, `financing_path_observed`.
- `ActorAttentionStateRecord` gains two plain-id source-tuple
  slots — `source_indicative_market_pressure_ids` and
  `source_corporate_financing_path_ids` — populated, validated,
  serialised on `to_dict`, and emitted on the
  `attention_state_created` ledger payload.
- `build_attention_feedback(...)` accepts two new kwargs
  (`indicative_market_pressure_ids` /
  `corporate_financing_path_ids`) and resolves them via the
  cited-id-only discipline (no global scan; unresolved ids
  silently tolerated).
- Two new closed-set rule helpers map cited records to fresh
  focus labels:
  - `_classify_market_pressure_focus(...)` —
    `market_access_label ∈ {constrained, closed}` →
    `market_access` + `funding` + `risk`;
    `financing_relevance_label = adverse_for_market_access` →
    `market_access` + `financing` + `risk`;
    `financing_relevance_label = caution_for_dilution` →
    `valuation` + `dilution` + `financing`;
    `liquidity_pressure_label ∈ {tight, stressed}` →
    `liquidity` + `funding`;
    `demand_pressure_label = supportive` →
    `market_interest` + `valuation`;
    `insufficient_observations` on demand / financing / status →
    `information_gap`.
  - `_classify_financing_path_focus(...)` —
    `coherence_label = conflicting_evidence` →
    `information_gap` + `financing`;
    `constraint_label = market_access_constraint` →
    `market_access` + `financing`;
    `next_review_label = compare_options` →
    `financing` + `valuation`.
- The v1.16.3 fresh focus set is **unioned into the v1.12.8
  fresh focus set before** the v1.12.9 decay / saturation
  pipeline runs, so the budget discipline holds bit-for-bit;
  pressure-driven labels can crowd out stale prior focus when
  the `_MAX_FOCUS_LABELS` cap is reached. A dedicated test pins
  this crowd-out.
- The orchestrator carries the previous period's pressure /
  path ids forward into the next period's attention build for
  both investors and banks. Period 0 has empty source slots (no
  prior period exists); periods 1+ cite the previous period's
  full pressure / path id sets.

## What v1.16 explicitly is not

- **Not a probabilistic classifier.** No softmax, no logistic
  regression, no random forest, no neural network, no LLM, no
  calibrated probability output. Every rule is a Boolean
  combination of closed-set / bounded-numeric inputs.
- **Not a behaviour predictor.** The classifier produces a
  *review-posture label*, not a forecast of what the investor
  will do. The v1.15 `SAFE_INTENT_LABELS` vocabulary is
  deliberately phrased to make this distinction structural.
- **Not a learned model.** No training data, no gradient, no
  fitting, no cross-validation, no backtest. The classifier is
  hand-written and audited.
- **Not order submission.** No `OrderSubmittedRecord`, no
  `order_submitted` event, no quantity, no notional, no side,
  no order id flowing from any record.
- **Not order matching.** No order book, no bid / ask / mid /
  spread, no match engine, no fill report, no execution notice.
- **Not trade execution.** No trade record, no clearing, no
  settlement (the v1.13 settlement substrate covers
  central-bank-shaped settlement labels — not trade-level
  execution).
- **Not real exchange mechanics.** No tick size, no lot size,
  no auction schedule, no halt rule, no circuit breaker, no
  reference-rate setting.
- **Not real price formation.** No price, no quote, no
  benchmark fixing, no NAV, no index level, no last-trade. The
  `PriceBook` is byte-equal across the full default sweep —
  pinned by tests at v1.15.5, v1.15.6, v1.16.2, and v1.16.3.
- **Not target prices, expected returns, or recommendations.**
  The classifier output set is closed; the forbidden trade-
  instruction verbs are disjoint from it.
- **Not financing execution.** No loan approval, no bond /
  equity issuance, no underwriting, no syndication, no
  bookbuilding, no allocation, no commitment, no pricing, no
  interest rate, no spread, no coupon, no fee, no offering
  price.
- **Not stochastic behaviour learning.** The attention-focus
  widening from prior-period pressure / path is a pure
  deterministic mapping (closed-set in → closed-set out) —
  not a Bayesian update, not an RL policy, not a learned
  attention head.
- **Not a real-data layer.** Every numeric value is a synthetic
  illustrative scalar; every id uses the `*_reference_*`
  synthetic naming convention; no real-system identifier (real
  exchange, broker, ticker, ISIN, CUSIP, SEDOL, regulator, or
  market data vendor) appears in any v1.16 module, fixture, or
  test.
- **Not a Japan calibration.** All venue ids, security ids, and
  labels are jurisdiction-neutral and synthetic. Real-venue
  calibration (JPX / TSE / OSE / NEX / etc.) is private JFWE
  territory (v2 / v3 only).

## Performance boundary at v1.16.last

- **Per-period record count (default fixture):** **108** (period
  0) / **110** (periods 1+). **Unchanged** from v1.15.6 /
  v1.16.1 / v1.16.2 / v1.16.3. v1.16.x added **no new records** —
  all changes are payload bytes (the classifier-audit metadata
  block in v1.16.2 and the two new attention-state source-id
  slots in v1.16.3).
- **Per-run window (default fixture):** **`[432, 480]`**.
  **Unchanged** from v1.15.6.
- **Default 4-period sweep total:** **460 records**.
  **Unchanged**.
- **Integration-test `living_world_digest`:**
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**.
  The digest moved twice in the v1.16 sequence — at v1.16.2
  (rotation → classifier; new classifier-audit metadata bytes
  on every `InvestorMarketIntentRecord`) and again at v1.16.3
  (new source-id slots and label widenings on every period-1+
  `ActorAttentionStateRecord`). v1.16.0 (docs-only) and v1.16.1
  (pure-function module — no living-world wiring) left the
  digest byte-identical.
- **Test count:** **4033 / 4033** passing. Up from 3883 / 3883
  at v1.15.last (+150 across v1.16.1 → v1.16.3).
- The v1.16 changes are bounded `O(P × I × F)` for the per-pair
  classifier call and `O(P × (I + B))` for the per-actor
  attention build — exactly the loop shapes already used by
  v1.15.5 and v1.12.8. No new dense shape was introduced.

## Discipline preserved bit-for-bit

Every v1.9.x / v1.10.x / v1.11.x / v1.12.x / v1.13.x / v1.14.x /
v1.15.x boundary anti-claim is preserved unchanged at v1.16.last:

- No real data, no Japan calibration, no LLM-agent execution,
  no behaviour probability.
- No price formation, no trading, no portfolio allocation, no
  investment advice, no rating.
- No lending decision, no covenant enforcement, no contract
  mutation, no constraint mutation, no default declaration.
- No financing execution, no loan approval, no securities
  issuance, no underwriting, no syndication, no allocation, no
  pricing.
- The v1.12.6 watch-label classifier is unchanged.
- The v1.12.9 attention-budget discipline (per-dimension budget
  / decay horizon / saturation policy / `_MAX_FOCUS_LABELS`) is
  preserved bit-for-bit; v1.16.3 fresh focus passes through the
  same decay / saturation pipeline.
- The v1.13.5 settlement / interbank-liquidity substrate is
  unchanged.
- The v1.14 corporate-financing record set is unchanged in
  vocabulary; v1.15.6 added two **citation** slots, and v1.16.x
  added zero new vocabulary or new records.
- The v1.15 `SAFE_INTENT_LABELS` vocabulary is unchanged.
  v1.16.1 only adds `"unknown"` (already in
  `INTENT_DIRECTION_LABELS`); v1.16.2 / v1.16.3 add no new
  vocabulary on the v1.15 surface.
- The `PriceBook` is byte-equal across the full default sweep —
  pinned by tests at every v1.15 / v1.16 milestone.
- The v1.9.last public-prototype freeze, the v1.12.last
  attention-loop freeze, the v1.13.last settlement-substrate
  freeze, the v1.14.last corporate-financing-intent freeze, the
  v1.15.last securities-market-intent freeze, and the v1.8.0
  public release remain untouched.

## Known limitations

The v1.16 layer is **deterministic and rule-based**. It is **not
learned from real market behaviour**, **not calibrated** against
any real-world dataset, and **does not claim predictive
validity**. The value of the v1.16 surface is:

1. **Auditability.** Every `intent_direction_label` is justified
   by a single named priority rule (`priority_1_*` …
   `priority_8_*`); every `focus_labels` widening cites the
   prior-period record id that triggered it. A reviewer can
   trace any label back through the cited evidence in finite
   read steps.
2. **Replayable causal structure.** The same seed produces
   byte-identical loop output across runs. The default-fixture
   `living_world_digest` is pinned and any drift fails a test.
3. **Composable closed-set vocabularies.** Adding a v1.17+ layer
   on top is a matter of registering plain-id citation slots —
   never re-modelling the upstream layers.

What the v1.16 layer is *not* useful for:

- predicting any specific actor's actual decision in any
  specific real market;
- estimating any calibrated probability of any real outcome;
- computing any real-world price, return, exposure, or risk
  metric;
- ranking real-world securities, sectors, or markets;
- generating real-world investment recommendations.

The classifier rule table is **illustrative only** — its job is
to make the loop's causal structure inspectable, not to be
correct against ground truth. Future calibration, if ever
attempted, would happen in private JFWE (v2 / v3) and would
**replace** the rule table with a separate audited surface, not
mutate the public-FWE one.

## What v1.17+ does next

v1.16.last freezes the public-FWE endogenous market-intent
feedback layer. The next roadmap candidates are:

- **v1.17 — UI / report / regime-comparison polish.** The
  workbench prototype in `examples/ui/` should expose the v1.16
  loop as a first-class view: per-period attention focus,
  market intent direction + classifier rule id, aggregated
  market interest, indicative market pressure, financing path
  outcome, and the next-period attention focus widening. The
  CLI `--regime` flag (v1.11.2) makes regime-comparison reports
  trivial; v1.17 lifts those into a side-by-side report and a
  static HTML view.
- **v1.18 — scenario library / exogenous event templates.** A
  small library of named, deterministic, reproducible scenario
  templates (e.g. `tightening_credit`, `equity_correction`,
  `liquidity_event`, `dialogue_breakdown`) that compose with
  the existing `--regime` presets to produce labelled
  cross-scenario reports. Still no real-data, no calibration.
- **v2.0 — Japan public calibration in private JFWE.** Real-
  venue / real-issuer / real-regulator calibration moves to
  private JFWE only. Public FWE remains jurisdiction-neutral
  and synthetic.
- **Future price formation.** Out of scope until the v1.16
  market-intent feedback layer is **easier to inspect** —
  i.e., until the v1.17 workbench / scenario library make the
  loop's causal structure operationally legible to a reviewer
  who has not read this document. Adding price formation on
  top of an opaque layer would defeat the auditability goal of
  the v1.16 freeze.

The v1.16 chain stays bounded and label-only forever. Future
milestones may *cite* the v1.16 records (plain-id cross-
references, additional citation slots), but they may **never**
mutate the v1.16 vocabulary, replace the deterministic rule
helpers with stochastic ones, or introduce execution paths on
top of the closed loop.
