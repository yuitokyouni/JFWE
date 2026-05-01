# Ontology

> **Note (v1.7 freeze):** This document captures the long-term ontology
> ambition. The current code (v0 + v1, frozen) is jurisdiction-neutral and
> contains no Japan-specific calibration; the "Japanese financial economy"
> framing below is a *future* target carried by the v2 (Japan public)
> and v3 (Japan proprietary) layers, neither of which is started. For
> what v0 and v1 actually deliver, see [`v0_release_summary.md`](v0_release_summary.md)
> and [`v1_release_summary.md`](v1_release_summary.md).

This project models a financial economy as interactions between
layered spaces, decision-making agents, assets, contracts, information, market
rules, and constraints. The smallest meaningful unit is not just an agent. It
is a stateful subject plus the ownership, contract, price, information, and
constraint networks that connect subjects.

## Core Principle

No space should directly mutate another space's internal state. Spaces interact
only through:

1. Asset ownership
2. Contract relationships
3. Market prices
4. Information signals
5. Constraints

For example, a firm's deterioration must not directly change investor behavior.
The correct path is:

firm state changes -> disclosure or price signal -> investor observes signal ->
investor expectation changes -> order flow changes -> market price changes.

## World

The world coordinates time, registries, spaces, and logs. It is not a god
object that decides outcomes. It advances clocks, calls spaces in the agreed
order, carries shared registries, and records state transitions.

## Space

A space is a bounded part of the world with its own state, update frequency,
and publication surface.

Required space interface:

```python
class Space:
    def step_pre_market(self, world):
        pass

    def step_market(self, world):
        pass

    def step_post_market(self, world):
        pass

    def publish_state(self):
        pass
```

Spaces should publish state through typed outputs rather than by exposing all
internal objects.

## Layer

Layers define simulation order and conceptual ownership:

- L0 Physical / Macro Environment: oil, FX, rates, overseas demand, disasters,
  geopolitics.
- L1 Real Economy: revenue, costs, investment, employment, capacity, inventory.
- L2 Balance Sheet / Contract Network: assets, liabilities, loans, bonds,
  collateral, real estate holdings.
- L3 Information Layer: disclosures, media, ratings, analyst views, rumors,
  price signals.
- L4 Decision Layer: firm, investor, bank, and real estate fund decisions.
- L5 Market Clearing Layer: equity, credit, and real estate prices and trades.
- L6 Feedback Layer: prices, credit conditions, and asset prices returning to
  real activity.

## Agent

An agent is a subject that has state, observes information, faces constraints,
and makes decisions.

Initial agent classes:

- FirmAgent: revenue, profit, assets, liabilities, cash, real estate holdings,
  overseas revenue, sector position.
- InvestorAgent: holdings across equities, bonds, REITs, cash, and other
  exposures; interprets information and trades.
- BankAgent: lends to firms and changes credit conditions based on collateral,
  borrower risk, funding cost, and capital constraints.
- RealEstateAgent: owner, buyer, REIT, fund, or developer in property markets.
- InformationAgent: disclosure, media, analyst, rumor, and narrative channels.
- PolicyAgent: central bank, government, regulator, or exchange rule maker.
  In v0 most policy behavior is exogenous.

Not every world component is an agent:

- ExchangeMechanism is an institution and clearing mechanism, not a strategic
  subject in v0.
- ExternalWorld is an environment, not an agent in v0.

## Asset

An asset is something owned by a subject and valued directly or indirectly by a
market, model, or contract.

Initial asset types:

- Cash
- Equity
- Corporate bond
- Bank loan asset
- Real estate
- REIT unit
- Commodity exposure
- FX exposure
- Derivative exposure, shallow in v0

## Contract

A contract connects subjects through future cash flows, covenants, collateral,
seniority, maturity, and default rules.

Initial contract types:

- Bank loan
- Corporate bond
- Lease
- Rental agreement
- Collateral agreement
- Derivative contract, shallow in v0

## Market

A market converts orders, liquidity, constraints, and information into prices
and transactions.

Initial markets:

- Equity market
- Credit market
- Bank lending market
- Real estate market
- REIT market

## Information

Information is not truth. It is an observable signal with source, lag, noise,
credibility, scope, and interpretation risk.

Initial information types:

- Financial disclosure
- News
- Analyst report
- Rumor
- Rating action
- Price signal
- Policy signal

## Institution

An institution defines rules rather than ordinary strategic behavior.

Initial institutions:

- Exchange rules
- Disclosure rules
- Accounting rules, simplified in v0
- Bank regulation, simplified in v0
- Tax rules, shallow in v0

## BalanceSheet

A balance sheet is the stock state of a subject:

- Assets
- Liabilities
- Equity / net worth
- Liquidity buffers
- Off-balance-sheet exposure, shallow in v0

## CashFlow

Cash flow is the period movement that changes balance sheets:

- Revenue
- Operating cost
- Interest expense
- Dividend
- Rent
- Asset sale proceeds
- Capex
- Debt repayment

## Expectation

An expectation is a subjective belief about future cash flows, rates, prices,
liquidity, or credit risk. Different agents can observe the same signal and
update expectations differently.

## Constraint

A constraint limits decisions and creates feedback:

- Liquidity constraint
- Collateral constraint
- Capital constraint
- Mandate constraint
- Regulatory constraint
- Market liquidity constraint
- Disclosure / information constraint

## Network Layers

The engine should explicitly maintain five network layers:

- Agent Network
- Asset Ownership Network
- Debt / Contract Network
- Information Network
- Market Price Network
