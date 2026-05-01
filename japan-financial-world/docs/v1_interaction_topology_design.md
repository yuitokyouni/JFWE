# v1.8.2 Interaction Topology and Attention Framework — Design

> **Status:** design-only milestone. No runtime code in v1.8.2.
> **Layer:** FWE Core (public, jurisdiction-neutral).
> **Depends on:** v1.7 frozen reference financial system, v1.8
> experiment harness, v1.8.1 Endogenous Reference Dynamics.
> **Blocks:** v1.8.3 (InteractionBook), v1.8.4 (AttentionProfile /
> ObservationMenu), and every routine + attention milestone after
> them.

## TL;DR — the core principle

> **`InteractionTopology` is not the engine of the world.
> `Routine` is the execution primitive (v1.8.1).
> `InteractionTopology` defines the possible channels that
> routines may use to push records cross-space.**
> **`AttentionProfile` defines what each actor actually watches.**

v1.8.1 named the *engine* of endogenous activity: scheduled,
bounded, auditable Routines that run regardless of whether an
external shock arrived. v1.8.2 names two layers around that engine:

1. **InteractionTopology** — the wiring diagram. Which spaces can
   talk to which through which channels. The set of *possible*
   cross-space records routines may produce.
2. **AttentionProfile + ObservationMenu + SelectedObservationSet**
   — the receiver-side filter. Different actors watch different
   things in heterogeneous, declared, auditable ways.

Together, the v1.8.1 → v1.8.2 stack reads as:

```
RoutineSpec               (what runs, when)            ← v1.8.1
   │
   │ may use channels declared in
   ▼
InteractionTopology       (which channels are possible) ← v1.8.2
   │
   │ produces records visible to actors per their
   ▼
AttentionProfile          (what each actor watches)     ← v1.8.2
   │
   │ resolved against the date/phase yields
   ▼
ObservationMenu           (what is available now)       ← v1.8.2
   │
   │ filtered by attention rules yields
   ▼
SelectedObservationSet    (what was selected)           ← v1.8.2
   │
   │ optionally consumed by
   ▼
RoutineRunRecord          (per-execution audit)         ← v1.8.1
```

**v1.8.2 implements none of this in code.** The deliverable is
record-shape proposals + boundary rules + heterogeneous-attention
examples, scoped tightly enough that v1.8.3 / v1.8.4 reviewers can
land each layer without re-litigating direction.

## Why scenario-driven shock-response is still wrong

A natural temptation when an interaction layer arrives is to model
it as "a routine runs, fans out a shock through the topology to
every connected actor, and each actor reacts." That is the
scenario-driven failure mode v1.8.1 explicitly rejected, recast in
graph terms.

v1.8.2 commits to two anti-scenario rules at the topology / attention
layer:

1. **An empty topology slice still produces a meaningful run.** If
   an actor's `AttentionProfile` resolves to an empty
   `ObservationMenu` for today, the routine that would consume it
   still runs (per v1.8.1 §43.1) with `status="degraded"` — it
   simply records "nothing relevant was visible" instead of
   producing a richer downstream record.
2. **A channel with no traffic is not a dead channel.** An
   `InteractionSpec` whose flow is silent today is still
   structurally present; it just produced zero records this run.
   The topology is about *what is possible*, not *what fired*.

If a routine becomes silent solely because the topology had no
incoming traffic, the design has slipped back into shock-response
mode and the milestone should be rejected at review.

## Spaces as nodes in a directed multigraph

The eight v0/v1 spaces (Corporate, Banking, Investors, Exchange,
Real Estate, Information, Policy, External) are nodes. Interactions
between them are **edges**. The structure is:

- **Directed.** A `Corporate → Banking` edge (a firm reporting an
  earnings disclosure that a bank reads) is distinct from a
  `Banking → Corporate` edge (a bank's covenant review whose
  output a firm sees). The two carry different `interaction_type`
  values, different timing, different visibility rules.
