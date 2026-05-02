# Japan Financial World Engine (JFWE) / Financial World Engine (FWE)

**FWE / JFWE is a jurisdiction-neutral financial-world simulation
substrate.** It models a financial economy through layered "spaces"
(Corporate, Banking, Investors, Exchange, Real Estate, Information,
Policy, External) coordinated by a world kernel, and now ships an
**endogenous routine + heterogeneous attention chain** that produces
auditable ledger traces from internal cycles — corporate reporting,
attention building, and review — without external shocks.

This is **research software**. It demonstrates *how* a financial
world can be modeled with explicit identity, time, ownership,
contracts, prices, signals, constraints, variables, exposures,
attention, and routines.

The current public prototype is **not a forecasting model**, **not
investment advice**, and **not calibrated** to any real economy or
institution. What it currently demonstrates is **auditable
endogenous information and review flows** across a small synthetic
world, with deterministic Markdown reports, replay-determinism
manifests (SHA-256 digest), and explicit no-economic-behavior
boundaries. **Financial decision behavior is intentionally
limited.** Mechanism layers (firm-financial, valuation,
credit-review, investor-intent, market) attach to the substrate one
milestone at a time and are documented in
[`docs/model_mechanism_inventory.md`](japan-financial-world/docs/model_mechanism_inventory.md)
and
[`docs/behavioral_gap_audit.md`](japan-financial-world/docs/behavioral_gap_audit.md).
The reference data is fully synthetic; Japan calibration is v2 / v3
territory.

The current code is at **v1.10.5 living-world integration**, layered
on top of the **v1.9.last public prototype freeze**. v1.9 layered
three review-only synthetic mechanisms (firm operating-pressure
assessment, valuation refresh lite, bank credit review lite) onto
the v1.8 endogenous activity stack and integrated them into a
deterministic four-quarter sweep over a small synthetic fixture.
v1.10.x added a non-binding engagement / strategic-response storage
layer on top: stewardship themes → portfolio-company dialogue
metadata → investor escalation candidates → corporate strategic
response candidates, with industry demand condition context.
v1.10.5 wires that layer into the living reference world demo as
five new per-period phases plus one setup-time phase. The headline
artifact is the **living reference world**: 3 firms × 2 investors ×
2 banks × 3 industries × 4 quarters, runnable from a clean clone
with a single command, byte-deterministic across runs, and fully
reconstructable from the kernel's append-only ledger. **No
autonomous economic behavior is added in v1 / v1.8 / v1.9 / v1.10**
— no price formation, no trading, no lending decisions, no
voting / proxy filing / corporate-action execution, no
disclosure-filing execution, no demand or revenue forecasting, no
firm financial-statement updates, no Japan calibration.

## Current public prototype (v1.9.last)

The v1.9.last public prototype freezes a **single runnable artifact**:
the **living reference world** — a deterministic four-quarter sweep
over a small synthetic fixture. From a clean clone:

```bash
pip install -e ".[dev]"
cd japan-financial-world

# Compact operational trace:
python -m examples.reference_world.run_living_reference_world

# + deterministic Markdown ledger trace report:
python -m examples.reference_world.run_living_reference_world --markdown

# + reproducibility manifest (JSON, SHA-256 living_world_digest):
python -m examples.reference_world.run_living_reference_world \
    --manifest /tmp/fwe_living_world_manifest.json
```

Each mode is byte-identical across consecutive runs.

**What runs each period:**

| Phase                                       | Source        |
| ------------------------------------------- | ------------- |
| Corporate quarterly reporting               | v1.8.7        |
| Firm operating-pressure assessment          | v1.9.4 mech   |
| Heterogeneous investor / bank attention     | v1.8.11/12    |
| Valuation refresh lite                      | v1.9.5 mech   |
| Bank credit review lite                     | v1.9.7 mech   |
| Investor / bank review routines             | v1.8.13       |
| Ledger trace report                         | v1.9.1        |
| Replay / manifest / digest                  | v1.9.2        |
| Performance-boundary discipline             | v1.9.8        |

**Default fixture:** 3 firms, 2 investors, 2 banks, 4 quarters.
Per-period work writes 37 ledger records; a full run total
sits in `[148, 180]` records (formula + small one-off setup
allowance). All identifiers follow the `*_reference_*`
synthetic-only convention.

**What v1.9.last deliberately does NOT do:**

