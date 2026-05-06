# v1.26 Entity Lifecycle + Reporting Calendar Foundation — Design Note

*v1.26 is the **generic, country-neutral substrate**
that prepares public-v1.x for future Japan public
calibration without using any Japan data. It adds two
append-only storage primitives — a v1.x universe-event
ledger and a per-entity reporting-calendar profile — and
one read-only readout that surfaces "which entities are
active as of a given period" + "which entities are
reporting-due as of a given period." It does not ingest
real data, name any real company, or apply any
jurisdiction-specific calibration; the v1.26 substrate
is the foundation v2.x Japan public calibration will
later condition on.*

This document is **docs-only at v1.26.0**. It introduces
no runtime module, no new dataclass, no new ledger
event, no new test, no new label vocabulary, no new
behavior. It is the binding scope pin for v1.26.x;
v1.26.1 / v1.26.2 / v1.26.3 / v1.26.4 / v1.26.last must
implement exactly to this design or the design must be
re-pinned.

The companion documents are:

- [`v1_25_institutional_investor_mandate_benchmark_pressure.md`](v1_25_institutional_investor_mandate_benchmark_pressure.md)
  §21 — the v1.25.last freeze v1.26 sits alongside.
- [`world_model.md`](world_model.md) §135 — the
  constitutional position of v1.26.
- [`v1_19_local_run_bridge_and_temporal_profiles_design.md`](v1_19_local_run_bridge_and_temporal_profiles_design.md)
  — the v1.19 monthly_reference profile that
  v1.26's ReportingCalendarProfile generalises.
- [`v1_20_monthly_scenario_reference_universe_design.md`](v1_20_monthly_scenario_reference_universe_design.md)
  — the v1.20 reference universe v1.26's
  UniverseEventBook layers over (read-only).

---

## 1. Scope statement (binding)

v1.26's single goal is narrow: **add the generic,
country-neutral substrate primitives needed before any
v2.x Japan public calibration can begin — without
ingesting any real data.**

Concretely:

- A **`UniverseEventRecord`** is one append-only,
  closed-set-label record describing one entity-
  lifecycle event (listing / delisting / merger /
  rename / split / status change). The record cites
  one or more existing entity ids via plain-id
  citation; it does **not** create, modify, or
  delete the cited entities.
- A **`ReportingCalendarProfile`** is one append-
  only, closed-set-label record describing one
  entity's reporting calendar — fiscal-year-end
  month, quarterly reporting months, disclosure
  cluster band, reporting intensity band. The
  profile cites one entity id via plain-id citation.
- A **`UniverseCalendarReadout`** is one immutable,
  read-only multiset projection over the kernel's
  `UniverseEventBook` + `ReportingCalendarProfileBook`
  + a caller-supplied `as_of_period_id`. It surfaces
  which entities are active as of that period, which
  entities are reporting-due as of that period, and
  which lifecycle events have fired prior to that
  period.
- The substrate is **empty-by-default on the
  kernel**. Both books are wired with
  `field(default_factory=...)`; an empty book emits
  no ledger record, leaving every existing
  `living_world_digest` byte-identical at v1.26.x.
  **A kernel without any UniverseEvent records
  continues to run as a static universe**, exactly
  as it did at v1.25.last. The v1.26 substrate adds
  primitives; it does not change how primitives that
  already exist behave.

What v1.26 is (binding):

- **Generic and country-neutral.** No Japan
  calibration. No real data ingestion. No real
  company name. No EDINET / JPX / TOPIX / Nikkei /
  GICS / MSCI / S&P / FactSet / Bloomberg /
  Refinitiv dependency. The fiscal-year-end month
  closed set is `month_01` … `month_12` plus
  `unknown` — no Japanese-fiscal-year (3月期)
  specialisation. v1.26 stays inside the v1.x
  jurisdiction-neutral boundary.
- **Append-only.** No event ever mutates a prior
  event; no profile ever mutates a prior profile;
  no event or profile ever mutates any existing
  source-of-truth book.
- **Read-only with respect to the world.** Adding
  a `UniverseEventRecord` does **not** delete or
  modify the cited entity in any other kernel book.
  The only "deactivation" surface is the v1.26.3
  read-only readout's `inactive_entity_ids`
  computation, which is purely a projection of the
  event ledger.
- **No forecast / no market effect inference.** A
  reporting-calendar profile says "this entity's
  fiscal year ends in `month_03`"; it does **not**
  say "this entity's earnings will move the market
  in `month_05`". The v1.26 readout exposes counts
  and label tuples, never a magnitude or
  probability.
- **Sequence is strictly serial.** v1.26.0 ships
  docs only; v1.26.1 ships UniverseEvent storage;
  v1.26.2 ships ReportingCalendar storage; v1.26.3
  ships the read-only universe-calendar readout;
  v1.26.4 ships optional export + minimal UI;
  v1.26.last ships the docs-only freeze.

What v1.26 is **NOT** (binding):

- v1.26 is **NOT** Japan calibration. No Japanese
  fiscal year cluster, no Japanese disclosure
  cluster, no real Japanese issuer ids, no real
  Japanese reporting calendar.
- v1.26 is **NOT** real data ingestion. v1.26.x
  does not download, parse, or ingest any external
  dataset. Synthetic profiles only.
- v1.26 is **NOT** an entity book. v1.26 does not
  introduce a new "entities" canonical book; it
  cites existing entity ids (firms / banks /
  investors) via plain-id citation. The
  `UniverseEventBook` is the *event* ledger over
  those existing ids.
