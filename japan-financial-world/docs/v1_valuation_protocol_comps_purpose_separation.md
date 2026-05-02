# v1.x Valuation Protocol — Comps Purpose Separation (advanced design note)

This document is the design rationale for an **advanced valuation
evidence discipline** that the FWE may adopt for sophisticated actor
types in a future v1.x milestone. It is **docs-only**. No code,
no records, no books, no calculation, no decision lives behind
this note today. The mechanism path through v1.12 — the
`EvidenceResolver` substrate (§83) → attention-conditioned
investor intent (anticipated v1.12.4) → attention-conditioned
valuation lite (anticipated v1.12.5) → attention-conditioned bank
credit review (anticipated v1.12.6) — is **not** modified or
gated by this note.

For the v1.1 valuation-vs-price-vs-fundamental separation, see
[`v1_valuation_fundamentals_design.md`](v1_valuation_fundamentals_design.md).
For the v1 behaviour boundary that this note sits inside, see
[`v1_behavior_boundary.md`](v1_behavior_boundary.md). For the
attention-as-bottleneck substrate this protocol could later
consume, see `world_model.md` §83.

## 1. Why this exists

A common silent error in valuation software — and in valuation
practice — is treating "comparables" as a single, purpose-free
data set. In reality, **the same word "comps" can mean different
things depending on what valuation question is being asked**, and
those different meanings can imply *materially different* valid
selection criteria:

- **Beta-estimation comps** ask: which other companies have a
  comparable *equity-return covariance with the market*? The
  selection criteria typically tilt toward operating-risk shape,
  cyclicality, input-cost sensitivity, and price-cycle exposure.
- **Debt-capacity comps** ask: how much debt can a company
  *plausibly support and refinance*? The selection criteria
  typically tilt toward asset collateral quality, asset
  redeployability, cash-flow visibility, and bankability.
- **Impairment discount-rate-support comps** ask: at what rate
  should a CGU's expected cash flows be discounted in an
  impairment test? The selection criteria typically tilt toward
  CGU-specific risk profile, service potential, and cash-flow
  cyclicality — and emphatically **must not** double-count a risk
  the cash-flow projection has already adjusted for.
- **Valuation-multiple comps** (EV/EBITDA, P/E, P/B) ask: what
  multiple does the market apply to similar businesses? The
  selection criteria typically tilt toward business model,
  margin profile, and growth shape.
- **Margin-benchmark comps** ask: what operating-margin band is
  reasonable for this kind of business? The selection criteria
  typically tilt toward sector, scale, and product-mix
  comparability.

A single comparable set rarely satisfies all of these purposes
simultaneously without compromise. Picking one set and reusing it
across purposes is one of the most common shapes of silent error
in valuation work; pretending the choice is purpose-free is the
audit-trail shape of that same error.

The FWE's response is **not** to compute valuation. The FWE's
response is to give a sophisticated actor a way to **record the
purpose, the comparable-set choice, the selection rationale, and
the warning flags** that go with it — so that an audit reader,
a future LLM-agent step, or a downstream attention-conditioned
mechanism can see *what the valuer was solving for* and *what the
valuer warned themselves about*.

This is an **advanced** discipline: only specialised actor types
(e.g., structured-credit reviewers, impairment-test reviewers,
multi-method valuers) need to record at this level. The default
investor and the default bank in the v1.9 living reference world
do **not** need this protocol; their valuation refresh lite and
bank credit review lite layers are intentionally minimal and
non-binding.

## 2. Scope (what this protocol does and does not do)

The protocol is a **vocabulary-and-discipline** specification.

It defines:

- a **`ValuationPurpose`** vocabulary that names *what valuation
  question* the valuer is solving;
- a **`ComparableSet.purpose`** vocabulary that names *what role
  this particular comps set plays* in the valuer's approach;
- **comps selection dimensions** — the small, named
  decision-axes a sophisticated valuer should be able to point
  at when defending a comps choice;
- a **warning-flag vocabulary** that names the well-known shapes
  of silent error this protocol is meant to surface;
- a **boundary statement** that pins what the protocol does
  *not* do.

It deliberately does **not**:

- compute beta, WACC, debt/equity, equity premium, or any cost
  of capital;
- compute or recommend a fair value, target price, expected
  return, or investment view;
- decide whether an impairment loss should be recorded;
- determine a target capital structure, leverage band, or
  refinancing schedule;