- **Multigraph.** A given pair of spaces may have multiple edges,
  one per `channel_type`. `Investors → Corporate` could carry
  *engagement-letter* channels, *AGM-vote* channels, and
  *activist-public-disclosure* channels concurrently — three
  edges, not one.
- **Self-loops are first-class.** `Corporate → Corporate`
  describes intra-corporate routines (quarterly reporting prep,
  internal disclosure committee review). The diagonal of the
  topology is not noise; it is where most v1.8.1 routines live.

The natural mathematical model is a **third-rank tensor**
`T ∈ S × S × C`, where:

- `S` is the (small, finite) set of registered spaces.
- `C` is the (open-ended, controlled-vocabulary) set of channel
  types.
- `T[s_i, s_j, c_k]` is either an `InteractionSpec` record or
  null (the channel is undeclared / disabled).

In code this will live as a sparse store keyed by `(source_space,
target_space, channel_type)` with optional per-actor scoping.

### Why a simple upper-triangular matrix is insufficient

A first instinct from textbook network analysis is to summarize
interactions as an adjacency matrix `A ∈ {0, 1}^(|S| × |S|)` —
possibly upper-triangular for "any interaction at all." That
shape silently destroys structure FWE needs:

| Loss | Why it matters |
| --- | --- |
| Direction collapsed | `Corporate → Banking` ≠ `Banking → Corporate`. They have different `interaction_type`, different visibility, different routines that may use them. Symmetric / triangular forms cannot distinguish. |
| Channel multiplicity collapsed | A pair may have 3 channels concurrently (engagement / AGM / activist). A matrix cell with a single 0/1 cannot represent which channels are open. |
| Self-edges erased | An upper-triangular form omits the diagonal; FWE's most active routines live on the diagonal (corporate self-reporting, bank self-review, investor self-portfolio refresh). |
| No room for per-channel timing / visibility / required-input shape | A scalar cell cannot carry `frequency`, `phase_id`, `visibility`, `required_input_ref_types`, etc. |
| Pair existence ≠ flow this tick | A 1 in the matrix says "the channel exists." It says nothing about whether anything flowed today, which is what consumers actually need. |

The design therefore commits to the `S × S × C` tensor shape, with
each non-null cell carrying a full `InteractionSpec`. Snapshots
that need a 2-D summary (e.g., for diagrams) project the tensor
into `S × S` by collapsing the channel axis, but the canonical
data structure preserves all three dimensions.

## `InteractionSpec` — proposed record shape

The static declaration of one interaction channel. **Immutable per
v1 conventions; updates produce a new spec record.**

| Field | Type | Notes |
| --- | --- | --- |
| `interaction_id` | `str` | stable id, e.g. `"interaction:corporate.earnings_disclosure->information.broadcast"` |
| `source_space_id` | `str` | one of the registered space ids |
| `target_space_id` | `str` | one of the registered space ids; may equal source for self-loops |
| `source_id` | `str \| None` | optional: scopes the channel to one source actor (e.g., one specific firm). Null = "any source within source_space_id." |
| `target_id` | `str \| None` | optional: scopes to one target actor. Null = "any target within target_space_id." |
| `interaction_type` | `str` | controlled vocabulary; the *semantic* category (e.g., `"earnings_disclosure"`, `"credit_review"`, `"policy_guidance"`) |
| `channel_type` | `str` | controlled vocabulary; the *delivery medium* category (e.g., `"scheduled_filing"`, `"private_communication"`, `"public_broadcast"`, `"market_action"`) |
| `direction` | `str` | one of `"source_to_target"` / `"bidirectional"`. Bidirectional channels still produce one record per direction at the routine layer; this field is a hint. |
| `frequency` | `Frequency \| None` | DAILY / MONTHLY / QUARTERLY / YEARLY / null (event-triggered). Inherits the v0 enum. |
| `phase_id` | `str \| None` | optional intraday phase (v1.2). |
| `visibility` | `str` | one of `"public"` / `"restricted"` / `"private"`. v0/v1 `SignalBook` already uses this vocabulary; topology mirrors it. |
| `enabled` | `bool` | flag to disable a channel without removing the spec; honors v1's "stored as data" rule. |
| `required_input_ref_types` | `tuple[str, ...]` | record-type names a routine must have read to use this channel (e.g., `("ValuationRecord", "FundamentalsRecord")`). |
| `optional_input_ref_types` | `tuple[str, ...]` | record-type names that *may* enrich the channel's output but are not required. Missing optional inputs lower a routine's status to `"degraded"`, not `"errored"`. |
| `output_ref_types` | `tuple[str, ...]` | record-type names the channel produces (e.g., `("InformationSignal",)`). |
| `routine_types_that_may_use_this_channel` | `tuple[str, ...]` | controlled vocabulary; declares which v1.8.1 routine types may emit on this channel. The empty tuple means "any" (rare; should be justified). |
| `metadata` | `Mapping[str, Any]` | free-form; provenance, parameters, owner notes. |

