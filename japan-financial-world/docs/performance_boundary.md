# Performance Boundary — v1.9.8

> **Status:** v1.9.8 shipped 2026-05-02. This document defines
> the computational boundaries of the v1.9 living reference world,
> identifies the loop shapes the demo currently uses, and pins
> the discipline that future scaling work must follow.
>
> **What this document is:** a written contract about
> *traversal shape*. It is not a profiler, not a benchmark, not
> an optimisation. It exists so a future contributor cannot
> silently turn the demo into a dense all-to-all simulator.
>
> **What this document is not:** a calibration plan, a hot-path
> rewrite, a C++ / Julia port, a price-formation design, or a
> trading / lending mechanism spec. None of those are in scope
> for v1.9.x.

## Why this exists

Through v1.9.0 → v1.9.7 the living reference world grew from a
single-period chain demo (corporate report → menu → selection
→ review) to a four-period sweep that also runs three
synthetic mechanisms each period: firm operating pressure
assessment (v1.9.4), valuation refresh lite (v1.9.5), and bank
credit review lite (v1.9.7). Each mechanism is integrated into
the per-period sweep through bounded all-pairs traversal:

- valuation refresh runs once per `(investor, firm)` pair,
- bank credit review runs once per `(bank, firm)` pair.

The fixture is **deliberately tiny** — 3 firms, 2 investors,
2 banks, 4 periods — and these bounded products are explicitly
demo-bounded. They are fine *only* because the fixture is fixed
and synthetic. The same loop shape against a production-scale
agent population would scale super-linearly in actor count,
which is exactly what this milestone forbids without a sparse
gating layer.

This milestone records the loop shapes so that:

1. Future increases in fixture size cannot accidentally trip a
   quadratic explosion without a test failing first.
2. Future production-like traversal *must* gate on
   relationships / exposures / coverage — not on Cartesian
   actor-product loops.
3. Anyone reviewing the v1.9 freeze surface can see, in one
   place, what the engine is and is not doing.

## Current loop shapes (v1.9.7)

The following table describes the loop shape of each phase
inside `world/reference_living_world.run_living_reference_world`.
`P` = number of periods, `F` = number of firms, `I` = number
of investors, `B` = number of banks. The `n_obs` and
`n_exposures` factors are bounded by the fixture's variable
count (currently 4) and per-firm exposure count (currently
2–3 each).

| Phase                             | Loop shape                                | v1.9 default           |
| --------------------------------- | ----------------------------------------- | ---------------------- |
| Corporate quarterly reporting     | `O(P × F)`                                | 4 × 3 = 12 reports     |
| Firm pressure assessment (v1.9.4) | `O(P × F × n_exposures)`                  | 4 × 3 × ~2.5 = 30 pass |
| Menu construction (per actor)     | `O(P × (I+B) × n_relevant_observations)`  | 4 × 4 × ~4 = 64 pass   |
| Observation set selection         | `O(P × (I+B))`                            | 4 × 4 = 16 selections  |
| Valuation refresh lite (v1.9.5)   | `O(P × I × F)`                            | 4 × 2 × 3 = 24 valns   |
| Bank credit review lite (v1.9.7)  | `O(P × B × F)`                            | 4 × 2 × 3 = 24 reviews |
| Review routines                   | `O(P × (I+B))`                            | 4 × 4 = 16 reviews     |
| Reporting / replay / manifest     | `O(R)` over emitted ledger records        | ~162 records           |

Per-period record-count breakdown (default fixture, v1.9.7):

```
2 × F                  corporate run + corporate signal              =  6
F                      firm pressure signal                          =  3
2 × (I + B)            menu + selection                              =  8
I × F                  valuation                                     =  6
B × F                  bank credit review note                       =  6
2 × (I + B)            review_run + review_signal                    =  8
                                                            total   = 37
× 4 periods                                                         = 148
+ ~14 one-off setup records (interactions, routines, profiles)
                                                          ≈ ~162 records
```

Of the loops above:

- The **bounded all-pairs** loops are the valuation
  `O(P × I × F)` and the bank credit review `O(P × B × F)`.
  These are the two we explicitly classify as *demo-bounded
  monitoring*, not production traversal patterns.
- All other loops are linear in the actor or firm count.

## v1.9 demo discipline

For v1.9.x and v1.9.last:

1. **All-pairs traversal is allowed inside fixed demo-size
   fixtures only.** The demo is not allowed to grow `F`, `I`,
   or `B` beyond a small constant without a milestone that
   first introduces sparse gating.
2. **No path enumeration.** No mechanism may iterate over
   reachable paths in any graph (interactions, ownership,
   relationships, exposures). Path-shaped views remain
   diagnostic, not operational.
