# v1.2 Intraday Phase Design

This document is the design rationale for the v1.2 Intraday Phase
Scheduler. v1.2 adds a way to express *order within a day*: a
sequence of named phases (overnight → pre_open → opening_auction →
continuous_session → closing_auction → post_close) that tasks can be
declared against. v1.2 implements **scheduling infrastructure only**
— it does not introduce auction matching, order books, halt logic,
or any other market behavior.

For v1's overall design, see
[`v1_reference_system_design.md`](v1_reference_system_design.md).
For where v1.2 sits in the module sequence, see
[`v1_module_plan.md`](v1_module_plan.md). For the policy that v1.2
must satisfy, see [`v1_behavior_boundary.md`](v1_behavior_boundary.md).

## Why intraday phases exist

v0's smallest time unit was one calendar day. Every task that fires
on a given day fires once on that day, in deterministic but
phase-blind order. That was correct for v0 because no v0 task
needed to react to another v0 task's intraday timing — nothing
acted, so order within a day was inert.

v1 is different. As soon as v1.3 introduces reference institutional
behavior, intraday ordering becomes load-bearing. A market clearing
mechanism cannot fire at the same instant as an investor intent
emission and produce a coherent trace; the investor must speak
first. Earnings releases conventionally land *after* the market
close, with their effect priced in at the *next* open. A foreign
overseas shock arriving overnight should be visible to domestic
opening reactions but not to closing trades from the prior day.

The v0 calendar gives one slot per day. v1.2 splits that slot into
six ordered phases so the above ordering can be expressed without
inventing wall-clock times.

## Why this is not trading logic

v1.2 introduces *names for ordered slots*. It does not introduce:

- **Order books.** No `OrderBook` class. No bid / ask / depth.
- **Auction pricing.** A phase named `opening_auction` is just a
  label. No clearing math runs at that phase by default.
- **Continuous matching.** A phase named `continuous_session` is
  just a label. No book-walking, no last-trade computation.
- **Halts or circuit breakers.** No phase-state-machine. The
  scheduler iterates all six phases in order on every day; nothing
  causes a phase to be "skipped" or "interrupted".
- **Country-specific exchange hours.** The phase sequence is
  jurisdiction-neutral. v2 may calibrate phase boundaries to a
  specific Japanese exchange's calendar; v1.2 does not.

The v1.2 phase sequence is just six strings in a fixed order. The
behavior is added later, in v1.3 when ExchangeSpace gains a
reference matching mechanism — and even then, the matching itself
is a property of ExchangeSpace's task body, not of the phase
scheduler.

## Default phase sequence

```
overnight  →  pre_open  →  opening_auction  →
continuous_session  →  closing_auction  →  post_close
```

The intuition behind each phase, expressed neutrally:

- **overnight** — the slot before the day's domestic activity
  begins. Conventionally where overseas-market observations land
  and where overnight settlements reconcile.
- **pre_open** — preparation slot before the opening auction.
  Conventionally where pre-market signals (earnings, regulatory
  announcements that arrived overnight) become visible to
  domestic actors.
- **opening_auction** — the slot when the day's first reference
  prices are formed. v1.2 declares the slot; v1.3 will add the
  reference matching mechanism that runs in it.
- **continuous_session** — the bulk of the trading day in real
  exchanges. v1.2 declares the slot; future modules add the
  behaviors that consume it.
- **closing_auction** — the slot when the day's closing reference
  prices are set. Conventionally where index rebalances are
  measured, where MOC orders match.
- **post_close** — the slot after the close. Conventionally where
  earnings are released (US convention) and where end-of-day
  settlement occurs.

Each phase's identifier is a free-form string; v1.2 ships these six
as `PhaseSequence.default_phases()`. Custom sequences can be
constructed for tests and future extensions.

## Examples of future use

These are the *intended* future uses of phases — none of them are
implemented in v1.2. Each becomes feasible because phases give a
place to declare ordering; the actual behavior arrives in later
milestones.

### Earnings release in `post_close`

A future v1.3 CorporateSpace might emit earnings signals at
`post_close` so that the next day's `pre_open` is the first phase
where investors can react. This separates "the firm announced" from
"the market reacted" cleanly across calendar boundaries.

### Foreign market shock in `overnight`

A future v1.4 ExternalSpace process can publish observations of
foreign markets at `overnight`, so that domestic opening at
`opening_auction` is the first slot that can read them. The
sequence makes "the world moved while we slept" expressible without
hand-rolled timestamps.

### Opening reaction in `opening_auction`

A future v1.3 InvestorSpace can place opening intents at
`pre_open`, the ExchangeSpace clearing reference can match at
`opening_auction`, and PriceBook updates land before
`continuous_session`. v1.2 only declares the slots; v1.3 wires the
behaviors.

### Continuous trading in `continuous_session`

The bulk of v1.3's reference matching will live here. The phase
exists; the matching engine doesn't.

### Index rebalance in `closing_auction`

A future module could schedule index rebalancing tasks at
`closing_auction`, so prices used for the rebalance reflect the
day's final reference. v1.2 makes the slot reachable; the rebalance
logic is later work.

## Backward compatibility with v0

The v1.2 implementation is purely additive over v0:

- The `Phase` enum gains six new values. The existing
  `Phase.MAIN` continues to be the default for any task that
  doesn't declare a phase.
- `_sorted_tasks` updates its `phase_rank` table to include the new
  values. `Phase.MAIN` is given the lowest rank so v0 tests, which
  use only `MAIN`, see no change in deterministic ordering.
- The kernel's `tick()` and `run()` methods are unchanged. They
  continue to fire all due tasks regardless of declared phase. v0
  spaces — all of which use `Phase.MAIN` — continue to work
  exactly as they did before v1.2.
