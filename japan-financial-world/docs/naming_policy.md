# Naming Policy

This document defines the naming conventions for the Financial World
Engine project: which names are preferred, which are avoided, and how
to handle the legacy names already in use.

The rules here are positioning rules, not a rename plan. The current
repository, working directory, Python packages, and import paths are
**unchanged** as of the v1.7 freeze. Any future rename is a separate
migration with its own milestone — not a side effect of this document.

## Preferred names

For the **generic, jurisdiction-neutral, public** layer of the project:

- **FWE** — short form, used in identifiers, headings, and code
  comments where brevity matters.
- **Financial World Engine** — long form, used in titles, prose, and
  the first reference in any document.
- **FinWorld Engine** — alternate long form, acceptable where
  "Financial" reads heavily (e.g., social-media-length blurbs).

For the **Japan-specific** layers:

- **JFWE Public** — Japan public calibration on top of FWE Core.
  Public where redistribution rights allow.
- **JFWE Proprietary** — private commercial Japan calibration. Never
  public.
- **JFWE** (alone, no qualifier) — only acceptable in the legacy
  context (existing repository name, existing paths, this document).
  In new prose, prefer one of the qualified forms above so a reader
  can tell which layer is meant.

## Avoided name

- **WFE** — **avoid.** WFE is the long-standing acronym for the
  **World Federation of Exchanges**, the global trade association of
  stock exchanges and clearinghouses. Using WFE in a financial-domain
  project creates an acronym collision that confuses readers and
  trips search relevance. Do not use WFE in identifiers, headings,
  prose, talks, or external materials, even informally.

The only acceptable use of "WFE" in this project is to explain why we
*don't* use it (i.e., this paragraph).

## Legacy names already in use

The following legacy names are not changed in this version. They will
remain stable until a future, explicit rename migration:

- **Repository name on GitHub:** `JFWE` (renamed from the legacy
  `JWFE` repository name; the rename is purely a GitHub-side relabel
  and changed no runtime, no model logic, no canonical digest, no
  package import path). The legacy `JWFE` name was a historical
  accident: "J" = Japan, "WFE" = World Financial Engine — predating
  the WFE-collision rule above.
- **Top-level working directory:** `japan-financial-world/`.
- **Python packages:** `world/`, `spaces/`.
- **Imports:** `from world.kernel import WorldKernel`, etc.
- **Test files:** `tests/test_*.py` paths.
- **Doc filenames:** `docs/v0_*.md`, `docs/v1_*.md`, etc. (most
  filenames already use neutral names; a few document filenames carry
  Japan-specific framing for historical reasons).

These legacy names are accepted as-is for the current freeze. New
documents and new prose should use the preferred names from the
section above; legacy paths in code should be left alone until a
deliberate rename milestone.

## How to handle the legacy names in prose

When writing new docs, talks, or external materials:

- Refer to the **engine** as FWE / Financial World Engine.
- Refer to the **Japan calibration layers** as JFWE Public or JFWE
  Proprietary, qualified.
- Acknowledge the **repository name** as `JFWE` only when discussing
  installation or repository operations (clone URL, repository
  structure). Do not promote `JFWE` as the engine's name — the
  engine is FWE / Financial World Engine; `JFWE` is the GitHub
  repository label, a separate concept. The repository previously
  carried the legacy `JWFE` label; both names refer to the same
  underlying repository and history.
- When a sentence would otherwise have to say "the JFWE / `japan-
  financial-world` codebase," prefer "the FWE Core codebase" or "the
  current FWE Core repository (the GitHub repository named `JFWE`,
  legacy `JWFE`)."

This keeps the public-facing identity consistent with the product
architecture even while the directory tree carries the legacy names.

## Future rename migration (out of scope here)

A future migration may move FWE Core code under an `fwe/` or
`finworld/` package namespace, separate Japan calibration into its own
package, and rename the repository. That migration is not committed in
this document. When it happens, the migration milestone must:

1. Land in a single, identifiable commit (or a clean sequence of
   commits) so `git log` records the rename event.
2. Update every public document that referenced the legacy paths.
3. Preserve test suite parity (tests pass before and after).
4. Update this document's "Legacy names already in use" section to
   reflect the new state, and keep a "Historical names" footnote so
   external links that pre-date the rename remain understandable.
5. Coordinate with any in-flight v2 work so the rename does not
   conflict with simultaneous Japan-calibration changes.

Until that migration lands, the names in this document's "Legacy
names" section are authoritative.

## Quick reference

| Use case                                  | Preferred                          | Avoid                            |
| ----------------------------------------- | ---------------------------------- | -------------------------------- |
| Generic engine, formal name               | Financial World Engine             | World Financial Engine, WFE      |
| Generic engine, short                     | FWE                                | WFE                              |
| Generic engine, alternative long form     | FinWorld Engine                    | (none)                           |
| Japan public calibration                  | JFWE Public                        | JFWE (alone, ambiguous)          |
| Japan private calibration                 | JFWE Proprietary                   | JFWE (alone, ambiguous)          |
| Repository name (current; legacy `JWFE`)  | `JFWE`                             | promoting the repo label as the engine's name |
| Working directory (legacy)                | `japan-financial-world/`           | (do not rename in this version)  |
| Python package (legacy)                   | `world/`, `spaces/`                | (do not rename in this version)  |
