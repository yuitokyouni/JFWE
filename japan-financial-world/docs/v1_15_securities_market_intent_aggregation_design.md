# v1.15.0 Securities Market Intent Aggregation — Design Note

**Status:** Docs-only design. No code, no tests, no
`living_world_digest` change. v1.14.last is the most recent
shipped freeze; v1.15.0 begins the next sequence by **describing
the missing broker / exchange / market-venue abstraction between
investor intent and price formation** without implementing any
of it.

> **Naming amendment (v1.15.2).** The per-investor / per-security
> record originally named `InvestorMarketIntentRecord` in this
> design note ships under `InvestorMarketIntentRecord` instead.
> Public FWE deliberately models *market interest / market intent*
> before *trading*; "trading" reads as order / execution language
> that the substrate explicitly does not implement. The label
> vocabulary is unchanged from this design — `intent_direction_label`
> stays on the v1.15 `SAFE_INTENT_LABELS` set (`increase_interest` /
> `reduce_interest` / `hold_review` / `liquidity_watch` /
> `rebalance_review` / `risk_reduction_review` /
> `engagement_linked_review`) plus `unknown`. The shipped module is
> `world/market_intents.py`; the shipped book is
> `InvestorMarketIntentBook`; the shipped ledger event is
> `investor_market_intent_recorded`. Other naming in this document
> (`AggregatedMarketInterestRecord`, `IndicativeMarketPressureRecord`,
> `ListedSecurityRecord`, `MarketVenueRecord`) ships under the
> design names. References below have been updated to the shipped
> name.

## Purpose

v1.12.1 records what individual investors are paying attention
to in firm-level posture terms (`investor_intent_signal_added`).
v1.14 records what firms are paying attention to in financing
terms (need → funding option → capital structure review →
financing path). Neither layer touches the *secondary-market*
side of the picture: an individual investor's directional
posture is **not** a price-moving force on its own — it has to
flow through a broker / exchange / market-venue **aggregation**
before it can plausibly affect indicative price pressure,
liquidity, market access, or equity-issuance accessibility.

v1.15 ships, *as labels and audit records only*, the missing
aggregation layer:

```
investor_intent_signal_added           (v1.12.1, per investor / firm)
  → InvestorMarketIntentRecord        (v1.15, per investor / security)
  → AggregatedMarketInterestRecord     (v1.15, per venue / security)
  → IndicativeMarketPressureRecord     (v1.15, per security)
  → feedback into capital_structure_review / financing_path  (v1.14.x)
```

The motivation is the same as the entire v1.x agenda:
**make a previously implicit context auditable** as small,
deterministic, synthetic, jurisdiction-neutral records *without*
introducing execution. v1.15 records *what the market is
collectively paying attention to per security*, not what it
trades, prices, or fills.

## Five vocabulary items

v1.15 introduces five new record types in design. None of them
is implemented at v1.15.0.

### 1. `ListedSecurityRecord`

A jurisdiction-neutral, synthetic record naming one security
listed at one venue.

- **Identity:** `security_id`, `issuer_firm_id`,
  `security_type`, `listing_status`, `market_venue_id`,
  `visibility`, `metadata`.
- **Closed-set labels (proposed):**
  - `security_type` ∈ { `common_equity`, `preferred_equity`,
    `senior_unsecured_bond`, `senior_secured_bond`,
    `subordinated_bond`, `convertible_bond`, `hybrid`,
    `unknown` }
  - `listing_status` ∈ { `listed`, `suspended`,
    `under_review`, `delisted`, `unknown` }
- **Anti-fields (binding):** no `price`, no `shares_outstanding`,
  no `market_cap`, no `nominal_amount`, no `par_value`, no
  `last_trade`, no `coupon`, no `yield`, no `target_price`, no
  `recommendation`, no `real_data_value`. The record names a
  *generic synthetic security id*; it never carries traded
  numbers.

### 2. `MarketVenueRecord`

