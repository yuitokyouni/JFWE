# Japan Financial World Engine (JFWE)

A simulation engine that represents a financial economy through layered
"spaces" (Corporate, Banking, Investors, Exchange, Real Estate, Information,
Policy, External) coordinated by a world kernel. Identity, time, ownership,
contracts, prices, signals, constraints, and inter-space communication all live
in explicit kernel-level structures so that future behavior can be added on top
without hidden cross-space writes.

The current code is at the **v0** milestone: a jurisdiction-neutral world
kernel. It defines the constitutional structure but does not implement any
economic decisions, scenarios, or country-specific calibration.

## Version boundary

| Version | Purpose                                                       |
| ------- | ------------------------------------------------------------- |
| v0.xx   | **Jurisdiction-neutral world kernel** (current)               |
| v1.xx   | Jurisdiction-neutral reference financial system (planned)     |
| v2.xx   | Japan public calibration (later)                              |
| v3.xx   | Japan proprietary / commercial calibration (later)            |

Only v0 is implemented today. Despite the project name, no Japan-specific
calibration is built into v0 — the kernel is fully neutral and could be
calibrated to any jurisdiction. Japan-specific work begins in v2.

## What v0 is

- A `WorldKernel` containing Registry, Scheduler, Clock, Ledger, State, EventBus
- Three network books: Ownership, Contract, Price
- Three projections / evaluators: BalanceSheetView, ConstraintEvaluator, SignalBook
- A `DomainSpace` base class plus minimal identity-level state for each of the
  eight spaces (Corporate, Banking, Investors, Exchange, Real Estate,
  Information, Policy, External)
- An immutable, append-only ledger that records every state-changing event
- An event-bus transport that delivers `WorldEvent`s between spaces with a
  strict next-tick rule
- 444 passing tests, including a full cross-space integration test

## What v0 is not

v0 does **not** implement:

- economic behavior of any kind (no decisions, no actions)
- scenarios, shocks, or stochastic processes
- price formation, order matching, or trading
- bank credit decisions or default logic
- corporate actions or earnings updates
- investor strategies or rebalancing
- policy decisions or central bank reaction functions
- valuation, fundamentals, or intraday market phases
- relationship capital or narrative dynamics
- any Japan-specific calibration

These belong to later versions (v1 for behavior, v2/v3 for Japan
calibration).

## Documentation map

Start here, in order:

- [docs/v0_release_summary.md](japan-financial-world/docs/v0_release_summary.md) — what v0 delivered, what it verifies, what is out of scope
- [docs/architecture_v0.md](japan-financial-world/docs/architecture_v0.md) — module stack and a simple text diagram of how v0 actually fits together
- [docs/v0_scope.md](japan-financial-world/docs/v0_scope.md) — the explicit in/out scope boundary for v0
- [docs/v1_roadmap.md](japan-financial-world/docs/v1_roadmap.md) — what v1 will add (reference behavior, valuation, intraday, etc.)
- [docs/test_inventory.md](japan-financial-world/docs/test_inventory.md) — the 444 tests grouped by component
- [docs/world_model.md](japan-financial-world/docs/world_model.md) — the long-form constitutional design document; every milestone has a section

The original ambition documents are kept for reference and represent the long-
term goal rather than the current v0 implementation:

- [docs/architecture.md](japan-financial-world/docs/architecture.md) — original ambition layout (see `architecture_v0.md` for what v0 actually built)
- [docs/scope.md](japan-financial-world/docs/scope.md) — original ambition scope (see `v0_scope.md` for what v0 actually delivered)
- [docs/ontology.md](japan-financial-world/docs/ontology.md) — domain ontology

## Running the tests

From the `japan-financial-world` directory:

```bash
python -m pytest -q
```

Expected: `444 passed`.

## Running the empty kernel CLI

`world/cli.py` runs an empty world kernel for a given number of days, loading
agents/assets/markets from a YAML file. It does not register any of the eight
domain spaces — it is the v0 smoke-runner, not a full simulation.

From the `japan-financial-world` directory:

```bash
python -m world.cli --world examples/minimal_world.yaml --start 2026-01-01 --days 30
```

The output reports the final clock date, the number of registered objects, and
the number of ledger records produced by the run.

For a full eight-space world, see `tests/test_world_kernel_full_structure.py`,
which builds a populated kernel programmatically and exercises every read
accessor.

## Repository layout

```
japan-financial-world/
├── world/           # Kernel: registry, clock, scheduler, ledger, state,
│                    # event bus, ownership, contracts, prices, balance sheet,
│                    # constraints, signals, kernel, cli
├── spaces/          # DomainSpace base + 8 concrete spaces
│   ├── domain.py
│   ├── corporate/   # {state.py, space.py}
│   ├── banking/
│   ├── investors/
│   ├── exchange/
│   ├── real_estate/
│   ├── information/
│   ├── policy/
│   └── external/
├── tests/           # 444 tests
├── docs/            # design and release documentation
├── schemas/         # YAML schema fragments
├── data/            # example data
└── examples/        # example world YAMLs for the CLI
```

## License

See `LICENSE`.
