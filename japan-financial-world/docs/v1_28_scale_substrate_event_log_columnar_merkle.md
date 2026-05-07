# v1.28 Scale Substrate — Event Log + Columnar Storage + Merkle Digest — Design Note

*v1.28 is a **generic engineering scale substrate**
proposal. It pins the architecture for moving public
FWE off the in-memory Book / Ledger extension path and
onto an immutable on-disk event log + lazy materialized
views + a Merkle-style digest tree. v1.28 is not Japan
calibration, not real-data ingestion, not investment
modeling, not price prediction, not alpha research, not
proprietary calibration.*

This document is **docs-only at v1.28.0**. It introduces
no runtime module, no new dataclass, no new ledger event,
no new test, no new label vocabulary, no new fixture,
no Polars / DuckDB / PyArrow / xxhash / Rust / PyO3
dependency, no Parquet file, no event-log writer, no
benchmark test, and no change to the current Ledger /
Book behavior or to the current canonical
`living_world_digest` implementation. Every existing
v1.21.last canonical digest is preserved byte-identically.
v1.28.1 / v1.28.2 / v1.28.3 / v1.28.4 / v1.28.5 / v1.28.6
/ v1.28.7 / v1.28.8 / v1.28.9 / v1.28.last (if any)
implement strictly to this design or the design must be
re-pinned.

---

## A. Purpose

v1.28 is a **generic engineering scale substrate**. It
addresses, in this order:

1. **Ledger explosion.** The append-only ledger has
   grown by ~250 RecordType events / period under v1.20+
   fixtures. At 100x scale (3000 firms × 60 periods,
   plus stress / scenario / annotation overlays) the
   ledger holds tens of millions of records. Keeping
   the entire history hydrated in Python `dataclass`
   instances on every kernel object is infeasible.
2. **Book memory pressure.** Every `*Book` (ownership /
   contracts / prices / scenarios / stress applications
   / manual annotations / investor mandates / universe
   events / reporting calendars / strategic
   relationships / annotation provenance) keeps every
   record it has ever seen in a Python dict. At scale,
   the working set exceeds the addressable Python heap
   on a typical local development machine.
3. **Historical snapshot cost.** `Book.snapshot()`
   currently materialises every record into nested
   plain-dict / list / tuple structures. Whole-history
   snapshots scale linearly with total record count and
   become the dominant cost of digest computation /
   export bundle creation / replay validation at scale.
4. **Full digest recomputation cost.** The current
   `living_world_digest` is recomputed from scratch
   each time. At 100x scale this is unacceptable when
   only a single partition (one period × one sector ×
   one record type) actually changed.
5. **Future 100x synthetic scale.** Even the *synthetic*
   target — 3000 firms × 60 periods, plus optional
   400 investors and 30 banks — exceeds what the
   current architecture handles cleanly without an
   on-disk canonical event log + columnar query path.

v1.28 is **NOT**:

- Japan calibration (no real Japanese identifier; no
  EDINET / TDnet / J-Quants / FSA filing / JPX /
  TOPIX / Nikkei / GICS / MSCI / S&P / FactSet /
  Bloomberg / Refinitiv adapter, helper, utility, or
  constants module).
- Real-data ingestion (no real prices, real holdings,
  real filings, real ownership figures, real fiscal-
  year-end month distributions, real index
  constituents).
- Investment modeling (no buy / sell / hold / target-
  price / portfolio-allocation / forecast /
  recommendation / alpha / backtest / event-to-price
  output).
- Proprietary calibration (no paid data, no expert-
  interview content, no manually curated proprietary
  relationship maps, no client-specific calibration).
- A licence-review-gated milestone (v1.28 is generic;
  it inherits v1.26.last + v1.27.last + v2.0.last
  hard boundaries verbatim).

v1.28 sits in **Layer 1 — Generic FWE substrate** of
the v2.0 three-layer boundary (`docs/v2_0_japan_public_calibration_boundary.md`
§C.1). It changes how the substrate scales; it does
not change what the substrate represents.

---

## B. Problem statement

The in-memory Book / Ledger extension path **will
fail** at the engineering target scale. The failure is
not a single bug; it is a class of failures with a
common root cause:

- **All historical records cannot remain fully
  hydrated in Python objects.** At 100x scale, the
  working-set memory exceeds typical local heap. Each
  frozen dataclass instance carries Python object
  overhead well beyond the bytes its fields occupy.
- **Naive snapshots over all history create memory
  pressure.** `Book.snapshot()` deep-copies every
  record into plain-dict structures, then deep-copies
  again into bundle export. At scale this dominates
  wall-clock and peak RSS.
- **Full O(N) digest recompute is unacceptable when
  only one partition changes.** Most simulation
  iterations only mutate a small period × sector ×
  record-type cell. Recomputing the whole-history
  digest each time is wasted work.
- **Historical queries should not require loading all
  records.** Common operations
  (`Book.list_by_<key>(...)`, period-window readouts,
  cross-record citation walks) need a small slice;
  they should not pay the cost of hydrating the
  entire history.
- **Scale requires a canonical append-only event log
  plus lazy projections.** The on-disk event log is
  the canonical source of truth; in-memory Books
  become projection caches that can be discarded and
  rebuilt deterministically.

These five failures are **architectural**. They cannot
be fixed by tuning the in-memory `*Book` classes. They
require the three-layer separation in §C.

