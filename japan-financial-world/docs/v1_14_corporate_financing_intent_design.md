# v1.14.0 Corporate Financing Intent — Design Note

**Status:** Docs-only design. No code, no tests, no
`living_world_digest` change.

## Purpose

v1.14 begins a small, jurisdiction-neutral, **label-only**,
synthetic substrate for **corporate financing intent**. The
substrate captures three orthogonal facets of a firm's financing
posture *as recorded labels* — never as a financing decision,
not a price, not a covenant, not an investment recommendation,
and not a calibrated probability of any external action.

The motivation is the same as v1.10.x's strategic-response
candidate, v1.12.1's investor-intent signal, and v1.13.x's
settlement substrate: **make a previously implicit context
auditable** as data without introducing execution. v1.14 records
*what a firm is paying attention to* in financing terms, not
what it does.

## Three vocabulary items

v1.14 ships three orthogonal record types in design. None of
them is implemented at v1.14.0.

### 1. `CorporateFinancingNeedRecord`

A firm's recorded financing-need posture at a point in time.

- **Identity:** `need_id`, `firm_id`, `as_of_date`, `status`,
  `visibility`, `confidence` (synthetic `[0,1]` ordering).
- **Need labels:**
  - `funding_horizon_label` (`immediate` / `near_term` /
    `medium_term` / `long_term` / `unknown`)
  - `funding_purpose_label` (`working_capital` / `refinancing`
    / `growth_capex` / `acquisition` / `restructuring` /
    `unknown`) — illustrative; never enforced
  - `urgency_label` (`low` / `moderate` / `elevated` /
    `critical` / `unknown`)
  - `synthetic_size_label` (`reference_size_small` /
    `reference_size_medium` / `reference_size_large` /
    `unknown`) — **never a real currency value**
- **Provenance:**
  `source_firm_financial_state_ids` (v1.12.0),
  `source_market_environment_state_ids` (v1.12.2),
  `source_corporate_signal_ids`, `metadata`.
- **Anti-fields (binding):** no `amount`, no `loan_amount`, no
  `interest_rate`, no `coupon`, no `tenor_years`, no
  `coverage_ratio`, no `decision_outcome`, no
  `default_probability`, no `recommendation`.

### 2. `FundingOptionCandidate`

A label-only enumeration of one synthetic financing option a
firm is *thinking about* in this period.

- **Identity:** `option_id`, `firm_id`, `as_of_date`, `status`,
  `visibility`, `confidence`.
- **Option labels:**
  - `option_type_label` (`bank_loan` / `bond_issuance` /
    `equity_issuance` / `revolver_drawdown` /
    `internal_resources` / `unknown`)
  - `instrument_class_label` (`secured` / `unsecured` /
    `senior` / `subordinated` / `unknown`)
  - `maturity_band_label` (`short` / `medium` / `long` /
    `unknown`) — never a tenor in years
  - `seniority_label` (`senior_secured` / `senior_unsecured` /
    `subordinated` / `unknown`)
  - `accessibility_label` (`accessible` / `selective` /
    `constrained` / `unknown`)
- **Cross-references:** `source_need_ids`,
  `source_market_environment_state_ids`,
  `source_interbank_liquidity_state_ids` (v1.13.3),
  `metadata`.
- **Anti-fields:** no rate, no spread, no haircut, no margin,
  no allocation, no underwrite decision, no syndication
  schedule, no offering price, no discount.

### 3. `CapitalStructureReviewCandidate`

A label-only audit of one synthetic candidate review of a firm's
capital structure — analogous to the v1.10.3 escalation candidate
but on the financing side, not the engagement side.

- **Identity:** `review_id`, `firm_id`, `as_of_date`, `status`,
  `visibility`, `confidence`.
- **Review labels:**
  - `review_motivation_label` (`refinancing_window` /
    `coverage_concern` / `acquisition_planning` /
    `routine_review` / `unknown`)
  - `posture_label` (`status_quo` / `incremental_adjustment` /
    `meaningful_realignment` / `unknown`)
  - `time_horizon_label` (`current_quarter` /
    `next_two_quarters` / `next_year` / `multi_year` /
    `unknown`)
- **Cross-references:** `source_need_ids`,
  `source_funding_option_candidate_ids`,
  `source_firm_financial_state_ids`,
  `source_market_environment_state_ids`,
  `source_bank_credit_review_signal_ids`, `metadata`.
- **Anti-fields:** no rating action, no covenant change, no
  contract or constraint mutation, no leverage target, no
  debt-to-equity number, no buyback decision, no dividend
  decision, no investment-grade migration claim.

## Discipline (v1.14)