A jurisdiction-neutral, synthetic record naming one market venue
that the v1.15 aggregation runs against.

- **Identity:** `venue_id`, `venue_type`, `status`,
  `supported_security_types`, `visibility`, `metadata`.
- **Closed-set labels (proposed):**
  - `venue_type` ∈ { `reference_stock_exchange`,
    `reference_otc_exchange`, `reference_bond_market`,
    `reference_dark_pool`, `reference_listing_authority`,
    `unknown` }
  - `status` ∈ { `active`, `suspended`, `under_review`,
    `closed`, `unknown` }
- **Anti-fields (binding):** no real-system identifier (no JPX,
  TSE, NYSE, LSE, Euronext, BOJ-NET, etc.), no real-venue rule
  set, no order-book parameters, no fee schedule, no tick size,
  no listing-fee numeric. Real-venue calibration is private
  JFWE territory (v2 / v3 only).

### 3. `InvestorMarketIntentRecord`

A per-investor, per-security, **non-binding** *market-interest*
posture. Strictly distinct from `investor_intent_signal_added`
(v1.12.1), which is per-investor / per-*firm* posture in
*review* terms; v1.15's record is per-investor / per-*security*
posture in *market-interest* terms — but neither is an order.

> **Naming amendment.** v1.15.0 originally called this record
> `InvestorTradingIntentRecord`; v1.15.2 ships it as
> `InvestorMarketIntentRecord`. Public FWE models *market
> interest* before *trading*; the rest of this section uses
> the shipped name.

- **Identity:** `market_intent_id`, `investor_id`,
  `security_id`, `as_of_date`, `confidence` (synthetic
  `[0,1]` ordering), `status`, `visibility`, `metadata`.
- **Closed-set safe labels (binding):**
  - `intent_direction_label` ∈ { `increase_interest`,
    `reduce_interest`, `hold_review`, `liquidity_watch`,
    `rebalance_review`, `risk_reduction_review`,
    `engagement_linked_review`, `unknown` } — exactly the
    v1.15 `SAFE_INTENT_LABELS` set ∪ `unknown`.
  - `intensity_label` ∈ { `low`, `moderate`, `elevated`,
    `high`, `unknown` }
  - `horizon_label` ∈ { `intraperiod`, `near_term`,
    `medium_term`, `long_term`, `unknown` }
  - `status` ∈ { `draft`, `active`, `stale`, `superseded`,
    `archived`, `unknown` }
- **Provenance (plain-id cross-references):**
  - `evidence_investor_intent_ids` (v1.12.1)
  - `evidence_valuation_ids` (v1.9.5 / v1.12.5)
  - `evidence_market_environment_state_ids` (v1.12.2)
  - `evidence_firm_state_ids` (v1.12.0)
  - `evidence_security_ids` (v1.15.1)
  - `evidence_venue_ids` (v1.15.1)
- **Forbidden labels (binding):** the record **must not** carry
  `buy`, `sell`, `order`, `target_weight`, `overweight`,
  `underweight`, `execution`, `submit`, `cancel`, `fill`,
  `match` — neither in the label vocabulary nor in metadata
  keys. Closed-set membership on `intent_direction_label`
  rejects each forbidden verb at construction; tests pin the
  rejection.
- **Anti-fields (binding):** no `quantity`, no `notional`, no
  `target_price`, no `expected_return`, no `recommendation`,
  no `investment_advice`, no `real_data_value`. The full
  v1.14.x anti-field family is also rejected.

### 4. `AggregatedMarketInterestRecord`

A per-venue / per-security aggregation of investor market
intents in one period. Audit / count object only — never an
order book, never a quote, never a fill.

- **Identity:** `aggregated_interest_id`, `venue_id`,
  `security_id`, `as_of_date`, `confidence`, `status`,
  `visibility`, `metadata`.
- **Counts:** `positive_interest_count`,
  `negative_interest_count`, `neutral_interest_count` (each is
  a non-negative integer; the trio sums to the count of cited
  market intents).
