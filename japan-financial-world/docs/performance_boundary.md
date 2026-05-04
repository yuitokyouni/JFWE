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

## Current loop shapes (v1.15.5)

The following table describes the loop shape of each phase
inside `world/reference_living_world.run_living_reference_world`.
`P` = number of periods, `F` = number of firms, `I` = number
of investors, `B` = number of banks, `N` = number of unique
industries derived from the firm → industry map, `M` = number of
synthetic markets in the orchestrator's market-condition spec
set, `K` = capital-market readouts per period (always 1 in
v1.11.1+). The `n_obs` and `n_exposures` factors are bounded by
the fixture's variable count (currently 4) and per-firm exposure
count (currently 2–3 each).

| Phase                                                    | Loop shape                                | v1.13.last default     |
| -------------------------------------------------------- | ----------------------------------------- | ---------------------- |
| Corporate quarterly reporting                            | `O(P × F)`                                | 4 × 3 = 12 reports     |
| Firm pressure assessment (v1.9.4)                        | `O(P × F × n_exposures)`                  | 4 × 3 × ~2.5 = 30 pass |
| Industry demand condition (v1.10.4)                      | `O(P × N)`                                | 4 × 3 = 12 conditions  |
| Capital-market condition (v1.11.0)                       | `O(P × M)`                                | 4 × 5 = 20 conditions  |
| Capital-market readout (v1.11.1)                         | `O(P × K)`                                | 4 × 1 = 4 readouts     |
| Market environment state (v1.12.2)                       | `O(P)`                                    | 4 × 1 = 4 states       |
| Firm financial latent state (v1.12.0)                    | `O(P × F)`                                | 4 × 3 = 12 states      |
| Menu construction (per actor)                            | `O(P × (I+B) × n_relevant_observations)`  | 4 × 4 × ~4 = 64 pass   |
| Observation set selection                                | `O(P × (I+B))`                            | 4 × 4 = 16 selections  |
| Memory selection (v1.12.8 + v1.12.9 budget)              | `O((P-1) × (I+B))` (period 1+; budgeted)  | 3 × 2 = 6 inv-memory   |
| Valuation refresh lite (v1.12.7 wires v1.12.5)           | `O(P × I × F)`                            | 4 × 2 × 3 = 24 valns   |
| Interbank liquidity state (v1.13.5)                      | `O(P × B)`                                | 4 × 2 = 8 states       |
| Bank credit review lite (v1.12.7 wires v1.12.6)          | `O(P × B × F)`                            | 4 × 2 × 3 = 24 reviews |
| Portfolio-company dialogue (v1.10.2)                     | `O(P × I × F)`                            | 4 × 2 × 3 = 24 dialog. |
| Investor escalation candidate (v1.10.3, investor)        | `O(P × I × F)`                            | 4 × 2 × 3 = 24 cands.  |
| Investor intent signal (v1.12.4 wires v1.12.1)           | `O(P × I × F)`                            | 4 × 2 × 3 = 24 intents |
| Corporate strategic response candidate (v1.10.3, corp.)  | `O(P × F)`                                | 4 × 3 = 12 cands.      |
| Review routines                                          | `O(P × (I+B))`                            | 4 × 4 = 16 reviews     |
| Attention feedback (v1.12.8)                             | `O(P × (I+B))`                            | 4 × 4 = 16 states+fb×2 |
| Corporate financing need (v1.14.5)                       | `O(P × F)`                                | 4 × 3 = 12 needs       |
| Funding option candidate (v1.14.5)                       | `O(P × F × 2)`                            | 4 × 3 × 2 = 24 options |
| Capital structure review candidate (v1.14.5)             | `O(P × F)`                                | 4 × 3 = 12 reviews     |
| Corporate financing path (v1.14.5)                       | `O(P × F)`                                | 4 × 3 = 12 paths       |
| Investor market intent (v1.15.5)                         | `O(P × I × F)`                            | 4 × 2 × 3 = 24 intents |
| Aggregated market interest (v1.15.5)                     | `O(P × F)`                                | 4 × 3 = 12 aggregated  |
| Indicative market pressure (v1.15.5)                     | `O(P × F)`                                | 4 × 3 = 12 pressure    |
| Reporting / replay / manifest                            | `O(R)` over emitted ledger records        | ~460 records           |