---

## C. Architecture overview

v1.28 introduces three layers and pins the
relationships between them. The layers are
**conceptual only at v1.28.0**; runtime modules,
dataclasses, file formats, and helper functions are
v1.28.1+ work.

### C.1 Layer 1 — Immutable event log

- **Canonical source of truth.** Every record that
  exists at any v1.x kernel-book level (ownership /
  contracts / prices / signals / valuations /
  institutions / external_processes / relationships /
  interactions / routines / attention / variables /
  exposures / stewardship / engagement / escalations /
  strategic_responses / industry_conditions /
  market_conditions / capital_market_readouts /
  market_environments / firm_financial_states /
  investor_intents / attention_feedback /
  settlement_accounts / settlement_payments /
  interbank_liquidity / central_bank_signals /
  corporate_financing_needs / funding_options /
  capital_structure_reviews / financing_paths /
  security_market / investor_market_intents /
  aggregated_market_interest /
  indicative_market_pressure / scenario_drivers /
  scenario_applications / information_releases /
  reference_universe / scenario_schedule /
  stress_programs / stress_applications /
  manual_annotations / investor_mandates /
  universe_events / reporting_calendars /
  strategic_relationships /
  manual_annotation_provenance) becomes a row in the
  event log.
- **Append-only.** No event is ever modified after
  it is written. Revisions append a new event citing
  the prior one (the v1.24 / v1.25 / v1.26 / v1.27
  append-only discipline carries forward unchanged).
- **On-disk in future implementation.** v1.28.0 does
  not write any file. v1.28.5+ may write Parquet
  behind an optional dependency gate. v1.28.2 may
  prototype with JSONL or in-memory only.
- **Future target: partitioned Parquet.** See §D for
  the partition shape.
- **No mutation of historical records.** Sealed
  partition files are read-only on disk; new events
  always create a new part file (see §I).

### C.2 Layer 2 — Materialized views

- **Current period can be hydrated.** A single
  active period's records may be materialised into
  Python objects (much like the current `*Book`
  classes) for low-latency local access.
- **History is lazy-loaded.** Older periods are
  loaded only when explicitly requested via a
  projection function.
- **Book / list / snapshot behavior becomes
  projection over event-log slices.** The current
  `Book.list_*(...)` and `Book.snapshot(...)`
  methods become deterministic projections that
  stream rows out of the event log under explicit
  filters.
- **Disposable and recomputable.** A materialized
  view may be dropped at any time and rebuilt
  byte-identically from the event log. The view
  caches computation; it is not the source of
  truth.

### C.3 Layer 3 — Digest tree

- **Merkle-style digest over partition cells.**
  Each partition (year_month × sector_id ×
  record_type — see §D) has a leaf digest computed
  from its contents. Inner digests roll up sorted
  child digests. The root digest is deterministic.
- **Partial recompute of changed cells.** Only
  partitions whose contents changed need re-
  hashing; the rest of the tree is reused. This is
  the property the current full-recompute
  `living_world_digest` lacks.
- **Deterministic root digest.** Two runs that
  produce the same canonical event log produce
  byte-identical Merkle root digests, regardless of
  filesystem listing order, dict iteration order,
  query-engine row order, or wall-clock timestamps.
- **Separate from legacy v1.x digest.** The Merkle
  scale digest is a **new** digest surface. It does
  **not** replace `living_world_digest` at v1.28; the
  legacy digest must remain byte-identical for every
  existing canonical fixture (see §L and §M).

The three layers are **physically separable**. The
event log can exist without materialized views (the
materialized-view layer is just a cache). The event
log can exist without the Merkle digest (the digest
layer is just a verification surface). Each layer
has its own §-level boundary in this document.

---

## D. Event-log partitioning design

### D.1 Conceptual path shape

```
events/
  year_month=<YYYY_MM>/
    sector_id=<synthetic_sector_id>/
      record_type=<record_type>/
        part-*.parquet
```

Partition keys (binding for v1.28.x):

- `year_month` — derived from the record's logical
  period. The exact derivation rule is part of the
  partition schema manifest (§N) and pinned at
  v1.28.3.
- `sector_id` — synthetic sector identifier (e.g.
  `industry:x` / `industry:y`). Real sector
  taxonomies (GICS / NACE / JPX-TSE / TOPIX-17 / 33)
  are forbidden; v1.28 uses synthetic sector ids
  only.
- `record_type` — the v1.x `RecordType` enum value
  string (e.g. `manual_annotation_recorded`,
  `strategic_relationship_recorded`,
  `universe_event_recorded`,
  `reporting_calendar_profile_recorded`,
  `manual_annotation_provenance_recorded`, plus the
  full v1.18+ set).

### D.2 Partition schema is part of the digest manifest

**Important.** The partition schema is itself part
of the digest manifest (§N). Changing the partition
schema changes the Merkle root digest. **This is not
a bug.** It is a schema/version change and must be
explicit:

- A new partition key dimension (e.g. adding
  `run_id` to the partition path) bumps
  `partition_schema_version`.
- Renaming a partition key dimension (e.g.
  `year_month` → `period_id`) bumps
  `partition_schema_version`.
- Reordering partition key dimensions does not
  change semantics but does change the manifest;
  bump `partition_schema_version` to surface it.

A silent partition-schema change is a digest
correctness bug. The Merkle digest is required to
react.