- **Closed-set labels (proposed):**
  - `net_interest_label` ∈ { `net_positive`, `net_negative`,
    `balanced`, `insufficient_evidence`, `unknown` }
  - `liquidity_interest_label` ∈ { `improving`, `steady`,
    `thinning`, `stressed`, `unknown` }
- **Provenance (plain-id):**
  - `source_market_intent_ids` — the per-investor market
    intents this venue/security aggregation read.
- **Anti-fields (binding):** no `volume`, no `notional`, no
  `bid`, no `ask`, no `mid`, no `vwap`, no `last_trade`, no
  `match_count`, no `fill_count`, no `order_book_depth`, no
  `target_price`, no `quote`, no `pricing`. The record carries
  *counts of distinct investor postures*; it never carries
  traded sizes or prices.

### 5. `IndicativeMarketPressureRecord`

A per-security summary that translates the venue-level
aggregation into compact pressure labels for downstream
consumers (the v1.14 capital-structure review and financing
path layers, future market-environment readouts).

- **Identity:** `pressure_id`, `security_id`, `as_of_date`,
  `confidence`, `status`, `visibility`, `metadata`.
- **Closed-set labels (proposed):**
  - `demand_pressure_label` ∈ { `supportive`, `neutral`,
    `restrictive`, `stressed`, `unknown` }
  - `liquidity_pressure_label` ∈ { `improving`, `steady`,
    `thinning`, `stressed`, `unknown` }
  - `volatility_pressure_label` ∈ { `calm`, `elevated`,
    `stressed`, `unknown` }
  - `market_access_label` ∈ { `open`, `selective`,
    `constrained`, `closed`, `unknown` } — same vocabulary as
    `CapitalStructureReviewCandidate.market_access_label`
    (v1.14.3) so the two layers compose cleanly.
- **Provenance (plain-id):**
  - `source_aggregated_interest_ids` — venue-level
    aggregation ids cited as input.
  - `source_market_environment_state_ids` — the period's
    v1.12.2 market environment.
- **Anti-fields (binding):** no `target_price`, no
  `expected_return`, no `recommendation`, no `forecast_value`,
  no `actual_value`, no `pricing`, no `bid`, no `ask`, no
  `match`, no `fill`. The record carries *pressure labels*,
  not prices.

## Future financing feedback

A v1.15.x milestone (after the storage layers ship) will wire
`IndicativeMarketPressureRecord` into the v1.14 chain as an
**additional citation slot**, never as a direct mutation:

- The per-firm `CapitalStructureReviewCandidate` (v1.14.3) may
  read `market_access_label` from the firm's
  `IndicativeMarketPressureRecord` (for issuer-level securities)
  and use it as additional evidence for its own
  `market_access_label`. The review record's slot remains
  `source_*_ids`-style — it cites the pressure id, never copies
  the value.
- The per-firm `CorporateFinancingPathRecord` (v1.14.4) may
  fold `IndicativeMarketPressureRecord.dilution_pressure` into
  its `coherence_label` derivation when an
  `equity_issuance_candidate` is on the path. The
  `build_corporate_financing_path` helper would gain a new
  optional id-tuple kwarg; the deterministic synthesis rules
  stay the same shape.
- No mutation flows the other direction: v1.14 records do not
  affect the v1.15 aggregation (the aggregation is upstream).

This feedback is *describing* a future composition — v1.15.0
itself ships nothing. The composition only becomes concrete
once the v1.15 storage modules have shipped.

## What v1.15 explicitly is not

- **Not order submission.** No `OrderSubmittedRecord`, no
  `order_submitted` ledger event, no quantity, no notional, no
  side, no order id flowing from the market-intent record.
- **Not order matching.** No order book, no bid / ask / mid /
  spread, no match engine, no fill report, no execution
  notice.
