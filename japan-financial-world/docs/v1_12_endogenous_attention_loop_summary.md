# v1.12.last — Endogenous Attention Loop Summary

> **Status:** v1.12.last freeze. This document is the single-page,
> reader-facing summary of what the v1.12 freeze ships and, more
> importantly, what it does **not** claim to be. For the full
> technical narrative see `docs/world_model.md` §80–§91.
>
> v1.12.last sits **alongside** the v1.9.last public prototype
> (see [`v1_9_public_prototype_summary.md`](v1_9_public_prototype_summary.md))
> — v1.9.last froze the **first runnable, reproducible synthetic
> living world**; v1.12.last freezes the **first endogenous
> attention-feedback loop** layered on top of that substrate.

## In one sentence

**v1.12 turns FWE from a mostly feed-forward audit substrate into
a minimal endogenous attention-feedback system** — the first
public FWE milestone where what an actor *saw and concluded* in
period N changes what it *attends to* in period N+1, under a
finite synthetic attention budget with deterministic decay,
crowding, and saturation.

## What v1.12.last is

A **deterministic, replayable, jurisdiction-neutral, synthetic
endogenous attention-feedback loop** layered on the v1.9.last
runnable substrate:

```
market environment
  → firm latent state
    → selected evidence
      → investor intent / valuation lite / bank credit review lite
        → attention feedback
          → next-period selected evidence
            → budget / decay / crowding / saturation
```

Every arrow is implemented; every step is observable in the
ledger; every step is bounded by the v1.12.9 attention budget;
every step is preserved bit-for-bit on two consecutive runs.

## What is frozen

The v1.12.last freeze surface is intentionally narrow:

- **The loop shape.** Eight phases per period, in this order:

  1. corporate quarterly reporting (v1.8.7)
  2. firm operating-pressure assessment (v1.9.4)
  3. industry demand condition (v1.10.4)
  4. capital-market condition (v1.11.0)
  5. capital-market readout (v1.11.1)
  6. **market environment state** (v1.12.2)
  7. **firm financial latent state** (v1.12.0)
  8. heterogeneous investor / bank attention (v1.8.11/12)
  9. **memory selection** (v1.12.8 + v1.12.9 budget)
  10. **attention-conditioned valuation lite** (v1.12.7 wires v1.12.5)
  11. **attention-conditioned bank credit review lite** (v1.12.7 wires v1.12.6)
  12. portfolio-company dialogue / escalation / corporate response (v1.10.2 / v1.10.3)
  13. **attention-conditioned investor intent** (v1.12.4)
  14. investor / bank review routines (v1.8.13)
  15. **attention feedback** (v1.12.8 + v1.12.9 decay/crowding)

- **The CLI surface.** The same v1.9.last entry points, plus
  the v1.11.2 market-regime preset flag (`--market-regime`):

  ```bash
  cd japan-financial-world
  python -m examples.reference_world.run_living_reference_world
  python -m examples.reference_world.run_living_reference_world --markdown
  python -m examples.reference_world.run_living_reference_world --manifest /tmp/lw.json
  python -m examples.reference_world.run_living_reference_world --market-regime constructive
  python -m examples.reference_world.run_living_reference_world --market-regime constrained
  python -m examples.reference_world.run_living_reference_world --market-regime tightening
  ```

  Two consecutive runs of the same command produce byte-identical
  output. The default-fixture `living_world_digest` is
  pinned in tests at the value documented in `world_model.md` §91.

- **The performance boundary.** Per-period record count moves
  from 37 (v1.9.last) to 79 (period 0) / 81 (period 1+) under
  v1.12.last. Per-run record window widens from `[148, 180]` to
  `[316, 364]`. No new per-period dense traversals were added;
  every phase is `O(P × {actors, firms, markets, ...})` linear in
  the same way v1.9.x was.

