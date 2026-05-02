# v1.13 Generic Central-Bank Settlement Infrastructure — Summary

This document closes the v1.13 sequence of FWE. The sequence
ships a **jurisdiction-neutral, label-only, synthetic** substrate
for central-bank-shaped settlement, interbank-liquidity, and
collateral-eligibility records, plus a citation-only cross-link
to the v1.12.x environment substrate. v1.13.last itself is
docs-only on top of the v1.13.1 → v1.13.5 code freezes.

This is **not** a payment system, **not** a market simulator,
**not** a credit-risk model, and **not** a Japan calibration. It
is a small set of immutable record types, append-only books, and
ledger event types. The substrate executes nothing.

## Sequence map

| Milestone   | Module                           | Adds                                                                                                                                                                                       |
| ----------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| v1.13.0     | docs only (§87)                  | Generic central-bank settlement-infrastructure design vocabulary; explicitly out of scope: any real-system mapping, real balance, payment execution, monetary-policy decision.             |
| v1.13.1     | `world/settlement_accounts.py`   | `SettlementAccountRecord` + `SettlementAccountBook`. Ledger event `settlement_account_registered`. Storage only.                                                                            |
| v1.13.2     | `world/settlement_payments.py`   | `PaymentInstructionRecord` + `SettlementEventRecord` + `SettlementInstructionBook`. Ledger events `payment_instruction_registered` + `settlement_event_recorded`. Synthetic-size labels.    |
| v1.13.3     | `world/interbank_liquidity.py`   | `InterbankLiquidityStateRecord` + `InterbankLiquidityStateBook`. Ledger event `interbank_liquidity_state_recorded`. Four label fields + `[0,1]` synthetic confidence + plain-id provenance. |
| v1.13.4     | `world/central_bank_signals.py`  | `CentralBankOperationSignalRecord` + `CollateralEligibilitySignalRecord` + `CentralBankSignalBook`. Two ledger events. Tier labels — never percentages.                                     |
| v1.13.5     | additive cross-link              | `MarketEnvironmentStateRecord` gains `evidence_interbank_liquidity_state_ids` slot; bank credit review helper accepts `explicit_interbank_liquidity_state_ids`; living-world emits one state per bank per period. |
| v1.13.last  | docs only                        | This summary, §98 in `docs/world_model.md`, `RELEASE_CHECKLIST.md` snapshot, `performance_boundary.md` update, `README.md` headline.                                                        |

## What v1.13 substrate is

- **Records:** seven new immutable-dataclass record types
  (settlement account, payment instruction, settlement event,
  interbank liquidity state, central-bank operation signal,
  collateral eligibility signal — plus the v1.13.5 additive slot
  on `MarketEnvironmentStateRecord`).
- **Books:** four new append-only books wired into
  `WorldKernel`: `settlement_accounts`, `settlement_payments`,
  `interbank_liquidity`, `central_bank_signals`. Each book emits
  one ledger record per add call and refuses to mutate any
  other source-of-truth book.
- **Ledger events:** six new record types
  (`settlement_account_registered`,
  `payment_instruction_registered`, `settlement_event_recorded`,
  `interbank_liquidity_state_recorded`,
  `central_bank_operation_signal_recorded`,
  `collateral_eligibility_signal_recorded`).
- **Cross-link (v1.13.5):** citation-only. The
  `MarketEnvironmentStateRecord` carries `evidence_interbank_liquidity_state_ids`;
  the bank credit review helper carries
  `explicit_interbank_liquidity_state_ids`; the orchestrator
  passes one bank-specific id per `(bank, firm)` review call.
  No record reads another record's content.

## What v1.13 substrate explicitly is not

- **Not a payment system.** No clearing, settlement, queueing,
  routing, prioritisation, netting, DvP, PvP, repo, intraday
  credit, or securities settlement.
- **Not a calibrated liquidity model.** No real balances, no
  reserve totals, no monetary base, no seigniorage, no default
  probability, no LGD, no EAD.
- **Not a monetary-policy decision layer.** No rate setting, no
  reserve-requirement change, no QE/QT execution, no forward
  guidance, no policy stance numeric, no operation amount.
- **Not a collateral revaluation layer.** No haircut percentage,
  no margin number, no collateral-pool valuation, no eligibility
  authority decision binding.
- **Not a lending or rating layer.** No loan origination, no
  covenant decision, no internal rating, no PD/LGD/EAD, no
  pricing, no investment recommendation, no portfolio
  allocation.
- **Not a real-system mapping.** No real RTGS, large-value
  payment system, central-securities-depository, or central
  counterparty appears in any public-FWE record. Real-system
  identifiers are in private JFWE territory (v2 / v3 only).
- **Not a Japan calibration.** All ids, labels, and confidence
  scalars are jurisdiction-neutral, synthetic, and illustrative.

## Performance boundary at v1.13.last

- **Per-period record count (default fixture):** 81 (period 0)
  / 83 (periods 1+) — up from 79 / 81 at v1.12.last. The +2
  per period is the v1.13.5 `interbank_liquidity_state` (one
  per bank per period).
- **Per-run window (default fixture):** `[324, 372]` records —
  up from `[316, 364]` at v1.12.last.
- **Integration-test `living_world_digest`:**
  `916e410d829bec0be26b92989fa2d5438b80637a5c56afd785e0b56cfbebb379`
  (v1.13.5; previously
  `e328f955922117f7d9697ea9a68877c418b818eedbab888f2d82c4b9ac4070b0`
  at v1.12.9). The shift is by design: v1.13.5 wiring adds new
  ledger records and a new payload key.
- **Test count:** 2988 / 2988 passing (up from 2751 / 2751 at
  v1.12.last; +237 across v1.13.1 → v1.13.5).
- The v1.13.1 / v1.13.2 / v1.13.4 substrate components are
  **storage-only** and not on the default per-period sweep.

## Discipline preserved bit-for-bit

Every v1.9.5 / v1.9.7 / v1.10.x / v1.11.x / v1.12.x boundary
anti-claim is preserved unchanged at v1.13.last:

- No real data, no Japan calibration, no LLM-agent execution,
  no behaviour probability.
- No price formation, no trading, no portfolio allocation, no
  investment advice, no rating.
- No lending decision, no covenant enforcement, no contract
  mutation, no constraint mutation, no default declaration.
- The v1.12.6 watch-label classifier is unchanged at v1.13.5
  (the new id slot is citation-only).
- The v1.9.last public-prototype freeze and the v1.8.0 public
  release remain untouched.

## What v1.14 does next

v1.14 begins the **corporate financing intent** layer. v1.14.0
is docs-only design; v1.14.1 (if straightforward) will ship a
minimal `CorporateFinancingNeedRecord` storage module. This
preserves the v1.13 storage-first discipline: no decision, no
execution, no calibration — labels + provenance + ledger events
only.