Per-period record-count breakdown (default fixture, v1.13.last):

```
2 × F                  corporate run + corporate signal              =  6
F                      firm pressure signal                          =  3
N                      industry demand condition (v1.10.4)           =  3
M                      capital-market condition (v1.11.0)            =  5
K                      capital-market readout (v1.11.1)              =  1
1                      market environment state (v1.12.2)            =  1
F                      firm financial latent state (v1.12.0)         =  3
2 × (I + B)            menu + selection                              =  8
I × F                  valuation                                     =  6
B                      interbank liquidity state (v1.13.5)           =  2
B × F                  bank credit review note                       =  6
I × F                  portfolio-company dialogue (v1.10.2)          =  6
I × F                  investor escalation candidate (v1.10.3, inv.) =  6
I × F                  investor intent signal (v1.12.1)              =  6
F                      corporate strategic response candidate        =  3
2 × (I + B)            review_run + review_signal                    =  8
2 × (I + B)            attention state + feedback (v1.12.8)          =  8
F                      corporate financing need (v1.14.5)            =  3
2 × F                  funding option candidate (v1.14.5)            =  6
F                      capital structure review candidate (v1.14.5)  =  3
F                      corporate financing path (v1.14.5)            =  3
I × F                  investor market intent (v1.15.5)              =  6
F                      aggregated market interest (v1.15.5)          =  3
F                      indicative market pressure (v1.15.5)          =  3
                                                            total   =108  (period 0)
+ (I + B) memory selections from period 1+ (budgeted)             ≈ +2  (period 1+)
                                                            total   =110  (period 1+)
× 4 periods (period 0: 108; periods 1–3: 110)                      = 438
+ ~14 one-off setup (interactions, routines, profiles)
+   4 one-off setup (stewardship themes, v1.10.5)
+   4 one-off setup (v1.15.5: 1 venue + F = 3 securities)
                                                          ≈ ~460 records
```

The v1.13 generic settlement substrate (v1.13.1 settlement
accounts, v1.13.2 payment instructions + settlement events,
v1.13.3 interbank-liquidity state, v1.13.4 central-bank
operation + collateral-eligibility signals) is **storage-only**;
v1.13.1, v1.13.2, and v1.13.4 are not yet wired into the
default living-reference-world per-period sweep. Only the
v1.13.5 `interbank_liquidity_state` is on the per-period path
(one record per bank per period).

The v1.14 corporate-financing chain (v1.14.1 needs, v1.14.2
funding options, v1.14.3 capital-structure reviews, v1.14.4
financing paths) was storage-only through v1.14.4. **v1.14.5 is
the first living-world integration** — the four layers are now
on the per-period path (1 need + 2 options + 1 capital-structure
review + 1 financing path per firm per period; bounded by
`P × F`, never an `I × F × option` or `B × F × option` dense
loop). Storage / audit / graph-linking only — no execution, no
loan approval, no security issuance, no underwriting, no
syndication, no pricing, no recommendation, no real leverage /
D/E / WACC.

The v1.15 securities-market-intent chain (v1.15.1 listed
securities + venues, v1.15.2 investor market intents, v1.15.3
aggregated market interest, v1.15.4 indicative market pressure)
was storage / helper-only through v1.15.4. **v1.15.5 is the first
living-world integration** — the four layers are now on the
per-period path: 1 venue + `F` securities at setup, then per
period `I × F` investor market intents + `F` aggregated-interest
records + `F` indicative-pressure records (12 records per period
in the default fixture; bounded by `P × I × F + 2 × P × F`,
never `P × I × F × venue` or `P × I × F × option`). Storage /
aggregation only — no order submission, no order book, no
matching, no execution, no clearing, no settlement, no quote
dissemination, no bid / ask, no price update, no `PriceBook`
mutation, no target price, no expected return, no recommendation.