- no price formation, no trading, no order matching;
- no lending decisions, no loan origination, no covenant
  enforcement, no contract or constraint mutation;
- no firm financial-statement updates;
- no canonical valuations (each `ValuationRecord` is one
  valuer's opinionated synthetic claim, stamped with
  `no_price_movement` / `no_investment_advice` / `synthetic_only`);
- no Japan calibration, no real-data ingestion, no scenarios;
- no investment advice — direct or indirect.

For the single-page reader-facing summary see
[`docs/v1_9_public_prototype_summary.md`](japan-financial-world/docs/v1_9_public_prototype_summary.md).
For the performance boundary that gates production-scale
traversal see
[`docs/performance_boundary.md`](japan-financial-world/docs/performance_boundary.md).

## Current capability

What the v1.8 stack ships:

- **World kernel** (v0) — `WorldKernel` orchestrating identity, time,
  registry, scheduler, ledger, state, and event bus.
- **Eight domain spaces** (v0) — Corporate, Banking, Investors,
  Exchange, Real Estate, Information, Policy, External; wired through
  a shared `DomainSpace` contract.
- **Ledger / registry / event bus** — append-only causal trace, stable
  WorldIDs, and `bind()`-mediated cross-space transport.
- **Valuation / institution / relationship layers** (v1.1, v1.3, v1.5)
  — `ValuationBook`, `InstitutionBook`, `RelationshipCapitalBook`, plus
  the four-property action contract.
- **Reference variable + exposure layers** (v1.8.9, v1.8.10) —
  `WorldVariableBook` (kernel-level reference variables and observations
  with vintage / look-ahead-safe filtering) and `ExposureBook` (per-actor
  variable dependencies as data, not as calculation).
- **Interaction topology** (v1.8.3) — `InteractionBook` + sparse
  tensor / matrix views over the inter-space channel graph.
- **Routine infrastructure** (v1.8.4 / v1.8.6 / v1.8.7) —
  `RoutineBook` + `RoutineEngine` + the first concrete routine
  (`corporate_quarterly_reporting`).
- **Attention infrastructure** (v1.8.5 / v1.8.11 / v1.8.12) —
  `AttentionBook` (profiles / menus / selections), the
  `ObservationMenuBuilder` join service, and the heterogeneous
  investor / bank attention demo.
- **Review routines** (v1.8.13) — `investor_review` and `bank_review`
  on Investors → Investors and Banking → Banking self-loops; consume
  selected observations and emit synthetic review notes.
- **Endogenous chain harness** (v1.8.14) —
  `world/reference_chain.py::run_reference_endogenous_chain`
  orchestrates the full chain in one helper call.
- **Ledger trace report** (v1.8.15) — `world/ledger_trace_report.py`
  turns the chain's ledger slice into a deterministic
  `LedgerTraceReport` plus a compact Markdown rendering.

## What the reference demo can do now

With v1.8.14 + v1.8.15, a single helper produces this auditable
non-shock chain:

```
corporate quarterly reporting
  -> RoutineRunRecord + corporate-report InformationSignal
heterogeneous investor / bank attention
  -> 2 ObservationMenu records
  -> 2 SelectedObservationSet records (investor and bank diverge)
investor / bank review routines
  -> 2 RoutineRunRecords
  -> 2 review-note InformationSignals
human-readable ledger trace report
  -> deterministic Markdown summary of every record the chain wrote
```

Every step is caller-initiated. Every record is reconstructable from
the kernel's ledger alone. Two fresh kernels seeded identically
produce byte-identical chains and byte-identical reports. Selection
between actors is heterogeneous *as data*, not as decision: the
investor and the bank, looking at the same world, record different
selected refs because their `AttentionProfile` watch fields differ.

## What it still does not do

The v1.8 stack is **infrastructure for endogenous activity**, not
behavior. It deliberately does not implement:

- price formation, order matching, or any market microstructure
- trading, portfolio rebalancing, or allocation decisions
- bank credit / lending decisions, default detection, covenant trips
- valuation refresh (the comparator stays read-only; no impact
  estimation, sensitivity, DSCR, LTV, or covenant stress)
- corporate actions, earnings dynamics, or cash-flow projection
- policy reaction functions, rate-setting rules, or scenario engines
- any Japan-specific calibration (BOJ, MUFG, GPIF, JGB / USDJPY
  series, TSE listings — all v2 / v3 territory)
- real data ingestion (no public-data licenses are wired)
- investment advice of any form