- **The vocabulary surface.**
  - 13 attention focus labels: `firm_state`, `market_environment`,
    `market_access`, `funding`, `liquidity`, `credit`,
    `refinancing_window`, `valuation`, `engagement`, `dialogue`,
    `escalation`, `stewardship`, `memory`.
  - 6 attention trigger labels: `risk_intent_observed`,
    `engagement_intent_observed`, `valuation_confidence_low`,
    `liquidity_or_refinancing_credit_review`,
    `restrictive_market_observed`, `routine_observed`.
  - 9 environment regime labels (v1.12.2): `liquidity_regime` /
    `volatility_regime` / `credit_regime` / `funding_regime` /
    `risk_appetite_regime` / `rate_environment` /
    `refinancing_window` / `equity_valuation_regime` /
    `overall_market_access`.
  - 7 watch labels (v1.12.6): `routine_monitoring` /
    `heightened_review` / `liquidity_watch` /
    `refinancing_watch` / `collateral_watch` /
    `market_access_watch` / `information_gap_review`.
  - 7 investor-intent direction labels (v1.12.1):
    `hold_review` / `increase_watch` / `decrease_confidence` /
    `engagement_watch` / `risk_flag_watch` /
    `deepen_due_diligence` / `coverage_review`.

  Closed sets pinned in tests against `_FORBIDDEN_TOKENS` —
  none contains `buy`, `sell`, `rating`, `pd`, `lgd`, `ead`,
  `default`, `recommendation`, `advice`, or any other binding /
  jurisdiction-loaded token.

## What changed across v1.12

| Sub-milestone | Scope | What it shipped |
| --- | --- | --- |
| v1.12.0 | Firm financial latent state | First time-crossing endogenous state; six bounded synthetic pressure / readiness scalars in `[0, 1]` chained period-over-period via `previous_state_id`. |
| v1.12.1 | Investor intent signal | Pre-action review-posture record: `hold_review` / `risk_flag_watch` / `engagement_watch` / `decrease_confidence` / `deepen_due_diligence` / `coverage_review`. Non-binding labels only. |
| v1.12.2 | Market environment state | Nine compact regime labels per period derived from v1.11.0 conditions + v1.11.1 readout. |
| v1.12.3 | EvidenceResolver / ActorContextFrame | Read-only attention-bottleneck substrate. Eleven evidence buckets resolved by id-prefix dispatch. |
| v1.12.4 | Attention-conditioned investor intent | First mechanism-level use of attention — investor intent classified on resolved frame ids only. |
| v1.12.5 | Attention-conditioned valuation lite | Helper-level + tests; valuer's selected evidence conditions estimated_value + confidence. |
| v1.12.6 | Attention-conditioned bank credit review lite | Helper-level + tests; bank's selected evidence conditions a deterministic `watch_label`. |
| v1.12.7 | Living-world integration | Orchestrator switches to v1.12.5 / v1.12.6 helpers — three mechanisms attention-conditioned end-to-end. |
| v1.12.8 | Next-period attention feedback | First cross-period feedback loop: prior-period outcomes → next-period focus_labels → memory `SelectedObservationSet` widens period N+1's selected evidence. |
| v1.12.9 | Attention budget / decay / saturation | Finite synthetic budget: `per_dimension_budget=3`, `decay_horizon=2`, `max_selected_refs=12`; deterministic decay, crowding, drop-oldest. |
| **v1.12.last** | **Endogenous attention loop freeze** | **This document.** Documentation, regime-comparison demo, release checklist. No new economic behavior. |

## Banker- / asset-manager-facing reading

**This engine does not predict prices.** It does not recommend
trades, lending decisions, or portfolio allocations. It contains
no calibrated probability of default, credit rating, expected
return, target price, or any binding signal of any kind.

What FWE v1.12 *does* show:

- How an information condition (the market environment regime)
  propagates **into actor-specific attention** through a documented
  rule set.
- How attention then conditions actor-specific **review posture
  records** — the investor's intent direction, the bank's
  watch label, the valuer's `estimated_value` / `confidence`
  pair — without any of these crossing into binding action.
- How next-period attention is **shaped by prior-period
  outcomes** — and how that shaping is bounded, decaying, and
  saturating, not unbounded accumulation.
