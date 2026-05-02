# Model Mechanism Inventory

> **v1.9.3 audit**. This document classifies every major
> component currently in the tree against a small mechanism
> taxonomy, so the project can talk honestly about *what is a
> model* vs *what is plumbing dressed as a model*. It is the
> substance gate before any v1.9.x public-prototype polish.
>
> Companion to [`behavioral_gap_audit.md`](behavioral_gap_audit.md),
> which names the missing mechanisms and ranks the next
> milestone options.
>
> **Numbering note.** The user-facing task that prompted this
> work was titled "v1.9.2 Model Mechanism Inventory & Behavioral
> Gap Audit." However v1.9.2 had already shipped as Living World
> Replay / Manifest / Digest (commit `9d495bf`,
> [`world_model.md`](world_model.md) §62) one milestone earlier.
> This audit therefore lands as **v1.9.3**. The recommended
> next path in the gap-audit doc is renumbered accordingly.

## Mechanism taxonomy

A *mechanism* is a piece of code that takes typed inputs and
produces typed outputs in a way that can be audited from the
ledger. Below is the taxonomy used in this inventory, ordered
roughly from "least model-substance" to "most":

| Class | What it is |
| --- | --- |
| **infrastructure** | The kernel surface that lets other things compose. No domain content of its own. Examples: `Registry`, `EventBus`, `Clock`. |
| **source-of-truth storage** | An append-only / immutable book that records typed records. No behavior beyond CRUD + invariants. Examples: `OwnershipBook`, `ContractBook`, `SignalBook`. |
| **structural model** | Records typed *relationships* (who owns whom, who is exposed to which variable). Still data; no dynamics. Examples: `RelationshipCapitalBook`, `ExposureBook`. |
| **observation / attention model** | Records *who notices what* and *who selects what to consume*. Encodes heterogeneity but does not interpret it economically. Examples: `AttentionBook`, `ObservationMenuBuilder`. |
| **routine / process model** | Encodes *who does what action when*, recording the run as data. The action itself may be synthetic. Examples: `RoutineEngine`, `corporate_quarterly_reporting`. |
| **deterministic demo rule** | A small, hand-coded rule that takes inputs and produces a recordable output. Synthetic; never calibrated. Examples: the v1.8.12 selection rule (`select_observations_for_profile`); the v1.8.13 review payload. |
| **economic behavior model** | A mechanism that produces an output meant to *carry economic interpretation* — a margin estimate, a valuation claim, a credit pressure score, a price update. **None currently implemented.** |
| **not yet modeled** | A capability the project intentionally does not provide. Examples: trading, lending decisions, price formation, macro dynamics. |

The taxonomy is deliberately ordered so the line *"this project
does not yet ship economic behavior models"* is unambiguous. The
**deterministic demo rule** class is the closest the current
tree gets — it produces structured outputs from structured
inputs, but the outputs are recordable artifacts, not economic
claims.

## Component classification

Every component below is currently in the tree at v1.9.2.
"Future model attachment point" names where a future v1.9.x or
v1.x economic-behavior model could plug in **as a mechanism**
(see `world/mechanisms.py` — `MechanismAdapter` Protocol).

### Kernel infrastructure

| Component | Class | What it does | What it does NOT do | Mutates economic state? | Decisions? | Deterministic? | Calibrated? | Synthetic-only? | Future model attachment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `WorldKernel` | infrastructure | Wires every book + clock + scheduler + ledger + state into one object. | Run any economic step. | No | No | Yes | No | Yes | Hosts future mechanism adapters. |
| `Registry` | infrastructure | Stable id assignment + entity lookup. | Decide entity behavior. | No | No | Yes | No | Yes | Naming surface for synthetic mechanism owners. |
| `Ledger` | infrastructure | Append-only causal record store. | Interpret records. | No | No | Yes | No | Yes | Mechanism run records flow through here. |
| `Clock` | infrastructure | Single source of simulation time. | Step itself. | No | No | Yes | No | Yes | Mechanisms read `as_of_date` from here. |
| `Scheduler` | infrastructure | Phase calendar + tick boundaries. | Auto-fire mechanisms. | No | No | Yes | No | Yes | Future schedulers can trigger mechanism runs (still caller-initiated; v1.x preserves the rule). |
| `EventBus` | infrastructure | Inter-space delivery on the next tick. | Decide what gets delivered. | No | No | Yes | No | Yes | Mechanism outputs may publish events (must respect the four-property contract). |
| `State` | infrastructure | Minimal mutable state facade. | Encode any domain meaning. | No | No | Yes | No | Yes | — |

