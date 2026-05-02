# Public Prototype Plan — v1.9.last + v1.12.last

> **Status:** v1.9.last freeze landed 2026-05-02; v1.12.last
> freeze landed 2026-05-04. The repository contents have been
> frozen as the v1.9 public prototype + v1.12 endogenous
> attention-feedback loop; tagging is the downstream gate in
> `RELEASE_CHECKLIST.md` and depends on CI being green on the
> commit being tagged.
> This document defines what "public prototype" means for this
> project, what gates each freeze must clear, and how the freeze
> maps to the runnable surface.
>
> For the single-page reader summaries see
> [`v1_9_public_prototype_summary.md`](v1_9_public_prototype_summary.md)
> (the runnable substrate) and
> [`v1_12_endogenous_attention_loop_summary.md`](v1_12_endogenous_attention_loop_summary.md)
> (the v1.12 endogenous attention-feedback loop layered on top).

## What "public prototype" means here

For FWE / JFWE, **public prototype** is *not*:

- a website,
- a hosted service,
- a tutorial,
- a marketing artifact,
- a Japan-calibrated simulator,
- or a tool that produces investment views.

Public prototype **is**:

- **GitHub-first or CLI-first.** A researcher clones the repo,
  installs the dev extras, and runs one command to see the
  endogenous chain in action.
- **Synthetic-only.** Every identifier is jurisdiction-neutral and
  follows the `*_reference_*` convention. No real institution
  names, no real ticker codes, no public-data feeds wired.
- **Explainability-first.** The point is to make the *engine*
  understandable. The CLI prints a compact operational trace; the
  `--markdown` flag emits the deterministic v1.8.15 ledger trace
  report. Two runs produce byte-identical output.
- **No calibrated Japan claims.** The repo says explicitly that
  v1 / v1.8 / v1.9 are jurisdiction-neutral and that Japan
  calibration is v2 / v3 territory.

The public prototype is a *demonstration that the substrate is
trustworthy in its mechanics*, not a demonstration that any output
is trustworthy as a real-world claim.

## Public surfaces v1.9.last may target

v1.9.last is allowed to ship any of:

- the **GitHub repository** itself, with this README, the v1.8 /
  v1.9 design docs, and the test suite green on CI;
- a **CLI demo** runnable from a clean clone:
  `python -m examples.reference_world.run_endogenous_chain --markdown`
  (extended for multi-period sweep when v1.9.0 lands);
- **static Markdown reports** committed under `examples/` for
  reference (so a reader can preview the demo output without
  cloning);
- **precomputed demo output** — small, byte-deterministic,
  human-readable;
- *optionally*, a thin **web UI** that renders the same Markdown
  / JSON the CLI emits — but only after the CLI experience is
  green and only as a presentation layer over deterministic
  artifacts.

A web UI is **not** required for v1.9.last. If it appears, it must
not introduce non-determinism, must not call out to external
services at runtime, and must not present economic claims.

## Public surfaces v1.9.last must NOT target

The following stay out of v1.9.last (and stay private until at
least v3 — see `docs/public_private_boundary.md`):

- **proprietary calibration** — sensitivities, transmission
  coefficients, expert overrides;
- **expert-interview notes** of any form;
- **paid data** — Bloomberg, Refinitiv, QUICK, or any
  similarly-licensed feed;
- **named-institution stress results** — even synthetic numbers
  that *imply* a real BOJ / MUFG / GPIF / Toyota stress claim;
- **client reports / advisory deliverables** — the public
  prototype is research substrate, not a deliverable template;
- **private templates** — internal stress-testing schemas, OB
  notes, NDA-restricted material;
- **investment advice in any form**, including indirect framings
  ("a portfolio with X exposure would experience Y").

If a contribution to v1.9.last would touch any of the above, it
belongs in a private branch / private repository, not in the
public prototype tag.

## v1.9.last acceptance criteria

The v1.9.last tag is allowed to ship when **all** of the following
are true:

1. **One-command demo.** From a clean clone:

   ```bash
   pip install -e ".[dev]"
   cd japan-financial-world
   python -m examples.reference_world.run_endogenous_chain --markdown
   ```

   produces a complete operational trace plus a deterministic
   Markdown ledger trace report.
2. **Readable output.** A first-time reader can scan the CLI output
   and the Markdown report and form an accurate mental model of
   what the engine did.
3. **Deterministic report.** Two consecutive runs produce
   byte-identical CLI traces and byte-identical Markdown. Tests
   already pin this for v1.8.15; v1.9.last must keep it true for
   the multi-period sweep.
4. **README explains scope in 60 seconds.** The opening paragraphs
   make it clear that the project is research software, not a
   predictor or advisor; that all data is synthetic; that Japan
   calibration is v2 / v3 territory.
5. **Public / private boundary clear.** `docs/public_private_boundary.md`,
   `SECURITY.md`, `docs/v1_8_release_summary.md`, and this document
   agree on what is public, what is private, and where the seam
   is.
6. **Tests green.** `pytest -q` passes with the expected total
   committed in `docs/test_inventory.md` and CI is green on the
   commit being tagged.
7. **`compileall` clean.** `python -m compileall world spaces tests
   examples` exits 0 with no syntax errors.
8. **`ruff check .` clean.** From repo root.
9. **Gitleaks clean.** `gitleaks detect --redact
   --log-opts="--all"` reports zero leaks; the v1.8.0 release
   precedent already documents this gate in `RELEASE_CHECKLIST.md`.
10. **Forbidden-token scan clean.** A word-boundary scan for the
    canonical token list at
    `world/experiment.py::_FORBIDDEN_TOKENS` finds no hits in any
    object id, signal id, or example output. (`tse` substring in
    `itself` is the well-known false positive — use `\b` boundaries.)
11. **No marketing language.** The README, design docs, and CLI
    output do not claim "predicts markets," "production-ready,"
    "enterprise-ready," "Japan market simulator," or similar
    unsubstantiated framings.
12. **Performance boundary documented.** `docs/performance_boundary.md`
    exists and explicitly states: the v1.9 demo uses bounded
    all-pairs loops (`O(P × I × F)` valuation, `O(P × B × F)`
    credit review) only inside fixed demo-size fixtures; future
    production-scale traversal must be sparse and gated on
    relationships / exposures / coverage rather than dense
    actor-product loops; no native (C++ / Julia / Rust / GPU)
    rewrite is in scope for v1.9. The
    `tests/test_living_reference_world_performance_boundary.py`
    suite enforces the discipline (record-budget, exact mechanism
    counts, no price / trade / contract-mutation records, no
    warnings or errors on the default sweep).

## How v1.9.last differs from v1.8.0's public release

v1.8.0 was already tagged `v1.8-public-release` — the public-release
gate exists in [`RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md)
and was cleared on commit `7fa2c42`. v1.9.last is a **public
prototype**, not a fresh public release of the same artifact:

- v1.8.0's public release shipped the v1.7 reference financial
  system + the v1.8 experiment harness. The endogenous activity
  stack was v1.8.x in-progress; the demo was a single-day causal
  trace.
- v1.9.last ships the **endogenous activity stack as the demo**,
  with the v1.9 multi-period sweep in front. A reader visiting the
  repo at v1.9.last sees the chain harness and the trace report
  as the headline capability, not a record-types tour.

The repo's existing public-release gate (`RELEASE_CHECKLIST.md`)
covers v1.9.last too — its checks are framing-neutral. If
v1.9.last needs a v1.9-specific addition (e.g., the multi-period
report being readable end-to-end), that goes into the checklist
when v1.9.0 lands, not before.