If your use case requires any of the above, this repository is the
**substrate** below them, not the implementation of them.

## Quickstart

From the repo root, install the project plus dev dependencies:

```bash
pip install -e ".[dev]"
```

Then, from `japan-financial-world/`:

```bash
# Tests
python -m pytest -q

# v1.7-era reference demo (single-day causal trace)
python -m examples.reference_world.run_reference_loop

# v1.8.14 endogenous chain demo (compact operational trace)
python -m examples.reference_world.run_endogenous_chain

# v1.8.15 ledger trace report appended to the operational trace
python -m examples.reference_world.run_endogenous_chain --markdown
```

Both demos use only synthetic, jurisdiction-neutral identifiers, run
in well under a second, and are deterministic across invocations.

## Roadmap

| Version       | Goal                                                      | Status                       |
| ------------- | --------------------------------------------------------- | ---------------------------- |
| v1.8.0–v1.8.16 | Endogenous activity infrastructure + freeze              | Shipped |
| v1.9.0        | Living Reference World Demo (multi-period sweep)          | Shipped |
| v1.9.1-prep   | Living world report contract audit                        | Shipped |
| v1.9.1        | Living World Trace Report                                 | Shipped |
| v1.9.2        | Living World Replay / Manifest / Digest                   | Shipped |
| v1.9.3        | Model Mechanism Inventory + Behavioral Gap Audit + Mechanism Interface | Shipped |
| v1.9.3.1      | Mechanism Interface Hardening (deep-freeze + rename + ordering clarification) | Shipped |
| v1.9.4        | Reference Firm Operating Pressure Assessment Mechanism (first concrete `MechanismAdapter`) | Shipped |
| v1.9.5        | Reference Valuation Refresh Lite Mechanism (`valuation_mechanism` adapter) | Shipped |
| v1.9.6        | Living-world Mechanism Integration (wires v1.9.4 + v1.9.5 into the multi-period sweep) | Shipped |
| v1.9.7        | Reference Bank Credit Review Lite Mechanism (`credit_review_mechanism` adapter; integrated into the multi-period sweep) | Shipped |
| v1.9.8        | Performance Boundary / Sparse Traversal Discipline (docs + tests pinning loop shapes; no new behaviour) | Shipped |
| **v1.9.last** | **Public Prototype Freeze** (synthetic-only, CLI-first, deterministic, explainability-first; living reference world as the headline artifact) | **Shipped** |
| v1.10.0       | Universal Engagement / Strategic Response Consolidation (docs-only design naming the engagement / response layer; signal-only, jurisdiction-neutral; no code, no test count change) | Shipped |
| v1.10.1       | Stewardship theme signal (`StewardshipThemeRecord` + `StewardshipBook` + ledger `STEWARDSHIP_THEME_ADDED` + kernel wiring + 58 tests; storage / audit only) | Shipped |
| v1.10.2       | Portfolio-company dialogue record (`PortfolioCompanyDialogueRecord` + `DialogueBook` + ledger `PORTFOLIO_COMPANY_DIALOGUE_RECORDED` + kernel wiring + 53 tests; engagement metadata storage / audit only — no transcript, content, notes, minutes, attendees, verbatim, or paraphrase fields) | Shipped |
| v1.10.3       | Investor escalation candidate + corporate strategic response candidate (`InvestorEscalationCandidate` + `EscalationCandidateBook` added to `world/engagement.py`; `CorporateStrategicResponseCandidate` + `StrategicResponseCandidateBook` in new `world/strategic_response.py`; ledger `INVESTOR_ESCALATION_CANDIDATE_ADDED` + `CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED` + kernel wiring + 107 tests; candidate-metadata storage / audit only — no execution, no vote_cast / proposal_filed / campaign_executed / exit_executed / letter_sent on the investor side, no buyback_executed / dividend_changed / divestment_executed / merger_executed / board_change_executed / disclosure_filed on the corporate side) | Shipped |
| v1.10.4       | Industry demand condition signal (`IndustryDemandConditionRecord` + `IndustryConditionBook` in new `world/industry.py`; ledger `INDUSTRY_DEMAND_CONDITION_ADDED` + kernel wiring + 84 tests; synthetic, jurisdiction-neutral context evidence — bounded `demand_strength` and `confidence` in `[0.0, 1.0]`; no forecast_value / revenue_forecast / sales_forecast / market_size / vendor_consensus fields; not a demand forecast, not a revenue model, not real data) | Shipped |
| v1.10.4.1     | Type-correct industry-condition cross-reference slot (additive `trigger_industry_condition_ids` field + `list_by_industry_condition` filter on `CorporateStrategicResponseCandidate` / `StrategicResponseCandidateBook`; +4 tests; backward-compatible — disambiguates `signal_id` vs `condition_id` by field, not by payload introspection; no new primitive, no new book, no new ledger record type) | Shipped |
| **v1.10.5**   | **Living-world integration** (wires v1.10.1 → v1.10.4 (+ v1.10.4.1) into `world/reference_living_world.py` as five new per-period phases — industry demand → dialogue → escalation → corporate response — plus one setup-time phase — stewardship themes; `LivingReferencePeriodSummary` / `LivingReferenceWorldResult` / `LivingWorldTraceReport` / canonical / manifest grow additively; CLI surfaces new counts; +15 integration tests; per-run record window widens from `[148, 180]` to `[220, 252]`; `living_world_digest` value differs from v1.9.last by design; no new mechanism, no new `RecordType`, no new book, no executed action) | **Shipped (1947 tests)** |
| v1.10.last    | Public engagement layer freeze (docs-only) | Planned |
| v2.0          | Japan public-data calibration design gate                 | Not started                  |
| v3.0          | Proprietary Japan calibration / expert-data layer         | Private                      |

