# Roadmap: JFWE Proprietary calibration

> **Status:** scoped, not started. v3 territory.
> **Layer:** JFWE Proprietary (**never public**).
> **Depends on:** JFWE Public calibration roadmap (v3 sits on top
> of a working v2).
> **Blocks:** any commercial / client engagement that uses
> proprietary content or paid data.

## Goal

Layer **proprietary, paid, or expert-curated content** on top of
JFWE Public, in a way that is **operationally and physically
separated from any public artifact** — and that preserves the
audit-trail and source-attribution discipline of the lower layers.

JFWE Proprietary is the only layer in which paid feeds, expert
notes, named-institution stress results, and client-specific
templates are allowed to exist. **None of those artifacts ever
land in the public repository.**

## In scope

### Private repo

- [ ] JFWE Proprietary lives in a **separate private repository**
  (or set of private repositories), not as a private branch of
  the public repo, not as a private subdirectory, and not as a
  `git-crypt`-encrypted blob inside the public repo.
- [ ] The private repo may import or depend on the public repo as
  a read-only library (pinned to a release tag).
- [ ] The private repo's CI / hosting / access control is owned by
  the project; no third-party integration that could exfiltrate
  proprietary data without a documented review.
- [ ] The public repo continues to build, test, and run with the
  private repo absent. No public file imports from a private
  module.

### Provenance schema

- [ ] Every record produced by JFWE Proprietary records a
  `provenance` block in `metadata`, including:
  - `source_kind` ∈ `{public_v2, paid_vendor, expert_interview,
     internal_consensus, expert_override, derived}`,
  - `source_id` (identifier of the source — a vendor product code,
    an interview pseudonym, etc.),
  - `license_id` (reference to the license review document),
  - `snapshot_id` (which version / date of the source was used),
  - `attribution_required` (bool),
  - `redistribution` ∈ `{denied, derived_only, with_attribution,
     unrestricted}`,
  - `pii_present` (bool),
  - `nda_protected` (bool).
- [ ] The provenance block flows through cross-references: a
  derived record inherits the strictest field of its inputs (e.g.,
  if any input is `nda_protected=true`, the derived record is
  too).
- [ ] Provenance is enforced at the ingestion boundary. Records
  without provenance are rejected at insertion.

### Expert interview handling

- [ ] Expert interviews are stored as **structured records**, not
  raw transcripts. Fields: pseudonymous expert id, role tag, date,
  topic tag, structured claims, paraphrase quality flag, link to
  the raw notes (which live in restricted storage, not the repo).
- [ ] Quotes are never reused verbatim in derived artifacts.
  Paraphrased structured claims are.
- [ ] Each expert id has an access-control policy (who can read
  the link to raw notes; who can read only the structured claims;
  who can read nothing).
- [ ] When an expert claim is used to override a v1.4
  `ExternalFactorProcess` parameter, the override carries the
  expert id and date in its provenance block. The override is
  reversible (the public-data fit is preserved alongside).

### Paid data handling

- [ ] One ingestion adapter per paid vendor, each isolated to its
  own module so the legal scope of each vendor is clear.
- [ ] Vendor data **never** lands in the repo as raw rows. Cache
  layers (if any) live outside the repo, with documented retention
  and rotation.
- [ ] Vendor identifiers (account ids, API keys, license codes)
  live in a secret store, not in the repo. The repo references
  them by name; runtime resolves them.
- [ ] Vendor-derived records carry a `redistribution=denied` flag
  unless the contract explicitly permits derived-result
  publication, in which case `redistribution=derived_only`.
- [ ] Outputs that include vendor data (or derive from it) are
  watermarked / attributed per the vendor's contract terms.

### Named-institution work

- [ ] Stress results, sensitivity tables, and counterparty-network
  analyses tied to real-institution names live only in JFWE
  Proprietary.
- [ ] Each artifact carries an audience scope (who can read it)
  and an expiration (when it must be re-reviewed or deleted).
- [ ] No named-institution result is exported, screenshotted, or
  shared outside that audience scope without a re-review.

### Client / engagement templates

- [ ] Client-specific scenario templates live under a `clients/`
  directory in the private repo, with one subdirectory per client
  engagement.
- [ ] Each client subdirectory has its own provenance and audience
  scope.
- [ ] Templates are reviewed for "could this leak the client's
  identity if exfiltrated" before any cross-engagement reuse.
- [ ] Aggregated learnings from client work that *could* be
  generalized to FWE Core or JFWE Public must go through an
  explicit declassification review — the default is to keep them
  private.

### No public release

- [ ] Nothing in this layer is ever pushed to the public repo,
  ever — not for marketing, not for transparency, not for talks.
  If a finding from this layer is genuinely worth sharing, the
  declassification review either approves a sanitized public
  version (synthesized, with names removed) or denies the share.
- [ ] Public-facing materials about the project's existence may
  describe JFWE Proprietary in **abstract** terms (this roadmap
  doc itself is fine), but never name a specific client, vendor,
  expert, or stress result.

## Out of scope

- Replacing JFWE Public. Proprietary builds on top of public; it
  does not displace it.
- Breaking the v1 record-shape contract. Provenance is a
  metadata-level discipline, not a record-shape change.
- Hosting / SaaS / multi-tenant architecture for proprietary
  content. v3 is operationally a research / consulting layer
  before it becomes a productized layer.
- Web UI on proprietary outputs. The to-C demo roadmap covers any
  UI; that is a deliberately downstream and synthetic layer.
- "Anonymized" public release of proprietary artifacts as a
  shortcut to publication. Re-identification risk is real;
  declassification reviews exist for this reason.

## Acceptance criteria for v3.0 (initial JFWE Proprietary setup)

A first JFWE Proprietary milestone is "done" when:

1. The private repo exists with documented access controls.
2. The provenance schema is defined and enforced at ingestion.
3. At least one paid-vendor ingestion adapter is wired and proves
   it can compute a derived result without leaking raw data.
4. At least one expert interview is encoded as a structured
   record, with raw notes stored outside the repo.
5. A test suite (private) verifies that proprietary records carry
   valid provenance, and that derived records inherit the
   strictest input flags.
6. A declassification-review template exists.
7. A documented "if this repo is leaked, here is the response
   plan" runbook exists.

## Dependencies

- JFWE Public (v2.0+) — proprietary work calibrates over public,
  not in place of it.
- A legal review of vendor contracts. Until that is on file, no
  paid data is ingested.
- A storage / access-control decision (where do raw expert notes
  live? what authentication?).
- A decision on whether proprietary work funds a separate hosted
  environment or is purely local. Default: purely local until
  there is a real reason to host.

## Notes

- The most dangerous failure mode of this layer is **accidental
  public exposure**. Every design choice should be evaluated
  against "what happens if this leaks." Default to the safest
  option.
- The second most dangerous failure mode is **provenance drift**:
  a derived record losing track of its source. Build the schema
  so this fails loudly at insertion, not silently at export.
- Public-facing language about the project should never claim
  proprietary capability that the public layer does not have.
  "We have a proprietary calibration" is fine; "our public model
  is calibrated to Japan" is not.