Of the loops above:

- The **bounded all-pairs** loops are the valuation
  `O(P × I × F)`, the bank credit review `O(P × B × F)`, the
  portfolio-company dialogue `O(P × I × F)`, and the investor
  escalation candidate `O(P × I × F)`. These four are the only
  bounded all-pairs traversals; v1.10.5 deliberately did **not**
  add a new dense shape (it reuses the existing `I × F` shape
  for both engagement records). v1.14.5 also did **not** add a
  new dense shape — the financing chain is `O(P × F)` per
  layer, never `O(P × F × I)` or `O(P × F × B × option_count)`.
- All other loops are linear in the actor, firm, or industry
  count.

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
`tests/test_living_reference_world_performance_boundary.py`.
**Note on units:** the budget pinned below is a *per-run total*
(across all four periods), not a per-period count. At v1.12.2
the per-period count is 71 records (37 v1.9.x + 18 v1.10.5
+ 5 v1.11.0 capital-market + 1 v1.11.1 capital-market readout
+ 1 v1.12.2 market environment state + 3 v1.12.0 firm financial
latent state + 6 v1.12.1 investor intent); the per-run total is
`71 × 4 = 284`, plus an infrastructure allowance for one-off
setup records (14 v1.9.x infra + 4 v1.10.5 stewardship themes
+ headroom; v1.11.0 / v1.11.1 / v1.11.2 / v1.12.0 / v1.12.1 /
v1.12.2 add no new setup records).

- per-period record formula equals
  `2F + F + N + M + K + 1 + F + 2(I+B) + IF + BF + IF + IF + IF + F + 2(I+B) = 71`
  for the default fixture (with `N = 3` industries,
  `M = 5` markets, `K = 1` capital-market readout per period,
  one v1.12.2 market environment state per period, one v1.12.0
  firm-state record per firm per period, and one v1.12.1
  investor-intent record per (investor, firm) pair per period),
- per-run total record count for a default 4-period sweep sits
  in `[284, 316]` — i.e. exactly `formula × periods` at the
  lower edge plus up to a 32-record infrastructure allowance,
- the valuation count for the run equals exactly `P × I × F`,
- the bank credit review count for the run equals exactly
  `P × B × F`,
- the firm pressure signal count for the run equals exactly
  `P × F`,
- the industry demand condition count for the run equals
  exactly `P × N`,
- the capital-market condition count for the run equals
  exactly `P × M` (v1.11.0),
- the capital-market readout count for the run equals exactly
  `P × K` (v1.11.1; default `K = 1`),
- the firm financial latent state count for the run equals
  exactly `P × F` (v1.12.0),
- the investor intent signal count for the run equals exactly
  `P × I × F` (v1.12.1),
- the market environment state count for the run equals exactly
  `P × 1 = P` (v1.12.2),
- the dialogue count for the run equals exactly `P × I × F`,
- the investor escalation candidate count for the run equals
  exactly `P × I × F`,
- the corporate strategic response candidate count for the run
  equals exactly `P × F`,
- the stewardship theme count for the run equals exactly
  `I × T` where `T` is the number of theme types (default 2),
- no order, price-update, contract-mutation, ownership-
  transfer, covenant-breach, institution-action-recorded, or
  firm-state-added records appear in the ledger,
- no v1.10 ledger payload carries a forecast / revenue /
  market-size / vote_cast / proposal_filed / campaign_executed /
  exit_executed / letter_sent / buyback_executed /
  dividend_changed / divestment_executed / merger_executed /
  board_change_executed / disclosure_filed / transcript /
  content / notes / minutes / attendees key,
- no warnings or errors appear in the ledger on the default
  sweep.

If any of those pins fails, the demo has either grown the
fixture (intentional but undocumented) or gained a hidden
quadratic loop (unintended).

## v1.19.last freeze pins

