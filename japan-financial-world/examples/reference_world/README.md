# FWE Reference Demos

Three synthetic, jurisdiction-neutral demos sit in this directory.
The **headline demo at v1.9.last** is the multi-period living
reference world; the older single-shot demos are kept as smaller
explainers and as reproducibility baselines for earlier releases.

1. **v1.9 living reference world** (`run_living_reference_world.py`)
   — **the v1.9.last public prototype headline.** A multi-period
   sweep: 4 quarters × 3 firms / 2 investors / 2 banks. Each
   period runs corporate quarterly reporting → firm
   operating-pressure assessment (v1.9.4) → heterogeneous
   investor / bank attention → valuation refresh lite (v1.9.5) →
   bank credit review lite (v1.9.7) → investor / bank review
   routines. Output is a compact `[setup]` / `[period N]` /
   `[ledger]` trace; `--markdown` appends the v1.9.1
   deterministic Markdown report; `--manifest path` writes a
   v1.9.2 reproducibility manifest with a SHA-256
   `living_world_digest`. Two consecutive runs are byte-identical
   for each mode. Per-period writes 37 ledger records; a full
   default 4-period run total sits in `[148, 180]` records.
2. **v1.8.14 endogenous chain** (`run_endogenous_chain.py`) — the
   non-shock chain shipped by the v1.8 stack: corporate quarterly
   reporting → heterogeneous investor / bank attention → investor /
   bank review → ledger trace report. Single-period explainer.
   With `--markdown` the v1.8.15 reporter renders a deterministic
   Markdown summary of every record the chain wrote.
3. **v1.6 reference loop** (`run_reference_loop.py`) — the original
   one-shot causal trace, kept as the v1.7-era manifest /
   replay-determinism baseline: external observation → signal →
   valuation → comparator → institutional action → follow-up
   signal → event → next-tick delivery.

All three are research artifacts. **None is a market predictor,
investment advice, or a calibrated Japan model.** Every entity
name uses the `*_reference_*` synthetic naming convention. Every
numeric value is an illustrative round number, not a measurement.

**v1.9.last public prototype: what runs each period and what is
explicitly out of scope.**

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

**Hard boundary (v1.9.last).** No price formation. No trading. No
lending decisions, loan origination, or covenant enforcement. No
contract or constraint mutation. No firm financial-statement
updates. No canonical valuations. No Japan calibration. No real
data. No scenarios. No investment advice — direct or indirect.

**v1.12.last endogenous attention loop (frozen 2026-05-04).**
Layered on top of the v1.9.last substrate, the v1.12 sequence
closes a minimal endogenous attention-feedback loop:

```
market environment → firm latent state → selected evidence
  → investor intent / valuation lite / bank credit review lite
  → attention feedback → next-period selected evidence
  → budget / decay / crowding / saturation
```

The loop is **synthetic, deterministic, non-binding, replayable**.
Two consecutive runs produce byte-identical output. For the
single-page reader-facing summary see
[`../../docs/v1_12_endogenous_attention_loop_summary.md`](../../docs/v1_12_endogenous_attention_loop_summary.md);
for the full technical narrative see `world_model.md` §80–§92.
The v1.12.last hard boundary preserves every v1.9.last item
above and adds: no probabilistic forgetting / random decay, no
behavior probabilities, no LLM-agent execution, no calibrated
sensitivities — every step is integer-counted and
weight-deterministic.

### v1.12 regime-comparison demo

The simplest way to see the v1.12 endogenous loop in action is
to run the same fixture under three different market regimes
and diff the outputs:

```bash
cd japan-financial-world

python -m examples.reference_world.run_living_reference_world \
    --market-regime constructive --markdown

python -m examples.reference_world.run_living_reference_world \
    --market-regime constrained --markdown

python -m examples.reference_world.run_living_reference_world \
    --market-regime tightening --markdown
```

What to look for between the three regimes (period by period):

- **Firm financial latent state trajectory** (§80) — under
  `constructive`, the six pressure / readiness scalars decay
  below the 0.5 baseline; under `constrained` and `tightening`,
  they accumulate above baseline. Watch
  `funding_need_intensity` and `market_access_pressure` in
  particular.
- **Investor intent direction histogram** (§81 / §85) — the
  default `constructive` regime concentrates intents on
  `engagement_watch`; `constrained` and `tightening` shift the
  histogram toward `risk_flag_watch` and `deepen_due_diligence`.
- **Valuation confidence and audit shape** (§86 / §89) — the
  v1.12.5 attention-conditioned helper applies a small
  documented synthetic delta on top of the v1.9.5
  pressure-haircut formula. Under `constructive`, valuations
  land at higher `confidence`; under `constrained`, lower.