3. **No hidden quadratic loops.** The record-count test in
   `tests/test_living_reference_world_performance_boundary.py`
   pins both the per-period and the total record count to
   exact expected values plus a small infrastructure
   allowance. Any change that adds a `(actor × actor)` or
   `(actor × event × firm)` loop will fail it.
4. **Tensor / matrix views are diagnostic.** The interaction
   tensor (`S × S × C`) and the matrix views constructed in
   v1.8 are *not* execution traversal plans. They are not
   materialised on the per-period sweep path.
5. **Reporting cost is `O(R)`.** Living-world report,
   replay-canonicalisation, and manifest are linear scans
   over the ledger record list. They must remain so.

## Sparse gating principles (future)

When v2.x or later begins adding sparse traversal to lift the
demo-bounded ceiling, the following gating principles apply.
None of these are implemented in v1.9.x; they are pinned here
so that a future contributor cannot quietly skip them.

- **Bank credit review** must be gated by an explicit set of
  *(bank, firm)* relationships — for example, `ContractBook`
  exposures (loans, guarantees, derivatives), held positions,
  watchlists, sector mandates, or credit-monitoring
  relationships. The dense `B × F` form is for the synthetic
  demo only.
- **Investor valuation** must be gated by holdings, coverage
  universes, mandates, or watchlists. The dense `I × F` form
  is for the synthetic demo only.
- **Menus** must be built from actor-specific exposure /
  relationship / visibility indexes. They must not enumerate
  every observation in the world.
- **Interaction tensor and matrix views** are diagnostic
  views, not traversal plans. A traversal plan that consults
  them is reading a view, not enumerating paths.
- **No path enumeration in v1.9.** When path-aware reasoning
  becomes necessary, it must be either hop-bounded or
  index-bounded.

## Future acceleration (deferred)

Python remains adequate for v1.9.x. The bounded sweep
completes in well under one second on the default fixture,
and the suite of 1623 tests runs in under ten seconds.

Candidate hot paths *if* future scaling demands a native
component:

- large-scale exposure joins (`ExposureBook` cross-products),
- large menu construction over big visibility indexes,
- a market mechanism / limit order book simulation,
- dense tensor / matrix views if ever materialised on the
  per-period path,
- repeated valuation / credit-review mechanism sweeps over
  large agent populations.

**The first step toward scale is profiling and sparse
indexing, not a premature native rewrite.** No C++, no Julia,
no Rust, no GPU work is in scope for v1.9.x or v1.9.last.

## Semantic caveat — review is not origination

A frequent misreading of v1.9.7 is that "all-bank × all-firm
credit review" describes a real lending-decision flow. It does
not. v1.9.7 produces *review notes* — diagnostic signals about
what a bank looked at and how the evidence aggregated as a
pressure score. v1.9.7 does not:

- approve, reject, or originate any loan,
- enforce any covenant,
- mutate `ContractBook` or `ConstraintBook`,
- declare default, or
- imply a probability of default or an internal rating.

A realistic origination workflow — *firm funding request →
bank underwriting → proposed terms → contract mutation* —
is **future work**, not v1.9.x. The current dense `B × F`
loop is demo-bounded monitoring, used because the synthetic
demo wants every bank to record one note about every firm
each period for explainability. A real engine would gate the
loop on the actual `(bank, firm)` lending relationships.

## Test pins

The discipline above is enforced by
`tests/test_living_reference_world_performance_boundary.py`:

- the per-period record budget equals
  `2F + F + 2(I+B) + IF + BF + 2(I+B) = 37` for the default
  fixture,
- the total over four periods equals 148, plus a small
  infrastructure allowance bounded above,
- the valuation count equals exactly `P × I × F`,
- the bank credit review count equals exactly `P × B × F`,
- the firm pressure signal count equals exactly `P × F`,
- no order, price-update, contract-mutation, ownership-
  transfer, or covenant-breach records appear,
- only the documented record types appear in the ledger.

If any of those pins fails, the demo has either grown the
fixture (intentional but undocumented) or gained a hidden
quadratic loop (unintended).

## Position in the v1.9 sequence

| Milestone | What | Status |
| --------- | ---- | ------ |
| v1.9.0–v1.9.2 | Living-world demo + report + replay/manifest | Shipped |
| v1.9.3 / v1.9.3.1 | Mechanism interface contract + hardening | Shipped |
| v1.9.4 | Reference firm operating pressure assessment | Shipped |
| v1.9.5 | Reference valuation refresh lite | Shipped |
| v1.9.6 | Living-world mechanism integration | Shipped |
| v1.9.7 | Reference bank credit review lite | Shipped |
| **v1.9.8** | **Performance boundary / sparse traversal discipline** | **Shipped** |
| v1.9.last | First public prototype freeze | Planned |

The next non-prototype-freeze work after v1.9.8 is v1.9.last
itself — the public prototype gate.