For the v1.8.16 freeze surface and the v1.9 plan see:

- [`docs/v1_8_release_summary.md`](japan-financial-world/docs/v1_8_release_summary.md)
- [`docs/v1_9_living_reference_world_plan.md`](japan-financial-world/docs/v1_9_living_reference_world_plan.md)
- [`docs/public_prototype_plan.md`](japan-financial-world/docs/public_prototype_plan.md)

## Project layers

The project is organized into five product layers. The current repository
contains FWE Core only; Japan-specific calibration is layered separately
above it.

- **FWE Core** — public; jurisdiction-neutral kernel + reference financial
  system. This is what the current freeze contains.
- **FWE Reference** — public; planned synthetic / fictional-country demo on
  top of FWE Core.
- **JFWE Public** — partially public; Japan public-data calibration (v2
  territory). Public release depends on per-source redistribution rights.
- **JFWE Proprietary** — never public; private commercial calibration with
  paid data, expert input, and proprietary templates (v3 territory).

FWE / JFWE is **not** a market predictor and **not** investment advice; it
is a causal, auditable, multi-space financial-world simulation engine. See
[`docs/product_architecture.md`](japan-financial-world/docs/product_architecture.md),
[`docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md),
and [`docs/naming_policy.md`](japan-financial-world/docs/naming_policy.md)
for the full layer definitions, public / restricted artifact rules, and
naming conventions. The repository keeps its legacy `JWFE` /
`japan-financial-world/` names in this version; any rename is a separate
migration.

## Disclaimer

This project is **research software** intended for engine design,
simulation methodology, and structural exploration of how financial
worlds can be modeled.

- It is **not investment advice.** Nothing in this repository — code,
  examples, tests, docs, ledger output — should be read as a market
  view, allocation suggestion, valuation opinion, or trade signal.
- It is **not a calibrated real-world market model.** v0 and v1 are
  jurisdiction-neutral and contain only synthetic, fictional reference
  identifiers. The example data in `data/sample/` and `examples/` is
  illustrative; numbers and names are placeholders, not measurements.
- It contains **no proprietary data.** No expert interview notes, no
  paid feeds, no fund holdings, no named-institution stress results,
  no client communications. See
  [`docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md)
  for the public / restricted artifact rules.
- **Japan calibration is future work.** v2 (Japan public calibration)
  and v3 (Japan proprietary calibration) have not started. Any
  reference to BOJ, MUFG, GPIF, Toyota, or other real Japanese
  institutions in the docs appears only to define what is *prohibited*
  in v1 or *deferred* to v2 / v3 — never as a present-day capability.
- It is **not production software.** No SLA, no support commitment,
  no guarantee of API stability beyond what each milestone's freeze
  document explicitly promises.

What this project *is*: a causal, auditable, multi-space simulation
kernel and reference financial system, with an append-only ledger
designed so that every state-changing event is reconstructable as a
graph. The intent is to make the *engine* trustworthy in its
mechanics, not to make any specific *output* trustworthy as a
real-world claim.