### Source-of-truth storage books

| Component | Class | What it does | What it does NOT do | Mutates state? | Decisions? | Det? | Cal? | Synth? | Future attachment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `OwnershipBook` | source-of-truth storage | `add_position`, `transfer`, balance reads. | Decide who owns what. | No (it *records* mutations the caller drove). | No | Yes | No | Yes | Investor-intent and credit mechanisms emit ownership-change proposals. |
| `ContractBook` | source-of-truth storage | Record + status-update contracts; covenants stored as data. | Trip covenants automatically. | No | No | Yes | No | Yes | Credit-review mechanism reads covenants; constraint-response mechanism proposes status updates. |
| `PriceBook` | source-of-truth storage | Append-only price observations. | Form prices. | No | No | Yes | No | Yes | A future market mechanism (FCN / herding / MG / SG / LOB adapter) would write here through proposed records the caller commits. |
| `BalanceSheetProjector` | source-of-truth storage | Read-only projection over `OwnershipBook` × `PriceBook`. | Mutate either. | No | No | Yes | No | Yes | Firm-financial mechanism reads balance-sheet views as inputs. |
| `ConstraintBook` | source-of-truth storage | Records named constraints with thresholds. | Evaluate them autonomously. | No | No | Yes | No | Yes | Credit-review mechanism proposes constraint pressure deltas. |
| `ConstraintEvaluator` | deterministic demo rule | Caller-initiated evaluation of one constraint against current state. | Stress-test scenarios. | No | The evaluator returns pass / fail; no behavior follows from it in v1.x. | Yes | No | Yes | Caller-side mechanism that produces constraint-evaluation records. |
| `SignalBook` | source-of-truth storage | Records `InformationSignal`s with visibility / credibility metadata. | Emit signals. | No | No | Yes | No | Yes | Every routine and every mechanism that produces a signal writes here. |
| `ValuationBook` | source-of-truth storage | Records `ValuationRecord` + `ValuationGap`. | Refresh valuations. | No | No | Yes | No | Yes | **Valuation Refresh Lite** (v1.9.5) writes here from review selections. |
| `InstitutionBook` | source-of-truth storage | `InstitutionProfile`, `MandateRecord`, `PolicyInstrumentProfile`, `InstitutionalActionRecord` (v1.3 four-property action contract). | Decide policy. | No | No | Yes | No | Yes | A future policy-reaction mechanism would emit `InstitutionalActionRecord`s through the contract. Out of scope for v1.x. |
| `RelationshipCapitalBook` | structural model | Directed-pair relationship records with strength. | Decay strength autonomously. | No | No | Yes | No | Yes | Relationship-mediated mechanisms (e.g., who tells whom) read here. |
| `ExternalProcessBook` | source-of-truth storage | Stores external-factor process specs + observations + scenario paths. | Run them. | No | No | Yes | No | Yes | A future macro mechanism would step a process and emit observations. v1.x stores only. |

### v1.8 endogenous activity layer