The v1.19.last freeze (docs-only on top of the v1.19.0 → v1.19.4
code freezes plus the v1.19.3.1 reconciliation follow-up)
closes the v1.19 sequence as the **first FWE milestone where a
user can generate deterministic local run bundles from CLI and
inspect them in the static workbench, including
monthly_reference runs** — without backend execution, prices,
trades, real data, or Japan calibration.

**Default `quarterly_default` sweep (unchanged from
v1.18.last):**

- per-period record count: **108** (period 0) / **110** (periods 1+),
- per-run window: **`[432, 480]`**,
- default 4-period sweep total: **460 records**,
- integration-test `living_world_digest`:
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**,
- pinned across the entire v1.19 sequence by per-book trip-wire
  tests at v1.19.1 (`tests/test_run_export.py::test_constructing_bundles_does_not_move_default_living_world_digest`),
  v1.19.2 (`tests/test_run_export_cli.py::test_default_fixture_living_world_digest_unchanged_after_cli`),
  v1.19.3 (`tests/test_information_release.py::test_empty_information_releases_does_not_move_default_living_world_digest`
  and `tests/test_living_reference_world.py::test_v1_19_3_quarterly_default_digest_unchanged`),
  v1.19.3.1 (`tests/test_run_export_cli.py::test_v1_19_3_1_monthly_reference_does_not_move_quarterly_default_digest`).

**Default `monthly_reference` sweep (v1.19.3, opt-in):**

- 12 monthly periods (synthetic month-end ISO dates),
- **3-5 information arrivals per month**, total **51** for the
  default fixture,
- `living_world_digest` (`monthly_reference`):
  **`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`**.

**CLI exporter discipline (v1.19.2 + v1.19.3.1):**

- builds its own *fresh* kernel per invocation — running the
  CLI cannot influence a separately seeded default sweep,
- writes deterministic JSON via `world.run_export` (`sort_keys=True`),
- the bundle JSON contains no ISO wall-clock timestamp inserted
  by the export module itself, no absolute path, no `$USER` /
  `$HOSTNAME` capture (pinned by
  `test_bundle_json_has_no_iso_wall_clock_timestamp` /
  `test_bundle_json_contains_no_absolute_paths` and the v1.19.3.1
  monthly equivalents),
- two runs with the same args, two different `--out` paths,
  produce byte-identical bytes,
- module imports no FastAPI / Flask / Rails / aiohttp / tornado
  / starlette / uvicorn / gunicorn / django / selenium /
  playwright names (pinned by
  `test_module_imports_no_backend_or_browser_names`).

**Static UI loader discipline (v1.19.4):**

- HTML / CSS / JS only — `<input type="file">` +
  `FileReader.readAsText` + `JSON.parse`; no `fetch()`, no
  XHR, no backend, no engine execution from the browser, no
  file-system write,
- renders user-loaded values via `textContent` only — never
  `innerHTML`,
- caps the rendered ledger excerpt at **20** rows,
- preserves the v1.17.4 / v1.18.4 no-jump discipline verbatim,
- accepts `quarterly_default` / `monthly_reference`; rejects
  `scenario_monthly` / `daily_display_only` /
  `future_daily_full_simulation` with a clear status message.

**Test count:** **4522 / 4522** passing (+188 across the v1.19
sequence: v1.19.1 +56, v1.19.2 +20, v1.19.3 +88+13+3,
v1.19.3.1 +8, v1.19.4 +0). v1.19.0 / v1.19.4 are docs /
static-HTML only and add no pytest tests; the in-page Validate
button enforces the workbench-side invariants instead.

If any of these pins fails, either the default fixture has
drifted (intentional but undocumented), the CLI has gained a
hidden network call, or the static workbench has gained a
hidden engine bridge.

## v1.19.3 monthly_reference profile pins

The v1.19.3 milestone adds a `monthly_reference` run profile and an `InformationReleaseCalendar` storage layer ([`world/information_release.py`](../world/information_release.py)). The default `quarterly_default` profile remains byte-identical to v1.18.last; the `monthly_reference` profile is opt-in and runs the existing v1.16 closed loop on a 12-month synthetic schedule with synthetic public-information arrivals.

