# v1.13.0 Generic Central Bank Settlement Infrastructure (docs-only design note)

This document is the design rationale for a **generic, jurisdiction-neutral
central-bank settlement and interbank-liquidity vocabulary** that public FWE
will adopt across the v1.13.x sequence. It is **docs-only**. No code, no
records, no books, no calculation, no decision lives behind this note today.
The full v1.13 sequence — `SettlementAccountBook` / `ReserveAccountBook`
storage (anticipated v1.13.1), `PaymentInstructionRecord` / `SettlementEvent`
storage (anticipated v1.13.2), `InterbankLiquidityState` storage and
classifier (anticipated v1.13.3), `CentralBankOperationSignal` /
`CollateralEligibilitySignal` storage (anticipated v1.13.4), and the
`MarketEnvironment` integration (anticipated v1.13.5) — are **not**
introduced or gated by this note; they are documented here as planned and
shipped one milestone at a time.

For the v1 behaviour boundary that this note sits inside, see
[`v1_behavior_boundary.md`](v1_behavior_boundary.md). For the public /
private layer split this note depends on, see
[`public_private_boundary.md`](public_private_boundary.md). For the
v1.12.2 market environment substrate the v1.13.5 cross-link will attach to,
see `world_model.md` §82. For the v1.12.0 firm financial latent state the
v1.13.5 cross-link will also attach to, see `world_model.md` §80.

## 1. Why this exists

A common silent error in financial-world simulation is treating the
**central-bank settlement substrate** as if it were either (a) a black
box that produces "interest rates" and nothing else, or (b) a
Japan-specific real-system mapping (BOJ-NET, BOJ current accounts, JGB
DvP) bolted onto the public engine. Both shapes are wrong for public
FWE.

The substrate that actually matters for the simulation's behaviour is
**generic**:

- there exist **settlement accounts** at a central-bank-shaped entity,
  held by participant banks, clearing members, and similar
  counterparties;
- there exist **payment instructions** that move from one settlement
  account toward another with a priority, a horizon, and a status;
- there exist **settlement events** that emit when an instruction
  changes status — queued, completed, partial, failed — with a
  cause label;
- there exists an **interbank liquidity tone** that downstream actors
  read as a compact regime label (`abundant` / `normal` / `tight` /
  `stressed`) without ever seeing a real funding rate;
- there exist **collateral-eligibility labels** and **central-bank
  operation labels** that bracket what kinds of assets can serve as
  collateral and what kind of market operation the central-bank
  shaped entity is signalling.

None of those items requires Japan calibration to *exist* in a public
substrate; they all become Japan-shaped only when private JFWE (v2)
maps them onto BOJ-NET, BOJ current accounts, JGB settlement, the BOJ
collateral framework, and the actual operations menu. Mapping is a v2
concern; **vocabulary is a public concern**, and the public FWE has
been silent on it through v1.12.4.

The v1.13.x sequence's response is **not** to compute settlement,
payments, reserves, balance sheets, monetary-policy decisions, or
collateral haircuts. The response is to give downstream consumers — a
future LLM-agent step, a downstream attention-conditioned mechanism, a
private-layer v2 calibration — a way to **read the substrate as
labels**: what kind of account, what kind of instruction, what
liquidity tone, what collateral tier, what central-bank operation
direction. The arithmetic stays out.

This note is the **design pin** for the eight vocabulary items the
v1.13.x sequence will introduce as records / books / signals. None of
them computes anything in v1.13.0; v1.13.0 ships only this document.

## 2. Scope (what this design does and does not do)

This is a **vocabulary-and-discipline** specification.

It defines:

- a **`CentralBankSettlementSystem`** placeholder for the abstract
  substrate name a future v1.13.1 record / book will instantiate;
- a **`SettlementAccountRecord`** vocabulary for one account at the
  central-bank-shaped entity, held by a participant;
- a **`SettlementAccountBook`** / **`ReserveAccountBook`** placeholder
  for the append-only storage layer the v1.13.1 milestone will ship;
