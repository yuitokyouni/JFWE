# World Model

## 0. Purpose

`world_model.md` defines the constitutional model of `japan-financial-world`.

This document does not define the detailed behavior of firms, investors, banks, exchanges, real estate markets, or policy makers.  
It defines the minimum world-level rules that every future implementation must obey.

The purpose of this document is to prevent the simulation from becoming an unstructured collection of ad-hoc interactions.

In this project, `World` is not a god object that directly executes every domain logic.  
`World` is the foundation that manages:

- registration
- time
- state reference
- history
- snapshots
- allowed interaction channels
- cross-space consistency

The core design principle is:

> Spaces must not directly mutate each other.  
> Cross-space effects must pass through explicit world objects such as ownership, contracts, market prices, information signals, and constraints.

---

## 1. What is World?

`World` is the top-level container of the simulation.

It represents the shared environment in which all spaces, agents, assets, contracts, markets, signals, prices, clocks, registries, ledgers, and snapshots coexist.

However, `World` is not responsible for making economic decisions.  
It does not decide how a firm invests, how a bank lends, how an investor allocates capital, or how a market clears.

The responsibilities of `World` are:

1. to register entities and spaces
2. to provide a common clock
3. to manage the execution order through a scheduler
4. to provide state lookup and snapshot access
5. to record historical changes through ledgers
6. to enforce interaction boundaries between spaces
7. to define which interaction channels are allowed
8. to prevent hidden direct references between domains

`World` is the operating system of the simulation, not the brain of each economic actor.

### 1.1 World must not become a god object

The following patterns are prohibited:

- `World` directly changes a firm balance sheet because a real estate price moved
- `World` directly changes an investor portfolio because a bank made a loan
- `World` directly calculates every market price
- `World` contains domain-specific if-else logic for corporate finance, real estate, banking, and policy
- `World` allows one space to hold mutable references to internal objects of another space

Instead, `World` should coordinate explicit objects and processes.

Example:

- Real Estate Space produces a market price.
- Market Price Layer records the price.
- Investor Space reads the price.
- Investor Agent decides whether to buy.
- Contract or ownership relation records the transaction.
- Ledger records the resulting state change.

---

## 2. What is Space?

A `Space` is a domain-bounded area of the world.

Each space owns its internal entities, domain rules, and local state.  
Spaces are used to separate parts of the financial world that have different objects, institutions, rules, and time scales.

Expected spaces include:

- `Corporate Space`
- `Investors Space`
- `Banking Space`
- `Exchange Space`
- `Real Estate Space`
- `Information Space`
- `Policy Space`
- `External Space`

A space is not just a folder or module.  
It is a boundary of responsibility.

### 2.1 Space responsibilities

A space is responsible for:

- maintaining its own local entities
- defining local domain concepts
- updating local state according to permitted inputs
- producing outputs through allowed world objects
- exposing only controlled views to other spaces

A space is not allowed to directly modify the internal state of another space.

### 2.2 Examples

`Corporate Space` may contain firms.  
`Investors Space` may contain investors.  
`Banking Space` may contain banks and lending institutions.  
`Exchange Space` may contain listed instruments and trading venues.  
`Real Estate Space` may contain properties, submarkets, rents, cap rates, and transactions.  
`Information Space` may contain reports, news, filings, analyst signals, and macro indicators.  
`Policy Space` may contain regulation, tax rules, monetary policy, or fiscal constraints.  
`External Space` may contain exogenous shocks, global macro variables, demographic trends, or foreign capital flows.

In v0, these spaces may exist mostly as empty structural containers.  
The purpose is to establish boundaries before implementing behavior.

---

## 3. What is Layer?

A `Layer` is a cross-space view of the world.

While `Space` divides the world by institutional or domain boundary, `Layer` cuts across spaces by relation type or state dimension.

Examples of layers:

- `Balance Sheet Layer`
- `Ownership Layer`
- `Contract Layer`
- `Market Price Layer`
- `Information Layer`
- `Constraint Layer`
- `Cash Flow Layer`
- `Risk Exposure Layer`

A layer does not replace a space.  
A layer provides a way to observe and organize relationships that span multiple spaces.

### 3.1 Space vs Layer

`Space` answers:

> Which domain does this entity belong to?

`Layer` answers:

> Through what kind of relation or state dimension are these entities connected?

