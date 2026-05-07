# v1.29 TraceEdgeRecord + CitationGraphProjection — Design Note

*v1.29 defines the **trace-graph layer** that sits
above the v1.28 event-log substrate. It clarifies the
boundary between raw log rows, event-ledger records,
inter-event trace edges, citation-graph projections,
and the audit-facing query surface. v1.29.0 ships
**only** the design pin; no runtime module, no test,
no dependency, no kernel mutation, no Parquet, no
graph database, no PROV-O / RDF / SPARQL / Cypher /
Neo4j / networkx, no counterfactual replay.*

This document is **docs-only at v1.29.0**. Every
existing v1.21.last canonical `living_world_digest`
value remains byte-identical. v1.28 runtime modules
(`world.event_log_*`) are untouched. v1.29.1 / v1.29.2
/ v1.29.3 / v1.29.4 / v1.29.5 / v1.29.last (if any)
implement strictly to this design or the design must
be re-pinned.

---

## A. Purpose

v1.29 defines the citation / trace graph surface above
the event-log substrate. It clarifies the difference
between five distinct artifacts that have been
loosely conflated in earlier prose:

1. **Raw log rows.** Free-form chronological textual
   records ("what happened when"). Not stored in any
   v1.x runtime; the term is a domain reference only.
2. **Event ledger records.** Append-only, typed,
   schema-pinned, digestable rows — i.e. the v1.28.1
   `EventLogRecord` shipped under
   `world.event_log_schema`.
