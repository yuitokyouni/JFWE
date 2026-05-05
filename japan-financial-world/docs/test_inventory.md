# Test Inventory

Snapshot of the test suite at **v1.20.last** (`Monthly Scenario
Reference Universe freeze` — docs-only milestone that closes
the v1.20 sequence; ships the single-page reader-facing summary
in
[`v1_20_monthly_scenario_reference_universe_summary.md`](v1_20_monthly_scenario_reference_universe_summary.md),
the v1.20.last release-readiness snapshot in
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md), the
v1.20.last freeze pin in
[`performance_boundary.md`](performance_boundary.md), and the
v1.20.last position-in-sequence rows in `world_model.md` §129
(specifically §129.25 / §129.26 / §129.27); no new code, no new
tests, no new ledger event types, no new behavior; test count
= **4764 / 4764**, per-period record count
(`scenario_monthly_reference_universe` default fixture) =
**257 / 261** (no-scenario period / scheduled-scenario period
3 = month_04), per-run target window = **`[2400, 3360]`**,
hard guardrail = **`≤ 4000`** — observed counts **3220** (the
v1.20.3 *profile canonical* record count under the test fixture
with no `market_regime` kwarg) and **3241** (the v1.20.4 CLI
exporter's `bundle.manifest.record_count` under
`--regime constrained --scenario credit_tightening_driver`)
are both within the target window and well under the hard
guardrail; the +21 record delta lives entirely in the
`observation_set_selected` record type and is fully driven by
the v1.11.2 `_REGIME_PRESETS["constrained"]` preset (see
§129.26 in `world_model.md` for the binding explanation);
`scenario_monthly_reference_universe` `living_world_digest` =
**`5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`**
under the v1.20.3 default fixture; v1.20.4 CLI export bundle
digest =
**`ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`**;
canonical `quarterly_default` `living_world_digest` =
**`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
(unchanged from v1.18.last across the entire v1.19 + v1.20
sequence when no scenario is applied), `monthly_reference`
`living_world_digest` =
**`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`**
(unchanged from v1.19.last across the entire v1.20 sequence);
the v1.20 surface is the **first public-FWE milestone where
the engine moves from a small closed-loop demo to a richer
synthetic market-like reference universe** — 12 monthly periods
× 11 generic sectors × 11 representative synthetic firm
profiles × 4 investor archetypes × 3 bank archetypes × 51
information arrivals × 1 scheduled scenario application × 2
scenario context shifts × 11 affected sector ids × 11 affected
firm profile ids; sector labels carry the `_like` suffix and
no public-FWE module text or test depends on bare `GICS`,
`MSCI`, `S&P`, `FactSet`, `Bloomberg`, `Refinitiv`, `TOPIX`,
`Nikkei`, or `JPX` tokens; firm ids follow the synthetic
`firm:reference_<sector>_a` pattern with no real company name;
the static workbench mockup now renders an additional Universe
tab (between Overview and Timeline; 11 tabs ↔ 11 sheets) with
an 11-row × 9-column sector sensitivity heatmap, an 11-row × 6-
column firm profile table, and a 5-step scenario causal trace;
the CLI exporter writes a deterministic JSON bundle that the
browser reads via `<input type="file">` + `FileReader.readAsText`;
**no real companies, no real sector weights, no licensed
taxonomy dependency, no real financial values, no real
indicator values, no real institutional identifiers, no price
formation, no market price, no predicted index, no forecast
path, no expected return, no target price, no trading, no
orders, no execution, no clearing, no settlement, no financing
execution, no direct firm decisions, no direct investor
actions, no bank approval logic, no investment advice, no real
data ingestion, no Japan calibration, no LLM execution, no LLM
prose as source-of-truth, no backend, no fetch / XHR, no
file-system write, no browser-to-Python execution, no daily
simulation, no mutation of pre-existing context records**. The
v1.19.last, v1.18.last, v1.17.last, v1.16.last, and v1.15.last
historical snapshots below are preserved unchanged.)

---

Earlier snapshot at **v1.19.last** (`Local Run Bundle
and Monthly Reference freeze` — docs-only milestone that closes
the v1.19 sequence; ships the single-page reader-facing summary
in
[`v1_19_local_run_bundle_and_monthly_reference_summary.md`](v1_19_local_run_bundle_and_monthly_reference_summary.md),
the v1.19.last release-readiness snapshot in
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md), and the
v1.19.last position-in-sequence row in `world_model.md` §128.20;
no new code, no new tests, no new ledger event types, no new
behavior; test count = **4522 / 4522**, per-period record count
(`quarterly_default`) = **108 / 110**, per-run window
(`quarterly_default`) = **`[432, 480]`**,
default-fixture `living_world_digest` =
**`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
(unchanged from v1.18.last across the entire v1.19 sequence
when no scenario is applied), `monthly_reference`
`living_world_digest` =
**`75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`**;
the v1.19 surface is the **first public-FWE local-run-bundle
inspection layer** — deterministic `RunExportBundle` JSON
(v1.19.1) + CLI exporter (v1.19.2 / v1.19.3.1) +
`monthly_reference` profile + `InformationReleaseCalendar` /
`ScheduledIndicatorRelease` / `InformationArrivalRecord`
(v1.19.3) + static UI read-only loader (v1.19.4); CLI generates
JSON, browser reads JSON, browser does **not** execute Python,
**no backend**, **no Rails**, **no FastAPI**, **no Flask**,
**no fetch / XHR / network**, **no file-system write**, **no
daily simulation**; `monthly_reference` is opt-in synthetic and
emits 51 information arrivals across 12 months from a
jurisdiction-neutral synthetic calendar (no real values, no
real release dates, no real institutional identifiers); UI
loader accepts `quarterly_default` / `monthly_reference` and
rejects `scenario_monthly` / `daily_display_only` /
`future_daily_full_simulation` with a clear status message;
**no price formation, no market price, no predicted index, no
forecast path, no expected return, no target price, no trading,
no orders, no execution, no clearing, no settlement, no
financing execution, no investment advice, no real data
ingestion, no Japan calibration, no LLM execution, no firm
decisions, no investor actions, no bank approval logic, no
mutation of pre-existing context records**. The v1.18.last,
v1.17.last, v1.16.last, and v1.15.last historical snapshots
below are preserved unchanged.)

---

Earlier snapshot at **v1.18.last** (`Scenario Driver
Library freeze` — docs-only milestone that closes the v1.18
sequence; ships the single-page reader-facing summary in
[`v1_18_scenario_driver_library_summary.md`](v1_18_scenario_driver_library_summary.md),
the v1.18.last release-readiness snapshot in
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md), and the
v1.18.last position-in-sequence row in `world_model.md` §127;
no new code, no new tests, no new ledger event types, no new
behavior; test count = **4334 / 4334**, per-period record count
= **108 / 110**, per-run window = **`[432, 480]`**,
`living_world_digest` =
**`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
— all unchanged from v1.17.last by design across the entire
v1.18 sequence when no scenario is applied; the v1.18 surface
is the **first public-FWE scenario-driver inspection layer**
over the v1.17 inspection surface and the v1.16 closed loop:
synthetic scenario templates (v1.18.1) → append-only scenario
applications (v1.18.2) → append-only context-shift records
(v1.18.2) → event / causal annotations rendered through the
v1.17.1 display surface (v1.18.3) → deterministic markdown
scenario report (v1.18.3) → static UI scenario selector mock
(v1.18.4); append-only, deterministic, rule-based-fallback
only — no price formation, no market price, no predicted
index, no forecast path, no expected return, no target price,
no trading, no orders, no execution, no clearing, no
settlement, no financing execution, no investment advice, no
real data ingestion, no Japan calibration, no LLM execution,
no LLM prose as source-of-truth, no stochastic behaviour
probabilities, no learned model, no firm decisions, no
investor actions, no bank approval logic, no mutation of
pre-existing context records. The scenario chain stays
template-only / append-only / label-only / stimulus-only — the
scenario driver is the stimulus, never the response. The
v1.18.4 static workbench gains a seven-option scenario
selector (Baseline / Rate repricing / Credit tightening /
Funding window closure / Liquidity stress / Information gap /
Unmapped fallback) — fixture switching only, the Python engine
is NOT invoked from the UI. The v1.17.last, v1.16.last, and
v1.15.last historical snapshots below are preserved unchanged.)

---

Earlier snapshot at **v1.17.last** (`Inspection Layer freeze`
— docs-only milestone that closes the v1.17 sequence; ships
the single-page reader-facing summary in
[`v1_17_inspection_layer_summary.md`](v1_17_inspection_layer_summary.md),
the v1.17.last release-readiness snapshot in
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md), and the
v1.17.last position-in-sequence row in `world_model.md` §123;
no new code, no new tests, no new ledger event types, no new
behavior; test count = **4165 / 4165**, per-period record count
= **108 / 110**, per-run window = **`[432, 480]`**,
`living_world_digest` =
**`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
— all unchanged from v1.16.last by design across the entire
v1.17 sequence; the v1.17 surface is the **first public-FWE
inspection layer over the v1.16 closed loop** (reporting
calendar / synthetic display path / event annotations / causal
timeline / regime comparison report / static analyst
workbench); inspection / rendering only — no price formation,
no market price, no predicted index, no forecast path, no
expected return, no target price, no trading, no orders, no
execution, no clearing, no settlement, no investment advice,
no real data, no Japan calibration, no LLM execution, no
stochastic behaviour probabilities, no learned model, no new
economic source-of-truth records.)

---

Earlier snapshot at **v1.16.last** (`Endogenous
Market Intent Feedback freeze` — docs-only milestone that closes
the v1.16 sequence; ships the single-page reader-facing summary
in [`v1_16_endogenous_market_intent_feedback_summary.md`](v1_16_endogenous_market_intent_feedback_summary.md),
the v1.16.last release-readiness snapshot in
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md), and the
v1.16.last position-in-sequence row in `world_model.md` §118;
no new code, no new tests, no new ledger event types, no new
behavior; test count = **4033 / 4033**, per-period record count
= **108 / 110**, per-run window = **`[432, 480]`**,
`living_world_digest` =
**`f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`**
— all unchanged from v1.16.3; the v1.16 surface is the **first
public-FWE closed endogenous-market-intent feedback loop**
(attention → InvestorMarketIntent via the v1.16.1 evidence-
conditioned classifier → AggregatedMarketInterest →
IndicativeMarketPressure → CapitalStructureReview /
CorporateFinancingPath → next-period ActorAttentionState focus
labels via the v1.16.3 deterministic mapping); market-interest
feedback / audit / replay only — no order submission, no order
book, no matching, no execution, no clearing, no settlement, no
quote dissemination, no bid / ask, no price update, no
`PriceBook` mutation, no target price, no expected return, no
recommendation, no portfolio allocation, no real exchange
mechanics, no financing execution, no loan approval, no bond /
equity issuance, no underwriting, no syndication, no pricing, no
investment advice, no real data, no Japan calibration, no LLM
execution, no stochastic behaviour probabilities, no learned
model. Known limitation: the v1.16 classifier and attention-
feedback rule helpers are **deterministic and rule-based** —
illustrative for auditability and replayable causal structure,
not calibrated and not predictive. The v1.15.last historical
snapshot below is preserved unchanged.)

---