## Version boundary

| Version | Purpose                                                                          | Status                       |
| ------- | -------------------------------------------------------------------------------- | ---------------------------- |
| v0.xx   | Jurisdiction-neutral world kernel                                                | **Frozen at v0.16**          |
| v1.0–v1.7 | Jurisdiction-neutral reference financial system                                | **Frozen at v1.7**           |
| v1.8.0  | Experiment harness (config-driven driver + manifest + replay gate, no new behavior) | **Tagged `v1.8-public-release`** |
| v1.8.x  | Endogenous activity infrastructure (interactions / routines / attention / variables / exposures / chain harness / trace report) | Shipped |
| v1.8.16 | Freeze / readiness / docs                                                        | Shipped                      |
| v1.9.0–v1.9.8 | Living reference world + three review-only mechanisms + performance boundary | Shipped                      |
| **v1.9.last** | **Public prototype freeze**                                                  | **Shipped (1626 tests)**     |
| v2.xx   | Japan public calibration                                                         | Not started                  |
| v3.xx   | Japan proprietary / commercial calibration                                       | Not started                  |

Despite the project name, no Japan-specific calibration is built into v0 or v1
— both are fully neutral and could be calibrated to any jurisdiction.
Japan-specific work begins in v2 (public data) and v3 (proprietary data). For
the v2 readiness picture see
[`docs/v2_readiness_notes.md`](japan-financial-world/docs/v2_readiness_notes.md).

## What v1 adds on top of v0

v0 froze the structural contract: books, projections, transport, identity-
level state, the four-property `bind()` contract, the next-tick rule, the
no-cross-mutation rule. v1 layers reference content on that contract:

- **v1.1 Valuation / fundamentals** — `ValuationBook`, `ValuationRecord`,
  `ValuationGap`, `ValuationComparator` (currency vs numeraire stored as
  data; gaps computed against `PriceBook`).
- **v1.2 Intraday phase scheduler** — `Phase` enum extended with six
  intraday phases (overnight → pre_open → opening_auction →
  continuous_session → closing_auction → post_close);
  `run_day_with_phases` dispatch; per-date run-mode guard preserving v0
  date-tick semantics for spaces that have not opted in.
- **v1.3 Institutional decomposition** — `InstitutionProfile`,
  `MandateRecord`, `PolicyInstrumentProfile`, `InstitutionalActionRecord`;
  the **four-property action contract** (explicit inputs / explicit
  outputs / ledger record / no cross-space mutation).
- **v1.4 External world process layer** — `ExternalFactorProcess` (spec,
  not runtime), `ExternalFactorObservation`, `ExternalScenarioPath`. v1
  stores process specs as data; v2+ runs them.
- **v1.5 Relationship capital** — `RelationshipRecord` (directed pairs),
  `RelationshipView`, `RelationshipCapitalBook`. Decay parameters stored
  but not applied automatically; reads return last-recorded strength
  deterministically.
- **v1.6 First closed-loop reference economy** — `ReferenceLoopRunner`, a
  thin orchestrator that links `ExternalFactorObservation` →
  `InformationSignal` → `ValuationRecord` → `ValuationGap` →
  `InstitutionalActionRecord` → `InformationSignal` → `WorldEvent`
  through cross-references alone, producing a complete causal ledger
  trace.
- **v1.7 Reference system freeze** — documentation only; no Python
  changes. This document, `v1_release_summary.md`, `architecture_v1.md`,
  `v1_scope.md`, and `v2_readiness_notes.md` were authored as part of
  the freeze.
- **v1.8 Experiment harness** — `world/experiment.py` provides
  `ExperimentConfig` / `load_experiment_config` /
  `validate_experiment_config` / `run_reference_experiment`. The
  harness loads a synthetic-only YAML config, validates it, runs the
  bundled reference demo, and emits a JSON manifest plus a SHA-256
  ledger digest under the configured `output_dir`. Adds zero
  simulation behavior; the schema's optional sections are documented
  for future v1.8.x milestones but raise `NotImplementedError` at
  runtime in v1.8 itself. See
  [`docs/v1_experiment_harness_design.md`](japan-financial-world/docs/v1_experiment_harness_design.md).