**Default `quarterly_default` sweep (unchanged from v1.18.last):**

- per-period record count: **108** (period 0) / **110** (periods 1+),
- per-run window: **`[432, 480]`**,
- default 4-period sweep total: **460 records**,
- integration-test `living_world_digest`: **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`** (pinned by `tests/test_information_release.py::test_empty_information_releases_does_not_move_default_living_world_digest` and `tests/test_living_reference_world.py::test_v1_19_3_quarterly_default_digest_unchanged`).

**Default `monthly_reference` sweep (v1.19.3 new):**

- 12 monthly periods (synthetic month-end ISO dates),
- **3-5 information arrivals per month**, total **51** for the default fixture (within the [36, 60] design budget pinned by `tests/test_living_reference_world.py::test_v1_19_3_monthly_reference_arrival_count_in_36_to_60` and the perf-boundary equivalent),
- per-period record count remains bounded — no daily-economic explosion (the `monthly_reference` profile reuses the same closed-loop machinery as `quarterly_default` plus 3-5 arrival records per period),
- `living_world_digest` (`monthly_reference`): **`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`** (pinned by `test_v1_19_3_monthly_reference_living_world_digest_is_pinned`).

**Bounded scale guarantees:**

- the monthly profile does **not** walk a `P x I x F x venue` or `P x I x F x option_count` Cartesian product (the per-period scale stays the v1.16 closed-loop scale plus a constant-bounded arrival count);
- the monthly profile emits **no** `ORDER_SUBMITTED` / `PRICE_UPDATED` / `CONTRACT_*` / `OWNERSHIP_TRANSFERRED` records (pinned by `test_v1_19_3_monthly_reference_emits_no_forbidden_record_types`);
- pytest count: **4494 / 4494** passing (+104 from v1.19.1; v1.19.2 is shipped by Agent A in parallel).

If any of these pins fails, either the default monthly fixture has drifted (intentional but undocumented) or a hidden quadratic loop has crept into the orchestrator.

## v1.18.last freeze pins

The v1.18.last freeze (docs-only on top of the v1.18.0 → v1.18.4
code freezes) closes the v1.18 sequence as the **first FWE
milestone where synthetic scenario drivers can be stored,
applied as append-only context shifts, rendered into scenario
reports, and selected in the static workbench UI** — without
mutating any source-of-truth record and without deciding actor
behaviour. None of these touch the kernel's per-period sweep
unless `apply_scenario_driver(...)` is explicitly invoked
outside the default fixture. On the default 4-period fixture
(3 firms, 2 investors, 2 banks, no scenario applied):

- per-period record count: **108** (period 0) / **110** (periods 1+),
  unchanged from v1.17.last (every v1.18 milestone added zero
  records to the per-period sweep — the scenario books are
  empty by default, the v1.18.2 helper runs only when called
  explicitly, the v1.18.3 driver builds its own *fresh* kernel,
  and v1.18.4 is a static-HTML edit),
- per-run window: **`[432, 480]`**, unchanged,
- default 4-period sweep total: **460 records**, unchanged,
- integration-test `living_world_digest` (v1.18.last):
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
  (unchanged from v1.17.last across all v1.18 milestones —
  pinned by per-book trip-wire tests at v1.18.1
  (`tests/test_scenario_drivers.py::test_empty_scenario_drivers_does_not_move_default_living_world_digest`),
  v1.18.2
  (`tests/test_scenario_applications.py::test_empty_scenario_applications_does_not_move_default_living_world_digest`
  + `…::test_explicit_scenario_application_does_not_touch_default_run`),
  and v1.18.3
  (`tests/test_display_timeline.py::test_scenario_helpers_do_not_move_default_living_world_digest`
  + `tests/test_scenario_report.py::test_run_scenario_report_does_not_move_default_living_world_digest`)),
- pytest count: **4334 / 4334** passing (+169 across the v1.18
  sequence; v1.18.0 / v1.18.4 are docs / static-HTML only and
  add no pytest tests; the in-page `Validate` button enforces
  the v1.18.4 scenario-selector / scenario-trace card
  invariants).

The v1.18 layer is **append-only** — every emitted record cites
the scenario template / application via plain-ids and never
mutates a pre-existing context record. The display helpers in
`world/display_timeline.py` import no source-of-truth book or
kernel (the standalone-display module-text scan is extended at
v1.18.3 to forbid `from world.scenario_drivers` and
`from world.scenario_applications`); the v1.18.3 driver builds
its own *fresh* kernel; the v1.18.4 static workbench writes
nothing, has no backend, no build, and no external runtime —
"Run mock" switches `(regime, scenario)` fixtures, never
invokes the Python engine.

## v1.17.last freeze pins

The v1.17.last freeze (docs-only on top of the v1.17.0 → v1.17.4
code freezes) closes the v1.17 sequence as the **first FWE
milestone where the v1.16 closed loop is operationally
inspectable** through display timelines, regime comparison,
causal annotations, and a static analyst workbench. None of
these touch the kernel or the per-period sweep. On the default
4-period fixture (3 firms, 2 investors, 2 banks):

- per-period record count: **108** (period 0) / **110** (periods 1+),
  unchanged from v1.16.last (every v1.17 milestone added zero
  records — the display layer runs only when the report / UI
  asks for it),
- per-run window: **`[432, 480]`**, unchanged,
- default 4-period sweep total: **460 records**, unchanged,
- integration-test `living_world_digest` (v1.17.last):
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
  (unchanged from v1.16.last across all v1.17 milestones —
  pinned by `tests/test_display_timeline.py::test_default_living_world_run_does_not_create_display_records`
  and `tests/test_regime_comparison_report.py::test_extract_regime_run_snapshot_does_not_mutate_kernel`),
- pytest count: **4165 / 4165** passing (+132 across the v1.17
  sequence; v1.17.0 / v1.17.4 are docs / static-HTML only and
  add no pytest tests; the in-page `Validate` button enforces
  the workbench-side bijection invariants instead).

The v1.17 layer is a **rendering** of the v1.16 closed-loop
records — it imports no source-of-truth book on the engine
side (the runtime-book-free discipline is pinned by a v1.17.1
text scan), runs each regime on its own freshly-seeded kernel
on the report-driver side, and never mutates any kernel book.
The static workbench writes nothing, has no backend, no build,
and no external runtime; "Run mock" is fixture switching, not
engine execution.

## v1.16.last freeze pins

The v1.16.last freeze (docs-only on top of the v1.16.0 → v1.16.3
code freezes) closes the v1.16 sequence as the **first FWE
milestone where the living reference world has a closed
deterministic endogenous-market-intent feedback loop** —
attention → market intent (v1.16.1 classifier) → aggregated
interest → indicative pressure → financing review → next-period
attention. On the default 4-period fixture (3 firms, 2
investors, 2 banks):

- per-period record count: **108** (period 0) / **110** (periods 1+),
  unchanged from v1.15.6 / v1.16.1 / v1.16.2 / v1.16.3 (every
  v1.16 milestone added zero new records — only payload bytes
  changed),
- per-run window: **`[432, 480]`**, unchanged,
- default 4-period sweep total: **460 records**, unchanged,
- integration-test `living_world_digest` (v1.16.last):
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
  (moved twice in the v1.16 sequence — at v1.16.2 with the
  rotation → classifier rewire, and at v1.16.3 with the
  attention-feedback union; unchanged at v1.16.0 and v1.16.1),
- pytest count: **4033 / 4033** passing.

The v1.16 changes are bounded `O(P × I × F)` for the per-pair
classifier call and `O(P × (I + B))` for the per-actor attention
build — exactly the loop shapes already used by v1.15.5 and
v1.12.8. **No new dense shape was introduced.** The v1.12.9
attention-budget discipline (`per_dimension_budget`,
`decay_horizon`, `saturation_policy`) is preserved bit-for-bit:
v1.16.3 fresh focus labels are unioned into the v1.12.8 fresh
set **before** decay / saturation runs. The `PriceBook` is
byte-equal across the full default sweep — pinned by tests at
every v1.15 / v1.16 milestone.

## v1.16.3 update pins

v1.16.3 closes the v1.12 endogenous-attention loop with the v1.15
securities-market-pressure / corporate-financing-path loop. Each
period-N+1 `ActorAttentionStateRecord` now carries two new
plain-id source-tuple slots
(`source_indicative_market_pressure_ids`,
`source_corporate_financing_path_ids`), and a closed-set
deterministic mapping
(`world.attention_feedback._classify_market_pressure_focus`
+ `world.attention_feedback._classify_financing_path_focus`)
widens `focus_labels` with five new closed-set tags (`risk` /
`financing` / `dilution` / `market_interest` /
`information_gap`) when prior-period pressure / path evidence
fires the rules. **No new records** — slot additions and label
unions only — so per-period record count, per-run window, and
loop shapes are unchanged from v1.16.2. On the default 4-period
fixture (3 firms, 2 investors, 2 banks):

- per-period record count: **108** (period 0) / **110** (periods 1+),
  unchanged from v1.16.2,
- per-run window: **`[432, 480]`**, unchanged,
- default 4-period sweep total: **460 records**, unchanged,
- integration-test `living_world_digest` (v1.16.3):
  **`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
  (moved by design — same record cardinality, different
  attention-state payload bytes per period 1+),
