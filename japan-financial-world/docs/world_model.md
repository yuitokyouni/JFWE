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

---

## 22. Event / Signal Transport Layer (v0.3)

The v0.3 milestone introduces the explicit transport mechanism by which spaces communicate without ever holding direct references to one another.

### 22.1 Why a transport layer

Direct cross-space mutation has already been forbidden in §14. To make that prohibition usable, spaces still need a way to influence each other — through information, not through references.

The transport layer provides exactly that: an explicit, addressable, time-aware, auditable message channel.

If a space ever needs to "tell" another space something, the answer is always the same: emit a `WorldEvent`. There is no other legitimate channel.

### 22.2 WorldEvent

`WorldEvent` is the unit of inter-space communication. It is a plain data record. It carries no behavior.

Required fields:

- `event_id` — stable unique identifier supplied by the publisher.
- `simulation_date` — ISO date when the event was created.
- `source_space` — `space_id` of the publishing space.
- `target_spaces` — tuple of `space_id`s. Empty tuple means broadcast.
- `event_type` — domain-neutral string tag.
- `payload` — arbitrary mapping of event-specific data.
- `visibility` — `"public"`, `"private"`, or `"internal"`.
- `delay_days` — integer days before the event becomes deliverable.
- `confidence` — float in `[0, 1]` indicating signal quality.
- `related_ids` — tuple of WorldIDs the event references.

A `WorldEvent` is immutable after creation. It must not be mutated by the bus, by the kernel, or by any space that receives it.

### 22.3 EventBus

`EventBus` is the only delivery mechanism. It exposes:

- `publish(event, *, on_date=None)` — register an event for future delivery.
- `collect_for_space(space_id, current_date)` — return events ready for the given space.
- `pending_events()` — events not yet delivered to any target.
- `delivered_events()` — events delivered to at least one target.

Delivery rules:

1. Same-tick delivery is forbidden. An event published on date `D` is visible only from date `D + 1` onward (subject to `delay_days`). This makes delivery independent of intra-tick task execution order.
2. An event is delivered to a space only when `current_date > publication_date` (strict) AND `current_date >= delivery_date` (`simulation_date + delay_days`).
3. The same `(event_id, space_id)` pair is delivered at most once.
4. Empty `target_spaces` means broadcast to every space *except* `source_space`.
5. The bus must not inspect, mutate, or reorder payload contents.

The bus contains no business logic. It does not decide who reacts. Reaction is the responsibility of each receiving space's `observe`.

### 22.4 Kernel responsibility

For each scheduled space task, the kernel wraps execution as:

1. `events = event_bus.collect_for_space(space.space_id, clock.current_date)`
2. For each delivered event, append `event_delivered` to the ledger.
3. `space.observe(events, state)`
4. `space.step(clock, state, registry, ledger)`
5. `outgoing = space.emit()`
6. For each outgoing event, `event_bus.publish(event, on_date=current_date)` and append `event_published` to the ledger.

Spaces never call `event_bus` directly through any other path in v0.3. All communication goes through `observe` and `emit`.

### 22.5 Ledger event types

Two new ledger record types are required:

- `event_published` — recorded by the kernel for every event a space emits.
- `event_delivered` — recorded by the kernel for every event a space receives.

Both records carry `correlation_id = event.event_id` so that the publish/deliver pair can be reconstructed by `correlation_id` regardless of `delay_days`.

### 22.6 What v0.3 does not do

v0.3 must not introduce:

- domain-specific event types (e.g., "loan_default", "stock_crash")
- routing logic based on payload content
- agent reactions to specific event types
- price formation, market clearing, or balance-sheet effects
- LLM-driven event interpretation

v0.3 is a transport layer. It carries messages. It does not understand them.

### 22.7 v0.3 success criteria

v0.3 is complete when **all** of the following hold:

1. `WorldEvent` exists with all required fields.
2. `EventBus` provides `publish`, `collect_for_space`, `pending_events`, `delivered_events`.
3. Empty spaces can emit and observe events without holding direct references to each other.
4. Delayed events are not delivered before their delivery date.
5. Targeted events reach only their named targets; broadcasts reach every other space.
6. The ledger records `event_published` and `event_delivered` for every transport event.
7. Same-tick delivery is impossible — delivery is always at least one tick after publication.

---

## 23. Asset / Contract / Ownership / Price Network (v0.4)

The v0.4 milestone introduces the structural data layer that records who owns what, who owes whom, and what prices are attached to which assets and contracts. It is the substrate that future economic behavior will sit on top of — but in v0.4 itself, it contains no behavior.

### 23.1 Why a network layer

§14 forbids hidden cross-space mutation. §22 introduced the message channel. But messages alone cannot represent ongoing economic *state*: who currently owns asset X, what loan exists between bank A and firm Y, what the latest observed price of an asset is.

The v0.4 layer adds three explicit, queryable books for that purpose:

- `OwnershipBook` — positions of (owner, asset, quantity)
- `ContractBook` — explicit obligations between parties
- `PriceBook` — versioned price observations

Each book is a structured store. Each emits ledger records on mutation. None of them decides anything.

### 23.2 OwnershipBook

`OwnershipRecord` fields:

- `owner_id` — WorldID of the owner.
- `asset_id` — WorldID of the asset.
- `quantity` — current accumulated quantity (positive number).
- `acquisition_price` — optional reference price for the most recent acquisition.
- `metadata` — optional mapping for non-standard attributes.

`OwnershipBook` API:

- `add_position(owner_id, asset_id, quantity, *, acquisition_price=None, metadata=None)` — create or accumulate a position. Subsequent calls aggregate quantity; the latest `acquisition_price` and `metadata` win. v0.4 deliberately does not implement weighted-average lot accounting — that is a domain decision.
- `get_positions(owner_id)` — all positions held by an owner.
- `get_owners(asset_id)` — all owners that hold an asset.
- `transfer(asset_id, from_owner, to_owner, quantity)` — move quantity. Rejects insufficient balance, unknown source, or self-transfer. Removes a position when its quantity drops to zero.
- `snapshot()` — sorted, JSON-friendly view of all current positions.

### 23.3 ContractBook

`ContractRecord` fields:

- `contract_id` — stable unique identifier.
- `contract_type` — domain-neutral string tag (e.g., `"loan"`, `"lease"`, `"bond"`).
- `parties` — tuple of party WorldIDs (at least one required).
- `principal` — optional principal amount.
- `rate` — optional rate (interpretation deferred to domain layer).
- `maturity_date` — optional ISO date.
- `collateral_asset_ids` — optional tuple of WorldIDs.
- `status` — string (`"active"`, `"settled"`, `"defaulted"`, etc.). v0.4 does not enumerate valid statuses.
- `metadata` — optional mapping for non-standard attributes.

`ContractBook` API:

- `add_contract(record)` — store a new contract; rejects duplicates.
- `get_contract(contract_id)` — lookup by id.
- `list_by_party(party_id)` — all contracts where this party appears.
- `list_by_type(contract_type)` — all contracts of a given type.
- `update_status(contract_id, new_status)` — replace status; preserves all other fields.
- `snapshot()` — sorted, JSON-friendly view of all contracts.

### 23.4 PriceBook

`PriceRecord` fields:

- `asset_id` — WorldID of the priced object.
- `price` — observed value.
- `simulation_date` — ISO date of the observation.
- `source` — string identifying the observation source (e.g., `"exchange"`, `"appraisal"`, `"model"`).
- `metadata` — optional mapping for non-standard attributes.

`PriceBook` API:

- `set_price(asset_id, price, simulation_date, source, *, metadata=None)` — append an observation. History is preserved.
- `get_latest_price(asset_id)` — most recent observation, or `None`.
- `get_price_history(asset_id)` — chronological tuple of observations.
- `snapshot()` — latest price per asset plus history-length summary.