- **v1.8.1 → v1.8.15 Endogenous activity stack** — interaction
  topology (`InteractionBook`, sparse tensor / matrix views), routine
  infrastructure (`RoutineBook`, `RoutineEngine`, the corporate
  quarterly reporting routine), attention infrastructure
  (`AttentionBook`, the `ObservationMenuBuilder` join service, the
  investor / bank attention demo with explicit variable / exposure
  hooks), reference variables (`WorldVariableBook`), exposures
  (`ExposureBook`), the two review routines (`investor_review`,
  `bank_review`), the orchestration harness
  (`run_reference_endogenous_chain`), and the read-only ledger trace
  report (`world/ledger_trace_report.py`). Each milestone landed
  additively; together they let a caller produce a deterministic,
  fully ledger-reconstructable non-shock chain. See `docs/world_model.md`
  §43 – §57 and
  [`docs/v1_8_release_summary.md`](japan-financial-world/docs/v1_8_release_summary.md).
- **v1.8.16 Freeze / readiness** — docs and release-readiness only.
  No new code behavior; consolidates v1.8 as a coherent milestone and
  prepares v1.9. See
  [`docs/v1_8_release_summary.md`](japan-financial-world/docs/v1_8_release_summary.md),
  [`docs/v1_9_living_reference_world_plan.md`](japan-financial-world/docs/v1_9_living_reference_world_plan.md),
  and
  [`docs/public_prototype_plan.md`](japan-financial-world/docs/public_prototype_plan.md).

## What v0 vs v1 own

A simple way to assign a feature to a milestone:

| Layer | Owns                                                                  | Examples                                                              |
| ----- | --------------------------------------------------------------------- | --------------------------------------------------------------------- |
| v0    | Structure: books, projections, transport, identity, scheduler         | `BalanceSheetView`, `EventBus`, `DomainSpace`, `OwnershipBook`        |
| v1    | Reference behavior: record types, reference books, action contract, orchestrator | `ValuationBook`, `InstitutionBook`, `ReferenceLoopRunner` |
| v2    | Japan public calibration                                              | BOJ as `InstitutionProfile`, public macro time series                 |
| v3    | Japan proprietary calibration                                         | Paid news feeds, fund holdings, expert overrides                      |

If a request would require changing a v1 record shape, it is a **v1+
behavioral milestone**. If it would require adding Japan public data, it
is a **v2 task**. If it would require paid data or expert overrides, it
is a **v3 task**. See
[`docs/v1_scope.md`](japan-financial-world/docs/v1_scope.md) and
[`docs/v2_readiness_notes.md`](japan-financial-world/docs/v2_readiness_notes.md).

## What is intentionally NOT in v0, v1, or v1.8

Neither v0 nor v1 (including the v1.8 harness) implements:

- price formation, order matching, market microstructure
- bank credit decisions, default detection, covenant trips
- investor strategy, allocation, rebalancing
- corporate actions, earnings updates, revenue dynamics
- policy reaction functions, rate-setting rules
- runtime execution of `ExternalFactorProcess` specs
- automatic relationship-strength decay
- iterative loops or year-long simulation drivers
- any Japan-specific calibration

These belong to v1+ behavioral milestones, v2 (Japan public), or v3
(Japan proprietary). The v1 contract is structural completeness — every
record type exists, every cross-reference field is wired, the ledger is
a complete causal trace — not realism or autonomous dynamics.

## Documentation map

Start here:

**Repo overview:**
- [docs/world_model.md](japan-financial-world/docs/world_model.md) — the
  constitutional design document; every milestone has a section.

**v0 (frozen at v0.16):**
- [docs/v0_release_summary.md](japan-financial-world/docs/v0_release_summary.md)
- [docs/architecture_v0.md](japan-financial-world/docs/architecture_v0.md)
- [docs/v0_scope.md](japan-financial-world/docs/v0_scope.md)

**v1 (frozen at v1.7):**
- [docs/v1_release_summary.md](japan-financial-world/docs/v1_release_summary.md)
  — what v1 delivered, what it proves, what is out of scope
- [docs/architecture_v1.md](japan-financial-world/docs/architecture_v1.md)
  — module stack and text diagram of v0 kernel + v1 modules + ledger
  causal trace
- [docs/v1_scope.md](japan-financial-world/docs/v1_scope.md) — explicit
  in/out boundary for v1
- [docs/v2_readiness_notes.md](japan-financial-world/docs/v2_readiness_notes.md)
  — forward-looking note on data sources, entity mapping, license
  review, and v2 vs v3 boundary