### D.3 Candidate event schema

The candidate event-row schema for v1.28.1+ work is:

| Field | Type (notional) | Purpose |
| ----- | --------------- | ------- |
| `event_id` | string | stable plain-id |
| `run_id` | string | run scope; appears in manifest, not in partition path |
| `period_id` | string | logical period; e.g. `2026-Q2` |
| `year_month` | string | partition key (e.g. `2026_06`) |
| `sector_id` | string | partition key |
| `record_type` | string | partition key; matches v1.x RecordType |
| `source_space` | string | which v1.x kernel-book / space emitted the event |
| `target_entity_type` | string | optional — the entity class the record describes |
| `target_entity_id` | string | optional — plain-id of the affected entity |
| `event_index` | int | dense per-record-type ordinal within the partition |
| `payload_schema_version` | string | which payload schema this row's payload conforms to |
| `payload_ref_or_json` | string | inline JSON or a plain-id reference into a side-table |
| `parent_event_ids` | list[string] | citation tuple to predecessor events |
| `provenance_kind` | string | closed-set: synthetic / annotated / projected / unknown |
| `synthetic_seed` | string \| null | synthetic-fixture seed if applicable |
| `created_at_logical` | string | logical period stamp; **never** a wall-clock timestamp |
| `partition_key` | string | denormalised for query convenience |
| `canonical_sort_key` | string | the row's position in the canonical sort order (§E) |

Every field above is **synthetic-by-default**. v1.28
forbids any field that would carry a real Japanese
identifier (real ticker, real company name, real LEI,
real securities code, real filing id) — those are
v2.x candidates, gated by `docs/v2_0_japan_public_calibration_boundary.md`
§D.

### D.4 Forbidden partition keys

The partition key space is restricted by §W and
inherits the v1.26.0 / v1.27.0 / v2.0.0 forbidden-
token vocabularies. Specifically, no partition key
may carry any of the following:

- A real Japanese sector / industry classification
  (TOPIX-17 / TOPIX-33 / GICS / NACE / JPX). Use
  synthetic sector ids only.
- A wall-clock timestamp.
- A monotonic counter that depends on filesystem
  listing order or dict iteration order.
- An account identifier, securities code, or filing
  reference.

---

## E. Canonical ordering and deterministic serialization

The Merkle digest is correct only if every step from
"records on disk" → "leaf digest bytes" is
deterministic. The following rules are **binding for
v1.28.x**:

1. **Leaf records must be sorted by
   `canonical_sort_key`** before serialisation. The
   `canonical_sort_key` is part of the schema (§D.3)
   and is pinned at v1.28.3.
2. **Inner Merkle children must be sorted by
   partition key / child key** before hashing. Two
   trees with the same set of children but different
   insertion order must produce the same inner
   digest.
3. **Filesystem listing order must never affect
   digest.** Part files within a partition are
   sorted by file name (lex ascending on a stable
   `part-NNNNN.parquet` convention) before
   concatenation.
4. **Dict iteration order must never affect digest.**
   Any dict-shaped value in a payload is serialised
   in key-sorted order.
5. **Polars / DuckDB query output order must never
   affect digest.** Every query feeding a leaf
   digest has an explicit ORDER BY on
   `canonical_sort_key`.
6. **No wall-clock timestamp in digest material.**
   The `created_at_logical` field carries logical-
   period information only. Real wall-clock times,
   if logged at all, live outside the canonical
   event-log columns and outside the digest manifest.
7. **No Python memory address in digest material.**
   No `id(...)`, no `repr(<object>)` containing
   `0x…` addresses, no class-name `__repr__` output.
8. **Stable JSON serialization if JSON is used.**
   When the leaf serializer falls back to JSON, it
   uses sorted keys, no whitespace, UTF-8 bytes,
   and ASCII-escape mode pinned by the manifest.
9. **Stable column order if Arrow / IPC / Parquet
   is used.** The partition manifest pins the
   schema column order; the leaf digest reads
   columns in that exact order regardless of how
   the storage layer returns them.
10. **Stable null handling.** A null value is
    serialised as a single canonical token; the
    manifest pins which (e.g. JSON `null` /
    Parquet logical null with explicit type).
    Round-trip through the storage layer must not
    convert nulls to empty strings or to default
    values.
11. **Stable list / tuple handling.** Lists and
    tuples serialise with explicit length prefixes
    (or with a stable bracket form) so that
    `["a", "b"]` and `["ab"]` are never confusable.
12. **Stable schema version string** is included in
    the manifest. Two runs with different
    `event_schema_version` cannot accidentally
    produce the same root digest.

Any v1.28.x sub-milestone that violates one of the
above rules is a digest-correctness bug and must be
fixed before its commit.

---

## F. Leaf digest computation policy

All Merkle leaf hashing must go through a **single
future function boundary**:

```
compute_leaf_digest(partition_path, *, manifest) -> bytes
```

`compute_leaf_digest(...)` is **the only** path
through which leaf bytes are produced. Required
behavior:

1. Read the partition's part files.
2. Concatenate part files in **explicit sorted file
   order** (lex-ascending by filename; never the OS
   directory enumeration order).
3. Sort rows by `canonical_sort_key` (the manifest
   pins which field).
4. Select **explicit schema column order** from the
   manifest.