The `routine_types_that_may_use_this_channel` field is the **key
boundary**: it makes explicit which routines are allowed to push
records through which channels. A routine that publishes on a
channel not listed here is a topology violation — caught at the
v1.8.3 engine layer, not silently allowed.

## `InteractionBook` — proposed API

Conceptually mirrors v1.4's `ExternalProcessBook`: append-only
storage with `Mapping`-shaped queries.

| Method | Returns | Notes |
| --- | --- | --- |
| `add_interaction(spec)` | `InteractionSpec` | append-only; emits `interaction_added` to the ledger; raises on duplicate `interaction_id` |
| `get_interaction(interaction_id)` | `InteractionSpec` | raises `UnknownInteractionError` if absent |
| `list_by_source_space(space_id)` | `tuple[InteractionSpec, ...]` | sparse-row view of the tensor |
| `list_by_target_space(space_id)` | `tuple[InteractionSpec, ...]` | sparse-column view |
| `list_between_spaces(source_space, target_space)` | `tuple[InteractionSpec, ...]` | one cell across all channels |
| `list_by_type(interaction_type)` | `tuple[InteractionSpec, ...]` | semantic-category view |
| `list_by_channel(channel_type)` | `tuple[InteractionSpec, ...]` | delivery-medium view |
| `list_for_routine_type(routine_type)` | `tuple[InteractionSpec, ...]` | every channel a given routine type is permitted to use |
| `build_space_interaction_matrix()` | `Mapping[(s_i, s_j), tuple[InteractionSpec, ...]]` | 2-D collapse of the tensor; `(s_i, s_j) → list[spec]`, channel axis preserved as the value list |
| `snapshot()` | deterministic dict | sorted by id keys; matches v0/v1 snapshot conventions |

`build_space_interaction_matrix` is for read-only consumers
(diagrams, design-doc rendering); routines should use the
filter-style methods.

## Heterogeneous attention — the receiver side

Topology says *what is possible*. **Attention says *what each
actor cares about*.** v1.8.2 introduces three records to make
attention a first-class, heterogeneous, auditable concept:

- `AttentionProfile` — the actor's static declaration of what it
  watches.
- `ObservationMenu` — what is *available* to the actor at a date /
  phase, after applying topology filters.
- `SelectedObservationSet` — what the actor *actually selected*
  from the menu, given the profile rules.

None of these decide behavior. They only record attention.

### `AttentionProfile` — proposed record shape