- **Bank credit review watch labels** (§88) — under
  `constructive`, every review lands on `routine_monitoring`;
  under `constrained`, the histogram includes `liquidity_watch`,
  `refinancing_watch`, `market_access_watch`, or
  `information_gap_review` depending on which firm states /
  market environments the bank actually selected.
- **Attention focus changes across periods** (§90) — period 0's
  attention state focus_labels reflect period 0's outcomes;
  period 1's reflect a mix (current period + decayed
  inheritance from period 0); under sustained regime, period 2+
  drops the unreinforced focus labels via the `decay_horizon=2`
  rule.
- **Memory-selected evidence and budget effects** (§91) — every
  memory `SelectedObservationSet` is bounded at
  `max_selected_refs=12` and `per_dimension_budget=3`. The
  `selected_refs` count never grows monotonically; the
  composition swaps as triggers swap.

Two runs of the same regime produce byte-identical Markdown
reports; two runs across regimes produce different reports
deterministically.

**v1.14.last corporate financing chain.** Layered on top of the
v1.9.last substrate and the v1.12.last attention loop, the v1.14
sequence ships a bounded corporate financing reasoning chain on
the per-period sweep. Per firm per period the orchestrator emits:

```
firm latent state / market environment / interbank liquidity / bank credit review / investor intent
  → 1 CorporateFinancingNeedRecord       (v1.14.1)
  → 2 FundingOptionCandidate records     (v1.14.2)
  → 1 CapitalStructureReviewCandidate    (v1.14.3)
  → 1 CorporateFinancingPathRecord       (v1.14.4 / v1.14.5)
```

Bounded by `P × F` per layer (`5 × firms = 15` records / period
on the default 3-firm fixture). The default 4-period sweep emits
**408 records** (up from `~348` at v1.13.last); the
integration-test `living_world_digest` is now
**`3df73fd4f152c16d1188f5c15b69bdc8a5cd6061b637ea35af671e86c6fa2d71`**
(moved at v1.14.5 by design). The markdown report (`--markdown`)
adds a `## Corporate financing` section with five histograms
(purpose / option-type / market-access / path-coherence /
path-constraint).

**Hard boundary preserved bit-for-bit.** Storage / audit /
graph-linking only — no financing execution, no loan approval,
no bond / equity issuance, no underwriting, no syndication, no
bookbuilding, no allocation, no interest rate / spread / fee /
coupon / offering price, no optimal capital structure decision,
no real leverage / D/E / WACC, no PD / LGD / EAD / rating, no
investment advice, no real data, no Japan calibration. See
[`../../docs/v1_14_corporate_financing_intent_summary.md`](../../docs/v1_14_corporate_financing_intent_summary.md)
for the v1.14 single-page summary.

**v1.15.last securities market intent aggregation.** Layered on
top of the v1.12.last attention loop and the v1.14.last corporate
financing chain, the v1.15 sequence ships a bounded securities-
market-interest aggregation chain on the per-period sweep with a
deterministic feedback path back into the corporate financing
review. Per period the orchestrator emits:

```
investor intent / valuation / firm state / market environment
  → investor market intent       (v1.15.2 — I × F = 6 records / period)
  → aggregated market interest   (v1.15.3 — F   = 3 records / period)
  → indicative market pressure   (v1.15.4 — F   = 3 records / period)
       │
       └→ cited by capital-structure review + financing path
                                  (v1.15.6 — citation slots only)
```

Setup-once: 1 `MarketVenueRecord` + `F = 3` `ListedSecurityRecord`.
Bounded by `O(P × I × F + 2 × P × F)` per layer (12 records per
period in the default 3-firm / 2-investor fixture). The v1.15.5
chain phase runs **before** the v1.14.5 corporate financing chain
phase so each firm's review and path can cite the same period's
pressure record. The v1.15.6 helper override forces the path's
`constraint_label` to `market_access_constraint` when pressure
says access is constrained / closed, and upgrades the
`coherence_label` to `conflicting_evidence` when pressure and
reviews disagree.

The default 4-period sweep emits **460 records** (unchanged from
v1.15.5 since v1.15.6 added zero new records — citation slots
only); the integration-test `living_world_digest` is now
**`bd7abdb9a62fb93a1001d3f760b76b3ab4a361313c3af936c8b860f5ab58baf8`**
(moved at v1.15.5 and v1.15.6 by design). The markdown report
(`--markdown`) adds a `## Securities market intent` section with
four histograms (intent direction / aggregated net interest /
pressure market access / pressure financing relevance).