5. Serialise each row in a **stable
   representation** (the manifest pins the
   serializer — `leaf_serializer` field, e.g.
   `"json_sorted_keys_v1"` or `"arrow_ipc_v1"`).
6. Hash with **SHA-256**. The leaf digest bytes are
   the SHA-256 hex digest of the concatenated
   serialised rows.

### F.1 Forbidden leaf-hashing patterns

The following are **explicitly forbidden** at any
v1.28.x sub-milestone:

- Hashing raw filesystem order (i.e. relying on
  `os.listdir` or `Path.iterdir` ordering without
  explicit sort).
- Hashing unsorted DataFrame output (Polars /
  pandas / Arrow) without a manifest-pinned
  `ORDER BY canonical_sort_key`.
- Hashing pandas CSV output without stable sort and
  explicit column order.
- Hashing DuckDB / Polars query results without an
  explicit `ORDER BY` on `canonical_sort_key`.
- Multiple independent leaf-hash implementations
  (e.g. one in a writer, one in a verifier). All
  paths route through `compute_leaf_digest(...)`.

### F.2 Hash algorithm boundary

SHA-256 is the canonical hash. Faster non-canonical
checksums (xxhash, blake3) may be used internally as
**caches** or fast inequality checks but must not
appear in the canonical digest manifest unless the
boundary is explicitly versioned (see §L).

---

## G. Materialized view policy

The Layer-2 materialized view is a cache; the
event log is the source of truth. The following are
**binding** for any v1.28.x materialized-view
implementation:

- **Current period is allowed to hydrate into Python
  objects.** A single active period may be materialised
  into the existing `*Book` shape (frozen dataclass
  instances in a dict) for low-latency local access.
- **Historical periods should be loaded through
  event-log queries.** Older periods load lazily via a
  projection function (e.g. a future
  `project_book_at(book_kind, *, period_window) ->
  *Book`).
- **`Book.list_*` methods may become projection APIs.**
  The current method signatures may be preserved, but
  the body becomes a projection over event-log
  slices rather than an in-memory dict iteration.
- **`snapshot()` is a deterministic projection, not
  necessarily a stored object.** Two
  `book.snapshot()` calls on the same event-log
  state must return byte-identical structures.
- **Materialized views must be recomputable from the
  event log.** Dropping a view and rebuilding from
  the event log must produce a byte-identical view.
- **Materialized views must never become canonical
  source of truth.** A view that "drifts" from the
  event log (e.g. by accepting a write the event log
  did not record) is a substrate bug.

The current v1.x in-memory `*Book` classes remain
the materialized-view shape during the v1.28
coexistence period; the event log is layered
**under** them. v1.28.x does not require a "big
bang" rewrite of every Book; it requires that every
Book's state can be derived from the event log when
the time comes.

---

## H. Re-projection determinism

The materialized-view contract is enforced by
re-projection determinism tests, designed at v1.28.0
and implemented at v1.28.8:

- **Full run snapshot equals full rematerialization
  snapshot.** A kernel snapshot taken after a full
  run equals the snapshot of a fresh kernel that
  has only re-projected from the run's event log.
- **Two fresh kernels projected from the same event
  log produce byte-identical Book snapshots.** No
  hidden non-determinism (random seed, dict order,
  filesystem order) is allowed to leak into the
  view.
- **Partial period-window load equals full load
  filtered to the same window.** A view loaded only
  for `period_id ∈ [start, end]` is byte-identical
  to a full-history view filtered to the same
  window.
- **Unloading history and reloading it must not
  change digest or snapshots.** Drop the older
  periods from the materialized view, re-project
  them from the event log, and verify the kernel
  snapshot is byte-identical.

These four properties together pin the view as a
**cache**, not a primary store.

---

## I. Append-only physical enforcement

The event log is append-only at the **physical**
level. The following are **binding** for any v1.28.x
event-log writer:

- **Sealed partition files are read-only.** Once a
  partition file is closed and committed, its bytes
  must not change. The writer must surface a sealed
  marker (e.g. an empty `.sealed` companion file or
  a write-protected ACL) and refuse to overwrite.
- **No in-place rewrite of existing part files.**
  Adding events always creates a **new** part file
  (`part-NNNNN.parquet`). The previous file's
  contents and bytes remain unchanged.
- **New events append by creating new part files.**
  The writer maintains a monotonically-increasing
  `NNNNN` index per partition.
- **Partition file list is explicitly sorted before
  hashing.** The leaf digest computation walks files
  in lex-ascending order of filename (§F.2.2).
- **Total event-log artifact size should be
  monotonic within a run** (under append-only
  semantics, the log can only grow).
- **A separately-versioned compaction protocol may
  be introduced later** as a strictly derived
  artifact. Compaction must:
  - produce a new compacted-log artifact in a
    distinct directory tree (e.g. `events_compacted/`);
  - never mutate the canonical `events/` tree;
  - carry its own manifest with a distinct
    `partition_schema_version` so the digest
    surfaces it.

### I.1 Future tests

Append-only enforcement tests, designed here and
implemented at v1.28.2:

- **Sealed file cannot be overwritten.** Attempting
  to open a sealed file for write must raise.
- **Adding an event creates a new part file.** No
  pre-existing part file's `mtime` or `size`
  changes.
- **Existing partition file checksum remains
  unchanged.** A SHA-256 over a sealed part file's
  bytes is identical before and after a subsequent
  append in the same partition.