- pytest count: **4033 / 4033** passing (+34 tests across
  attention-feedback unit + living-world integration suites).

The v1.12.9 attention-budget discipline (`per_dimension_budget`,
`decay_horizon`, `saturation_policy`) is preserved bit-for-bit:
v1.16.3 fresh focus labels are unioned into the v1.12.8 fresh set
**before** decay / saturation runs, so the saturation cap can
still drop stale prior focus to make room for new pressure-driven
labels.

## v1.16.2 update pins

v1.16.2 rewires the v1.15.5 living-world investor-market-intent
phase to call the v1.16.1 pure-function classifier
`classify_market_intent_direction(...)` instead of the four-cycle
`(period_idx + investor_idx + firm_idx) % 4` rotation. Loop shape,
record types, record count, and per-run window are unchanged from
v1.15.6 / v1.16.1 — `InvestorMarketIntentRecord` payloads now
carry classifier-derived `intent_direction_label` /
`intensity_label` / `confidence` and a small classifier-audit
`metadata` block (`classifier_version` / `classifier_rule_id` /
`classifier_status` / `classifier_confidence` /
`classifier_unresolved_or_missing_count` /
`classifier_evidence_summary`). On the default 4-period fixture
(3 firms, 2 investors, 2 banks):

- per-period record count: **108** (period 0) / **110** (periods 1+),
  unchanged from v1.15.6 / v1.16.1,
