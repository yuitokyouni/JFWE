# Architecture

The engine is organized as spaces under a world scheduler. Each space owns its
internal state and publishes limited outputs. Cross-space interaction is
restricted to asset ownership, contracts, market prices, information signals,
and constraints.

## Top-Level Spaces

```text
World
  Real Economy Layer
    Corporate Sector
    Household / Consumption Sector
    External Trade Sector

  Financial Intermediation Layer
    Bank / Loan Sector
    Bond / Credit Market
    Shadow Banking / Funds

  Capital Market Layer
    Equity Market
    Exchange / Trading Venue
    Index / Passive Flow
    Derivatives / Leverage

  Asset Market Layer
    Real Estate Market
    REIT Market
    Commodity Exposure

  Information Layer
    Disclosure
    Media
    Analyst / Research
    Narrative / Rumor

  Policy / Institution Layer
    BOJ
    Government / Ministries
    Tax / Regulation
    Exchange Rules

  External World Layer
    Oil Price
    FX
    Global Demand
    Geopolitics
    Overseas Markets
```

## Repository Layout

```text
japan-financial-world/
  docs/
    ontology.md
    scope.md
    architecture.md
    world_model.md

  schemas/
    firm.yaml
    investor.yaml
    bank.yaml
    market.yaml
    property_market.yaml
    information_signal.yaml
    contract.yaml
    asset.yaml

  world/
    ids.py
    registry.py
    clock.py
    scheduler.py
    ledger.py
    state.py
    loader.py
    validation.py

  data/
    sample/
      firms.yaml
      investors.yaml
      banks.yaml
      markets.yaml
      assets.yaml
      contracts.yaml

  spaces/
    corporate/
    investors/
    banking/
    exchange/
    real_estate/
    information/
    policy/
    external/

  tests/
```

The `world/` directory owns orchestration and shared infrastructure. Domain
behavior belongs in `spaces/`. Old event-specific scaffolding is intentionally
excluded.

## Allowed Interactions

Corporate <-> Investors:

- Equity ownership
- Disclosures
- Market prices

Corporate <-> Banks:

- Loan contracts
- Collateral
- Credit conditions

Corporate <-> Real Estate:

- Owned properties
- Rent
- Sale prices
- Liquidity

Investors <-> Exchange:

- Orders
- Executed trades
- Market prices
- Liquidity signals

Banks <-> Real Estate:

- Collateral values
- Lending appetite
- Default loss assumptions

Information <-> All Spaces:

- Receives state changes and state summaries
- Publishes observable signals
- Adds lag, noise, framing, and credibility

Policy / External <-> All Spaces:

- Rates
- FX
- Oil
- Regulation
- Tax
- Macro demand

## Forbidden Coupling

- Corporate must not directly call investor strategy methods.
- Investors must not directly mutate bank lending standards.
- Banks must not directly rewrite equity prices.
- Exchange must not decide firm fundamentals.
- Information must not expose omniscient truth as if all agents can observe it.
- External variables must not become hidden backdoors for arbitrary state
  changes.

## Step Order

Each simulated day should follow:

1. External and policy variables update if scheduled.
2. Real economy and balance-sheet state update if scheduled.
3. Firms publish disclosures or internal state summaries if scheduled.
4. Information space converts state changes into observable signals.
5. Investors and banks update expectations and constraints.
6. Markets clear orders and update prices.
7. Credit and collateral conditions update through published prices.
8. Firms receive funding and balance-sheet feedback.
9. World records ledger entries and snapshots.

Quarterly, monthly, and yearly updates should be triggered by the world clock,
not by ad hoc checks scattered across agents.

## Minimal v0 Execution Loop

```python
for day in world.clock:
    world.step_external()
    world.step_pre_market()
    world.step_information()
    world.step_decisions()
    world.step_market()
    world.step_post_market()
    world.record()
```

## Architectural Test

For every new feature, ask:

1. Which space owns this state?
2. Which reproduction level does this space have?
3. Which of the five allowed interaction channels carries the effect?
4. Which clock frequency updates it?
5. Is this in v0 scope?

If any answer is unclear, the feature belongs in design docs before code.
