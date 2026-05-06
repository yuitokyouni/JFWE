# v2.0 Japan Public Calibration Boundary Design — Design Note

*v2.0 is the **first non-generic** milestone in the public
FWE roadmap. It is the boundary design between (1) the
generic FWE substrate already shipped at v1.27.last, (2)
future Japan public calibration using legally accessible
public data, and (3) Japan proprietary calibration using
paid data, expert interviews, manual expert annotation, or
non-public assumptions. v2.0 does **not** calibrate Japan,
does **not** import Japanese data, and does **not** assert
any real Japanese company / market / ownership / calendar /
filing / index fact. v2.0 only defines what may be
considered later, what must remain forbidden, what must be
represented as generic records first, and what belongs to
v3 proprietary calibration rather than public v2.*

This document is **docs-only at v2.0.0**. It introduces no
runtime module, no new dataclass, no new ledger event, no
new test, no new label vocabulary, no new behavior, no new
data fixture. Every existing v1.21.last canonical
``living_world_digest`` is preserved byte-identically.
v2.0.last (if needed) will be a docs-only freeze. v2.x
implementations (if any) require a fresh design pin per
sub-milestone.

---

## A. Purpose

v2.0 defines the **boundary** for any future Japan public
calibration work. It does not perform calibration. It does
not ingest Japanese data. It does not introduce real
Japanese identifiers or facts.

The single purpose of v2.0 is to make it impossible for any
future agent — human or otherwise — to confuse:

1. **Public calibration.** The use of legally accessible,
   redistributable or reference-only public sources to
   anchor a generic FWE substrate primitive (a v1.26
   `UniverseEventRecord`, a v1.26
   `ReportingCalendarProfile`, a v1.27
   `StrategicRelationshipRecord`, a v1.24
   `ManualAnnotationRecord`) to a Japan-specific
   observable.
2. **Real-data ingestion.** The actual mechanical pull of
   raw Japanese filings or market data through an adapter
   (EDINET / TDnet / J-Quants / FSA filing / JPX / TOPIX /
   index-constituent feed). v2.0 has no adapter, designs
   no adapter, and forbids any adapter implementation in
   the v2.0.x sequence.
3. **Proprietary alpha.** Predictive models, expert priors,
   alpha hypotheses, paid-dataset calibrations, client-
   specific assumptions. v2.0 hard-forbids proprietary-
   alpha calibration in public v2; that work belongs to
   the proprietary v3 track and must not be open-sourced.
4. **Investment advice.** Buy / sell / hold / target-price
   / portfolio-allocation / forecast / recommendation
   output. v2.0 hard-forbids any investment-advice
   semantic, even as a hypothetical v2.x extension.
5. **Japan-specific factual claim.** Naming a real
   Japanese company, asserting a real ownership
   percentage, claiming a real fiscal year-end month, or
   citing a real listing date. v2.0 hard-forbids any such
   claim and pins the requirement that any future Japan-
   specific factual claim must travel through (a) a
   citation-bound `ManualAnnotationRecord` with v1.27.3
   provenance, and (b) the closed-set generic record
   shapes already shipped at v1.26 / v1.27.

v2.0 is therefore a **design-only contract**. It binds
future v2.x work without performing any of it.

---

## B. Why v2.0 comes after v1.26 and v1.27

Japan public calibration cannot exist without generic
substrate primitives that can carry Japan-specific
observables without leaking real-data assumptions into the
canonical v1 fixtures. v1.26 and v1.27 closed the **last
generic substrate additions** in public v1.x; v2.0 can now
define Japan boundaries against fully-shipped substrate.

### B.1 Generic primitives v2.0 builds on

From **v1.26 (Entity Lifecycle + Reporting Calendar
Foundation)**:

- `UniverseEventRecord` (closed-set
  `UNIVERSE_EVENT_TYPE_LABELS`: entity_listed /
  entity_delisted / entity_merged / entity_renamed /
  entity_split / entity_status_changed / unknown) —
  abstract listing-lifecycle primitive that any v2.x
  Japan listing event must use unchanged. Real Japanese
  listing dates and exchange transitions, when admitted,
  travel through this record only.
- `ReportingCalendarProfile` (closed-set `MONTH_LABELS`,
  `DISCLOSURE_CLUSTER_LABELS`, `REPORTING_INTENSITY_LABELS`)
  — abstract per-entity reporting-calendar primitive that
  any v2.x Japan fiscal-year-end profile must use
  unchanged. Real Japanese fiscal-year-end month
  distributions, when admitted, travel through this
  record only.
- `UniverseCalendarReadout` — read-only multiset projection
  with no event-to-price mapping. Any v2.x Japan reporting
  calendar projection must reuse this readout shape;
  v2.0 forbids any v2.x extension that would add a
  market-effect inference column.

From **v1.27 (Generic Strategic Relationship Network +
Annotation Provenance Hardening)**:

- `StrategicRelationshipRecord` (closed-set
  `RELATIONSHIP_TYPE_LABELS`: strategic_holding_like /
  supplier_customer_like / group_affiliation_like /
  lender_relationship_like / governance_relationship_like
  / commercial_relationship_like / unknown; closed-set
  `DIRECTION_LABELS`) — abstract relationship primitive
  with no ownership percentage, no voting power, no
  market value, no centrality score. Any v2.x Japan
  cross-shareholding or supplier-customer mapping must
  use this record unchanged. The `_like` archetype
  suffix is binding.
