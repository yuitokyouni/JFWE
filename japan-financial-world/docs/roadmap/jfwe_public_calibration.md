# Roadmap: JFWE Public calibration

> **Status:** scoped, not started. v2 territory.
> **Layer:** JFWE Public (partially public, depends on per-source
> redistribution rights).
> **Depends on:** FWE Core public release roadmap (must be done so
> v1 contract is stable and the project's public framing is set).
> **Blocks:** any "Japan-calibrated" claim. None of those claims
> are valid until at least the v2.0 milestone of this roadmap
> ships.

## Goal

Layer **Japan public-data calibration** on top of the frozen
v1.7 reference financial system **without changing any v1 record
shape, book API, scheduler extension, or invariant**. v2's job is
to populate v1 books with values drawn from public sources —
nothing more.

This is multi-milestone work. The roadmap below describes the
**v2.0** scope (smallest credible Japan public calibration) and
flags later v2.x extensions.

## v2.0: Smallest credible Japan public calibration

### Public data inventory

- [ ] Pick a small, defensible starter set of public sources:
  - BOJ policy rate history.
  - One BOJ public macro series (e.g., reference-rate FX or one
    aggregated indicator).
  - JPX listing master for one identifiable subset (e.g., TSE
    Prime listings as of a fixed snapshot date).
  - One MOF / Cabinet Office macro series (e.g., monthly CPI).
- [ ] For each source: record the URL, the license or terms-of-use
  reference, the snapshot date, and the field mapping into v1
  record shapes.
- [ ] Store the inventory as a structured doc under
  `docs/v2/<source_name>.md` (one file per source).
- [ ] No source is added to the inventory before its license review
  is on file (next section).

### License review

- [ ] Per-source review document covering: redistribution,
  caching, attribution, commercial use, update obligation, and
  format / API stability — the six-question checklist already in
  `docs/v2_readiness_notes.md`.
- [ ] If a source disallows redistribution, JFWE Public stores
  derived results only and never checks raw data into the public
  repo.
- [ ] If a source's license requires per-deployment registration
  (e.g., JPX market data), the milestone documents the path; it
  does not silently use the data.
- [ ] If a source is paid or requires NDA, it is **not** v2
  material — escalate to JFWE Proprietary roadmap instead.

### Entity mapping

- [ ] Map each Japan public entity onto v1 record shapes. Open
  questions are pre-recorded in `docs/v2_readiness_notes.md` and
  must be answered before populating data:
  - One or two registry entries per ticker?
  - Signal-first or action-first for announcements?
  - How is the BOJ policy rate stored: `MandateRecord` +
    `ExternalFactorProcess`, or one of those alone?
- [ ] Pick an `institution_type` controlled vocabulary
  appropriate for Japan and document it in
  `docs/v2/institution_type_vocabulary.md`.
- [ ] Each Japan institution becomes an `InstitutionProfile` with
  `jurisdiction_label="JP_public"` (or similar).

### Unit / calendar conventions

- [ ] Currency: explicit `currency` field on every priced or
  valued record; default to `"JPY"` only when the source explicitly
  publishes in JPY. Never assume.
- [ ] Time: explicit `as_of_date` per record using the source's
  publication date; convert to ISO `YYYY-MM-DD` at ingestion.
- [ ] Holiday calendar: pick one published Japan business-day
  calendar (e.g., the JPX calendar) and document the snapshot.
  The simulation clock continues to advance one calendar day at a
  time; business-day annotations live in record metadata.
- [ ] Index points / yields / rates expressed in their published
  unit; the unit field is required, not optional.

### No redistribution unless license permits

- [ ] Default: a v2 repository or directory contains code that
  *transforms* public data, plus the **derived** records, plus a
  manifest pointing at the original sources — but **not** the raw
  data.
- [ ] Only when a source's license explicitly permits
  redistribution (with attribution) may raw data be cached in the
  public repo, and only with the attribution embedded next to it.
- [ ] Every committed file derived from a public source carries a
  comment header naming the source, snapshot date, and license.

### Reproducibility

- [ ] A v2 calibration commit is reproducible from a fixed
  snapshot identifier. "Latest" pulls are not allowed in committed
  runs.
- [ ] Calibration parameters (process drift, vol, regime
  probabilities) chosen for v1.4 process specs are fitted from a
  named snapshot, with the fitting code checked in.
- [ ] A v2 calibration ships with a deterministic test that
  asserts the resulting `ExternalFactorObservation` populations,
  `InstitutionProfile` set, and macro time series match a fixed
  expected hash.

## Out of scope for v2

- Any paid or NDA-restricted data. That is JFWE Proprietary (v3).
- Expert overrides for structural breaks. v2 uses what the data
  says; expert judgment is v3.
- News / narrative dynamics. Public news data is rarely
  redistributable; v2 either skips this domain or limits it to
  metadata (titles + dates) under explicit license terms.
- Real-time / intraday data. v2 ships daily-or-coarser data only.
- Tick / trade-by-trade data. v3 territory.
- Stress test scenarios named after real institutions. Even with
  public data, a public-repo stress test that names a real bank's
  losses crosses the public / private boundary.
- Renaming any v1 record shape, book API, or invariant.
- Ingestion harness library / framework decisions that pull in
  large dependencies. Pick the smallest set possible.

## Acceptance criteria for v2.0

The first JFWE Public milestone is done when **all** hold:

1. At least three public sources have license reviews on file.
2. Their data is mapped into v1 record shapes per the entity
   mapping doc.
3. A reproducible calibration test passes on a fixed snapshot.
4. The CI gate from FWE Core release continues to pass.
5. No raw data without redistribution rights is committed.
6. No real-institution stress result is committed.
7. v1.7's 642-test baseline is unchanged; v2 tests add to the
   total without modifying any existing test.
8. A "v2.0 release summary" doc records what was calibrated, from
   what snapshot, and what is **still** out of scope.

## Later v2.x milestones (rough)

- v2.1: Add one more macro series (e.g., GDP) once the v2.0
  pipeline is stable.
- v2.2: Add JPX listings beyond the starter subset, with explicit
  attention to redistribution terms.
- v2.3: Add disclosure-event calendars (TDnet / EDINET dates only,
  not text).
- v2.4: Add Basel III JP capital-ratio rules as
  `ConstraintRecord`s.
- v2.x+: each successor adds one source or one entity mapping.
  Never bundle.

Each v2.x milestone must satisfy the same redistribution / license
/ reproducibility rules above.

## Dependencies

- FWE Core public release (must be tagged) — JFWE Public sits on
  top of v1.7 contract.
- Per-source license reviews (per the above).
- A decision on **where** v2 code lives: same repo or separate?
  This is a v2.0 planning task, not a v1.7 task. Either is
  compatible with the v1 contract.

## Notes

- Treat license reviews as load-bearing. A missing review blocks
  the source.
- "Calibration" means picking parameters from data; it does not
  mean adding behavior. If a v2 milestone proposes to add
  reaction-function logic, that is a v1+ behavioral milestone,
  not v2.
- Every Japan-specific identifier introduced by v2 should be
  reviewed against `docs/naming_policy.md`. Even when real names
  are valid (because they are public-data labels), the FWE Core
  layer's neutral identifiers stay neutral.