| Field | Type | Notes |
| --- | --- | --- |
| `profile_id` | `str` | stable id |
| `actor_id` | `str` | the actor (firm / bank / investor / institution / etc.) whose attention this describes |
| `actor_type` | `str` | `"firm"` / `"bank"` / `"investor"` / `"institution"` / `"information_source"` / `"policy_authority"` / etc. |
| `watched_space_ids` | `tuple[str, ...]` | spaces the actor reads from |
| `watched_subject_ids` | `tuple[str, ...]` | specific subjects the actor focuses on (firm tickers, asset ids, factor ids) |
| `watched_signal_types` | `tuple[str, ...]` | filter on `InformationSignal.signal_type` |
| `watched_channels` | `tuple[str, ...]` | filter on `InteractionSpec.interaction_id` (or `channel_type` / `interaction_type`) |
| `watched_metrics` | `tuple[str, ...]` | controlled vocabulary of derived metrics (e.g., `"earnings"`, `"margins"`, `"free_cash_flow"`, `"dscr"`, `"ltv"`, `"valuation_gap"`) |
| `watched_valuation_types` | `tuple[str, ...]` | filter on `ValuationRecord.valuation_type` |
| `watched_constraint_types` | `tuple[str, ...]` | filter on `ConstraintRecord.constraint_type` |
| `watched_relationship_types` | `tuple[str, ...]` | filter on `RelationshipRecord.relationship_type` |
| `update_frequency` | `Frequency` | how often the actor refreshes its attention (DAILY / MONTHLY / QUARTERLY) |
| `phase_id` | `str \| None` | optional intraday phase |
| `priority_weights` | `Mapping[str, float]` | optional ranking weights for resolving conflicts when the menu is over-large; v1.8.4 design will commit to a vocabulary |
| `missing_input_policy` | `str` | one of `"degraded"` (default; partial menu still consumed) / `"strict"` (any missing required item → status=`"errored"`) / `"skip"` (any missing item → status=`"skipped"`). v1.8.1's anti-scenario discipline strongly recommends `"degraded"`. |
| `metadata` | `Mapping[str, Any]` | free-form |

Multiple `AttentionProfile`s per actor are allowed and expected. A
single bank may have one profile for daily liquidity monitoring and
another for quarterly counterparty review — different watched
spaces, different metrics, different cadences.

### `ObservationMenu` — proposed record shape

The *available-to-the-actor* view at a moment. Computed by the
attention engine from the actor's profile and the world's current
record state. **A view, not a stored book**: each routine run
produces its own menu.

| Field | Type | Notes |
| --- | --- | --- |
| `actor_id` | `str` | who this menu is for |
| `as_of_date` | `str` | ISO date the menu is computed for |
| `phase_id` | `str \| None` | optional intraday phase |
| `available_signal_ids` | `tuple[str, ...]` | signals visible to the actor that match the profile |
| `available_valuation_ids` | `tuple[str, ...]` | valuations visible + matching the profile |
| `available_constraint_ids` | `tuple[str, ...]` | constraint evaluations visible + matching |
| `available_relationship_ids` | `tuple[str, ...]` | relationships visible + matching |
| `available_price_ids` | `tuple[str, ...]` | latest price observations for watched subjects |
| `available_external_observation_ids` | `tuple[str, ...]` | external observations on watched factors. **May be empty without invalidating the menu.** |
| `available_interaction_ids` | `tuple[str, ...]` | interaction-spec ids whose channels carried records into the menu |
| `metadata` | `Mapping[str, Any]` | free-form; counts, source breakdowns, warnings |

The menu is *partial-by-design*. Empty lists for one or more
availability fields are normal, not erroneous.

### `SelectedObservationSet` — proposed record shape

The *actually-selected* subset of the menu. Persisted to the
ledger so the routine's audit trail names exactly what informed
its run.

| Field | Type | Notes |
| --- | --- | --- |
| `selection_id` | `str` | stable id |
| `actor_id` | `str` | who selected |
| `attention_profile_id` | `str` | the profile that drove the selection |
| `routine_run_id` | `str \| None` | optional link to the v1.8.1 run that consumed this set |
| `selected_refs` | `tuple[str, ...]` | the record ids selected |
| `skipped_refs` | `tuple[str, ...]` | ids that were on the menu but explicitly skipped (e.g., already consumed in a prior run, low priority weight) |
| `selection_reason` | `str` | controlled vocabulary; `"profile_match"` / `"priority_top_k"` / `"recency"` / `"explicit"` / `"degraded_no_input"` |
| `as_of_date` | `str` | |
| `phase_id` | `str \| None` | |
| `status` | `str` | one of `"completed"` / `"partial"` / `"degraded"` / `"errored"` |
| `metadata` | `Mapping[str, Any]` | free-form |