- `StrategicRelationshipReadout` — read-only multiset
  projection. Any v2.x Japan relationship projection must
  reuse this readout shape; v2.0 forbids any v2.x
  extension that would introduce centrality / systemic-
  importance / risk scoring.
- `ManualAnnotationProvenanceRecord` (pseudonymous;
  closed-set `AUTHORITY_LABELS`,
  `EVIDENCE_ACCESS_SCOPE_LABELS`; anti-email-leak guard) —
  abstract provenance primitive. Any future Japan-
  specific manual annotation **must** carry a v1.27.3
  provenance companion record. v2.0 makes provenance
  mandatory for any v2.x calibration record sourced from
  a real reviewer.

### B.2 What v1.x did *not* ship that v2.x will need

v1.x did not ship — and v2.0 explicitly does not request:

- Real-data adapters (EDINET / TDnet / J-Quants / FSA
  filing / JPX / TOPIX / index-constituent feed).
- Real Japanese company name / securities code / ticker
  identity bridge.
- Price / volume / market-cap fields on any v1.x record.
- Index constituent / weight / membership semantics.
- Predictive / forecast / target-price / alpha fields.
- Recommendation / advice surface.

v2.x sub-milestones — if approved — will design these
gates in detail. v2.0 only commits to *not* extending
v1.x silently.

---

## C. Three-layer boundary

The v2.0 boundary partitions all calibration work into
exactly three disjoint layers. Every artifact, record,
fixture, document, or commit must be classifiable into
one of these three layers; no fourth layer is permitted.

### C.1 Layer 1 — Generic FWE substrate (public, shipped)

- **Jurisdiction-neutral.** No country-specific
  identifier, no country-specific calendar assumption, no
  country-specific market structure assumption baked into
  any closed-set vocabulary or default boundary flag.
- **Synthetic fixtures only.** Every canonical fixture
  uses `firm:a` / `firm:b` / `firm:c` / `industry:x` /
  `bank:y` style synthetic identifiers; no real names.
- **No real-data adapter.** No HTTP fetch, no XBRL parser,
  no PDF scraper, no API-key consumer in any
  `world/` / `spaces/` / `examples/` module.
- **No real filing-system reference.** No EDINET /
  TDnet / J-Quants / FSA / EDGAR / SEDAR adapter, helper,
  utility, or constants module.
- **Safe to publish.** Every Layer-1 artifact must be
  releasable under the public license without further
  legal review.

v1.18 through v1.27 ship entirely in Layer 1. Layer 1
remains the default residency for any future generic
substrate addition.

### C.2 Layer 2 — Japan public calibration (gated, future)

- **Public, legally accessible source data only.** The
  source must be publicly viewable, the use must be
  permitted by the source license, and the redistribution
  policy of any derived data must be checked separately.
- **Citation-bound.** Every Layer-2 record must carry a
  stable plain-id citation back to its public source
  (e.g. a public-filing reference id, a public-disclosure
  document id). v2.0 makes the citation requirement
  mandatory; the citation field shape will be designed in
  v2.1 / v2.2 / v2.3 candidate sub-milestones.
- **Provenance-bound.** Every Layer-2 manually curated
  annotation must carry a v1.27.3
  `ManualAnnotationProvenanceRecord` companion. The
  provenance must be pseudonymous; the
  `evidence_access_scope_label` must reflect the actual
  source class (public_synthetic / internal_synthetic /
  restricted_synthetic / unknown — the "synthetic"
  qualifier carries forward into Layer 2 because the
  *generic-record shape* is synthetic even when the
  *anchor* is real).
- **Raw-source separation.** Raw downloaded source data
  must not be committed to the repository. Only derived
  generic records (with citations) may be committed, and
  only after a license review.
- **No investment recommendation.** A Layer-2 record may
  state "entity X had a reporting event of type
  `entity_listed` on period_id Y, citation `pub:abc`",
  but may **not** state "buy entity X", "X will
  outperform", "X is undervalued", or any equivalent.
- **Publishable only after data-license review.** A
  Layer-2 commit requires (a) a license review note in
  the design document for that v2.x sub-milestone, (b) an
  explicit redistribution-policy statement, and (c) a
  confirmation that no raw source data is being
  committed.

v2.0 does not ship a single Layer-2 record. v2.x
sub-milestones may, **only after** a fresh design pin
per sub-milestone.

### C.3 Layer 3 — Japan proprietary calibration (closed, not open-sourced)

- **Paid datasets.** Subscriber-only feeds, paid
  consensus estimates, paid relationship maps, paid
  index data.
- **Expert interviews.** Direct conversations with
  Japanese practitioners; non-public expert priors;
  industry-insider commentary.
- **Manually curated proprietary relationship maps.**
  Hand-built cross-shareholding maps that incorporate
  non-public observations.
- **Proprietary scoring rules.** Any model that ranks,
  scores, or filters entities using proprietary inputs.
- **Alpha hypotheses.** Any hypothesis that asserts
  predictive value of a feature for return / volatility
  / drawdown / fund flow.
- **Client-specific calibration.** Mandate-specific
  parameter overrides, attention budgets tuned to a
  client's investment universe, scenario decks
  reflecting a client's view.
- **Non-public assumptions.** Anything not derivable from
  Layer-1 substrate + Layer-2 cited public data.

Layer 3 must **not** be open-sourced. v2.0 forbids any
Layer-3 artifact from being committed to the public
repository, even as a placeholder, even as a
documentation example, even as a "TODO" note. Layer 3
work — if undertaken — belongs to a separate proprietary
v3.x track that lives outside this repository.