- enforce or interpret IFRS, US GAAP, J-GAAP, or any
  jurisdiction-specific accounting standard;
- ingest real market data, real benchmark data, real audited
  financial statements, or real broker / lender / regulator
  output;
- apply Japan-specific calibration of any kind;
- dispatch a calculation to an LLM agent or any external solver;
- emit any ledger record, mutate any source-of-truth book, or
  cross any boundary already pinned by `v1_behavior_boundary.md`
  or `world_model.md` §69 (v1.9.last freeze) / §83 (v1.12.3
  evidence resolver).

The protocol is *evidence discipline*. It records what was
considered and warned about; it does not produce a number, a
recommendation, or a compliance opinion.

## 3. `ValuationPurpose` vocabulary

A `ValuationPurpose` answers the question *what is this valuation
for?* Suggested jurisdiction-neutral labels:

| Label | What it means |
| --- | --- |
| `impairment_test` | The valuer is testing whether a CGU / asset's recoverable amount may be below its carrying amount. The output of the surrounding work is a *trigger / no-trigger* finding, not an investment view. |
| `market_value_claim` | The valuer is asserting an opinion of value as if a willing buyer and seller transacted under typical-market assumptions. |
| `internal_review` | The valuer is producing a non-public review for internal portfolio / risk / governance use. |
| `credit_support_review` | The valuer is forming a *credit-side* opinion in support of a lender / bondholder / counterparty's review. |
| `strategic_response_review` | The valuer is forming a corporate-side opinion in support of a strategic-response candidate (e.g., capital allocation review, governance-change review). |

These labels are illustrative. A sophisticated actor type
implementing the protocol may extend the vocabulary; the
protocol does not enum-lock it. The `ValuationPurpose` value is
expected to be carried as a free-form string field on a future
`AdvancedValuationProtocolRecord` (deferred to a later v1.x
milestone).

The protocol's binding rule is that **the same valuation work
must declare its purpose explicitly**, and a downstream consumer
must be able to read that purpose without inferring it from
context.

## 4. `ComparableSet.purpose` vocabulary

A `ComparableSet.purpose` answers the question *what role does
this particular comps set play in the valuer's approach?*
Suggested labels:

| Label | What this comps set is for |
| --- | --- |
| `beta_estimation` | Comparable companies whose equity-return covariance with the market is informative for the subject's beta. |
| `debt_capacity` | Comparable companies whose leverage / refinancing experience is informative for the subject's debt capacity. |
| `discount_rate_support` | Comparable companies / instruments whose risk profile supports the subject's discount-rate choice (impairment, DCF). |
| `valuation_multiple` | Comparable companies whose trading / transaction multiples (EV/EBITDA, P/E, P/B, etc.) are informative for the subject's multiple. |
| `margin_benchmark` | Comparable companies whose operating-margin band is informative for the subject's margin assumption. |

Different `ComparableSet.purpose` values may legitimately
populate **different** comparable lists for the same subject on
the same date. The protocol does **not** require the lists to be
identical, equal in size, or drawn from the same universe — only
that each set declares its own purpose, its own selection
rationale, and its own warning flags.

## 5. Comps selection dimensions

The selection dimensions are the small, named axes a
sophisticated valuer should be able to cite when defending a
comparable choice. They are *labels* — never thresholds, never
calibrated bands, never numeric scores. The protocol records
*which dimensions the valuer reasoned over*, not the underlying
numbers.

Suggested dimension vocabulary (jurisdiction-neutral):

| Dimension | Question it asks |
| --- | --- |
| `cash_flow_cyclicality` | How sensitive is the subject's cash flow to the macro cycle? |
| `operating_risk` | How concentrated, fragile, or contestable is the subject's operating model? |
| `input_cost_sensitivity` | How exposed is the subject to commodity, energy, labour, or other input shocks? |
| `asset_collateral_quality` | How readily can the subject's assets serve as collateral under typical lender practice? |
| `asset_redeployability` | How readily can the subject's assets be redeployed to alternative uses or buyers? |
| `cash_flow_visibility` | How forecastable is the subject's near-term cash-flow path? |
| `price_cycle_exposure` | How exposed is the subject's revenue / margin to a known price cycle (commodities, real-estate, semiconductor, shipping, etc.)? |
| `bankability` | How well does the subject fit a typical syndicated-loan / bond / CP underwriter's box? |
| `service_potential` | How material is the subject's residual *service potential* (relevant when the recoverable-amount ceiling is value in use rather than fair value less costs of disposal)? |
| `CGU_risk_profile` | What is the risk profile of the relevant cash-generating unit specifically (impairment-test context)? |