**Hard boundary preserved bit-for-bit.** Market-interest
aggregation, not market trading. Indicative pressure, not price
formation. Feedback to corporate financing review, not financing
execution. No order submission, no buy / sell labels, no order
book, no matching, no execution, no clearing, no settlement, no
quote dissemination, no bid / ask, no price update, no
`PriceBook` mutation, no target price, no expected return, no
recommendation, no portfolio allocation, no real exchange
mechanics, no financing execution, no loan approval, no bond /
equity issuance, no underwriting, no syndication, no pricing, no
investment advice, no real data, no Japan calibration. The
`PriceBook` is byte-equal across the full default sweep — pinned
by tests at v1.15.5 and v1.15.6.

**Known limitation (v1.15.last).** v1.15.5 currently sets each
`InvestorMarketIntentRecord.intent_direction_label` via a
deterministic four-cycle rotation. This is acceptable for bounded
demo diversity but not yet endogenous in the v1.12 sense. The
v1.16 sequence will replace the rotation with an
evidence-conditioned classifier over the upstream investor
intent / valuation / firm state / market environment / attention
records. See
[`../../docs/v1_15_securities_market_intent_summary.md`](../../docs/v1_15_securities_market_intent_summary.md)
for the v1.15 single-page summary and the v1.16 plan.

## What is in this directory

| File                    | Purpose                                                     |
| ----------------------- | ----------------------------------------------------------- |
| `README.md`             | This file (entry point).                                    |
| `entities.yaml`         | Synthetic entity catalog: 5 firms, 2 banks, 3 investor types, 1 exchange, 1 real-estate market, 1 information source, 1 policy authority, 2 external factors, plus seed prices, seed ownership, and the loop parameters. |
| `expected_story.md`     | Per-step narrative of the ledger trace the script produces. |
| `run_reference_loop.py` | Runnable script that builds the demo kernel, walks the seven loop steps, advances two ticks, and prints a summary. |
| `run_endogenous_chain.py` | v1.8.14 endogenous chain demo. Builds a small synthetic seed kernel, runs `run_reference_endogenous_chain`, and prints a compact operational trace. With `--markdown` it appends the v1.8.15 deterministic ledger trace report. |
| `run_living_reference_world.py` | v1.9.0 multi-period sweep. Builds a small synthetic seed kernel (3 firms / 2 investors / 2 banks / 6 variables / 10 exposures) and runs `run_living_reference_world` over 4 quarterly periods. Prints a compact `[setup]` / `[period N]` / `[ledger]` trace. `--markdown` appends the v1.9.1 report; `--manifest path` writes the v1.9.2 reproducibility manifest. |
| `living_world_replay.py` | v1.9.2 `canonicalize_living_world_result(kernel, result)` + `living_world_digest(kernel, result)` — deterministic structural digest (64-char lowercase SHA-256) of the multi-period sweep. |
| `living_world_manifest.py` | v1.9.2 `build_living_world_manifest(kernel, result, ...)` + `write_living_world_manifest(manifest, output_path)` — atomic deterministic JSON manifest carrying the `living_world_digest`, structural counts, git revision (best-effort), Python / platform info, and the v1.9.1 hard-boundary statement. |
| `replay_utils.py`       | v1.7-era `canonicalize_ledger(kernel)` and `ledger_digest(kernel)` helpers used by the v1 replay-determinism gate. |
| `manifest.py`           | `build_reference_demo_manifest(kernel, summary)` and `write_manifest(manifest, path)` helpers for the reproducibility manifest (git_sha, python_version, platform, input file hashes, ledger digest, summary). |
| `configs/`              | YAML configs for the v1.8 experiment harness. `configs/base.yaml` mirrors the bundled demo and produces the same SHA-256 ledger digest. |

For the design rationale see
[`../../docs/fwe_reference_demo_design.md`](../../docs/fwe_reference_demo_design.md)
and (for the v1.8 harness)
[`../../docs/v1_experiment_harness_design.md`](../../docs/v1_experiment_harness_design.md).

## How to run

From the `japan-financial-world/` directory:

```bash
# v1.6 one-shot causal trace
python examples/reference_world/run_reference_loop.py

# v1.8.14 endogenous chain (operational trace only)
python -m examples.reference_world.run_endogenous_chain

# v1.8.14 chain + v1.8.15 deterministic Markdown ledger trace report
python -m examples.reference_world.run_endogenous_chain --markdown

# v1.9.0 living reference world (4 quarterly periods)
python -m examples.reference_world.run_living_reference_world

# v1.9.0 sweep + v1.9.1 deterministic Markdown trace report
python -m examples.reference_world.run_living_reference_world --markdown

# v1.9.2 reproducibility manifest (deterministic JSON + SHA-256 digest)
python -m examples.reference_world.run_living_reference_world \
    --manifest /tmp/living_world.manifest.json
```