- a **`PaymentInstructionRecord`** vocabulary for one payment
  instruction routed across settlement accounts;
- a **`SettlementEvent`** vocabulary for the emission of a
  settlement-status change;
- an **`InterbankLiquidityState`** vocabulary for a synthetic compact
  regime label about interbank liquidity;
- a **`CollateralEligibilitySignal`** vocabulary for a synthetic
  *signal* labeling whether a class of asset is eligible to serve as
  central-bank collateral, plus a haircut tier label;
- a **`CentralBankOperationSignal`** vocabulary for a synthetic
  *signal* labeling a central-bank market operation direction and
  horizon.

It deliberately does **not**:

- introduce or recommend BOJ-NET, BOJ current accounts, JGB
  settlement, JSCC, JASDEC, or any other Japan-specific real-system
  mapping (those go to private JFWE v2);
- execute payments, RTGS settlement, or intraday liquidity loans;
- compute central-bank accounting, balance-sheet identities, reserve
  totals, or seigniorage;
- execute securities settlement, DvP / PvP delivery, or repo legs;
- compute collateral valuation, haircut percentages, or margin
  numbers;
- decide monetary policy (rate setting, reserve-requirement changes,
  QE / QT execution);
- ingest real central-bank data or apply Japan-specific calibration of
  any kind;
- dispatch an operation, signal, or instruction to an LLM agent or
  any external solver;
- emit any ledger record, mutate any source-of-truth book, or cross
  any boundary already pinned by `v1_behavior_boundary.md` or
  `world_model.md` §69 (v1.9.last freeze) / §83 (v1.12.3 evidence
  resolver).

The substrate is *labels and ids*. It records what kind of account,
what kind of instruction, what liquidity tone; it does not produce a
balance, a settled amount, a reserve number, or a policy decision.

## 3. `CentralBankSettlementSystem` — abstract substrate name

`CentralBankSettlementSystem` is the **vocabulary placeholder** for the
substrate name a future v1.13.1 record / book will instantiate. At
v1.13.0 it is a *name only* — there is no class, no record type, no
ledger event, no book, no kernel field. The placeholder pins the
following discipline:

- the substrate is **abstract and singular per simulated jurisdiction**
  in the public engine: a public FWE world has at most one
  `CentralBankSettlementSystem` shape, identified by its synthetic id;
- the substrate is **jurisdiction-neutral** in v1.13.x: the substrate
  id is a synthetic label (e.g., `cbss:reference_alpha`), never
  `boj_net`, never any real-system identifier;
- the substrate is **storage-and-routing-shaped, not balance-shaped**:
  the instantiated record carries no balance, no available credit, no
  total reserves, no policy rate, no operating-account aggregate;
- the substrate is **not the central bank itself**: the central
  bank-shaped institutional entity (an `InstitutionProfile` in v1.3
  vocabulary, or a future `CentralBankProfile` in v2) is a separate
  concept — the settlement system is the rails, not the issuer.

A future v1.13.1 milestone may instantiate the substrate as a
`CentralBankSettlementSystemRecord` or a kernel-level config field; the
shape choice is left to v1.13.1. v1.13.0 only pins the name and the
boundaries above.

## 4. `SettlementAccountRecord` — one account at the substrate

`SettlementAccountRecord` is the vocabulary for **one account at the
central-bank settlement substrate held by a participant**. Suggested
labels (jurisdiction-neutral, illustrative):

| Label | What it carries |
| --- | --- |
| `account_id` | Synthetic id for the account (e.g., `cb_account:reference_bank_a`). |
| `holder_id` | Synthetic id of the account holder (commercial bank, clearing member, etc.). |
| `holder_type` | One of `participant_bank`, `clearing_member`, `government_entity`, `other_central_bank`, `policy_counterparty`. |
| `account_type` | One of `reserve_account`, `settlement_account`, `restricted_account`, `policy_facility_account`. |
| `status` | One of `active`, `frozen`, `closed`, `provisional`. |
| `as_of_date` | Effective-as-of date for the record (vintage discipline). |
| `metadata` | Free-form metadata dict. |