`PriceBook` does not decide which source is authoritative when multiple sources exist. It only stores what each source claims.

### 23.5 Ledger event types

v0.4 introduces the following ledger record types:

- `ownership_position_added`
- `ownership_transferred`
- `contract_created` (already existed; now emitted by `ContractBook.add_contract`)
- `contract_status_updated`
- `price_updated` (already existed; now emitted by `PriceBook.set_price`)

Every mutation through these books writes one ledger record. Reads do not.

### 23.6 Kernel wiring

`WorldKernel` exposes three book attributes:

- `kernel.ownership: OwnershipBook`
- `kernel.contracts: ContractBook`
- `kernel.prices: PriceBook`

When the kernel is constructed, it shares its `ledger` and `clock` references with the books so that ledger records carry the correct simulation date automatically. Books constructed independently (e.g., in unit tests) can operate without ledger or clock — they then act as plain in-memory stores.

### 23.7 What v0.4 does not do

v0.4 must not introduce:

- valuation logic (how to derive value from price + quantity)
- balance-sheet construction
- credit risk analysis
- collateral valuation or LTV calculations
- contract-default detection
- price formation, market clearing, or model-based valuation
- portfolio-level aggregation across spaces
- domain-specific contract types or status transitions

These belong to future agent or scenario code, not to the network layer.

### 23.8 v0.4 success criteria

v0.4 is complete when **all** of the following hold:

1. `OwnershipBook` records positions, transfers, and snapshots without business logic.
2. `ContractBook` stores contracts, supports lookup by party and by type, and supports status updates.
3. `PriceBook` stores chronological observations per asset and exposes the latest price.
4. The ledger records `ownership_position_added`, `ownership_transferred`, `contract_created`, `contract_status_updated`, and `price_updated` on the corresponding mutations.
5. All three books expose deterministic, JSON-friendly snapshots.
6. The empty world can hold assets, ownership links, contracts, and prices without any economic behavior being implemented.
7. All previous milestones (v0, v0.2, v0.3) continue to pass.

---

## 24. Balance Sheet View (v0.5)

The v0.5 milestone adds the first cross-book *projection*: a read-only view that combines `OwnershipBook`, `ContractBook`, and `PriceBook` into a per-agent balance sheet. The projection is derived state, not stored state.

### 24.1 Why a projection layer

The network layer (§23) records facts: who owns what, who has a contract with whom, what the latest observed price of an asset is. Those facts are atomic and additive. They do not, on their own, answer the question "what is this agent worth right now?".

A balance sheet view answers that question by combining the three books. It does so without owning any of its own state, without enforcing any economic rule, and without mutating the books it reads from.

The projection is the model's answer to:

> Given the current ownership records, contracts, and observed prices, what does an agent's financial position look like?

It is not the model's opinion. It is a deterministic readout of the books.

### 24.2 BalanceSheetView

`BalanceSheetView` fields:

- `agent_id` — the agent the view describes.
- `as_of_date` — ISO date the view was computed for.
- `asset_value` — total of all valued assets (held assets + financial-asset contracts).
- `liabilities` — total of all priced liabilities.
- `net_asset_value` — `asset_value - liabilities`.
- `cash_like_assets` — optional total of cash-typed holdings (only populated when a registry is available).
- `debt_principal` — optional total face value of borrower-side principals.
- `collateral_value` — optional total of collateral-asset prices, attached only to the borrower view.
- `asset_breakdown` — mapping of `asset_id` (or `contract_id` for receivables) to value.
- `liability_breakdown` — mapping of `contract_id` to face-value liability.
- `metadata` — optional bag for warnings such as `missing_prices`.

A `BalanceSheetView` is immutable. Mutating the view, or any of its dictionaries, has no effect on the source books.

### 24.3 BalanceSheetProjector

`BalanceSheetProjector` API:

- `build_view(agent_id, *, as_of_date=None)` — recompute the view from current book contents.
- `build_views(agent_ids, *, as_of_date=None)` — convenience wrapper.
- `snapshot(*, as_of_date=None)` — discover all known agents from `OwnershipBook` owners and `ContractBook` parties, build views for each, and emit `balance_sheet_view_created` ledger records.

The projector holds references only. It must not mutate `OwnershipBook`, `ContractBook`, or `PriceBook`. Test [`test_build_view_does_not_mutate_source_books`](../tests/test_balance_sheet.py) enforces this.

### 24.4 Borrower / lender identification

A contract opts into balance-sheet treatment by setting role keys in its metadata:

```python
metadata = {"borrower_id": "agent:firm_x", "lender_id": "agent:bank_a"}
```

Without these keys, the contract is recorded in `ContractBook` but contributes nothing to any agent's balance sheet view. v0.5 deliberately does not infer roles from `parties` order or from `contract_type`.

When `principal` is set:

- if `agent_id == metadata["borrower_id"]`, the principal is added to liabilities.
- if `agent_id == metadata["lender_id"]`, the principal is added to financial assets.

When `collateral_asset_ids` is set, the borrower view sums the latest prices of those collateral assets into `collateral_value`. The lender view does not include collateral_value (the lender does not own the collateral).

### 24.5 Cash-like asset detection

`cash_like_assets` is computed only when a `Registry` is provided to the projector. An asset is cash-like when its registered `type` field equals `"cash"`. Without a registry, `cash_like_assets` stays `None`.

This avoids encoding a list of asset-id prefixes or other heuristics inside the projector. Whether something is cash is a registration-time fact, not a projection-time guess.

### 24.6 Missing prices

A position with no observed price does **not** crash `build_view`. The asset is skipped (contributes 0 to `asset_value`) and its id is recorded in `view.metadata["missing_prices"]`. Collateral assets without prices are also recorded there.

This rule is intentional: the projector reports what it can compute and is honest about what it cannot.

### 24.7 v0.5 simplifications

These simplifications are intentional and must be preserved until later milestones explicitly relax them:

- Asset value is `quantity × latest_price`. No model price, no time-weighted average.
- Loan principal is treated as undiscounted face value. No present value, no amortization, no accrued interest.
- Collateral value is the sum of latest prices of `collateral_asset_ids`. Collateral quantities are not modeled.
- Status filtering is not applied. Settled or defaulted contracts are still visible to the projector. Pre-filter contracts upstream if a different rule is required.
- The projector knows nothing about leverage limits, capital requirements, default thresholds, or solvency rules.

### 24.8 Kernel wiring

`WorldKernel` exposes `kernel.balance_sheets: BalanceSheetProjector`, constructed in `__post_init__` with the kernel's `ownership`, `contracts`, `prices`, `registry`, `clock`, and `ledger`. `as_of_date` defaults to `kernel.clock.current_date` when not explicitly provided.

### 24.9 What v0.5 does not do

v0.5 must not introduce:

- balance-sheet-driven decisions (no agent reads its own NAV to choose actions)
- solvency or capital-adequacy checks
- regulatory ratio computation
- portfolio aggregation across spaces
- present-value or yield computation
- automatic balance-sheet consolidation between related entities

These remain explicitly out of scope.

### 24.10 v0.5 success criteria

v0.5 is complete when **all** of the following hold:

1. `BalanceSheetView` exists with all required fields.
2. `BalanceSheetProjector` provides `build_view`, `build_views`, and `snapshot`.
3. Asset values are derived from `OwnershipBook` × `PriceBook`.
4. Borrower-role contracts contribute `principal` to liabilities; lender-role contracts contribute `principal` as financial assets.
5. Collateral values are summed from latest prices on the borrower view.
6. Missing prices do not crash; affected ids appear in `metadata["missing_prices"]`.
7. The projector mutates none of `OwnershipBook`, `ContractBook`, or `PriceBook`.
8. The kernel exposes `kernel.balance_sheets` with default wiring.
9. All previous milestones (v0, v0.2, v0.3, v0.4) continue to pass.