Earlier snapshot at **v1.15.last** (`Securities Market
Intent Aggregation freeze` — docs-only milestone that closes the
v1.15 sequence; ships the single-page reader-facing summary in
[`v1_15_securities_market_intent_summary.md`](v1_15_securities_market_intent_summary.md),
the v1.15.last release-readiness snapshot in
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md), and the
v1.15.last position-in-sequence row in `world_model.md` §113;
no new code, no new tests, no new ledger event types, no new
behavior; test count = **3883 / 3883**, per-period record count
= **108 / 110**, per-run window = **`[432, 480]`**,
`living_world_digest` =
**`bd7abdb9a62fb93a1001d3f760b76b3ab4a361313c3af936c8b860f5ab58baf8`**
— all unchanged from v1.15.6; the underlying surface is the
bounded securities-market-interest aggregation
`investor intent / valuation / firm state / market environment →
investor market intent → aggregated market interest → indicative
market pressure → capital-structure review / financing path`,
layered on top of the v1.12 endogenous attention loop and the
v1.14 corporate-financing chain; market-interest aggregation /
audit / feedback only — no order submission, no order book, no
matching, no execution, no clearing, no settlement, no quote
dissemination, no bid / ask, no price update, no `PriceBook`
mutation, no target price, no expected return, no recommendation,
no portfolio allocation, no real exchange mechanics, no financing
execution, no loan approval, no bond / equity issuance, no
underwriting, no syndication, no pricing, no investment advice,
no real data, no Japan calibration. Known limitation: v1.15.5
uses a deterministic rotation for `intent_direction_label`
instead of evidence-conditioned classification; v1.16 will
replace the rotation. The v1.14.last historical snapshot below
is preserved unchanged.)

---

Earlier snapshot at **v1.14.last** (`Corporate Financing
Intent freeze` — docs-only milestone that closes the v1.14
sequence; ships the single-page reader-facing summary in
[`v1_14_corporate_financing_intent_summary.md`](v1_14_corporate_financing_intent_summary.md),
the v1.14.last release-readiness snapshot in
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md), and the
v1.14.last position-in-sequence row in `world_model.md` §105;
no new code, no new tests, no new ledger event types, no new
behavior; test count = **3391 / 3391**, per-period record count
= **96 / 98**, per-run window = **`[384, 432]`**,
`living_world_digest` =
**`3df73fd4f152c16d1188f5c15b69bdc8a5cd6061b637ea35af671e86c6fa2d71`**
— all unchanged from v1.14.5; the underlying surface is the
bounded corporate financing reasoning chain
`market environment → firm latent state → investor intent /
valuation / bank credit review → corporate financing need →
funding option candidates → capital structure review → financing
path`, layered on top of the v1.12 endogenous attention loop and
the v1.13 settlement substrate; storage / audit / graph-linking
only — no financing execution, no loan approval, no bond / equity
issuance, no underwriting, no syndication, no bookbuilding, no
allocation, no pricing, no optimal capital structure decision,
no investment advice, no real data, no Japan calibration. The
v1.12.last historical snapshot below is preserved unchanged.)

---