- How the entire flow is **reconstructable from a single
  append-only ledger** — every step has a record id, every record
  has a deterministic payload, and two runs produce byte-identical
  ledgers.

If you are reading this as a banker, asset manager, fund
allocator, or financial supervisor: treat the output as a
**documentation of an information-and-attention process**, not as
a market view. The engine is a substrate for thinking about
*why* an actor would attend to one piece of evidence over another
under regime stress; it is **not** a forecasting tool, **not** a
pricing model, **not** a capital-allocation tool, and **not** a
research-coverage replacement.

## Regime-comparison demo

The simplest way to see the v1.12 endogenous loop in action is
to run the same fixture under three different market regimes and
diff the outputs:

```bash
cd japan-financial-world

python -m examples.reference_world.run_living_reference_world \
    --market-regime constructive --markdown

python -m examples.reference_world.run_living_reference_world \
    --market-regime constrained --markdown

python -m examples.reference_world.run_living_reference_world \
    --market-regime tightening --markdown
```

What to look for, period by period, between the three regimes:

- **Firm financial latent state trajectory**
  (`world_model.md` §80) — under `constructive`, the six
  pressure / readiness scalars decay below the 0.5 baseline;
  under `constrained` and `tightening`, they accumulate above
  baseline. Watch `funding_need_intensity` and
  `market_access_pressure` in particular.
- **Investor intent direction histogram** (§81 / §85) — the
  default `constructive` regime concentrates intents on
  `engagement_watch`; `constrained` and `tightening` shift the
  histogram toward `risk_flag_watch` and `deepen_due_diligence`.
- **Valuation confidence** (§86) — the v1.12.5
  attention-conditioned helper applies a small documented
  synthetic delta on top of the v1.9.5 pressure-haircut formula.
  Under `constructive` regimes, valuations land at higher
  `confidence`; under `constrained` regimes, lower.
- **Bank credit review watch labels** (§88) — under
  `constructive`, every review lands on `routine_monitoring`;
  under `constrained`, the histogram includes `liquidity_watch`,
  `refinancing_watch`, `market_access_watch`, or
  `information_gap_review` depending on which firm states / market
  environments / valuations the bank actually selected.
- **Attention focus labels across periods** (§90) — period 0's
  attention state focus_labels reflect period 0's outcomes;
  period 1's reflect the **mix** (current period + decayed
  inheritance from period 0); under sustained regime, period 2+
  drops the unreinforced focus labels via the `decay_horizon=2`
  rule.
- **Memory-selected evidence and budget effects** (§91) — every
  memory `SelectedObservationSet` is bounded at
  `max_selected_refs=12` and `per_dimension_budget=3`. The
  `selected_refs` count never grows monotonically; the
  composition swaps as triggers swap.

Two runs of the same regime produce byte-identical Markdown
reports and identical `living_world_digest` digests; two runs
across regimes produce different reports and different digests
deterministically.

## Hard boundary (binding)

v1.12.last does **not**:

- form, observe, or move any **price**;
- match, route, clear, or settle any **order or trade**;
- decide any **lending action** — no loan origination, no
  approval / rejection, no covenant enforcement, no contract or
  constraint mutation, no default declaration;
- compute any **internal rating**, probability of default (PD),
  loss given default (LGD), exposure at default (EAD), or any
  other regulator-recognised credit measure;
- compute any **target price**, expected return, recommendation,
  investment advice, target weight, overweight / underweight,
  rebalance, or portfolio allocation;
- update any **firm financial statement** — no revenue, EBITDA,
  net income, cash balance, debt amount, or accounting value
  appears anywhere on a v1.12 record;
- ingest any **real market, audit, broker, lender, regulator,
  or vendor data**;
- apply any **Japan-specific calibration** — no BOJ, FSA, JPX,
  TSE, MUFG, SMBC, Mizuho, JGB, or any other real-system
  identifier appears in any public-FWE record. Japan calibration
  is private JFWE (v2 / v3); see
  [`public_private_boundary.md`](public_private_boundary.md);