Example:

A real estate asset belongs to `Real Estate Space`.  
A fund that owns the asset belongs to `Investors Space`.  
The ownership relation between the fund and the asset belongs to the `Ownership Layer`.  
The acquisition loan belongs to the `Contract Layer`.  
The property valuation belongs to the `Market Price Layer`.  
The rent roll may appear in the `Cash Flow Layer`.  
A zoning rule may appear in the `Constraint Layer`.

### 3.2 Layer responsibilities

A layer should:

- represent cross-space relations explicitly
- provide queryable views
- support snapshots
- avoid hidden mutation
- help explain why one part of the world affected another

A layer should not become a second implementation of domain logic.

---

## 4. What is Agent?

An `Agent` is an entity that can make decisions.

Agents are the only entities that should own decision rules, preferences, strategies, objectives, or policies.

Examples of agents:

- firm
- investor
- bank
- broker
- exchange operator
- regulator
- household
- analyst
- rating agency
- developer
- property owner

In v0, agents may be registered without full internal behavior.  
The important point is to reserve the concept of agency for decision-making subjects.

### 4.1 Agent responsibilities

An agent may eventually:

- observe allowed state
- receive signals
- evaluate constraints
- choose actions
- enter contracts
- trade assets
- issue signals
- update internal beliefs
- record decisions

However, an agent must not directly mutate the state of another agent.

For example:

A bank may offer a loan contract to a firm.  
The bank must not directly alter the firm’s balance sheet.  
The firm’s balance sheet changes only after a valid contract or transaction is processed through the appropriate world mechanism.

---

## 5. What is Asset?

An `Asset` is an ownable object with economic value.

Assets connect agents across spaces because they can be owned, transferred, financed, priced, pledged, rented, or referenced by contracts.

Examples of assets:

- cash
- equity
- bond
- loan claim
- real estate property
- land
- building
- leasehold interest
- fund interest
- derivative position
- receivable
- inventory
- data asset

An asset is not necessarily physical.  
It only needs to be economically ownable and representable in the world state.

### 5.1 Asset responsibilities

An asset should have:

- stable identity
- type
- owner or ownership relation
- state attributes
- valuation references
- possible constraints
- historical records

An asset should not contain all logic related to its trading, financing, or valuation.  
Those belong to markets, contracts, agents, and price mechanisms.

---

## 6. What is Contract?

A `Contract` is an explicit agreement or obligation between parties.

Contracts are one of the primary legal-economic connectors of the world.

Examples of contracts:

- loan agreement
- bond indenture
- lease agreement
- equity issuance agreement
- purchase and sale agreement
- derivatives contract
- advisory contract
- management agreement
- insurance contract
- credit facility
- covenant package

A contract defines rights, obligations, claims, constraints, and state transitions that may occur over time.

### 6.1 Contract responsibilities

A contract should define:

- parties
- referenced assets
- terms
- obligations
- payment schedule
- covenants
- triggers
- maturity
- status
- history

Contracts should be explicit because they are a major mechanism by which one space affects another.

Example:

A bank does not directly inject debt into a corporate balance sheet.  
Instead:

1. Banking Space creates or approves a loan contract.
2. Corporate Agent accepts the contract.
3. Contract Layer records the loan.
4. Ledger records the resulting cash and liability changes.
5. Balance Sheet Layer reflects the new state.

---

## 7. What is Market?

A `Market` is a mechanism that connects buyers, sellers, assets, orders, prices, and transactions.

A market is not simply a price series.  
A market defines how prices are formed, how orders or intentions interact, and how ownership or claims are transferred.

Examples of markets:

- stock exchange
- bond market
- loan market
- real estate transaction market
- rental market
- repo market
- FX market
- private placement market
- fund interest secondary market

In v0, markets do not need full clearing logic.  
They may only expose market price references and transaction interfaces.

### 7.1 Market responsibilities

A market may eventually:

- collect orders
- match counterparties
- clear transactions
- produce market prices
- record volume
- impose trading constraints
- expose liquidity conditions
- transmit shocks

A market should not directly change unrelated agent internals.  
Transactions should be recorded through ownership, contracts, prices, and ledger entries.

---

## 8. What is Signal?

A `Signal` is an information object that may influence decisions or beliefs.

Signals connect the world through information rather than ownership or legal obligation.