- v1.26 is **NOT** a price / forecast surface. No
  earnings-date-to-price mapping, no event-study
  framework, no expected-response model.
- v1.26 is **NOT** an actor decision. No firm /
  investor / bank decision is fired or modified by
  any v1.26 record.
- v1.26 is **NOT** an interaction-inference layer.
  The v1.21.0a *Deferred: StressInteractionRule*
  boundary applies verbatim to v1.26.x.
- v1.26 is **NOT** a strategic-relationship
  surface. Cross-shareholding / supplier /
  governance relationships are the v1.27 candidate.
- v1.26 is **NOT** a UI rebuild. v1.26.4 may add a
  small read-only "Universe / calendar" panel
  inside an existing sheet; it adds no tab, no
  backend, no scrollable free-text input.

---

## 2. Why v1.26 follows v1.25 (sequencing, not coupling)

The v1.25 sequence (Generic Institutional Investor
Mandate / Benchmark Pressure) added an attention-
context conditioning surface; v1.25.last is **frozen**
and v1.25 explicitly does **not** make the system
Japan-ready. The post-v1.25 review identified four
substrate gaps that must close before v2.0 Japan
public calibration boundary design begins:

1. **Time-varying universe** — v1.x has no entity
   lifecycle. A real Japanese listed universe at
   v2.x will need to record listings / delistings /
   mergers; v1.26 ships the generic substrate.
2. **Reporting calendar heterogeneity** — v1.19's
   `monthly_reference` profile assumes uniform
   reporting; a real Japanese listed universe has
   wide fiscal-year-end / disclosure-cluster
   variation. v1.26 ships the generic substrate.
3. **Strategic relationship network** — v1.27
   candidate; not in v1.26 scope.
4. **Annotation provenance hardening** — v1.27
   candidate; not in v1.26 scope.

v1.26 closes substrate gaps **1 and 2**. The
abstractions are deliberately generic so v2.x can
calibrate on top without touching the v1.x layer.

v1.26 does **not** depend on v1.25 runtime behaviour
(or v1.24 / v1.23 / v1.22 / v1.21 runtime behaviour);
the two surfaces are decoupled. A kernel that loads no
mandate profile and no annotation continues to satisfy
every v1.21.last / v1.22.last / v1.23.last / v1.24.last
/ v1.25.last freeze pin verbatim.

---

## 3. What `UniverseEventRecord` is (binding)

A **universe event** is one immutable, append-only
record describing a single entity-lifecycle event.
The record is **descriptive**, not interpretive: it
says "as of this period, this event happened to
these entities", not "this event caused that price /
recommendation / decision."

### 3.1 Proposed shape (design level)

```python
@dataclass(frozen=True)
class UniverseEventRecord:
    """Immutable, append-only record of one entity-
    lifecycle event."""

    universe_event_id: str
    effective_period_id: str
    event_type_label: str
    affected_entity_ids: tuple[str, ...]
    predecessor_entity_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    successor_entity_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    citation_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )
```

### 3.2 Field semantics (binding)

- `universe_event_id` — stable id, unique within
  the `UniverseEventBook`. Plain string id.
- `effective_period_id` — plain-string period id
  that defines when the event takes effect. v1.26
  does not pin a period-id format (the v1.16.x /
  v1.19.x layers use ISO date strings; v1.20.x
  uses `month_01`-style labels); the v1.26 layer
  treats `effective_period_id` as opaque text and
  the v1.26.3 readout filters lexicographically.
  A future v1.26.x.x correction may pin a period-
  id format.
- `event_type_label` — closed-set string, member
  of `UNIVERSE_EVENT_TYPE_LABELS` (§3.4).
- `affected_entity_ids` — non-empty tuple of
  plain-id citations to existing entities (firms /
  banks / investors, etc.). The book does **not**
  dereference these; the v1.26.3 readout cross-
  references them against existing kernel books
  for the unresolved-citation diagnostic.
- `predecessor_entity_ids` — optional tuple of
  plain-id citations naming the entities that
  ceased to exist as a result of the event (used
  for `entity_merged` / `entity_renamed`).
- `successor_entity_ids` — optional tuple of
  plain-id citations naming the entities that came
  into existence as a result of the event (used for
  `entity_split` / `entity_renamed`).
- `citation_ids` — optional tuple of plain-id
  citations to evidence records (e.g. v1.18.2
  scenario-context-shift ids, v1.21.3 readout ids,
  v1.24 manual-annotation ids). v1.26 does not
  enforce a closed-set prefix list at v1.26.0; the
  v1.26.3 readout surfaces unresolved citations
  diagnostically.
- `status` — small closed-set string (`"draft"` /
  `"active"` / `"superseded"` / `"archived"` /
  `"unknown"`). Status changes are recorded by
  appending a new event citing the prior one.
- `visibility` — small closed-set string
  (`"public"` / `"restricted"` / `"internal"` /
  `"private"` / `"unknown"`).
- `boundary_flags` — small mapping defaulted to
  the v1.26 anti-claim set (§5.1). Caller-set
  additional `True` flags allowed; default flags
  non-removable.
- `metadata` — opaque mapping scanned for
  forbidden keys.

### 3.3 Required-field discipline

- `universe_event_id`, `effective_period_id`,
  `event_type_label`, `affected_entity_ids`,
  `status`, `visibility` are required.
- `affected_entity_ids` must be a non-empty tuple
  of non-empty strings.
- All optional plain-id-tuple fields, when non-
  empty, must contain only non-empty strings.

### 3.4 `UNIVERSE_EVENT_TYPE_LABELS` closed set (binding)

