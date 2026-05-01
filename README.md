# Japan Financial World Engine (JFWE)

A simulation engine that represents a financial economy through layered
"spaces" (Corporate, Banking, Investors, Exchange, Real Estate, Information,
Policy, External) coordinated by a world kernel. Identity, time, ownership,
contracts, prices, signals, constraints, and inter-space communication all live
in explicit kernel-level structures so that future behavior can be added on top
without hidden cross-space writes.

The current code is at the **v1.7** milestone: a jurisdiction-neutral reference
financial system layered on top of the v0 world kernel. v1 adds reference
record types, books, and an end-to-end orchestrator that links every record
type into a single causal ledger trace. v1 does **not** add autonomous
behavior, decision logic, or country-specific calibration.

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

## Version boundary

| Version | Purpose                                                       | Status                       |
| ------- | ------------------------------------------------------------- | ---------------------------- |
| v0.xx   | Jurisdiction-neutral world kernel                             | **Frozen at v0.16**          |
| v1.xx   | Jurisdiction-neutral reference financial system               | **Frozen at v1.7**           |
| v2.xx   | Japan public calibration                                      | Not started                  |
| v3.xx   | Japan proprietary / commercial calibration                    | Not started                  |

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

## What is intentionally NOT in v0 or v1

Neither v0 nor v1 implements:

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
  — 632 tests grouped by component (444 v0 + 188 v1)

**Long-form / original ambition (kept for reference):**
- [docs/architecture.md](japan-financial-world/docs/architecture.md) —
  original ambition layout
- [docs/scope.md](japan-financial-world/docs/scope.md) — original
  ambition scope
- [docs/ontology.md](japan-financial-world/docs/ontology.md) — domain
  ontology

## Running the tests

From the `japan-financial-world` directory:

```bash
python -m pytest -q
```

Expected: `632 passed` (444 v0 + 188 v1).

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