| Component | Class | What it does | What it does NOT do | Mutates state? | Decisions? | Det? | Cal? | Synth? | Future attachment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `InteractionBook` (v1.8.3) | structural model | Sparse channel multigraph between spaces. | Decide which channels fire. | No | No | Yes | No | Yes | Mechanism runs declare which interaction channel they used. |
| `RoutineBook` (v1.8.4) | source-of-truth storage | Records routine specs + run records. | Execute routines. | No | No | Yes | No | Yes | Mechanism runs produce `RoutineRunRecord` (or a sibling `MechanismRunRecord`). |
| `RoutineEngine` (v1.8.6) | routine / process model | Caller-initiated execution: validate, collect refs, persist one `RoutineRunRecord`. | Auto-fire from `tick()` / `run()`. | No | The engine routes refs but does not interpret them. | Yes | No | Yes | Mechanism runs may flow through this engine or a `MechanismAdapter` symmetric path. |
| `AttentionBook` (v1.8.5) | observation / attention model | Records `AttentionProfile` / `ObservationMenu` / `SelectedObservationSet`. | Build menus or select. | No | The schema records selections; selection logic lives elsewhere. | Yes | No | Yes | Mechanisms read selections as input bundles. |
| `WorldVariableBook` (v1.8.9) | source-of-truth storage | `ReferenceVariableSpec` + `VariableObservation` + look-ahead-safe filters. | Generate observations. | No | No | Yes | No | Yes | A future macro mechanism populates observations as proposed records. |
| `ExposureBook` (v1.8.10) | structural model | Declares per-actor dependencies on world variables. | Compute impact. | No | No | Yes | No | Yes | Firm / valuation / credit mechanisms read exposures. |
| `ObservationMenuBuilder` (v1.8.11) | observation / attention model | Joins `AttentionBook` × `SignalBook` × `WorldVariableBook` × `ExposureBook` to materialise one menu per actor. | Select. | No | No | Yes | No | Yes | Provides the canonical input bundle for selection-driven mechanisms. |
| `select_observations_for_profile` (v1.8.12) | deterministic demo rule | Filters menu refs against `AttentionProfile.watched_*` fields. | Rank / weight / interpret. | No | No (recordable filter, not a decision). | Yes | No | Yes | A future ranking mechanism may pre-process the menu before this filter runs. |
| `corporate_quarterly_reporting` (v1.8.7) | routine / process model | Self-loop routine that publishes one synthetic `corporate_quarterly_report` signal per call. | Compute earnings, revenue, leverage. | No | The signal payload is illustrative. | Yes | No | Yes | A future v1.9.x mechanism may produce the payload from a synthetic state-update model. **Note:** v1.9.4 ships a *separate* `Reference Firm Operating Pressure Assessment Mechanism` (`firm_financial_mechanism` family) that emits a `firm_operating_pressure_assessment` signal — it does **not** update the corporate-reporting payload, and it does **not** update any financial statement line item. See `world_model.md` §64. |
| `FirmPressureMechanismAdapter` (v1.9.4) | economic behavior model (reference, synthetic) | First concrete `MechanismAdapter`. Reads resolved variable observations + exposures from `MechanismRunRequest.evidence`, computes five synthetic operating / financing pressure dimensions in `[0, 1]` (input-cost / energy-power / debt-service / fx-translation / logistics) plus the mean overall, and proposes one `firm_operating_pressure_assessment` signal. | Update any financial statement, balance-sheet view, valuation, price, or any other piece of state. The mechanism's hard boundary, embedded verbatim in the signal's metadata: *"pressure_assessment_signal_only; no financial-statement update; no decision; no auto-trigger"*. | No | The pressure dimensions are diagnostic; they are not decisions. | Yes | `calibration_status="synthetic"` | Yes | Valuation Refresh Lite (v1.9.5, shipped) consumes the pressure assessment as input via the v1.9.3.1 evidence contract. |
| `ValuationRefreshLiteAdapter` (v1.9.5) | economic behavior model (reference, synthetic) | Second concrete `MechanismAdapter`. Reads the v1.9.4 firm-pressure-assessment signal from `MechanismRunRequest.evidence` (plus optional corporate signals, selected observation sets, observations, exposures), applies a synthetic linear pressure-haircut to a caller-supplied baseline value (default coefficients: 0.30 haircut per unit pressure; 0.40 confidence decay per unit pressure), and proposes one `ValuationRecord` with `method="synthetic_lite_pressure_adjusted"`. | Form, observe, or move any market price; trade; rebalance any portfolio; make a buy / sell / hold recommendation; lend; enforce a covenant; update any firm financial statement; imply that the produced `estimated_value` is canonical truth — it is *one valuer's opinionated synthetic claim*. The four-flag boundary statement is embedded verbatim in the valuation's metadata: `no_price_movement` / `no_investment_advice` / `synthetic_only` / `model_id`. | No | Valuation is a recordable claim, not a decision. | Yes | `calibration_status="synthetic"` | Yes | Bank Credit Review Lite (v1.9.7, shipped) consumes the pressure signal and the valuation record as inputs via the v1.9.3.1 evidence contract. |
| `BankCreditReviewLiteAdapter` (v1.9.7) | economic behavior model (reference, synthetic) | Third concrete `MechanismAdapter` (`credit_review_mechanism` family). Consumes the v1.9.4 firm-pressure-assessment signal + the v1.9.5 valuation records on the firm + the bank's selected observation set + corporate reporting signal as evidence, and proposes one `bank_credit_review_note` `InformationSignal` per (bank, firm). Five synthetic [0,1] dimensions: operating_pressure_score, valuation_pressure_score, debt_service_attention_score, collateral_attention_score, information_quality_score; plus overall_credit_review_pressure (mean of the four pressure-side scores). | Approve / reject any loan; enforce or trip any covenant; mutate `ContractBook` / `ConstraintBook`; change interest rates; declare default; move any price; imply that any score is a probability of default, an internal rating, or any other regulator-recognised credit measure. The eight-flag boundary statement is embedded verbatim in the signal's metadata: `no_lending_decision`, `no_covenant_enforcement`, `no_contract_mutation`, `no_constraint_mutation`, `no_default_declaration`, `no_internal_rating`, `no_probability_of_default`, `synthetic_only`. | No | Credit review is a diagnostic note, not a decision. | Yes | `calibration_status="synthetic"` | Yes | Future credit-decision / covenant mechanisms can consume the credit review note as upstream evidence via the v1.9.3.1 evidence contract. v1.9.x deliberately does not ship them. |
| `investor_review` / `bank_review` (v1.8.13) | routine / process model | Self-loop routines that consume `SelectedObservationSet`s and emit a synthetic review-note signal. | Make buy / sell / lend decisions. | No | The note carries count summaries only. | Yes | No | Yes | Investor-intent (v1.9.x) and credit-review (v1.9.6) mechanisms attach here. |
| `run_reference_endogenous_chain` (v1.8.14) | routine / process model | Orchestrates the corporate report → menus → selections → reviews chain in one call. | Add new behavior. | No | No | Yes | No | Yes | Mechanism runs replace component helper calls one-by-one as v1.9.x lands. |
| `LedgerTraceReport` (v1.8.15) | deterministic demo rule | Read-only Markdown / dict projection over a chain's ledger slice. | Interpret records. | No | No | Yes | No | Yes | Mechanism run records appear in the same slice and are reportable through the same shape. |
| `run_living_reference_world` (v1.9.0) | routine / process model | Sweeps the v1.8.14 chain across multiple firms × periods. | Add behavior. | No | No | Yes | No | Yes | Each period becomes a mechanism-run scope. |
| `LivingWorldTraceReport` (v1.9.1) | deterministic demo rule | Read-only Markdown / dict projection over a sweep. | Interpret. | No | No | Yes | No | Yes | Same. |
| `living_world_replay` / `living_world_manifest` (v1.9.2) | infrastructure | Canonical view + SHA-256 digest + JSON manifest. | Add behavior. | No | No | Yes | No | Yes | Mechanism run digests can be folded in as a sibling field. |