A protocol record may cite *any subset* of these dimensions; the
protocol does not require all of them on every record. The
binding rule is that **the dimensions cited are the ones the
valuer actually reasoned over** — fabricating coverage is itself
the kind of audit error this protocol is designed to surface.

The recommended `ComparableSet.purpose` → typical-dimension map
(illustrative, **not** prescriptive — a valuer may legitimately
deviate with a documented rationale):

| Purpose | Typical dimensions |
| --- | --- |
| `beta_estimation` | `cash_flow_cyclicality`, `operating_risk`, `input_cost_sensitivity`, `price_cycle_exposure` |
| `debt_capacity` | `asset_collateral_quality`, `asset_redeployability`, `cash_flow_visibility`, `bankability` |
| `discount_rate_support` | `CGU_risk_profile`, `service_potential`, `cash_flow_cyclicality` |
| `valuation_multiple` | `cash_flow_cyclicality`, `operating_risk`, `cash_flow_visibility` |
| `margin_benchmark` | `input_cost_sensitivity`, `operating_risk` |

A future `AdvancedValuationProtocolRecord` will likely store
both the cited dimensions and the recommended map's edge cases
as metadata so a reader can see *where the valuer departed from
the recommended mapping and why*.

## 6. Warning-flag vocabulary

The protocol surfaces well-known shapes of silent error as
**warning flags**. A warning flag is a *recorded concern*, not a
veto; the valuer can still proceed, but the audit trail makes the
concern explicit. Suggested labels:

| Flag | What it warns about |
| --- | --- |
| `purpose_mismatch` | A comps set is being reused across `ComparableSet.purpose` values that legitimately need different selection criteria (e.g., a beta-estimation comps set being used as the debt-capacity comps set). |
| `double_counting_risk` | The same risk is being adjusted for twice — typically once in a cash-flow projection (e.g., conservative case) and again in a discount-rate adjustment. |
| `cherry_picking_risk` | The comparable list looks engineered to support a target conclusion. The protocol does not enforce the warning; it surfaces it for review. |
| `target_capital_structure_misuse` | A *target* capital structure is being asserted in a context (e.g., debt-capacity review) where the *actual* observable structure is the relevant input, or vice versa. |
| `unexplained_comps_divergence` | The comps set's distribution diverges materially from the subject without an explanation in the rationale field. |
| `cash_flow_and_discount_rate_risk_overlap` | The cash-flow projection and the discount-rate construction are pricing the same risk dimension into the answer, producing a double-discount. |

Warning flags are *recorded labels*, never thresholds. The
protocol does not compute "is the divergence material?" and never
issues a binary fail; it gives the audit trail somewhere to
*name* the concern.

## 7. Boundary (binding)

This protocol records valuation evidence discipline. It does
**not**:

- compute a valuation truth, a fair value, or a target price;
- recommend an investment, a divestment, or a portfolio weight;
- decide whether an impairment loss should be recognised, at
  what amount, or against which CGU;
- determine a capital structure, a leverage band, or a debt
  schedule;
- form a credit decision, a covenant view, or a default opinion;
- provide accounting compliance under IFRS, US GAAP, J-GAAP, or
  any jurisdiction-specific standard;
- ingest real market, audit, broker, lender, or regulator data;
- apply Japan-specific calibration of any kind;
- emit any ledger record, mutate any source-of-truth book, or
  cross the v1.9.last public-prototype-freeze surface
  (`world_model.md` §69) on the default living-world sweep.

Every action this protocol *would* describe — selecting comps,
declaring purpose, warning about double-counting — is a
**recording** action. The protocol stores opinions, evidence, and
warnings; it does not produce truths.

## 8. Future integration

When (and if) a sophisticated actor type adopts this protocol,
the natural integration points are:

### 8.1 EvidenceResolver / ActorContextFrame (v1.12.3, §83)

A future `AdvancedValuationProtocolRecord` would cite — through
plain-id cross-references — the same evidence ids that the
v1.12.3 `EvidenceResolver` resolves into an `ActorContextFrame`
for the relevant actor on the relevant date. Specifically:

- `evidence_market_condition_ids` — the period's market-context
  records the comps choice was conditioned on;
