# Release Checklist

A short, runnable checklist to walk before publicly tagging or
announcing a release of this repository. Most items are local
commands; a few are eyes-on review steps. The list is intentionally
short so it is actually used.

For the public / private rules these checks enforce, see
[`SECURITY.md`](SECURITY.md) and
[`japan-financial-world/docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md).

## Public release gate (must be green for a public release)

A **public release tag** (e.g., `v1.8-public-release`) requires CI
to be green on the commit being tagged. CI runs the items below
automatically; this section is the manual mirror so you can
reproduce locally before pushing.

### Latest readiness-review snapshot

Each readiness review records its result here so the next reviewer
can pick up where the last one stopped. Replace the snapshot when a
new review is performed.

- **Date:** 2026-05-02
- **Target:** v1.9.last public prototype freeze. The v1.8.0 public
  release (`v1.8-public-release` at commit `7fa2c42`) remains
  unchanged; v1.9.last freezes the v1.9 living reference world
  as the headline runnable artifact on top of that earlier
  release.
- **Status:** docs + tests frozen. The freeze is conditional on
  CI being green on the commit being tagged.
- **Local results (v1.9.last):**
  - `pytest -q` → 1626 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `python -m examples.reference_world.run_living_reference_world`
    → produces `[setup]` / `[period N]` / `[ledger]` trace;
    re-run yields byte-identical output
  - `... --markdown` → appends v1.9.1 deterministic Markdown report;
    re-run yields byte-identical output
  - `... --manifest /tmp/lw.json` → writes
    `living_world_manifest.v1` JSON; two runs into different
    paths diff to zero (modulo path)
  - Forbidden-token scan (word-boundary against
    `world/experiment.py::_FORBIDDEN_TOKENS`) → no hits in any
    object id, signal id, or example output
  - Public-wording audit → no "predicts markets",
    "production-ready", "Japan market simulator", buyout-target,
    or similar marketing framings in `README.md` or `docs/*.md`

#### v1.8.0 historical snapshot (unchanged)

- **Date:** 2026-05-01
- **Tag:** `v1.8-public-release`, pointing at commit `7fa2c42`
  ("ci: trigger workflow on version-tag pushes"). The same commit
  also carries `v1.8-public-rc2`.
- **Status:** released. All release-gate checks pass locally and
  on CI under the tag ref.
- **Local results:**
  - `pytest -q` → 725 passed
  - `compileall world spaces tests examples` → clean
  - `ruff check .` (repo root) → clean
  - `examples/reference_world/run_reference_loop.py` → produces
    seven loop record types + day-2 delivery to
    `(banking, investors)`
  - Replay-determinism gate (`tests/test_reference_demo_replay.py`)
    → 6 / 6 passed
  - Manifest gate (`tests/test_reference_demo_manifest.py`) →
    14 / 14 passed
  - Experiment-harness gate (`tests/test_experiment_config.py`) →
    43 / 43 passed
  - Catalog-shape regression (`tests/test_reference_demo_catalog_shape.py`)
    → 8 / 8 passed
  - Manifest sample build → ledger digest matches the digest the
    replay test asserts
  - Public-wording audit → zero hits in the "needs softening"
    category
  - Synthetic-ID audit → zero remaining real-name fixtures in
    `tests/` or `examples/`. Forbidden tokens (`toyota`, `mufg`,
    `boj`, etc.) appear only inside
    `tests/test_reference_demo.py` as the forbidden-list its
    hygiene test asserts must not appear in `object_id`s.
  - `gitleaks detect --redact --log-opts="--all"` (homebrew
    8.30.1, 46 commits, ~1.56 MB) → no leaks found
- **CI on tag ref:**
  - GitHub Actions run for `v1.8-public-release` (push event,
    headBranch=`v1.8-public-release`, sha=`7fa2c42`):
    `Tests + lint + demo` ✅ success, `Secret scan (gitleaks)` ✅
    success.
  - Same commit also passed CI under `main` and
    `v1.8-public-rc2` refs.
- **Notes for the next reviewer:**
  - The `secret-scan` CI job runs gitleaks-action with
    `continue-on-error: true` (license-key independent). Local
    gitleaks is the authoritative pre-tag check until a license
    token is wired.
  - No remaining release-blockers identified for v1.8.

### CI

- [ ] `.github/workflows/ci.yml` ran on the commit being tagged and
  every job is green. A red job blocks the public release; an
  intermittent flake should be investigated and fixed at the root,
  not retried.

## Code health (mirrors CI; reproducible locally)

- [ ] Dependencies installed via `pip install -e ".[dev]"` from
  the repo root. This brings in **PyYAML 6.x** (pinned
  `>=6,<7` as a runtime dep in `pyproject.toml`'s `[project]
  dependencies`) and pytest + ruff (under
  `[project.optional-dependencies] dev`). PyYAML is required for
  the reference demo and the v1.8 harness; the loader's fallback
  parser is a defensive minimal fallback (not a full YAML
  implementation) and will fail loudly via
  `tests/test_reference_demo_catalog_shape.py` if it ends up in
  use. Adopting PyYAML 7.x is a deliberate version-bump milestone
  and should not happen by an unpinned upgrade.
- [ ] `pytest -q` from `japan-financial-world/` reports the expected
  passing total. v1.8 + post-rc1 CI fix: `725 passed`. v1.9.last
  freeze: `1626 passed`. Use the count of the milestone being
  tagged; mismatch means the tree is not the freeze tree.
- [ ] `python -m compileall world spaces tests examples` from
  `japan-financial-world/` succeeds (no syntax errors anywhere,
  including the reference demo and test files).
- [ ] `ruff check .` from repo root passes against the
  `[tool.ruff]` config in `pyproject.toml`. The starter rule set
  is `select = ["E", "F"]` with `ignore = ["E501", "E402"]`;
  if the release tightens this, note the change in the release
  note.
- [ ] FWE Reference Demo runs end-to-end:
  `python examples/reference_world/run_reference_loop.py`
  from `japan-financial-world/` produces the seven loop
  record types and day-2 delivery to `(banking, investors)`.
- [ ] Replay determinism: two runs of the reference demo
  produce the same canonical ledger trace and the same SHA-256
  digest. The dedicated test
  `tests/test_reference_demo_replay.py` enforces this; if it
  fails, **do not** tag a release until the regression is
  understood. New non-determinism in the kernel is a v0/v1
  invariant violation. Helpers live in
  `examples/reference_world/replay_utils.py`
  (`canonicalize_ledger(kernel)`, `ledger_digest(kernel)`).
- [ ] Reference demo manifest can be generated. From within
  Python (or interactively for a release-note attachment):
  `build_reference_demo_manifest(kernel, summary)` returns a
  dict; `write_manifest(manifest, path)` writes deterministic
  JSON. Helpers live in
  `examples/reference_world/manifest.py`. The dedicated test
  `tests/test_reference_demo_manifest.py` enforces field shape,
  hash format, deterministic writes, and graceful git-absent
  behavior. The manifest is for reproducibility, not proprietary
  provenance — see
  `japan-financial-world/docs/public_private_boundary.md`.
- [ ] No new `print` / debug statements in committed code.
- [ ] No accidentally committed `*.bak`, `*.pyc`, `__pycache__/`,
  `.DS_Store`, IDE settings, or notebook output.

## Secret scanning

- [ ] CI's `secret-scan` job (gitleaks-action) is green for the
  commit being tagged. The job is currently `continue-on-error:
  true` for license-key reasons — a positive find still requires
  manual triage; do **not** treat the green job as a substitute
  for reviewing the action log.
- [ ] If gitleaks is not yet enabled with a license, run
  `gitleaks detect --redact` locally over the working tree and
  the full history (`gitleaks detect --redact --log-opts="--all"`)
  and document a clean run in the release note.
- [ ] Investigate every hit. Do not skip "looks like a false
  positive" without checking.
- [ ] If a real secret is found, treat it as compromised — rotate at
  source, then decide whether to rewrite history.

## Public-repo hygiene review

- [ ] Open the diff for this release and read every changed file.
- [ ] Confirm no expert-interview notes, OB notes, NDA-restricted
  material, or paid-data outputs were added.
- [ ] Confirm no real-institution stress results, named-institution
  scenarios, or client communications were added.
- [ ] Confirm no real ticker codes / real-firm identifiers were
  introduced in synthetic example data, tests, or schemas.
  Synthetic data must use `*_reference_*` style identifiers; see
  [`docs/naming_policy.md`](japan-financial-world/docs/naming_policy.md)
  for accepted forms.
- [ ] Confirm no Japan-calibration claim was made for v0 / v1.
  v0 and v1 are jurisdiction-neutral; mentions of BOJ / MUFG /
  GPIF / etc. should appear only as "what v1 deliberately avoids"
  or "what v2 will populate" — never as present-day capability.

## README and docs review

- [ ] `README.md` at repo root reads correctly. The disclaimer
  section is present and unchanged in spirit.
- [ ] `README.md` test count matches the actual `pytest -q` total.
- [ ] No release-blocking TODOs remain in
  `japan-financial-world/docs/v0_*.md`, `v1_*.md`, or
  `world_model.md` for the milestones being shipped.
- [ ] If a milestone freeze is being tagged, confirm the matching
  release-summary doc lists the freeze surface and that
  `test_inventory.md` reflects the current test counts.
- [ ] No "predicts markets," "production-ready," "enterprise-ready,"
  "Japan market simulator," "buyout target," or similar
  unsubstantiated public-facing claims appear in `README.md` or
  any `docs/*.md`.

## Examples and synthetic data review

- [ ] `examples/minimal_world.yaml` and any new examples use
  fictional, jurisdiction-neutral identifiers.
- [ ] `data/sample/*.yaml` does not introduce real-institution names
  or real-ticker codes since the previous release.
- [ ] Schemas under `schemas/` use neutral example values.

## Final eyes-on

- [ ] Browse the GitHub repo as if you were a researcher seeing it
  for the first time. Does the framing read as research software?
  Does the disclaimer surface early? Are real institutions clearly
  flagged as out-of-scope?
- [ ] If the answer to any of the above is "no," fix before
  releasing.

## Living-world reproducibility (v1.9.2)

A v1.9.x or v1.9.last public release that includes the multi-
period demo should also exercise the v1.9.2 reproducibility
helpers. Each item below mirrors the v1.7-era reference-demo
manifest gate but for the living-world sweep.

- [ ] `python -m examples.reference_world.run_living_reference_world`
  produces the canonical `[setup]` / `[period N]` / `[ledger]`
  trace. Re-running yields byte-identical output.
- [ ] `python -m examples.reference_world.run_living_reference_world --markdown`
  appends the v1.9.1 Markdown report. Re-running yields
  byte-identical output (CLI + Markdown).
- [ ] `python -m examples.reference_world.run_living_reference_world --manifest /tmp/lw.json`
  writes a v1.9.2 manifest. Re-running into a different path and
  diffing the two files shows zero changes (modulo the path).
- [ ] The manifest's `living_world_digest` matches the digest
  produced by
  `examples.reference_world.living_world_replay.living_world_digest(kernel, result)`
  on the same fixture.
- [ ] `manifest_version == "living_world_manifest.v1"` and
  `run_type == "living_reference_world"`.
- [ ] `infra_record_count + per_period_record_count_total ==
  created_record_count` (the v1.9.1-prep algebra).
- [ ] The manifest's `boundary_statement` matches the v1.9.1
  reporter verbatim and includes "no investment advice."
- [ ] `git_status` is `"ok"` (or `"git_unavailable"` /
  `"not_a_repo"` only on environments where that is genuinely
  the case — never `"error"` on a release machine).

## Public prototype gate (v1.9.last)

The **v1.9.last public prototype** is allowed to ship when the
public-release gate above is fully green *and* the prototype-
specific items below are all true. v1.9.last is a public *prototype*
(synthetic-only, CLI-first, explainability-first), not a fresh
public release of unrelated material — see
[`japan-financial-world/docs/public_prototype_plan.md`](japan-financial-world/docs/public_prototype_plan.md)
and the single-page reader summary at
[`japan-financial-world/docs/v1_9_public_prototype_summary.md`](japan-financial-world/docs/v1_9_public_prototype_summary.md).

### Code health (v1.9.last)

- [ ] `pytest -q` from `japan-financial-world/` → `1626 passed`.
- [ ] `python -m compileall world spaces tests examples` → clean.
- [ ] `ruff check .` from repo root → clean.
- [ ] `gitleaks detect --redact --log-opts="--all"` (or
  `--no-git --source .` if the working tree is the artifact)
  → zero leaks. If gitleaks is not installed locally, document
  the equivalent CI run.

### Demo gates (v1.9.last)

- [ ] **One-command demo (operational trace).** From a clean
  clone, after `pip install -e ".[dev]"` and `cd japan-financial-world`:

  ```bash
  python -m examples.reference_world.run_living_reference_world
  ```

  produces a `[setup]` / `[period N]` / `[ledger]` trace;
  two consecutive runs produce byte-identical CLI output.

- [ ] **Markdown report.**

  ```bash
  python -m examples.reference_world.run_living_reference_world --markdown
  ```

  appends the v1.9.1 deterministic Markdown ledger trace
  report; two consecutive runs produce byte-identical CLI +
  Markdown output. The hard-boundary statement appears verbatim
  in the Markdown (`no investment advice`).

- [ ] **Manifest generation.**

  ```bash
  python -m examples.reference_world.run_living_reference_world \
      --manifest /tmp/fwe_living_world_manifest.json
  ```

  writes a v1.9.2 `living_world_manifest.v1` JSON; running twice
  into different paths and diffing yields zero changes (modulo
  path). `manifest_version == "living_world_manifest.v1"`,
  `run_type == "living_reference_world"`,
  `infra_record_count + per_period_record_count_total ==
  created_record_count`, `git_status` is `"ok"` /
  `"git_unavailable"` / `"not_a_repo"` (never `"error"`).

### Scope and wording gates (v1.9.last)

- [ ] **README scope read.** The first ~60 seconds of `README.md`
  state, accurately and without marketing language, that the
  project is research software, not a market predictor or
  investment advisor; that all data is synthetic; that Japan
  calibration is v2 / v3 territory. The "Current public
  prototype (v1.9.last)" section is present and accurate.
- [ ] **Hard-boundary language present.** README, reference-world
  README, public-prototype plan, public-prototype summary, and
  the v1.9.1 Markdown report each state explicitly: no price
  formation, no trading, no lending decisions, no firm
  financial-statement updates, no canonical valuation, no
  Japan calibration, no real data, no investment advice.
- [ ] **Public / private boundary agreement.** `README.md`,
  `SECURITY.md`,
  [`docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md),
  [`docs/v1_8_release_summary.md`](japan-financial-world/docs/v1_8_release_summary.md),
  [`docs/public_prototype_plan.md`](japan-financial-world/docs/public_prototype_plan.md),
  and
  [`docs/v1_9_public_prototype_summary.md`](japan-financial-world/docs/v1_9_public_prototype_summary.md)
  agree on what is public, what is private, and where the seam is.
- [ ] **Forbidden-token scan clean.** A word-boundary scan for the
  canonical token list at `world/experiment.py::_FORBIDDEN_TOKENS`
  finds no hits in any object id, signal id, or example output.
  Use `\b` boundaries — naive substring greps mis-flag `tse` ⊂
  `itself`.
- [ ] **No proprietary content.** No expert-interview notes, no
  named-institution stress results, no paid-data references, no
  client-report templates, no NDA-restricted material.
- [ ] **No investment-advice framings.** Neither direct ("buy
  X") nor indirect ("a portfolio with exposure E would
  experience O") forms appear in code, docs, or demo output.
- [ ] **CI green on the tag commit.** `Tests + lint + demo`
  and `Secret scan (gitleaks)` jobs both green.

## Tagging

A release candidate (RC) may be tagged with the public-release
gate not fully green; a final public-release tag may not.

```bash
# from repo root
# Release candidate (CI may have known yellow items, e.g.,
# gitleaks not yet licensed):
git tag -a vX.Y-public-rcN -m "vX.Y-public-rcN — short release note"

# Final public release (CI fully green, every checklist box
# above ticked):
git tag -a vX.Y-public-release -m "vX.Y-public-release — short release note"

git push origin <tag>
```

The release note should briefly state: what changed, what tests
report (e.g., `pytest -q` count, `compileall` clean,
`ruff check .` clean), and any known issues. Do not include
marketing language.