## Verdict

> **The current system is an auditable routine-driven
> information-flow substrate, with one shipped reference
> mechanism. It is still not a price-formation model, credit
> model, valuation model, macro model, or firm-financial
> dynamics model.**

What the system *does* do, well:

- record who notices what and what they selected;
- record routine runs that consume selections and emit
  audit-only review notes;
- preserve every record in a deterministic, replay-checked
  ledger;
- render the result as a Markdown / JSON report that a
  reader can verify in 60 seconds;
- **assess synthetic operating / financing pressure** on a
  firm via the v1.9.4
  `Reference Firm Operating Pressure Assessment Mechanism`,
  emitting a diagnostic signal (read-only against the kernel;
  no financial-statement mutation).

What it still does **not** do — and the gap audit
([`behavioral_gap_audit.md`](behavioral_gap_audit.md)) names
the ranking — is *interpret* most records as economic claims.
There is no margin number that came from a balance-sheet
update mechanism, no valuation that came from a discount-rate
mechanism, no credit pressure that came from a covenant-stress
mechanism, no price that came from a market mechanism. The
v1.9.4 pressure assessment is the *first* such mechanism, and
it is deliberately scoped to a diagnostic signal (not a
decision and not a financial-state update). v1.9.5 (valuation
refresh lite) and v1.9.6 (bank credit review lite) are the
next mechanisms in the recommended path.

## Mechanism interface (from `world/mechanisms.py`)

The substrate now ships a small mechanism interface so v1.9.4+
mechanisms have a standard shape to attach. The interface is
**pure data** — the dataclasses carry no behavior. Mechanisms
*propose* outputs; the caller decides what is committed.

### Five types (v1.9.3 + v1.9.3.1 hardening)