- **Not trade execution.** No trade record, no clearing, no
  settlement (the v1.13 settlement substrate covers
  central-bank-shaped settlement *labels* — not trade-level
  execution).
- **Not real exchange mechanics.** No tick size, no lot size,
  no auction schedule, no halt rule, no circuit breaker, no
  reference-rate setting.
- **Not real price formation.** No price, no quote, no
  benchmark fixing, no NAV, no index level, no last-trade.
- **Not target prices, expected returns, or recommendations.**
  The vocabulary is deliberately phrased to make a
  market-intent-as-recommendation reading impossible.
- **Not a Japan calibration.** All venue ids, security ids,
  and labels are jurisdiction-neutral and synthetic.
  Real-venue calibration (JPX / TSE / OSE / NEX / etc.) is
  private JFWE territory (v2 / v3 only).
- **Not a market simulator.** v1.15 is an *aggregation /
  audit* substrate, not a simulator. It composes with the
  v1.12 endogenous attention loop and the v1.14 corporate
  financing chain in the same audit-only way the v1.13
  settlement substrate composes — labels + provenance +
  ledger events, never execution.
- **Not a real-data layer.** Every numeric value is a
  synthetic illustrative scalar; every id uses the
  `*_reference_*` synthetic naming convention; no real-system
  identifier appears in any v1.15 module, fixture, or test.

## Position in the v1 sequence

| Milestone   | What                                                                                       | Status                  |
| ----------- | ------------------------------------------------------------------------------------------ | ----------------------- |
| v1.14.last  | Corporate financing intent freeze (need → option → review → path)                          | Shipped                 |
| v1.15.0     | Securities market intent aggregation design (this document)                                | Shipped (docs-only)     |
| v1.15.1     | `world/securities.py` — `ListedSecurityRecord` + `MarketVenueRecord` + `SecurityMarketBook`| Shipped                 |
| v1.15.2     | `world/market_intents.py` — `InvestorMarketIntentRecord` + `InvestorMarketIntentBook` + safe-label enforcement | Shipped                 |
| v1.15.3     | `world/market_interest.py` — `AggregatedMarketInterestRecord` + `AggregatedMarketInterestBook` + `build_aggregated_market_interest` deterministic helper | Shipped                 |
| **v1.15.4** | **`world/market_pressure.py`** — **`IndicativeMarketPressureRecord` + `IndicativeMarketPressureBook` + `build_indicative_market_pressure` deterministic helper (reuses v1.14.3 `MARKET_ACCESS_LABELS`)** | **Shipped**             |
| v1.15.5     | Living-world integration — per-period venue × security aggregation; digest moves by design | Planned                 |
| v1.15.6     | v1.14 feedback wiring — `CapitalStructureReviewCandidate` and `CorporateFinancingPathRecord` cite `IndicativeMarketPressureRecord` ids; `build_corporate_financing_path` gains an optional pressure-evidence kwarg | Planned                 |
| v1.15.last  | Securities market intent aggregation freeze (docs-only)                                    | Planned                 |

The v1.15 sequence preserves the v1.x storage-first discipline:
each milestone ships one record + one book + one (or two)
ledger event(s), passes a closed-set label test, passes the
forbidden-label / forbidden-payload-key scan, and integrates
into the living world only at v1.15.5. Through v1.15.4 the
`living_world_digest` is unchanged from v1.14.5
(`3df73fd4f152c16d1188f5c15b69bdc8a5cd6061b637ea35af671e86c6fa2d71`).

## Boundary recap

This is **market interest aggregation, not market trading.** It
creates audit records, not trades or prices. Every v1.9.x /
v1.10.x / v1.11.x / v1.12.x / v1.13.x / v1.14.x anti-claim is
preserved unchanged. The v1.9.last public-prototype freeze, the
v1.12.last attention-loop freeze, the v1.13.last settlement-
substrate freeze, the v1.14.last corporate-financing-intent
freeze, and the v1.8.0 public release remain untouched.