**Anti-fields (binding)** — `SettlementAccountRecord` does **not**
carry:

- `balance`, `current_balance`, `closing_balance`, `opening_balance`,
  or any balance-shaped scalar;
- `available_credit`, `intraday_credit_used`, `overdraft_remaining`,
  or any credit-line scalar;
- `pending_settlement_amount`, `queued_settlement_amount`, or any
  amount-shaped scalar;
- `interest_accrued`, `interest_rate`, `accrual_basis`, or any
  interest-shaped scalar;
- `currency_value`, `fx_rate`, `currency_code` (currency belongs to
  the v1.1 valuation / numeraire layer, not to the settlement-account
  record);
- any other real number that would make the record a balance-sheet
  line.

A future `SettlementAccountBook` (anticipated v1.13.1) is **append-only**
in the v0 ledger sense: status transitions emit new records, never
mutating prior records. The book's read API is plain-id lookup and
filter-by-holder / filter-by-type / filter-by-status; there is no
"current balance" query.

## 5. `SettlementAccountBook` / `ReserveAccountBook` — storage placeholder

`SettlementAccountBook` and `ReserveAccountBook` are **storage
placeholder names** for the append-only books a future v1.13.1
milestone will ship. The dual name reflects two viewpoints:

- **`SettlementAccountBook`** — the routing / payment-rail viewpoint.
  Reads index by `account_id`, by `holder_id`, by `account_type`.
- **`ReserveAccountBook`** — the *reserve-account-shaped subset*
  viewpoint. The same underlying storage may be projected through a
  reserve-account filter for downstream consumers that only care about
  `account_type == "reserve_account"`. The reserve-account viewpoint
  does **not** add new fields, does **not** compute aggregate reserves,
  and does **not** produce a balance number.

At v1.13.0 these are vocabulary only. The exact storage shape (one
book vs. one book + one view, dataclass vs. mapping, ledger event type
naming) is left to v1.13.1; v1.13.0 only pins:

- both viewpoints are **append-only**;
- both viewpoints are **read-only from the FWE-engine perspective**
  (no autonomous balance update, no autonomous status flip);
- neither viewpoint computes a *balance* or an *aggregate reserve
  total* — those are private JFWE (v2) concerns once Japan
  calibration is wired;
- the books cross-reference the
  `CentralBankSettlementSystem` substrate id (per §3) so a reader can
  see *which substrate* an account belongs to in a multi-substrate
  future (deferred beyond v1).

## 6. `PaymentInstructionRecord` — one payment instruction

`PaymentInstructionRecord` is the vocabulary for **one payment
instruction routed across settlement accounts**. Suggested labels
(jurisdiction-neutral, illustrative):

| Label | What it carries |
| --- | --- |
| `instruction_id` | Synthetic id for the instruction. |
| `from_account_id` | Synthetic id of the originating settlement account. |
| `to_account_id` | Synthetic id of the receiving settlement account. |
| `as_of_date` | Effective-as-of date for the instruction (vintage discipline). |
| `instruction_type` | One of `interbank_transfer`, `securities_settlement_leg`, `repo_leg`, `liquidity_provision_leg`, `liquidity_absorption_leg`, `policy_facility_leg`. |
| `priority` | One of `urgent`, `normal`, `bulk`. |
| `status` | One of `queued`, `pending`, `settled`, `partial`, `rejected`, `cancelled`. |
| `time_horizon` | One of `intraday`, `same_day`, `next_day`, `multi_day`. |
| `metadata` | Free-form metadata dict. |

**Anti-fields (binding)** — `PaymentInstructionRecord` does **not**
carry:

- `amount`, `notional`, `principal`, or any amount-shaped scalar;
- `currency_value`, `fx_rate`, `settlement_value`, or any
  currency-converted scalar;