### C.4 Layer-disjointness invariant (binding)

A single artifact cannot belong to two layers. If a
record is sourced from a paid feed, it is Layer 3 —
even if it could *also* have been sourced publicly.
If an annotation reflects a non-public expert
conversation, it is Layer 3 — even if the reviewer
also has public-source corroboration. The classification
is by **strongest dependency**, not by weakest.

---

## D. Candidate public data categories for future v2.x

v2.0 lists candidate categories for future v2.x
exploration. **No category in this section is approved
for ingestion.** Each category is a candidate only;
admission requires its own design pin and license
review.

For each category, v2.0 specifies:

- the potential future generic target record (a v1.26 /
  v1.27 record shape; never a new schema);
- the citation/provenance requirement at that target;
- a license-risk classification (low / medium / high /
  unknown); and
- whether raw data may be redistributed or only
  referenced.

| # | Category | Future generic target | Citation requirement | License risk | Redistribution |
| - | -------- | -------------------- | -------------------- | ------------ | -------------- |
| D.1 | **Listed entity universe** (which entities exist on a public exchange at a given period) | v1.26 `UniverseEventRecord` (`entity_listed` / `entity_delisted`); v1.27 entity-id citation only — no real name field | mandatory: source filing or exchange notice plain-id citation; v1.27.3 provenance for any manual annotation | medium | reference-only by default; case-by-case review for redistribution |
| D.2 | **Exchange / market segment classification** (segment / tier / board membership) | v1.26 `UniverseEventRecord` (`entity_status_changed`) only — no segment-name field on any v1 record | mandatory: exchange-segment notice plain-id citation | medium | reference-only |
| D.3 | **Issuer lifecycle events** (real listings, delistings, mergers, renames, splits, status changes) | v1.26 `UniverseEventRecord` of the matching closed-set `UNIVERSE_EVENT_TYPE_LABELS` value | mandatory: filing / disclosure plain-id citation | medium | reference-only |
| D.4 | **Reporting calendar / fiscal period anchors** (real fiscal-year-end month per entity, real reporting cadence) | v1.26 `ReportingCalendarProfile` — closed-set `MONTH_LABELS` / `REPORTING_INTENSITY_LABELS` only | mandatory: corporate-disclosure document plain-id citation | low–medium | derived calendar profile may be redistributable; raw filing not |
| D.5 | **Public disclosure metadata** (filing date, filing type, document id, period covered) | metadata only on `UniverseEventRecord` / `ReportingCalendarProfile` `metadata` mapping; never as a new top-level field | mandatory: document plain-id citation | medium | reference-only |
| D.6 | **Public financial statement fields** (a small number of widely-published line items, e.g. revenue, net income at a period level — only where licensing permits) | **NO v1.x record carries financial-statement values today.** A v2.x sub-milestone would require a fresh design pin to introduce a closed-set, value-free *anchor* record. v2.0 forbids retrofitting numeric financial fields onto any existing v1.x record. | mandatory: filing-line plain-id citation | high | almost always reference-only; redistribution case-by-case |
| D.7 | **Public ownership / large-shareholder references** (only where legally usable; jurisdictionally varies) | v1.27 `StrategicRelationshipRecord` with `relationship_type_label = "strategic_holding_like"`, **no ownership_percentage / voting_power / share_count fields** (these remain in `FORBIDDEN_TOKENS_V1_27_0_RELATIONSHIP_DELTA`) | mandatory: large-shareholder report plain-id citation | high | reference-only by default |
| D.8 | **Public relationship signals** (supplier-customer disclosure, group-affiliation disclosure, lender relationship disclosure where publicly disclosed) | v1.27 `StrategicRelationshipRecord` with the matching closed-set archetype label | mandatory: source disclosure plain-id citation | high | reference-only |
| D.9 | **Public macro / sector indicators** (publicly published macro time series — license varies sharply by source) | metadata-only annotation on existing records; no new time-series schema in v2.0 | mandatory: source plain-id citation | medium–high | varies by source; license review required per source |
| D.10 | **Public price and volume references** (only where licensing explicitly permits) | **NO v1.x record carries price / volume fields today.** v2.0 forbids retrofitting price / volume fields onto any existing v1.x record. A v2.x sub-milestone would require a fresh design pin to introduce a closed-set, value-free reference record — and v2.0 pins that even then, no event-to-price mapping is allowed. | mandatory: source plain-id citation | high | usually reference-only; redistribution rare |
| D.11 | **Index constituent membership** (index → entity membership lists) | **NO v1.x record carries index constituent / weight / membership semantics today.** v2.0 forbids any v2.x extension that would introduce index_weight / constituent_weight / index_membership semantics — these tokens already sit in the v1.26.0 forbidden delta. Any future "is a member of an index" semantic must travel through a closed-set generic *group_affiliation_like* relationship and **no weight field**. | mandatory: index methodology plain-id citation | high | almost always reference-only; weights almost always non-redistributable |

The categories above are **the canonical candidate list**.
Any v2.x sub-milestone proposing a category not in this
list requires a fresh design pin amending this section
under a new revision header.

---

## E. Explicitly forbidden at v2.0

The following are forbidden at v2.0. Each item below is
forbidden as a v2.0 commit, as a v2.0.x sub-milestone, and
as any v2.0.last freeze artifact.

### E.1 Adapter implementations (forbidden)

