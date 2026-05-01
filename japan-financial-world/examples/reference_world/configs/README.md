# Reference Demo Experiment Configs

YAML configs for the v1.8 experiment harness
(`world/experiment.py`).

The harness loads a config, validates it (synthetic-only +
required-field checks), runs the bundled FWE Reference Demo, and
writes a manifest and ledger digest under the config's
`output_dir`. v1.8 only supports configs equivalent to the bundled
demo; future v1.8.x milestones will wire the optional sections so
configs can drive different observations / valuations / actions /
event deliveries.

## Files in this directory

| File | Purpose |
| --- | --- |
| `README.md` | This file. |
| `base.yaml` | Canonical starter config. Mirrors the bundled demo's parameters; running it produces the same SHA-256 ledger digest as `run_reference_loop.run()`. |

## Schema (v1)

```
run_id                  required str   stable identifier; appears in manifest
run_label               required str   human-readable label
start_date              required str   ISO YYYY-MM-DD; v1.8 only "2026-01-01"
days                    required int   >= 1; v1.8 only 2
execution_mode          required str   "date_tick" | "intraday_phase"; v1.8 only "date_tick"
input_entities_path     required str   path (repo-relative or absolute) to a synthetic entity catalog
output_dir              required str   where manifest + digest are written
manifest_enabled        required bool  toggle: write manifest.json
replay_digest_enabled   required bool  toggle: compute + write ledger_digest.txt

external_observations   optional list  v1.8.x: drive Step 1 (recorded but ignored in v1.8)
signal_templates        optional list  v1.8.x: drive Step 2 / 6
valuation_templates     optional list  v1.8.x: drive Step 3 / 4
institutional_actions   optional list  v1.8.x: drive Step 5
event_delivery_targets  optional list  v1.8.x: drive Step 7
```

A config that contains any forbidden token (real-firm /
jurisdiction-specific name) is rejected by
`load_experiment_config`. The forbidden list is jurisdiction-
neutral by construction; v2 (Japan public calibration) introduces
a separate, license-aware schema.

## Running a config

From the `japan-financial-world/` directory:

```python
from world.experiment import load_experiment_config, run_reference_experiment

config = load_experiment_config("examples/reference_world/configs/base.yaml")
result = run_reference_experiment(config)

print(result.ledger_digest)      # stable across runs
print(result.manifest_path)      # {output_dir}/manifest.json
print(result.digest_path)        # {output_dir}/ledger_digest.txt
```

`result.kernel` and `result.summary` are also available for
inspection (the same objects `run_reference_loop.run()` returns).

## Constraints v1.8 enforces at runtime

If a config sets `input_entities_path`, `start_date`, `days`, or
`execution_mode` to anything other than the demo defaults, or if
any optional section is non-empty, `run_reference_experiment`
raises `NotImplementedError` with a message naming the parameter
and the v1.8.x milestone where it will be wired. The schema is
validated up-front so the call fails before any kernel work, but
loading + validating still succeeds — the rejection is at the run
boundary, not at the schema boundary. This separation lets the
manifest / config-versioning machinery evolve independently of
runtime support.

## Adding a new config

1. Copy `base.yaml` to a new filename in this directory.
2. Pick a fresh `run_id` (no spaces; no forbidden tokens) and
   `run_label`.
3. Pick an `output_dir` that does not collide with other configs.
4. Leave the rest of the required fields at the v1.8-supported
   defaults until a future milestone widens the supported range.
5. The optional sections may be left as `[]` empty lists or filled
   with future-shape hints (commented-out in `base.yaml`); v1.8
   raises if any of them is non-empty at run time.

For the design rationale see
[`../../../docs/v1_experiment_harness_design.md`](../../../docs/v1_experiment_harness_design.md).