The `status` vocabulary intentionally differs slightly from
`RoutineRunRecord.status`: a `SelectedObservationSet` can be
`"partial"` (some watched items had nothing visible) without the
parent routine run being `"degraded"` — the routine may have
designed the partial selection as fully acceptable.

`selection_reason` makes the heuristic explicit. v1.8.4 will
commit a starter vocabulary; v1.8.5+ may extend it.

## Degraded operation — the v1.8.1 principle restated

The whole point of v1.8.1 was: routines run on schedule whether or
not the world receives external shocks. v1.8.2 has to preserve
that. The status-vocabulary cascade is:

```
ExternalFactorObservation present? optional input only. Absence ≠ silence.

ObservationMenu may be partial.
  Empty lists in the menu are normal.

SelectedObservationSet may be status="partial" or "degraded".
  selection_reason="degraded_no_input" is a valid recorded outcome.

RoutineRunRecord may be status="degraded".
  The routine still produced its endogenous output (a fundamentals
  record, a relationship view refresh, a debt-aging projection,
  an "review happened" institutional action, etc.).
```

A routine that sets `RoutineRunRecord.status="errored"` solely
because the menu was empty is **violating the v1.8.1 contract**.
v1.8.4+ engine implementations should reject this pattern at
review.

## Heterogeneous attention — examples

Each example below shows what an actor's `AttentionProfile` looks
like in spirit. v1.8.4 will commit the exact schemas; the goal
here is to show that different actors really do watch different
things and that the model accommodates this naturally.

### Value investor

```
profile_id              : "profile:investor:reference_pension_a:value_screening"
actor_id                : "investor:reference_pension_a"
actor_type              : "investor"
watched_space_ids       : ("corporate", "exchange", "information")
watched_signal_types    : ("earnings_disclosure", "guidance_revision",
                            "rating_change")
watched_metrics         : ("earnings", "margins", "free_cash_flow",
                            "valuation_gap")
watched_valuation_types : ("equity",)
update_frequency        : MONTHLY
missing_input_policy    : "degraded"
```

### Macro fund

```
watched_space_ids       : ("external", "policy", "exchange", "information")
watched_signal_types    : ("policy_guidance", "external_observation_summary")
watched_metrics         : ("fx", "rates", "overseas_demand_index")
update_frequency        : DAILY
missing_input_policy    : "degraded"
```

### Credit fund

```
watched_space_ids       : ("banking", "corporate", "information")
watched_signal_types    : ("rating_change", "covenant_breach_notice",
                            "refinancing_announcement")
watched_metrics         : ("spread", "dscr", "covenant_headroom",
                            "maturity_profile")
watched_constraint_types: ("debt_service_coverage", "leverage_max")
update_frequency        : MONTHLY
```

### Bank

```
watched_space_ids       : ("corporate", "real_estate", "information")
watched_metrics         : ("dscr", "ltv", "collateral_value",
                            "refinancing_pressure")
watched_relationship_types: ("main_bank", "syndicate_lead",
                              "trust_committee")
watched_constraint_types: ("debt_service_coverage", "max_leverage")
update_frequency        : MONTHLY
```

### Firm

```
watched_space_ids       : ("banking", "investors", "real_estate",
                            "information")
watched_signal_types    : ("activist_pressure", "rating_change",
                            "credit_conditions_summary")
watched_metrics         : ("credit_conditions", "investor_pressure",
                            "property_valuation")
update_frequency        : QUARTERLY
```

### Information space

```
profile_id              : "profile:information.amplification"
actor_id                : "source:reference_news_outlet"
actor_type              : "information_source"
watched_signal_types    : ("earnings_disclosure", "rating_change",
                            "covenant_breach_notice")
watched_metrics         : ()
update_frequency        : DAILY
```

