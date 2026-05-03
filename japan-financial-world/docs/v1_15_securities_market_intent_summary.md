# v1.15 Securities Market Intent Aggregation — Summary

This document closes the v1.15 sequence of FWE. The sequence
ships a **jurisdiction-neutral, label-only, synthetic** securities-
market-interest aggregation layer plus a feedback loop into the
v1.14 corporate-financing chain. v1.15.last itself is docs-only on
top of the v1.15.1 → v1.15.6 code freezes.

This is **not** an order book, **not** a quote stream, **not** a
match engine, **not** a trade execution layer, **not** a price
formation layer, **not** a clearing or settlement layer, **not**
an issuance / underwriting / pricing layer, **not** a Japan
calibration. It is a small set of immutable record types, four
append-only books, two deterministic helpers, five ledger event
types, one bounded per-period synthesis phase, and one
deterministic feedback path. The chain executes nothing.

## Sequence map

| Milestone   | Module / surface                                         | Adds                                                                                                                                                                                                                          |
| ----------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.15.0     | docs only                                                | Securities-market-intent design vocabulary; explicitly out of scope: order submission, matching, execution, clearing, settlement, quote dissemination, price formation, target price, recommendation, investment advice.       |
| v1.15.1     | `world/securities.py`                                    | `ListedSecurityRecord` + `MarketVenueRecord` + `SecurityMarketBook`. Two ledger events. Eight closed-set label axes. Storage only.                                                                                              |
| v1.15.2     | `world/market_intents.py`                                | `InvestorMarketIntentRecord` + `InvestorMarketIntentBook`. Ledger event `investor_market_intent_recorded`. Four closed-set label fields. **Naming amendment** — "market intent" not "trading intent". Storage only.            |
| v1.15.3     | `world/market_interest.py`                               | `AggregatedMarketInterestRecord` + `AggregatedMarketInterestBook` + `build_aggregated_market_interest` deterministic helper. Per-venue / per-security count + label aggregation.                                                |
| v1.15.4     | `world/market_pressure.py`                               | `IndicativeMarketPressureRecord` + `IndicativeMarketPressureBook` + `build_indicative_market_pressure` deterministic helper. Reuses v1.14.3 `MARKET_ACCESS_LABELS` (`is`-identity pin) so the two layers compose cleanly.       |
| v1.15.5     | `world/reference_living_world.py` (per-period sweep)     | First living-world integration: setup-once 1 venue + `F` securities; per period `I × F` market intents + `F` aggregated-interest + `F` indicative-pressure records.                                                             |
| v1.15.6     | `world/capital_structure.py` + `world/financing_paths.py` (citation slots + helper override) + `world/reference_living_world.py` (phase reorder + label drift) | Feedback wiring — capital-structure review and financing path now cite `IndicativeMarketPressureRecord` ids; helper overrides constraint / coherence; orchestrator overrides review's `market_access_label` and `dilution_concern_label` when pressure pushes. |
| v1.15.last  | docs only                                                | This summary, §113 in `docs/world_model.md`, `RELEASE_CHECKLIST.md` snapshot, `performance_boundary.md` update, `README.md` headline.                                                                                            |

## What v1.15 ships

The final living-world chain is:

```
investor intent (v1.12.1)
valuation (v1.9.5 / v1.12.5)
firm financial state (v1.12.0)
market environment state (v1.12.2)
        |
        v
InvestorMarketIntentRecord       (v1.15.2 — per investor / security)
        |
        v
AggregatedMarketInterestRecord   (v1.15.3 — per venue / security)
        |
        v
IndicativeMarketPressureRecord   (v1.15.4 — per security)
        |
        v
CapitalStructureReviewCandidate  (v1.14.3, citation slot added at v1.15.6)
CorporateFinancingPathRecord     (v1.14.4, citation slot added at v1.15.6)
```

- **Records:** five new immutable-dataclass record types
  (`ListedSecurityRecord`, `MarketVenueRecord`,
  `InvestorMarketIntentRecord`, `AggregatedMarketInterestRecord`,
  `IndicativeMarketPressureRecord`) — all carrying closed-set-
  enforced label fields, optional `[0,1]` synthetic confidence
  (booleans rejected), and plain-id source-reference tuples.
  Plus two new citation slots added at v1.15.6 to existing
  v1.14.3 / v1.14.4 records.
- **Books:** four new append-only books wired into `WorldKernel`:
  `security_market`, `investor_market_intents`,
  `aggregated_market_interest`, `indicative_market_pressure`.
  Each book emits exactly one ledger record per add call and
  refuses to mutate any other source-of-truth book — including
  the `PriceBook`.
- **Ledger events:** five new record types
  (`listed_security_registered`, `market_venue_registered`,
  `investor_market_intent_recorded`,
  `aggregated_market_interest_recorded`,
  `indicative_market_pressure_recorded`).
