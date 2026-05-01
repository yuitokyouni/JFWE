# v1.8 Experiment Harness — Design

> **Status:** v1.8 milestone shipped (config-driven harness for the
> existing FWE Reference Demo). v1.8.x will widen the harness to
> drive the optional config sections.
> **Layer:** FWE Core (public, jurisdiction-neutral).
> **Depends on:** v1.7 freeze + v1.7-public-rc1 hygiene + the
> reference demo + the manifest writer + the replay-determinism
> gate.
> **Blocks:** v1.8.x parameterization milestones; v2 (Japan public
> calibration) — v2 calibration runs will use this harness shape
> (with v2-specific schema extensions) rather than re-inventing one.

## Why an experiment harness exists

The v1.7-public-rc1 reference demo answered "what does FWE actually
do?" by running a fixed seven-step causal chain end-to-end. That
demo is enough to *show* the engine, but not enough to *experiment
with* it: the demo's parameters are hardcoded in
`run_reference_loop.py`, the entity catalog is bundled, and there
is no first-class way to record "I ran the demo this way on this
date with this code; here is the digest of what I got."

The v1.8 experiment harness fills that gap **without adding new
simulation behavior**. It:

1. Takes a YAML config describing one experiment.
2. Validates the config against a small synthetic-only schema.
3. Runs the existing reference demo.
4. Writes a manifest + replay digest under the config's
   `output_dir`.

After v1.8, any future experiment — a v1.8.x parameter sweep, a
v2 calibrated run, a v3 proprietary stress test — uses *this* shape
(load config → validate → run → manifest) rather than each
milestone re-inventing a driver.

## How the harness differs from simulation behavior

This is the most important boundary in v1.8.

The harness is a **driver / orchestrator**. It chooses *which*
record-producing functions to call and *what* to record about the
call. It does not implement any record-producing logic itself.

Specifically, the harness does **not** add:

- price formation, order matching, market microstructure
- bank credit decisions, default detection
- investor strategy, allocation, rebalancing
- corporate actions, earnings updates
- policy reaction functions, rate-setting rules
- runtime execution of `ExternalFactorProcess` specs
- automatic relationship-strength decay
- iterative loops or year-long simulation drivers
- new ledger record types
- new book APIs
- new scheduler extensions

All of those would be **v1+ behavioral milestones** — separate from
the harness, with their own design documents, their own tests, and
their own milestone releases. The harness's job is to *call* them
once they exist; the harness's existence is not a license to add
them.

In v1.8, the harness's runtime support is intentionally narrow: it
delegates to the bundled demo and rejects any config that would
require alternate behavior. The schema documents the v1.8.x
extension points so future milestones know where to plug in.

## How v1.8 supports reproducibility

A v1.8 experiment run produces three durable artifacts:

1. **The config itself** — checked into source control (or
   distributed alongside results), naming the run via `run_id` and
   `run_label`.
2. **`{output_dir}/manifest.json`** — the existing demo manifest
   (git_sha / git_dirty / python_version / platform / input_files
   / ledger_digest / ledger_record_count / summary) plus an
   `experiment` block carrying the config schema version, the
   run_id, the run_label, and the full config-as-used.
3. **`{output_dir}/ledger_digest.txt`** — the canonical SHA-256
   ledger digest as a single hex string + trailing newline. This
   is the same digest the v1 replay-determinism gate computes; if
   two runs of the same config yield different digests, something
   non-deterministic was introduced.

The pieces compose. Given a manifest:

- The `git_sha` + `git_dirty` tell you the exact source state.
- The `experiment.config_used` tells you the exact run parameters.
- The `input_files` sha256 tells you the exact entity catalog.
- The `ledger_digest` lets a future re-run prove the trace
  matched.

Anyone who has the source at `git_sha` and the same config can
re-run the experiment and assert the digest matches. That is the
v1.8 reproducibility contract.

## Why Japan calibration is deferred

v1.8 is **jurisdiction-neutral**. The harness rejects any config
containing forbidden tokens (toyota, mufg, smbc, mizuho, boj, fsa,
jpx, gpif, tse, nikkei, topix, sony, jgb, nyse — the same list the
reference-demo hygiene test enforces). This is enforced before any
file-system or kernel work; a config with a forbidden token cannot
load.

Japan calibration belongs to v2 (`docs/roadmap/jfwe_public_calibration.md`),
which introduces a different — and richer — schema:

- per-source license metadata (redistribution rights, attribution
  requirements, snapshot date),
- mapped entities under `jurisdiction_label="JP_public"`,
- public-data ingestion adapters per source,
- a calibration-snapshot identifier so a v2 run is reproducible
  from a fixed public-data snapshot date.