The information space's profile produces *new* signals that
amplify or revise prior ones. The amplification routine (v1.8.5+)
consumes the information source's `SelectedObservationSet` and
emits a follow-up signal — preserving the v1.6 reference-loop
shape but driven by attention, not by an external observation.

### Corporate self-space (quarterly reporting)

```
profile_id              : "profile:firm:reference_manufacturer_a:internal_reporting"
actor_id                : "firm:reference_manufacturer_a"
actor_type              : "firm"
watched_space_ids       : ("corporate",)               # self-loop
watched_metrics         : ("revenue_run_rate", "operating_margin",
                            "cash", "debt", "book_value")
update_frequency        : QUARTERLY
phase_id                : "post_close"
```

The firm's self-space profile is the input to the
`corporate_quarterly_reporting` routine (v1.8.5). The fact that
this profile uses the diagonal `Corporate → Corporate` edge of the
topology is the most direct demonstration of why the diagonal is
not noise.

## Relation to existing v1 modules

v1.8.2 layers cleanly on top of frozen v1 books — no v1 record
shape, book API, scheduler extension, ledger record type, or
cross-reference field is altered.

| v0 / v1 module | Role under v1.8.2 |
| --- | --- |
| `SignalBook` (v0.7) | Stores information records that interactions emit. `AttentionProfile.watched_signal_types` filters this book. |
| `ValuationBook` (v1.1) | Stores value claims. `AttentionProfile.watched_valuation_types` filters; `ObservationMenu.available_valuation_ids` references. |
| `ConstraintEvaluator` (v0.6) | Produces evaluations. `AttentionProfile.watched_constraint_types` filters; menus reference. |
| `RelationshipCapitalBook` (v1.5) | Stores soft ties. `AttentionProfile.watched_relationship_types` filters. |
| `InstitutionBook` (v1.3) | Stores action records produced by institution-owned routines. The four-property action contract (v1.3) continues to govern these writes. |
| `ExternalProcessBook` (v1.4) | Stores external observations. `AttentionProfile.watched_*` may include external factor ids; absence of observations does not silence the actor. |
| `RoutineSpec` (v1.8.1) | The execution primitive. Routines may declare topology / attention dependencies in their `input_refs`. |
| `InteractionTopology` (v1.8.2) | Defines possible cross-space channels. |
| `AttentionProfile` (v1.8.2) | Defines what each actor watches. |
| `ObservationMenu` (v1.8.2) | View of what is available to an actor at a moment. |
| `SelectedObservationSet` (v1.8.2) | Record of what was selected from a menu. |

The v1.8.2 records are **additive**. v1.8.3 will add
`InteractionBook`; v1.8.4 will add the attention machinery. The v1
freeze surface (v1.7) is unchanged.

## Boundaries — what v1.8.2 does NOT do

v1.8.2 is a vocabulary milestone. The following are explicitly out
of scope and v1.8.x reviewers should reject any PR that crosses
them:

- **Interaction topology does not decide behavior.** A topology
  with an open channel from `Banking → Corporate` does not imply
  that any bank lends to any firm. Lending decisions are a
  separate v1+ behavioral milestone.
- **Attention does not execute trades or lending decisions.** A
  bank's `AttentionProfile.watched_metrics` may include `"dscr"`,
  but the bank routine that consumes the resulting menu does not
  call any loan, change any covenant, or reprice any contract.
- **`ObservationMenu` is a view, not a mutation.** Building a menu
  reads from the ledger and the books; it never writes.
  `ObservationMenu` is not a record type; it is a typed mapping
  produced fresh per routine run.
- **`SelectedObservationSet` is a record of attention, not an
  economic action.** Persisting which signals an investor "looked
  at" is not the same as the investor buying or selling. v1.8.x
  routines emit signals / valuations / institutional-action records
  through the existing v1 APIs; selecting an observation does not
  by itself produce any of those.