- **Closed-set vocabularies:** *eight* label axes total on the
  v1.15.1 surface (security-side: `security_type` / `listing_status`
  / `issue_profile` / `liquidity_profile` / `investor_access`;
  venue-side: `venue_type` / `venue_role` / `status`); *four* label
  axes on the v1.15.2 record (`intent_direction` / `intensity` /
  `horizon` / `status`); *four* label axes on the v1.15.3 record
  (`net_interest` / `liquidity_interest` / `concentration` /
  `status`); *six* label axes on the v1.15.4 record
  (`demand_pressure` / `liquidity_pressure` /
  `volatility_pressure` / `market_access` / `financing_relevance`
  / `status`). Vocabulary alignment with v1.14.3
  `CapitalStructureReviewCandidate.MARKET_ACCESS_LABELS` is
  pinned by an `is`-identity test in v1.15.4.
- **Safe-only intent vocabulary:** the v1.15 `SAFE_INTENT_LABELS`
  set (`increase_interest` / `reduce_interest` / `hold_review` /
  `liquidity_watch` / `rebalance_review` /
  `risk_reduction_review` / `engagement_linked_review`) is the
  binding boundary against trade-instruction language. The
  forbidden trading verbs (`buy` / `sell` / `order` /
  `target_weight` / `overweight` / `underweight` / `execution`)
  are rejected by closed-set membership at construction across
  v1.15.1's `MarketVenueRecord.supported_intent_labels` and
  v1.15.2's `InvestorMarketIntentRecord.intent_direction_label`.
- **Deterministic helpers (v1.15.3 / v1.15.4):** both helpers
  read only the cited ids via `get_*` calls and never iterate
  the cited books globally — pinned by trip-wire tests that
  monkey-patch every `list_*` and `snapshot` on the cited
  books. Both helpers record `mismatched_security_id_count` /
  `unresolved_*_count` in metadata for deterministic mismatch
  / miss accounting.
- **Living-world integration (v1.15.5):** the chain runs once
  per firm per period after the v1.12.8 attention-feedback
  phase. Setup-once: 1 venue + `F` securities. Per period:
  `I × F` market intents + `F` aggregated-interest + `F`
  pressure records. Bounded by `P × I × F + 2 × P × F` per
  layer — never `P × I × F × venue` or
  `P × I × F × option_count`.
- **Feedback wiring (v1.15.6):** capital-structure review and
  financing path each gain one citation slot for
  `IndicativeMarketPressureRecord` ids. The
  `build_corporate_financing_path` helper gains an
  `indicative_market_pressure_ids` kwarg with two override
  rules (constraint → `market_access_constraint`; coherence →
  `conflicting_evidence` when pressure and reviews disagree).
  The orchestrator additionally overrides the review's
  `market_access_label` and `dilution_concern_label` when
  pressure pushes. The v1.15.5 securities-market chain phase is
  reordered to run *before* the v1.14.5 financing chain phase
  so each firm's review and path can cite the same period's
  pressure record.

## What v1.15 explicitly is not

- **Not order submission.** No `OrderSubmittedRecord`, no
  `order_submitted` event, no quantity, no notional, no side,
  no order id flowing from any record.
- **Not order matching.** No order book, no bid / ask / mid /
  spread, no match engine, no fill report, no execution notice.
- **Not trade execution.** No trade record, no clearing, no
  settlement (the v1.13 settlement substrate covers
  central-bank-shaped settlement labels — not trade-level
  execution).
- **Not real exchange mechanics.** No tick size, no lot size, no
  auction schedule, no halt rule, no circuit breaker, no
  reference-rate setting.
- **Not real price formation.** No price, no quote, no benchmark
  fixing, no NAV, no index level, no last-trade. The
  `PriceBook` is byte-equal across the full default sweep —
  pinned by a dedicated `test_v1_15_5_does_not_mutate_pricebook`
  test and a v1.15.6-extension that pins the same invariant
  through the helper.
- **Not target prices, expected returns, or recommendations.**
  The vocabulary is deliberately phrased to make a
  market-intent-as-recommendation reading impossible.
- **Not financing execution.** No loan approval, no bond / equity
  issuance, no underwriting, no syndication, no bookbuilding, no
  allocation, no commitment. v1.15.6 only adds citation slots
  and label-drift rules; it does not introduce any execution
  path.
