# Release Checklist

A short, runnable checklist to walk before publicly tagging or
announcing a release of this repository. Most items are local
commands; a few are eyes-on review steps. The list is intentionally
short so it is actually used.

For the public / private rules these checks enforce, see
[`SECURITY.md`](SECURITY.md) and
[`japan-financial-world/docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md).

## Code health

- [ ] `pytest -q` from `japan-financial-world/` reports the expected
  passing total (currently `632 passed` at v1.7).
- [ ] `python -m compileall world spaces tests` from
  `japan-financial-world/` succeeds (no syntax errors anywhere).
- [ ] `ruff check .` (if configured) passes — or note the open
  warnings in the release note.
- [ ] No new `print` / debug statements in committed code.
- [ ] No accidentally committed `*.bak`, `*.pyc`, `__pycache__/`,
  `.DS_Store`, IDE settings, or notebook output.

## Secret scanning

- [ ] Run `gitleaks detect` (or equivalent — `trufflehog`, GitHub's
  secret scanner) over the working tree.
- [ ] Run the same scanner over the full git history.
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

After the checklist is clean:

```bash
# from repo root
git tag -a vX.Y -m "vX.Y — short release note"
git push origin vX.Y
```

The release note should briefly state: what changed, what tests
report, and any known issues. Do not include marketing language.