```python
UNIVERSE_EVENT_TYPE_LABELS: frozenset[str] = frozenset({
    "entity_listed",
    "entity_delisted",
    "entity_merged",
    "entity_renamed",
    "entity_split",
    "entity_status_changed",
    "unknown",
})
```

The set is intentionally small. Adding a label
requires a fresh design pin.

### 3.5 Active-entity semantics (binding for v1.26.3)

The v1.26.3 readout computes "active as of
`as_of_period_id`" by walking the
`UniverseEventBook`'s events in `effective_period_id`
order (lexicographic ascending, then
`universe_event_id` lexicographic ascending as
tie-break) and applying:

- `entity_listed` adds every id in
  `affected_entity_ids` to the active set.
- `entity_delisted` removes every id in
  `affected_entity_ids` from the active set.
- `entity_merged` removes every id in
  `predecessor_entity_ids` from the active set
  and adds every id in `successor_entity_ids`.
- `entity_renamed` removes every id in
  `predecessor_entity_ids` and adds every id in
  `successor_entity_ids` (functionally identical
  to `entity_merged` at the active-set level; the
  distinction is recorded in the event type only).
- `entity_split` removes every id in
  `predecessor_entity_ids` and adds every id in
  `successor_entity_ids`.
- `entity_status_changed` does **not** alter the
  active set; the readout records the event but the
  active set is the set membership.
- `unknown` events are **logged in warnings** and
  do **not** alter the active set (the readout
  flags them so a reviewer can investigate).

When the kernel has **no** `UniverseEventRecord`,
the readout returns an empty active set + an
empty inactive set. The semantics for "static
universe" is preserved by the calling layer (e.g.
v1.20.5's universe sheet renders the existing
v1.20.1 generic-sector universe regardless of v1.26
state); v1.26 explicitly does **not** introduce a
"default universe" concept.

---

## 4. What `ReportingCalendarProfile` is (binding)

A **reporting calendar profile** is one immutable,
append-only record describing one entity's reporting
schedule: fiscal-year-end month, quarterly reporting
months, disclosure cluster band, reporting intensity.

### 4.1 Proposed shape (design level)

```python
@dataclass(frozen=True)
class ReportingCalendarProfile:
    """Immutable, append-only record of one entity's
    reporting calendar."""

    reporting_calendar_profile_id: str
    entity_id: str
    fiscal_year_end_month_label: str
    quarterly_reporting_month_labels: tuple[str, ...] = (
        field(default_factory=tuple)
    )
    disclosure_cluster_label: str = "unknown"
    reporting_intensity_label: str = "unknown"
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )
```

### 4.2 Field semantics (binding)

- `reporting_calendar_profile_id` — stable id,
  unique within the `ReportingCalendarProfileBook`.
- `entity_id` — plain-id citation to an existing
  entity. The book does **not** dereference; the
  v1.26.3 readout cross-references.
- `fiscal_year_end_month_label` — closed-set
  string from `MONTH_LABELS` (§4.4).
- `quarterly_reporting_month_labels` — tuple of 0
  to 4 month labels (each from `MONTH_LABELS`).
  Duplicates rejected at construction. v1.26
  expects "report quarterly" semantics; an entity
  that reports semi-annually carries a 2-element
  tuple, an entity that reports annually carries a
  1-element tuple, an entity that reports more
  often than quarterly is out of v1.26 scope.
- `disclosure_cluster_label` — closed-set string
  (`"concentrated"` / `"moderate"` / `"dispersed"`
  / `"unknown"`). Describes how concentrated the
  entity's disclosure month is *across the
  universe* — a `concentrated` entity files in
  the same month as many others, a `dispersed`
  entity files in an off-cycle month. v1.26 does
  **not** quantify the cluster; the label is
  descriptive.
- `reporting_intensity_label` — closed-set string
  (`"low"` / `"medium"` / `"high"` / `"unknown"`).
  Describes how much disclosure the entity emits
  per reporting period (number of disclosure
  artifacts, density of footnotes). v1.26 does
  **not** quantify intensity; the label is
  descriptive.

### 4.3 Required-field discipline

- `reporting_calendar_profile_id`, `entity_id`,
  `fiscal_year_end_month_label`,
  `disclosure_cluster_label`,
  `reporting_intensity_label`, `status`,
  `visibility` are required.
- `quarterly_reporting_month_labels` may be empty
  (annual reporting / unknown).
- One profile per entity in the v1.26.x
  implementation. A reviewer revising an entity's
  reporting calendar appends a new profile (the
  prior profile remains in the book; status
  change is recorded by appending a new profile
  citing the prior one).

### 4.4 `MONTH_LABELS` closed set (binding)

```python
MONTH_LABELS: frozenset[str] = frozenset({
    "month_01",
    "month_02",
    "month_03",
    "month_04",
    "month_05",
    "month_06",
    "month_07",
    "month_08",
    "month_09",
    "month_10",
    "month_11",
    "month_12",
    "unknown",
})
```

This closed set mirrors v1.20.2's
`SCHEDULED_MONTH_LABELS` deliberately — v1.26
inherits the v1.x convention rather than inventing
a new month vocabulary.

### 4.5 `DISCLOSURE_CLUSTER_LABELS` closed set (binding)

```python
DISCLOSURE_CLUSTER_LABELS: frozenset[str] = frozenset({
    "concentrated",
    "moderate",
    "dispersed",
    "unknown",
})
```

### 4.6 `REPORTING_INTENSITY_LABELS` closed set (binding)

```python
REPORTING_INTENSITY_LABELS: frozenset[str] = frozenset({
    "low",
    "medium",
    "high",
    "unknown",
})
```