Examples of signals:

- earnings report
- analyst report
- rating action
- news article
- macro indicator
- policy announcement
- transaction comparable
- rent survey
- cap rate estimate
- default warning
- rumor
- disclosure filing
- alternative data indicator

Signals do not directly change economic state.  
They change what agents may observe, believe, or decide.

### 8.1 Signal responsibilities

A signal should define:

- source
- `timestamp`
- target or topic
- content
- credibility
- visibility
- affected spaces
- decay or validity period
- references to assets, agents, markets, or contracts

Signals should not directly mutate balance sheets, prices, contracts, or ownership.  
They may influence agents, and agents may then act.

Example:

A negative rating signal does not directly lower a bond price.  
It becomes observable information.  
Investors may sell.  
Market mechanisms may produce a new price.  
The new price is recorded through the Market Price Layer.

---

## 9. What is Price?

A `Price` is a state variable representing an exchange value, valuation, quote, mark, or reference level.

Prices can come from different mechanisms.  
Not every price is a traded market price.

Types of prices include:

- transaction price
- quoted price
- model price
- appraisal value
- mark-to-market value
- mark-to-model value
- reference index
- rent level
- cap rate
- spread
- yield
- NAV
- book value

### 9.1 Price responsibilities

A price should define:

- priced object
- price type
- source
- timestamp
- currency or unit
- confidence or quality
- applicable market or methodology
- validity period

Prices should be versioned and historical.  
A price at time `t` should not overwrite the meaning of a price at time `t-1`.

### 9.2 Price is not value itself

A price is an observed or computed representation of value under a specific context.  
The same asset may have multiple prices:

- book value
- appraised value
- transaction value
- market quote
- liquidation value
- collateral value
- internal underwriting value

The world model must support this plurality.

---

## 10. Registry Responsibilities

The `Registry` manages identity and lookup.

Its primary role is to ensure that world objects have stable IDs and can be referenced safely.

The registry should manage:

- spaces
- agents
- assets
- contracts
- markets
- signals
- price objects
- constraints
- ledgers
- layers

### 10.1 Registry must provide stable identity

Every major object should have a stable identifier.  
The system should not rely on direct Python object references across spaces as the primary connection mechanism.

The registry should support:

- registration
- lookup by ID
- lookup by type
- existence checks
- lifecycle status
- metadata access

### 10.2 Registry must not own domain logic

The registry should not decide:

- whether an investor buys an asset
- whether a bank lends
- whether a firm defaults
- whether a price moves
- whether a market clears

It only manages identity and lookup.

---

## 11. Scheduler / Clock Responsibilities

The `Clock` defines simulation time.  
The `Scheduler` defines execution order.

Together, they prevent the world from becoming an unordered sequence of side effects.

### 11.1 Clock

The clock should provide:

- current simulation time
- time step definition
- calendar or tick structure
- time advancement
- timestamp generation

The clock must make temporal assumptions explicit.

Possible time structures include:

- tick-based time
- daily time
- monthly time
- quarterly time
- event-driven time
- hybrid time

v0 should choose the minimum structure needed for consistent snapshots and event ordering.

### 11.2 Scheduler

The scheduler should define:

- which spaces update
- in what order they update
- which events are processed
- when snapshots are taken
- when ledgers are finalized
- when signals become visible
- when prices become valid

The scheduler should not contain domain-specific decision logic.  
It coordinates execution; it does not decide economic behavior.

### 11.3 Why scheduling matters

Without a scheduler, hidden causality appears.

Example problem:

1. Investor reads a price.
2. Market updates the price.
3. Bank evaluates collateral.
4. Real Estate Space updates appraisal.
5. Investor acts again.

If this order is not explicit, the simulation becomes impossible to interpret.

---

## 12. Ledger Responsibilities

The `Ledger` records state-changing records.

It is the memory of what changed, when it changed, and why it changed.

Ledgers should support:

- ownership changes
- cash movements
- contract creation
- contract settlement
- price updates
- signal publication
- balance sheet changes
- market transactions
- constraint changes
- agent actions

### 12.1 Ledger is not just accounting

The ledger is broader than financial accounting.  
It records world-level records that matter for reproducibility and explanation.

Every material ledger record should include these core fields:

- `record_id`
- `sequence`
- timestamp
- `simulation_date`
- `record_type`
- `source`
- `target`
- `object_id`
- `parent_record_ids`
- `correlation_id`
- `payload`
- `metadata`

`parent_record_ids` is mandatory for explainability. It is the field that turns
the ledger from "many things happened on the same day" into a causal graph of
how stress propagated.

Example chain:

```text
signal_emitted
  -> perceived_state_updated
  -> order_submitted
  -> price_updated
  -> bank_warning
  -> contract_covenant_breached
  -> state_snapshot_created
```

Each record after the first should reference the prior relevant record in
`parent_record_ids`. If multiple records jointly caused a transition, all of
them should be listed.

Optional fields that are useful for future replay, experiments, and graph
analysis:

- `causation_id`: the single most direct parent record when one exists.
- `scenario_id`: the experiment or scenario that produced the record.
- `run_id`: the simulation run.
- `seed`: random seed used for reproducibility.
- `space_id`: space that produced the record.
- `agent_id`: decision maker, if any.
- `snapshot_id`: state snapshot used as input.
- `state_hash`: state integrity or diff reference.
- `schema_version`: record and payload version.
- `visibility`: public, private, or internal.
- `confidence`: confidence in a signal or perceived state.

Not every optional field must be populated immediately. If a value is important
for querying or graph reconstruction, prefer a top-level field. Otherwise place
it in `metadata`.

### 12.2 Ledger must support replay and audit

The long-term goal is to make the simulation explainable.

For any state at time `t`, we should eventually be able to ask:

- what changed?
- when did it change?
- who caused it?
- through which permitted interaction channel?
- which previous state did it depend on?
- which parent records caused this record?
- what downstream records did this record trigger?

v0 does not need complete replay infrastructure, but the model should not block it.

---

## 13. State / Snapshot Responsibilities

`State` represents the current condition of the world or part of the world.

`Snapshot` is a frozen view of state at a specific time.

The distinction matters:

- `State` is mutable during simulation.
- `Snapshot` is immutable after creation.

### 13.1 State responsibilities

State should provide:

- current attributes
- current relations
- current prices
- current contract statuses
- current ownership
- current signal visibility
- current constraints

State should be accessed through controlled interfaces rather than direct cross-space mutation.

### 13.2 Snapshot responsibilities

Snapshots should provide:

- reproducible views
- historical comparison
- debugging support
- analysis support
- export support

Snapshots are necessary because financial worlds are path-dependent.  
A later state cannot be understood without knowing the earlier sequence of states.

### 13.3 Snapshot principle

A snapshot should answer:

> What did the world look like at this time, from this defined viewpoint?

Possible snapshot scopes:

- whole world
- specific space
- specific layer
- specific agent
- specific market
- specific asset
- specific contract

---

## 14. Why Direct Cross-Space Reference and Mutation Are Forbidden

Direct reference and direct mutation between spaces are forbidden because they destroy modularity, causality, auditability, and interpretability.

### 14.1 Forbidden pattern

Example of forbidden logic:

- Real Estate Space directly changes Investor Space portfolio.
- Banking Space directly changes Corporate Space balance sheet.
- Information Space directly changes Market Price Layer.
- Policy Space directly edits agent behavior.
- Exchange Space directly changes investor wealth.

This creates hidden coupling.

### 14.2 Problems caused by direct mutation

Direct cross-space mutation causes:

1. unclear causality
2. impossible debugging
3. circular dependencies
4. duplicated logic
5. non-reproducible results
6. fragile implementation
7. loss of economic meaning
8. inability to audit state changes
9. difficulty adding new spaces
10. difficulty testing individual components

### 14.3 Required pattern

Cross-space effects must pass through explicit interaction channels.

For example:

- ownership relation
- contract
- market price
- information signal
- constraint

This makes the world legible.

---

## 15. Allowed Interaction Channels

Spaces may interact only through permitted channels.

The initial allowed channels are:

1. ownership
2. contract
3. market price
4. information signal
5. constraint

These channels are the constitutional interfaces of the world.

---

## 15.1 Ownership

Ownership defines who owns what.

Ownership connects agents and assets across spaces.

Examples:

- investor owns equity
- fund owns real estate
- bank owns loan claim
- firm owns cash
- household owns deposit
- SPV owns property
- investor owns fund interest

Ownership should be represented explicitly, not implied through nested object references.