Expected output (abbreviated):

```
[setup] registered N entities; ledger has M baseline records
[loop ] step 1 external_observation_added : <record_id>
[loop ] step 2 signal_added                : <record_id>
[loop ] step 3 valuation_added              : <record_id>
[loop ] step 4 valuation_compared           : <record_id>
[loop ] step 5 institution_action_recorded  : <record_id>
[loop ] step 6 signal_added                 : <record_id>
[loop ] step 7 event_published              : <record_id>
[tick ] day 1: 0 event_delivered (next-tick rule)
[tick ] day 2: 2 event_delivered (banking, investors)
[ledger] total records: <N>; record types:
  external_observation_added : 1
  signal_added                : 2
  valuation_added             : 1
  valuation_compared          : 1
  institution_action_recorded : 1
  event_published             : 1
  event_delivered             : 2
  ... (plus setup records)
```

The script returns the populated kernel for further interactive
inspection if imported as a module:

```python
import importlib.util, pathlib
path = pathlib.Path("examples/reference_world/run_reference_loop.py")
spec = importlib.util.spec_from_file_location("demo", path)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
kernel, summary = demo.run()
# kernel.ledger.records — full causal trace
```

## What `run_reference_loop.py` represents

- An external macro factor is observed.
- A signal is emitted referencing the observation.
- A research desk records a valuation referencing the signal.
- A comparator computes a `ValuationGap` against the seed price.
- An institution records an action referencing the valuation and
  gap; its `parent_record_ids` link the ledger lineage.
- A follow-up signal is emitted referencing the action.
- A `WorldEvent` is published; on the next tick it is delivered to
  banking + investors.

## What `run_endogenous_chain.py` represents

- A firm publishes a synthetic quarterly-report `InformationSignal`
  through the v1.8.7 corporate reporting routine.
- The v1.8.11 `ObservationMenuBuilder` builds one `ObservationMenu`
  per actor, surfacing the corporate signal plus visible variable
  observations gated by each actor's exposures.
- The v1.8.12 attention demo writes one
  `SelectedObservationSet` per actor, applying a structural
  selection rule against each `AttentionProfile`'s watch fields. The
  investor and the bank, looking at the same world, select
  different refs.
- The v1.8.13 review routines (`investor_review`, `bank_review`)
  consume those selections through `RoutineEngine`, persist one
  `RoutineRunRecord` each, and emit one synthetic review-note
  `InformationSignal` each.
- The v1.8.14 harness (`run_reference_endogenous_chain`) sequences
  the above and returns a deterministic `EndogenousChainResult`
  naming every record id the chain wrote.
- The v1.8.15 ledger trace report
  (`build_endogenous_chain_report` +
  `render_endogenous_chain_markdown`) projects the slice of the
  ledger the chain produced into a deterministic Markdown summary.

The chain is **fully endogenous** — no external observation,
shock, or scenario branch is required to make any of these records
appear.

## What these demos do NOT represent

- No price formation. Prices do not move.
- No trading. Investor portfolios are static.
- No bank credit decisions or default detection.
- No corporate actions or earnings updates.
- No policy reaction or rate-setting rule.
- No information dynamics (no rumor propagation, no credibility
  updates).
- No scenarios, scenario branching, or stress logic.
- No Japan-specific calibration of any kind.

The demos' job is to make the v1 record-shape and audit-trail
contract concrete and runnable. Anything beyond that is v1+
behavioral, v2 (Japan public), or v3 (Japan proprietary) territory.

The endogenous chain in particular is **infrastructure**, not
behavior — it shows that the v1.8 stack composes correctly, not
that any specific output should be acted upon.

## Read in this order

If you have not seen FWE before:

1. The repo-root [`README.md`](../../../README.md) for the project
   layers and the disclaimer.
2. [`expected_story.md`](expected_story.md) for what the ledger
   records mean.
3. `python examples/reference_world/run_reference_loop.py` to see
   the trace produced live.
4. [`../../docs/fwe_reference_demo_design.md`](../../docs/fwe_reference_demo_design.md)
   for the design rationale.
5. [`../../docs/v1_release_summary.md`](../../docs/v1_release_summary.md)
   for the broader v1 freeze surface.
