# v1.9.last — Public Prototype Summary

> **Status:** v1.9.last shipped 2026-05-02. This document is the
> single-page, reader-facing summary of what the v1.9 public
> prototype freezes and, more importantly, what it does **not**
> claim to be. For the full plan and gates, see
> [`public_prototype_plan.md`](public_prototype_plan.md) and
> [`v1_9_living_reference_world_plan.md`](v1_9_living_reference_world_plan.md).

## What v1.9.last is

A **lightweight public prototype**: a runnable, reproducible,
synthetic, jurisdiction-neutral demonstration of the FWE / JFWE
substrate. The headline artifact is the **multi-period living
reference world** — a deterministic four-quarter sweep over a
small synthetic fixture (3 firms, 2 investors, 2 banks) that
exercises corporate reporting, firm operating-pressure
assessment, heterogeneous attention, valuation refresh, bank
credit review, and review routines, all reconstructable from a
single append-only ledger.

## What is frozen

The v1.9.last freeze surface is intentionally narrow:

- **The CLI surface.** Three reproducible entry points:

  ```bash
  cd japan-financial-world
  python -m examples.reference_world.run_living_reference_world
  python -m examples.reference_world.run_living_reference_world --markdown
  python -m examples.reference_world.run_living_reference_world --manifest /tmp/fwe_living_world_manifest.json
  ```

  Two consecutive runs produce byte-identical output for each
  mode. The CLI is the only user-facing interface that v1.9.last
  promises.

- **The default fixture.** `3 firms × 2 investors × 2 banks ×
  4 periods` (quarterly). Every identifier follows the
  `*_reference_*` synthetic-only convention. Every numeric value
  is a round illustrative number, not a measurement.

- **The per-period flow.**
  ```
  corporate quarterly reporting
    → firm operating-pressure assessment    (v1.9.4 mechanism)
    → heterogeneous investor / bank attention
    → valuation refresh lite                (v1.9.5 mechanism)
    → bank credit review lite               (v1.9.7 mechanism)
    → investor / bank review routines
  ```

- **The reproducibility surface.** The v1.9.1 Markdown report and
  the v1.9.2 `living_world_manifest.v1` JSON manifest, both
  byte-deterministic. The manifest carries a structural SHA-256
  digest (`living_world_digest`), structural counts, the v1.9.1
  hard-boundary statement verbatim, a best-effort git probe,
  Python version, and platform.

- **The performance boundary.** The bounded per-period flow has
  loop shapes `O(P × F)` (corporate reporting), `O(P × F × n_exposures)`
  (pressure), `O(P × I × F)` (valuation), `O(P × B × F)` (credit
  review). These are demo-bounded products, allowed only because
  the fixture is fixed and synthetic. The discipline is documented
  in [`performance_boundary.md`](performance_boundary.md) and
  pinned by `tests/test_living_reference_world_performance_boundary.py`.

- **The test surface.** `1626 / 1626 passing`; `compileall` clean;
  `ruff check .` clean.

- **The disclaimers and the scope language.** The README, the
  reference-world README, the public-prototype plan, this summary,
  and `RELEASE_CHECKLIST.md` all agree on what the prototype is
  and is not.

## What v1.9.last does NOT claim

This list is normative. The freeze is conditional on every line
remaining true:

- **Not a forecast.** The prototype does not predict markets,
  prices, returns, defaults, or any real-world quantity.