- **Routines may later consume `SelectedObservationSet`, but
  v1.8.2 does not implement that consumption.** v1.8.4 wires the
  attention machinery; v1.8.5+ is where routines actually read a
  selection. v1.8.2 only records the proposed shape.
- **No price formation, trading, lending decisions, corporate
  actions, policy reaction functions, Japan calibration, real
  data, or external-shock scenario engine.** All of these were
  off-limits in v1.7 and v1.8.1; v1.8.2 inherits the same
  prohibitions.

## Updated milestone sequence (revises v1.8.1's draft)

v1.8.1's design doc proposed a sequence that put the Routine
Engine immediately at v1.8.2 and the rest of the routines after.
v1.8.2 now reorders the v1.8.x line so the topology + attention
substrate lands *before* concrete routines, because routines
should consume the substrate from their first commit rather than
being retro-fitted later.

| Milestone | Scope | Code? |
| --- | --- | --- |
| **v1.8.1 Endogenous Reference Dynamics — Design** | Routine vocabulary, the seven candidate routines, anti-scenario discipline. (Shipped as `abb1a7c`.) | No |
| **v1.8.2 Interaction Topology and Attention — Design** | This document. `InteractionSpec` / `InteractionBook` / `AttentionProfile` / `ObservationMenu` / `SelectedObservationSet` proposed shapes; heterogeneous-attention examples; boundaries. | No |
| **v1.8.3 InteractionBook + Matrix / Tensor View** | `InteractionSpec` + `InteractionBook` + `RecordType.INTERACTION_ADDED` + `build_space_interaction_tensor()` + `build_space_interaction_matrix()`. No routines wired yet; the book is a sparse store + tensor / matrix projection view. **Shipped** (50 tests; 725 → 775 total). | Yes (kernel) |
| **v1.8.4 RoutineBook + RoutineRunRecord** (storage + audit) | `RoutineSpec` + `RoutineRunRecord` + `RoutineBook` + `routine_can_use_interaction(...)` predicate. **Storage only**: no execution. The original v1.8.4 draft bundled the attention layer too, but landing four record types in one PR was too large; the attention layer was split out to v1.8.5. **Shipped** (72 tests; 775 → 847 total). | Yes (kernel) |
| **v1.8.5 AttentionProfile / ObservationMenu / SelectedObservationSet** | The §44 attention layer split out from the original v1.8.4 draft. Storage + lookup only; `AttentionBook` plus the three new ledger types and the `profile_matches_menu` structural-overlap predicate. **Shipped** (102 tests; 847 → 949 total). | Yes (kernel) |
| **v1.8.6 Routine engine (plumbing)** | Caller-initiated execution service: `RoutineEngine`, `RoutineExecutionRequest`, `RoutineExecutionResult`. Validates interaction compatibility against this `InteractionBook`. v1.8.6 is plumbing only — no scheduler integration, no automatic firing, no concrete routines. **Shipped** (50 tests; 949 → 999 total). | Yes (kernel) |
| **v1.8.7 Corporate Quarterly Reporting Routine** | First concrete routine: `corporate_quarterly_reporting`, on the diagonal `Corporate → Corporate` self-loop. Writes one synthetic `corporate_quarterly_report` `InformationSignal` per call through `RoutineEngine` + `SignalBook`. Synthetic only. **Shipped** (26 tests; 999 → 1025 total). | Yes (one routine) |
| **v1.8.8 Reference Variable Layer — Design** | Names the universe of observable world-context variables (macro / financial / material / energy / technology / real-estate / labor / logistics / expectations). Anti-scenario discipline: **the interaction tensor stays about channels, not scenarios**; reference variables are observable context, not shocks. See `v1_reference_variable_layer_design.md`. | No |
| **v1.8.9 `WorldVariableBook` / `IndicatorBook`** | Code: `ReferenceVariableSpec` + `VariableObservation` records, append-only revision history with `vintage_id` / `revision_of`, look-ahead-bias-free release helper. | Yes (kernel) |
| **v1.8.10 Exposure / Dependency Layer** | Code: per-actor exposure declarations distinct from `AttentionProfile.watched_*`. | Yes (kernel) |
| **v1.8.11 `ObservationMenu` builder** | Code: helpers that build an `ObservationMenu` automatically by joining an `AttentionProfile` against `ReferenceVariableBook` + `SignalBook` + other v0/v1 books. | Yes (kernel) |
| **v1.8.12 Investor and Bank Attention Demo** | Two more concrete routines: investor-side review and bank-side review. First place where heterogeneous attention against a shared variable layer produces structurally different ledger traces for two actors looking at the same world. | Yes |
| **v1.9 Living Reference World Demo** | A successor reference demo that runs for a full year on the routine + topology + attention + variable stack **without any external observation**, with non-empty ledger entries on every quarter-end / monthly review / relationship refresh cycle. The replay-determinism gate must hold; the manifest must remain stable. | Yes (demo + tests) |