- per-run window: **`[432, 480]`**, unchanged,
- default 4-period sweep total: **460 records**, unchanged,
- integration-test `living_world_digest` (v1.16.2):
  **`0b75e95ad8f157df5e938c1318817c07f00798179c3d11b8629452d30d9398fa`**
  (moved by design — same record shapes, different label / metadata
  bytes per `InvestorMarketIntentRecord`),
- pytest count: **3999 / 3999** passing (+16 living-world tests).

## v1.15.last freeze pins

The v1.15.last freeze (docs-only on top of the v1.15.1 → v1.15.6
code freezes) pins the following on the default 4-period fixture
(3 firms, 2 investors, 2 banks):

- per-period record count: **108** (period 0) / **110** (periods 1+),
  unchanged from v1.15.5 / v1.15.6 (v1.15.6 added citation slots
  but no new records),
- per-run window: **`[432, 480]`**, unchanged,
- default 4-period sweep total: **460 records**,
- integration-test `living_world_digest` (v1.15.last):
  **`bd7abdb9a62fb93a1001d3f760b76b3ab4a361313c3af936c8b860f5ab58baf8`**
  (moved twice in the v1.15 sequence — at v1.15.5 chain
  integration and at v1.15.6 phase reorder + citation slots;
  unchanged through v1.15.1 → v1.15.4),
