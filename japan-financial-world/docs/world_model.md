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