Earlier snapshot at **v1.12.last** (`Endogenous
attention loop freeze` — docs-only milestone that closes the
v1.12 endogenous-attention sequence; ships the single-page
reader-facing summary in
[`v1_12_endogenous_attention_loop_summary.md`](v1_12_endogenous_attention_loop_summary.md),
the regime-comparison demo section in
[`examples/reference_world/README.md`](../examples/reference_world/README.md),
the v1.12.last release-readiness snapshot in
[`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md), and the
v1.12.last position-in-sequence row in `world_model.md` §92; no
new code, no new tests, no new ledger event types, no new
behavior; test count, per-period record count, per-run window,
and `living_world_digest` are all **unchanged** from v1.12.9 —
the underlying surface is what v1.12.9 froze: `Attention
budget / decay / saturation` — disciplines the v1.12.8
cross-period feedback loop with a **finite synthetic attention
budget**:
`ActorAttentionStateRecord` carries `per_dimension_budget=3` /
`decay_horizon=2` / `saturation_policy="drop_oldest"`;
`max_selected_refs` is capped at 12; an inherited focus label
halves to 0.5 in the next period without reinforcement, halves
to 0.0 after that, or is dropped once stale_count exceeds
`decay_horizon`; reinforcement resets weight to 1.0 and
stale_count to 0; saturation above 8 focus labels triggers
drop-oldest; new `apply_attention_budget` helper bounds candidate
selected refs by per-dimension and total caps deterministically;
the headline crowding pin shows new risk focus replaces decayed
engagement focus in a 3-period synthetic scenario; per-period
record count and per-run window unchanged from v1.12.8 (the
v1.12.9 changes are internal to attention-state field shapes
and memory-selection contents); default-fixture
`living_world_digest` moves from `3002a499...` to
`e508b4bf10df217f7b561b41aea845f841b12215d5bf815587375c52cffcdcb5`
by design — pinned in a regression test):
`2751 / 2751 passing` (444 v0 + 188 v1.0-v1.7 frozen reference +
2119 post-v1.7 additions covering reference demo, replay, manifest,
catalog-shape, experiment harness, renamed WorldID tests,
interactions, routines, attention, routine engine, the corporate
quarterly reporting routine, the world-variable storage layer, the
exposure / dependency storage layer, the observation-menu builder
join service, the heterogeneous-attention investor / bank demo, the
investor / bank review routines, the endogenous chain harness, the
ledger trace report, the multi-period living reference world demo,
the v1.9.1-prep report contract, the v1.9.1 living world trace
report, the v1.9.2 living-world replay-determinism + manifest
helpers, the v1.9.3 mechanism interface contract, the v1.9.3.1
hardening, the CLI argv-isolation pin, the v1.9.4 firm operating
pressure assessment mechanism, the v1.10.1 stewardship theme signal
storage / audit layer, the v1.10.2 portfolio-company dialogue record
metadata storage / audit layer, the v1.10.3 investor escalation
candidate storage / audit layer (added to the engagement test file),
the v1.10.3 corporate strategic response candidate storage / audit
layer in the strategic-response test file, the v1.10.4 industry
demand condition signal storage / audit layer in the new
industry-conditions test file, the v1.10.4.1 additive
type-correct industry-condition cross-reference slot on
`CorporateStrategicResponseCandidate` exercised in the
strategic-response test file, and the v1.10.5 living-world
integration that wires the v1.10.1 → v1.10.4.1 storage layer
into the living reference world demo's per-period sweep
exercised in `tests/test_living_reference_world.py`, and the
v1.11.0 capital-market surface — `MarketConditionRecord` /
`MarketConditionBook` in `world/market_conditions.py` plus the
v1.11.0 ``trigger_market_condition_ids`` type-correct slot on
`CorporateStrategicResponseCandidate` plus the per-period
capital-market phase in the living reference world demo
exercised in the new `tests/test_market_conditions.py` and
extended in `tests/test_strategic_response.py` and
`tests/test_living_reference_world.py`, and the v1.11.1
capital-market readout — `CapitalMarketReadoutRecord` /
`CapitalMarketReadoutBook` / `build_capital_market_readout` in
`world/market_surface_readout.py` plus the per-period readout
phase in the living reference world demo exercised in the new
`tests/test_market_surface_readout.py` and extended in
`tests/test_living_reference_world.py`, the v1.11.2 demo
market regime presets — four named synthetic presets
(constructive / mixed / constrained / tightening) +
`--market-regime` CLI flag, exercised in
`tests/test_living_reference_world.py`, and the v1.12.0 firm
financial latent state — `FirmFinancialStateRecord` /
`FirmFinancialStateBook` / `run_reference_firm_financial_state_update`
in `world/firm_state.py` plus the per-period firm-state phase
in the living reference world demo, the first time-crossing
endogenous state-update layer, exercised in the new
`tests/test_firm_state.py` and extended in
`tests/test_living_reference_world.py`, and the v1.12.1
investor intent signal — `InvestorIntentRecord` /
`InvestorIntentBook` / `run_reference_investor_intent_signal`
in `world/investor_intent.py` plus the per-period investor-intent
phase between the v1.10.3 escalation and the v1.10.3 corporate
response phases, exercised in the new
`tests/test_investor_intent.py` and extended in
`tests/test_living_reference_world.py`, and the v1.12.2
market environment state — `MarketEnvironmentStateRecord` /
`MarketEnvironmentBook` / `build_market_environment_state` in
`world/market_environment.py` plus the per-period market
environment phase between the v1.11.1 readout and the v1.12.0
firm-state phases plus the additive
`evidence_market_environment_state_ids` slot on
`FirmFinancialStateRecord` and `InvestorIntentRecord` plus the
additive `trigger_market_environment_state_ids` slot on
`CorporateStrategicResponseCandidate`, exercised in the new
`tests/test_market_environment.py` and extended in
`tests/test_firm_state.py`, `tests/test_investor_intent.py`,
`tests/test_strategic_response.py`, and
`tests/test_living_reference_world.py`, and the v1.12.3
EvidenceResolver / ActorContextFrame — read-only evidence
resolution layer (`EvidenceRef` + `ActorContextFrame` +
`EvidenceResolver` + `resolve_actor_context` in new
`world/evidence.py`) plus the optional
`WorldKernel.evidence_resolver` field, exercised in the new
`tests/test_evidence_resolver.py`, and the v1.12.4
attention-conditioned investor intent —
`run_attention_conditioned_investor_intent_signal` in
`world/investor_intent.py` (new helper alongside the existing
`run_reference_investor_intent_signal`) that calls
`resolve_actor_context` and classifies on the resolved frame
ids only, plus the additive `stewardship_theme` bucket on
`ActorContextFrame`, plus the orchestrator switch to the new
helper, exercised by extended tests in
`tests/test_investor_intent.py` (including the headline
attention-divergence test) and
`tests/test_living_reference_world.py`, and the v1.12.5
attention-conditioned valuation lite —
`run_attention_conditioned_valuation_refresh_lite` in
`world/reference_valuation_refresh_lite.py` (new helper alongside
the existing `run_reference_valuation_refresh_lite`) that calls
`resolve_actor_context` with `actor_type="valuer"` and runs the
v1.9.5 pressure-haircut adapter on only the resolved frame ids,
applying a small documented synthetic delta on top of the v1.9.5
formula (resolved-buckets confidence bonus, unresolved-refs
confidence penalty, restrictive-market value haircut, risk-off
appetite haircut), exercised by extended tests in
`tests/test_reference_valuation_refresh_lite.py` including the
headline three-valuers divergence test; v1.12.5 is helper-level
+ tests only — the orchestrator continues to call the
pre-existing v1.9.5 helper, so the `living_world_digest` and
per-run record-count window remain unchanged from v1.12.4).

This inventory is grouped by what each component verifies. The numbers in
parentheses are test counts per file. Run the full suite with:

```bash
python -m pytest -q
```

The v0 portion (`444 passed`) is unchanged from v0.16 freeze. The v1
portion (`188 passed`) was added across milestones v1.1 – v1.6; v1.7 is
documentation-only and adds no new tests.

## Identity, time, and registration

- `test_yaml_load.py` (5) — YAML world specs load into typed records;
  malformed inputs raise `ValueError`.
- `test_validation.py` (4) — basic registry-object validation rules.

## Registry, scheduler, clock, ledger, state

- `test_clock.py` (11) — calendar advance, `is_month_end /
  is_quarter_end / is_year_end` boundary detection, advance-by-day
  semantics.
- `test_scheduler.py` (10) — task registration, frequency dispatch,
  due-task ordering, phase placeholder, deterministic order across
  ties.
- `test_ledger.py` (3) — record append, query, JSONL round-trip.
- `test_state.py` (5) — initialize_object, snapshot creation,
  immutability of snapshots, state-hash determinism.

## Cross-cutting kernel smoke

- `test_world_kernel_smoke.py` (1) — empty kernel runs for one year
  with two no-op tasks; verifies expected `task_executed` counts and
  monthly snapshot count.
- `test_spaces_smoke.py` (2) — three empty spaces (Corporate / Investor
  / Bank) coexist and fire at their declared frequencies.

## Inter-space transport (v0.3)

- `test_event_bus.py` (10) — publish, collect_for_space, next-tick
  delivery rule, broadcast (with source exclusion), at-most-once
  per-target delivery, pending-vs-delivered split.
- `test_space_signal_flow.py` (5) — emitter and observer spaces
  exchange a `WorldEvent` through the kernel; ledger records
  `event_published / event_delivered`.

## Network books (v0.4)

- `test_ownership.py` (14) — add/get/list positions, per-(owner|asset)
  views, transfer with insufficient-balance / unknown-source / self-
  transfer rejection, snapshot determinism, ledger writes.
- `test_contract_network.py` (13) — add_contract / get_contract /
  list_by_party / list_by_type, status update, duplicate rejection,
  ledger writes.
- `test_price_book.py` (11) — append-only history, `get_latest_price`,
  per-asset history retrieval, snapshot, ledger writes.

## Projections

- `test_balance_sheet.py` (18) — quantity × latest_price valuation,
  borrower-vs-lender contract treatment via `metadata`, collateral
  summation, missing-price tolerance, NAV computation, snapshot, no-
  mutation guarantee, kernel wiring.
- `test_constraints.py` (23) — `ConstraintRecord` / `ConstraintEvaluation`
  CRUD, all five constraint types (max_leverage, min_net_asset_value,
  min_cash_like_assets, min_collateral_coverage,
  max_single_asset_concentration) with ok / warning / breached /
  unknown paths, ledger writes, no-mutation guarantee.

## Information layer (v0.7)

- `test_signals.py` (25) — `InformationSignal` validation, six
  visibility values, effective-date filter, `mark_observed`, snapshot,
  ledger writes, cross-book isolation.
- `test_signal_event_flow.py` (4) — `WorldEvent` payload references a
  `signal_id`; observer fetches the signal through `SignalBook`;
  transport / visibility independence.

## DomainSpace (v0.10.1)

- `test_domain_space.py` (10) — `bind()` contract (idempotent / fill-
  only / explicit refs win / no hot-swap), three read-only accessors,
  graceful unbound behavior, kernel wiring.

## Domain spaces — identity state and integration

Each domain space has two test files: a unit-style state file
covering CRUD / snapshot / ledger / unbound behavior, and an
integration file covering kernel wiring, projection reads, and
no-mutation guarantee.

### Corporate (v0.8)

- `test_corporate_state.py` (16) — `FirmState` dataclass, CRUD,
  snapshot, ledger.
- `test_corporate_space_integration.py` (9) — kernel wiring, balance-
  sheet / constraint / signal reads, no-mutation, scheduler
  compatibility.

### Banking (v0.9)

- `test_bank_state.py` (21) — `BankState`, `LendingExposure`, CRUD,
  metadata-only role inference rule.
- `test_bank_space_integration.py` (12) — kernel wiring, lending-
  exposure derivation, no-mutation, scheduler compatibility.

### Investors (v0.10)

- `test_investor_state.py` (21) — `InvestorState`, `PortfolioExposure`
  with missing-data tolerance.
- `test_investor_space_integration.py` (13) — kernel wiring, three-
  book join (ownership × prices × registry), no-mutation.

### Exchange (v0.11)

- `test_exchange_state.py` (27) — `MarketState`, `ListingState` with
  composite-key relation, cross-listing support, snapshot.
- `test_exchange_space_integration.py` (10) — kernel wiring, price /
  signal reads, price/listing independence, no-mutation.

### Real Estate (v0.12)

- `test_real_estate_state.py` (28) — `PropertyMarketState`,
  `PropertyAssetState` with foreign-key relation, unenforced FK rule.
- `test_real_estate_space_integration.py` (10) — kernel wiring, price
  / signal reads, no-mutation.

### Information (v0.13)

- `test_information_state.py` (27) — `InformationSourceState`,
  `InformationChannelState`, channel-vs-signal visibility independence.
- `test_information_space_integration.py` (9) — signal queries by
  source / type / visibility, registration-independence, no-mutation.

### Policy (v0.14)

- `test_policy_state.py` (20) — `PolicyAuthorityState`,
  `PolicyInstrumentState`, list_instruments_by_authority filter.
- `test_policy_space_integration.py` (5) — kernel wiring, signal
  reads, no-mutation, scheduler compatibility.

### External (v0.14)

- `test_external_state.py` (21) — `ExternalFactorState` with `unit`
  field, `ExternalSourceState` (no tier — distinguished from
  InformationSourceState).
- `test_external_space_integration.py` (5) — kernel wiring, signal
  reads, no-mutation, scheduler compatibility.

## Cross-space integration (v0.15)

- `test_world_kernel_full_structure.py` (16) — the v0 closing test.
  Builds a populated `WorldKernel` with all eight spaces, runs for
  365 days, verifies per-frequency task counts, every space's read
  accessors, EventBus next-tick delivery to two target spaces,
  transport / visibility independence, no source-of-truth book
  mutation across all reads, and a complete ledger audit trail.

## Valuation / fundamentals layer (v1.1)

- `test_valuations.py` (34) — `ValuationRecord` validation,
  `ValuationBook` CRUD / snapshot / ledger, currency vs numeraire
  storage, `ValuationGap` computation, `ValuationComparator`
  comparing against the latest `PriceRecord`, `valuation_compared`
  ledger emission with `parent_record_ids` lineage, missing-price
  tolerance, no-mutation guarantee.

## Intraday phase scheduler (v1.2)

- `test_phases.py` (18) — `IntradayPhaseSpec` / `PhaseSequence`
  validation, ordered traversal, duplicate / unknown phase
  rejection, phase-id storage on records that carry `phase_id`.
- `test_phase_scheduler.py` (21) — `Scheduler.run_day_with_phases`
  dispatch through six intraday phases, MAIN-phase compatibility
  with v0 tasks, per-date run-mode guard rejecting mixed
  `date_tick` / `intraday_phase` advancement, scope reset on next
  date, deterministic order across phase ties.

## Institutional decomposition (v1.3)

- `test_institutions.py` (35) — `InstitutionProfile`,
  `MandateRecord`, `PolicyInstrumentProfile`,
  `InstitutionalActionRecord` validation; `InstitutionBook` CRUD /
  snapshot / ledger; the four-property action contract (explicit
  inputs / outputs / ledger record / no cross-space mutation);
  duplicate detection per record type; cross-references stored as
  data without resolution.

## External world process layer (v1.4)

- `test_external_processes.py` (44) — `ExternalFactorProcess` spec
  (constant / random_walk / ar1 / regime_switch),
  `ExternalFactorObservation` with `phase_id` field,
  `ExternalScenarioPoint` / `ExternalScenarioPath` storage,
  `ExternalProcessBook` CRUD / snapshot / ledger,
  `create_constant_observation` helper, duplicate detection,
  no-runtime-execution guarantee.

## Relationship capital (v1.5)

- `test_relationships.py` (31) — `RelationshipRecord` validation,
  directed-pair semantics, `RelationshipCapitalBook` CRUD /
  snapshot / ledger, `relationship_strength_updated` on update,
  `RelationshipView` latest-strength queries, `decay_spec` stored
  but not applied automatically, deterministic reads.

## First closed-loop reference economy (v1.6)

- `test_reference_loop.py` (5) — the v1 closing test.
  `ReferenceLoopRunner` chains `ExternalFactorObservation` →
  `InformationSignal` → `ValuationRecord` → `ValuationGap` →
  `InstitutionalActionRecord` → `InformationSignal` → `WorldEvent`
  → `event_delivered` (D+1). Verifies that every cross-reference
  field is wired correctly, that `parent_record_ids` form a complete
  causal graph reconstructable from the ledger alone, that
  direct-bus and space-driven publication produce equivalent ledger
  audit trails, and that the runner does not mutate any state
  outside the books that own each record type.

## Reference demo + replay + manifest (v1.7-public-rc1+)

- `test_reference_demo.py` (10) — the FWE Reference Demo runs
  end-to-end, populates eight spaces, emits all seven loop
  record types, links `parent_record_ids` correctly, does not
  mutate seeded prices / ownership, and uses only neutral
  identifiers.
- `test_reference_demo_replay.py` (6) — replay-determinism gate:
  two runs of the demo produce equal canonical ledger traces and
  equal SHA-256 digests.
- `test_reference_demo_manifest.py` (14) — manifest contract:
  required fields, ledger digest matches `replay_utils`, sha256
  hex shape, deterministic write, atomic parent-dir creation,
  graceful git-unavailable / not-a-repo paths, no ledger
  mutation.
- `test_reference_demo_catalog_shape.py` (8) — catalog-shape
  regression: `catalog["loop"]` is a Mapping with all 18 keys
  the runner reads; fails loudly if a degraded YAML parser is in
  use (PyYAML missing).

## Experiment harness (v1.8)

- `test_experiment_config.py` (43) — config schema (load,
  required-field validation, type / value validation, optional-
  section defaults), synthetic-only guard, code-built-config
  validation, base-config digest equivalence with the demo,
  manifest + digest write / skip, unimplemented-override
  boundaries, and a no-side-effects-on-the-demo regression.
- `test_ids.py` (12) — `WorldID` parsing, `build_world_id`,
  invalid-id rejection, `category_for_kind`. (Renamed from
  `tests.py` at v1.7-public-rc1+.)

## Interaction topology (v1.8.3)

- `test_interactions.py` (50) — `InteractionSpec` field
  validation; `InteractionBook` CRUD + duplicate rejection; every
  filter listing (by source space / target space / between
  spaces / interaction type / channel type / routine type);
  disabled-by-default + `include_disabled=True`; self-loops on
  the diagonal (`corporate → corporate`, `investors → investors`,
  `information → information`); channel multiplicity in one cell;
  tensor view shape `S × S × C` and determinism; matrix view
  count / enabled-count / channel-types / interaction-ids and
  determinism; snapshot determinism; ledger emission of
  `RecordType.INTERACTION_ADDED`; kernel wiring; no-mutation
  guarantee against every other v0 / v1 source-of-truth book.

## Performance boundary / sparse traversal discipline (v1.9.8)

- `test_living_reference_world_performance_boundary.py` (10) —
  pins the v1.9 living reference world's *traversal shape* with
  no new behaviour. `test_performance_boundary_doc_exists`
  asserts `docs/performance_boundary.md` exists and contains the
  expected section headings (Performance Boundary, Current loop
  shapes, Sparse gating principles, Future acceleration,
  Semantic caveat, "review is not origination", "demo-bounded").
  `test_default_living_world_total_run_record_count_matches_formula`
  asserts the **total** record count for a full default 4-period
  run sits in `[148, 180]` — lower bound = `P × (2F + F + 2(I+B)
  + IF + BF + 2(I+B))` = `4 × 37` = `148`, tight upper = lower +
  32-record infrastructure allowance. (The per-period count is
  37; the budget pinned here is the per-run total, not a
  per-period bound.)
  `test_per_period_record_count_is_constant_across_periods`
  asserts the per-period summary shape tuple
  (`corporate_signal_ids`, `firm_pressure_signal_ids`, valuations,
  credit reviews, etc.) is identical across all four periods.
  `test_pressure_signal_count_is_exactly_periods_times_firms`,
  `test_valuation_count_is_exactly_periods_times_investors_times_firms`,
  and `test_credit_review_count_is_exactly_periods_times_banks_times_firms`
  pin the three mechanism counts to their exact bounded products.
  `test_no_forbidden_mutation_records_appear` forbids
  `ORDER_SUBMITTED` / `PRICE_UPDATED` / `CONTRACT_CREATED` /
  `CONTRACT_STATUS_UPDATED` / `CONTRACT_COVENANT_BREACHED` /
  `OWNERSHIP_TRANSFERRED` from appearing in the ledger after a
  default sweep — those are trade / price / lending mutation
  events and v1.9 is review-only.
  `test_no_warning_or_error_records_during_default_sweep`
  asserts no `WARNING` / `ERROR` records appear (the default
  fixture is healthy by construction). The
  `count_expected_living_world_records` helper is exercised by
  two tests that pin its formula (`148` for the default fixture)
  and its linearity in `periods`.

## Reference bank credit review lite (v1.9.7) + v1.12.6 attention-conditioned helper

- `test_reference_bank_credit_review_lite.py` (51) — adapter
  satisfies `MechanismAdapter`; `MechanismSpec` carries the right
  vocabulary (`model_id == BANK_CREDIT_REVIEW_MODEL_ID`,
  `model_family == "credit_review_mechanism"`, `version == "0.1"`,
  `calibration_status == "synthetic"`,
  `stochasticity == "deterministic"`); adapter rejects a kernel
  argument; runs without a kernel (proves it reads
  `request.evidence` only); missing-evidence cases yield
  `status="degraded"` with conservative midpoint scores; all five
  scores in [0,1]; `operating_pressure_score` ==
  `pressure.overall_pressure`; `valuation_pressure_score` == 1 −
  mean(valuation.confidence); `information_quality_score` is a
  coverage metric (0.25 per channel); `overall_credit_review_pressure`
  == arithmetic mean of the four pressure-side scores
  (information_quality NOT in mean); deterministic across two
  fresh kernels; request not mutated; proposed signal carries
  every required field; `signal_type` label is verbatim
  `"bank_credit_review_note"`; metadata carries the eight boundary
  flags (`no_lending_decision`, `no_covenant_enforcement`,
  `no_contract_mutation`, `no_constraint_mutation`,
  `no_default_declaration`, `no_internal_rating`,
  `no_probability_of_default`, `synthetic_only`) and the
  `pressure_signal_id` / valuation lineage links; `related_ids`
  include the pressure signal and every consulted valuation on
  the firm; caller helper commits exactly one
  `InformationSignal` through `InformationBook.add_signal`;
  `evidence_refs` preserved verbatim on the `MechanismRunRecord`;
  `as_of_date` defaults to `kernel.clock.current_date`; full
  no-mutation guarantee against contracts / constraints / prices
  / ownership / valuations / corporate signals / pressure signals
  / observations / selected observation sets / exposures (the
  mechanism only *adds* one new credit review note plus its
  audit `mechanism_run`).

## Living-world mechanism integration (v1.9.6 + v1.9.7 + v1.12.7)

- `test_living_reference_world.py` (+9 v1.9.6 tests, +7 v1.9.7
  tests, +11 v1.12.7 tests, total 132) — v1.9.6 wires v1.9.4 firm-pressure-assessment
  and v1.9.5 valuation-refresh-lite into the multi-period sweep;
  v1.9.7 adds a third phase between valuation and reviews that
  runs `BankCreditReviewLiteAdapter` once per (bank, firm) per
  period. New tests pin: one pressure signal per firm per period;
  pressure signals resolve to stored
  `firm_operating_pressure_assessment` signals; one valuation per
  (investor × firm) per period; valuations resolve to stored
  `synthetic_lite_pressure_adjusted` records;
  `valuation.metadata["pressure_signal_id"]` points to the same
  firm's pressure signal for the same period (proves v1.9.5
  actually consumed v1.9.4's output, not coincidental ordering);
  `valuation.metadata` carries the four boundary flags
  (`no_price_movement` / `no_investment_advice` / `synthetic_only`);
  one credit review note per (bank × firm) per period; credit
  review signals resolve to stored `bank_credit_review_note`
  signals; `payload["pressure_signal_id"]` points to the firm's
  pressure signal for the same period; `related_ids` thread every
  valuation on the firm; the eight boundary flags are present
  verbatim in metadata
  (`no_lending_decision`, `no_covenant_enforcement`,
  `no_contract_mutation`, `no_constraint_mutation`,
  `no_default_declaration`, `no_internal_rating`,
  `no_probability_of_default`, `synthetic_only`); pressure /
  valuation / credit-review `mechanism_run` ids are unique per
  (subject, period); no-mutation guarantee narrowed to exclude
  `valuations` and `information_signals` (both now expected to
  grow) plus separate count-growth tests pinning exact growth
  (`investors × firms × periods` for valuations,
  `(investors+banks) × 2 + banks × firms` per period for
  signals); record-count budget updated (per period now ~37
  records; ≥ 148, ≤ 280); CLI smoke now expects
  `pressures=...` / `valuations=...` / `credit_reviews=...` in
  the trace, the integrated-chain summary line including
  "bank credit review lite" and the eight-flag boundary
  summary. The fixture is extended with firm exposures so the
  v1.9.4 mechanism produces non-zero output during the sweep,
  and the bank's selected observation sets are routed into the
  v1.9.7 evidence.

  v1.12.7 (`+11`) — the orchestrator-integration milestone that
  closes the v1.12.4 → v1.12.6 sequence. The per-period valuation
  phase and the per-period bank credit review phase in
  `world/reference_living_world.py` switch from the pre-existing
  v1.9.5 / v1.9.7 helpers to the v1.12.5 / v1.12.6
  attention-conditioned helpers. The default living reference
  world demo now uses the v1.12.3 `EvidenceResolver` substrate
  for **three mechanisms end-to-end**: investor intent (since
  v1.12.4), valuation lite (new in v1.12.7), and bank credit
  review lite (new in v1.12.7). Tests pin: every
  orchestrator-produced valuation carries the four v1.12.5
  attention-metadata keys (`attention_conditioned`,
  `context_frame_id`, `context_frame_status`,
  `context_frame_confidence`) plus the three v1.9.5 anti-claim
  flags (`no_price_movement` / `no_investment_advice` /
  `synthetic_only`); every orchestrator-produced bank credit
  review signal carries the v1.12.6 watch label
  (`information_gap_review` / `liquidity_watch` /
  `refinancing_watch` / `market_access_watch` / `collateral_watch`
  / `heightened_review` / `routine_monitoring`), the four
  context-frame metadata keys, and every one of the eight v1.9.7
  anti-claim flags (`no_lending_decision` /
  `no_covenant_enforcement` / `no_contract_mutation` /
  `no_constraint_mutation` / `no_default_declaration` /
  `no_internal_rating` / `no_probability_of_default` /
  `synthetic_only`); each valuation's `context_frame_id`
  references its valuer (one frame per investor on a date, not
  one frame per firm); each credit review signal's
  `context_frame_id` references its bank; the integrated v1.12.7
  sweep emits no forbidden ledger payload key (no `order` /
  `trade` / `rebalance` / `target_price` / `expected_return` /
  `recommendation` / `investment_advice` / `lending_decision` /
  `loan_approved` / `covenant_breached` / `default_declared` /
  `internal_rating` / `rating_grade` / `probability_of_default` /
  `pd` / `lgd` / `ead` / `loan_pricing` / `interest_rate` /
  `underwriting_decision` / `approval_status` / `loan_terms`)
  and no forbidden event types; canonical replay deterministic
  across two fresh runs; the new v1.12.7 default-fixture
  `living_world_digest` is **pinned** in a regression test so
  any future silent change to the orchestrator path or to the
  v1.12.5 / v1.12.6 helpers fails loudly; the v1.12.1 / v1.12.4
  constrained-regime divergence is preserved (every intent →
  `risk_flag_watch` or `deepen_due_diligence`); the constrained
  regime now also produces at least one non-routine
  bank-credit-review watch label across the run, proving the
  bank's resolved frame drives classification through the
  orchestrator path; the v1.9.1 trace report continues to render
  the integrated ledger slice without raising. The default-fixture
  `living_world_digest` moves from `d6b25704...` (v1.12.4 →
  v1.12.6, where the orchestrator still called the pre-existing
  helpers) to
  `2c748aa6e37b679d9d52984e7f2c252d434e6a2192f7fa58b71866e59f54b709`
  (v1.12.7) by design. Per-period record count and per-run window
  unchanged from v1.12.4 / v1.12.5 / v1.12.6.

  v1.12.6 (`+22`) — the new
  `run_attention_conditioned_bank_credit_review_lite(...)` helper
  alongside the preserved `run_reference_bank_credit_review_lite(...)`
  helper. The new helper resolves an `ActorContextFrame` for the
  bank (`actor_type="bank"`) via `world.evidence.resolve_actor_context`
  and runs the v1.9.7 adapter on the resolved frame ids only. A
  deterministic priority-order watch-label classifier
  (`information_gap_review` → `liquidity_watch` →
  `refinancing_watch` → `market_access_watch` → `collateral_watch`
  → `heightened_review` → `routine_monitoring`) layers a
  non-binding label on top of the existing v1.9.7 pressure scores.
  Tests pin: resolver-call + four context-frame metadata keys
  (`attention_conditioned`, `context_frame_id`,
  `context_frame_status`, `context_frame_confidence`); the v1.9.7
  boundary anti-claim metadata is preserved verbatim
  (`no_lending_decision` / `no_covenant_enforcement` /
  `no_contract_mutation` / `no_constraint_mutation` /
  `no_default_declaration` / `no_internal_rating` /
  `no_probability_of_default` / `synthetic_only`); reads-only-
  selected-or-explicit-evidence pin (an un-cited pressure signal
  in the kernel is *not* surfaced; helper takes the degraded
  path); unresolved-refs land in `metadata["unresolved_refs"]` and
  lower the frame confidence; `strict=True` raises
  `StrictEvidenceResolutionError` and emits no signal; per-rule
  classification (high liquidity → `liquidity_watch`, high funding
  need → `refinancing_watch`, restrictive environment →
  `market_access_watch`); selection refs flow through to evidence
  buckets (a pressure-signal id reachable only via a
  `SelectedObservationSet` lands in the signal bucket); the
  headline divergence test asserts three banks produce three
  distinct (watch_label, status) audit shapes on the same borrower
  (Bank A → `liquidity_watch` / completed; Bank B →
  `information_gap_review` / completed; Bank C →
  `information_gap_review` / degraded); no-mutation guarantee
  against every other source-of-truth book; ledger / signal
  payload / signal metadata carry no anti-field key (`buy` /
  `sell` / `lending_decision` / `loan_approved` / `loan_rejected`
  / `covenant_breached` / `covenant_enforced` / `default_declared`
  / `internal_rating` / `rating_grade` / `probability_of_default`
  / `pd` / `lgd` / `ead` / `loan_pricing` / `credit_pricing` /
  `interest_rate` / `underwriting_decision` / `approval_status` /
  `loan_terms` / `investment_advice` / `recommendation` /
  `contract_amended` / `constraint_changed`); only the existing
  `signal_added` event type is emitted; determinism across two
  fresh kernels with byte-identical signal payload + metadata;
  idempotency-via-`signal_id` (the v1.9.7 SignalBook contract
  refuses duplicates); `ALL_WATCH_LABELS` vocabulary export pin
  (the closed set is importable and contains no forbidden tokens
  like `buy` / `sell` / `rating` / `approved` / `rejected` /
  `default` / `pd` / `lgd` / `ead` / `advice` / `recommendation`
  / `underwrite`); defensive errors on `kernel=None` / empty
  `bank_id` / empty `firm_id`. Helper-level + tests milestone —
  the orchestrator continues to call the pre-existing v1.9.7
  helper, so the per-run record-count window and
  `living_world_digest` remain unchanged from v1.12.4.

## Reference valuation refresh lite (v1.9.5) + v1.12.5 attention-conditioned helper

- `test_reference_valuation_refresh_lite.py` (45) — adapter
  satisfies `MechanismAdapter`;
  `MechanismSpec` carries the right vocabulary
  (`model_id == VALUATION_REFRESH_MODEL_ID`,
  `model_family == "valuation_mechanism"`,
  `version == "0.1"`, `calibration_status == "synthetic"`,
  `stochasticity == "deterministic"`); adapter rejects a kernel
  argument; runs without a kernel (proves it reads
  `request.evidence` only); missing pressure evidence yields
  `status="degraded"` with `baseline_value` if supplied
  (otherwise `None`); pressure signal whose `subject_id` does
  not match `request.actor_id` is ignored; algorithm
  correctness — zero pressure → baseline; full pressure (1.0) →
  baseline × 0.70 + confidence 0.6; custom coefficient overrides
  via `request.parameters` work; deterministic across two fresh
  kernels; request not mutated; proposed valuation carries
  every required field; `method` label is verbatim
  `"synthetic_lite_pressure_adjusted"`; metadata carries the
  four boundary flags (`no_price_movement`,
  `no_investment_advice`, `synthetic_only`, `model_id`) and
  `pressure_signal_id` link; `related_ids` include the pressure
  signal; caller helper commits exactly one `ValuationRecord`
  through `ValuationBook.add_valuation`; `evidence_refs`
  preserved verbatim on the `MechanismRunRecord` (default
  concatenation order and explicit override); `as_of_date`
  defaults to `kernel.clock.current_date`; defensive errors on
  `kernel=None`, empty `firm_id`, empty `valuer_id`; full
  no-mutation guarantee against `prices`, `ownership`,
  `contracts`, `constraints`, `exposures`, `variables`,
  `institutions`, `external_processes`, `relationships`,
  `routines`, `attention`, `interactions`, and the signal count
  (the mechanism reads but does not emit signals); only one new
  ledger record per call (the `valuation_added` from
  `ValuationBook.add_valuation`); module constants and committed
  identifiers pass a word-boundary forbidden-token check.
  v1.12.5 (`+17`) — the new
  `run_attention_conditioned_valuation_refresh_lite(...)` helper
  records context-frame metadata on `record.metadata`
  (`attention_conditioned`, `context_frame_id`,
  `context_frame_status`, `context_frame_confidence`); reads
  only selected/explicit evidence (a globally-resident un-cited
  pressure signal is *not* surfaced); unresolved refs land in
  `metadata["unresolved_refs"]` and lower the frame confidence;
  strict mode raises `StrictEvidenceResolutionError` and emits no
  record on unknown refs; strict mode passes when all-resolving;
  the headline three-valuers / three-evidence-sets divergence
  test pins at least two distinct
  `(estimated_value, confidence)` triples on the same firm and
  same period; selection refs flow through to the resolved signal
  bucket (a pressure-signal id reachable only via a
  `SelectedObservationSet` lands in the signal bucket and the
  v1.9.5 haircut fires); no-mutation guarantee covers every other
  source-of-truth book in the kernel including
  `market_conditions`, `capital_market_readouts`,
  `market_environments`, and `firm_financial_states`; ledger
  payload and `record.metadata` carry no anti-field keys
  (`target_price` / `expected_return` / `recommendation` /
  `investment_advice` / `buy` / `sell` / `overweight` /
  `underweight` / `rebalance` / `target_weight` /
  `portfolio_allocation` / `execution` / `order` / `trade` /
  `forecast_value` / `real_data_value`) and no anti-field event
  types appear in the ledger; two fresh kernels with identical
  inputs produce byte-identical record output (determinism);
  idempotent on `valuation_id`; qualitative ordering pins (more
  resolved evidence → strictly higher confidence; unresolved refs
  → strictly lower confidence); defensive errors on
  `kernel=None`, empty `firm_id`, empty `valuer_id`; the
  v1.12.5 helper's committed record passes the word-boundary
  forbidden-token check (extended to also scan
  `record.metadata.context_frame_id`).

## Reference firm operating pressure assessment (v1.9.4)

- `test_reference_firm_pressure.py` (28) — adapter satisfies
  the v1.9.3 / v1.9.3.1 `MechanismAdapter` Protocol;
  `MechanismSpec` carries the right vocabulary
  (`model_id == FIRM_PRESSURE_MODEL_ID`,
  `model_family == "firm_financial_mechanism"`,
  `version == "0.1"`, `calibration_status == "synthetic"`,
  `stochasticity == "deterministic"`); adapter does not accept
  a kernel argument (passing one raises `TypeError`); adapter
  can run without a kernel (proves it reads `request.evidence`
  only); missing evidence yields `status="degraded"` rather
  than crashing; observation-only and exposure-only requests
  also yield degraded; all five pressure dimensions
  (input_cost / energy_power / debt_service / fx_translation /
  logistics) and `overall_pressure` are in `[0, 1]`;
  `overall_pressure` is the deterministic mean of the five;
  multi-exposure sums clamp to 1.0; two byte-identical seed
  kernels produce byte-identical outputs; the v1.9.3.1
  deep-freeze guarantee carries (apply doesn't mutate the
  request); proposed signal mapping carries every required
  field (signal_id / signal_type / subject_id / source_id /
  published_date / effective_date / visibility / payload /
  related_ids / metadata); payload includes all five pressure
  dimensions, `overall_pressure`, `evidence_counts`,
  `calibration_status="synthetic"`; metadata's `boundary`
  string is the verbatim *"pressure_assessment_signal_only;
  no financial-statement update; no decision; no auto-trigger"*;
  caller helper commits exactly one signal; resolved evidence
  hydrates `variable_group` from `WorldVariableBook`;
  `MechanismRunRecord.input_refs` preserves caller-supplied
  `evidence_refs` verbatim (default and explicit override);
  `as_of_date` defaults to `kernel.clock.current_date`;
  defensive errors on `kernel=None` and empty `firm_id`; full
  no-mutation guarantee against `valuations`, `prices`,
  `ownership`, `contracts`, `constraints`, `exposures`,
  `variables`, `institutions`, `external_processes`,
  `relationships`, `routines`, `attention`, `interactions`;
  the only new ledger record per call is the `signal_added`
  from `SignalBook.add_signal`; module constants and signal
  identifiers pass a word-boundary forbidden-token check.

## Mechanism interface contract (v1.9.3 + v1.9.3.1 hardening)

- `test_mechanism_interface.py` (65) — required-field contract
  on `MechanismSpec` (model_id / model_family / version /
  assumptions / calibration_status / stochasticity /
  required_inputs / output_types / metadata),
  `MechanismRunRequest` (request_id / model_id / actor_id /
  as_of_date / selected_observation_set_ids / **evidence_refs** /
  **evidence** / state_views / parameters / metadata — v1.9.3.1
  rename of the v1.9.3 `MechanismInputBundle`; the old name is
  pinned as a one-line alias to the same class),
  `MechanismOutputBundle`
  (request_id / model_id / status / proposed_signals /
  proposed_valuation_records /
  proposed_constraint_pressure_deltas / proposed_intent_records /
  proposed_run_records / output_summary / warnings / metadata),
  and `MechanismRunRecord` (run_id / request_id / model_id /
  model_family / version / actor_id / as_of_date / status /
  input_refs / committed_output_refs / parent_record_ids /
  input_summary_hash / output_summary_hash / metadata); all
  four dataclasses are immutable (`frozen=True`); empty required
  strings and empty tuple entries are rejected; non-Mapping
  proposal entries are rejected; `to_dict` JSON round-trips
  byte-identically; the `runtime_checkable` `MechanismAdapter`
  Protocol accepts a minimally-shaped class (with `spec` +
  `apply`) and rejects classes missing `apply`; the three
  vocabulary tuples (`MECHANISM_FAMILIES` ⊇ {firm_financial,
  valuation, credit_review, investor_intent, market};
  `CALIBRATION_STATUSES == {synthetic, public_data_calibrated,
  proprietary_calibrated}`; `STOCHASTICITY_LABELS ==
  {deterministic, pinned_seed, open_seed}`); constructing the
  interface dataclasses requires no kernel (anti-behavior
  invariant carried from v1.9.3).
- **v1.9.3.1 hardening additions**: `_freeze_json_like` /
  `_thaw_json_like` helpers tested directly (mapping →
  `MappingProxyType`; list / tuple → tuple; set → sorted-tuple;
  scalar passthrough; thaw round-trips back to mutable
  `dict` / `list`). Nested-mutation rejected on every
  JSON-like field of every dataclass —
  `MechanismSpec.metadata`, `MechanismRunRequest.evidence` /
  `state_views` / `parameters`, every
  `MechanismOutputBundle` proposal mapping + `output_summary`,
  `MechanismRunRecord.metadata`. `to_dict()` returns mutable
  copies. `MechanismInputBundle` is a one-line alias to
  `MechanismRunRequest`. `MechanismRunRecord.input_refs` and
  `committed_output_refs` preserve caller-supplied order
  verbatim — duplicates kept, no auto-dedupe / auto-sort.
  Adapter Protocol's `apply` signature uses
  `MechanismRunRequest`. The "adapter does not require kernel"
  anti-behavior test constructs an adapter that computes from
  `request.evidence` alone.

## Living world replay / manifest / digest (v1.9.2)

- `test_living_world_replay.py` (16) —
  `canonicalize_living_world_result(kernel, result)` returns the
  documented JSON-friendly dict (`format`, `run_id`,
  `period_count`, actor id tuples, ledger slice indices,
  `created_record_count`, `infra_record_count`,
  `per_period_record_count_total`, `created_record_ids`,
  sorted `record_type_counts`, per-period summaries,
  aggregated set differences, per-actor count triples,
  canonicalised ledger slice, boundary statement); the canonical
  view excludes volatile `record_id` / `timestamp` and rewrites
  `parent_record_ids` as slice-relative `parent_sequences`;
  `infra + per_period == created` algebra preserved;
  `record_type_counts` sums to `created_record_count`; canonical
  JSON round-trips through `json.dumps` / `json.loads`
  byte-identically; `living_world_digest` is 64-char lowercase
  hex SHA-256; canonical and digest are byte-equal across two
  fresh runs; the digest matches the explicit
  `hashlib.sha256(json.dumps(canonical, sort_keys=True,
  separators=(",", ":"), ensure_ascii=False))` recipe; the
  digest changes when a canonical field changes;
  `LIVING_WORLD_BOUNDARY_STATEMENT` matches the v1.9.1 reporter's
  verbatim string; canonicalize / digest are read-only; defensive
  errors on `kernel=None` and non-`LivingReferenceWorldResult`
  inputs.
- `test_living_world_manifest.py` (19) — manifest carries every
  required field; `manifest_version == "living_world_manifest.v1"`
  and `run_type == "living_reference_world"`; manifest's
  `living_world_digest` equals the standalone digest; counts
  (period / firm / investor / bank / created / infra /
  per-period / variable / exposure) match the result;
  `boundary_statement` matches the replay constant; optional
  `report_digest` appears only when a v1.9.1 report is supplied;
  defensive errors on `kernel=None` and non-result inputs;
  `_git_probe` returns a status dict with the canonical key set;
  missing-git environments yield `git_status == "git_unavailable"`
  without crashing; the writer produces deterministic JSON
  byte-identically across consecutive writes (`sort_keys=True`,
  `indent=2`, trailing newline); writer creates parent
  directories; writer leaves no `.tmp` file behind; writer
  returns the resolved `Path`; building + writing the manifest
  does not mutate any kernel book or the ledger length; CLI
  smoke tests for both `--manifest` and default modes.

## Living world trace report (v1.9.1)

- `test_living_world_report.py` (27) — `LivingWorldTraceReport`
  immutable shape and schema-level `__post_init__` validation
  (rejects `infra + per_period != created`); per-period
  `LivingWorldPeriodReport` records preserve `period_id`,
  `as_of_date`, `record_count_created`, and the corporate /
  review signal id tuples; `infra_record_count +
  per_period_record_count_total == created_record_count` (the
  v1.9.1-prep algebra); overall and per-period
  `record_type_counts` sum to their record counts and are sorted
  for determinism; `ordered_record_ids` matches
  `LivingReferenceWorldResult.created_record_ids` byte-identically;
  aggregated set differences (`shared_selected_refs`,
  `investor_only_refs`, `bank_only_refs`) match the unions of
  stored `kernel.attention.get_selection(...)` selections and
  are sorted alphabetically; per-actor count triples
  (`(actor_id, period_id, count)`) cover every period × actor
  and are sorted by `(period_id, actor_id)`; `to_dict` and
  `render_living_world_markdown` are byte-identical across two
  fresh kernels seeded identically; Markdown contains every
  required section heading and emits the hard-boundary statement
  verbatim — *"No price formation, no trading, no lending
  decisions, no valuation behavior, no Japan calibration, no
  real data, no investment advice."* — plus per-period table
  rows for every period; warnings emitted on tampered chain
  results (slice / chain mismatch, ledger truncated) without
  crashing; defensive errors on `kernel=None` and non-
  `LivingReferenceWorldResult` inputs; full read-only guarantee
  against every kernel book and the ledger length; CLI smoke
  tests for both `--markdown` and default modes.

## Living world report contract (v1.9.1-prep)

- `test_living_reference_world_report_contract.py` (12) —
  regression-gate test set that pins the v1.9.0 result schema
  invariants the future v1.9.1 reporter will rely on.
  `LivingReferenceWorldResult` and
  `LivingReferencePeriodSummary` are dataclasses; both expose the
  full required-field set documented in
  `docs/v1_9_living_world_report_contract.md`;
  `created_record_ids` matches the kernel ledger slice
  byte-identically; the v1.9.0 **infra prelude** (idempotent
  registrations before period 1) is an honest separate window —
  per-period `record_count_created` totals plus
  `infra_record_count` equal the chain delta; per-period
  metadata carries chronological `ledger_record_count_before /
  _after` indices that chain end-to-end from period 1 onward;
  investor and bank selection refs are tuples of non-empty
  strings reachable from `kernel.attention.get_selection`;
  pairwise set-difference (shared / investor_only / bank_only)
  resolves to non-empty data on the canonical seed; report-
  critical fields are deterministic across two fresh kernels
  seeded identically; the read paths the v1.9.1 reporter will
  use do not mutate any kernel book or the ledger length.

## Living reference world (v1.9.0)

- `test_living_reference_world.py` (27) —
  `LivingReferenceWorldResult` immutable shape;
  `LivingReferencePeriodSummary` per-period record
  (4 entries by default); per-period counts exact (one corporate
  signal + one corporate run per firm per period; one menu /
  selection / review-run / review-signal per investor and per
  bank per period); ledger grows in every period; every result
  id (corporate runs, corporate signals, menus, selections,
  review runs, review signals) resolves back to a stored record;
  `created_record_ids` matches `kernel.ledger.records[before:after]`
  byte-identically; investor and bank selections diverge per
  period; corporate signals appear in every actor's selection
  (they all watch `corporate_quarterly_report` by default);
  determinism — two fresh kernels seeded identically produce
  byte-identical structural summaries; default
  `period_dates` is the four 2026 quarter ends, with explicit
  override honored; defensive errors on `kernel=None`, empty id
  lists, and empty `period_dates`; full no-mutation guarantee
  against `valuations` / `prices` / `ownership` / `contracts` /
  `constraints` / `institutions` / `external_processes` /
  `relationships` (snapshots byte-equal before / after); also
  byte-equal on `exposures` and `variables` (the harness does not
  mutate them after the seed); `kernel.tick()` and
  `kernel.run(days=N)` do NOT auto-fire the chain; complexity
  budget — the default sweep produces ≥ 88 records (tight lower
  bound) and ≤ 200 records (loose upper bound that flags
  Cartesian-product drift); synthetic-only identifiers verified
  with a word-boundary forbidden-token check; CLI smoke test
  prints `[setup]` / `[period 1]` / `[period 4]` / `[ledger]`
  and the no-economic-behavior summary line.

## Ledger trace report (v1.8.15)

- `test_ledger_trace_report.py` (23) — `LedgerTraceReport`
  immutable shape and schema-level `__post_init__` validation
  (rejecting inconsistent indices, count mismatches);
  `build_endogenous_chain_report` produces a report whose
  `record_count`, `start_record_index`, and `end_record_index`
  match the kernel ledger slice from the chain result;
  `ordered_record_ids` matches `chain_result.created_record_ids`
  byte-identically on the canonical chain;
  `record_type_counts` sums to `record_count` and is sorted for
  determinism; role-bucketed ids
  (`routine_run_ids` / `signal_ids` / `menu_ids` /
  `selection_ids`) match the chain's primary ids; selection
  refs (`investor_selected_refs`, `bank_selected_refs`,
  `shared_selected_refs`, `investor_only_refs`, `bank_only_refs`)
  are carried through verbatim; default `report_id` formula and
  explicit override; audit metadata
  (`renderer == "v1.8.15"`, `chain_*_status` fields,
  `chain_as_of_date`, etc.); determinism — `to_dict` and
  `render_endogenous_chain_markdown` are byte-identical across
  two fresh kernels seeded identically; Markdown contains the
  expected section headings and event-type counts;
  validation warnings (ledger truncated after chain returned,
  count mismatch on a tampered chain result) without crashing;
  defensive errors on `kernel=None` or non-`EndogenousChainResult`
  inputs; full read-only guarantee against every kernel book and
  the ledger; CLI smoke tests confirming `--markdown` produces
  both the operational trace and the report and that the default
  mode produces only the trace.

## Endogenous chain harness (v1.8.14)

- `test_reference_endogenous_chain.py` (29) —
  `EndogenousChainResult` shape and immutability; every result
  id (corporate run, corporate signal, both attention profiles,
  both menus, both selections, both review runs, both review
  signals) resolves back to an actually-stored record in the
  kernel; phase counts are exact (one corporate run, two menus,
  two selections, two review runs, three signals); the ledger
  slice produced during the chain matches
  `created_record_ids` byte-identically (count, order, ids); the
  chain uses **only** the existing seven event types
  (`interaction_added`, `routine_added`, `routine_run_recorded`,
  `signal_added`, `attention_profile_added`,
  `observation_menu_created`, `observation_set_selected`); ledger
  ordering pinned (corporate → attention → investor review → bank
  review); investor review's `input_refs` includes the investor
  selection's refs (proving phase 3 ran after phase 2);
  heterogeneous attention propagates (investor vs bank
  `selected_refs` differ; `shared` / `investor_only` /
  `bank_only` agree with set membership; corporate signal lands
  in `shared_selected_refs`); determinism (two fresh kernels
  seeded identically produce byte-identical `EndogenousChainResult`
  values); status semantics (`completed` for the canonical seed;
  the no-exposure edge case still completes because the corporate
  signal flows through both selections); date defaulting to
  `kernel.clock.current_date` and explicit override; defensive
  rejection of `kernel=None` and empty `firm_id` / `investor_id`
  / `bank_id`; no-mutation guarantees against `valuations`,
  `prices`, `ownership`, `contracts`, `constraints`,
  `institutions`, `external_processes`, `relationships`, plus
  `exposures` / `variables` byte-equality across the call;
  `kernel.tick()` and `kernel.run(days=N)` do NOT execute the
  chain; synthetic-only identifiers verified with a
  word-boundary forbidden-token check.

## Investor / bank review routines (v1.8.13)

- `test_reference_review_routines.py` (32) — interaction
  registration on the Investors → Investors and Banking → Banking
  self-loops (channel types `investor_review_channel` /
  `bank_credit_review_channel`, `routine_types_that_may_use_this_channel`
  locked to the matching review type, idempotent re-registration);
  per-actor routine registration with the matching
  `allowed_interaction_ids`, idempotent re-registration, defensive
  rejection of empty `investor_id` / `bank_id`; the run flow
  writes exactly one `RoutineRunRecord` (via
  `RoutineEngine.execute_request` → `RoutineBook.add_run_record`)
  and exactly one `InformationSignal` (via
  `SignalBook.add_signal`), with bidirectional run↔signal links
  (`output_refs` ⊇ `{signal_id}` and `related_ids ==
  (run_id,)`, `metadata["routine_run_id"] == run_id`); ledger
  ordering pinned to `routine_run_recorded` → `signal_added`;
  selected `SelectedObservationSet` ids flow through the engine
  into `RoutineRunRecord.input_refs`; payload count summaries
  (`selected_signal_count`, `selected_variable_observation_count`,
  `selected_exposure_count`, `selected_other_count`) sum to
  `selected_ref_count`; status defaults to `"completed"` when
  refs flow through and `"degraded"` when they don't (anti-scenario
  rule), including the empty-selection edge case; date defaulting
  to `kernel.clock.current_date`, explicit `as_of_date` override;
  determinism (same kernel + seed → same run id, signal id, and
  payload across fresh kernels); strict no-mutation guarantees
  against `valuations`, `prices`, `ownership`, `contracts`,
  `constraints`, `exposures`, `variables`, `attention`,
  `institutions`, `external_processes`, `relationships`; only
  `RoutineBook` and `SignalBook` grow under the routine's writes;
  `kernel.tick()` and `kernel.run(days=N)` do NOT auto-fire
  either review routine; investor and bank `input_refs` differ
  when the underlying selections differ (heterogeneous attention
  propagates); synthetic-only identifiers verified with a
  word-boundary check that handles substring false positives
  (`tse` ⊂ `itself`).

## Reference attention demo + variable hooks (v1.8.12)

- `test_reference_attention_demo.py` (23) — end-to-end shape of
  `run_investor_bank_attention_demo`: result is immutable,
  exactly one `ObservationMenu` per actor is persisted through
  `AttentionBook.add_menu`, exactly one
  `SelectedObservationSet` per actor is persisted through
  `AttentionBook.add_selection`, the canonical investor / bank
  profiles register idempotently; heterogeneous selection
  semantics (the corporate-reporting signal is shared, investor
  picks fx + investor exposures, bank picks real-estate /
  energy + bank exposures, neither picks the other's axes,
  `shared_refs` / `investor_only_refs` / `bank_only_refs`
  agree with set membership); determinism across two fresh
  kernels (same selected refs, same set differences, same menu
  ids); ledger evidence using existing record types only
  (`OBSERVATION_MENU_CREATED` × 2 +
  `OBSERVATION_SET_SELECTED` × 2 per call, no new types); strict
  no-mutation guarantees against `valuations`, `prices`,
  `ownership`, `contracts`, `constraints`, `external_processes`,
  `institutions`, `relationships`; the demo runs no routine and
  emits no signal beyond optional setup; `kernel.tick()` and
  `kernel.run(days=N)` do NOT auto-fire the demo; defensive
  validation on empty `firm_id` / `investor_id` / `bank_id`;
  `as_of_date` defaults to `kernel.clock.current_date` when
  omitted.
- `test_attention.py` (9 new; 102 → 111) — v1.8.12 `AttentionProfile`
  extension acceptance: the four new fields
  (`watched_variable_ids`, `watched_variable_groups`,
  `watched_exposure_types`, `watched_exposure_metrics`) default
  to empty tuples, normalize lists to tuples, reject empty
  strings, round-trip through `to_dict`, appear in the
  `ATTENTION_PROFILE_ADDED` ledger payload, and extend
  `profile_matches_menu` so structural overlap is reported on
  the new dimensions.

## Observation menu builder (v1.8.11)

- `test_observation_menu_builder.py` (50) — `ObservationMenu`
  extension acceptance for the two new fields
  (`available_variable_observation_ids` and
  `available_exposure_ids`), their participation in
  `total_available_count()` and `to_dict()`, rejection of empty
  strings inside the new tuples, and the two new counts
  (`available_variable_observation_count`,
  `available_exposure_count`) in the existing
  `OBSERVATION_MENU_CREATED` ledger payload;
  `ObservationMenuBuildRequest` field validation (parametrized
  rejection of empty required strings, non-bool include flags),
  frozen dataclass, `to_dict` round-trip; `build_menu` end-to-end
  flow writing exactly one `ObservationMenu` through
  `AttentionBook.add_menu` (and exactly one ledger record),
  result-mirrors-stored-menu, default `menu_id` formula
  (`menu:` + `request_id`), `metadata["menu_id"]` override,
  `metadata["status"]` override; date semantics
  (`request.as_of_date` overrides clock; clock default; missing
  date raises `ObservationMenuBuildMissingDateError`);
  exposure→variable join semantics (only variables the actor is
  exposed to surface; no-exposure ⇒ empty
  `available_variable_observation_ids` by default; visibility
  filter (`visible_from_date <= as_of_date`) admits and rejects
  correctly); inactive exposures (effective_to in past) excluded
  from both `available_exposure_ids` and the variable join;
  exposure scoping by `subject_id`; signal collection through
  `SignalBook.list_visible_to` (private signals excluded);
  `available_interaction_ids` union from
  `carried_by_interaction_id` + signal `metadata["interaction_id"]`,
  with deduplication; status auto-derivation
  (`completed` / `empty`) and caller override; include flags
  (`include_signals` / `include_variables` / `include_exposures`)
  skip the corresponding collector; preview path produces no
  persisted menu and no ledger record, returns same content as
  build, prefixes id with `menu:preview:`; read-only collectors
  (`collect_visible_signals`, `collect_active_exposures`,
  `collect_visible_variable_observations`); kernel wiring
  (`kernel.observation_menu_builder` exposed, books and clock
  shared); `kernel.tick()` and `kernel.run(days=N)` do NOT
  auto-build menus; no-mutation guarantee against `SignalBook`,
  `WorldVariableBook`, and `ExposureBook`;
  `DuplicateObservationMenuError` raised when the same
  `menu_id` is built twice.

## Exposure / dependency layer (v1.8.10)

- `test_exposures.py` (59) — `ExposureRecord` field validation
  (parametrized rejection of empty required strings, magnitude /
  confidence bounds in `[0.0, 1.0]`, bool rejection on numeric
  fields, inverted validity windows, empty entries in
  `source_ref_ids`); `is_active_as_of` semantics covering inside
  / before / after / inclusive at bounds / open-ended on each
  side / both bounds open cases; date coercion on optional date
  fields; tuple normalization for `source_ref_ids`; frozen
  dataclass; `to_dict` round-trip; CRUD with
  `DuplicateExposureError` / `UnknownExposureError`;
  cross-reference rule (`variable_id` NOT validated against
  `WorldVariableBook`); every filter listing using a
  six-record realistic synthetic seed (food processor /
  property operator / bank / macro fund / electricity-intensive
  manufacturer / AI-exposed labor sector — exactly the
  examples called out in the v1.8.10 task);
  `list_active_as_of` filtering with both ISO date strings and
  `date` objects; snapshot determinism with `exposure_count`
  and sorted-by-id record list; ledger emission of
  `RecordType.EXPOSURE_ADDED` (`source = subject_id`,
  `target = variable_id`); kernel wiring (`exposures` field +
  shared ledger / clock); no-mutation guarantee against every
  other v0 / v1 source-of-truth book including
  `InteractionBook`, `RoutineBook`, `AttentionBook`, and
  `WorldVariableBook`; `kernel.tick()` and `kernel.run(days=N)`
  do NOT auto-create exposures.

## World variable book (v1.8.9)

- `test_variables.py` (91) — `ReferenceVariableSpec` and
  `VariableObservation` field validation (parametrized rejection
  of empty required strings, empty entries in tuple fields,
  non-numeric / out-of-bounds / bool-typed `confidence`, non-int
  `expected_release_lag_days`); date coercion on every date
  field; numeric (int / float) and string and `None` `value`
  acceptance; frozen dataclasses; `to_dict` round-trip;
  `WorldVariableBook` CRUD with duplicate rejection
  (`DuplicateVariableError` /
  `DuplicateVariableObservationError`) for both records; every
  filter listing for variables (by group / source space /
  related space / consumer space) and observations (by variable
  / `as_of_date` / channel); the visibility-filter rule —
  `visible_from_date` overrides `as_of_date` when present, in
  *both* directions (earlier and later); `latest_observation`
  deterministic tiebreaker (`visibility_date` desc →
  `as_of_date` desc → `observation_id` desc); `latest_observation`
  returns `None` when nothing visible or variable unknown;
  vintage / revision storage and retrieval; cross-reference rule
  (`variable_id` on observation NOT validated against the
  variables store); snapshot determinism with separate counts;
  ledger emission of `VARIABLE_ADDED` and
  `VARIABLE_OBSERVATION_ADDED` (with `simulation_date` from the
  observation's `as_of_date` and `correlation_id` from
  `carried_by_interaction_id`); kernel wiring; no-mutation
  guarantee against every other v0 / v1 source-of-truth book
  including `InteractionBook`, `RoutineBook`, and
  `AttentionBook`; `kernel.tick()` and `kernel.run(days=N)` do
  NOT auto-mutate variables or observations.

## Corporate quarterly reporting routine (v1.8.7)

- `test_corporate_reporting_routine.py` (26) — registration
  helpers (`register_corporate_reporting_interaction` /
  `register_corporate_quarterly_reporting_routine`) are
  idempotent and produce a Corporate → Corporate self-loop
  channel locked to the `corporate_quarterly_reporting`
  routine type, plus per-firm `RoutineSpec`s with the right
  `frequency` / `phase_id` / `missing_input_policy` /
  `allowed_interaction_ids`. The
  `run_corporate_quarterly_reporting` helper produces exactly
  one `RoutineRunRecord` and exactly one
  `corporate_quarterly_report` `InformationSignal` per call,
  linked by id (`signal.related_ids` and
  `signal.metadata["routine_run_id"]` back-reference the run;
  `record.output_refs` forward-references the signal). Default
  `status="completed"` when inputs are present; `status="degraded"`
  when `explicit_input_refs=()` (v1.8.1 anti-scenario discipline);
  date defaults to clock and explicit override honored;
  missing interaction or missing routine spec raise the
  v1.8.6 controlled errors; ledger ordering pinned to
  `routine_run_recorded` then `signal_added`; no-mutation
  guarantee against every other v0/v1 source-of-truth book;
  `kernel.tick()` and `kernel.run(days=N)` do NOT auto-run;
  signal payload + module constants are scanned for the
  forbidden Japan-name token list and asserted clean;
  multiple firms each get their own routine; the same firm
  across two quarters produces two distinct run records and
  signals.

## Routine engine (v1.8.6)

- `test_routine_engine.py` (50) — `RoutineExecutionRequest` field
  validation (parametrized rejection of empty required strings,
  empty entries in tuple fields); frozen dataclass + `to_dict`
  round-trip; `execute_request` end-to-end happy path producing
  exactly one `RoutineRunRecord`; `RoutineExecutionResult`
  mirrors the stored record; default `run_id` format
  (`"run:" + request_id`) and metadata-`run_id` override; date
  semantics (request override > clock fallback > controlled
  `RoutineExecutionMissingDateError`); `collect_selected_refs`
  preserves declaration order across selections and raises
  `RoutineExecutionUnknownSelectionError` on missing ids;
  explicit + selected refs combine deterministically with
  first-occurrence dedup; status defaults
  (`"completed"` with inputs / `"degraded"` without; explicit
  override preserved); interaction compatibility (compatible
  passes; not-in-allowed-list raises; not-admitting-routine-type
  raises; unknown-interaction fails execution with
  `RoutineExecutionIncompatibleInteractionError`); attention
  compatibility (unknown selection raises;
  subset-of-menu NOT enforced per v1.8.5);
  `RoutineExecutionValidationError` on unknown / disabled
  routine; `parent_record_ids` flow from metadata to record;
  `selected_observation_set_ids` stored under run record's
  `metadata`; `validate_request` returns the same shape and
  raises the same controlled errors; `RoutineBook` ledger emits
  exactly one `routine_run_recorded` per request via the
  existing `add_run_record` path; kernel exposes
  `routine_engine`; `kernel.tick()` and `kernel.run(days=N)` do
  NOT auto-execute; no-mutation guarantee against every other
  v0 / v1 source-of-truth book including `InteractionBook`,
  `AttentionBook`, and `RoutineBook` snapshot before-and-after;
  the error hierarchy.

## Attention (v1.8.5)

- `test_attention.py` (102) — `AttentionProfile`,
  `ObservationMenu`, and `SelectedObservationSet` field validation
  (parametrized rejection of empty required strings, non-bool
  `enabled`, empty entries in tuple fields, non-numeric and
  bool-typed `priority_weights`, date coercion on `as_of_date`);
  tuple normalization; frozen dataclasses; `AttentionBook` CRUD +
  duplicate rejection (`DuplicateAttentionProfileError` /
  `DuplicateObservationMenuError` /
  `DuplicateSelectedObservationSetError`) for all three record
  types; every filter listing (`list_profiles_by_actor` /
  `list_profiles_by_actor_type` /
  `list_profiles_by_watched_space` / `list_profiles_by_channel`;
  `list_menus_by_actor` / `list_menus_by_date`;
  `list_selections_by_actor` / `list_selections_by_profile` /
  `list_selections_by_menu` / `list_selections_by_status`);
  multiple profiles per actor allowed; disabled-by-default with
  `include_disabled=True` opt-in; `priority_weights` preserved as
  numeric `dict[str, float]`; `missing_input_policy` defaults to
  `"degraded"`; empty / partial menus accepted; recommended
  selection status vocabulary (`"completed"` / `"partial"` /
  `"degraded"` / `"empty"`) round-trips cleanly;
  `selected_refs` not enforced as subset of menu (documented
  v1.8.5 behavior); `profile_matches_menu` shape, overlap-found,
  no-overlap, omits-unwatched-dimensions, unknown-profile raises,
  unknown-menu raises, no-mutation cases; snapshot determinism
  with separate enabled / disabled counts; ledger emission of
  all three new `RecordType` members (`attention_profile_added`,
  `observation_menu_created` with `simulation_date=as_of_date`,
  `observation_set_selected` with `correlation_id=routine_run_id`);
  kernel wiring; no-mutation guarantee against every other v0 /
  v1 source-of-truth book including `InteractionBook` and
  `RoutineBook`.

## Routines (v1.8.4)

- `test_routines.py` (72) — `RoutineSpec` and
  `RoutineRunRecord` field validation (parametrized rejection of
  empty required strings, non-bool `enabled`, empty entries in
  tuple fields); date coercion on `as_of_date`; tuple
  normalization; `RoutineBook` CRUD for both record types with
  duplicate rejection (`DuplicateRoutineError` /
  `DuplicateRoutineRunError`); every filter listing
  (`list_by_type` / `list_by_owner_space` / `list_by_frequency`
  / `list_for_interaction` for routines;
  `list_runs_by_routine` / `list_runs_by_date` /
  `list_runs_by_status` for runs); disabled-by-default + the
  `include_disabled=True` opt-in; the recommended status
  vocabulary (`"completed"` / `"partial"` / `"degraded"` /
  `"failed"`) round-trips cleanly; `missing_input_policy`
  defaults to `"degraded"` and stores any free-form label;
  `parent_record_ids` preserved on run records;
  `routine_can_use_interaction` predicate covering the positive
  case, the routine-type-not-allowed case, the
  not-in-allowed-interaction-ids case, the unknown-routine
  raises (`UnknownRoutineError`) case, the unknown-interaction
  returns False case, the empty-allowed-types-means-any case,
  and the no-mutation guarantee; snapshot determinism with
  separate enabled / disabled counts; ledger emission of
  `RecordType.ROUTINE_ADDED` and `RecordType.ROUTINE_RUN_RECORDED`;
  kernel wiring; no-mutation guarantee against every other v0 /
  v1 source-of-truth book including `InteractionBook`.

## Test count by component

### v0 components (frozen at v0.16)

| Component                        | Files | Tests |
| -------------------------------- | ----- | ----- |
| YAML load / validation           | 2     | 9     |
| Clock / scheduler / ledger / state | 4   | 29    |
| Kernel / spaces smoke            | 2     | 3     |
| Event bus + signal flow          | 2     | 15    |
| Network books                    | 3     | 38    |
| Projections (balance sheet, constraints) | 2 | 41 |
| Signals (signals + flow)         | 2     | 29    |
| DomainSpace                      | 1     | 10    |
| Domain spaces (state + integration) × 8 | 16 | 254 |
| Cross-space integration          | 1     | 16    |
| **v0 subtotal**                  | **35**| **444** |

### v1 components (frozen at v1.7)

| Component                        | Files | Tests |
| -------------------------------- | ----- | ----- |
| Valuation / fundamentals (v1.1)  | 1     | 34    |
| Intraday phase scheduler (v1.2)  | 2     | 39    |
| Institutional decomposition (v1.3) | 1   | 35    |
| External world process (v1.4)    | 1     | 44    |
| Relationship capital (v1.5)      | 1     | 31    |
| Reference loop (v1.6)            | 1     | 5     |
| **v1 subtotal**                  | **7** | **188** |

### v1.7-public-rc1+ / v1.8.x / v1.9.0 / v1.9.1-prep / v1.9.1 / v1.9.2 / v1.9.3 / v1.9.3.1 / CLI argv pin / v1.9.4 / v1.9.5 / v1.9.6 / v1.9.7 / v1.9.8 additions

| Component                               | Files | Tests |
| --------------------------------------- | ----- | ----- |
| Reference demo (v1.7-public-rc1)        | 1     | 10    |
| Replay determinism (v1.7-public-rc1+)   | 1     | 6     |
| Manifest (v1.7-public-rc1+)             | 1     | 14    |
| Catalog-shape regression (v1.7-public-rc1+) | 1 | 8     |
| Experiment harness config (v1.8)        | 1     | 43    |
| WorldID tests (renamed from tests.py)   | 1     | 12    |
| Interaction topology (v1.8.3)           | 1     | 50    |
| Routines (v1.8.4)                       | 1     | 72    |
| Attention (v1.8.5 + v1.8.12 schema)     | 1     | 111   |
| Routine engine (v1.8.6)                 | 1     | 50    |
| Corporate quarterly reporting (v1.8.7)  | 1     | 26    |
| World variable book (v1.8.9)            | 1     | 91    |
| Exposure / dependency layer (v1.8.10)   | 1     | 59    |
| Observation menu builder (v1.8.11)      | 1     | 50    |
| Reference attention demo (v1.8.12)      | 1     | 23    |
| Reference review routines (v1.8.13)     | 1     | 32    |
| Endogenous chain harness (v1.8.14)      | 1     | 29    |
| Ledger trace report (v1.8.15)           | 1     | 23    |
| Living reference world (v1.9.0)         | 1     | 27    |
| Living world report contract (v1.9.1-prep) | 1 | 12    |
| Living world trace report (v1.9.1)      | 1     | 27    |
| Living world replay (v1.9.2)            | 1     | 16    |
| Living world manifest (v1.9.2)          | 1     | 19    |
| Mechanism interface contract (v1.9.3 + v1.9.3.1) | 1 | 65    |
| CLI argv-isolation pin                  | 1     | 8     |
| Reference firm operating pressure (v1.9.4) | 1  | 28    |
| Reference valuation refresh lite (v1.9.5) + v1.12.5 attention-conditioned helper | 1  | 45    |
| Living-world integration (v1.9.6 — added in test_living_reference_world.py) | 0 | 9 |
| Reference bank credit review lite (v1.9.7) + v1.12.6 attention-conditioned helper | 1 | 51    |
| Living-world integration (v1.9.7 — added in test_living_reference_world.py) | 0 | 7 |
| Performance boundary (v1.9.8)           | 1     | 10    |
| Stewardship theme signal (v1.10.1)      | 1     | 58    |
| Portfolio-company dialogue record (v1.10.2) + investor escalation candidate (v1.10.3, added to test_engagement.py) | 1 | 105    |
| Corporate strategic response candidate (v1.10.3) + v1.10.4.1 type-correct industry-condition cross-reference slot + v1.11.0 type-correct market-condition cross-reference slot + v1.12.2 type-correct market-environment-state cross-reference slot (added to test_strategic_response.py) | 1 | 66    |
| Industry demand condition signal (v1.10.4) | 1 | 84    |
| Capital-market condition (v1.11.0) | 1 | 84 |
| Capital-market readout (v1.11.1) | 1 | 72 |
| Firm financial latent state (v1.12.0) | 1 | 116 |
| Investor intent signal (v1.12.1) + v1.12.4 attention-conditioned helper | 1 | 103 |
| Market environment state (v1.12.2) | 1 | 87 |
| EvidenceResolver / ActorContextFrame (v1.12.3 base + v1.13.6 interbank-liquidity bucket) | 1 | 98 |
| Living-world integration tests (v1.9.x core + v1.10.5 + v1.11.0 + v1.11.1 + v1.11.2 + v1.12.0 + v1.12.1 + v1.12.2 + v1.12.4 additive in test_living_reference_world.py — 15 v1.10.5, 8 v1.11.0, 7 v1.11.1, 15 v1.11.2, 9 v1.12.0, 9 v1.12.1, 11 v1.12.2, and 4 v1.12.4 integration tests; v1.12.3 is substrate-only and adds no living-world integration tests) | (counted under existing files) | (+15 v1.10.5 / +8 v1.11.0 / +7 v1.11.1 / +15 v1.11.2 / +9 v1.12.0 / +9 v1.12.1 / +11 v1.12.2 / +4 v1.12.4 in test_living_reference_world.py) |
| **post-v1.7 subtotal**                  | **39**| **1962** |

### v0 + v1 + post-v1.7 totals

| Layer                            | Files | Tests |
| -------------------------------- | ----- | ----- |
| v0                               | 35    | 444   |
| v1.0–v1.7 frozen reference       | 7     | 188   |
| Attention feedback (v1.12.8) + budget/decay/saturation (v1.12.9) | 1 | 122   |
| Settlement accounts (v1.13.1)        | 1     | 34    |
| Settlement payments (v1.13.2)        | 1     | 47    |
| Interbank liquidity (v1.13.3)        | 1     | 63    |
| Central-bank signals (v1.13.4)       | 1     | 78    |
| v1.13.5 integration                  | 1     | 15    |
| Corporate financing need (v1.14.1)   | 1     | 64    |
| Funding option candidate (v1.14.2)   | 1     | 99    |
| Capital structure review candidate (v1.14.3) | 1 | 105   |
| Corporate financing path (v1.14.4)   | 1     | 106   |
| Listed security + market venue (v1.15.1) | 1 | 132   |
| Investor market intent (v1.15.2)     | 1     | 87    |
| Aggregated market interest (v1.15.3) | 1     | 121   |
| Indicative market pressure (v1.15.4) | 1     | 118   |
| Market intent classifier (v1.16.1)   | 1     | 100   |
| Attention feedback (v1.16.3 union)   | 0     |  +23  |
| Living-world v1.16.3 integration     | 0     |  +11  |
| Display timeline (v1.17.1)           | 1     |  66   |
| Regime comparison panel (v1.17.2)    | 0     |  +18  |
| Regime comparison report (v1.17.2)   | 1     |  17   |
| Event / causal annotation (v1.17.3)  | 0     |  +26  |
| Regime comparison annotation (v1.17.3)| 0    |   +5  |
| Scenario driver template (v1.18.1)   | 1     |  56   |
| Scenario driver application (v1.18.2)| 1     |  72   |
| Scenario annotations (v1.18.3)       | 0     |  +23  |
| Scenario report (v1.18.3)            | 1     |  18   |
| Run export bundle (v1.19.1)          | 1     |  56   |
| Run export CLI (v1.19.2 / v1.19.3.1) | 1     |  28   |
| Information release (v1.19.3)        | 1     |  88   |
| Living-world monthly_reference (v1.19.3)| 0  |  +16  |
| Reference universe storage (v1.20.1) | 1     |  92   |
| Scenario schedule storage (v1.20.2)  | 1     |  90   |
| Scenario universe run profile (v1.20.3) — functional + boundary scans | 0 | +22 |
| Scenario universe run profile (v1.20.3) — performance boundary | 0 | +18 |
| Scenario universe CLI export (v1.20.4)  | 0     | +20   |
| Scenario universe UI rendering (v1.20.5) — HTML / CSS / JS only, no Python tests | 0 |  0  |
| post-v1.7 (v1.7-public-rc1+ / v1.8.x / v1.9.0 / v1.9.1-prep / v1.9.1 / v1.9.2 / v1.9.3 / v1.9.3.1 / CLI argv pin / v1.9.4 / v1.9.5 / v1.9.6 / v1.9.7 / v1.9.8 / v1.10.1 / v1.10.2 / v1.10.3 / v1.10.4 / v1.10.4.1 / v1.10.5 / v1.11.0 / v1.11.1 / v1.11.2 / v1.12.0 / v1.12.1 / v1.12.2 / v1.12.3 / v1.12.4 / v1.12.5 / v1.12.6 / v1.12.7 / v1.12.8 / v1.12.9 / v1.13.1 / v1.13.2 / v1.13.3 / v1.13.4 / v1.13.5 / v1.13.6 / v1.14.1 / v1.14.2 / v1.14.3 / v1.14.4 / v1.14.5 / v1.15.1 / v1.15.2 / v1.15.3 / v1.15.4 / v1.15.5 / v1.15.6 / v1.16.1 / v1.16.2 / v1.16.3 / v1.17.1 / v1.17.2 / v1.17.3 / v1.18.1 / v1.18.2 / v1.18.3 / v1.19.1 / v1.19.2 / v1.19.3 / v1.19.3.1) | 42 | 2313 |
| **Total**                        | **106**| **4764** |

## Auditing for jurisdiction-neutral identifiers

The v1 line is jurisdiction-neutral by design (see
`docs/v1_scope.md` and `docs/v1_release_summary.md`). When
auditing the tree for stray Japan-specific identifiers, prefer
the canonical token list maintained at
`world/experiment.py::_FORBIDDEN_TOKENS` (`toyota`, `mufg`,
`smbc`, `mizuho`, `boj`, `fsa`, `jpx`, `gpif`, `tse`, `nikkei`,
`topix`, `sony`, `jgb`, `nyse`) and use **word-boundary
matches**, not raw substring greps.

A naive `grep -RIn "tse\|jgb\|topix"` produces large numbers of
false positives because, e.g., `"tse"` is a substring of
`"itself"`. Use word boundaries instead:

```bash
grep -RInE "\b(toyota|mufg|smbc|mizuho|boj|fsa|jpx|gpif|tse|nikkei|topix|sony|jgb|nyse)\b" .
```

Some tokens (`JPY`, `USD/JPY`, `cash_jpy`, the v1.1 currency
display field) appear deliberately in v0 / v1 modules as
*examples* of free-form unit / currency labels — those are
**not** jurisdiction-specific behavior and are explicitly
allowed by `docs/v1_scope.md`. The forbidden-token list above
is the authoritative gate; new code that introduces any of
those tokens should fail review unless it is explicitly part
of the v2 calibration roadmap.

## How to interpret a failing test

If a test fails after this freeze, one of three things is true:

1. The freeze invariants have been broken. This is a regression and
   should be the default suspicion — every test in this inventory
   passed at v1.7 freeze.
2. The test environment differs from the freeze environment (e.g., a
   Python version that changed dict ordering, a timezone issue
   affecting date conversions). Check the test name against the
   inventory above to determine which invariant is being tested.
3. New code intentionally relaxed an invariant. In that case the
   relaxing commit should have updated this inventory and a milestone
   document explaining the decision.
