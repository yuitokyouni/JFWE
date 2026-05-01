# v1.8.8 Reference Variable Layer — Design

> **Status:** design-only milestone. No runtime code in v1.8.8.
> **Layer:** FWE Core (public, jurisdiction-neutral).
> **Depends on:** v1.7 frozen reference financial system, v1.8.1 –
> v1.8.7 routine + interaction + attention substrate.
> **Blocks:** v1.8.9 (`WorldVariableBook`), v1.8.10 (Exposure /
> Dependency layer), v1.8.11 (`ObservationMenu` builder), v1.8.12
> (Investor + Bank Attention Demo). Without v1.8.8 the v1.8.x line
> has nowhere to attach the macro / financial / material / energy /
> technology / expectation context that future routines will read.

## TL;DR — the core principle

> **Reference variables are observable world-context variables.
> They are not scenarios and not shocks by default.**
> Their presence does not drive behavior automatically. Their
> absence does not silence routines.

The v1.8.7 milestone shipped the first concrete endogenous routine
(`corporate_quarterly_reporting`). That routine writes a synthetic
signal that nothing else reads. Before the v1.8.12 investor + bank
attention demo can do something interesting with a corporate
reporting signal, the world has to have *more things* observable
than just one signal — a CPI release that the bank's review
routine takes seriously, a yield curve that the investor's macro
profile cares about, an FX rate, an electricity price, an AI
capability index. v1.8.8 names that universe of observables.

The v1.8.8 design is **not** a scenario engine, **not** a stochastic
process driver, **not** a calibrated macro model. Reference
variables are *names* and *shapes*. They have:

- A canonical identity (`variable_id`), a controlled-vocabulary
  group, a unit, a frequency, an observation kind.
- A history of `VariableObservation`s, each tagged with the
  observation period it describes, the release date on which the
  observation became known, an optional vintage id, and an
  optional pointer to the prior observation it revises.

That shape is enough to support v1.8.11+ routines that *read*
released observations. It is **not** enough to drive an economy. v2
calibration will populate the same shape with Japan public data; v3
proprietary calibration will add paid sources. v1.8.8 stays neutral.

## Why a separate layer

The project already has five places where world state lives. Why
add a sixth? Each existing book answers a different question:

| Book / view                      | Answers                                                   |
| -------------------------------- | --------------------------------------------------------- |
| `PriceBook` (v0.4)               | "What was the last priced observation for this asset?"    |
| `SignalBook` (v0.7)              | "What information events have been published?"           |
| `ValuationBook` (v1.1)           | "What value claim did *this valuer* make about *this subject*?" |
| `ExternalProcessBook` (v1.4)     | "How does this external factor evolve, and what observations did its process produce?" |
| `ConstraintEvaluator` (v0.6)     | "Does this agent currently breach this constraint, given its balance sheet view?" |
| **`ReferenceVariableBook`** (v1.8.9) | **"What is the released value of this named world-context variable, and what is its release / vintage history?"** |

The differences matter:

- **vs. `PriceBook`** — prices are per-asset, per-tick, with no
  release / vintage concept. CPI for 2026Q1 is *not* a price; it is
  a released figure that describes a past period and may be revised.