- dispatch to an **LLM agent** or any external solver. The
  attention state with budget + decay is the *substrate* a
  future LLM-agent step can read, but v1.12 itself is not an
  LLM call;
- attach any **calibrated behavior probability** or stochastic
  forgetting — the decay rule is integer-counted and
  weight-deterministic.

## Anti-overclaiming language (binding)

**FWE v1.12 is not a market simulator.** It does not simulate
prices, trades, lending decisions, or capital flows. It does not
forecast anything.

**FWE v1.12 is not a research model.** It does not consume real
data, it does not produce real recommendations, and it does not
substitute for any analyst, bank, supervisor, or regulator's
judgement.

**FWE v1.12 is a synthetic, deterministic, replayable
financial-world substrate with a minimal endogenous
attention-feedback loop.** That is the entire claim.

If a reader (banker, asset manager, supervisor, journalist,
investor) reads any of the v1.12 output and concludes it is a
market view or a calibrated estimate, that reading is wrong; the
output is documentation of an attention process, never a market
view.

## Cross-references

- **The v1.9.last public prototype** —
  [`v1_9_public_prototype_summary.md`](v1_9_public_prototype_summary.md):
  the first runnable reproducible substrate. v1.12 builds on
  this; the v1.9.last freeze is unchanged.
- **The world model** — [`world_model.md`](world_model.md)
  §80–§91 for full v1.12 technical narrative.
- **The behavior boundary** —
  [`v1_behavior_boundary.md`](v1_behavior_boundary.md): the v1
  no-economic-behavior carve-out.
- **The public / private boundary** —
  [`public_private_boundary.md`](public_private_boundary.md):
  what is public vs private JFWE.
- **The performance boundary** —
  [`performance_boundary.md`](performance_boundary.md): per-period
  loop shapes + per-run budget + sparse gating principles.
- **The release checklist** —
  [`../../RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md):
  required gates for tagging a v1.12 public release.
- **The advanced valuation protocol design note** —
  [`v1_valuation_protocol_comps_purpose_separation.md`](v1_valuation_protocol_comps_purpose_separation.md):
  docs-only design for advanced-actor-only purpose-separated
  comparable-set discipline.
- **The generic central-bank settlement design note** —
  [`v1_13_generic_central_bank_settlement_design.md`](v1_13_generic_central_bank_settlement_design.md):
  docs-only design for the v1.13 settlement substrate vocabulary.

## Position in the v1 sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.8.16 | Endogenous activity stack freeze | Shipped |
| v1.9.last | First public prototype freeze (runnable substrate) | Shipped |
| v1.10.last | Public engagement layer freeze (docs-only) | Planned |
| v1.11.x | Capital-market surface stack | Shipped (§77 → §79) |
| v1.12.0 → v1.12.9 | Endogenous attention-feedback stack | Shipped (§80 → §91) |
| **v1.12.last** | **Endogenous attention loop freeze** (docs-only). | **Shipped (this document)** |
| v1.x advanced | Valuation protocol — comps purpose separation | Shipped (docs-only, §84) |
| v1.13.0 | Generic central bank settlement infrastructure design | Shipped (docs-only, §87) |
| v1.13.1 → v1.13.5 | Settlement substrate code | Planned |
| v2.0 | Japan public-data calibration design gate | Not started |

## Summary

- v1.12 closes the endogenous attention-feedback loop, period to
  period, end to end, in the default living reference world demo.
- The loop is **synthetic, deterministic, non-binding, replayable**.
  No price, no trade, no recommendation, no rating, no real data,
  no Japan calibration, no LLM execution.
- Attention is **scarce, budgeted, decaying, saturating**. New
  focus crowds out old; sustained regime reinforces; sustained
  silence drops.
- The headline test pin (`test_crowding_new_focus_replaces_decayed_focus_in_memory`)
  shows new risk focus crowding out old engagement focus over
  three periods.
- v1.12.last freezes this surface for documentation, demo, and
  banker / asset-manager-facing reading. Nothing in v1.12 should
  be read as a market view; everything in v1.12 should be read
  as a documentation of an attention process.