The v1.8 harness deliberately does **not** anticipate that schema.
Future v2 calibration will grow its own config type (`v2-calibration-
config`) that loads + validates differently, and the v1.8 harness
will continue to handle synthetic-only reference experiments.
Splitting the schema by jurisdiction-vs-neutral keeps each layer's
review cadence independent — a v2 schema change should not break a
v1.8 reference run, and vice versa.

## Schema (v1)

### Required fields

| Field | Type | Notes |
| --- | --- | --- |
| `run_id` | str | stable identifier; appears in the manifest |
| `run_label` | str | human-readable label |
| `start_date` | str | ISO `YYYY-MM-DD`; v1.8 only `"2026-01-01"` |
| `days` | int | `>= 1`; v1.8 only `2` |
| `execution_mode` | str | `"date_tick"` or `"intraday_phase"`; v1.8 only `"date_tick"` |
| `input_entities_path` | str | repo-relative or absolute path; v1.8 only the bundled demo file |
| `output_dir` | str | where artifacts are written |
| `manifest_enabled` | bool | toggle: write `manifest.json` |
| `replay_digest_enabled` | bool | toggle: compute + write `ledger_digest.txt` |

### Optional sections

Each is a list of mappings. v1.8 round-trips them through the
manifest but **does not act on them**; setting any of them
non-empty raises `NotImplementedError` at run time.

| Section | Reference-loop step it will drive in v1.8.x |
| --- | --- |
| `external_observations` | Step 1 — `record_external_observation` |
| `signal_templates` | Steps 2 / 6 — `emit_signal_*` |
| `valuation_templates` | Steps 3 / 4 — `record_valuation_from_signal` + `compare_valuation_to_price` |
| `institutional_actions` | Step 5 — `record_institutional_action` |
| `event_delivery_targets` | Step 7 — `publish_signal_event` |

### Synthetic-only guard

Every string anywhere in the config (including inside optional
sections) is scanned case-insensitively for forbidden tokens. A hit
raises `ExperimentConfigError` (a subclass of `ValueError`) before
any other validation work. The list is the same one
`tests/test_reference_demo.py` enforces against the demo's ledger.

## API

```python
from world.experiment import (
    ExperimentConfig,
    ExperimentConfigError,
    ExperimentResult,
    load_experiment_config,
    validate_experiment_config,
    run_reference_experiment,
)

config = load_experiment_config(
    "examples/reference_world/configs/base.yaml"
)
result = run_reference_experiment(config)

result.ledger_digest    # str | None
result.manifest_path    # Path | None
result.digest_path      # Path | None
result.kernel           # populated WorldKernel
result.summary          # DemoSummary
```

`load_experiment_config(path)` performs YAML parse + schema
validation + synthetic-only guard. `validate_experiment_config(cfg)`
re-runs the same schema checks on a code-built config; tests use
this when constructing configs in code instead of YAML.

## Files in this milestone

- `world/experiment.py` — the harness (config loader, validator,
  runner, dataclasses).
- `examples/reference_world/configs/README.md` — entry point for
  the configs directory + schema summary.
- `examples/reference_world/configs/base.yaml` — canonical starter
  config; mirrors the bundled demo's parameters and produces the
  same ledger digest.
- `docs/v1_experiment_harness_design.md` — this document.
- `tests/test_experiment_config.py` — 43 tests covering load,
  required-field validation, type / value validation, defaults,
  synthetic-only guard, code-built config validation,
  digest-equivalence with the demo, manifest + digest write,
  manifest + digest skip, unimplemented-override boundaries
  (custom entities path, custom days, intraday_phase, non-empty
  optional sections), and no-side-effects-on-the-demo regression.

No file under `world/` (other than the new `experiment.py`),
`spaces/`, `examples/reference_world/run_reference_loop.py`,
`examples/reference_world/replay_utils.py`, or
`examples/reference_world/manifest.py` is modified. The 674 v1
tests are unchanged; v1.8 adds 43 tests for a new total of **717
passed**.

## Next steps (v1.8.x)

In rough order:

- **v1.8.1**: support `input_entities_path` overrides — load a
  user-supplied synthetic catalog instead of the bundled one.
  Synthetic-only guard still applies.
- **v1.8.2**: support `days` overrides + a custom `start_date`.
  Requires verifying that the next-tick rule is preserved across
  longer runs.
- **v1.8.3**: support the `external_observations` section to drive
  Step 1.
- **v1.8.4 → v1.8.7**: progressively wire `signal_templates` /
  `valuation_templates` / `institutional_actions` /
  `event_delivery_targets`.
- **v1.8.8**: support `execution_mode = "intraday_phase"` so the
  harness can drive the v1.2 phase scheduler.

Each of those is a discrete, scope-bounded milestone. None of them
re-introduces simulation behavior; they only widen what the
harness can drive among the already-existing v1 record types.