---

## 25. Constraint Skeleton (v0.6)

The v0.6 milestone introduces a declarative constraint layer on top of the balance sheet view. Constraints describe what to check; v0.6 evaluators report ok / warning / breached / unknown but never act on the result.

### 25.1 Why a constraint layer

Once balance sheets exist (§24), the world needs a way to assert structural invariants — leverage limits, capital floors, concentration caps, collateral coverage requirements. These invariants are domain-defined but their *evaluation* is purely structural: derive a number from the view, compare it to a threshold.

v0.6 separates the *declaration* of these invariants from their *consequences*. A breach is an observation, not an action. Whether a breach should trigger a margin call, a downgrade, a covenant test, or a liquidation is a business decision belonging to a future milestone.

### 25.2 ConstraintRecord

`ConstraintRecord` fields:

- `constraint_id` — stable unique identifier.
- `owner_id` — the agent the constraint applies to.
- `constraint_type` — one of the supported types listed in §25.5 (or any custom string; unsupported types resolve to `status="unknown"`).
- `threshold` — the boundary used by the comparison.
- `comparison` — one of `"<="`, `"<"`, `">="`, `">"`, `"=="`.
- `target_ids` — optional tuple of WorldIDs the constraint is scoped to (e.g., specific assets for a concentration check).
- `warning_threshold` — optional second boundary that produces `status="warning"` when crossed but not yet at the breach line.
- `severity` — string label (default `"warning"`).
- `source` — string identifying the constraint's origin (default `"system"`).
- `metadata` — optional mapping for non-standard attributes.

ConstraintRecords are immutable.

### 25.3 ConstraintEvaluation

`ConstraintEvaluation` fields:

- `constraint_id`, `owner_id`, `as_of_date`, `threshold`
- `status` — `"ok"`, `"warning"`, `"breached"`, or `"unknown"`.
- `current_value` — the derived value, or `None` when status is `"unknown"`.
- `message` — human-readable summary.
- `related_ids` — copied from the constraint's `target_ids` for traceability.
- `metadata` — includes `reason` when status is `"unknown"`.

Status semantics:

- `ok` — the current value satisfies the constraint with margin.
- `warning` — the threshold is satisfied but `warning_threshold` was crossed (closer to the breach boundary).
- `breached` — the current value violates the constraint.
- `unknown` — the current value cannot be derived (missing data, divide-by-zero, or unsupported `constraint_type`). The reason is recorded in `metadata["reason"]` and `message`.

### 25.4 ConstraintBook and ConstraintEvaluator

`ConstraintBook` API:

- `add_constraint(record)` — store; rejects duplicates; emits `constraint_added` to the ledger.
- `get_constraint(constraint_id)`
- `list_by_owner(owner_id)` / `list_by_type(constraint_type)`
- `all_constraints()`
- `snapshot()` — sorted, JSON-friendly list of all constraints.

`ConstraintEvaluator` API:

- `evaluate_constraint(constraint, balance_sheet_view)` — evaluate one constraint against an already-built view; emits `constraint_evaluated` to the ledger when present.
- `evaluate_owner(owner_id, *, as_of_date=None)` — build the owner's view once and evaluate all of that owner's constraints.
- `evaluate_all(*, as_of_date=None)` — discover every owner that has any constraint, evaluate everything.
- `snapshot(*, as_of_date=None)` — wrapper around `evaluate_all` returning JSON-friendly evaluations.

The evaluator must not mutate `OwnershipBook`, `ContractBook`, `PriceBook`, or `ConstraintBook`. Test [`test_evaluator_does_not_mutate_source_books`](../tests/test_constraints.py) enforces this.

### 25.5 Supported constraint types