- **EDINET adapter.** No `world/edinet_*.py`, no
  `examples/edinet_*.py`, no `tools/edinet_*.py`, no
  HTTP / XBRL / filing-id fetch logic.
- **TDnet adapter.** No `world/tdnet_*.py`, no
  `examples/tdnet_*.py`, no fetch logic.
- **J-Quants adapter.** No `world/j_quants_*.py`, no
  API-key consumer, no fetch logic.
- **FSA filing adapter.** No `world/fsa_*.py`, no
  filing-pull logic.
- **JPX / TOPIX / Nikkei / GICS / MSCI / S&P / FactSet /
  Bloomberg / Refinitiv adapter.** Already forbidden at
  v1.26.0; re-pinned at v2.0.
- **EDGAR / SEDAR / equivalent non-Japan adapter.** Out
  of scope at v2.0; same forbidden status.

### E.2 Real-data ingestion behaviors (forbidden)

- Scraping real filings (HTML / PDF / XBRL parse).
- Importing real company lists (CSV / Parquet / JSON of
  real Japanese company names or any country's company
  names).
- Importing real securities codes (ticker / ISIN / CUSIP /
  SEDOL / Japanese 4-digit code).
- Importing real cross-shareholding data.
- Importing real index constituent lists.
- Importing real price / volume / market-cap data.
- Loading real fiscal-year-end month distributions from a
  paid or scraped source.

### E.3 Data-source classes (forbidden)

- Paid datasets (Bloomberg, Refinitiv, FactSet, Capital
  IQ, S&P CIQ, MSCI, paid consensus, paid event feeds).