- `fee`, `interest`, `accrual`, or any compensation scalar;
- `collateral_value`, `haircut_amount`, `margin_amount`, or any
  collateral-arithmetic scalar;
- a `routing_hash`, `swift_message`, `iso20022_payload`, or any real
  message-format payload (real-format mapping belongs to v2 / v3);
- any other real number that would let a downstream actor reconstruct
  a settled-amount time series.

The instruction record is **a labelled status object**, not an
executed payment. v1.13.x does *not* execute payments. A separate
private-layer v2 milestone may add an executed-payment shadow book on
top of the public substrate; that addition is out of scope for public
FWE.

## 7. `SettlementEvent` — settlement status-change emission

`SettlementEvent` is the vocabulary for the **emission of a
settlement-status change** on a `PaymentInstructionRecord`. Suggested
labels (jurisdiction-neutral, illustrative):

| Label | What it carries |
| --- | --- |
| `event_id` | Synthetic id for the event. |
| `instruction_id` | Synthetic id of the instruction whose status changed. |
| `as_of_date` | Effective-as-of date / time for the event (vintage discipline). |
| `event_type` | One of `settlement_queued`, `settlement_pending`, `settlement_completed`, `settlement_partial`, `settlement_failed`, `settlement_cancelled`. |
| `cause_label` | One of `routine`, `liquidity_shortfall`, `collateral_shortfall`, `cutoff_breach`, `counterparty_freeze`, `system_throttle`, `policy_intervention_pause`. |
| `metadata` | Free-form metadata dict. |

**Anti-fields (binding)** — `SettlementEvent` does **not** carry:

- `settled_amount`, `partial_amount`, `outstanding_amount`, or any
  amount-shaped scalar;
- `expected_settlement_amount`, `loss_given_failure`, or any
  expected-value scalar;
- `delay_minutes`, `latency_microseconds`, or any throughput /
  latency scalar (RTGS / large-value-system performance is a v2
  concern);
- any `fee`, `interest`, or `compensation` scalar;
- any other real number that would let a downstream actor reconstruct
  a system throughput / loss-rate time series.

The event is **a labelled status emission**, not a settlement record
in the bookkeeping sense. The pairing — `PaymentInstructionRecord`
plus a chain of `SettlementEvent` records on that instruction — is the
substrate's full labelling vocabulary; the substrate's *amount*
viewpoint is intentionally absent.

## 8. `InterbankLiquidityState` — compact liquidity-tone label

`InterbankLiquidityState` is the vocabulary for **a synthetic compact
regime label about interbank liquidity** at a given as-of date.
Suggested labels (jurisdiction-neutral, illustrative):

| Label | What it carries |
| --- | --- |
| `liquidity_state_id` | Synthetic id for the state record. |
| `as_of_date` | Effective-as-of date. |
| `tone_label` | One of `abundant`, `normal`, `tight`, `stressed`. |
| `funding_pressure_label` | One of `low`, `medium`, `high`. |
| `cb_intervention_label` | One of `none`, `routine_ops`, `emergency_facility`, `extraordinary_facility`. |
| `metadata` | Free-form metadata dict. |

`InterbankLiquidityState` is a **regime label**, in the same shape as
the v1.12.2 `MarketEnvironmentStateRecord`'s nine compact regime
labels. It is not a funding rate, not a turnover number, not a
volatility number. A future v1.13.3 milestone will ship the storage
layer plus a small documented classifier that derives the label from
an `InterbankLiquidityState` *input view* over the substrate (e.g.,
fraction of `SettlementEvent` records with `cause_label ==
"liquidity_shortfall"` over a window, fraction of instructions with
`status == "settled"` by a cutoff). The classifier maps to *labels
only* — never to a numeric tone-strength scalar.

**Anti-fields (binding)** — `InterbankLiquidityState` does **not**
carry:

- a `funding_rate`, `tonar_proxy`, `repo_rate`, `o_n_rate`, or any
  rate-shaped scalar;