```python
MechanismSpec        — model_id, model_family, version,
                       assumptions, calibration_status,
                       stochasticity, required_inputs,
                       output_types, metadata
MechanismRunRequest  — one resolved mechanism invocation prepared
                       by the caller. Splits evidence_refs
                       (caller-resolved lineage id tuple,
                       verbatim) from evidence (the resolved
                       data, grouped by record type / logical
                       key). Adapters read evidence; they do NOT
                       access kernel / books.
                       (v1.9.3.1 rename of the v1.9.3
                       MechanismInputBundle. The old name is
                       kept as a one-line alias to the same
                       class for one milestone.)
MechanismOutputBundle — proposed records the caller may commit
                        (signals, valuations, run records,
                        constraint pressure deltas, etc.)
MechanismRunRecord   — append-only audit record of one
                       mechanism invocation (model_id, status,
                       input / output digests, ledger refs).
                       v1.9.3.1: input_refs and
                       committed_output_refs are preserved
                       verbatim — no auto-dedupe, no auto-sort.
MechanismAdapter     — Protocol for "an object with a `spec`
                       and `apply(request) -> output`" — adapters
                       are how concrete mechanisms (FCN /
                       herding / MG / SG / LOB / firm-financial /
                       valuation / credit-review) plug in
```

### v1.9.3.1 deep-freeze property

A `frozen=True` dataclass alone is *shallow* — it prevents
reassignment of a top-level attribute but does nothing to stop
an outsider mutating a nested `dict` via subscript-assign.
v1.9.3.1 adds a deep-freeze pass: every JSON-like field on the
four dataclasses is recursively converted to `MappingProxyType`
(for mappings) and `tuple` (for lists / tuples / sets) on
construction. Subscript-assign on any nested dict raises
`TypeError`. `to_dict()` thaws back to plain mutable `dict` /
`list` so the JSON-friendly projection stays caller-mutable.

The fields covered:

- `MechanismSpec.metadata`
- `MechanismRunRequest.evidence` / `state_views` / `parameters`
  / `metadata`
- every proposal mapping inside `MechanismOutputBundle` plus
  `output_summary` and `metadata`
- `MechanismRunRecord.metadata`

### v1.9.3.1 ordering responsibility

`MechanismRunRecord.input_refs` and `committed_output_refs` are
stored **verbatim** in caller-supplied order — duplicates are
preserved, ordering is preserved, no sort. Callers needing
deterministic replay must order / dedupe their tuples themselves;
some mechanisms (e.g., a sequence of revisions) intentionally
carry meaningful order, and v1.9.3.1 declines to second-guess
them.

### Mechanism principles

1. **Mechanisms do not directly mutate books.** They propose
   outputs; the caller commits them through the existing
   `add_*` ledger paths.
2. **Mechanisms consume typed refs / selected observations /
   state views.** Inputs are explicit; no hidden globals.
3. **Mechanisms return proposed records or output bundles.**
4. **The caller decides which outputs are committed.**
5. **Every mechanism run is ledger-auditable.**
6. **Each mechanism declares**: `model_id`, `model_family`,
   `version`, `assumptions`, `calibration_status`,
   `stochasticity`, `required_inputs`, `output_types`.
7. **Reference mechanisms are simple and synthetic.** v1.9.4 –
   v1.9.6 mechanisms must be jurisdiction-neutral, deterministic
   (or pinned-seed stochastic), and produce visible ledger
   traces.
8. **Advanced mechanisms (FCN, herding, minority game,
   speculation game, LOB models) attach as adapters.** They are
   v2+ candidates; v1.x ships the *contract* they will fit
   into.

### Suggested mechanism families

The five families v1.9.4+ will populate:

- `firm_financial_mechanism` — synthetic margin / liquidity /
  debt pressure update from corporate-reporting signals + world
  variables.
- `valuation_mechanism` — selected refs → `ValuationRecord`
  proposals + `ValuationGap`.
- `credit_review_mechanism` — selected refs → credit-review
  notes + constraint-pressure deltas.
- `investor_intent_mechanism` — selected refs → non-binding
  intent records (no trades, no orders, no allocations).
- `market_mechanism` — FCN / herding / MG / SG / LOB adapters.
  Out of scope for v1.x.

The first four are the recommended next milestones; the last is
explicitly v2+ territory.

## Read this with

- [`behavioral_gap_audit.md`](behavioral_gap_audit.md) — the
  gap analysis + recommended path.
- [`world_model.md`](world_model.md) §63 — the v1.9.3 audit
  section.
- [`v1_9_living_reference_world_plan.md`](v1_9_living_reference_world_plan.md) — the v1.9 plan with the renumbered roadmap.
- [`public_prototype_plan.md`](public_prototype_plan.md) — the
  v1.9.last public-prototype gates (re-affirmed by this audit).