- **vs. `SignalBook`** — a signal is "something was published." A
  variable observation is "the world's CPI for 2026Q1 was 2.3%."
  The two often co-exist (a CPI release is *both* a signal in
  time and a numeric data point on a variable's history); they
  serve different consumers. Routines that ask "did the BOJ
  publish anything yesterday?" use `SignalBook`. Routines that ask
  "what is the latest released value of CPI YoY?" use
  `ReferenceVariableBook`.
- **vs. `ValuationBook`** — valuations are *opinions* of named
  valuers. Variable observations are *measurements*. A DCF
  valuation of a firm and a CPI release are not the same kind of
  fact; conflating them in one book would force every
  `ValuationRecord` field set onto every CPI release.
- **vs. `ExternalProcessBook`** — external processes describe
  *how a value evolves over time* (constant / random walk / AR(1)
  / regime switch). Variable observations describe *the value
  itself*. The two are complementary: a v3 milestone could attach
  an `ExternalFactorProcess` to a `variable_id` to model its
  evolution, but v1.8.8 does not require that.
- **vs. `ConstraintEvaluator`** — constraint evaluations are
  *derived* per-agent views (DSCR / LTV / leverage). They live on
  top of `BalanceSheetView` + `ContractBook`. Reference variables
  are *world-level* observations independent of any one agent.

The clean way to read this six-row table: each book owns one
distinct *kind* of fact. v1.8.9 introduces a new kind ("released
world-context variables with vintages") that does not fit any
existing book's shape, so it gets its own.

## `ReferenceVariableSpec` — proposed record shape

The static declaration of one reference variable. **Immutable per
v1 conventions; updates produce a new spec record (typically with a
new vintage of metadata, not a new `variable_id`).**

| Field | Type | Notes |
| --- | --- | --- |
| `variable_id` | `str` | stable id, e.g. `"variable:cpi_yoy"`. Unique within a `ReferenceVariableBook`. |
| `variable_name` | `str` | human-readable label, e.g. `"Consumer Price Index, year-over-year"`. |
| `variable_group` | `str` | controlled vocabulary; one of the 13 groups in §"Variable groups" below. |
| `variable_type` | `str` | controlled vocabulary; suggested values: `"level"`, `"rate"`, `"index"`, `"spread"`, `"ratio"`, `"log_change"`, `"qualitative_score"`. v1.8.9 will commit a starter set. |
| `source_space_id` | `str` | which v0/v1 space *publishes* this variable. Suggested values: `"external"` for macro / FX / commodities, `"policy"` for policy-rate-like, `"information"` for surveys / narratives, `"corporate"` for firm-level fundamentals (as v2 expands), etc. Cross-reference is data, not validated. |
| `canonical_unit` | `str` | unit string (e.g. `"percent"`, `"index_points"`, `"USD_per_barrel"`). Free-form; v1.8.9 will not enforce a vocabulary. |
| `frequency` | `str` | release cadence label. Recommended values mirror the v0 `Frequency` enum (`"DAILY"`, `"WEEKLY"`, `"MONTHLY"`, `"QUARTERLY"`, `"YEARLY"`) plus `"CONTINUOUS"` for live-observable variables (FX, oil futures); `"IRREGULAR"` for surveys / qualitative measures. |
| `observation_kind` | `str` | controlled vocabulary; suggested values: `"released"` (periodic, retrospective — GDP, CPI), `"continuous"` (live observable — FX, policy rate), `"estimate"` (model-derived), `"expectations_proxy"` (survey / market-implied), `"qualitative"` (text-based scoring; v3+). |
| `default_visibility` | `str` | mirrors the `SignalBook` vocabulary (`"public"` / `"restricted"` / `"private"`). Default: `"public"`. v1.8.9 stores; consumers enforce. |
| `expected_release_lag_days` | `int \| None` | typical lag between the period a variable describes and its release date. CPI YoY is roughly 30; a yield curve quote has lag 0. `None` for continuous / live variables. Used by v1.8.11 to refuse to surface unreleased observations on the as-of date. |
| `metadata` | `Mapping[str, Any]` | free-form for provenance, parameters, and owner notes. |

`variable_id` should be globally unique across the project; the
`variable:` prefix is the project's convention. v2 calibration may
introduce a parallel `variable:jp_*` namespace, or it may reuse the
neutral ids — v1.8.8 does not commit either way.

## `VariableObservation` — proposed record shape

The actual data point. One observation per (variable, period,
vintage) combination. **Immutable per v1 conventions; revisions
produce new observation records linked back to the prior via
`revision_of`.**

| Field | Type | Notes |
| --- | --- | --- |
| `observation_id` | `str` | stable id; unique within a `ReferenceVariableBook`. Suggested format: `"observation:<variable_id>:<vintage_id or as_of_date>"`. |
| `variable_id` | `str` | reference back to the spec. |
| `as_of_date` | `str` | ISO `YYYY-MM-DD`. The date the observation *became known*. For released variables: the release date. For continuous variables: the date of the quote. |
| `observation_period_start` | `str \| None` | ISO date; the start of the period the observation describes. For released variables: typically the period start (e.g., `"2026-01-01"` for 2026Q1 CPI). For continuous variables: typically equal to `as_of_date`. |
| `observation_period_end` | `str \| None` | ISO date; the end of the period. Together with `observation_period_start` defines the *period the observation describes*, distinct from when it was released. |
| `release_date` | `str \| None` | ISO date; the official release date if different from `as_of_date`. Most v1.8.x usage will set `as_of_date == release_date`; the field exists so v3 can model embargoed releases or pre-release leaks. |
| `vintage_id` | `str \| None` | a stable label naming this vintage (e.g., `"2026Q1_initial"`, `"2026Q1_first_revision"`, `"2026-03-31_close"`). Multiple vintages of the same `(variable, period)` may exist. |
| `revision_of` | `str \| None` | when this observation revises a prior one, the prior `observation_id`. Forms a linked-list of revisions. The original release has `revision_of=None`. |
| `value` | `Any` | numeric for most variables; structured (e.g., yield-curve term-structure) where appropriate; categorical for qualitative scores. v1.8.9 will commit a specific schema; v1.8.8 design defers. |
| `unit` | `str` | unit at observation time. Often equals `spec.canonical_unit`; differs when a release is in nominal terms while the canonical is real, or vice versa. |
| `source_id` | `str` | who published this observation. For v1.8.x: synthetic source ids only (`"source:reference_macro_publisher"` etc.). For v2+: real source identifiers. |
| `confidence` | `float` | `0.0` to `1.0`. For released official figures: typically `1.0`. For survey expectations / qualitative scores: lower. v1.8.9 stores; consumers may weight. |
| `metadata` | `Mapping[str, Any]` | free-form. Suggested keys: `"data_quality"`, `"source_url"` (v2 only and only when license permits), `"survey_response_count"`. |

## Why period / release_date / vintage / revision_of all matter

The four time-ish fields exist for one reason: **to prevent
look-ahead bias** in routines that read variable observations.

- `observation_period_start` / `observation_period_end` describe
  *what the observation says*. CPI for 2026Q1 says something about
  Jan–Mar 2026.
- `as_of_date` / `release_date` describe *when the observation
  became visible to agents*. CPI for 2026Q1 was released on (e.g.)
  2026-04-15 with `expected_release_lag_days≈30`.
- `vintage_id` distinguishes multiple observations of the same
  `(variable, period)`. The 2026Q1 CPI may have an `initial`
  vintage (2026-04-15), a `first_revision` (2026-05-20), a
  `second_revision` (2026-06-10).
- `revision_of` links each vintage to the prior one so the
  revision history is reconstructable from the ledger alone.

A v1.8.11 `ObservationMenu` builder (or any future routine engine
that consumes variable observations) **must filter out
observations whose `as_of_date` is in the future of the menu's
`as_of_date`**. Otherwise a routine looking at "what did the bank
know on 2026-03-31?" would see the 2026Q1 CPI release that lands
on 2026-04-15, which is the canonical look-ahead-bias mistake.

The v1.8.8 design names these fields up front so the v1.8.9
implementation enforces the filter from the start, not after a
v2 calibration milestone discovers the bug.

`expected_release_lag_days` on the spec is the *expectation*; the
actual release is recorded on the observation. They can disagree
(a delayed release, an early leak); the engine layer trusts the
observation, not the spec.

## Variable groups (controlled vocabulary)

Thirteen groups, ordered roughly from most to least
mainstream-macro:

| Group | Purpose | Examples (see §"Examples" for ids) |
| --- | --- | --- |
| `real_activity` | output, employment, capacity utilization | GDP growth, industrial production index, employment ratio |
| `inflation` | price-level measures | CPI YoY, core CPI, PPI |
| `rates` | policy rate, term structure, money-market rates | policy rate, yield curve 10y-2y |
| `fx` | currency pairs | USD/JPY, EUR/JPY, real effective exchange rate |
| `credit` | corporate / sovereign spreads, default-implied measures | reference credit spread, distressed share |
| `financial_market` | equity indices, volatility measures, market liquidity | reference equity index, volatility index, market liquidity |
| `material` | metals, petrochemicals, agricultural / soft commodities | reference oil, metal price reference, petrochemical input cost |
| `energy_power` | electricity, natural gas, grid reserve, fuel-stock measures | electricity price index, grid reserve margin, natural gas reference |
| `logistics` | shipping rates, port throughput, container availability | logistics cost index, dry bulk index |
| `real_estate` | rents, land prices, transaction volumes, vacancy | rent index, land price index |
| `labor` | shortage indices, wage-pressure measures, automation displacement | labor shortage index, automation adoption index |
| `technology` | capability scores, semiconductor supply, capex intensity | AI capability index, semiconductor supply index |
| `expectations_narratives` | survey expectations, narrative-implied indices, prediction markets | inflation expectations, narrative theme index |

The vocabulary is **append-only** at the group level: v1.8.9
implements the 13 groups; v2 / v3 may extend with milestone
documentation but should not silently rename or remove. A
`variable_group` value not in the vocabulary is a v1.8.9 schema
violation.

## Examples — `variable_id` set

The illustrative ids the v1.8.8 design names. v1.8.9 will register
a starter subset; v1.8.11+ will add more on demand. None of the
ids carry Japan-specific calibration; v2 may attach jurisdiction
metadata.

```
real_activity:
  variable:gdp_growth
  variable:industrial_production_index
  variable:employment_ratio_reference

inflation:
  variable:cpi_yoy
  variable:core_cpi_yoy
  variable:ppi_yoy

rates:
  variable:policy_rate
  variable:yield_curve_10y_2y

fx:
  variable:usd_jpy
  variable:eur_jpy_reference

credit:
  variable:credit_spread_reference

financial_market:
  variable:reference_equity_index
  variable:reference_volatility_index

material:
  variable:oil_price_reference
  variable:petrochemical_input_cost
  variable:metal_price_reference

energy_power:
  variable:electricity_price_index
  variable:grid_reserve_margin

logistics:
  variable:logistics_cost_index

real_estate:
  variable:rent_index_reference
  variable:land_price_index_reference

labor:
  variable:labor_shortage_index
  variable:automation_adoption_index

technology:
  variable:ai_capability_index
  variable:semiconductor_supply_index

expectations_narratives:
  variable:inflation_expectations
```

The list is illustrative. The actual v1.8.9 starter set will be
small (~10 variables across the most-used groups) so the milestone
remains reviewable. v1.8.11+ will register additional variables on
demand as concrete routines (investor / bank review, valuation
refresh) need to read them.

## Material / energy / technology — transmission attachment points

Three of the groups are economically impactful in ways that need
explicit naming, *even though v1.8.8 does not model the
transmission*. The transmission lives in future routines that
**read** these variables, not in the variable layer itself. v1.8.8
just declares where the wiring will eventually attach.

### Material variables

`variable:oil_price_reference`, `variable:metal_price_reference`,
`variable:petrochemical_input_cost`. Future routines may attach
material observations to:

- **Input cost models** in corporate routines (capex / opex
  forecasting that v2 calibration may parameterize from public
  data).
- **Sector-level constraints**: a high oil price might constrain a
  refining-heavy firm's margin index; the constraint is computed
  by a *future routine*, not by the variable book.
- **Inventory and substitution decisions** in corporate routines
  that v3+ may add. Out of scope for v1.8.x.

v1.8.8 does **not** specify how a routine consumes
`variable:oil_price_reference`. It just declares the variable so a
future routine has somewhere to point.

### Energy / power variables

`variable:electricity_price_index`,
`variable:grid_reserve_margin`. Future routines may attach to:

- **Production cost** for electricity-intensive sectors (steel,
  aluminum, semiconductor fabrication, data centers).
- **Logistics cost** chaining (electricity → cold chain →
  perishables).
- **Household consumption capacity** (high electricity bills →
  reduced discretionary spend; v3+ behavioral milestone).

v1.8.8 declares the variables; transmission is later.

### Technology variables

`variable:ai_capability_index`,
`variable:automation_adoption_index`,
`variable:semiconductor_supply_index`. Future routines may attach
to:

- **Productivity expectations** in valuation refresh routines.
- **Labor displacement risk** scoring in workforce-relevant
  corporate routines.
- **Capex pull-forward** in technology-leveraged sectors.
- **Sector rotation narratives** that the
  `expectations_narratives` group amplifies.

v1.8.8 declares the variables. The v3 (or paid) calibration that
turns "AI capability index = 0.65" into a real productivity
adjustment is many milestones away.

The point of naming these attachment points now is to keep the
v1.8.x line honest about what *will* matter once concrete routines
extend beyond corporate quarterly reporting. Without these
variables in the layer, every future routine that wants to read
"the world's oil price right now" would have to invent its own ad-
hoc state, and the project would re-litigate this design under a
worse name.

## Relation to `AttentionProfile`

v1.8.5's `AttentionProfile` already has `watched_metrics` —
"earnings", "valuation_gap", "dscr". Future v1.8.10+ work may
extend the profile with two new fields:

- `watched_variable_ids: tuple[str, ...]` — explicit variable ids
  the actor cares about (e.g., `("variable:cpi_yoy",
  "variable:policy_rate")`).
- `watched_variable_groups: tuple[str, ...]` — group-level filter
  (e.g., `("rates", "inflation")` for a macro fund).

Until those fields land, **the existing `watched_metrics` field
bridges**: a profile may list `"cpi"` or `"policy_rate"` as a
metric, and a future v1.8.11 menu builder may map metric strings
to variable ids via metadata. v1.8.8 does not mandate this
mapping; it just notes the bridge exists so v1.8.5 callers can
start declaring what they would care about without waiting for
v1.8.10.

## Relation to `InteractionTopology`

The v1.8.3 / v1.8.2 interaction tensor `S × S × C` is about
*channels*, not scenarios. v1.8.8 does not change that.

Interaction channels **may carry** variable observations as their
content. An `InteractionSpec` from `external` to `information`
might publish observations of `variable:oil_price_reference` —
that is the channel through which the world's oil price becomes
visible. The channel exists in the topology; the observation
exists in `ReferenceVariableBook`; the link is data, not enforced.

What the topology must **not** become: a *shock tensor*. There is
no v1.8.x mechanism that says "when this variable moves by X,
publish an event through this channel." That would re-introduce
scenario-driven dynamics. v1.8.8's ground rule:

> The interaction tensor stays about *which channels are possible*.
> The reference variable layer stays about *what world-context
> values currently are*. Routines (v1.8.7+) decide what to do with
> a variable observation, including whether to publish a derivative
> signal through a channel.

If a future v3 calibration wants automatic signal-on-shock
behavior, that goes inside a routine, not as a hidden side effect
of the variable layer.

## Relation to `Routine`

The v1.8.7 corporate quarterly reporting routine does not yet
consume any reference variable. v1.8.11+ routines will. The rules:

- **Consumption is read-only.** A routine reads variable
  observations through `ReferenceVariableBook` (or the v1.8.11
  `ObservationMenu` builder). The routine may include the
  observation ids in its `RoutineRunRecord.input_refs`. The
  routine does **not** mutate the variable book.
- **Absence is partial / degraded, not silent.** If the routine
  expects (e.g.) a CPI release for the prior quarter and none
  exists yet (release lag, data gap), the routine still runs —
  with `status="degraded"` per the v1.8.1 anti-scenario discipline
  cascaded through the v1.8.6 engine. The routine's output may
  carry a `metadata.degraded_inputs = ("variable:cpi_yoy",)` note.
- **No look-ahead.** The v1.8.11 menu builder is responsible for
  filtering observations whose `as_of_date` is later than the
  menu's `as_of_date`. Routines that bypass the menu builder and
  query `ReferenceVariableBook` directly are responsible for
  applying the same filter; v1.8.9 may expose a helper
  (`book.list_released_as_of(variable_id, as_of_date)`) to make
  the correct path easy.

## Boundaries — what v1.8.8 (and v1.8.9 / 10 / 11) does NOT do

The reference variable layer is *infrastructure for context*. It
is not:

- **A GDP / CPI / rate calculator.** No routine inside v1.8.x
  computes a real GDP growth rate from underlying components. v2
  ingests official releases as `VariableObservation`s; v3 may add
  proprietary now-cast estimates.
- **A forecaster.** No routine inside v1.8.x produces a forward
  point estimate for any variable. Future expectations may be
  recorded as observations on `variable:inflation_expectations`
  (with `observation_kind="expectations_proxy"`) — but the
  expectation is published from a survey or market, not computed
  by FWE.
- **A rate-setting engine.** Even when `variable:policy_rate`
  exists, no v1.8.x routine sets it. Policy reaction functions
  remain a v3+ commercial concern.
- **A commodity market simulator.** `variable:oil_price_reference`
  is a *value*, not a market. Order matching, inventory dynamics,
  and storage arbitrage are out of v1.8.x scope.
- **A power grid simulator.** `variable:grid_reserve_margin` is
  reported, not computed. Grid dynamics are out of v1.8.x scope.
- **A technology diffusion model.** `variable:ai_capability_index`
  is reported. The diffusion process is whatever v3 chooses to
  parameterize — out of v1.8.x scope.
- **A policy reaction engine.** Out of v1.8.x scope.
- **A price formation / trading / lending mechanism.** Out of
  v1.8.x scope.
- **Japan calibration.** v1.8.8 stays jurisdiction-neutral. v2
  (Japan public) and v3 (Japan proprietary) populate the same
  shapes with real data.
- **Real-data ingestion.** v1.8.x ships no ingestion adapters; v2
  builds ingestion separately, source by source.
- **Automatic economic behavior of any kind.** v1.8.x stays
  endogenous-but-bounded.

## Hardening — anchoring variables to spaces, channels, and exposures

> **Why this section exists:** the v1.8.8 design as originally
> written was at risk of producing *disembodied global state*. A
> `ReferenceVariableBook` that lives in the kernel and is read by
> any routine, with no anchoring to spaces, no anchoring to
> interaction channels, and no anchoring to who actually depends on
> the variable, would re-introduce the scenario-driven failure mode
> through a side door — every routine would consult a global
> "macro environment" object and pretend that was endogenous. The
> hardening update below adds the explicit hooks that prevent that.

### What a `ReferenceVariable` is — and is not

A `ReferenceVariable` is **not**:

- **Not an `Agent`.** It does not act, decide, hold contracts, or
  appear as an `actor_id` anywhere. Agents (firms, banks,
  investors, institutions) are the ones who *observe* variables.
- **Not a `Space`.** It does not belong to any of the eight v0
  spaces (Corporate / Banking / Investors / Exchange / Real
  Estate / Information / Policy / External). It is *published by*
  one or more spaces and *observed by* zero or more spaces, but
  it is not itself a space-resident object.
- **Not a `Scenario`.** A scenario is a forward-going alternative
  history that v1.8.x does not implement. A reference variable is
  a name for an observable; specific observations are recorded as
  data, not generated as scenario branches.
- **Not a `Shock`.** A shock is an exogenous event that drives
  behavior. A reference variable's values may change over time,
  but those values do not auto-trigger any routine.
- **Not a `PriceBook` replacement.** Prices remain in `PriceBook`,
  per-asset, per-tick, with no release / vintage concept. A
  reference variable describes *world state* and may be revised;
  a price describes *market state* at a moment.

A `ReferenceVariable` **is**:

- A **world-context / field / substrate variable** that exists in
  the world independently of any one agent, may be observed by
  agents through routines and interaction channels, and carries an
  audit-grade history of release dates, vintages, and revisions.

The distinction matters operationally. An agent has a
`balance_sheet_view`; a variable does not. An agent has an
`AttentionProfile`; a variable does not. A variable has *consumers*
(agents that observe it) and *exposures* (agents that depend on
it); v1.8.10 will introduce explicit `ExposureRecord` to name the
"depends on" relationship as data.

### The three required hooks

Every `ReferenceVariableSpec` must declare, by construction, three
hooks that anchor it to the rest of the world:

1. **Source hook — *which space / source publishes or observes
   this variable.*** Carried by `source_space_id` (required) and
   `source_id` (optional). Without a source hook a variable is a
   ghost: someone has to be the publisher / observer of record.
2. **Scope hook — *which spaces / sectors / subjects / asset
   classes the variable is relevant to.*** Carried by
   `related_space_ids`, `related_subject_ids`,
   `related_sector_ids`, `related_asset_class_ids`,
   `observability_scope`, `typical_consumer_space_ids`. Without a
   scope hook a variable is universally global; with the hook,
   the v1.8.11 menu builder knows whose menus the variable should
   even be a candidate for.
3. **Exposure hook — *which agents / assets / contracts / sectors
   are economically dependent on this variable.*** Lives in v1.8.10
   `ExposureRecord` rather than on the spec itself, but the spec
   names which scope the exposure layer is expected to resolve
   against. Without an exposure hook, the variable becomes a free-
   floating global driver — exactly the failure the hardening
   prevents.

The three hooks satisfy a simple invariant: **for every variable,
something publishes it, something is in scope to read it, and
something concrete depends on it.** A variable that fails any hook
should not be registered.

### Updated `ReferenceVariableSpec` field set (additions)

The original §"`ReferenceVariableSpec` — proposed record shape"
table lists `variable_id`, `variable_name`, `variable_group`,
`variable_type`, `source_space_id`, `canonical_unit`, `frequency`,
`observation_kind`, `default_visibility`,
`expected_release_lag_days`, `metadata`. The hardening update
**adds** the following fields (or expands `metadata` semantics for
implementations that prefer a flatter starter schema):

| Field | Type | Hook | Notes |
| --- | --- | --- | --- |
| `source_id` | `str \| None` | source | optional named source within `source_space_id` (e.g., a specific `InformationSourceState` id). Null = "the space publishes the variable but no specific source is named." |
| `related_space_ids` | `tuple[str, ...]` | scope | spaces other than `source_space_id` for which this variable is *relevant* (e.g., `variable:oil_price_reference` is published by `external` but relevant to `corporate`, `banking`, `real_estate`, `information`). |
| `related_subject_ids` | `tuple[str, ...]` | scope | specific subjects (firm ids, asset ids, market ids) for which this variable is most directly relevant. May be empty for broadly-relevant variables (e.g., `variable:cpi_yoy`). |
| `related_sector_ids` | `tuple[str, ...]` | scope | sector labels (free-form strings; suggested vocabulary in `metadata`). Used by v1.8.10 to bulk-resolve exposures by sector. |
| `related_asset_class_ids` | `tuple[str, ...]` | scope | asset-class labels (e.g., `("equity", "real_estate")`). Used by `PortfolioExposure` consumers to filter relevant variables. |
| `observability_scope` | `str` | scope | controlled vocabulary; suggested values: `"global"` (any space may observe), `"jurisdictional"` (v2+ only), `"private"` (only the source space). v1.8.9 stores; v1.8.11 enforces in the menu builder. |
| `typical_consumer_space_ids` | `tuple[str, ...]` | scope | spaces typically expected to consume the variable, e.g., `("investors", "banking")` for `variable:credit_spread_reference`. Used by v1.8.11 menu builder for default profile suggestions. |

The fields above are stored as data and **not** validated for
resolution against the registry, per the v0/v1 cross-reference
rule. v1.8.10 (`ExposureRecord`) and v1.8.11 (`ObservationMenu`
builder) will read them; v1.8.9 just persists them.

### Updated `VariableObservation` field set (additions)

The original `VariableObservation` table lists `observation_id`,
`variable_id`, `as_of_date`, `observation_period_start?`,
`observation_period_end?`, `release_date?`, `vintage_id?`,
`revision_of?`, `value`, `unit`, `source_id`, `confidence`,
`metadata`. The hardening update adds three more anchoring fields
and clarifies one existing one:

| Field | Type | Hook | Notes |
| --- | --- | --- | --- |
| `observed_by_space_id` | `str \| None` | source | the space that *recorded* the observation (often equal to `spec.source_space_id`, but may differ — e.g., a `policy` variable observed by `information` after a press release). |
| `published_by_source_id` | `str \| None` | source | named publisher within the recording space (preferred name; replaces or aliases the existing `source_id` field for clarity in v1.8.9 implementation). |
| `carried_by_interaction_id` | `str \| None` | topology | optional `InteractionSpec.interaction_id` naming the channel through which this observation reached its consumers. Null when the observation was simply stored without a channel record. |
| `as_of_date` | `str` (already in spec) | — | clarified: the date the observation **became visible to agents**. The v1.8.11 menu builder filters using this field. `release_date` is an alias used when the publication moment differs from the observation moment (e.g., embargo / leak); when both exist, `as_of_date` wins for visibility. |

`as_of_date` is the **canonical visibility timestamp**. v1.8.11
must use it (not `observation_period_start`, not `release_date`)
when filtering observations against a menu's `as_of_date`. The
look-ahead-bias rule from §"Why period / release_date / vintage /
revision_of all matter" is unchanged.

### How variables enter the `S × S × C` interaction topology

The v1.8.3 / v1.8.2 `S × S × C` tensor describes channels between
spaces. Reference variable observations may be **carried** through
channels — that is what `VariableObservation.carried_by_interaction_id`
records. The topology stays about *which channels are possible*;
the variable layer stays about *what world-context values
currently are*; the link is data, not enforced.

Five concrete channel examples that v1.8.10+ may register:

| `interaction_id` | source → target | `interaction_type` | typical variables carried |
| --- | --- | --- | --- |
| `interaction:external.commodity_feed_to_information` | `external → information` | `commodity_feed` | `variable:oil_price_reference`, `variable:metal_price_reference`, `variable:petrochemical_input_cost` |
| `interaction:information.macro_data_release_to_investors` | `information → investors` | `macro_data_release` | `variable:gdp_growth`, `variable:cpi_yoy`, `variable:industrial_production_index` |
| `interaction:information.credit_monitoring_data_to_banking` | `information → banking` | `credit_monitoring_data` | `variable:credit_spread_reference`, `variable:yield_curve_10y_2y` |
| `interaction:policy.policy_rate_announcement_to_investors` | `policy → investors` | `policy_rate_announcement` | `variable:policy_rate` |
| `interaction:real_estate.collateral_market_update_to_banking` | `real_estate → banking` | `collateral_market_update` | `variable:rent_index_reference`, `variable:land_price_index_reference` |

These are **illustrative**. v1.8.10+ milestones may register any
subset; v2 / v3 calibration may add jurisdiction-specific channels
on top. The crucial property is that *every* variable observation
that crosses a space boundary should ideally be associated with an
`InteractionSpec` (and recorded via `carried_by_interaction_id`)
so the cross-space flow is auditable. v1.8.9 does not enforce this;
v1.8.11 may enforce it for menu eligibility.

### Responsibility chain — relation to the future Exposure / Dependency layer

The hardening update's central conceptual move: split
responsibilities cleanly across five record types so no record
becomes a "global driver."

```
ReferenceVariableSpec    — what variable EXISTS
                           (identity, group, source, scope)

VariableObservation      — what value was OBSERVED and WHEN
                           (period, release date, vintage, revision)

ExposureRecord           — who DEPENDS on it and IN WHAT DIRECTION
                           (v1.8.10; not yet implemented)

AttentionProfile         — who WATCHES it
                           (v1.8.5; already implemented)

Routine                  — when it is REVIEWED
                           (v1.8.4 / v1.8.6 / v1.8.7; already
                            implemented)
```

Reading the chain top-to-bottom: a variable can exist (Spec) and
be observed at concrete moments (Observation) without anyone yet
depending on it; an exposure can be declared (Exposure) without
the exposed actor watching the variable today; an actor can watch
the variable (Attention) without yet running a routine that reads
it; a routine can run (Routine) and choose, on its own schedule,
whether the latest observation matters.

**Each step is opt-in.** A variable does not auto-affect any
exposed actor; an exposed actor does not auto-watch the variable;
a watching actor does not auto-fire a routine when the variable
moves. The chain reads top-down (Variable → Observation →
Exposure → Attention → Routine) for *causality* but each step
requires explicit data, not implicit propagation.

This is the structural answer to "how do you keep variables from
becoming disembodied global drivers": you require the data at
every link.

### Transmission chain examples

The four examples below show how *future* routines will use
variables. v1.8.x does not model any of these transmissions;
they are documented to make the attachment points concrete.

#### a. Oil → petrochemical → packaging → logistics → food processor margin

```
variable:oil_price_reference                    (external publishes)
   │
   │ released through interaction:external.commodity_feed_to_information
   ▼
variable:petrochemical_input_cost               (information publishes,
                                                  derived in a future
                                                  v3 routine)
   │
   ▼ (future routine: packaging cost recomputation)
variable:packaging_cost_index                   (real_economy)
   │
   ▼ (future routine: logistics cost recomputation)
variable:logistics_cost_index                   (real_economy)
   │
   ▼ (future routine: food_processor margin pressure
                       — corporate review routine reads
                       packaging + logistics + own pricing
                       power and emits a margin-pressure
                       signal)
food_processor's corporate review routine
```

Each arrow is a **future routine** that v1.8.x has not implemented.
The variables exist in v1.8.9; the chain is filled in milestone by
milestone. Crucially, no variable in the chain *automatically*
moves any other variable. A routine has to be configured to read
the upstream observation and produce the downstream variable.

#### b. Electricity / power

```
variable:electricity_price_index, variable:grid_reserve_margin
   │
   ▼ (future routine: production-cost recomputation
                       for electricity-intensive sectors)
production cost adjustments → corporate routine outputs

   │
   ▼ (future routine: outage-risk scoring against
                       grid_reserve_margin thresholds)
outage-risk signals → bank review consumes
```

#### c. AI / technology

```
variable:ai_capability_index, variable:automation_adoption_index
   │
   ▼ (future routine: labor-displacement-risk scoring)
labor displacement risk signals
   │
   ▼ (future routine: productivity-frontier reweighting)
productivity-frontier observation
   │
   ▼ (future routine: narrative aggregation in
                       expectations_narratives group)
narrative theme index updates
```

#### d. Interest rates

```
variable:policy_rate, variable:yield_curve_10y_2y
   │
   ▼ (future routine: debt-service-burden recomputation
                       for indebted firms)
DSCR view updates                                  (constraint side)

   │
   ▼ (future routine: discount-rate update in
                       valuation_refresh routine)
valuation refresh → ValuationGap

   │
   ▼ (future routine: bank funding-cost recomputation)
bank-side funding cost adjustment → bank review
```

Note: each chain ends in a v1.8.x routine artifact (a signal, a
view, a `RoutineRunRecord`), not in a balance sheet write or a
price move. The transmission structure is preserved; the
behavioral outputs are deferred.

### Hard boundary — variable movement does NOT auto-trigger routines

The hard boundary is the test for whether the v1.8.8 design has
slipped:

> **A variable observation only matters when *all four* gates are
> satisfied:**
>
> 1. The observation is **visible** by date / release / vintage
>    (`as_of_date <= menu.as_of_date`, vintage selection rule
>    applied).
> 2. The observation is **available** through a channel or menu
>    (`carried_by_interaction_id` resolves to a channel that the
>    consumer's `AttentionProfile.watched_channels` includes,
>    *or* the consumer reads `ReferenceVariableBook` directly
>    through a menu builder that respects scope).
> 3. An **`AttentionProfile`** *selects* it
>    (`watched_variable_ids` / `watched_variable_groups` /
>    bridged-via-`watched_metrics`).
> 4. A **`Routine`** consumes it (the v1.8.6 engine writes a
>    `RoutineRunRecord` whose `input_refs` include the
>    observation id).

A variable that moves but fails any of the four gates produces no
behavior. A routine that fires solely because a variable crossed a
threshold has bypassed gate (4) — that is scenario-driven and
should be rejected at review.

The four gates correspond to the responsibility chain:

```
visibility gate     ← VariableObservation.as_of_date / release_date / vintage
availability gate   ← InteractionSpec / carried_by_interaction_id (or ObservationMenu)
selection gate      ← AttentionProfile + SelectedObservationSet
consumption gate    ← Routine + RoutineRunRecord.input_refs
```

Each gate has its own data record. Removing data for any gate
breaks the chain — which is exactly why none of them is
auto-derivable.

### Anti-scenario discipline preserved

The hardening preserves and strengthens the v1.8.1 anti-scenario
discipline:

- **Absence is partial / degraded, not silent.** A variable with
  zero observations does not break a routine; the routine runs
  with an `input_refs` subset and `status="degraded"`. (v1.8.1
  §43.1; v1.8.6 §48.2.)
- **Presence does not auto-produce behavior.** A variable
  observation alone, without exposure declaration + attention
  selection + routine consumption, has zero behavioral effect.
  This is the four-gate rule above.

These two rules together pin the layer in place: it is rich enough
to host real macro / financial / material / energy / technology /
real-estate / labor / logistics / expectations data (v2 / v3 will
populate it), and disciplined enough that none of that data
silently steers the simulation.

## Anti-scenario discipline — restated

The v1.8.1 anti-scenario principle cascades through v1.8.8:

> The reference variable layer makes more observables available to
> routines. It does **not** make routines fire when a variable
> moves. Routines run on their own schedules, read whatever
> observations are available at their `as_of_date`, and produce
> output. A routine that becomes silent because no variable
> observation is "interesting enough" has slipped back into
> scenario-driven mode.

The status vocabulary cascade is unchanged from §43.1:

```
ReferenceVariableBook may have zero observations of a variable.
ObservationMenu may carry zero variable ids on the watched list.
SelectedObservationSet may have status="empty" or "degraded".
RoutineRunRecord may have status="degraded" but still produces
  endogenous output.
```

If a future v1.8.x review surfaces a routine whose only behavior
is "react when variable X moves by N percent," reject the design.
Reactions belong in v3 calibration with full provenance, not in
the v1.8.x reference layer.

## Proposed milestone sequence (revises v1.8.7's table)

The v1.8.7 milestone closed with a sequence ending at v1.8.8
(Investor + Bank Attention Demo). v1.8.8's design correction
inserts four new sub-milestones because v1.8.12's investor + bank
demo needs *something to watch* — and that something is the
reference variable layer plus its supporting infrastructure.

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.1 Endogenous Reference Dynamics | Design (§43). | Shipped |
| v1.8.2 Interaction Topology + Attention | Design (§44). | Shipped |
| v1.8.3 InteractionBook + Tensor View | Code (§45). | Shipped |
| v1.8.4 RoutineBook + RoutineRunRecord | Code (§46). | Shipped |
| v1.8.5 AttentionProfile + ObservationMenu + SelectedObservationSet | Code (§47). | Shipped |
| v1.8.6 Routine Engine plumbing | Code (§48). | Shipped |
| v1.8.7 Corporate Quarterly Reporting Routine | Code (§49). | Shipped |
| **v1.8.8 Reference Variable Layer — Design** | This document. | **(this milestone)** |
| **v1.8.9 `WorldVariableBook`** | Code: kernel-level book for `ReferenceVariableSpec` + `VariableObservation`, with append-only revision history, look-ahead-bias-free `list_observations_visible_as_of(...)` and `latest_observation(..., as_of_date=...)` helpers, channel-aware filter, and the two `VARIABLE_ADDED` / `VARIABLE_OBSERVATION_ADDED` ledger types. **Shipped** as `world/variables.py` (91 tests; 1025 → 1116 total). Naming: `WorldVariableBook` (not `IndicatorBook`) to avoid narrowing to macro indicators only — energy / technology / qualitative variables are first-class members of the layer. | Yes (kernel) |
| **v1.8.10 Exposure / Dependency Layer** | Code: kernel-level `ExposureBook` storing `ExposureRecord` entries (`subject_id × variable_id × direction × magnitude × metric × validity window`) with `EXPOSURE_ADDED` ledger emission and an `is_active_as_of(...)` validity-window filter. Distinct from `AttentionProfile.watched_*` (what the actor *watches*); exposure is *what affects* the actor. `magnitude` is a **synthetic dependency strength** in `[0.0, 1.0]`, NOT a calibrated sensitivity. `direction` is a free-form **label**, NOT arithmetic. v1.8.10 stores exposures only; transmission (how a variable affects an exposed actor) is later. **Shipped** as `world/exposures.py` (59 tests; 1116 → 1175 total). | Yes (kernel) |
| **v1.8.11 `ObservationMenu` builder** | Code: kernel-level `ObservationMenuBuilder` that joins `AttentionBook` + `SignalBook` + `WorldVariableBook` + `ExposureBook`, surfaces visible signals + visible variable observations gated by the actor's active exposures + active exposures themselves, and writes one `ObservationMenu` per `build_menu` call through the existing `OBSERVATION_MENU_CREATED` ledger path. Read-only `preview_menu` does not write. `ObservationMenu` extended additively with `available_variable_observation_ids` and `available_exposure_ids`. v1.8.5 storage shape unchanged; existing tests untouched. **Shipped** as `world/observation_menu_builder.py` (50 tests; 1175 → 1225 total). | Yes (kernel) |
| **v1.8.12 Attention Variable Hooks + Investor / Bank Attention Demo** | Code: `AttentionProfile` extended additively with explicit hooks into the v1.8.9 / v1.8.10 layers (`watched_variable_ids`, `watched_variable_groups`, `watched_exposure_types`, `watched_exposure_metrics`); demo helper `run_investor_bank_attention_demo` registers synthetic investor + bank attention profiles, builds menus through the v1.8.11 `ObservationMenuBuilder`, and writes one `SelectedObservationSet` per actor through `AttentionBook.add_selection` using a structural rule that filters menu refs against the profile's watch fields. The demo is selection-only: no investor / bank review routine, no valuation / price / lending mutation. **Shipped** as `world/reference_attention.py` (32 tests = 9 schema + 23 demo; 1225 → 1257 total). | Yes (kernel) |
| v1.9 Living Reference World Demo | Code + tests: a year-long run on the routine + topology + attention + variable stack with **no** external observation, with non-empty ledger entries on every reporting / review cycle. | After v1.8.12 |

Inserting v1.8.8–v1.8.11 between v1.8.7 and the demo is the
clean way to make "the investor watches CPI; the bank watches
DSCR; the firm publishes earnings" a structurally honest
demonstration. Without the variable layer, the demo would either
have to invent ad-hoc state per actor or fall back to scenario-
driven hand-wired data, both of which the v1.8.1 direction
forbids.

## Open questions / non-decisions

v1.8.8 deliberately does not commit:

- **`VariableObservation.value` schema.** v1.8.8 design names
  `value: Any`; v1.8.9 implementation will commit to either a
  numeric-only `float | None` (with categorical / structured
  values stored under `metadata`) or a tagged union
  (`{"numeric": ..., "qualitative": ..., "structured": ...}`).
  Reviewer note: prefer the numeric-only path for the starter
  variables; revisit when qualitative variables become real
  consumers in v1.8.12+.
- **`variable_id` namespace.** The `variable:` prefix is the
  project convention. Whether v2 introduces `variable:jp_*`
  namespacing or reuses the neutral ids is a v2 decision.
- **Where the book lives in `world/`.** Likely
  `world/reference_variables.py` modeled on
  `world/external_processes.py`. v1.8.9 will commit.
- **Whether `ObservationMenu` carries variable ids as a separate
  list.** v1.8.5's `ObservationMenu` already has
  `available_external_observation_ids`; v1.8.11 will decide
  whether to add a parallel `available_variable_observation_ids`
  or to alias variable observations into the existing field.
- **Concurrent vintage handling.** What if two vintages of the
  same `(variable, period)` arrive on the same day? v1.8.9 will
  either commit "vintage_id is the tiebreaker for stable sorting"
  or "the latest add wins for `list_released_as_of`." Either is
  defensible; reviewer should pick one.
- **Cross-jurisdiction overlay.** A v2 Japan-only variable and a
  v3 proprietary global variable may both exist in the same book.
  v1.8.8 design does not commit a separation policy; v3 readiness
  notes (`docs/v2_readiness_notes.md` and a future
  `docs/v3_readiness_notes.md`) will address this.

## Files in this milestone

- `docs/v1_reference_variable_layer_design.md` — this document.
- `docs/v1_endogenous_reference_dynamics_design.md` — milestone
  table updated to insert v1.8.8 / v1.8.9 / v1.8.10 / v1.8.11 /
  v1.8.12 between v1.8.7 and v1.9.
- `docs/v1_interaction_topology_design.md` — milestone table
  updated similarly; clarifies that the interaction tensor stays
  about channels, not scenarios.
- `docs/world_model.md` — gains §50 documenting the principle and
  the proposed record shapes in the constitutional design log.

No `world/`, `spaces/`, `examples/`, or `tests/` file is changed.
The 1025-test baseline is unchanged at v1.8.8; v1.8.9+ milestones
will grow the suite.

## v1.8.8 success criteria

§50 (the constitutional log entry) is complete when **all** hold:

1. This document exists and contains the principle, the
   distinction from existing books, the proposed
   `ReferenceVariableSpec` and `VariableObservation` field sets,
   the look-ahead / vintage / revision rationale, the 13 variable
   groups, the example variable ids, the material / energy /
   technology attachment points, the relation-to-attention,
   relation-to-topology, and relation-to-routine sections, the
   boundaries, and the revised milestone sequence.
2. `docs/v1_endogenous_reference_dynamics_design.md` and
   `docs/v1_interaction_topology_design.md` carry sequence-revision
   notes pointing at v1.8.9 / v1.8.10 / v1.8.11 / v1.8.12 as the
   build path to the v1.8.12 demo and v1.9 closing milestone.
3. `docs/world_model.md` §50 records the design in the
   constitutional log.
4. No `world/`, `spaces/`, `examples/`, or `tests/` file is
   modified. The 1025-test baseline is unchanged.
5. v1.8.9 reviewers can land `WorldVariableBook` against the
   proposed `ReferenceVariableSpec` and `VariableObservation`
   shapes without re-litigating either the look-ahead-bias rule or
   the anti-scenario discipline.