Each supported type maps a `BalanceSheetView` to a single derived number. The evaluator then compares this number against the constraint's `threshold` and `warning_threshold`.

| `constraint_type`                   | Derived value                                            | Natural comparison |
| ----------------------------------- | -------------------------------------------------------- | ------------------ |
| `max_leverage`                      | `liabilities / asset_value`                              | `<=`               |
| `min_net_asset_value`               | `net_asset_value`                                        | `>=`               |
| `min_cash_like_assets`              | `cash_like_assets` (registry-derived)                    | `>=`               |
| `min_collateral_coverage`           | `collateral_value / debt_principal`                      | `>=`               |
| `max_single_asset_concentration`    | `max(asset_value across target_ids) / asset_value`       | `<=`               |

Each derivation reports `(None, reason)` when the value cannot be computed. The most common unknown cases are:

- `max_leverage`: `asset_value == 0`.
- `min_cash_like_assets`: registry not provided or no cash-typed asset registered.
- `min_collateral_coverage`: `collateral_value` or `debt_principal` unavailable, or `debt_principal == 0`.
- `max_single_asset_concentration`: `asset_breakdown` empty, or `target_ids` set but none of the named assets are owned.

Unsupported `constraint_type` strings are not errors. They resolve to `status="unknown"` with `metadata["reason"] == "unsupported_constraint_type"`. This lets the codebase carry forward declarative constraints that later milestones will teach the evaluator to interpret.

### 25.6 Comparison and warning logic

The evaluator uses a single helper `_classify(current, threshold, warning_threshold, comparison)`:

1. If `current` violates the constraint relative to `threshold` under `comparison`, return `"breached"`.
2. Else if `warning_threshold is not None` and `current` violates the constraint relative to `warning_threshold` under the same `comparison`, return `"warning"`.
3. Otherwise return `"ok"`.

Convention: for `<=` constraints, `warning_threshold < threshold`. For `>=` constraints, `warning_threshold > threshold`. The classifier does not enforce this convention; it simply applies the same comparison to both boundaries.

### 25.7 Ledger event types

- `constraint_added` — emitted by `ConstraintBook.add_constraint` when a ledger is configured.
- `constraint_evaluated` — emitted by `ConstraintEvaluator.evaluate_constraint` for every evaluation. Higher-level methods (`evaluate_owner`, `evaluate_all`, `snapshot`) compose on `evaluate_constraint`, so they automatically log every evaluation.

### 25.8 Kernel wiring

`WorldKernel` exposes:

- `kernel.constraints: ConstraintBook` — storage.
- `kernel.constraint_evaluator: ConstraintEvaluator` — runner, wired to `kernel.balance_sheets`.

Both are constructed in `__post_init__` with the kernel's `clock` and `ledger`.

### 25.9 What v0.6 does not do

v0.6 must not introduce:

- automated reactions to breaches (no margin calls, no downgrades, no liquidations, no covenant trips)
- regulatory threshold catalogs
- cross-constraint dependency resolution
- time-windowed or path-dependent constraints (e.g., "leverage above 0.7 for 90 consecutive days")
- agents that read their own evaluations and act on them
- price formation, market clearing, or balance-sheet mutation triggered by constraint state

These are deliberate omissions. The evaluator reports state; consequence-engineering belongs to later milestones.

### 25.10 v0.6 success criteria

v0.6 is complete when **all** of the following hold:

1. `ConstraintRecord` and `ConstraintEvaluation` exist with all required fields and are immutable.
2. `ConstraintBook` provides `add_constraint`, `get_constraint`, `list_by_owner`, `list_by_type`, and `snapshot`.
3. `ConstraintEvaluator` provides `evaluate_constraint`, `evaluate_owner`, `evaluate_all`, and `snapshot`.
4. The five supported constraint types in §25.5 produce correct ok / warning / breached classifications under the standard derivations.
5. Missing values and unsupported types resolve to `status="unknown"` with a reason; nothing crashes.
6. `constraint_added` and `constraint_evaluated` are recorded to the ledger when configured.
7. The evaluator does not mutate any source book (ownership, contracts, prices, constraints).
8. The kernel exposes `kernel.constraints` and `kernel.constraint_evaluator` with default wiring.
9. All previous milestones (v0, v0.2, v0.3, v0.4, v0.5) continue to pass.