Ownership may include:

- owner ID
- asset ID
- share
- control rights
- economic rights
- timestamp
- acquisition basis
- restrictions

Ownership is one of the core ways balance sheets and economic exposure are formed.

---

## 15.2 Contract

Contracts define obligations and rights.

Contracts connect agents, assets, cash flows, and constraints over time.

Examples:

- loan from bank to firm
- lease between tenant and landlord
- bond issued by company and held by investor
- acquisition agreement for property
- derivative contract between counterparties

Contracts are required whenever a continuing obligation exists.

Contracts should not be replaced by direct balance-sheet edits.

---

## 15.3 Market Price

Market price connects markets, assets, and agents through valuation.

A market price may influence decisions, collateral values, balance sheets, risk limits, or trading behavior.

However, price changes should not automatically mutate every dependent object unless a defined mechanism processes them.

Example:

- property cap rate changes
- real estate valuation changes
- investor NAV may update
- loan-to-value covenant may be tested
- bank risk exposure may change

Each step must be explicit.

---

## 15.4 Information Signal

Information signals connect spaces through observability.

Signals may affect agents by changing their information set.

Examples:

- rating downgrade
- earnings surprise
- interest rate announcement
- property transaction comparable
- new demographic data
- policy change announcement
- news about tenant bankruptcy

Signals do not directly change ownership, contracts, or prices.  
They become inputs to agents or markets.

---

## 15.5 Constraint

Constraints define limits on possible actions or states.

Examples:

- regulation
- capital requirement
- leverage limit
- zoning rule
- investment mandate
- liquidity requirement
- covenant
- trading halt
- tax rule
- budget constraint
- short-sale restriction

Constraints may belong to Policy Space, Contract Layer, Market Layer, or Agent configuration.

Constraints do not decide actions.  
They restrict the set of valid actions.

---

## 16. What v0 Will Do

v0 should build the minimum constitutional structure of the world.

The goal of v0 is not to simulate the economy.  
The goal is to create a stable base on which future simulations can be built.

v0 should include:

1. `World` container
2. `Space` abstraction
3. basic spaces:
   - Corporate
   - Investors
   - Banking
   - Exchange
   - Real Estate
   - Information
   - Policy
   - External
4. `Layer` concept
5. `Registry`
6. `Clock`
7. `Scheduler`
8. `Ledger`
9. `State`
10. `Snapshot`
11. base object schemas:
   - Agent
   - Asset
   - Contract
   - Market
   - Signal
   - Price
   - Constraint
12. ID-based references
13. explicit cross-space interaction rules
14. minimal validation that forbids direct cross-space mutation
15. documentation-first implementation discipline

v0 should make it possible to ask:

- What spaces exist?
- What objects are registered?
- What time is the world at?
- What happened in the last step?
- Which layer connects which objects?
- Which interaction channel caused a state change?
- Can this space legally access or mutate that object?

---

## 17. What v0 Will Not Do

v0 should not implement detailed economic behavior.

v0 will not implement:

1. firm decision-making
2. investor portfolio optimization
3. bank credit analysis
4. market clearing
5. exchange order book
6. real estate underwriting
7. detailed accounting engine
8. macro scenario generation
9. policy reaction functions
10. rating models
11. default models
12. full balance sheet simulation
13. LLM agent behavior
14. strategy learning
15. scenario design
16. empirical calibration
17. visualization layer
18. production database design
19. API server
20. UI

v0 should also avoid premature realism.

In particular, v0 should not attempt to build a full Japanese financial economy.  
It should only define the world kernel required to build such a model later.

---

## 18. Design Principles

The following principles govern the world model.

### 18.1 Explicit over implicit

Important relations must be represented explicitly.

Bad:

- investor object directly contains property object

Good:

- investor ID owns asset ID through ownership relation

### 18.2 ID reference over mutable object reference

Cross-space references should use IDs, not direct mutable object pointers.

### 18.3 Interaction channels over hidden side effects

Spaces interact only through ownership, contracts, prices, signals, and constraints.

### 18.4 World coordinates, agents decide

World manages structure, time, state, and history.  
Agents make decisions.

### 18.5 Layers explain cross-space structure

Layers should make cross-domain connections visible and queryable.

### 18.6 Ledger before cleverness

Every meaningful state change should be recordable.  
If an event cannot be explained later, the implementation is probably too implicit.