The substrate is binding-by-construction:

1. Every record is a frozen dataclass; mutation raises.
2. Every confidence is a synthetic `[0.0, 1.0]` ordering;
   booleans are rejected.
3. Cross-references are plain-id tuples; no record reads
   another record's content.
4. Books emit exactly one ledger record per add call; no book
   mutates any other source-of-truth book.
5. Recommended label vocabularies are **illustrative**; tests
   pin the recommended sets but the records do not enforce
   membership.
6. Anti-fields are pinned by tests on both the dataclass field
   set and the ledger payload key set.
7. Synthetic-size labels replace any real currency value.
8. Real-system identifiers (e.g., real bank names, real
   exchange names, real bond identifiers, real loan covenants)
   never appear in any v1.14 public-FWE record.

## What v1.14 explicitly is not

- Not a credit-application system. No actor *applies for* a
  loan, *originates* an instrument, *prices* an offer, or
  *underwrites* a security.
- Not a financial-decision layer. No record represents a board
  decision, a CFO sign-off, an underwriter mandate, an arranger
  commitment, an allocator weight, a regulator approval, or a
  rating agency action.
- Not a covenant or contract layer. No `ContractRecord` is
  created or mutated. No `ConstraintRecord` is added.
- Not a price or yield layer. No coupon, no spread, no
  yield-to-maturity, no offering price, no clearing price.
- Not a calibrated forecast. No probability of issuance, no
  probability of refinancing, no expected take-up, no expected
  recovery.
- Not a Japan calibration. No reference to Japanese real
  systems, real bank identifiers, real central-bank operations,
  or jurisdiction-specific accounting rules.
- Not an investment-advice layer. No "issue X", no "raise Y",
  no "approach lender Z" framing in records, payloads,
  metadata, or test fixtures.

## Position in the FWE sequence

| Milestone   | Status                                                                                            |
| ----------- | ------------------------------------------------------------------------------------------------- |
| v1.13.last  | Generic central-bank settlement infrastructure freeze — Shipped                                   |
| **v1.14.0** | **Corporate financing intent design — Docs-only (this note)**                                     |
| v1.14.1     | `CorporateFinancingNeedRecord` storage only — Conditional on straightforward extension            |
| v1.14.2     | `FundingOptionCandidate` storage only — Planned                                                   |
| v1.14.3     | `CapitalStructureReviewCandidate` storage only — Planned                                          |
| v1.14.4     | Provenance cross-link to v1.12.x firm-state + v1.13.x interbank-liquidity records — Planned       |
| v1.14.5     | Living-world wiring (one financing-need per firm per period in the default fixture) — Planned     |
| v1.14.last  | Freeze — Planned                                                                                  |

## Performance boundary forecast (non-binding)

v1.14.0 is docs-only — no record-count change, no
`living_world_digest` change. Per-record-type forecast for the
v1.14 sequence (default fixture: 3 firms, 4 periods):

| Record type                              | Per-period | Per-run | Adds to formula |
| ---------------------------------------- | ----------:| -------:| --------------- |
| `CorporateFinancingNeedRecord` (v1.14.5) |          3 |      12 | `+ firms`       |
| `FundingOptionCandidate` (v1.14.5)       |       3..6 |  12..24 | `+ firms..2*firms` (one option-type per need, capped at 2 per firm) |
| `CapitalStructureReviewCandidate` (v1.14.5) |       3 |      12 | `+ firms`       |

Worst-case per-period delta at v1.14.last: **+12** (3 firms × 4
record types per firm); per-run total moves from 81/83
(v1.13.last) toward an estimated **93/95** at v1.14.last. The
exact numbers will be pinned at v1.14.5 / v1.14.last in
`docs/performance_boundary.md`.

## v1.14 anti-claims (forward-binding)

The v1.14 substrate **must never**:

- create or mutate any `ContractRecord` or `ConstraintRecord`;
- emit a price, yield, spread, coupon, fee, haircut, margin,
  or any monetary scalar;
- emit a calibrated probability of any external action
  (issuance, drawdown, repayment, default, downgrade);
- emit any rating, internal-rating, PD, LGD, EAD, or recovery;
- emit any allocation, weight, target leverage, target equity,
  or target capital structure;
- represent a board decision, regulator decision, central-bank
  decision, or any binding action;
- ingest real corporate-finance data, real bond pricing, real
  loan terms, or any Japan-specific calibration;
- dispatch to an LLM agent or any external solver;
- imply investment advice — direct or indirect.

These anti-claims are binding for every v1.14.x milestone.
Tests will pin them on every record dataclass field set and
every ledger payload key set, mirroring the v1.13.x pattern.