---

## 5. Default boundary flags + forbidden tokens

### 5.1 Default boundary flags (binding)

Every emitted `UniverseEventRecord` and
`ReportingCalendarProfile` carries the v1.26 anti-
claim set. v1.26.1 / v1.26.2 construction merges
caller-supplied flags on top, but the defaults
below are non-removable:

```python
_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    # v1.18.0 boundary
    ("no_actor_decision", True),
    ("no_llm_execution", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_financing_execution", True),
    ("no_investment_advice", True),
    ("synthetic_only", True),
    # v1.21.0a additions (re-pinned at v1.26.0)
    ("no_aggregate_stress_result", True),
    ("no_interaction_inference", True),
    ("no_field_value_claim", True),
    ("no_field_magnitude_claim", True),
    # v1.26.0 additions
    ("descriptive_only", True),
    ("no_real_data_ingestion", True),
    ("no_japan_calibration", True),
    ("no_real_company_name", True),
    ("no_market_effect_inference", True),
    ("no_event_to_price_mapping", True),
    ("no_forecast_from_calendar", True),
)
```

A caller can set additional flags to `True`; a
caller **cannot** set any of the defaults to
`False`. Construction rejects any `False` override.

### 5.2 v1.26.0 forbidden-token delta (binding)

The v1.26.0 forbidden-token list extends the
v1.23.1 / v1.24.0 / v1.25.0 canonical composition
with v1.26-specific tokens:

```python
FORBIDDEN_TOKENS_V1_26_0_UNIVERSE_CALENDAR_DELTA: frozenset[str] = (
    frozenset({
        # v1.26.0 calendar / event-as-action prohibitions
        "earnings_surprise",
        "earnings_beat",
        "earnings_miss",
        "event_study_alpha",
        "event_window_return",
        "post_event_drift",
        "calendar_arbitrage",
        # v1.26.0 real-data / Japan-specific prohibitions
        "edinet",
        "edinet_xbrl",
        "edinet_filing_id",
        "j_quants",
        "tdnet",
        "fsa_filing",
        # v1.26.0 universe-as-portfolio prohibitions
        "universe_weight",
        "constituent_weight",
        "index_weight_change",
        "rebalance_event",
    })
)
```

The composed `FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES`
set will be:

```python
FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_19_3_REAL_INDICATOR_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_REAL_ISSUER_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_LICENSED_TAXONOMY_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
    | FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_24_0_MANUAL_ANNOTATION_DELTA
    | FORBIDDEN_TOKENS_V1_25_0_MANDATE_DELTA
    | FORBIDDEN_TOKENS_V1_26_0_UNIVERSE_CALENDAR_DELTA
)
```

Scan discipline (carried verbatim from v1.21.x /
v1.24.x / v1.25.x storage):

- Dataclass field names checked at construction.
- Payload keys (ledger payload mapping) checked at
  construction.
- Metadata keys checked at construction.
- Label values checked at construction (closed-set
  membership + belt-and-braces forbidden scan).

---

## 6. `UniverseEventBook` + `ReportingCalendarProfileBook` shape (design level)

```python
@dataclass
class UniverseEventBook:
    """Append-only storage for UniverseEventRecord."""

    ledger: Ledger | None = None
    clock: Clock | None = None
    _events: dict[str, UniverseEventRecord] = field(
        default_factory=dict
    )

    def add_event(
        self,
        event: UniverseEventRecord,
        *,
        simulation_date: Any = None,
    ) -> UniverseEventRecord: ...

    def get_event(
        self, universe_event_id: str
    ) -> UniverseEventRecord: ...

    def list_events(
        self,
    ) -> tuple[UniverseEventRecord, ...]: ...

    def list_by_event_type(
        self, event_type_label: str
    ) -> tuple[UniverseEventRecord, ...]: ...

    def list_by_entity(
        self, entity_id: str
    ) -> tuple[UniverseEventRecord, ...]: ...

    def list_by_effective_period(
        self, effective_period_id: str
    ) -> tuple[UniverseEventRecord, ...]: ...

    def snapshot(self) -> dict[str, Any]: ...


@dataclass
class ReportingCalendarProfileBook:
    """Append-only storage for ReportingCalendarProfile."""

    ledger: Ledger | None = None
    clock: Clock | None = None
    _profiles: dict[str, ReportingCalendarProfile] = (
        field(default_factory=dict)
    )

    def add_profile(...): ...
    def get_profile(...): ...
    def list_profiles(...): ...
    def list_by_entity(...): ...
    def list_by_fiscal_year_end_month(...): ...
    def list_by_reporting_month(...): ...
    def snapshot(...): ...
```

### 6.1 Storage discipline (binding)

- One ledger record per successful
  `add_event(...)` / `add_profile(...)` call.
  v1.26.1 emits `universe_event_recorded`;
  v1.26.2 emits
  `reporting_calendar_profile_recorded`.
- No ledger record on duplicate id (raises
  `DuplicateUniverseEventError` /
  `DuplicateReportingCalendarProfileError`).
- No mutation of any other source-of-truth book.
- No call to `apply_stress_program` /
  `apply_scenario_driver` / `add_annotation` /
  `add_profile` (the v1.25 mandate one) / any
  v1.15.x / v1.16.x intent helper.
- No automatic event / profile helper. The book
  exposes `add_event(event)` / `add_profile(profile)`
  only.

### 6.2 Empty-by-default kernel wiring (binding)

The kernel's `universe_events` and
`reporting_calendars` fields are wired with
`field(default_factory=...)`. An empty book emits
no ledger record. Therefore:

- A kernel with **no** `UniverseEventRecord`
  continues to run as a **static universe** —
  exactly as it did at v1.25.last and every prior
  freeze. No fixture changes; no digest movement.
- A kernel with **no** `ReportingCalendarProfile`
  continues to run with the **uniform reporting**
  semantics implied by v1.19's `monthly_reference`
  profile — exactly as before.
- Every v1.21.last canonical `living_world_digest`
  remains byte-identical at every v1.26.x sub-
  milestone:
  - `quarterly_default` —
    `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
  - `monthly_reference` —
    `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
  - `scenario_monthly_reference_universe` test-
    fixture —
    `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
  - v1.20.4 CLI bundle —
    `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`

The empty-by-default rule is the **single
mechanism** that lets v1.26 introduce a time-
varying universe primitive without breaking any
existing fixed-universe fixture. This is
deliberate: every v1.21.x / v1.24.x / v1.25.x
sub-milestone used the same pattern and v1.26
inherits it verbatim.

---

## 7. Read-only `UniverseCalendarReadout` (binding shape for v1.26.3)

`world/universe_calendar_readout.py` (NEW at
v1.26.3) will ship:

```python
@dataclass(frozen=True)
class UniverseCalendarReadout:
    """Immutable, read-only multiset projection over
    the UniverseEventBook + ReportingCalendarProfileBook
    + a caller-supplied as_of_period_id."""

    readout_id: str
    as_of_period_id: str
    active_entity_ids: tuple[str, ...]
    inactive_entity_ids: tuple[str, ...]
    lifecycle_event_ids: tuple[str, ...]
    listed_event_count: int
    delisted_event_count: int
    merged_event_count: int
    renamed_event_count: int
    split_event_count: int
    status_changed_event_count: int
    reporting_calendar_profile_ids: tuple[str, ...]
    reporting_due_entity_ids: tuple[str, ...]
    fiscal_year_end_month_counts: tuple[
        tuple[str, int], ...
    ]
    reporting_intensity_counts: tuple[
        tuple[str, int], ...
    ]
    disclosure_cluster_counts: tuple[
        tuple[str, int], ...
    ]
    warnings: tuple[str, ...]
    metadata: Mapping[str, Any]
