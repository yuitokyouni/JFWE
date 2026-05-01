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
| v1.8.9 `WorldVariableBook` / `IndicatorBook` | Code: kernel-level book for `ReferenceVariableSpec` + `VariableObservation`, with append-only revision history and a `list_released_as_of(...)` helper. | After v1.8.8 |
| v1.8.10 Exposure / Dependency Layer | Design + code: a per-actor declaration of which variables / groups the actor is *exposed to* (e.g., a refinery is exposed to `oil_price_reference`). Distinct from `AttentionProfile.watched_*` (what the actor *watches*); exposure is *what affects* the actor. v1.8.10 stores exposures only; transmission (how a variable affects an exposed actor) is later. | After v1.8.9 |
| v1.8.11 `ObservationMenu` builder | Code: helpers that build an `ObservationMenu` automatically by joining an `AttentionProfile` against `ReferenceVariableBook` (filtered for as-of look-ahead) + `SignalBook` + the other v0/v1 books. v1.8.5 storage stays unchanged; v1.8.11 just adds the build path. | After v1.8.10 |
| v1.8.12 Investor + Bank Attention Demo | Code: two more concrete routines (`investor_review`, `bank_review`) that read variables through `ObservationMenu`, declare exposures, and demonstrate that two heterogeneous actors looking at the same world produce structurally different ledger traces. | After v1.8.11 |
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