- **Not investment advice.** Direct ("buy X") or indirect ("a
  portfolio with exposure E would experience O") forms appear
  nowhere in v1.15 modules, fixtures, or example output.
- **Not a real-data layer.** Every numeric value is a synthetic
  illustrative scalar; every id uses the `*_reference_*`
  synthetic naming convention; no real-system identifier (real
  exchange, broker, ticker, ISIN, CUSIP, SEDOL, regulator, or
  market data vendor) appears in any v1.15 module, fixture, or
  test.
- **Not a Japan calibration.** All venue ids, security ids, and
  labels are jurisdiction-neutral and synthetic. Real-venue
  calibration (JPX / TSE / OSE / NEX / etc.) is private JFWE
  territory (v2 / v3 only).

## Performance boundary at v1.15.last

- **Per-period record count (default fixture):** **108** (period
  0) / **110** (periods 1+). Up from 96 / 98 at v1.14.5. The
  +12 per period is the v1.15.5 chain (`I × F` market intents +
  `F` aggregated-interest + `F` pressure records).
- **Per-run window (default fixture):** **`[432, 480]`**. Up from
  `[384, 432]` at v1.14.5. Default 4-period sweep emits **460
  records** (438 per-period + 4 v1.15.5 setup + 18 prior setup).
- **Integration-test `living_world_digest`:**
  **`bd7abdb9a62fb93a1001d3f760b76b3ab4a361313c3af936c8b860f5ab58baf8`**.
  The digest moved at v1.15.5 (chain on the per-period path)
  and again at v1.15.6 (phase reorder + new citation slots on
  every review / path payload). Storage-only milestones v1.15.1
  → v1.15.4 left the digest byte-identical.
- **Test count:** **3883 / 3883** passing. Up from 3391 / 3391
  at v1.14.last (+492 across v1.15.1 → v1.15.6).
- The v1.15 chain is bounded `O(P × I × F + 2 × P × F)` per
  layer; v1.15.5 deliberately did **not** add a new dense
  shape, and v1.15.6 added zero new records.

## Discipline preserved bit-for-bit

Every v1.9.x / v1.10.x / v1.11.x / v1.12.x / v1.13.x / v1.14.x
boundary anti-claim is preserved unchanged at v1.15.last:

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
- The v1.13.5 settlement / interbank-liquidity substrate is
  unchanged.
- The v1.14 corporate-financing record set is unchanged in
  vocabulary; v1.15.6 only adds two **citation** slots and
  small label-drift effects, not new vocabulary or new records.
- The `PriceBook` is byte-equal across the full default sweep
  — pinned by tests at v1.15.5 and v1.15.6.
- The v1.9.last public-prototype freeze, the v1.12.last
  attention-loop freeze, the v1.13.last settlement-substrate
  freeze, the v1.14.last corporate-financing-intent freeze, and
  the v1.8.0 public release remain untouched.

## Known limitation — v1.15.5 rotation vs endogeneity

The v1.15.5 living-world integration sets each
`InvestorMarketIntentRecord.intent_direction_label` via a
deterministic four-cycle rotation:

```
intent_direction = SAFE_INTENT_LABELS_BY_ROTATION[
    (period_idx + investor_idx + firm_idx) % 4
]
```

This is **acceptable for bounded demo diversity** (the
per-period histogram is non-trivial, the rotation is
deterministic, and the safe-label vocabulary is preserved) but
it is **not yet endogenous in the v1.12 sense**. The investor's
direction does not currently respond to the upstream evidence
the record cites — the rotation only varies by position. A
future v1.16+ milestone should make the direction a
deterministic function of:

- `InvestorIntentRecord.intent_direction` (v1.12.1) for the
  same `(investor, firm)` pair this period,
- `ValuationRecord.confidence` (v1.9.5 / v1.12.5) — low
  confidence might tilt toward `hold_review` / `risk_reduction_review`,
- `FirmFinancialStateRecord.market_access_pressure` (v1.12.0)
  — high pressure might tilt toward `liquidity_watch` /
  `risk_reduction_review`,
- `MarketEnvironmentStateRecord.overall_market_access_regime_label`
  (v1.12.2) — `closed` / `constrained` regime might tilt the
  whole histogram defensive,
- `ActorAttentionStateRecord.focus_labels` (v1.12.8) — what
  the investor was attending to in the previous period feeds
  the next period's direction, closing the v1.12 loop into the
  v1.15 chain.

The rule must remain deterministic, label-only,
non-probabilistic, and replayable — every v1.12 / v1.14 / v1.15
discipline carries forward. v1.15.last freezes the **rotation**
state; v1.16 replaces the rotation with the **classification**.

## What v1.16 does next

v1.16 begins the **endogenous market intent direction** layer.
v1.16.0 is docs-only design; v1.16.1 ships the deterministic
classifier (a small label-only function over the five upstream
evidence sources listed above) and rewires the v1.15.5 phase to
call the classifier instead of the rotation. v1.16.2 wires the
classifier into the v1.12.8 attention loop so the v1.12 / v1.15
loops compose. v1.16.3 living-world digest moves by design.
v1.16.last freezes the layer.

The classifier must:

- read only the cited evidence ids (no global scan);
- return one of the v1.15 `SAFE_INTENT_LABELS` plus `unknown`;
- never call into a calibrated probability model, an LLM, or a
  real-data source;
- preserve byte-identical replay determinism on the default
  fixture across two consecutive runs.

No order submission, no order matching, no trade execution, no
clearing, no settlement, no real exchange mechanics, no real
price formation, no Japan calibration. The v1.16 layer is the
**internal-cause** of the market-intent vocabulary, not a step
toward execution.