**v1.8 (tagged `v1.8-public-release` at v1.8.0; v1.8.16 freeze):**
- [docs/v1_8_release_summary.md](japan-financial-world/docs/v1_8_release_summary.md)
  — v1.8 milestone-by-milestone summary
- [docs/v1_9_living_reference_world_plan.md](japan-financial-world/docs/v1_9_living_reference_world_plan.md)
  — next milestone (Living Reference World Demo)
- [docs/v1_9_public_prototype_summary.md](japan-financial-world/docs/v1_9_public_prototype_summary.md)
  — single-page reader summary of what v1.9.last freezes (and
  what it does not claim)
- [docs/public_prototype_plan.md](japan-financial-world/docs/public_prototype_plan.md)
  — v1.9.last public-prototype target + acceptance criteria
- [docs/performance_boundary.md](japan-financial-world/docs/performance_boundary.md)
  — loop shapes, demo discipline, sparse-gating principles
- [docs/fwe_reference_demo_design.md](japan-financial-world/docs/fwe_reference_demo_design.md)
  — reference demo, replay-determinism gate, manifest design
- [docs/v1_experiment_harness_design.md](japan-financial-world/docs/v1_experiment_harness_design.md)
  — config-driven harness for the demo
- [docs/v1_endogenous_reference_dynamics_design.md](japan-financial-world/docs/v1_endogenous_reference_dynamics_design.md)
  — anti-scenario routine vocabulary (v1.8.1)
- [docs/v1_interaction_topology_design.md](japan-financial-world/docs/v1_interaction_topology_design.md)
  — interaction topology + heterogeneous attention design (v1.8.2)
- [docs/v1_reference_variable_layer_design.md](japan-financial-world/docs/v1_reference_variable_layer_design.md)
  — reference variable + exposure design (v1.8.8 + hardening)
- [examples/reference_world/README.md](japan-financial-world/examples/reference_world/README.md)
  — runnable demos (reference loop + endogenous chain)

**v1 sub-milestone designs:**
- [docs/v1_reference_system_design.md](japan-financial-world/docs/v1_reference_system_design.md)
  — v1 design statement
- [docs/v1_design_principles.md](japan-financial-world/docs/v1_design_principles.md)
  — invariants
- [docs/v1_module_plan.md](japan-financial-world/docs/v1_module_plan.md)
  — v1.1 → v1.6 sequence
- [docs/v1_behavior_boundary.md](japan-financial-world/docs/v1_behavior_boundary.md)
  — per-module behavior owner table
- [docs/v1_valuation_fundamentals_design.md](japan-financial-world/docs/v1_valuation_fundamentals_design.md)
  (v1.1)
- [docs/v1_intraday_phase_design.md](japan-financial-world/docs/v1_intraday_phase_design.md)
  (v1.2)
- [docs/v1_institutional_decomposition_design.md](japan-financial-world/docs/v1_institutional_decomposition_design.md)
  (v1.3)
- [docs/v1_external_world_process_design.md](japan-financial-world/docs/v1_external_world_process_design.md)
  (v1.4)
- [docs/v1_relationship_capital_design.md](japan-financial-world/docs/v1_relationship_capital_design.md)
  (v1.5)
- [docs/v1_first_closed_loop_design.md](japan-financial-world/docs/v1_first_closed_loop_design.md)
  (v1.6)
- [docs/v1_roadmap.md](japan-financial-world/docs/v1_roadmap.md) —
  earlier high-level overview, kept for reference

**Tests:**
- [docs/test_inventory.md](japan-financial-world/docs/test_inventory.md)
  — 1947 tests grouped by component (444 v0 + 188 v1.0–v1.7 + 1315 post-v1.7)

**Long-form / original ambition (kept for reference):**
- [docs/architecture.md](japan-financial-world/docs/architecture.md) —
  original ambition layout
- [docs/scope.md](japan-financial-world/docs/scope.md) — original
  ambition scope
- [docs/ontology.md](japan-financial-world/docs/ontology.md) — domain
  ontology

## Installing dependencies

From the **repo root** (this directory), install the project plus
its dev dependencies (pytest + ruff):

```bash
pip install -e ".[dev]"
```

This brings in **PyYAML 6.x** (pinned `>=6,<7` in `pyproject.toml`),
the supported YAML parser for the reference demo's catalog
(`examples/reference_world/entities.yaml`) and the v1.8 experiment
harness configs. CI runs the same `pip install -e ".[dev]"` step.
The `world/loader.py` fallback parser is a defensive minimal
fallback — **not a full YAML implementation** — and only handles
the v0 sample-data shape. If you skip PyYAML, the reference demo
will fail at runtime; see
[`japan-financial-world/world/loader.py`](japan-financial-world/world/loader.py)
for the exact policy.

