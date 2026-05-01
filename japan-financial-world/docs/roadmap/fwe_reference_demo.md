# Roadmap: FWE Reference Demo

> **Status:** v1 of the demo shipped (see
> `docs/fwe_reference_demo_design.md`); this roadmap covers
> follow-on work.
> **Layer:** FWE Reference (public, synthetic).
> **Depends on:** FWE Core public release roadmap.
> **Blocks:** any external talk / write-up that links to a runnable
> example.

## Goal

Keep the FWE Reference Demo as the **single, runnable, synthetic,
jurisdiction-neutral artifact** that answers "what does FWE
actually do?" — and grow it carefully over time without crossing
into market-prediction or calibration territory.

The demo's value is **causal traceability**, not realism. Every
deliverable below preserves that boundary.

## In scope

### Fictional world only

- [ ] Every entity in `examples/reference_world/entities.yaml`
  continues to use the `*_reference_*` naming convention.
- [ ] No real city, region, ticker, instrument, central bank, fund,
  or rating agency name is added in any future expansion.
- [ ] Numeric values stay illustrative round numbers (e.g.,
  base 100, gap +15) chosen for traceability over realism.
- [ ] Currency / unit fields stay neutral (`reference_unit`,
  `index_points`, `rate`); no `JPY` / `USD` / `EUR` baked in.

### Causal ledger trace

- [ ] `expected_story.md` stays in sync with what the script
  produces. Any record-shape change in v0 / v1 that affects the
  demo's output must update this doc in the same commit.
- [ ] The script's printed summary continues to surface the seven
  loop record ids, the delivery target spaces, and the per-event
  type counts.
- [ ] A future expansion may add a second loop run (e.g., a chain
  triggered by the FX factor) but only if it (a) uses the
  existing `ReferenceLoopRunner`, (b) produces independent
  cross-references back to its own setup, and (c) does not
  pretend to model interaction effects.

### No trading

- [ ] Investor portfolios remain **static**. The demo does not buy,
  sell, rebalance, or settle anything.
- [ ] The two banks remain populated for composition completeness;
  they do not extend, tighten, or default on credit.
- [ ] No `ContractBook` mutation is added inside the loop.
- [ ] If a future v1+ behavioral milestone introduces trading, that
  milestone gets its **own** demo; this demo stays trade-free as
  the structural baseline.

### No prediction claims

- [ ] The demo's docs and printed output never use "predict,"
  "forecast," "expected return," "alpha," "trading signal," or
  similar language.
- [ ] The demo is referred to as a "causal trace example" or
  "structural walkthrough" — not as a "scenario" or a
  "stress test."
- [ ] The disclaimer in
  `examples/reference_world/README.md` continues to lead with
  "not investment advice / not a calibrated model."

### Maintenance

- [ ] Demo runs in CI per the FWE Core release roadmap.
- [ ] When v0 / v1 record shapes evolve (e.g., a new optional
  field), the demo's expected story is updated.
- [ ] When the test suite adds new invariants, the demo's tests in
  `tests/test_reference_demo.py` are updated to match.

## Out of scope

- Web UI, hosted service, scenario interactivity.
- Multi-day evolving simulations. The demo is one snapshot.
- Multi-agent decision dynamics.
- Performance / scale benchmarks. The demo runs in milliseconds;
  speed is not its purpose.
- Calibration to any jurisdiction.
- Replacing or competing with the v1.6 closing test
  (`tests/test_reference_loop.py`). The demo is a **runnable**
  artifact; the test stays as the **invariant** record.

## Acceptance criteria for any future expansion

A change to the reference demo is acceptable when **all** hold:

1. The change uses only existing v0 / v1 public APIs.
2. No real-world identifier is introduced.
3. No prediction claim is introduced.
4. `expected_story.md` is updated in the same commit.
5. `tests/test_reference_demo.py` covers the change.
6. `pytest -q` and CI both green.

## Dependencies

- v1.6 `ReferenceLoopRunner` (done).
- `examples/reference_world/` v1 (done).
- FWE Core public release roadmap (CI for the demo).

## Notes

- Resist the temptation to "make the demo more realistic." Realism
  is calibration, and calibration is v2 / v3 territory.
- Resist the temptation to add a second loop "showing investor
  reaction." Reaction is autonomous behavior, which is v1+ work.
- The demo's success is measured by *clarity*, not by output
  complexity.
