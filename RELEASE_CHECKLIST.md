# Release Checklist

A short, runnable checklist to walk before publicly tagging or
announcing a release of this repository. Most items are local
commands; a few are eyes-on review steps. The list is intentionally
short so it is actually used.

For the public / private rules these checks enforce, see
[`SECURITY.md`](SECURITY.md) and
[`japan-financial-world/docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md).

## Public release gate (must be green for a public release)

A **public release tag** (e.g., `v1.7-public-release`) requires CI
to be green on the commit being tagged. CI runs the items below
automatically; this section is the manual mirror so you can
reproduce locally before pushing.

### CI

- [ ] `.github/workflows/ci.yml` ran on the commit being tagged and
  every job is green. A red job blocks the public release; an
  intermittent flake should be investigated and fixed at the root,
  not retried.

## Code health (mirrors CI; reproducible locally)

- [ ] `pytest -q` from `japan-financial-world/` reports the expected
  passing total (currently `660 passed` at v1.7-public-rc1+,
  including the replay-determinism test file).
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
