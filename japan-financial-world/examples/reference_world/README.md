# FWE Reference Demos

Three synthetic, jurisdiction-neutral demos sit in this directory:

1. **v1.6 reference loop** (`run_reference_loop.py`) — the original
   one-shot causal trace: external observation → signal →
   valuation → comparator → institutional action → follow-up
   signal → event → next-tick delivery.
2. **v1.8.14 endogenous chain** (`run_endogenous_chain.py`) — the
   non-shock chain shipped by the v1.8 stack: corporate quarterly
   reporting → heterogeneous investor / bank attention → investor /
   bank review → ledger trace report. **No external observation is
   required, and no shock is applied.** With `--markdown` the v1.8.15
   reporter renders a deterministic Markdown summary of every
   record the chain wrote.
3. **v1.9.0 living reference world** + **v1.9.1 trace report**
   (`run_living_reference_world.py`) — the multi-period sweep: 4
   quarters × 3 firms / 2 investors / 2 banks. Each quarter every
   firm publishes a synthetic report, the investor and the bank
   rebuild their menus, their selections diverge, and both run a
   review routine. Output is a compact `[setup]` / `[period N]` /
   `[ledger]` trace. With `--markdown` the v1.9.1 reporter
   appends a deterministic Markdown report covering setup, infra
   prelude, per-period table, attention divergence, ledger
   event-type counts, warnings, and the mandatory hard-boundary
   statement.

Both demos are research artifacts. **Neither is a market predictor,
investment advice, or a calibrated Japan model.** Every entity name
uses the `*_reference_*` synthetic naming convention. Every numeric
value is an illustrative round number, not a measurement.

## What is in this directory

| File                    | Purpose                                                     |
| ----------------------- | ----------------------------------------------------------- |
| `README.md`             | This file (entry point).                                    |
| `entities.yaml`         | Synthetic entity catalog: 5 firms, 2 banks, 3 investor types, 1 exchange, 1 real-estate market, 1 information source, 1 policy authority, 2 external factors, plus seed prices, seed ownership, and the loop parameters. |
| `expected_story.md`     | Per-step narrative of the ledger trace the script produces. |
| `run_reference_loop.py` | Runnable script that builds the demo kernel, walks the seven loop steps, advances two ticks, and prints a summary. |
| `run_endogenous_chain.py` | v1.8.14 endogenous chain demo. Builds a small synthetic seed kernel, runs `run_reference_endogenous_chain`, and prints a compact operational trace. With `--markdown` it appends the v1.8.15 deterministic ledger trace report. |
| `run_living_reference_world.py` | v1.9.0 multi-period sweep. Builds a small synthetic seed kernel (3 firms / 2 investors / 2 banks / 6 variables / 10 exposures) and runs `run_living_reference_world` over 4 quarterly periods. Prints a compact `[setup]` / `[period N]` / `[ledger]` trace. |
| `replay_utils.py`       | `canonicalize_ledger(kernel)` and `ledger_digest(kernel)` helpers used by the v1 replay-determinism gate. |
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