---

## 26. Information / Signal Layer (v0.7)

The v0.7 milestone introduces information as a first-class world object. A signal is a discrete claim, observation, report, or rumor — registered, queryable, and addressable from `WorldEvent` payloads — with no built-in notion of how anyone reacts to it.

### 26.1 Why a signal layer

§22 introduced a transport channel for events; §23 introduced ownership / contract / price state; §24 introduced derived balance sheet views. None of those layers represent *information* per se: ratings, earnings reports, news, regulatory announcements, leaks, rumors. The signal layer fills that gap.

The constitutional rule from §15.4 still applies: **signals do not directly mutate balance sheets, prices, contracts, or ownership.** They become inputs that future agents may observe, weigh, and act upon. v0.7 implements the storage and visibility plumbing only.

### 26.2 InformationSignal

`InformationSignal` is an immutable record. Its fields:

- `signal_id` — stable unique identifier.
- `signal_type` — domain-neutral string (e.g., `"rating_action"`, `"earnings_report"`, `"news"`, `"internal_memo"`).
- `subject_id` — the WorldID the signal is *about* (typically an agent or asset).
- `source_id` — the WorldID that produced the signal.
- `published_date` — ISO date the signal was published.
- `effective_date` — ISO date the signal becomes observable (defaults to `published_date` when omitted).
- `visibility` — one of `"public"`, `"private"`, `"restricted"`, `"leaked"`, `"rumor"`, `"delayed"`. Unsupported values are rejected at construction.
- `credibility` — float in `[0, 1]`, source quality (not enforced as an interpretive ceiling).
- `confidence` — float in `[0, 1]`, source's certainty about the content.
- `payload` — arbitrary mapping of signal-specific data (e.g., `{"rating": "BBB-"}`).
- `related_ids` — tuple of other WorldIDs the signal references.
- `metadata` — bag for non-standard attributes; `metadata["allowed_viewers"]` controls access for `private` and `restricted` signals.

Signals are immutable: `add_signal` stores the record once; subsequent updates require a new signal with a new id (preserving the audit trail).

### 26.3 Visibility model

| visibility | Who can see it (subject to effective_date) |
|----------|---------------------------------------------|
| public   | anyone |
| leaked   | anyone (label-only differentiation from public) |
| rumor    | anyone (low credibility implied by convention; not enforced) |
| delayed  | anyone, but only on or after `effective_date` |
| private  | only ids in `metadata["allowed_viewers"]` |
| restricted | only ids in `metadata["allowed_viewers"]` |

The effective_date filter applies to *all* visibilities, not just `delayed`. A signal whose `effective_date` is later than the query's `as_of_date` is invisible regardless of label.

For v0.7, the differences between `leaked`, `rumor`, and `delayed` are bookkeeping tags. v0.7 does **not** implement narrative interpretation: rumor decay, leak propagation, partial visibility, source-credibility weighting, or analyst summarization. Those belong to later milestones that will reason about how agents weigh information.

### 26.4 SignalBook API

- `add_signal(signal)` — store; rejects duplicates; records `signal_added` to the ledger.
- `get_signal(signal_id)` — lookup; raises `UnknownSignalError` if not found.
- `list_by_subject(subject_id)` / `list_by_type(signal_type)` / `list_by_source(source_id)` — filter without applying visibility (the caller is the system itself, not an observer).
- `list_visible_to(observer_id, *, as_of_date=None)` — apply visibility AND effective_date filtering.
  - When `as_of_date` is omitted, the book uses its `clock.current_date` if a clock is wired.
  - When neither `as_of_date` nor `clock` is available, the effective_date filter is **skipped** (all signals treated as effective). This is a v0.7 simplification documented in `test_list_visible_to_without_clock_or_date_skips_effective_date_filter`.
