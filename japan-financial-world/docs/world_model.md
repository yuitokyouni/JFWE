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

---

## 27. Minimum Corporate State (v0.8)

The v0.8 milestone gives `CorporateSpace` its first piece of native state: a registry of firms keyed by `firm_id`, plus read-only access to the kernel-level projections that describe each firm's financial position, constraint compliance, and observable signals.

This is the first time a domain space carries any state of its own. v0.8 establishes the pattern that every later domain space will follow: store identity-level facts internally, derive everything else from the world's books.

### 27.1 Why a minimum corporate state

Earlier milestones can already represent firms entirely through kernel-level books — a firm's holdings live in `OwnershipBook`, its loans in `ContractBook`, the latest prices of its assets in `PriceBook`, etc. So why should `CorporateSpace` carry *any* internal state?

Because some facts are domain-classification facts, not balance-sheet facts: which sector the firm operates in, what tier (large / mid / small) it occupies, what status (active / delisted / under_review) it is currently in. These influence which firms are picked up by which queries. They are unambiguously "Corporate Space's responsibility" — neither `OwnershipBook` nor any projection has a natural place to put them.

But everything *else* about a firm — its asset value, its liabilities, its leverage, its constraint compliance, the signals it has emitted or received — must continue to live in the kernel-level books. v0.8 enforces this by giving `CorporateSpace` *only* the classification fields, and *only* read access (via projections) to everything else.

This is the load-bearing rule: **CorporateSpace classifies; the world books value.**

### 27.2 FirmState

`FirmState` is an immutable record. Its fields:

- `firm_id` — WorldID of the firm.
- `sector` — domain-neutral string label (default `"unspecified"`).
- `tier` — domain-neutral string label (default `"unspecified"`).
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

There is intentionally no `cash`, `revenue`, `profit`, `leverage`, `assets`, or `liabilities` field. Anything derivable from the world's books is computed, not stored.

### 27.3 CorporateSpace API additions

`CorporateSpace` now exposes:

- `add_firm_state(firm_state)` — register a firm; rejects duplicate `firm_id`; emits `firm_state_added` to the ledger.
- `get_firm_state(firm_id)` — returns `FirmState` or `None`. **Does not raise** for unknown firms.
- `list_firms()` — tuple of all `FirmState`s in **insertion order** (a stable v0.8 invariant). Useful for audit-style reads where "added Nth" matters.
- `snapshot()` — JSON-friendly view of the space's firms, **sorted by `firm_id`** (deterministic regardless of insertion order). Use `list_firms()` if insertion order matters.

And read-only accessors over the kernel projections:

- `get_balance_sheet_view(firm_id, *, as_of_date=None)` — returns a `BalanceSheetView`, or `None` when the projector is unbound or no date can be resolved.
- `get_constraint_evaluations(firm_id, *, as_of_date=None)` — returns a tuple of `ConstraintEvaluation`s for the firm, or `()` when no evaluator is bound.
- `get_visible_signals(observer_id, *, as_of_date=None)` — returns the tuple of `InformationSignal`s visible to the given observer, or `()` when no signal book is bound.

All accessors return safe defaults when refs are unbound. None of them mutate any source book.

### 27.4 The bind() pattern

To pass kernel-level books and projectors into a space without coupling the kernel to specific space subclasses, `BaseSpace` exposes a `bind(kernel)` hook. Default implementation is a no-op.

`WorldKernel.register_space(space)` invokes `space.bind(self)` after Registry/Ledger registration but before task scheduling. Concrete spaces override `bind()` to capture the references they need:

```python
def bind(self, kernel):
    if self.registry is None:
        self.registry = kernel.registry
    if self.balance_sheets is None:
        self.balance_sheets = kernel.balance_sheets
    ...
```

Two important properties:

1. **bind() is opt-in**: the default no-op means existing empty spaces (Investor, Bank, etc.) keep working unchanged.
2. **bind() does not overwrite explicit refs**: tests can pass refs at construction (e.g., a custom ledger) and `bind()` will leave those alone, only filling in unset fields. This makes it safe to register the same space pattern in tests with custom wiring.

Spaces that need additional injection points add corresponding fields and extend their `bind()` override. The kernel does not need to know.

#### bind() contract for overrides

Every `bind()` override (now and in future domain spaces) must satisfy four properties:

1. **Idempotent.** Calling `bind()` more than once must be safe. The second call should produce the same end state as the first. Concretely: gate every assignment on `is None` so a re-call is a no-op.
2. **Fill-only.** `bind()` must not overwrite a reference that is already set on the space. It only fills in fields that are currently `None`.
3. **Explicit constructor refs win.** Anything passed via the dataclass constructor (e.g., `CorporateSpace(ledger=custom_ledger)`) is authoritative. `bind()` never replaces it. This is the rule that makes test wiring tractable.
4. **Hot-swap / reload is out of scope.** v0.8 does not support rebinding a space to a different kernel mid-simulation. Overrides are not expected to handle that case. Future milestones may relax this; for now, register a space exactly once with exactly one kernel.

These four rules are documented on `BaseSpace.bind` and on every concrete override. Tests verify property 3 (`test_bind_does_not_overwrite_explicit_construction_refs`); properties 1, 2, and 4 are invariants of the implementation pattern.

### 27.5 What CorporateSpace must not do

v0.8 explicitly forbids the following inside `CorporateSpace` (or any space that follows this pattern):

- mutating `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, or `SignalBook`
- mutating `BankSpace`, `InvestorSpace`, `ExchangeSpace`, `RealEstateSpace`, or any other space's internal state
- implementing revenue / profit / earnings update logic
- implementing asset sale or borrowing decisions
- implementing scenario or narrative logic
- reacting to constraint breaches or signals (reading is allowed; reacting is not)
- producing `WorldEvent`s that carry domain-level decisions (transport-level events for v0.3 testing remain fine)

The space reads. It classifies. It does not act.

### 27.6 Ledger event types

- `firm_state_added` — emitted by `CorporateSpace.add_firm_state` when a ledger is configured.

Existing ledger types continue to apply: reading projections through the space inherits whatever logging the underlying projector or evaluator does. In particular, calling `get_constraint_evaluations` triggers the constraint evaluator's `constraint_evaluated` records (because that is the evaluator's standard behavior). The space adds no separate evaluation record.

### 27.7 Pattern for future domain spaces

`CorporateSpace`'s shape is the template for every future domain space:

- Hold a small dataclass map of identity-level state (e.g., `BankState`, `InvestorState`, `PropertyState`).
- Override `bind()` to capture kernel projections.
- Provide `add_*_state` / `get_*_state` / `list_*` for the local registry.
- Provide read-only accessors that delegate to kernel projections.
- Override `snapshot()` to expose the local state.
- Never mutate external books or other spaces.

Domain *behavior* — bank credit decisions, investor portfolio choices, property valuations — belongs to later milestones that will operate on top of this skeleton.

### 27.8 v0.8 success criteria

v0.8 is complete when **all** of the following hold:

1. `FirmState` exists with all required fields and is immutable.
2. `CorporateSpace` holds a `firm_id -> FirmState` mapping and exposes `add_firm_state`, `get_firm_state`, `list_firms`, and `snapshot`.
3. `CorporateSpace` exposes read-only accessors `get_balance_sheet_view`, `get_constraint_evaluations`, and `get_visible_signals`.
4. Unbound or missing references resolve to `None` / `()` rather than raising.
5. `BaseSpace.bind(kernel)` exists as a no-op; `WorldKernel.register_space` invokes it; `CorporateSpace.bind` captures kernel projections without overwriting explicit construction refs.
6. `firm_state_added` is recorded to the ledger when configured.
7. `CorporateSpace` does not mutate `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, or `SignalBook`.
8. v0.2 scheduler integration still works: an empty world with a populated `CorporateSpace` runs for one year and the scheduler still invokes the space at its declared frequencies.
9. All previous milestones (v0 through v0.7) continue to pass.

---

## 28. Minimum Bank / Debt State (v0.9)

The v0.9 milestone applies the `CorporateSpace` template (§27) to `BankSpace`, with one structural addition: a **lending-exposure projection** derived from `ContractBook`. v0.9 does not add credit behavior of any kind.

### 28.1 Why mirror the corporate pattern

`BankSpace` is the second domain space to gain native state. The shape established in §27 — *classify locally, derive everything else* — is intentionally repeated here so the pattern is verifiable on more than one example. By the time a third space adopts the same skeleton (Investor or RealEstate), the repetition will tell us whether a `DomainSpace` mixin is justified.

For now, expect:

- An immutable identity dataclass (`BankState`).
- A `bind()` override that captures the kernel projections the space needs.
- Read-only accessors that delegate to those projections.
- Insertion-ordered `list_*` and id-sorted `snapshot()`.
- One ledger record type per space (`bank_state_added`).
- A new derived view class (`LendingExposure`) introduced because the bank's natural query — "what loans am I holding?" — has no equivalent in CorporateSpace.

### 28.2 BankState

`BankState` is an immutable record. Its fields:

- `bank_id` — WorldID of the bank.
- `bank_type` — domain-neutral string label (default `"unspecified"`). Examples: `"city_bank"`, `"regional_bank"`, `"trust_bank"`, `"shinkin"`. v0.9 enumerates none of these — types are free-form strings.
- `tier` — domain-neutral string label (default `"unspecified"`).
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

Like `FirmState`, `BankState` deliberately omits everything balance-sheet-derivable. There is no `capital`, `deposits`, `loan_book`, `npl_ratio`, or `spread` field. Anything computable from `OwnershipBook` × `ContractBook` × `PriceBook` is computed, not stored.

### 28.3 LendingExposure

`LendingExposure` is the v0.9 addition. It is a *projection* derived from `ContractBook`, not a stored fact, and is rebuilt on every query.

Its fields:

- `contract_id` — the underlying contract's id.
- `lender_id` — always the bank that the projection was built for.
- `borrower_id` — taken from `metadata["borrower_id"]` on the contract; may be `None` if the contract did not declare one.
- `principal` — face-value principal as recorded on the contract; may be `None`.
- `contract_type` — copied from the contract verbatim.
- `status` — copied from the contract verbatim. **v0.9 does not filter by status** — settled, defaulted, and active loans all appear.
- `collateral_asset_ids` — copied from the contract verbatim.

`LendingExposure` is intentionally narrow. It is what `BankSpace` needs to answer "list the loans where this bank is the explicit lender" without forcing every caller to grep contract metadata themselves. It is not a credit-quality classification, a risk-weighted exposure, or a capital-relief view. Those are deferred.

### 28.4 BankSpace API additions

BankSpace now exposes:

- `add_bank_state(bank_state)` — register a bank; rejects duplicate `bank_id`; emits `bank_state_added` to the ledger.
- `get_bank_state(bank_id)` — returns `BankState` or `None`. Does not raise for unknown banks.
- `list_banks()` — tuple of all `BankState`s in **insertion order**.
- `snapshot()` — JSON-friendly view sorted by `bank_id`.

Read-only kernel projections:

- `get_balance_sheet_view(bank_id, *, as_of_date=None)`
- `get_constraint_evaluations(bank_id, *, as_of_date=None)`
- `get_visible_signals(observer_id, *, as_of_date=None)`

Bank-specific contract views:

- `list_contracts_for_bank(bank_id)` — broad: every contract where the bank appears in `parties`. Does not filter by role. Useful for "where is this bank involved at all?".
- `list_lending_exposures(bank_id)` — narrow: contracts where `metadata["lender_id"] == bank_id`. Returns `tuple[LendingExposure, ...]`.

All accessors return safe defaults (`None` / `()`) when their underlying refs are unbound. None of them mutate any source book.

### 28.5 Why metadata-only role inference

`list_lending_exposures` deliberately filters on `metadata["lender_id"]` and **does not infer role from `parties` order**. A contract with `parties=("bank:x", "firm:y")` but no metadata role tags is invisible to `list_lending_exposures` even though many real-world conventions would interpret position 0 as the lender.

This is the same v0.5 / v0.7 design rule, restated for the bank context: **roles are opt-in via metadata, not inferred from data shape**. Inferring would mean two sources of truth (party order and metadata) could disagree, and silent role guessing is exactly the kind of hidden coupling §14 forbids.

If a contract should be a lending exposure for the bank, it must declare `metadata["lender_id"] = bank_id` (and ideally `metadata["borrower_id"]` too). `test_list_lending_exposures_does_not_infer_role_from_parties_order` enforces this.

### 28.6 What BankSpace must not do

v0.9 explicitly forbids the following inside `BankSpace`:

- mutating `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, or `SignalBook`
- mutating `CorporateSpace`, `InvestorSpace`, `ExchangeSpace`, `RealEstateSpace`, or any other space's internal state
- implementing lending decisions, credit underwriting, or origination
- implementing credit tightening, spread updates, or rate adjustments
- implementing default detection, non-performing classification, or covenant trips
- implementing collateral haircut, LTV breach, or margin-call logic
- implementing scenario logic
- producing `WorldEvent`s that carry credit-decision payloads (transport-level events for testing remain fine)

The space reads contracts. It surfaces them as lending exposures. It does not decide.

### 28.7 Ledger event types

- `bank_state_added` — emitted by `BankSpace.add_bank_state` when a ledger is configured.

Existing types continue to apply: reading projections through the space inherits whatever logging the underlying projector or evaluator does. Notably, `list_lending_exposures` produces no ledger record on its own — it is a query, not a state change.

### 28.8 v0.9 success criteria

v0.9 is complete when **all** of the following hold:

1. `BankState` exists with all required fields and is immutable.
2. `LendingExposure` exists as an immutable projection record.
3. `BankSpace` holds a `bank_id -> BankState` mapping and exposes `add_bank_state`, `get_bank_state`, `list_banks`, and `snapshot`.
4. `BankSpace` exposes the four read-only kernel-projection accessors and the two contract-derived helpers (`list_contracts_for_bank`, `list_lending_exposures`).
5. `list_lending_exposures` filters strictly on `metadata["lender_id"]`; it does not infer role from `parties` order.
6. `bank_state_added` is recorded to the ledger when configured.
7. `BankSpace` does not mutate any source book or any other space.
8. `BankSpace.bind` follows the four-property contract from §27.4.
9. v0.2 scheduler integration still works: a populated `BankSpace` runs for one year and is invoked at its declared frequencies (DAILY × 365, QUARTERLY × 4).
10. All previous milestones (v0 through v0.8) continue to pass.

---

## 29. Minimum Investor State (v0.10)

The v0.10 milestone applies the same domain-space template (§27 / §28) to `InvestorSpace`, with one structural addition: a **portfolio-exposure projection** derived from `OwnershipBook` × `PriceBook` × `Registry`. v0.10 does not add trading behavior.

### 29.1 Three examples is the threshold

v0.10 is the third domain space to follow the same pattern: an immutable identity record (`InvestorState`), a `bind()` override, kernel-projection accessors, insertion-ordered `list_*`, id-sorted `snapshot()`, one ledger record type, and one new domain-specific projection. The first three concrete examples are:

| Space            | Identity     | Domain-specific projection |
| ---------------- | ------------ | -------------------------- |
| CorporateSpace   | FirmState    | (none)                     |
| BankSpace        | BankState    | LendingExposure            |
| InvestorSpace    | InvestorState | PortfolioExposure         |

Three is the threshold. After v0.10 the structural similarity is unmistakable: the only meaningful variations are which kernel refs to capture and which derived projection to expose. This makes a future `DomainSpace` mixin or template a defensible refactor — but that abstraction is **out of scope for v0.10**. The pattern is established here in concrete, repeatable form, and the call to factor it can be made later when the costs of repetition (boilerplate, drift between spaces) are clearly visible.

### 29.2 InvestorState

`InvestorState` is an immutable record. Its fields:

- `investor_id` — WorldID of the investor.
- `investor_type` — domain-neutral string label (default `"unspecified"`). Examples: `"pension_fund"`, `"hedge_fund"`, `"insurer"`, `"retail"`, `"sovereign_wealth_fund"`. v0.10 enumerates none of these.
- `tier` — domain-neutral string label (default `"unspecified"`).
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

Like `FirmState` and `BankState`, `InvestorState` deliberately omits everything derivable. There is no `aum`, `nav`, `target_allocation`, `risk_budget`, or `mandate` field. Anything computable from `OwnershipBook` × `PriceBook` × `ContractBook` is computed, not stored.

### 29.3 PortfolioExposure

`PortfolioExposure` is the v0.10 addition. It is a *projection* — rebuilt on every query, never stored.

Its fields:

- `investor_id` — the investor the projection was built for.
- `asset_id` — the WorldID of the held asset.
- `quantity` — copied from the underlying `OwnershipRecord`.
- `latest_price` — most recent price from `PriceBook`, or `None` if no observation exists.
- `market_value` — `quantity × latest_price` when both are present; `None` otherwise.
- `asset_type` — taken from `Registry.get(asset_id).type` if the asset is registered, else `None`.
- `metadata` — bag containing `{"missing_price": True}` and/or `{"missing_asset_type": True}` flags so callers can detect gaps without re-querying.

PortfolioExposure is intentionally narrow. It is what InvestorSpace needs to answer "what does this investor hold, and what is each position worth right now?" without forcing every caller to join three books themselves. It is **not** an allocation report, a target/actual comparison, a risk decomposition, or a P&L view. Those are deferred.

Specifically, v0.10 does **not**:

- compute portfolio-level totals or weights
- classify positions as core / satellite / hedge
- infer strategy or intent from the holdings
- mark positions as off-target or in-need-of-rebalancing
- distinguish liquid from illiquid assets

These are all valuation / strategy / interpretation concerns, and they are out of scope.

### 29.4 InvestorSpace API additions

InvestorSpace now exposes:

- `add_investor_state(investor_state)` — register; rejects duplicates; emits `investor_state_added` to the ledger.
- `get_investor_state(investor_id)` — returns `InvestorState` or `None`.
- `list_investors()` — tuple in **insertion order**.
- `snapshot()` — sorted by `investor_id`.

Read-only kernel projections:

- `get_balance_sheet_view(investor_id, *, as_of_date=None)`
- `get_constraint_evaluations(investor_id, *, as_of_date=None)`
- `get_visible_signals(observer_id, *, as_of_date=None)`

Investor-specific ownership views:

- `list_portfolio_positions(investor_id)` — broad: raw `OwnershipRecord`s held by the investor (no valuation, no asset typing). Equivalent to `kernel.ownership.get_positions(investor_id)`.
- `list_portfolio_exposures(investor_id)` — narrow: each position joined with the latest price and registry-derived asset type. Returns `tuple[PortfolioExposure, ...]`.

All accessors return safe defaults when their refs are unbound. None of them mutate any source book.

### 29.5 Why missing data does not crash

`list_portfolio_exposures` is intentionally tolerant of incomplete data:

- A position with no `PriceBook` observation still produces a `PortfolioExposure` — quantity is preserved, `latest_price` and `market_value` are `None`, and `metadata["missing_price"] = True`.
- A position whose `asset_id` is not in the `Registry` still produces a `PortfolioExposure` — `asset_type` is `None`, and `metadata["missing_asset_type"] = True`. Valuation still happens if a price is available.

This rule mirrors `BalanceSheetProjector` (§24): the projector reports what it can compute and is honest about what it cannot. Crashing would force every caller to defensively pre-check whether all needed data exists before issuing the read. That defeats the point of having a projection layer.

### 29.6 What InvestorSpace must not do

v0.10 explicitly forbids the following inside `InvestorSpace`:

- mutating `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, or `SignalBook`
- mutating `CorporateSpace`, `BankSpace`, `ExchangeSpace`, `RealEstateSpace`, or any other space's internal state
- implementing trading decisions, order generation, or rebalancing
- implementing allocation logic, mandate enforcement, or strategy selection
- implementing price impact, liquidity, or market microstructure
- implementing performance attribution, benchmark comparison, or risk budgeting
- implementing investor-to-investor activist behavior
- implementing scenario logic
- producing `WorldEvent`s that carry trading-decision payloads (transport-level events for testing remain fine)

The space reads positions. It surfaces them as exposures. It does not act.

### 29.7 Ledger event types

- `investor_state_added` — emitted by `InvestorSpace.add_investor_state` when a ledger is configured.

Existing types continue to apply. `list_portfolio_exposures` is a query and produces no ledger record on its own.

### 29.8 v0.10 success criteria

v0.10 is complete when **all** of the following hold:

1. `InvestorState` exists with all required fields and is immutable.
2. `PortfolioExposure` exists as an immutable projection record.
3. `InvestorSpace` holds an `investor_id -> InvestorState` mapping and exposes `add_investor_state`, `get_investor_state`, `list_investors`, and `snapshot`.
4. `InvestorSpace` exposes the three read-only kernel-projection accessors and the two ownership-derived helpers (`list_portfolio_positions`, `list_portfolio_exposures`).
5. `list_portfolio_exposures` joins `OwnershipBook` × `PriceBook` × `Registry` and never crashes on missing data; missing-data flags appear in `metadata`.
6. `investor_state_added` is recorded to the ledger when configured.
7. `InvestorSpace` does not mutate any source book or any other space.
8. `InvestorSpace.bind` follows the four-property contract from §27.4.
9. v0.2 scheduler integration still works: a populated `InvestorSpace` runs for one year and is invoked at its declared frequencies (DAILY × 365, MONTHLY × 12).
10. All previous milestones (v0 through v0.9) continue to pass.

---

## 30. DomainSpace Extraction (v0.10.1)

After v0.10 introduced the third concrete domain space, the read-only-accessor and `bind()` boilerplate had been written three times in nearly identical form. v0.10.1 is a pure refactor that extracts the duplicated parts into a `DomainSpace` base class without changing any observable behavior.

### 30.1 Review result

The duplication was real and mechanical:

| Concern                              | Before                                     | After                                |
| ------------------------------------ | ------------------------------------------ | ------------------------------------ |
| Common ref fields                    | declared in 3 dataclasses                  | declared once on `DomainSpace`       |
| `bind()` for common refs             | 3 near-identical implementations           | one canonical implementation         |
| `get_balance_sheet_view` accessor    | 3 copies (different param names)           | one accessor on `DomainSpace`        |
| `get_constraint_evaluations` accessor | 3 copies                                   | one accessor on `DomainSpace`        |
| `get_visible_signals` accessor       | 3 copies                                   | one accessor on `DomainSpace`        |

Net effect:

- `spaces/corporate/space.py`: 203 → 110 lines (−93)
- `spaces/banking/space.py`: 271 → 180 lines (−91)
- `spaces/investors/space.py`: 305 → 210 lines (−95)
- `spaces/domain.py`: new, 167 lines
- Total: 779 → 667 lines (−112, −14%)

All 266 tests pass after the refactor (10 new contract tests for DomainSpace itself, 256 inherited from previous milestones).

### 30.2 What DomainSpace owns

```python
@dataclass
class DomainSpace(BaseSpace):
    registry: Registry | None = None
    balance_sheets: BalanceSheetProjector | None = None
    constraint_evaluator: ConstraintEvaluator | None = None
    signals: SignalBook | None = None
    ledger: Ledger | None = None
    clock: Clock | None = None

    def bind(self, kernel) -> None: ...
    def get_balance_sheet_view(self, agent_id, *, as_of_date=None): ...
    def get_constraint_evaluations(self, agent_id, *, as_of_date=None): ...
    def get_visible_signals(self, observer_id, *, as_of_date=None): ...
```

The accessors take a generic `agent_id` (or `observer_id`) parameter. Per-domain documentation explains that the natural caller passes their own domain id (firm_id / bank_id / investor_id), but the underlying projectors are agent-agnostic, so a unified parameter name is honest.

### 30.3 What DomainSpace deliberately does NOT own

The extraction was kept narrow on purpose. The following stayed in concrete spaces:

- **Domain-specific state records**: `FirmState`, `BankState`, `InvestorState`, and their `Duplicate*StateError` exception classes. Each captures a different vocabulary (sector / bank_type / investor_type) and merging would either lose that or force a generic field name that reads worse at every call site.
- **Domain-specific CRUD**: `add_firm_state` / `add_bank_state` / `add_investor_state`, etc. Naming these `add_state` would erase the type-level distinction.
- **`list_*` and `snapshot()` semantics**: each space's snapshot has a different shape (`firms` / `banks` / `investors`) and naming is informative.
- **Domain-specific projections**: `LendingExposure` (BankSpace) and `PortfolioExposure` (InvestorSpace) live alongside their owning spaces. CorporateSpace has none.
- **Additional kernel refs that only some spaces need**: `contracts` for BankSpace; `ownership` and `prices` for InvestorSpace. Subclasses extend `bind()` by calling `super().bind(kernel)` first and then capturing their own refs.

### 30.4 The bind() extension pattern

Subclass `bind()` overrides are now reduced to two patterns:

**No additional refs (CorporateSpace):**

```python
# CorporateSpace inherits DomainSpace.bind() unchanged.
# No bind() override needed.
```

**Additional refs (BankSpace, InvestorSpace):**

```python
def bind(self, kernel):
    super().bind(kernel)
    if self.contracts is None:
        self.contracts = kernel.contracts
```

The four-property contract from §27.4 (idempotent / fill-only / explicit refs win / no hot-swap) is now enforced once on `DomainSpace.bind` and inherited by every subclass.

### 30.5 Why the extraction was safe

Three conditions held, and all three were verified:

1. **No keyword-arg callers of the renamed parameters**: a grep over the test suite confirmed no test called `get_balance_sheet_view(firm_id=...)` or similar. All call sites are positional.
2. **No introspection on subclass-declared fields**: the existing tests assert on attribute *values* (e.g., `space.balance_sheets is kernel.balance_sheets`), not on which class declared the field. Inheritance is transparent here.
3. **Behavior preserved**: `pytest -q` reports the same 256-pass result before and after the refactor (now 266 with the 10 new DomainSpace contract tests).

### 30.6 Why we did not abstract more

The temptation when a third repetition appears is to factor everything that *can* be factored. We deliberately resisted in two places:

- **State CRUD**: collapsing `add_firm_state` / `add_bank_state` / `add_investor_state` into a single `add_state` method on a generic Mapping[id, State] would compile, but every call site would lose the per-domain naming that makes test code self-explanatory. The cost (call-site clarity) outweighed the benefit (~30 lines saved).
- **Snapshot shape**: each space's snapshot returns `{firms: [...]}`, `{banks: [...]}`, or `{investors: [...]}`. Renaming the inner key to a generic `entries` or `items` would force every consumer to know which space they're reading. This is a serialization contract, and serialization contracts deserve specific names.

Both decisions are reversible. If consumer code grows large enough that the per-domain naming becomes friction, the call-site cost is what to measure first.

### 30.7 v0.10.1 success criteria

v0.10.1 is complete when **all** of the following hold:

1. `DomainSpace` exists, inherits `BaseSpace`, owns the six common ref fields, and implements `bind()` plus the three read-only accessors.
2. CorporateSpace, BankSpace, and InvestorSpace inherit from `DomainSpace` instead of `BaseSpace`.
3. CorporateSpace has no `bind()` override (inherits `DomainSpace.bind` directly).
4. BankSpace and InvestorSpace `bind()` overrides call `super().bind(kernel)` and capture only their additional refs.
5. The three duplicated kernel-projection accessor methods have been removed from each subclass.
6. State CRUD, projections, and snapshot semantics remain in their respective concrete spaces.
7. Test count grows by exactly the number of new DomainSpace contract tests; all previously passing tests continue to pass without modification.
8. No call site is broken: no positional or keyword-arg callers needed to be rewritten.

---

## 31. Minimum Exchange / Market State (v0.11)

The v0.11 milestone adds `ExchangeSpace`, the fourth concrete domain space. It introduces the first **two-entity** internal state shape (markets and listings, not just one record type), and the first space whose primary kernel reference is `PriceBook` rather than `OwnershipBook` or `ContractBook`. v0.11 does not add trading or price formation behavior of any kind.

### 31.1 Two entity types, by design

Every previous domain space has held a single dataclass map: `firm_id -> FirmState`, `bank_id -> BankState`, `investor_id -> InvestorState`. ExchangeSpace breaks that pattern because the exchange's own structure has two entity types:

- **MarketState** — identity-level facts about a venue (which market, what type, which tier, what status).
- **ListingState** — the relationship between a market and an asset (whether asset X is listed on market Y, and with what status).

Listings are inherently relational. A single asset can be listed on multiple markets (cross-listed equity), and a single market lists many assets. Storing markets and listings as separate maps is the simplest representation that preserves both perspectives.

### 31.2 MarketState

`MarketState` is an immutable record. Its fields:

- `market_id` — WorldID of the market.
- `market_type` — domain-neutral string label (default `"unspecified"`). Examples: `"stock_exchange"`, `"bond_market"`, `"fx"`, `"real_estate_transaction"`. v0.11 enumerates none of these.
- `tier` — domain-neutral string label (default `"unspecified"`).
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

There is no `trading_hours`, `lot_size`, `tick_size`, `settlement_cycle`, `index_membership`, or `fee_schedule` field. These are the foundation of trading behavior, and v0.11 does not implement trading.

### 31.3 ListingState

`ListingState` is an immutable record keyed implicitly by `(market_id, asset_id)`. Its fields:

- `market_id` — the market on which the asset is listed.
- `asset_id` — the listed asset's WorldID.
- `listing_status` — free-form string. Common labels: `"listed"`, `"delisted"`, `"suspended"`, `"pre_listing"`. v0.11 enumerates none and applies no interpretive rules.
- `metadata` — bag for non-standard attributes.

There is intentionally no quote, last trade, halt window, lot conversion factor, or order-book reference. ListingState is the **fact of the relationship**, not the trading state.

### 31.4 ExchangeSpace API

ExchangeSpace inherits from `DomainSpace` (§30) and adds:

**Lifecycle:**

- `bind(kernel)` — extends `DomainSpace.bind()` to also capture `kernel.prices`. Other inherited refs (`balance_sheets`, `constraint_evaluator`, `signals`, `ledger`, `clock`, `registry`) are wired by the parent class even though Exchange typically reads only `prices` and `signals`.

**Market CRUD:**

- `add_market_state(market_state)` — register; rejects duplicate `market_id`; emits `market_state_added` to the ledger.
- `get_market_state(market_id)` — returns `MarketState` or `None`.
- `list_markets()` — tuple of all markets in **insertion order**.

**Listing CRUD:**

- `add_listing(listing)` — register; rejects duplicate `(market_id, asset_id)` pair; emits `listing_added` to the ledger.
- `get_listing(market_id, asset_id)` — returns `ListingState` or `None`.
- `list_listings()` — tuple of all listings in **insertion order**.
- `list_assets_on_market(market_id)` — tuple of `ListingState` records filtered to one market.

**Price-derived views:**

- `get_latest_price(asset_id)` — wraps `PriceBook.get_latest_price`; returns `None` when unbound or no price observed. Does not require the asset to be listed on any market.
- `get_price_history(asset_id)` — wraps `PriceBook.get_price_history`; returns `()` when unbound or no observations.

**Inherited from DomainSpace:**

- `get_balance_sheet_view(agent_id)`, `get_constraint_evaluations(agent_id)`, `get_visible_signals(observer_id)`.

**Snapshot:**

- `snapshot()` — returns `{"space_id", "market_count", "listing_count", "markets", "listings"}`. Markets sorted by `market_id`. Listings sorted by `(market_id, asset_id)`. The shape differs from previous spaces because it carries two entity types.

### 31.5 Prices and listings are independent

A deliberate v0.11 simplification: `get_latest_price(asset_id)` returns whatever the `PriceBook` knows, **regardless of whether the asset is listed anywhere**. Similarly, an asset can be listed without ever having been priced. Two reasons:

1. The `PriceBook` is the canonical source for prices (§9, §23.4). Gating `get_latest_price` on listing status would create a second source of truth and force callers to reason about which one is authoritative.
2. Real markets often have prices for unlisted assets (model marks, off-market trades, appraisals from data vendors), and v0.11 should not preclude that.

This is the same principle as v0.7's transport / visibility separation: ownership of a fact (the price) lives in one place; classification (the listing relationship) lives elsewhere. Joining them is the caller's choice.

### 31.6 What ExchangeSpace must not do

v0.11 explicitly forbids the following inside `ExchangeSpace`:

- mutating `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, or `SignalBook`
- mutating `CorporateSpace`, `BankSpace`, `InvestorSpace`, `RealEstateSpace`, or any other space's internal state
- implementing order matching, order books, or limit-order semantics
- implementing price formation, last-trade vs mid vs VWAP, quote logic, or auction dynamics
- implementing price impact or market impact estimation
- implementing trading sessions, opens, closes, halts, or auctions
- implementing circuit breakers, kill switches, or volatility brakes
- implementing index construction or rebalancing
- implementing trade reporting, fee computation, or settlement
- implementing scenario logic
- producing `WorldEvent`s that carry trading-decision payloads (transport-level events for testing remain fine)

The space classifies markets and listings. It surfaces prices and signals on request. It does not trade.

### 31.7 Ledger event types

- `market_state_added` — emitted by `ExchangeSpace.add_market_state` when a ledger is configured.
- `listing_added` — emitted by `ExchangeSpace.add_listing` when a ledger is configured. Records `object_id = asset_id` and `target = market_id`, so the relationship is fully reconstructable from the ledger entry alone.

Existing types continue to apply. `get_latest_price` and `get_price_history` are queries and produce no ledger record.

### 31.8 v0.11 success criteria

v0.11 is complete when **all** of the following hold:

1. `MarketState` exists with all required fields and is immutable.
2. `ListingState` exists with all required fields and is immutable.
3. `ExchangeSpace` inherits from `DomainSpace`.
4. `ExchangeSpace.bind` extends `DomainSpace.bind` to capture `prices`, following the four-property contract from §27.4.
5. `ExchangeSpace` exposes the market CRUD (`add_market_state` / `get_market_state` / `list_markets`), the listing CRUD (`add_listing` / `get_listing` / `list_listings` / `list_assets_on_market`), and the two price-derived views (`get_latest_price`, `get_price_history`).
6. Duplicate `market_id` is rejected; duplicate `(market_id, asset_id)` listing is rejected.
7. The same asset can be listed on multiple markets without conflict.
8. `market_state_added` and `listing_added` are recorded to the ledger when configured.
9. `ExchangeSpace` does not mutate any source book or any other space.
10. Price queries do not depend on listings; both work independently.
11. Missing-price queries return `None` / `()` and do not crash.
12. v0.2 scheduler integration still works: a populated `ExchangeSpace` runs for one year and is invoked at its declared frequency (DAILY × 365).
13. All previous milestones (v0 through v0.10.1) continue to pass.

---

## 32. Minimum Real Estate State (v0.12)

The v0.12 milestone adds `RealEstateSpace`, the fifth concrete domain space and the second to use a two-entity internal state shape. Like ExchangeSpace (§31), it captures `PriceBook` and exposes price-derived helpers — but it differs structurally in how property assets relate to property markets.

### 32.1 Foreign-key vs composite-key relations

ExchangeSpace and RealEstateSpace both hold two entity types: a market record and an asset-level record. The relationship between them is shaped differently in each:

| Aspect                    | ExchangeSpace (§31)                              | RealEstateSpace (v0.12)                           |
| ------------------------- | ------------------------------------------------ | ------------------------------------------------- |
| Asset → market cardinality | many-to-many (cross-listing allowed)             | one-to-one (a property is in exactly one market)  |
| Asset record key          | `(market_id, asset_id)` composite                | `asset_id` primary, `property_market_id` foreign  |
| Asset record name         | `ListingState`                                   | `PropertyAssetState`                              |
| Storage map               | `dict[tuple[str, str], ListingState]`            | `dict[str, PropertyAssetState]`                   |

This is not a stylistic preference — it reflects a real-world distinction. Equity instruments are routinely cross-listed across exchanges. A specific office building, by contrast, exists in one regional / typological property market at a time. Modeling that asymmetry in keys keeps the data shape honest.

### 32.2 PropertyMarketState

`PropertyMarketState` is an immutable record. Its fields:

- `property_market_id` — WorldID of the market segment.
- `region` — domain-neutral string label (default `"unspecified"`). Examples: `"tokyo_central"`, `"osaka_central"`, `"fukuoka"`.
- `property_type` — domain-neutral string label (default `"unspecified"`). Examples: `"office"`, `"residential"`, `"logistics"`, `"hotel"`, `"retail"`.
- `tier` — domain-neutral string label (default `"unspecified"`). Examples: `"prime"`, `"secondary"`.
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

There is no `cap_rate`, `vacancy_rate`, `rent_index`, `transaction_volume`, or `comparable_sales` field. These are the foundation of real-estate market behavior and v0.12 does not implement that behavior.

### 32.3 PropertyAssetState

`PropertyAssetState` is an immutable record. Its fields:

- `asset_id` — WorldID of the property (primary key).
- `property_market_id` — the market this property belongs to (foreign key).
- `asset_type` — domain-neutral string label (default `"unspecified"`). Examples: `"office_building"`, `"apartment_complex"`, `"warehouse"`, `"hotel"`, `"land_parcel"`.
- `status` — domain-neutral string label (default `"active"`). Examples: `"under_construction"`, `"under_renovation"`, `"demolished"`.
- `metadata` — bag for non-standard attributes.

There is no `noi`, `rent_roll`, `lease_schedule`, `valuation`, `cap_rate`, or `comparable_sales` field. These are valuation / income / underwriting concerns deferred to later milestones.

v0.12 deliberately does **not** validate that the referenced `property_market_id` is registered in the space. An asset may declare a market that has not been added (and may never be). This mirrors the v0.11 / v0.5 pattern: cross-references are recorded as data, not enforced as invariants. If callers care, they validate themselves.

### 32.4 RealEstateSpace API

RealEstateSpace inherits from `DomainSpace` (§30) and adds:

**Lifecycle:**

- `bind(kernel)` — extends `DomainSpace.bind()` to also capture `kernel.prices`. All four properties of the bind contract (§27.4) are preserved.

**Property market CRUD:**

- `add_property_market_state(market_state)` — register; rejects duplicates; emits `property_market_state_added` to the ledger.
- `get_property_market_state(property_market_id)` — returns `PropertyMarketState` or `None`.
- `list_property_markets()` — tuple of all markets in **insertion order**.

**Property asset CRUD:**

- `add_property_asset_state(asset_state)` — register; rejects duplicate `asset_id`; emits `property_asset_state_added` to the ledger with `target = property_market_id` so the relationship is reconstructable from the ledger entry.
- `get_property_asset_state(asset_id)` — returns `PropertyAssetState` or `None`.
- `list_property_assets()` — tuple of all property assets in **insertion order**.
- `list_assets_in_property_market(property_market_id)` — filter to one market.

**Price-derived views:**

- `get_latest_price(asset_id)` — wraps `PriceBook.get_latest_price`. Returns `None` when unbound or no price observed. Independent of whether the asset is registered in the space.
- `get_price_history(asset_id)` — wraps `PriceBook.get_price_history`. Returns `()` when unbound.

**Inherited from DomainSpace:**

- `get_balance_sheet_view(agent_id)`, `get_constraint_evaluations(agent_id)`, `get_visible_signals(observer_id)`.

**Snapshot:**

- `snapshot()` — returns `{"space_id", "property_market_count", "property_asset_count", "property_markets", "property_assets"}`. Markets sorted by `property_market_id`. Assets sorted by `asset_id`.

### 32.5 Frequencies

`RealEstateSpace` declares `(MONTHLY, QUARTERLY)` as its scheduler frequencies. Real-estate observation cadences are typically slower than equity exchange cadences (DAILY) — appraisals and market reports come monthly or quarterly, not daily. v0.12 does not implement any task body at these frequencies; the scheduler simply invokes the inherited no-op step. The frequencies are declared so that future milestones have a natural place to attach behavior.

### 32.6 What RealEstateSpace must not do

v0.12 explicitly forbids the following inside `RealEstateSpace`:

- mutating `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, or `SignalBook`
- mutating `CorporateSpace`, `BankSpace`, `InvestorSpace`, `ExchangeSpace`, or any other space's internal state
- implementing real-estate price formation, appraisal logic, or model marks
- implementing cap rate updates, rent updates, or vacancy dynamics
- implementing transaction matching, property auctions, or distressed sale dynamics
- implementing fire sale logic or forced liquidation
- implementing collateral haircut or LTV breach reactions
- implementing REIT NAV computation or fund-level valuation
- implementing scenario logic
- producing `WorldEvent`s that carry property-market-decision payloads (transport-level events for testing remain fine)

The space classifies property markets and property assets. It surfaces prices and signals on request. It does not value or transact.

### 32.7 Ledger event types

- `property_market_state_added` — emitted by `add_property_market_state` when a ledger is configured.
- `property_asset_state_added` — emitted by `add_property_asset_state`. Records `object_id = asset_id` and `target = property_market_id`, so the relationship is fully reconstructable from a single ledger entry.

`get_latest_price`, `get_price_history`, and other queries produce no ledger record.

### 32.8 v0.12 success criteria

v0.12 is complete when **all** of the following hold:

1. `PropertyMarketState` exists with all required fields and is immutable.
2. `PropertyAssetState` exists with all required fields and is immutable; `property_market_id` is required, but the referenced market is not validated for existence.
3. `RealEstateSpace` inherits from `DomainSpace`.
4. `RealEstateSpace.bind` extends `DomainSpace.bind` to capture `prices`, following the four-property contract from §27.4.
5. `RealEstateSpace` exposes the property-market CRUD, the property-asset CRUD, the per-market filter (`list_assets_in_property_market`), and the two price-derived views.
6. Duplicate `property_market_id` is rejected; duplicate `asset_id` is rejected.
7. A property asset may declare a `property_market_id` that has not been registered in the space.
8. `property_market_state_added` and `property_asset_state_added` are recorded to the ledger when configured.
9. `RealEstateSpace` does not mutate any source book or any other space.
10. Price queries do not depend on property-asset registration; both work independently.
11. Missing-price queries return `None` / `()` and do not crash.
12. v0.2 scheduler integration still works: a populated `RealEstateSpace` runs for one year and is invoked at its declared frequencies (MONTHLY × 12, QUARTERLY × 4).
13. All previous milestones (v0 through v0.11) continue to pass.

---

## 33. Minimum Information Space State (v0.13)

The v0.13 milestone adds `InformationSpace`, the sixth concrete domain space. Where prior milestones have classified the *who* (firms / banks / investors) and the *where* (exchanges / property markets), v0.13 classifies the **how** of information flow: which sources produce signals, and through which channels they are distributed.

`SignalBook` (§26) remains the canonical store of signals. InformationSpace classifies sources and channels but does not own, generate, or interpret signal content.

### 33.1 Why a separate space for sources and channels

Information has been a first-class concern since v0.7: `InformationSignal` records exist, are addressable, and can be referenced from `WorldEvent` payloads. But `SignalBook` is a flat store keyed by `signal_id`. It can answer "who is `source_id` pointing at?" via `list_by_source`, but it has no notion of *what kind of source* that is, or *what channels distribute its output*.

A rating agency, a wire service, a regulator, a leaker, and an automated data feed all show up in `SignalBook` as `source_id` strings. They are not all the same kind of thing, and future milestones will need to reason about that difference (credibility, distribution speed, audience). The InformationSpace state layer is where those classifications live.

The same logic applies to channels: a press release reaches everyone; an internal memo reaches a small allowlist; a leaked document might reach an unintended audience entirely. Channels are the medium of distribution, distinct from the source that authored the message. Both deserve identity-level records.

### 33.2 InformationSourceState

`InformationSourceState` is an immutable record. Its fields:

- `source_id` — WorldID of the source.
- `source_type` — domain-neutral string label (default `"unspecified"`). Examples: `"rating_agency"`, `"wire_service"`, `"analyst"`, `"regulator"`, `"internal_disclosure"`, `"automated_feed"`.
- `tier` — domain-neutral string label (default `"unspecified"`). Examples: `"tier_1"`, `"tier_2"`.
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

There is no `credibility_score`, `accuracy_history`, `bias_estimate`, or `topical_specialty` field. These would be the foundation of credibility / narrative behavior, and v0.13 does not implement that behavior.

### 33.3 InformationChannelState

`InformationChannelState` is an immutable record. Its fields:

- `channel_id` — WorldID of the channel.
- `channel_type` — domain-neutral string label (default `"unspecified"`). Examples: `"wire_service"`, `"press_release"`, `"social_media"`, `"internal_memo"`, `"regulatory_filing"`.
- `visibility` — free-form string label (default `"public"`). Captures the channel's inherent reach pattern.
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

`visibility` is intentionally **not** validated against `SignalBook`'s visibility enum. Channel reach and signal visibility are related but distinct concepts:

- `SignalBook.visibility` answers "who is *allowed* to observe this signal?".
- `InformationChannelState.visibility` answers "what kind of medium *is* this channel?".

A signal might be `restricted` even if it is published on a `public` channel (e.g., a regulatory filing on EDGAR is technically public but only allowed to be acted upon by registered users). v0.13 keeps the two labels independent so callers can reason about the propagation-vs-permission distinction without having to override one with the other.

There is no `audience_size`, `read_rate`, `decay`, or `noise_level` field. v0.13 does not implement narrative dynamics.

### 33.4 InformationSpace API

InformationSpace inherits from `DomainSpace` (§30). It needs no domain-specific kernel ref of its own — `signals` and `registry` from `DomainSpace` are sufficient. Therefore there is **no `bind()` override**. This is the second domain space (alongside CorporateSpace) that inherits `DomainSpace.bind` unchanged.

**Source CRUD:**

- `add_source_state(source_state)` — register; rejects duplicate `source_id`; emits `information_source_state_added` to the ledger.
- `get_source_state(source_id)` — returns `InformationSourceState` or `None`.
- `list_sources()` — tuple in **insertion order**.

**Channel CRUD:**

- `add_channel_state(channel_state)` — register; rejects duplicate `channel_id`; emits `information_channel_state_added` to the ledger.
- `get_channel_state(channel_id)` — returns `InformationChannelState` or `None`.
- `list_channels()` — tuple in **insertion order**.

**Signal-derived views:**

- `list_signals_by_source(source_id)` — wraps `SignalBook.list_by_source`. Returns `()` when unbound.
- `list_signals_by_type(signal_type)` — wraps `SignalBook.list_by_type`. Returns `()` when unbound.
- `list_visible_signals(observer_id, *, as_of_date=None)` — delegates to the inherited `get_visible_signals`. Both names are exposed; `list_visible_signals` is the InformationSpace-flavored name and `get_visible_signals` is the DomainSpace-pattern name. They are equivalent.

**Inherited from DomainSpace:**

- `get_balance_sheet_view`, `get_constraint_evaluations`, `get_visible_signals`. Information rarely needs the first two but inherits them for free.

**Snapshot:**

- `snapshot()` — returns `{"space_id", "source_count", "channel_count", "sources", "channels"}`. Sources sorted by `source_id`. Channels sorted by `channel_id`.

### 33.5 Source / channel registration is not gating

A signal in `SignalBook` may declare a `source_id` that has not been registered in `InformationSpace`. v0.13 deliberately does not require pre-registration:

- `signals.add_signal(...)` succeeds regardless of whether the source has been added.
- `info_space.list_signals_by_source("source:unregistered")` returns the matching signals and does not crash.
- `info_space.list_sources()` returns only the sources InformationSpace has been told about, even if `SignalBook` references others.

This is the same separation pattern used elsewhere: cross-references are recorded as data, not enforced as invariants. Signals are facts about what was published; source / channel registrations are classifications that the space chooses to maintain.

### 33.6 What InformationSpace must not do

v0.13 explicitly forbids the following inside `InformationSpace`:

- generating news, signals, or content of any kind
- writing analyst reports, summaries, or opinions
- interpreting signals (computing sentiment, polarity, importance, novelty)
- updating source credibility dynamically based on signal accuracy
- propagating rumors, modeling leak diffusion, or simulating word-of-mouth
- forming narratives or aggregating signals into themes
- triggering investor reactions, price movement, or credit decisions
- mutating `SignalBook`, `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, or any other source book
- mutating `CorporateSpace`, `BankSpace`, `InvestorSpace`, `ExchangeSpace`, `RealEstateSpace`, or any other space's internal state
- producing `WorldEvent`s that carry interpretive payloads (transport-level events for testing remain fine)

The space classifies sources and channels. It surfaces signals on request. It does not interpret, propagate, or generate.

### 33.7 Ledger event types

- `information_source_state_added` — emitted by `add_source_state` when a ledger is configured.
- `information_channel_state_added` — emitted by `add_channel_state` when a ledger is configured.

`list_signals_by_*` and `list_visible_signals` are queries and produce no ledger record.

### 33.8 v0.13 success criteria

v0.13 is complete when **all** of the following hold:

1. `InformationSourceState` exists with all required fields and is immutable.
2. `InformationChannelState` exists with all required fields and is immutable; `visibility` is a free-form string and is not validated against `SignalBook`'s visibility enum.
3. `InformationSpace` inherits from `DomainSpace` and requires no `bind()` override.
4. `InformationSpace` exposes the source CRUD, the channel CRUD, and three signal-derived views (`list_signals_by_source`, `list_signals_by_type`, `list_visible_signals`).
5. Duplicate `source_id` is rejected; duplicate `channel_id` is rejected.
6. Signals may reference unregistered sources; signal queries do not require source or channel registration.
7. `information_source_state_added` and `information_channel_state_added` are recorded to the ledger when configured.
8. `InformationSpace` does not mutate `SignalBook` or any other source book or any other space.
9. Missing-data queries return `None` / `()` and do not crash.
10. v0.2 scheduler integration still works: a populated `InformationSpace` runs for one year and is invoked at its declared frequency (DAILY × 365).
11. All previous milestones (v0 through v0.12) continue to pass.

---

## 34. Minimum Policy / External Space State (v0.14)

The v0.14 milestone adds the final two domain spaces — `PolicySpace` and `ExternalSpace` — completing the eight spaces enumerated in §2: Corporate, Investors, Banking, Exchange, Real Estate, Information, Policy, External.

Both are pure classification layers. `PolicySpace` records who has policy-making authority and what instruments they could in principle use; `ExternalSpace` records what exogenous factors the world tracks and where data feeds in from. Neither implements any decision, reaction, shock, or stochastic process.

### 34.1 Why a single milestone for two spaces

Combining Policy and External into one milestone is a deliberate choice. Both are minimal classification layers with no domain-specific kernel ref of their own (they need only `signals` and `registry` from `DomainSpace`), no `bind()` override, and no novel structural element beyond what v0.11–§32 already established. The shared characteristic is that **v0.14 deliberately defines what these spaces will not do** — central bank reaction functions and exogenous shock generation are exactly the kinds of behaviors that future v1 reference behavior will introduce, and v0.14 has to keep its hands off them.

After v0.14, every space from §2 has a state file, a space file, integration tests, and a documented contract. The world kernel is structurally complete; what remains is content (specific firms, specific banks, specific signals, scenarios) and behavior (reactions, decisions, dynamics).

### 34.2 PolicySpace

#### 34.2.1 PolicyAuthorityState

`PolicyAuthorityState` is an immutable record. Its fields:

- `authority_id` — WorldID of the authority.
- `authority_type` — domain-neutral string label (default `"unspecified"`). Examples: `"central_bank"`, `"financial_regulator"`, `"securities_commission"`, `"finance_ministry"`, `"deposit_insurance"`.
- `tier` — domain-neutral string label (default `"unspecified"`). Examples: `"national"`, `"regional"`, `"supra-national"`.
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

There is no `mandate`, `independence_index`, `voting_members`, `target_rate`, or `reaction_function` field. v0.14 does not implement policy behavior.

#### 34.2.2 PolicyInstrumentState

`PolicyInstrumentState` is an immutable record. Its fields:

- `instrument_id` — primary key.
- `authority_id` — foreign key to a PolicyAuthorityState. **Not validated** for existence in the space (same rule as v0.12 PropertyAssetState).
- `instrument_type` — domain-neutral string label (default `"unspecified"`). Examples: `"policy_rate"`, `"reserve_requirement"`, `"open_market_operation"`, `"capital_ratio"`, `"deposit_insurance_ceiling"`.
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

There is no `current_rate`, `target_level`, `transmission_lag`, or `effectiveness_estimate` field. v0.14 does not implement policy mechanics.

#### 34.2.3 PolicySpace API

PolicySpace inherits from `DomainSpace` (§30) and **needs no `bind()` override** (third such case, joining CorporateSpace and InformationSpace). The inherited `signals` and `registry` are sufficient.

- Authority CRUD: `add_authority_state` / `get_authority_state` / `list_authorities`.
- Instrument CRUD: `add_instrument_state` / `get_instrument_state` / `list_instruments`.
- Filter helper: `list_instruments_by_authority(authority_id)`.
- `snapshot()` returns `{"space_id", "authority_count", "instrument_count", "authorities", "instruments"}`. Both lists deterministically sorted.
- Inherits `get_visible_signals` and the other DomainSpace accessors.
- Frequencies: `(MONTHLY,)` matching realistic policy review cadence.

#### 34.2.4 What PolicySpace must not do

- set, change, or guide policy rates
- implement reaction functions (Taylor / Brainard / inflation-targeting)
- conduct liquidity operations or balance-sheet expansion / contraction
- change regulatory rules (capital ratios, leverage caps)
- mutate `ConstraintBook` (the ConstraintBook is owned by the kernel; future milestones may have spaces propose constraints, but v0.14 does not)
- mutate any other source book or any other space
- implement scenario logic

### 34.3 ExternalSpace

#### 34.3.1 ExternalFactorState

`ExternalFactorState` is an immutable record. Its fields:

- `factor_id` — WorldID of the factor.
- `factor_type` — domain-neutral string label (default `"unspecified"`). Examples: `"fx_rate"`, `"commodity_price"`, `"foreign_macro"`, `"sovereign_yield"`, `"demographic"`, `"weather"`.
- `unit` — free-form string label (default `"unspecified"`). Examples: `"USD/JPY"`, `"USD/barrel"`, `"%"`, `"index_points"`, `"persons"`.
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

There is no `current_value`, `last_observed`, `volatility`, `shock_model`, or `regime` field. v0.14 does not implement stochastic processes or shock generation.

The `unit` field is captured at the classification layer because future milestones will need to interpret factor values dimensionally (a USD/JPY rate of 150 means something different from a CPI percentage of 150). v0.14 does not enforce any unit grammar — it is a free-form label like every other classifier.

#### 34.3.2 ExternalSourceState

`ExternalSourceState` is an immutable record. Its fields:

- `source_id` — WorldID of the data source.
- `source_type` — domain-neutral string label (default `"unspecified"`). Examples: `"international_organization"`, `"foreign_central_bank"`, `"foreign_statistical_agency"`, `"data_vendor"`.
- `status` — domain-neutral string label (default `"active"`).
- `metadata` — bag for non-standard attributes.

Note that `ExternalSourceState` deliberately does **not** carry a `tier` field, in contrast to `InformationSourceState` (§33.2). The reason: external data sources are typically classified by *kind* (vendor, agency, organization) rather than by tier, and adding a vestigial tier field would invite incorrect taxonomies. If future milestones need a tier-like distinction, they can use `metadata`.

#### 34.3.3 InformationSourceState vs ExternalSourceState

Two spaces have a `source` concept and an `add_source_state` method:

| Concept                | InformationSourceState (§33)                             | ExternalSourceState (§34.3.2)                               |
| ---------------------- | -------------------------------------------------------- | ----------------------------------------------------------- |
| What it classifies     | Signal-producing entities about the *domestic* world     | Where *exogenous* data feeds in from                        |
| Typical examples       | rating agency, wire service, regulator, internal desk    | IMF, World Bank, foreign CB, foreign stat agency, vendor    |
| Has `tier`?            | yes                                                      | no                                                          |
| Owns                   | InformationSpace                                         | ExternalSpace                                               |

The two often overlap in practice (e.g., a wire service can be both a signal source and an external data feed) but the classification axes are different. Each space keeps its own view; v0.14 does not merge them.

#### 34.3.4 ExternalSpace API

ExternalSpace inherits from `DomainSpace` and **needs no `bind()` override** (fourth such case).

- Factor CRUD: `add_factor_state` / `get_factor_state` / `list_factors`.
- Source CRUD: `add_source_state` / `get_source_state` / `list_sources`.
- `snapshot()` returns `{"space_id", "factor_count", "source_count", "factors", "sources"}`. Both lists deterministically sorted.
- Inherits `get_visible_signals` and the other DomainSpace accessors.
- Frequencies: `(DAILY,)` matching typical external observation cadence.

Factors and sources are independent maps in v0.14 — there is no factor → source relation or source → factor relation. Real-world relationships are many-to-many and v0.14 does not pick a representation. Future milestones may introduce a relation map if cross-references become load-bearing.

#### 34.3.5 What ExternalSpace must not do

- generate shocks of any kind (oil, FX, war, natural disaster, pandemic, regime change)
- implement random walks, AR/ARMA processes, or any stochastic process
- implement regime switching, regime detection, or regime classification
- replay historical data (e.g., back-running 1990s asset bubble values)
- update factor values or maintain factor time series
- propagate shock impact to prices, ownership, contracts, or any other book
- mutate any other source book or any other space
- implement scenario logic

### 34.4 Ledger event types

- `policy_authority_state_added`
- `policy_instrument_state_added` (records `target = authority_id` for relationship reconstruction)
- `external_factor_state_added`
- `external_source_state_added`

Queries produce no ledger record.

### 34.5 v0.14 success criteria

v0.14 is complete when **all** of the following hold:

**PolicySpace:**

1. `PolicyAuthorityState` exists with all required fields and is immutable.
2. `PolicyInstrumentState` exists with all required fields and is immutable; `authority_id` is required and unvalidated for existence.
3. `PolicySpace` inherits from `DomainSpace` and requires no `bind()` override.
4. `PolicySpace` exposes authority CRUD, instrument CRUD, and `list_instruments_by_authority`.
5. Duplicate `authority_id` is rejected; duplicate `instrument_id` is rejected.
6. `policy_authority_state_added` and `policy_instrument_state_added` are recorded to the ledger when configured.
7. PolicySpace does not mutate `ConstraintBook` or any other source book or any other space.
8. v0.2 scheduler integration still works (MONTHLY × 12).

**ExternalSpace:**

9. `ExternalFactorState` exists with all required fields and is immutable.
10. `ExternalSourceState` exists with all required fields and is immutable.
11. `ExternalSpace` inherits from `DomainSpace` and requires no `bind()` override.
12. `ExternalSpace` exposes factor CRUD and source CRUD.
13. Duplicate `factor_id` is rejected; duplicate `source_id` is rejected.
14. `external_factor_state_added` and `external_source_state_added` are recorded to the ledger when configured.
15. ExternalSpace does not mutate any source book or any other space.
16. v0.2 scheduler integration still works (DAILY × 365).

**Shared:**

17. Missing-data queries return `None` / `()` and do not crash.
18. All previous milestones (v0 through v0.13) continue to pass.

### 34.6 World kernel structural completeness

After v0.14, all eight spaces enumerated in §2 (Corporate, Investors, Banking, Exchange, Real Estate, Information, Policy, External) have:

- a state dataclass file (or two, for two-entity spaces)
- a space implementation file inheriting from `DomainSpace`
- integration with the kernel via `register_space` and `bind()`
- ledger event types for state-addition records
- unit and integration tests
- a documented contract in `world_model.md`

The world kernel as a constitutional structure is now complete. Subsequent milestones build on it in distinct layers:

- **v1.xx** adds *jurisdiction-neutral reference behavior* — central bank reaction functions, investor strategies, market clearing, valuation, intraday phases — on top of this kernel.
- **v2.xx** adds *Japan public calibration* on top of v1, using public data sources.
- **v3.xx** adds *Japan proprietary / commercial calibration* on top of v2, using paid or expert-knowledge data.

v0 itself stays jurisdiction-neutral and behavior-free.

---

## 35. Cross-Space Integration Verification (v0.15)

The v0.15 milestone is a single integration test file — `tests/test_world_kernel_full_structure.py` — that exercises the entire eight-space world together. It writes no new production code; everything it verifies has already been implemented across §22–§34. The point of v0.15 is to confirm that those layers compose into one coherent system without behavior, scenarios, or domain logic, and to draw a line under v0 with a passing reference test.

### 35.1 What the integration test covers

The file builds one populated `WorldKernel` via a `_build_full_world()` helper, and asserts the following properties as separate test functions:

1. **Coexistence.** All eight spaces register with the same kernel and run for one calendar year (365 ticks) without raising. The clock advances to `2027-01-01`.
2. **Frequency correctness.** Each space's scheduled tasks fire the expected number of times across 365 days. For example, `banking_daily` fires 365 times, `corporate_quarterly` fires 4 times, `corporate_yearly` fires 1 time. This catches any regression in how `DomainSpace` interacts with `Scheduler`.
3. **Snapshot creation.** The kernel emits 12 `state_snapshot_created` records over the year, one per month-end.
4. **Per-space read access.** Each space can query its relevant projections through the inherited or domain-specific accessors:
   - CorporateSpace reads balance sheet, constraint evaluations, and visible signals.
   - BankSpace reads contracts, lending exposures, balance sheet, constraints, signals.
   - InvestorSpace reads portfolio positions, exposures, balance sheet, constraints, signals.
   - ExchangeSpace reads listings, latest price, price history, signals.
   - RealEstateSpace reads property assets, prices, signals.
   - InformationSpace reads signals by source / type / visibility.
   - PolicySpace and ExternalSpace each read visible signals.
5. **EventBus delivery semantics (§22 / §26).** A `WorldEvent` referencing a `signal_id` and addressed to two daily-firing target spaces is delivered exactly once to each target, on day 2 (the v0.3 next-tick rule). The test runs day 1 first, asserts zero deliveries, then runs day 2 and asserts two `event_delivered` ledger records.
6. **Transport / visibility independence (§26.5).** A WorldEvent referencing a `restricted` signal is delivered through the bus regardless of the signal's visibility. The visibility filter applies only when the receiver queries `SignalBook.list_visible_to` directly.
7. **No cross-space mutation.** The test takes a snapshot of every kernel-level book (ownership, contracts, prices, constraints, signals), exercises every read accessor across every space, and confirms that all five book snapshots are byte-identical to the pre-read state. The ledger accumulates entries (notably `constraint_evaluated` records produced by the evaluator), but no source-of-truth book is mutated by reading.
8. **Complete ledger audit trail.** After setup and a one-year run, the ledger contains every expected event type: `object_registered`, `task_scheduled`, the 12 state-addition record types (`firm_state_added`, `bank_state_added`, etc.), the network-book mutation types (`ownership_position_added`, `contract_created`, `price_updated`, `constraint_added`, `signal_added`), the runtime types (`task_executed`, `state_snapshot_created`).

### 35.2 What the integration test deliberately does not check

v0.15 does not exercise behavior that v0 does not implement. The test does not assert anything about:

- price formation or model marks
- order flow or trade execution
- credit decisions, default outcomes, covenant trips
- investor allocation or rebalancing
- policy rate changes or reaction-function output
- external shock generation or factor value updates
- narrative / rumor / credibility dynamics
- cap rate or rent updates

If any of those become non-zero in a future milestone's run, that milestone's own tests will assert them. v0.15 stays inside the empty-but-structured world.

### 35.3 v0.15 success criteria

v0.15 is complete when **all** of the following hold:

1. The new test file exists at `tests/test_world_kernel_full_structure.py` and passes under `pytest -q`.
2. All eight spaces are instantiated and registered against one `WorldKernel`.
3. Minimal coherent state is populated in every space and across every kernel-level book.
4. A 365-day run completes without exceptions, and per-frequency task counts match the declared frequencies of each space.
5. Every space's read-only accessors return the expected shapes and values for the populated data.
6. EventBus integration is verified end-to-end: next-tick delivery, two-target delivery, and transport independence from signal visibility.
7. No source-of-truth book is mutated by read operations.
8. The ledger carries every expected event type after setup and run.
9. All previous milestones (v0 through v0.14) continue to pass.

### 35.4 v0 closure

v0.15 is the final milestone in the v0 line. After it passes, the project's invariants are:

- the world kernel is a jurisdiction-neutral constitutional structure
- all eight spaces classify but do not act
- all reads are non-mutating; all writes are explicit and ledger-recorded
- inter-space communication is mediated by EventBus, with same-tick delivery forbidden
- signal content lives in `SignalBook`; classifications live in their respective spaces
- no decision, valuation, scenario, or stochastic process is implemented anywhere

Subsequent versions will build on this foundation:

- **v1.xx** adds jurisdiction-neutral reference behavior (decisions, valuation, market clearing, intraday phases, scenarios).
- **v2.xx** adds Japan public calibration on top of v1.
- **v3.xx** adds Japan proprietary / commercial calibration on top of v2.

None of those layers may weaken the v0 invariants above without an explicit, documented decision.

---

## 36. Valuation Layer (v1.1)

The v1.1 milestone is the first implementation step in the v1 line. It adds **valuation as a first-class world object** without introducing fundamentals or any decision-making behavior. v1.1 sits inside the non-behavioral carve-out described in [`v1_behavior_boundary.md`](v1_behavior_boundary.md): it stores claims and compares them against observed prices, but it never acts on a comparison.

For the full design rationale — three-way distinction between price / valuation / fundamental, four worked use cases, the currency-vs-numeraire split, and the explanation of why fundamentals are deferred — see [`v1_valuation_fundamentals_design.md`](v1_valuation_fundamentals_design.md).

### 36.1 Why valuation is not price

`PriceBook` (§9, §23.4) records what was observed: transaction prices, quotes, marks. v1.1 introduces `ValuationBook` for what was *opined*: a valuer's estimate of what something is worth, for a specific purpose, by a specific method, with stated assumptions and a stated confidence. Two valuers can produce different numbers for the same subject on the same day, and v1.1 stores both. There is no "the valuation" of any subject — only valuations.

Conflating the two would weaken v0 invariant 4 (prices are observed, not modeled) and v1 invariant 5 (valuation is not price or truth). v1.1 enforces the separation by giving valuations their own store, their own record type in the ledger, and their own comparator that produces a `ValuationGap` rather than appending into `PriceBook`.

### 36.2 ValuationRecord

`ValuationRecord` is an immutable dataclass with 15 fields:

- `valuation_id` — stable unique identifier.
- `subject_id` — what is being valued. Free-form WorldID. May refer to firms, assets, contracts, properties, FX pairs, portfolios, markets, or any other world object. v1.1 does not validate that the referenced subject is registered.
- `valuer_id` — who produced the valuation. Any agent, model, appraiser, or synthetic source.
- `valuation_type` — domain-neutral string label (`"equity"`, `"debt"`, `"real_estate"`, `"fx_view"`, `"fund_nav"`, …).
- `purpose` — domain-neutral string label (`"investment_research"`, `"underwriting"`, `"financial_reporting"`, `"covenant_test"`, …).
- `method` — domain-neutral string label (`"dcf"`, `"comparables"`, `"book_value"`, `"cap_rate"`, `"comparable_sales"`, …).
- `as_of_date` — ISO date of the valuation.
- `estimated_value` — float, or `None` if the valuation is qualitative or failed.
- `currency` — display currency of `estimated_value`.
- `numeraire` — perspective currency or value basis the valuer reasoned in. Distinct from `currency`; see §36.5.
- `confidence` — float in `[0, 1]`.
- `assumptions` — dict of method assumptions (e.g., discount rate, cap rate, terminal growth).
- `inputs` — dict of model inputs (e.g., free cash flow series, NOI, comparable sales).
- `related_ids` — tuple of related WorldIDs.
- `metadata` — bag for non-standard attributes.

v1.1 enumerates none of the type / purpose / method strings. They are free-form so any plausible professional vocabulary fits without schema changes.

### 36.3 ValuationGap

`ValuationGap` is the output of comparing one valuation to the latest observed price. Its fields:

- `subject_id`, `valuation_id`, `as_of_date`, `currency` — copied from the valuation.
- `estimated_value` — copied from the valuation.
- `observed_price` — the latest `PriceRecord.price` for the subject, or `None` if no price exists.
- `absolute_gap` — `estimated_value - observed_price` when both exist.
- `relative_gap` — `absolute_gap / observed_price` when `observed_price` is non-zero.
- `metadata["reason"]` — populated when a numeric gap cannot be computed: `"missing_price"`, `"estimated_value_unavailable"`, `"currency_mismatch"`, or `"observed_price_zero"`.

A `ValuationGap` is informational. It records the difference; it does not act on it.

### 36.4 ValuationBook and ValuationComparator

`ValuationBook` API:

- `add_valuation(record)` — store; rejects duplicate `valuation_id`; emits `valuation_added` to the ledger.
- `get_valuation(valuation_id)` — raises `UnknownValuationError` for unknown ids.
- `list_by_subject` / `list_by_valuer` / `list_by_type` / `list_by_purpose` / `list_by_method` — five indexed read paths.
- `get_latest_by_subject(subject_id)` — picks the highest `as_of_date` among the subject's valuations (ISO date strings compare lexicographically; ties break to the most recently added record).
- `snapshot()` — sorted, JSON-friendly view.

`ValuationComparator` API:

- `compare_to_latest_price(valuation_id)` — produce a `ValuationGap` against the subject's latest price.
- `compare_subject_latest(subject_id)` — find the latest valuation for the subject and compare.

The comparator records `valuation_compared` to the ledger when a ledger is configured, with `parent_record_ids` referencing the originating `valuation_added` record so the ledger forms a causal chain.

### 36.5 currency vs numeraire

`currency` is the display currency of `estimated_value` — the unit of the number. `numeraire` is the perspective the valuer reasoned in. For purely domestic valuations the two are identical. They differ in cross-border contexts: a USD-perspective fund valuing a JPY-denominated equity sets `currency="JPY"`, `numeraire="USD"`.

v1.1 does **not** implement FX conversion. The comparator detects a currency mismatch by inspecting `metadata["currency"]` on the latest priced observation and refuses to convert; instead, it produces a `ValuationGap` with `metadata["reason"] = "currency_mismatch"`. The choice of FX rate, source, and timestamp is itself a calibration decision and belongs to a later milestone.

### 36.6 Ledger event types

- `valuation_added` — emitted by `ValuationBook.add_valuation` when a ledger is configured. Records `object_id = valuation_id`, `target = subject_id`, `agent_id = valuer_id`.
- `valuation_compared` — emitted by `ValuationComparator` for every comparison. `correlation_id = valuation_id`. `parent_record_ids` links back to the originating `valuation_added` record so an audit can reconstruct the comparison's origin.

### 36.7 Kernel wiring

`WorldKernel` exposes:

- `kernel.valuations: ValuationBook`
- `kernel.valuation_comparator: ValuationComparator`

Both are constructed in `__post_init__` with the kernel's `clock`, `ledger`, and `prices` references. Existing v0 behavior is unchanged: every previous test continues to pass.

### 36.8 What v1.1 does not do

v1.1 explicitly does **not**:

- introduce a typed `FundamentalsBook` or `FundamentalView` — deferred.
- implement any specific valuation engine (DCF, comparables, cap-rate, etc.). v1.1 stores opinions, it does not produce them.
- implement FX conversion in the comparator.
- consume valuations to drive any decision. A v1.3 bank that wants to underwrite against an `underwriting`-purpose valuation reads it directly; the valuation layer never pushes.
- compute "consensus" or "fair value" by aggregating multiple valuations.
- mutate `PriceBook`, `OwnershipBook`, `ContractBook`, `ConstraintBook`, or `SignalBook`.
- introduce Japan-specific anything.

### 36.9 v1.1 success criteria

v1.1 is complete when **all** of the following hold:

1. `ValuationRecord` exists with all 15 documented fields and is immutable.
2. `ValuationGap` exists with all 9 documented fields and is immutable.
3. `ValuationBook` supports `add_valuation`, `get_valuation`, the five `list_by_*` helpers, `get_latest_by_subject`, and `snapshot`.
4. `ValuationComparator` supports `compare_to_latest_price` and `compare_subject_latest`.
5. The four documented failure paths (`missing_price`, `estimated_value_unavailable`, `currency_mismatch`, `observed_price_zero`) all produce a non-crashing `ValuationGap` with the corresponding `metadata["reason"]`.
6. `subject_id` accepts non-firm WorldIDs (FX pairs, portfolios, properties, contracts, markets) without validation.
7. Multiple conflicting valuations for the same subject coexist; the book picks no winner.
8. `valuation_added` and `valuation_compared` are recorded to the ledger; comparison records carry `parent_record_ids` linking to the originating `valuation_added` record.
9. v1.1 mutates none of `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, or `SignalBook`.
10. The kernel exposes `kernel.valuations` and `kernel.valuation_comparator` with default wiring.
11. All previous milestones (v0 through v0.16) continue to pass.

---

## 37. Intraday Phase Scheduler (v1.2)

The v1.2 milestone gives the world a way to express *order within a day*. v0's smallest time unit was one calendar day; v1.2 splits that day into a sequence of named phases (overnight → pre_open → opening_auction → continuous_session → closing_auction → post_close). v1.2 ships **scheduling infrastructure only** — no auction matching, no order book, no halt logic, no country-specific exchange hours.

For the full design rationale, examples of future use, and the carve-out from v1's behavior contract, see [`v1_intraday_phase_design.md`](v1_intraday_phase_design.md).

### 37.1 Why phases exist now

v0's tasks fired once per day in a deterministic but phase-blind order. That was correct for v0 because no v0 task acted, so intraday ordering was inert. v1's introduction of behavior changes that. Earnings released after the close should be visible at the next open, not at the same instant. A reference market clearing in v1.3 cannot meaningfully run at the same instant as the investor intent it consumes.

v1.2 adds the slot mechanism. v1.3 will fill the slots with reference behavior; v1.2 only declares them.

### 37.2 Phase definitions

`world/phases.py` defines two types:

- `IntradayPhaseSpec` — immutable record with `phase_id`, `order`, `label`, `metadata`. The `phase_id` is a free-form string; when the phase participates in scheduler dispatch it must match a value of the `Phase` enum.
- `PhaseSequence` — an ordered tuple of `IntradayPhaseSpec` with helpers `default_phases`, `list_phases`, `get_phase`, `next_phase`, `is_first_phase`, `is_last_phase`, and `to_dict`.

The default sequence is the six-phase day documented above. Custom sequences are allowed for tests and future jurisdiction-specific calendars; v1.2 ships only the default.

### 37.3 Scheduler extension

The existing `Phase` enum gains six new values (`OVERNIGHT`, `PRE_OPEN`, `OPENING_AUCTION`, `CONTINUOUS_SESSION`, `CLOSING_AUCTION`, `POST_CLOSE`) alongside the v0 `MAIN`. The `_sorted_tasks` helper updates its `phase_rank` table to rank `MAIN` first (preserving v0 ordering tests) followed by the six intraday phases in their canonical order.

`Scheduler.due_tasks(clock)` continues to return all due tasks regardless of declared phase when no `phase` filter is given. With a `phase` filter it returns only tasks declared at that phase. v0 callers that pass no filter see no behavior change.

### 37.4 Kernel methods

Three new methods on `WorldKernel`, all optional and additive:

- `iter_intraday_phases(sequence=None)` — generator yielding `(IntradayPhaseSpec, due_tasks)` pairs for the current clock date. Tasks declared with `Phase.MAIN` are intentionally excluded.
- `run_day_with_phases(sequence=None)` — runs one calendar day phase-by-phase, executes phase-matching due tasks, emits a month-end snapshot when applicable, and advances the clock by one day. The clock and snapshot semantics mirror `tick()`.
- `run_with_phases(days, sequence=None)` — runs `days` consecutive days through `run_day_with_phases`.

The v0 `tick()` and `run()` methods are unchanged. v0 spaces — all of which use `Phase.MAIN` — continue to be invoked exactly as before.

### 37.5 Ledger event types

v1.2 reuses the existing `task_executed` ledger record type. When a task fires through `run_day_with_phases`, the payload gains a `phase` key recording which phase it ran in. No new record types are introduced for intraday dispatch (per the user's preference for "reuse if cleaner").

### 37.6 Backward compatibility

The v0 path (`tick` / `run`) is unchanged in behavior:

- All due tasks fire on every tick regardless of declared phase.
- v0 tests pass without modification (444 v0 + 34 v1.1 + 33 v1.2 + 6 v1.2.1 = 517 / 517 passing).
- Tasks declared with `Phase.MAIN` continue to be the default and fire under both paths (`tick` includes them; `run_day_with_phases` excludes them — see §37.7).

The v1.2 path (`run_day_with_phases` / `run_with_phases`) is opt-in. Mixing the two paths on the same calendar day would advance the clock twice; the documented rule is "use one or the other per day".

**The rule is enforced (v1.2.1).** See §37.10.

### 37.7 Why MAIN is excluded from phase dispatch

`run_day_with_phases` does not fire `Phase.MAIN` tasks. The reasoning:

1. v0 tasks were written with no phase semantics. Forcing them into one of the six intraday phases would tie v0 spaces' dispatch order to a v1 convention.
2. Callers that want a task to fire phase-blind should keep using `Phase.MAIN` plus `tick()`. Callers that want phase-aware dispatch declare a specific intraday phase explicitly.

The two buckets are kept separate by design. v1.3 will introduce phase-aware tasks in the eight v0 spaces alongside their existing `MAIN` tasks; both buckets coexist.

### 37.8 What v1.2 does not do

- No order matching, order books, or limit-order semantics.
- No auction pricing or reference clearing mechanism.
- No price impact, halts, or circuit breakers.
- No country-specific exchange hours, session calendars, or holiday logic.
- No phase-specific behavior in any v0 space.
- No cross-day phases or sub-second / wall-clock-aware phases.
- No mutation of any source-of-truth book.
- No Japan-specific anything.

### 37.9 v1.2 success criteria

v1.2 is complete when **all** of the following hold:

1. `IntradayPhaseSpec` and `PhaseSequence` exist as documented.
2. The default sequence is exactly: `overnight`, `pre_open`, `opening_auction`, `continuous_session`, `closing_auction`, `post_close`.
3. The `Phase` enum carries the six intraday values plus `MAIN`.
4. `_sorted_tasks` ranks all phases consistently; existing v0 sorting tests pass without modification.
5. `WorldKernel` exposes `iter_intraday_phases`, `run_day_with_phases`, and `run_with_phases`, all opt-in.
6. `run_day_with_phases` advances the clock once per day and emits a month-end snapshot when applicable.
7. Phase-aware daily / monthly / quarterly tasks fire the correct number of times at their declared phase.
8. Multiple tasks at the same phase execute in the deterministic order produced by `_sorted_tasks` (phase rank → frequency → order → space → name).
9. No source-of-truth book is mutated by the phase dispatcher.
10. v0 `tick` / `run` behavior is unchanged; v0 tests pass without modification.
11. All previous milestones (v0 through v1.1) continue to pass.

### 37.10 Run-mode guard (v1.2.1)

§37.6 documents that the v0 path (`tick` / `run`) and the v1.2 path (`run_day_with_phases` / `run_with_phases`) must not be mixed on the same simulation date. v1.2.1 promotes that rule from advisory to **enforced**.

The kernel keeps a private `_run_modes` map (`simulation_date → mode`) populated in `__post_init__`. Every entry into `tick()` calls `_enter_run_mode("date_tick")` before doing any work; every entry into `run_day_with_phases()` calls `_enter_run_mode("intraday_phase")`. The helper:

- Looks up the mode previously recorded for `clock.current_date`.
- If a mode exists and differs from the requested mode, raises `RuntimeError` with a message naming the date and both modes.
- Otherwise records the requested mode for `clock.current_date`.

Repeated calls in the *same* mode at the same date are idempotent — the guard rejects only mode mixing, not mode reentry. The map keys on `simulation_date`, so the guard resets naturally as soon as the clock advances to a new date.

The guard does not fire in ordinary sequential use because both paths advance the clock at the end of their work. It only fires when a caller manually rewinds the clock and tries to revisit a date in the other mode. The hardening tests
[`test_tick_then_run_day_with_phases_on_same_date_raises`](../tests/test_phase_scheduler.py)
and
[`test_run_day_with_phases_then_tick_on_same_date_raises`](../tests/test_phase_scheduler.py)
construct exactly that scenario by assigning a past value to `clock.current_date`.

The v1.2.1 success condition is:

12. The two execution paths remain backward-compatible but cannot be silently mixed on the same simulation date. Mixing raises `RuntimeError` with a message that names both modes and the date, and the guard resets naturally when the clock moves to the next date.

---

## 38. Institutional Decomposition and Action Contract (v1.3)

The v1.3 milestone adds **institutions, mandates, instrument profiles, and recorded institutional actions** as kernel-level objects, plus the **4-property action contract** that every future v1 behavior module must follow when it produces an action record. v1.3 introduces the *recording schema* for institutional behavior — but explicitly not the behavior itself.

For the full design rationale (institutions vs PolicySpace, why behavior is deferred, why Japan-specific institutions belong to v2/v3, examples of future use), see [`v1_institutional_decomposition_design.md`](v1_institutional_decomposition_design.md).

### 38.1 Why a kernel-level institution layer

PolicySpace (§34.2) classifies which policy authorities and which instruments exist as *domain-space facts*. v1.3's `InstitutionBook` operates one layer up: it represents institutions as **kernel-level actors with mandates and a recorded action history**, not as classifications living inside one space. The two layers coexist; v1.3 does not replace PolicySpace.

The institution layer is needed because action recording must be reusable across spaces. A reference policy reaction in PolicySpace, a reference supervisory review in a regulator (which has no v0 space yet), a reference exchange announcement in ExchangeSpace — all want to record actions with the same shape: explicit inputs, explicit outputs, ledger trail, no cross-space mutation. Promoting the recording schema to a kernel-level book lets a single contract serve all of them.

### 38.2 The four record types

v1.3 ships four immutable dataclasses in `world/institutions.py`:

- **`InstitutionProfile`** — `institution_id`, `institution_type`, `jurisdiction_label`, `mandate_summary`, `authority_scope`, `status`, `metadata`. The `jurisdiction_label` is a free-form string; v1.3 does not validate it. Tests verify the field accepts any label, including the empty string, so v1 stays jurisdiction-neutral and v2 can populate real labels later.
- **`MandateRecord`** — `mandate_id`, `institution_id`, `mandate_type`, `description`, `priority`, `status`, `metadata`. An institution may carry multiple mandates that interact (price stability, financial stability, etc.); each is its own record.
- **`PolicyInstrumentProfile`** — `instrument_id`, `institution_id`, `instrument_type`, `target_domain`, `status`, `metadata`. Distinct from v0.14's `PolicyInstrumentState`, which is a domain-space classification; the two layers can coexist on the same instrument id.
- **`InstitutionalActionRecord`** — `action_id`, `institution_id`, `action_type`, `as_of_date`, optional `phase_id`, `input_refs`, `output_refs`, `target_ids`, `instrument_ids`, `payload`, `parent_record_ids`, `metadata`.

All four are frozen dataclasses with `to_dict()` for serialization. Validation rejects empty required fields.

### 38.3 InstitutionBook API

- Institution profiles: `add_institution_profile`, `get_institution_profile`, `list_by_type`, `all_institutions`.
- Mandates: `add_mandate`, `list_mandates_by_institution`.
- Instrument profiles: `add_instrument_profile`, `list_instruments_by_institution`.
- Action records: `add_action_record`, `get_action_record`, `list_actions_by_institution`, `all_actions`.
- `snapshot()` returns a sorted, JSON-friendly view of all four entity types.

Duplicate ids in any bucket are rejected with the appropriate `Duplicate*Error`. `get_*` methods raise `Unknown*Error` when the id is not found, matching the kernel-book convention from v0.4 (`ContractBook`) and v1.1 (`ValuationBook`).

### 38.4 The 4-property action contract

This is the load-bearing contract for v1.3 and beyond. Every `InstitutionalActionRecord` must satisfy:

1. **Explicit inputs.** `input_refs` lists the WorldIDs / record IDs the action consumed (prices, valuations, signals, ownership entries, etc.). Empty tuple is allowed; `None` is not.
2. **Explicit outputs.** `output_refs` lists what the action produced. Empty tuple is allowed.
3. **Ledger record.** `add_action_record` emits an `institution_action_recorded` ledger record. The action's `parent_record_ids` are preserved verbatim onto the ledger record so the audit trail forms a causal graph (per v1 design principle 6).
4. **No direct cross-space mutation.** The action record's storage and ledger emission are the only side effects. If a real action *should* produce a price observation, a contract update, or a signal, the consuming behavior module must mutate the relevant book through its own API and then record the action with `output_refs` pointing to the resulting records — the action record itself never drives the mutation.

The contract is the schema every v1.3+ behavioral module follows when it produces an action. Test `test_action_record_does_not_mutate_other_books` enforces property 4 by snapshotting every kernel-level book before and after recording an action and verifying byte-equality.

### 38.5 Recorded actions vs decided actions

v1.3 distinguishes:

- A **decided action** is the output of a reaction function or decision rule. v1.3 implements **none**.
- A **recorded action** is a fact stored after the decision (or after a routine non-decision event). v1.3 ships only the recording mechanism.

A future v1.3+ module that introduces a reference policy reaction function, for example, will read mandates from `InstitutionBook`, reference instruments from there, and call `add_action_record(...)` with `parent_record_ids` linking to the inputs that triggered the action. v1.3 itself only ensures the recording shape works.

### 38.6 Ledger event types

- `institution_profile_added`
- `institution_mandate_added`
- `institution_instrument_added`
- `institution_action_recorded` — preserves `parent_record_ids` from the source action record onto the ledger record.

All four use `space_id="institutions"`.

### 38.7 Kernel wiring

`WorldKernel` exposes `kernel.institutions: InstitutionBook`. The book's `ledger` and `clock` are propagated in `__post_init__`, alongside the existing books (`ownership`, `contracts`, `prices`, `constraints`, `signals`, `valuations`).

### 38.8 What v1.3 does not do

- No central bank reaction function, policy rate setting, liquidity operation, or regulatory impact.
- No decision logic that creates `InstitutionalActionRecord`s from world state. Future v1.3+ modules will create records as outputs of their own decision rules; v1.3 itself never creates an action automatically.
- No country-specific institutions or jurisdiction-calibrated behavior. `jurisdiction_label` is a free-form string with no validation.
- No automatic signal emission, EventBus delivery, contract creation, price update, or any other cross-space side effect from action records.
- No external shock generation, scenarios, or Japan calibration.

### 38.9 v1.3 success criteria

v1.3 is complete when **all** of the following hold:

1. The four immutable dataclasses exist with all documented fields and reject empty required fields.
2. `InstitutionBook` provides the full CRUD surface (`add_institution_profile`, `get_institution_profile`, `list_by_type`, `add_mandate`, `list_mandates_by_institution`, `add_instrument_profile`, `list_instruments_by_institution`, `add_action_record`, `get_action_record`, `list_actions_by_institution`) plus `snapshot()`.
3. Duplicate ids in each bucket are rejected with the appropriate dedicated error.
4. `InstitutionalActionRecord` enforces the 4-property action contract: inputs / outputs / ledger / no cross-space mutation.
5. `institution_action_recorded` ledger records preserve `parent_record_ids` from the source action record.
6. The four ledger record types are emitted on the corresponding `add_*` calls when a ledger is configured.
7. `kernel.institutions` is exposed with default wiring (clock and ledger propagated in `__post_init__`).
8. Adding an action record does not mutate any other source-of-truth book.
9. `jurisdiction_label` accepts any free-form string without validation.
10. All previous milestones (v0 through v1.2.1) continue to pass.

---

## 39. ExternalWorld Process (v1.4)

The v1.4 milestone makes external factors first-class objects in the kernel: it lets the world declare *how an external factor evolves* (process), record *what was observed* (observation), and replay *a known trajectory* (scenario path) — all without causing any domestic economic behavior. v1.4 ships only two minimal generation helpers (constant + scenario-path replay); stochastic dynamics, real data loading, and domestic propagation are out of scope.

For the full design rationale (process vs observation vs scenario path, why no shocks, why domestic impact is deferred, how v2/v3 calibrated data plug in), see [`v1_external_world_process_design.md`](v1_external_world_process_design.md).

### 39.1 Why external factors are first-class

`ExternalSpace` (v0.14, §34.3) classifies which exogenous factors the world tracks. v1.4 adds the next layer: a process that defines how a factor evolves, observations that record what value the factor took, and scenario paths that replay a deterministic trajectory. The three are stored independently in `ExternalProcessBook` and answer different questions; later milestones (or test fixtures) decide which one drives a given run.

### 39.2 The four record types

v1.4 ships four immutable dataclasses in `world/external_processes.py`:

- **`ExternalFactorProcess`** — `process_id`, `factor_id`, `factor_type`, `process_type`, `unit`, `base_value`, `status`, `metadata`. The `process_type` is a free-form string with suggested labels (`"constant"`, `"manual"`, `"scenario_path"`, `"historical_replay"`, `"random_walk"`, `"mean_reverting"`, `"regime_switching"`); v1.4 only ships generation logic for `"constant"`.
- **`ExternalFactorObservation"** — `observation_id`, `factor_id`, `as_of_date`, `value`, `unit`, `source_id`, optional `phase_id`, optional `process_id`, `confidence`, `related_ids`, `metadata`. An observation records what the world saw; not every observation comes from a process, so `process_id` is optional.
- **`ExternalScenarioPoint`** — `factor_id`, `as_of_date`, `value`, `unit`, optional `phase_id`, `metadata`. A point is the building block of a scenario path.
- **`ExternalScenarioPath`** — `path_id`, `factor_id`, `points`, `source_id`, `metadata`. The path validates on construction that all points share its `factor_id`.

### 39.3 ExternalProcessBook API

- Process CRUD: `add_process`, `get_process`, `list_processes_by_factor`, `list_processes_by_type`.
- Observation CRUD: `add_observation`, `get_observation`, `list_observations_by_factor`, `latest_observation(factor_id)`.
- Scenario-path CRUD: `add_scenario_path`, `get_scenario_path`, `get_scenario_point(path_id, as_of_date, phase_id=None)`.
- Helpers: `create_constant_observation` (uses process `base_value`), `create_observation_from_path` (replays a scenario point).
- `snapshot()` returns sorted, JSON-friendly views of all three buckets.

`latest_observation` returns the highest-`as_of_date` observation for a factor, or `None`. `get_scenario_point` returns `None` for a missing point on an existing path and raises `UnknownScenarioPathError` for an unknown path.

### 39.4 Two minimal generation helpers

v1.4 ships exactly two generation helpers and explicitly nothing else:

- `create_constant_observation(process_id, as_of_date, phase_id=None)` — looks up a process with `process_type="constant"`, validates `base_value is not None`, builds an observation with a deterministic id (`f"observation:{process_id}:{as_of_date}:{phase_id or 'no_phase'}"`), and stores it.
- `create_observation_from_path(path_id, as_of_date, phase_id=None)` — looks up the matching point on a scenario path, builds an observation from it (with `metadata["source_path_id"] = path_id` for provenance), and stores it. Returns `None` for a missing point.

Random walks, mean reversion, regime switching, jump diffusion, historical replay from real data files — none of these are in v1.4. Each is a calibration decision, and v1 stays jurisdiction-neutral.

### 39.5 Conceptual rules

- Observations record what the world *observed*, not what any domestic agent does about it.
- `ExternalProcessBook` does **not** mutate `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, `SignalBook`, `ValuationBook`, or `InstitutionBook`.
- `ExternalProcessBook` does **not** update prices automatically. An observation that the USD/JPY rate moved does not propagate into `PriceBook`. Behavior that consumes observations and updates other books belongs to later milestones and must satisfy the v1 four-property action contract.
- `ExternalProcessBook` does **not** generate signals automatically. v1.4 considered emitting `signal_added` from observations and rejected it: signal creation is an authoring decision, not a side effect of observation.

### 39.6 Cross-reference rule

`factor_id` on processes and observations, and `process_id` on observations, are not validated for resolution. v1.4 does not require a factor to be registered in `ExternalSpace` before a process references it; it does not require a process to exist before an observation claims it. This is the v0 / v1 cross-reference rule: cross-references are recorded as data, not enforced as invariants. v2 / v3 calibration may populate factors and processes in either order.

### 39.7 Ledger event types

- `external_process_added` — emitted by `add_process`.
- `external_observation_added` — emitted by `add_observation`.
- `external_scenario_path_added` — emitted by `add_scenario_path`.

All three use `space_id="external_processes"`. Observations propagate `confidence` to the ledger record's `confidence` field.

### 39.8 Kernel wiring

`WorldKernel` exposes `kernel.external_processes: ExternalProcessBook`. The book's `ledger` and `clock` are propagated in `__post_init__`, alongside the existing books (`ownership`, `contracts`, `prices`, `constraints`, `signals`, `valuations`, `institutions`).

### 39.9 What v1.4 does not do

- No stochastic process generation (random walk, mean reversion, regime switching, etc.). Those are later milestones.
- No historical replay from real data files. Loading public Japan data is a v2 task; loading proprietary or paid data is a v3 task.
- No domestic propagation of observations to `PriceBook`, `SignalBook`, or any domain space.
- No FX conversion (v1.1's `ValuationComparator` already declines to convert; v1.4 likewise does not).
- No shock primitives ("oil shock", "war", "FX crash"); no scenario interpretation; no Japan-specific calibration.

### 39.10 v1.4 success criteria

v1.4 is complete when **all** of the following hold:

1. The four immutable dataclasses exist with all documented fields and reject empty required fields where applicable.
2. `ExternalProcessBook` provides the full CRUD surface plus the two helpers and `snapshot`.
3. Duplicate ids in each bucket are rejected with their `Duplicate*Error`. Unknown lookups raise `Unknown*Error`.
4. `latest_observation` returns the highest-`as_of_date` observation for a factor, or `None`.
5. `get_scenario_point` returns `None` for a missing point on an existing path and raises `UnknownScenarioPathError` for an unknown path.
6. `create_constant_observation` validates `process_type == "constant"` and `base_value is not None`, builds a deterministic `observation_id`, and rejects double-calls as duplicates.
7. `create_observation_from_path` returns `None` for a missing point and writes nothing in that case; raises for an unknown path.
8. The three ledger record types are emitted on the corresponding `add_*` calls when a ledger is configured.
9. `kernel.external_processes` is exposed with default wiring.
10. v1.4 mutates none of `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, `SignalBook`, `ValuationBook`, or `InstitutionBook`.
11. All previous milestones (v0 through v1.3) continue to pass.

---

## 40. Relationship Capital Layer (v1.5)

The v1.5 milestone adds **non-contractual relationships** between world objects as first-class records. Relationship capital captures soft links — trust, reputation, information access, historical support, advisory ties, main-bank-like ties — that contracts (`ContractBook`, v0.4) and ownership (`OwnershipBook`, v0.4) cannot express. v1.5 stores the records and supports controlled strength updates; it does **not** apply decay, decide lending, drive investor behavior, propagate reputation effects, or calibrate to any specific jurisdiction.

For the full design rationale (why contracts are not enough, the four-layer separation between contract / ownership / signal / relationship, evidence-refs and causal traceability, why decay is stored but not applied, why Japan main-bank calibration is v2/v3), see [`v1_relationship_capital_design.md`](v1_relationship_capital_design.md).

### 40.1 RelationshipRecord

`RelationshipRecord` is an immutable dataclass with twelve fields:

- `relationship_id` — unique identifier.
- `source_id`, `target_id` — free-form WorldIDs (not validated for resolution).
- `relationship_type` — free-form string (e.g., `"main_bank"`, `"advisory"`, `"trust"`, `"interlocking_directorate"`).
- `strength` — domain-specific numeric score; v1.5 does not normalize.
- `as_of_date` — ISO date of the recorded state.
- `direction` — free-form string. Suggested labels: `"directed"` (asymmetric source→target), `"undirected"` (symmetric), `"reciprocal"` (mutual, possibly different strengths each way).
- `visibility` — free-form string (`"public"`, `"private"`, `"restricted"`, `"inferred"`, `"rumored"`). Stored but not enforced at read time; consumers decide visibility filtering.
- `decay_rate` — stored verbatim; v1.5 does **not** apply it on read.
- `confidence` — bounded to [0, 1].
- `evidence_refs` — tuple of WorldIDs / record IDs justifying the relationship (signals, contracts, action records, valuations, observations, ledger record IDs).
- `metadata` — bag for non-standard attributes.

### 40.2 RelationshipView

`RelationshipView` is an immutable derived record returned by `build_relationship_view`. Its fields:

- `subject_id`, `counterparty_id` — the two ids the view aggregates between.
- `relationship_types` — tuple of types found.
- `total_strength` — simple sum of strengths over included records.
- `visible_relationship_ids` — tuple of relationship_ids included.
- `as_of_date` — kernel clock's current date when available.
- `metadata` — empty by default.

The view is built on demand and never stored; reads are pure.

### 40.3 RelationshipCapitalBook API

- `add_relationship(record)` — append; rejects duplicate id; emits `relationship_added` to the ledger.
- `get_relationship(relationship_id)` — raises `UnknownRelationshipError` for unknown ids.
- `list_by_source` / `list_by_target` / `list_by_type` — indexed reads.
- `list_between(source_id, target_id)` — returns records with the exact (source, target) pair. Directional: callers wanting both directions call twice.
- `update_strength(relationship_id, new_strength, as_of_date=None, reason=None)` — replaces the record under the id with a copy carrying the new strength. Records `relationship_strength_updated` to the ledger with the previous strength and the supplied reason. Other fields (type, direction, visibility, decay_rate, confidence, evidence_refs, metadata) are preserved.
- `build_relationship_view(subject_id, counterparty_id)` — aggregation view (see §40.4).
- `snapshot()` — sorted, JSON-friendly view of all relationships.

### 40.4 build_relationship_view direction handling

`build_relationship_view(A, B)` returns a `RelationshipView` from A's perspective:

- All `(source=A, target=B)` records are included regardless of `direction`.
- `(source=B, target=A)` records are included **only** when their `direction` is `"undirected"` or `"reciprocal"`. `"directed"` records in the reverse direction describe B's view of A and belong to `build_relationship_view(B, A)`.

`total_strength` is the simple sum over the included records. v1.5 does not apply decay, normalize across types, weight by confidence, deduplicate, or filter by visibility — those are interpretation concerns. The view sums what is there.

### 40.5 Why decay is stored but not applied

`decay_rate` is recorded as a parameter slot and v1.5 explicitly does not compute `strength * exp(-decay * elapsed)` on read. The reasons:

- Decay parameters are jurisdiction-specific empirical findings (calibration, not architecture). v1 stays jurisdiction-neutral.
- Multiple decay models (continuous exponential, step on covenant breach, ratchet on success) are plausible. v1.5 should not commit to one.
- If decay were auto-applied, two reads of the same relationship at different dates would return different strengths, making the read path stateful in a way the rest of the kernel avoids. v1.5's reads are deterministic.

A future module that wants decayed strength computes it from the stored fields, or calls `update_strength` to persist a decayed value as a new fact. Either path keeps the audit trail clear. Test [`test_decay_rate_stored_but_not_applied`](../tests/test_relationships.py) enforces this rule.

### 40.6 Evidence refs

`evidence_refs` carries the ids of records that justify why a relationship exists. The field accepts any kind of WorldID / record id without validation: contracts, signals, action records, valuations, observations, ledger record ids. The point is *causal traceability* — a future replay engine can walk from a relationship to its evidence and reconstruct the chain that produced the record.

This is the relationship-layer counterpart to v1.3's `InstitutionalActionRecord.parent_record_ids`. Both fields turn the ledger from a flat log into a causal graph.

### 40.7 Cross-reference rule

`source_id`, `target_id`, and `evidence_refs` are recorded as data and not validated for resolution. v1.5 follows the v0 / v1 rule: cross-references are data, not enforced invariants.

### 40.8 Ledger event types

- `relationship_added` — emitted by `add_relationship`. Carries the relationship's `visibility` and `confidence` to the ledger record's corresponding fields.
- `relationship_strength_updated` — emitted by `update_strength`. Records `previous_strength`, `new_strength`, `as_of_date` (post-update), and the supplied `reason`.

Both use `space_id="relationships"`.

### 40.9 Kernel wiring

`WorldKernel` exposes `kernel.relationships: RelationshipCapitalBook`. The book's `ledger` and `clock` are propagated in `__post_init__`, alongside the existing books (`ownership`, `contracts`, `prices`, `constraints`, `signals`, `valuations`, `institutions`, `external_processes`).

### 40.10 What v1.5 does not do

- No lending decisions, investor behavior, or automatic rescue / support. All belong to later milestones that consume relationships and satisfy the v1 four-property action contract.
- No decay application. `decay_rate` is stored verbatim.
- No reputation contagion across third parties (A's trust in B influencing C's trust in B). v1.5 stores pairwise relationships only.
- No information-asymmetry modeling. v1.5 records the tie; it does not model the asymmetry.
- No visibility filtering at read time. The label is stored but not enforced.
- No network analytics (centrality, communities, clustering). Those are derivable from `snapshot()` if needed.
- No Japan main-bank calibration. v1.5 supports `relationship_type="main_bank"` as a string label and stores any caller-assigned strength; jurisdiction-specific main-bank semantics belong to v2 (public calibration) or v3 (proprietary).
- No price impact, credit decisions, trading, or scenarios.

### 40.11 v1.5 success criteria

v1.5 is complete when **all** of the following hold:

1. `RelationshipRecord` exists with all twelve documented fields and is immutable. Required fields are validated; `confidence` is bounded to [0, 1].
2. `RelationshipView` exists as an immutable derived record.
3. `RelationshipCapitalBook` provides `add_relationship`, `get_relationship`, `list_by_source`, `list_by_target`, `list_by_type`, `list_between`, `update_strength`, `build_relationship_view`, and `snapshot`.
4. Duplicate ids are rejected with `DuplicateRelationshipError`. Unknown lookups raise `UnknownRelationshipError`.
5. `update_strength` replaces the record in place, preserves all other fields, and records a ledger event with the previous strength and supplied reason.
6. `evidence_refs` is preserved through add and get unchanged.
7. `decay_rate` is stored verbatim and **not** automatically applied on read.
8. `build_relationship_view` aggregates forward records plus undirected / reciprocal reverse records, sums strengths without applying decay, and triggers no behavior in any other book.
9. The two ledger record types are emitted on the corresponding `add_*` / update calls when a ledger is configured.
10. `kernel.relationships` is exposed with default wiring.
11. v1.5 mutates none of `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, `SignalBook`, `ValuationBook`, `InstitutionBook`, or `ExternalProcessBook`.
12. All previous milestones (v0 through v1.4) continue to pass.

---

## 41. First Closed-loop Reference System (v1.6)

The v1.6 milestone is the v1 line's climax. It connects v1.1 valuation, v1.2 intraday phases, v1.3 institutional decomposition, v1.4 ExternalWorld processes, and v1.5 relationship capital into a single end-to-end causal trace through the kernel — without any module mutating state outside its own book and without any economic decision being made.

For the full design rationale and chain diagram, see [`v1_first_closed_loop_design.md`](v1_first_closed_loop_design.md).

### 41.1 The reference loop

v1.6 implements the *shape* of a closed financial-economy feedback loop without any of the decisions:

```
ExternalFactorObservation  (v1.4, phase_id="overnight")
  → InformationSignal_1                    (v0.7, related_ids=obs)
  → ValuationRecord                        (v1.1, related_ids=signal_1, inputs={signal_id})
  → ValuationGap                           (v1.1, comparator output)
  → InstitutionalActionRecord              (v1.3, phase_id="post_close",
                                                  input_refs=valuation,
                                                  output_refs=signal_2,
                                                  parent_record_ids=ledger refs)
  → InformationSignal_2                    (v0.7, related_ids=action)
  → WorldEvent                             (v0.3, payload signal_id=signal_2)
  → event_delivered records on day D+1     (v0.3 next-tick rule)
```

Every step is a record. No step decides. Every link is preserved through `parent_record_ids` (on the action's ledger record), `related_ids` (on signals and events), `input_refs` and `output_refs` (on the action). A reviewer walking the ledger after the run can reach every node from any other.

### 41.2 ReferenceLoopRunner

`world/reference_loop.py` ships a thin orchestrator with one method per step:

- `record_external_observation` — uses v1.4's `create_constant_observation` helper.
- `emit_signal_from_observation` — adds a signal whose `related_ids` and `payload` reference the observation.
- `record_valuation_from_signal` — adds a valuation whose `related_ids` and `inputs.signal_id` reference the signal.
- `compare_valuation_to_price` — calls v1.1's `ValuationComparator.compare_to_latest_price`.
- `record_institutional_action` — adds an action whose `input_refs` include the valuation, whose `output_refs` name the planned follow-up signal, and whose `parent_record_ids` link to the `valuation_added` and `valuation_compared` ledger records.
- `emit_signal_from_action` — adds the planned follow-up signal with `related_ids` pointing back to the action.
- `publish_signal_event` — publishes a `WorldEvent` referencing the follow-up signal, and records `event_published` to the ledger so runner-driven publication produces the same audit trail as `BaseSpace`-driven publication.

The runner does not decide anything; it only chains the bookkeeping. Future behavior modules that consume valuations and produce decisions will call the same book APIs the runner calls.

### 41.3 Phase stamps

The observation is stamped with `phase_id="overnight"` and the action with `phase_id="post_close"`, matching the use cases documented in §37.4 / `v1_intraday_phase_design.md`. v1.6 does not run via `run_day_with_phases` — that is a v1.2 feature exercised separately. The phase stamps on the records document conceptually when each step happens.

### 41.4 What v1.6 does not do

- No price formation, investor trading, bank credit decisions, corporate actions, or policy decisions.
- No relationship-driven behavior (v1.5 is available but not used in the v1.6 chain).
- No external shock impact propagation. The observation has a constant value; the gap is just a number.
- No iteration. The loop demonstrates one cycle; iterating the chain (so the follow-up signal feeds back into the next valuation cycle) is a future behavioral milestone.
- No Japan-specific calibration. The test uses neutral identifiers (`institution:reference_authority`, `factor:reference_macro_index`, `firm:reference_a`).
- No price update. `PriceBook` is read by the comparator and never written by the loop. Snapshots of ownership, contracts, prices, constraints, and relationships are byte-identical before and after the loop.

### 41.5 How v1.6 prepares v2 / v3

v2 (Japan public calibration) and v3 (Japan proprietary calibration) plug into the same chain shape with calibrated data:

- The constant `ExternalFactorProcess` becomes a real macro indicator from public Japan data (v2) or paid sources (v3).
- The `InformationSignal_1` becomes a real disclosure (TDnet, EDINET, BoJ press release) at v2; vendor-curated content at v3.
- The `ValuationRecord` becomes a real model output (v2 reference DCF; v3 proprietary).
- The `InstitutionalActionRecord` becomes a real institution's action (v2 BoJ; v3 with proprietary policy intelligence).
- The `WorldEvent` delivers to the same eight v0 spaces.

The chain shape, record types, and audit trail are unchanged. Calibration changes the data; v1.6 freezes the structure.

### 41.6 v1.6 success criteria

v1.6 is complete when **all** of the following hold:

1. `ReferenceLoopRunner` exists in `world/reference_loop.py` with seven step methods, each delegating to the existing kernel-level book that owns the record type produced.
2. The end-to-end loop test runs without exceptions and produces all seven expected ledger event types (`external_observation_added`, `signal_added`, `valuation_added`, `valuation_compared`, `institution_action_recorded`, `event_published`, `event_delivered`).
3. Forward and backward references are preserved at every link in the chain.
4. The action's `parent_record_ids` includes both the `valuation_added` and `valuation_compared` ledger record IDs.
5. Event delivery follows the v0.3 next-tick rule: no `event_delivered` records on day 1; both target spaces (`banking`, `investors` — both DAILY-firing) receive on day 2.
6. `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, and `RelationshipCapitalBook` are byte-identical before and after the loop runs.
7. The runner is jurisdiction-neutral. No Japan-specific institution, factor, firm, or data source appears in v1.6 code or tests.
8. All previous milestones (v0 through v1.5) continue to pass.

## 42. v1 Reference System Freeze (v1.7)

v1.7 closes the v1 line. It is **documentation only**: no Python behavior changes, no record-shape changes, no API additions, no test additions. Its purpose is to declare the v1 reference financial system frozen and to record the v2 hand-off picture before context fades.

### 42.1 What v1.7 freezes

v1.7 declares the following v1 surface frozen:

- **Record shapes.** `ValuationRecord`, `ValuationGap`, `IntradayPhaseSpec`, `PhaseSequence`, `InstitutionProfile`, `MandateRecord`, `PolicyInstrumentProfile`, `InstitutionalActionRecord`, `ExternalFactorProcess`, `ExternalFactorObservation`, `ExternalScenarioPoint`, `ExternalScenarioPath`, `RelationshipRecord`, `RelationshipView`. Field sets, types, defaults, and validation rules are frozen.
- **Book APIs.** `ValuationBook`, `InstitutionBook`, `ExternalProcessBook`, `RelationshipCapitalBook`. Method signatures, ledger emission contracts, snapshot determinism, and duplicate-detection rules are frozen.
- **Orchestrator semantics.** `ValuationComparator.compare_to_latest_price`, `ReferenceLoopRunner` step methods. Input shape, cross-reference wiring, and ledger emission are frozen.
- **Scheduler extensions.** `Phase` enum members (MAIN + 6 intraday phases), `PhaseSequence` reference order, `Scheduler.run_day_with_phases`, per-date run-mode guard. Frozen.
- **Ledger taxonomy.** Every v1 record type has a corresponding `RecordType` enum member. The set of v1 ledger record types is frozen.
- **Cross-reference vocabulary.** `related_ids`, `input_refs`, `output_refs`, `target_ids`, `instrument_ids`, `parent_record_ids`, `evidence_refs`, `inputs`, `assumptions`, `payload`, `metadata`. Shape and semantics frozen.
- **Action contract.** The four-property action contract (explicit inputs / outputs / ledger record / no cross-space mutation). Frozen.
- **Cross-references-as-data rule.** v1 books do not validate that referenced ids exist. Frozen.

After v1.7, breaking any of the above is a documented decision recorded in a new milestone, not a routine change.

### 42.2 What v1.7 deliberately is not

v1.7 is **not**:

- A v2 design session. v2 will pick a Japan public-data ingestion strategy, an institution-type controlled vocabulary, and a calibration-versioning scheme; none of those decisions is made here.
- A behavior-adding milestone. v1.7 adds zero Python lines.
- A test-adding milestone. v1.7 adds zero tests; the suite remains 632 / 632.
- A re-litigation of v0 or v1 invariants. Every v0 / v1 invariant is preserved.

### 42.3 Documents authored at v1.7

Four new docs and three updated docs together form the freeze record:

**New:**

- `docs/v1_release_summary.md` — what v1 delivered, what it proves, what is out of scope, test status, relationship to v2 / v3.
- `docs/architecture_v1.md` — text diagram of v0 kernel + v1 modules + ledger causal trace; per-record-type cross-reference vocabulary; run-mode guard.
- `docs/v1_scope.md` — explicit in/out boundary for v1; v1 vs v2 vs v3 boundary; pre-v2 checklist.
- `docs/v2_readiness_notes.md` — informal Japan public data source inventory; entity mapping (v1 record shape ← Japan reality) open questions; license-review open questions; v2 vs v3 clarification.

**Updated:**

- `README.md` (repo root) — v1 status, v0 vs v1 layer ownership, doc map updated, test count updated to 632.
- `docs/test_inventory.md` — v1 test files added, totals updated to 632.
- `docs/world_model.md` — this section.

### 42.4 v1.7 success criteria

v1.7 is complete when **all** of the following hold:

1. `docs/v1_release_summary.md`, `docs/architecture_v1.md`, `docs/v1_scope.md`, and `docs/v2_readiness_notes.md` exist and describe the v1 freeze surface.
2. `README.md` references v1 as the current frozen milestone, links to all new v1 docs, and reports `632 passed` as expected.
3. `docs/test_inventory.md` lists every v1 test file with its individual count, the v1 subtotal (188), and the v0 + v1 total (632).
4. `pytest -q` reports `632 passed`. No new tests were added; no existing tests were modified.
5. No Python file in `world/`, `spaces/`, or `tests/` is changed.
6. No v1 record shape, book API, scheduler extension, ledger record type, or cross-reference field is altered.
7. Every v0 invariant (no cross-space mutation, append-only ledger, deterministic snapshot, next-tick rule, MAIN-phase compatibility) continues to hold unchanged.
8. The freeze record (this section + the four new docs + the three updated docs) is committed under a single v1.7 commit so that the freeze is a discrete, identifiable event in the repository history.

After v1.7 is committed and pushed, the v1 line is closed. The next milestone is either a v1+ behavioral milestone with an explicit charter (e.g., adding price formation as v1.8) or a v2 milestone introducing Japan public calibration on top of the frozen v1 contract.

## 43. v1.8.1 Endogenous Reference Dynamics — Design

The v1.8 experiment harness (§42-era addition) wraps the v1.6 reference demo in a config-driven driver and a manifest. That structure is correct for the v1.7 freeze's "structural completeness" goal but exposes a design gap: the demo's seven-step causal chain only fires when an `ExternalFactorObservation` is recorded. Without an observation, the ledger is silent.

§43 (v1.8.1) is a **design-only** correction. Its principle, in one line:

> External shocks are not the engine of the world. They are optional inputs to an already-running endogenous system.

### 43.1 The Routine concept

A **Routine** is a scheduled, bounded, auditable process that the world runs on its own schedule, independent of external observations. Every routine:

- has explicit inputs (declared, not discovered) and explicit outputs;
- emits a `RoutineRunRecord` to the ledger on every execution;
- writes only to the books it owns + emits signals / valuations / institutional actions through existing v1 APIs;
- can run productively even when no external observation exists for that date.

A routine is the engine of endogenous activity. An external observation, when present, is *optional fuel* — never the trigger.

### 43.2 Proposed record shapes

`RoutineSpec` (immutable per v1 conventions): `routine_id`, `routine_type`, `owner_space_id`, `frequency`, `phase_id?`, `input_refs`, `output_schema`, `enabled`, `metadata`.

`RoutineRunRecord` (per-execution audit): `run_id`, `routine_id`, `as_of_date`, `phase_id?`, `input_refs`, `output_refs`, `parent_record_ids`, `status` ∈ `{completed, skipped, degraded, errored}`, `metadata`.

The `degraded` status is load-bearing: a routine that runs without one of its declared inputs (e.g., a missing external observation) still produces meaningful output and records the missing input in `metadata`. **A degraded run is a valid run, not an error.** This is the operational test for "is this milestone scenario-driven or endogenous?"

### 43.3 The seven reference routines

v1.8.1 names seven candidate routines without implementing any of them:

1. `corporate_quarterly_reporting` — firm files calendar-driven results.
2. `valuation_refresh` — research desk re-computes a valuation.
3. `debt_maturity_aging` — projection refresh as time passes.
4. `bank_review` — bank's periodic exposure review (signal only, no lending change).
5. `investor_review` — investor's periodic mandate review (signal only, no rebalance).
6. `relationship_refresh` — `RelationshipView` snapshot, optional decay write.
7. `information_staleness_update` — projection refresh as time passes.

For each, the design doc specifies what the routine reads, what it writes, what it must not yet do (price moves, trades, contract rewrites, corporate actions, discretionary policy, jurisdiction calibration), and how it appears in the ledger.

### 43.4 Boundaries — what routines may NOT do (yet)

- Move prices (no `PriceBook` writes).
- Execute trades (no `OwnershipBook` writes representing decisions).
- Change lending terms (no `ContractBook` rewrites).
- Trigger corporate actions (no asset sales / buybacks / issuances).
- Implement discretionary policy (no Taylor / Brainard / inflation-targeting rules).
- Apply Japan-specific calibration (no real-institution identifiers, no jurisdiction parameters).

The first four boundaries are load-bearing. A routine PR that touches `PriceBook`, `OwnershipBook`, or rewrites `ContractBook` fields is a behavioral milestone, not a routine.

### 43.5 Sensitivity matrices — not the engine

A natural temptation is to ship a sensitivity-matrix layer that translates observations into impact estimates. v1.8.1 commits to two principles:

1. Sensitivity matrices *parameterize* routines; they do not replace them.
2. A routine that runs without external input must still produce something meaningful. If a routine's only behavior is "look up sensitivity to today's external shock," the design has slipped back into scenario-driven mode.

### 43.6 Relation to ExternalFactorObservation

`ExternalFactorObservation` (§39, v1.4) remains a first-class record type. Routines may include an observation in `input_refs`; if present, the routine uses it; if absent, the routine still runs (with `status="completed"` or `status="degraded"`). Absence of an observation never means absence of activity.

### 43.7 Proposed milestone sequence

| Milestone | Scope |
| --- | --- |
| **v1.8.1** | This design doc. No code. |
| **v1.8.2** | Routine Engine: `RoutineSpec` + `RoutineBook`, `RoutineRunRecord` ledger emission, scheduler integration. Engine plumbing only. |
| **v1.8.3** | First concrete routine: `corporate_quarterly_reporting`. |
| **v1.8.4** | `valuation_refresh`, demonstrating the "degraded but valid" path explicitly. |
| **v1.8.5** | `bank_review`, `investor_review`, `relationship_refresh`, `information_staleness_update`, `debt_maturity_aging`. |
| **v1.9** | Living Reference World Demo: a year-long run on the routine engine *without any external observation*, with a non-empty ledger on every quarter-end / month-end / review cycle. |

### 43.8 v1.8.1 success criteria

v1.8.1 is complete when **all** of the following hold:

1. `docs/v1_endogenous_reference_dynamics_design.md` exists and states the core principle, the Routine vocabulary, the proposed `RoutineSpec` and `RoutineRunRecord` field sets, the seven reference routines, the boundaries, the sensitivity-matrix discipline, the external-world relation, and the milestone sequence.
2. `docs/fwe_reference_demo_design.md` carries a direction note pointing at v1.8.1 and flagging that the v1.7 demo is structurally complete but not yet endogenous.
3. This section (§43) records the design in the constitutional log.
4. No `world/`, `spaces/`, `examples/`, or `tests/` file is modified. The 725-test baseline is unchanged at v1.8.1.
5. The v1.8.2 Routine Engine milestone has a clear charter to land against, including the exact record-shape proposals above.

After v1.8.1 ships, the v1.x line is no longer "frozen reference + demo wrapper" — it is "frozen reference + demo wrapper + endogenous activity layer being built milestone by milestone." The v1.9 Living Reference World Demo is the v1.x layer's natural closing milestone.

> **Sequence revision:** §44 (v1.8.2) reorders the v1.8.x line so the topology + attention substrate lands *before* the Routine Engine. The authoritative milestone table is in §44.7 below.

## 44. v1.8.2 Interaction Topology and Attention Framework — Design

§43 (v1.8.1) named the *engine* of endogenous activity (Routines). §44 (v1.8.2) names two layers around that engine: the **InteractionTopology** (which channels are possible between spaces) and the **AttentionProfile / ObservationMenu / SelectedObservationSet** stack (what each actor watches, what is available, what was selected).

§44 (v1.8.2) is **design-only**. No `world/`, `spaces/`, `examples/`, or `tests/` file is changed.

The principle, in one line:

> `InteractionTopology` is not the engine of the world. `Routine` is the execution primitive (§43). `InteractionTopology` defines the possible channels routines may use; `AttentionProfile` defines what each actor actually watches.

### 44.1 Spaces as a directed multigraph

Spaces are nodes. Interactions are edges. Edges are **directed** (`Corporate → Banking` ≠ `Banking → Corporate`), the graph is a **multigraph** (a pair may have multiple channels concurrently), and **self-loops are first-class** (most v1.8.1 routines live on the diagonal). The natural data structure is a third-rank tensor `T ∈ S × S × C` where `S` is the set of registered spaces and `C` is the set of channel types. A simple upper-triangular adjacency matrix collapses direction, channel multiplicity, and the diagonal — and is therefore insufficient.

### 44.2 `InteractionSpec`

Static declaration of one channel. Proposed fields:

`interaction_id`, `source_space_id`, `target_space_id`, `source_id?`, `target_id?`, `interaction_type`, `channel_type`, `direction`, `frequency`, `phase_id?`, `visibility` ∈ `{public, restricted, private}`, `enabled`, `required_input_ref_types`, `optional_input_ref_types`, `output_ref_types`, `routine_types_that_may_use_this_channel`, `metadata`.

`routine_types_that_may_use_this_channel` is the load-bearing field that prevents arbitrary routines from publishing on arbitrary channels.

### 44.3 `InteractionBook`

Append-only kernel-level book mirroring v1.4's `ExternalProcessBook`. API: `add_interaction`, `get_interaction`, `list_by_source_space`, `list_by_target_space`, `list_between_spaces`, `list_by_type`, `list_by_channel`, `list_for_routine_type`, `build_space_interaction_matrix`, `snapshot`. The matrix builder is a 2-D collapse of the tensor for diagram / overview consumers; routines should use the filter-style methods.

### 44.4 `AttentionProfile`

Heterogeneous receiver-side declaration. Proposed fields:

`profile_id`, `actor_id`, `actor_type`, `watched_space_ids`, `watched_subject_ids`, `watched_signal_types`, `watched_channels`, `watched_metrics`, `watched_valuation_types`, `watched_constraint_types`, `watched_relationship_types`, `update_frequency`, `phase_id?`, `priority_weights`, `missing_input_policy` ∈ `{degraded, strict, skip}`, `metadata`.

Multiple profiles per actor are allowed and expected (a bank may run "daily liquidity" and "quarterly counterparty review" as separate profiles).

### 44.5 `ObservationMenu` and `SelectedObservationSet`

`ObservationMenu` is a *view*: what is available to an actor at a date / phase, computed fresh per routine run from the actor's profile and the world's current ledger state. Fields: `actor_id`, `as_of_date`, `phase_id?`, `available_signal_ids`, `available_valuation_ids`, `available_constraint_ids`, `available_relationship_ids`, `available_price_ids`, `available_external_observation_ids`, `available_interaction_ids`, `metadata`. **Empty availability lists are normal**, not erroneous.

`SelectedObservationSet` is a *record*: what the actor actually selected from the menu. Fields: `selection_id`, `actor_id`, `attention_profile_id`, `routine_run_id?`, `selected_refs`, `skipped_refs`, `selection_reason` ∈ `{profile_match, priority_top_k, recency, explicit, degraded_no_input}`, `as_of_date`, `phase_id?`, `status` ∈ `{completed, partial, degraded, errored}`, `metadata`.

### 44.6 Degraded operation — restated

The v1.8.1 anti-scenario discipline (§43.1) cascades through v1.8.2 as:

```
ExternalFactorObservation absent? optional input only.
ObservationMenu may be partial.
SelectedObservationSet may have status="partial" / "degraded" with selection_reason="degraded_no_input".
RoutineRunRecord may have status="degraded" but still produces endogenous output.
```

A routine that becomes silent solely because the menu was empty is violating §43.1. v1.8.4+ reviewers should reject this pattern.

### 44.7 Revised milestone sequence

| Milestone | Scope | Code? |
| --- | --- | --- |
| **v1.8.1 Endogenous Reference Dynamics — Design** | §43. Routine vocabulary; seven candidate routines. (Shipped.) | No |
| **v1.8.2 Interaction Topology and Attention — Design** | §44. Topology + attention vocabulary. | No |
| **v1.8.3 InteractionBook + Matrix / Tensor View** | `InteractionSpec` + `InteractionBook` + `build_space_interaction_matrix()` + ledger event types. | Yes (kernel) |
| **v1.8.4 AttentionProfile / ObservationMenu** | `AttentionProfile` + `SelectedObservationSet` + `ObservationMenu` view builder. Routine-engine plumbing (per §43): `RoutineSpec` + `RoutineBook` + `RoutineRunRecord`. No concrete routine yet. | Yes (kernel) |
| **v1.8.5 Corporate Reporting Routine** | First concrete routine: `corporate_quarterly_reporting`. Diagonal `Corporate → Corporate` channel. | Yes |
| **v1.8.6 Investor and Bank Attention Demo** | Two more concrete routines using heterogeneous attention; demonstrates that different actors looking at the same world produce structurally different ledger traces. Remaining §43 reference routines wired here or in v1.8.7+. | Yes |
| **v1.9 Living Reference World Demo** | Year-long run on the routine + topology + attention stack with **no** external observation; non-empty ledger on every reporting / review cycle. Replay-determinism + manifest preserved. | Yes (demo + tests) |

### 44.8 Boundaries

Topology does not decide behavior. Attention does not execute trades or lending decisions. `ObservationMenu` is a view, not a mutation. `SelectedObservationSet` is a record of attention, not an economic action. Routines may later consume `SelectedObservationSet`, but v1.8.2 does not implement that. All v1.8.1 prohibitions (no price formation, no trading, no credit decisions, no corporate actions, no policy reaction functions, no Japan calibration, no real data, no external-shock scenario engine) are inherited.

### 44.9 v1.8.2 success criteria

§44 is complete when **all** hold:

1. `docs/v1_interaction_topology_design.md` exists and contains the principle, the directed-multigraph rationale, the proposed `InteractionSpec` / `InteractionBook` / `AttentionProfile` / `ObservationMenu` / `SelectedObservationSet` shapes, the heterogeneous-attention examples, the relation to existing v1 modules, the boundaries, and the revised milestone sequence.
2. `docs/v1_endogenous_reference_dynamics_design.md` carries a "sequence revised by v1.8.2" note pointing at v1.8.2's authoritative table.
3. This section (§44) records the design in the constitutional log.
4. No `world/`, `spaces/`, `examples/`, or `tests/` file is modified. The 725-test baseline is unchanged.
5. v1.8.3 reviewers can land `InteractionBook` against the proposed `InteractionSpec` shape without re-litigating direction; v1.8.4 reviewers can land the attention machinery against the proposed `AttentionProfile` / `ObservationMenu` / `SelectedObservationSet` shapes without re-litigating direction.

## 45. v1.8.3 InteractionBook + Tensor View

§45 (v1.8.3) implements the v1.8.2 design's storage layer: a kernel-level `InteractionBook` that stores **possible** directed interaction channels between spaces (and optionally between specific world objects), with deterministic tensor / matrix views.

§45 ships **only** the storage. The Routine engine (§43, v1.8.4+), `AttentionProfile` / `ObservationMenu` / `SelectedObservationSet` (§44, v1.8.4) are later milestones that will consume this book; v1.8.3 does not execute any channel, fire any routine, or decide any behavior.

### 45.1 What lands in v1.8.3

- `world/interactions.py`:
  - `InteractionSpec` immutable dataclass with the 16 fields proposed in §44.2: `interaction_id`, `source_space_id`, `target_space_id`, `interaction_type`, `channel_type`, `direction`, `frequency`, `phase_id`, `visibility`, `enabled`, `required_input_ref_types`, `optional_input_ref_types`, `output_ref_types`, `routine_types_that_may_use_this_channel`, `source_id`, `target_id`, `metadata`.
  - `InteractionBook` append-only store with the §44.3 API: `add_interaction`, `get_interaction`, `list_interactions`, `list_by_source_space`, `list_by_target_space`, `list_between_spaces`, `list_by_type`, `list_by_channel`, `list_for_routine_type`, `snapshot`, plus `build_space_interaction_tensor` and `build_space_interaction_matrix` view helpers.
  - `InteractionError`, `DuplicateInteractionError`, `UnknownInteractionError`.
- `world/ledger.py`: new `RecordType.INTERACTION_ADDED = "interaction_added"`. `add_interaction` writes one such record per insert when a ledger is wired.
- `world/kernel.py`: new `interactions: InteractionBook` field; the standard `__post_init__` wiring shares the kernel's ledger and clock with the book.
- `tests/test_interactions.py`: 50 tests covering field validation, CRUD + duplicate rejection, every filter listing, the disabled-by-default rule, self-loops on the diagonal, channel multiplicity in one cell, tensor and matrix view shape + determinism, snapshot determinism, ledger emission + the new `RecordType` member, kernel wiring, and a no-mutation guarantee against every other v0/v1 source-of-truth book.

### 45.2 Tensor / matrix view shape

`build_space_interaction_tensor(include_disabled=False)` returns a sparse, deterministically-ordered nested mapping:

```
T[source_space_id][target_space_id][channel_type] = [interaction_id, ...]
```

All keys are sorted; the leaf list of `interaction_id`s is sorted. Disabled interactions are excluded by default; pass `include_disabled=True` to retain them.

`build_space_interaction_matrix(include_disabled=False)` is the channel-axis collapse of the tensor:

```
M[source_space_id][target_space_id] = {
    "count": int,
    "enabled_count": int,
    "channel_types": [channel_type, ...],   # sorted
    "interaction_ids": [interaction_id, ...],   # sorted
}
```

When `include_disabled=False` (default), `count == enabled_count` because disabled rows are filtered out before counting. When `include_disabled=True`, `count` is the unfiltered total and `enabled_count` is the live subset.

### 45.3 Self-loops are first-class

`source_space_id == target_space_id` is a normal case, not an error. The §44 design called the diagonal of the topology load-bearing because most §43 routines live there. v1.8.3 ships specific tests for the three §44 examples:

- `corporate → corporate`: `reporting_preparation` channel (drives the §43.5 corporate quarterly reporting routine in the v1.8.5 milestone).
- `investors → investors`: `crowding_or_peer_pressure` channel.
- `information → information`: `analyst_revision_chain` channel.

`build_space_interaction_tensor` includes diagonal cells alongside cross-space cells; the matrix view does the same.

### 45.4 Boundaries

§45 is a storage milestone. v1.8.3 does **not** add:

- Routine engine (the v1.8.4 milestone wires `RoutineSpec` / `RoutineBook` / `RoutineRunRecord` per §43).
- `AttentionProfile`, `ObservationMenu`, `SelectedObservationSet` (also v1.8.4 per §44).
- Price formation, trading, lending decisions, corporate actions, policy reaction functions, Japan calibration, real data, or any external-shock scenario engine. All v1.7 / v1.8.1 / v1.8.2 prohibitions are inherited.

The book stores possible channels; it does not execute them. Cross-references (`source_space_id`, `target_space_id`, `source_id`, `target_id`) are recorded as data and **not** validated against the registry, per the v0/v1 cross-reference rule.

### 45.5 v1.8.3 success criteria

§45 is complete when **all** hold:

1. `world/interactions.py`, the `INTERACTION_ADDED` ledger type, and the `interactions` kernel field exist and behave per §45.1.
2. `tests/test_interactions.py` passes (50 tests).
3. The full test suite passes (775 tests = 725 prior + 50 interactions).
4. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
5. No existing test was modified; no existing record shape, book API, scheduler extension, or ledger record type was altered.
6. `InteractionBook` does not mutate `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, `SignalBook`, `ValuationBook`, `InstitutionBook`, `ExternalProcessBook`, or `RelationshipCapitalBook` — verified by an explicit no-mutation test that reads their snapshots before and after the v1.8.3 read APIs run.

After §45 ships, the v1.8.4 milestone can land `RoutineBook` + the attention machinery against this storage layer without re-litigating either the topology shape or the §43 endogenous-dynamics direction.

## 46. v1.8.4 RoutineBook + RoutineRunRecord

§46 (v1.8.4) implements the §43 (v1.8.1) endogenous-dynamics design's *storage layer*: a kernel-level `RoutineBook` that stores **scheduled endogenous routine specifications** and **auditable per-execution run records**, integrated with the §45 (v1.8.3) `InteractionBook` through a single read-only compatibility predicate.

§46 is intentionally **narrower** than the v1.8.2 design's draft v1.8.4 ("RoutineBook + AttentionProfile + ObservationMenu + SelectedObservationSet"). The four-layer landing was too large; v1.8.4 ships only `RoutineBook` + `RoutineRunRecord`. `AttentionProfile`, `ObservationMenu`, and `SelectedObservationSet` move to v1.8.5+.

§46 does **not** ship execution. The book stores specs and run records; it does not schedule, fire, or otherwise *run* any routine. The Routine Engine that performs execution is a later milestone.

### 46.1 What lands in v1.8.4

- `world/routines.py`:
  - `RoutineSpec` immutable dataclass: `routine_id`, `routine_type`, `owner_space_id`, `frequency`, `owner_id?`, `phase_id?`, `enabled`, `required_input_ref_types`, `optional_input_ref_types`, `output_ref_types`, `allowed_interaction_ids`, `missing_input_policy` (default `"degraded"`), `metadata`. The default `missing_input_policy="degraded"` is the v1.8.1 anti-scenario default — a routine with missing optional inputs still produces output; only the status flags the partial run.
  - `RoutineRunRecord` immutable dataclass: `run_id`, `routine_id`, `routine_type`, `owner_space_id`, `as_of_date`, `status`, `owner_id?`, `phase_id?`, `input_refs`, `output_refs`, `interaction_ids`, `parent_record_ids`, `metadata`. Denormalized (`routine_type` and `owner_space_id` copied from the spec) so the audit record is self-contained.
  - `RoutineBook` append-only store: `add_routine`, `get_routine`, `list_routines`, `list_by_type`, `list_by_owner_space`, `list_by_frequency`, `list_for_interaction`, `add_run_record`, `get_run_record`, `list_runs_by_routine`, `list_runs_by_date`, `list_runs_by_status`, `snapshot`, plus the `routine_can_use_interaction(routine_id, interaction_id, interactions_book) -> bool` predicate.
  - `RoutineError`, `DuplicateRoutineError`, `DuplicateRoutineRunError`, `UnknownRoutineError`, `UnknownRoutineRunError`.
- `world/ledger.py`: new `RecordType.ROUTINE_ADDED = "routine_added"` and `RecordType.ROUTINE_RUN_RECORDED = "routine_run_recorded"`. `add_routine` writes the former; `add_run_record` writes the latter, preserving `parent_record_ids` on the ledger entry.
- `world/kernel.py`: new `routines: RoutineBook` field; the standard `__post_init__` wiring shares the kernel's ledger and clock.
- `tests/test_routines.py`: 72 tests covering `RoutineSpec` + `RoutineRunRecord` field validation, CRUD + duplicate rejection for both, every filter listing for routines and run records, the disabled-by-default rule, the recommended status vocabulary (`"completed"` / `"partial"` / `"degraded"` / `"failed"`), the `"degraded"` default for `missing_input_policy`, `parent_record_ids` preservation, the predicate's positive and negative cases (including the empty-allowed "any routine type" semantics inherited from §45), unknown-routine raises / unknown-interaction returns False, snapshot determinism, ledger emission of both new `RecordType` members, kernel wiring, and a no-mutation guarantee against every other v0/v1 source-of-truth book.

### 46.2 The compatibility predicate

`routine_can_use_interaction(routine_id, interaction_id, interactions_book) -> bool` is the **only** integration point between `RoutineBook` and `InteractionBook` in v1.8.4. Both sides must agree:

- The routine declares the channel by listing `interaction_id` in its `RoutineSpec.allowed_interaction_ids`.
- The interaction admits the routine type either by listing `RoutineSpec.routine_type` in its `InteractionSpec.routine_types_that_may_use_this_channel` *or* by leaving that tuple empty (the §45 / §44 "any routine type" semantics).

Behavior on missing inputs:

- Unknown `routine_id` → raises `UnknownRoutineError` (the routine half is local to this book; the caller should know its own routine ids).
- Unknown `interaction_id` → returns `False` (the interaction half is in another book; predicates should not raise on a closed-world miss). This keeps the predicate safe to call against any pair of ids without crash, which matters for downstream attention / engine milestones that may probe the topology speculatively.

The predicate is pure: it reads both books and mutates neither.

### 46.3 Boundaries

§46 is a storage + audit milestone. v1.8.4 does **not** add:

- Execution. `RoutineBook.add_run_record` records that a routine ran; nothing in v1.8.4 *causes* it to run.
- Scheduler integration. `RoutineSpec.frequency` is a free-form label; no scheduler tasks are registered.
- `AttentionProfile`, `ObservationMenu`, `SelectedObservationSet`. Those move to v1.8.5+.
- Concrete routines. `corporate_quarterly_reporting`, `valuation_refresh`, `bank_review`, `investor_review`, `relationship_refresh`, `information_staleness_update`, `debt_maturity_aging` — all v1.8.6+ milestones.
- Price formation, trading, lending decisions, corporate actions, policy reaction functions, Japan calibration, real data, or any external-shock scenario engine. All v1.7 / v1.8.1 / v1.8.2 / v1.8.3 prohibitions are inherited.

Cross-references on records (`allowed_interaction_ids` on a spec; `input_refs` / `output_refs` / `interaction_ids` / `parent_record_ids` on a run record) are recorded as data and **not** validated against any other book, per the v0 / v1 cross-reference rule.

### 46.4 v1.8.4 success criteria

§46 is complete when **all** hold:

1. `world/routines.py`, the two new ledger types, and the `routines` kernel field exist and behave per §46.1.
2. `tests/test_routines.py` passes (72 tests).
3. The full test suite passes (847 tests = 775 prior + 72 routines).
4. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
5. No existing test was modified; no existing record shape, book API, scheduler extension, or ledger record type was altered.
6. `RoutineBook` does not mutate any other v0 / v1 source-of-truth book (`OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, `SignalBook`, `ValuationBook`, `InstitutionBook`, `ExternalProcessBook`, `RelationshipCapitalBook`, `InteractionBook`) — verified by an explicit no-mutation test.

### 46.5 Revised v1.8.x sequence

The v1.8.2 design's milestone table named v1.8.4 as "AttentionProfile + ObservationMenu + Routine engine plumbing." §46 splits that landing:

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.1 Endogenous Reference Dynamics | Design (§43). | Shipped |
| v1.8.2 Interaction Topology + Attention | Design (§44). | Shipped |
| v1.8.3 InteractionBook + Tensor View | Code (§45). | Shipped |
| **v1.8.4 RoutineBook + RoutineRunRecord** | Code (§46). Storage + audit only. | **Shipped** |
| v1.8.5 AttentionProfile / ObservationMenu / SelectedObservationSet | Code. The §44 attention layer that v1.8.4 deferred. | Next |
| v1.8.6 Routine engine (execution) | Code. Schedule-and-fire wiring that consumes routines + attention to produce `RoutineRunRecord` entries automatically. | After v1.8.5 |
| v1.8.7 Corporate Reporting Routine | First concrete routine. | After v1.8.6 |
| v1.8.8 Investor + Bank Attention Demo | Two more concrete routines using heterogeneous attention. | After v1.8.7 |
| v1.9 Living Reference World Demo | Year-long run with no external observation; non-empty ledger on every reporting / review cycle. | After v1.8.8 |

The split keeps each milestone reviewable; previously v1.8.4 carried four record types, four ledger event types, and a view builder, which is too much to land in one PR.

## 47. v1.8.5 AttentionProfile + ObservationMenu + SelectedObservationSet

§47 (v1.8.5) implements the attention layer that the v1.8.2 design (§44) named: a kernel-level `AttentionBook` that stores **what each actor tends to watch** (`AttentionProfile`), **what is available at a date / phase** (`ObservationMenu`), and **what was actually selected** (`SelectedObservationSet`).

§47 ships **storage and lookup only**. The book stores the records and offers filter / lookup APIs plus a single read-only structural-overlap predicate. It does not build menus from other books, decide what to select, execute routines, or take any economic action. The Routine engine that consumes `SelectedObservationSet` to drive `RoutineRunRecord` entries is the v1.8.6 milestone.

### 47.1 What lands in v1.8.5

- `world/attention.py`:
  - `AttentionProfile` immutable dataclass with the §44.4 field set: `profile_id`, `actor_id`, `actor_type`, `update_frequency`, `phase_id?`, the eight `watched_*` tuple-of-string fields (`watched_space_ids`, `watched_subject_ids`, `watched_signal_types`, `watched_channels`, `watched_metrics`, `watched_valuation_types`, `watched_constraint_types`, `watched_relationship_types`), `priority_weights` (mapping `str → float`), `missing_input_policy` (default `"degraded"` — the v1.8.1 anti-scenario default), `enabled`, `metadata`.
  - `ObservationMenu` immutable dataclass with the §44.5 field set: `menu_id`, `actor_id`, `as_of_date`, `phase_id?`, the seven `available_*_ids` tuple-of-string fields (signals / valuations / constraints / relationships / prices / external observations / interactions), `metadata`. Empty and partial menus are valid.
  - `SelectedObservationSet` immutable dataclass with the §44.5 field set: `selection_id`, `actor_id`, `attention_profile_id`, `menu_id`, `routine_run_id?`, `selected_refs`, `skipped_refs`, `selection_reason`, `as_of_date`, `phase_id?`, `status`, `metadata`. v1.8.5 does **not** enforce that `selected_refs` is a subset of the menu's `available_*_ids` — the predicate is too speculative for a storage milestone, and the engine layer that consumes the selection can enforce it if it wishes. Callers that want `parent_record_ids` causal links put them under `metadata["parent_record_ids"]`; v1.8.5 does not invent a dedicated field.
  - `AttentionBook` append-only store with the v1.8.2 API: `add_profile`, `get_profile`, `list_profiles`, `list_profiles_by_actor`, `list_profiles_by_actor_type`, `list_profiles_by_watched_space`, `list_profiles_by_channel`, `add_menu`, `get_menu`, `list_menus_by_actor`, `list_menus_by_date`, `add_selection`, `get_selection`, `list_selections_by_actor`, `list_selections_by_profile`, `list_selections_by_menu`, `list_selections_by_status`, `snapshot`, plus the `profile_matches_menu(profile_id, menu_id) -> dict` structural-overlap helper.
  - `AttentionError`, `DuplicateAttentionProfileError`, `DuplicateObservationMenuError`, `DuplicateSelectedObservationSetError`, `UnknownAttentionProfileError`, `UnknownObservationMenuError`, `UnknownSelectedObservationSetError`.
- `world/ledger.py`: three new `RecordType` members:
  - `ATTENTION_PROFILE_ADDED = "attention_profile_added"`
  - `OBSERVATION_MENU_CREATED = "observation_menu_created"`
  - `OBSERVATION_SET_SELECTED = "observation_set_selected"`
  `add_profile` / `add_menu` / `add_selection` write the corresponding entry when a ledger is wired. The selection ledger entry carries `routine_run_id` as the `correlation_id` so a future routine engine can join attention writes to its `RoutineRunRecord` lineage.
- `world/kernel.py`: new `attention: AttentionBook` field; the standard `__post_init__` wiring shares the kernel's ledger and clock with the book.
- `tests/test_attention.py`: 102 tests covering field validation for all three record types, CRUD + duplicate rejection for each, every filter listing, the disabled-by-default rule for profiles, the "multiple profiles per actor" rule from §44.4, the recommended status vocabulary (`"completed"` / `"partial"` / `"degraded"` / `"empty"`), the `priority_weights` numeric-only rule (rejects `bool`, accepts `int` / `float`), the `profile_matches_menu` shape and behavior on overlap / no overlap / unknown profile / unknown menu, snapshot determinism with separate enabled / disabled counts, ledger emission of all three new `RecordType` members (with `correlation_id` carrying `routine_run_id` on selections), kernel wiring, and a no-mutation guarantee against every other v0/v1 source-of-truth book including `InteractionBook` and `RoutineBook`.

### 47.2 The `profile_matches_menu` predicate

`AttentionBook.profile_matches_menu(profile_id, menu_id) -> dict` returns a **structural overlap summary** between an `AttentionProfile` and an `ObservationMenu` without inferring economic meaning. The dict has:

- `profile_id`, `menu_id` — echoed back for the caller.
- `has_any_overlap` (`bool`) — `True` if any of the dimensions below is non-empty *and* the menu carries at least one available item in that dimension.
- `per_dimension` (`dict[str, dict]`) — for each (watched-dimension, menu-field) pair where the profile's watched filter is non-empty, a sub-dict with `watched_count` and `menu_available_count`.

The predicate intentionally does **not** check whether each available id has a *type* matching the profile's filter — that requires reading the underlying record books and is deferred to the v1.8.6 engine layer. The summary is conservative: it tells the caller "is there structural potential for overlap?" not "are these specific records relevant?"

`UnknownAttentionProfileError` / `UnknownObservationMenuError` are raised on missing ids; the predicate reads both books and mutates neither.

### 47.3 Boundaries

§47 is a storage + lookup milestone. v1.8.5 does **not** add:

- Routine execution. The Routine engine that consumes selections to produce `RoutineRunRecord` entries lands at v1.8.6.
- Automatic menu construction. Callers build `ObservationMenu` instances by hand (or via future v1.8.6+ helpers); v1.8.5 stores what is given.
- Selection logic. Callers build `SelectedObservationSet` instances by hand; v1.8.5 stores what is given. Selection rules — recency, priority-top-K, profile-driven match — are v1.8.6+ engine concerns.
- Concrete routines. Corporate quarterly reporting / valuation refresh / bank review / investor review / etc. are v1.8.7+.
- Subset enforcement. `SelectedObservationSet.selected_refs` is **not** required to be a subset of the menu's `available_*_ids`. v1.8.5 documents this and persists what the caller gives. Engine layers may enforce it.
- Price formation, trading, lending decisions, corporate actions, policy reaction functions, Japan calibration, real data, or any external-shock scenario engine. All v1.7 / v1.8.1 / v1.8.2 / v1.8.3 / v1.8.4 prohibitions are inherited.

Cross-references (`actor_id`, `attention_profile_id`, `menu_id`, `routine_run_id`, `selected_refs`, `skipped_refs`, `available_*_ids`) are recorded as data and **not** validated for resolution against any other book, per the v0 / v1 cross-reference rule.

### 47.4 v1.8.5 success criteria

§47 is complete when **all** hold:

1. `world/attention.py`, the three new ledger types, and the `attention` kernel field exist and behave per §47.1.
2. `tests/test_attention.py` passes (102 tests).
3. The full test suite passes (949 tests = 847 prior + 102 attention).
4. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
5. No existing test was modified; no existing record shape, book API, scheduler extension, or ledger record type was altered.
6. `AttentionBook` does not mutate any other v0 / v1 source-of-truth book — verified by an explicit no-mutation test that exercises every read + write API and asserts every other book's snapshot is byte-identical before and after.

### 47.5 Revised v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.1 Endogenous Reference Dynamics | Design (§43). | Shipped |
| v1.8.2 Interaction Topology + Attention | Design (§44). | Shipped |
| v1.8.3 InteractionBook + Tensor View | Code (§45). | Shipped |
| v1.8.4 RoutineBook + RoutineRunRecord | Code (§46). | Shipped |
| **v1.8.5 AttentionProfile + ObservationMenu + SelectedObservationSet** | Code (§47). Storage + lookup only. | **Shipped** |
| v1.8.6 Routine engine (execution) | Code. Schedule-and-fire wiring that consumes routines + attention to produce `RoutineRunRecord` entries automatically. | Next |
| v1.8.7 Corporate Reporting Routine | First concrete routine using `corporate_quarterly_reporting` on the diagonal `Corporate → Corporate` channel. | After v1.8.6 |
| v1.8.8 Investor + Bank Attention Demo | Two more concrete routines using heterogeneous attention. | After v1.8.7 |
| v1.9 Living Reference World Demo | Year-long run with no external observation; non-empty ledger on every reporting / review cycle. | After v1.8.8 |

## 48. v1.8.6 Routine Engine Plumbing

§48 (v1.8.6) implements the *thin execution service* that turns a `RoutineExecutionRequest` plus selected observation records (§47) into one auditable `RoutineRunRecord` (§46), validating interaction compatibility against the topology (§45) along the way. The engine is **plumbing, not behavior**: it generates no signals, valuations, prices, contracts, ownership changes, or economic actions. It does not hook into `tick()` / `run()`.

### 48.1 What lands in v1.8.6

- `world/routine_engine.py`:
  - `RoutineExecutionRequest` immutable dataclass: `request_id`, `routine_id`, `as_of_date?`, `phase_id?`, `interaction_ids`, `selected_observation_set_ids`, `explicit_input_refs`, `output_refs`, `status?`, `metadata`. The two reserved metadata keys `parent_record_ids` and `run_id` are honored if present.
  - `RoutineExecutionResult` immutable dataclass: mirrors the resulting `RoutineRunRecord` plus `request_id` for caller-side correlation.
  - `RoutineEngine` service: `execute_request(request) -> RoutineExecutionResult`, `validate_request(request) -> dict`, `collect_selected_refs(selected_observation_set_ids) -> tuple[str, ...]`. Constructed with `RoutineBook`, `InteractionBook`, `AttentionBook`, optional `Clock`. Stateless beyond its references to those books.
  - Errors: `RoutineExecutionError` (base), `RoutineExecutionValidationError`, `RoutineExecutionMissingDateError`, `RoutineExecutionIncompatibleInteractionError`, `RoutineExecutionUnknownSelectionError`.
- `world/kernel.py`: new `routine_engine: RoutineEngine | None = None` field, constructed in `__post_init__` from the kernel's `routines` / `interactions` / `attention` / `clock` if not already supplied. The standard `tick()` / `run()` paths are unchanged — execution is caller-initiated only.
- `tests/test_routine_engine.py`: 50 tests covering request validation, execute happy path, result-mirrors-stored-record contract, default `run_id` format (`"run:" + request_id`) and metadata override, date defaulting (request → clock → controlled error), selected-ref collection (concatenation order; unknown selection raises), explicit + selected combine deterministically with first-occurrence dedup, status semantics (default `"completed"` with inputs / `"degraded"` without; explicit override preserved), interaction compatibility (compatible passes; not-in-allowed-list raises; not-admitting-routine-type raises; unknown-interaction fails execution), attention compatibility (unknown selection raises; subset-of-menu NOT enforced per v1.8.5), unknown-routine raises, disabled-routine rejected, `parent_record_ids` flow from metadata to record, `selected_observation_set_ids` stored under run record's `metadata`, `validate_request` returns the same shape the engine uses internally and raises the same controlled errors as `execute_request`, `RoutineBook` ledger emits exactly one `routine_run_recorded` per request, kernel exposes the engine, `tick()` and `run()` do not auto-execute, no-mutation guarantee against every other v0/v1 source-of-truth book, and the error hierarchy.

### 48.2 Execution semantics

The engine validates → resolves → writes:

1. **Resolve routine.** Look up `request.routine_id` in `RoutineBook`. Unknown id → `RoutineExecutionValidationError`. Disabled routine → `RoutineExecutionValidationError` (v1.8.6 chooses *reject* over *allow*).
2. **Resolve as-of date.** `request.as_of_date` if supplied; else `clock.current_date`; else `RoutineExecutionMissingDateError`.
3. **Validate interactions.** For each `interaction_id` in `request.interaction_ids`, call `RoutineBook.routine_can_use_interaction(routine_id, interaction_id, interactions)`. The v1.8.4 predicate returns `False` on unknown ids; the engine treats that as a fatal `RoutineExecutionIncompatibleInteractionError` so the failure is loud (the engine cannot execute against a channel that does not exist).
4. **Collect selected refs.** Walk `selected_observation_set_ids`, look each up in `AttentionBook`, concatenate `selected_refs` in input declaration order. Unknown selection → `RoutineExecutionUnknownSelectionError`. Subset-of-menu is **not** enforced (per v1.8.5's documented decision).
5. **Resolve input refs.** `final = dedupe(explicit_input_refs ++ collected_selected_refs)` with first-occurrence ordering. v1.8.6 documents this as the engine's canonical input shape.
6. **Compute status.** Explicit `request.status` wins. Otherwise default to `"completed"` if resolved input refs are non-empty, `"degraded"` if empty (v1.8.1 anti-scenario discipline — a run with no inputs is *degraded*, not *failed*).
7. **Build the run record.** Reserved metadata keys (`parent_record_ids`, `run_id`) are pulled out; `metadata["selected_observation_set_ids"]` is set; `RoutineRunRecord.routine_type` and `owner_space_id` are denormalized from the spec.
8. **Persist.** `RoutineBook.add_run_record(record)` writes the record and emits `ROUTINE_RUN_RECORDED` through its existing ledger path. The engine adds **no other ledger writes**.

### 48.3 Boundaries

§48 is plumbing. v1.8.6 does **not** add:

- Concrete routines. Corporate reporting / valuation refresh / bank review / investor review / etc. are v1.8.7+.
- Automatic menu construction. Menus arrive on `AttentionBook` already built (per v1.8.5).
- Selection logic. Selections arrive on `AttentionBook` already chosen.
- Signal generation, valuation generation, price formation, trading, lending decisions, corporate actions, policy reaction functions, Japan calibration, real data, or any external-shock scenario engine. All v1.7 / v1.8.1 / v1.8.2 / v1.8.3 / v1.8.4 / v1.8.5 prohibitions are inherited.
- Scheduler integration. `RoutineSpec.frequency` is still a label only; nothing in the engine registers or fires tasks against the scheduler.

The engine writes only to `RoutineBook` and only via `add_run_record`. Cross-references on the request (`interaction_ids`, `selected_observation_set_ids`) are validated for existence; other ids (`explicit_input_refs`, `output_refs`, `parent_record_ids`) are recorded as data, per the v0 / v1 cross-reference rule.

### 48.4 v1.8.6 success criteria

§48 is complete when **all** hold:

1. `world/routine_engine.py` and the `routine_engine` kernel field exist and behave per §48.1 / §48.2.
2. `tests/test_routine_engine.py` passes (50 tests).
3. The full test suite passes (999 tests = 949 prior + 50 engine).
4. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
5. No existing test was modified; no existing record shape, book API, scheduler extension, or ledger record type was altered.
6. The engine does not mutate any other v0 / v1 source-of-truth book — verified by an explicit no-mutation test.
7. `kernel.tick()` and `kernel.run(days=N)` do not execute routines automatically — verified by tests that exercise both paths against a populated kernel and assert zero `RoutineRunRecord` entries land.

### 48.5 Revised v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.1 Endogenous Reference Dynamics | Design (§43). | Shipped |
| v1.8.2 Interaction Topology + Attention | Design (§44). | Shipped |
| v1.8.3 InteractionBook + Tensor View | Code (§45). | Shipped |
| v1.8.4 RoutineBook + RoutineRunRecord | Code (§46). | Shipped |
| v1.8.5 AttentionProfile + ObservationMenu + SelectedObservationSet | Code (§47). | Shipped |
| **v1.8.6 Routine Engine plumbing** | Code (§48). | **Shipped** |
| v1.8.7 Corporate Reporting Routine | First concrete routine using `corporate_quarterly_reporting` on the diagonal `Corporate → Corporate` channel. | Next |
| v1.8.8 Investor + Bank Attention Demo | Two more concrete routines using heterogeneous attention. | After v1.8.7 |
| v1.9 Living Reference World Demo | Year-long run with no external observation; non-empty ledger on every reporting / review cycle. | After v1.8.8 |

## 49. v1.8.7 Corporate Quarterly Reporting Routine

§49 (v1.8.7) ships **the first concrete endogenous routine** on top of the v1.8.3 / v1.8.4 / v1.8.5 / v1.8.6 substrate. The routine is intentionally narrow: a Corporate → Corporate self-loop that produces one synthetic quarterly reporting `InformationSignal` per call, through the existing `RoutineEngine` and `SignalBook` plumbing. No economic computation, no investor reaction, no price formation, no scheduler integration.

§49 is the first place in the project where an actor "does something" on its own schedule cycle without being shocked into action. It validates that the §43 (v1.8.1) endogenous-dynamics direction can produce a real ledger trace using only the existing primitives — no special new API needed for one routine to exist.

### 49.1 What lands in v1.8.7

- `world/reference_routines.py` (new module):
  - Three module constants establishing the v1.8.7 controlled vocabulary:
    - `CORPORATE_REPORTING_INTERACTION_ID = "interaction:corporate.reporting_preparation"` — the shared self-loop channel id.
    - `CORPORATE_QUARTERLY_REPORTING_ROUTINE_TYPE = "corporate_quarterly_reporting"` — the routine_type string.
    - `CORPORATE_REPORTING_SIGNAL_TYPE = "corporate_quarterly_report"` — the produced signal's `signal_type`. Distinct from the v1.8.2 design's `"earnings_disclosure"` watched-type because v1.8.7 does **not** compute earnings — it publishes a synthetic report.
    - `CORPORATE_REPORTING_SOURCE_ID = "source:corporate_self_reporting"` — synthetic source id; not a real news outlet or filing system.
  - `register_corporate_reporting_interaction(kernel) -> InteractionSpec` — idempotent registration of the self-loop channel. `routine_types_that_may_use_this_channel` is locked to `("corporate_quarterly_reporting",)`.
  - `register_corporate_quarterly_reporting_routine(kernel, *, firm_id, routine_id=None) -> RoutineSpec` — idempotent per-firm registration. `frequency="QUARTERLY"`, `phase_id="post_close"`, `missing_input_policy="degraded"`, `allowed_interaction_ids` contains the corporate-reporting channel.
  - `run_corporate_quarterly_reporting(kernel, *, firm_id, ...) -> CorporateReportingResult` — the routine itself.
  - `CorporateReportingResult` immutable dataclass carrying the engine result + the produced signal, with `run_id` / `signal_id` / `routine_id` / `as_of_date` / `status` properties for caller convenience.
- `tests/test_corporate_reporting_routine.py`: 26 tests covering the three helpers + the end-to-end flow + boundaries (see §49.4 for the test inventory).

The v1.8.7 module is **additive only**. No `world/` infrastructure module, no `spaces/` file, and no existing test is changed. The kernel's `__post_init__` is not modified — registration is caller-driven, mirroring how v1.8.6 made execution caller-driven.

### 49.2 Execution flow

The helper composes the existing primitives in a single call:

```
run_corporate_quarterly_reporting(kernel, firm_id="firm:reference_manufacturer_a")

  1. Resolve as_of_date (argument > kernel.clock).
  2. Build RoutineExecutionRequest:
       - routine_id   = "routine:corporate_quarterly_reporting:<firm_id>"
       - request_id   = "req:routine:corporate_quarterly_reporting:<firm_id>:<date>"
       - interaction_ids = (CORPORATE_REPORTING_INTERACTION_ID,)
       - explicit_input_refs = (firm_id,)        # default; pass () for degraded
       - output_refs        = (signal_id,)
  3. kernel.routine_engine.execute_request(request)
       -> writes one RoutineRunRecord
       -> emits one routine_run_recorded ledger entry
  4. Build InformationSignal:
       - signal_id    = "signal:corporate_quarterly_report:<firm_id>:<date>"
       - signal_type  = "corporate_quarterly_report"
       - subject_id   = firm_id
       - source_id    = "source:corporate_self_reporting"
       - related_ids  = (run_id,)                # back-link to the run
       - metadata     = {"routine_run_id": run_id, "routine_type": ..., "interaction_id": ...}
       - payload      = synthetic toy fields (see §49.3)
  5. kernel.signals.add_signal(signal)
       -> writes the signal to SignalBook
       -> emits one signal_added ledger entry
```

Two ledger entries land per call, in this order: `routine_run_recorded`, then `signal_added`. The pairing is reconstructable from the ledger alone via the `related_ids` back-link on the signal and the `output_refs` forward-link on the run record.

### 49.3 Synthetic signal payload

The signal's `payload` carries a small set of toy fields:

```
firm_id            : str    — the subject
reporting_period   : str    — ISO YYYY-MM-DD (= as_of_date)
revenue_index      : float  — toy, default 100.0
margin_index       : float  — toy, default 0.10
leverage_hint      : float  — toy, default 1.0
liquidity_hint     : float  — toy, default 1.0
confidence         : float  — toy, default 1.0
statement          : str    — "synthetic quarterly reporting signal"
```

These values are illustrative round numbers chosen for traceability. **They are not computed from any balance sheet, price book, valuation book, external observation, or other source-of-truth book.** v1.8.7 explicitly does not implement economic computation. Callers may override the defaults to publish different toy values; future v2 calibration will populate the same fields from public Japan data without altering the routine's structural shape.

### 49.4 Test coverage

`tests/test_corporate_reporting_routine.py` (26 tests):

- Registration helpers: idempotent re-registration of both interaction and routine; correct self-loop / channel-type / `routine_types_that_may_use_this_channel` shape; per-firm routine metadata; `firm_id` rejection on empty.
- Run helper happy path: exactly one `RoutineRunRecord` created per call; exactly one `InformationSignal` published; signal back-references the run via `related_ids` and `metadata["routine_run_id"]`; run record forward-references the signal via `output_refs`; the run uses the corporate self-loop interaction (`source_space_id == target_space_id == "corporate"`).
- Synthetic payload fields preserved verbatim; default `status="completed"` when inputs present; `status="degraded"` when `explicit_input_refs=()` (v1.8.1 anti-scenario discipline).
- Date semantics: defaults to clock; explicit override honored.
- Compatibility failures: missing interaction → `RoutineExecutionIncompatibleInteractionError`; missing routine spec → engine raises `RoutineExecutionValidationError`; both surfaced loudly.
- Ledger ordering: exactly two new ledger entries land per call, in the order `routine_run_recorded` then `signal_added`, with matching `object_id`s.
- No-mutation guarantee against `OwnershipBook` / `ContractBook` / `PriceBook` / `ConstraintBook` / `ValuationBook` / `InstitutionBook` / `ExternalProcessBook` / `RelationshipCapitalBook`.
- Auto-execution prohibition: `kernel.tick()` and `kernel.run(days=N)` produce zero new run records and zero new signals — the routine is caller-initiated only.
- Synthetic-only identifiers: the signal's `signal_id` / `source_id` / `payload` / `metadata` and every module constant are walked for the v1.7-public-rc1 forbidden-token list and asserted clean.
- Multi-firm and multi-period scaling: distinct firms get distinct routines and signals; the same firm across two quarters produces two distinct run records under one routine spec.

### 49.5 Boundaries

§49 is the *first* concrete routine. It is also the *narrowest* possible one. v1.8.7 explicitly does **not**:

- Trigger investor reactions, bank reviews, valuation refreshes, or any other downstream routine. The signal sits in `SignalBook`; nothing reads it.
- Update prices, ownership, contracts, balance sheets, valuations, constraints, relationships, institutions, or external processes.
- Compute revenue, margin, leverage, liquidity, or any other economic metric. The payload's "indices" and "hints" are toy values.
- Hook into the scheduler. Caller invokes the routine; nothing fires it automatically.
- Implement or imply Japan calibration. All identifiers and source labels are synthetic; the synthetic-only identifier test enforces this at runtime.
- Call user-defined callbacks, attention selection logic, or automatic menu construction. The v1.8.5 attention layer is not wired into v1.8.7 — the routine simply passes its own `firm_id` as an explicit input ref.

The sole writes per call are: one `RoutineRunRecord` (via `RoutineBook.add_run_record`) and one `InformationSignal` (via `SignalBook.add_signal`). Reviewers should reject any v1.8.x PR that adds writes outside this set under the v1.8.7 helper.

### 49.6 v1.8.7 success criteria

§49 is complete when **all** hold:

1. `world/reference_routines.py` exists and behaves per §49.1 / §49.2.
2. `tests/test_corporate_reporting_routine.py` passes (26 tests).
3. The full test suite passes (1025 tests = 999 prior + 26 corporate-reporting).
4. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
5. No existing test was modified; no existing record shape, book API, scheduler extension, or ledger record type was altered.
6. The two new ledger entries (`routine_run_recorded` then `signal_added`) appear in that order per call, and the signal's `related_ids` contain the run's `run_id` — verified by an explicit ordering test.
7. `kernel.tick()` and `kernel.run(days=N)` do not auto-execute the routine — verified by tests that exercise both paths against a populated kernel and assert zero run records and zero signals appear.

### 49.7 Position in the v1.8.x sequence

v1.8.7 is the v1.8.x line's **first economically-suggestive output** — but it is suggestive only. The signal exists; nothing reads it. The next two milestones make it useful:

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.1 Endogenous Reference Dynamics | Design (§43). | Shipped |
| v1.8.2 Interaction Topology + Attention | Design (§44). | Shipped |
| v1.8.3 InteractionBook + Tensor View | Code (§45). | Shipped |
| v1.8.4 RoutineBook + RoutineRunRecord | Code (§46). | Shipped |
| v1.8.5 AttentionProfile + ObservationMenu + SelectedObservationSet | Code (§47). | Shipped |
| v1.8.6 Routine Engine plumbing | Code (§48). | Shipped |
| **v1.8.7 Corporate Quarterly Reporting Routine** | Code (§49). First concrete routine; Corporate → Corporate self-loop. | **Shipped** |
| v1.8.8 Reference Variable Layer — Design | Design (§50). Names the universe of observable world-context variables. | Next |
| v1.8.9 `WorldVariableBook` / `IndicatorBook` | Code. | After v1.8.8 |
| v1.8.10 Exposure / Dependency Layer | Code. | After v1.8.9 |
| v1.8.11 `ObservationMenu` builder | Code. | After v1.8.10 |
| v1.8.12 Investor + Bank Attention Demo | Code. The first place where two heterogeneous actors looking at the same variable layer produce structurally different ledger traces. | After v1.8.11 |
| v1.9 Living Reference World Demo | Year-long run on the routine + topology + attention + variable stack with no external observation; non-empty ledger on every reporting / review cycle. | After v1.8.12 |

## 50. v1.8.8 Reference Variable Layer — Design

§50 (v1.8.8) names the universe of observable world-context variables that future routines will read: macro, financial, material, energy, technology, real-estate, labor, logistics, and expectation/narrative measures. The full design is in [`v1_reference_variable_layer_design.md`](v1_reference_variable_layer_design.md).

§50 is **design-only**. No `world/`, `spaces/`, `examples/`, or `tests/` file is changed. The constitutional log entry below summarises the principle and the proposed record shapes; v1.8.9 is the implementation milestone.

### 50.1 Core principle

> Reference variables are observable world-context variables. They are not scenarios and not shocks by default. Their presence does not drive behavior automatically. Their absence does not silence routines.

The v1.8.7 reporting routine writes a signal that nothing reads. v1.8.12's investor + bank demo will be the first place where heterogeneous attention against a shared world produces structurally different ledger traces — but the demo needs *something to watch*. §50 names that something.

§50 does **not** introduce a scenario engine, a stochastic process driver, or a calibrated macro model. Reference variables are *names* (specs) and *data points* (observations). The v1.8.1 anti-scenario discipline cascades through unchanged: a routine that becomes silent because no variable observation is "interesting enough" has slipped back into scenario-driven mode and should be rejected at review.

### 50.2 Distinction from existing books

| Book / view | Answers |
| --- | --- |
| `PriceBook` (v0.4) | "What was the last priced observation for this asset?" |
| `SignalBook` (v0.7) | "What information events have been published?" |
| `ValuationBook` (v1.1) | "What value claim did *this valuer* make about *this subject*?" |
| `ExternalProcessBook` (v1.4) | "How does this external factor evolve, and what observations did its process produce?" |
| `ConstraintEvaluator` (v0.6) | "Does this agent currently breach this constraint?" |
| **`ReferenceVariableBook`** (v1.8.9) | **"What is the released value of this named world-context variable, and what is its release / vintage history?"** |

Each existing book owns one distinct kind of fact. v1.8.9 introduces a new kind ("released world-context variables with vintages") that does not fit any existing book's shape, so it gets its own.

### 50.3 Proposed record shapes

`ReferenceVariableSpec` — static declaration of one variable. Proposed fields:

`variable_id`, `variable_name`, `variable_group`, `variable_type`, `source_space_id`, `canonical_unit`, `frequency`, `observation_kind`, `default_visibility`, `expected_release_lag_days?`, `metadata`.

`VariableObservation` — one data point per (variable, period, vintage). Proposed fields:

`observation_id`, `variable_id`, `as_of_date`, `observation_period_start?`, `observation_period_end?`, `release_date?`, `vintage_id?`, `revision_of?`, `value`, `unit`, `source_id`, `confidence`, `metadata`.

The four time-ish fields exist to **prevent look-ahead bias**: `observation_period_start` / `observation_period_end` describe *what the observation says*; `as_of_date` / `release_date` describe *when the observation became visible to agents*; `vintage_id` distinguishes multiple observations of the same `(variable, period)`; `revision_of` links each vintage to the prior so the revision history is reconstructable from the ledger alone.

A v1.8.11 `ObservationMenu` builder must filter out observations whose `as_of_date` is later than the menu's `as_of_date`. Otherwise a routine looking at "what did the bank know on 2026-03-31?" would see the 2026Q1 CPI release that lands on 2026-04-15 — the canonical look-ahead-bias mistake.

### 50.4 Variable groups

13 controlled-vocabulary groups: `real_activity`, `inflation`, `rates`, `fx`, `credit`, `financial_market`, `material`, `energy_power`, `logistics`, `real_estate`, `labor`, `technology`, `expectations_narratives`. The full list with examples and attachment-point notes for material / energy / technology transmission is in `v1_reference_variable_layer_design.md` §"Variable groups" / §"Material / energy / technology — transmission attachment points".

### 50.5 Relation to attention, topology, routine

- **Attention.** Future v1.8.10+ work may extend `AttentionProfile` with `watched_variable_ids` and `watched_variable_groups`. Until then, `watched_metrics` bridges.
- **Topology.** Interaction channels may *carry* variable observations as their content; the topology stays about channels, not scenarios. There is no v1.8.x mechanism that says "when a variable moves by N percent, publish through this channel" — that would re-introduce scenario-driven dynamics.
- **Routine.** Consumption is read-only; absence is partial / degraded; no look-ahead. A v1.8.11 menu builder enforces the look-ahead filter; routines that bypass the menu and query the variable book directly are responsible for applying the same filter.

### 50.6 Boundaries

§50 is infrastructure for *context*. It is not a GDP / CPI / rate calculator; not a forecaster; not a rate-setting engine; not a commodity / power / technology-diffusion simulator; not a policy reaction engine; not a price formation / trading / lending mechanism; not Japan calibration; not a real-data ingestion harness; not automatic economic behavior of any kind. v2 (Japan public) and v3 (Japan proprietary) populate the same shapes with real data; v1.8.x stays neutral.

### 50.7 Revised v1.8.x sequence (post-v1.8.7)

| Milestone | Scope | Status |
| --- | --- | --- |
| **v1.8.8 Reference Variable Layer — Design** | §50. | **(this design milestone)** |
| v1.8.9 `WorldVariableBook` / `IndicatorBook` | Code: `ReferenceVariableSpec` + `VariableObservation` + revision history + `list_released_as_of(...)` helper. | Next |
| v1.8.10 Exposure / Dependency Layer | Code: per-actor exposure declarations distinct from attention. | After v1.8.9 |
| v1.8.11 `ObservationMenu` builder | Code: helpers that build `ObservationMenu` automatically with look-ahead filtering. | After v1.8.10 |
| v1.8.12 Investor + Bank Attention Demo | Code: two concrete routines reading the variable layer through heterogeneous attention. | After v1.8.11 |
| v1.9 Living Reference World Demo | Year-long run on the full stack with no external observation. | After v1.8.12 |

### 50.8 v1.8.8 success criteria

§50 is complete when **all** hold:

1. `docs/v1_reference_variable_layer_design.md` exists and contains the principle, the distinction from existing books, the proposed `ReferenceVariableSpec` and `VariableObservation` field sets, the look-ahead / vintage / revision rationale, the 13 variable groups, the example variable ids, the material / energy / technology attachment points, the relation-to-attention / -topology / -routine sections, the boundaries, and the revised milestone sequence.
2. `docs/v1_endogenous_reference_dynamics_design.md` and `docs/v1_interaction_topology_design.md` carry sequence-revision notes pointing at v1.8.9 / v1.8.10 / v1.8.11 / v1.8.12 as the build path to the v1.8.12 demo and v1.9 closing milestone.
3. This section (§50) records the design in the constitutional log.
4. No `world/`, `spaces/`, `examples/`, or `tests/` file is modified. The 1025-test baseline is unchanged.
5. v1.8.9 reviewers can land `WorldVariableBook` against the proposed shapes without re-litigating either the look-ahead-bias rule or the anti-scenario discipline.

## 50.1 v1.8.8 hardening — anchoring variables to spaces, channels, and exposures

§50.1 is a **hardening update** to the v1.8.8 design that closed §50. The original design risked producing *disembodied global state*: a `ReferenceVariableBook` read by any routine, with no anchoring to spaces, no anchoring to interaction channels, and no anchoring to who actually depends on the variable, would re-introduce the scenario-driven failure mode through a side door — every routine would consult a global "macro environment" object and pretend that was endogenous. §50.1 closes that door.

The full hardening is in [`v1_reference_variable_layer_design.md`](v1_reference_variable_layer_design.md) under "Hardening — anchoring variables to spaces, channels, and exposures". The constitutional summary:

### 50.1.1 Conceptual classification

A `ReferenceVariable` is **not** an `Agent`, **not** a `Space`, **not** a `Scenario`, **not** a `Shock`, and **not** a `PriceBook` replacement. It **is** a *world-context / field / substrate variable* observable by agents through routines and interaction channels.

### 50.1.2 The three required hooks

Every `ReferenceVariableSpec` must declare three hooks by construction:

1. **Source hook** — which space / source publishes or observes the variable (`source_space_id`, optional `source_id`).
2. **Scope hook** — which spaces / sectors / subjects / asset classes the variable is relevant to (`related_space_ids`, `related_subject_ids`, `related_sector_ids`, `related_asset_class_ids`, `observability_scope`, `typical_consumer_space_ids`).
3. **Exposure hook** — which agents / assets / contracts / sectors are economically dependent on the variable (lives in v1.8.10 `ExposureRecord`; the spec just names the scope it resolves against).

Without all three, a variable is a free-floating global driver. v1.8.9 implementations should reject specs that fail any hook.

### 50.1.3 Updated record-shape additions

`ReferenceVariableSpec` adds (relative to the original §50.3 list): `source_id?`, `related_space_ids`, `related_subject_ids`, `related_sector_ids`, `related_asset_class_ids`, `observability_scope`, `typical_consumer_space_ids`.

`VariableObservation` adds: `observed_by_space_id?`, `published_by_source_id?` (renames the original `source_id`), `carried_by_interaction_id?`. The `as_of_date` field is clarified as the **canonical visibility timestamp** that the v1.8.11 menu builder must filter on (not `observation_period_*`, not `release_date` when both exist).

### 50.1.4 Variables in the `S × S × C` topology

Variable observations may be **carried** through `InteractionSpec` channels. The topology stays about *which channels are possible*; the variable layer stays about *what world-context values currently are*. Five illustrative channels (full table in the design doc):

- `external → information` (`commodity_feed`)
- `information → investors` (`macro_data_release`)
- `information → banking` (`credit_monitoring_data`)
- `policy → investors` (`policy_rate_announcement`)
- `real_estate → banking` (`collateral_market_update`)

The interaction tensor must **not** become a shock tensor. A v3 calibration that wants automatic signal-on-shock behavior puts that inside a routine, not as a hidden side effect of the variable layer.

### 50.1.5 Responsibility chain — five record types, no global driver

```
ReferenceVariableSpec    — what variable EXISTS
VariableObservation      — what value was OBSERVED and WHEN
ExposureRecord           — who DEPENDS on it (v1.8.10)
AttentionProfile         — who WATCHES it (v1.8.5)
Routine                  — when it is REVIEWED (v1.8.4 / v1.8.6 / v1.8.7)
```

Each step is opt-in. A variable does not auto-affect any exposed actor; an exposed actor does not auto-watch the variable; a watching actor does not auto-fire a routine when the variable moves. Each link requires explicit data.

### 50.1.6 Hard boundary — the four gates

A variable observation only matters when **all four** gates are satisfied: visibility (date / release / vintage filter), availability (channel or menu), selection (`AttentionProfile` selects it), consumption (`Routine` reads it via `input_refs`). A routine that fires solely because a variable crossed a threshold has bypassed gate 4 — that is scenario-driven and must be rejected at review.

### 50.1.7 v1.8.8 hardening success criteria

§50.1 is complete when **all** hold:

1. `docs/v1_reference_variable_layer_design.md` carries the "Hardening — anchoring variables to spaces, channels, and exposures" section with the conceptual classification, the three hooks, the updated spec / observation field discussions, the channel examples, the responsibility chain, the four transmission examples (oil / electricity / AI / interest rates), the four-gate hard boundary, and the anti-scenario-discipline restatement.
2. This section (§50.1) records the hardening in the constitutional log.
3. No `world/`, `spaces/`, `examples/`, or `tests/` file is modified. The 1025-test baseline is unchanged.
4. v1.8.9 reviewers reading the hardened design can answer "where does this variable hook into spaces, channels, and exposures?" before they touch any code.

## 51. v1.8.9 WorldVariableBook

§51 (v1.8.9) implements the v1.8.8 design + hardening as a kernel-level book. `WorldVariableBook` stores `ReferenceVariableSpec` records (what variables exist, with explicit source / scope / channel hooks) and `VariableObservation` records (what value was observed and when, with explicit visibility / vintage / revision metadata). It does **not** calculate macro variables, simulate commodity / power / technology dynamics, trigger routines, or perform Japan calibration. Cross-references are stored as data; the v0/v1 cross-reference rule holds.

§51 is the storage milestone for the §50 / §50.1 design. The v1.8.10 Exposure / Dependency Layer, the v1.8.11 ObservationMenu builder, and the v1.8.12 Investor + Bank Attention Demo will read this book; v1.8.9 only stores.

### 51.1 What lands in v1.8.9

- `world/variables.py`:
  - `ReferenceVariableSpec` immutable dataclass with the 18 fields in §50.1.3 (the original §50.3 set + the hardening additions). Required: `variable_id`, `variable_name`, `variable_group`, `variable_type`, `source_space_id`, `canonical_unit`, `frequency`, `observation_kind`, `default_visibility`, `observability_scope`. Optional / tuple / metadata fields per §50.1.3.
  - `VariableObservation` immutable dataclass with the 16 fields in §50.1.3. Required: `observation_id`, `variable_id`, `as_of_date`, `value`, `unit`. Optional period / release / visibility / vintage / revision / anchoring / metadata fields. `value` accepts `int | float | str | None` (qualitative and quantitative). `confidence` validated in `[0.0, 1.0]`.
  - `VariableObservation.visibility_date` — derived property returning `visible_from_date if present else as_of_date`. The v1.8.8 hardening's gate-1 visibility filter uses this property.
  - `WorldVariableBook` append-only store: `add_variable`, `get_variable`, `list_variables`, `list_variables_by_group`, `list_variables_by_source_space`, `list_variables_by_related_space`, `list_variables_by_consumer_space`, `add_observation`, `get_observation`, `list_observations` (with optional `variable_id` arg), `list_observations_by_variable`, `list_observations_by_as_of_date`, `list_observations_visible_as_of`, `list_observations_carried_by_interaction`, `latest_observation` (with optional `as_of_date` for look-ahead-bias-free lookup), `snapshot`.
  - Errors: `VariableError` (base), `DuplicateVariableError`, `DuplicateVariableObservationError`, `UnknownVariableError`, `UnknownVariableObservationError`.
- `world/ledger.py`: two new `RecordType` members:
  - `VARIABLE_ADDED = "variable_added"`
  - `VARIABLE_OBSERVATION_ADDED = "variable_observation_added"`
  `add_variable` / `add_observation` write the corresponding entry when a ledger is wired. The observation ledger entry uses `simulation_date = observation.as_of_date` and carries `correlation_id = carried_by_interaction_id` so a future routine engine can join variable observations to interaction-channel lineage.
- `world/kernel.py`: new `variables: WorldVariableBook` field; the standard `__post_init__` wiring shares the kernel's ledger and clock with the book.
- `tests/test_variables.py`: 91 tests covering field validation for both record types (parametrized rejection of empty required strings, empty entries in tuple fields, non-numeric / out-of-bounds / bool-typed `confidence`), date coercion on every date field, frozen dataclass immutability, `to_dict` round-trip; CRUD with duplicate rejection for both records; every filter listing for variables (by group / source space / related space / consumer space) and observations (by variable / as_of_date / visibility / channel); the visibility-filter rule (`visible_from_date` overrides `as_of_date` when present, in either direction — earlier or later); `latest_observation` deterministic tiebreaker (visibility_date desc → as_of_date desc → observation_id desc); `latest_observation` returns `None` when nothing is visible; vintage / revision storage; cross-reference rule (`variable_id` on observation NOT validated against the variables store); snapshot determinism with separate counts; ledger emission of both new record types (with `simulation_date` from the observation and `correlation_id` from the channel); kernel wiring; no-mutation guarantee against every other v0/v1 source-of-truth book; and the auto-execution prohibition (`tick()` / `run()` produce zero new variable / observation records).

### 51.2 Visibility semantics — the v1.8.8 hardening's gate-1

`list_observations_visible_as_of(as_of_date)` returns observations whose `visibility_date <= as_of_date`, where `visibility_date` is `visible_from_date if visible_from_date is not None else as_of_date`. ISO `YYYY-MM-DD` strings sort lexicographically the same as chronologically, so direct string comparison is correct.

`latest_observation(variable_id, as_of_date=None)` filters to a specific variable, then (when `as_of_date` is provided) applies the same visibility filter, then returns the single record with the highest `(visibility_date, as_of_date, observation_id)` tuple under reverse sort. The tiebreaker is fully deterministic — two repeated calls against the same book state always return the same record.

The book does **not** implement revision resolution beyond storing `vintage_id` and `revision_of`; "give me the latest non-superseded vintage of variable X for period Y" is a v1.8.10+ concern that may build on top of this book.

### 51.3 Naming choice

The class is `WorldVariableBook`, not `IndicatorBook`. "World variable" matches the §50.1.1 conceptual classification — a reference variable is a *world-context / field / substrate variable*, not specifically a macro indicator. Energy variables, technology indices, and qualitative narratives are first-class members of the layer; "indicator" would narrow to macroeconomic context only and obscure the AI / electricity / labor groups. The module name is `world/variables.py`.

### 51.4 Boundaries

§51 is a storage + lookup milestone. v1.8.9 does **not** add:

- A GDP / CPI / rate calculator. The book stores released figures; nothing computes them.
- A forecaster. No routine produces a forward point estimate for any variable.
- A rate-setting engine. Even with `variable:policy_rate` registered, no v1.8.x routine sets it.
- Commodity / power / technology-diffusion simulation. Variables are *values*, not markets / grids / models.
- Policy reaction logic.
- Price formation, trading, lending decisions, corporate actions.
- Japan calibration or any real-data ingestion.
- Auto-firing on `tick()` / `run()`. The book is read / written only by direct caller invocations — verified by the auto-execution-prohibition test.

The book writes only to itself + the ledger (via the existing `Ledger.append` path). Tests assert no mutation of `OwnershipBook`, `ContractBook`, `PriceBook`, `ConstraintBook`, `SignalBook`, `ValuationBook`, `InstitutionBook`, `ExternalProcessBook`, `RelationshipCapitalBook`, `InteractionBook`, `RoutineBook`, or `AttentionBook`.

### 51.5 v1.8.9 success criteria

§51 is complete when **all** hold:

1. `world/variables.py`, the two new ledger types, and the `variables` kernel field exist and behave per §51.1.
2. `tests/test_variables.py` passes (91 tests).
3. The full test suite passes (1116 tests = 1025 prior + 91 variables).
4. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
5. No existing test was modified; no existing record shape, book API, scheduler extension, or ledger record type was altered.
6. `WorldVariableBook` does not mutate any other v0 / v1 source-of-truth book — verified by the explicit no-mutation test.
7. `visible_from_date` overrides `as_of_date` for visibility filtering in both directions (earlier and later), per the v1.8.8 hardening's gate-1.

### 51.6 Position in the v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.7 Corporate Quarterly Reporting Routine | First concrete routine. | Shipped |
| v1.8.8 Reference Variable Layer — Design | Design (§50). | Shipped |
| v1.8.8 hardening — anchor variables to spaces / channels / exposures | Design (§50.1). | Shipped |
| v1.8.9 WorldVariableBook | Code (§51). Storage + lookup only. | Shipped |
| v1.8.10 Exposure / Dependency Layer | Code (§52). | Shipped |
| v1.8.11 `ObservationMenu` builder | Code (§53). Read-only join. | Shipped |
| v1.8.12 Attention Variable Hooks + Investor / Bank Attention Demo | Code (§54). Heterogeneous attention. | Shipped |
| v1.8.13 Investor / Bank Review Routines | Code (§55). Routines consume attention. | Shipped |
| v1.8.14 Endogenous Chain Harness | Code (§56). Single helper orchestrates the full chain. | Shipped |
| v1.8.15 Ledger Trace Report | Code (§57). Read-only explainability over the chain. | Shipped |
| **v1.8.16 Freeze / Readiness** | Docs only (§58). Consolidates v1.8 + plans v1.9. | **Shipped** |
| v1.9 Living Reference World Demo | Code + tests. | Next |

## 52. v1.8.10 Exposure / Dependency Layer

§52 (v1.8.10) implements the v1.8.8 hardening's **exposure hook** as a kernel-level book. `ExposureBook` records *who depends on which world variable, in what direction, with what synthetic dependency strength*. It does **not** compute impacts, calibrate sensitivities, multiply variable values by magnitudes, adjust valuations, update DSCR / LTV / leverage, or simulate transmission chains.

§52 closes the source / scope / **exposure** hook chain that §50.1 named. Together with `WorldVariableBook` (§51), the v1.8.x line now has the data shape needed for v1.8.11's `ObservationMenu` builder to surface "variables that matter to this subject" without inventing the relationship at runtime.

### 52.1 What lands in v1.8.10

- `world/exposures.py`:
  - `ExposureRecord` immutable dataclass with 14 fields per the v1.8.10 spec: `exposure_id`, `subject_id`, `subject_type`, `variable_id`, `exposure_type`, `metric`, `direction`, `magnitude`, `unit` (default `"synthetic_strength"`), `confidence` (default `1.0`), `effective_from?`, `effective_to?`, `source_ref_ids`, `metadata`. `magnitude` and `confidence` are validated in `[0.0, 1.0]` (rejecting bool which is a subclass of int). `direction` is a free-form **label** (suggested vocabulary: `"positive"` / `"negative"` / `"mixed"` / `"neutral"` / `"nonlinear"`) — the book does no sign math.
  - `ExposureRecord.is_active_as_of(as_of_date) -> bool` — open-ended bounds (`None`) are treated as `±∞`. The book's `list_active_as_of(...)` filter reuses this property.
  - `ExposureBook` append-only store with the v1.8.10 API: `add_exposure`, `get_exposure`, `list_exposures`, `list_by_subject`, `list_by_subject_type`, `list_by_variable`, `list_by_exposure_type`, `list_by_metric`, `list_by_direction`, `list_active_as_of`, `snapshot`.
  - Errors: `ExposureError` (base), `DuplicateExposureError`, `UnknownExposureError`.
- `world/ledger.py`: new `RecordType.EXPOSURE_ADDED = "exposure_added"`. `add_exposure` writes the entry when a ledger is wired; `source` carries `subject_id` and `target` carries `variable_id` so the source→target shape of a v1 ledger record matches the dependency direction.
- `world/kernel.py`: new `exposures: ExposureBook` field; the standard `__post_init__` wiring shares the kernel's ledger and clock with the book.
- `tests/test_exposures.py`: 59 tests covering field validation (parametrized rejection of empty required strings, magnitude / confidence bounds, bool rejection on numeric fields, inverted validity windows, empty entries in `source_ref_ids`); `is_active_as_of` semantics (inside / before / after / inclusive at bounds / open-ended on each side / both bounds open); date coercion; tuple normalization; frozen dataclass; `to_dict` round-trip; CRUD with `DuplicateExposureError` / `UnknownExposureError`; cross-reference rule (`variable_id` not validated against `WorldVariableBook`); every filter listing using a six-record realistic synthetic seed (food processor / property operator / bank / macro fund / electricity-intensive manufacturer / AI-exposed labor sector); `list_active_as_of` filtering with date strings and `date` objects; snapshot determinism with `exposure_count` and sorted-by-id record list; ledger emission of `EXPOSURE_ADDED`; kernel wiring (`exposures` field + shared ledger / clock); no-mutation guarantee against every other v0/v1 source-of-truth book including `InteractionBook`, `RoutineBook`, `AttentionBook`, and `WorldVariableBook`; and the auto-execution prohibition (`tick()` / `run()` produce zero new exposures).

### 52.2 Synthetic dependency strength, not calibrated sensitivity

`ExposureRecord.magnitude` is in `[0.0, 1.0]` — a **synthetic dependency strength**, not a calibrated sensitivity. v1.8.10 deliberately rejects out-of-bounds magnitudes so that v1.8.11+ consumers can rely on the bound when computing future ranking weights. v2 / v3 calibration may attach real sensitivity numbers under a different schema (e.g., `metadata["calibration_status"] = "public_data_calibrated"` plus a separate calibrated-sensitivity field), but v1.8.10 ships the synthetic shape only.

`direction` is a **label**, not arithmetic. The book stores `"positive"` / `"negative"` / `"mixed"` / `"neutral"` / `"nonlinear"` (or any other free-form string) verbatim. v1.8.11+ consumers may interpret the label; v1.8.10 does not.

### 52.3 Six illustrative exposures (the v1.8.10 spec examples)

The test seed exercises all six examples called out in the v1.8.10 task:

| Subject | Variable | Metric (transmission target) | Direction | Magnitude |
| --- | --- | --- | --- | --- |
| `firm:reference_food_processor_a` | `variable:petrochemical_input_cost` | `packaging_margin_pressure` | positive | 0.45 |
| `firm:reference_property_operator_a` | `variable:policy_rate` | `debt_service_burden` | positive | 0.7 |
| `bank:reference_bank_a` | `variable:land_price_index_reference` | `collateral_value` | positive | 0.6 |
| `investor:reference_macro_fund_a` | `variable:usd_jpy` | `portfolio_translation_exposure` | mixed | 0.4 |
| `firm:reference_electric_manufacturer_a` | `variable:electricity_price_index` | `operating_cost_pressure` | positive | 0.55 |
| `sector:reference_labor_sector_a` | `variable:automation_adoption_index` | `labor_displacement_risk` | negative | 0.3 |

These are **synthetic** records. The numbers are illustrative round figures chosen for traceability. v2 / v3 calibration may attach Japan-specific exposure data; v1.8.10 stays neutral.

### 52.4 Boundaries

§52 is a storage + lookup milestone. v1.8.10 does **not** add:

- Impact estimation. No multiplication of `magnitude` by any `VariableObservation.value`. No transmission simulation.
- Sensitivity calibration. v1.8.10 uses synthetic strengths only; v2 / v3 calibrate.
- Valuation adjustment. The book does not touch `ValuationBook`.
- DSCR / LTV / leverage updates. The book does not touch `ConstraintBook` or `BalanceSheetView`.
- Scenario engine, stochastic processes, macro / commodity / power / technology dynamics, policy reaction logic, price formation, trading, lending decisions, Japan calibration, real-data ingestion. All v1.7 / v1.8.x prohibitions are inherited.
- Auto-firing on `tick()` / `run()`. The book is read / written only by direct caller invocations — verified by the auto-execution-prohibition test.

### 52.5 The v1.8.8 hardening's hook chain — now complete

§50.1 (the v1.8.8 hardening) named three required hooks: source, scope, exposure. With v1.8.10 the chain is data-complete:

```
ReferenceVariableSpec.source_space_id, source_id      — source hook   (v1.8.9)
ReferenceVariableSpec.related_*_ids,                  — scope hook    (v1.8.9)
                       observability_scope,
                       typical_consumer_space_ids
ExposureRecord (subject_id × variable_id)             — exposure hook (v1.8.10)
```

A future v1.8.11 `ObservationMenu` builder, given a subject id, can:

1. Look up the subject's `ExposureRecord`s via
   `kernel.exposures.list_by_subject(subject_id)`.
2. For each exposure, fetch the variable's spec and its latest visible observation via `kernel.variables.get_variable(...)` and `kernel.variables.latest_observation(variable_id, as_of_date=menu_date)`.
3. Surface the joined `(variable, observation, exposure)` triples to the subject's `AttentionProfile` for selection.
4. The selected observations flow into `RoutineExecutionRequest.selected_observation_set_ids` and ultimately into a `RoutineRunRecord.input_refs`.

Each step is opt-in. v1.8.10 does **not** implement the join; it only persists the data.

### 52.6 v1.8.10 success criteria

§52 is complete when **all** hold:

1. `world/exposures.py`, the `EXPOSURE_ADDED` ledger type, and the `exposures` kernel field exist and behave per §52.1.
2. `tests/test_exposures.py` passes (59 tests).
3. The full test suite passes (1175 tests = 1116 prior + 59 exposures).
4. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
5. No existing test was modified; no existing record shape, book API, scheduler extension, or ledger record type was altered.
6. `ExposureBook` does not mutate any other v0 / v1 source-of-truth book — verified by the explicit no-mutation test.
7. `magnitude` and `confidence` are enforced in `[0.0, 1.0]` (with `bool` rejected) so v1.8.11+ consumers can rely on the bound.

### 52.7 Position in the v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.7 Corporate Quarterly Reporting Routine | First concrete routine. | Shipped |
| v1.8.8 Reference Variable Layer — Design (+ hardening) | Design (§50, §50.1). | Shipped |
| v1.8.9 WorldVariableBook | Code (§51). | Shipped |
| **v1.8.10 Exposure / Dependency Layer** | Code (§52). Storage + lookup only. | **Shipped** |
| v1.8.11 `ObservationMenu` builder | Code (§53). Read-only join. | Shipped |
| v1.8.12 Attention Variable Hooks + Investor / Bank Attention Demo | Code (§54). Heterogeneous attention. | Shipped |
| v1.8.13 Investor / Bank Review Routines | Code (§55). Routines consume attention. | Shipped |
| v1.8.14 Endogenous Chain Harness | Code (§56). Single helper orchestrates the full chain. | Shipped |
| v1.8.15 Ledger Trace Report | Code (§57). Read-only explainability over the chain. | Shipped |
| **v1.8.16 Freeze / Readiness** | Docs only (§58). Consolidates v1.8 + plans v1.9. | **Shipped** |
| v1.9 Living Reference World Demo | Code + tests. | Next |

## 53. v1.8.11 ObservationMenu Builder

§53 (v1.8.11) implements the v1.8.8 hardening's **gate 1 (visibility) + gate 2 (availability)** of the four-gate rule as a kernel-level join service. `ObservationMenuBuilder` reads `AttentionBook`, `SignalBook`, `WorldVariableBook`, and `ExposureBook` and writes one `ObservationMenu` per build call (via the existing `OBSERVATION_MENU_CREATED` ledger path on `AttentionBook.add_menu`). It does **not** perform attention selection (gate 3 — `SelectedObservationSet`), does **not** consume observations or fire routines (gate 4 — `RoutineEngine`), and does **not** auto-fire from `tick()` / `run()`.

§53 is the first piece of code that operationalizes the source / scope / exposure hook chain that §50.1 named and §52 made data-complete. v1.8.11 surfaces the chain as data — *which signals are visible, which variable observations are visible, which exposures are active* — without inventing the relationship at runtime.

### 53.1 What lands in v1.8.11

- `world/attention.py` — `ObservationMenu` extended additively with `available_variable_observation_ids: tuple[str, ...]` and `available_exposure_ids: tuple[str, ...]`. Both default empty for backwards compatibility, both flow through the existing `AVAILABLE_FIELDS` machinery (so `total_available_count()` and `__post_init__` normalization automatically cover them), both round-trip through `to_dict()`, and both carry counts in the existing `OBSERVATION_MENU_CREATED` ledger payload (`available_variable_observation_count`, `available_exposure_count`).
- `world/observation_menu_builder.py` — new module:
  - `ObservationMenuBuildRequest` immutable dataclass: `request_id`, `actor_id`, `as_of_date?`, `phase_id?`, `include_signals=True`, `include_variables=True`, `include_exposures=True`, `metadata`.
  - `ObservationMenuBuildResult` immutable dataclass mirroring the persisted menu plus the originating `request_id` and a derived `status` label.
  - `ObservationMenuBuilder` dataclass wired to `AttentionBook`, `SignalBook`, `WorldVariableBook`, `ExposureBook`, `InteractionBook?`, `Clock?`. Public API: `build_menu(req) -> Result`, `preview_menu(req) -> Result` (no write), and the read-only collectors `collect_visible_signals`, `collect_active_exposures`, `collect_visible_variable_observations`.
  - `ObservationMenuBuilderError` / `ObservationMenuBuildMissingDateError` for controlled failure paths.
- `world/kernel.py` — new optional field `observation_menu_builder: ObservationMenuBuilder | None`, constructed in `__post_init__` mirroring the v1.8.6 `routine_engine` pattern. NOT fired by `tick()` / `run()`.
- `tests/test_observation_menu_builder.py` — 50 tests covering the menu extension, request validation, end-to-end build, date semantics, exposure→variable join, no-exposure→empty default, visibility filtering, inactive-exposure exclusion, signal collection through `list_visible_to`, interaction-id collection (carried + signal-metadata), include flags, status semantics, single ledger emission, preview-does-not-write, kernel wiring, no-mutation guarantee.

### 53.2 Exposure / variable join semantics

The join is the v1.8.8 hardening's **exposure hook** in code:

1. The actor's exposures define which variables matter to them (`ExposureBook.list_by_subject(actor_id)` filtered by `is_active_as_of(as_of_date)`).
2. For each relevant variable, only observations with `visibility_date <= as_of_date` are surfaced (where `visibility_date = visible_from_date if present else as_of_date`).
3. **If the actor has zero active exposures, the menu's `available_variable_observation_ids` is empty by default** — the builder does *not* dump every world variable on every actor.

`available_interaction_ids` is the deduplicated union of `carried_by_interaction_id` values across the surfaced variable observations and the `interaction_id` key (when present) in the surfaced signals' metadata. This gives downstream consumers a way to navigate from a menu back to the channels that carried its content, without the builder having to validate that each interaction id resolves in `InteractionBook` (per the v0 / v1 cross-reference rule).

### 53.3 Status vocabulary

`ObservationMenuBuildResult.status` is a descriptive label, not an economic claim:

- `"completed"` — at least one available ref exists across the menu (auto-derived).
- `"empty"` — zero candidates across all sources (auto-derived).
- `"partial"` / `"degraded"` — caller-supplied via `request.metadata["status"]`. v1.8.11 reserves the labels but does not auto-derive them.

### 53.4 Anti-scope (what v1.8.11 deliberately does not do)

§53 is a read-only join milestone. v1.8.11 does **not** add:

- Attention selection. Gate 3 (`SelectedObservationSet`) remains caller-driven.
- Routine execution. Gate 4 (`RoutineEngine`) is unchanged.
- Auto-firing from `tick()` / `run()`. The builder is exposed as `kernel.observation_menu_builder` and fires only when a caller invokes `build_menu` / `preview_menu`.
- Sensitivity calibration. Exposures are still synthetic strengths from §52.
- Cross-reference validation. `actor_id` / `variable_id` / `interaction_id` are recorded as data, per the v0/v1 rule.
- Economic behavior. No price formation, no impact computation, no routine triggering.

### 53.5 v1.8.11 success criteria

§53 is complete when **all** hold:

1. `world/observation_menu_builder.py`, the two new `ObservationMenu` fields, the two new `OBSERVATION_MENU_CREATED` payload counts, and the `observation_menu_builder` kernel field exist and behave per §53.1.
2. `tests/test_observation_menu_builder.py` passes (50 tests).
3. The full test suite passes (1225 tests = 1175 prior + 50 builder).
4. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
5. No existing test was modified; no existing record shape was altered destructively (the `ObservationMenu` extension is additive; defaults preserve prior behavior).
6. The builder does not mutate `SignalBook`, `WorldVariableBook`, or `ExposureBook` — verified by the explicit no-mutation test.
7. `tick()` / `run()` does not auto-build menus — verified by the kernel non-firing test.
8. `build_menu` writes exactly one menu per call through `AttentionBook.add_menu`; `preview_menu` writes nothing.

### 53.6 Position in the v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.8 Reference Variable Layer — Design (+ hardening) | Design (§50, §50.1). | Shipped |
| v1.8.9 WorldVariableBook | Code (§51). | Shipped |
| v1.8.10 Exposure / Dependency Layer | Code (§52). | Shipped |
| v1.8.11 `ObservationMenu` builder | Code (§53). Read-only join. | Shipped |
| v1.8.12 Attention Variable Hooks + Investor / Bank Attention Demo | Code (§54). Heterogeneous attention. | Shipped |
| v1.8.13 Investor / Bank Review Routines | Code (§55). Routines consume attention. | Shipped |
| v1.8.14 Endogenous Chain Harness | Code (§56). Single helper orchestrates the full chain. | Shipped |
| v1.8.15 Ledger Trace Report | Code (§57). Read-only explainability over the chain. | Shipped |
| **v1.8.16 Freeze / Readiness** | Docs only (§58). Consolidates v1.8 + plans v1.9. | **Shipped** |
| v1.9 Living Reference World Demo | Code + tests. | Next |

## 54. v1.8.12 Attention Variable Hooks + Investor / Bank Attention Demo

§54 (v1.8.12) closes the v1.8.x attention loop by giving `AttentionProfile` *explicit* hooks into the v1.8.9 / v1.8.10 layers (variables and exposures), then demonstrates that two heterogeneous actors looking at the same reference world build *different* `SelectedObservationSet` records.

This is the first milestone that operationalizes **heterogeneous attention** as data: an investor and a bank can observe the same menu universe but record structurally different selections, without invoking any economic behavior. The demo is recordable, replayable, and reviewable from the ledger alone.

§54 deliberately does **not** ship: investor-review or bank-review routines, valuation refresh, impact estimation, sensitivity calculation, DSCR / LTV updates, price formation, trading, lending decisions, corporate actions, policy reactions, Japan calibration, real data ingestion, scenario engines, or any automatic economic behavior. Those land in v1.8.13 / v1.9 and beyond.

### 54.1 What lands in v1.8.12

- `world/attention.py` — `AttentionProfile` extended **additively** with four new watch fields:
  - `watched_variable_ids: tuple[str, ...]`
  - `watched_variable_groups: tuple[str, ...]`
  - `watched_exposure_types: tuple[str, ...]`
  - `watched_exposure_metrics: tuple[str, ...]`

  All default to empty tuples for backwards compatibility, all flow through `__post_init__` normalization, all round-trip through `to_dict()`, and all carry into the existing `ATTENTION_PROFILE_ADDED` ledger payload. The `_DIMENSION_TO_MENU_FIELD` table that drives `profile_matches_menu` is extended so the structural-overlap predicate covers the new dimensions (variable hooks pair with `available_variable_observation_ids`; exposure hooks pair with `available_exposure_ids`). Cross-references are recorded as data and not validated against `WorldVariableBook` or `ExposureBook`, per the v0/v1 cross-reference rule.
- `world/reference_attention.py` — new module:
  - `register_investor_attention_profile(...)` and `register_bank_attention_profile(...)` — idempotent helpers that register synthetic `AttentionProfile` records with v1.8.12-relevant defaults (investor watches fx / rates / financial_market / expectations_narratives + portfolio-translation / discount-rate / narrative exposure metrics; bank watches rates / credit / real_estate / energy_power + funding-cost / collateral / input-cost exposure metrics).
  - `run_investor_bank_attention_demo(kernel, *, firm_id, investor_id, bank_id, as_of_date=None, phase_id=None)` — the top-level helper. Builds one `ObservationMenu` per actor through the v1.8.11 `ObservationMenuBuilder`, applies a structural selection rule (signals filtered by `signal_type` / `subject_id`; variable observations filtered by `variable_id` / `variable_group`; exposures filtered by `exposure_type` / `metric`), persists one `SelectedObservationSet` per actor through `AttentionBook.add_selection`, and returns an immutable `InvestorBankAttentionDemoResult`.
  - `InvestorBankAttentionDemoResult` — an immutable dataclass carrying the menu / selection ids each actor received plus the convenience set differences (`shared_refs`, `investor_only_refs`, `bank_only_refs`).
- `tests/test_attention.py` — 9 new tests covering field acceptance, normalization, `to_dict` shape, ledger payload presence, and `profile_matches_menu` extension to the new dimensions.
- `tests/test_reference_attention_demo.py` — 23 new tests covering result shape, one-menu / one-selection-per-actor persistence, idempotent profile registration, the heterogeneous-selection contract (investor and bank diverge along investor- vs bank-relevant axes), determinism across fresh kernels, ledger evidence using existing record types only, and the no-mutation guarantees against `valuations` / `prices` / `ownership` / `contracts` / `constraints` / `external_processes` / `institutions` / `relationships`. The demo also does not run any routine, does not emit any signal beyond optional setup, and does not auto-fire from `tick()` / `run()`.

### 54.2 Selection semantics — structural, not economic

The demo selection rule is **rule-based and deterministic**. For each actor, the helper asks:

- **Signals** — does `signal.signal_type` ∈ `profile.watched_signal_types`, OR `signal.subject_id` ∈ `profile.watched_subject_ids`?
- **Variable observations** — does the underlying variable's `variable_id` ∈ `profile.watched_variable_ids`, OR `variable.variable_group` ∈ `profile.watched_variable_groups`?
- **Exposures** — does `exposure.exposure_type` ∈ `profile.watched_exposure_types`, OR `exposure.metric` ∈ `profile.watched_exposure_metrics`?

Matched refs are concatenated in **menu-order** (signals → variable observations → exposures, preserving each axis's ordering inside the menu) so the output is byte-identical across two fresh kernels with the same seed. The rule is *structural*: it asks "does this ref's record satisfy this profile's filters?" — it does **not** rank, weight, top-k truncate, or otherwise economically prioritize.

Selection in v1.8.12 is **attention**, not **decision**: a `SelectedObservationSet` is the actor noticing this ref, not buying / selling / lending against it.

### 54.3 What heterogeneous attention buys

With v1.8.12 in the tree, the same reference world produces different ledger traces depending on who is looking. In the canonical demo (firm-A reports earnings; macro / fx / rates / land / energy variables are released; investor and bank declare distinct exposures):

- The investor's `SelectedObservationSet` includes the corporate-reporting signal, fx + rates observations, and portfolio-translation / discount-rate exposures.
- The bank's `SelectedObservationSet` includes the corporate-reporting signal, rates + real-estate + energy observations, and funding-cost / collateral / operating-cost exposures.
- Both selections share the corporate-reporting signal and the rates observation; everything else diverges cleanly along investor- vs bank-relevant axes.

The shared / diverging structure is computed in the `InvestorBankAttentionDemoResult` (`shared_refs`, `investor_only_refs`, `bank_only_refs`) so callers can verify the divergence without re-querying the books.

### 54.4 Anti-scope (what v1.8.12 deliberately does not do)

§54 is an attention-only milestone. v1.8.12 does **not** add:

- Investor-review or bank-review routines. Selections are recorded; nothing consumes them.
- Valuation refresh, impact estimation, sensitivity calculation, DSCR / LTV updates, covenant pressure scoring, liquidity stress, price formation, trading, lending decisions, corporate actions, policy reactions.
- Cross-reference validation. `firm_id` / `investor_id` / `bank_id` are recorded as data; the demo does not check that they exist in the registry.
- Auto-firing from `tick()` / `run()`. The demo runs only when a caller invokes `run_investor_bank_attention_demo(...)`.
- Real data. All variable observations, exposures, and the corporate-reporting signal are synthetic.
- New ledger record types. Profile / menu / selection insertions reuse the v1.8.5 `ATTENTION_PROFILE_ADDED` / `OBSERVATION_MENU_CREATED` / `OBSERVATION_SET_SELECTED` paths.

### 54.5 v1.8.12 success criteria

§54 is complete when **all** hold:

1. `AttentionProfile` carries the four new `watched_*` fields with empty-tuple defaults; `to_dict`, `__post_init__` normalization, and the `ATTENTION_PROFILE_ADDED` ledger payload are extended; `profile_matches_menu` reports overlap on the new dimensions.
2. `world/reference_attention.py` exports `register_investor_attention_profile`, `register_bank_attention_profile`, `run_investor_bank_attention_demo`, and `InvestorBankAttentionDemoResult` with the v1.8.12 contract.
3. `tests/test_attention.py` (111 tests = 102 prior + 9 v1.8.12 schema) and `tests/test_reference_attention_demo.py` (23 tests) pass.
4. The full test suite passes (1257 tests = 1225 prior + 32 v1.8.12).
5. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
6. No existing test was modified destructively; the four new `AttentionProfile` fields default empty so v1.8.5 / v1.8.6 / v1.8.11 callers see no behavior change.
7. The demo does not mutate `valuations`, `prices`, `ownership`, `contracts`, `constraints`, `external_processes`, `institutions`, or `relationships` — verified by direct snapshot equality.
8. The demo does not run any routine and does not emit any signal beyond optional setup.
9. `tick()` / `run()` does not auto-build menus or selections — verified by direct test.
10. The demo is deterministic across fresh kernels with the same seed — verified by equality of `investor_selected_refs`, `bank_selected_refs`, `shared_refs`, `investor_only_refs`, `bank_only_refs`, and the menu / selection ids.

### 54.6 Position in the v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.9 WorldVariableBook | Code (§51). | Shipped |
| v1.8.10 Exposure / Dependency Layer | Code (§52). | Shipped |
| v1.8.11 `ObservationMenu` builder | Code (§53). | Shipped |
| v1.8.12 Attention Variable Hooks + Investor / Bank Attention Demo | Code (§54). | Shipped |
| **v1.8.13 Investor / Bank Review Routines** | Code (§55). | **Shipped** |
| v1.9 Living Reference World Demo | Year-long run on the routine + topology + attention + variable stack. | Next |

## 55. v1.8.13 Investor / Bank Review Routines

§55 (v1.8.13) closes the v1.8.x endogenous chain by giving heterogeneous attention a **consumer**: two narrow concrete review routines (`investor_review` and `bank_review`) that read `SelectedObservationSet` records through the existing v1.8.6 `RoutineEngine` and emit synthetic review notes. The full chain — *corporate reporting → menus → heterogeneous selected observations → investor / bank review run records → synthetic review notes* — is now reconstructable from the ledger alone, with zero economic behavior at any link.

§55 is the first place where "the investor reviews" and "the bank reviews" exist as recorded simulation events, not just as data shapes the v1.8.5 / v1.8.12 layers can describe. The routines are caller-initiated, structurally narrow (a self-loop within their own space), and forbidden from any economic mutation.

### 55.1 What lands in v1.8.13

- `world/reference_reviews.py` — new module:
  - Controlled vocabulary constants: `INVESTOR_REVIEW_ROUTINE_TYPE = "investor_review"`, `BANK_REVIEW_ROUTINE_TYPE = "bank_review"`, `INVESTOR_REVIEW_INTERACTION_ID = "interaction:investors.investor_review"`, `BANK_REVIEW_INTERACTION_ID = "interaction:banking.bank_credit_review"`, `INVESTOR_REVIEW_SIGNAL_TYPE = "investor_review_note"`, `BANK_REVIEW_SIGNAL_TYPE = "bank_review_note"`.
  - `register_investor_review_interaction(kernel)` / `register_bank_review_interaction(kernel)` — idempotent helpers that register the Investors→Investors and Banking→Banking self-loop channels (`channel_type` `"investor_review_channel"` / `"bank_credit_review_channel"`) with `routine_types_that_may_use_this_channel` locked to the matching routine type.
  - `register_investor_review_routine(kernel, *, investor_id)` / `register_bank_review_routine(kernel, *, bank_id)` — idempotent helpers that register a per-actor `RoutineSpec` with the matching `allowed_interaction_ids`. `optional_input_ref_types = ("InformationSignal", "VariableObservation", "ExposureRecord")` mirrors the v1.8.12 attention surface; `output_ref_types = ("InformationSignal",)` names the review-note signal.
  - `run_investor_review(kernel, *, investor_id, selected_observation_set_ids, as_of_date=None, ...)` / `run_bank_review(kernel, *, bank_id, selected_observation_set_ids, as_of_date=None, ...)` — the run helpers. Build a `RoutineExecutionRequest`, call `kernel.routine_engine.execute_request(...)`, and emit one synthetic review-note signal through `kernel.signals.add_signal(...)`.
  - `ReviewRoutineResult` — immutable result carrying the engine result and the produced signal.
- `tests/test_reference_review_routines.py` — 32 tests pinning interaction / routine self-loop topology, idempotent registration, single-run-record / single-signal flow, bidirectional run↔signal links, ledger ordering (`routine_run_recorded` → `signal_added`), selected-ref consumption, payload-count integrity, status semantics (`completed` when refs flow through, `degraded` when they don't — anti-scenario), date defaulting, determinism, no-mutation guarantees against `valuations`, `prices`, `ownership`, `contracts`, `constraints`, `exposures`, `variables`, `attention`, `institutions`, `external_processes`, `relationships`, no auto-firing from `tick()` / `run()`, and synthetic-only identifiers (with a word-boundary check that handles substrings like `tse` ⊂ `itself`).

### 55.2 The endogenous chain, end to end

With v1.8.13 in the tree, a kernel can be driven through this audit trace from a single deterministic seed:

1. **Corporate report** — `run_corporate_quarterly_reporting(kernel, firm_id=...)` writes one `RoutineRunRecord` and one `corporate_quarterly_report` `InformationSignal` through the existing v1.8.7 path.
2. **Menus + heterogeneous selections** — `run_investor_bank_attention_demo(kernel, firm_id=..., investor_id=..., bank_id=...)` writes two `ObservationMenu` records (one per actor, via the v1.8.11 `ObservationMenuBuilder`) and two `SelectedObservationSet` records (one per actor, via the v1.8.12 structural selection rule).
3. **Reviews** — `run_investor_review(kernel, investor_id=..., selected_observation_set_ids=(investor_selection_id,))` and `run_bank_review(kernel, bank_id=..., selected_observation_set_ids=(bank_selection_id,))` each write one `RoutineRunRecord` (with the selected refs in `input_refs`) and one review-note signal.

Every step is caller-initiated. Every step writes only to its own book(s) and the shared ledger. No price, valuation, ownership, contract, exposure, variable, attention, institution, or external-process state changes anywhere in the chain.

### 55.3 Review signal payload — count summaries only

The investor / bank review notes carry **structural counts**, not economic interpretation. Each note's `payload` includes:

- `actor_id`, `review_type`, `as_of_date`, `status`, `statement`.
- `selected_ref_count` — total resolved input refs (after engine dedup).
- `selected_signal_count` / `selected_variable_observation_count` / `selected_exposure_count` — how many of those refs the helper could resolve in `SignalBook` / `WorldVariableBook` / `ExposureBook` respectively.
- `selected_other_count` — anything that didn't classify (so the four counts always sum to `selected_ref_count`).
- `selected_observation_set_ids` — the ids that were passed in.

The four counts are **descriptive**, not normative: v1.8.13 does not score risk, flag covenants, take views, generate buy / sell / hold notes, or otherwise interpret the selected refs. The note is an audit artifact — proof that the routine ran, with what shape of input, on what date.

### 55.4 Anti-scope (what v1.8.13 deliberately does not do)

§55 is a *consumer-routine* milestone. v1.8.13 does **not** add:

- Buy / sell / hold decisions, portfolio rebalancing, lending decisions, covenant enforcement, credit-line repricing.
- Valuation refresh, impact estimation, sensitivity calculation, DSCR / LTV updates, liquidity stress, scenario rollout.
- Price formation, trading, market-making, corporate actions, policy reactions.
- Real Japan calibration. All ids and values are synthetic; the v1 forbidden-token list (`world/experiment.py::_FORBIDDEN_TOKENS`) is honored.
- Auto-firing. The routines run only when a caller invokes `run_investor_review` / `run_bank_review`. `tick()` and `run()` never trigger them.
- New ledger record types. Run records flow through `ROUTINE_RUN_RECORDED`; review notes flow through `SIGNAL_ADDED`.
- Cross-reference validation beyond what the engine already does (the engine validates that the routine, the supplied selections, and the supplied interaction exist; the cross-references inside the selection — signal ids, variable observation ids, exposure ids — are recorded as data per the v0/v1 rule).

### 55.5 v1.8.13 success criteria

§55 is complete when **all** hold:

1. `world/reference_reviews.py` exports the six controlled-vocabulary constants, the four registration helpers, the two run helpers, and `ReviewRoutineResult`, and the routines self-loop on Investors→Investors and Banking→Banking respectively.
2. Each `run_*_review` call writes exactly one `RoutineRunRecord` and exactly one `InformationSignal`, in that order on the ledger, with bidirectional run↔signal links.
3. Selected `SelectedObservationSet` ids flow through into `RoutineRunRecord.input_refs` (the engine collects them); the review note's count summaries match.
4. Status defaults to `"completed"` when refs flow through and `"degraded"` when they don't (anti-scenario rule).
5. The full test suite passes (1289 tests = 1257 prior + 32 review).
6. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
7. The review routines do not mutate `valuations`, `prices`, `ownership`, `contracts`, `constraints`, `exposures`, `variables`, `attention` (beyond reading the supplied selection), `institutions`, `external_processes`, or `relationships` — verified by direct snapshot equality.
8. `kernel.tick()` and `kernel.run(days=N)` do NOT auto-fire either review routine — verified by direct test.
9. Determinism: identical kernels seeded identically produce identical run ids, signal ids, and signal payloads.
10. All identifiers are synthetic and pass a word-boundary check against the v1 forbidden-token list.

### 55.6 Position in the v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.10 Exposure / Dependency Layer | Code (§52). | Shipped |
| v1.8.11 `ObservationMenu` builder | Code (§53). | Shipped |
| v1.8.12 Attention Variable Hooks + Investor / Bank Attention Demo | Code (§54). | Shipped |
| v1.8.13 Investor / Bank Review Routines | Code (§55). | Shipped |
| **v1.8.14 Endogenous Chain Harness** | Code (§56). Orchestration only. | **Shipped** |
| v1.9 Living Reference World Demo | Year-long run on the full endogenous chain. | Next |

## 56. v1.8.14 Endogenous Chain Harness

§56 (v1.8.14) is **pure orchestration**. It ships one helper — `run_reference_endogenous_chain` — that calls the existing v1.8.7 / v1.8.12 / v1.8.13 component helpers in order and returns one immutable `EndogenousChainResult` summarizing every record the chain wrote. v1.8.14 does **not** introduce any new economic behavior, any new ledger record type, or any new world-construction logic; it is the first compact non-shock endogenous chain you can run with a single helper call.

The chain it sequences:

1. **Corporate quarterly reporting** — `register_corporate_reporting_interaction` + `register_corporate_quarterly_reporting_routine` + `run_corporate_quarterly_reporting`. Writes one `RoutineRunRecord` and one synthetic `corporate_quarterly_report` `InformationSignal`.
2. **Heterogeneous investor / bank attention** — `run_investor_bank_attention_demo`. Writes (idempotently) two `AttentionProfile` records, then two `ObservationMenu` records and two `SelectedObservationSet` records, one per actor.
3. **Investor review** — `register_investor_review_interaction` + `register_investor_review_routine` + `run_investor_review`. Writes one `RoutineRunRecord` and one `investor_review_note` `InformationSignal`, with `input_refs` carrying the investor's selected refs.
4. **Bank review** — `register_bank_review_interaction` + `register_bank_review_routine` + `run_bank_review`. Symmetric.

§56 is the last v1.8.x milestone before v1.9; it is the smallest possible "everything fits together" demonstration that the v1.8.x stack composes correctly.

### 56.1 What lands in v1.8.14

- `world/reference_chain.py` — new module with `EndogenousChainResult` (immutable summary) and `run_reference_endogenous_chain(kernel, *, firm_id, investor_id, bank_id, as_of_date=None, phase_id=None, metadata=None)`. The harness:
  - Records `len(kernel.ledger.records)` immediately before and after the chain so the slice of new records is reconstructable.
  - Captures the ordered tuple of `LedgerRecord.object_id` values created during the call into `EndogenousChainResult.created_record_ids`.
  - Names every primary record id (corporate run + signal; both menus; both selections; both review runs + review signals; both attention profiles).
  - Surfaces the v1.8.12 set differences (`shared_selected_refs`, `investor_only_selected_refs`, `bank_only_selected_refs`) so callers do not have to recompute them.
  - Reports each phase's status (`completed` / `degraded`) verbatim from the underlying component results.
- `examples/reference_world/run_endogenous_chain.py` — small CLI that builds a synthetic seed kernel, runs the chain, and prints a compact human-readable trace. Re-runs are byte-identical.
- `tests/test_reference_endogenous_chain.py` — 29 tests pinning result shape, persistence (every result id resolves to a stored record), counts (one corporate run, two menus, two selections, two review runs, three signals total), ledger trace correctness (count diff equals `len(created_record_ids)` and the ids match the slice exactly), ledger ordering (corporate → attention → reviews), event-type discipline (no new record types), heterogeneous attention propagation (set differences agree with membership), determinism across fresh kernels, status semantics, date defaulting, defensive errors, no economic mutation against `valuations` / `prices` / `ownership` / `contracts` / `constraints` / `institutions` / `external_processes` / `relationships` (and no mutation of `exposures` / `variables` after setup), no auto-firing from `tick()` / `run()`, and synthetic-only identifiers.

### 56.2 Determinism contract

Two fresh kernels seeded identically and run with the same `firm_id` / `investor_id` / `bank_id` / `as_of_date` produce byte-identical `EndogenousChainResult`s. Every id in the chain is derived from those inputs (or directly from the as-of-date), and every component helper is itself deterministic. The harness does not consult the wall clock; `as_of_date` defaults to `kernel.clock.current_date`.

This is what makes v1.8.14 a viable foundation for v1.9: a year-long sweep can rerun the same chain on each tick boundary without any non-determinism leaking in.

### 56.3 The summary is convenience, not truth

`EndogenousChainResult` exists so callers can correlate chain phases without re-querying the kernel — but it is **not** the source of truth. The same chain is fully reconstructable from the kernel's ledger by slicing
`kernel.ledger.records[result.ledger_record_count_before : result.ledger_record_count_after]`. Tests verify that the slice's `object_id`s match `result.created_record_ids` exactly, in the same order. If the result and the ledger ever disagree, **trust the ledger**.

### 56.4 Anti-scope (what v1.8.14 deliberately does not do)

§56 is an orchestration milestone. v1.8.14 does **not** add:

- New economic behavior. No price formation, trading, lending decisions, valuation refresh, impact estimation, sensitivity calculation, DSCR / LTV updates, covenant enforcement, corporate actions, policy reactions.
- New ledger record types. The chain reuses the existing seven event types (`interaction_added`, `routine_added`, `routine_run_recorded`, `signal_added`, `attention_profile_added`, `observation_menu_created`, `observation_set_selected`); a test pins this.
- Auto-firing. The harness does not register a scheduler task and does not hook into `tick()` / `run()`. Calling the chain is a deliberate caller act.
- World construction. The harness *requires* a kernel — it does not seed variables / exposures / etc. on the caller's behalf. v1.9 will own the year-long seed.
- A year-long simulation. v1.8.14 runs one chain on one `as_of_date`. Sweeping is the v1.9 milestone.
- Real Japan calibration; no real data ingestion; no scenario engine. All ids are synthetic and pass the v1 forbidden-token check.

### 56.5 v1.8.14 success criteria

§56 is complete when **all** hold:

1. `world/reference_chain.py` exports `EndogenousChainResult` and `run_reference_endogenous_chain` with the v1.8.14 contract.
2. The harness writes nothing itself; every write goes through the existing v1.8.7 / v1.8.12 / v1.8.13 component helpers.
3. The result names every primary record id; each id resolves to an actually-stored record in the kernel.
4. The full test suite passes (1318 tests = 1289 prior + 29 chain).
5. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
6. `valuations` / `prices` / `ownership` / `contracts` / `constraints` / `institutions` / `external_processes` / `relationships` snapshots are byte-identical before and after the chain.
7. `exposures` and `variables` snapshots are byte-identical before and after the chain (the harness does not mutate them after setup).
8. `kernel.tick()` / `kernel.run(days=N)` do NOT run the chain.
9. The chain is deterministic across fresh kernels seeded identically.
10. All identifiers are synthetic (word-boundary forbidden-token check).

### 56.6 Position in the v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.11 `ObservationMenu` builder | Code (§53). | Shipped |
| v1.8.12 Attention Variable Hooks + Investor / Bank Attention Demo | Code (§54). | Shipped |
| v1.8.13 Investor / Bank Review Routines | Code (§55). | Shipped |
| v1.8.14 Endogenous Chain Harness | Code (§56). | Shipped |
| **v1.8.15 Ledger Trace Report** | Code (§57). Read-only explainability layer. | **Shipped** |
| v1.9 Living Reference World Demo | Year-long run sweeping the chain. | Next |

## 57. v1.8.15 Ledger Trace Report

§57 (v1.8.15) is **explainability**, not modeling. It ships a small read-only reporter that turns the ledger slice produced by `run_reference_endogenous_chain` (the v1.8.14 harness) into a deterministic immutable summary, plus deterministic dict and Markdown projections. v1.8.15 introduces no new ledger record type, no new economic behavior, no scheduler change, no real data ingestion — it is pure presentation over the records the v1.8.x stack already emits.

The reporter is the last piece of v1.8.x before v1.9: with it, anyone running the endogenous chain can immediately see *what happened* in a form suitable for code review, demo decks, public-facing notebooks, or post-hoc audit.

### 57.1 What lands in v1.8.15

- `world/ledger_trace_report.py` — new module with:
  - `LedgerTraceReport` — immutable dataclass naming the chain's ledger slice (`start_record_index`, `end_record_index`, `record_count`), the per-event-type counts (`record_type_counts`, sorted for determinism), the ordered ids and event types (`ordered_record_ids`, `ordered_record_types`), the role-bucketed ids (`routine_run_ids`, `signal_ids`, `menu_ids`, `selection_ids`), the v1.8.12 set differences (`investor_only_refs`, `bank_only_refs`, `shared_selected_refs`, plus `investor_selected_refs` / `bank_selected_refs`), a `warnings` tuple, and an audit-friendly `metadata` mapping.
  - `build_endogenous_chain_report(kernel, chain_result, *, chain_name=..., report_id=..., metadata=...)` — re-walks `kernel.ledger.records[before:after]`, populates the report, and emits informative warning strings (slice / chain mismatch, ledger truncated, missing expected event type) without crashing.
  - `LedgerTraceReport.to_dict()` — deterministic dict / list projection suitable for JSON.
  - `render_endogenous_chain_markdown(report)` — deterministic compact Markdown rendering with fixed section headings.
- `examples/reference_world/run_endogenous_chain.py` — extended with a `--markdown` flag that prints the rendered report after the operational trace. The previous compact trace (`[corporate]` / `[attention]` / `[selection]` / `[review]` / `[ledger]`) still prints by default.
- `tests/test_ledger_trace_report.py` — 23 tests pinning report shape, ledger-slice arithmetic (`record_count == end - start == len(ordered_record_ids)`), `record_type_counts` sums to `record_count` and is sorted, `ordered_record_ids` matches `chain_result.created_record_ids` byte-identically on the canonical chain, role bucketing, ref carry-through, default and explicit `report_id` / `chain_name`, audit metadata, determinism of `to_dict` and Markdown across two fresh kernels seeded identically, Markdown contains the expected section headings and event-type counts, validation warnings (slice grown after chain returned, count mismatch on a tampered chain result) without crashing, defensive errors (None kernel, wrong-type chain result), schema-level validation in `__post_init__`, full no-mutation guarantee against every kernel book and the ledger itself, and CLI smoke tests that confirm `--markdown` produces both the operational trace and the report and that the default mode does not.

### 57.2 The summary is convenience; the ledger is truth

The same record-by-record ground truth lives at `kernel.ledger.records[report.start_record_index:report.end_record_index]`. `LedgerTraceReport` re-projects that slice into a shape humans and downstream consumers can read at a glance — it does **not** replace the ledger. If the report and the ledger ever disagree, **trust the ledger**; v1.8.15's validation warnings exist to flag exactly this kind of drift.

### 57.3 Determinism

For a given kernel + chain_result pair, the report (and its `to_dict` / Markdown projections) is byte-identical across fresh process invocations. v1.8.15 does not consult the wall clock, does not mint random ids, and sorts every collection that does not have a natural ledger order.

This is what makes v1.8.15 viable for the v1.9 Living Reference World Demo: a year-long sweep can render one report per chain invocation and concatenate the Markdown with no manifest drift.

### 57.4 Anti-scope (what v1.8.15 deliberately does not do)

§57 is a reporting milestone. v1.8.15 does **not** add:

- New economic behavior, new routines, new ledger record types, new scheduler hooks.
- New books or kernel fields.
- Hashing / replay-determinism manifests beyond what v1.7 already ships. The Markdown is a *report*, not a manifest; it is not part of the v1.7 catalog-shape regression.
- Wall-clock dependencies, randomness, or floating-point accumulation that could drift across runs.
- Any read of records *outside* the chain's ledger slice. Records that exist before `start_record_index` or after `end_record_index` are not inspected.
- Real Japan calibration; no real data ingestion.

### 57.5 v1.8.15 success criteria

§57 is complete when **all** hold:

1. `world/ledger_trace_report.py` exports `LedgerTraceReport`, `build_endogenous_chain_report`, and `render_endogenous_chain_markdown` with the v1.8.15 contract.
2. `record_count`, `ordered_record_ids`, and the role-bucketed id tuples match the kernel ledger slice on the canonical chain.
3. `record_type_counts` sums to `record_count` and is sorted.
4. `ordered_record_ids == chain_result.created_record_ids` when the ledger is untouched after the chain.
5. `to_dict` and `render_endogenous_chain_markdown` are deterministic across two fresh kernels seeded identically.
6. The reporter does not mutate `valuations`, `prices`, `ownership`, `contracts`, `constraints`, `exposures`, `variables`, `attention`, `routines`, `interactions`, `signals`, `institutions`, `external_processes`, `relationships`, or the ledger.
7. Validation issues (slice / chain mismatch, count mismatch, missing expected event type) emit `warnings` strings without crashing.
8. The CLI prints both the operational trace and the Markdown report when `--markdown` is supplied; the default mode prints only the trace.
9. The full test suite passes (1341 tests = 1318 prior + 23 reporter).
10. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.

### 57.6 Position in the v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.12 Attention Variable Hooks + Investor / Bank Attention Demo | Code (§54). | Shipped |
| v1.8.13 Investor / Bank Review Routines | Code (§55). | Shipped |
| v1.8.14 Endogenous Chain Harness | Code (§56). | Shipped |
| v1.8.15 Ledger Trace Report | Code (§57). | Shipped |
| **v1.8.16 Freeze / Readiness** | Docs only (§58). | **Shipped** |
| v1.9 Living Reference World Demo | Year-long run sweeping the chain + report. | Next |

## 58. v1.8.16 Freeze / Readiness

§58 (v1.8.16) is **docs and release-readiness only**. No new code, no new tests, no new ledger record types, no new model behavior. v1.8.16 consolidates the v1.8 line as a coherent endogenous-activity milestone and prepares the project for v1.9 Living Reference World and eventual v1.9.last public prototype.

### 58.1 What ships in v1.8.16

- **`README.md`** (repo root) — opening repositioned to emphasize the jurisdiction-neutral / research-software / synthetic-only framing. New sections: "Current capability" (names the v1.8 stack components), "What the reference demo can do now" (the *corporate reporting → menus → heterogeneous selections → reviews → trace report* chain), "What it still does not do" (the v1.8 hard rails restated for first-time readers), "Quickstart" (the two demo invocations including `--markdown`), and "Roadmap" (v1.8.0 – v1.8.16 shipped, v1.9.0 next, v1.9.last first public prototype, v2.0 Japan public-data design gate, v3.0 proprietary).
- **`docs/v1_8_release_summary.md`** — new doc cataloging every v1.8 sub-release (v1.8.0 → v1.8.16), the v1.8 conceptual result ("external shocks are not the engine of the world"), the v1.8 technical result (a deterministic endogenous chain renderable as a Markdown report), the test surface at v1.8 freeze (1341 passed), and the hard boundaries v1.8 keeps.
- **`docs/v1_9_living_reference_world_plan.md`** — new doc defining v1.9's goal (multi-period synthetic living world without external shocks), scope (3–5 firms / 2 investors / 2 banks / 5–8 variables / 10–20 exposures / 4 quarterly periods), per-period flow (each period walks the v1.8.14 chain), complexity discipline (sparse edge-list traversal, no Cartesian-product loops, expected `O(periods × actors × relevant_refs)`), and the v1.9.last acceptance criteria.
- **`docs/public_prototype_plan.md`** — new doc defining what "public prototype" means for this project (GitHub-first / CLI-first / synthetic-only / explainability-first / no-Japan-claims), the public surfaces v1.9.last may target (repo + CLI + static Markdown reports + precomputed demo output + optional UI later), the surfaces v1.9.last must not target (proprietary calibration, expert notes, paid data, named-institution stress, client reports, private templates, investment advice), and the eleven acceptance gates.
- **`RELEASE_CHECKLIST.md`** — new "Public prototype gate (v1.9.last)" section covering the prototype-specific items on top of the existing public-release gate (one-command demo, README scope read, public/private boundary agreement, forbidden-token scan with word boundaries, no proprietary content, no investment-advice framings, CI green).
- **`examples/reference_world/README.md`** — extended to introduce both demos (the v1.6 reference loop and the v1.8.14 endogenous chain), add the `--markdown` invocation, and explain that the endogenous chain requires no external shock.
- **`docs/world_model.md`** §58 — this section.
- **`docs/fwe_reference_demo_design.md`** — appended a v1.8.16 freeze note.
- **`docs/test_inventory.md`** — headline updated to v1.8.16 (test count unchanged at 1341).

### 58.2 What v1.8.16 deliberately does NOT do

§58 is documentation only. v1.8.16 does **not**:

- Add new routines, books, or kernel fields.
- Introduce new economic behavior (no price formation, trading, lending decisions, valuation refresh, impact estimation, sensitivity calculation, DSCR / LTV updates, covenant enforcement, corporate actions, policy reactions).
- Add scheduler auto-firing.
- Sweep the v1.8.14 chain over multiple periods. That is v1.9.0.
- Add Japan calibration or real data ingestion.
- Modify any v1.0 – v1.8.15 record shape, helper, or test destructively.
- Introduce a scenario engine.

### 58.3 v1.8.16 success criteria

§58 is complete when **all** hold:

1. `README.md` accurately describes the v1.8 stack, the endogenous chain, and the explicit non-capabilities; the disclaimer remains intact and the version table reflects v1.8.16 / v1.9.0 / v1.9.last / v2 / v3.
2. `docs/v1_8_release_summary.md`, `docs/v1_9_living_reference_world_plan.md`, and `docs/public_prototype_plan.md` exist and cross-reference each other coherently.
3. `examples/reference_world/README.md` introduces both demos and the `--markdown` flag.
4. `RELEASE_CHECKLIST.md` carries the v1.9.last public-prototype gate alongside the existing public-release gate.
5. `docs/world_model.md` §58 (this section) summarises v1.8 and points at v1.9.
6. The full test suite still passes (1341 tests = no change from v1.8.15).
7. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.

### 58.4 Position in the v1.8.x sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.13 Investor / Bank Review Routines | Code (§55). | Shipped |
| v1.8.14 Endogenous Chain Harness | Code (§56). | Shipped |
| v1.8.15 Ledger Trace Report | Code (§57). | Shipped |
| v1.8.16 Freeze / Readiness | Docs (§58). | Shipped |
| **v1.9.0 Living Reference World Demo** | Code (§59). Multi-period sweep over the chain. | **Shipped** |
| v1.9.x | Report polishing, sparse / performance boundary, public-prototype readiness. | Next |
| v1.9.last | First lightweight public prototype. | Planned |

## 59. v1.9.0 Living Reference World Demo

§59 (v1.9.0) is the first concrete sub-release of the v1.9 line. Where v1.8.14's harness ran the endogenous chain *once* on a single `as_of_date`, v1.9.0 sweeps the chain across **multiple firms** and **multiple periods** with a small bounded fixture. Each quarter, every firm publishes a synthetic report; the investor and the bank rebuild their menus; their selections diverge along the v1.8.12 attention axes; and both run a review routine that emits a synthetic note. The ledger grows quarter by quarter; nothing else changes.

§59 is the smallest possible "everything composes over time" demonstration and the immediate prerequisite for v1.9.last. The conceptual point: with v1.9.0 you can **see endogenous routine activity recurring across periods, with no external shocks and no economic decision-making**.

### 59.1 What lands in v1.9.0

- `world/reference_living_world.py` — new module:
  - `LivingReferencePeriodSummary` — immutable per-period summary (corporate signal ids + run ids; investor / bank menu / selection / review-run / review-signal id tuples; record_count_created; metadata).
  - `LivingReferenceWorldResult` — immutable aggregate (run_id, period_count, firm / investor / bank id tuples, per_period_summaries, created_record_ids, ledger counts before / after, metadata).
  - `run_living_reference_world(kernel, *, firm_ids, investor_ids, bank_ids, period_dates=None, phase_id=None, run_id=None, metadata=None)` — top-level orchestrator. Defaults `period_dates` to four 2026 quarter-end dates. Iterates each period, registers infra idempotently on the first period (interactions, per-firm corporate routines, per-actor profiles + review routines), then for each period runs the corporate phase → attention phase → review phase via existing v1.8 helpers.
  - `_build_actor_menu_and_selection` — internal helper that calls `kernel.observation_menu_builder.build_menu(...)` and `select_observations_for_profile(...)` (v1.8.12 public selector) and persists one `SelectedObservationSet` through `AttentionBook.add_selection`. Used per actor per period.
- `world/reference_attention.py` — `_build_selected_refs` re-exposed publicly as `select_observations_for_profile(kernel, profile, menu)`. Identical behavior; the private alias is kept so v1.8.12's `run_investor_bank_attention_demo` continues to work without changes.
- `examples/reference_world/run_living_reference_world.py` — runnable CLI with a small synthetic seed kernel (3 firms / 2 investors / 2 banks / 6 variables / 10 exposures) and a compact `[setup]` / `[period N]` / `[ledger]` / `[summary]` trace.
- `tests/test_living_reference_world.py` — 27 tests pinning result shape, per-period record counts (one corporate report per firm per period; one menu / selection / review per actor per period), persistence (every result id resolves to a stored record), `created_record_ids` ↔ ledger slice equality, heterogeneous attention propagation across periods, determinism, default and explicit `period_dates`, defensive errors, no economic mutation against `valuations` / `prices` / `ownership` / `contracts` / `constraints` / `institutions` / `external_processes` / `relationships`, no mutation of `exposures` / `variables` after setup, no auto-firing from `tick()` / `run()`, a complexity budget that flags accidental Cartesian-product loops, synthetic-only identifiers (word-boundary forbidden-token check), and a CLI smoke test.

### 59.2 Per-period flow

For each `as_of_date` in `period_dates`, the harness runs:

1. **Corporate phase** — for each `firm_id`, call `run_corporate_quarterly_reporting(kernel, firm_id=..., as_of_date=...)`. One `RoutineRunRecord` + one `corporate_quarterly_report` `InformationSignal` per firm.
2. **Attention phase** — for each investor and each bank, call `kernel.observation_menu_builder.build_menu(...)` (idempotent), apply `select_observations_for_profile(...)` to the resulting menu, and persist one `SelectedObservationSet` through `AttentionBook.add_selection`. Investor and bank selections diverge along the v1.8.12 attention axes.
3. **Review phase** — for each investor and each bank, call the matching `run_*_review` helper with the period's selection ids. One `RoutineRunRecord` + one review-note `InformationSignal` per actor.

With the v1.9.0 default fixture (3 firms / 2 investors / 2 banks / 4 periods), the sweep produces ~100 ledger records and finishes in well under a second.

### 59.3 Complexity discipline (codified in tests)

v1.9.0 is deliberately bounded:

- **No dense all-to-all traversal.** The per-period flow iterates firms once, then investors once, then banks once. There is no Cartesian iteration over `firms × investors × banks × variables × exposures`.
- **Sparse menu builds.** The v1.8.11 `ObservationMenuBuilder` already iterates only the actor's exposures and the visible variable observations on the as-of date; v1.9.0 reuses it verbatim.
- **Sparse selection.** The v1.8.12 selection rule filters menu refs against the actor's watch fields; it does not enumerate all firms or all variables.
- **No path enumeration.** v1.9.0 does not walk the channel multigraph; the v1.8.3 tensor view stays a sparse projection.
- **No floating-point accumulation across periods.** All counts are integers; refs are tuples; statuses are string labels. Determinism is byte-level.
- **Expected complexity:** roughly **O(periods × actors × relevant_refs)**.

The complexity budget is encoded as a test: with the default fixture, the sweep must produce ≥ 88 records (the tight lower bound from the per-period work formula) and ≤ 200 records. Drift in either direction fails the test loudly so the loop is re-examined.

### 59.4 Anti-scope (carried forward from v1.8 verbatim)

§59 introduces no new economic behavior. v1.9.0 does **not** add:

- price formation, trading, investor buy / sell decisions, bank lending decisions, covenant enforcement;
- valuation refresh, impact estimation, sensitivity calculation, DSCR / LTV updates;
- corporate actions, policy reactions, scenario engines, stochastic shocks;
- dense all-to-all interaction traversal (the complexity budget enforces this);
- Japan calibration; real data ingestion;
- public web UI; v1.9.0 is CLI-first.

Every existing v1.8 anti-scope rule continues to apply. The only writes the harness performs are the writes the existing component helpers already perform (corporate reporting + menu / selection / review), and they use the same ledger paths.

### 59.5 v1.9.0 success criteria

§59 is complete when **all** hold:

1. `world/reference_living_world.py` exports `run_living_reference_world` + `LivingReferenceWorldResult` + `LivingReferencePeriodSummary` with the v1.9.0 contract.
2. `select_observations_for_profile` is publicly re-exposed in `world/reference_attention.py`; v1.8.12's `run_investor_bank_attention_demo` continues to pass its existing tests.
3. The harness produces exactly the expected per-period record counts: one corporate report per firm per period; one menu / selection / review per actor per period; review notes counted alongside.
4. Every result id resolves to a stored record in the kernel; `created_record_ids` matches `kernel.ledger.records[before:after]` byte-identically.
5. The result is deterministic across two fresh kernels seeded identically.
6. The full test suite passes (1368 tests = 1341 prior + 27 living-world).
7. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
8. `valuations` / `prices` / `ownership` / `contracts` / `constraints` / `institutions` / `external_processes` / `relationships` snapshots are byte-equal before and after the sweep; `exposures` / `variables` snapshots are byte-equal after the seed phase.
9. `kernel.tick()` / `kernel.run(days=N)` do NOT auto-fire the chain.
10. The complexity budget (≥ 88 and ≤ 200 records on the default fixture) holds.
11. All identifiers are synthetic and pass a word-boundary forbidden-token check.

### 59.6 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.16 Freeze / Readiness | Docs (§58). | Shipped |
| v1.9.0 Living Reference World Demo | Code (§59). | Shipped |
| **v1.9.1-prep Report Contract Audit** | Docs + contract test (§60). No code change. | **Shipped** |
| v1.9.1 Living World Trace Report | Code: `LivingWorldTraceReport` + Markdown renderer. | Next |
| v1.9.x | Report polishing, sparse / performance boundary, public-prototype readiness. | After v1.9.1 |
| v1.9.last | First lightweight public prototype (CLI-first, deterministic, explainability-first). | Planned |

## 60. v1.9.1-prep Report Contract Audit

§60 (v1.9.1-prep) is a **contract-audit milestone** — docs and one regression-gate test only. No production code change. v1.9.1-prep records the verdict that v1.9.0's `LivingReferenceWorldResult` and `LivingReferencePeriodSummary` schemas already carry every field the v1.9.1 reporter (the future `LivingWorldTraceReport`) will need, and pins that verdict with a small regression-gate test so future v1.9.x changes can't quietly break the reporter's input shape.

### 60.1 What lands in v1.9.1-prep

- `docs/v1_9_living_world_report_contract.md` — new contract doc:
  - schema cross-check tables for both v1.9.0 dataclasses;
  - input policy (`build_living_world_report(kernel, result)` reads result as the structural index, re-walks the ledger slice for verification, never mutates anything);
  - output contract (`LivingWorldTraceReport` immutable dataclass + `to_dict()` + `render_living_world_markdown(report)`);
  - Markdown section layout (title → setup → per-period table → attention divergence → ledger event-type counts → warnings → boundary statement);
  - determinism rules;
  - warning vocabulary suggestions (slice / chain mismatch, missing expected event types, empty per-period selections);
  - the mandatory hard-boundary statement: *"No price formation, no trading, no lending decisions, no valuation behavior, no Japan calibration, no real data."*
  - the **infra-prelude finding** — see below.
- `tests/test_living_reference_world_report_contract.py` — 12 tests pinning: every required field exists on both dataclasses, `created_record_ids` matches the ledger slice byte-identically, per-period `record_count_created` plus `infra_record_count` equals the total chain delta, per-period metadata carries chronological ledger indices, investor / bank selection refs are reachable for the set-difference computation, the canonical seed produces non-empty shared / investor_only / bank_only sets, report-critical fields are deterministic across fresh kernels, and reading every report-critical field does not mutate any kernel book.
- `docs/v1_9_living_reference_world_plan.md` — updated with a "v1.9.1-prep — what shipped" section pointing at the contract doc.
- `docs/world_model.md` §60 (this section).
- `docs/test_inventory.md` — bumped to v1.9.1-prep / 1380.

### 60.2 The infra-prelude finding

The audit found one non-obvious property worth pinning: v1.9.0's `run_living_reference_world` does idempotent infrastructure registration (interactions + per-firm corporate routines + per-actor attention profiles + review interactions + review routines) **before** entering the period loop. Those writes land in `kernel.ledger.records` *between* `result.ledger_record_count_before` and `per_period_summaries[0].metadata["ledger_record_count_before"]`. Concretely:

```
infra_record_count = (
    per_period_summaries[0].metadata["ledger_record_count_before"]
    - result.ledger_record_count_before
)
sum(p.record_count_created for p in per_period_summaries)
    + infra_record_count
    == result.created_record_count
```

This is **expected and honest**: per-period counts cover only what each period itself wrote; the prelude is a one-time setup window. The v1.9.1 reporter must surface the prelude separately in its Setup summary (so the per-period totals add up correctly). The contract test pins the algebra so any future v1.9.x change that breaks it (e.g., moving infra into period 1) fails loudly.

### 60.3 Anti-scope

§60 is contract-audit only. v1.9.1-prep does **not**:

- ship the `LivingWorldTraceReport` dataclass, `to_dict`, or Markdown renderer (that is v1.9.1).
- modify v1.9.0's `world/reference_living_world.py` in any way (byte-identical before / after).
- add new economic behavior, new routines, new books, or new ledger record types.
- change the v1.8 / v1.9.0 anti-scope rails.

### 60.4 v1.9.1-prep success criteria

§60 is complete when **all** hold:

1. `docs/v1_9_living_world_report_contract.md` exists with the schema tables, input policy, output contract, Markdown layout, determinism rules, warning vocabulary, mandatory boundary statement, and the infra-prelude finding.
2. `tests/test_living_reference_world_report_contract.py` runs and all 12 tests pass.
3. The full test suite passes (1380 tests = 1368 prior + 12 contract).
4. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
5. `world/reference_living_world.py` is byte-identical before and after this milestone.
6. The contract doc cross-references the v1.9 plan and `world_model.md` §59 / §60.

### 60.5 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.0 Living Reference World Demo | Code (§59). | Shipped |
| v1.9.1-prep Report Contract Audit | Docs + contract test (§60). | Shipped |
| **v1.9.1 Living World Trace Report** | Code (§61). Read-only explainability over the multi-period sweep. | **Shipped** |
| v1.9.x | Report polishing, sparse / performance boundary, public-prototype readiness. | Next |
| v1.9.last | First lightweight public prototype (CLI-first, deterministic, explainability-first). | Planned |

## 61. v1.9.1 Living World Trace Report

§61 (v1.9.1) is the implementation of the v1.9.1-prep contract (§60). Where v1.8.15 ships a read-only reporter for the **single-chain** v1.8.14 harness, v1.9.1 ships the symmetric reporter for the **multi-period** v1.9.0 sweep. Same discipline — no new ledger types, no new economic behavior, no new books, no scheduler hooks, no kernel mutation. The reporter takes a `LivingReferenceWorldResult` plus the kernel's ledger slice and produces a deterministic immutable `LivingWorldTraceReport` plus `to_dict()` and Markdown projections.

The reporter exists for **public-prototype explainability**. With v1.9.1 in the tree, a reader who runs `python -m examples.reference_world.run_living_reference_world --markdown` gets, in one byte-deterministic block: setup summary → infra prelude (with the algebraic relationship visible) → per-period table → attention divergence aggregated across all periods → overall ledger event-type counts → warnings → the mandatory hard-boundary statement.

### 61.1 What lands in v1.9.1

- `world/living_world_report.py` — new module:
  - `LivingWorldPeriodReport` — immutable per-period record (period_id, as_of_date, record_count_created, the six count fields for corporate / menus / selections / reviews, the corporate / review signal id tuples, the per-period sorted `record_type_counts`, per-period warnings, metadata).
  - `LivingWorldTraceReport` — immutable aggregate naming the run, the actor counts, the ledger slice metadata (`ledger_record_count_before` / `_after`, `created_record_count`), the **infra prelude** (`infra_record_count`) and `per_period_record_count_total` (which sum to `created_record_count`), the overall sorted `record_type_counts`, the per-period reports, the per-actor `(actor_id, period_id, count)` triples, the aggregated set differences (`shared_selected_refs`, `investor_only_refs`, `bank_only_refs` — sorted alphabetically), `ordered_record_ids` (preserving ledger order), `warnings`, and `metadata`.
  - `build_living_world_trace_report(kernel, living_world_result, *, report_id=None, metadata=None)` — re-walks the ledger slice for verification and event-type counts; reads each period's selections via `kernel.attention.get_selection(...)` to compute per-actor counts and the aggregated unions; computes `infra_record_count` from the v1.9.1-prep algebraic relationship; emits non-fatal warning strings on any cross-check that fails (slice / chain mismatch, ledger truncated, missing expected event types, empty selections).
  - `LivingWorldTraceReport.to_dict()` — JSON-friendly projection.
  - `render_living_world_markdown(report)` — deterministic compact Markdown rendering with the fixed section layout the v1.9.1-prep contract specified.
- `examples/reference_world/run_living_reference_world.py` — extended with a `--markdown` flag mirroring v1.8.15's CLI. Default mode (no flag) prints only the operational trace; both modes are byte-identical across runs.
- `tests/test_living_world_report.py` — 27 tests pinning shape, field carry-through, infra-algebra equality, sorted record_type_counts, byte-equal `ordered_record_ids`, aggregated set-difference correctness, sorted set-difference tuples, per-actor count triples sorted by `(period_id, actor_id)`, determinism of `to_dict` and Markdown across two fresh kernels seeded identically, every required Markdown section heading, the mandatory hard-boundary statement emitted verbatim, warning emission on tampered chain results without crashing, defensive errors (None kernel, wrong-type result), schema-level `__post_init__` validation (rejects `infra + per_period != created`), full no-mutation guarantee against every kernel book and the ledger length, and CLI smoke for both `--markdown` and default modes.

### 61.2 Aggregated set-difference semantics

The v1.9.0 sweep has `len(investors) ≥ 1` and `len(banks) ≥ 1`, so the natural "shared / investor-only / bank-only" question is whether a ref appears in *any* investor selection vs *any* bank selection. v1.9.1 adopts the **union-of-unions** rule:

```
investor_union = ⋃ investor_selection.selected_refs across all investors and all periods
bank_union     = ⋃ bank_selection.selected_refs     across all banks    and all periods
shared_selected_refs   = sorted(investor_union ∩ bank_union)
investor_only_refs     = sorted(investor_union - bank_union)
bank_only_refs         = sorted(bank_union - investor_union)
```

Per-actor counts are surfaced separately as
`investor_selected_ref_counts: tuple[(actor_id, period_id, count), ...]`
sorted by `(period_id, actor_id)` so the Markdown table renders deterministically. The same shape is used for banks.

### 61.3 The infra prelude in the report

The v1.9.1-prep contract requires the reporter to surface the v1.9.0 infra prelude separately from per-period activity. v1.9.1 implements this via:

```
infra_record_count
    = max(created_record_count - per_period_record_count_total, 0)
```

The `__post_init__` validator on `LivingWorldTraceReport` enforces
`infra_record_count + per_period_record_count_total == created_record_count` so any tampering with one component without the other fails construction. The Markdown's "Infra prelude" section prints all three numbers and the algebra check, so a reader can verify the relationship at a glance.

### 61.4 Determinism rules

- `record_type_counts` (overall and per period) sorted by event type.
- `period_summaries` preserve input order (chronological by `as_of_date`).
- `ordered_record_ids` preserve ledger order.
- `shared_selected_refs` / `investor_only_refs` / `bank_only_refs` sorted alphabetically (set differences have no natural order; we pick a stable one).
- `investor_selected_ref_counts` / `bank_selected_ref_counts` sorted by `(period_id, actor_id)`.
- No timestamps, no random ids, no wall-clock dependencies, no floating-point accumulation.
- Markdown layout fixed: title → Setup → Infra prelude → Per-period summary → Attention divergence (per-actor counts → shared → investor-only → bank-only) → Ledger event-type counts → Warnings → Boundaries (verbatim hard-boundary statement).

### 61.5 Anti-scope

§61 is reporting only. v1.9.1 does **not** add:

- new economic behavior, new routines, new books, new ledger record types;
- new kernel state or scheduler hooks;
- web UI, real data ingestion, scenario engines, randomness, wall-clock dependencies;
- ranking, weighting, recommendation, or any economic interpretation of selected refs.

If a future polishing milestone needs to extend the reporter, it must keep the read-only invariant and the deterministic-output invariant.

### 61.6 v1.9.1 success criteria

§61 is complete when **all** hold:

1. `world/living_world_report.py` exports `LivingWorldPeriodReport`, `LivingWorldTraceReport`, `build_living_world_trace_report`, and `render_living_world_markdown` with the v1.9.1 contract.
2. `infra_record_count + per_period_record_count_total == created_record_count` is enforced in `__post_init__`.
3. `record_type_counts` (overall and per period) sums to its corresponding record count and is sorted.
4. `ordered_record_ids` matches `LivingReferenceWorldResult.created_record_ids` byte-identically on the canonical seed.
5. Aggregated set differences match the unions of stored selections.
6. The reporter does not mutate any kernel book or the ledger length.
7. `to_dict` and `render_living_world_markdown` are deterministic across two fresh kernels seeded identically.
8. Markdown contains every required section heading and emits the hard-boundary statement verbatim:
   *"No price formation, no trading, no lending decisions, no valuation behavior, no Japan calibration, no real data, no investment advice."*
9. The CLI's `--markdown` flag prints both the operational trace and the report; the default mode prints only the trace.
10. The full test suite passes (1407 tests = 1380 prior + 27 reporter).
11. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.

### 61.7 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.0 Living Reference World Demo | Code (§59). | Shipped |
| v1.9.1-prep Report Contract Audit | Docs + contract test (§60). | Shipped |
| v1.9.1 Living World Trace Report | Code (§61). | Shipped |
| **v1.9.2 Living World Replay / Manifest / Digest** | Code (§62). Reproducibility infrastructure. | **Shipped** |
| v1.9.x | Report polishing, sparse / performance boundary, public-prototype readiness. | Next |
| v1.9.last | First lightweight public prototype. | Planned |

## 62. v1.9.2 Living World Replay / Manifest / Digest

§62 (v1.9.2) is **reproducibility infrastructure** for the multi-period v1.9.0 living reference world. Where v1.7-public-rc1+ shipped `replay_utils.py` + `manifest.py` for the single-day reference demo, v1.9.2 ships the symmetric pair for the multi-period sweep:

- `examples/reference_world/living_world_replay.py` — `canonicalize_living_world_result(...)` + `living_world_digest(...)`.
- `examples/reference_world/living_world_manifest.py` — `build_living_world_manifest(...)` + `write_living_world_manifest(...)`.

The point of v1.9.2 is to give a researcher running the v1.9.0 demo a way to answer two questions, deterministically and from a single command:

1. **"Is this the same run as that one?"** — compare the SHA-256 `living_world_digest`.
2. **"If I re-run on the same code, do I get the same trace?"** — re-run the demo with `--manifest path/to/m.json` and compare `m["living_world_digest"]` between runs.

§62 is reporting / packaging only. It introduces no new economic behavior, no new ledger record types, no new books, no kernel mutation, no scheduler hooks.

### 62.1 What lands in v1.9.2

- `examples/reference_world/living_world_replay.py` — new module:
  - `LIVING_WORLD_BOUNDARY_STATEMENT` constant (must match the v1.9.1 reporter's verbatim string; tests pin this).
  - `CANONICAL_FORMAT_VERSION = "living_world_canonical.v1"`.
  - `canonicalize_living_world_result(kernel, result, report=None) -> dict` — JSON-friendly structural projection of the run. Captures run identity, ledger slice metadata, the v1.9.1-prep infra-algebra (`infra_record_count + per_period_record_count_total == created_record_count`), per-period summaries (with id tuples in ledger order), aggregated event-type counts (sorted), aggregated attention divergence, per-actor selected-ref count triples, the canonicalised ledger slice (volatile `record_id` / `timestamp` excluded; `parent_record_ids` rewritten as slice-relative `parent_sequences`), and the boundary statement.
  - `living_world_digest(kernel, result, report=None) -> str` — 64-char lowercase hex SHA-256 over `json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
- `examples/reference_world/living_world_manifest.py` — new module:
  - `MANIFEST_VERSION = "living_world_manifest.v1"` and `RUN_TYPE = "living_reference_world"`.
  - `_git_probe()` — best-effort git revision / dirty / status probe; never raises (`status ∈ {"ok", "git_unavailable", "not_a_repo", "error"}`).
  - `build_living_world_manifest(kernel, result, *, report=None, input_profile=None, preset_name=None, variable_count=None, exposure_count=None, summary=None) -> dict` — the manifest builder. Includes the standalone `living_world_digest` and (when `report` is supplied) a `report_digest` cross-check. Returns a deterministic dict.
  - `write_living_world_manifest(manifest, output_path) -> Path` — deterministic JSON writer (`sort_keys=True`, `indent=2`, `ensure_ascii=False`, trailing newline). Atomic via temp sibling + rename. Creates parent directories.
- `examples/reference_world/run_living_reference_world.py` — new `--manifest path/to/m.json` flag. Default mode unchanged; `--markdown` still works; `--manifest` writes the deterministic JSON manifest at the supplied path and prints a `[manifest]` line with the digest.
- `tests/test_living_world_replay.py` — 16 tests pinning canonical shape, infra-algebra preservation, volatile-field exclusion (with slice-relative parent sequences), JSON round-trip stability, byte-equal canonical / digest across two fresh kernels seeded identically, the explicit SHA-256 digest recipe, digest sensitivity to canonical changes, the read-only guarantee, the boundary-statement consistency check against the v1.9.1 reporter, and defensive errors.
- `tests/test_living_world_manifest.py` — 19 tests pinning required fields, `manifest_version` / `run_type` constants, manifest digest equality with `living_world_digest`, count carry-through, missing-git resilience (monkey-patched `subprocess.run`), deterministic byte-equal writer output across consecutive writes, sorted-keys JSON layout, parent-directory creation, atomic-write cleanup (no `.tmp` left behind), writer return type, full read-only guarantee, and CLI smoke tests for both `--manifest` and default modes.

### 62.2 The canonical view's volatility rule

v1.9.2 mirrors the v1.7-era replay-utils volatility rule:

| Field | In canonical? | Rationale |
| --- | --- | --- |
| `record_id` | **No** | Hash-derived from `timestamp.isoformat()`; non-deterministic. |
| `timestamp` | **No** | Wall-clock. |
| `parent_record_ids` | **Rewritten** | Replaced with `parent_sequences`: slice-relative integer indices. Two kernels whose pre-existing ledgers differ in length still produce identical `parent_sequences`. |
| `record_type`, `source`, `target`, `object_id`, `payload`, `metadata`, `simulation_date`, `correlation_id`, `causation_id`, `scenario_id`, `run_id`, `seed`, `space_id`, `agent_id`, `snapshot_id`, `state_hash`, `visibility`, `confidence`, `schema_version` | **Yes** | All deterministic across runs of a deterministic fixture. |
| Result-level fields (`run_id`, `period_count`, actor id tuples, `created_record_ids`, per-period summaries) | **Yes** | All pinned deterministic by v1.9.0 tests. |
| Aggregated event-type counts | **Yes** (sorted) | Re-walked from the slice. |
| Aggregated attention divergence | **Yes** (sorted alphabetically) | Read from `kernel.attention.get_selection(...).selected_refs`. |
| `boundary_statement` | **Yes** | Pinned to v1.9.1 reporter. |

### 62.3 The manifest schema

The manifest is intentionally narrow. Required fields:

```
manifest_version, run_type,
git_sha, git_dirty, git_status,
python_version, platform,
input_profile, preset_name,
period_count, firm_count, investor_count, bank_count,
variable_count, exposure_count,
ledger_record_count_before, ledger_record_count_after,
created_record_count, infra_record_count,
per_period_record_count_total,
living_world_digest,
boundary_statement,
summary
```

When the caller supplies a v1.9.1 `LivingWorldTraceReport`, the manifest also carries `report_digest` (a SHA-256 over a small report-derived view) as a sanity cross-check.

The manifest is **synthetic-demo metadata only**. It carries no real data, no proprietary content, no investment claims. The boundary statement embedded in the manifest is the same verbatim string the v1.9.1 reporter emits.

### 62.4 Anti-scope

§62 is reproducibility infrastructure only. v1.9.2 does **not** add:

- new economic behavior, new routines, new books, new ledger record types;
- new kernel state or scheduler hooks;
- web UI, real data ingestion, scenario engines, randomness, wall-clock dependencies in canonical output;
- ranking, weighting, recommendation, or any economic interpretation.

### 62.5 v1.9.2 success criteria

§62 is complete when **all** hold:

1. `living_world_replay.py` exports `LIVING_WORLD_BOUNDARY_STATEMENT`, `CANONICAL_FORMAT_VERSION`, `canonicalize_living_world_result`, and `living_world_digest`.
2. `living_world_manifest.py` exports `MANIFEST_VERSION`, `RUN_TYPE`, `build_living_world_manifest`, and `write_living_world_manifest`.
3. The canonical view excludes `record_id` / `timestamp` and rewrites `parent_record_ids` as slice-relative `parent_sequences`.
4. Two fresh kernels seeded identically produce byte-equal canonical dicts and equal SHA-256 digests; the digest is 64-char lowercase hex.
5. `infra_record_count + per_period_record_count_total == created_record_count` is preserved in both the canonical view and the manifest.
6. The manifest's `living_world_digest` equals `living_world_digest(kernel, result)` standalone.
7. The writer produces deterministic JSON (`sort_keys=True`, `indent=2`, `ensure_ascii=False`, trailing newline) byte-identically across consecutive writes; creates parent directories; uses temp-sibling + rename to avoid partial files.
8. A missing-git environment does not crash the manifest builder; `git_status` reports `"git_unavailable"`.
9. The CLI's `--manifest path` flag writes a valid manifest with the right digest; default mode is unchanged.
10. Canonicalize / digest / build / write are read-only against every kernel book and the ledger length.
11. The full test suite passes (1442 tests = 1407 prior + 16 replay + 19 manifest).
12. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.

### 62.6 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.0 Living Reference World Demo | Code (§59). | Shipped |
| v1.9.1-prep Report Contract Audit | Docs + contract test (§60). | Shipped |
| v1.9.1 Living World Trace Report | Code (§61). | Shipped |
| v1.9.2 Living World Replay / Manifest / Digest | Code (§62). | Shipped |
| **v1.9.3 Model Mechanism Inventory + Behavioral Gap Audit + Mechanism Interface** | Docs + interface contract (§63). | **Shipped** |
| v1.9.4 Synthetic Firm Financial Update / Margin Pressure | First concrete `MechanismAdapter`. | Next |
| v1.9.5 Reference Valuation Refresh Lite Mechanism | `valuation_mechanism` adapter (§65). | Shipped |
| v1.9.6 Bank Credit Review Lite | `credit_review_mechanism` adapter. | After v1.9.5 |
| v1.9.7 Performance Boundary | Sparse-iteration / complexity-budget hardening. | After v1.9.6 |
| v1.9.last | First lightweight public prototype. | After v1.9.7 |

## 63. v1.9.3 Model Mechanism Inventory + Behavioral Gap Audit + Mechanism Interface

§63 (v1.9.3) is a **substance audit + interface contract**. It ships no economic behavior. Its job is to:

1. record what the project *actually* implements (vs what the surface area might appear to imply);
2. name the missing mechanisms ranked by suitability for the next milestone;
3. lock the mechanism interface so v1.9.4+ concrete mechanisms cannot quietly drift the contract;
4. tighten anti-overclaiming language in the README before any public-prototype polish.

The audit ships before v1.9.last so the public prototype gate cannot be cleared while the project is still infrastructure-only.

### 63.1 Numbering note

The user-facing task that prompted this work was titled *"v1.9.2 Model Mechanism Inventory & Behavioral Gap Audit."* However v1.9.2 had already shipped one milestone earlier as Living World Replay / Manifest / Digest (§62, commit `9d495bf`). This audit therefore lands as **v1.9.3**; the v1.9 plan's "recommended next path" is renumbered accordingly (see [`v1_9_living_reference_world_plan.md`](v1_9_living_reference_world_plan.md) and [`behavioral_gap_audit.md`](behavioral_gap_audit.md)). Every downstream milestone (firm-financial, valuation lite, credit-review lite, performance boundary, public-prototype freeze) shifts one slot.

### 63.2 What lands in v1.9.3

- [`docs/model_mechanism_inventory.md`](model_mechanism_inventory.md) — the per-component classification table. Maps every kernel / book / engine / routine / attention / report component to one of: *infrastructure / source-of-truth storage / structural model / observation-attention model / routine-process model / deterministic demo rule / economic behavior model / not yet modeled*. Every row names what the component does, what it does not do, whether it changes economic state, whether it makes a decision, whether it is deterministic, whether it is calibrated, whether it is synthetic-only, and where a future mechanism could plug in.
- [`docs/behavioral_gap_audit.md`](behavioral_gap_audit.md) — the gap analysis. Names the highest-value missing mechanisms (firm financial update, input-cost / margin-pressure propagation, valuation refresh, bank credit review, investor intent, constraint / covenant response, macro / world-variable process, market price formation), ranks them on five filters (reuses existing infra; synthetic / jurisdiction-neutral; no real data; produces visible ledger traces; avoids price formation), records the recommended next path, and provides verbatim anti-overclaiming language for the public prototype.
- `world/mechanisms.py` — the mechanism interface contract. Five immutable types:
  - `MechanismSpec` — `model_id`, `model_family`, `version`, `assumptions`, `calibration_status`, `stochasticity`, `required_inputs`, `output_types`, `metadata`.
  - `MechanismInputBundle` — `request_id`, `model_id`, `actor_id`, `as_of_date`, `selected_observation_set_ids`, `input_refs`, `state_views`, `parameters`, `metadata`.
  - `MechanismOutputBundle` — `request_id`, `model_id`, `status`, five `proposed_*` tuples (signals / valuation records / constraint pressure deltas / intent records / run records), `output_summary`, `warnings`, `metadata`.
  - `MechanismRunRecord` — `run_id`, `request_id`, `model_id`, `model_family`, `version`, `actor_id`, `as_of_date`, `status`, `input_refs`, `committed_output_refs`, `parent_record_ids`, `input_summary_hash`, `output_summary_hash`, `metadata`.
  - `MechanismAdapter` — `runtime_checkable` Protocol exposing `spec` and `apply(bundle) -> output`.
  - Vocabulary tuples: `MECHANISM_FAMILIES`, `CALIBRATION_STATUSES`, `STOCHASTICITY_LABELS`.
- `tests/test_mechanism_interface.py` — 39 contract tests pinning required-field shape on all four dataclasses, immutability (`frozen=True`), validation rejection of empty required strings and empty tuple entries, `to_dict` JSON round-trips, the `runtime_checkable` Protocol's structural acceptance / rejection, the vocabulary tuples cover the canonical set, and the "constructing interface records does not require a kernel" anti-behavior check.
- `README.md` — anti-overclaiming language tightened. The opening paragraph now says explicitly: not a forecasting model, not investment advice, not calibrated, currently demonstrates auditable endogenous information and review flows, financial decision behavior intentionally limited. The roadmap is renumbered to reflect the recommended path.

### 63.3 Verdict

> **The current system is an auditable routine-driven information-flow substrate. It is not yet a price-formation model, credit model, valuation model, macro model, or firm-financial dynamics model.**

What v1.9.3 changes is *clarity*, not *substrate*. Code that already shipped is unchanged; the new module (`world/mechanisms.py`) introduces no behavior; the new docs catalogue what exists rather than promising what does not.

### 63.4 Mechanism principles (ship-or-die invariants)

These principles apply to v1.9.4+ mechanisms and are pinned in the contract test file:

1. **Mechanisms do not directly mutate books.** They propose; the caller commits.
2. **Mechanisms consume typed refs / selected observations / state views.** Inputs are explicit; no hidden globals.
3. **Mechanisms return proposed records or output bundles.**
4. **The caller decides which outputs are committed.**
5. **Every mechanism run is ledger-auditable.**
6. **Each mechanism declares**: `model_id`, `model_family`, `version`, `assumptions`, `calibration_status`, `stochasticity`, `required_inputs`, `output_types`.
7. **Reference mechanisms are simple and synthetic.** v1.9.4 – v1.9.6 mechanisms are jurisdiction-neutral, deterministic (or pinned-seed stochastic), and produce visible ledger traces.
8. **Advanced mechanisms (FCN, herding, minority game, speculation game, LOB models) attach as adapters.** They are v2+ candidates; v1.x ships only the contract they fit into.

### 63.5 Suggested mechanism families (forward-looking, not shipped)

- `firm_financial_mechanism` — synthetic margin / liquidity / debt pressure update.
- `valuation_mechanism` — selected refs → `ValuationRecord` proposals.
- `credit_review_mechanism` — selected refs → credit-review notes + constraint-pressure deltas.
- `investor_intent_mechanism` — selected refs → non-binding `investor_intent` records (no orders, no trades).
- `market_mechanism` — FCN / herding / minority-game / speculation-game / LOB adapters. v2+ territory.

### 63.6 Anti-scope

§63 is contract + audit only. v1.9.3 does **not** add:

- any concrete mechanism (those are v1.9.4 onward);
- any new ledger record type;
- any auto-firing scheduler hook;
- any economic interpretation of any record;
- any real-data ingestion, Japan-specific calibration, or scenario engine;
- any v1.9.0 / v1.9.1 / v1.9.2 code change. The v1.9.0 living-world helper, the v1.9.1 reporter, and the v1.9.2 replay / manifest helpers are all byte-identical before / after.

### 63.7 v1.9.3 success criteria

§63 is complete when **all** hold:

1. `docs/model_mechanism_inventory.md` and `docs/behavioral_gap_audit.md` exist and cross-reference each other.
2. `world/mechanisms.py` exports `MechanismSpec`, `MechanismInputBundle`, `MechanismOutputBundle`, `MechanismRunRecord`, `MechanismAdapter`, plus the three vocabulary tuples.
3. The four dataclasses are frozen, validate empty / wrong-type inputs, and `to_dict` JSON-round-trips.
4. `tests/test_mechanism_interface.py` (39) passes; the full suite passes.
5. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
6. `world/reference_living_world.py`, `world/living_world_report.py`, and `examples/reference_world/living_world_replay.py` / `living_world_manifest.py` are unchanged.
7. The README's opening paragraph reflects the v1.9.3 anti-overclaiming language.

### 63.8 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.0 Living Reference World Demo | Code (§59). | Shipped |
| v1.9.1-prep Report Contract Audit | Docs + contract test (§60). | Shipped |
| v1.9.1 Living World Trace Report | Code (§61). | Shipped |
| v1.9.2 Living World Replay / Manifest / Digest | Code (§62). | Shipped |
| v1.9.3 Model Mechanism Inventory + Behavioral Gap Audit + Mechanism Interface | Docs + interface contract (§63). | Shipped |
| v1.9.3.1 Mechanism Interface Hardening | Code (§63.9). Deep-freeze + rename + ordering clarification. | Shipped |
| v1.9.4 Reference Firm Operating Pressure Assessment Mechanism | Code (§64). First concrete `MechanismAdapter`. | Shipped |
| v1.9.5 Reference Valuation Refresh Lite Mechanism | Code (§65). Second concrete `MechanismAdapter` (`valuation_mechanism` family). | Shipped |
| **v1.9.6 Living-world Mechanism Integration** | Code (§66). Wires v1.9.4 + v1.9.5 into `run_living_reference_world`. | **Shipped** |
| v1.9.7 Bank Credit Review Lite | `credit_review_mechanism` adapter. | Next |
| v1.9.8 Performance Boundary | Sparse-iteration hardening. | After v1.9.7 (now Next). |
| v1.9.last | First lightweight public prototype. | After v1.9.8 |

## 64. v1.9.4 Reference Firm Operating Pressure Assessment Mechanism

§64 (v1.9.4) ships the project's **first concrete mechanism** on top of the v1.9.3 / v1.9.3.1 interface contract. It is **not** a "firm financial update" — that framing was rejected during pre-v1.9.4 review on the grounds that a firm does not update its financial statements simply because it receives operating or financing pressure. The corrected framing:

> v1.9.4 ships the **Reference Firm Operating Pressure Assessment Mechanism**: it assesses synthetic operating / financing pressure from resolved variable observations and exposure records, then proposes one diagnostic ``firm_operating_pressure_assessment`` signal. **It does not update any financial statement line item**, balance-sheet view, valuation, price, or any other piece of state. The output is a *signal* an observer may attend to, not a *claim* about firm value.

§64 is the first place where the v1.8 endogenous chain produces an output with concrete economic *content* (pressure dimensions in `[0, 1]`) rather than purely-structural counts. The content is **synthetic**, deterministic, and read-only against the kernel.

### 64.1 What lands in v1.9.4

- `world/reference_firm_pressure.py` — new module:
  - Six controlled-vocabulary constants:
    - `FIRM_PRESSURE_MODEL_ID = "mechanism:firm_financial_mechanism:reference_firm_pressure_v0"`
    - `FIRM_PRESSURE_MODEL_FAMILY = "firm_financial_mechanism"` (per the v1.9.3 family vocabulary)
    - `FIRM_PRESSURE_MECHANISM_VERSION = "0.1"`
    - `FIRM_PRESSURE_SIGNAL_TYPE = "firm_operating_pressure_assessment"`
    - `FIRM_PRESSURE_SOURCE_ID = "source:firm_operating_pressure_self_assessment"`
    - `_PRESSURE_DIMENSIONS` — the five pressure-axis definitions and the (`exposure_types`, `variable_groups`) mappings each draws from.
  - `FirmPressureMechanismAdapter` — frozen dataclass implementing `MechanismAdapter`. `apply(request)` reads `request.evidence` only and returns a `MechanismOutputBundle` with one proposed signal. The adapter takes **no kernel parameter**, reads no book, and never mutates the request.
  - `FirmPressureMechanismResult` — caller-side aggregate of (request, output, run_record, signal_id, pressure_summary).
  - `run_reference_firm_pressure_mechanism(kernel, *, firm_id, as_of_date=None, evidence_refs=None, variable_observation_ids=None, exposure_ids=None, corporate_signal_ids=None, request_id=None, metadata=None)` — caller-side helper. Resolves observations from `WorldVariableBook` (hydrating each with `variable_group` from the spec lookup), exposures from `ExposureBook`, and optional corporate signals from `SignalBook`; builds the `MechanismRunRequest`; calls the adapter; commits the one proposed signal through `kernel.signals.add_signal`; constructs the `MechanismRunRecord` for audit.
- `tests/test_reference_firm_pressure.py` — 28 tests pinning every contract requirement (see §64.5 below).

### 64.2 Hard boundary

The mechanism only proposes a **pressure assessment signal**. It explicitly does **not**:

- update `FirmState` or any other firm-state book;
- update `BalanceSheetView` or any balance-sheet line item;
- update cash, leverage, revenue, margin, or any financial statement line item;
- imply accounting realisation;
- imply shareholder pressure (that is a separate stakeholder-pressure mechanism family for a later milestone);
- trigger any corporate action;
- make any economic decision;
- update prices, valuations, ownership, contracts, constraints, variables, or exposures.

Tests pin all of these as byte-equality checks across a representative sample of v0/v1/v1.8 books before/after the helper's call.

### 64.3 Pressure dimensions

Five synthetic pressure dimensions, each a deterministic float in `[0, 1]`, plus one summary:

| Dimension | Reads exposures with `exposure_type` ∈ | Reads observations with `variable_group` ∈ |
| --- | --- | --- |
| `input_cost_pressure` | `{"input_cost"}` | `{"material", "input_costs", "raw_materials"}` |
| `energy_power_pressure` | `{"input_cost"}` | `{"energy_power", "energy"}` |
| `debt_service_pressure` | `{"funding_cost", "discount_rate"}` | `{"rates", "credit"}` |
| `fx_translation_pressure` | `{"translation"}` | `{"fx"}` |
| `logistics_pressure` | `{"input_cost", "supply_chain"}` | `{"logistics", "freight", "shipping"}` |
| `overall_pressure` | (computed) | mean of the five dimensions above |

Algorithm per dimension (deterministic):

1. Collect `variable_id`s of observations whose `variable_group` is in the dimension's relevant groups.
2. Sum the magnitudes of exposures whose `exposure_type` is in the dimension's relevant types AND whose `variable_id` is in the set from step 1.
3. Clamp the sum to `[0, 1]`.

A dimension contributes only when both observation-side and exposure-side evidence intersect — which is when the firm is actually exposed *and* the pressure source is actually observable. v1.8.1's anti-scenario rule applies: empty evidence on a dimension produces 0, not silence.

### 64.4 Mechanism interface contract

The adapter implements `MechanismAdapter`:

- `apply(request: MechanismRunRequest) -> MechanismOutputBundle` reads `request.evidence`, returns proposals.
- The adapter is a frozen dataclass; two adapters with the same spec produce byte-identical outputs on byte-identical requests.
- The adapter does **not** accept a kernel parameter (a defensive test pins this — passing a kernel raises `TypeError`).
- The adapter does **not** read any book or the ledger. The contract test `test_adapter_can_run_without_a_kernel` proves the property by constructing a request with caller-supplied evidence and no kernel.
- The adapter does **not** mutate the request (the v1.9.3.1 deep-freeze property carries; we re-pin it for the concrete adapter).
- The adapter does **not** commit any proposal. Commitment is the caller's job — `run_reference_firm_pressure_mechanism` does it.

The proposed signal mapping carries:

- `signal_id` (deterministic: `signal:firm_operating_pressure_assessment:{firm_id}:{as_of_date}`)
- `signal_type = FIRM_PRESSURE_SIGNAL_TYPE`
- `subject_id` = the firm being assessed
- `source_id = FIRM_PRESSURE_SOURCE_ID`
- `published_date` / `effective_date` = `as_of_date`
- `visibility = "public"`
- `payload` = the five pressure dimensions + `overall_pressure` + `evidence_counts` + `calibration_status="synthetic"` + `status`
- `related_ids` = the optional corporate-signal ids the caller passed in
- `metadata` = `model_id`, `model_family`, `version`, `calibration_status`, plus the literal boundary statement *"pressure_assessment_signal_only; no financial-statement update; no decision; no auto-trigger"*

### 64.5 v1.9.4 success criteria

§64 is complete when **all** hold:

1. `world/reference_firm_pressure.py` exports the six controlled-vocabulary constants, `FirmPressureMechanismAdapter`, `FirmPressureMechanismResult`, and `run_reference_firm_pressure_mechanism`.
2. `FirmPressureMechanismAdapter` satisfies the v1.9.3 / v1.9.3.1 `MechanismAdapter` Protocol.
3. The adapter runs without a kernel; the contract test confirms it.
4. The adapter does not accept a kernel argument (`TypeError` otherwise).
5. Missing evidence produces `status="degraded"` rather than crashing.
6. All five pressure dimensions are in `[0, 1]`; `overall_pressure` is the mean of the five.
7. The proposed signal mapping carries every required field; the payload includes all five dimensions, `overall_pressure`, `evidence_counts`, and `calibration_status="synthetic"`.
8. The caller helper commits exactly one signal; `evidence_refs` lineage is preserved verbatim on the resulting `MechanismRunRecord`.
9. No mutation against `valuations` / `prices` / `ownership` / `contracts` / `constraints` / `exposures` / `variables` / `institutions` / `external_processes` / `relationships` / `routines` / `attention` / `interactions`.
10. The full test suite passes (1543 tests = 1515 prior + 28 firm-pressure).
11. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.

### 64.6 Anti-scope

§64 deliberately does **not** add:

- firm financial statement updates;
- balance sheet mutation;
- valuation refresh (that is v1.9.5);
- credit decision (v1.9.6);
- investor / shareholder pressure (separate `stakeholder_pressure_mechanism` family, later);
- price formation, trading, lending decisions, covenant enforcement, default;
- corporate actions, policy reactions;
- Japan calibration, real data ingestion, scenario engines;
- automatic scheduler firing.

### 64.7 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.3 Model Mechanism Inventory + Behavioral Gap Audit + Mechanism Interface | Docs + interface contract (§63). | Shipped |
| v1.9.3.1 Mechanism Interface Hardening | Code (§63.9). | Shipped |
| v1.9.4 Reference Firm Operating Pressure Assessment Mechanism | Code (§64). First concrete `MechanismAdapter`. | Shipped |
| v1.9.5 Reference Valuation Refresh Lite Mechanism | Code (§65). Second concrete `MechanismAdapter` (`valuation_mechanism` family). | Shipped |
| **v1.9.6 Living-world Mechanism Integration** | Code (§66). Wires v1.9.4 + v1.9.5 into `run_living_reference_world`. | **Shipped** |
| v1.9.7 Bank Credit Review Lite | `credit_review_mechanism` adapter. | Next |
| v1.9.8 Performance Boundary | Sparse-iteration hardening. | After v1.9.7 (now Next). |
| v1.9.last | First lightweight public prototype. | After v1.9.8 |


### 63.9 v1.9.3.1 Mechanism Interface Hardening

§63.9 (v1.9.3.1) hardens the v1.9.3 mechanism interface in three small ways before v1.9.4 introduces the first concrete mechanism. **No economic behavior; no concrete mechanism.** The change set:

1. **Deep-ish freeze for JSON-like data.** Two private helpers in `world/mechanisms.py` — `_freeze_json_like` and `_thaw_json_like` — recursively convert nested mappings to `MappingProxyType` and lists / tuples to `tuple`. The four immutable dataclasses now apply this on construction:
   - `MechanismSpec.metadata`
   - `MechanismRunRequest.evidence` / `state_views` / `parameters` / `metadata`
   - `MechanismOutputBundle` proposal tuples + `output_summary` + `metadata`
   - `MechanismRunRecord.metadata`

   `to_dict()` thaws back to plain mutable `dict` / `list` for JSON friendliness. The shallow-immutability of `frozen=True` is no longer the only line of defence; nested-dict subscript-assign is rejected at runtime. Tests (`test_mechanism_interface.py`) pin every nested-mutation refusal.
2. **Rename `MechanismInputBundle` → `MechanismRunRequest`.** The new type splits `evidence_refs` (caller-resolved lineage id tuple, verbatim) from `evidence` (resolved data the adapter reads, grouped by record-type or logical key). Adapters consume `evidence`; they do **not** read the kernel or any book — the caller resolves before invocation. `MechanismInputBundle = MechanismRunRequest` is kept as a one-line backwards-compat alias for one milestone; the alias does not restore the old `input_refs` field (callers must rename to `evidence_refs`).
3. **Clarify `MechanismRunRecord` ordering responsibility.** The record preserves caller-supplied `input_refs` / `committed_output_refs` order **verbatim** — no auto-dedupe, no auto-sort. Callers needing deterministic replay must order / dedupe their tuples themselves; mechanisms that intentionally carry meaningful order keep their order. The "preserve verbatim" property is pinned by a contract test.

The Protocol's `apply` signature changes accordingly:

```python
def apply(self, request: MechanismRunRequest) -> MechanismOutputBundle: ...
```

#### What v1.9.3.1 lands

- `world/mechanisms.py` — `_freeze_json_like` / `_thaw_json_like` helpers, the renamed `MechanismRunRequest` dataclass with the `evidence_refs` + `evidence` field split, deep-freeze applied to every JSON-like field on the four dataclasses, the updated Protocol signature, and the one-line `MechanismInputBundle = MechanismRunRequest` alias.
- `tests/test_mechanism_interface.py` — 26 new tests pinning the deep-freeze property (one per nested mutation site), the `to_dict` thaw round-trip, the alias equality, the rename / field set, the new `evidence` validation (Mapping required; non-empty string keys; lists become tuples on freeze), the `evidence_refs` verbatim storage, the caller-preserved `MechanismRunRecord.input_refs` order including duplicates, the new Protocol signature acceptance, and the "adapter does not require kernel" anti-behavior test. The original 39 tests carry forward (some renamed to use `MechanismRunRequest`).

#### What v1.9.3.1 deliberately does NOT do

- ship any concrete mechanism (those are v1.9.4 onward);
- introduce any new ledger record type;
- change v1.9.0 / v1.9.1 / v1.9.2 modules (they are byte-identical before / after);
- alter the eight ship-or-die mechanism principles;
- change the calibration / stochasticity / family vocabularies.

#### v1.9.3.1 success criteria

§63.9 is complete when **all** hold:

1. `_freeze_json_like` recursively freezes mappings → `MappingProxyType`, lists / tuples → `tuple`, sets → sorted-tuple, scalars → passthrough.
2. `_thaw_json_like` round-trips back to plain `dict` / `list`.
3. Every JSON-like field on the four dataclasses is deeply frozen on construction; subscript-assign on any nested dict raises `TypeError`.
4. `to_dict()` returns mutable `dict` / `list` copies; mutation on the thawed copy succeeds.
5. `MechanismRunRequest` is the public name; `MechanismInputBundle` is a one-line alias to the same class.
6. `evidence` is a Mapping with non-empty string keys; lists inside `evidence` are tuples after freeze.
7. `MechanismRunRecord.input_refs` and `committed_output_refs` are stored verbatim (no dedupe / sort).
8. The `MechanismAdapter` Protocol's `apply` signature is `apply(self, request: MechanismRunRequest) -> MechanismOutputBundle`.
9. The full test suite passes (1507 = 1481 prior + 26 v1.9.3.1).
10. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
11. v1.9.0 / v1.9.1 / v1.9.2 modules are byte-identical before / after.

## 65. v1.9.5 Reference Valuation Refresh Lite Mechanism

§65 (v1.9.5) ships the project's **second concrete mechanism** on the v1.9.3 / v1.9.3.1 hardened interface. It consumes the v1.9.4 firm-pressure-assessment signal (plus optional corporate reporting signals, selected observation sets, variable observations, and exposures) and proposes one **opinionated synthetic** `ValuationRecord` that is committed through the existing v1.1 `ValuationBook.add_valuation` ledger path.

### 65.1 What this is — and is not

This is **not a true valuation model**. It is a synthetic reference mechanism showing how diagnostic pressure and selected evidence can produce an auditable valuation claim. Every produced `ValuationRecord` is stamped with `method = "synthetic_lite_pressure_adjusted"`; calibration is `"synthetic"`; the metadata carries four boundary flags (`no_price_movement`, `no_investment_advice`, `synthetic_only`, `model_id`) so any reader can immediately see what the claim *isn't*.

§65 explicitly does **not**:

- form, observe, or move any market price;
- trade, allocate, or rebalance any portfolio;
- make a buy / sell / hold recommendation;
- make a lending decision;
- enforce or trip a covenant;
- update any firm financial statement, balance-sheet line item, cash, leverage, revenue, margin, or DSCR / LTV measure;
- imply that the produced `estimated_value` is canonical truth — it is *one valuer's opinionated claim* under the synthetic, jurisdiction-neutral assumptions documented in the module;
- imply investment advice;
- ingest real data, calibrate, or run a scenario engine.

### 65.2 What lands in v1.9.5

- `world/reference_valuation_refresh_lite.py` — new module:
  - Constants: `VALUATION_REFRESH_MODEL_ID`, `VALUATION_REFRESH_MODEL_FAMILY = "valuation_mechanism"` (per the v1.9.3 family vocabulary), `VALUATION_REFRESH_MECHANISM_VERSION = "0.1"`, `VALUATION_REFRESH_METHOD_LABEL = "synthetic_lite_pressure_adjusted"`, `VALUATION_REFRESH_VALUATION_TYPE = "synthetic_firm_equity_estimate"`, `VALUATION_REFRESH_PURPOSE = "reference_pressure_aware_valuation"`.
  - `ValuationRefreshLiteAdapter` — frozen dataclass implementing `MechanismAdapter`. `apply(request)` reads `request.evidence` + `request.parameters` only; returns `MechanismOutputBundle` with one `proposed_valuation_records` mapping. Adapter takes **no kernel parameter**, reads no book, and never mutates the request.
  - `ValuationRefreshLiteResult` — caller-side aggregate of (request, output, run_record, valuation_id, valuation_summary).
  - `run_reference_valuation_refresh_lite(kernel, *, firm_id, valuer_id, as_of_date=None, pressure_signal_ids=..., corporate_signal_ids=..., selected_observation_set_ids=..., variable_observation_ids=..., exposure_ids=..., baseline_value=..., currency="unspecified", numeraire="unspecified", pressure_haircut_per_unit_pressure=None, confidence_decay_per_unit_pressure=None, ...)` — caller-side helper. Resolves evidence from `SignalBook` / `WorldVariableBook` / `ExposureBook` / `AttentionBook` (selections); calls the adapter; commits the one proposed `ValuationRecord` through `kernel.valuations.add_valuation`; constructs the `MechanismRunRecord` for audit.
- `tests/test_reference_valuation_refresh_lite.py` — 28 tests pinning every contract requirement (see §65.5).

### 65.3 Algorithm

Given a v1.9.4 pressure assessment with `overall_pressure ∈ [0, 1]` and a caller-supplied `baseline_value`:

```
pressure_haircut_fraction
    = pressure_haircut_per_unit_pressure × overall_pressure
estimated_value
    = baseline_value × (1 − clamp(pressure_haircut_fraction, 0, 1))
confidence
    = clamp(1 − confidence_decay_per_unit_pressure × overall_pressure, 0, 1)
```

Default coefficients: `pressure_haircut_per_unit_pressure = 0.30`, `confidence_decay_per_unit_pressure = 0.40`. Pressure of 1.0 trims the baseline by 30% and drops confidence to 0.6. Coefficients are caller-overridable through `request.parameters`.

**Degraded path.** If no pressure assessment signal is present in evidence:

- with `baseline_value` supplied → `estimated_value = baseline_value`, `confidence = 1.0`, `status = "degraded"`;
- without `baseline_value` → `estimated_value = None`, `confidence = 0.0`, `status = "degraded"`.

The mechanism never crashes on missing optional evidence (v1.8.1 anti-scenario rule).

### 65.4 Mechanism interface contract

The adapter implements `MechanismAdapter`:

- `apply(request: MechanismRunRequest) -> MechanismOutputBundle`.
- The adapter is a frozen dataclass; deterministic across two byte-identical requests.
- The adapter does **not** accept a kernel parameter (a defensive test pins this — passing a kernel raises `TypeError`).
- The adapter does **not** read any book or the ledger (a contract test proves it by constructing a request without a kernel).
- The adapter does **not** mutate the request (the v1.9.3.1 deep-freeze property carries; we re-pin it).
- The adapter does **not** commit any proposal — the caller helper does it.

The proposed `ValuationRecord` mapping carries `valuation_id`, `subject_id`, `valuer_id`, `valuation_type`, `purpose`, `method`, `as_of_date`, `estimated_value`, `currency` / `numeraire` (default `"unspecified"`), `confidence`, `assumptions` (coefficient values + linear-haircut flag + baseline-supplied flag), `inputs` (overall_pressure, baseline_value, pressure_signal_id, evidence_counts, pressure_signal_status), `related_ids` (pressure signal id + any other signals + selected observation set ids), and `metadata` (model_id, model_family, version, calibration_status, method, the four boundary flags `no_price_movement` / `no_investment_advice` / `synthetic_only` / `model_id`, plus the `pressure_signal_id` link and the verbatim boundary statement).

### 65.5 v1.9.5 success criteria

§65 is complete when **all** hold:

1. `world/reference_valuation_refresh_lite.py` exports the constants, `ValuationRefreshLiteAdapter`, `ValuationRefreshLiteResult`, and `run_reference_valuation_refresh_lite`.
2. The adapter satisfies `MechanismAdapter`; the spec uses `model_family="valuation_mechanism"`, `calibration_status="synthetic"`, `stochasticity="deterministic"`.
3. The adapter runs without a kernel; rejects a kernel argument; does not mutate the request.
4. Missing pressure evidence yields `status="degraded"` with conservative output (baseline-only or `None`).
5. The proposed valuation carries every required field including the `synthetic_lite_pressure_adjusted` method label.
6. The metadata carries the four boundary flags and the `pressure_signal_id` link.
7. The caller helper commits exactly one `ValuationRecord` through `ValuationBook.add_valuation`; `evidence_refs` lineage is preserved verbatim on the `MechanismRunRecord`.
8. No mutation against `prices` / `ownership` / `contracts` / `constraints` / `exposures` / `variables` / `institutions` / `external_processes` / `relationships` / `routines` / `attention` / `interactions`; `signals` count is unchanged (the mechanism reads the v1.9.4 signal but emits no new `InformationSignal`).
9. The full test suite passes (1571 = 1543 prior + 28 valuation).
10. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.

### 65.6 Anti-scope

§65 deliberately does **not** add:

- price formation, trading, buy/sell decisions, portfolio rebalancing;
- lending decisions, covenant enforcement;
- firm financial statement updates;
- bank credit decisions;
- market clearing;
- Japan calibration, real data ingestion, scenario engines;
- automatic scheduler firing.

### 65.7 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.3 / v1.9.3.1 Mechanism interface + hardening | Docs + contract (§63 / §63.9). | Shipped |
| v1.9.4 Reference Firm Operating Pressure Assessment Mechanism | Code (§64). | Shipped |
| v1.9.5 Reference Valuation Refresh Lite Mechanism | Code (§65). Second concrete `MechanismAdapter`. | Shipped |
| v1.9.6 Living-world Mechanism Integration | Code (§66). Wires v1.9.4 + v1.9.5 into the multi-period sweep. | Shipped |
| **v1.9.7 Reference Bank Credit Review Lite Mechanism** | Code (§67). Third concrete `MechanismAdapter` (`credit_review_mechanism` family) + integration into the multi-period sweep. | **Shipped** |
| v1.9.8 Performance Boundary | Sparse-iteration hardening. | Next |
| v1.9.last | First lightweight public prototype. | After v1.9.8 |

## 66. v1.9.6 Living-world Mechanism Integration

§66 (v1.9.6) wires the v1.9.4 firm-pressure-assessment and v1.9.5 valuation-refresh-lite mechanisms into the multi-period `run_living_reference_world` sweep. Until v1.9.6, both mechanisms shipped as **standalone** caller helpers — they were tested in isolation but the living-world demo did not exercise them per period. The user-visible result was that the `run_living_reference_world()` trace did not show the chain the v1.9.x mechanisms were supposed to populate. v1.9.6 closes that integration gap.

The integrated per-period flow is now:

```
corporate quarterly reporting           (v1.8.7 — per firm)
    →
firm operating pressure assessment      (v1.9.4 — per firm)
    →
heterogeneous attention                 (v1.8.5 / v1.8.11 / v1.8.12 — per actor)
    →
valuation refresh lite                  (v1.9.5 — per investor × firm)
    →
investor / bank review                  (v1.8.13 — per actor)
```

§66 introduces **no new mechanism** and **no new ledger record type**. It is pure integration plus the additive period-summary fields needed to expose the new ids. Bank-side valuation is intentionally out of scope for v1.9.6 — a future stakeholder-pressure milestone may extend it.

### 66.1 What lands in v1.9.6

- `world/reference_living_world.py`:
  - `LivingReferencePeriodSummary` extended additively with four tuples: `firm_pressure_signal_ids`, `firm_pressure_run_ids` (one entry per firm), `valuation_ids`, `valuation_mechanism_run_ids` (one entry per investor × firm pair). Default empty tuples preserve compatibility for any caller building a summary by hand.
  - `run_living_reference_world` extended with a new pressure phase between corporate reporting and the attention phase, and a new valuation phase between selections and reviews. Per period: each firm runs `run_reference_firm_pressure_mechanism` with all visible variable observations + the firm's own `ExposureBook` rows + the firm's corporate signal as evidence. After selections, each (investor, firm) pair runs `run_reference_valuation_refresh_lite` with the firm's pressure signal + the firm's corporate signal + the investor's selection + a caller-supplied baseline (default `1_000_000.0` per firm, overridable via `firm_baseline_values` mapping).
  - Two new keyword-only parameters: `firm_baseline_values: Mapping[str, float] | None = None` and `valuation_baseline_default: float = 1_000_000.0`.
  - The valuation request_id is built per (investor, firm, period) so multi-investor valuations on the same firm/period don't collide on the audit lineage (the v1.9.5 default request_id formula did not include the valuer; v1.9.6 supplies an explicit one).
- `examples/reference_world/run_living_reference_world.py`:
  - Synthetic firm exposures added to the seed fixture (`firm:reference_manufacturer_a` → fx + rates + energy; `firm:reference_retailer_b` → fx + rates; `firm:reference_utility_c` → energy + rates) so the v1.9.4 mechanism produces non-zero output during the sweep.
  - The compact `[period N]` trace line now includes `pressures=...` and `valuations=...` columns.
  - The `[summary]` line names the integrated chain and the boundary statement: *"No price formation, no trading, no lending decisions, no firm financial statement updates, no canonical-truth valuation, no investment advice."*
- `world/living_world_report.py`:
  - `LivingWorldPeriodReport` extended additively with `pressure_signal_count` + `valuation_count` (default 0).
  - The Markdown per-period table grows two columns (`pressures`, `valuations`).
- `examples/reference_world/living_world_replay.py`:
  - `_canonicalize_period` includes the four new id tuples so the deterministic SHA-256 living-world digest reflects pressure / valuation activity.
- `tests/test_living_reference_world.py`:
  - Fixture `_seed_exposures` adds the same firm exposures as the CLI.
  - Record-count budget updated: per period now produces ~31 records (previously ~22); the lower-bound formula and the upper bound (≤ 250) are both pinned.
  - **Nine new tests** for v1.9.6 integration: one pressure signal per firm per period; pressure signals resolve to stored `firm_operating_pressure_assessment` signals; one valuation per (investor, firm) per period; valuations resolve to stored `synthetic_lite_pressure_adjusted` records; valuation metadata carries the `pressure_signal_id` link to the correct firm's pressure signal (proves v1.9.5 actually consumed v1.9.4's output); valuation metadata carries the four boundary flags; pressure / valuation run-record ids are unique per period.
  - The no-mutation guarantee is *narrowed*: `valuations` is now expected to grow (one new record per investor × firm × period), so it is removed from the byte-equality snapshot. A separate `test_valuation_count_grows_by_expected_amount` pins the exact growth.

### 66.2 Algorithm-side details

- **Pressure inputs.** The v1.9.6 helper passes *all visible variable observations* on the as-of date as evidence, plus the firm's exposures (filtered via `kernel.exposures.list_by_subject(firm_id)`), plus the firm's corporate signal as optional auxiliary evidence. The v1.9.4 mechanism filters the observations / exposures by its own pressure-dimension definitions; the helper's job is just to surface candidate evidence.
- **Pressure signal visibility for selection.** v1.9.4 emits the pressure signal with `visibility="public"`, so it would show up in any future menu builder query. v1.9.6 deliberately does **not** extend `AttentionProfile.watched_signal_types` to include `firm_operating_pressure_assessment` — selecting pressure signals via attention is a separate v1.9.x concern. Instead, v1.9.6 surfaces the pressure signal to the valuation mechanism by direct id-passing, which is the cleanest separation of *availability* from *selection*.
- **Valuation request_id formula.** Default v1.9.5 request_id is `req:valuation_refresh_lite:{firm}:{date}`, which would collide when multiple investors value the same firm on the same date. v1.9.6 overrides it with `req:valuation_refresh_lite:{investor}:{firm}:{date}` so each `mechanism_run:` audit id is unique.
- **Bank-side valuation.** Out of scope for v1.9.6. Banks still build menus, selections, and review notes — they just don't issue valuations. A stakeholder-pressure mechanism family (later milestone) may consume bank attention as separate input.

### 66.3 Per-period record-count after integration

With the default fixture (3 firms, 2 investors, 2 banks, 4 periods):

```
per period:
    firms × (corp_run + corp_signal)            = 6
    firms × pressure_signal                      = 3
    (investors + banks) × (menu + selection)    = 8
    investors × firms × valuation                = 6
    (investors + banks) × (review_run + signal) = 8
    -------------------------------------------------
    total per period                            = 31
× 4 periods                                     = 124
+ infra prelude (~14 records)                   ≈ 138
```

The budget guard (`test_living_world_stays_within_record_budget`) was tightened to require ≥ 124 (per-period work × 4) and ≤ 250 — well below the dense product space, so accidental quadratic loops fail the test loudly.

### 66.4 Anti-scope (carried forward)

§66 is integration only. v1.9.6 deliberately does **not** add:

- bank credit review lite (v1.9.7);
- lending decisions, trading, price formation, portfolio decisions, covenant enforcement;
- firm financial statement updates;
- canonical-truth valuation claims;
- Japan calibration, real data ingestion, scenario engines, automatic scheduler firing.

The v1.9.4 / v1.9.5 hard boundaries carry through end-to-end: every committed pressure signal still stamps `pressure_assessment_signal_only` in metadata; every committed valuation still stamps `no_price_movement` / `no_investment_advice` / `synthetic_only`.

### 66.5 v1.9.6 success criteria

§66 is complete when **all** hold:

1. `run_living_reference_world` invokes `run_reference_firm_pressure_mechanism` once per firm per period and `run_reference_valuation_refresh_lite` once per (investor × firm) per period.
2. `LivingReferencePeriodSummary` exposes `firm_pressure_signal_ids` / `firm_pressure_run_ids` / `valuation_ids` / `valuation_mechanism_run_ids`.
3. The CLI trace shows `pressures=...` and `valuations=...` columns; the summary line names the integrated chain.
4. The v1.9.1 Markdown report includes `pressures` and `valuations` columns in the per-period table.
5. The v1.9.2 canonical view (and therefore the SHA-256 digest) reflects pressure / valuation activity.
6. The v1.9.0 record-count budget is updated (≥ 124, ≤ 250); the no-mutation test allows valuations to grow but pins the exact count via a separate test.
7. Every committed valuation's `pressure_signal_id` points to *the same period's pressure signal for the same firm* (proving v1.9.5 actually consumed v1.9.4's output).
8. Mechanism run ids are unique per (investor, firm, period) — the v1.9.5 default request_id formula is overridden in the helper.
9. The full test suite passes (1580 = 1571 prior + 9 v1.9.6 integration).
10. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
11. v1.9.0 / v1.9.1 / v1.9.2 / v1.9.3 / v1.9.4 / v1.9.5 standalone semantics are unchanged (additive extension throughout).

### 66.6 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.4 Reference Firm Operating Pressure Assessment Mechanism | Code (§64). | Shipped |
| v1.9.5 Reference Valuation Refresh Lite Mechanism | Code (§65). | Shipped |
| v1.9.6 Living-world Mechanism Integration | Code (§66). | Shipped |
| **v1.9.7 Reference Bank Credit Review Lite Mechanism** | Code (§67). | **Shipped** |
| v1.9.8 Performance Boundary | Sparse-iteration hardening. | After v1.9.7 (now Next). |
| v1.9.last | First lightweight public prototype. | After v1.9.8 |

## 67. v1.9.7 Reference Bank Credit Review Lite Mechanism

§67 (v1.9.7) ships the project's **third concrete mechanism** on the v1.9.3 / v1.9.3.1 hardened interface, plus its integration into the multi-period `run_living_reference_world` sweep. It consumes resolved evidence — firm pressure assessment signals (v1.9.4), opinionated valuation claims (v1.9.5), the bank's own selected observation set, corporate reporting signals, and exposure records — and proposes one synthetic `bank_credit_review_note` signal per (bank, firm) per period.

### 67.1 What this is — and is not

This is **not a lending decision model**. It is a synthetic reference mechanism showing how a bank could review credit-relevant evidence without changing contracts, rates, covenants, or lending status. Every produced signal carries a verbatim boundary statement in metadata so downstream readers cannot mistake the diagnostic note for a decision.

§67 explicitly does **not**:

- approve / reject any loan;
- enforce or trip any covenant;
- mutate `ContractBook`, `ConstraintBook`, or any other source-of-truth book beyond the single `SignalBook.add_signal` write;
- change interest rates or any other contract field;
- detect or declare default;
- form, observe, or move any market price;
- imply that any score is a *probability of default*, an *internal rating*, or any other regulator-recognised credit measure;
- imply investment advice;
- ingest real data, calibrate to any real economy, or run a scenario engine.

### 67.2 What lands in v1.9.7

- `world/reference_bank_credit_review_lite.py` — new module with `BANK_CREDIT_REVIEW_MODEL_ID`, `BANK_CREDIT_REVIEW_MODEL_FAMILY = "credit_review_mechanism"`, `BANK_CREDIT_REVIEW_MECHANISM_VERSION = "0.1"`, `BANK_CREDIT_REVIEW_SIGNAL_TYPE = "bank_credit_review_note"`. `BankCreditReviewLiteAdapter` (frozen dataclass implementing `MechanismAdapter`; reads `request.evidence` + `request.parameters` only; no kernel parameter; no book access; no mutation). `BankCreditReviewLiteResult`. `run_reference_bank_credit_review_lite(kernel, *, bank_id, firm_id, as_of_date=None, pressure_signal_ids=..., valuation_ids=..., selected_observation_set_ids=..., corporate_signal_ids=..., exposure_ids=..., variable_observation_ids=..., ...)` caller-side helper. **Default request_id formula includes both bank_id AND firm_id** so multi-bank reviews on the same firm don't alias on the `mechanism_run:` audit id (the v1.9.5 default formula had this collision; v1.9.6 worked around it; v1.9.7 makes it impossible by construction).
- `world/reference_living_world.py` — integrated into the per-period flow. New phase between valuation refresh and reviews. `LivingReferencePeriodSummary` extended additively with `bank_credit_review_signal_ids` + `bank_credit_review_mechanism_run_ids` (one entry per bank × firm pair).
- `examples/reference_world/run_living_reference_world.py` — `[period N]` trace adds `credit_reviews=...`; summary line names the bank-credit-review-lite step and the boundary set.
- `world/living_world_report.py` — `LivingWorldPeriodReport` adds `credit_review_signal_count`; Markdown per-period table grows the `credit_reviews` column.
- `examples/reference_world/living_world_replay.py` — canonical view includes the new id tuples (digest reflects credit-review activity).
- `tests/test_reference_bank_credit_review_lite.py` — 29 tests pinning the standalone contract.
- `tests/test_living_reference_world.py` — 7 new v1.9.7 integration tests; record-count budget updated (per period now ~37 records; ≥ 148, ≤ 280); CLI smoke updated.

### 67.3 Credit review dimensions

Five synthetic dimensions, each a deterministic float in `[0, 1]`:

| Dimension | How it is computed |
| --- | --- |
| `operating_pressure_score` | Verbatim copy of the firm's pressure signal `payload.overall_pressure`. |
| `valuation_pressure_score` | `1 − mean(valuation.confidence)` across all supplied valuations on the firm. High-confidence valuations imply low pressure; low-confidence implies "look harder". |
| `debt_service_attention_score` | Verbatim copy of the firm pressure signal's `payload.debt_service_pressure`. |
| `collateral_attention_score` | Verbatim copy of the firm pressure signal's `payload.fx_translation_pressure` (synthetic stand-in; a fuller model would consume the bank's own collateral exposures). |
| `information_quality_score` | Coverage metric in `[0, 1]`: 0.25 per present evidence channel (pressure / valuation / corporate-report / selection). Maxes at 1.0. |

Plus one summary:

- `overall_credit_review_pressure` — deterministic mean of the **four pressure-side scores** (operating + valuation + debt_service + collateral). `information_quality_score` is a *coverage* metric and does **not** enter the mean.

**This is not a probability of default.** **This is not an internal rating.** **This is not a lending decision.**

### 67.4 Mechanism interface contract

The adapter implements `MechanismAdapter`:

- `apply(request: MechanismRunRequest) -> MechanismOutputBundle`.
- The adapter is a frozen dataclass; deterministic across two byte-identical requests.
- The adapter does **not** accept a kernel parameter (defensive test pins this).
- The adapter does **not** read any book or the ledger (contract test proves it by constructing a request without a kernel).
- The adapter does **not** mutate the request (the v1.9.3.1 deep-freeze property carries; we re-pin it).
- The adapter does **not** commit any proposal — the caller helper does it.

The proposed signal mapping carries `signal_id` (deterministic: `signal:bank_credit_review_note:{bank_id}:{firm_id}:{as_of_date}`), `signal_type = "bank_credit_review_note"`, `subject_id` = the firm being reviewed, `source_id` = the reviewing bank, `published_date` / `effective_date` = `as_of_date`, `visibility = "public"`, `payload` (the five scores + overall + evidence_counts + calibration_status + status + pressure_signal_id link), `related_ids` (pressure signal id + every valuation on that firm + corporate signal + selection ids), and `metadata` with eight boundary flags: `no_lending_decision`, `no_covenant_enforcement`, `no_contract_mutation`, `no_constraint_mutation`, `no_default_declaration`, `no_internal_rating`, `no_probability_of_default`, `synthetic_only`, plus the verbatim `boundary` string.

### 67.5 Per-period record-count after integration

With the default fixture (3 firms, 2 investors, 2 banks, 4 periods):

```
per period:
    firms × (corp_run + corp_signal)            = 6
    firms × pressure_signal                      = 3
    (investors + banks) × (menu + selection)    = 8
    investors × firms × valuation                = 6
    banks × firms × credit_review_signal         = 6   ← v1.9.7
    (investors + banks) × (review_run + signal) = 8
    -------------------------------------------------
    total per period                            = 37   (was 31)
× 4 periods                                     = 148
+ infra prelude (~14 records)                   ≈ 162
```

The budget guard is now ≥ 148 (per-period × 4) and ≤ 280.

### 67.6 v1.9.7 success criteria

§67 is complete when **all** hold:

1. `world/reference_bank_credit_review_lite.py` exports the constants, `BankCreditReviewLiteAdapter`, `BankCreditReviewLiteResult`, and `run_reference_bank_credit_review_lite`.
2. The adapter satisfies `MechanismAdapter`; `model_family="credit_review_mechanism"`, `calibration_status="synthetic"`, `stochasticity="deterministic"`.
3. The adapter runs without a kernel; rejects a kernel argument; does not mutate the request.
4. Missing pressure + valuation evidence yields `status="degraded"` with zero scores; with only one of the two channels still yields `"completed"`.
5. The proposed signal carries every required field including the eight boundary flags.
6. The caller helper commits exactly one `InformationSignal` through `SignalBook.add_signal`; `evidence_refs` lineage preserved verbatim on the `MechanismRunRecord`.
7. The default request_id formula includes both bank_id and firm_id (no v1.9.5-style collision).
8. Living-world integration produces one credit review per (bank, firm) per period; `payload.pressure_signal_id` links to the same firm's pressure signal for the same period; `related_ids` thread valuations on that firm.
9. No mutation of `contracts`, `constraints`, `prices`, `ownership`, `valuations` (after the v1.9.5 phase), `exposures`, `variables`, `institutions`, `external_processes`, `relationships`, `routines`, `attention`, `interactions`.
10. The full test suite passes (1616 = 1580 prior + 29 standalone + 7 integration).
11. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.

### 67.7 Anti-scope

§67 deliberately does **not** add: lending decisions, loan approval / rejection; covenant enforcement, default declaration; interest-rate changes, contract mutation, constraint mutation; price formation, trading, investor decisions; firm financial statement updates; Japan calibration, real data ingestion, scenario engines, automatic scheduler firing.

### 67.8 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.4 Reference Firm Operating Pressure Assessment Mechanism | Code (§64). | Shipped |
| v1.9.5 Reference Valuation Refresh Lite Mechanism | Code (§65). | Shipped |
| v1.9.6 Living-world Mechanism Integration | Code (§66). | Shipped |
| v1.9.7 Reference Bank Credit Review Lite Mechanism | Code (§67). | Shipped |
| v1.9.8 Performance Boundary / Sparse Traversal Discipline | Docs + tests (§68). | Shipped |
| **v1.9.last Public Prototype Freeze** | Docs-only (§69). | **Shipped** |









## 68. v1.9.8 Performance Boundary / Sparse Traversal Discipline

### 68.1 Purpose

§68 is a **discipline milestone**, not a behaviour milestone. The runtime, the kernel, and every mechanism are unchanged. What v1.9.8 adds is a written, test-pinned contract about *traversal shape*: which loops are bounded, which loops are demo-only, which record types are forbidden, and what sparse-gating principles future production-scale traversal must follow.

The motivation is concrete. From v1.9.0 to v1.9.7, the living reference world grew bounded all-pairs loops — `O(P × I × F)` for valuation refresh and `O(P × B × F)` for bank credit review. Those products are fine *only* because the fixture is deliberately tiny (3 firms, 2 investors, 2 banks, 4 periods). The same loop shape over a production-scale agent population would scale super-linearly. v1.9.8 records this so that no future contributor can quietly turn the demo into a dense all-to-all simulator.

### 68.2 What lands at v1.9.8

- `docs/performance_boundary.md` — single-file written contract. Covers: current loop shapes per phase, per-period record-count breakdown (`2F + F + 2(I+B) + IF + BF + 2(I+B) = 37` for the default fixture), v1.9 demo discipline, sparse-gating principles for future production scale, future native-acceleration position (deferred), and the semantic caveat that **review is not origination**.
- `tests/test_living_reference_world_performance_boundary.py` — 10 tests pinning every claim in the doc.
- A `count_expected_living_world_records(*, firms, investors, banks, periods)` helper inside the test module — a written, reusable formula for the budget.
- v1.9 plan, behavioral gap audit, model mechanism inventory, README, and test inventory updated.

### 68.3 Loop shapes (v1.9.7 frozen)

`P` = periods, `F` = firms, `I` = investors, `B` = banks.

| Phase                                | Loop shape                              | v1.9 default        |
| ------------------------------------ | --------------------------------------- | ------------------- |
| Corporate quarterly reporting        | `O(P × F)`                              | 4 × 3 = 12          |
| Firm pressure assessment (v1.9.4)    | `O(P × F × n_exposures)`                | ~30                 |
| Menu construction (per actor)        | `O(P × (I+B) × n_relevant_obs)`         | ~64                 |
| Observation set selection            | `O(P × (I+B))`                          | 4 × 4 = 16          |
| Valuation refresh lite (v1.9.5)      | `O(P × I × F)`                          | 4 × 2 × 3 = 24      |
| Bank credit review lite (v1.9.7)     | `O(P × B × F)`                          | 4 × 2 × 3 = 24      |
| Review routines                      | `O(P × (I+B))`                          | 4 × 4 = 16          |
| Reporting / replay / manifest        | `O(R)` over emitted ledger records      | linear scan         |

The two **bounded all-pairs** loops are the valuation `O(P × I × F)` and the credit review `O(P × B × F)`. These are the loops that v1.9.8 explicitly classifies as *demo-bounded monitoring*, allowed only because `I`, `B`, `F` are small constants in the fixture.

### 68.4 v1.9 demo discipline (test-pinned)

1. **All-pairs traversal is allowed inside fixed demo-size fixtures only.** No growth of `F`, `I`, or `B` beyond a small constant without a milestone that first introduces sparse gating.
2. **No path enumeration.** No mechanism iterates over reachable paths in any graph (interactions, ownership, relationships, exposures). Path-shaped views remain diagnostic, not operational.
3. **No hidden quadratic loops.** The **per-run total** record count (i.e. across all four periods of a default sweep) is pinned to `≥ 148` (= per-period formula × 4 periods) and `≤ 180` (= 148 + a 32-record one-off-setup allowance). The per-period count itself is 37; the budget bound is a run total, not a per-period bound. Any change adding a `(actor × actor)` or `(actor × event × firm)` loop fails the test.
4. **Tensor / matrix views are diagnostic.** v1.8 interaction tensor (`S × S × C`) and matrix views are not execution traversal plans and are not materialised on the per-period sweep path.
5. **Reporting cost is `O(R)`.** Living-world report, replay-canonicalisation, and manifest are linear scans over the ledger record list.

### 68.5 Sparse-gating principles (future, not implemented)

When future scaling lifts the demo-bounded ceiling, these gating principles apply. None are implemented in v1.9.x; they are pinned here so a future contributor cannot quietly skip them.

- **Bank credit review** must be gated by *(bank, firm)* relationships from `ContractBook` exposures (loans, guarantees, derivatives), held positions, watchlists, sector mandates, or credit-monitoring relationships.
- **Investor valuation** must be gated by holdings, coverage universes, mandates, or watchlists.
- **Menus** must be built from actor-specific exposure / relationship / visibility indexes.
- **Interaction tensor and matrix views** are diagnostic, not traversal plans.

### 68.6 Forbidden record types

`tests/test_living_reference_world_performance_boundary.py::test_no_forbidden_mutation_records_appear` asserts none of the following appear in the ledger after a default sweep:

```
ORDER_SUBMITTED              CONTRACT_CREATED
PRICE_UPDATED                CONTRACT_STATUS_UPDATED
OWNERSHIP_TRANSFERRED        CONTRACT_COVENANT_BREACHED
```

These are the trade-execution / price-formation / loan-origination / covenant-enforcement mutation events. v1.9 is review-only; if any appear, the demo has crossed a behaviour boundary.

### 68.7 Future native acceleration (deferred)

Python remains adequate for v1.9. The bounded sweep finishes in well under one second; the full 1626-test suite runs in under ten. Candidate hot paths *if* future scaling demands a native component:

- large-scale exposure joins (`ExposureBook` cross-products),
- large menu construction over big visibility indexes,
- a market mechanism / limit order book simulation,
- dense tensor / matrix views if ever materialised on the per-period path,
- repeated valuation / credit-review sweeps over large agent populations.

**The first step toward scale is profiling and sparse indexing, not a premature native rewrite.** No C++, no Julia, no Rust, no GPU work is in scope for v1.9.x or v1.9.last.

### 68.8 Semantic caveat — review is not origination

A frequent misreading of v1.9.7's `B × F` loop is that it describes a real lending-decision flow. It does not. v1.9.7 produces *review notes* — diagnostic signals about what a bank looked at and how the evidence aggregated as a pressure score. v1.9.7 does not approve, reject, or originate any loan; does not enforce any covenant; does not mutate `ContractBook` or `ConstraintBook`; does not declare default; does not imply a probability of default or an internal rating.

A realistic origination workflow — *firm funding request → bank underwriting → proposed terms → contract mutation* — is **future work**, not v1.9.x. The current dense `B × F` loop is demo-bounded monitoring, used so that every bank records one note about every firm each period for explainability.

### 68.9 v1.9.8 success criteria

§68 is complete when **all** hold:

1. `docs/performance_boundary.md` exists and covers all eight subsections (purpose, current loop shapes, demo discipline, sparse-gating principles, future native acceleration, semantic caveat, test pins, position).
2. `tests/test_living_reference_world_performance_boundary.py` exists and contains the 10 listed tests, all passing.
3. `count_expected_living_world_records` returns `148` for the default fixture and scales linearly in `periods`.
4. Total ledger record count for a default 4-period run sits in `[148, 180]` — note this is a per-run total (per-period count is 37), not a per-period bound.
5. Per-period record shape is constant across all four periods.
6. Pressure-signal count = `P × F`; valuation count = `P × I × F`; credit-review count = `P × B × F`.
7. None of the six forbidden mutation record types appear in the ledger after a default sweep.
8. No `WARNING` / `ERROR` records appear in the ledger after a default sweep.
9. The full test suite passes (`1626 = 1616 prior + 10 v1.9.8`).
10. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.

### 68.10 Anti-scope

§68 deliberately does **not** add: any new economic behaviour, any new mechanism, any new `MechanismAdapter`, any new ledger record type, any new book; price formation, trading, lending decisions, loan origination, covenant enforcement, contract or constraint mutation; native (C++ / Julia / Rust / GPU) rewrites; profiling harnesses or benchmark suites; Japan calibration, real data ingestion. v1.9.8 is documentation and tests only.

### 68.11 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.6 Living-world Mechanism Integration | Code (§66). | Shipped |
| v1.9.7 Reference Bank Credit Review Lite Mechanism | Code (§67). | Shipped |
| v1.9.8 Performance Boundary / Sparse Traversal Discipline | Docs + tests (§68). | Shipped |
| **v1.9.last Public Prototype Freeze** | Docs-only (§69). | **Shipped** |


## 69. v1.9.last Public Prototype Freeze

### 69.1 Purpose

§69 is a **freeze**, not a behaviour milestone. The runtime, the kernel, and every mechanism are unchanged. v1.9.last consolidates v1.9.0 through v1.9.8 into a coherent reader-facing public prototype: synthetic-only, CLI-first, deterministic, explainability-first, and explicitly *not* a forecasting or investment-advice tool.

The motivation is simple. Through v1.9.0 → v1.9.8 the project added enough capability that a first-time reader can now *run* the engine end-to-end and see meaningful ledger activity — corporate reports, pressure assessments, valuations, credit-review notes, attention divergence, review routines — all reconstructable from a single append-only ledger. v1.9.last is the milestone that says: *that is the public prototype*. Stop adding capability sideways; freeze the framing; document what is and is not claimed; let CI verify the freeze.

### 69.2 What lands at v1.9.last

- `docs/v1_9_public_prototype_summary.md` — single-page reader-facing summary covering: what v1.9.last *is* (the lightweight public prototype), what is frozen (CLI surface, default fixture, per-period flow, reproducibility surface, performance boundary, test surface, scope language), what v1.9.last does **not** claim (12-item normative list), how to verify locally in a few minutes, and the next path after v1.9.last.
- `README.md` (repo root) — adds a "Current public prototype (v1.9.last)" section near the top with the one-command demo block, the per-period flow table, the default fixture, the per-period and per-run record budgets, and the explicit "what v1.9.last deliberately does NOT do" list. Roadmap row flips to Shipped (1626 tests).
- `RELEASE_CHECKLIST.md` — refreshed v1.9.last public prototype gate. Splits the gate into Code health (pytest 1626 / compileall / ruff / gitleaks), Demo (operational trace / Markdown / manifest, each byte-deterministic across runs), and Scope and wording (README scope read, hard-boundary language, public/private agreement, forbidden-token scan, no proprietary content, no investment-advice framings, CI green on the tag commit). Renames the headline expected-test count from `725` to `1626`. v1.8.0's historical readiness snapshot is preserved unchanged.
- `docs/public_prototype_plan.md` — flipped from "plan-only" to "v1.9.last freeze landed".
- `docs/v1_9_living_reference_world_plan.md` — appended a "v1.9.last — what shipped" section.
- `docs/fwe_reference_demo_design.md` — added a v1.9.last update note clarifying that the headline runnable artifact is now `run_living_reference_world.py`, not the v1.7-era one-shot demo.
- `examples/reference_world/README.md` — promoted the living reference world to the headline demo, with the per-period flow table and the eight-flag hard boundary.
- `docs/test_inventory.md` — bumped the headline to v1.9.last (test count unchanged at 1626).

### 69.3 What is frozen by v1.9.last

The freeze surface is intentionally narrow:

- **The CLI surface.** Three reproducible entry points:
  ```bash
  python -m examples.reference_world.run_living_reference_world
  python -m examples.reference_world.run_living_reference_world --markdown
  python -m examples.reference_world.run_living_reference_world --manifest /tmp/fwe_living_world_manifest.json
  ```
  Two consecutive runs are byte-identical for each mode.
- **The default fixture.** 3 firms × 2 investors × 2 banks × 4 periods. All identifiers `*_reference_*`. All numbers illustrative round numbers.
- **The per-period flow.** corporate quarterly reporting → firm operating-pressure assessment (v1.9.4) → heterogeneous investor / bank attention → valuation refresh lite (v1.9.5) → bank credit review lite (v1.9.7) → investor / bank review routines.
- **The reproducibility surface.** v1.9.1 Markdown report and v1.9.2 `living_world_manifest.v1` JSON manifest with SHA-256 `living_world_digest`. Both byte-deterministic.
- **The performance boundary.** Per-period 37 records, per-run total `[148, 180]`. Bounded all-pairs loops `O(P × I × F)` and `O(P × B × F)` allowed only because the fixture is small and synthetic. Production-scale traversal must be sparse and gated; see §68.
- **The test surface.** 1626 / 1626 passing. `compileall` clean. `ruff check .` clean.
- **The scope language.** README, reference-world README, public-prototype plan, public-prototype summary, performance-boundary doc, and `RELEASE_CHECKLIST.md` all agree on what the prototype is and is not.

### 69.4 What v1.9.last does NOT claim

Normative; the freeze is conditional on every line remaining true:

- **Not a forecast.** No prediction of markets, prices, returns, defaults, or any real-world quantity.
- **Not investment advice.** No direct ("buy X") or indirect ("a portfolio with exposure E would experience O") framing in code, docs, or demo output.
- **No price formation.** No order matching, no microstructure, no `PRICE_UPDATED` records.
- **No trading.** Investor portfolios are static. No `ORDER_SUBMITTED` records.
- **No lending decisions.** v1.9.7 produces *bank credit review notes* — diagnostic signals, not loan approvals, rejections, or originations. No `CONTRACT_CREATED` / `CONTRACT_STATUS_UPDATED` / `CONTRACT_COVENANT_BREACHED` / `OWNERSHIP_TRANSFERRED` records on the default sweep.
- **No firm financial-statement updates.** v1.9.4 is pressure assessment, not bookkeeping.
- **No canonical valuations.** v1.9.5 produces one valuer's opinionated synthetic claim per `(investor, firm, period)`, stamped `no_price_movement` / `no_investment_advice` / `synthetic_only`.
- **No Japan calibration.** Forbidden-token scan against `world/experiment.py::_FORBIDDEN_TOKENS` is clean. v2 has not started.
- **No real data.** No public-data feeds wired. No paid feeds. No expert-interview content. Every fixture is a constant.
- **No scenarios.** No stress logic, no shock injection, no scenario branching, no policy reaction function.
- **No production-scale traversal.** Demo-bounded all-pairs loops only. See §68.
- **No native rewrite.** Python is adequate. No C++ / Julia / Rust / GPU work in scope.
- **No web UI.** CLI is the interface. No hosted service.

### 69.5 Position vs prior v1.8 release

v1.8.0 was tagged `v1.8-public-release` at commit `7fa2c42` and remains unchanged. v1.9.last is layered on top:

- v1.8.0's public release shipped the v1.7 reference financial system + the v1.8 experiment harness. The endogenous activity stack was v1.8.x in-progress; the demo was a single-day causal trace.
- v1.9.last ships the **endogenous activity stack as the demo**, with the v1.9 multi-period sweep + three review-only mechanisms in front. A reader visiting the repo at v1.9.last sees `run_living_reference_world.py` as the headline capability, not a record-types tour.

The repo's existing public-release gate covers v1.9.last (its checks are framing-neutral); v1.9.last adds the Public-prototype-specific gate as a separate section in `RELEASE_CHECKLIST.md`.

### 69.6 v1.9.last success criteria

§69 is complete when **all** hold:

1. `docs/v1_9_public_prototype_summary.md` exists and covers the four sections: what v1.9.last *is*, what is frozen, what is NOT claimed, how to verify, position in the version sequence, next path after v1.9.last.
2. `README.md` has a "Current public prototype (v1.9.last)" section with the one-command demo block, the per-period flow table, the default fixture, and the explicit anti-claim list.
3. `RELEASE_CHECKLIST.md` has a v1.9.last-specific gate covering Code health, Demo (operational / Markdown / manifest), and Scope and wording.
4. `docs/public_prototype_plan.md` is no longer "plan-only".
5. `docs/v1_9_living_reference_world_plan.md` carries a "v1.9.last — what shipped" section.
6. `docs/world_model.md` carries this §69.
7. The full test suite passes (`1626 / 1626`).
8. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
9. The forbidden-token word-boundary scan is clean.
10. No marketing language ("predicts markets", "production-ready", "Japan market simulator", buyout-target, etc.) appears in `README.md` or any `docs/*.md`.

### 69.7 Anti-scope

§69 deliberately does **not** add: any new economic behaviour, any new mechanism, any new `MechanismAdapter`, any new ledger record type, any new book; price formation, trading, lending decisions, loan origination, covenant enforcement, contract or constraint mutation; native (C++ / Julia / Rust / GPU) rewrites; profiling harnesses or benchmark suites; web UI; Japan calibration; real-data ingestion. v1.9.last is documentation only.

### 69.8 Position in the v1.9 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.6 Living-world Mechanism Integration | Code (§66). | Shipped |
| v1.9.7 Reference Bank Credit Review Lite Mechanism | Code (§67). | Shipped |
| v1.9.8 Performance Boundary / Sparse Traversal Discipline | Docs + tests (§68). | Shipped |
| **v1.9.last Public Prototype Freeze** | Docs-only (§69). | **Shipped** |
| **v1.10.0 Universal Engagement / Strategic Response Consolidation** | Docs-only (§70). | **In progress** |
| v1.10.1 Stewardship theme signal | Code. Concrete `signal`-shaped record + minimal book. | Planned |
| v1.10.2 Portfolio-company dialogue record | Code. Dialogue book + record shape. | Planned |
| v1.10.3 Investor escalation candidate + corporate strategic response candidate | Code. Two `MechanismAdapter` implementations. | Planned |
| v1.10.4 Optional industry demand condition signal | Code. Optional context-signal book. | Optional |
| v1.10.5 Living-world integration | Code. Wires v1.10.1–v1.10.3 into the multi-period sweep. | Planned |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

## 70. v1.10.0 Universal Engagement / Strategic Response Consolidation

### 70.1 Purpose

§70 is a **design / consolidation** milestone, not a behavior milestone. The runtime, the kernel, and every mechanism are unchanged. v1.10.0 names the *engagement and response* layer of FWE — the relational surface where investor stewardship themes, portfolio-company dialogues, investor escalation candidates, and corporate strategic response candidates are recorded — and locks that layer's scope as **signal-only and jurisdiction-neutral** before any v1.10.x code is written.

The motivation is structural. v1.9 closed the diagnostic loop: corporate quarterly reports → firm operating-pressure assessment → heterogeneous attention → valuation refresh lite → bank credit review lite → review routines, all on an append-only ledger. That loop is observation-and-assessment-only. It does not yet name the relational surface where investors raise themes with firms, where firms respond, where dialogues are recorded, where an investor escalates, and where a firm sketches a strategic response. v1.10 names that surface and gives it a vocabulary so the v1.10.x milestones can implement it without re-litigating direction.

The full design lives in `docs/v1_10_universal_engagement_and_response_design.md`. This section is the §-anchored summary in `world_model.md`.

### 70.2 Selected concepts

v1.10 selects four concrete primitives plus one optional context signal:

1. **`stewardship_theme_signal`** — names a theme an investor (or other steward) is prepared to raise across portfolio companies. A signal-shaped record on the investor / information layer, parallel to existing v1.8.x signal emissions. Hooks: `InteractionBook` (§45), `RoutineBook` (§46), v1.8.x `SignalBook`.
2. **`portfolio_company_dialogue_record`** — names that an engagement contact happened in a given period under a given theme, with a generic outcome class. A relational record sibling to `RelationshipCapitalBook` (§40). Carries metadata only; verbatim or paraphrased contents are restricted artifacts and never appear in public FWE.
3. **`investor_escalation_candidate`** — names that, given a sequence of dialogue records, an investor *could* escalate. A `candidate`-shaped record sibling to v1.9.5 / v1.9.7 diagnostic outputs. Implemented at v1.10.3 as a `MechanismAdapter` satisfying the v1.9.3 / v1.9.3.1 contract.
4. **`corporate_strategic_response_candidate`** — names a strategic response a firm *could* take in response to themes / dialogues / escalations. Symmetric `MechanismAdapter` shape to the escalation candidate.
5. **`industry_demand_condition_signal` (optional)** — names a generic industry-level demand condition (e.g., `weakening` / `stable` / `strengthening`) as a context signal. Sibling to existing v1.8.x macro-style signals.

Every selected concept is a **signal** or a **candidate** — never an action, never a contract change, never a price move, never a trade, never a vote, never a corporate action.

### 70.3 Hard boundary — what v1.10 must never do

v1.10 (every milestone, including v1.10.last) must not:

- introduce country-specific institution names;
- introduce source / report names from any private design probe;
- introduce jurisdiction-specific thresholds, regimes, or tiers;
- introduce domestic dataset names or paid-data references;
- introduce behavior probabilities derived from non-public reports;
- introduce bank-specific or sector-specific strategy assumptions;
- introduce forecast values as parameters;
- import paid / NDA / proprietary content;
- record confidential dialogue contents (verbatim or paraphrased);
- implement trading, price formation, lending decisions, corporate-action execution, voting execution, or AGM / EGM filings;
- emit investment-recommendation language (direct or indirect) in code, docs, schemas, or demo output;
- consume real-world calibration data of any provenance.

The `world/experiment.py::_FORBIDDEN_TOKENS` forbidden-token scan continues to gate every v1.10 commit. v1.9.last's anti-claim list (no forecast, no investment advice, no price formation, no trading, no lending decisions, no Japan calibration, no real data, no scenarios, no production-scale traversal, no native rewrite, no web UI) continues to hold without modification through every v1.10 milestone.

### 70.4 Meta-abstraction deferral rule

Two meta-abstractions surfaced as candidates: `actor_business_model_transition_pressure` (a generalization of pressure on any actor's business model) and `actor_strategic_response_candidate` (a generalization of a candidate strategic response from any actor). Both are explicitly **deferred**. The rule is: do not implement a meta-abstraction in public FWE until at least two concrete specializations of that abstraction have been implemented and have stabilized in public FWE. v1.10's concrete primitives are listed above. After v1.10.last lands and at least two concrete *response candidate* specializations are stable in public FWE, the meta-abstraction gate can be reopened. Until then, v1.10 implements the concrete primitives only.

### 70.5 What v1.10.0 lands

v1.10.0 itself ships **no behavior, no test additions, no new ledger record types, no new books, and no new mechanisms**. v1.10.0 lands:

- `docs/v1_10_universal_engagement_and_response_design.md` — the full design document covering the five selected concepts, the hard boundary, the meta-abstraction deferral rule, the milestone sequence, and the v1.10.0 success criteria.
- `docs/world_model.md` §70 (this section).
- `docs/public_private_boundary.md` — a brief v1.10 addendum reaffirming that engagement-layer artifacts (theme signals, dialogue records, escalation / response candidates, industry demand-condition signals) follow the same public / restricted rules, with verbatim / paraphrased dialogue contents always restricted.
- `docs/test_inventory.md` — headline updated to v1.10.0 (docs-only; test count unchanged at `1626 / 1626`).
- `README.md` — roadmap section adds v1.10.x rows.

The test count is unchanged at `1626 / 1626`. The CLI surface, the default fixture, the per-period flow, the reproducibility surface, the performance boundary, the test surface, and the scope language of v1.9.last are all preserved unchanged.

### 70.6 v1.10 milestone sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| **v1.10.0 Universal Engagement / Strategic Response Consolidation** | Docs-only. This section + `docs/v1_10_universal_engagement_and_response_design.md` + boundary updates. | **In progress** |
| v1.10.1 `stewardship_theme_signal` | Code. First concrete record + minimal book + investor review-routine emission path. | Planned |
| v1.10.2 `portfolio_company_dialogue_record` | Code. Dialogue book + record shape + review-routine emission path that reads v1.10.1's theme signals. | Planned |
| v1.10.3 `investor_escalation_candidate` + `corporate_strategic_response_candidate` | Code. Two `MechanismAdapter` implementations satisfying the v1.9.3 / v1.9.3.1 contract. | Planned |
| v1.10.4 `industry_demand_condition_signal` | Code. Optional later context-signal extension. | Optional |
| v1.10.5 Living-world integration | Code. Wires v1.10.1–v1.10.3 (and optionally v1.10.4) into the multi-period sweep behind a v1.10-scoped fixture, separate from the v1.9.last default fixture. | Planned |
| **v1.10.last Public engagement layer freeze** | Docs-only. Anti-claim list, scope-language agreement, forbidden-token scan clean, no investment-advice framings, CI green on the tag commit. | Planned |

### 70.7 v1.10.0 success criteria

§70 is complete when **all** hold:

1. `docs/v1_10_universal_engagement_and_response_design.md` exists and covers the five selected concepts using the same template (purpose, generic inputs, generic outputs, candidate FWE object type, existing FWE hook, no-behavior boundary, out of scope, future v2 mapping slot), the hard boundary, the meta-abstraction deferral rule, the milestone sequence, the v1.10.0 success criteria, and the anti-scope.
2. `docs/world_model.md` carries this §70.
3. `docs/public_private_boundary.md` carries the v1.10 addendum.
4. `docs/test_inventory.md` headline reflects v1.10.0 (docs-only; no test count change).
5. `README.md` roadmap section adds v1.10.x rows at "In progress" / "Planned" status.
6. The full test suite continues to pass at `1626 / 1626`.
7. `compileall world spaces tests examples` is clean and `ruff check .` from the repo root is clean.
8. The forbidden-token word-boundary scan is clean.
9. No country-specific institution names, source / report names, jurisdiction-specific thresholds, domestic dataset names, behavior probabilities, bank-specific strategy assumptions, forecast values, paid / NDA / proprietary content, or confidential dialogue contents appear in the v1.10.0 docs.
10. No investment-recommendation language (direct or indirect) appears in the v1.10.0 docs.

### 70.8 Anti-scope

§70 deliberately does **not** add: any new economic behavior, any new mechanism, any new `MechanismAdapter`, any new ledger record type, any new book, any new test; price formation, trading, lending decisions, loan origination, covenant enforcement, contract or constraint mutation, voting execution, AGM / EGM filings, corporate-action execution, real-data ingestion, paid-data ingestion, expert-input ingestion, Japan calibration, named real-institution content, calibrated behavior probabilities, forecast values, investment-recommendation framings, scenario branching, stress logic, native (C++ / Julia / Rust / GPU) rewrites, profiling harnesses, web UI. v1.10.0 is documentation only.

### 70.9 Position in the v1.10 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 Universal Engagement / Strategic Response Consolidation | Docs-only (§70). | Shipped |
| **v1.10.1 Stewardship theme signal** | Code (§71). | **Shipped** |
| v1.10.2 → v1.10.5 | Code. | Planned |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

## 71. v1.10.1 Stewardship theme signal — storage and audit layer

§71 lands the first concrete primitive of the v1.10 engagement / strategic-response layer named in §70 and in `docs/v1_10_universal_engagement_and_response_design.md`. The deliverable is **storage and audit only** — a small, immutable record shape and an append-only book. The runtime, the per-period flow of v1.9, and every existing mechanism are unchanged. The v1.10 hard boundary (§70.3) and the meta-abstraction deferral rule (§70.4) continue to hold without modification.

### 71.1 What v1.10.1 names

A *stewardship theme* is a monitoring / attention input that an investor, asset owner, or other steward declares it is **prepared to raise** across portfolio companies in a given period. It is not an action: it does not vote, does not engage with any specific portfolio company, does not escalate, does not trade, does not change ownership, does not produce any corporate-response candidate, and does not move any price. It is a named, audit-grade input shape that later v1.10.x milestones (v1.10.2 dialogue records, v1.10.3 escalation / corporate-response candidate mechanisms, v1.10.5 living-world integration) read.

### 71.2 What v1.10.1 ships

- `world/stewardship.py` — `StewardshipThemeRecord` (immutable dataclass) and `StewardshipBook` (append-only store).
- `world/ledger.py` — `RecordType.STEWARDSHIP_THEME_ADDED`, emitted exactly once per `add_theme` call.
- `world/kernel.py` — `stewardship: StewardshipBook` wired in `WorldKernel.__post_init__` with the same ledger / clock injection pattern every other source-of-truth book uses.
- `tests/test_stewardship.py` — 58 tests covering field validation, immutability, duplicate rejection, unknown-id lookup, every list / filter, the active-window predicate semantics, deterministic snapshots, ledger emission of the new record type, kernel wiring, the no-mutation guarantee against every other source-of-truth book, the no-action invariant, and a jurisdiction-neutral identifier scan over both the new module and the test file.

### 71.3 Record shape

`StewardshipThemeRecord` is a frozen dataclass with the following fields. All required strings reject empty values; tuple fields normalize to `tuple[str, ...]` and reject empty entries; cross-references are stored as data and not validated against any other book (per the v0/v1 cross-reference rule already used by `world/attention.py`).

- `theme_id` — stable, unique-within-book id.
- `owner_id`, `owner_type` — investor / steward identification (free-form strings).
- `theme_type` — controlled-vocabulary tag (`"capital_allocation_discipline"`, `"governance_structure"`, `"disclosure_quality"`, `"operational_efficiency"`, `"sustainability_practice"`, …); not enforced.
- `title` — short jurisdiction-neutral label.
- `description` — optional jurisdiction-neutral prose; defaults to empty string.
- `target_scope` — controlled-vocabulary tag (`"all_holdings"`, `"top_holdings"`, `"sector_subset"`, `"single_firm"`, …); not enforced.
- `priority` — small enumerated tag (`"low"` / `"medium"` / `"high"`). **Never** a calibrated probability.
- `horizon` — free-form label (`"short_term"` / `"medium_term"` / `"long_term"`).
- `status` — small free-form tag (`"draft"` / `"active"` / `"under_review"` / `"retired"`). `"retired"` themes remain in the book for audit; the active-window predicate handles them via `effective_to`.
- `effective_from` — required ISO `YYYY-MM-DD` start date.
- `effective_to` — optional ISO `YYYY-MM-DD` end date. `None` means "no declared end". `effective_to`, when set, must be on or after `effective_from`.
- `related_variable_ids`, `related_signal_ids` — tuples of free-form ids the steward declares as related; cross-references stored as data and not validated.
- `metadata` — free-form mapping for provenance.

### 71.4 Active-window semantics

`StewardshipThemeRecord.is_active_on(on_date)` returns `True` iff the theme's `[effective_from, effective_to]` window contains `on_date` inclusive on both ends. `effective_to=None` means "no declared end" (open-ended right side). The check is purely on dates; `status` is **not** consulted, so a record with status `"retired"` and no `effective_to` is still treated as active by date. The book's `list_by_status` filter is the natural complement when callers want status-based semantics. `StewardshipBook.list_active_as_of(as_of)` returns every theme whose window contains `as_of`.

### 71.5 Ledger emission

Every successful `add_theme` call emits exactly one ledger record of type `STEWARDSHIP_THEME_ADDED`, with `object_id = theme_id`, `source = owner_id`, `agent_id = owner_id`, `space_id = "stewardship"`, and a payload that carries the full field set (excluding `metadata`). A duplicate `add_theme` call raises `DuplicateStewardshipThemeError` and emits **no** additional ledger record. A book without a ledger accepts adds silently. No other ledger record type is emitted by the book — the no-action invariant is asserted explicitly in the test suite.

### 71.6 Kernel wiring

`WorldKernel` exposes `kernel.stewardship: StewardshipBook`. The book is constructed via `field(default_factory=StewardshipBook)` and joined to the kernel's ledger and clock in `__post_init__` alongside every other source-of-truth book. The book does not register tasks, does not subscribe to events, and does not participate in `tick()` / `run()` — it is a passive append-only store, mirroring the v1.8.5 `AttentionBook` discipline.

### 71.7 No-behavior boundary (binding)

A `StewardshipThemeRecord` and the `StewardshipBook` storing it are jurisdiction-neutral, signal-only, and behavior-free. v1.10.1 does **not**:

- introduce voting, proxy voting, engagement execution, escalation, corporate-response generation, investment recommendation, trading, price formation, real data ingestion, Japan calibration, jurisdiction-specific stewardship codes, or source-specific behavior probabilities;
- mutate any other source-of-truth book (the no-mutation test asserts this against ownership, contracts, prices, constraints, signals, valuations, institutions, external_processes, relationships, interactions, routines, attention, variables, and exposures);
- enforce membership of `theme_type`, `target_scope`, `priority`, `horizon`, or `status` against any controlled vocabulary — the recommended labels are illustrative;
- emit any ledger record other than `STEWARDSHIP_THEME_ADDED` from a bare `add_theme` call.

### 71.8 What v1.10.1 does not decide

- The exact field schema for `portfolio_company_dialogue_record` (v1.10.2).
- The `MechanismAdapter` shape for `investor_escalation_candidate` and `corporate_strategic_response_candidate` (v1.10.3).
- Whether `industry_demand_condition_signal` ships (v1.10.4).
- Which review routines emit which records (v1.10.5).
- Any fixture extension to the v1.9.last default living-world demo. v1.10.x demo additions land behind v1.10-scoped fixtures, separate from the v1.9.last default.

### 71.9 Position in the v1.10 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 Universal Engagement / Strategic Response Consolidation | Docs-only (§70). | Shipped |
| v1.10.1 Stewardship theme signal | Code (§71). | Shipped |
| v1.10.2 Portfolio-company dialogue record | Code (§72). | Shipped |
| v1.10.3 Investor escalation candidate + corporate strategic response candidate | Code (§73). | Shipped |
| v1.10.4 Industry demand condition signal | Code (§74). | Shipped |
| v1.10.4.1 Type-correct industry-condition cross-reference slot | Code (§75). Additive. | Shipped |
| v1.10.5 Living-world integration | Code (§76). | Shipped |
| v1.11.0 Capital-market surface | Code (§77). | Shipped |
| v1.11.1 Capital-market readout | Code (§78). Additive readout layer. | Shipped |
| v1.11.2 Demo market regime presets | Code (§79). Additive demo-only preset layer. | Shipped |
| **v1.12.0 Firm financial latent state** | Code (§80). First time-crossing endogenous state-update layer. | **Shipped** |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

The test count moves from `1626 / 1626` (v1.10.0) to `1684 / 1684` (v1.10.1) — the 58 tests in `tests/test_stewardship.py` — and to `1737 / 1737` (v1.10.2) with the 53 tests in `tests/test_engagement.py`. The CLI surface, the default fixture, the per-period flow, the reproducibility surface, and the performance boundary of v1.9.last are all preserved unchanged.

## 72. v1.10.2 Portfolio-company dialogue record — engagement metadata storage

§72 lands the second concrete primitive of the v1.10 engagement / strategic-response layer named in §70 and in `docs/v1_10_universal_engagement_and_response_design.md`. Like v1.10.1 (§71), the deliverable is **storage and audit only** — an immutable record shape and an append-only book — with one additional discipline that v1.10.2 makes binding: the record carries *engagement metadata only* and never a transcript, content, notes, minutes, attendees, or other verbatim / paraphrased dialogue body. The runtime, the per-period flow of v1.9, and every existing mechanism are unchanged. The v1.10 hard boundary (§70.3) and the meta-abstraction deferral rule (§70.4) continue to hold without modification.

### 72.1 What v1.10.2 names

A *portfolio-company dialogue record* is structured metadata for a single engagement touchpoint between an investor / asset owner / steward (the *initiator*) and a portfolio company / firm (the *counterparty*). It records *that* a contact happened on a given date, *which* themes (and, optionally, signals / valuations / pressure-assessment signals) it referenced, *what* generic outcome label the steward attached to it, and *what* generic next-step label the steward attached to it.

A dialogue record is **not** the dialogue itself. It does not carry verbatim or paraphrased contents, meeting notes, attendee lists, non-public company information, named-client material, or expert-interview content — those remain restricted under `docs/public_private_boundary.md` and never appear in public FWE. By itself, a dialogue record does not vote, does not file proxies, does not execute any AGM / EGM action, does not escalate (escalation candidates are a separate v1.10.3 primitive), does not produce any corporate-response candidate (also v1.10.3), does not recommend any investment / divestment / weight change, does not trade, does not change ownership, does not move any price, does not form any forecast or behavior probability, and does not mutate any other source-of-truth book in the kernel.

### 72.2 What v1.10.2 ships

- `world/engagement.py` — `PortfolioCompanyDialogueRecord` (immutable dataclass) and `DialogueBook` (append-only store).
- `world/ledger.py` — `RecordType.PORTFOLIO_COMPANY_DIALOGUE_RECORDED`, emitted exactly once per `add_dialogue` call.
- `world/kernel.py` — `engagement: DialogueBook` wired in `WorldKernel.__post_init__` with the same ledger / clock injection pattern every other source-of-truth book uses (sibling to `kernel.stewardship`).
- `tests/test_engagement.py` — 53 tests covering field validation, immutability, duplicate rejection, unknown-id lookup, every list / filter (`list_dialogues`, `list_by_initiator`, `list_by_counterparty`, `list_by_theme`, `list_by_status`, `list_by_dialogue_type`, `list_by_date`), deterministic snapshots, ledger emission of the new record type, kernel wiring, the no-mutation guarantee against every other source-of-truth book (including v1.10.1's `StewardshipBook`), the no-action invariant, an explicit assertion that no transcript / content / notes / minutes / attendees / verbatim / paraphrase / body field exists on the record or in the ledger payload, an explicit assertion that no action-class record (`order_submitted`, `price_updated`, `contract_*`, `ownership_*`, `institution_action_recorded`) is emitted by `add_dialogue`, and a jurisdiction-neutral identifier scan over both the new module and the test file.

### 72.3 Record shape

`PortfolioCompanyDialogueRecord` is a frozen dataclass. All required strings reject empty values; tuple fields normalize to `tuple[str, ...]` and reject empty entries; cross-references are stored as data and not validated against any other book (per the v0/v1 cross-reference rule already used by `world/attention.py`, `world/routines.py`, and `world/stewardship.py`).

- `dialogue_id` — stable, unique-within-book id.
- `initiator_id`, `initiator_type` — investor / steward / asset owner identification (free-form strings).
- `counterparty_id`, `counterparty_type` — portfolio company / firm identification (free-form strings).
- `as_of_date` — required ISO `YYYY-MM-DD` date for the engagement contact.
- `dialogue_type` — controlled-vocabulary tag (`"private_meeting"`, `"public_statement"`, `"private_letter"`, `"questionnaire_response"`, `"information_request"`, `"follow_up_meeting"`, …); not enforced.
- `status` — small free-form tag (`"draft"` / `"logged"` / `"awaiting_response"` / `"resolved"` / `"closed"`).
- `outcome_label` — small free-form tag describing the generic outcome class the steward attached to the contact (`"acknowledged"` / `"partial_response"` / `"no_response"` / `"information_received"` / `"position_unchanged"`, …). **Never** a forecast and **never** a calibrated probability.
- `next_step_label` — small free-form tag describing the generic follow-up class the steward attached to the contact (`"no_action"` / `"continue_monitoring"` / `"follow_up_meeting"` / `"escalation_candidate"` / `"close_engagement"`, …). The label is metadata only — it does **not** by itself trigger any escalation, voting, trading, or corporate-response mechanism.
- `visibility` — free-form generic visibility tag (`"public"` / `"internal_only"` / `"restricted"`); recorded so downstream JFWE Public / JFWE Proprietary boundaries and downstream filtering can rely on it. Not enforced as a runtime gate in v1.10.2.
- `theme_ids` — tuple of stewardship-theme ids referenced by the dialogue; cross-references are stored as data and not validated against `StewardshipBook`.
- `related_signal_ids` — tuple of signal ids referenced by the dialogue; not validated against `SignalBook`.
- `related_valuation_ids` — tuple of valuation ids referenced by the dialogue; not validated against `ValuationBook`.
- `related_pressure_signal_ids` — tuple of v1.9.4 firm operating-pressure assessment signal ids referenced by the dialogue. Recorded as a separate slot from `related_signal_ids` so the audit trace can distinguish ordinary information signals from pressure assessments without re-parsing the signal payloads.
- `metadata` — free-form mapping for provenance, parameters, and steward notes. Must not carry verbatim or paraphrased dialogue contents, meeting notes, attendee lists, non-public company information, named-client material, or expert-interview content.

### 72.4 Anti-fields (binding)

The record deliberately has **no** `transcript`, `content`, `contents`, `notes`, `minutes`, `attendees`, `attendee_list`, `verbatim`, `paraphrase`, `paraphrased`, or `body` field. This is enforced by an explicit test (`test_dialogue_record_has_no_transcript_or_content_field`) that introspects the dataclass field set and a parallel test (`test_add_dialogue_ledger_payload_carries_no_transcript_or_content_keys`) that introspects the ledger payload key set. A future v1.10.x milestone that introduces such a field would by construction trip these tests.

### 72.5 Ledger emission

Every successful `add_dialogue` call emits exactly one ledger record of type `PORTFOLIO_COMPANY_DIALOGUE_RECORDED`, with `object_id = dialogue_id`, `source = initiator_id`, `target = counterparty_id`, `agent_id = initiator_id`, `space_id = "engagement"`, `visibility = dialogue.visibility`, and a payload that mirrors the record fields (excluding `metadata`). A duplicate `add_dialogue` call raises `DuplicateDialogueError` and emits **no** additional ledger record. A book without a ledger accepts adds silently. No other ledger record type is emitted by the book — the no-action invariant is asserted explicitly in the test suite, and the no-action-class assertion enumerates `order_submitted`, `price_updated`, `contract_created`, `contract_status_updated`, `contract_covenant_breached`, `ownership_position_added`, `ownership_transferred`, and `institution_action_recorded` as forbidden output types.

### 72.6 Kernel wiring

`WorldKernel` exposes `kernel.engagement: DialogueBook`. The book is constructed via `field(default_factory=DialogueBook)` and joined to the kernel's ledger and clock in `__post_init__` alongside every other source-of-truth book. The book does not register tasks, does not subscribe to events, and does not participate in `tick()` / `run()` — it is a passive append-only store, mirroring the v1.8.5 `AttentionBook` and v1.10.1 `StewardshipBook` discipline.

### 72.7 No-behavior boundary (binding)

A `PortfolioCompanyDialogueRecord` and the `DialogueBook` storing it are jurisdiction-neutral, signal-only, behavior-free, and content-free. v1.10.2 does **not**:

- introduce voting, proxy voting, engagement execution, escalation, corporate-response generation, investment recommendation, trading, price formation, real data ingestion, Japan calibration, jurisdiction-specific stewardship codes, or source-specific behavior probabilities;
- store dialogue transcripts, verbatim or paraphrased meeting notes, attendee lists, or any non-public company information — see §72.4 (anti-fields, binding) and `docs/public_private_boundary.md`;
- mutate any other source-of-truth book (the no-mutation test asserts this against ownership, contracts, prices, constraints, signals, valuations, institutions, external_processes, relationships, interactions, routines, attention, variables, exposures, and stewardship);
- enforce membership of `dialogue_type`, `status`, `outcome_label`, `next_step_label`, `visibility`, `initiator_type`, or `counterparty_type` against any controlled vocabulary — the recommended labels are illustrative;
- emit any ledger record other than `PORTFOLIO_COMPANY_DIALOGUE_RECORDED` from a bare `add_dialogue` call.

### 72.8 What v1.10.2 does not decide

- The `MechanismAdapter` shape for `investor_escalation_candidate` and `corporate_strategic_response_candidate` (v1.10.3). v1.10.2 records the data inputs those mechanisms will read; it does not name the mechanisms themselves.
- Whether `industry_demand_condition_signal` ships (v1.10.4).
- Which review routines emit which records (v1.10.5).
- Any fixture extension to the v1.9.last default living-world demo. v1.10.x demo additions land behind v1.10-scoped fixtures, separate from the v1.9.last default.

### 72.9 Position in the v1.10 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 Universal Engagement / Strategic Response Consolidation | Docs-only (§70). | Shipped |
| v1.10.1 Stewardship theme signal | Code (§71). | Shipped |
| v1.10.2 Portfolio-company dialogue record | Code (§72). | Shipped |
| v1.10.3 Investor escalation candidate + corporate strategic response candidate | Code (§73). | Shipped |
| v1.10.4 Industry demand condition signal | Code (§74). | Shipped |
| v1.10.4.1 Type-correct industry-condition cross-reference slot | Code (§75). Additive. | Shipped |
| v1.10.5 Living-world integration | Code (§76). | Shipped |
| v1.11.0 Capital-market surface | Code (§77). | Shipped |
| v1.11.1 Capital-market readout | Code (§78). Additive readout layer. | Shipped |
| v1.11.2 Demo market regime presets | Code (§79). Additive demo-only preset layer. | Shipped |
| **v1.12.0 Firm financial latent state** | Code (§80). First time-crossing endogenous state-update layer. | **Shipped** |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

## 73. v1.10.3 Investor escalation candidate + corporate strategic response candidate

§73 lands the third concrete primitive group of the v1.10 engagement / strategic-response layer named in §70 and in `docs/v1_10_universal_engagement_and_response_design.md`. Like v1.10.1 (§71) and v1.10.2 (§72), the deliverable is **storage and audit only** — two immutable record shapes and two append-only books, plus the kernel wiring that joins them to the kernel's ledger and clock. The runtime, the per-period flow of v1.9, and every existing mechanism are unchanged. The v1.10 hard boundary (§70.3) and the meta-abstraction deferral rule (§70.4) continue to hold without modification.

### 73.1 What v1.10.3 names

v1.10.3 names two **candidate** records that close the non-binding engagement chain:

- An *investor escalation candidate* names that an investor *could* escalate against a target portfolio company in a given period, given prior themes, dialogues, signals, and valuations. It is **not** an executed escalation: no vote, no proxy filing, no shareholder proposal, no public campaign, no exit, no letter sent. The candidate names the option, not the act.
- A *corporate strategic response candidate* names that a portfolio company *could* take a strategic response in a given period, given prior themes, dialogues, signals, and valuations. It is **not** an executed corporate action: no buyback, no dividend change, no divestment, no merger, no governance change, no disclosure filing, no operational restructure occurs because a candidate is recorded.

Together, v1.10.1 → v1.10.2 → v1.10.3 close the public-FWE engagement chain as a sequence of *signal / metadata / candidate* records:

```
stewardship theme (v1.10.1)
  → portfolio-company dialogue metadata (v1.10.2)
    → investor escalation candidate (v1.10.3, investor side)
    → corporate strategic response candidate (v1.10.3, corporate side)
```

Every link in the chain is non-binding. No execution occurs at any step.

### 73.2 Module layout

The investor side and the corporate side are separated by file:

- `world/engagement.py` carries both v1.10.2 (`PortfolioCompanyDialogueRecord` + `DialogueBook`) and v1.10.3 investor-side (`InvestorEscalationCandidate` + `EscalationCandidateBook`). The investor flow is one module because dialogue and escalation candidate are both initiated by the investor side and share the same v1.10.2 cross-reference rule (theme / signal / valuation ids stored as data, not validated).
- `world/strategic_response.py` is new in v1.10.3 and carries the corporate side (`CorporateStrategicResponseCandidate` + `StrategicResponseCandidateBook`). Splitting the corporate side into its own module keeps the engagement module from drifting into a generic catch-all and leaves room for later corporate-side primitives without bloating `engagement.py`.

### 73.3 What v1.10.3 ships

- `world/engagement.py` — adds `InvestorEscalationCandidate` (immutable dataclass) + `EscalationCandidateBook` (append-only store) alongside the existing v1.10.2 dialogue types.
- `world/strategic_response.py` (new) — `CorporateStrategicResponseCandidate` (immutable dataclass) + `StrategicResponseCandidateBook` (append-only store).
- `world/ledger.py` — `RecordType.INVESTOR_ESCALATION_CANDIDATE_ADDED` and `RecordType.CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED`, each emitted exactly once per `add_candidate` call.
- `world/kernel.py` — `escalations: EscalationCandidateBook` and `strategic_responses: StrategicResponseCandidateBook` wired in `WorldKernel.__post_init__` with the same ledger / clock injection pattern every other source-of-truth book uses.
- `tests/test_engagement.py` — extended to 105 tests (was 53) covering the investor-side escalation candidate: field validation, immutability, duplicate rejection, unknown-id lookup, every list / filter (`list_candidates`, `list_by_investor`, `list_by_target_company`, `list_by_type`, `list_by_status`, `list_by_priority`, `list_by_theme`, `list_by_dialogue`, `list_by_date`), deterministic snapshots, ledger emission of the new record type, kernel wiring, the no-mutation guarantee against every other source-of-truth book (including v1.10.1 stewardship, v1.10.2 dialogues, and v1.10.3 corporate responses), the no-action invariant, an explicit assertion that no transcript / content / vote_cast / proposal_filed / campaign_executed / exit_executed / letter_sent / verbatim / paraphrase / body field exists on the record or in the ledger payload, an explicit assertion that no action-class record (`order_submitted`, `price_updated`, `contract_*`, `ownership_*`, `institution_action_recorded`) is emitted by `add_candidate`, plain-id cross-reference acceptance, and a jurisdiction-neutral identifier scan over both the module and the test file.
- `tests/test_strategic_response.py` (new) — 55 tests covering the corporate-side response candidate with the same shape as the investor side, plus the optional `next_review_date` semantics (must be `None` or on/after `as_of_date`).

### 73.4 Investor-side record shape

`InvestorEscalationCandidate` is a frozen dataclass. All required strings reject empty values; tuple fields normalize to `tuple[str, ...]` and reject empty entries; cross-references are stored as data and not validated against any other book.

- `escalation_candidate_id` — stable, unique-within-book id.
- `investor_id` — investor / steward / asset owner identification (free-form).
- `target_company_id` — portfolio-company identification (free-form).
- `as_of_date` — required ISO `YYYY-MM-DD` date.
- `escalation_type` — controlled-vocabulary tag (`"private_letter"`, `"public_statement"`, `"shareholder_proposal_candidate"`, `"campaign_candidate"`, `"exit_candidate"`, `"vote_against_candidate"`, …); not enforced.
- `status` — small free-form lifecycle tag (`"draft"` / `"active"` / `"on_hold"` / `"withdrawn"` / `"superseded"` / `"closed"`).
- `priority` — small enumerated tag (`"low"` / `"medium"` / `"high"`). **Never** a calibrated probability.
- `horizon` — free-form label (`"short_term"` / `"medium_term"` / `"long_term"`).
- `theme_ids`, `dialogue_ids`, `related_signal_ids`, `related_valuation_ids` — tuples of plain-id cross-references, stored as data and not validated.
- `rationale_label` — small free-form tag (`"no_response"` / `"insufficient_action"` / `"persistent_underperformance_signal"` / `"governance_concern"`, …); illustrative only, not a forecast and not a calibrated probability.
- `next_step_label` — small free-form tag (`"schedule_followup"` / `"draft_communication"` / `"continue_monitoring"` / `"close_candidate"`, …). Metadata only — does **not** by itself trigger any escalation, voting, trading, or corporate-response mechanism.
- `visibility` — free-form generic visibility tag (`"public"` / `"internal_only"` / `"restricted"`); metadata only, not enforced as a runtime gate.
- `metadata` — free-form mapping for provenance.

### 73.5 Corporate-side record shape

`CorporateStrategicResponseCandidate` is a frozen dataclass. Same validation discipline as the investor side. The optional `next_review_date` adds a small extra invariant; everything else mirrors the investor side modulo field naming.

- `response_candidate_id` — stable, unique-within-book id.
- `company_id` — issuing portfolio-company identification (free-form).
- `as_of_date` — required ISO `YYYY-MM-DD` date.
- `response_type` — controlled-vocabulary tag (`"capital_allocation_review"`, `"governance_change_review"`, `"operational_restructure_review"`, `"disclosure_enhancement_review"`, `"sustainability_practice_review"`, `"no_change_candidate"`, …); not enforced.
- `status` — small free-form lifecycle tag (`"draft"` / `"active"` / `"on_hold"` / `"withdrawn"` / `"superseded"` / `"closed"`).
- `priority` — small enumerated tag (`"low"` / `"medium"` / `"high"`). **Never** a calibrated probability.
- `horizon` — free-form label.
- `trigger_theme_ids`, `trigger_dialogue_ids`, `trigger_signal_ids`, `trigger_valuation_ids`, `trigger_industry_condition_ids` — tuples of plain-id cross-references; stored as data, not validated. The `trigger_industry_condition_ids` slot was added in v1.10.4.1 (§75) so v1.10.4 `IndustryDemandConditionRecord` ids are kept *out* of `trigger_signal_ids` — see §75 for the type-correctness rationale.
- `expected_effect_label` — small free-form tag (`"expected_efficiency_improvement_candidate"` / `"expected_governance_improvement_candidate"` / `"expected_disclosure_quality_improvement_candidate"` / `"effect_unspecified"`, …). **Never** a forecast and **never** a calibrated probability — illustrative ordering only.
- `constraint_label` — small free-form tag (`"subject_to_board_review"` / `"subject_to_regulatory_review"` / `"subject_to_internal_review"` / `"no_known_constraint"`, …); metadata only.
- `next_review_date` — optional ISO `YYYY-MM-DD` date naming the firm's scheduled next internal review of the candidate. `None` means no scheduled review date. When set, must be on or after `as_of_date`.
- `visibility` — free-form generic visibility tag; metadata only, not enforced as a runtime gate.
- `metadata` — free-form mapping for provenance.

### 73.6 Anti-fields (binding)

Both records deliberately have **no** `transcript`, `content`, `contents`, `notes`, `minutes`, `attendees`, `verbatim`, `paraphrase`, `paraphrased`, or `body` field — the v1.10.2 anti-field discipline carries forward.

The investor-side record additionally has **no** `vote_cast`, `proposal_filed`, `campaign_executed`, `exit_executed`, or `letter_sent` field. The corporate-side record additionally has **no** `buyback_executed`, `dividend_changed`, `divestment_executed`, `merger_executed`, `board_change_executed`, or `disclosure_filed` field. These exclusions are enforced by explicit tests on both the dataclass field set and the ledger payload key set, parallel to the v1.10.2 dialogue tests. A future v1.10.x or later milestone that introduces such a field would by construction trip these tests.

### 73.7 Ledger emission

Every successful `add_candidate` call on `EscalationCandidateBook` emits exactly one ledger record of type `INVESTOR_ESCALATION_CANDIDATE_ADDED`, with `object_id = escalation_candidate_id`, `source = investor_id`, `target = target_company_id`, `agent_id = investor_id`, `space_id = "engagement"`, `visibility = candidate.visibility`, and a payload mirroring the record fields (excluding `metadata`).

Every successful `add_candidate` call on `StrategicResponseCandidateBook` emits exactly one ledger record of type `CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED`, with `object_id = response_candidate_id`, `source = company_id`, `agent_id = company_id`, `space_id = "strategic_response"`, `visibility = candidate.visibility`, and a payload mirroring the record fields (excluding `metadata`).

Duplicate `add_candidate` calls raise `DuplicateEscalationCandidateError` / `DuplicateResponseCandidateError` respectively and emit **no** additional ledger record. Books without a ledger accept adds silently. No other ledger record type is emitted from a bare `add_candidate` — the no-action invariant and the no-action-class assertion (enumerating `order_submitted`, `price_updated`, `contract_*`, `ownership_*`, `institution_action_recorded`) hold for both books.

### 73.8 Kernel wiring

`WorldKernel` exposes `kernel.escalations: EscalationCandidateBook` and `kernel.strategic_responses: StrategicResponseCandidateBook`. Both are constructed via `field(default_factory=...)` and joined to the kernel's ledger and clock in `__post_init__` alongside every other source-of-truth book. Neither book registers tasks, subscribes to events, nor participates in `tick()` / `run()` — they are passive append-only stores, mirroring the v1.8.5 `AttentionBook`, the v1.10.1 `StewardshipBook`, and the v1.10.2 `DialogueBook` discipline.

### 73.9 No-behavior boundary (binding)

The v1.10.3 candidate records and their books are jurisdiction-neutral, signal-only, behavior-free, and content-free. v1.10.3 does **not**:

- introduce voting, proxy voting, shareholder-proposal execution, public-campaign execution, exit execution, letter sending, AGM / EGM action, corporate-action execution (buyback / dividend / divestment / merger / governance change), disclosure-filing execution, investment recommendation, trading, price formation, real data ingestion, Japan calibration, jurisdiction-specific stewardship codes, source-specific behavior probabilities, or any new mechanism;
- store transcripts, verbatim or paraphrased meeting notes, attendee lists, or any non-public company information — see §73.6 (anti-fields, binding) and `docs/public_private_boundary.md`;
- mutate any other source-of-truth book (the no-mutation tests assert this against ownership, contracts, prices, constraints, signals, valuations, institutions, external_processes, relationships, interactions, routines, attention, variables, exposures, stewardship, engagement, escalations, and strategic_responses, in both directions);
- enforce membership of `escalation_type`, `response_type`, `status`, `priority`, `horizon`, `rationale_label`, `next_step_label`, `expected_effect_label`, `constraint_label`, or `visibility` against any controlled vocabulary — the recommended labels are illustrative;
- emit any ledger record other than `INVESTOR_ESCALATION_CANDIDATE_ADDED` or `CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED` from a bare `add_candidate` call.

### 73.10 What v1.10.3 does not decide

- Whether `industry_demand_condition_signal` ships (v1.10.4).
- Which review routines emit which records (v1.10.5). v1.10.3 records the data shape that those routines will read; it does not name the routines themselves.
- Any fixture extension to the v1.9.last default living-world demo. v1.10.x demo additions land behind v1.10-scoped fixtures, separate from the v1.9.last default.
- The meta-abstractions `actor_business_model_transition_pressure` and `actor_strategic_response_candidate`. v1.10.3 ships the *concrete* corporate-side response candidate; the meta gate stays closed until at least two concrete *response candidate* specializations are stable in public FWE.

### 73.11 Position in the v1.10 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 Universal Engagement / Strategic Response Consolidation | Docs-only (§70). | Shipped |
| v1.10.1 Stewardship theme signal | Code (§71). | Shipped |
| v1.10.2 Portfolio-company dialogue record | Code (§72). | Shipped |
| v1.10.3 Investor escalation candidate + corporate strategic response candidate | Code (§73). | Shipped |
| v1.10.4 Industry demand condition signal | Code (§74). | Shipped |
| v1.10.4.1 Type-correct industry-condition cross-reference slot | Code (§75). Additive. | Shipped |
| v1.10.5 Living-world integration | Code (§76). | Shipped |
| v1.11.0 Capital-market surface | Code (§77). | Shipped |
| v1.11.1 Capital-market readout | Code (§78). Additive readout layer. | Shipped |
| v1.11.2 Demo market regime presets | Code (§79). Additive demo-only preset layer. | Shipped |
| **v1.12.0 Firm financial latent state** | Code (§80). First time-crossing endogenous state-update layer. | **Shipped** |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

The test count moves from `1737 / 1737` (v1.10.2) to `1844 / 1844` (v1.10.3) — `+52` tests added to `tests/test_engagement.py` for the investor-side escalation candidate, plus `+55` tests in the new `tests/test_strategic_response.py` for the corporate-side response candidate. The CLI surface, the default fixture, the per-period flow, the reproducibility surface, and the performance boundary of v1.9.last are all preserved unchanged.

## 74. v1.10.4 Industry demand condition signal — context evidence storage

§74 lands the optional context-signal primitive of the v1.10 engagement / strategic-response layer named in §70 and in `docs/v1_10_universal_engagement_and_response_design.md`. Like every prior v1.10 milestone, the deliverable is **storage and audit only** — one immutable record shape and one append-only book, plus the kernel wiring that joins it to the kernel's ledger and clock. The runtime, the per-period flow of v1.9, and every existing mechanism are unchanged. The v1.10 hard boundary (§70.3) and the meta-abstraction deferral rule (§70.4) continue to hold without modification.

### 74.1 What v1.10.4 names

An *industry demand condition* is **context evidence**: a synthetic, jurisdiction-neutral *demand state* of an industry / sector / market in a given period. The record names a direction class (`expanding` / `stable` / `contracting` / `mixed` / `unknown`), a bounded synthetic strength in `[0.0, 1.0]`, a horizon class, a bounded synthetic confidence in `[0.0, 1.0]`, an illustrative condition-type tag, and a small lifecycle-status tag, plus plain-id cross-references to variables, signals, and exposures.

The record is explicitly *not* a forecast. It does not predict demand, sales, or revenue; it does not update any firm's financial statements; it does not move any price, trigger any corporate action, drive any lending decision, or recommend any investment. It is a context record that later milestones (firm pressure assessment, valuation refresh, bank credit review, corporate strategic response candidates, v1.10.5 living-world integration) may *read* as one input among many, by plain id.

### 74.2 What v1.10.4 ships

- `world/industry.py` (new) — `IndustryDemandConditionRecord` (immutable dataclass) and `IndustryConditionBook` (append-only store) with `add_condition`, `get_condition`, `list_conditions`, `list_by_industry`, `list_by_condition_type`, `list_by_demand_direction`, `list_by_status`, `list_by_date`, and `snapshot`.
- `world/ledger.py` — `RecordType.INDUSTRY_DEMAND_CONDITION_ADDED`, emitted exactly once per `add_condition` call.
- `world/kernel.py` — `industry_conditions: IndustryConditionBook` wired in `WorldKernel.__post_init__` with the same ledger / clock injection pattern every other source-of-truth book uses.
- `tests/test_industry_conditions.py` (new) — 84 tests covering field validation, the bounded synthetic numeric fields (`demand_strength` and `confidence` each in `[0.0, 1.0]` inclusive, with explicit bool rejection matching the v1 `world/exposures.py` style), immutability, duplicate rejection, unknown-id lookup, every list / filter, deterministic snapshots, ledger emission of the new record type, kernel wiring, the no-mutation guarantee against every other source-of-truth book (including v1.10.1 stewardship, v1.10.2 dialogues, v1.10.3 escalation, v1.10.3 strategic response), the no-action invariant, an explicit no-action / no-forecast / no-firm-state ledger assertion, an explicit assertion that no `forecast_value` / `revenue_forecast` / `sales_forecast` / `market_size` / `demand_index_value` / `vendor_consensus` / `consensus_forecast` / `real_data_value` field exists on the record or in the ledger payload, plain-id cross-reference acceptance, and a jurisdiction-neutral identifier scan over both module and test file. The test suite also exercises the v1.10.3 ↔ v1.10.4 link by citing a v1.10.4 condition id from a `CorporateStrategicResponseCandidate` `trigger_signal_ids` slot without forcing cross-book validation.

### 74.3 Record shape

`IndustryDemandConditionRecord` is a frozen dataclass. All required strings reject empty values; tuple fields normalize to `tuple[str, ...]` and reject empty entries; cross-references are stored as data and not validated against any other book.

- `condition_id` — stable, unique-within-book id.
- `industry_id` — generic, jurisdiction-neutral industry / sector / market identifier (e.g., `"industry:reference_manufacturing_general"`); free-form.
- `industry_label` — short jurisdiction-neutral label.
- `as_of_date` — required ISO `YYYY-MM-DD` date.
- `condition_type` — controlled-vocabulary tag (`"demand_assessment"`, `"demand_outlook_synthetic"`, `"structural_demand_state"`, `"cyclical_demand_state"`, …); not enforced.
- `demand_direction` — small free-form tag (`"expanding"` / `"stable"` / `"contracting"` / `"mixed"` / `"unknown"`); not enforced.
- `demand_strength` — synthetic bounded numeric in `[0.0, 1.0]` inclusive. Booleans rejected. Coerced to `float`. **Never** a calibrated probability and **never** a forecast — illustrative magnitude ordering only.
- `time_horizon` — free-form label (`"short_term"` / `"medium_term"` / `"long_term"` / `"structural"`).
- `confidence` — synthetic bounded numeric in `[0.0, 1.0]` inclusive. Booleans rejected. Coerced to `float`. **Never** a calibrated probability and **never** a measurement — illustrative confidence ordering only.
- `status` — small free-form lifecycle tag (`"draft"` / `"active"` / `"under_review"` / `"superseded"` / `"retired"` / `"withdrawn"`).
- `related_variable_ids`, `related_signal_ids`, `related_exposure_ids` — tuples of plain-id cross-references; stored as data, not validated.
- `visibility` — free-form generic visibility tag (`"public"` / `"internal_only"` / `"restricted"`); metadata only, not enforced as a runtime gate.
- `metadata` — free-form mapping for provenance.

### 74.4 Anti-fields (binding)

The record deliberately has **no** `forecast_value`, `revenue_forecast`, `sales_forecast`, `market_size`, `demand_index_value`, `vendor_consensus`, `consensus_forecast`, or `real_data_value` field. The ledger payload likewise carries none of these keys. Two explicit tests (`test_condition_record_has_no_forecast_or_revenue_field`, `test_add_condition_payload_carries_no_forecast_or_revenue_keys`) introspect the dataclass field set and the ledger payload key set respectively. A future v1.10.x or later milestone that introduces such a field would by construction trip these tests.

### 74.5 Ledger emission

Every successful `add_condition` call emits exactly one ledger record of type `INDUSTRY_DEMAND_CONDITION_ADDED`, with `object_id = condition_id`, `source = industry_id`, `space_id = "industry"`, `visibility = condition.visibility`, `confidence = condition.confidence` (the `LedgerRecord` already carries an optional `confidence` slot validated to `[0, 1]`), and a payload mirroring the record fields (excluding `metadata`). A duplicate `add_condition` call raises `DuplicateIndustryConditionError` and emits **no** additional ledger record. A book without a ledger accepts adds silently. No other ledger record type is emitted by the book — the no-action invariant and the no-action / no-forecast / no-firm-state ledger assertion (enumerating `order_submitted`, `price_updated`, `contract_*`, `ownership_*`, `institution_action_recorded`, `valuation_added`, `valuation_compared`, `firm_state_added`) hold.

### 74.6 Kernel wiring

`WorldKernel` exposes `kernel.industry_conditions: IndustryConditionBook`. The book is constructed via `field(default_factory=IndustryConditionBook)` and joined to the kernel's ledger and clock in `__post_init__` alongside every other source-of-truth book. The book does not register tasks, does not subscribe to events, and does not participate in `tick()` / `run()` — it is a passive append-only store, mirroring the v1.8.5 `AttentionBook`, the v1.10.1 `StewardshipBook`, the v1.10.2 `DialogueBook`, and the v1.10.3 `EscalationCandidateBook` / `StrategicResponseCandidateBook` discipline.

### 74.7 No-behavior boundary (binding)

An `IndustryDemandConditionRecord` and the `IndustryConditionBook` storing it are jurisdiction-neutral, signal-only, behavior-free, and forecast-free. v1.10.4 does **not**:

- introduce demand forecasting, sales forecasting, revenue updates, financial-statement updates, corporate-action execution, voting execution, AGM / EGM action, disclosure-filing execution, investment recommendation, trading, price formation, lending decisions, real data ingestion, Japan calibration, jurisdiction-specific sector classifications, source-specific forecast values, or calibrated behavior probabilities;
- mutate any other source-of-truth book (the no-mutation test asserts this against ownership, contracts, prices, constraints, signals, valuations, institutions, external_processes, relationships, interactions, routines, attention, variables, exposures, stewardship, engagement, escalations, and strategic_responses);
- enforce membership of `condition_type`, `demand_direction`, `time_horizon`, `status`, or `visibility` against any controlled vocabulary — the recommended labels are illustrative;
- emit any ledger record other than `INDUSTRY_DEMAND_CONDITION_ADDED` from a bare `add_condition` call.

### 74.8 What v1.10.4 does not decide

- Which review routines emit which records (v1.10.5). v1.10.4 records the data shape that those routines will read; it does not name the routines themselves.
- Any fixture extension to the v1.9.last default living-world demo. v1.10.x demo additions land behind v1.10-scoped fixtures, separate from the v1.9.last default.
- The corporate-side / firm-side consumer plumbing that *uses* an industry condition (firm pressure assessment, valuation refresh, bank credit review, corporate strategic response candidates). v1.10.4 makes industry conditions *citable* by plain id from any of those layers; it does not change any of them.

### 74.9 Position in the v1.10 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 Universal Engagement / Strategic Response Consolidation | Docs-only (§70). | Shipped |
| v1.10.1 Stewardship theme signal | Code (§71). | Shipped |
| v1.10.2 Portfolio-company dialogue record | Code (§72). | Shipped |
| v1.10.3 Investor escalation candidate + corporate strategic response candidate | Code (§73). | Shipped |
| v1.10.4 Industry demand condition signal | Code (§74). | Shipped |
| v1.10.4.1 Type-correct industry-condition cross-reference slot | Code (§75). Additive. | Shipped |
| v1.10.5 Living-world integration | Code (§76). | Shipped |
| v1.11.0 Capital-market surface | Code (§77). | Shipped |
| v1.11.1 Capital-market readout | Code (§78). Additive readout layer. | Shipped |
| v1.11.2 Demo market regime presets | Code (§79). Additive demo-only preset layer. | Shipped |
| **v1.12.0 Firm financial latent state** | Code (§80). First time-crossing endogenous state-update layer. | **Shipped** |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

The test count moves from `1844 / 1844` (v1.10.3) to `1928 / 1928` (v1.10.4) — `+84` tests in the new `tests/test_industry_conditions.py`. The CLI surface, the default fixture, the per-period flow, the reproducibility surface, and the performance boundary of v1.9.last are all preserved unchanged.

## 75. v1.10.4.1 Additive: type-correct industry-condition cross-reference slot on `CorporateStrategicResponseCandidate`

§75 is a small, additive cleanup on top of v1.10.3 + v1.10.4. It does not introduce a new primitive, a new book, or a new ledger record type; it adds one type-correct cross-reference slot to an existing v1.10.3 record so that v1.10.4 industry-condition ids do not have to ride in the wrong field.

### 75.1 Why this exists

v1.10.4 (§74) introduced `IndustryDemandConditionRecord` in `world/industry.py`. The v1.10.4 test suite originally exercised the v1.10.3 ↔ v1.10.4 cross-link by citing an industry-condition id from a `CorporateStrategicResponseCandidate.trigger_signal_ids` slot. That worked operationally — `trigger_signal_ids` is a `tuple[str, ...]` of plain ids and accepts any string — but it was **type-incorrect**: an `IndustryDemandConditionRecord` is not a `SignalBook` `Signal`. Conflating the two in the same field meant a downstream consumer (a future report builder, a future replay tool, a future lineage / dependency graph view) would have had to introspect the payload to tell whether each id resolved to a `SignalBook` entry or to an `IndustryConditionBook` entry.

v1.10.4.1 fixes this by adding a dedicated slot. Disambiguation is now by *field*, not by *payload introspection*.

### 75.2 What v1.10.4.1 ships

- `world/strategic_response.py`:
  - New field `trigger_industry_condition_ids: tuple[str, ...]` on `CorporateStrategicResponseCandidate`, default `()`. Added to `TUPLE_FIELDS` so the same empty-string-rejection / normalization discipline applies. Added to `to_dict()` and to the ledger payload emitted by `StrategicResponseCandidateBook.add_candidate`.
  - New method `StrategicResponseCandidateBook.list_by_industry_condition(condition_id)` — symmetric with the existing `list_by_dialogue` / `list_by_theme` filters.
- `world/ledger.py` — unchanged; the existing `CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED` record type carries the new payload key automatically (`payload` is a free-form `Mapping`).
- `world/kernel.py` — unchanged.
- `tests/test_strategic_response.py` — extended with `test_response_default_trigger_industry_condition_ids_is_empty_tuple`, `test_list_response_by_industry_condition`, `test_list_by_industry_condition_does_not_match_signal_slot`, and an additional parametrize entry for the empty-string-rejection test on the new tuple field. The existing `test_response_to_dict_round_trips_fields`, `test_add_response_payload_carries_full_field_set`, `test_response_can_reference_unresolved_trigger_ids`, and the no-mutation guarantee test are extended in place to exercise the new slot. `+4` new tests overall.
- `tests/test_industry_conditions.py` — the v1.10.3 ↔ v1.10.4 cross-link test (`test_condition_id_can_be_referenced_from_corporate_response_candidate`) is rewritten to use the dedicated `trigger_industry_condition_ids` slot, asserts that `trigger_signal_ids` stays empty for the same record, and asserts that `list_by_industry_condition(condition_id)` surfaces the candidate. The test count here is unchanged.

### 75.3 Backward compatibility

The change is purely additive:

- The new field has a default of `()` so every existing `CorporateStrategicResponseCandidate` constructor call (in tests, demos, or any future caller) continues to work without modification.
- The ledger payload of an existing record is augmented by a new key whose value is `[]` for any record constructed without the new field — the consumer that doesn't read it pays no cost.
- No existing field is removed, renamed, or re-typed. `trigger_signal_ids` keeps its meaning: ids that resolve against `SignalBook`. The new slot keeps `IndustryConditionBook` ids out of that field by giving them a dedicated home.
- `CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED` is unchanged as a record type — only the payload shape grew.
- No kernel field changed; no new book was added.

A test (`test_list_by_industry_condition_does_not_match_signal_slot`) explicitly exercises the disambiguation: a condition-id sitting *in* `trigger_signal_ids` (the historical, type-incorrect placement) must **not** be surfaced by `list_by_industry_condition`. Field-level disambiguation is what v1.10.4.1 buys; the test pins it.

### 75.4 Hard boundary (binding) — unchanged from §70.3 / §73 / §74

v1.10.4.1 does **not** introduce voting, voting execution, proxy voting, shareholder-proposal execution, public-campaign execution, exit execution, AGM / EGM action, corporate-action execution (buyback / dividend / divestment / merger / governance change), disclosure-filing execution, demand forecasting, sales forecasting, revenue updates, financial-statement updates, investment recommendation, trading, price formation, lending decisions, real data ingestion, Japan calibration, jurisdiction-specific sector classifications, source-specific forecast values, calibrated behavior probabilities, or any new mechanism. The candidate-only / no-execution / no-forecast disciplines of §73 and §74 carry forward without modification.

### 75.5 Why an additive field rather than a separate book

Two alternatives were considered and rejected:

1. **Repurpose `trigger_signal_ids` to carry both signal and industry-condition ids.** Rejected: ledger replay, lineage reconstruction, and report generation should disambiguate by field, not by payload introspection. The cost of an extra field is one optional `tuple[str, ...]` per candidate; the cost of payload introspection is paid by every downstream consumer for the lifetime of the schema.
2. **Add a separate "trigger book" or "trigger graph" abstraction that holds (candidate, industry_condition) edges.** Rejected for v1.10.4.1: the v1.10 layer is deliberately a sequence of *flat* append-only books. Introducing a join book would conflict with the v1.8.5 `AttentionBook`, v1.10.1 `StewardshipBook`, v1.10.2 `DialogueBook`, v1.10.3 `EscalationCandidateBook` / `StrategicResponseCandidateBook`, and v1.10.4 `IndustryConditionBook` discipline. If a join layer is later wanted, it can land on top of these existing books without re-litigating v1.10's record shapes.

### 75.6 Position in the v1.10 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 Universal Engagement / Strategic Response Consolidation | Docs-only (§70). | Shipped |
| v1.10.1 Stewardship theme signal | Code (§71). | Shipped |
| v1.10.2 Portfolio-company dialogue record | Code (§72). | Shipped |
| v1.10.3 Investor escalation candidate + corporate strategic response candidate | Code (§73). | Shipped |
| v1.10.4 Industry demand condition signal | Code (§74). | Shipped |
| v1.10.4.1 Type-correct industry-condition cross-reference slot | Code (§75). Additive. | Shipped |
| v1.10.5 Living-world integration | Code. | Planned |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

The test count moves from `1928 / 1928` (v1.10.4) to `1932 / 1932` (v1.10.4.1) — `+4` new tests in `tests/test_strategic_response.py` (one extra parametrize entry plus three new test functions). The CLI surface, the default fixture, the per-period flow, the reproducibility surface, and the performance boundary of v1.9.last are all preserved unchanged.

## 76. v1.10.5 Living-world integration

§76 wires the v1.10.1 → v1.10.4 (and v1.10.4.1) engagement / strategic-response storage primitives into the existing v1.9 living reference world demo. The runtime grows by five new phases (industry demand → stewardship setup → dialogue → escalation → corporate response) and the `LivingReferencePeriodSummary` / `LivingReferenceWorldResult` / report / canonical / manifest surfaces grow additively to surface the new id tuples. **No new mechanism is introduced.** The integration is composition over the v1.10 storage books only: every v1.10 link in the demo chain is non-binding, candidate-only, and content-free, exactly as the per-record contracts of §71 → §75 prescribe. The v1.10 hard boundary (§70.3) and the meta-abstraction deferral rule (§70.4) continue to hold without modification.

### 76.1 What the demo now demonstrates

The integrated chain over a single period:

```
corporate quarterly report (§49)
  → firm operating-pressure assessment (§64)
    → industry demand condition (§74)
      → heterogeneous attention (§54)
        → valuation refresh lite (§65)
          → bank credit review lite (§67)
            → portfolio-company dialogue metadata (§72)
              → investor escalation candidate (§73)
              → corporate strategic response candidate (§73)
                → review routines (§55)
```

The investor side and the corporate side run in parallel. Every cross-reference is plain-id and not validated against any other book (the v0/v1 cross-reference rule). Industry-condition ids ride in the v1.10.4.1 type-correct `trigger_industry_condition_ids` slot on `CorporateStrategicResponseCandidate`, never in `trigger_signal_ids`.

### 76.2 What v1.10.5 ships

- `world/reference_living_world.py` — extends the orchestrator with three optional kwargs (`firm_industry_map`, `industry_demand_states`, `stewardship_theme_types`) plus five new per-period phases and one new setup-time phase. The `LivingReferencePeriodSummary` dataclass grows additively with `industry_condition_ids` / `stewardship_theme_ids` / `dialogue_ids` / `investor_escalation_candidate_ids` / `corporate_strategic_response_candidate_ids`; `LivingReferenceWorldResult` grows with setup-level `industry_ids` / `stewardship_theme_ids`. Every new field defaults to `()` so older callers keep working.
- `world/living_world_report.py` — `LivingWorldPeriodReport` grows with `industry_condition_count` / `stewardship_theme_count` / `dialogue_count` / `investor_escalation_candidate_count` / `corporate_strategic_response_candidate_count`. The Markdown renderer adds a concise `## v1.10 engagement / response` section between the per-period table and the attention divergence section. The boundary statement is extended in place to cover the v1.10 anti-claims; the v1.9.1 prefix is preserved verbatim.
- `examples/reference_world/living_world_replay.py` — the canonical view echoes setup-level `industry_ids` / `industry_count` / `stewardship_theme_ids` / `stewardship_theme_count` plus the per-period v1.10 id tuples. The boundary statement constant tracks the reporter's. **Expected digest change:** the v1.10.5 living-world digest is *not* the same as the v1.9.last digest — the canonical view now includes the new id tuples and the boundary string was extended. Two fresh runs of the v1.10.5 default fixture produce byte-identical canonical JSON and the same digest; the digest just differs from v1.9.last.
- `examples/reference_world/living_world_manifest.py` — the manifest summary echoes the new counts (`industry_count`, `stewardship_theme_count`, `industry_condition_total`, `dialogue_total`, `investor_escalation_candidate_total`, `corporate_strategic_response_candidate_total`).
- `examples/reference_world/run_living_reference_world.py` — the per-period CLI trace line names the v1.10 phases (`industry=`, `themes=`, `dialogues=`, `escalations=`, `responses=`); the summary line names the integrated chain and carries the v1.10 anti-claims.
- `tests/test_living_reference_world.py` — `+15` new tests pinning v1.10.5 integration invariants. See §76.7.
- `tests/test_living_reference_world_performance_boundary.py` — the per-period formula and the per-run upper bound are updated to reflect the v1.10.5 contributions. See §76.5.

### 76.3 Per-period flow (runtime order)

The runtime flow follows data dependencies, not narrative order:

1. **Corporate phase** (§49) — one corporate quarterly report per firm.
2. **Firm pressure phase** (§64) — one pressure signal per firm.
3. **Industry demand condition phase** (§74, NEW) — one record per unique industry derived from `firm_industry_map`. Synthetic context evidence; *not* a forecast.
4. **Attention phase** (§54) — one menu + one selection per actor.
5. **Valuation phase** (§65) — one valuation per (investor, firm).
6. **Bank credit review phase** (§67) — one review note per (bank, firm).
7. **Dialogue phase** (§72, NEW) — one dialogue record per (investor, firm). Carries metadata only: theme refs, corp-signal ref, valuation refs, pressure-signal refs. No transcript / content / notes / minutes / attendees.
8. **Investor escalation phase** (§73, NEW) — one candidate per (investor, firm). Carries the option, never the act: theme refs, dialogue refs, signal refs (corp + pressure), valuation refs.
9. **Corporate strategic response phase** (§73, NEW) — one candidate per firm. Carries the option, never the act: theme refs (across all investors that talked to the firm), dialogue refs (with this firm), signal refs (corp + pressure), valuation refs (on this firm), `trigger_industry_condition_ids` (the firm's industry's per-period condition).
10. **Review phase** (§55) — one investor review run + one bank review run.

**Setup-time (NEW, idempotent, fires once per kernel):** stewardship themes — one per (investor, theme_type) for `theme_types = ("capital_allocation_discipline", "governance_structure")` by default. The same theme tuple is echoed on every period summary's `stewardship_theme_ids` so a downstream consumer sees which themes were active without joining against the result.

### 76.4 Default fixture

The default fixture is the v1.9.last fixture plus three keyword-derived industries and four stewardship themes:

| Slice | Count | Source |
| --- | --- | --- |
| firms | 3 | unchanged |
| investors | 2 | unchanged |
| banks | 2 | unchanged |
| periods | 4 | unchanged |
| industries | 3 | derived from firm-id keyword (manufacturer / retailer / utility) |
| themes per investor | 2 | `_DEFAULT_STEWARDSHIP_THEME_TYPES` |
| stewardship themes (setup) | 4 | `2 investors × 2 themes` |

The `industry_ids` are deduplicated from `firm_industry_map.values()` and sorted for canonical-view determinism. Callers may override via `firm_industry_map=` and `industry_demand_states=` kwargs.

### 76.5 Performance boundary (binding)

The v1.10.5 per-period formula and per-run window are pinned by `tests/test_living_reference_world_performance_boundary.py` and `count_expected_living_world_records`:

```
per_period_total =
    2 * firms                    # corporate run + corporate signal
  + firms                        # firm pressure signal (v1.9.4)
  + industries                   # industry demand condition (v1.10.4)
  + 2 * (investors + banks)      # menu + selection
  + investors * firms            # valuation (v1.9.5)
  + banks * firms                # bank credit review (v1.9.7)
  + investors * firms            # dialogue (v1.10.2)
  + investors * firms            # escalation candidate (v1.10.3 investor)
  + firms                        # response candidate (v1.10.3 corporate)
  + 2 * (investors + banks)      # review run + review signal
```

For the default fixture (firms=3, investors=2, banks=2, industries=3, periods=4):

- per-period: **55 records** (was 37 at v1.9.last; **+18** v1.10.5: +3 industry, +6 dialogue, +6 escalation, +3 response).
- per-run total formula: 55 × 4 = **220 records**.
- setup allowance (one-off): up to **32 records** (14 v1.9.x infra + 4 v1.10.5 stewardship themes + headroom). The historical v1.9.last allowance was the same 32; v1.10.5 fits within it.
- per-run window: **[220, 252]** (formula → formula + 32 setup headroom).

The bounded all-pairs loops are **demo-bounded only**. Production-scale traversal still requires sparse gating per §68. v1.10.5 does *not* introduce any new dense traversal: the dialogue and escalation loops are the same `investors × firms` shape that valuation already walks; the response loop is `firms` only; the industry loop is `industries` only.

### 76.6 Living-world digest (expected change)

The v1.10.5 living-world digest is **not** equal to the v1.9.last digest. The canonical view now carries:

- setup-level `industry_ids` / `industry_count` / `stewardship_theme_ids` / `stewardship_theme_count`;
- per-period `industry_condition_ids` / `stewardship_theme_ids` / `dialogue_ids` / `investor_escalation_candidate_ids` / `corporate_strategic_response_candidate_ids`;
- the extended `boundary_statement` covering the v1.10 anti-claims.

This is **expected** and is part of v1.10.5's freeze surface. Tests assert that two fresh runs of the v1.10.5 default fixture produce *byte-identical* canonical JSON and the same digest, but no test pins the v1.10.5 digest to the v1.9.last digest. The default-fixture digest at v1.10.5 is `2e21cd0e2d12c92fff56e7de193c2acf6a1a59489b32643add4aa4b157f6e652`.

### 76.7 What v1.10.5 tests pin

`tests/test_living_reference_world.py` adds 15 v1.10.5-specific integration tests on top of the v1.9.x suite:

- one industry condition per industry per period;
- conditions resolve to `IndustryConditionBook` with strength / confidence in `[0.0, 1.0]`;
- stewardship themes are setup-level (`investors × theme_types` records, same tuple on every period summary);
- stewardship-theme registration is idempotent across re-runs on the same kernel;
- one dialogue per (investor, firm) per period; dialogues resolve and carry the firm's pressure signal in the dedicated v1.10.2 slot;
- one investor escalation candidate per (investor, firm) per period; escalations resolve and link the same period's dialogue;
- one corporate response candidate per firm per period;
- corporate response candidates use the v1.10.4.1 `trigger_industry_condition_ids` slot for industry-condition refs and **never** `trigger_signal_ids` (an explicit anti-leak assertion);
- no v1.10.5 ledger payload across the integrated demo carries any of `vote_cast` / `proposal_filed` / `campaign_executed` / `exit_executed` / `letter_sent` / `buyback_executed` / `dividend_changed` / `divestment_executed` / `merger_executed` / `board_change_executed` / `disclosure_filed` / `transcript` / `content` / `notes` / `minutes` / `attendees` / `verbatim` / `paraphrase` / `body` / `forecast_value` / `revenue_forecast` / `sales_forecast` / `market_size` / `demand_index_value` / `vendor_consensus` / `consensus_forecast` / `real_data_value` keys;
- the integrated sweep emits no `order_submitted` / `price_updated` / `contract_*` / `ownership_*` / `institution_action_recorded` / `firm_state_added` records;
- the engagement phases mutate no other source-of-truth book (`ownership` / `contracts` / `prices` / `constraints` / `institutions` / `external_processes` / `relationships` snapshots before / after match exactly);
- two fresh runs produce byte-identical canonical JSON and the same `living_world_digest`;
- the canonical view surfaces the v1.10 id tuples explicitly so a downstream lineage / replay consumer does not have to re-walk the ledger.

The CLI smoke test pins the `industry=` / `themes=` / `dialogues=` / `escalations=` / `responses=` columns and the v1.10 anti-claims in the summary line.

### 76.8 No-behavior boundary (binding)

v1.10.5 is **integration only**. It does **not**:

- introduce any new mechanism, new `MechanismAdapter`, new `RecordType`, new book, or new kernel attribute;
- mutate any source-of-truth book outside the v1.10 storage books (and the kernel ledger's append-only growth);
- enforce any vocabulary against any country / regulator / code / named institution — every controlled-vocabulary tag remains illustrative;
- emit voting, proxy filing, public-campaign, exit, AGM / EGM action, corporate-action execution (buyback / dividend / divestment / merger / governance change), disclosure-filing execution, demand / sales / revenue forecasting, firm financial-statement updates, investment recommendation, trading, price formation, lending decisions, real-data ingestion, Japan calibration, jurisdiction-specific stewardship codes, or calibrated behavior probabilities;
- alter the v1.9.5 / v1.9.7 mechanism contracts. Valuation and credit-review inputs are unchanged; the v1.10 phases are downstream of those mechanisms in the runtime order, not upstream.

### 76.9 What v1.10.5 does not decide

- The v1.10.last freeze gate (anti-claim list, scope-language audit, forbidden-token scan, CI green on the tag commit). v1.10.last lands as a docs-only follow-up.
- The fixture composition for v2.x Japan public-data calibration. The v1.10.5 demo remains 100% synthetic.
- Whether the meta-abstractions (`actor_business_model_transition_pressure`, `actor_strategic_response_candidate`) ever ship in public FWE. The deferral rule of §70.4 stays in force; v1.10.5 does *not* introduce them.

### 76.10 Position in the v1.10 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 Universal Engagement / Strategic Response Consolidation | Docs-only (§70). | Shipped |
| v1.10.1 Stewardship theme signal | Code (§71). | Shipped |
| v1.10.2 Portfolio-company dialogue record | Code (§72). | Shipped |
| v1.10.3 Investor escalation candidate + corporate strategic response candidate | Code (§73). | Shipped |
| v1.10.4 Industry demand condition signal | Code (§74). | Shipped |
| v1.10.4.1 Type-correct industry-condition cross-reference slot | Code (§75). Additive. | Shipped |
| v1.10.5 Living-world integration | Code (§76). | Shipped |
| v1.11.0 Capital-market surface | Code (§77). | Shipped |
| v1.11.1 Capital-market readout | Code (§78). Additive readout layer. | Shipped |
| v1.11.2 Demo market regime presets | Code (§79). Additive demo-only preset layer. | Shipped |
| **v1.12.0 Firm financial latent state** | Code (§80). First time-crossing endogenous state-update layer. | **Shipped** |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

The test count moves from `1932 / 1932` (v1.10.4.1) to `1947 / 1947` (v1.10.5) — `+15` v1.10.5 integration tests in `tests/test_living_reference_world.py`. The CLI surface, the default fixture *shape*, the per-period flow, and the reproducibility surface all grow additively; the `living_world_digest` value changes (expected — see §76.6) and the per-run record window widens from `[148, 180]` to `[220, 252]` (documented — see §76.5).

## 77. v1.11.0 Capital-market surface — synthetic context evidence

§77 adds a jurisdiction-neutral *capital-market context* layer to public FWE: a `MarketConditionRecord` shape and a `MarketConditionBook` storing one record per (synthetic market, period) pair. The layer makes the living reference world visibly **finance-aware** — interest-rate environment, credit-spread environment, equity-valuation environment, funding window, liquidity / volatility regime — without implementing **any** of price formation, trading, yield-curve calibration, order matching, clearing, security recommendation, DCM / ECM execution, loan origination, lending decisions, covenant enforcement, or portfolio-allocation decisions. The runtime, the v1.9 / v1.10 mechanism contracts, and every existing book are unchanged. The v1.10 hard boundary (§70.3) and the meta-abstraction deferral rule (§70.4) continue to hold without modification, and v1.11 adds its own anti-claim list to the public-FWE freeze surface.

### 77.1 Why this exists

v1.10.5's living world reads, to a banker eye, like a *governance and stewardship* demo: stewardship themes → dialogues → escalation candidates → corporate response candidates. That is intentional and accurate, but it leaves the *capital-market surface* invisible. v1.11.0 names that surface as a small set of synthetic, jurisdiction-neutral context records so a viewer can see at a glance that the engine sits inside a financial-market world without the engine claiming to forecast, price, or recommend anything.

This is *context*, not behavior. The v1.10 anti-claim list ("no price formation, no trading, no lending decisions, no investment advice") carries forward unchanged; v1.11 adds a parallel anti-claim list for the capital-market surface ("no yield-curve calibration, no order matching, no clearing, no quote dissemination, no security recommendation, no DCM / ECM execution, no portfolio-allocation decisions") that is enforced by tests on both the dataclass field set and the ledger payload key set.

### 77.2 What v1.11.0 ships

- `world/market_conditions.py` (new) — `MarketConditionRecord` (immutable dataclass) + `MarketConditionBook` (append-only store) + `DuplicateMarketConditionError` / `UnknownMarketConditionError`. Same shape pattern as v1.10.4 `IndustryDemandConditionRecord`. Bounded synthetic `strength` and `confidence` in `[0.0, 1.0]` with explicit bool rejection (matching v1 `world/exposures.py`). Listings: `list_conditions`, `list_by_market`, `list_by_market_type`, `list_by_condition_type`, `list_by_direction`, `list_by_status`, `list_by_date`, `snapshot`.
- `world/ledger.py` — `RecordType.MARKET_CONDITION_ADDED`, emitted exactly once per `add_condition` call.
- `world/kernel.py` — `market_conditions: MarketConditionBook` wired in `WorldKernel.__post_init__` with the same ledger / clock injection pattern every other source-of-truth book uses.
- `world/strategic_response.py` — additive field `trigger_market_condition_ids: tuple[str, ...] = ()` on `CorporateStrategicResponseCandidate` + new `list_by_market_condition` filter on `StrategicResponseCandidateBook`. **Type-correct cross-reference slot**, parallel to the v1.10.4.1 `trigger_industry_condition_ids` slot. Market-condition ids must **never** ride in `trigger_signal_ids` (a `SignalBook` slot) or in `trigger_industry_condition_ids` (a v1.10.4 industry-condition slot); the v1.11.0 slot is what keeps `signal_id` / `industry_condition_id` / `market_condition_id` distinguishable in ledger replay, lineage reconstruction, and report generation by *field*, not by *payload introspection*.
- `world/reference_living_world.py` — new per-period market-condition phase between firm pressure and attention. The orchestrator gains a `market_condition_specs` kwarg; default is a 5-market set covering reference rates, credit spreads, equity valuation environment, funding window, and liquidity / volatility regime. `LivingReferencePeriodSummary` grows with `market_condition_ids`; `LivingReferenceWorldResult` grows with setup-level `market_ids`. Every new field defaults to `()` so older callers keep working. The corporate response candidate now cites every period's full market-condition id set via the v1.11.0 type-correct slot.
- `world/living_world_report.py` — `LivingWorldPeriodReport` grows with `market_condition_count`; the Markdown renderer adds a `## Capital market conditions` section (one row per period showing the count). The boundary statement is extended in place to cover the v1.11 anti-claims; the v1.9.1 / v1.10.5 prefixes are preserved verbatim.
- `examples/reference_world/living_world_replay.py` — the canonical view echoes setup-level `market_ids` / `market_count` plus per-period `market_condition_ids`. The boundary statement constant tracks the reporter's. **Expected digest change**: the v1.11.0 living-world digest is *not* the same as the v1.10.5 digest — the canonical view now includes the new id tuples and the boundary string was extended. Two fresh runs of the v1.11.0 default fixture produce byte-identical canonical JSON and the same digest; the digest just differs from v1.10.5.
- `examples/reference_world/living_world_manifest.py` — manifest summary echoes the new counts (`market_count`, `market_condition_total`).
- `examples/reference_world/run_living_reference_world.py` — per-period CLI trace line names `market_conditions=`; the setup line names `markets=`; the summary line names the v1.11 anti-claims.
- `tests/test_market_conditions.py` (new) — 84 tests covering field validation, bounded numeric fields with explicit bool rejection, immutability, duplicate rejection, unknown lookup, every list / filter, deterministic snapshots, ledger emission, kernel wiring, no-mutation guarantee against every other source-of-truth book (including all v1.10.x siblings), no-action / no-price-formation invariant, the explicit anti-fields assertion against `price` / `market_price` / `yield_value` / `spread_bps` / `index_level` / `forecast_value` / `expected_return` / `recommendation` / `target_price` / `real_data_value` / `market_size` on both the dataclass and the ledger payload, plain-id cross-reference acceptance, an explicit v1.10.3 ↔ v1.11.0 link test (citing a market-condition id from a `CorporateStrategicResponseCandidate.trigger_market_condition_ids` slot and asserting the slot-cleanliness of `trigger_signal_ids` and `trigger_industry_condition_ids`), and a jurisdiction-neutral identifier scan over both module and test file.
- `tests/test_strategic_response.py` — extended with `+4` tests for the v1.11.0 cross-reference slot (default empty tuple, listing, anti-leak from signal slot, anti-leak from industry slot) plus an additional parametrize entry for the empty-string-rejection test on the new tuple field. Existing to_dict / payload / unresolved-trigger / no-mutation tests are extended in place.
- `tests/test_living_reference_world.py` — extended with `+8` v1.11.0 integration tests: market-condition per market per period, conditions resolve to `MarketConditionBook` with strength / confidence in `[0.0, 1.0]`, default markets cover the finance surface (rates / credit / equity / funding / liquidity), corporate response candidates use the v1.11.0 slot and never `trigger_signal_ids` / `trigger_industry_condition_ids`, no v1.11.0 ledger payload across the integrated demo carries any of the anti-fields, no forbidden action / price-formation event types appear, two fresh runs produce byte-identical canonical JSON and the same digest, and the canonical view surfaces the v1.11.0 id tuples explicitly.
- `tests/test_living_reference_world_performance_boundary.py` — `count_expected_living_world_records` and the per-run upper-bound test refreshed for the v1.11.0 fixture.

### 77.3 Per-period flow (runtime order, v1.11.0)

```
1. corporate quarterly report (§49)
2. firm operating-pressure assessment (§64)
3. industry demand condition (§74)
3a. capital-market condition (§77) — NEW
4. heterogeneous attention (§54)
5. valuation refresh lite (§65)
6. bank credit review lite (§67)
7. portfolio-company dialogue metadata (§72)
8. investor escalation candidate (§73, investor side)
9. corporate strategic response candidate (§73, corporate side)
   → cites every period's market-condition id set in the v1.11.0
     ``trigger_market_condition_ids`` slot
10. review routines (§55)
```

Setup-time (idempotent): stewardship themes (§71). v1.11.0 adds no new setup records.

### 77.4 Default fixture

The v1.11.0 default extends the v1.10.5 fixture with five synthetic markets:

| Slice | Count | Notes |
| --- | --- | --- |
| firms | 3 | unchanged |
| investors | 2 | unchanged |
| banks | 2 | unchanged |
| periods | 4 | unchanged |
| industries | 3 | unchanged |
| themes per investor | 2 | unchanged |
| markets | 5 | reference rates, credit spreads, equity valuation, funding window, liquidity/volatility (NEW) |

Every market spec carries a deterministic `(direction, strength, confidence, time_horizon)` triple chosen to be visible / distinguishable in the report — never calibrated to any real yield, spread, index, level, or forecast. Callers may override via the `market_condition_specs` kwarg.

### 77.5 Performance boundary (binding)

The v1.11.0 per-period formula and per-run window are pinned by `tests/test_living_reference_world_performance_boundary.py` and `count_expected_living_world_records`:

```
per_period_total =
    2 * firms                    # corporate run + corporate signal
  + firms                        # firm pressure signal (v1.9.4)
  + industries                   # industry demand condition (v1.10.4)
  + markets                      # capital-market condition (v1.11.0)
  + 2 * (investors + banks)      # menu + selection
  + investors * firms            # valuation (v1.9.5)
  + banks * firms                # bank credit review (v1.9.7)
  + investors * firms            # dialogue (v1.10.2)
  + investors * firms            # escalation candidate (v1.10.3 investor)
  + firms                        # response candidate (v1.10.3 corporate)
  + 2 * (investors + banks)      # review run + review signal
```

For the default fixture (firms=3, investors=2, banks=2, industries=3, markets=5, periods=4):

- per-period: **60 records** (was 55 at v1.10.5; **+5** v1.11.0).
- per-run total formula: 60 × 4 = **240 records**.
- setup allowance: up to **32 records** (14 v1.9.x infra + 4 v1.10.5 stewardship themes + headroom; v1.11.0 adds **0** new setup records — the market-condition phase is per-period only).
- per-run window: **[240, 272]**.

The market-condition loop is `O(P × N)` where `N` is the number of markets — linear in `markets`, not in any actor count. v1.11.0 introduces **no new dense traversal**.

### 77.6 Living-world digest (expected change)

The v1.11.0 living-world digest is **not** equal to the v1.10.5 digest. The canonical view now carries:

- setup-level `market_ids` / `market_count`;
- per-period `market_condition_ids`;
- the extended `boundary_statement` covering the v1.11 anti-claims.

This is **expected** and is part of v1.11.0's freeze surface. Tests assert that two fresh runs of the v1.11.0 default fixture produce *byte-identical* canonical JSON and the same digest. The default-fixture digest at v1.11.0 is `bb572567d87ba34ff94dca2db99bf7671ea061222a520ed9830a39e29ac54a11`.

### 77.7 Anti-fields (binding)

The dataclass deliberately has **no** `price`, `market_price`, `yield_value`, `spread_bps`, `index_level`, `forecast_value`, `expected_return`, `recommendation`, `target_price`, `real_data_value`, or `market_size` field. The ledger payload likewise carries none of these keys. Two explicit tests (`test_condition_record_has_no_price_or_forecast_field`, `test_add_condition_payload_carries_no_price_or_forecast_keys`) introspect the dataclass field set and the ledger payload key set respectively. A future v1.11.x or later milestone that introduces such a field would by construction trip these tests.

### 77.8 No-behavior boundary (binding)

A `MarketConditionRecord` and the `MarketConditionBook` storing it are jurisdiction-neutral, signal-only, behavior-free, and price-free. v1.11.0 does **not**:

- form any price, quote, yield, spread, or index level (no order matching, no microstructure, no clearing);
- trade, allocate, or recommend any security;
- originate, approve, reject, price, or mutate any loan / contract / covenant / ownership relation;
- mutate any firm financial statement;
- forecast any market level, return, or default probability;
- issue, allocate, or price any DCM / ECM offering;
- introduce voting, proxy filing, public-campaign execution, exit execution, AGM / EGM action, corporate-action execution, disclosure-filing execution, demand / sales / revenue forecasting, real-data ingestion, Japan calibration, jurisdiction-specific market codes, or calibrated behavior probabilities;
- mutate any other source-of-truth book (the no-mutation test asserts this against ownership, contracts, prices, constraints, signals, valuations, institutions, external_processes, relationships, interactions, routines, attention, variables, exposures, stewardship, engagement, escalations, strategic_responses, and industry_conditions);
- enforce membership of `market_id`, `market_type`, `condition_type`, `direction`, `time_horizon`, `status`, or `visibility` against any controlled vocabulary — the recommended labels are illustrative;
- emit any ledger record other than `MARKET_CONDITION_ADDED` from a bare `add_condition` call.

### 77.9 What v1.11.0 does not decide

- The v1.10.last freeze gate. v1.10.last is a docs-only freeze for the v1.10 engagement layer; v1.11.0 layers on top without altering the v1.10 freeze surface.
- The fixture composition for v2.x Japan public-data calibration. The v1.11.0 demo remains 100% synthetic.
- The interface for *consumer* mechanisms reading market conditions (e.g., a future "valuation refresh adjusted for funding window" mechanism). v1.11.0 makes market conditions *citable* by plain id from any future or existing layer; it does not change v1.9.5 / v1.9.7 mechanism contracts. The corporate response candidate is the only existing artifact updated to cite market conditions, via the v1.11.0 type-correct slot.

### 77.10 Position in the v1.11 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 → v1.10.5 (engagement / strategic-response stack) | Code (§70 → §76). | Shipped |
| v1.11.0 Capital-market surface | Code (§77). | Shipped |
| v1.11.1 Capital-market readout | Code (§78). Additive readout layer. | Shipped |
| v1.11.2 Demo market regime presets | Code (§79). Additive demo-only preset layer. | Shipped |
| **v1.12.0 Firm financial latent state** | Code (§80). First time-crossing endogenous state-update layer. | **Shipped** |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

The test count moves from `1947 / 1947` (v1.10.5) to `2043 / 2043` (v1.11.0) — `+96` tests (`+84` in the new `tests/test_market_conditions.py`, `+4` in `tests/test_strategic_response.py` for the v1.11.0 cross-reference slot, `+8` v1.11.0 integration tests in `tests/test_living_reference_world.py`). The CLI surface, the default fixture *shape*, the per-period flow, and the reproducibility surface all grow additively; the `living_world_digest` value changes (expected — see §77.6) and the per-run record window widens from `[220, 252]` to `[240, 272]` (documented — see §77.5).

## 78. v1.11.1 Capital-market readout — banker-readable surface labels

§78 adds a *readout* layer on top of v1.11.0's capital-market surface: a deterministic, jurisdiction-neutral summary of one period's worth of synthetic `MarketConditionRecord` instances into per-market tone tags + an overall market-access label + a short banker-summary label. The runtime, the v1.9 / v1.10 / v1.11.0 mechanism and book contracts, and every existing record type are unchanged. v1.11.1 is **a readout / report artifact**, not a new economic model and not a decision engine. The v1.10 hard boundary (§70.3) and the meta-abstraction deferral rule (§70.4) continue to hold without modification, and v1.11.1 adds its own anti-claim list to the public-FWE freeze surface.

### 78.1 Why this exists

v1.11.0 made the capital-market surface *visible* by emitting per-period market-condition records. v1.11.1 makes that surface *banker-readable*: instead of forcing a viewer to inspect five condition records and reason about them, the readout gives one labeled summary row per period — rates / credit / equity / funding window / liquidity / volatility tones plus an overall market-access label (`open_or_constructive` / `selective_or_constrained` / `mixed`).

This is a presentation layer. It produces *labels*, not prices, yields, spreads, forecasts, recommendations, target prices, deal advice, market sizes, or real-data values.

### 78.2 What v1.11.1 ships

- `world/market_surface_readout.py` (new):
  - `CapitalMarketReadoutRecord` (immutable dataclass) with the v1.11.1 anti-fields binding (no `price` / `target_price` / `yield_value` / `spread_bps` / `forecast_value` / `expected_return` / `recommendation` / `deal_advice` / `market_size` / `real_data_value`).
  - `CapitalMarketReadoutBook` (append-only store) with `add_readout`, `get_readout`, `list_readouts`, `list_by_date`, `list_by_status`, `list_by_overall_market_access_label`, `snapshot`.
  - `build_capital_market_readout(kernel, *, as_of_date, market_condition_ids, ...)` — deterministic builder reading `MarketConditionRecord` instances and applying the v1.11.1 rule set. Idempotent on `readout_id`.
  - Errors: `DuplicateCapitalMarketReadoutError`, `UnknownCapitalMarketReadoutError`.
- `world/ledger.py` — `RecordType.CAPITAL_MARKET_READOUT_ADDED`, emitted exactly once per `add_readout` call.
- `world/kernel.py` — `capital_market_readouts: CapitalMarketReadoutBook` wired in `WorldKernel.__post_init__`.
- `world/reference_living_world.py` — new per-period readout phase that fires once per period after the v1.11.0 market-condition phase. `LivingReferencePeriodSummary` grows additively with `capital_market_readout_ids`.
- `world/living_world_report.py` — `LivingWorldPeriodReport` grows with `capital_market_readout_count` plus the seven label fields (`rates_tone` / `credit_tone` / `equity_tone` / `funding_window_tone` / `liquidity_tone` / `volatility_tone` / `overall_market_access_label`); the Markdown renderer adds a `## Capital market surface` section between `## Capital market conditions` and `## v1.10 engagement / response`. The boundary statement is extended in place to cover the v1.11.1 anti-claims; the v1.9.1 / v1.10.5 / v1.11.0 prefixes are preserved verbatim.
- `examples/reference_world/living_world_replay.py` — the canonical view echoes `capital_market_readout_ids` per period; the boundary statement constant tracks the reporter's. **Expected digest change**: the v1.11.1 living-world digest is *not* the same as the v1.11.0 digest — the canonical view now includes the new id tuple and the boundary string was extended.
- `examples/reference_world/living_world_manifest.py` — manifest summary echoes the new `capital_market_readout_total` count.
- `examples/reference_world/run_living_reference_world.py` — per-period CLI trace line names `market_readouts=`.
- `tests/test_market_surface_readout.py` (new) — 72 tests covering field validation, bounded `confidence` with bool rejection, anti-fields on dataclass + ledger payload, listings (`list_readouts`, `list_by_date`, `list_by_status`, `list_by_overall_market_access_label`), snapshot determinism, ledger emission, kernel wiring, no-mutation against every other source-of-truth book (including v1.11.0 `MarketConditionBook`), no-action / no-pricing / no-issuance ledger assertion, the builder's deterministic rule set (mapping every v1.11.0 `market_type` to its tone slot, the three `overall_market_access_label` branches, idempotency on `readout_id`, average-confidence math, `volatility_regime` market overriding the `liquidity_market` fallback, "unknown" defaults for missing market types, no-mutation against `MarketConditionBook` during build), and a jurisdiction-neutral identifier scan over both module and test file.
- `tests/test_living_reference_world.py` — `+7` v1.11.1 integration tests: one readout per period, readouts resolve and carry default labels, default overall is `open_or_constructive`, no forbidden price / advice payload keys end-to-end, two fresh runs produce byte-identical canonical view, canonical view carries the readout id tuples, Markdown report includes the `## Capital market surface` section.
- `tests/test_living_reference_world_performance_boundary.py` — `count_expected_living_world_records` and the per-run upper-bound test refreshed for the v1.11.1 fixture.

### 78.3 Builder rule set (binding)

The builder reads each cited `MarketConditionRecord` and overlays its `direction` onto the tone slot named by its `market_type`:

| Source `market_type` | Target tone slot |
| --- | --- |
| `reference_rates` | `rates_tone` |
| `credit_spreads` | `credit_tone` |
| `equity_market` | `equity_tone` |
| `funding_market` | `funding_window_tone` |
| `liquidity_market` | `liquidity_tone` |
| `volatility_regime` | `volatility_tone` |

Tone slots not populated by any condition default to `"unknown"`. Conditions whose `market_type` is not in this map are ignored (no error) so the builder is forward-compatible with caller-defined market types.

The overall classifier:

```
if funding_window_tone in {"supportive", "easing", "narrowing", "open"}
   and credit_tone not in {"restrictive", "widening", "tightening"}:
    overall_market_access_label = "open_or_constructive"
elif credit_tone in {"restrictive", "widening", "tightening"}
     and liquidity_tone in {"restrictive", "tightening", "widening"}:
    overall_market_access_label = "selective_or_constrained"
else:
    overall_market_access_label = "mixed"
```

The banker-summary label is a deterministic 1:1 map:

| `overall_market_access_label` | `banker_summary_label` |
| --- | --- |
| `open_or_constructive` | `constructive_market_access_synthetic` |
| `selective_or_constrained` | `selective_market_access_synthetic` |
| `mixed` | `mixed_market_access_synthetic` |

`confidence` is the arithmetic mean of the cited conditions' `confidence` values, clamped to `[0.0, 1.0]`. With zero cited conditions it is `0.5` by convention.

The rule set is small, documented, and reproducible. No rule is a recommendation; each branch returns a label, never a market view.

### 78.4 Anti-fields (binding)

The dataclass deliberately has **no** `price`, `target_price`, `yield_value`, `spread_bps`, `forecast_value`, `expected_return`, `recommendation`, `deal_advice`, `market_size`, or `real_data_value` field. The ledger payload likewise carries none of these keys. Two explicit tests (`test_readout_record_has_no_price_or_advice_field`, `test_add_readout_payload_carries_no_price_or_advice_keys`) introspect the dataclass field set and the ledger payload key set respectively. A future v1.11.x or later milestone that introduces such a field would by construction trip these tests.

### 78.5 Performance boundary (binding)

v1.11.1 adds **one** record per period. The per-period formula gains `capital_market_readouts_per_period` (default `1`); the per-run formula moves from 240 to **244** for the default fixture; the per-run window moves from `[240, 272]` to **`[244, 276]`**. The readout phase is `O(P)` (one readout per period) — no actor-count multiplier, no industry-count multiplier, no market-count multiplier (the readout *reads* `M` conditions, but emits one record). The performance boundary discipline of §68 / §76 / §77 carries forward unchanged.

### 78.6 Living-world digest (expected change)

The v1.11.1 living-world digest is **not** equal to the v1.11.0 digest. The canonical view now carries `capital_market_readout_ids` per period and the boundary string was extended. This is **expected** and is part of v1.11.1's freeze surface. Tests assert that two fresh runs of the v1.11.1 default fixture produce *byte-identical* canonical JSON and the same digest. The default-fixture digest at v1.11.1 is `209ff81682d331a9700e5c3c8dfac9aa9ecfa028757db6b060f75590249833ea`.

### 78.7 No-behavior boundary (binding)

A `CapitalMarketReadoutRecord` and the `CapitalMarketReadoutBook` storing it are jurisdiction-neutral, signal-only, label-only, and price-free. v1.11.1 does **not**:

- price, quote, calibrate, or recommend any security, deal, instrument, or market;
- execute any DCM / ECM action, security issuance, loan origination, trade, order match, or clearing event;
- mutate any firm financial statement;
- forecast any market level, return, default probability, or any real-world quantity;
- emit any spread / yield / index / market-size / real-data value;
- mutate any other source-of-truth book (the no-mutation test asserts this against ownership, contracts, prices, constraints, signals, valuations, institutions, external_processes, relationships, interactions, routines, attention, variables, exposures, stewardship, engagement, escalations, strategic_responses, industry_conditions, and market_conditions);
- enforce membership of any tone tag, status tag, visibility tag, or label against any controlled vocabulary — the recommended labels are illustrative;
- emit any ledger record other than `CAPITAL_MARKET_READOUT_ADDED` from a bare `add_readout` call.

### 78.8 What v1.11.1 does not decide

- The fixture composition for v2.x Japan public-data calibration. The v1.11.1 demo remains 100% synthetic.
- Whether and how a future v1.12 funding / issuance intent layer will *consume* the readout. v1.11.1 makes the readout citable by plain id; it does not introduce any new consumer. v1.12 may add a `trigger_capital_market_readout_ids` slot on a future intent record, mirroring the v1.10.4.1 / v1.11.0 type-correct cross-reference patterns.
- The *content* of the rule set beyond the documented v1.11.1 minimum. A future milestone may extend the rule set (e.g., add a "rates_tightening" trigger) without breaking the v1.11.1 freeze surface, as long as the deterministic / no-recommendation discipline is preserved.

### 78.9 Position in the v1.11 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 → v1.10.5 (engagement / strategic-response stack) | Code (§70 → §76). | Shipped |
| v1.11.0 Capital-market surface | Code (§77). | Shipped |
| v1.11.1 Capital-market readout | Code (§78). Additive readout layer. | Shipped |
| v1.11.2 Demo market regime presets | Code (§79). Additive demo-only preset layer. | Shipped |
| **v1.12.0 Firm financial latent state** | Code (§80). First time-crossing endogenous state-update layer. | **Shipped** |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v1.12 Funding / issuance intent layer (anticipated) | Code. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

The test count moves from `2043 / 2043` (v1.11.0) to `2122 / 2122` (v1.11.1) — `+79` tests (`+72` in the new `tests/test_market_surface_readout.py`, `+7` v1.11.1 integration tests in `tests/test_living_reference_world.py`). The CLI surface, the default fixture *shape*, the per-period flow, and the reproducibility surface all grow additively; the `living_world_digest` value changes (expected — see §78.6) and the per-run record window widens from `[240, 272]` to `[244, 276]` (documented — see §78.5).

## 79. v1.11.2 Demo market regime presets

§79 adds a small set of synthetic, jurisdiction-neutral *demo presets* on top of v1.11.0's capital-market surface so the living reference world can be run under different market environments without adding any real data, calibrated yields, calibrated spreads, forecasts, recommendations, or transactions. The runtime, the v1.11.0 record contract, the v1.11.1 readout contract, the v1.10 hard boundary (§70.3), and every existing book are unchanged. v1.11.2 is **a demo-configuration layer**, not a new economic model and not a decision engine.

### 79.1 Why this exists

The default fixture lands on the `open_or_constructive` overall label every period — which is fine for a baseline demo but does not let a banker viewer see the engine running under different environments. v1.11.2 ships four named presets that each deterministically alter only the synthetic `(direction, strength, confidence, time_horizon)` tuples on the orchestrator's per-period market-condition specs. The v1.11.1 readout classifier then reaches a different branch per preset, so the rendered Markdown's `## Capital market surface` section visibly differs across regimes.

### 79.2 What v1.11.2 ships

- `world/reference_living_world.py`:
  - new module-level `_REGIME_PRESETS: Mapping[str, tuple[_MarketConditionSpec, ...]]` defining `constructive` / `mixed` / `constrained` / `tightening`;
  - new `market_regime: str | None = None` kwarg on `run_living_reference_world` with documented resolution order:
    1. caller-supplied `market_condition_specs` (full override; regime ignored);
    2. caller-supplied `market_regime` (selects one preset; unknown name raises `ValueError`);
    3. fall back to the v1.11.0 default 5-market spec set (preserves backward compatibility — see §79.5).
- `examples/reference_world/run_living_reference_world.py`:
  - new `--market-regime constructive|mixed|constrained|tightening` CLI flag with `argparse` `choices`;
  - regime banner line `[regime]  market_regime=<name> (v1.11.2 synthetic preset; no real data, no forecasts)` printed before the per-period trace when the flag is set.
- `tests/test_living_reference_world.py` — `+15` v1.11.2 tests: each regime runs and produces the documented overall label, each regime is byte-identically deterministic across two fresh runs, the four regimes produce distinct per-market tone signatures, default behavior unchanged when `market_regime` is `None` (v1.11.1 digest preserved), unknown regime raises `ValueError`, explicit `market_condition_specs` overrides `market_regime`, no regime sweep emits forbidden action / pricing / issuance event types, no regime payload carries forbidden price / forecast / recommendation / deal-advice keys, and a CLI smoke test for `--market-regime constrained` prints the regime banner and the per-period trace.

### 79.3 Regime → readout label map (binding)

| Regime | rates | credit | equity | funding window | liquidity | overall_market_access_label |
| --- | --- | --- | --- | --- | --- | --- |
| `constructive` | supportive | stable | supportive | supportive | stable | `open_or_constructive` |
| `mixed` | stable | stable | mixed | mixed | stable | `mixed` |
| `constrained` | tightening | restrictive | restrictive | mixed | tightening | `selective_or_constrained` |
| `tightening` | tightening | widening | mixed | tightening | tightening | `selective_or_constrained` |

The `tightening` regime is documented as also landing on `selective_or_constrained`: rates tightening flows through to credit (widening) and liquidity (tightening), while funding leaves the supportive set, so the v1.11.1 second classifier branch fires (`credit in {restrictive, widening, tightening}` AND `liquidity in {restrictive, tightening, widening}`). The `tightening` and `constrained` regimes therefore *share* an overall label but have visibly different per-market tone signatures (rates / credit / equity / funding direction differ), so a banker viewer can still tell them apart in the Markdown table.

### 79.4 Anti-fields and anti-claims (binding)

v1.11.2 changes only the synthetic `(direction, strength, confidence, time_horizon)` tuples on `MarketConditionRecord` instances. It does **not**:

- introduce any real yield, spread, index, level, market size, forecast, expected return, target price, recommendation, or deal advice;
- introduce any new record type, new book, new kernel attribute, new mechanism, or new ledger event;
- alter the v1.11.0 / v1.11.1 anti-fields list, the v1.10 hard boundary, or any existing test invariant;
- emit any pricing / yield-curve calibration / spread calibration / order-matching / clearing / DCM / ECM / loan-origination / lending-decision / portfolio-allocation / Japan-calibration / real-data record.

Tests pin the no-forbidden-event-type assertion and the no-forbidden-payload-key assertion across all four presets.

### 79.5 Backward compatibility

`market_regime=None` (default) preserves the v1.11.1 default behavior bit-for-bit. The default-fixture `living_world_digest` remains:

```
209ff81682d331a9700e5c3c8dfac9aa9ecfa028757db6b060f75590249833ea
```

A test (`test_v1_11_2_default_behavior_unchanged_when_regime_is_none`) explicitly compares the digest with the regime kwarg omitted to the digest with the regime kwarg passed as `None`, asserting equality. Existing callers and the existing CLI invocations (without `--market-regime`) continue to work unchanged.

When a regime is explicitly passed, the `living_world_digest` differs (different underlying tuples). Each regime is byte-identically deterministic across two fresh runs. The per-run record-count window is unchanged from v1.11.1: `[244, 276]` records, and the per-period record count remains 61.

### 79.6 What v1.11.2 does not decide

- The fixture composition for v2.x Japan public-data calibration. v1.11.2 remains 100% synthetic.
- Whether a future v1.12 funding / issuance intent layer should *consume* the regime label as a context input. v1.11.2 makes the label citable by reading the period's `CapitalMarketReadoutRecord.overall_market_access_label`; it does not introduce any consumer.
- The exact preset values beyond the v1.11.2 minimum. A future milestone may extend the preset set or alter individual values without breaking the v1.11.2 freeze surface, as long as: each preset stays deterministic and synthetic; the four named regimes continue to produce distinct per-market tone signatures; the regime → overall-label map in §79.3 stays consistent with the v1.11.1 classifier.

### 79.7 Position in the v1.11 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 → v1.10.5 (engagement / strategic-response stack) | Code (§70 → §76). | Shipped |
| v1.11.0 Capital-market surface | Code (§77). | Shipped |
| v1.11.1 Capital-market readout | Code (§78). | Shipped |
| **v1.11.2 Demo market regime presets** | Code (§79). Demo-config layer. | **Shipped** |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v1.12 Funding / issuance intent layer (anticipated) | Code. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

The test count moves from `2122 / 2122` (v1.11.1) to `2137 / 2137` (v1.11.2) — `+15` v1.11.2 tests in `tests/test_living_reference_world.py`. The CLI surface gains the `--market-regime` flag; the default fixture *shape*, the per-period record count, the per-run record window, and the default-fixture `living_world_digest` are all preserved unchanged.

## 80. v1.12.0 Firm financial latent state — first endogenous state-update layer

§80 ships the **first time-crossing endogenous state-update layer** in public FWE. It introduces `FirmFinancialStateRecord` + `FirmFinancialStateBook` + `run_reference_firm_financial_state_update`, a small synthetic latent-state layer that updates one record per (firm, period) by reading the period's evidence and the prior-period state for the same firm. Market regimes, capital-market readouts, industry-demand context, and pressure evidence now **accumulate over time** into a firm's latent state — the first place where v1.10.x → v1.11.x signal records propagate beyond their own period and shape future periods.

This is **a synthetic latent state update for endogenous dynamics** (per the task spec), not an accounting statement update. The record stores six bounded synthetic pressure / readiness scalars in `[0.0, 1.0]` plus a `confidence` scalar plus an explicit `previous_state_id` chain link to the prior-period state. It does **not** store revenue, sales, EBITDA, net income, cash balance, debt amount, real financial statements, forecasts, real measurements, accounting values, or investment recommendations.

### 80.1 Why this exists

Through v1.11.2 the living world emitted lots of records but every record's lifetime was confined to its own period. A market regime in period 1 had no influence on period 2's records. v1.12.0 closes the first endogenous loop: a firm's latent state at period N is a function of the prior state at period N-1 plus the new evidence available at period N. Constructive market regimes let pressures decay; constrained / tightening regimes amplify them; contracting industry demand raises margin pressure; pressure signals raise liquidity pressure. All deltas are small and clamped, so trajectories stay bounded but visibly differentiated.

### 80.2 What v1.12.0 ships

- `world/firm_state.py` (new):
  - `FirmFinancialStateRecord` (immutable dataclass) with seven bounded numeric scalars validated to `[0.0, 1.0]` with bool rejection (matching the v1.11.0 / v1.11.1 idiom). Anti-fields binding: no `revenue`, `sales`, `EBITDA`, `net_income`, `cash_balance`, `debt_amount`, `real_financial_statement`, `forecast_value`, `actual_value`, `accounting_value`, or `investment_recommendation` field.
  - `FirmFinancialStateBook` (append-only store) with `add_state` / `get_state` / `list_states` / `list_by_firm` / `list_by_date` / `get_latest_for_firm` / `history_for_firm` / `snapshot`. The `get_latest_for_firm` and `history_for_firm` helpers return records in **insertion order** (the v1.12 living-world orchestrator inserts in chronological order).
  - `run_reference_firm_financial_state_update(...)` — deterministic helper that resolves prior state (explicit `previous_state_id` overrides `get_latest_for_firm`), reads the cited evidence (market readouts / market conditions / industry conditions / pressure signals / valuations as plain ids), applies the v1.12.0 rule set, and emits exactly one record. Idempotent on `state_id`.
  - Errors: `DuplicateFirmFinancialStateError`, `UnknownFirmFinancialStateError`.
  - `FirmFinancialStateUpdateResult` dataclass returns the produced record + the resolved `previous_state_id`.
- `world/ledger.py` — new `RecordType.FIRM_LATENT_STATE_UPDATED` (event type `firm_latent_state_updated`). Deliberately distinct from the legacy v0/v1 `firm_state_added` registration record type so the new endogenous-state event is unambiguously distinguishable in the ledger.
- `world/kernel.py` — `firm_financial_states: FirmFinancialStateBook` wired in `WorldKernel.__post_init__`.
- `world/reference_living_world.py` — new per-period firm-state phase between the v1.11.1 readout phase and the v1.8.x attention phase. `LivingReferencePeriodSummary` grows additively with `firm_financial_state_ids`. The phase walks every firm, cites that firm's evidence (the period's readout, its mapped industry condition, and its pressure signal), and writes one state record per (firm, period).
- `world/living_world_report.py` — `LivingWorldPeriodReport` grows with `firm_financial_state_count` plus six bounded average-pressure scalars (`avg_margin_pressure`, `avg_liquidity_pressure`, `avg_debt_service_pressure`, `avg_market_access_pressure`, `avg_funding_need_intensity`, `avg_response_readiness`). The Markdown renderer adds a `## Firm financial states` section between the v1.10 engagement section and the attention divergence section. The boundary statement is extended in place to cover the v1.12 anti-claims; all prior prefixes are preserved verbatim.
- `examples/reference_world/living_world_replay.py` — the canonical view echoes `firm_financial_state_ids` per period; the boundary statement constant tracks the reporter's. **Expected digest change**: the v1.12.0 living-world digest is *not* the same as the v1.11.2 / v1.11.1 default digest — the canonical view now includes the new id tuple and the boundary string was extended.
- `examples/reference_world/living_world_manifest.py` — manifest summary echoes the new `firm_financial_state_total` count.
- `examples/reference_world/run_living_reference_world.py` — per-period CLI trace line names `firm_states=`; summary line names the firm-state phase and the v1.12 anti-claims.
- `tests/test_firm_state.py` (new) — 113 tests covering field validation, bounded numeric fields with bool rejection, anti-fields on dataclass + ledger payload, listings, snapshot determinism, ledger emission, kernel wiring, no-mutation against every other source-of-truth book (including v1.10.4 / v1.11.0 / v1.11.1 books), no-action / no-pricing / no-firm_state_added invariant, the helper's deterministic rule set (idempotency, chain via explicit `previous_state_id`, chain via `get_latest_for_firm`, neutral baseline when no prior state, constructive decay, constrained amplification, multi-period chained constructive vs constrained gap, contracting / expanding industry effects, pressure-signal-count effect on liquidity, derived `funding_need_intensity` and `response_readiness` arithmetic, clamping under saturation, helper-does-not-mutate-evidence-books), plus a jurisdiction-neutral identifier scan over both module and test file.
- `tests/test_living_reference_world.py` — `+9` v1.12.0 integration tests: one state per firm per period, states resolve and carry bounded scalars, states chain via `previous_state_id` within a run, constructive regime yields lower end-of-run market_access_pressure than constrained (visible separation > 0.3), no forbidden accounting / forecast payload keys end-to-end, no `firm_state_added` (legacy) event types appear, two fresh runs produce byte-identical canonical view, canonical view carries the new id tuples explicitly, Markdown report includes the `## Firm financial states` section.
- `tests/test_living_reference_world_performance_boundary.py` — `count_expected_living_world_records` and the per-run upper-bound test refreshed for the v1.12.0 fixture.

### 80.3 Update rule set (binding, illustrative, deterministic)

Each call to `run_reference_firm_financial_state_update`:

1. **Resolves prior state.** If `previous_state_id` is supplied, fetch it. Else call `book.get_latest_for_firm(firm_id)`. If neither is available, start from a neutral baseline `0.5` for every pressure scalar.
2. **Reads readout evidence.** For each cited `CapitalMarketReadoutRecord`:
   - if `overall_market_access_label == "open_or_constructive"`: market_access_pressure -= 0.05; debt_service_pressure -= 0.03;
   - if `overall_market_access_label == "selective_or_constrained"`: market_access_pressure += 0.10; debt_service_pressure += 0.05;
   - if `overall_market_access_label == "mixed"`: market_access_pressure += 0.02;
   - if `credit_tone in {"restrictive", "widening", "tightening"}`: debt_service_pressure += 0.05.
3. **Reads market-condition evidence (only if no readout was cited).** Avoids double-counting the credit signal under the default living-world wiring where both readout and conditions are cited together.
4. **Reads industry-demand evidence.** For each cited `IndustryDemandConditionRecord`:
   - if `demand_direction in {"contracting", "weakening", "tightening"}`: margin_pressure += 0.05;
   - if `demand_direction in {"expanding", "strengthening", "supportive"}`: margin_pressure -= 0.03.
5. **Reads pressure-signal evidence.** Each cited pressure signal id nudges liquidity_pressure += 0.02 (count-based, intentionally simple).
6. **Synthesizes derived scalars.**
   - `funding_need_intensity = mean(liquidity_pressure, debt_service_pressure, market_access_pressure)`
   - `response_readiness = mean(funding_need_intensity, margin_pressure)`
7. **Clamps every scalar to `[0.0, 1.0]`.** All deltas use the `_step` helper which applies the clamp.
8. **Sets confidence = 0.5** by default. Future milestones may refine to e.g. the mean of cited evidence's confidences.

The rule set is small, documented, and reproducible. No rule is a recommendation; each scalar is a synthetic ordering whose value is shaped by the cited evidence.

### 80.4 Anti-fields and anti-claims (binding)

The dataclass deliberately has **no** `revenue`, `sales`, `EBITDA`, `net_income`, `cash_balance`, `debt_amount`, `real_financial_statement`, `forecast_value`, `actual_value`, `accounting_value`, or `investment_recommendation` field. The ledger payload likewise carries none of these keys. Two explicit tests (`test_state_record_has_no_accounting_or_forecast_field`, `test_add_state_payload_carries_no_accounting_or_forecast_keys`) introspect the dataclass field set and the ledger payload key set respectively.

v1.12.0 does **not**:

- update any firm financial statement;
- emit any accounting value, real financial number, or vendor-curated number;
- price, quote, calibrate, or recommend any security, deal, instrument, or market;
- execute any DCM / ECM action, security issuance, loan origination, trade, order match, clearing event, contract mutation, covenant enforcement, or disclosure filing;
- forecast any market level, return, default probability, revenue, EBITDA, or any real-world quantity;
- mutate any other source-of-truth book (the no-mutation test asserts this against ownership, contracts, prices, constraints, signals, valuations, institutions, external_processes, relationships, interactions, routines, attention, variables, exposures, stewardship, engagement, escalations, strategic_responses, industry_conditions, market_conditions, and capital_market_readouts);
- emit the legacy v0/v1 `firm_state_added` registration event from `add_state` — the new event is `firm_latent_state_updated`, distinct by name;
- enforce membership of any free-form tag against any controlled vocabulary;
- emit any ledger record other than `FIRM_LATENT_STATE_UPDATED` from a bare `add_state` call.

### 80.5 Performance boundary (binding)

v1.12.0 adds **one** record per (firm, period). The per-period formula gains `firms`; the per-run formula moves from 244 to **256** for the default fixture (firms=3 × 4 periods = +12); the per-run window moves from `[244, 276]` to **`[256, 288]`**. The firm-state phase is `O(P × F)` (one state per firm per period) — same shape as the v1.10.3 corporate-response phase. v1.12.0 introduces no new dense traversal.

### 80.6 Living-world digest (expected change)

The v1.12.0 living-world digest is **not** equal to the v1.11.2 / v1.11.1 default digest. The canonical view now carries `firm_financial_state_ids` per period and the boundary string was extended. This is **expected** and is part of v1.12.0's freeze surface. Tests assert that two fresh runs of the v1.12.0 default fixture produce *byte-identical* canonical JSON and the same digest. The default-fixture digest at v1.12.0 is `1b9ee84ab8e6e0f3012004a8fe2932c689d5dff5ea0031997a3dd5bca6b913ca`.

### 80.7 What v1.12.0 does not decide

- The shape of the eventual *attention-conditioned* downstream consumers. v1.12.0 makes firm-state ids citable by plain id; it does not refactor v1.9.5 / v1.9.7 / v1.10.3 mechanisms to consume them. A future milestone may add a `evidence_firm_state_ids` slot on `CorporateStrategicResponseCandidate`, on `BankCreditReviewLite`, or on a future funding/issuance intent record, mirroring the v1.10.4.1 / v1.11.0 type-correct cross-reference patterns.
- The exact rule values beyond the v1.12.0 minimum. A future milestone may extend or tune the rule set without breaking the v1.12.0 freeze surface, as long as: the chain link via `previous_state_id` is preserved; constructive regimes still allow decay; constrained / tightening regimes still amplify; the per-period firm-count budget remains `firms`.
- Whether `confidence` should average the cited evidence's confidences (instead of a hardcoded `0.5`). v1.12.0 keeps the simpler hardcode for now; a future milestone may refine.

### 80.8 Position in the v1.12 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69). | Shipped |
| v1.10.0 → v1.10.5 (engagement / strategic-response stack) | Code (§70 → §76). | Shipped |
| v1.11.0 → v1.11.2 (capital-market surface stack) | Code (§77 → §79). | Shipped |
| **v1.12.0 Firm financial latent state** | Code (§80). First endogenous state-update layer. | **Shipped** |
| v1.10.last Public engagement layer freeze | Docs-only. | Planned |
| v1.12.x next steps (anticipated) | Code. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

The test count moves from `2137 / 2137` (v1.11.2) to `2259 / 2259` (v1.12.0) — `+122` tests (`+113` in the new `tests/test_firm_state.py`, `+9` v1.12.0 integration tests in `tests/test_living_reference_world.py`). The CLI surface gains a `firm_states=` column; the per-period record count moves from 61 to 64; the per-run record window widens from `[244, 276]` to `[256, 288]`; the default-fixture `living_world_digest` changes to `1b9ee84ab8e6e0f3012004a8fe2932c689d5dff5ea0031997a3dd5bca6b913ca` (expected — see §80.6).