### 18.7 Snapshot before scenario

Before building scenarios, the world must support stable snapshots.  
A scenario without reproducible state is not a simulation; it is a story generator.

### 18.8 Minimal v0

The first version should protect architecture, not maximize realism.

---

## 19. Canonical Example

This example illustrates the intended structure.

A real estate fund buys an office building using debt financing.

Correct world-level sequence:

1. `Real Estate Space` registers the building as an asset.
2. `Investors Space` registers the fund as an agent.
3. `Banking Space` registers the bank as an agent.
4. `Market Price Layer` records a reference valuation for the building.
5. Fund and seller enter a purchase contract.
6. Bank and fund enter a loan contract.
7. `Ownership Layer` records the fund's ownership of the building.
8. `Contract Layer` records the acquisition contract and loan contract.
9. `Ledger` records cash movement, ownership transfer, and debt obligation.
10. `Snapshot` captures the post-transaction world state.

Incorrect implementation:

- Real Estate Space directly inserts the building into the fund object.
- Banking Space directly changes the fund balance sheet.
- World directly recalculates all investor NAVs through hard-coded logic.
- Price object directly changes ownership.
- Signal object directly changes the bank's loan exposure.

The correct version is more verbose but more interpretable, testable, and extensible.

---

## 20. Implementation Implication

Before implementing detailed agents, the project should first implement the following kernel-level guarantees:

1. every object has an ID
2. every object belongs to a space or layer
3. every cross-space relation is explicit
4. every state-changing event can be logged
5. every simulation step has a timestamp
6. every snapshot is immutable
7. spaces cannot directly mutate each other
8. world does not contain domain-specific economic logic
9. v0 behavior remains minimal
10. future complexity is added through agents, markets, contracts, and signals, not through hidden world-level shortcuts

This is the constitutional base of `japan-financial-world`.

---

## 21. World Kernel v0 — Success Criteria

This section defines the acceptance line for the `World Kernel v0` milestone.

The goal of v0 is not economic realism. It is a stable, reproducible substrate that future spaces and scenarios can be built on. v0 is considered complete when **all** of the following hold:

1. **Schema YAML files load.** All YAML files under `schemas/` and example world YAMLs under `data/` / `examples/` can be loaded without raising.
2. **Core objects can be registered in the Registry.** Agents, assets, contracts, markets, signals, and prices can be registered through stable WorldIDs and retrieved by ID, type, and category.
3. **Clock can advance through a full year.** Starting at any valid simulation date, the clock can step forward 365 days and correctly identifies month-end, quarter-end, and year-end boundaries.
4. **Scheduler correctly triggers Daily / Monthly / Quarterly / Yearly tasks.** Tasks registered at each frequency fire the expected number of times over a one-year run, in deterministic order.
5. **Ledger records registrations, task executions, and snapshots.** Every `register_object`, scheduled `task_executed`, and `state_snapshot_created` event produces a ledger record with stable identity, simulation date, and required provenance fields.
6. **State snapshots can be created.** Month-end snapshots are produced automatically and are immutable. State at time `t` is queryable independently from later state.
7. **Empty world simulation runs without scenario logic.** A world containing only registered objects and no-op tasks can run for one year without any domain-specific economic logic in `world/` or in any `Space`.

### 21.1 What v0 explicitly does not require

The following are explicitly **out of scope** for v0 acceptance and must not be used to gate this milestone:

- firm / investor / bank decision logic
- market clearing or order books
- price formation models
- contract settlement engines
- macro scenarios (e.g. oil shocks, rate shocks, demographic shifts)
- portfolio optimization
- credit analysis
- any LLM-driven agent behavior

If any of these are tempting to implement before items 1–7 are stable, the temptation should be resisted. v0 is a kernel, not a simulator.

### 21.2 Next milestone — Space interface (v0.2)

After v0 is fixed, the next acceptance line is:

> Empty `Space` instances (Corporate, Investors, Banking, etc.) are registered with the world, the scheduler invokes them at their declared frequency over one year, and the ledger records each invocation.

This milestone introduces the `BaseSpace` contract (`observe`, `step`, `emit`, `snapshot`) but still contains no economic logic. Its purpose is to lock down the boundary between `world/` (coordination) and `spaces/` (domain), before any domain behavior is written.