After v1.9, the v1.x line closes. Subsequent work is either a v1+
behavioral milestone with an explicit charter (e.g., adding price
formation as v1.10) or v2 (Japan public calibration, populating
routine / attention / topology parameters from public data).

## Open questions / non-decisions

v1.8.2 deliberately does not commit:

- **Where `InteractionBook` lives in `world/`.** Likely
  `world/interactions.py` modeled on `world/external_processes.py`;
  v1.8.3 will commit.
- **The exact `channel_type` and `interaction_type` controlled
  vocabularies.** A starter set will be drawn from the seven
  reference routines and the heterogeneous-attention examples
  above when v1.8.3 / v1.8.4 land. v1.8.2's vocabulary is
  illustrative only.
- **Whether `AttentionProfile` is per-actor-per-routine or
  per-actor.** v1.8.4 will commit; preference is multiple profiles
  per actor (the bank may run "daily liquidity" and "quarterly
  counterparty review" as separate profiles).
- **`priority_weights` schema.** Reserved for v1.8.4. v1.8.2 only
  promises the field exists.
- **Sensitivity-matrix integration.** v1.8.1 already prohibited
  sensitivity matrices from being the *engine*. v1.8.2 inherits
  the prohibition and adds: if a future v1.8.6+ ships
  sensitivity-matrix content, it does so as `metadata` on
  `InteractionSpec` or as a separate v3 SensitivityBook. It must
  not introduce a code path that requires an external observation
  to fire.
- **How `InteractionTopology` interacts with the v1.2 phase
  scheduler.** The `phase_id` field exists on every relevant
  record; the engine-side wiring is a v1.8.3 concern.
- **Cross-actor cross-space security.** v1.8.2 keeps the v1
  visibility vocabulary (`"public"` / `"restricted"` / `"private"`).
  Stricter access-control models (e.g., per-actor allow lists on
  restricted channels) are out of scope until a milestone names
  them as a target.

## Files in this milestone

- `docs/v1_interaction_topology_design.md` — this document.
- `docs/v1_endogenous_reference_dynamics_design.md` — milestone
  sequence updated to point at the v1.8.2-revised order; cross-
  link to this doc added.
- `docs/world_model.md` — gains §44 documenting the principle and
  the proposed record shapes.

No `world/`, `spaces/`, `examples/`, or `tests/` file is changed.
The 725-test baseline is unchanged at v1.8.2; v1.8.3+ milestones
will grow the suite.

## Relation to v1.8.1's anti-scenario discipline

v1.8.2 strengthens, not weakens, the v1.8.1 principle:

- v1.8.1 said: "external shocks are not the engine; routines are."
- v1.8.2 adds: "and even when the topology has open channels and
  every actor has an attention profile, an empty menu does not
  silence the routine. Heterogeneous attention is *more* robust
  to absent inputs, not less."

If a future v1.8.x review uncovers a routine + attention design
where every routine becomes silent on a no-shock day, **the
problem is the design, not the inputs**. Reject and re-spec.
