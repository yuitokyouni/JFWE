# v1.1 Valuation / Fundamentals Design

This document is the design rationale for the v1.1 Valuation Layer. v1.1
introduces valuation as a first-class world object — and explicitly does
**not** introduce fundamentals or any decision-making behavior. The
fundamentals layer is deferred to a later v1 milestone; the gating reason
is documented at the bottom of this file.

For the higher-level v1 design statement, see
[`v1_reference_system_design.md`](v1_reference_system_design.md). For
v1.1's place in the module sequence, see [`v1_module_plan.md`](v1_module_plan.md).
For the policy under which behavior enters v1, see
[`v1_behavior_boundary.md`](v1_behavior_boundary.md). v1.1 sits inside the
non-behavioral carve-out described there.

## Price, Valuation, Fundamental — three distinct things

A core design claim of v1.1 is that **price, valuation, and fundamental
are three different concepts**, and the system must keep them separate.
Conflating them is the most common shape of silent error in financial
software.

| Concept       | Question it answers                              | Lives in                        |
| ------------- | ------------------------------------------------ | ------------------------------- |
| Price         | What was actually transacted, quoted, or marked? | `PriceBook` (v0.4)              |
| Valuation     | What does some valuer think it is worth, for some purpose, by some method, with some confidence? | `ValuationBook` (v1.1) |
| Fundamental   | What underlying economic facts is the entity producing? (revenue, margin, book value, NOI, occupancy, etc.) | Fundamentals layer (deferred)   |

The distinction is sharp:

- A **price** is data the world observed. Past prices are historical
  fact. They are not opinions, and `PriceBook` therefore does not carry
  a valuation method or a confidence level.
- A **valuation** is an opinion held by a valuer. Two valuers can
  reasonably disagree about the same subject on the same day, and
  v1.1's `ValuationBook` records the disagreement without picking a
  winner.
- A **fundamental** is a factual measurement of the underlying entity:
  revenue, EBITDA, book value, rent roll, occupancy. A fundamental is
  not a valuation — but a valuation is typically derived *from*
  fundamentals using a method.

v1.1 implements only the middle layer. It can store a valuation that
references fundamentals via the `inputs` field as free-form data, but
the fundamentals themselves do not have their own typed store yet.

## Valuation as an opinionated claim

v1.1 frames every valuation as an explicit, attributed, justified
opinion. A `ValuationRecord` carries:

- **who** thinks it is worth this much (`valuer_id`)
- **about what** (`subject_id`)
- **of what kind** (`valuation_type`)
- **for what reason** (`purpose`)
- **using what technique** (`method`)
- **as of when** (`as_of_date`)
- **how confident** (`confidence`)
- **with what assumptions** (`assumptions` dict)
- **based on what inputs** (`inputs` dict)
- **referencing which other world objects** (`related_ids`)

The point of recording all eight together is that a valuation only
makes sense in context. Saying "Toyota is worth ¥45 trillion" without
specifying who said it, when, why, and using what method is barely
information. Saying "the sell-side analyst at Source A, on
2026-01-15, computed a DCF valuation of ¥45 trillion using a 7%
discount rate and 2% terminal growth, with confidence 0.6" is
information.

`ValuationBook` is therefore append-only and stores conflicting
claims as separate records. There is no "the valuation" of any
subject. There are only valuations.

## subject_id design

`subject_id` is intentionally a free-form `WorldID`. It can refer to
any object the world might want to value:

- a firm: `firm:reference_manufacturer_a`
- a tradable asset: `asset:reference_equity_a`
- a contract: `contract:reference_loan_001`
- a real estate property: `asset:reference_office_a`
- an FX pair: `fx:usd_jpy`
- a portfolio or fund: `portfolio:etf_global`, `fund:reference_pension`
- a market itself: `market:reference_real_estate_tokyo_central`
- a synthetic basket or index: `index:reference_equity_500`