- `mark_observed(signal_id, observer_id, *, as_of_date=None)` — record an explicit observation; raises `SignalError` if the signal is not visible to that observer; emits `signal_observed` to the ledger.
- `all_signals()` / `snapshot()` — administrative views; visibility-blind.

`list_*` queries do not record to the ledger (they are reads). Only `add_signal` and `mark_observed` write.

### 26.5 Integration with the EventBus (§22)

A `WorldEvent` may carry a `signal_id` in its payload. This is the canonical pattern for "I want to tell you about a signal":

```python
WorldEvent(
    event_id="event:rating_announcement",
    simulation_date="2026-01-01",
    source_space="information",
    target_spaces=("investors",),
    event_type="signal_emitted",
    payload={"signal_id": "signal:rating_001"},
    related_ids=("signal:rating_001",),
)
```

The receiving space's `observe()` method can resolve the `signal_id` against `kernel.signals.get_signal(...)`. This pattern decouples *transport* (who hears about the signal existing) from *interpretation* (who actually reads its content).

Critically: **event delivery is not gated by signal visibility.** The bus delivers events to whoever is in `target_spaces`. Whether the receiver is *allowed* to read the referenced signal is a separate query, made through `SignalBook.list_visible_to` or `signal.is_visible_to`. This separation is intentional — coupling transport to visibility would entangle two policies.

### 26.6 Ledger event types

- `signal_added` — emitted by `SignalBook.add_signal` when a ledger is configured.
- `signal_observed` — emitted by `SignalBook.mark_observed`. Optional, but when used it captures the explicit causality between a receiver and a signal.
- `signal_emitted` — already defined in §22; conventionally used as the `event_type` of a `WorldEvent` whose payload references a `signal_id`.

These three types form a complete information audit trail: when the signal entered the world, when it was sent over the bus, and when an observer acknowledged it.

### 26.7 Kernel wiring

`WorldKernel` exposes `kernel.signals: SignalBook`. The book is constructed by default and shares the kernel's `clock` and `ledger` via `__post_init__`, alongside the existing books (`ownership`, `contracts`, `prices`, `constraints`).

### 26.8 What v0.7 does not do

v0.7 must not introduce:

- agent reactions to signals (no buying after a downgrade, no panic, no rebalancing)
- price movement triggered by signals
- credit decisions based on signals
- analyst report generation
- narrative formation, rumor decay, or leak propagation
- coupling between event delivery and signal visibility (these remain orthogonal)
- cross-signal aggregation or "consensus" computation

These are deliberately out of scope. v0.7 stores information and lets it flow; later milestones will teach the world to interpret it.

### 26.9 v0.7 success criteria

v0.7 is complete when **all** of the following hold:

1. `InformationSignal` exists with all required fields and is immutable.
2. `SignalBook` provides `add_signal`, `get_signal`, `list_by_subject`, `list_by_type`, `list_by_source`, `list_visible_to`, `mark_observed`, `all_signals`, and `snapshot`.
3. Visibility rules enforce public/leaked/rumor as anyone-visible, private/restricted as `allowed_viewers`-only, and `delayed` as effective_date-gated.
4. Unsupported visibility values are rejected at construction.
5. `signal_added` is recorded to the ledger on every `add_signal`. `signal_observed` is recorded on every `mark_observed`.
6. A `WorldEvent` whose payload contains `signal_id` flows through the event bus and lets the receiver resolve the signal via `SignalBook.get_signal`.
7. `SignalBook` operations do not mutate `OwnershipBook`, `ContractBook`, `PriceBook`, or `ConstraintBook`.
8. The kernel exposes `kernel.signals` with default wiring.
9. All previous milestones (v0, v0.2, v0.3, v0.4, v0.5, v0.6) continue to pass.