- pytest count: **3883 / 3883** passing.

The chain itself stays bounded `O(P × I × F + 2 × P × F)` per
layer — never `P × I × F × venue` or `P × I × F × option`.
v1.15.5 deliberately did **not** add a new dense shape, and
v1.15.6 deliberately added zero new records. The v1.15 surface
composes with the v1.14 corporate-financing chain via citation
slots only — no execution path, no `PriceBook` mutation, no
financing approval.

## v1.15.6 update pins

v1.15.6 wires `IndicativeMarketPressureRecord` ids into the v1.14
corporate-financing chain as additional citation slots and
reorders the per-period sweep so the v1.15.5 chain runs *before*
the v1.14.5 chain. **No new records** — citation slots only — so
the per-period record count is unchanged. On the default 4-period
fixture (3 firms, 2 investors, 2 banks):

- per-period record count: **108** (period 0) / **110** (periods 1+),
  unchanged from v1.15.5,
- per-run window: **`[432, 480]`**, unchanged from v1.15.5,
- default 4-period sweep total: **460 records**, unchanged,
- integration-test `living_world_digest`:
  **`bd7abdb9a62fb93a1001d3f760b76b3ab4a361313c3af936c8b860f5ab58baf8`**
  (moved at v1.15.6 by design — phase reorder + new citation
  slots on review/path payloads),
- pytest count: **3883 / 3883** passing.

## v1.15.5 update pins

v1.15.5 puts the v1.15 securities-market-intent chain on the
per-period sweep. On the default 4-period fixture (3 firms, 2
investors, 2 banks):

- per-period record count: **108** (period 0) / **110** (periods 1+),
  up from 96 / 98 at v1.14.5,
- per-run window: **`[432, 480]`**, up from `[384, 432]`,
- default 4-period sweep total: **460 records**,
- integration-test `living_world_digest`:
  `041686b0c69eea751cb24e3e3e5b4ac25e56a8ae20d4b1bd40a41dc5303403a5`
  (moved at v1.15.5 by design; unchanged through v1.15.1 →
  v1.15.4),
- pytest count at v1.15.5: 3863 / 3863 passing.

Loop-shape constraints: the v1.15.5 chain stays bounded at
`P × I × F + 2 × P × F` per run — no `P × I × F × venue` or
`P × I × F × option` dense loop. The investor-market-intent
phase is the only `I × F` layer added; aggregated-interest and
indicative-pressure are both `P × F` per layer.

## v1.14.last freeze pins

The v1.14.last freeze (docs-only on top of the v1.14.5 code
freeze) pins the following on the default 4-period fixture
(3 firms, 2 investors, 2 banks, 4 periods):

- per-period record count: **96** (period 0) / **98** (periods 1+),
  up from 81 / 83 at v1.13.last (the +15 per period is the
  v1.14.5 corporate-financing chain: 1 need + 2 options + 1
  capital-structure review + 1 financing path per firm),
- per-run window: **`[384, 432]`**, up from `[324, 372]` at
  v1.13.last,
- default 4-period sweep total: **408 records**,
- integration-test `living_world_digest`:
  **`3df73fd4f152c16d1188f5c15b69bdc8a5cd6061b637ea35af671e86c6fa2d71`**
  (moved at v1.14.5 by design; unchanged through v1.14.1 →
  v1.14.4 because those milestones were storage-only),
- pytest count: **3391 / 3391** passing.

The chain itself is bounded by `P × F` per layer — never
`O(P × F × I)` or `O(P × F × B × option_count)`. v1.14.5
deliberately did **not** add a new dense shape: every layer of
the chain stays in the same `O(P × F)` shape as the v1.10.3
corporate strategic response candidate.

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
