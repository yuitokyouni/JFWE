---
name: Auto commit & push after edits in JFWE
description: In the JFWE repo, after completing a code/docs change, commit and push to origin/main without waiting for an explicit ask, so the CI workflow (.github/workflows/ci.yml) runs.
type: feedback
---

After finishing any change in `/Users/hasegawayuito/Documents/GitHub/JFWE`, commit the change and push to `origin/main` as part of completing the task — do not wait for the user to ask each time.

**Why:** The user has explicitly designed this repo to rely on automatic commit + push so that `.github/workflows/ci.yml` (pytest, compileall, ruff, FWE Reference Demo smoke, gitleaks) runs on every change. They asked Claude to inherit this practice across sessions. Skipping the push leaves CI unrun and breaks the feedback loop the user is depending on.

**How to apply:**
- Stage only the files actually changed (avoid `git add -A`).
- Match the existing commit-message style — recent commits use prefixes like `vX.Y.Z: …`, `docs/ui: …`, `docs/roadmap: …`. Pick the closest fit; do not invent a new convention.
- Push to `origin/main` (the repo currently develops directly on `main`).
- After pushing, optionally `gh run list --branch main --limit 1` to surface the CI run id, but do not block waiting for it unless the user asks.
- Still respect the global git-safety rules: never `--no-verify`, never force-push, never amend a pushed commit. If a hook fails, fix the root cause and create a new commit.
- This applies to substantive changes only. Skip auto-commit for: scratch/experiment files the user is iterating on, partial work the user explicitly said "don't commit yet", or anything containing secrets.
