# Public / Private Boundary

This document defines what is public and what is restricted in the
Financial World Engine project. It complements
[`product_architecture.md`](product_architecture.md), which defines the
five product layers (FWE Core / FWE Reference / FWE Public Demo / JFWE
Public / JFWE Proprietary). This document is the single rule that says
which artifacts may be redistributed, and which must not be.

The rule is simple: **public artifacts must not embed restricted
content; restricted artifacts may reference public content but must
not redistribute it without the public license's terms attached.**

## Public artifacts

The following are public. They may be hosted in the open repository,
discussed in public talks, included in academic papers, and shared
without further approval.

### Code

- The FWE Core kernel and reference layer (`world/`, `spaces/`).
- Synthetic / fictional reference content authored within the project
  (the future FWE Reference layer).
- Any FWE Public Demo code, if and when that layer ships.
- JFWE Public code that *structures* Japan public data, when the
  underlying public source's license permits redistribution.

### Tests

- The 632 v0 + v1 tests in `tests/`.
- Future FWE Reference tests covering synthetic populations.
- JFWE Public tests that use a redistributable public-data snapshot.

### Docs

- Every file currently in `docs/` (v0 and v1 design / scope / release
  / architecture / readiness / inventory documents).
- This document, [`product_architecture.md`](product_architecture.md),
  and [`naming_policy.md`](naming_policy.md).
- The repository `README.md`.

### Schemas

- The YAML / JSON schema fragments under `schemas/` that describe the
  v0 / v1 record shapes and book APIs.

### Examples

- The minimal-world YAML files under `examples/` and `data/` used by
  `world/cli.py` and the integration tests.

### Reference demo (when FWE Reference ships)

- The synthetic country / market / institutional populations.
- Process specs and parameters chosen for the demo.
- Snapshot artifacts produced by the demo.

## Restricted / not public artifacts

The following are **never** committed to the public repository, never
embedded in public docs, and never published in public talks without
explicit per-item approval. They live in a private repository,
in private storage, or in a JFWE Proprietary access-controlled space.

### Expert interview notes

- Verbatim transcripts or paraphrased notes from expert interviews
  (Japan banking, asset management, regulator, central-bank watcher,
  academic, etc.).
- Quotes attributable or de-anonymizable.
- Any "the expert said X about Y bank" claim, with or without
  attribution.

### Paid data

- Vendor-licensed datasets (Bloomberg, Refinitiv, QUICK, etc.).
- Paid fund-holdings disclosures beyond public minimums.
- Paid news feeds (full text or processed signals).
- Paid analyst / consensus datasets.
- Real-time market data feeds and tick / trade-by-trade history.

Paid data may be loaded by JFWE Proprietary code at runtime; it is not
checked into public storage and is not reproduced in public outputs.

### Proprietary calibration

- Process parameters, regime probabilities, decay half-lives, or
  reaction-function coefficients chosen with reference to expert input
  or paid data.
- Calibration snapshots that bind to a paid-data version.
- Internal consensus forecasts.
- Expert overrides for structural breaks (e.g., post-disaster regime
  shifts, policy regime changes).
- Any calibration whose provenance includes a non-public source.

### Named-bank / named-institution stress results

- Stress-test outputs with real-institution names (e.g., "Bank A's
  losses under scenario S").
- Sensitivity tables ranked by named institution.
- Counterparty-network visualizations with real names.
- Any artifact that ties simulation outputs to specific named legal
  entities.

The fact that the simulation is causal and auditable makes this rule
*more* important, not less: a public auditable trace tied to a real
named institution would create reputational and regulatory risk that
the project must not assume.

### Client reports

- Bespoke analyses produced for a specific client.
- Custom scenario runs requested by a client.
- Communications about a client's portfolio, mandate, or strategy.
- Anything that names a client.

### Private scenario templates

- Scenario templates developed against expert input or paid data.
- Templates that encode proprietary "house view" assumptions.
- Stress-test scenarios designed for client engagement.

Public scenario templates (synthetic, jurisdiction-neutral) are fine
and may live in FWE Reference or FWE Public Demo. The restriction is
on templates whose construction depended on non-public input.

## How to tell if an artifact is public or restricted

Three questions, in order:

1. **Provenance.** Was this artifact constructed using only public
   sources, or did its construction depend on expert input, paid data,
   or other non-public input? If the latter, it is restricted.
2. **Identifiability.** Does the artifact name a real institution
   (bank, firm, fund, regulator, person)? If yes, **and** it carries
   a simulation outcome (stress result, valuation, action prediction)
   tied to that name, it is restricted regardless of provenance.
3. **License.** If the artifact is built on a public source, does the
   source's license permit redistribution? If no, the artifact stays
   in JFWE Public's restricted-redistribution bucket even though it
   is "public-data-derived."

If any of (1) is non-public, (2) names a real institution with an
outcome, or (3) lacks redistribution rights, the artifact is
restricted.

## Public ↔ restricted interface

JFWE Public and JFWE Proprietary do interact, but only at well-defined
boundaries:

- **Public → Restricted:** the restricted layer may **read** public
  code, public data, and public docs. This is the normal direction.
  The restricted layer adds proprietary content on top.
- **Restricted → Public:** the public layer **must not** import,
  reference by file path, or otherwise depend on restricted artifacts
  at build time. The public layer must continue to build, test, and
  run with the restricted layer absent.
- **Cross-layer outputs:** if a JFWE Proprietary run produces an
  artifact (a calibration, a scenario, an analysis), that artifact
  inherits the most-restrictive provenance of its inputs. A
  proprietary-input run cannot produce a public-output artifact by
  fiat; only by carefully removing all proprietary content.

## What this means for the current repository

At v1.7 freeze:

- This repository (`JWFE` on GitHub) contains only FWE Core code,
  tests, docs, schemas, and minimal-world examples. It contains no
  expert interview notes, no paid data, no proprietary calibration,
  no real-institution stress results, no client reports, and no
  private scenario templates.
- The repository is fully public.
- Future v2 work that adds JFWE Public calibration may land in this
  repository or in a separate one. That decision is part of v2
  planning. If it lands here, every JFWE Public commit must verify
  its sources' licenses and attach the attribution required by each.
- Future v3 work (JFWE Proprietary) **does not land in this
  repository**, ever. v3 lives in a separate private repository.

## What this document does not decide

- The specific access-control model for JFWE Proprietary (a v3
  planning task).
- The vendor-onboarding process for paid data sources (a v3 / legal
  task).
- Whether JFWE Public will be a separate repository or a subdirectory
  here (a v2 planning task; either is compatible with the rule above).
- Per-source license terms. Those go in
  [`v2_readiness_notes.md`](v2_readiness_notes.md) and become formal
  reviews during v2 milestones.

The role of this document is solely to draw the public / restricted
line clearly enough that, at the v1.7 freeze, no one mistakenly assumes
the freeze allows or disallows something it does not.