- **Event-log size grows monotonically under
  append-only writes.** The total `events/` tree
  byte size after N writes is ≥ the size after N−1
  writes.

---

## J. Polars layer

**Future role of Polars** (not added at v1.28.0):

- Scan partitioned Parquet via `pl.scan_parquet` or
  equivalent lazy-scan.
- Validate schema (column names, column types,
  partition-key fields).
- Perform columnar transformations (filter,
  project, group_by) in lazy mode where possible to
  avoid eager hydration.
- Derive summaries (counts, group-by-count, rollups
  for §Q metrics).
- Avoid eager hydration of the full event log into
  Python lists.
- Produce run-level compact tables (e.g.
  per-period × per-record-type counts; partition
  occupancy maps).

**Do not add Polars dependency in v1.28.0.** Polars
enters the project as an **optional** dependency at
v1.28.6 earliest, behind the dependency gate
described in §T. Tests that require Polars must
skip cleanly when the dependency is absent.

---

## K. DuckDB layer

**Future role of DuckDB** (not added at v1.28.0):

- Query Parquet directly via `read_parquet(...)`
  glob patterns.
- Validate counts and joins (e.g. partition
  occupancy = sum of per-part counts;
  parent_event_id citations resolve to existing
  rows).
- Support historical `Book.list_*` equivalents as
  ad-hoc SQL projections.
- Run integrity checks (no orphan citations; no
  duplicate `event_id`; no out-of-range
  `event_index` per partition; no
  `canonical_sort_key` collisions).
- Support ad-hoc local analysis without loading
  all events into Python memory.

**Do not add DuckDB dependency in v1.28.0.** DuckDB
enters the project as an **optional** dependency at
v1.28.7 earliest, behind the dependency gate
described in §T. Tests that require DuckDB must
skip cleanly when the dependency is absent.

---

## L. Hashing and digest design

v1.28 defines **two** digest surfaces clearly. They
coexist; neither is required to equal the other.

### L.1 Legacy digest