- a `turnover`, `volume`, `count_settled`, or any flow-shaped scalar
  (counts may be referenced inside the classifier but never *stored*
  on the state record);
- a `volatility`, `spread`, or any second-moment scalar;
- any other real number that would let a downstream actor reconstruct
  a funding-cost time series.

`InterbankLiquidityState` cross-references the v1.12.2
`MarketEnvironmentStateRecord` and the v1.12.0 `FirmFinancialStateRecord`
through **plain-id slots planned for v1.13.5** (e.g.,
`evidence_market_environment_state_ids`,
`evidence_firm_financial_state_ids`). The cross-link is a *citation*,
never a calculation: the liquidity state never reads a market-environment
record's content, only its id.

## 9. `CollateralEligibilitySignal` — eligibility + haircut-tier label

`CollateralEligibilitySignal` is the vocabulary for **a synthetic
signal labeling whether a class of asset is eligible to serve as
central-bank collateral**, plus a haircut tier label. Suggested labels
(jurisdiction-neutral, illustrative):

| Label | What it carries |
| --- | --- |
| `signal_id` | Synthetic id for the signal. |
| `as_of_date` | Effective-as-of date. |
| `eligibility_label` | One of `eligible`, `eligible_with_haircut`, `restricted`, `ineligible`. |
| `haircut_tier_label` | One of `tier_a`, `tier_b`, `tier_c`, `tier_special`. |
| `metadata` | Free-form metadata dict (e.g., the abstract asset-class label the signal is about). |

**Anti-fields (binding)** — `CollateralEligibilitySignal` does **not**
carry:

- a `haircut_pct`, `haircut_bps`, `haircut_amount`, or any
  haircut-numeric scalar;
- a `collateral_value`, `mark_to_market_value`, or any valuation
  scalar (those belong to the v1.1 valuation / v1.x valuation-protocol
  surface, not to the eligibility signal);
- a `margin_required`, `initial_margin`, `variation_margin`, or any
  margin-arithmetic scalar;
- a `concentration_limit`, `position_limit`, or any limit-arithmetic
  scalar;
- any other real number that would let a downstream actor reconstruct
  a collateral-haircut schedule.

The signal is a **labelled eligibility statement**, not a haircut
calculator. A future v1.13.4 milestone will ship the storage layer
plus the small documented mapping from abstract asset-class labels to
eligibility / tier labels; the mapping is illustrative and explicitly
**not** a real-system collateral framework. Real-collateral-framework
mapping is private JFWE (v2).

## 10. `CentralBankOperationSignal` — operation direction / horizon label

`CentralBankOperationSignal` is the vocabulary for **a synthetic signal
labeling a central-bank market operation**. Suggested labels
(jurisdiction-neutral, illustrative):

| Label | What it carries |
| --- | --- |
| `signal_id` | Synthetic id for the signal. |
| `as_of_date` | Effective-as-of date. |
| `operation_label` | One of `liquidity_provision`, `liquidity_absorption`, `outright_purchase_synthetic`, `outright_sale_synthetic`, `lending_facility_synthetic`, `deposit_facility_synthetic`. |
| `direction_label` | One of `provision`, `absorption`, `neutral`. |
| `time_horizon` | One of `intraday`, `same_day`, `next_day`, `multi_day`. |
| `metadata` | Free-form metadata dict. |

**Anti-fields (binding)** — `CentralBankOperationSignal` does **not**
carry:

- an `operation_amount`, `notional`, `purchase_amount`, `sale_amount`,
  or any amount-shaped scalar;
- a `policy_rate`, `target_rate`, `corridor_top`, `corridor_bottom`,
  `o_n_rate`, or any rate-shaped scalar;
- a `monetary_policy_stance` numeric, a `dovish_score`, a
  `hawkish_score`, or any policy-stance scalar;
- a `qe_pace`, `qt_pace`, `balance_sheet_target`, or any
  balance-sheet-target scalar;
- any other real number that would let a downstream actor reconstruct
  a monetary-policy decision.