- **Not investment advice.** Nothing the demo emits — code, ledger
  records, Markdown report, manifest — should be read as a market
  view, allocation suggestion, valuation opinion, or trade signal.
  Indirect framings ("a portfolio with exposure E would experience
  O") are equally out of scope.
- **No price formation.** No order matching, no microstructure,
  no price update events.
- **No trading.** Investor portfolios are static. No
  rebalancing, no allocation decisions, no order flow.
- **No lending decisions.** v1.9.7 produces *bank credit review
  notes*, not loan approvals, rejections, or originations. There
  is no underwriting, no covenant enforcement, no probability of
  default, no internal rating, no contract or constraint mutation.
  See `docs/performance_boundary.md` § "Semantic caveat — review
  is not origination".
- **No firm financial-statement updates.** v1.9.4 produces
  *operating-pressure assessment signals* — diagnostic, not
  bookkeeping. Firm financial state is not mutated by any
  mechanism.
- **No canonical valuation.** v1.9.5 produces *one valuer's
  opinionated synthetic claim* per `(investor, firm, period)`,
  carrying explicit `no_price_movement` / `no_investment_advice`
  / `synthetic_only` boundary flags. Valuations are not consensus
  estimates and are not authoritative.
- **No Japan calibration.** All identifiers are
  jurisdiction-neutral. BOJ / MUFG / GPIF / Toyota / TSE / Nikkei
  / Topix / JGB / etc. appear in the codebase only as forbidden
  tokens to scan against. v2 (Japan public-data calibration) and
  v3 (proprietary calibration) have not started.
- **No real data.** No public-data feeds wired, no paid feeds,
  no expert-interview content. Every fixture is a constant in
  the test or example file.
- **No scenarios.** No stress logic, no shock injection, no
  scenario branching, no policy reaction function.
- **No production-scale traversal.** The bounded all-pairs loops
  are explicitly demo-only. Future scaling must be sparse and
  gated on relationships / exposures / coverage; see the
  performance-boundary doc for the principles.
- **No native rewrite.** Python is adequate for v1.9. No C++ /
  Julia / Rust / GPU work is in scope for v1.9.x or v1.9.last.
- **No web UI.** The interface is the CLI. v1.9.last does not
  ship a hosted service, a tutorial site, or any presentation
  layer beyond the deterministic Markdown the CLI emits.

## How to verify

A reader can verify the v1.9.last freeze locally in a few minutes:

```bash
# from a clean clone
pip install -e ".[dev]"

cd japan-financial-world

# Tests + lint + compile
python -m pytest -q                          # expect: 1626 passed
python -m compileall world spaces tests examples   # expect: clean
ruff check .                                 # from the repo root; expect: clean

# Demo
python -m examples.reference_world.run_living_reference_world
python -m examples.reference_world.run_living_reference_world --markdown
python -m examples.reference_world.run_living_reference_world \
    --manifest /tmp/fwe_living_world_manifest.json

# Reproducibility — two runs into different paths, then diff
python -m examples.reference_world.run_living_reference_world \
    --manifest /tmp/fwe_living_world_manifest_a.json
python -m examples.reference_world.run_living_reference_world \
    --manifest /tmp/fwe_living_world_manifest_b.json
diff /tmp/fwe_living_world_manifest_a.json /tmp/fwe_living_world_manifest_b.json
# expect: zero differences in everything except the file path
```

The full release-readiness gate is in
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md) under
"Public prototype gate (v1.9.last)".

## Position in the version sequence

| Version | Scope | Status |
| ------- | ----- | ------ |
| v0.xx | Jurisdiction-neutral world kernel | Frozen at v0.16 |
| v1.0–v1.7 | Jurisdiction-neutral reference financial system | Frozen at v1.7 |
| v1.8.0 | Experiment harness + first public release | Tagged `v1.8-public-release` |
| v1.8.1–v1.8.16 | Endogenous activity infrastructure | Shipped |
| v1.9.0–v1.9.2 | Living reference world demo + report + replay/manifest | Shipped |
| v1.9.3 / v1.9.3.1 | Mechanism interface contract + hardening | Shipped |
| v1.9.4 | Reference firm operating-pressure assessment mechanism | Shipped |
| v1.9.5 | Reference valuation refresh lite mechanism | Shipped |
| v1.9.6 | Living-world mechanism integration | Shipped |
| v1.9.7 | Reference bank credit review lite mechanism | Shipped |
| v1.9.8 | Performance boundary / sparse traversal discipline | Shipped |
| **v1.9.last** | **Public prototype freeze** | **Shipped** |
| v2.0 | Japan public-data calibration design gate | Not started |
| v3.0 | Proprietary Japan calibration | Private |

## Next path after v1.9.last

v1.9.last is a **freeze**, not an end-state. After it, the next
non-trivial work falls into one of three buckets, none of which
is in v1.9 scope:

1. **More substrate behaviour, still synthetic** — additional
   mechanism families on the v1.9.3 interface (investor intent,
   market mechanism, macro-process), still review-only,
   still synthetic-only, still bounded fixture. These would
   extend v1.9 sideways, not forward.

2. **Sparse-traversal hardening** — replacing the `O(P × I × F)`
   and `O(P × B × F)` demo loops with relationship-, exposure-,
   or coverage-gated indexes so that the engine could in
   principle scale to non-toy populations. The principles are
   already pinned in [`performance_boundary.md`](performance_boundary.md);
   the implementation is post-v1.9 work.

3. **Calibration gate (v2)** — Japan public-data calibration
   design and per-source license review. v2 is what turns the
   substrate from a runnable demonstration into a calibrated
   model of a specific economy. v2 has not started; see
   [`v2_readiness_notes.md`](v2_readiness_notes.md).

None of those are part of v1.9.last's freeze surface.
v1.9.last is what it is: a small, deterministic, synthetic
demonstration that the substrate is trustworthy in its
mechanics, runnable from a clean clone in under a minute.