- **Existing `living_world_digest`.**
- Must remain byte-identical for every existing
  canonical fixture:
  - `quarterly_default` —
    `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
  - `monthly_reference` —
    `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
  - `scenario_monthly_reference_universe` —
    `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
  - v1.20.4 CLI bundle —
    `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`
- Existing expected values must **not** change at
  any v1.28.x sub-milestone.
- Used for backward compatibility with every
  v1.18 → v1.27 fixture and every v2.0 boundary
  doc.

### L.2 Merkle scale digest

- **New digest surface for event-log partitions.**
- **Leaf digest:** SHA-256 over canonically-
  serialised records in one partition cell, via
  `compute_leaf_digest(...)` (§F).
- **Inner digest:** SHA-256 over **sorted child
  digest tuples** (children sorted by partition
  key / child key — §E.2).
- **Root digest:** SHA-256 over the top-level
  child digest tuples.
- **Changed partition should require partial
  recompute only.** The Merkle structure is the
  property that makes this true; the legacy
  full-recompute digest does not have it.

### L.3 The two digests must coexist

**Important.** Do **NOT** require the Merkle root
to equal the legacy `living_world_digest`. They are
two different digest surfaces over two different
canonical representations of the same semantic state:

- The legacy digest hashes the in-memory snapshot
  shape (Books → snapshots → JSON-serialised
  bundle → SHA-256).
- The Merkle digest hashes the event-log partition
  shape (events → canonically-sorted rows → SHA-
  256-rolled-up Merkle tree).

Instead, v1.28 requires:

1. Legacy digest **remains byte-identical** for
   every existing canonical fixture (§L.1).
2. Merkle digest is **deterministic and stable**
   across reruns of the same fixture.
3. The mapping between legacy fixtures and
   event-log fixtures is tested **separately**
   (see §M).
4. Both digest surfaces must react **consistently**
   to the same semantic fixture change during the
   coexistence period: a change that moves the
   legacy digest must also move the Merkle digest,
   and vice-versa. Drift between the two surfaces
   is a substrate bug to be detected and fixed.

### L.4 xxhash mention

xxhash may be used internally as a non-canonical
fast checksum (e.g. for "did this part file
likely change?" gating before a full SHA-256
recompute). It must not appear in the canonical
digest manifest. SHA-256 remains the canonical
digest boundary unless explicitly changed.

---

## M. Legacy/Merkle drift policy

The two digest surfaces must remain consistent. The
following compatibility tests are designed here and
implemented progressively at v1.28.4 / v1.28.6 /
v1.28.8:

- **`legacy_living_world_digest` remains byte-
  identical for existing fixtures.** Every existing
  v1.21.last canonical digest matches.
- **`merkle_world_digest` is stable across identical
  reruns.** Two reruns of the same fixture produce
  the same Merkle root.
- **A changed partition changes the Merkle root.**
  Mutating one cell propagates upward.
- **A changed record changes its leaf digest and
  every ancestor inner digest up to the root.** No
  silent equality.
- **Unchanged partitions keep the same leaf digest.**
  The partial-recompute property holds.
- **A semantic fixture change causes both legacy
  and Merkle digest surfaces to change.** Drift
  detection: if only one surface moves on a real
  semantic change, the sync boundary is wrong.
- **If legacy digest is unchanged but Merkle
  digest changes, the sync boundary must be
  investigated.** This indicates the event-log
  representation captures a difference the
  in-memory snapshot path filters out — possibly a
  field that should be in the snapshot, or a
  serialisation difference in the manifest.
- **If Merkle digest is unchanged but legacy
  digest changes, the projection boundary must be
  investigated.** This indicates the in-memory
  snapshot captures a difference the event log
  does not — possibly a field that should be in
  the event log, or a transient state that should
  not be in the snapshot.

These eight tests, plus the §H re-projection tests,
form the v1.28 substrate-correctness contract.

---

## N. Partition schema manifest

Each event-log artifact carries a **manifest** with
the following fields:

| Field | Purpose |
| ----- | ------- |
| `partition_schema_version` | semver-style version string for the partition shape |
| `partition_key_fields` | ordered tuple of partition-path field names |
| `event_schema_version` | semver-style version string for the event-row schema |
| `canonical_sort_key_fields` | which row fields define `canonical_sort_key` and in what order |
| `schema_column_order` | ordered tuple of column names; the leaf serializer reads in this order |
| `digest_algorithm` | canonical hash name (`"sha256"` at v1.28) |
| `leaf_serializer` | serializer name + version (e.g. `"json_sorted_keys_v1"`, `"arrow_ipc_v1"`) |
| `merkle_tree_version` | semver-style version string for the inner-digest construction rule |

**Pin** (binding for v1.28.x):

- **Re-hashing requires the manifest.** A digest
  computed without the manifest is undefined.
- **Changing manifest fields is a versioned digest
  change.** Bump the corresponding version field.
- **Partition schema optimization cannot be silent.**
  Any change to `partition_key_fields`,
  `canonical_sort_key_fields`,
  `schema_column_order`, `leaf_serializer`, or
  `merkle_tree_version` must bump the relevant
  version field and surface in the manifest.

---

## O. Schema versioning policy

- **Event log schema must include
  `event_schema_version`.** Every event row carries
  the version under which it was written.
- **Readers must dispatch by schema version.**
  v1.28.x readers must accept `event_schema_version`
  values they understand and refuse (with a clear
  error) values they do not.
- **v1.28 schema is prototype only until frozen.**
  v1.28.0 pins the candidate; the schema is not
  formally frozen until v1.28.last (if v1.28.last
  is shipped).
- **After freeze, schema changes require migration
  or versioned readers.** A reader that sees an
  older `event_schema_version` either migrates the
  rows to the current shape (preferred) or dispatches
  to a version-specific projection function. Silent
  in-place schema rewrites are forbidden.
- **Avro / Protobuf may be evaluated later but are
  not introduced in v1.28.0.** These are external
  schema systems; if introduced they require their
  own design pin and dependency-gate review.
- **No external schema system is added yet.** v1.28.x
  uses Python dataclass + typed columnar headers as
  the canonical schema declaration.

---

## P. Legacy digest deprecation timeline

**Do not delete the legacy digest now.** The legacy
`living_world_digest` is the public-fixture
contract; it cannot be removed until the event-log
projection path and compatibility tests are strong
enough to take over.

**Proposed timeline** (provisional, subject to
review at v1.28.last):

- **v1.28:** coexistence design (this document).
  Legacy digest unchanged. Merkle digest added as a
  new, separate surface.
- **v1.29 or v2.x:** explicit deprecation-warning
  design, if appropriate. Whether legacy is
  deprecated depends on whether the projection path
  is robust enough to take over.
- **v2.x:** event-log digest becomes primary for
  scale paths. The 100x synthetic scale runs
  validate against the Merkle root; the legacy
  digest may continue to apply to small-fixture
  paths.
- **v3.x:** decide whether legacy digest remains for
  small fixtures or is fully retired.

**Pin:**

- Legacy digest **cannot be removed** until event-
  log projection and compatibility tests are
  strong enough.
- **No silent deletion.**
- **No silent expected-value updates.** Any change
  to a published canonical digest value is a
  breaking change and must be a deliberate,
  numbered milestone.

---

## Q. Synthetic scale target

**Engineering target** for v1.28's eventual scale
prototype (v1.28.9 opt-in run):

- 3000 synthetic firms.
- 60 synthetic periods.
- Optional 400 synthetic investors.
- Optional 30 synthetic banks.
- Synthetic sectors (e.g. `industry:x`, `industry:y`,
  …) — never real GICS / TOPIX / NACE.
- Synthetic event types only (the existing v1.18 +
  v1.20 + v1.21 + v1.22 + v1.24 + v1.25 + v1.26 +
  v1.27 RecordType set).

**No real data.** No real Japanese identifier; no
real ticker; no real LEI; no real filing data;
no real index constituent.

### Q.1 Provisional target metrics (non-binding)

The metrics below are **non-binding** until v1.28.9
benchmark implementation. They provide a target
order-of-magnitude for design discussion only:

| Metric | Provisional target | Notes |
| ------ | ------------------ | ----- |
| Full synthetic replay wall-clock | ≤ 10 minutes on a modern laptop | configurable per hardware profile |
| Peak RSS (full replay) | ≤ 8 GB | depends on partition strategy |
| Single-cell partial recompute | ≤ 2 seconds | one cell ≈ 1 partition |
| On-disk event-log size | ≤ 10 GB | depends on payload encoding |

These are **provisional**. The final budgets are
pinned at v1.28.9 against actual measured
performance and surfaced in the §R configurable
profile.

---

## R. Performance budget policy

Performance tests are **not** part of the default
lightweight pytest until stabilised. The test
hierarchy:

### R.1 Normal test suite

- Schema validation.
- Deterministic serialization (round-trip
  byte-identical).
- Digest stability (same fixture → same digest
  across reruns).
- Append-only semantics on tiny fixtures.
- Projection equivalence on tiny fixtures (full
  vs. partial-window load).
- Legacy/Merkle drift detection on tiny fixtures.

The normal suite must remain fast enough to run
on every commit. Targets at v1.28.x milestones
must keep pytest wall-clock in the same order of
magnitude as v1.27.last (~150 s).

### R.2 Opt-in scale / benchmark suite

Marked with one of:

- `@pytest.mark.scale`
- `@pytest.mark.slow`
- `@pytest.mark.benchmark`

Tests in this category may include:

- 3000 × 60 synthetic replay run.
- Peak memory measurement.
- Partial-recompute timing.
- On-disk event-log size check.

**Future target examples** (illustrative; pinned at
v1.28.9):

- Full replay under configured budget.
- Peak memory under configured budget.
- Single-cell partial recompute under configured
  budget.
- Event-log disk size under configured budget.

### R.3 Hardware-profile configurability

Budgets must be **configurable by hardware
profile** and not hard-coded to one machine
without documentation. The provisional shape is a
small TOML / YAML file under
`japan-financial-world/examples/scale_profiles/`
(future, not at v1.28.0) declaring per-profile
budgets:

```toml
[profile.developer_laptop_2026]
full_replay_wall_clock_seconds = 600
peak_rss_bytes = 8_000_000_000
single_cell_recompute_seconds = 2.0
event_log_disk_bytes = 10_000_000_000
```

Tests that enforce budgets read the active profile
from an env var or CLI flag (default: skip if
unset). A profile may declare itself as
informational-only (no failure on miss).

---

## S. Local-first boundary

v1.28 explicitly preserves the **local-first**
boundary that v1.x has held throughout:

- **No Kafka.** No event-streaming broker.
- **No Postgres.** No external relational
  database.
- **No Redis.** No external cache / KV store.
- **No external services.** No HTTP / gRPC server
  required to run the suite or to validate a
  fixture.
- **No cloud dependency.** No S3 / GCS / Azure
  Blob client. No AWS / GCP / Azure SDK.
- **No database server required.** All state lives
  on the local filesystem.

Instead:

- **Parquet files** on the local filesystem.
- **DuckDB embedded query engine** (in-process
  C++ library; no server).
- **Polars in-process DataFrame engine** (in-
  process Rust library wrapped in Python; no
  server).
- **Reproducible filesystem artifacts.** A given
  event-log directory, copied bit-for-bit to a
  different machine, must produce the same
  Merkle root.

The local-first boundary is preserved at every
v1.28.x sub-milestone. Any proposal to introduce a
service-style dependency requires a fresh design
pin amending this section.

---

## T. Dependency policy

- **Polars / DuckDB / PyArrow should first enter as
  optional prototype/dev dependencies.** They are
  declared under `[project.optional-dependencies]`
  (e.g. a `scale` extra), not under runtime
  `dependencies`.
- **Tests must skip gracefully if optional
  dependencies are absent.** Use
  `pytest.importorskip("polars")` /
  `pytest.importorskip("duckdb")` /
  `pytest.importorskip("pyarrow")` at module load.
- **Runtime core must not hard-require them until
  approved.** The v1.x `world.*` and `spaces.*`
  packages must continue to import cleanly with
  only PyYAML in the runtime dependency set.
- **xxhash is optional and non-canonical.** Used
  only for fast inequality checks (§L.4); never in
  the digest manifest.
- **Rust / PyO3 is future-only.** No Rust code in
  v1.28.0; no Rust code in v1.28.x without a
  separate design pin amending this section.
- **No premature optimisation before
  Python / Polars / DuckDB prototype.** The
  v1.28.x sub-milestones run in pure Python
  (v1.28.1–v1.28.4) before any columnar
  dependency is introduced (v1.28.5+).

---

## U. Future implementation sequence

**Strictly serial sub-milestones** (do not start
in v1.28.0):

| Sub-milestone | Surface |
| ------------- | ------- |
| **v1.28.0** | docs-only design pin (this document) |
| v1.28.1 | event-log schema dataclasses + canonical serializer; **no Parquet** |
| v1.28.2 | append-only local event-log writer (JSONL or in-memory prototype) |
| v1.28.3 | partition manifest + partition-schema digest tests |
| v1.28.4 | Merkle digest core on tiny in-memory / JSONL fixtures |
| v1.28.5 | optional Parquet writer / reader behind dependency gate |
| v1.28.6 | Polars scanner + deterministic leaf digest boundary |
| v1.28.7 | DuckDB validation queries |
| v1.28.8 | materialized-view re-projection prototype |
| v1.28.9 | opt-in 3000 × 60 synthetic scale smoke run |
| v1.28.last | docs-only freeze |

**Do not start implementation sub-milestones in
v1.28.0.** Each sub-milestone above requires its
own design pin (or design-pin amendment) before
implementation.

---

## V. Future testing strategy

Tests designed at v1.28.0 and implemented
progressively across v1.28.1–v1.28.9:

### V.1 Schema tests

- Event schema validation (every row has the
  required fields; types match).
- Schema-version manifest field present and
  non-empty.
- Partition schema included in the digest
  manifest.

### V.2 Digest manifest tests

- Partition schema change changes the Merkle
  root.
- Inner digest independent of child insertion
  order.
- Explicit child sort required (a test that
  fakes filesystem-order children must produce
  the same root as a sorted-children construction).
- Canonical serialisation stable across reruns.

### V.3 Append-only tests

- Append-only write behavior (sealed file refused
  for write; new event creates new part file;
  existing part file checksum unchanged).
- Sealed partition immutability.
- No in-place edit of existing partition files.
- Sorted part-file concatenation.

### V.4 Determinism tests

- Leaf digest independent of filesystem order.
- Projection determinism (full snapshot equals
  full rematerialisation snapshot).
- Full rematerialisation snapshot equality.
- Partial-window load equals full load filtered
  to the same window.

### V.5 Drift-detection tests

- Changed record changes affected leaf and root.
- Unchanged partition keeps same leaf digest.
- Legacy digest byte-identical for existing
  fixtures.
- Legacy / Merkle drift detection (semantic
  fixture change moves both surfaces; if only
  one moves, fail).

### V.6 Optional-dependency tests

- Optional-dependency tests skip cleanly when
  Polars / DuckDB / PyArrow is absent.

### V.7 Opt-in scale tests

- Opt-in scale run completes within configured
  budget (the §R hardware-profile selection).

---

## W. Boundary and forbidden content

v1.28 inherits the v2.0.0 hard boundary verbatim
plus the v1.27.0 / v1.26.0 / v1.25.0 / v1.24.0 /
v1.22.0 / v1.21.0a / v1.20.0 / v1.19.0 / v1.18.0
boundaries. **Explicitly forbidden** at every
v1.28.x sub-milestone:

- Real company names (any company; not just
  Japanese).
- Securities codes (ticker / ISIN / CUSIP /
  SEDOL / Japanese 4-digit code / LEI).
- Real filing data (HTML / PDF / XBRL / paid feed
  payload).
- Real cross-shareholding data.
- Real reporting calendar data.
- Real price / volume data.
- EDINET / TDnet / J-Quants / FSA / EDGAR /
  SEDAR / JPX / TOPIX / Nikkei / GICS / MSCI /
  S&P / FactSet / Bloomberg / Refinitiv /
  Capital IQ adapters.
- Investment recommendations.
- Buy / sell / hold labels.
- Target prices.
- Alpha claims.
- Backtest claims.
- Paid data.
- Employer / internship-derived data.
- Expert-interview-derived data.
- Client-specific calibration.

The composed forbidden-token sets shipped at
v1.27.last (`FORBIDDEN_RUN_EXPORT_FIELD_NAMES` /
`FORBIDDEN_STRESS_*_FIELD_NAMES` /
`FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES` /
`FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES` /
`FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES` /
`FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES` /
`FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES`)
apply to every event-log row payload as well.
v1.28.x event-log writers must scan payloads
against the appropriate composed set at
construction time.

---

## X. Success criteria

v1.28 succeeds **only if** every condition below
holds:

1. The existing full test suite remains green
   throughout the v1.28.x sequence.
2. Existing canonical legacy digest values remain
   byte-identical (the four §L.1 hex strings
   never change).
3. The event-log path is **opt-in** (no canonical
   v1.x fixture starts depending on it).
4. The scale prototype uses **synthetic data
   only** (no real Japanese identifier; no
   real-data adapter).
5. The partition schema is pinned in the manifest
   (§N).
6. Inner Merkle ordering is deterministic (§E.2).
7. Event-log projection is byte-stable (§H).
8. Append-only physical semantics are enforced
   (§I).
9. Legacy / Merkle drift can be detected (§M).
10. Performance budgets are defined and later
    tested in the opt-in scale suite (§R).
11. The 3000 × 60 synthetic run eventually
    completes under the configured budget (§Q,
    §R).
12. The local-first boundary is preserved (§S).
13. No real-data / Japan-calibration leak occurs
    at any sub-milestone.

If any condition above fails at any v1.28.x
sub-milestone, that sub-milestone is rolled back
or its design pin is amended before proceeding.

---

## v1.28.0 closing statement

v1.28.0 is a docs-only design pin. It introduces
no runtime module, no new dataclass, no new
ledger event, no new test, no new label
vocabulary, no new fixture, no Polars / DuckDB /
PyArrow / xxhash / Rust / PyO3 dependency, no
Parquet file, no event-log writer, no benchmark
test, and no change to the current Ledger / Book
behavior or to the current canonical
`living_world_digest` implementation. v1.28.0
changes no canonical `living_world_digest`
value.

v1.28.0 only **defines the architecture** for the
future scale substrate: an immutable on-disk
event log, lazy materialized views over event-log
slices, and a Merkle-style digest tree that
permits partial recompute. The architecture
coexists with the legacy digest; it does not
replace it. v1.28.x sub-milestones implement
strictly to this design, in serial order, each
behind its own design pin.

The next milestone (provisional) is **v1.28.1
event-log schema dataclasses + canonical
serializer**. v1.28.0 does not start it; v1.28.1
requires its own design pin or design-pin
amendment before implementation.