The signal is a **labelled operation emission**, not a monetary-policy
decision and not an executed market operation. Public FWE does **not**
make monetary-policy decisions in v1.13.x (or anywhere in v1, full
stop). A future private JFWE (v2) layer may map the operation_label
vocabulary onto BOJ market-operation menu items; that mapping is out
of scope for public FWE.

## 11. Public / private boundary (binding)

The v1.13.x sequence sits inside the three-layer split already pinned by
[`public_private_boundary.md`](public_private_boundary.md):

- **Public FWE (v1.13.x)** — generic synthetic abstraction; the
  vocabulary defined in §3 – §10 lives here. Jurisdiction-neutral; no
  real-system mapping; no real central-bank data; no Japan
  calibration.
- **Private JFWE (v2)** — BOJ-NET / BOJ current accounts / JGB
  settlement / Japan-specific calibration. v2 maps the public
  abstraction onto Japanese reality: `holder_type` →
  BOJ-current-account-holder taxonomy; `account_type` → BOJ reserve
  vs. settlement vs. restricted; `instruction_type` → BOJ-NET message
  taxonomy; `cause_label` → BOJ outage / cutoff / intervention
  taxonomy; `operation_label` → BOJ market-operation menu items
  (outright JGB purchase, securities lending facility, complementary
  deposit facility, complementary lending facility, etc.). v2 is the
  only layer where a real central-bank-system identifier may appear.
- **Proprietary JFWE (v3)** — proprietary liquidity assumptions,
  non-public settlement behaviour, expert-data extensions. v3 is the
  only layer where a proprietary calibration of the
  `InterbankLiquidityState` classifier, of the
  `CollateralEligibilitySignal` haircut-tier mapping, or of the
  `CentralBankOperationSignal` direction inference may appear. v3 is
  never public.

The binding rule is that **every Japan-shaped concept is private**. If
a contributor is tempted to add `boj_net`, `boj_current_account`,
`jgb`, `tonar`, `mutan`, `complementary_deposit_facility`,
`complementary_lending_facility`, or any other real-system identifier
to the public vocabulary, that addition does not belong in v1.13.x —
it belongs in v2.

## 12. Boundary (binding)

The v1.13.x sequence records central-bank settlement substrate
discipline. It does **not**:

- introduce or recommend BOJ-NET, BOJ current accounts, JGB
  settlement, JSCC, JASDEC, TARGET2, Fedwire, CHAPS, EBA STEP2, or any
  other real-system mapping (those are v2 / v3 territory);
- execute payments, RTGS settlement, intraday-credit lending, or
  end-of-day net-settlement runs;
- compute central-bank accounting, balance-sheet identities,
  consolidated-reserve totals, monetary-base aggregates, or
  seigniorage;
- execute securities settlement, DvP / PvP delivery, or repo
  open / close legs;
- compute collateral valuation, haircut percentages, margin
  requirements, or concentration limits;
- decide monetary policy — rate setting, reserve-requirement changes,
  QE / QT execution, forward guidance, or any policy-stance number;
- ingest real central-bank data (no public BOJ time series, no public
  Fed time series, no public ECB time series — none, anywhere,
  v1.13.x);
- apply Japan-specific calibration of any kind;
- dispatch a payment, a settlement event, an operation signal, or an
  eligibility signal to an LLM agent or any external solver;
- emit any ledger record, mutate any source-of-truth book, or cross
  the v1.9.last public-prototype-freeze surface (`world_model.md`
  §69) at v1.13.0;
- compute or attach any *behaviour probability* — the substrate is
  label / id machinery, not a behaviour model.

Every concept this design *would* describe — accounts, instructions,
events, liquidity tone, collateral eligibility, operation direction —
is a **labelling** concept. The substrate stores labels, ids, and
status; it does not produce balances, amounts, rates, or policy
decisions.

## 13. Future integration

When (and if) the v1.13.x sequence ships its records / books / signals
across v1.13.1 → v1.13.4, the natural integration points are:

### 13.1 EvidenceResolver / ActorContextFrame (v1.12.3, §83)

A future actor — for example, an investor who reads interbank
liquidity tone before forming an investor-intent signal, or a bank
who reads its own settlement-account status before forming a credit
review note — will cite the v1.13.x record / signal ids through the
v1.12.3 `EvidenceResolver` substrate's plain-id cross-reference
mechanism. Specifically:

- `evidence_settlement_account_ids` — the period's
  `SettlementAccountRecord` ids the actor cited;
- `evidence_payment_instruction_ids` — the period's
  `PaymentInstructionRecord` ids the actor cited;
- `evidence_settlement_event_ids` — the period's `SettlementEvent`
  ids the actor cited;
- `evidence_interbank_liquidity_state_ids` — the period's
  `InterbankLiquidityState` ids the actor cited;
- `evidence_collateral_eligibility_signal_ids` — the period's
  `CollateralEligibilitySignal` ids the actor cited;
- `evidence_central_bank_operation_signal_ids` — the period's
  `CentralBankOperationSignal` ids the actor cited.

Because the cross-link is plain-ids, the v1.12.3 substrate is
sufficient — no new resolution helper is required at the FWE level
beyond the existing prefix-dispatch table extension a future v1.13.x
milestone will add for the new prefixes.

### 13.2 MarketEnvironment integration (anticipated v1.13.5)

The v1.13.5 milestone will wire **type-correct additive cross-link
slots** between the v1.13.x substrate and the v1.12.x environment
substrate, mirroring the v1.12.2 pattern that wired
`MarketEnvironmentStateRecord` into `FirmFinancialStateRecord` /
`InvestorIntentRecord` / `CorporateStrategicResponseCandidate`.
Specifically:

- `evidence_market_environment_state_ids` on
  `InterbankLiquidityState` — the period's market-environment
  context the liquidity state was conditioned on;
- `evidence_firm_financial_state_ids` on
  `InterbankLiquidityState` — the period's firm-state context
  surface that overlaps with funding pressure;
- `evidence_interbank_liquidity_state_ids` on
  `MarketEnvironmentStateRecord` (additive, deferred) — the period's
  liquidity context the environment label may cite.

The v1.13.5 cross-link is **citation-only**: every slot is a plain-id
list. The v1.13.x records never read a market-environment record's
content; the market-environment record never reads a v1.13.x record's
content. The cross-link is the audit trail, not a calculation.

### 13.3 Default living-world adoption (binding)

The default v1.9 living reference world's investor / bank profiles
must continue to work without the v1.13.x substrate. Adding the
substrate to the default per-period sweep is explicitly out of scope
for v1.13.0:

- the default living-world fixture has no central-bank-shaped entity,
  no settlement accounts, and no payment instructions, by design —
  the public-prototype-freeze surface (§69) does not include
  settlement infrastructure;
- adding the substrate to the default sweep would change the
  per-period record count, the per-run record window, and the
  `living_world_digest`, which the public-prototype freeze pins
  bit-for-bit until v1.10.x or later milestones explicitly widen;
- forcing the default sweep through a settlement-substrate phase
  would import settlement-system shape choices the FWE is explicitly
  *not* taking at the public-prototype layer.

A future opt-in living-world variant (e.g.,
`run_living_reference_world_with_settlement_substrate`) gated by an
opt-in fixture flag would be the adoption path. v1.13.0 does not ship
that opt-in path; v1.13.5 will revisit it.

### 13.4 Private JFWE (v2) adoption path

Private JFWE (v2) is the **adoption path for Japan-shaped
calibration** of the v1.13.x vocabulary. v2 will:

- map `holder_type` to the BOJ-current-account-holder taxonomy;
- map `account_type` to BOJ reserve / settlement / restricted account
  shapes;
- map `instruction_type` to the BOJ-NET message taxonomy;
- map `cause_label` to the BOJ outage / cutoff / intervention
  taxonomy;
