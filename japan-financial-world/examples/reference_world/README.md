# FWE Reference Demo

A single, synthetic, jurisdiction-neutral demo world that walks the
v1.6 reference loop end-to-end and produces a complete causal ledger
trace.

The demo's role is structural: it shows what FWE simulates and why
the ledger matters. **It is not a market predictor, not investment
advice, and not a calibrated Japan model.** Every entity name uses
the `*_reference_*` synthetic naming convention. Every numeric value
is an illustrative round number, not a measurement.

## What is in this directory

| File                    | Purpose                                                     |
| ----------------------- | ----------------------------------------------------------- |
| `README.md`             | This file (entry point).                                    |
| `entities.yaml`         | Synthetic entity catalog: 5 firms, 2 banks, 3 investor types, 1 exchange, 1 real-estate market, 1 information source, 1 policy authority, 2 external factors, plus seed prices, seed ownership, and the loop parameters. |
| `expected_story.md`     | Per-step narrative of the ledger trace the script produces. |
| `run_reference_loop.py` | Runnable script that builds the demo kernel, walks the seven loop steps, advances two ticks, and prints a summary. |
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
python examples/reference_world/run_reference_loop.py
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

## What this demo represents

- An external macro factor is observed.
- A signal is emitted referencing the observation.
- A research desk records a valuation referencing the signal.
- A comparator computes a `ValuationGap` against the seed price.
- An institution records an action referencing the valuation and
  gap; its `parent_record_ids` link the ledger lineage.
- A follow-up signal is emitted referencing the action.
- A `WorldEvent` is published; on the next tick it is delivered to
  banking + investors.

## What this demo does NOT represent

- No price formation. Prices do not move.
- No trading. Investor portfolios are static.
- No bank credit decisions or default detection.
- No corporate actions or earnings updates.
- No policy reaction or rate-setting rule.
- No information dynamics (no rumor propagation, no credibility
  updates).
- No scenarios, scenario branching, or stress logic.
- No Japan-specific calibration of any kind.

The demo's job is to make the v1 record-shape and audit-trail
contract concrete and runnable. Anything beyond that is v1+
behavioral, v2 (Japan public), or v3 (Japan proprietary) territory.

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