- New methods (`iter_intraday_phases`, `run_day_with_phases`,
  `run_with_phases`) are added to the kernel. They are *opt-in*:
  callers who don't use them see no change.

The two paths (v0 phase-blind, v1.2 phase-aware) are intentionally
separate. Mixing them on the same day would advance the clock
twice; the choice is "use one or the other per day", not "use
both".

**This rule is enforced (v1.2.1).** The kernel records which mode
processed each simulation date in an internal ``_run_modes`` map. A
call that would process a date already processed in the other mode
raises ``RuntimeError``. The natural advance-clock semantics means
the guard never fires during ordinary sequential use — it only
fires when a caller manually rewinds the clock or otherwise revisits
a date that has already been claimed. The guard resets naturally
because each entry is keyed by ``simulation_date``: once the clock
moves to a new date, the new date carries no mode and either path
can claim it.

## Where Phase.MAIN fits

`Phase.MAIN` is the v0 default. Tasks that declare no phase get
`MAIN` automatically. v1.2's `run_day_with_phases` deliberately
**excludes** `MAIN` tasks from intraday dispatch. There are two
reasons:

1. v0 tasks were written without phase semantics. Forcing them
   into one of the six intraday phases would be an arbitrary
   choice and would tie v0 spaces' dispatch order to a v1
   convention.
2. v1.2 should let callers register tasks at exactly the phase
   they care about. If they want a task to fire phase-blind, they
   either keep using `Phase.MAIN` and run via `kernel.tick()`, or
   register the task at one of the six intraday phases explicitly.

This means the eight v0 spaces (Corporate, Banking, Investors,
Exchange, Real Estate, Information, Policy, External) continue to
declare `MAIN` tasks and continue to be invoked by `kernel.tick()`
unchanged. v1.3 will add new tasks in those spaces declared at
specific intraday phases.

## What v1.2 ships

In scope:

- `world/phases.py` with `IntradayPhaseSpec` and `PhaseSequence`
  (`default_phases`, `list_phases`, `get_phase`, `next_phase`,
  `is_first_phase`, `is_last_phase`, `to_dict`).
- Six new values on the existing `Phase` enum (overnight,
  pre_open, opening_auction, continuous_session, closing_auction,
  post_close) plus an updated `phase_rank` table.
- Kernel methods: `iter_intraday_phases`, `run_day_with_phases`,
  `run_with_phases(days)`. All optional.
- Reuse of the existing `task_executed` ledger record type, with
  an additional `phase` key in the payload when a task fires
  through `run_day_with_phases`. No new behavior-specific record
  types.
- Tests covering the six-phase default sequence, navigation
  helpers, custom sequences, phase-aware daily / monthly /
  quarterly dispatch, deterministic ordering of multiple tasks in
  the same phase, no-mutation guarantee, and v0 backward
  compatibility.

## What v1.2 does not ship

Out of scope:

- Order books or order matching logic.
- Auction pricing or any reference clearing mechanism.
- Price impact estimation.
- Country-specific exchange hours, holiday calendars, or session
  rules.
- Halts, circuit breakers, kill switches.
- Index rebalancing logic.
- Trade reporting, fee computation, or settlement engines.
- Phase-specific behavior in any v0 space (Corporate / Banking /
  Investors / Exchange / Real Estate / Information / Policy /
  External). v0 spaces continue to declare `Phase.MAIN`.
- Cross-day phases (e.g., a settlement phase that spans the
  Saturday-Sunday gap).
- Sub-second or wall-clock-aware phases.
- Any Japan-specific calibration.

These belong to later milestones. v1.3 is where actual phase-aware
behavior begins.

## Why v1.2 is non-behavioral

v1.2 satisfies the v1 behavior boundary contract from
[`v1_behavior_boundary.md`](v1_behavior_boundary.md) trivially:

- It introduces *no decision*. The phase dispatcher iterates a
  fixed sequence and fires tasks; it does not read state to choose
  what to do.
- It mutates *no source-of-truth book*. The phase scheduler does
  not touch ownership, contracts, prices, constraints, signals,
  or valuations.
- It writes only to the ledger, and only via the existing
  `task_executed` record type. The only addition is a `phase` key
  in the payload — a documentation field, not a behavior.

v1.2 is structural infrastructure for the behavior that v1.3 will
introduce. By itself it adds no economic content.

## v1.2 success criteria

v1.2 is complete when **all** of the following hold:

1. `IntradayPhaseSpec` exists with `phase_id`, `order`, `label`,
   `metadata`, and is immutable.
2. `PhaseSequence` provides `default_phases`, `list_phases`,
   `get_phase`, `next_phase`, `is_first_phase`, `is_last_phase`,
   and `to_dict`.
3. The default sequence is exactly the six phases in the
   documented order.
4. The `Phase` enum carries the six intraday values plus the
   legacy `MAIN`.
5. `_sorted_tasks` ranks all phases consistently; v0 sorting
   tests continue to pass without modification.
6. `WorldKernel` exposes `iter_intraday_phases`,
   `run_day_with_phases`, and `run_with_phases` as optional
   additive methods.
7. `run_day_with_phases` advances the clock once per day and
   emits a month-end snapshot when applicable, mirroring
   `tick()`'s clock and snapshot semantics.
8. Phase-aware daily / monthly / quarterly tasks fire the correct
   number of times at their declared phase.
9. Multiple tasks at the same phase execute in the same
   deterministic order as v0's `_sorted_tasks` rule (phase rank
   first, then frequency, then order, then space, then name).
10. No source-of-truth book is mutated by the phase dispatcher.
11. v0 `tick()` / `run()` behavior is unchanged.
12. All previous tests (444 v0 + 34 v1.1 = 478) continue to pass
    without modification.