## Running the tests

From the `japan-financial-world` directory:

```bash
python -m pytest -q
```

Expected: `1947 passed` at the latest commit (444 v0 + 188 v1
frozen reference + 1315 post-v1.7 additions covering the reference
demo, replay, manifest, catalog-shape, experiment harness, the
v1.8.x endogenous-activity stack — interactions, routines,
attention, variable / exposure layers, the menu builder, the
investor / bank attention demo, the two review routines, the chain
harness, and the ledger trace report — plus the v1.9.x living
reference world, its trace report, the replay / manifest helpers,
the v1.9.3 / v1.9.3.1 mechanism interface contract + hardening,
the CLI argv-isolation pin, the v1.9.4 reference firm operating
pressure assessment mechanism, the v1.9.5 reference valuation
refresh lite mechanism, the v1.9.6 integration of those two
mechanisms into the multi-period sweep, the v1.9.7 reference
bank credit review lite mechanism integrated into the same sweep,
the v1.9.8 performance-boundary / sparse-traversal discipline tests
pinning the loop shapes of that sweep, the v1.10.1 stewardship
theme signal storage / audit layer, the v1.10.2
portfolio-company dialogue record metadata storage / audit layer,
the v1.10.3 investor escalation candidate storage / audit layer
(extending the engagement test file), the v1.10.3 corporate
strategic response candidate storage / audit layer in the
strategic-response test file, the v1.10.4 industry demand
condition signal storage / audit layer in the new
industry-conditions test file, the v1.10.4.1 additive
type-correct industry-condition cross-reference slot on
`CorporateStrategicResponseCandidate` exercised in the
strategic-response test file, and the v1.10.5 living-world
integration that wires the v1.10.1 → v1.10.4.1 storage layer
into the living reference world demo's per-period sweep
exercised in `tests/test_living_reference_world.py`).

To run only v0 tests, exclude the v1 test files; to run only v1 tests:

```bash
python -m pytest -q tests/test_valuations.py tests/test_phases.py \
    tests/test_phase_scheduler.py tests/test_institutions.py \
    tests/test_external_processes.py tests/test_relationships.py \
    tests/test_reference_loop.py
```

## Running the empty kernel CLI

`world/cli.py` runs an empty world kernel for a given number of days, loading
agents/assets/markets from a YAML file. It does not register any of the eight
domain spaces or any v1 books — it is the v0 smoke-runner, not a full
simulation.

From the `japan-financial-world` directory:

```bash
python -m world.cli --world examples/minimal_world.yaml --start 2026-01-01 --days 30
```

The output reports the final clock date, the number of registered objects, and
the number of ledger records produced by the run.

For a populated eight-space world, see
`tests/test_world_kernel_full_structure.py`. For an end-to-end v1 reference
loop trace, see `tests/test_reference_loop.py`.

## Repository layout

```
japan-financial-world/
├── world/                    # v0 kernel (frozen) + v1 books (frozen)
│   ├── ids.py, registry.py, clock.py, scheduler.py,
│   ├── ledger.py, state.py, event_bus.py, events.py,
│   ├── ownership.py, contracts.py, prices.py,
│   ├── balance_sheet.py, constraints.py, signals.py,
│   ├── loader.py, validation.py, kernel.py, cli.py,    # ─── v0
│   ├── valuations.py,                                  # ─── v1.1
│   ├── phases.py,                                      # ─── v1.2
│   ├── institutions.py,                                # ─── v1.3
│   ├── external_processes.py,                          # ─── v1.4
│   ├── relationships.py,                               # ─── v1.5
│   └── reference_loop.py                               # ─── v1.6
├── spaces/                   # DomainSpace base + 8 concrete spaces (v0)
│   ├── domain.py
│   ├── corporate/   banking/   investors/   exchange/
│   ├── real_estate/ information/ policy/    external/
├── tests/                    # 632 tests (444 v0 + 188 v1)
├── docs/                     # design, release, scope, readiness docs
├── schemas/                  # YAML schema fragments
├── data/                     # example data
└── examples/                 # example world YAMLs for the CLI
```

## License

See `LICENSE`.
