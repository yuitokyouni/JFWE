# Roadmap: FWE Core public release

> **Status:** scoped, not started.
> **Layer:** FWE Core (public).
> **Depends on:** v1.7 freeze (done).
> **Blocks:** any external announcement of the project.

## Goal

Make the v1.7 FWE Core repository **safe and credible to publish
publicly** — as research software, not as a product. This milestone
turns "the code passes tests" into "an external researcher can clone
this, read it, run it, and understand what is and is not claimed."

The milestone ships **no new behavior**. It is a release-engineering
and credibility-engineering milestone.

## In scope

### Release hygiene

- [ ] `RELEASE_CHECKLIST.md` (already at repo root) walked from top
  to bottom and every box ticked, with the result captured in a
  release-note file (e.g., `docs/release_notes/v1.7.md`).
- [ ] `git log` reviewed — no leaked secrets, no real-institution
  fixtures, no proprietary content in any commit since the project
  started. If a violation exists in history, decide on rotation +
  history-rewrite policy before tagging.
- [ ] `pytest -q` reports the expected total cleanly on a fresh
  checkout in a clean Python environment.
- [ ] `python -m compileall world spaces tests` succeeds.
- [ ] No `*.pyc`, `__pycache__/`, `.DS_Store`, IDE settings, or
  notebook output checked in.

### CI / replay / security

- [ ] GitHub Actions workflow (or equivalent) that runs `pytest -q`
  on every push and PR against the supported Python versions.
- [ ] Workflow runs the FWE Reference Demo
  (`examples/reference_world/run_reference_loop.py`) as part of CI
  so the demo cannot silently break.
- [ ] Secret-scanning on push (GitHub built-in or `gitleaks` action).
- [ ] Reproducibility check: a CI job that builds a fresh kernel
  twice with the same inputs and asserts ledger byte-equality
  (a "replay" smoke check). The mechanism already exists in tests;
  this just promotes it to a CI gate.
- [ ] Dependency policy stated: minimal third-party deps; any new
  dep needs an explicit decision and license check.

### Docs

- [ ] Repo-root `README.md` reviewed for currency, disclaimer
  presence, accurate test count, and absence of overstating claims.
- [ ] `SECURITY.md` reviewed — vulnerability reporting path is
  reachable, hygiene rules match what the repo actually contains.
- [ ] `docs/product_architecture.md`, `docs/public_private_boundary.md`,
  and `docs/naming_policy.md` reviewed and cross-linked from the
  README.
- [ ] `docs/v0_release_summary.md` and `docs/v1_release_summary.md`
  reviewed; freeze-surface lists match the code.
- [ ] `docs/test_inventory.md` reviewed; counts match `pytest -q`.
- [ ] `docs/world_model.md` table of contents (or equivalent)
  navigable.
- [ ] A short "How to read this repo" section pointing first-time
  visitors at the four entry points: root README → product
  architecture → reference demo → world_model.

### Synthetic examples only

- [ ] `examples/reference_world/` reviewed: every entity uses the
  `*_reference_*` naming convention; every numeric value is an
  illustrative round number, not a measurement.
- [ ] `examples/minimal_world.yaml` reviewed: synthetic dummy ids
  only.
- [ ] `data/sample/*.yaml` reviewed: any remaining values that read
  as Japan-specific are either renamed or flagged with a comment
  noting they are illustrative, not calibrated.
- [ ] No real ticker codes anywhere in `examples/`, `data/`, or
  `tests/`.

### No real data

- [ ] Confirm the repo contains zero rows of real macro / market /
  filing data.
- [ ] Confirm no paid-vendor identifier appears as a present-day
  capability claim. Vendor names may appear only in the
  never-commit / v3-only lists.
- [ ] Confirm no expert interview quotes, paraphrased OB notes, or
  named-institution stress results.

## Out of scope

- New simulation behavior (price formation, decisions, etc.).
- v2 calibration, even partially.
- Web UI, hosted service, pricing, or to-C features.
- A renamed repository or package namespace (separate migration).
- Performance optimization. Correctness > speed for this layer.
- Any external advertising or "launch" event. Public release here
  means *the repo is safe to look at*; promotion is a separate
  decision.

## Acceptance criteria

The milestone is done when **all** of the following hold:

1. A release-note file (e.g., `docs/release_notes/v1.7.md`) is
   present and accurately summarizes what was tagged.
2. CI is green on `main` and runs: `pytest -q`, the reference demo,
   secret scanning, and the replay determinism check.
3. A first-time external reader can land on the repo, follow the
   README's documentation map, run the reference demo, and
   correctly identify FWE Core as research software with no
   Japan calibration.
4. A separate hygiene reviewer (per `RELEASE_CHECKLIST.md`)
   confirms no proprietary content, no real-institution fixtures,
   no leaked secrets in HEAD or history.
5. Public-facing claims in README and docs are bounded — no
   "predicts," "production-ready," "enterprise," "investment
   advice," "calibrated Japan model," or competitor-comparison
   language.

## Dependencies

- v1.7 freeze (done).
- `RELEASE_CHECKLIST.md` and `SECURITY.md` (done).
- The FWE Reference Demo (done) — needed for the CI demo job.

## Notes for the implementer

- This milestone is **boring on purpose**. It must not introduce
  novelty.
- If a reviewer finds an unboundable claim that requires non-trivial
  rewriting, prefer to soften / delete rather than to argue. The
  bar for the public release is "nothing in here overpromises."
- If a CI job is flaky, fix the determinism root cause; do not
  silence it.
- Tagging convention: `v1.7-public-release` (or similar) — distinct
  from the `v1.7` freeze commit so the release event is traceable.