- map `operation_label` to the BOJ market-operation menu;
- map `eligibility_label` and `haircut_tier_label` to the BOJ
  collateral framework's eligibility list and haircut schedule.

Each mapping is private; none of the mappings ship in public FWE.
v1.13.x's vocabulary is designed so that the v2 mapping is a *table
lookup*, not a refactor of the public records.

## 14. Position in the v1 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.12.0 → v1.12.2 (firm state / investor intent / market environment) | Code (§80 → §82). | Shipped |
| v1.12.3 EvidenceResolver / ActorContextFrame | Code (§83). | Shipped |
| v1.x Valuation Protocol — Comps Purpose Separation | Docs-only (§84). Advanced-actor-only. | Shipped |
| v1.12.4 Attention-conditioned investor intent | Code (§85). | Shipped |
| **v1.13.0 Generic central bank settlement infrastructure design** | **Docs-only (this note + §86). Jurisdiction-neutral substrate vocabulary.** | **Shipped (this note)** |
| v1.13.1 `SettlementAccountBook` / `ReserveAccountBook` storage | Code. | Planned |
| v1.13.2 `PaymentInstructionRecord` + `SettlementEvent` storage | Code. | Planned |
| v1.13.3 `InterbankLiquidityState` storage + classifier | Code. | Planned |
| v1.13.4 `CentralBankOperationSignal` / `CollateralEligibilitySignal` storage | Code. | Planned |
| v1.13.5 `MarketEnvironment` integration (v1.12.2 ↔ v1.13.x cross-link) | Code. | Planned |
| v1.13.last Freeze | Docs. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

This note's adoption is gated on (a) the v1.12.4 attention-conditioned
mechanism path landing first (already shipped), so the substrate has
an evidence-resolver to attach to, and (b) at least one downstream
mechanism wanting to read settlement labels. Until both gates open
simultaneously for a specific v1.13.1 → v1.13.4 milestone, the
vocabulary stays as docs.

The test count, per-period record count, per-run window, and
`living_world_digest` are **unchanged** from v1.12.4 — v1.13.0 is
docs-only and ships no code, no record, no test, no fixture.

## 15. Summary

- The substrate that matters for a financial-world simulation's
  central-bank settlement layer is **generic, label-shaped, and
  jurisdiction-neutral**; pretending it is either a black box or a
  Japan-specific real-system mapping is the wrong shape for public
  FWE.
- The FWE's answer is to define eight vocabulary items —
  `CentralBankSettlementSystem`, `SettlementAccountRecord`,
  `SettlementAccountBook` / `ReserveAccountBook`,
  `PaymentInstructionRecord`, `SettlementEvent`,
  `InterbankLiquidityState`, `CollateralEligibilitySignal`,
  `CentralBankOperationSignal` — that record *what kind* of account,
  instruction, event, tone, eligibility, and operation the substrate
  carries, never *how much*.
- The substrate is **strictly bounded**: no BOJ-NET / BOJ current
  accounts / JGB settlement, no payment execution, no RTGS settlement
  mechanics, no central-bank accounting, no securities settlement
  execution, no DvP / PvP execution, no collateral valuation, no
  haircut calculation, no monetary-policy decisions, no real data
  ingestion, no Japan calibration, no LLM-agent execution, no
  behaviour probabilities.
- The substrate composes with the v1.12.3 `EvidenceResolver` (§83)
  via plain-id cross-references and with the v1.12.2
  `MarketEnvironmentStateRecord` and v1.12.0 `FirmFinancialStateRecord`
  via type-correct additive slots planned for v1.13.5; no new
  resolution helper or calculation primitive is required at the FWE
  level.
- The public / private boundary is binding: **every Japan-shaped
  calibration is private JFWE (v2 / v3)**; the public engine carries
  vocabulary only.
- v1.13.0 is **docs-only**: no code, no records, no books, no tests,
  no fixture changes, no `living_world_digest` movement; the v1.13.1
  → v1.13.last milestones each ship one storage / classifier / signal
  layer at a time.