- Employer / internship / private data ("data I have
  access to from work").
- Expert-interview content (transcripts, paraphrases,
  notes from a private conversation).
- Non-public assumptions (priors that cannot be derived
  from publicly cited sources).

### E.4 Output / claim classes (forbidden)

- Generating investment recommendations.
- Event-to-price mapping (already forbidden at v1.26.0).
- Target-price / buy / sell / hold output.
- Portfolio construction output.
- Alpha claims (predictive-value claims about any
  feature).
- Backtest claims.

v2.0 makes the above five output / claim classes
**permanently forbidden in public v2** even after
license review. They belong to proprietary v3 and may
not be open-sourced.

### E.5 Forbidden-token vocabulary linkage

The v1.x composed forbidden-name sets
(`FORBIDDEN_RUN_EXPORT_FIELD_NAMES`,
`FORBIDDEN_STRESS_*_FIELD_NAMES`,
`FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES`,
`FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES`,
`FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES`,
`FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES`,
`FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES`)
already cover the bulk of these prohibitions at the
storage / readout / export surfaces. v2.0 pins the
following additional rule for v2.x sub-milestones: **any
new v2.x record shape must inherit at least one of these
composed forbidden-name sets verbatim** and may extend
it only with new prohibitions, never with relaxations.

---

## F. Public-data license policy

The public-data license policy below is **binding for the
v2 sequence as a whole**. v2.0 commits no data; v2.0.x
and v2.1.x commits (if any) must satisfy these rules.

### F.1 Publicly viewable ≠ freely reusable

A document being publicly viewable on a website does
**not** automatically make it redistributable, derivable,
or reusable. Most public Japanese disclosure systems
allow viewing under license terms that restrict bulk
download, redistribution, and derivative-work
publication. v2.0 pins that the default assumption for
any new public source is **non-redistributable until
proven otherwise**.

### F.2 Redistribution vs. derived-data publication

These are two separate questions and must be answered
separately for every source:

- **Raw redistribution.** Can the original document /
  feed be re-hosted? Almost always: no. Default: no.
- **Derived-data publication.** Can a derived,
  generalised, citation-bound record (e.g. a
  `UniverseEventRecord` carrying only the generic event
  shape + a citation back to the original) be
  published? Sometimes. Default: requires explicit
  license review per source.

### F.3 Adapter-implementation gating

A real-data adapter requires, before any code is
written:

1. A v2.x sub-milestone design pin naming the source.
2. An explicit license note in that design pin.
3. A redistribution policy statement.
4. A confirmation that no raw source data will be
   committed.
5. A confirmation that derived records will carry
   stable, plain-id citations.

v2.0 forbids any adapter implementation; the gating
above applies to v2.5 candidate or later, only after
v2.0.last freeze and an additional sub-milestone
design pin.

### F.4 Raw source data must not be committed

Under no circumstances may raw downloaded source data
(filing HTML, filing PDF, filing XBRL, exchange notice
text, paid-feed payload, scraped HTML) be committed to
the public repository. This rule applies to every v2.x
sub-milestone, every example, every fixture, every
test resource.

The only items that may be committed are:

- generic v1.26 / v1.27 records carrying a stable plain-
  id citation back to the source (Layer 2);
- the citation reference string itself (a public URL or
  a public document id), provided the URL / id itself
  is not subject to a no-publication clause; and
- a license-review note in the design document
  describing the source class.

### F.5 Synthetic-default rule

Future v2.x examples must default to **synthetic
fixtures**. A license-safe sample may be added only
after explicit approval per the F.3 gating. The
canonical v1 fixtures (`quarterly_default`,
`monthly_reference`, `scenario_monthly_reference_universe`,
v1.20.4 CLI bundle) **must not gain Japan fields,
real-data fields, or Japan-only paths** under any
v2.x sub-milestone — see §J.

### F.6 Citation discipline

Citation IDs are **mandatory** for any future real-data-
derived record. The citation must be:

- **stable** — the id must not change across revisions
  of the same source;
- **plain-id** — string only, no schema-bearing dict;
- **traceable** — the id must permit a reviewer to
  locate the source via a reference list living
  alongside the record's design pin; and
- **license-safe** — the id itself must not violate
  the source's no-publication clause.

---

## G. Entity identity policy

### G.1 v2.0 introduces no real identity

v2.0 introduces no real company name, no real securities
code, no real ticker, no real ISIN / CUSIP / SEDOL, no
real Japanese 4-digit code, no real LEI, no real
exchange-issued identifier of any kind. v2.0.x will not
introduce these either; the question is deferred.

### G.2 Future identity-mapping principles (designed only)

If a future v2.x sub-milestone designs a real-identity
mapping, it must satisfy:

- **Mapping principle: separation.** The real-identity
  bridge must be a distinct module (e.g. a future
  `world/japan_identity_bridge.py`), not a field on a
  generic v1.x record. The bridge translates between a
  generic synthetic id and a real id; the generic record
  itself never carries the real id.
- **Mapping principle: opt-in.** The bridge must be
  empty by default. A canonical v1 fixture must not
  populate it; only an explicit Japan-fixture path may.
- **Mapping principle: license-reviewed.** Every entry
  in the bridge must cite the public source authorising
  the public use of the real id (some Japanese
  identifiers are public, others are licensed; the
  distinction matters).
- **Mapping principle: pseudonymous default.** Where
  the real id is not license-safe to publish, the
  bridge must store a pseudonymous placeholder and a
  citation to the (privately retained) real id —
  *and that pseudonymous placeholder is what the
  public repo sees*.
- **Mapping principle: provenance-bound.** Every
  bridge entry that was sourced from a manual reviewer
  must carry a v1.27.3
  `ManualAnnotationProvenanceRecord` companion; the
  reviewer must be pseudonymous; the
  evidence_access_scope_label must reflect the actual
  source class.

### G.3 Synthetic-id default

The public-fixture default remains the synthetic-id
convention used at v1.x: `firm:a` / `firm:b` /
`firm:c` / `industry:x` / `bank:y`. v2.0 forbids any
v2.x sub-milestone from changing the synthetic-id
default in any canonical fixture.

### G.4 Real-identity bridge isolation

If — and only if — a future v2.x bridge is approved,
it must be:

- **module-isolated** (its own file, its own design
  pin);
- **kernel-optional** (no `WorldKernel` field becomes
  mandatory because of it);
- **digest-neutral** (an empty bridge keeps every
  v1.21.last canonical `living_world_digest` byte-
  identical); and
- **license-review-gated** (no commit without an
  explicit license review note).

---

## H. Calibration policy

v2.0 distinguishes four categories of calibration. Each
has its own admission criteria; mixing them is forbidden.

### H.1 Structural calibration (allowed in v2)

Anchoring the *shape* of generic records to Japan-
observable structure: e.g. confirming that a Japanese
listed entity's lifecycle events fit the closed-set
`UNIVERSE_EVENT_TYPE_LABELS`; confirming that a
Japanese fiscal-year-end month is one of
`MONTH_LABELS`; confirming that a publicly-disclosed
relationship fits one of the `_like` archetypes in
`RELATIONSHIP_TYPE_LABELS`.

Structural calibration is allowed in v2.x. It does
not introduce numeric values, alpha claims, or
predictions. It only checks "does the generic
substrate fit?".

### H.2 Parameter calibration (allowed in v2 only with explicit gating)

Anchoring small numeric defaults (e.g. how many
Japanese fiscal-year-ends fall in March on the open
market — a count, not a forecast) to public sources.

Parameter calibration in v2.x **must**:

- target only generic-record metadata, never a
  predictive output;
- carry a citation per anchor;
- be reversible (removing the calibration must restore
  every canonical digest byte-identically); and
- be flagged in the design pin of its sub-milestone.

### H.3 Empirical validation (allowed in v2 with no claim of predictive utility)

Comparing a generic record's structural assumptions
to publicly-observed Japan distributions: e.g.
checking that the closed-set
`DISCLOSURE_CLUSTER_LABELS` covers the observed
clusters in public Japanese disclosure timing.

Empirical validation in v2.x **must not**:

- claim predictive utility;
- claim investment usefulness;
- assert profitability;
- imply backtest results.

It may publish a coverage statement ("the closed set
covers N publicly-observed cases out of M") with full
citation. That is the limit.

### H.4 Proprietary alpha calibration (forbidden in public v2)

Any calibration that uses paid data, expert priors,
non-public assumptions, or that claims predictive
value on any feature, is **proprietary alpha
calibration** and belongs to v3, not v2.0. v2.0
forbids any v2.x sub-milestone from approaching this
class, even as an example, even as a TODO note.

### H.5 Japan-specific facts require citations

Any Japan-specific factual claim — at any layer, in
any v2.x sub-milestone — must carry a stable plain-id
citation back to a public source. A Japan-specific
factual claim without a citation is forbidden at
v2.0; there is no path to admit one in v2.x.

---

## I. Provenance and annotation policy

### I.1 v2.0 binds Japan annotations to v1.27 provenance

Every manually created Japan-related record (whether
a v1.24 `ManualAnnotationRecord`, a v1.27
`StrategicRelationshipRecord` annotation, or a future
v2.x calibration anchor) **must** carry a v1.27.3
`ManualAnnotationProvenanceRecord` companion. v2.0
makes provenance mandatory; v1.27.3 made it
available.

### I.2 No real-person identity in any annotation

Manual annotation must not contain:

- real-person names (full names; partial names that
  uniquely identify);
- real personal emails (the v1.27.3 anti-email-leak
  guard rejects any `@` in `annotator_id_label`; v2.0
  generalises this to *all* annotation text fields);
- real phone numbers;
- real national-id / employee-id strings; or
- private comments that paraphrase a private
  conversation.

The `annotator_id_label` must remain pseudonymous
under v1.27.3 rules. Any text field that would
otherwise carry a real-person reference must replace
it with a pseudonymous placeholder.

### I.3 Source-citation vs. analyst-inference separation

A future Japan relationship record must distinguish
two epistemic categories on the same surface:

- **public-source citation:** "the source disclosure
  states X about entity A's relationship to entity B";
- **analyst inference:** "the reviewer interprets the
  disclosure as evidence of relationship type
  `group_affiliation_like`".

These two categories must occupy distinct fields. The
public-source citation lives in the
`evidence_ref_ids` tuple of the v1.27
`StrategicRelationshipRecord`. The analyst inference
lives in a v1.24 `ManualAnnotationRecord` with a
v1.27.3 provenance companion. They must not be
collapsed into one field.

### I.4 Citation IDs must be stable

A citation id is a contract between the record and
the source. It must not change across record
revisions. If a source revises its document id, the
record must append a new annotation referencing the
new id; the old annotation stays in the book (v1.24
append-only discipline).

### I.5 Annotations are descriptive, not advisory

A v2.x annotation may state "the public disclosure
on plain-id `pub:abc` describes entity A as a
shareholder of entity B with no public ownership
percentage stated". It may not state "therefore A is
a controlling shareholder", "therefore A's stake is
material", "therefore B is exposed to A", or any
similar advisory phrasing. Annotation text scanners
already enforce many of these prohibitions at v1.24;
v2.0 re-pins the rule for v2.x.

---

## J. Digest and fixture policy

### J.1 v2.0.0 must not change canonical living_world_digest values

v2.0.0 ships zero runtime change. Every v1.21.last
canonical `living_world_digest` value remains byte-
identical at v2.0.0:

- `quarterly_default` —
  `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
- `monthly_reference` —
  `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
- `scenario_monthly_reference_universe` —
  `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
- v1.20.4 CLI bundle —
  `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`

### J.2 No existing fixture may gain Japan fields

The four canonical fixtures above, plus every
existing test fixture under `tests/`, examples
fixture under `examples/`, and `examples/reference_world/`
artifact, **must not** gain any Japan-specific field at
any v2.x sub-milestone. Their digest stability is
contractual.

### J.3 No existing fixture may gain real-data fields

A canonical fixture must remain synthetic. The
"empty-by-default" rule that already preserves digest
stability under v1.24 / v1.25 / v1.26 / v1.27 is
re-pinned at v2.0 for any future Japan calibration:
*if* a v2.x sub-milestone adds a Japan-specific
record kind, *then* that record kind must be wired as
empty-by-default on the kernel, never populated in
canonical fixtures, and only populated in a separate
opt-in Japan-fixture path.

### J.4 Future Japan fixtures must be separate

Any future v2.x explicit Japan fixture must:

- live in its own file (e.g. a future
  `examples/japan_public_calibration_*.py`), never in
  any existing canonical fixture file;
- run only in opt-in tests, never as part of the
  canonical `living_world_digest` regression suite;
- carry its own digest, distinct from the v1.21.last
  canonical set; and
- be removable without affecting any canonical
  digest byte.

### J.5 Empty-by-default behavior remains required

The empty-by-default rule that v1.24 / v1.25 / v1.26 /
v1.27 used to preserve digest stability is binding for
the v2 sequence. Any v2.x record-bearing module must
default to empty on the kernel and emit no ledger
record under an empty book.

---

## K. Future v2.x roadmap

The roadmap below is **proposal only**. v2.0.0 commits
to v2.0.0 itself and (provisionally) to a v2.0.last
docs-only freeze. Any other line below requires its own
design pin.

| Sub-milestone | Surface | Status |
| ------------- | ------- | ------ |
| **v2.0.0** | Japan Public Calibration Boundary Design — docs-only design pin (this document) | Shipped here |
| v2.0.last | Docs-only freeze, if needed after review | Provisional |
| v2.1 candidate | Japan public entity-universe schema boundary — synthetic examples only; no real ids; no real-data adapter; design-only on what a future Japan-cited `UniverseEventRecord` would look like | Not started; gated by license review |
| v2.2 candidate | Japan reporting-calendar public-source mapping design — synthetic examples only; design-only on what a future Japan-cited `ReportingCalendarProfile` would look like | Not started; gated by v2.1 |
| v2.3 candidate | Japan public relationship-source mapping design — synthetic examples only; design-only on what a future Japan-cited `StrategicRelationshipRecord` + provenance would look like | Not started; gated by v2.2 |
| v2.4 candidate | Japan public disclosure metadata boundary design — what disclosure metadata may be cited; what may not | Not started; gated by v2.3 |
| v2.5 candidate | License-safe adapter interface design — interface only; no real adapter implementation | Not started; gated by v2.4 + license review |
| v3.0 candidate | **Proprietary calibration boundary — not open-sourced.** Lives outside this repository | Out of scope for the public repo |

v2.0 does **not** commit to implementing v2.1 / v2.2 /
v2.3 / v2.4 / v2.5. Each is a candidate. Each requires
its own design pin and license review. v2.0 commits
only to the boundary that constrains them.

---

## L. Commercial boundary

v2.0 makes the commercial boundary explicit so that
public-track work does not erode the proprietary asset.

### L.1 Public v2 may show structural seriousness

The public v2 track demonstrates that the substrate
can carry real-world calibration without leaking
investment-advice semantics. Showing structural
seriousness — that v1.x records *can* anchor to public
Japan observables under disciplined provenance and
license rules — is appropriate and welcome in public
v2.

### L.2 Public v2 must not reveal proprietary alpha hypotheses

Any specific belief about *why* a Japan structural
feature should be expected to predict return /
volatility / drawdown / fund flow is proprietary
alpha. The public v2 sequence must not discuss,
example, or document such beliefs. v2.0 forbids:

- describing a Japan-specific structural feature as
  "predictive";
- describing a relationship pattern as a "signal";
- describing a calendar feature as an "anomaly";
- describing a disclosure pattern as a "factor"; or
- otherwise embedding alpha-claim language anywhere
  in a public v2.x artifact.

### L.3 Proprietary v3 is where paid data and expert priors live

Paid datasets, paid event feeds, paid consensus
estimates, expert-interview transcripts, manually
curated proprietary relationship maps, proprietary
scoring rules, and client-specific calibration belong
to a separate proprietary v3 track. v3 lives outside
this repository. v2.0 forbids any v3 artifact from
being committed to the public repository.

### L.4 Open-source release should protect the future commercial asset

The public release must remain valuable as a generic
substrate without commodifying the commercial work
that depends on it. The boundary above achieves this
asymmetry: public v2 publishes the *shape* and the
*discipline*; proprietary v3 retains the *signal*
and the *parameter values*.

---

## M. Design invariants

The following invariants are binding for the v2
sequence. Every v2.x sub-milestone must satisfy each.
Any violation requires this document to be revised
under a fresh revision header before the offending
work proceeds.

| # | Invariant | Binding scope |
| - | --------- | ------------- |
| M.1 | **Public FWE remains jurisdiction-neutral by default.** No country-specific identifier, calendar assumption, or market structure assumption may be baked into any closed-set vocabulary, default boundary flag, or canonical fixture. | All v2.x sub-milestones |
| M.2 | **Japan calibration is opt-in.** A canonical v1 fixture may never depend on Japan calibration, even partially. Japan calibration appears only in opt-in Japan fixtures. | All v2.x sub-milestones |
| M.3 | **Real data is citation-bound.** Any record sourced from real public data carries a stable plain-id citation to the source. | All v2.x sub-milestones |
| M.4 | **Source license is tracked before ingestion.** No real-data adapter is implemented without an explicit license-review note in its sub-milestone design pin. | v2.5 candidate and beyond |
| M.5 | **No investment advice.** No v2.x artifact carries buy / sell / hold / target-price / portfolio-allocation / forecast / recommendation semantics, in any field, label, value, metadata key, payload key, or text fragment. | All v2.x sub-milestones |
| M.6 | **No alpha claim without validation.** No v2.x artifact asserts predictive value on any feature, even with caveats. (Public v2 makes no alpha claims at all; alpha-with-validation belongs to proprietary v3, outside the public repo.) | All v2.x sub-milestones |
| M.7 | **No proprietary data in the public repo.** No paid feed, no paid dataset, no expert-interview content, no manually curated proprietary map, no client-specific assumption. | All v2.x sub-milestones |
| M.8 | **No private annotation leakage.** No real name, email, phone, national-id, employee-id, or paraphrase of a private conversation appears in any annotation, metadata, payload, or text field. | All v2.x sub-milestones |
| M.9 | **No digest impact for existing canonical fixtures.** Every `quarterly_default` / `monthly_reference` / `scenario_monthly_reference_universe` / v1.20.4 CLI bundle digest stays byte-identical at every v2.x sub-milestone. | All v2.x sub-milestones |

Silent extension of v2 is forbidden. Any v2.x
sub-milestone that proposes work outside the
boundary above must amend this document under a new
revision header before any code or fixture is
committed.

---

## v2.0.0 closing statement

v2.0.0 is a docs-only design pin. It introduces no
runtime module, no new dataclass, no new ledger event,
no new test, no new label vocabulary, no new behavior,
no new data fixture, no real-data adapter, no real
Japanese company name, no real securities code, no
real filing data, no real cross-shareholding data, no
real reporting-calendar data, no index constituent
data, no price-impact model, no investment
recommendation. v2.0.0 changes no canonical
`living_world_digest` value.

v2.0.0 only **defines the boundary** between (1) the
generic public FWE substrate, (2) future Japan public
calibration using legally accessible public data, and
(3) Japan proprietary calibration using paid data,
interviews, manual expert annotation, or non-public
assumptions. The boundary is binding: future agents —
human or otherwise — that confuse public calibration
with real-data ingestion, proprietary alpha, or
investment advice are out of compliance with v2.0 and
must amend this document before proceeding.

The next milestone (provisional) is **v2.0.last
docs-only freeze**. v2.1 / v2.2 / v2.3 / v2.4 / v2.5
candidates exist on the roadmap but are not scheduled.
v3.x proprietary calibration belongs to a separate
proprietary track and is **not** open-sourced.

---

## N. v2.0.last freeze (docs-only)

*Final pin section for the v2.0 sequence. v2.0.last
ships **no** new code, **no** new tests, **no** new
RecordTypes, **no** new dataclasses, **no** new label
vocabularies, **no** UI regions, **no** export-schema
changes, **no** new fixtures, **no** real-data
adapter, **no** real Japanese identifier of any kind.*

### N.1 What v2.0.last is

v2.0.last is the freeze of the **public boundary**.
It marks the point at which the public FWE
repository commits to remaining a generic substrate
+ boundary-documentation artifact, rather than
becoming a Japan-calibrated quantitative product.

v2.0.last commits, in addition to everything pinned
at v2.0.0:

- **v2.0 is a boundary design only.** It defines a
  contract between layers; it is not a calibration
  step, not a Japan-readiness step, and not a
  market-effect step.
- **v2.0 does not begin Japan calibration.** No
  Japan-specific factual claim, no Japan-specific
  identifier, no Japan-specific calibration
  parameter is admitted at v2.0.last. Every Japan-
  observable structural anchor that v2.0 §H allows
  for future v2.x consideration remains *future
  consideration only* — not started.
- **v2.1+ Japan calibration work should not proceed
  in the public repo unless explicitly synthetic and
  license-safe.** Any v2.1 / v2.2 / v2.3 / v2.4 /
  v2.5 sub-milestone that ships in this public
  repository must (a) carry a fresh design pin
  amending this document under a new revision
  header, (b) commit only synthetic examples or
  citation-bound generic records as defined in
  §C.2, (c) carry a per-source license-review note
  per §F.3, and (d) preserve every v1.21.last
  canonical `living_world_digest` byte-identically.
  Anything that cannot satisfy all four conditions
  does not belong in this repository.
- **Real-data work belongs in the private JFWE
  repository.** Real Japanese filings, real
  cross-shareholding extraction, real ownership /
  voting / market-value calibration, paid-feed
  ingestion, expert-interview content, manually
  curated proprietary relationship maps, and any
  client-specific calibration belong to a separate
  private track. They are out of scope for this
  public repository.
- **Public FWE remains a generic substrate /
  portfolio artifact.** The public repository's
  durable purpose is (1) the generic FWE substrate
  shipped at v1.27.last, (2) the v2.0 boundary
  documentation, and (3) any future v2.x synthetic
  illustration that satisfies the four conditions
  above. Beyond that, the public repository serves
  as a portfolio / structural-seriousness artifact
  — not as a Japan-calibrated quantitative product.

### N.2 Pinned at v2.0.last

- `pytest -q`: **5113 / 5113 passing** (unchanged
  from v2.0.0; unchanged from v1.27.last).
- `ruff check .`: clean.
- `python -m compileall -q world spaces tests examples`:
  clean.
- All v1.21.last canonical living-world digests
  preserved byte-identical at v2.0.last:
  - `quarterly_default` —
    `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
  - `monthly_reference` —
    `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
  - `scenario_monthly_reference_universe` —
    `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
  - v1.20.4 CLI bundle —
    `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`
- New runtime files: **0**.
- New runtime modules: **0**.
- New dataclasses: **0**.
- New `RecordType` values: **0**.
- New tests: **0**.
- New tabs: **0**.
- Export schema changes: **0**.
- New real-data adapters: **0**.
- New real Japanese company names: **0**.
- New real securities codes: **0**.
- New fixtures: **0**.

### N.3 Sub-milestone sequence

| Sub-milestone | Surface |
| ------------- | ------- |
| v2.0.0 | docs-only design pin (boundary; sections A–M) |
| **v2.0.last** | this freeze |

### N.4 Hard boundary re-pinned at v2.0.last

The v2.0.0 hard boundary is re-pinned verbatim at
v2.0.last. To re-state explicitly:

- No EDINET / TDnet / J-Quants / FSA filing /
  EDGAR / SEDAR adapter implementation in the
  public repository — at v2.0.last and at every
  v2.x candidate beyond it.
- No real Japanese company name, securities code
  (ticker / ISIN / CUSIP / SEDOL / 4-digit code /
  LEI), filing id, cross-shareholding figure,
  fiscal-calendar table, index constituent list, or
  price / volume series in the public repository.
- No paid dataset, expert-interview content, or
  client-specific calibration in the public
  repository — at any milestone.
- No investment recommendation, target-price /
  buy / sell / hold output, portfolio-construction
  output, alpha claim, or backtest claim in the
  public repository — at any milestone.
- No event-to-price mapping in the public
  repository — at any milestone.
- No private annotation leakage (real names,
  emails, phone numbers, national-ids, employee-
  ids, paraphrased private conversations) in any
  v2.x annotation, metadata, payload, or text
  field.
- No digest impact for existing canonical fixtures
  at any v2.x sub-milestone.

### N.5 Closing statement

v2.0.last freezes the public-repository boundary
in its entirety. From here forward, the public
repository's generic substrate (v1.18 → v1.27.last)
+ boundary documentation (v2.0.0 + this freeze) is
the public commitment. Future Japan calibration
proceeds in the private repository; the public
repository remains the generic substrate +
boundary artifact, and that is its durable shape.

The v2.0 sequence is **frozen**. v2.1 / v2.2 / v2.3 /
v2.4 / v2.5 candidates exist on the roadmap but are
not scheduled in the public repository; if undertaken
they require fresh per-sub-milestone design pins +
license review and must satisfy §N.1 in full. v3.x
proprietary calibration is out of scope for this
public repository.