v1.1 does **not** validate that `subject_id` resolves to a registered
object. A valuation can reference a subject the registry has never
seen. The reason is the same as for the foreign-key rule in v0.12:
cross-references are recorded as data, not enforced as invariants. If
a future caller cares about resolution, they validate themselves.

The flexibility matters because a valuer can value almost anything in
the world:

- An equity analyst values a firm.
- A property appraiser values a building.
- A mark-to-model engine values a structured note.
- An FX strategist values a currency pair.
- A fund administrator values a fund's NAV.
- A risk team values a portfolio under a stress scenario.

The `ValuationRecord` shape is the same in every case. Only the
`valuation_type`, `purpose`, and `method` strings differ.

## valuer_id design

Like `subject_id`, `valuer_id` is free-form. A valuer is whoever
produced the opinion. Examples:

- a human or institutional analyst: `valuer:source_a_research`
- an internal modeling system: `valuer:reference_dcf_engine_v3`
- a credit underwriting system at a bank: `valuer:bank_b_underwriting`
- a real estate appraiser: `valuer:appraiser_c`
- an automated mark-to-model engine: `valuer:reference_mtm`
- a covenant calculator: `valuer:reference_covenant_calc`
- a synthetic counterfactual: `valuer:reference_what_if_engine`

v1.1 makes no distinction between human and synthetic valuers. The
schema treats them identically. Whether a valuer is "trustworthy" is
a question for v1.5 (Relationship Capital) and ultimately v2/v3
(jurisdiction calibration).

## purpose, method, type — three free-form strings

These three string fields disambiguate the same numerical answer
across different professional contexts:

- **`valuation_type`** — *what kind of valuation is this?* Examples:
  `"equity"`, `"debt"`, `"real_estate"`, `"fx_view"`, `"fund_nav"`,
  `"derivative"`, `"structured"`. This is the broadest classifier.
- **`purpose`** — *why was this valuation produced?* Examples:
  `"investment_research"`, `"underwriting"`, `"financial_reporting"`,
  `"covenant_test"`, `"impairment_test"`, `"tax"`, `"internal_review"`.
  The same valuation_type can serve very different purposes, and the
  same subject can have multiple valuations existing for different
  purposes simultaneously.
- **`method`** — *how was the number produced?* Examples: `"dcf"`,
  `"comparables"`, `"book_value"`, `"cap_rate"`, `"comparable_sales"`,
  `"black_scholes"`, `"lookthrough_aggregation"`, `"reference_macro_model"`.

v1.1 does not enumerate any of these. They are free-form strings so
that any plausible professional vocabulary can be expressed without
schema changes. v2 may introduce stricter enums for Japan-specific
sub-classes; v1.1 does not.

## currency vs numeraire

These are intentionally two distinct fields, even when they happen to
be the same string in practice.

- **`currency`** — the display currency of `estimated_value`. The
  unit of the number itself. If `estimated_value` is `1.5e10` and
  `currency` is `"JPY"`, the valuation is "fifteen billion yen".
- **`numeraire`** — the perspective currency or value basis the
  valuer is reasoning in. The lens through which the math was done.

For most domestic valuations the two are identical. The distinction
only matters in cross-border contexts:

- A USD-perspective fund valuing a JPY-denominated equity for its
  reporting line might set `currency="JPY"`, `numeraire="USD"`. The
  number it produced is in yen, but its model framework was
  dollar-centric.
- A risk team computing a ¥-equivalent for a USD-denominated bond
  position might set `currency="JPY"`, `numeraire="JPY"`, with the
  USD-denominated price entering as an `inputs` dict entry plus an
  FX assumption in `assumptions`.

v1.1 does **not** implement FX conversion. The comparator detects
mismatches and refuses to convert; it records `"currency_mismatch"`
as the reason on the resulting `ValuationGap` rather than producing
a possibly-wrong number. v2 may introduce a reference FX-conversion
policy; v1.1 does not, because the choice of FX rate, FX timestamp,
and FX source is itself a calibration decision.

## Use case 1: Bank underwriting