```

### 7.1 Read-only discipline (binding)

- Same kernel state + same `as_of_period_id` →
  byte-identical readout. Cat 1 determinism extends
  verbatim.
- The readout emits **no** ledger record; v1.26.3
  ships **no** new `RecordType`.
- The readout does **not** mutate any kernel book.
- The readout does **not** call any apply / intent
  / annotation / mandate / book-add helper.
- No automatic interpretation. The readout never
  reduces multiple events into a "combined" event,
  never infers an interaction, never produces an
  outcome / impact / forecast / recommendation.
- **Counts are counts**, not scores — the v1.21.0a
  labels-not-numbers discipline applies. Each
  count tuple element is `(label, int)`; no float,
  no probability, no magnitude.

### 7.2 Helpers + markdown renderer

```python
def build_universe_calendar_readout(
    kernel: WorldKernel,
    *,
    as_of_period_id: str,
    readout_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> UniverseCalendarReadout: ...


def render_universe_calendar_readout_markdown(
    readout: UniverseCalendarReadout,
) -> str: ...
```

The markdown renderer emits 9 sections:

1. ``## Universe / calendar readout`` — id +
   period.
2. ``## Active entities`` — plain-id list.
3. ``## Inactive entities`` — plain-id list.
4. ``## Lifecycle event counts`` — closed-set
   count tuple per event type.
5. ``## Reporting calendar profiles`` — plain-id
   list.
6. ``## Reporting-due entities`` — plain-id list
   filtered by `as_of_period_id`'s month label.
7. ``## Fiscal-year-end month distribution`` —
   `(month_label, count)` tuple.
8. ``## Disclosure cluster + reporting intensity
   distribution`` — two count tuples.
9. ``## Boundary statement`` — pinned anti-claim
   block.

Reporting-due semantics: an entity is
"reporting-due as of `as_of_period_id`" if the
period's month label is in the entity's
`quarterly_reporting_month_labels`. v1.26.3
extracts the month label from
`as_of_period_id` via a small deterministic rule
(e.g. last segment after `:` is a month label, or
a configured period-id-to-month-label map; the
exact rule lands at v1.26.3 design time).

### 7.3 Inactive-reporting-profile warning

If a reporting-calendar profile cites an entity id
that the v1.26 active-set computation reports as
inactive at `as_of_period_id`, the readout
surfaces a `warning` entry. This is a diagnostic
only; the profile remains in the book. The
warning serves a future v1.x reviewer auditing the
substrate for stale calendar entries.

---

## 8. Optional export + minimal UI (design level for v1.26.4)

### 8.1 Export

v1.26.4 may add an optional descriptive-only
`universe_calendar_readout` payload section on
`RunExportBundle`. The section is **omitted when
empty** (no UniverseEvent record AND no
ReportingCalendarProfile in the kernel) so every
pre-v1.26 bundle digest stays byte-identical.

Allowed export keys (whitelist):

- `as_of_period_id`
- `active_entity_ids`
- `inactive_entity_ids`
- `lifecycle_event_ids`
- `reporting_calendar_profile_ids`
- `reporting_due_entity_ids`
- `fiscal_year_end_month_counts`
- `reporting_intensity_counts`
- `disclosure_cluster_counts`
- `warnings`

Forbidden (binding):

- `earnings_surprise` / `earnings_beat` /
  `earnings_miss` / any event-study or alpha
  language.
- `universe_weight` / `constituent_weight` / any
  index-weight language.
- `forecast` / `prediction` / `expected_return` /
  `target_price` / `recommendation`.
- `buy` / `sell` / `order` / `trade` /
  `execution`.
- `real_data` / `japan_calibration` /
  `real_company_name` / `edinet` / `tdnet` /
  `j_quants` / `gics` / `topix` / `nikkei` / `jpx`.
- v1.18.0 / v1.19.0 / v1.21.0a / v1.22.0 /
  v1.24.0 / v1.25.0 / v1.26.0 forbidden tokens at
  any depth.

### 8.2 UI

v1.26.4 may add a small read-only **"Universe /
calendar"** panel inside an existing sheet (likely
the existing Universe sheet, below the v1.25.3
Investor mandate context panel). The v1.20.5 11-tab
↔ 11-sheet bijection is preserved at v1.26.last;
v1.26.4 introduces no new tab.

Candidate panel content:

- active entity count;
- inactive entity count;
- lifecycle event counts (per type);
- reporting calendar profile count;
- reporting-due entity count;
- fiscal-year-end month distribution counts;
- disclosure cluster + reporting intensity counts;
- warnings count + first warning text.

Forbidden (binding):

- No real Japanese fiscal-year distribution
  (`month_03` heavy distribution would be a Japan
  calibration claim). v1.26 stays generic; an
  even or random distribution is acceptable.
- No price / forecast / recommendation wording.
- No allocation / weight / target / overweight /
  underweight wording.

`textContent` only for caller-supplied values.
If v1.26.4 prefers export-only (no UI), the
design pin permits skipping the UI panel entirely.

---

## 9. Sub-milestone sequence (binding for v1.26.x)

The sequence is **strictly serial**. v1.26.1 must
not start until v1.26.0 docs are merged + CI is
green. v1.26.2 must not start until v1.26.1
storage is byte-stable. v1.26.3 must not start
until v1.26.2 storage is in place. v1.26.4 must
not start until v1.26.3 readout ships. v1.26.last
must not start until v1.26.4 is shipped + CI is
green.

| Sub-milestone | Surface | What it ships |
| ------------- | ------- | ------------- |
| **v1.26.0** | docs only | This design pin (§§1-12). §135 in `world_model.md`. README §9 row. |
| v1.26.1 | runtime + tests | `UniverseEventRecord` + `UniverseEventBook` storage in [`world/universe_events.py`](../world/universe_events.py) (NEW). Closed-set `UNIVERSE_EVENT_TYPE_LABELS`. Default boundary flags. v1.26.0 forbidden-token delta (universe-events-only subset) + composed set added to [`world/forbidden_tokens.py`](../world/forbidden_tokens.py). New `UNIVERSE_EVENT_RECORDED` `RecordType`. Empty-by-default kernel field. ~ +12 tests. |
| v1.26.2 | runtime + tests | `ReportingCalendarProfile` + `ReportingCalendarProfileBook` storage in [`world/reporting_calendar_profiles.py`](../world/reporting_calendar_profiles.py) (NEW). Closed-set `MONTH_LABELS` / `DISCLOSURE_CLUSTER_LABELS` / `REPORTING_INTENSITY_LABELS`. Default boundary flags. New `REPORTING_CALENDAR_PROFILE_RECORDED` `RecordType`. Empty-by-default kernel field. ~ +12 tests. |
| v1.26.3 | runtime + tests | `UniverseCalendarReadout` + `build_universe_calendar_readout(...)` + `render_universe_calendar_readout_markdown(...)` in [`world/universe_calendar_readout.py`](../world/universe_calendar_readout.py) (NEW). Read-only / no ledger emission / no mutation. ~ +10 tests. |
| v1.26.4 | export + UI + tests | Optional descriptive-only `universe_calendar_readout` payload section on `RunExportBundle` (omitted-when-empty so v1.21.last digests stay byte-identical) + minimal "Universe / calendar" panel inside the existing Universe sheet (no new tab; `textContent` only). ~ +8 tests. |
| v1.26.last | docs only | Final freeze. Sequence map, hard-boundary re-pin, future candidates. |

### 9.1 Cardinality (binding for v1.26.x)

- **0** new closed-set vocabularies *outside* those
  pinned in §3.4 / §4.4 / §4.5 / §4.6 + the v1.26.3
  count-pair vocabularies (which reuse §4.4–§4.6).
- **3** new dataclasses across the v1.26.x
  sequence: `UniverseEventRecord` (v1.26.1),
  `ReportingCalendarProfile` (v1.26.2),
  `UniverseCalendarReadout` (v1.26.3).
- **2** new `RecordType` values:
  `UNIVERSE_EVENT_RECORDED` (v1.26.1) and
  `REPORTING_CALENDAR_PROFILE_RECORDED` (v1.26.2).
- **2** new ledger event types:
  `universe_event_recorded` and
  `reporting_calendar_profile_recorded` (only
  emitted when an event / profile is added; empty
  books are silent).
- **0** new tabs in the static UI.
- v1.26.1 expected test delta: **+ ~ 12**.
- v1.26.2 expected test delta: **+ ~ 12**.
- v1.26.3 expected test delta: **+ ~ 10**.
- v1.26.4 expected test delta: **+ ~ 8**.
- v1.26.last final test count target: **~ 5074**.

### 9.2 Digest preservation (binding)

Every v1.26.x sub-milestone preserves every
v1.21.last canonical `living_world_digest` byte-
identical via the empty-by-default rule. The
v1.26.3 readout helper is read-only; the v1.26.4
export section is omitted when empty.

---

## 10. Test plan summary (per sub-milestone)

### v1.26.1 — universe-event storage tests (~ +12)

1. `test_universe_event_record_validates_required_fields`
2. `test_universe_event_record_validates_event_type_label`
3. `test_universe_event_record_rejects_empty_affected_entity_ids`
4. `test_universe_event_record_rejects_forbidden_field_names`
5. `test_universe_event_record_rejects_forbidden_metadata_keys`
6. `test_universe_event_book_add_get_list_snapshot`
7. `test_universe_event_book_list_by_entity_includes_predecessor_and_successor`
8. `test_duplicate_universe_event_emits_no_extra_ledger_record`
9. `test_universe_event_storage_does_not_mutate_source_of_truth_books`
10. `test_world_kernel_universe_events_empty_by_default`
11. `test_universe_event_storage_does_not_call_apply_or_intent_helpers`
12. `test_existing_digests_unchanged_with_empty_universe_event_book`

### v1.26.2 — reporting-calendar storage tests (~ +12)

1. `test_reporting_calendar_profile_validates_required_fields`
2. `test_reporting_calendar_profile_validates_month_labels`
3. `test_reporting_calendar_profile_rejects_duplicate_quarterly_months`
4. `test_reporting_calendar_profile_rejects_too_many_quarterly_months`
5. `test_reporting_calendar_profile_rejects_forbidden_field_names`
6. `test_reporting_calendar_profile_rejects_forbidden_metadata_keys`
7. `test_reporting_calendar_profile_book_add_get_list_snapshot`
8. `test_reporting_calendar_profile_list_by_entity_and_fiscal_year_end_month`
9. `test_duplicate_reporting_calendar_profile_emits_no_extra_ledger_record`
10. `test_world_kernel_reporting_calendars_empty_by_default`
11. `test_reporting_calendar_storage_does_not_mutate_source_of_truth_books`
12. `test_existing_digests_unchanged_with_empty_reporting_calendar_book`

### v1.26.3 — universe-calendar readout tests (~ +10)

1. `test_universe_calendar_readout_is_read_only`
2. `test_active_set_changes_with_listed_and_delisted_events`
3. `test_merged_renamed_split_events_preserve_predecessor_successor`
4. `test_unknown_event_type_does_not_alter_active_set_and_warns`
5. `test_reporting_due_entity_ids_respect_quarterly_month_labels`
6. `test_inactive_reporting_profile_warning_visible`
7. `test_readout_emits_no_ledger_record`
8. `test_readout_does_not_mutate_kernel`
9. `test_readout_no_forbidden_wording_in_markdown`
10. `test_readout_deterministic_across_runs`

### v1.26.4 — export + UI tests (~ +8)

1. `test_export_omits_universe_calendar_readout_when_absent`
2. `test_existing_no_universe_calendar_bundle_digest_unchanged`
3. `test_export_includes_universe_calendar_readout_when_present`
4. `test_export_keys_are_descriptive_only`
5. `test_export_carries_no_forbidden_wording`
6. `test_ui_no_new_tab_added_at_v1_26_4` (if UI ships)
7. `test_ui_uses_textcontent_only` (if UI ships)
8. `test_existing_panels_still_render` (Active Stresses / Manual annotations / Investor mandate context)

### v1.26.0 / v1.26.last — what ships in tests

**Nothing.** v1.26.0 is docs-only. Test count holds
at 5032 / 5032 at v1.26.0 (and again at v1.26.last
after the v1.26.1-4 increments).

---

## 11. Hard boundary (re-pinned at v1.26.0)

v1.26.0 inherits and re-pins the v1.25.last hard
boundary in full. v1.26.x adds the v1.26-specific
prohibitions (§5.1 / §5.2):

**No real-world output.**
- No price formation, no market price, no order, no
  trade, no execution, no clearing, no settlement,
  no financing execution.
- No forecast / expected return / target price /
  recommendation / investment advice.
- No magnitude / probability / expected response.
- No firm decision, no investor action, no bank
  approval logic.
- No portfolio allocation, no target weight, no
  rebalancing.

**No real-world input.**
- No real data ingestion. No real institutional
  identifiers. No licensed taxonomy dependency. No
  Japan calibration. **No EDINET / TDnet /
  J-Quants / FSA filing adapter.**
- **No real Japanese fiscal-year distribution
  claim.** A `concentrated` `disclosure_cluster_label`
  describes synthetic clustering; it is not a Japan
  calibration claim.

**No autonomous reasoning.**
- No LLM execution. No LLM prose accepted as
  source-of-truth.
- No interaction auto-inference. No aggregate /
  combined / net / dominant / composite stress
  output.
- No auto-annotation (v1.24.0 boundary applies).
- v1.26.x adds: **no event-to-price mapping, no
  earnings-surprise / earnings-beat / earnings-miss
  inference, no event-study alpha, no event-window-
  return, no calendar-arbitrage claim.**

**No source-of-truth book mutation.**
- v1.26.x adds two storage books + one read-only
  readout + one optional export section + one
  optional UI panel. No v1.26.x helper mutates any
  pre-existing kernel book; pre-existing book
  snapshots remain byte-identical pre / post any
  v1.26.x helper call.

**No backend in the UI.**
- v1.26.4 may touch the static UI mockup; the
  v1.20.5 / v1.22.2 / v1.24.3 / v1.25.3 loader
  discipline is preserved. No new tab. No new
  sheet. No backend / fetch / XHR / file-system
  write.

**No digest movement.**
- v1.26.x preserves every v1.21.last canonical
  living-world digest byte-identical at every
  sub-milestone.

---

## 12. Read-in order (for a v1.26 reviewer)

1. [`v1_25_institutional_investor_mandate_benchmark_pressure.md`](v1_25_institutional_investor_mandate_benchmark_pressure.md)
   §21 "v1.25.last freeze" — the v1.25.last hard
   boundary v1.26 inherits.
2. This document — the v1.26.0 design pin.
3. [`world_model.md`](world_model.md) §135 — the
   constitutional position.
4. [`v1_19_local_run_bridge_and_temporal_profiles_design.md`](v1_19_local_run_bridge_and_temporal_profiles_design.md)
   — the v1.19 monthly_reference profile that
   v1.26's ReportingCalendarProfile generalises.
5. [`v1_20_monthly_scenario_reference_universe_design.md`](v1_20_monthly_scenario_reference_universe_design.md)
   — the v1.20 reference universe v1.26's
   UniverseEventBook layers over (read-only).

---

## 13. Deliverables for v1.26.0 (this PR)

- This design note:
  `docs/v1_26_entity_lifecycle_reporting_calendar_foundation.md`.
- New section §135 in `docs/world_model.md` —
  "v1.26 Entity Lifecycle + Reporting Calendar
  Foundation (design pointer, **v1.26.0 design-
  only**)".
- README §9 roadmap-row refresh — the v1.26 row
  updates from "Optional candidate" to "Design
  scoped at v1.26.0".

No runtime code change. No UI implementation. No
new tests. No new dataclass. No new ledger event.
No new label vocabulary. No digest movement. No
record-count change. No pytest-count change.

---

## 14. Cardinality summary (binding at v1.26.0)

- **0** new dataclasses at v1.26.0 (the
  `UniverseEventRecord` + `ReportingCalendarProfile`
  + `UniverseCalendarReadout` shapes are *designed*
  here, not *implemented*; they land at v1.26.1 /
  v1.26.2 / v1.26.3).
- **0** new ledger event types at v1.26.0.
- **0** new label vocabularies at v1.26.0 (the
  closed sets in §3.4 / §4.4 / §4.5 / §4.6 are
  *designed* here; they land at v1.26.1 / v1.26.2).
- **0** new runtime modules at v1.26.0.
- **0** new tests at v1.26.0.
- **0** new UI regions at v1.26.0; **0** new tabs
  at any v1.26.x milestone.
- v1.26.1 expected test delta: **+ ~ 12**.
- v1.26.2 expected test delta: **+ ~ 12**.
- v1.26.3 expected test delta: **+ ~ 10**.
- v1.26.4 expected test delta: **+ ~ 8**.
- v1.26.last final test count target: **~ 5074**.
- v1.21.last canonical digests: **byte-identical
  at every v1.26.x sub-milestone** — guaranteed by
  the empty-by-default rule.

The v1.26 sequence is scoped. Subsequent work
that touches the entity-lifecycle / reporting-
calendar layer must explicitly re-open scope under
a new design pin (a v1.26.0a or later correction);
silent extension is forbidden.

The static-universe / uniform-reporting semantics
of every existing fixed fixture is preserved by
the empty-by-default rule. v1.26 explicitly does
**not** introduce a "default universe" or "default
reporting calendar"; a kernel without v1.26
records continues to behave as it did at every
prior freeze.

---

## 15. v1.26.last freeze (docs-only)

*Final pin section for the v1.26 sequence. v1.26.last
ships **no** new code, no new tests, no new
RecordTypes, no new dataclasses, no new label
vocabularies, no UI regions, no export-schema
changes.*

### 15.1 Shipped sequence

| Sub-milestone | Surface |
| ------------- | ------- |
| v1.26.0 | docs-only design pin |
| v1.26.1 | UniverseEvent storage (12 tests) |
| v1.26.2 | ReportingCalendarProfile storage (12 tests) |
| v1.26.3 | UniverseCalendarReadout (10 tests) |
| v1.26.4 | export + minimal UI panel (10 tests) |
| v1.26.last | this freeze |

### 15.2 Pinned at v1.26.last

- `pytest -q`: **5076 / 5076 passing** (+44 vs v1.25.last).
- `ruff check .`: clean.
- `python -m compileall -q world spaces tests examples`:
  clean.
- All v1.21.last canonical living-world digests
  preserved byte-identical at every v1.26.x sub-
  milestone.
- Source-of-truth book mutations from v1.26.x
  helpers: 0.
- Ledger emissions from v1.26.x helpers (other than
  the one `UNIVERSE_EVENT_RECORDED` /
  `REPORTING_CALENDAR_PROFILE_RECORDED` event per
  caller-initiated `add_event` / `add_profile` call):
  0.
- New `RecordType` values: 2.
- New dataclasses: 3 (`UniverseEventRecord`,
  `ReportingCalendarProfile`,
  `UniverseCalendarReadout`).
- New tabs: 0.
- Export schema changes: 1 optional /
  omitted-when-empty field
  (`universe_calendar_readout`).

### 15.3 Closing statement

v1.26 substrate is generic and country-neutral. It
adds time-varying-universe + reporting-calendar
primitives but does **not** ingest real data, claim
any Japan calibration, or add real-company
identifiers. The empty-by-default rule preserves
every existing fixed fixture byte-identically.

The v1.26 sequence is **frozen**. v1.27 candidate
(Generic Strategic Relationship Network +
Annotation Provenance Hardening) is the next
milestone; v2.0 candidate (Japan Public
Calibration Boundary Design) follows v1.27.
