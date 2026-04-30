# Scope

> **Note (v0 freeze):** This document was written as the original ambition
> scope for the project. It includes targets — behavior, scenarios, Japan
> calibration, feedback loops — that the v0 milestone deliberately did **not**
> implement. For an accurate description of what v0 actually delivered (and
> what is explicitly out of scope for v0), see [`v0_scope.md`](v0_scope.md).
> The content below remains as a long-term design target for v1 (reference
> behavior), v2 (Japan public calibration), and v3 (Japan proprietary
> calibration).

This document defines what v0 should reproduce and what it must deliberately
avoid. The goal is a complex Japanese financial economy model, but the first
version must protect the core feedback loop from becoming an unbounded
everything-affects-everything system.

## Reproduction Levels

Each space has a reproduction level:

- Level 0: Exogenous variable only
- Level 1: Aggregate agent or mechanism
- Level 2: Multiple agent types
- Level 3: Individual subjects
- Level 4: Internal decisions, contracts, and constraints

## Initial Depth by Space

Corporate Sector: Level 3

Individual firms exist, but v0 should use named core firms, sector
representatives, and background firms instead of every listed company at full
depth.

Investor Sector: Level 2

Investor types exist. Individual real-world fund names are not needed in v0.

Bank / Debt Sector: Level 2 to 3

Megabanks, regional banks, credit investors, and ratings should be separate.
Individual loan files are out of scope for v0.

Exchange Sector: Level 1 to 2

The exchange is a price formation mechanism. A full limit order book is out of
scope for v0.

Real Estate Sector: Level 2

Property type, region, and buyer type exist. Every individual building is out
of scope for v0.

Information Sector: Level 2

Disclosure, news, analysts, rumors, and narratives exist as signal types. Full
natural-language article generation is out of scope for v0.

Policy / External Sector: Level 0 to 1

Rates, FX, oil, global demand, overseas rates, and policy variables are mostly
exogenous in v0. Smart central bank behavior comes later.

## Core Feedback Loop

v0 should focus on the connection point between firms, investors, banks, real
estate, and market prices:

1. Firm real state changes.
2. Disclosure and observable signals are produced.
3. Investors interpret signals.
4. Market prices move.
5. Credit conditions change.
6. Firm funding constraints tighten or loosen.
7. Firms sell assets, reduce investment, borrow, repay, or adjust employment.
8. Real economy and asset markets receive feedback.

## In Scope for v0

- Simplified corporate P/L and B/S
- Corporate funding constraints
- Equity market price formation
- Credit spreads or borrowing conditions
- Real estate holdings and asset sales
- Investor-type trading pressure
- Bank lending attitude
- Public information, delay, noise, and misinterpretation
- Sector cost and demand propagation
- Tiered firm, investor, and bank populations
- Scenario playback for macro, credit, real estate, and market shocks

## Out of Scope for v0

- Full reproduction of all listed Japanese companies
- Full high-frequency order book simulation
- Natural-language generation of individual news articles
- Exact financial statements for real companies
- Household micro-consumption simulation
- Full government budget model
- Endogenous global economy model
- Detailed derivative valuation
- Detailed accounting standard treatment
- Named real fund strategies at trade-level precision
- Full BOJ reaction function

## Population Tiers

Firms:

- Tier 1: Named core firms, detailed enough to affect system dynamics.
- Tier 2: Sector representative firms.
- Tier 3: Background firms that create market thickness.

Investors:

- Tier 1: GPIF-like long-only giant, foreign macro fund, domestic retail,
  activist fund.
- Tier 2: Passive funds, mutual funds, insurers, hedge funds.
- Tier 3: Noise traders and background liquidity.

Banks:

- Tier 1: MegaBankA, MegaBankB, MegaBankC.
- Tier 2: RegionalBankGroup.
- Tier 3: CreditMarketAggregate.

## Time Scales

The world should maintain multiple clocks:

- Daily: equity prices, news, investor trading, liquidity.
- Monthly: bank lending attitude, rent, real estate price marks, macro stats.
- Quarterly: earnings, capex, asset sales, credit ratings.
- Yearly: industry structure, policy regime changes, long-term investment,
  population and demand structure.

Not every agent acts on every day. Decision frequency is part of the model.

## Design Boundary

The v0 success condition is not realism of every component. It is whether the
system can show credible balance-sheet, credit, information, and market-price
feedback without hidden direct writes across spaces.