A bank evaluating whether to extend a loan against collateral
produces a valuation of the collateral.

```
ValuationRecord(
    valuation_id="valuation:underwriting_loan_001",
    subject_id="asset:reference_office_a",
    valuer_id="valuer:bank_b_underwriting",
    valuation_type="real_estate",
    purpose="underwriting",
    method="cap_rate",
    as_of_date="2026-03-15",
    estimated_value=950_000_000.0,
    currency="USD_REFERENCE",
    confidence=0.55,
    assumptions={"cap_rate": 0.06, "noi_haircut": 0.10},
    inputs={"observed_noi": 60_000_000.0},
    related_ids=("contract:reference_loan_001",),
)
```

The bank's underwriting valuation is intentionally conservative
(low confidence, NOI haircut). The same building may carry a
separate appraiser valuation with a higher number for financial
reporting purposes. v1.1 stores both. The bank's downstream credit
decision (which v1.3 will introduce) consumes this underwriting
record specifically — distinguished from the appraisal record by
the `purpose` field.

## Use case 2: Investor research valuation

A buy-side investor's research model values a firm to decide
whether to over- or under-weight it.

```
ValuationRecord(
    valuation_id="valuation:research_q1_2026",
    subject_id="firm:reference_manufacturer_a",
    valuer_id="valuer:investor_b_research",
    valuation_type="equity",
    purpose="investment_research",
    method="dcf",
    as_of_date="2026-04-01",
    estimated_value=2_800.0,
    currency="USD_REFERENCE",
    confidence=0.65,
    assumptions={"discount_rate": 0.085, "terminal_growth": 0.02},
    inputs={"fcf_5y": [..., ..., ...]},
)
```

The investor will compare this to the latest market price. v1.1's
`ValuationComparator` produces a `ValuationGap` showing the spread
between the investor's view and the market price. Whether the
investor *acts* on that gap — buys, holds, shorts — is a v1.3
investor-decision question. v1.1 only records the gap.

## Use case 3: Real estate appraisal

A regulated appraiser produces a valuation for financial reporting.

```
ValuationRecord(
    valuation_id="valuation:appraisal_2026Q1",
    subject_id="asset:reference_office_a",
    valuer_id="valuer:appraiser_c",
    valuation_type="real_estate",
    purpose="financial_reporting",
    method="comparable_sales",
    as_of_date="2026-03-31",
    estimated_value=1_050_000_000.0,
    currency="USD_REFERENCE",
    confidence=0.80,
    assumptions={"comparable_set": "tier_1_office_central"},
    inputs={"comparable_sales": [..., ..., ...]},
)
```

This appraiser valuation typically differs from the bank
underwriting valuation in the same building (use case 1). The two
coexist in `ValuationBook` and serve different consumers — the
appraiser's number drives reporting, the underwriting number drives
credit decisions.

## Use case 4: Structured finance / covenant test

A covenant calculator produces a valuation specifically to test a
contract's covenant.

```
ValuationRecord(
    valuation_id="valuation:covenant_test_2026Q2",
    subject_id="contract:reference_loan_001",
    valuer_id="valuer:reference_covenant_calc",
    valuation_type="debt",
    purpose="covenant_test",
    method="defined_in_contract",
    as_of_date="2026-06-30",
    estimated_value=975_000_000.0,
    currency="USD_REFERENCE",
    confidence=1.0,
    assumptions={"computation_basis": "as_specified_in_section_4_2"},
    inputs={"prior_quarter_collateral_value": 1_000_000_000.0},
    related_ids=("contract:reference_loan_001",),
)
```

The covenant valuation has confidence=1.0 because the contract
itself defines the computation. There is no professional opinion
involved — only a deterministic calculation. The same
`ValuationRecord` shape captures all four use cases above with
nothing more than different string values in `purpose` and `method`.

## Why fundamentals are deferred

A fundamentals store would carry the underlying economic facts that
valuations depend on: revenue, operating margin, book value, NOI,
occupancy, leverage, cash flow streams, etc. v1.1 deliberately does
not introduce one, for two reasons:

1. **Fundamentals require source attribution and time series.** A
   single revenue number is rarely enough — the consumer needs to
   know *whose* number this is (issuer-reported? analyst-adjusted?
   regulator-restated?), *as of when*, and *how it relates to prior
   periods*. That is its own design problem and deserves its own
   milestone.
2. **Fundamentals lock in jurisdiction-specific schemas.** A
   "Japanese GAAP operating profit" is not the same as a "U.S. GAAP
   operating income". Picking field names commits the model to a
   specific accounting standard's vocabulary. v1.1 sidesteps this
   by letting valuations carry their inputs as a free-form dict —
   so a `dcf` valuation can include `inputs={"fcf_5y": [...]}` even
   though no typed `FundamentalsBook` exists yet.

The fundamentals layer will land in a later v1 sub-milestone (or
possibly v1.3 alongside institutional decomposition, if reference
behavior needs typed fundamentals). v1.1's `inputs` dict is the
escape hatch until then.

## v1.1 scope

In scope for v1.1:

- `ValuationRecord` immutable dataclass with all 15 documented fields.
- `ValuationGap` immutable dataclass for comparison results.
- `ValuationBook` storage with append-only writes, indexed reads
  (by subject, valuer, type, purpose, method), latest-by-subject
  helper, deterministic snapshot.
- `ValuationComparator` that compares a valuation to the latest
  observed price and produces a `ValuationGap`.
- Ledger event types `valuation_added` and `valuation_compared`,
  with `parent_record_ids` linking comparisons back to their
  originating valuation records.
- Kernel wiring: `kernel.valuations` and `kernel.valuation_comparator`
  are constructed in `__post_init__` with the kernel's clock,
  ledger, and prices ref.
- Tests covering CRUD, all five list-by-* helpers, latest-by-subject,
  snapshot, ledger writes, comparator success path, comparator
  failure paths (missing price, None estimated_value, currency
  mismatch, observed price zero), non-firm subject ids, multiple
  conflicting claims about the same subject, no-mutation guarantee.

## v1.1 out of scope

- A typed `FundamentalsBook` or `FundamentalView` (deferred).
- A reference DCF engine, comparables engine, or any model
  implementation. v1.1 stores opinions; it does not produce them.
- A reference real estate appraisal engine.
- A reference credit decision engine that consumes valuations
  (deferred to v1.3).
- Covenant generation and covenant evaluation logic.
- Any trading behavior, price formation, or investor reaction.
- FX conversion of any kind. The comparator detects currency
  mismatch and refuses to convert.
- Scenario logic.
- Any Japan-specific calibration.
- Computation of "consensus" or "fair value" by aggregating multiple
  valuations of the same subject. v1.1 stores the disagreement; it
  does not summarize it.

## Why v1.1 is non-behavioral

Per [`v1_behavior_boundary.md`](v1_behavior_boundary.md), v1.1 is
explicitly carved out from the four-property behavior contract.
v1.1 introduces new state (the valuation book) and new ledger
record types, but its operations are *not behavior*:

- v1.1 stores valuation claims.
- v1.1 compares valuation claims to observed prices.
- v1.1 records both operations to the ledger.
- v1.1 does **not** decide anything. A valuation is data, not a
  trigger.
- v1.1 does **not** propagate to any other space. A v1.3 bank that
  wants to use a valuation reads it; the valuation layer never pushes.
- v1.1 does **not** drive prices.

This matters because every v1 module after v1.1 will satisfy the
four-property contract (explicit inputs / outputs / ledger record per
change / no direct cross-space mutation). v1.1 is the only place where
the contract does not strictly apply, because there is no decision to
apply it to. The other invariants from
[`v1_design_principles.md`](v1_design_principles.md) — no cross-space
mutation, prices stay in PriceBook, valuation is not price or truth,
ledger records every state change and comparison, reads are
non-mutating — all hold.