3. **Trace edges.** Future
   `TraceEdgeRecord` instances — directed
   relationships between event-log records (e.g. "this
   later judgment cited that earlier evidence").
   Designed at v1.29.0; implemented v1.29.1+.
4. **Citation graph projection.** Deterministic
   read-only projection over event-log records + trace
   edges. Designed at v1.29.0; implemented v1.29.3+.
5. **Audit-facing query surface.** Future deterministic
   read-only queries answering specific audit
   questions ("which evidence contributed to this
   judgment?"). Designed at v1.29.0; implemented
   v1.29.4+.

The v1.29 sequence designs these five artifacts as a
strict hierarchy: every later artifact is a derived
projection over earlier artifacts. None of (3)–(5) is
a canonical source of truth.

---

## B. Why v1.29 comes after v1.28

v1.28 established the deterministic substrate that
v1.29 depends on:

- **Deterministic event rows.** v1.28.1
  `EventLogRecord` with the canonical 18-field
  schema, the `compute_leaf_digest(...)` boundary,
  and the canonical-JSON serializer.
- **Append-only on-disk storage.** v1.28.2 JSONL
  writer with sealed-marker, monotonic part-file
  index, and atomic exclusive-open append.
- **Manifest pinning.** v1.28.3 `_MANIFEST.json`
  sidecar + `ManifestMismatchError` enforce schema
  versioning across the event-log root.
- **Merkle digest core.** v1.28.4 partition / inner /
  root digest construction with single-leaf-hash-
  implementation pin and sorted-children invariant.
- **Read-only projection prototype.** v1.28.8
  `EventLogProjectionSummary` with partial-window
  determinism + no-mutation guarantee.

v1.29 must **not** replace any of the above. The
event log remains the canonical store; trace edges
are a new record type that **also** lives in the
event log; the citation graph is a new projection
**alongside** `EventLogProjectionSummary`. v1.29
adds graph semantics as a **layer** over v1.28
records, not as a parallel substrate.

---

## C. Boundary

v1.29.0 is **NOT**:

- A PROV-O / W3C-PROV implementation.
- An RDF implementation.
- A graph database integration (no Neo4j,
  TigerGraph, JanusGraph, ArangoDB, Memgraph,
  AnzoGraph, etc.).
- A SPARQL / Cypher / Gremlin query engine.
- A counterfactual replay engine.
- An investment recommendation layer.
- A price-impact model.
- A real-data adapter (no EDINET / TDnet /
  J-Quants / FSA / EDGAR / SEDAR / JPX / TOPIX /
  Nikkei / GICS / MSCI / S&P / FactSet / Bloomberg
  / Refinitiv / Capital IQ).
- A Japan calibration step.

v1.29.0 ships docs only. Every later v1.29.x
sub-milestone (if approved) inherits this boundary
verbatim.

---

## D. Log vs ledger vs trace graph

The three terms are **distinct** and must not be
collapsed:

### D.1 Log

- Chronological record stream.
- Answers: **"what happened when?"**
- In v1.x, "log" is a domain term, not a runtime
  artifact. The closest concrete object is the v1.x
  `Ledger` of `RecordType` events.

### D.2 Ledger

- Append-only, typed, schema-pinned, digestable
  event record substrate.
- Answers: **"what was recorded, by which schema,
  under which manifest, with what digest?"**
- Concrete v1.x objects:
  - The historical `world.ledger.Ledger` (per-
    `RecordType` event stream, since v0.x).
  - The v1.28.1 `EventLogRecord` + v1.28.2 JSONL
    storage + v1.28.3 manifest sidecar + v1.28.4
    Merkle digest core.

### D.3 Trace graph

- Directed relationship projection over recorded
  events, derived from a future
  `TraceEdgeRecord` book.
- Answers: **"which evidence, review, constraint,
  and prior event contributed to this later
  judgment?"**
- v1.29 defines this layer's record shape (§F),
  projection shape (§H), and audit query surface
  (§I).

A trace edge **describes** a relationship between
two event-log records; it does **not** create a new
event fact independently. Removing every trace edge
must leave the underlying event-log substrate
unchanged.

---

## E. Canonical source of truth

Pin (binding for the v1.29 sequence):

- **`EventLogRecord` (v1.28.1) remains canonical
  for event facts.** No v1.29 record may shadow,
  override, or modify an event-log row.
- **`TraceEdgeRecord` (v1.29.1+, when implemented)
  is canonical for inter-event relationships.** It
  has its own append-only book and its own JSONL
  partition shape (see §F).
- **`CitationGraphProjection` is derived, read-
  only, and recomputable.** Dropping the projection
  and rebuilding from the event log + trace edges
  must produce a byte-identical projection.
- **No graph object is canonical by itself.** A
  computed adjacency list, traversal result, or
  audit-query output is a transient projection
  artifact. It must not be persisted as the source
  of truth for any later derivation.
- **No graph database is required.** The local-
  first boundary established at v1.28 is preserved.
  No Neo4j / TigerGraph / etc. dependency is
  introduced at any v1.29.x sub-milestone.

---

## F. Future `TraceEdgeRecord` shape

**Design only. Do not implement at v1.29.0.**

### F.1 Candidate fields

| Field | Type (notional) | Purpose |
| ----- | --------------- | ------- |
| `edge_id` | string | stable plain-id |
| `run_id` | string | run scope (matches v1.28.1 `EventLogRecord.run_id`) |
| `source_event_id` | string | the earlier event's plain-id |
| `target_event_id` | string | the later event's plain-id |
| `edge_type_label` | string | closed-set; see §F.2 |
| `edge_category_label` | string | closed-set; see §F.3 |
| `evidence_ref_ids` | tuple[string, …] | plain-id citation tuple to evidence records (may be empty) |
| `citation_ids` | tuple[string, …] | plain-id citation tuple to upstream sources (may be empty; §G policy) |
| `actor_id` | string \| null | optional pseudonymous actor reference |
| `period_id` | string | logical period (matches v1.28.1 convention) |
| `provenance_kind` | string | closed-set: `synthetic` / `annotated` / `projected` / `unknown` |
| `confidence_label` | string | closed-set: `not_assessed` / `low` / `medium` / `high` / `unknown` (see §F.4) |
| `notes` | string \| null | optional descriptive note (forbidden-token-scanned per §G) |
| `canonical_sort_key` | string | derived sort key; see §K |

The `canonical_sort_key` default candidate is

```
edge_partition_key/edge_index=NNN/edge_id=…
```

with a 12-digit zero-padded `edge_index` mirroring
the v1.28.1 `EventLogRecord.canonical_sort_key`
convention.

### F.2 Closed-set `edge_type_label`

```python
TRACE_EDGE_TYPE_LABELS: frozenset[str] = frozenset({
    "attended_to",
    "cited_as_evidence",
    "constrained_by",
    "reviewed_under",
    "propagated_to",
    "contradicted_by",
    "superseded_by",
    "derived_from",
    "related_to",
    "unknown",
})
```

These are **procedural / structural relation
labels**, not sentiment labels. Adding a new label
requires a fresh design pin per the v1.x closed-set
convention.

### F.3 Closed-set `edge_category_label`

```python
TRACE_EDGE_CATEGORY_LABELS: frozenset[str] = frozenset({
    "evidence",
    "attention",
    "review",
    "constraint",
    "propagation",
    "contradiction",
    "lineage",
    "annotation",
    "unknown",
})
```

The category complements the type: e.g. an
`attended_to` edge maps to the `attention`
category; a `constrained_by` edge maps to
`constraint`. The mapping is fixed at v1.29.1+ by
a closed-set lookup.

### F.4 Forbidden-label boundary (binding)

`TraceEdgeRecord` **must not** carry any sentiment
or investment label, in any field, label, value,
metadata key, payload key, or text fragment:

- `bullish` / `bearish`
- `optimistic` / `pessimistic`
- `buy` / `sell` / `hold`
- `target_price` / `target_return`
- `alpha` / `expected_alpha`
- `recommendation` / `advice`

`TraceEdgeRecord` also inherits the v1.x composed
forbidden-name sets shipped at v1.27.last + v2.0.0
+ v1.28.0 (real Japanese identifier, real-data
adapter, ownership / voting / market-value /
centrality / systemic-importance, real-person
identity / compliance claim, etc.).

`confidence_label` is a closed-set epistemic
descriptor (`not_assessed` / `low` / `medium` /
`high` / `unknown`), **not** a numeric probability
or a forecast — and `not_assessed` is the default
for any record where the reviewer has not made a
deliberate confidence judgment. v1.29 does **not**
introduce probabilities or numeric forecasts.

---

## G. Plain-ID citation policy

`citation_ids` are **stable plain-id strings**, not
raw private notes. v1.29 binds the following rules
across every v1.29.x sub-milestone:

- **Stable.** A citation id may not change across
  record revisions. If the upstream source revises
  its id, append a new edge citing the new id; the
  old edge stays.
- **Plain-id only.** No raw email, no full personal
  name, no phone number, no national-id, no
  employee-id, no private comment, no confidential
  paraphrase. The v1.27.3 anti-email-leak guard is
  re-pinned: any field that would otherwise carry an
  identity reference must use a pseudonymous
  placeholder.
- **No real-data source payloads in public
  fixtures.** Public fixtures may cite synthetic
  ids (e.g. `pub:synthetic_001`,
  `manual_annotation:synthetic_x`); they may not
  cite real filing ids, real exchange notices, real
  consensus-feed payloads, or real index-
  constituent lists.
- **License-reviewed real bridges live in v2/v3.**
  A citation id pointing to a real Japanese filing
  belongs to a future v2.x sub-milestone (under the
  v2.0 boundary) or to the proprietary v3.x track.
  v1.29 does not introduce real bridges.
- **Notes scanner re-pinned.** Any optional `notes`
  field must be scanned for the v1.x composed
  forbidden-token vocabularies at construction
  (mirroring the v1.24.1 `ManualAnnotationRecord`
  whitespace-normalising scan).

---

## H. CitationGraphProjection

**Design only. Do not implement at v1.29.0.**

A `CitationGraphProjection` is:

- **Deterministic.** Same event log + same
  trace edges → byte-identical projection.
- **Read-only.** Computing a projection mutates no
  v1.x runtime state (no kernel field, no event-log
  file, no `_MANIFEST.json` sidecar, no v1.28.4
  Merkle digest).
- **Recomputable.** Dropping the projection and
  rebuilding from the same event log + trace edges
  produces the same projection.
- **A projection over `EventLogRecord` +
  `TraceEdgeRecord`.** It composes existing
  primitives; it never declares a new canonical
  store.
- **Independent of filesystem ordering.** Walking
  via `world.event_log_merkle.discover_partitions`
  + `world.event_log_writer._list_part_files_sorted`
  ensures lex-ascending order regardless of OS-level
  enumeration.
- **Sorted by canonical keys.** Nodes sorted by
  `event_id`; edges sorted by
  `canonical_sort_key`. No dict iteration order, no
  random traversal order, no wall-clock ordering
  bleeds through.
- **Compact.** The projection summarises (counts,
  sorted-pair tuples) rather than materialising
  every adjacency in memory.

### H.1 Possible future outputs

A future `CitationGraphProjectionSummary` (frozen
dataclass) may carry:

- `nodes_by_type` — `(record_type, count)` tuples
  sorted by `record_type`.
- `edges_by_type` — `(edge_type_label, count)`
  tuples sorted by `edge_type_label`.
- `lineage_paths` — sorted tuples of
  `(target_event_id, sorted-tuple-of-source-event_ids)`
  expressing single-hop or multi-hop ancestor sets.
- `evidence_dependency_counts` —
  `(target_event_id, evidence_count)` tuples
  sorted by `target_event_id`.
- `actor_attention_paths` —
  `(actor_id, sorted-tuple-of-attended-event_ids)`
  for any edge with
  `edge_type_label == "attended_to"`.
- `review_category_paths` —
  `(actor_id, sorted-tuple-of-(review_category,
  reviewed_event_ids))` for any edge with
  `edge_category_label == "review"`.
- `contradiction_pairs` — sorted tuples of
  `(earlier_event_id, later_event_id)` for any edge
  with `edge_type_label == "contradicted_by"`.
- `propagation_chains` — sorted tuples expressing
  forward propagation from a source event to its
  reachable descendants under
  `edge_type_label == "propagated_to"`.

Cardinality of each output is bounded by the
number of trace edges in the input. Empty inputs
yield empty outputs.

### H.2 Out of scope at v1.29.0

- Centrality / PageRank / betweenness scoring.
- Community detection / clustering.
- Embedding / vector representation.
- Probabilistic edge weights.
- Time-decay weighting.
- Predictive / forecast extensions.

These are not "deferred"; they are **forbidden**
extensions until a future design pin explicitly
admits them.

---

## I. Audit query surface

**Design only. Do not implement at v1.29.0.**

A future `world.event_log_audit_query` module
(v1.29.4+) may expose deterministic read-only
helpers answering specific audit questions:

| Audit question | Helper sketch |
| -------------- | ------------- |
| Which evidence contributed to this judgment? | `evidence_for(event_id) -> tuple[EventLogRecord, ...]` |
| Which actor attended to this event first? | `first_attender_of(event_id) -> str \| None` |
| Which judgments cite the same evidence? | `co_citers_of(evidence_id) -> tuple[EventLogRecord, ...]` |
| Which judgments depend on a withdrawn or superseded input? | `judgments_depending_on(superseded_event_id) -> tuple[EventLogRecord, ...]` |
| Which actors diverged in review category despite seeing the same evidence? | `divergent_reviewers(evidence_id) -> tuple[tuple[str, str], ...]` |
| Through which path did attention propagate? | `attention_path(start_event_id, end_event_id) -> tuple[str, ...]` |

Every helper:

- is a **read-only function** over event log +
  trace edges;
- returns a deterministic result independent of
  filesystem / dict / random order;
- mutates no source-of-truth book;
- raises a clear, named error if the input id is
  unknown (no silent empty result).

### I.1 Counterfactual questions are out of scope

Questions of the form "what would have happened if
this evidence had been withdrawn before this
judgment?" require a **future deterministic replay
engine**. v1.29 designs neither the replay engine
nor any helper that answers a counterfactual
question. Such helpers, if undertaken, require
their own milestone (likely v1.30+).

The audit query surface answers questions about
**what is in the event log**, never about
**what could have been**.

---

## J. Relationship to answer surface

The v1.28 `docs/answer_surface.md` framing is

> evidence → attention → review → citation graph →
> ledger.

v1.29 defines the **citation graph** portion. After
v1.29 ships:

- The "evidence" stage continues to be carried by
  v1.18 + v1.20 + v1.21 records and v1.24 manual
  annotations + v1.27.3 provenance.
- The "attention" stage continues to be carried by
  the v1.12.last endogenous attention loop +
  v1.16.last closed-loop freeze.
- The "review" stage continues to be carried by
  v1.25 mandate / archetype records.
- **The "citation graph" stage** is the new v1.29
  surface — `TraceEdgeRecord` + `CitationGraphProjection`.
- The "ledger" stage continues to be carried by
  the v1.x `world.ledger.Ledger` and the v1.28
  on-disk event log.

What v1.29 does **not** change:

- JFWE still does not return price predictions.
- JFWE still does not provide investment advice.
- JFWE still models pinned actor archetypes with
  deterministic processing rules; the citation
  graph adds **structure**, not **prediction**.
- The `_like` archetype suffix discipline (v1.25
  mandate vocabularies, v1.27 relationship
  vocabularies) is preserved; trace edges describe
  relationships **between records**, not between
  real-world institutions.

---

## K. Determinism and ordering

Pin (binding for v1.29.x):

- **Trace edges must have `canonical_sort_key`.**
  The schema mirrors the v1.28.1 `EventLogRecord`
  convention (sorted lex-ascending; 12-digit
  zero-padded numeric component).
- **Projection must sort nodes and edges
  explicitly.** Nodes by `event_id`; edges by
  `canonical_sort_key`. No reliance on insertion
  order.
- **Graph traversal output must be deterministic.**
  Lineage paths, ancestor sets, and propagation
  chains return tuples in canonical order; multi-
  path results are sorted by the lexicographic
  representation of the path.
- **No dict iteration order.** Where Python dicts
  are used internally, every materialised output
  passes through an explicit `sorted(...)`.
- **No filesystem order.** Walking the event log
  reuses `world.event_log_merkle.discover_partitions`
  + `_list_part_files_sorted` (both already lex-
  sorted at v1.28).
- **No random traversal order.** No `random.shuffle`,
  no `set` iteration as the canonical output, no
  hash-based bucketing of records before output.
- **No timestamp-based ordering unless logical and
  deterministic.** `created_at_logical` is a
  logical-period string at v1.28.1; trace edges
  inherit the same convention. Wall-clock
  timestamps may not appear in any canonical
  ordering.

---

## L. Digest policy

- `TraceEdgeRecord` may later be included in the
  v1.28.4 Merkle event-log digest **or** in a
  separate v1.29.5 trace digest. The choice is
  deferred.
- **v1.29.0 does not change any digest
  implementation.** The four canonical
  `living_world_digest` values shipped at v1.21.last
  remain byte-identical:
  - `quarterly_default` —
    `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
  - `monthly_reference` —
    `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
  - `scenario_monthly_reference_universe` —
    `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
  - v1.20.4 CLI bundle —
    `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`
- **Existing v1.28 Merkle surfaces remain
  unchanged.** No `TraceEdgeRecord` is ever written
  through `compute_partition_leaf_digest` or
  `compute_event_log_root_digest` at v1.29.0.
- Any future v1.29.x trace digest must:
  - include the trace-edge schema manifest in its
    leaf material (mirroring v1.28.4's
    manifest-included-in-leaf rule);
  - sort children by canonical key explicitly;
  - route through a single approved leaf-digest
    function (mirroring v1.28.4 §F.1 single-
    leaf-implementation pin).

---

## M. Testing plan for v1.29.1+

Designed at v1.29.0; implemented progressively
across v1.29.1–v1.29.5.

### M.1 Schema tests (v1.29.1)

- `TraceEdgeRecord` validates closed-set
  `edge_type_label` (the v1.29.0 §F.2 set).
- `TraceEdgeRecord` validates closed-set
  `edge_category_label` (the v1.29.0 §F.3 set).
- Rejects sentiment / investment labels (`bullish`
  / `bearish` / `buy` / `sell` / `hold` /
  `target_price` / `alpha` / `recommendation` /
  `advice`).
- Rejects raw private citation payloads (any token
  in the v1.27.3 + v2.0.0 forbidden-name sets).
- Required-string fields non-empty.
- `canonical_sort_key` derived deterministically.

### M.2 Serialization tests (v1.29.1)

- Same record serialises to identical bytes across
  repeated calls.
- Tuple fields (`evidence_ref_ids`,
  `citation_ids`) serialise as JSON arrays.
- Construction order does not change canonical
  bytes.
- Module text contains no `import polars` /
  `import duckdb` / `import pyarrow` / `import
  networkx` / `import rdflib` / `import neo4j` /
  `import sparql`.

### M.3 Storage tests (v1.29.2)

- Append-only `TraceEdgeBook` with monotonic
  per-partition part-file index.
- Sealed partition refuses appends.
- Existing part-file checksum unchanged after
  subsequent append.
- No mutation of the v1.28.x event-log files (no
  rewrite of any pre-existing JSONL or
  `_MANIFEST.json` byte).
- No `WorldKernel` field added (kernel-empty-by-
  default).

### M.4 Projection tests (v1.29.3)

- Edge insertion order does not change the
  projection.
- Same event log + same edges yields the same
  `CitationGraphProjection`.
- Graph projection is recomputable (drop +
  rebuild = byte-identical).
- Graph projection does not mutate the event log
  (per-file SHA-256 unchanged before / after).
- Filesystem listing order does not change the
  projection.
- Empty event log + empty trace edges → empty
  projection (deterministic).

### M.5 Audit query tests (v1.29.4)

- Lineage query deterministic.
- Dependency query deterministic.
- Contradiction-pair extraction deterministic.
- Unknown-id input raises a clear named error
  (no silent empty result).
- Audit helpers do not mutate any source-of-truth
  book (per-file SHA-256 unchanged before /
  after).
- No `import sparql` / `import cypher` / `import
  rdflib` / `import neo4j` / `import networkx`.

### M.6 Optional-dependency tests (v1.29.x)

- Default suite passes without PROV-O / SPARQL /
  Cypher / Neo4j / networkx.
- No graph database driver required by default.
- No real identifiers in any test fixture.

---

## N. Future sub-milestone plan

| Sub-milestone | Surface |
| ------------- | ------- |
| **v1.29.0** | docs-only design pin (this document) |
| v1.29.1 | `TraceEdgeRecord` schema + canonical serializer |
| v1.29.2 | `TraceEdgeBook` / append-only trace-edge storage (in-memory or JSONL) |
| v1.29.3 | `CitationGraphProjection` on tiny synthetic fixtures |
| v1.29.4 | audit query helpers (deterministic, read-only) |
| v1.29.5 | trace digest / graph projection digest, **if needed** (decision deferred to v1.29.4 review) |
| v1.29.last | docs-only freeze |

**Do not start v1.29.1+ in v1.29.0.** Each later
sub-milestone requires its own design pin (or
design-pin amendment) before implementation.

---

## O. Boundary and forbidden content

v1.29 inherits the v2.0.0 + v1.28.0 + v1.27.0 +
v1.26.0 + v1.25.0 + v1.24.0 hard boundaries
verbatim. **Explicitly forbidden** at every v1.29.x
sub-milestone:

- Real company names (any company; not just
  Japanese).
- Securities codes (ticker / ISIN / CUSIP / SEDOL
  / Japanese 4-digit code / LEI).
- Real filing data.
- Real cross-shareholding data.
- Real price / volume data.
- Real reporting calendar data.
- EDINET / TDnet / J-Quants / FSA / EDGAR /
  SEDAR / JPX / TOPIX / Nikkei / GICS / MSCI /
  S&P / FactSet / Bloomberg / Refinitiv /
  Capital IQ adapters.
- Paid data.
- Expert-interview content.
- Employer / internship-derived content.
- Client-specific calibration.
- Investment recommendations.
- `buy` / `sell` / `hold`.
- Target prices.
- Alpha claims.
- Backtest claims.
- Legal-compliance claims.

The v1.x composed forbidden-token sets shipped at
v1.27.last apply to every `TraceEdgeRecord`
payload at construction time (mirroring the
v1.24.1 / v1.25.1 / v1.26.1 / v1.27.1 / v1.27.3
storage discipline).

---

## P. Success criteria

v1.29 succeeds **only if** every condition below
holds:

1. The trace graph remains a **projection**, not a
   canonical source of truth.
2. The event log remains the canonical substrate.
3. No existing fixtures change.
4. The legacy `living_world_digest` remains byte-
   identical for every existing canonical fixture.
5. No real data, real-data adapter, or Japan
   calibration enters the repository at any
   v1.29.x sub-milestone.
6. No investment-output surface appears.
7. The audit query surface (when implemented) is
   deterministic and read-only.
8. Counterfactual replay remains deferred (out of
   scope for the v1.29 sequence).
9. Optional graph dependencies (Neo4j / networkx /
   rdflib / sparql / cypher) are not required by
   default and are not added to runtime
   dependencies.
10. The local-first boundary established at v1.28
    is preserved.

If any condition above fails at any v1.29.x sub-
milestone, that sub-milestone is rolled back or
its design pin is amended before proceeding.

---

## v1.29.1 implementation note

*v1.29.1 ships the canonical `TraceEdgeRecord` row
shape + canonical-JSON serializer + SHA-256 leaf
digest function boundary. No storage, no projection,
no audit query. No graph database, no PROV-O / RDF /
SPARQL / Cypher / Neo4j / networkx / rdflib
dependency. No `prev_hash` / `self_hash` field —
tamper evidence is delegated to the v1.28 event-log
/ manifest / Merkle substrate.*

### v1.29.1.1 Surface

In [`world/trace_edges.py`](../world/trace_edges.py):

- Closed-set vocabularies (binding):
  `TRACE_EDGE_TYPE_LABELS` (10),
  `TRACE_EDGE_CATEGORY_LABELS` (9),
  `TRACE_EDGE_CONFIDENCE_LABELS` (5).
- `TRACE_EDGE_PROV_COMPAT_MAPPING` — descriptive-only
  string mapping from each `edge_type_label` to a
  `prov:…Like` / `jfwe:…` name. Strings only; no
  rdflib / OWL / SPARQL.
- `CANONICAL_TRACE_EDGE_COLUMN_ORDER` — 14-field
  canonical column order.
- `TRACE_EDGE_SCHEMA_VERSION` — schema-version
  sentinel; bumping it changes every leaf digest.
- `TraceEdgeRecord` (frozen dataclass; required non-
  empty `edge_id` / `run_id` / `source_event_id` /
  `target_event_id` / `provenance_kind`; closed-set
  `edge_type_label` / `edge_category_label` /
  `confidence_label`; tuple-of-non-empty-string
  `evidence_ref_ids` / `citation_ids` (default `()`);
  optional empty-by-default `actor_id` / `period_id`
  / `notes`; deterministic `canonical_sort_key`
  derivation:
  `run_id=…/source=…/target=…/type=…/edge_id=…`).
- `trace_edge_to_canonical_dict(record)` — projects
  to a canonical mapping in `CANONICAL_TRACE_EDGE_COLUMN_ORDER`.
- `serialize_trace_edges_canonical_json(records)` —
  canonical JSON bytes (routes through v1.28.1's
  `serialize_canonical_json`).
- `compute_trace_edge_leaf_digest(records, *,
  schema_version=TRACE_EDGE_SCHEMA_VERSION)` —
  single trace-edge leaf-digest boundary. Sorts
  records by `canonical_sort_key`, builds
  `{"schema_version": …, "trace_edges": [...]}`,
  serialises canonically, hashes with SHA-256,
  returns lowercase hex.

### v1.29.1.2 What v1.29.1 does NOT ship

- No graph database / PROV-O / RDF / SPARQL / Cypher /
  Neo4j / networkx / rdflib runtime.
- No `prev_hash` / `self_hash` / `edge_chain_hash`
  field on `TraceEdgeRecord`.
- No `WorldKernel` field (kernel-empty-by-default).
- No real Japanese identifier, no real-data adapter,
  no Japan calibration, no investment output, no
  sentiment label.

### v1.29.1.3 Tests added

`tests/test_trace_edges.py` adds **+56 tests** (after
parametrisation expansion). Coverage: closed-set
vocabularies match design pin; parametrised forbidden-
sentiment-label exclusion across 13 forbidden tokens;
valid-minimal record acceptance; canonical_sort_key
default; parametrised empty-required-string rejection
across 5 fields; invalid edge_type / category /
confidence label rejection; full-cross-product label
acceptance (10 × 9 × 5); non-tuple evidence_ref_ids /
citation_ids rejection; empty-string entry rejection;
optional empty actor_id / period_id / notes; explicit
canonical_sort_key bypass; frozen-immutability;
canonical-dict explicit column order; tuples-as-lists;
byte-identical repeated calls; serialize uses
explicit field order; non-record TypeError; leaf
digest lowercase-hex-64 / stable / insertion-order
independent / reacts to edge change / reacts to
evidence_ref / citation_ids change / reacts to
schema_version change / empty-list deterministic /
non-record TypeError / empty-schema-version rejection
/ explicit-recompute SHA-256 equality match; PROV-O
mapping covers every edge_type_label / values are
strings / uses descriptive `prov:…Like` or `jfwe:…`
namespaces; module text contains no rdflib / OWL /
SPARQL / Neo4j / TigerGraph / Gremlin / networkx /
Polars / DuckDB / PyArrow imports; no real-data
adapter imports; no `prev_hash` / `self_hash` /
`edge_chain_hash` dataclass field; no WorldKernel
field added; module exports match design pin.

### v1.29.1.4 Validation

- `pytest -q`: **5383 passed, 2 skipped, 1 deselected
  / 5386 collected** (5327 → 5383; +56 tests).
- `ruff check japan-financial-world`: clean.
- `python -m compileall -q
  japan-financial-world/world japan-financial-world/spaces
  japan-financial-world/tests japan-financial-world/examples`:
  clean.
- All v1.21.last canonical living-world digests
  preserved byte-identical.
- No new dependency; no `pyproject.toml` change.

---

## v1.29.2 implementation note

*v1.29.2 ships the append-only local trace-edge JSONL
writer + manifest sidecar + `compute_partition_trace_edge_leaf_digest`
hook. Mirrors the v1.28.2 + v1.28.3 event-log writer
discipline. No graph database, no PROV-O, no `prev_hash` /
`self_hash` chain. Tamper evidence routes through the
v1.29.1 leaf-digest boundary.*

### v1.29.2.1 Surface

In [`world/trace_edge_store.py`](../world/trace_edge_store.py):

- `TraceEdgePartitionKey` (`run_id`,
  `period_id_or_unknown`, `edge_category_label`;
  empty `period_id` becomes
  `PERIOD_ID_UNKNOWN_PATH_VALUE = "unknown"` in the
  partition path; closed-set
  `edge_category_label` validation;
  `to_path_segments()` produces
  `("run_id=…", "period_id=…", "edge_category=…")`;
  `from_record(TraceEdgeRecord)` classmethod).
- `TraceEdgeManifest` (frozen dataclass; pins
  `manifest_version`, `trace_edge_schema_version`,
  `partition_key_fields`,
  `canonical_sort_key_fields`, `schema_column_order`,
  `digest_algorithm` (must be `"sha256"`),
  `leaf_serializer` (default `"canonical-json-v1"`);
  `partition_key_fields` must include
  `{run_id, period_id, edge_category_label}`;
  `schema_column_order` must equal the
  v1.29.1 canonical 14-field set).
- `default_trace_edge_manifest()` — convenience
  builder pinned at the v1.29.1 schema version.
- `TraceEdgePartitionWriter` (per-partition append-
  only JSONL writer with monotonic 6-digit zero-
  padded part-file index, sealed-marker, exclusive-
  open append, eager manifest sidecar verification at
  construction, ensure-or-write sidecar on first
  append). Mirrors v1.28.2 conventions.
- `TraceEdgeWriteResult` frozen dataclass.
- Sidecar helpers
  `write_trace_edges_manifest_sidecar`,
  `read_trace_edges_manifest_sidecar`,
  `ensure_trace_edges_manifest_sidecar`.
- `read_trace_edge_part_file(part_path)` — JSONL
  reader returning a tuple of plain dicts (used by
  v1.29.3 / v1.29.5).
- `compute_partition_trace_edge_leaf_digest(root,
  partition_key, manifest=None)` — walks part files
  in lex-ascending order, parses canonical JSONL,
  reconstructs `TraceEdgeRecord` instances, and
  routes through
  `world.trace_edges.compute_trace_edge_leaf_digest`
  (the v1.29.1 single boundary). **Single trace-edge
  leaf-hash implementation in the project.**
- Exception hierarchy: `TraceEdgeWriteError` (base),
  `TraceEdgeSealedPartitionError`,
  `TraceEdgeAlreadySealedError`,
  `TraceEdgeValidationError`,
  `TraceEdgeManifestMismatchError`.

Path layout (binding):

    <root>/
      run_id=<run_id>/
        period_id=<period_id_or_unknown>/
          edge_category=<edge_category_label>/
            part-000001.jsonl
            ...
            _SEALED   (optional)
      _TRACE_EDGES_MANIFEST.json   (per-root sidecar)

### v1.29.2.2 What v1.29.2 does NOT ship

- No graph database / Neo4j / TigerGraph.
- No PROV-O / RDF / SPARQL / Cypher / rdflib /
  networkx.
- No Polars / DuckDB / PyArrow / xxhash / Rust /
  PyO3.
- No `prev_hash` / `self_hash` / `edge_chain_hash`
  field on `TraceEdgeRecord`.
- No `WorldKernel` field. No mutation of any v1.28
  event-log file.
- No projection (v1.29.3) and no audit query
  (v1.29.4).

### v1.29.2.3 Tests added

`tests/test_trace_edge_store.py` adds **+37 tests**.
Coverage: partition-key validation; path segments;
`from_record` with non-empty period_id; `from_record`
with empty period_id resolves to
`PERIOD_ID_UNKNOWN_PATH_VALUE`; default manifest
valid; manifest rejects non-sha256 / missing partition
dimension / invalid schema_column_order; sidecar
round-trip + canonical-bytes-stable; ensure-helper
idempotent on equal / raises on mismatch; first append
creates `part-000001.jsonl`; second append creates
`part-000002.jsonl`; existing-part-file SHA-256 + size
unchanged after subsequent append; lex-sorted listing;
JSONL round-trip via `read_trace_edge_part_file`;
in-file canonical_sort_key sort; sealing creates
marker, refuses appends, refuses re-seal; empty-record-
list / non-record-item / wrong-partition-key rejection;
invalid constructor argument rejection; eager manifest-
mismatch at construction; partition-digest matches
in-memory `compute_trace_edge_leaf_digest`; partition-
digest reacts to record change; partition-digest
independent of part-file split; forbidden-scope
(no Polars / DuckDB / PyArrow / xxhash / rdflib /
sparql / Neo4j / networkx / Gremlin imports; no real-
data adapter imports); no `WorldKernel` field; no
`prev_hash` / `self_hash` / `edge_chain_hash` field on
`TraceEdgeRecord`; module exports match design pin;
v1.28 event-log modules unaffected.

### v1.29.2.4 Validation

- `pytest -q`: **5420 passed, 2 skipped, 1 deselected
  / 5423 collected** (5383 → 5420; +37 tests).
- `ruff check japan-financial-world`: clean.
- `python -m compileall -q
  japan-financial-world/world japan-financial-world/spaces
  japan-financial-world/tests japan-financial-world/examples`:
  clean.
- All v1.21.last canonical living-world digests
  preserved byte-identical.
- v1.28 event-log substrate intact; no v1.28 test
  affected.
- No new dependency; no `pyproject.toml` change.

---

## v1.29.3 implementation note

*v1.29.3 ships `CitationGraphProjection` — a frozen,
deterministic, read-only projection from
`EventLogRecord` + `TraceEdgeRecord` into an audit-
oriented graph summary. Materialised view, not source
of truth. No graph database, no networkx, no centrality
/ PageRank / community detection / embedding, no
counterfactual replay.*

### v1.29.3.1 Surface

In [`world/citation_graph_projection.py`](../world/citation_graph_projection.py):

- `CitationGraphProjection` (frozen dataclass:
  `run_id`, `node_event_ids`, `edge_ids`,
  `nodes_by_record_type`, `edges_by_type`,
  `edges_by_category`, `evidence_ref_counts`,
  `citation_ref_counts`, `actor_edge_counts`,
  `disconnected_event_ids`,
  `dangling_source_event_ids`,
  `dangling_target_event_ids`,
  `projection_digest`).
- `build_citation_graph_projection(event_records,
  trace_edges, *, run_id)` — deterministic builder.

Determinism contract (binding):

- Inputs are not mutated.
- Event records sorted by `event_id` for the
  canonical node-id list and for
  `nodes_by_record_type`.
- Trace edges sorted by `canonical_sort_key` for the
  canonical edge-id list, count aggregations, and
  the `projection_digest` payload.
- All count-pair tuples sorted by key ascending.
- Empty inputs → empty outputs (deterministic).
- Edges whose `source_event_id` /
  `target_event_id` are not present in the supplied
  event records surface as
  `dangling_source_event_ids` /
  `dangling_target_event_ids` (sorted, deduplicated).
- Events that appear in no trace edge surface as
  `disconnected_event_ids` (sorted).
- `projection_digest` is SHA-256 lowercase hex over
  the canonical payload that includes the trace
  edges in canonical sorted order plus the v1.29.1
  `TRACE_EDGE_SCHEMA_VERSION` sentinel; any edge-
  semantic change propagates.

### v1.29.3.2 What v1.29.3 does NOT ship

- No graph database (Neo4j / TigerGraph / etc.).
- No PROV-O / RDF / SPARQL / Cypher / rdflib /
  networkx / Gremlin.
- No graph centrality / PageRank / community-
  detection / embedding (forbidden-scope test
  enforces `def …centrality` /
  `def …pagerank` / `def …embedding` / call-site
  patterns are absent).
- No counterfactual replay.
- No `WorldKernel` field.
- No mutation of inputs.
- No mutation of any v1.28 event-log file or any
  v1.29.2 trace-edge file.

### v1.29.3.3 Tests added

`tests/test_citation_graph_projection.py` adds **+28
tests**. Coverage: dataclass shape; node_event_ids
sorted; edge_ids sorted by `canonical_sort_key` (NOT
alphabetic on edge_id — explicit expected-order
check); `nodes_by_record_type` /
`edges_by_type` / `edges_by_category` /
`evidence_ref_counts` / `citation_ref_counts` /
`actor_edge_counts` correct on a 3-event / 4-edge
fixture; deterministic across repeated calls;
edge-insertion-order independent; event-insertion-
order independent; projection_digest lowercase-hex-64;
projection_digest reacts to edge-semantic change
/ event-set change / run_id change; disconnected
event ids surfaced; dangling source / target
surfaced; empty-inputs deterministic; no-mutation of
inputs; type guards; empty run_id rejection; frozen
dataclass; forbidden-scope (no rdflib / sparql /
neo4j / networkx / gremlin / Polars / DuckDB /
PyArrow imports; no `def …centrality` /
`def …pagerank` / `def …embedding` definitions; no
`centrality(` / `pagerank(` / `embedding(` /
`louvain(` / `node2vec(` call sites); no
`WorldKernel` field; module exports match design
pin.

### v1.29.3.4 Validation

- `pytest -q`: **5448 passed, 2 skipped, 1 deselected
  / 5451 collected** (5420 → 5448; +28 tests).
- `ruff check japan-financial-world`: clean.
- `python -m compileall -q
  japan-financial-world/world japan-financial-world/spaces
  japan-financial-world/tests japan-financial-world/examples`:
  clean.
- All v1.21.last canonical living-world digests
  preserved byte-identical.
- v1.28 event-log substrate intact.
- No new dependency; no `pyproject.toml` change.

---

## v1.29.4 implementation note

*v1.29.4 ships read-only deterministic audit query
helpers over `TraceEdgeRecord` collections +
`CitationGraphProjection`. Answers a small fixed
catalogue of audit questions about **what is in the
event log**. Counterfactual replay (**what could
have been**) is explicitly out of scope.*

### v1.29.4.1 Surface

In [`world/audit_trace_queries.py`](../world/audit_trace_queries.py):

- Edge-type label sets (subsets of v1.29.1
  `TRACE_EDGE_TYPE_LABELS`):
  - `LINEAGE_EDGE_TYPE_LABELS`:
    `cited_as_evidence` / `derived_from` /
    `reviewed_under` / `constrained_by`.
  - `PROPAGATION_EDGE_TYPE_LABELS`:
    `propagated_to`.
  - `CONTRADICTION_EDGE_TYPE_LABELS`:
    `contradicted_by`.
- `list_edges_for_event(event_id, trace_edges)` —
  every edge that references `event_id` as source
  or target; sorted by `canonical_sort_key`.
- `list_evidence_for_judgment_event(event_id,
  trace_edges)` — sorted unique tuple of
  `evidence_ref_ids` cited by edges whose
  `target_event_id` matches.
- `list_events_citing_evidence(evidence_ref_id,
  trace_edges)` — sorted unique tuple of target
  event_ids whose edges include `evidence_ref_id` in
  `evidence_ref_ids` OR `citation_ids`.
- `list_edges_by_actor(actor_id, trace_edges)` —
  every edge whose `actor_id` matches; sorted by
  `canonical_sort_key`.
- `list_propagation_edges(trace_edges)` — every edge
  with `edge_type_label in PROPAGATION_…` or
  `edge_category_label == "propagation"`.
- `list_contradiction_pairs(trace_edges)` — sorted
  unique tuple of
  `(source_event_id, target_event_id)` pairs from
  `contradicted_by` edges.
- `trace_lineage_to_origin(event_id, trace_edges, *,
  max_depth=16)` — bounded-depth ancestor walk along
  lineage-type edges. **Cycle-safe** (visited
  de-duplication). Deterministic regardless of input
  order.
- `summarize_audit_questions(projection,
  trace_edges, *, event_id, actor_id="",
  max_depth=16)` — single-call bundle returning a
  frozen :class:`AuditTraceSummary` (event_id,
  actor_id, edges_for_event, evidence_for_judgment,
  edges_by_actor, propagation_edges,
  contradiction_pairs, lineage_ancestors,
  projection_digest).

Counterfactual boundary (binding):

- `COUNTERFACTUAL_REPLAY_NOT_IMPLEMENTED_MESSAGE` is
  a module-level constant explicitly stating the
  boundary.
- v1.29.4 helpers answer "**which** judgments depend
  on evidence X?" — i.e. dependency lookup. They do
  **not** answer "**what would change** if evidence
  X were withdrawn?" — that requires future
  deterministic replay (likely v1.30+).

### v1.29.4.2 What v1.29.4 does NOT ship

- No `def replay(`, no `def counterfactual_replay`,
  no `def what_if_…`, no `def simulate_without_…`.
- No graph database / Neo4j / TigerGraph / SPARQL /
  Cypher / Gremlin / rdflib / networkx.
- No Polars / DuckDB / PyArrow.
- No prediction / forecast / investment output.
- No `WorldKernel` field.

### v1.29.4.3 Tests added

`tests/test_audit_trace_queries.py` adds **+34
tests**. Coverage: edge-type label sets are subsets
of v1.29.1 `TRACE_EDGE_TYPE_LABELS`;
`list_edges_for_event` finds source + target /
deterministic / unknown-id-empty / empty-id-rejected;
`list_evidence_for_judgment_event` correct +
deterministic; `list_events_citing_evidence`
includes evidence_ref AND citation_ids /
deterministic; `list_edges_by_actor` correct +
deterministic; `list_propagation_edges` correct +
includes category-only match; `list_contradiction_pairs`
correct + deterministic; `trace_lineage_to_origin`
walks lineage edges to depth 1 ({e1, e2}); respects
max_depth (0 / 1); handles cycles safely (2-cycle
terminates); deterministic; rejects negative /
non-int max_depth; ignores non-lineage edges;
`summarize_audit_questions` returns dataclass /
deterministic / rejects non-projection / frozen
dataclass; counterfactual-replay-not-implemented
constant is a string, mentions "counterfactual" and
"v1.30"; module no `def replay` / `def
counterfactual_replay` / `def what_if_` /
`def simulate_without_` definitions; module no
graph DB / SPARQL / Cypher / Gremlin / rdflib /
networkx / Polars / DuckDB / PyArrow imports; module
text contains no `buy_signal` / `sell_signal` /
`target_price` / `alpha_claim` / `backtest_claim` /
`investment_advice` / `ownership_percentage` /
`voting_power` identifier; no `WorldKernel` field;
module exports match design pin.

### v1.29.4.4 Validation

- `pytest -q`: **5482 passed, 2 skipped, 1 deselected
  / 5485 collected** (5448 → 5482; +34 tests).
- `ruff check japan-financial-world`: clean.
- `python -m compileall -q
  japan-financial-world/world japan-financial-world/spaces
  japan-financial-world/tests japan-financial-world/examples`:
  clean.
- All v1.21.last canonical living-world digests
  preserved byte-identical.
- v1.28 event-log substrate intact.
- No new dependency; no `pyproject.toml` change.

---

## v1.29.0 closing statement

v1.29.0 is a docs-only design pin. It introduces
no runtime module, no new dataclass, no new
ledger event, no new test, no new label
vocabulary, no new fixture, no graph database
dependency, no PROV-O / RDF / SPARQL / Cypher /
Neo4j / networkx implementation, no counterfactual
replay engine, no investment recommendation
surface. v1.29.0 changes no canonical
`living_world_digest` value.

v1.29.0 only **defines the architecture** for the
trace-graph layer above the v1.28 event-log
substrate: a future `TraceEdgeRecord` shape
(closed-set procedural relation labels), a future
`CitationGraphProjection` (deterministic, read-
only, recomputable), and a future audit-facing
query surface. The architecture coexists with the
v1.28 substrate; it does not replace it. v1.29.x
sub-milestones implement strictly to this design,
in serial order, each behind its own design pin.

The next milestone (provisional) is **v1.29.1
`TraceEdgeRecord` schema + canonical serializer**.
v1.29.0 does not start it; v1.29.1 requires its
own design pin or design-pin amendment before
implementation.
