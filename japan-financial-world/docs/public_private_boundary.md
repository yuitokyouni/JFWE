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

- This repository (`JFWE` on GitHub; renamed from the legacy
  `JWFE` repository name — relabel only, no runtime / model /
  digest impact) contains only FWE Core code,
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

## v1.10 addendum — engagement / response layer

v1.10 adds an engagement-and-response layer on top of the v1.9
diagnostic stack. The new public artifacts are:

- `stewardship_theme_signal` — a signal-shaped record naming a
  generic stewardship theme an investor is prepared to raise across
  portfolio companies in a given period.
- `portfolio_company_dialogue_record` — a relational record naming
  that an engagement contact happened in a given period under a
  given theme, with a generic outcome class.
- `investor_escalation_candidate` — a candidate-shaped record naming
  that an investor *could* escalate, given prior dialogue records.
- `corporate_strategic_response_candidate` — a candidate-shaped
  record naming a strategic response a firm *could* take.
- `industry_demand_condition_signal` — an optional context signal
  naming a generic industry-level demand condition.

These artifacts follow the same public / restricted rules as every
other FWE artifact, with one additional explicit rule that v1.10
calls out:

- **Verbatim or paraphrased dialogue contents are restricted in every
  jurisdiction.** A `portfolio_company_dialogue_record` carries
  metadata only — investor identifier, firm identifier, period,
  theme reference, generic outcome class. It must not carry the
  actual content of any conversation, even synthetic. Synthetic
  dialogues used for tests must use the existing FWE Reference
  identifier conventions and must remain identifiably synthetic.
- **Calibrated behavior probabilities, threshold tiers, taxonomy
  attributions to real institutions, and forecast values are
  restricted regardless of jurisdiction.** v1.10 record shapes use
  small enumerated controlled vocabularies as illustrative
  enumerations only, with no calibrated probabilities of selection.
- **Named-institution engagement / escalation / response histories
  are restricted regardless of jurisdiction.** The same rule that
  prohibits named-institution stress results applies, end-to-end,
  to engagement records.

v1.10's public layer must continue to build, test, and run with the
restricted layer absent. The forbidden-token word-boundary scan
gating each commit is unchanged.

### v1.10.2 — binding implementation of the dialogue-content rule

v1.10.2 ships the public-FWE `PortfolioCompanyDialogueRecord` shape
(see `world/engagement.py`). The implementation makes the
dialogue-content rule binding rather than aspirational:

- The dataclass deliberately has **no** `transcript`, `content`,
  `contents`, `notes`, `minutes`, `attendees`, `attendee_list`,
  `verbatim`, `paraphrase`, `paraphrased`, or `body` field.
- The ledger payload mirrors the record fields and likewise carries
  none of the above keys.
- A test (`test_dialogue_record_has_no_transcript_or_content_field`)
  introspects the dataclass field set against the forbidden list,
  and a parallel test
  (`test_add_dialogue_ledger_payload_carries_no_transcript_or_content_keys`)
  introspects the ledger payload key set. A future v1.10.x or
  later milestone that introduces such a field would by
  construction trip these tests.
- The recommended outcome / next-step labels are illustrative
  controlled-vocabulary tags, never calibrated probabilities; the
  book does not enforce membership of any tag against any list, so
  no jurisdiction-specific code can leak in via tag enforcement.
- The `visibility` field is recorded so that downstream JFWE Public
  / JFWE Proprietary boundaries can rely on it, but v1.10.2 itself
  does **not** use it as a runtime gate — it is metadata only.

If a future milestone needs to attach actual dialogue contents, that
attachment lives in JFWE Proprietary (v3 territory), in a separate
private repository, with access controls — never in this public
repository, even synthetically.

### v1.10.3 — binding implementation of the no-execution rule

v1.10.3 ships the public-FWE `InvestorEscalationCandidate` shape
(see `world/engagement.py`) and the public-FWE
`CorporateStrategicResponseCandidate` shape (see
`world/strategic_response.py`). Both implementations make the
candidate-only / no-execution rule binding rather than aspirational:

- The investor-side dataclass deliberately has **no** `vote_cast`,
  `proposal_filed`, `campaign_executed`, `exit_executed`, or
  `letter_sent` field. The corporate-side dataclass deliberately
  has **no** `buyback_executed`, `dividend_changed`,
  `divestment_executed`, `merger_executed`,
  `board_change_executed`, or `disclosure_filed` field. Both
  inherit the v1.10.2 anti-field rule (no `transcript`, `content`,
  `notes`, `minutes`, `attendees`, `verbatim`, `paraphrase`, or
  `body`).
- The ledger payloads mirror the record fields and likewise carry
  none of the above keys.
- Tests
  (`test_escalation_record_has_no_execution_or_content_field`,
  `test_response_record_has_no_execution_or_content_field`,
  `test_add_escalation_payload_carries_no_execution_or_content_keys`,
  `test_add_response_payload_carries_no_execution_or_content_keys`)
  introspect both the dataclass field set and the ledger payload
  key set against the forbidden lists. A future v1.10.x or later
  milestone that introduces such a field would by construction
  trip these tests.
- A no-action-class assertion (forbidding `order_submitted`,
  `price_updated`, `contract_*`, `ownership_*`,
  `institution_action_recorded`) holds for `add_candidate` on both
  books.
- The recommended `escalation_type` / `response_type` /
  `expected_effect_label` / `constraint_label` /
  `rationale_label` / `next_step_label` tags are illustrative
  controlled-vocabulary labels, never calibrated probabilities;
  the books do not enforce membership of any tag against any list,
  so no jurisdiction-specific code can leak in via tag enforcement.
- The `visibility` field is recorded so that downstream JFWE
  Public / JFWE Proprietary boundaries can rely on it, but
  v1.10.3 itself does **not** use it as a runtime gate — it is
  metadata only.

If a future milestone needs to attach an executed escalation, an
executed corporate action, or any document filed with a real
regulator / exchange, that attachment lives in JFWE Proprietary
(v3 territory), in a separate private repository, with access
controls — never in this public repository, even synthetically.

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