- `evidence_market_environment_state_ids` — the period's nine
  compact regime labels (v1.12.2);
- `evidence_industry_condition_ids` — the demand context for
  the comps universe;
- `evidence_firm_state_ids` — the subject's latent
  pressure / readiness state;
- `evidence_signal_ids` — corporate / pressure / review signals
  the valuer cited;
- `evidence_valuation_ids` — *prior* valuation records the new
  protocol record references (chain link); the protocol record
  itself is not a `ValuationRecord` replacement.

Because the protocol record only cites ids, the
`ActorContextFrame` substrate is sufficient — no new resolution
helper is required at the FWE level.

### 8.2 Attention-conditioned valuation (anticipated v1.12.5)

When v1.12.5 ships an attention-conditioned valuation lite, the
default valuation refresh continues to *not* require the
advanced protocol. A separate, opt-in advanced-actor variant may
take the v1.12.5 `ActorContextFrame` plus an
`AdvancedValuationProtocolRecord` and produce an *opinionated*
valuation — still labels-only, still no real financial number.
The two paths should remain composable but distinct: the default
path is bounded and unsurprising; the advanced path is rich and
auditable.

### 8.3 Valuation assumption audit records

A future `ValuationAssumptionAuditRecord` (deferred) could pair
with the protocol to track *which assumption changed between two
valuation versions*. The protocol's warning flags would feed
that audit record's *what we already warned ourselves about*
column, and a downstream consumer (LLM-agent reviewer, governance
report generator) could read both records in a single pass.

### 8.4 Advanced-actor-only adoption (binding)

The protocol is **opt-in for advanced actor types** only. The
default v1.9 living reference world's investor and bank profiles
must continue to work without the protocol. Adding the protocol
to the default path is explicitly out of scope:

- the default investor's valuation refresh lite is intentionally
  a thin opinionated synthetic claim;
- the default bank's credit review note is intentionally a thin
  opinionated synthetic diagnostic;
- forcing the default path through the protocol's warning-flag
  vocabulary would import accounting and credit-policy
  judgements the FWE is explicitly *not* taking.

A future advanced-actor variant (e.g., `investor:reference_advanced_protocol_a`)
or a future advanced-mechanism variant
(`run_reference_advanced_valuation_review`) would be the
adoption path, gated by an opt-in actor-profile flag.

## 9. Position in the v1 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.1 Valuation / fundamentals separation | Code (price ≠ valuation ≠ fundamental). | Shipped |
| v1.9 Valuation refresh lite | Code (synthetic non-binding valuation). | Shipped |
| v1.12.3 EvidenceResolver / ActorContextFrame | Code (attention bottleneck substrate). | Shipped |
| **v1.x Valuation Protocol — Comps Purpose Separation** | **Docs-only. Advanced-actor-only.** | **This document** |
| v1.12.4 Attention-conditioned investor intent (anticipated) | Code. | Planned |
| v1.12.5 Attention-conditioned valuation lite (anticipated) | Code. | Planned |
| v1.12.6 Attention-conditioned bank credit review (anticipated) | Code. | Planned |
| v1.12.7 Next-period attention feedback (anticipated) | Code. | Planned |
| Advanced valuation protocol record (deferred) | Code. Opt-in advanced-actor variant. | Not started |
| Valuation assumption audit record (deferred) | Code. | Not started |
| v2.0 Japan public-data calibration design gate | — | Not started |

This note's adoption is gated on (a) the v1.12.4 → v1.12.7
attention-conditioned mechanism path landing first, so the
protocol has a substrate to attach to, and (b) at least one
advanced actor type wanting to record at this discipline level.
Until both gates open, the protocol stays as docs.

## 10. Summary

- The same word *comps* can mean different things depending on
  *purpose*; pretending one set serves all purposes is an audit
  shape of error.
- The FWE's answer is to record purpose, evidence, rationale,
  and warning flags — not to compute a valuation truth.
- The protocol is opt-in for advanced actor types; the default
  v1.9 living reference world is unaffected.
- The protocol composes with the v1.12.3 `EvidenceResolver`
  substrate via plain-id cross-references; no new resolution
  helper is required.
- The protocol's binding rule is **discipline, not arithmetic**:
  the same valuation work must declare its purpose, its
  selection dimensions, and its warnings explicitly, and a
  downstream reader must be able to see *what the valuer was
  solving for* without inferring it from context.
